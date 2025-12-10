from __future__ import annotations
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from src.controller.views import *

# ---------------------------------------------------------------------------
# ACTION ITEM DEFINITIONS
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    """
    Represents a single concrete action to be executed by the Controller.
    Exactly one field must be populated.
    """
    model_config = ConfigDict(exclude_none=True) 
    done: Optional[NoParamsAction] = None
    input_text: Optional[InputTextAction] = None
    open_app: Optional[OpenAppAction] = None
    run_apple_script: Optional[AppleScriptAction] = None
    Hotkey: Optional[PressAction] = None 
    multi_Hotkey: Optional[PressCombinedAction] = None
    RightSingle: Optional[RightClickPixel] = None
    Click: Optional[LeftClickPixel] = None
    Drag: Optional[DragAction] = None
    move_mouse: Optional[MoveToAction] = None
    scroll_up: Optional[ScrollUpAction] = None
    scroll_down: Optional[ScrollDownAction] = None
    record_info: Optional[NoParamsAction] = None
    wait: Optional[NoParamsAction] = None

    def __repr__(self) -> str:
        non_none = self.model_dump(exclude_none=True)
        field_strs = ", ".join(f"{k}={v!r}" for k, v in non_none.items())
        return f"{self.__class__.__name__}({field_strs})"
    
    @field_validator("wait", "record_info", mode="before")
    def fix_empty_string(cls, v):
        if v == "" or v is None:
            return {}
        if not isinstance(v, dict):
            return {}
        return v

# ---------------------------------------------------------------------------
# STATE & MEMORY MODELS
# ---------------------------------------------------------------------------

class CurrentState(BaseModel):
    """
    Captures the Agent's understanding of the current step, including memory and self-evaluation.
    """
    evaluation_previous_goal: str = Field(..., description="Success/Failed (From evaluator)")
    next_goal: str = Field(..., description="Goal of this step based on actions. ONLY DESCRIBE THE EXPECTED ACTIONS RESULT.")
    information_stored: str = Field(..., description="Accumulated important information (text/prices/ids). Add continuously, else 'None'.")
    step_summary: Optional[str] = Field(
        None,
        description="CRITICAL FOR LONG-TERM MEMORY: A concise summary of what was ACHIEVED in this step. "
                    "Focus on outcomes (e.g. 'Found user email'), not clicks. "
                    "This summary becomes the persistent record after this step leaves short-term memory."
    )

class PlannerOutput(BaseModel):
    """
    Schema for the Planner Agent's (Brain) output.
    Contains high-level reasoning and global planning.
    """
    model_config = ConfigDict(exclude_none=True)
    
    analysis: str = Field(
        ..., 
        description="Chain-of-thought analysis of the current screen state, previous history, and overall progress."
    )

    global_plan: str = Field(
        ...,
        description="The updated Global Plan. Format: '1. Step A (Done), 2. Step B (Current), 3. Step C (Pending)'."
    )

    next_high_level_goal: str = Field(
        ..., 
        description="A clear, directive instruction for the Actor agent to execute in this step."
    )

    def __repr__(self) -> str:
        return f"Planner(Goal: {self.next_high_level_goal})"

# ---------------------------------------------------------------------------
# AGENT OUTPUT (MAIN MODEL)
# ---------------------------------------------------------------------------

class AgentStepOutput(BaseModel):
    """
    Schema for the Actor Agent's per-step output.
    """
    current_state: CurrentState
    action: List[ActionItem] = Field(
        ...,
        min_items=0,
        max_items=10,
        description="Ordered list of 0-10 actions for this step."
    )

    def __repr__(self) -> str:
        non_none = self.model_dump(exclude_none=True)
        field_strs = ", ".join(f"{k}={v!r}" for k, v in non_none.items())
        return f"{self.__class__.__name__}({field_strs})"

    @property
    def content(self) -> str:
        return self.model_dump_json(exclude_none=True, exclude_unset=True)

    @property
    def parsed(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True, exclude_unset=True)

__all__ = [
    "AgentStepOutput",
    "PlannerOutput"
]