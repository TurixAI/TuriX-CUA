from __future__ import annotations
import re
import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Type

from openai import RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from src.controller.registry.views import ActionModel
from pydantic.v1 import BaseModel, Field
from src.controller.views import *

@dataclass
    
class AgentStepInfo:
    step_number: int
    max_steps: int


class ActionResult(BaseModel):
    """Result of executing an action"""

    is_done: Optional[bool] = False
    extracted_content: Optional[str] = None
    error: Optional[str] = None
    include_in_memory: bool = False  # whether to include in past messages as context or not
    current_app_pid: Optional[int] = None
    action_is_valid: Optional[bool] = True


class AgentBrain(BaseModel):
    """Current state of the agent"""

    evaluation_previous_goal: str = Field(..., description="Success/Failed of previous step (From evaluator)")
    next_goal: str = Field(..., description="The immediate next goal.")
    information_stored: str = Field(..., description="Accumulated important information, add continuously, else 'None'")

class AgentOutput(BaseModel):
    """Output model for agent

    @dev note: this model is extended with custom actions in AgentService. 
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


    action: list[ActionModel] = Field(
        ...,
        min_items=0,
        max_items=10,                     # ← hard limit
        description="Ordered list of 0-10 actions for this step."
    )
    current_state: AgentBrain
    @staticmethod
    def type_with_custom_actions(custom_actions: Type[ActionModel]) -> Type['AgentOutput']:
        """Extend actions with custom actions"""
        return create_model(
            'AgentOutput',
            __base__=AgentOutput,
            action=(list[custom_actions], Field(...)),  # Properly annotated field with no default
            __module__=AgentOutput.__module__,
        )


class AgentHistory(BaseModel):
    """History item for agent actions"""

    model_output: AgentOutput | None
    result: list[ActionResult]
    state: str

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Custom serialization handling circular references"""

        model_output_dump = None
        if self.model_output:
            action_dump = [action.model_dump(exclude_none=True) for action in self.model_output.action]
            model_output_dump = {
                'current_state': self.model_output.current_state.model_dump(),
                'action': action_dump,
            }

        return {
            'model_output': model_output_dump,
            'result': [r.model_dump(exclude_none=True) for r in self.result],
            'state': self.state,
        }


class AgentHistoryList(BaseModel):
    """List of agent history items"""

    history: list[AgentHistory]

    def __str__(self) -> str:
        """Representation of the AgentHistoryList object"""
        return f'AgentHistoryList(all_results={self.action_results()}, all_model_outputs={self.model_actions()})'

    def __repr__(self) -> str:
        """Representation of the AgentHistoryList object"""
        return self.__str__()

    def save_to_file(self, filepath: str | Path) -> None:
        """Save history to JSON file with proper serialization"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            data = self.model_dump()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise e

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Custom serialization that properly uses AgentHistory's model_dump"""
        return {
            'history': [h.model_dump(**kwargs) for h in self.history],
        }

    @classmethod
    def load_from_file(cls, filepath: str | Path, output_model: Type[AgentOutput]) -> 'AgentHistoryList':
        """Load history from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # loop through history and validate output_model actions to enrich with custom actions
        for h in data['history']:
            if h['model_output']:
                if isinstance(h['model_output'], dict):
                    h['model_output'] = output_model.model_validate(h['model_output'])
                else:
                    h['model_output'] = None
        history = cls.model_validate(data)
        return history

    def last_action(self) -> None | dict:
        """Last action in history"""
        if self.history and self.history[-1].model_output:
            return self.history[-1].model_output.action[-1].model_dump(exclude_none=True)
        return None

    def errors(self) -> list[str]:
        """Get all errors from history"""
        errors = []
        for h in self.history:
            errors.extend([r.error for r in h.result if r.error])
        return errors

    def final_result(self) -> None | str:
        """Final result from history"""
        if self.history and self.history[-1].result[-1].extracted_content:
            return self.history[-1].result[-1].extracted_content
        return None

    def is_done(self) -> bool:
        """Check if the agent is done"""
        if self.history and len(self.history[-1].result) > 0 and self.history[-1].result[-1].is_done:
        # if self.history and self.history[-1].model_output.current_state.evaluation_previous_goal == 'Success' and self.history[-1].result[-1].is_done:
            return True
        return False

    def has_errors(self) -> bool:
        """Check if the agent has any errors"""
        return len(self.errors()) > 0

    def action_names(self) -> list[str]:
        """Get all action names from history"""
        action_names = []
        for action in self.model_actions():
            actions = list(action.keys())
            if actions:
                action_names.append(actions[0])
        return action_names

    def model_thoughts(self) -> list[AgentBrain]:
        """Get all thoughts from history"""
        return [h.model_output.current_state for h in self.history if h.model_output]

    def model_outputs(self) -> list[AgentOutput]:
        """Get all model outputs from history"""
        return [h.model_output for h in self.history if h.model_output]

    def model_actions(self) -> list[dict]:
        """Get all actions from history"""
        outputs = []
        for h in self.history:
            if h.model_output:
                for action in h.model_output.action:
                    output = action.model_dump(exclude_none=True)
                    outputs.append(output)
        return outputs

    def action_results(self) -> list[ActionResult]:
        """Get all results from history"""
        results = []
        for h in self.history:
            results.extend([r for r in h.result if r])
        return results

    def extracted_content(self) -> list[str]:
        """Get all extracted content from history"""
        content = []
        for h in self.history:
            content.extend([r.extracted_content for r in h.result if r.extracted_content])
        return content

    def model_actions_filtered(self, include: list[str] = []) -> list[dict]:
        """Get all model actions from history as JSON"""
        outputs = self.model_actions()
        result = []
        for o in outputs:
            for i in include:
                if i == list(o.keys())[0]:
                    result.append(o)
        return result


class AgentError:
    """Container for agent error handling"""

    VALIDATION_ERROR = 'Invalid model output format. Please follow the correct schema.'
    RATE_LIMIT_ERROR = 'Rate limit reached. Waiting before retry.'
    NO_VALID_ACTION = 'No valid action found'

    @staticmethod
    def format_error(error: Exception, include_trace: bool = False) -> str:
        """Format error message based on error type and optionally include trace"""
        if isinstance(error, ValidationError):
            return f'{AgentError.VALIDATION_ERROR}\nDetails: {str(error)}'
        if isinstance(error, RateLimitError):
            return AgentError.RATE_LIMIT_ERROR
        if include_trace:
            return f'{str(error)}\nStacktrace:\n{traceback.format_exc()}'
        return f'{str(error)}'
