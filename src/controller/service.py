import asyncio
import logging
from typing import Optional
import subprocess
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
	MoveToAction,
	
)


from src.mac.actions import type_into, press, _scroll_invisible_at_position, move_to, left_click_pixel, right_click_pixel, press_combination, drag_pixel
from src.mac.tree import MacUITreeBuilder
from src.utils import time_execution_async, time_execution_sync

from pypinyin import pinyin, Style

import re
from ApplicationServices import AXUIElementCreateApplication, AXUIElementCopyAttributeValue
from rapidfuzz import process as rapidfuzz_process
from rapidfuzz import fuzz as rapidfuzz_fuzz
logger = logging.getLogger(__name__)
import time

def fuzzy_find_pid(user_norm: str, workspace) -> Optional[int]:
    """
    Return a PID for the best matching running app (with visible window),
    or None if no good match found.
    """
    running_apps = workspace.runningApplications()
    logger.debug(f"Running apps: {running_apps}")

    candidate_map = {}
    for app in running_apps:
        pid = app.processIdentifier()
        bundle_id = app.bundleIdentifier() or ""
        name = app.localizedName() or ""

        norm_bundle_id = normalize_for_matching(bundle_id)
        norm_name = normalize_for_matching(name)

        if norm_bundle_id:
            key = f"{norm_bundle_id}:{pid}"
            candidate_map[key] = (pid, app)

        if norm_name:
            key = f"{norm_name}:{pid}"
            candidate_map[key] = (pid, app)

    if not candidate_map:
        logger.debug("No candidate apps found.")
        return None

    # 1) First try ratio
    ratio_match = rapidfuzz_process.extractOne(
        user_norm,
        candidate_map.keys(),
        scorer=rapidfuzz_fuzz.ratio
    )

    best_candidate_key = None
    best_confidence = 0

    if ratio_match:
        tmp_key, tmp_conf, _ = ratio_match
        logger.debug(f"Ratio best match: '{user_norm}' -> '{tmp_key}' (conf={tmp_conf})")
        # If ratio-based confidence is under 60, let's do a fallback partial_ratio
        if tmp_conf >= 80:
            best_candidate_key, best_confidence = tmp_key, tmp_conf
        else:
            logger.debug("Ratio confidence too low, falling back to partial_ratio.")
    else:
        logger.debug("No match using ratio, falling back to partial_ratio.")

    # 2) If still nothing or too low from ratio, do partial_ratio
    if not best_candidate_key:
        partial_match = rapidfuzz_process.extractOne(
            user_norm,
            candidate_map.keys(),
            scorer=rapidfuzz_fuzz.partial_ratio
        )
        if not partial_match:
            logger.debug("No fuzzy matches using partial_ratio either.")
            return None
        best_candidate_key, best_confidence, _ = partial_match
        logger.debug(
            f"Partial best match: '{user_norm}' -> '{best_candidate_key}' (conf={best_confidence})"
        )

    # Final check for confidence
    if best_confidence < 80:
        logger.debug(f"Best confidence only {best_confidence}, returning None.")
        return None

    # Now get the (pid, app)
    pid, candidate_app = candidate_map[best_candidate_key]

    # Check if app has visible windows
    if has_app_windows(pid):
        logger.info(
            f"Using best fuzzy match => PID: {pid}, "
            f"{candidate_app.bundleIdentifier()} / {candidate_app.localizedName()}, "
            f"confidence={best_confidence}, windows=YES"
        )
        return pid

    # If no windows, return None
    return None


def chinese_to_pinyin(s: str) -> str:
    # Convert each character to pinyin, no tones, join with space
    return " ".join(syll[0] for syll in pinyin(s, style=Style.NORMAL))

def normalize_for_matching(s: str) -> str:
    # If it has Chinese, convert to pinyin
    if re.search(r"[\u4e00-\u9fff]", s):
        s = chinese_to_pinyin(s)
    # Lowercase, remove punctuation/spaces
    s = s.lower()
    s = re.sub(r"[^\w]", "", s)
    return s
def has_app_windows(pid: int) -> bool:
    # Create an accessibility element for that PID
    app_ref = AXUIElementCreateApplication(pid)
    # Attempt to get list of windows
    windows = AXUIElementCopyAttributeValue(app_ref, "AXWindows", None)
    if windows is not None and len(windows) > 0:
        return True
    return False

