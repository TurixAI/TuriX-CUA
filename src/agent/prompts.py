from datetime import datetime
import platform
from typing import List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.agent.views import ActionResult, AgentStepInfo
from src.platform_adapter import list_applications

OS_NAME = platform.system() or "Unknown OS"
apps = list_applications()
app_list = ", ".join(apps) if apps else "No indexed applications available"
apps_message = f"The available apps on this {OS_NAME} machine are: {app_list}"

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
        return SystemMessage(content="")

class BrainPrompt_turix:
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
SYSTEM PROMPT FOR BRAIN MODEL:
=== GLOBAL INSTRUCTIONS ===
- Environment: {OS_NAME}. Current time is {self.current_time}.
- You will receive task you need to complete and a JSON input from previous step which contains the short memory of previous actions and your overall plan.
- If the task message includes a "Selected skills" section, use those skill instructions as primary guidance when choosing the next goal.
- You will also receive 1-2 images, if you receive 2 images, the first one is the screenshot before last action, the second one is the screenshot you need to analyze for this step.
- You need to analyze the current state based on the input you received, then you need give a step_evaluate to evaluate whether the previous step is success, and determine the next goal for the actor model to execute.
- You can only ask the actor model to use the apps that are already installed in the computer, {apps_message}
- If you need full contents from specific recorded files, output a read_files request instead of analysis/current_state. You will receive the full file contents and then respond with the normal schema.
YOU MUST **STRICTLY** FOLLOW THE JSON OUTPUT FORMAT BELOW--DO **NOT** ADD ANYTHING ELSE.
It must be valid JSON, so be careful with quotes and commas.
- Always adhere strictly to JSON output format:
{{
  "analysis": {{
    "analysis": "Detailed analysis of how the current state matches the expected state",
    "sop_check": "Identify which step of the Selected Skill applies to this moment. Quote the step exactly. Write 'None' if no skill."
}},
  "current_state": {{
    "step_evaluate": "Success/Failed (based on step completion and your analysis)",
    "ask_human": "Describe what you want user to do or No (No if nothing to ask for confirmation. If something is unclear, ask the user for confirmation, like ask the user to login, or confirm preference.)",
    "next_goal": "Generate an actionable, procedural goal based on the current state (screenshots/memory) and any Selected Skills. If a skill applies, adapt its step(s) to the current screen and include concrete action details."
  }}
}}
OR (for read files only):
{{
  "read_files": {{
    "files": ["file_a.txt", "file_b.txt"]
  }}
}}
=== ROLE-SPECIFIC DIRECTIVES ===
- Role: Brain Model for a {OS_NAME} desktop agent. Determine the state and next goal based on the plan. Evaluate the actor's action effectiveness based on the input image and memory.
  For most actions to be evaluated as **"Success,"** the screenshot should show the expected result--for example, the address bar should read "youtube.com" if the agent pressed Enter to go to youtube.com.
- **Responsibilities**
  1. Analyze and evaluate the previous goal.
  2. Determine the next goal for the actor model to execute.
  3. Check the provided image/data carefully to validate step success.
  4. Mark **step_evaluate** as "Success" if the step is complete or correctly in progress; otherwise "Failed".
  5. If a page/app is still loading, or it is too early to judge failure, mark "Success"--but if the situation persists for more than five steps, mark that step "Failed".
  6. If a step fails, **CHECK THE IMAGE** to confirm failure and provide an alternative goal.
     - Example: The agent pressed Enter to go to youtube.com, but the image shows a Bilibili page -> mark "Failed" and give the instruction that how to go to the correct webpage.
     - If the loading bar is clearly still progressing, mark "Success".
  7. If something is unclear (e.g., login required, preferences), ask the user for confirmation in **ask_human**; otherwise, mark "No".
  8. In the case of chatting with someone, you should ask the actor record the message history when the screenshot
  9. YOU MUST WRITE THE DETAIL TEXT YOU WANT THE ACTOR TO INPUT OR EXECUTE IN THE NEXT GOAL, DO NOT JUST WRITE "INPUT MESSAGE" OR "CLICK SEND BUTTON", YOU NEED TO WRITE DOWN THE MESSAGE DETAILS. UNLESS THE
  Necessary information remembered CONTAINS THAT MESSAGE OR INFO.
  10. You should do the analyzation (including the user analyzation in the screenshot) in the analysis field.
  11. When you ask the actor to scroll down and you want to store the information in the screenshot, you need to write down in the next goal that you want the actor to record_info (with a short `file_name`), then scroll down.
  12. If you find the information in the screenshot will help the later execution of the task, you need to write down in the next goal that you want the actor to record_info (with a short `file_name`), and what info to record.
