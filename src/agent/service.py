from __future__ import annotations
import asyncio
import base64
import io
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from pynput import keyboard
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Type
from collections import OrderedDict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI          # OpenAI endpoints
from langchain_anthropic import ChatAnthropic                     # Claude
from langchain_google_genai import ChatGoogleGenerativeAI  
from langchain_core.messages import (
    BaseMessage,
)

from datetime import datetime
from openai import RateLimitError
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ValidationError
from src.agent.message_manager.service import MessageManager
from src.agent.prompts import (
    SystemPrompt_turix,
    SystemPrompt,
)
from src.agent.views import (
    ActionResult,
    AgentError,
    AgentHistory,
    AgentHistoryList,
    AgentOutput,
    AgentStepInfo,
    AgentBrain
)
from src.controller.registry.views import ActionModel
from src.controller.service import Controller
from src.mac.tree import MacUITreeBuilder
from src.utils import time_execution_async
from src.agent.output_schemas import OutputSchemas
from src.agent.structured_llm import *

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def screenshot_to_dataurl(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    base64_encoded = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{base64_encoded}'

def _get_installed_app_names() -> list[str]:
    """
    Returns a list of application names (minus ".app") 
    from both /Applications and /System/Applications
    """
    apps = set()
    for apps_path in ["/Applications", "/System/Applications"]:
        if os.path.exists(apps_path):
            for item in os.listdir(apps_path):
                if item.endswith(".app"):
                    # e.g. "Safari.app" -> "Safari"
                    apps.add(item[:-4])
    return list(apps)


def to_structured(llm: BaseChatModel, Schema, Structured_Output) -> BaseChatModel:
    """
    Wrap *any* LangChain chat model with the right structured-output mechanism:

    • ChatOpenAI / AzureChatOpenAI  → bind(response_format=…)      (OpenAI style)
    • ChatAnthropic / ChatGoogleGenerativeAI → with_structured_output(…) (Claude/Gemini style)
    • anything else → returned unchanged
    """
    OPENAI_CLASSES: tuple[Type[BaseChatModel], ...] = (ChatOpenAI, AzureChatOpenAI)
    ANTHROPIC_OR_GEMINI: tuple[Type[BaseChatModel], ...] = (
        ChatAnthropic,
        ChatGoogleGenerativeAI,
    )

    if isinstance(llm, OPENAI_CLASSES):
        # OpenAI only: use the response_format param with your flattened schema
        return llm.bind(response_format=Schema)

    if isinstance(llm, ANTHROPIC_OR_GEMINI):
        # Claude & Gemini accept any schema textually → keep the nice Pydantic model
        return llm.with_structured_output(Structured_Output)

    # Fallback: no structured output
    return llm

class Agent:
    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        short_memory_len : int,
        controller: Controller = Controller(),
        use_ui = False,
        use_turix: bool = True,
        save_conversation_path: Optional[str] = None,
        save_conversation_path_encoding: Optional[str] = 'utf-8',
        max_failures: int = 5,
        retry_delay: int = 10,
        system_prompt_class: Type[SystemPrompt] = SystemPrompt,
        max_input_tokens: int = 32000,
        resume = False,
        include_attributes: list[str] = [
            'title',
            'type',
            'name',
            'role',
            'tabindex',
            'aria-label',
            'placeholder',
            'value',
            'alt',
            'aria-expanded',
        ],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,

        register_new_step_callback: Callable[['str', 'AgentOutput', int], None] | None = None,
        register_done_callback: Callable[['AgentHistoryList'], None] | None = None,
        tool_calling_method: Optional[str] = 'auto',
        agent_id: Optional[str] = None,
        running_mcp: bool = False,
    ):
        self.current_time = datetime.now()
        self.agent_id = agent_id or str(uuid.uuid4())
        self.task = task
        self.resume = resume
        self.llm = to_structured(llm, OutputSchemas.AGENT_RESPONSE_FORMAT, AgentStepOutput)
        self.use_turix = use_turix

        self.save_conversation_path = save_conversation_path
        self.save_conversation_path_encoding = save_conversation_path_encoding

        self.include_attributes = include_attributes
        self.max_error_length = max_error_length
        self.screenshot_annotated = None
        self.short_memory_len = short_memory_len
        self.max_input_tokens = max_input_tokens
        self.save_temp_file_path = os.path.join(os.path.dirname(__file__), 'temp_files')
        self.use_ui = use_ui

        self.mac_tree_builder = MacUITreeBuilder()
        self.controller = controller
        self.max_actions_per_step = max_actions_per_step
        self.last_step_action = None
        self.goal_action_memory = OrderedDict()
        self.running_mcp = running_mcp

        self.last_goal = None
        if not self.use_turix:
            self.system_prompt_class = system_prompt_class
        else:
            self.system_prompt_class = SystemPrompt_turix
        self.state_memory = OrderedDict()
        self.status = "success"
        # Setup dynamic Action Model
        self._setup_action_models()

        self._set_model_names()

        self.tool_calling_method = self.set_tool_calling_method(tool_calling_method)
        self.initiate_messages()
        self._last_result = None

        self.register_new_step_callback = register_new_step_callback
        self.register_done_callback = register_done_callback

        # Agent run variables
        self.history: AgentHistoryList = AgentHistoryList(history=[])
        self.n_steps = 1
        self.consecutive_failures = 0
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self._paused = False
        self._stopped = False
        self.short_memory = ''
        self.infor_memory = []
        self.last_pid = None
        self.ask_for_help = False
        if save_conversation_path:
            logger.info(f'Saving conversation to {save_conversation_path}')

        if self.resume and not agent_id:
            raise ValueError("Agent ID is required for resuming a task.")
        self.save_temp_file_path = os.path.join(self.save_temp_file_path, f"{self.agent_id}")
        

    def _set_model_names(self) -> None:
        self.chat_model_library = self.llm.__class__.__name__
        if hasattr(self.llm, 'model_name'):
            self.model_name = self.llm.model_name  # type: ignore
        elif hasattr(self.llm, 'model'):
            self.model_name = self.llm.model  # type: ignore
        else:
            self.model_name = 'Unknown'

    def set_tool_calling_method(self, tool_calling_method: Optional[str]) -> Optional[str]:
        if tool_calling_method == 'auto':
            if self.chat_model_library == 'ChatGoogleGenerativeAI':
                return None
            elif self.chat_model_library == 'ChatOpenAI':
                return 'function_calling'
            elif self.chat_model_library == 'AzureChatOpenAI':
                return 'function_calling'
            else:
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

    def save_memory(self) -> None:
        """
        Save the current memory to a file.
        """
        if not self.save_temp_file_path:
            return
        data = {
            "pid": self.get_last_pid(),
            "task": self.task,
            "short_memory": self.short_memory,
            "infor_memory": self.infor_memory,
            "state_memory": self.state_memory,
            "step": self.n_steps
        }
        file_name = os.path.join(self.save_temp_file_path, f"memory.jsonl")
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None
        with open(file_name, "w", encoding=self.save_conversation_path_encoding) as f:
            if os.path.getsize(file_name) > 0:
                f.truncate(0)
            f.write(json.dumps(data, ensure_ascii=False, default=lambda o: list(o) if isinstance(o, set) else o) + "\n")

    def load_memory(self) -> None:
        """
        Load the current memory from a file.
        """
        if not self.save_temp_file_path:
            return
        file_name = os.path.join(self.save_temp_file_path, f".jsonl")
        if os.path.exists(file_name):
            with open(file_name, "r", encoding=self.save_conversation_path_encoding) as f:
                lines = f.readlines()
            if len(lines) >= 1:
                data = json.loads(lines[-1])
                self.last_pid = data.get("pid", None)
                self.short_memory = data.get("short_memory", [])
                self.infor_memory = data.get("infor_memory", [])
                self.state_memory = data.get("state_memory", None)
                self.n_steps = data.get("step", 1)
                logger.info(f"Loaded memory from {file_name}")

    @time_execution_async("--step")
    async def step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        logger.info(f"\n📍 Step {self.n_steps}")
        state = "No UI state available"  # Default value
        model_output = None
        result: list[ActionResult] = []
        
        try:
            #---------------------------
            # 1) Build the UI tree and capture a screenshot
            #---------------------------
            
            logger.debug(f'Last PID: {self.last_pid}')
            if self.use_ui:
                self.last_pid = self.get_last_pid()
                root = await self.mac_tree_builder.build_tree(self.last_pid)
            # if root and self.use_ui:
                state = root._get_visible_clickable_elements_string() if root else "No UI tree found."
            else:
                state = ''
            if self.n_steps == 1:
                apps = _get_installed_app_names()
                app_list = ', '.join(apps)
                state = f'The available apps in this macbook is: {app_list}'
            self.save_memory()
            
            # ---------------------------
            # 2) Define the input message for the agent
            # ---------------------------
            if self.n_steps >= 2:
                self.previous_screenshot = self.screenshot_annotated
                screenshot = self.mac_tree_builder.capture_screenshot()
                if self.use_ui:
                    annotated_screenshot = self.mac_tree_builder.annotate_screenshot(root)
                    screenshot_filename = f'images/screenshot_to_use_{self.n_steps}.png'
                    annotated_screenshot.save(screenshot_filename) 
                # self.screenshot_annotated = annotated_screenshot or screenshot
                self.screenshot_annotated = screenshot # Use annotated screenshot if you like
                # delete the local save later
                if not self.running_mcp:
                    screenshot.save(f'images/screenshot_{self.n_steps}.png')
                if self.use_ui:
                    state_content = [
                        {
                            "type": "text",
                            "content": f"State is: {state}\n\n The previous action is evaluated to be successful.\n\n Saved information memory: {self.infor_memory}\n\n"
                            f"{self.short_memory}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)},
                        }
                    ]
                else:
                    state_content = [
                        {
                            "type": "text",
                            "content": f"The previous action is evaluated to be successful.\n\n Saved information memory: {self.infor_memory}\n\n"
                            f"{self.short_memory}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)},
                        }
                    ]
            else:
                screenshot = self.mac_tree_builder.capture_screenshot()
                self.screenshot_annotated = screenshot
                if not self.running_mcp:
                    screenshot.save(f'images/screenshot_{self.n_steps}.png')
                state_content = [
                    {
                        "type": "text",
                        "content": f"State is: {state}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": screenshot_to_dataurl(screenshot)},
                    }]
            self.agent_message_manager._remove_last_AIntool_message()
            self.agent_message_manager._remove_last_state_message()
            self.agent_message_manager.add_state_message(state_content, self._last_result, step_info)


            input_messages = self.agent_message_manager.get_messages()
            model_output, raw = await self.get_next_action(input_messages)
            
            self.last_goal = model_output.current_state.next_goal
            information_stored = model_output.current_state.information_stored
            if self.register_new_step_callback:
                self.register_new_step_callback(state, model_output, self.n_steps)
            self._save_agent_conversation(input_messages, model_output,step=self.n_steps)

            self.agent_message_manager._remove_last_state_message()
            self.agent_message_manager.add_model_output(model_output)

            
            self.last_step_action = [action.model_dump(exclude_unset=True) for action in model_output.action] if model_output else []
            # join the self.state_memory and the self.last_goal
            self.state_memory[f'Step {self.n_steps}'] = f'Goal: {self.last_goal}'
            self.state_memory[f'Step {self.n_steps} is'] = '(success)'

            result = await self.controller.multi_act(
                model_output.action,
                self.mac_tree_builder,
                action_valid=True # Set to True temporarily, halusination checker
            )
            self._last_result = result
            if information_stored != 'None':
                self.infor_memory.append({f'Step {self.n_steps}, the information stored is: {information_stored}'})
            if self.use_ui:
                for i in range(len(model_output.action)):
                    if 'open_app' in str(model_output.action[i]):
                        logger.debug(f'Found open_app action, building the tree again')
                        await self.mac_tree_builder.build_tree(self.get_last_pid())

            if self.last_step_action:
                self.goal_action_memory[f'Step {self.n_steps}'] = f'Goal: {self.last_goal}, Actions: {self.last_step_action}'
                self.goal_action_memory[f'Step {self.n_steps} is'] = f'(success)'

                if len(self.goal_action_memory) > self.short_memory_len:
                    first_key = next(iter(self.goal_action_memory))
                    del self.goal_action_memory[first_key]
                self.short_memory = f'The important memory: {self.state_memory}. {self.goal_action_memory}'

        except Exception as e:
            result = await self._handle_step_error(e)
            self._last_result = result

        finally:
            if result:
                self._make_history_item(model_output, state, result)
        self.n_steps += 1

    async def _handle_step_error(self, error: Exception) -> list[ActionResult]:
        include_trace = logger.isEnabledFor(logging.DEBUG)
        error_msg = AgentError.format_error(error, include_trace=include_trace)
        prefix = f'❌ Result failed {self.consecutive_failures + 1}/{self.max_failures} times:\n '

        if isinstance(error, (ValidationError, ValueError)):
            logger.error(f'{prefix}{error_msg}')
            if 'Max token limit reached' in error_msg:
                # Possibly reduce tokens from history
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

    @time_execution_async('--get_next_action')
    async def get_next_action(self, input_messages: list[BaseMessage]) -> AgentOutput:
        """
        Build a 'structured_llm' approach on top of self.llm. 
        Using the dynamic self.AgentOutput
        """        
        response: dict[str, Any] = await self.llm.ainvoke(input_messages)
        logger.debug(f'LLM response: {response}')
        record = str(response.content)

        output_dict = json.loads(record)

        brain = AgentBrain(evaluation_previous_goal=output_dict['current_state']['evaluation_previous_goal'],
                            information_stored=output_dict['current_state']['information_stored'],
                            next_goal=output_dict['current_state']['next_goal'],
                            )
        parsed: AgentOutput | None = AgentOutput(current_state=brain, action=output_dict['action'])

        self._log_response(parsed)
        return parsed, record
    

    def _log_response(self, response: AgentOutput) -> None:
        if 'Success' in response.current_state.evaluation_previous_goal:
            emoji = '✅'
        elif 'Failed' in response.current_state.evaluation_previous_goal:
            emoji = '❌'
        else:
            emoji = '🤷'
        logger.info(f'{emoji} Eval: {response.current_state.evaluation_previous_goal}')
        logger.info(f'🧠 Memory: {self.state_memory}')
        logger.info(f'🎯 Next goal: {response.current_state.next_goal}')
        for i, action in enumerate(response.action):
            logger.info(f'🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}')

    def _save_agent_conversation(
        self,
        input_messages: list[BaseMessage],
        response: Any,
        step: int
    ) -> None:
        """
        Write all the agent conversation (input messages + final AgentOutput)
        into a file: e.g. "agent_conversation_{step}.txt"
        """
        # If you do NOT want to save or no path provided, skip
        if not self.save_conversation_path:
            return
        file_name = f"{self.save_conversation_path}_agent_{step}.txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None

        with open(file_name, "w", encoding=self.save_conversation_path_encoding) as f:
            # 1) Write input messages
            self._write_messages_to_file(f, input_messages)
            # 2) Write the final agent "response" (AgentOutput)
            if response is not None:
                self._write_response_to_file(f, response)

        logger.info(f"Agent conversation saved to: {file_name}")

    def _write_messages_to_file(self, f: Any, messages: list[BaseMessage]) -> None:
        """
        For each message, write it out in a human-readable format.
        Or adapt your existing logic from _write_messages_to_file.
        """
        for message in messages:
            f.write(f"\n{message.__class__.__name__}\n{'-'*40}\n")
            if isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            txt = item.get('content') or item.get('text', '')
                            f.write(f"[Text Content]\n{txt.strip()}\n\n")
                        elif item.get('type') == 'image_url':
                            image_url = item['image_url']['url']
                            f.write(f"[Image URL]\n{image_url[:100]}...\n\n")
            else:
                # If it's a string or something else:
                f.write(f"{str(message.content)}\n\n")
            f.write('\n' + '='*60 + '\n')

    def _write_response_to_file(self, f: Any, response: Any) -> None:
        """
        If the AgentOutput is JSON-like, you can do:
        """
        f.write('RESPONSE\n')
        # If it's an AgentOutput, you might do:
        #   f.write(json.dumps(json.loads(response.model_dump_json(exclude_unset=True)), indent=2))
        # Otherwise just string-ify it:
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
                if self._too_many_failures():
                    break
                if not await self._handle_control_flags():
                    break

                await self.step()

                if self.history.is_done():
                    logger.info('✅ Task completed successfully')
                    if self.register_done_callback:
                        self.register_done_callback(self.history)
                    break
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
            if self._stopped:
                return False

        return True

    def save_history(self, file_path: Optional[str | Path] = None) -> None:
        if not file_path:
            file_path = 'AgentHistory.json'
        self.history.save_to_file(file_path)

    def initiate_messages(self):
        self.agent_message_manager = MessageManager(
            llm=self.llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=self.system_prompt_class,  # Typically your SystemPrompt
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
        )

    async def run_MCP(self, max_steps: int = 100) -> str:
        """ Run the MCP agent with a maximum number of steps."""
        # Set up a hotkey listener to stop the agent
        # if you want to stop the agent manually, press cmd+shift+2
        terminate_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def _on_hotkey():
            loop.call_soon_threadsafe(terminate_event.set)

        hotkey_listener = keyboard.GlobalHotKeys({
            '<cmd>+<shift>+2': _on_hotkey
        })
        hotkey_listener.start()
        try:
            for step in range(1,max_steps+1):
                await asyncio.sleep(0)
                if self.resume:
                    self.load_memory()
                    self.resume = False
                if self._too_many_failures():
                    return "Too many consecutive failures, stopping the agent."

                if not await self._handle_control_flags():
                    break

                if terminate_event.is_set():
                    return "User terminate the agent"

                await self.step()

                if self.histories.is_done():
                    return "Task completed successfully"
                
            return "Failed to complete task"
        except Exception:
            raise
        finally:
            hotkey_listener.stop()