from __future__ import annotations
import asyncio
import base64
import io
import json
import logging
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Optional, Type, TypeVar

# LangChain & AI Imports
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from openai import RateLimitError
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# Internal Imports
from src.agent.message_manager.service import MessageManager
from src.agent.views import (
    ActionResult, AgentError, AgentHistory, AgentHistoryList, 
    AgentOutput, AgentStepInfo, AgentBrain
)
from src.controller.service import Controller
from src.mac.tree import MacUITreeBuilder
from src.utils import time_execution_async
from src.agent.output_schemas import OutputSchemas
from src.agent.structured_llm import AgentStepOutput, PlannerOutput
from src.agent.prompts import SystemPrompt_turix, SystemPrompt, SystemPrompt_Planner 

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# --- Helper Functions ---

def screenshot_to_dataurl(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    base64_encoded = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{base64_encoded}'

def _get_installed_app_names() -> list[str]:
    """Returns a list of application names (minus ".app")"""
    apps = set()
    for apps_path in ["/Applications", "/System/Applications"]:
        if os.path.exists(apps_path):
            for item in os.listdir(apps_path):
                if item.endswith(".app"):
                    apps.add(item[:-4])
    return list(apps)

def to_structured(llm: BaseChatModel, Schema, Structured_Output) -> BaseChatModel:
    """
    Wrap LangChain chat model with structured-output mechanism.
    Handles differences between OpenAI (bind/parse) and Anthropic/Gemini (with_structured_output).
    """
    OPENAI_CLASSES = (ChatOpenAI, AzureChatOpenAI)
    ANTHROPIC_OR_GEMINI = (ChatAnthropic, ChatGoogleGenerativeAI)

    if isinstance(llm, OPENAI_CLASSES):
        # Scenario 1: Actor Mode (Schema provided)
        if Schema is not None:
            return llm.bind(response_format=Schema)
        # Scenario 2: Planner Mode (Pydantic model provided)
        elif Structured_Output is not None:
            return llm.with_structured_output(Structured_Output)

    if isinstance(llm, ANTHROPIC_OR_GEMINI):
        return llm.with_structured_output(Structured_Output)
    
    return llm

# --- Main Agent Class ---

class Agent:
    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        short_memory_len: int,
        controller: Controller = Controller(),
        use_ui: bool = False,
        use_turix: bool = True,
        save_conversation_path: Optional[str] = None,
        save_conversation_path_encoding: Optional[str] = 'utf-8',
        max_failures: int = 5,
        retry_delay: int = 10,
        system_prompt_class: Type[SystemPrompt] = SystemPrompt,
        max_input_tokens: int = 32000,
        resume: bool = False,
        include_attributes: list[str] = None,
        max_error_length: int = 400,
        max_actions_per_step: int = 10, 
        register_new_step_callback: Callable = None,
        register_done_callback: Callable = None,
        tool_calling_method: Optional[str] = 'auto',
        agent_id: Optional[str] = None,
        enable_step_memory: bool = False,
        step_memory_dir: str = "temp_files/step_memory",
        max_history_images: int = 2
    ):
        # 1. Identity & Task
        if agent_id:
            self.agent_id = agent_id
        else:
            # Use timestamp for easy debugging sorting
            self.agent_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.task = task
        self.resume = resume
        self.use_turix = use_turix
        self.current_time = datetime.now()

        # 2. LLM & Controller
        # Initialize Actor LLM
        self.llm = to_structured(llm, OutputSchemas.AGENT_RESPONSE_FORMAT, AgentStepOutput)
        # Initialize Planner LLM
        self.planner_llm = to_structured(llm, None, PlannerOutput)

        self.controller = controller
        self.mac_tree_builder = MacUITreeBuilder()
        self.use_ui = use_ui
        self._set_model_names()
        self.tool_calling_method = self.set_tool_calling_method(tool_calling_method)

        # 3. Memory Architecture (Tiered)
        self.enable_step_memory = enable_step_memory
        self.step_memory_dir = Path(step_memory_dir)
        self.step_memory_file = None
        
        if self.enable_step_memory:
            memory_path = self.step_memory_dir / "default_agent"
            memory_path.mkdir(parents=True, exist_ok=True)
            self.step_memory_file = memory_path / "step_memory.txt"
            logger.info(f"Step memory enabled at: {self.step_memory_file}")

        # Tiered Memory Structures
        self.full_step_history = []  # Master list for Short & Medium term
        self.infor_memory = []       # Information accumulator (text/numbers)
        self.short_term_limit = 6    # Steps > N-6 are detailed short-term memory
        self.medium_term_limit = 15  # Steps N-15 to N-6 are medium-term summaries
        self.max_history_images = max_history_images # Limit historical images to save tokens

        # 4. Configuration
        self.include_attributes = include_attributes or ['title', 'type', 'name', 'role', 'value', 'alt']
        self.max_input_tokens = max_input_tokens
        self.max_actions_per_step = max_actions_per_step
        self.max_error_length = max_error_length
        self.save_conversation_path = save_conversation_path
        self.save_conversation_path_encoding = save_conversation_path_encoding
        self.save_temp_file_path = os.path.join(os.path.dirname(__file__), 'temp_files', f"{self.agent_id}")

        # 5. Runtime State
        self.n_steps = 1
        self.consecutive_failures = 0
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self.last_pid = None
        self.last_goal = None
        self.last_step_action = None
        self.screenshot_annotated = None
        self._last_result = None
        self.wait_this_step = False
        self._paused = False
        self._stopped = False
        self.history = AgentHistoryList(history=[])

        # 6. Callbacks & Prompts
        self.register_new_step_callback = register_new_step_callback
        self.register_done_callback = register_done_callback
        self.system_prompt_class = SystemPrompt_turix if self.use_turix else system_prompt_class
        
        # 7. Setup
        self._setup_action_models()
        self.initiate_messages()

        if self.save_conversation_path:
            logger.info(f'Saving conversation to {self.save_conversation_path}')
        
        if self.resume and not agent_id:
            raise ValueError("Agent ID is required for resuming a task.")

    # --- Memory Management ---

    def _build_tiered_memory_context(self) -> str:
        """
        Constructs the tiered memory string (Long/Medium/Short) to be injected into the Prompt.
        """
        current_step = self.n_steps

        # 1. Long Term Memory (Episodic summaries from file)
        long_term_text = ""
        if self.enable_step_memory and self.step_memory_file and self.step_memory_file.exists():
            try:
                lines = self.step_memory_file.read_text(encoding="utf-8").strip().splitlines()
                filtered_summaries = []
                for line in lines:
                    match = re.match(r"Step (\d+):", line)
                    if match:
                        if int(match.group(1)) <= current_step - self.medium_term_limit:
                            filtered_summaries.append(line)
                if filtered_summaries:
                    long_term_text = "=== LONG TERM MEMORY (Summaries of past events) ===\n" + "\n".join(filtered_summaries) + "\n"
            except Exception as e:
                logger.warning(f"Failed to read long term memory: {e}")

        # 2. Medium Term Memory (Goals Only)
        medium_term_text = ""
        medium_steps = [
            item for item in self.full_step_history 
            if (current_step - self.medium_term_limit) < item['step'] <= (current_step - self.short_term_limit)
        ]
        if medium_steps:
            medium_term_text = "=== MEDIUM TERM MEMORY (Past Goals history) ===\n"
            for item in medium_steps:
                medium_term_text += f"Step {item['step']} Goal: {item['goal']}\n"
            medium_term_text += "\n"

        # 3. Short Term Memory (Detailed Context + Plan Snapshot)
        short_term_text = ""
        short_steps = [
            item for item in self.full_step_history 
            if item['step'] > (current_step - self.short_term_limit)
        ]
        if short_steps:
            short_term_text = "=== SHORT TERM MEMORY (Recent Detailed Context) ===\n"
            for item in short_steps:
                # Include the plan snapshot so the Planner knows what it thought previously
                plan_info = f"  Plan Snapshot: {item.get('plan', 'N/A')}\n" if item.get('plan') else ""
                short_term_text += (
                    f"Step {item['step']}:\n"
                    f"  Goal: {item['goal']}\n"
                    f"{plan_info}"
                    f"  Actions: {item['actions']}\n"
                )
            short_term_text += "\n"

        # 4. Debug Logging
        try:
            if self.save_temp_file_path:
                debug_log_content = (
                    f"\n{'='*30} STEP {self.n_steps} MEMORY INPUT {'='*30}\n"
                    f"🧠 [LONG TERM]:\n{long_term_text.strip() if long_term_text else '(Empty)'}\n\n"
                    f"📖 [MEDIUM TERM]:\n{medium_term_text.strip() if medium_term_text else '(Empty)'}\n\n"
                    f"⚡ [SHORT TERM]:\n{short_term_text.strip() if short_term_text else '(Empty)'}\n"
                    f"{'='*80}\n"
                )
                debug_file_path = os.path.join(self.save_temp_file_path, "memory_debug_log.txt")
                os.makedirs(os.path.dirname(debug_file_path), exist_ok=True)
                mode = 'w' if self.n_steps == 1 else 'a'
                with open(debug_file_path, mode, encoding="utf-8") as f:
                    f.write(debug_log_content)
                logger.info(f"💾 Memory context saved to: {debug_file_path}")
        except Exception as e:
            logger.warning(f"Failed to save memory debug log: {e}")

        return long_term_text + medium_term_text + short_term_text

    def _save_debug_log(self, title: str, content: Any) -> None:
        """Helper to append detailed execution logs (Planner thoughts / Actor actions) to a file."""
        if not self.save_temp_file_path:
            return
            
        file_path = os.path.join(self.save_temp_file_path, "execution_debug_log.txt")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*20} {title} {'='*20}\n")
                if hasattr(content, 'model_dump_json'):
                    f.write(content.model_dump_json(indent=2))
                else:
                    f.write(str(content))
                f.write(f"\n{'='*60}\n")
        except Exception as e:
            logger.warning(f"Failed to write debug log: {e}")

    def save_memory(self) -> None:
        """Saves current state to JSONL for crash recovery/resume."""
        if not self.save_temp_file_path:
            return
        
        data = {
            "pid": self.get_last_pid(),
            "task": self.task,
            "full_step_history": self.full_step_history,
            "infor_memory": self.infor_memory,
            "step": self.n_steps
        }
        file_name = os.path.join(self.save_temp_file_path, f"memory.jsonl")
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None
        with open(file_name, "w", encoding=self.save_conversation_path_encoding) as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def load_memory(self) -> None:
        """Loads state from JSONL to resume execution."""
        if not self.save_temp_file_path:
            return
        file_name = os.path.join(self.save_temp_file_path, f"memory.jsonl")
        if os.path.exists(file_name):
            try:
                with open(file_name, "r", encoding=self.save_conversation_path_encoding) as f:
                    lines = f.readlines()
                if len(lines) >= 1:
                    data = json.loads(lines[-1])
                    self.last_pid = data.get("pid", None)
                    self.full_step_history = data.get("full_step_history", [])
                    self.infor_memory = data.get("infor_memory", [])
                    self.n_steps = data.get("step", 1)
                    logger.info(f"Loaded memory from {file_name}")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")

    # --- Core Execution Logic ---
    
    @time_execution_async('--planner_think')
    async def get_planner_instruction(self, input_messages: list[BaseMessage]) -> PlannerOutput:
        """
        Invokes the Planner (Brain) model.
        It sees the history and state but outputs high-level reasoning, not actions.
        """
        # Replace the Actor's System Prompt with the Planner's System Prompt
        original_system_msg = input_messages[0]
        planner_system_msg = self.system_prompt_planner_class.get_system_message()
        
        # Filter images from history to save tokens
        planner_messages = [planner_system_msg] + input_messages[1:]
        final_planner_messages = self._filter_messages_with_images(planner_messages)
        
        response = await self.planner_llm.ainvoke(final_planner_messages)
        logger.info(f"🧠 Planner Output: {response}")
        return response

    @time_execution_async("--step")
    async def step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        """
        Main execution loop for a single step.
        Flow: UI Tree -> Memory -> Planner (Think) -> Actor (Act) -> Execute -> Save.
        """
        logger.info(f"\n📍 Step {self.n_steps}")
        state = "No UI state available"
        model_output = None
        result: list[ActionResult] = []

        try:
            # 1. UI Tree & Initial State
            if self.use_ui:
                self.last_pid = self.get_last_pid()
                root = await self.mac_tree_builder.build_tree(self.last_pid)
                state = root._get_visible_clickable_elements_string() if root else "No UI tree found."
            else:
                state = ''
            
            if self.n_steps == 1:
                apps = _get_installed_app_names()
                state = f'The available apps in this macbook is: {", ".join(apps)}'
            
            self.save_memory()
            
            # 2. Build Memory & Prompt Context
            tiered_memory_context = self._build_tiered_memory_context()
            
            screenshot = self.mac_tree_builder.capture_screenshot()
            self.screenshot_annotated = screenshot
            if self.n_steps >= 2 and self.use_ui and 'root' in locals() and root:
                 self.screenshot_annotated = self.mac_tree_builder.annotate_screenshot(root)

            # Save raw screenshot for debugging
            screenshot.save(f'images/screenshot_{self.n_steps}.png')

            prompt_content_text = (
                f"{tiered_memory_context}"
                f"State is: {state}\n\n"
                f"The previous action is evaluated to be successful.\n\n"
                f"Saved information memory: {self.infor_memory}\n\n"
            )

            state_content = [
                {"type": "text", "content": prompt_content_text},
                {"type": "image_url", "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)}}
            ]

            # --- DUAL AGENT EXECUTION ---

            # A. Prepare context for Planner
            self.agent_message_manager._remove_last_AIntool_message()
            self.agent_message_manager._remove_last_state_message()
            self.agent_message_manager.add_state_message(state_content, self._last_result, step_info)
            
            current_messages = self.agent_message_manager.get_messages()

            # B. Run Planner (The Brain)
            planner_output = await self.get_planner_instruction(current_messages)
            self._save_debug_log(f"Step {self.n_steps} - PLANNER THINKING", planner_output)

            # C. Inject Planner's High-Level Goal into Actor's Context
            # Note: We do NOT show the Global Plan to the Actor to keep it focused.
            planner_directive = (
                f"\n\n🚨 **PLANNER INSTRUCTION (EXECUTE THIS):**\n"
                f"Analysis: {planner_output.analysis}\n"
                f"GOAL: {planner_output.next_high_level_goal}\n"
            )
            
            final_actor_prompt = prompt_content_text + planner_directive
            state_content_actor = [
                {"type": "text", "content": final_actor_prompt},
                {"type": "image_url", "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)}}
            ]
            
            # Update Message Manager with the new Actor-specific prompt
            self.agent_message_manager._remove_last_state_message() 
            self.agent_message_manager.add_state_message(state_content_actor, self._last_result, step_info)

            # D. Run Actor (The Hand)
            input_messages = self.agent_message_manager.get_messages()
            model_output, raw = await self.get_next_action(input_messages)
            self._save_debug_log(f"Step {self.n_steps} - ACTOR ACTION", model_output)
            
            # --- END DUAL AGENT EXECUTION ---

            # 3. Persist Long-Term Summary (to .txt)
            if self.enable_step_memory and self.step_memory_file:
                step_summary = getattr(model_output.current_state, 'step_summary', None)
                # Fallback parsing for raw outputs
                if not step_summary and 'step_summary' in raw:
                     try:
                        raw_dict = json.loads(raw) if isinstance(raw, str) else raw
                        step_summary = raw_dict['current_state'].get('step_summary')
                     except: pass
                
                if step_summary and str(step_summary).strip().lower() not in ["none", "null", "", "n/a"]:
                    summary_line = f"Step {self.n_steps}: {str(step_summary).strip()}\n"
                    if self.n_steps == 1:
                        self.step_memory_file.write_text("", encoding="utf-8")
                    with self.step_memory_file.open("a", encoding="utf-8") as f:
                        f.write(summary_line)

            # 4. Process Output & Callbacks
            self.last_goal = model_output.current_state.next_goal
            information_stored = model_output.current_state.information_stored

            if self.register_new_step_callback:
                self.register_new_step_callback(state, model_output, self.n_steps)
            self._save_agent_conversation(input_messages, model_output, step=self.n_steps)

            self.agent_message_manager._remove_last_state_message()
            self.agent_message_manager.add_model_output(model_output)
            
            self.last_step_action = [action.model_dump(exclude_unset=True) for action in model_output.action] if model_output else []
            
            # 5. Execute Actions via Controller
            result = await self.controller.multi_act(
                model_output.action,
                self.mac_tree_builder,
                action_valid=True 
            )
            self._last_result = result
            
            # 6. Update Memories
            # Update Information Accumulator
            if information_stored != 'None':
                self.infor_memory.append({f'Step {self.n_steps}, the information stored is: {information_stored}'})
            
            # Rebuild tree if necessary
            if self.use_ui:
                for action in model_output.action:
                    if action.open_app:
                        await self.mac_tree_builder.build_tree(self.get_last_pid())
            
            # Determine wait status
            self.wait_this_step = False
            if not self.last_step_action or 'wait' in str(self.last_step_action[0]):
                self.wait_this_step = True

            # Update History List (Append the Planner's Global Plan here for future reference)
            if not self.wait_this_step and model_output is not None:
                current_record = {
                    'step': self.n_steps,
                    'goal': self.last_goal,
                    'actions': self.last_step_action, 
                    'summary': getattr(model_output.current_state, 'step_summary', ''),
                    'status': 'success',
                    'plan': getattr(planner_output, 'global_plan', 'N/A')
                }
                self.full_step_history.append(current_record)

        except Exception as e:
            result = await self._handle_step_error(e)
            self._last_result = result

        finally:
            if result:
                self._make_history_item(model_output, state, result)
            if not self.wait_this_step:
                self.n_steps += 1

    # --- Utility Methods ---

    def _log_response(self, response: AgentOutput) -> None:
        """Updated logging to reflect new memory structure"""
        state = response.current_state
        emoji = '✅' if 'Success' in state.evaluation_previous_goal else '❌' if 'Failed' in state.evaluation_previous_goal else '🤷'
        
        logger.info(f'{emoji} Eval: {state.evaluation_previous_goal}')
        
        if self.full_step_history:
            logger.info(f'🧠 Last Goal: {self.full_step_history[-1]["goal"]}')
        else:
            logger.info(f'🧠 Memory: (Initializing...)')
            
        logger.info(f'🎯 Next goal: {state.next_goal}')
        for i, action in enumerate(response.action):
            logger.info(f'🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}')

    async def _handle_step_error(self, error: Exception) -> list[ActionResult]:
        include_trace = logger.isEnabledFor(logging.DEBUG)
        error_msg = AgentError.format_error(error, include_trace=include_trace)
        prefix = f'❌ Result failed {self.consecutive_failures + 1}/{self.max_failures} times:\n '

        if isinstance(error, (ValidationError, ValueError)):
            logger.error(f'{prefix}{error_msg}')
            if 'Max token limit reached' in error_msg:
                self.agent_message_manager.max_input_tokens -= 500
                logger.info(f'Reducing agent max input tokens: {self.agent_message_manager.max_input_tokens}')
                self.agent_message_manager.cut_messages()
            elif 'Could not parse response' in error_msg:
                error_msg += '\n\nReturn a valid JSON object with the required fields.'
            self.consecutive_failures += 1
        elif isinstance(error, RateLimitError):
            logger.warning(f'{prefix}{error_msg}')
            await asyncio.sleep(self.retry_delay)
            self.consecutive_failures += 1
        else:
            logger.error(f'{prefix}{error_msg}')
            self.consecutive_failures += 1

        return [ActionResult(error=error_msg, include_in_memory=True)]

    def _make_history_item(self, model_output, state, result) -> None:
        self.history.history.append(AgentHistory(model_output=model_output, result=result, state=state))

    @time_execution_async('--get_next_action')
    async def get_next_action(self, input_messages: list[BaseMessage]) -> AgentOutput:      
        final_messages = self._filter_messages_with_images(input_messages)
        response: dict[str, Any] = await self.llm.ainvoke(final_messages)
        logger.debug(f'LLM response: {response}')
        record = str(response.content)
        output_dict = json.loads(record)

        brain = AgentBrain(
            evaluation_previous_goal=output_dict['current_state']['evaluation_previous_goal'],
            information_stored=output_dict['current_state']['information_stored'],
            next_goal=output_dict['current_state']['next_goal'],
            step_summary=output_dict['current_state'].get('step_summary', None)
        )
        parsed: AgentOutput | None = AgentOutput(current_state=brain, action=output_dict['action'])
        self._log_response(parsed)
        return parsed, record

    def _filter_messages_with_images(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        Filters the message history to retain only the most recent N images.
        Older messages are stripped of their image data (retaining text) to save tokens.
        """
        if self.max_history_images < 0:
            return messages 

        filtered_messages = []
        image_count = 0
        
        # Traverse in reverse (newest to oldest)
        for msg in reversed(messages):
            if isinstance(msg, BaseMessage) and isinstance(msg.content, list):
                has_image = any(item.get('type') == 'image_url' for item in msg.content)
                
                if has_image:
                    image_count += 1
                    if image_count > self.max_history_images:
                        # Strip image, keep text
                        new_content = [item for item in msg.content if item.get('type') == 'text']
                        msg = type(msg)(content=new_content)
            
            filtered_messages.append(msg)
        
        # Reverse back to original order
        return list(reversed(filtered_messages))
    
    def _save_agent_conversation(self, input_messages, response, step) -> None:
        if not self.save_conversation_path: return
        file_name = f"{self.save_conversation_path}_agent_{step}.txt"
    
        directory = os.path.dirname(file_name)
        if directory:  
            os.makedirs(directory, exist_ok=True)
    
        with open(file_name, "w", encoding=self.save_conversation_path_encoding) as f:
            self._write_messages_to_file(f, input_messages)
            if response: self._write_response_to_file(f, response)
        logger.info(f"Agent conversation saved to: {file_name}")

    def _write_messages_to_file(self, f, messages) -> None:
        for message in messages:
            f.write(f"\n{message.__class__.__name__}\n{'-'*40}\n")
            if isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            f.write(f"[Text]\n{item.get('content', '').strip()}\n\n")
                        elif item.get('type') == 'image_url':
                            f.write(f"[Image]\n{item['image_url']['url'][:50]}...\n\n")
            else:
                f.write(f"{str(message.content)}\n\n")
            f.write('\n' + '='*60 + '\n')

    def _write_response_to_file(self, f, response) -> None:
        f.write('RESPONSE\n')
        f.write(str(response) + '\n')
        f.write('\n' + '='*60 + '\n')

    def _log_agent_run(self) -> None:
        logger.info(f'🚀 Starting task: {self.task}')

    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        try:
            self._log_agent_run()
            for step in range(max_steps):
                if self.resume:
                    self.load_memory()
                    self.resume = False
                if self._too_many_failures(): break
                if not await self._handle_control_flags(): break

                await self.step()

                if self.history.is_done():
                    logger.info('✅ Task completed successfully')
                    if self.register_done_callback:
                        self.register_done_callback(self.history)
                    break
                await asyncio.sleep(2)
            else:
                logger.info('❌ Failed to complete task in maximum steps')
            return self.history
        except Exception:
            logger.exception('Error running agent')
            raise

    def _too_many_failures(self) -> bool:
        if self.consecutive_failures >= self.max_failures:
            logger.error(f'❌ Stopping due to {self.max_failures} consecutive failures')
            return True
        return False

    async def _handle_control_flags(self) -> bool:
        if self._stopped:
            logger.info('Agent stopped')
            return False
        while self._paused:
            await asyncio.sleep(0.2)
            if self._stopped: return False
        return True

    def save_history(self, file_path: Optional[str | Path] = None) -> None:
        if not file_path: file_path = 'AgentHistory.json'
        self.history.save_to_file(file_path)

    def initiate_messages(self):
        self.agent_message_manager = MessageManager(
            llm=self.llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=self.system_prompt_class,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
        )
        self.system_prompt_planner_class = SystemPrompt_Planner(task=self.task)

    def _set_model_names(self) -> None:
        self.chat_model_library = self.llm.__class__.__name__
        self.model_name = getattr(self.llm, 'model_name', getattr(self.llm, 'model', 'Unknown'))

    def set_tool_calling_method(self, tool_calling_method: Optional[str]) -> Optional[str]:
        if tool_calling_method == 'auto':
            if self.chat_model_library == 'ChatGoogleGenerativeAI': return None
            if self.chat_model_library in ['ChatOpenAI', 'AzureChatOpenAI']: return 'function_calling'
            return None
        return tool_calling_method

    def _setup_action_models(self) -> None:
        self.ActionModel = self.controller.registry.create_action_model()
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)

    def get_last_pid(self) -> Optional[int]:
        latest_pid = self.last_pid
        if self._last_result:
            for r in self._last_result:
                if r.current_app_pid: latest_pid = r.current_app_pid
        return latest_pid