=== ACTION-SPECIFIC REMINDERS ===
- **Text Input:** Verify the insertion point is correct.
- **Scrolling:** Confirm that scrolling completed.
- **Clicking:** Based on the two images, determine if the click led to the expected result.
---
*Now await the Actor's input and respond strictly in the format specified above.*
            """
        )

class ActorPrompt_turix:
    def __init__(
        self,
        action_descriptions: str,
        max_actions_per_step: int = 8,
    ):
        self.action_descriptions = action_descriptions
        self.current_time = datetime.now()
        self.max_actions_per_step = max_actions_per_step

    def get_system_message(self) -> SystemMessage:
        return SystemMessage(
            content=f"""
SYSTEM PROMPT FOR ACTION MODEL:
=== GLOBAL INSTRUCTIONS ===
- Environment: {OS_NAME}. Current time is {self.current_time}.
- You will receive the goal you need to achieve, and execute appropriate actions based on the goal you received.
- You can only open the apps that are already installed in the computer, {apps_message}
- All the coordinates are normalized to 0-1000. You MUST output normalized positions.
- The maximum number of actions you can output in one step is {self.max_actions_per_step}.
- Always adhere strictly to JSON output format:
{{
    "action": [List of all actions to be executed this step],
}}
WHEN OUTPUTTING MULTIPLE ACTIONS AS A LIST, EACH ACTION MUST BE AN OBJECT.
=== ROLE-SPECIFIC DIRECTIVES ===
- Role: Action Model for a {OS_NAME} desktop agent. Execute actions based on goal.
- Responsibilities:
  1. Follow the next_goal precisely using available actions:
{self.action_descriptions}
  2. If the next goal involves the intention to store information, you must output the action "record_info" with both `text` and `file_name`.
  3. When the next goal involves analyzing the user information, you must output a record_info action with a detailed analysis based on the screenshot, brain's analysis, and the stored information. The `file_name` should be a short summary ending in `.txt`.
            """
        )

class MemoryPrompt:
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
SYSTEM PROMPT FOR MEMORY MODEL:
You are a memory summarization model for a computer use agent on macOS.
Condense the provided step history into a structured summary.

Your summary MUST include these sections (omit empty ones):
1. Completed Actions: What was done and the outcome (success/failed)
2. Current App State: Which app is open, what screen/page is visible
3. Information Gathered: Any data extracted (search results, file contents, form values)
4. Errors and Recovery: What went wrong and how it was handled
5. Pending Goals: What was attempted but not yet finished

Rules:
- Be concise but preserve all actionable details.
- Include specific element names, coordinates, app names, and file names/paths when relevant.
- Do not include step numbers.
- Output must be valid JSON only:
{{
    "summary": "Structured summary following the sections above",
    "file_name": "short_descriptive_name.txt"
}}
- `file_name` must be short, end with `.txt`, and contain no path.
            """
        )

