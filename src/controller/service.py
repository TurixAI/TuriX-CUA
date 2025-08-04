import asyncio
import logging
from typing import Optional

from src.agent.views import ActionModel, ActionResult
from src.controller.registry.service import Registry
from src.controller.views import (
	InputTextAction,
	OpenAppAction,
	PressAction,
	PressCombinedAction,
	DragAction,
	RightClickPixel,
	LeftClickPixel,
	ScrollDownAction,
	ScrollUpAction,
	MoveToAction,
)
from src.utils import time_execution_async, time_execution_sync
from src.windows.openapp import open_application_by_name
from src.windows.actions import WindowsActions

logger = logging.getLogger(__name__)

class Controller:
	def __init__(
		self,
		exclude_actions: list[str] = [],
	):
		self.exclude_actions = exclude_actions
		self.registry = Registry(exclude_actions)
		self.win = WindowsActions()
		self._register_default_actions()

	def _register_default_actions(self):
		"""Register all default Windows UI actions"""

		@self.registry.action(
				'Complete task',
				param_model=NoParamsAction)
		async def done():
			return ActionResult(extracted_content='done', is_done=True)
		@self.registry.action(
				'Type', 
				param_model=InputTextAction,
				requires_mac_builder=False)
		async def input_text(text: str):
			try:			
				input_successful = await self.win.type_text(text)
				if input_successful:
					return ActionResult(extracted_content=f'Successfully input text')
				else:
					msg = f'❌ Input failed'
					return ActionResult(extracted_content=msg, error=msg)
			except Exception as e:
				msg = f'❌ An error occurred: {str(e)}'
				logging.error(msg)
				return ActionResult(extracted_content=msg, error=msg)


		@self.registry.action("Open a Windows app", param_model=OpenAppAction)
		async def open_app(app_name: str):
			"""
			Attempt to open a Windows app by name.
			"""

			user_input = app_name
			if user_input.lower() == 'wechat':
				user_input = '微信'
			success, _ = await open_application_by_name(user_input)
			logger.info(f"\nLaunching app: {user_input}...")			
			if not success:
				msg = f"❌ Failed to launch '{user_input}'"
				logger.error(msg)
				return ActionResult(extracted_content=msg, error=msg)

		
			pid = None

			success_msg = f"✅ Launched {user_input}, PID={pid}"
			logger.info(success_msg)
			return ActionResult(extracted_content=success_msg, current_app_pid=pid)
		
		@self.registry.action(
			'Single Hotkey',
			param_model=PressAction,
		)
		async def Hotkey(key: str = "enter"):
			# The key is Key.enter, but what i need is the string "enter"
			key_press = key.replace("Key.", "")
			press_successful = await self.win.press_key(key_press)
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
				return raw.replace("Key.", "").strip("'\"")   # handles 't', "t", Key.'t', etc.
			key1 = clean_key(key1)
			key2 = clean_key(key2)
			if key3:	
				key3 = clean_key(key3)
			key_map = {
				'cmd': 'ctrl',
				'delete': 'backspace'
			}
			# 映射键名
			def map_key(key: str) -> str:
				return key_map.get(key.lower(), key)
			
			key1 = map_key(key1)
			key2 = map_key(key2)
			key3 = map_key(key3) if key3 is not None else None
			if key3 is not None:
				press_successful = await self.win.press_hotkey(key1, key2, key3)
				if press_successful:
					logging.info(f'✅ pressed combination key: {key1}, {key2} and {key3}')
				return ActionResult(extracted_content=f'Successfully press keyboard with key code {key1}, {key2} and {key3}')
			else:
				press_successful = await self.win.press_hotkey(key1, key2)
				if press_successful:
					logging.info(f'✅ pressed combination key: {key1} and {key2}')
				return ActionResult(extracted_content=f'Successfully press keyboard with key code {key1} and {key2}')

		@self.registry.action(
			'RightSingle click at specific pixel',
			param_model=RightClickPixel,
			requires_mac_builder=False
		)
		async def RightSingle(position: list = [0,0]):
			logger.debug(f'Correct clicking pixel position {position}')
			try:
				x, y = position
				click_successful = await self.win.click(x, y, button='right')
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
			param_model=LeftClickPixel,
			requires_mac_builder=False
		)
		async def Click(position: list = [0,0]):
			logger.debug(f'Correct clicking pixel position {position}')
			try:
				x, y = position
				click_successful = await self.win.click(x, y, button='left')
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
			param_model=DragAction,
			requires_mac_builder=False
		)
		async def Drag(position1: list = [0,0], position2: list = [0,0]):
			try:
				x1, y1 = position1
				x2, y2 = position2
				drag_successful = await self.win.drag(x1, y1, x2, y2)
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
				requires_mac_builder=False
		)
		async def move_mouse(position: list = [0,0]):
			logger.debug(f'Correct move mouse to position {position}')
			try:
				x, y = position
				move_successful = await self.win.move_mouse(x, y)
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
		async def scroll_up(position, dx: int = -20, dy: int = 20):
			x,y = position
			amount = dy
			scroll_successful = await self.win.scroll(x, y, amount)
			if scroll_successful:
				logging.info(f'✅ Scrolled up by {amount}')
				return ActionResult(extracted_content=f'Successfully scrolled up by {amount}')
			
		@self.registry.action(
			'Scroll down',
			param_model=ScrollDownAction,
		)
		async def scroll_down(position, dx: int = -20, dy: int = 20):
			x,y = position
			amount = dy
			scroll_successful = await self.win.scroll(x, y, -amount)
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
		self, actions: list[ActionModel], ui_tree_builder=None
	) -> list[ActionResult]:
		"""Execute multiple actions"""
		results = []
		for i, action in enumerate(actions):
			results.append(await self.act(action, ui_tree_builder))
			await asyncio.sleep(0.5)

			logger.debug(f'Executed action {i + 1} / {len(actions)}')
			if results[-1].is_done or results[-1].error or i == len(actions) - 1:
				break

		return results

	@time_execution_sync('--act')
	async def act(self, action: ActionModel, ui_tree_builder=None) -> ActionResult:
		"""Execute an action"""
		try:
			for action_name, params in action.model_dump(exclude_unset=True).items():
				if params is not None:
					result = await self.registry.execute_action(action_name, params, ui_tree_builder=ui_tree_builder)
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
