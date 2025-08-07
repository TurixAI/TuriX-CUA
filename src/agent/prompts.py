from datetime import datetime
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.views import ActionResult, AgentStepInfo
import logging
logger = logging.getLogger(__name__)
import pyautogui

class SystemPrompt:
    def __init__(
        self,
        action_descriptions: str,
        max_actions_per_step: int = 10,
    ):
        self.action_descriptions = action_descriptions
        self.current_time = datetime.now()
        self.max_actions_per_step = max_actions_per_step


    def get_system_message(self) -> SystemMessage:
        # Current date: {self.current_date.strftime('%Y-%m-%d')}
        screen_size = pyautogui.size()
        return SystemMessage(
            content=f"""
            SYSTEM PROMPT FOR AGENT
=======================

=== GLOBAL INSTRUCTIONS ===
- **Environment:** Windows 11.  Current time is {self.current_time}.
- **Always** adhere strictly to the JSON output format and output no harmful language:
{{
    "action": [List of all actions to be executed this step],
    "current_state": {{
        "evaluation_previous_goal": "Success/Failed", (From evaluator)
        "next_goal": "Goal of this step based on "actions", ONLY DESCRIBE THE EXPECTED ACTIONS RESULT OF THIS STEP",
        "information_stored": "Accumulated important information, add continuously, else 'None'",
    }},
    
}}

*When outputting multiple actions as a list, each action **must** be an object.*
**DO NOT OUTPUT ACTIONS IF IT IS NONE or Null**
=== ROLE-SPECIFIC DIRECTIVES ===
- **Role:** *You are a Windows 11 Computer-use Agent.* Execute the Planner’s plan, evaluated by the Evaluator.  
- You will receive an overall plan for completing a task and a JSON input from the previous step, which contains:
- Memory  
- The screenshot  
- The current state of the computer (i.e., the current computer UI tree)  
- A message containing the Evaluator’s suggestion for the new next step if previous step failed  
- Decide on the next step to take based on the input you receive and output the actions to take.

**Responsibilities**
1. Follow the Planner’s *Step-by-step plan* precisely using available actions:  
 `{self.action_descriptions}`, For actions that take no parameters (done, wait, record_info) set the value to an empty object *{{}}*
2. If an action fails twice, switch methods.  
3. **All coordinates are normalized to 0–1. You MUST output normalized positions.**

**Open App**
- **Must** use the `open_app` action **first**.  
- Even if the app is already on screen, you still need to use `open_app` to get the UI tree.  

=== APP-SPECIFIC NOTES ===
- **Finder:** Prefer keyboard shortcuts to navigate between folders.


            """
            )

class AgentMessagePrompt:
    def __init__(
        self,
        state_content: list,  # Changed from dict to list
        result: Optional[List[ActionResult]] = None,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        step_info: Optional[AgentStepInfo] = None,
    ):
        """
        Initialize AgentMessagePrompt with state and optional parameters.
        Changed state_content type to list for proper unpacking
        """
        # Unpack the text item and all image items
        text_item = next(item for item in state_content if item['type'] == 'text')
        image_items = [item['image_url']['url'] for item in state_content if item['type'] == 'image_url']
        
        self.state = text_item['content']
        self.image_urls = image_items  # Now storing all image URLs in a list
        self.result = result
        self.max_error_length = max_error_length
        self.include_attributes = include_attributes
        self.step_info = step_info

    def get_user_message(self) -> HumanMessage:
        """Keep text and images separated but in a single message"""
        step_info_str = f"Step {self.step_info.step_number + 1}/{self.step_info.max_steps}\n" if self.step_info else ""
        
        # Create structured content list
        content = [
            {
                "type": "text",
                "text": f"{step_info_str}CURRENT APPLICATION STATE:\n{self.state}"
            }
        ]
        
        # Add all images to the content list
        for image_url in self.image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # Add action results as text
        if self.result:
            results_text = "\n".join(
                f"ACTION RESULT {i+1}: {r.extracted_content}" if r.extracted_content 
                else f"ACTION ERROR {i+1}: ...{r.error[-self.max_error_length:]}" 
                for i, r in enumerate(self.result)
            )
            content.append({"type": "text", "text": results_text})

        return HumanMessage(content=content)