class AgentMessagePrompt:
    def __init__(
        self,
        state_content: list,
        result: Optional[list[ActionResult]] = None,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        step_info: Optional[AgentStepInfo] = None,
    ):
        # Collect all text items in order and keep all images.
        text_items = [
            item.get("content") or item.get("text", "")
            for item in state_content
            if item.get("type") == "text"
        ]
        image_items = [
            item["image_url"]["url"]
            for item in state_content
            if item.get("type") == "image_url"
        ]

        self.state = "\n\n".join([t for t in text_items if t])
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
                "text": f"{step_info_str}CURRENT APPLICATION STATE:\n{self.state}",
            }
        ]

        for image_url in self.image_urls:
            content.append({"type": "image_url", "image_url": {"url": image_url}})

        # since we introduce the result into brain in state_content, here is not required
        # if self.result:
        #     results_text = "\n".join(
        #         f"ACTION RESULT {i+1}: {r.extracted_content}" if r.extracted_content
        #         else f"ACTION ERROR {i+1}: ...{r.error[-self.max_error_length:]}"
        #         for i, r in enumerate(self.result)
        #     )
        #     content.append({"type": "text", "text": results_text})

        return HumanMessage(content=content)

class PlannerPrompt(SystemPrompt):
    def __init__(
        self,
        action_descriptions: str,
        max_actions_per_step: int = 10,
        skill_catalog: str = "",
    ):
        self.action_descriptions = action_descriptions
        self.max_actions_per_step = max_actions_per_step
        self.skill_catalog = skill_catalog
    def get_system_message(self) -> SystemMessage:
        skills_block = ""
        if self.skill_catalog:
            skills_block = f"""
=== SKILLS CATALOG ===
You may select from the skills below using ONLY the skill names listed.
Use the descriptions to decide which skills help the task.
{self.skill_catalog}
"""
        else:
            skills_block = """
=== SKILLS CATALOG ===
(No skills provided.)
"""
        return SystemMessage(
content = f"""
SYSTEM_PROMPT_FOR_PLANNER
=========================
=== GLOBAL INSTRUCTIONS ===
- **Environment:** {OS_NAME}.
- Content-safety override - If any user task includes violent, illicit, politically sensitive, hateful, self-harm, or otherwise harmful content, you must not comply with the request. Instead, you must output exactly with the phrase "REFUSE TO MAKE PLAN". (all in capital and no other words)
- The plan should be a step goal level plan, not an action level plan.
- **Output Format for Single-turn Non-repetitive Tasks:** Strictly JSON in English, no harmful language:
{{
    "iteration_info": {{
        "current_iteration": i,
        "total_iterations": times you need to repeat,
    }},
    "search_summary": "Concise summary of the most relevant search findings (empty string if none).",
    "selected_skills": ["skill-name-1", "skill-name-2"],
    "natural_language_plan": "High-level plan in natural language (no step IDs, no low-level actions).",
    "step_by_step_plan": [
        {{ "step_id": "Step 1", "description": "[Goal Description]", "important_search_info": "[Relevant search info for this step or empty string]" }},
        {{ "step_id": "Step 2", "description": "[Goal Description]", "important_search_info": "[Relevant search info for this step or empty string]" }},
        {{ "step_id": "Step N", "description": "[Goal Description]", "important_search_info": "[Relevant search info for this step or empty string]" }}
    ]
}}
- **Output Format for Multi-turn Repetitive Tasks:** Same JSON structure as above, but with total_iterations > 1. In the first turn (initial task), set current_iteration=1 and output the plan for the FIRST instance/item only. In subsequent turns, the human message will specify the previous completed iteration (e.g., "Continue: previous iteration X completed, summary: [brief what was done], original task: [reminder]"), then set current_iteration = previous + 1 and output the plan ONLY for that specific next instance/item.
- **IMPORTANT STEP ID FORMAT**: Each step in `step_by_step_plan` must have `step_id` as "Step X" starting from 1 (reset per iteration).
- **IMPORTANT DESCRIPTION CONTENT**: Descriptions must be concise, high-level goals in English, no low-level details (e.g., no keystrokes, clicks). Focus on achieving the step's goal for the CURRENT iteration's specific item/instance.
- **SEARCH INFO FIELDS**: If no search was used or no relevant findings, set `search_summary` and each `important_search_info` to an empty string.
- **SKILL SELECTION**: Always include `selected_skills` as a list of skill names from the Skills Catalog. If none apply or no skills are provided, output an empty list []. If the user message provides "Preselected skills", you MUST use that list exactly and do not add or remove skills.
- **NATURAL LANGUAGE PLAN**: Include `natural_language_plan` as a concise, high-level description of the overall plan. Do NOT include step IDs, numbering like "Step 1", or low-level actions (clicks, keystrokes). Prefer 2-6 short sentences or bullets describing the main objectives.
{skills_block}
=== MULTI-TURN REPETITIVE TASK HANDLING ===
- **Detect Repetition:** If the task involves repeating similar actions for multiple distinct items (e.g., "download 5 images: url1,url2,..."; "send message to 3 people: Alice, Bob, Charlie"), calculate total_iterations = number of items/instances.
- **First Turn (Initial Message):**
  - Determine total_iterations N.
  - Output iteration_info with current_iteration=1, total_iterations=N.
  - step_by_step_plan: ONLY for the 1st item/instance (e.g., download url1 only; make it specific to that item).
- **Subsequent Turns (Continuation Messages):**
  - Human will provide: "Summary of previous: [brief, e.g., 'Downloaded image1 from url1']; The information stored previous tasks; Previous task you planned that completed; Original task."
  - Parse this to identify the next item/instance (X+1).
  - Output iteration_info: current_iteration = X+1, total_iterations = same N.
  - step_by_step_plan: ONLY for the (X+1)th specific item/instance (independent, no reference to others).
  - You should give the full information stored to the agent if the information stored does help in next iteration.
  - Avoid give the previous completed plan you generated. (e.g. the previous plan download the first image, your next plan should not include download the first image again)
- **Non-repetitive Tasks:** Always total_iterations=1, current_iteration=1, full plan in one output.
- **Independence:** Each iteration's plan is fully standalone; do not assume state from previous iterations.
=== ROLE & RESPONSIBILITIES ===
- **Role:** Planner for {OS_NAME} GUI Agent in multi-turn sessions.
- **Responsibilities:**
  1. Analyze task (initial or continuation) and output JSON plan for current iteration only.
  2. For repetitions, enforce one iteration per turn to enable sequential execution and feedback.
  3. If the previous tasks were completed successfully, the new plan should not involve redoing previous completed plans.
=== SPECIFIC PLANNING GUIDELINES ===
- Prioritize PowerShell or terminal for speed in repetitive actions if suitable.
=== IMPORTANT REMINDERS ===
- Specify apps in descriptions (e.g., "In Edge, download the specific image").
- No "verify/check" in descriptions.
- For coding: Use VS Code/Copilot/Cursor.
- Sometimes the screenshot of the completion of the previous subtask will mislead the performance of the agent in executing the next subtask. Give instructions to remove the completion status to avoid ambiguity. (e.g. close the tab showing the completed status)
---
*Respond strictly with the JSON output.*
"""

  )


