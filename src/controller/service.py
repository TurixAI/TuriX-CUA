import asyncio
import logging
import subprocess
from typing import Optional
import Cocoa
from src.agent.views import ActionModel, ActionResult
from src.controller.registry.service import Registry
from src.controller.views import (
	InputTextAction,
	OpenAppAction,
	AppleScriptAction,
	PressAction,
	PressCombinedAction,
	DragAction,
	RightClickPixel,
	LeftClickPixel,
	ScrollDownAction,
	ScrollUpAction,
	MoveToAction
)
from src.helpers.actions import type_into, press, _scroll_invisible_at_position, move_to, left_click_pixel, right_click_pixel, press_combination, drag_pixel
from src.utils import time_execution_async, time_execution_sync
logger = logging.getLogger(__name__)

class Controller:
	def __init__(
		self,
		exclude_actions: list[str] = [],
	):
		self.exclude_actions = exclude_actions
		self.registry = Registry(exclude_actions)
		self._register_default_actions()

	def _register_default_actions(self):
		"""Register all default mac actions"""

		@self.registry.action(
				'Complete task',
				param_model=NoParamsAction)
		async def done():
			return ActionResult(extracted_content='done', is_done=True)
		@self.registry.action(
				'Type', 
				param_model=InputTextAction
				)
		async def input_text(text: str):
			try:			
				input_successful = await type_into(text)
				if input_successful:
					return ActionResult(extracted_content=f'Successfully input text')
				else:
					msg = f'❌ Input failed'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)


		@self.registry.action("Open a mac app", param_model=OpenAppAction)
		async def open_app(app_name: str):
			"""
			Attempt to open a macOS app by name. Then:
			1) Try pgrep-based PID lookup first.
			2) If that fails or the process has no visible window, fallback to fuzzy matching
			against NSWorkspace.sharedWorkspace().runningApplications().
			"""

			user_input = app_name
			workspace = Cocoa.NSWorkspace.sharedWorkspace()
			logger.info(f"\nLaunching app: {user_input}...")

			success = workspace.launchApplication_(user_input)
			if not success:
				msg = f"❌ Failed to launch '{user_input}'"
				logger.error(msg)
				return ActionResult(extracted_content=msg, error=msg)
			
			success_msg = f"✅ Launched {user_input}"
			logger.info(success_msg)
			return ActionResult(extracted_content=success_msg)
		
		@self.registry.action(
			'Run an AppleScript',
			param_model=AppleScriptAction
		)
		async def run_apple_script(script: str):
			logger.debug(f'Running AppleScript: {script}')
			
			wrapped_script = f'''
				try
					{script}
					return "OK"
				on error errMsg
					return "ERROR: " & errMsg
				end try
			'''
			
			try:
				result = subprocess.run(
					['osascript', '-e', wrapped_script],
					capture_output=True,
					text=True
				)
				
				if result.returncode == 0:
					output = result.stdout.strip()
					if output == "OK":
						return ActionResult(extracted_content="Success")
					elif output.startswith("ERROR:"):
						error_msg = output
						logger.error(error_msg)
						return ActionResult(extracted_content=error_msg, error=error_msg)
					else:
						return ActionResult(extracted_content=output)
				else:
					error_msg = f"AppleScript failed with return code {result.returncode}: {result.stderr.strip()}"
					logger.error(error_msg)
					return ActionResult(extracted_content=error_msg, error=error_msg)
					
			except Exception as e:
				error_msg = f"Failed to run AppleScript: {str(e)}"
				logger.error(error_msg)
				return ActionResult(extracted_content=error_msg, error=error_msg)
		
		@self.registry.action(
			'Single Hotkey',
			param_model=PressAction,
		)
		async def Hotkey(key: str = "enter"):
			key_press = key.replace("Key.", "")
			press_successful = await press(key_press)
			if press_successful:
				logging.info(f'✅ pressed key code: {key}')
				return ActionResult(extracted_content=f'Successfully press keyboard with key code {key}')
			
		@self.registry.action(
			'Press Multiple Hotkey',
			param_model=PressCombinedAction,
		)
		async def multi_Hotkey(key1: str, key2: str, key3: Optional[str] = None):
			def clean_key(raw: str | None) -> str | None:
				"""Strip the `Key.` prefix and any stray quote marks."""
				if raw is None:
					return None
				return raw.replace("Key.", "").strip("'\"")
			key1 = clean_key(key1)
			key2 = clean_key(key2)
			key3 = clean_key(key3)
			key_map = {
				'cmd': 'command',
				'delete': 'backspace'
			}
			def map_key(key: str) -> str:
				return key_map.get(key.lower(), key)
			
			key1 = map_key(key1)
			key2 = map_key(key2)
			key3 = map_key(key3) if key3 is not None else None
			if key3 is not None:
				press_successful = await press_combination(key1, key2, key3)
				if press_successful:
					logging.info(f'✅ pressed combination key: {key1}, {key2} and {key3}')
					return ActionResult(extracted_content=f'Successfully press keyboard with key code {key1}, {key2} and {key3}')
			else:
				press_successful = await press_combination(key1,key2,key3=None)
				if press_successful:
					logging.info(f'✅ pressed combination key: {key1} and {key2}')
					return ActionResult(extracted_content=f'Successfully press keyboard with key code {key1} and {key2}')

		@self.registry.action(
			'RightSingle click at specific pixel',
			param_model=RightClickPixel
		)
		async def RightSingle(position: list = [0,0]):
			logger.debug(f'Correct clicking pixel position {position}')
			try:
				click_successful = await right_click_pixel(position)
				if click_successful:
					logging.info(f'✅ Finished right click at pixel: {position}')
					return ActionResult(extracted_content=f'Successfully clicked pixel {position}')
				else:
					msg = f'❌ Right click failed for pixel with position: {position}'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)
			
		@self.registry.action(
			'Left click at specific pixel',
			param_model=LeftClickPixel
		)
		async def Click(position: list = [0,0]):
			logger.debug(f'Correct clicking pixel position {position}')
			try:
				click_successful = await left_click_pixel(position)
				if click_successful:
					logging.info(f'✅ Finished left click at pixel: {position}')
					return ActionResult(extracted_content=f'Successfully clicked pixel {position}')
				else:
					msg = f'❌ Left click failed for pixel with position: {position}'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)
			
		@self.registry.action(
			'Drag an object from one pixel to another',
			param_model=DragAction
		)
		async def Drag(position1: list = [0,0], position2: list = [0,0]):
			try:
				drag_successful = await drag_pixel(position1, position2)
				if drag_successful:
					logger.info(f'Correct draging pixel from position {position1} to {position2}')
					return ActionResult(extracted_content=f'Successfully drag pixel {position1} to {position2}')
				else:
					msg = f'❌ Drag failed for pixel with position: {position1}'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)
			
		@self.registry.action(
				'Move mouse to specific pixel',
				param_model=MoveToAction,
		)
		async def move_mouse(position: list = [0,0]):
			logger.debug(f'Correct move mouse to position {position}')
			try:
				move_successful = await move_to(position)
				if move_successful:
					logging.info(f'✅ Finished move mouse to pixel: {position}')
					return ActionResult(extracted_content=f'Successfully move mouse to {position}')
				else:
					msg = f'❌ Failed move mouse to pixel with position: {position}'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)
		
		@self.registry.action(
			'Scroll up',
			param_model=ScrollUpAction,
		)
		async def scroll_up(position, dx: int = 0, dy: int = 20):
			x,y = position
			amount = dy
			scroll_successful = await _scroll_invisible_at_position(x,y,amount)
			if scroll_successful:
				logging.info(f'✅ Scrolled up by {amount}')
				return ActionResult(extracted_content=f'Successfully scrolled up by {amount}')
			
		@self.registry.action(
			'Scroll down',
			param_model=ScrollDownAction,
		)
		async def scroll_down(position, dx: int = 0, dy: int = 20):
			x,y = position
			amount = dy
			scroll_successful = await _scroll_invisible_at_position(x,y, -amount)
			if scroll_successful:
				logging.info(f'✅ Scrolled down by {amount}')
				return ActionResult(extracted_content=f'Successfully scrolled down by {amount}')
			
		@self.registry.action(
			'Tell the short memory that you are recording information',
			param_model=NoParamsAction
		)
		async def record_info():
			return ActionResult(extracted_content=f'Recorded info into information_stored.')
		
		@self.registry.action(
			'Wait',
			param_model=NoParamsAction
		)
		async def wait():
			return ActionResult(extracted_content=f'Waiting')

	def action(self, description: str, **kwargs):
		"""Decorator for registering custom actions

		@param description: Describe the LLM what the function does (better description == better function calling)
		"""
		return self.registry.action(description, **kwargs)

	@time_execution_async('--multi-act')
	async def multi_act(
		self, actions: list[ActionModel], action_valid: bool = True
	) -> list[ActionResult]:
		"""Execute multiple actions"""
		results = []
		if action_valid:
			for i, action in enumerate(actions):
				results.append(await self.act(action))
				await asyncio.sleep(0.5)

				logger.debug(f'Executed action {i + 1} / {len(actions)}')
				if results[-1].is_done or results[-1].error or i == len(actions) - 1:
					break

			return results
		else:
			return [ActionResult(error="Invalid action. Please use the screenshot to determine the correct pixel to act on again.",include_in_memory=True)]

	@time_execution_sync('--act')
	async def act(self, action: ActionModel) -> ActionResult:
		"""Execute an action"""
		try:
			for action_name, params in action.model_dump(exclude_unset=True).items():
				if params is not None:
					result = await self.registry.execute_action(action_name, params)
					if isinstance(result, str):
						return ActionResult(extracted_content=result)
					elif isinstance(result, ActionResult):
						return result
					elif result is None:
						return ActionResult()
					else:
						raise ValueError(f'Invalid action result type: {type(result)} of {result}')
			return ActionResult()
		except Exception as e:
			msg = f'Error executing action: {str(e)}'
			logger.error(msg)
			return ActionResult(extracted_content=msg, error=msg)

class NoParamsAction(ActionModel):
	"""
	Simple parameter model requiring no arguments.
	"""
	pass
