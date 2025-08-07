from __future__ import annotations

"""Pydantic models corresponding to the JSON schemas used by the agent pipeline.

Import any of these models and pass them to ``ChatGoogleGenerativeAI.with_structured_output``
(or ``llm.with_structured_output``) to force Gemini to emit JSON that conforms to the
specified schema.

Example
-------
>>> from langchain_google_genai import ChatGoogleGenerativeAI
>>> from output_models import AgentStepOutput
>>>
>>> llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-05-06", temperature=0)
>>> structured_llm = llm.with_structured_output(AgentStepOutput)
>>> structured_llm.invoke("Open TextEdit, type 'Hello', then save the file.")
AgentStepOutput(...)
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from src.controller.views import *

class ActionItem(BaseModel):
    """Exactly one of the fields must be populated to specify the concrete action."""
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

class CurrentState(BaseModel):
    evaluation_previous_goal: str = Field(..., description="Evaluation of the previous goal execution.")
    next_goal: str = Field(..., description="The immediate next goal for the agent.")
    information_stored: str = Field(..., description="Information to remember.")

class AgentStepOutput(BaseModel):
    """Schema for the agent's per‑step output.

    - ``action``: list of actions the agent should perform in order. Multiple actions
      are allowed in a single step.
    """
    action: List[ActionItem] = Field(
        ...,
        min_items=0,
        max_items=10,
        description="Ordered list of 0-10 actions for this step."
    )
    current_state: CurrentState

    def __repr__(self) -> str:
        non_none = self.model_dump(exclude_none=True)
        field_strs = ", ".join(f"{k}={v!r}" for k, v in non_none.items())
        return f"{self.__class__.__name__}({field_strs})"

    @property
    def content(self) -> str:
        """
        Returns a JSON-formatted string representation of the instance,
        allowing access via the `.content` attribute.
        """
        return self.model_dump_json(exclude_none=True, exclude_unset=True)

    @property
    def parsed(self) -> Dict[str, Any]:
        """
        Returns the dictionary representation of the instance,
        facilitating direct access to structured data.
        """
        return self.model_dump(exclude_none=True, exclude_unset=True)