class Controller:
	def __init__(
		self,
		exclude_actions: list[str] = [],
	):
		self.exclude_actions = exclude_actions
		self.registry = Registry(exclude_actions)
		self._register_default_actions()
		self.mac_tree_builder = MacUITreeBuilder()

	def _register_default_actions(self):
		"""Register all default cua actions"""

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

			# Attempt launching via NSWorkspace
			success = workspace.launchApplication_(user_input)
			if not success:
				msg = f"❌ Failed to launch '{user_input}'"
				logger.error(msg)
				return ActionResult(extracted_content=msg, error=msg)

			# Give macOS time to start the app
			await asyncio.sleep(1)
			pid = None
			# check if the pid is an integer or a string of integer
			if isinstance(pid, str) and pid.isdigit():
				pid = int(pid)
			elif not isinstance(pid, int):
				pid = None
			
			if not pid:
				msg = f"❌ Could not find a matching PID for '{user_input}'"
				logger.error(msg)
				user_norm = normalize_for_matching(user_input)
				pid = fuzzy_find_pid(user_norm, workspace)

				if not pid:
					try:
						logger.debug(f'Attempting to find PID using pgrep for app: {app_name}')
						result = subprocess.run(
							['pgrep', '-i', app_name],
							capture_output=True,
							text=True
						)
						if result.returncode == 0 and result.stdout.strip():
							# pgrep might return multiple PIDs, take the first one
							pid = int(result.stdout.strip().split('\n')[0])
							logging.debug(f'Found PID using pgrep: {pid}')
						else:
							logging.error(f'❌ Failed to find PID for app: {app_name} with pgrep')
					except Exception as e:
						logging.error(f'❌ Error while running pgrep: {str(e)}')
				if not pid:
					msg = f"❌ Could not find a matching PID for '{user_input}'"
					logger.error(msg)
					return ActionResult(extracted_content=msg, error=msg)

			success_msg = f"✅ Launched {user_input}, PID={pid}"
			logger.info(success_msg)
			return ActionResult(extracted_content=success_msg, current_app_pid=pid)
		
		@self.registry.action(
			'Run an AppleScript',
			param_model=AppleScriptAction
		)
		async def run_apple_script(script: str):
			logger.debug(f'Running AppleScript: {script}')
			
			# Wrap the original script in error handling and return value logic
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
			# The key is Key.enter, but what i need is the string "enter"
			key_press = key.replace("Key.", "")
			press_successful = await press(key_press)
			if press_successful:
				logging.info(f'✅ pressed key code: {key}')
				return ActionResult(extracted_content=f'Successfully press keyboard with key code {key}')
			
		@self.registry.action(
			'Press Multiple Hotkey',
			param_model=PressCombinedAction,
		)
		async def multi_Hotkey(key1: str, key2: str, key3: str):
			def clean_key(raw: str | None) -> str | None:
				"""Strip the `Key.` prefix and any stray quote marks."""
				if raw is None:
					return None
				return raw.replace("Key.", "").strip("'\"")   # handles 't', "t", Key.'t', etc.
			key1 = clean_key(key1)
			key2 = clean_key(key2)
			key3 = clean_key(key3)
			key_map = {
				'cmd': 'command',
				'delete': 'backspace'
			}
			# 映射键名
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
			param_model=RightClickPixel,
			requires_mac_builder=False
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
			param_model=LeftClickPixel,
			requires_mac_builder=False
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
			param_model=DragAction,
			requires_mac_builder=False
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
				requires_mac_builder=False
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
		async def scroll_up(position, dx: int = -20, dy: int = 20):
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
		async def scroll_down(position, dx: int = -20, dy: int = 20):
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
		self, actions: list[ActionModel], mac_tree_builder: MacUITreeBuilder, action_valid: bool = True
	) -> list[ActionResult]:
		"""Execute multiple actions"""
		results = []
		if action_valid:
			for i, action in enumerate(actions):
				results.append(await self.act(action, mac_tree_builder))
				await asyncio.sleep(0.5)

				logger.debug(f'Executed action {i + 1} / {len(actions)}')
				if results[-1].is_done or results[-1].error or i == len(actions) - 1:
					break

			return results
		else:
			return [ActionResult(error="Invalid action, index is out of the UI Tree. Please use the screenshot to determine the correct pixel to act on.",include_in_memory=True)]

	@time_execution_sync('--act')
	async def act(self, action: ActionModel, mac_tree_builder: MacUITreeBuilder) -> ActionResult:
		"""Execute an action"""
		try:
			for action_name, params in action.model_dump(exclude_unset=True).items():
				if params is not None:
					result = await self.registry.execute_action(action_name, params, mac_tree_builder=mac_tree_builder)
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
