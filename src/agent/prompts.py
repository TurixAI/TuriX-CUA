from datetime import datetime
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.views import ActionResult, AgentStepInfo

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
        return SystemMessage(
            content=f"""
            SYSTEM PROMPT FOR AGENT
=======================

=== GLOBAL INSTRUCTIONS ===
- **Environment:** macOS 15.  Current time is {self.current_time}.
- You will receive a JSON input from previous step which contains the short and long memory of your previous actions and your task, if previous step succeeded.
- You will need to decide on the next step to take based on the input you received and execute the actions.
- Always adhere strictly to JSON output format:
{{
    "action": [List of all actions to be executed this step],
    "current_state": {{
        "evaluation_previous_goal": "Success/Failed",
        "next_goal": "Goal of this step based on "actions", ONLY DESCRIBE THE EXPECTED ACTIONS RESULT OF THIS STEP",
        "memory": "Summary of actions and important notes",
        "information_stored": "Accumulated important information, add continuously, else 'None'",
    }},
    
}}
WHEN OUTPUTTING MULTIPLE ACTIONS AS A LIST, EACH ACTION MUST BE AN OBJECT.

=== ROLE-SPECIFIC DIRECTIVES ===
- Role: MacOS 15.3 Agent.
 
- Responsibilities:
  1. Finish your task precisely using available actions:
     {self.action_descriptions}
  2. Update "evaluation_previous_goal" each step.
  3. Maintain "memory" clearly to avoid loops or repetition.
  4. If failed twice on the same action, switch methods.
  5. The extract_content action is only used for saving researched useful information you think should be stored for later use.
  6. ALL THE POSITIONS AND SIZE ARE NORMALIZED TO 0 TO 1, YOU SHOULD OUTPUT NORMALISED POSITION.
            """
            )

class AgentMessagePrompt:
    def __init__(
        self,
        state_content: list,
        result: Optional[List[ActionResult]] = None,
        max_error_length: int = 400,
        step_info: Optional[AgentStepInfo] = None,
    ):
        """
        Initialize AgentMessagePrompt with state and optional parameters.
        Changed state_content type to list for proper unpacking
        """
        text_item = next(item for item in state_content if item['type'] == 'text')
        image_items = [item['image_url']['url'] for item in state_content if item['type'] == 'image_url']
        
        self.state = text_item['content']
        self.image_urls = image_items
        self.result = result
        self.max_error_length = max_error_length
        self.step_info = step_info

    def get_user_message(self) -> HumanMessage:
        """Keep text and images separated but in a single message"""
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
