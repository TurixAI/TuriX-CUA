import asyncio
from inspect import iscoroutinefunction, signature
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, Field, create_model

from src.controller.registry.views import (
	ActionModel,
	ActionRegistry,
	RegisteredAction,
)

class Registry:
	"""Service for registering and managing actions"""

	def __init__(self, exclude_actions: list[str] = []):
		self.registry = ActionRegistry()
		self.exclude_actions = exclude_actions

	def _create_param_model(self, function: Callable) -> Type[BaseModel]:
		"""Creates a Pydantic model from function signature"""
		sig = signature(function)
		params = {
			name: (param.annotation, ... if param.default == param.empty else param.default)
			for name, param in sig.parameters.items()
		}
		return create_model(
			f'{function.__name__}_parameters',
			__base__=ActionModel,
			**params,
		)

	def action(
		self,
		description: str,
		param_model: Optional[Type[BaseModel]] = None,
	):
		"""Decorator for registering actions"""

		def decorator(func: Callable):
			if func.__name__ in self.exclude_actions:
				return func

			actual_param_model = param_model or self._create_param_model(func)

			if not iscoroutinefunction(func):
				async def async_wrapper(*args, **kwargs):
					return await asyncio.to_thread(func, *args, **kwargs)

				async_wrapper.__signature__ = signature(func)
				async_wrapper.__name__ = func.__name__
				async_wrapper.__annotations__ = func.__annotations__
				wrapped_func = async_wrapper
			else:
				wrapped_func = func

			action = RegisteredAction(
				name=func.__name__,
				description=description,
				function=wrapped_func,
				param_model=actual_param_model,
			)
			self.registry.actions[func.__name__] = action
			return func

		return decorator

	async def execute_action(self, action_name: str, params: dict) -> Any:
		"""Execute a registered action"""
		if action_name not in self.registry.actions:
			raise ValueError(f'Action {action_name} not found')

		action = self.registry.actions[action_name]
		try:
			validated_params = action.param_model(**params)

			sig = signature(action.function)
			parameters = list(sig.parameters.values())
			is_pydantic = parameters and issubclass(parameters[0].annotation, BaseModel)
			
			if is_pydantic:
				return await action.function(validated_params)
			return await action.function(**validated_params.model_dump())

		except Exception as e:
			raise RuntimeError(f'Error executing action {action_name}: {str(e)}') from e

	def create_action_model(self) -> Type[ActionModel]:
		"""Creates a Pydantic model from registered actions"""
		fields = {
			name: (
				Optional[action.param_model],
				Field(default=None, description=action.description),
			)
			for name, action in self.registry.actions.items()
		}

		return create_model('ActionModel', __base__=ActionModel, **fields)

	def get_prompt_description(self) -> str:
		"""Get a description of all actions for the prompt"""
		return self.registry.get_prompt_description()
