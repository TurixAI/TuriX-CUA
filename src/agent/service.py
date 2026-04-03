from __future__ import annotations
import asyncio
import base64
import io
import json
import logging
import os
import tempfile
from pathlib import Path
import re
from datetime import datetime
from typing import Any, Callable, Optional, Type, TypeVar
from collections import OrderedDict

import pyautogui
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage
from openai import RateLimitError
from pydantic import BaseModel, ValidationError
from PIL import Image

from src.agent.message_manager.service import MessageManager
from src.agent.prompts import (
    BrainPrompt_turix,
    ActorPrompt_turix,
    MemoryPrompt,
    PlannerPrompt,
)
from src.agent.views import (
    ActionResult,
    AgentError,
    AgentHistory,
    AgentHistoryList,
    AgentOutput,
    AgentStepInfo,
    AgentBrain,
)
from src.utils.record_store import RecordStore
from src.utils.brain_search import BrainSearchFlow
from src.utils.skills import (
    load_skill_metadata,
    load_skill_contents,
    format_skill_catalog,
    format_skill_context,
)
from src.agent.planner_service import Planner
from src.controller.service import Controller
from src.utils import time_execution_async
from src.utils.token_counter import TokenCounter
from src.agent.output_schemas import OutputSchemas
from src.agent.structured_llm import *

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

TASK_ID_MAX_LEN = 60
MAX_PENDING_LINES = 20
MAX_BRAIN_CONTEXT_ENTRIES = 50


def _task_to_slug(task: str, max_len: int = TASK_ID_MAX_LEN) -> str:
    task = task.strip().lower()
    task = re.sub(r"[^a-z0-9]+", "-", task)
    task = task.strip("-")
    if not task:
        task = "task"
    return task[:max_len]


def _default_agent_id(task: str, now: datetime) -> str:
    date_str = now.strftime("%Y-%m-%d")
    slug = _task_to_slug(task)
    return f"{date_str}_{slug}"


def screenshot_to_dataurl(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format="PNG")
    base64_encoded = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_encoded}"


