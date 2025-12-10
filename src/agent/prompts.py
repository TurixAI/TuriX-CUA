from datetime import datetime
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.views import ActionResult, AgentStepInfo
import logging
import os

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def _get_installed_app_names() -> list[str]:
    """Returns a list of application names (minus ".app") to provide context to the agent."""
    apps = set()
    paths = ["/Applications", "/System/Applications"]
    for apps_path in paths:
        if os.path.exists(apps_path):
            try:
                for item in os.listdir(apps_path):
                    if item.endswith(".app"):
                        apps.add(item[:-4])
            except Exception:
                pass
    return list(apps)

# Pre-calculate app list to save IO operations
APP_LIST_STR = ', '.join(_get_installed_app_names())

# --- 1. Planner Prompt (The Brain) ---
class SystemPrompt_Planner:
    """
    Prompt for the High-Level Planner Agent.
    Focuses on: Chain of Thought, Global Planning, and Instruction generation.
    Does NOT handle low-level action execution.
    """
    def __init__(self, task: str):
        self.task = task
        self.current_time = datetime.now()

    def get_system_message(self) -> SystemMessage:
        return SystemMessage(
            content=f"""
            SYSTEM PROMPT FOR PLANNER AGENT
=======================
You are the **BRAIN** of a macOS Computer-use Agent. Your job is to PLAN, not to execute.
Current time: {self.current_time}
User's Overall Task: "{self.task}"

=== RESPONSIBILITIES ===
1. Analyze the current screenshot and UI state.
2. Review the history (Long/Medium/Short term memory).
3. **Update the Global Plan**: List the steps required to complete the task.
   - Format: "1. [Step Name] (Done/Current/Pending)"
4. Determine the immediate next logical step (High-Level Goal).

=== OUTPUT FORMAT ===
Strictly adhere to the JSON format:
{{
    "analysis": "Reasoning...",
    "global_plan": "1. Open Safari (Done)\\n2. Search Google (Current)\\n3. Click Result (Pending)",
    "next_high_level_goal": "Specific instruction for Actor."
}}
            """
        )

# --- 2. Actor Prompt (The Hand) ---
class SystemPrompt_Actor:
    """
    Prompt for the Low-Level Actor Agent.
    Focuses on: Converting high-level goals into concrete mouse/keyboard actions.
    Contains detailed OS-specific interaction rules.
    """
    def __init__(
        self,
        action_descriptions: str,
        max_actions_per_step: int = 10,
    ):
        self.action_descriptions = action_descriptions
        self.current_time = datetime.now()
        self.max_actions_per_step = max_actions_per_step

    def get_system_message(self) -> SystemMessage:
        return SystemMessage(
            content=f"""
            SYSTEM PROMPT FOR AGENT (ACTOR)
=======================
=== GLOBAL INSTRUCTIONS ===
- **Environment:** macOS. Current time: {self.current_time}. 
- **Available Apps:** {APP_LIST_STR}
- **Role:** You are a macOS Computer-use Agent (ACTOR). 
- **CRITICAL:** You will receive a **High-Level Goal** from a Planner Agent. Your ONLY job is to translate that goal into concrete actions (clicks, types, shortcuts).
- Do not deviate from the Planner's goal unless it is physically impossible.

=== OUTPUT FORMAT ===
Strictly adhere to the JSON output format:
{{
    "current_state": {{
        "evaluation_previous_goal": "Success/Failed",
        "next_goal": "Copy the Planner's goal here",
        "information_stored": "Accumulated important information (text/numbers) from screen, else 'None'",
        "step_summary": "A concise sentence summarizing what you actually did (e.g. 'Clicked the download button')."
    }},
    "action": [List of action objects]
}}

=== DETAILED ACTION GUIDELINES (MUST FOLLOW) ===
**General**
- **No Double-Click:** Do NOT use two single clicks at the same position.
- **Coordinates:** All coordinates are normalized to 0–1000. Output normalized positions.

**Open App**
- Use `open_app` first to get the UI tree, even if the app looks open.
- Use correct names: **Lark** (Feishu), **TencentMeeting** (Tencent Meeting).

**Browsing & Files**
- **New Tab:** Always use **Command + T** to open a new tab/window when opening a browser.
- **Address Bar:** Type URLs into the address bar, not the search bar.
- **Search:** Use **Command + F** if you cannot find text on a page.
- **Files:** To open, if click fails, try Right-click -> "Open" or select + **Command + O**.

**Input**
- Switch languages using **Ctrl + Space** if needed.
- Always type at the caret end unless deliberately inserting elsewhere.

=== AVAILABLE ACTIONS ===
{self.action_descriptions}

*Now await the Planner's instruction and the Screenshot.*
            """
        )

# --- 3. Message Helper ---
class AgentMessagePrompt:
    def __init__(
        self,
        state_content: list,
        result: Optional[List[ActionResult]] = None,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        step_info: Optional[AgentStepInfo] = None,
    ):
        text_item = next(item for item in state_content if item['type'] == 'text')
        image_items = [item['image_url']['url'] for item in state_content if item['type'] == 'image_url']
        
        self.state = text_item['content']
        self.image_urls = image_items
        self.result = result
        self.max_error_length = max_error_length
        self.include_attributes = include_attributes
        self.step_info = step_info

    def get_user_message(self) -> HumanMessage:
        step_info_str = f"Step {self.step_info.step_number + 1}/{self.step_info.max_steps}\n" if self.step_info else ""
        content = [
            {
                "type": "text",
                "text": f"{step_info_str}CURRENT APPLICATION STATE:\n{self.state}"
            }
        ]
        for image_url in self.image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        if self.result:
            results_text = "\n".join(
                f"ACTION RESULT {i+1}: {r.extracted_content}" if r.extracted_content 
                else f"ACTION ERROR {i+1}: ...{r.error[-self.max_error_length:]}" 
                for i, r in enumerate(self.result)
            )
            content.append({"type": "text", "text": results_text})

        return HumanMessage(content=content)

# Aliases for backward compatibility with existing imports
SystemPrompt = SystemPrompt_Actor
SystemPrompt_turix = SystemPrompt_Actor