class PlannerPreplanPrompt:
    def __init__(self, task: str, use_search: bool, use_skills: bool, skill_catalog: str = ""):
        self.task = task
        self.use_search = use_search
        self.use_skills = use_skills
        self.skill_catalog = skill_catalog or ""

    def _skills_block(self) -> str:
        if self.skill_catalog:
            return f"\nSKILLS CATALOG (choose exact names):\n{self.skill_catalog}\n"
        return "\nSKILLS CATALOG: (No skills provided.)\n"

    def _system_prompt(self) -> str:
        return (
            "You are a planner pre-processor. Decide whether web search is needed and which skills apply. "
            "Return JSON only in the following format:\n"
            "{\"use_search\": false, \"queries\": [], \"selected_skills\": []}\n"
            "Rules:\n"
            f"- Search enabled: {self.use_search}. If disabled, set use_search=false and queries=[].\n"
            "- If search is needed, use_search=true and provide 1-3 queries.\n"
            "- Each query must be under 12 words, English, diverse, and not a copy of the full task.\n"
            f"- Skills enabled: {self.use_skills}. If disabled or none apply, selected_skills=[].\n"
            "- If skills are enabled, choose ONLY from the catalog and output exact skill names.\n"
            f"{self._skills_block()}"
        )

    def get_messages(self) -> list[BaseMessage]:
        system = SystemMessage(content=self._system_prompt())
        return [system, HumanMessage(content=self.task)]