def downscale_screenshot_by_tier(screenshot):
    """
    Apply tiered screenshot downscaling:
    - 720p/1080p: keep original
    - 2K/4K (and >2200px, <8K): divide width/height by 2
    - 8K/16K: divide width/height by 4
    """
    width, height = screenshot.size
    max_dim = max(width, height)
    scale_factor = 1

    if max_dim >= 7680:
        scale_factor = 4
    elif max_dim > 2200:
        scale_factor = 2

    if scale_factor == 1:
        return screenshot

    target_size = (max(1, width // scale_factor), max(1, height // scale_factor))
    if hasattr(Image, "Resampling"):
        resample = Image.Resampling.LANCZOS
    else:
        resample = Image.LANCZOS
    resized = screenshot.resize(target_size, resample=resample)
    logger.debug(
        "Downscaled screenshot from %sx%s to %sx%s (scale factor: %s)",
        width,
        height,
        resized.width,
        resized.height,
        scale_factor,
    )
    return resized


def llm_supports_response_format(llm: Optional[BaseChatModel]) -> bool:
    if llm is None:
        return False
    explicit = getattr(llm, "_turix_supports_response_format", None)
    if explicit is not None:
        return bool(explicit)
    return True


def to_structured(llm: BaseChatModel, Schema, Structured_Output) -> BaseChatModel:
    """
    Wrap any LangChain chat model with the right structured-output mechanism:

    - ChatOpenAI / AzureChatOpenAI -> bind(response_format=...) (OpenAI style)
    - ChatAnthropic / ChatGoogleGenerativeAI -> with_structured_output(...) (Claude/Gemini style)
    - ChatOllama -> bind(format=<json schema>) (Ollama json schema, when enabled)
    - anything else -> returned unchanged
    """
    OPENAI_CLASSES: tuple[Type[BaseChatModel], ...] = (ChatOpenAI, AzureChatOpenAI)
    ANTHROPIC_OR_GEMINI: tuple[Type[BaseChatModel], ...] = (
        ChatAnthropic,
        ChatGoogleGenerativeAI,
    )
    OLLAMA_CLASSES: tuple[Type[BaseChatModel], ...] = (ChatOllama,)

    if isinstance(llm, OPENAI_CLASSES):
        # OpenAI cloud endpoint expects flattened json_schema fields under
        # response_format (type/name/schema/strict), while many OpenAI-compatible
        # backends accept the nested {"type":"json_schema","json_schema":{...}}.
        response_format = Schema
        base_url = str(getattr(llm, "openai_api_base", "") or getattr(llm, "base_url", "") or "").lower()
        is_openai_cloud = (not base_url) or ("api.openai.com" in base_url)
        if is_openai_cloud and isinstance(Schema, dict):
            schema_type = Schema.get("type")
            json_schema = Schema.get("json_schema")
            if schema_type == "json_schema" and isinstance(json_schema, dict):
                flat = {"type": "json_schema"}
                if json_schema.get("name"):
                    flat["name"] = json_schema.get("name")
                if json_schema.get("schema") is not None:
                    flat["schema"] = json_schema.get("schema")
                if json_schema.get("strict") is not None:
                    flat["strict"] = json_schema.get("strict")
                response_format = flat
        return llm.bind(response_format=response_format)

    if isinstance(llm, ANTHROPIC_OR_GEMINI):
        return llm.with_structured_output(Structured_Output)

    if isinstance(llm, OLLAMA_CLASSES):
        if not llm_supports_response_format(llm):
            logger.info(
                "Structured response_format is disabled for Ollama model '%s'; falling back to prompt-only JSON.",
                getattr(llm, "model_name", getattr(llm, "model", "unknown")),
            )
            return llm
        # Ollama expects a raw JSON schema in the "format" param.
        schema = None
        if isinstance(Schema, dict):
            json_schema = Schema.get("json_schema")
            if isinstance(json_schema, dict):
                schema = json_schema.get("schema")
        return llm.bind(format=schema or "json")

    return llm


class Agent:
    def __init__(
        self,
        task: str,
        brain_llm: BaseChatModel,
        actor_llm: BaseChatModel,
        memory_llm: BaseChatModel,
        controller: Controller = Controller(),
        use_search: bool = True,
        use_skills: bool = False,
        skills_dir: Optional[str] = None,
        skills_max_chars: int = 4000,
        planner_llm: Optional[BaseChatModel] = None,
        save_planner_conversation_path: Optional[str] = None,
        save_planner_conversation_path_encoding: Optional[str] = "utf-8",
        save_brain_conversation_path: Optional[str] = None,
        save_brain_conversation_path_encoding: Optional[str] = "utf-8",
        save_actor_conversation_path: Optional[str] = None,
        save_actor_conversation_path_encoding: Optional[str] = "utf-8",
        artifacts_dir: Optional[str] = None,
        max_failures: int = 5,
        memory_budget: int = 500,
        summary_memory_budget: Optional[int] = None,
        retry_delay: int = 10,
        max_input_tokens: int = 32000,
        resume: bool = False,
        include_attributes: list[str] = [
            "title",
            "type",
            "name",
            "role",
            "tabindex",
            "aria-label",
            "placeholder",
            "value",
            "alt",
            "aria-expanded",
        ],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,
        register_new_step_callback: Callable[["str", "AgentOutput", int], None] | None = None,
        register_done_callback: Callable[["AgentHistoryList"], None] | None = None,
        tool_calling_method: Optional[str] = "auto",
        agent_id: Optional[str] = None,
    ):
        self.wait_this_step = False
        self.current_time = datetime.now()
        self.agent_id = agent_id or _default_agent_id(task, self.current_time)
        self.task = task
        self.artifacts_dir = Path(artifacts_dir).expanduser().resolve() if artifacts_dir else None
        if self.artifacts_dir:
            self.images_dir = str(self.artifacts_dir / "images" / self.agent_id)
            self.save_temp_file_path = str(self.artifacts_dir / "temp_files")
        else:
            self.images_dir = "images"
            self.save_temp_file_path = os.path.join(os.path.dirname(__file__), "temp_files")
        self.original_task = task
        self.resume = resume
        self.memory_llm = to_structured(memory_llm, OutputSchemas.MEMORY_RESPONSE_FORMAT, MemoryOutput)
        self.brain_llm = to_structured(brain_llm, OutputSchemas.BRAIN_RESPONSE_FORMAT, BrainOutput)
        self.actor_llm = to_structured(actor_llm, OutputSchemas.ACTION_RESPONSE_FORMAT, ActorOutput)
        self.planner_llm_raw = planner_llm
        self.planner_llm = to_structured(planner_llm, OutputSchemas.PLANNER_RESPONSE_FORMAT, PlannerOutput)
        self.token_counter = TokenCounter(brain_llm)
        self.memory_budget_tokens = max(1, int(memory_budget))
        default_summary_budget = max(1, self.memory_budget_tokens * 4)
        self.summary_memory_budget_tokens = max(
            1,
            int(summary_memory_budget) if summary_memory_budget is not None else default_summary_budget,
        )
        # Backward-compatible aliases used by older run artifacts/config assumptions.
        self.memory_budget = self.memory_budget_tokens
        self.summary_memory_budget = self.summary_memory_budget_tokens
        self.memory_warn_ratio = 0.7
        self.memory_hard_ratio = 1.0

        self.save_actor_conversation_path = save_actor_conversation_path
        self.save_actor_conversation_path_encoding = save_actor_conversation_path_encoding
        self.save_brain_conversation_path = save_brain_conversation_path
        self.save_brain_conversation_path_encoding = save_brain_conversation_path_encoding
        self.save_planner_conversation_path = save_planner_conversation_path
        self.save_planner_conversation_path_encoding = save_planner_conversation_path_encoding or "utf-8"

        self.include_attributes = include_attributes
        self.max_error_length = max_error_length
        self.screenshot_annotated = None
        self.max_input_tokens = max_input_tokens
        self.use_search = use_search
        self.use_skills = use_skills
        self.skills_dir = Path(skills_dir).expanduser() if skills_dir else None
        self.skills_max_chars = max(0, skills_max_chars or 0)
        self.available_skills = []
        self.selected_skills = []
        self.skill_context = ""
        self.next_goal = ""
        self.brain_thought = ""
        self.current_state: dict[str, str] = {
            "step_evaluate": "unknown",
            "ask_human": "No",
            "next_goal": "",
        }

        self.controller = controller
        self.max_actions_per_step = max_actions_per_step
        self.last_step_action = None
        self.goal_action_memory = OrderedDict()

        self.last_goal = None
        self.brain_context = OrderedDict()
        self.status = "success"
        self._setup_action_models()
        # self._set_model_names()

        if self.resume and not agent_id:
            raise ValueError("Agent ID is required for resuming a task.")
        self.save_temp_file_path = os.path.join(self.save_temp_file_path, f"{self.agent_id}")
        self.record_dir = os.path.join(self.save_temp_file_path, "records")
        self.record_store = RecordStore(
            self.record_dir,
            encoding=self.save_brain_conversation_path_encoding or "utf-8",
        )
        self.memory_snapshot_dir = os.path.join(self.save_temp_file_path, "memory_snapshots")
        self.memory_snapshot_store = RecordStore(
            self.memory_snapshot_dir,
            encoding=self.save_brain_conversation_path_encoding or "utf-8",
        )
        self.brain_search = BrainSearchFlow(self.record_store)
        logger.info("Agent ID: %s", self.agent_id)
        logger.info("Agent memory path: %s", self.save_temp_file_path)

        if self.use_skills and self.skills_dir:
            self.available_skills = load_skill_metadata(self.skills_dir)
            if not self.available_skills:
                logger.info("No skills loaded from %s", self.skills_dir)
            else:
                skill_names = ", ".join(skill.name for skill in self.available_skills)
                logger.info(
                    "Loaded %d skill(s) from %s: %s",
                    len(self.available_skills),
                    self.skills_dir,
                    skill_names,
                )
        elif self.use_skills:
            logger.info("Skills enabled but no skills directory provided.")

        if self.planner_llm:
            skill_catalog = ""
            if self.use_skills and self.available_skills:
                skill_catalog = format_skill_catalog(self.available_skills)
            planner_preplan_llm = self.planner_llm_raw if (self.use_search or self.use_skills) else None
            self.planner = Planner(
                planner_llm=self.planner_llm,
                task=self.task,
                max_input_tokens=self.max_input_tokens,
                preplan_llm=planner_preplan_llm,
                use_search=self.use_search,
                skill_catalog=skill_catalog,
                use_skills=self.use_skills,
                available_skills=self.available_skills,
                skills_max_chars=self.skills_max_chars,
                save_planner_conversation_path=self.save_planner_conversation_path,
                save_planner_conversation_path_encoding=self.save_planner_conversation_path_encoding,
            )
        elif self.use_skills:
            logger.info("Skills enabled but planner is disabled. Set agent.use_plan=true to select skills.")

        self.initiate_messages()
        self._last_result = None

        self.register_new_step_callback = register_new_step_callback
        self.register_done_callback = register_done_callback

        self.history: AgentHistoryList = AgentHistoryList(history=[])
        self.n_steps = 1
        self.consecutive_failures = 0
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self._paused = False
        self._stopped = False
        self.brain_memory = ""
        self.summary_memory = ""
        self.recent_memory = ""
        # Pending step lines are finalized in the next brain step.
        self.pending_recent_memory = ""
        self.memory_snapshot_files: list[dict[str, Any]] = []
        self.infor_memory = []
        self.last_pid = None
        self.ask_for_help = False

    def _set_model_names(self) -> None:
        self.chat_model_library = self.llm.__class__.__name__
        if hasattr(self.llm, "model_name"):
            self.model_name = self.llm.model_name  # type: ignore
        elif hasattr(self.llm, "model"):
            self.model_name = self.llm.model  # type: ignore
        else:
            self.model_name = "Unknown"

    def set_tool_calling_method(self, tool_calling_method: Optional[str]) -> Optional[str]:
        if tool_calling_method == "auto":
            if self.chat_model_library == "ChatGoogleGenerativeAI":
                return None
            if self.chat_model_library == "ChatOpenAI":
                return "function_calling"
            if self.chat_model_library == "AzureChatOpenAI":
                return "function_calling"
            return None

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        self.ActionModel = self.controller.registry.create_action_model()
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)

    def get_last_pid(self) -> Optional[int]:
        latest_pid = self.last_pid
        if self._last_result:
            for r in self._last_result:
                if r.current_app_pid:
                    latest_pid = r.current_app_pid
        return latest_pid

    def _refresh_brain_memory(self) -> None:
        parts = []
        if self.summary_memory:
            parts.append(
                "Summarized memory (compressed from earlier steps, details may be approximate):\n"
                + self.summary_memory
            )
        if self.recent_memory:
            parts.append("Recent steps:\n" + self.recent_memory)
        if self.pending_recent_memory:
            parts.append("Pending steps (not yet evaluated):\n" + self.pending_recent_memory)
        self.brain_memory = "\n\n".join(parts).strip()

    @property
    def total_memory_tokens(self) -> int:
        return (
            self.token_counter.count(self.summary_memory)
            + self.token_counter.count(self.recent_memory)
            + self.token_counter.count(self.pending_recent_memory)
        )

    def _log_memory_metrics(self) -> None:
        logger.info(
            "[Memory] Step %d | recent=%d tokens | summary=%d tokens | pending=%d tokens | total=%d/%d tokens | info_files=%d",
            self.n_steps,
            self.token_counter.count(self.recent_memory),
            self.token_counter.count(self.summary_memory),
            self.token_counter.count(self.pending_recent_memory),
            self.total_memory_tokens,
            self.memory_budget_tokens + self.summary_memory_budget_tokens,
            len(self.infor_memory),
        )

    def _is_summary_valid(self, original_text: str, summary_text: str, tier: str) -> bool:
        summary_tokens = self.token_counter.count(summary_text)
        original_tokens = self.token_counter.count(original_text)

        if summary_tokens < 10:
            logger.warning(
                "[Memory] %s summary too short (%d tokens). Keeping original.",
                tier,
                summary_tokens,
            )
            return False
        if original_tokens > 0 and summary_tokens >= original_tokens:
            logger.warning(
                "[Memory] %s summary (%d tokens) not shorter than original (%d tokens). Keeping original.",
                tier,
                summary_tokens,
                original_tokens,
            )
            return False
        return True

    def _extract_response_token_usage(self, response: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        usage_candidates = []
        response_metadata = getattr(response, "response_metadata", None)
        if isinstance(response_metadata, dict):
            usage_candidates.append(response_metadata.get("token_usage"))
            usage_candidates.append(response_metadata.get("usage"))
        usage_metadata = getattr(response, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            usage_candidates.append(usage_metadata)
        if isinstance(response, dict):
            usage_candidates.append(response.get("token_usage"))
            usage_candidates.append(response.get("usage"))

        usage = next((item for item in usage_candidates if isinstance(item, dict)), {})
        if not isinstance(usage, dict):
            return None, None, None

        def _to_int(value: Any) -> Optional[int]:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        prompt_tokens = _to_int(usage.get("prompt_tokens"))
        if prompt_tokens is None:
            prompt_tokens = _to_int(usage.get("input_tokens"))

        completion_tokens = _to_int(usage.get("completion_tokens"))
        if completion_tokens is None:
            completion_tokens = _to_int(usage.get("output_tokens"))

        total_tokens = _to_int(usage.get("total_tokens"))
        if total_tokens is None:
            total_tokens = self.token_counter.count_from_api_usage(response)

        return prompt_tokens, completion_tokens, total_tokens

    def _extract_memory_payload(self, response: Any) -> dict:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(response, dict):
            return response
        memory_text = str(getattr(response, "content", response))
        cleaned_memory_response = re.sub(r"^```(json)?", "", memory_text.strip())
        cleaned_memory_response = re.sub(r"```$", "", cleaned_memory_response).strip()
        logger.debug("[Memory] Raw text: %s", cleaned_memory_response)
        return json.loads(cleaned_memory_response)

    async def _run_memory_summary(self, memory_text: str, context_label: str) -> tuple[str, str]:
        memory_content = [
            {
                "type": "text",
                "content": f"{context_label}\n\n{memory_text}",
            }
        ]
        self.memory_message_manager._remove_last_state_message()
        self.memory_message_manager._remove_last_AIntool_message()
        self.memory_message_manager.add_state_message(memory_content)
        memory_messages = self.memory_message_manager.get_messages()
        response = await self.memory_llm.ainvoke(memory_messages)
        prompt_tokens, completion_tokens, total_tokens = self._extract_response_token_usage(response)
        estimate_tokens = self.token_counter.count(memory_text)
        if total_tokens:
            logger.info(
                "[Memory] Summary call (%s) token usage | prompt=%s output=%s total=%s estimate_input=%d",
                context_label,
                prompt_tokens if prompt_tokens is not None else "?",
                completion_tokens if completion_tokens is not None else "?",
                total_tokens,
                estimate_tokens,
            )
        if prompt_tokens is not None:
            logger.debug(
                "[Memory] Input token estimate delta (%s): estimate=%d, prompt=%d, delta=%d",
                context_label,
                estimate_tokens,
                prompt_tokens,
                estimate_tokens - prompt_tokens,
            )
        if completion_tokens is not None and completion_tokens > max(128, self.memory_budget_tokens // 2):
            logger.warning(
                "[Memory] Summary output is large (%d tokens). Compression quality may be poor.",
                completion_tokens,
            )
        parsed = self._extract_memory_payload(response)
        summary = str(parsed.get("summary", "")).strip()
        file_name = str(parsed.get("file_name", "")).strip()
        return summary, file_name

    def _save_memory_snapshot(
        self,
        memory_text: str,
        file_name: str,
        source: str,
        step_override: Optional[int] = None,
    ) -> Optional[str]:
        if not memory_text:
            return None
        step_value = step_override if step_override is not None else self.n_steps
        safe_name = file_name or f"memory_snapshot_{source}_step_{step_value}.txt"
        saved_name = self.memory_snapshot_store.save(memory_text, safe_name, step=step_value)
        self.memory_snapshot_files.append(
            {
                "file_name": saved_name,
                "source": source,
                "step": step_value,
            }
        )
        return saved_name

    async def _summarise_memory(self) -> None:
        """
        Summarise recent memory to reduce its size without counting summaries in the budget.
        """
        await self._summarise_recent_memory()

    async def _summarise_recent_memory(self, step_override: Optional[int] = None) -> None:
        if not self.recent_memory:
            return
        try:
            summary, file_name = await self._run_memory_summary(
                self.recent_memory,
                "Summarize the following recent-step memory.",
            )
        except Exception:
            logger.exception("[Memory] Failed to summarize recent memory.")
            self._save_memory_snapshot(self.recent_memory, "", "recent", step_override=step_override)
            self._refresh_brain_memory()
            return

        self._save_memory_snapshot(self.recent_memory, file_name, "recent", step_override=step_override)
        if not summary:
            logger.warning("[Memory] Empty summary from memory model; keeping recent memory.")
            self._refresh_brain_memory()
            return
        if not self._is_summary_valid(self.recent_memory, summary, tier="Recent"):
            self._refresh_brain_memory()
            return

        if self.summary_memory:
            self.summary_memory = "\n".join([self.summary_memory, summary]).strip()
        else:
            self.summary_memory = summary
        self.recent_memory = ""
        await self._summarise_summary_memory(step_override=step_override)
        self._refresh_brain_memory()

    async def _summarise_summary_memory(self, step_override: Optional[int] = None) -> None:
        if not self.summary_memory:
            return
        if self.token_counter.count(self.summary_memory) <= self.summary_memory_budget_tokens:
            return
        try:
            summary, file_name = await self._run_memory_summary(
                self.summary_memory,
                "Summarize the following accumulated summaries into a higher-level summary.",
            )
        except Exception:
            logger.exception("[Memory] Failed to summarize accumulated summaries.")
            self._save_memory_snapshot(self.summary_memory, "", "summary", step_override=step_override)
            return

        self._save_memory_snapshot(self.summary_memory, file_name, "summary", step_override=step_override)
        if not summary:
            logger.warning("[Memory] Empty high-level summary; keeping existing summaries.")
            self._refresh_brain_memory()
            return
        if not self._is_summary_valid(self.summary_memory, summary, tier="Higher-level"):
            self._refresh_brain_memory()
            return
        self.summary_memory = summary
        self._refresh_brain_memory()

    async def _update_memory(self) -> None:
        """
        Update memory content.
        """
        sorted_steps = sorted(self.brain_context.keys(), reverse=True)
        if not sorted_steps:
            return
        current_state = self.brain_context[sorted_steps[0]]["current_state"]
        step_goal = current_state["next_goal"] if current_state else None
        step_id = sorted_steps[0]

        # Always write the current step as pending. The success/failed signal for step N
        # arrives in brain_step() of step (N+1). Pending lines do not count toward budget.
        line = f"Step {step_id} | Eval: pending | Goal: {step_goal}"
        pending_lines = [ln for ln in self.pending_recent_memory.splitlines() if ln.strip()]
        pending_lines = [ln for ln in pending_lines if not ln.startswith(f"Step {step_id} |")]
        pending_lines.append(line)
        if len(pending_lines) > MAX_PENDING_LINES:
            pending_lines = pending_lines[-MAX_PENDING_LINES:]
            logger.warning("[Memory] Trimmed pending memory to last %d lines.", MAX_PENDING_LINES)
        self.pending_recent_memory = "\n".join(pending_lines).strip()
        self._refresh_brain_memory()
        self._log_memory_metrics()

    def save_memory(self) -> None:
        """Save the current memory to a file."""
        if not self.save_temp_file_path:
            return
        data = {
            "pid": self.get_last_pid(),
            "task": self.task,
            "next_goal": self.next_goal,
            "last_step_action": self.last_step_action,
            "infor_memory": self.infor_memory,
            "brain_context": self.brain_context,
            "step": self.n_steps,
            "summary_memory": self.summary_memory,
            "pending_recent_memory": self.pending_recent_memory,
            "recent_memory": self.recent_memory,
            "memory_budget_tokens": self.memory_budget_tokens,
            "summary_memory_budget_tokens": self.summary_memory_budget_tokens,
            # Backward-compatible fields
            "memory_budget": self.memory_budget_tokens,
            "summary_memory_budget": self.summary_memory_budget_tokens,
            "recent_memory_tokens": self.token_counter.count(self.recent_memory),
            "summary_memory_tokens": self.token_counter.count(self.summary_memory),
            "pending_memory_tokens": self.token_counter.count(self.pending_recent_memory),
            "total_memory_tokens": self.total_memory_tokens,
            "memory_snapshot_files": self.memory_snapshot_files,
        }
        file_name = os.path.join(self.save_temp_file_path, "memory.jsonl")
        dir_name = os.path.dirname(file_name)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=self.save_brain_conversation_path_encoding) as f:
                f.write(json.dumps(data, ensure_ascii=False, default=lambda o: list(o) if isinstance(o, set) else o) + "\n")
                # f.flush()
                # os.fsync(f.fileno())
            os.replace(tmp_path, file_name)
        except Exception:
            logger.exception("[Memory] Failed to save memory.")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def load_memory(self) -> None:
        """Load the current memory from a file."""
        if not self.save_temp_file_path:
            return
        file_name = os.path.join(self.save_temp_file_path, "memory.jsonl")
        if os.path.exists(file_name):
            with open(file_name, "r", encoding=self.save_brain_conversation_path_encoding) as f:
                lines = f.readlines()
            if len(lines) >= 1:
                data = json.loads(lines[-1])
                self.task = data.get("task", "")
                self.last_pid = data.get("pid", None)
                self.infor_memory = data.get("infor_memory", [])
                self.brain_context = data.get("brain_context", OrderedDict())
                if self.brain_context:
                    self.brain_context = OrderedDict({int(k): v for k, v in self.brain_context.items()})
                    while len(self.brain_context) > MAX_BRAIN_CONTEXT_ENTRIES:
                        self.brain_context.popitem(last=False)
                self.summary_memory = data.get("summary_memory", "")
                self.pending_recent_memory = data.get("pending_recent_memory", "")
                self.recent_memory = data.get("recent_memory", "")
                self.memory_budget_tokens = data.get(
                    "memory_budget_tokens",
                    data.get("memory_budget", self.memory_budget_tokens),
                )
                self.summary_memory_budget_tokens = data.get(
                    "summary_memory_budget_tokens",
                    data.get("summary_memory_budget", self.summary_memory_budget_tokens),
                )
                self.memory_budget_tokens = max(1, int(self.memory_budget_tokens))
                self.summary_memory_budget_tokens = max(1, int(self.summary_memory_budget_tokens))
                self.memory_budget = self.memory_budget_tokens
                self.summary_memory_budget = self.summary_memory_budget_tokens
                self.n_steps = int(data.get("step", 1))
                self.memory_snapshot_files = data.get("memory_snapshot_files", [])
                # Back-compat: older runs may have stored pending lines in recent_memory.
                if self.recent_memory:
                    recent_lines = [ln for ln in self.recent_memory.splitlines() if ln.strip()]
                    keep_recent: list[str] = []
                    move_pending: list[str] = []
                    for ln in recent_lines:
                        if "| Eval: pending |" in ln:
                            move_pending.append(ln)
                        else:
                            keep_recent.append(ln)
                    if move_pending:
                        self.pending_recent_memory = "\n".join(
                            [ln for ln in [self.pending_recent_memory, "\n".join(move_pending)] if ln]
                        ).strip()
                        self.recent_memory = "\n".join(keep_recent).strip()
                pending_lines = [ln for ln in self.pending_recent_memory.splitlines() if ln.strip()]
                if len(pending_lines) > MAX_PENDING_LINES:
                    self.pending_recent_memory = "\n".join(pending_lines[-MAX_PENDING_LINES:]).strip()
                if "summary_memory" not in data and "recent_memory" not in data:
                    await self._rebuild_memory_from_context()
                else:
                    self._refresh_brain_memory()
                self._log_memory_metrics()
                self.last_step_action = data.get("last_step_action", None)
                self.next_goal = data.get("next_goal", "")
                logger.info("Loaded memory from %s", file_name)

    async def _rebuild_memory_from_context(self) -> None:
        self.summary_memory = ""
        self.recent_memory = ""
        self.memory_snapshot_files = []
        for step_id in sorted(self.brain_context.keys()):
            current_state = self.brain_context[step_id].get("current_state", {})
            evaluation = current_state.get("step_evaluate")
            step_goal = current_state.get("next_goal")
            line = f"Step {step_id} | Eval: {evaluation} | Goal: {step_goal}"
            self.recent_memory = "\n".join([ln for ln in [self.recent_memory, line] if ln]).strip()
            if self.token_counter.count(self.recent_memory) > self.memory_budget_tokens:
                await self._summarise_recent_memory(step_override=step_id)
        self._refresh_brain_memory()
        self._log_memory_metrics()

    @time_execution_async("--brain_step")
    async def brain_step(self) -> dict:
        step_id = self.n_steps
        logger.info("\nStep %s", self.n_steps)
        prev_step_id = step_id - 1
        try:
            self.previous_screenshot = self.screenshot_annotated
            screenshot = pyautogui.screenshot()
            screenshot = downscale_screenshot_by_tier(screenshot)
            self.screenshot_annotated = screenshot
            os.makedirs(self.images_dir, exist_ok=True)
            current_screenshot_path = os.path.join(self.images_dir, f"screenshot_{self.n_steps}.png")
            screenshot.save(current_screenshot_path)
            if self.screenshot_annotated:
                screenshot_dataurl = screenshot_to_dataurl(self.screenshot_annotated)
            if self.previous_screenshot:
                previous_screenshot_dataurl = screenshot_to_dataurl(self.previous_screenshot)
            info_files = "\n".join(str(item) for item in self.infor_memory) if self.infor_memory else "None"

            def build_state_content(
                read_files_content: Optional[str] = None,
                read_files_list: Optional[list[str]] = None,
            ) -> list[dict]:
                if step_id >= 2:
                    state_content = [
                        {
                            "type": "text",
                            "content": (
                                f"Previous step is {prev_step_id}.\n\n"
                                f"Recorded info files (filenames only):\n{info_files}\n\n"
                                f"Previous Actions Short History:\n{self.brain_memory}\n\n"
                            ),
                        }
                    ]
                else:
                    state_content = [
                        {
                            "type": "text",
                            "content": (
                                "This is the first step.\n\n"
                                "You should provide a JSON with a well-defined goal based on images information. "
                                "The other fields should be default value."
                            ),
                        }
                    ]
                if read_files_content:
                    files_label = ", ".join(read_files_list) if read_files_list else ""
                    read_label = (
                        f"Requested file contents for: {files_label}\n" if files_label else "Requested file contents:\n"
                    )
                    state_content.append(
                        {
                            "type": "text",
                            "content": f"{read_label}{read_files_content}",
                        }
                    )
                if step_id >= 2 and previous_screenshot_dataurl:
                    state_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": previous_screenshot_dataurl},
                        }
                    )
                if screenshot_dataurl:
                    state_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_dataurl},
                        }
                    )
                return state_content

            state_content = build_state_content()
            self.brain_message_manager._remove_last_state_message()
            self.brain_message_manager._remove_last_AIntool_message()
            self.brain_message_manager.add_state_message(state_content)
            brain_messages = self.brain_message_manager.get_messages()

            response = await self.brain_llm.ainvoke(brain_messages)
            parsed = self.brain_search.parse_response(str(response.content))
            parsed, brain_messages = await self.brain_search.maybe_reinvoke(
                parsed,
                build_state_content,
                self.brain_message_manager,
                self.brain_llm,
            )
            if "current_state" not in parsed or "analysis" not in parsed:
                raise ValueError("Brain response missing required fields after read-files handling.")
            self._save_brain_conversation(brain_messages, parsed, step=self.n_steps)
            self.brain_context[self.n_steps] = parsed
            while len(self.brain_context) > MAX_BRAIN_CONTEXT_ENTRIES:
                self.brain_context.popitem(last=False)
            self.next_goal = parsed["current_state"]["next_goal"]
            self.brain_thought = parsed["analysis"]
            self.current_state = parsed["current_state"]

            # Finalize the previous step's memory line based on this response's evaluation signal.
            # Keep step N in pending_recent_memory until step (N+1) arrives, so it won't be summarized away.
            if prev_step_id >= 1:
                raw_eval = str(self.current_state.get("step_evaluate", "")).lower()
                if "success" in raw_eval:
                    final_status = "success"
                elif "fail" in raw_eval:
                    final_status = "failed"
                else:
                    final_status = "pending"

                pending_lines = [ln for ln in self.pending_recent_memory.splitlines() if ln.strip()]
                new_pending: list[str] = []
                goal_text: Optional[str] = None
                for ln in pending_lines:
                    if ln.startswith(f"Step {prev_step_id} |"):
                        if "| Goal: " in ln:
                            goal_text = ln.split("| Goal: ", 1)[1].strip()
                        continue
                    new_pending.append(ln)
                self.pending_recent_memory = "\n".join(new_pending).strip()

                if goal_text is not None:
                    final_line = f"Step {prev_step_id} | Eval: {final_status} | Goal: {goal_text}"
                    recent_lines = [ln for ln in self.recent_memory.splitlines() if ln.strip()]
                    recent_lines = [ln for ln in recent_lines if not ln.startswith(f"Step {prev_step_id} |")]
                    recent_lines.append(final_line)
                    self.recent_memory = "\n".join(recent_lines).strip()
                    recent_tokens = self.token_counter.count(self.recent_memory)
                    hard_limit = int(self.memory_budget_tokens * self.memory_hard_ratio)
                    warn_limit = int(self.memory_budget_tokens * self.memory_warn_ratio)
                    if recent_tokens > hard_limit:
                        await self._summarise_recent_memory(step_override=prev_step_id)
                    elif recent_tokens > warn_limit:
                        logger.info(
                            "[Memory] Recent memory at %.0f%% of budget (%d/%d tokens). Compression will trigger soon.",
                            (recent_tokens / self.memory_budget_tokens) * 100,
                            recent_tokens,
                            self.memory_budget_tokens,
                        )
                        self._refresh_brain_memory()
                    else:
                        self._refresh_brain_memory()
                else:
                    self._refresh_brain_memory()
            self._log_memory_metrics()

        except Exception as e:
            logger.exception("[Brain] Unexpected error in brain_step.")
            return {"Brain_text": {"step_evaluate": "unknown", "reason": str(e)}}

    @time_execution_async("--actor_step")
    async def actor_step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        step_id = self.n_steps
        state = ""
        model_output = None
        result: list[ActionResult] = []
        prev_step_id = step_id - 1
        try:
            self.save_memory()
            info_files = "\n".join(str(item) for item in self.infor_memory) if self.infor_memory else "None"
            if self.n_steps >= 2:
                state_content = [
                    {
                        "type": "text",
                        "content": (
                            f"Recorded info files (filenames only): {info_files}\n\n"
                            f"Analysis to the current screen is: {self.brain_thought}.\n\n"
                            f"Your goal to achieve in this step is: {self.next_goal}\n\n"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)}},
                ]
            else:
                state_content = [
                    {
                        "type": "text",
                        "content": (
                            f"Analysis to the current screen is: {self.brain_thought}. "
                            f"Your goal to achieve in this step is: {self.next_goal}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)}},
                ]

            self.actor_message_manager._remove_last_AIntool_message()
            self.actor_message_manager._remove_last_state_message()
            self.actor_message_manager.add_state_message(state_content, step_info=step_info)

            actor_messages = self.actor_message_manager.get_messages()
            model_output, raw = await self.get_next_action(actor_messages)

            self.last_goal = self.next_goal
            if self.register_new_step_callback:
                self.register_new_step_callback(state, model_output, self.n_steps)
            self._save_actor_conversation(actor_messages, model_output, step=self.n_steps)

            self.actor_message_manager._remove_last_state_message()
            self.actor_message_manager.add_model_output(model_output)

            self.last_step_action = (
                [action.model_dump(exclude_unset=True) for action in model_output.action] if model_output else []
            )

            result = await self.controller.multi_act(model_output.action)
            self._last_result = result

            if len(self.last_step_action) == 0:
                self.wait_this_step = True
            elif "wait" in str(self.last_step_action[0]):
                self.wait_this_step = True
            else:
                self.wait_this_step = False
            if self.last_step_action and not self.wait_this_step:
                await self._update_memory()
                self.save_memory()

        except Exception as e:
            result = await self._handle_step_error(e)
            self._last_result = result
        finally:
            if result:
                self._make_history_item(model_output, state, result)
            if not self.wait_this_step:
                self.n_steps += 1

    async def _handle_step_error(self, error: Exception) -> list[ActionResult]:
        include_trace = logger.isEnabledFor(logging.DEBUG)
        error_msg = AgentError.format_error(error, include_trace=include_trace)
        prefix = f"Result failed {self.consecutive_failures + 1}/{self.max_failures} times:\n "

        if isinstance(error, (ValidationError, ValueError)):
            logger.error("%s%s", prefix, error_msg)
            if "Max token limit reached" in error_msg:
                self.actor_message_manager.max_input_tokens -= 500
                logger.info(
                    "Reducing agent max input tokens: %s", self.actor_message_manager.max_input_tokens
                )
                self.actor_message_manager.cut_messages()
            elif "Could not parse response" in error_msg:
                error_msg += "\n\nReturn a valid JSON object with the required fields."
            self.consecutive_failures += 1

        elif isinstance(error, RateLimitError):
            logger.warning("%s%s", prefix, error_msg)
            await asyncio.sleep(self.retry_delay)
            self.consecutive_failures += 1

        else:
            logger.error("%s%s", prefix, error_msg)
            self.consecutive_failures += 1

        return [ActionResult(error=error_msg, include_in_memory=True)]

    def _make_history_item(
        self,
        model_output: AgentOutput | None,
        state: str,
        result: list[ActionResult],
    ) -> None:
        history_item = AgentHistory(
            model_output=model_output,
            result=result,
            state=state,
        )
        self.history.history.append(history_item)

    @time_execution_async("--get_next_action")
    async def get_next_action(self, input_messages: list[BaseMessage]) -> AgentOutput:
        """
        Build a structured_llm approach on top of actor_llm.
        """
        response: dict[str, Any] = await self.actor_llm.ainvoke(input_messages)
        logger.debug("LLM response: %s", response)
        record = str(response.content)

        output_dict = json.loads(record)
        normalized_actions = []
        for action in output_dict.get("action", []):
            if not isinstance(action, dict) or not action:
                normalized_actions.append(action)
                continue
            outer_key = list(action.keys())[0]
            inner_value = action[outer_key] if isinstance(action, dict) else {}
            if outer_key == "record_info" and isinstance(inner_value, dict):
                information_stored = inner_value.get("text", "")
                file_name = inner_value.get("file_name", "")
                saved_name = self.record_store.save(
                    information_stored,
                    file_name,
                    screenshot=self.screenshot_annotated,
                    step=self.n_steps,
                )
                if saved_name and saved_name not in self.infor_memory:
                    self.infor_memory.append(saved_name)
            normalized_actions.append(action)
        parsed: AgentOutput | None = AgentOutput(action=normalized_actions)

        self._log_response(parsed)
        return parsed, record

    def _log_response(self, response: AgentOutput) -> None:
        if "Success" in self.current_state["step_evaluate"]:
            emoji = "OK"
        elif "Failed" in self.current_state["step_evaluate"]:
            emoji = "FAIL"
        else:
            emoji = "UNKNOWN"
        logger.info("%s Eval: %s", emoji, self.current_state["step_evaluate"])
        logger.info("Memory: %s", self.brain_memory)
        logger.info("Goal to achieve this step: %s", self.next_goal)
        for i, action in enumerate(response.action):
            logger.info("Action %s/%s: %s", i + 1, len(response.action), action.model_dump_json(exclude_unset=True))

    def _save_brain_conversation(
        self,
        input_messages: list[BaseMessage],
        response: Any,
        step: int,
    ) -> None:
        """
        Write all the Brain agent conversation into a file.
        """
        if not self.save_brain_conversation_path:
            return
        file_name = f"{self.save_brain_conversation_path}_brain_{step}.txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None

        with open(file_name, "w", encoding=self.save_brain_conversation_path_encoding) as f:
            self._write_messages_to_file(f, input_messages)
            if response is not None:
                self._write_response_to_file(f, response)

        logger.info("Brain conversation saved to: %s", file_name)

    def _save_actor_conversation(
        self,
        input_messages: list[BaseMessage],
        response: Any,
        step: int,
    ) -> None:
        """
        Write all the Actor agent conversation into a file.
        """
        if not self.save_actor_conversation_path:
            return
        file_name = f"{self.save_actor_conversation_path}_actor_{step}.txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None

        with open(file_name, "w", encoding=self.save_actor_conversation_path_encoding) as f:
            self._write_messages_to_file(f, input_messages)
            if response is not None:
                self._write_response_to_file(f, response)

        logger.info("Actor conversation saved to: %s", file_name)

    def _write_messages_to_file(self, f: Any, messages: list[BaseMessage]) -> None:
        for message in messages:
            f.write(f"\n{message.__class__.__name__}\n{'-'*40}\n")
            if isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            txt = item.get("content") or item.get("text", "")
                            f.write(f"[Text Content]\n{txt.strip()}\n\n")
                        elif item.get("type") == "image_url":
                            image_url = item["image_url"]["url"]
                            f.write(f"[Image URL]\n{image_url[:100]}...\n\n")
            else:
                f.write(f"{str(message.content)}\n\n")
            f.write("\n" + "=" * 60 + "\n")

    def _write_response_to_file(self, f: Any, response: Any) -> None:
        f.write("RESPONSE\n")
        f.write(str(response) + "\n")
        f.write("\n" + "=" * 60 + "\n")

    def _log_agent_run(self) -> None:
        logger.info("Starting task: %s", self.task)

    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        try:
            self._log_agent_run()

            if self.planner_llm and not self.resume:
                await self.edit()

            for step in range(max_steps):
                if self.resume:
                    await self.load_memory()
                    self.resume = False
                if self._too_many_failures():
                    break
                if not await self._handle_control_flags():
                    break

                await self.brain_step()
                await self.actor_step()

                if self.history.is_done():
                    logger.info("Task completed successfully")
                    if self.register_done_callback:
                        self.register_done_callback(self.history)
                    break
                await asyncio.sleep(2)
            else:
                logger.info("Failed to complete task in maximum steps")

            return self.history
        except Exception:
            logger.exception("Error running agent")
            raise

    async def edit(self):
        result = await self.planner.edit_task()
        self._set_new_task(result.raw_text, result.payload)

    PREFIX = "The overall user's task is: "
    SUFFIX = "The step by step plan is: "

    def _set_new_task(self, generated_plan: str, plan_payload: Optional[dict] = None) -> None:
        """
        Build the final task string:
            "The overall plan is: <original task>\n\n<generated plan>"
        and update every MessageManager in one go.
        """
        plan_text = generated_plan
        if isinstance(plan_payload, dict):
            plan_text = self._format_plan_payload(plan_payload)
        if generated_plan.startswith(self.PREFIX):
            final_task = generated_plan
        else:
            final_task = f"{self.PREFIX}{self.original_task}\n{self.SUFFIX}\n{plan_text}"

        if self.use_skills and self.available_skills:
            selected = []
            if isinstance(plan_payload, dict):
                selected = plan_payload.get("selected_skills", []) or []
            if isinstance(selected, list):
                selected = [str(s) for s in selected if isinstance(s, str) and s.strip()]
            else:
                selected = []

            self.selected_skills = selected
            if self.selected_skills:
                logger.info("Planner selected skills: %s", ", ".join(self.selected_skills))
            else:
                logger.info("Planner selected no skills.")
            skill_contents = load_skill_contents(
                self.available_skills,
                self.selected_skills,
                max_chars=self.skills_max_chars or None,
            )
            self.skill_context = format_skill_context(skill_contents)
            if self.skill_context:
                final_task = (
                    f"{final_task}\n\nSelected skills (planner-chosen):\n"
                    f"{self.skill_context}"
                )

        self.task = final_task
        self.initiate_messages()

    def _format_plan_payload(self, payload: dict) -> str:
        lines: list[str] = []
        iteration = payload.get("iteration_info")
        if isinstance(iteration, dict):
            current = iteration.get("current_iteration")
            total = iteration.get("total_iterations")
            if current and total:
                lines.append(f"Iteration: {current}/{total}")

        search_summary = payload.get("search_summary")
        if isinstance(search_summary, str) and search_summary.strip():
            lines.append(f"Search summary: {search_summary.strip()}")

        selected = payload.get("selected_skills")
        if isinstance(selected, list):
            selected_clean = [str(s) for s in selected if isinstance(s, str) and s.strip()]
            if selected_clean:
                lines.append(f"Selected skills: {', '.join(selected_clean)}")

        natural_plan = payload.get("natural_language_plan")
        if isinstance(natural_plan, str) and natural_plan.strip():
            lines.append("Plan:")
            lines.append(natural_plan.strip())
        else:
            steps = payload.get("step_by_step_plan")
            if isinstance(steps, list) and steps:
                lines.append("Plan:")
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    desc = step.get("description") or ""
                    info = step.get("important_search_info") or ""
                    if not desc:
                        continue
                    if info:
                        lines.append(f"- {desc} (search: {info})")
                    else:
                        lines.append(f"- {desc}")

        return "\n".join(lines) if lines else json.dumps(payload, ensure_ascii=False)

    def _too_many_failures(self) -> bool:
        if self.consecutive_failures >= self.max_failures:
            logger.error("Stopping due to %s consecutive failures", self.max_failures)
            return True
        return False

    async def _handle_control_flags(self) -> bool:
        if self._stopped:
            logger.info("Agent stopped")
            return False

        while self._paused:
            await asyncio.sleep(0.2)
            if self._stopped:
                return False

        return True

    def stop(self, reason: Optional[str] = None) -> None:
        if reason:
            logger.warning("Stopping agent: %s", reason)
        self._stopped = True

    def save_history(self, file_path: Optional[str | Path] = None) -> None:
        if not file_path:
            file_path = "AgentHistory.json"
        self.history.save_to_file(file_path)

    def initiate_messages(self):
        self.brain_message_manager = MessageManager(
            llm=self.brain_llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=BrainPrompt_turix,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            give_task=True,
        )
        self.actor_message_manager = MessageManager(
            llm=self.actor_llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=ActorPrompt_turix,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            give_task=False,
        )
        self.memory_message_manager = MessageManager(
            llm=self.memory_llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=MemoryPrompt,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            give_task=True,
        )