class PlannerPlanMessageBuilder:
    def __init__(self, action_descriptions: str, skill_catalog: str = "", use_skills: bool = False):
        self.action_descriptions = action_descriptions
        self.skill_catalog = skill_catalog
        self.use_skills = use_skills

    def _search_blocks(self, search_context: str) -> tuple[str, str]:
        if not search_context:
            return "", ""
        search_block = (
            "Readable DuckDuckGo findings selected by planner (summary only):\n"
            f"{search_context}\n\n"
        )
        search_guidance = (
            "Use the search findings above to populate the \"important search info\" field in every step "
            "with concise, useful insights that support that step. "
            "Include a short summary of the most relevant search findings for the overall task if helpful.\n"
        )
        return search_block, search_guidance

    def _skill_blocks(
        self,
        selected_skills: list[str],
        skill_context: str,
    ) -> tuple[str, str]:
        if not self.use_skills:
            return "", ""
        if selected_skills:
            skills_list = ", ".join(selected_skills)
            skill_block = (
                f"Preselected skills (use EXACTLY these in selected_skills): {skills_list}\n\n"
            )
            if skill_context:
                skill_block += f"Selected skill instructions:\n{skill_context}\n\n"
            skill_guidance = "Use the selected skill instructions above to guide the plan for each step.\n"
            return skill_block, skill_guidance
        return "Preselected skills: [] (no skills selected).\n\n", ""

    def build_initial_messages(
        self,
        task: str,
        search_context: str,
        selected_skills: list[str],
        skill_context: str,
    ) -> list[BaseMessage]:
        planner_prompt = PlannerPrompt(
            self.action_descriptions,
            skill_catalog=self.skill_catalog,
        )
        system_message = planner_prompt.get_system_message().content
        search_block, search_guidance = self._search_blocks(search_context)
        skill_block, skill_guidance = self._skill_blocks(selected_skills, skill_context)
        content = f"""
                {system_message}
                {search_block}
                {skill_block}
                {search_guidance}
                {skill_guidance}
                Now, here is the task you need to break down:
                "{task}"
                Please follow the guidelines and provide the required JSON output.
                """
        return [HumanMessage(content=content)]

    def build_continue_messages(
        self,
        task: str,
        info_memory: str,
        task_summary: str,
        plan_list: list[str],
        search_context: str,
        selected_skills: list[str],
        skill_context: str,
    ) -> list[BaseMessage]:
        planner_prompt = PlannerPrompt(
            self.action_descriptions,
            skill_catalog=self.skill_catalog,
        )
        search_block, search_guidance = self._search_blocks(search_context)
        skill_block, skill_guidance = self._skill_blocks(selected_skills, skill_context)
        content = f"The summary of previous tasks are as follows: {task_summary}\n\n"
        content += f"The information memory for previous tasks are as follows: {info_memory}\n\n"
        content += f"The previous task you planned and being completed is as follows: '{plan_list}'.\n\n"
        content += search_block
        content += skill_block
        if search_guidance:
            content += search_guidance
        if skill_guidance:
            content += skill_guidance
        content += (
            "Based on the above information memory and task summaries, please continue to edit and "
            f"provide a detailed step-by-step plan for the overall task: '{task}'. Ensure that the plan "
            "is clear, actionable, avoid the previous plan you generated, and follows the required format."
        )
        return [planner_prompt.get_system_message(), HumanMessage(content=content)]
