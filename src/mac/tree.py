# --- START OF FILE mac_use/mac/tree.py ---
import asyncio
import re
import numpy as np
# --- START OF FILE mac_use/mac/actions.py ---
import logging
from typing import Callable, Dict, List, Optional
import pyautogui
from PIL import Image, ImageDraw
import Cocoa
from ApplicationServices import AXUIElementPerformAction, AXUIElementSetAttributeValue, kAXPressAction, kAXValueAttribute
from Foundation import NSString
import time
# from mlx_use.mac.element import MacElementNode
import HIServices
logger = logging.getLogger(__name__)
from ApplicationServices import AXValueGetType, kAXValueCGPointType, kAXValueTypeCGSize, AXValueGetValue, kAXValueCGSizeType
from Quartz import CGPoint, CGSize
import Cocoa
import objc
from ApplicationServices import (
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXPressAction,
    kAXValueAttribute,
    AXUIElementCopyActionNames,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeNames,  # Newly added to retrieve all attribute names
    AXUIElementCreateApplication,
    kAXChildrenAttribute,
    kAXDescriptionAttribute,
    kAXErrorAPIDisabled,
    kAXErrorAttributeUnsupported,
    kAXErrorCannotComplete,
    kAXErrorFailure,
    kAXErrorIllegalArgument,
    kAXErrorSuccess,
    kAXMainWindowAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
    kAXWindowsAttribute,
)
from CoreFoundation import CFRunLoopAddSource, CFRunLoopGetCurrent, kCFRunLoopDefaultMode
from src.mac.element import MacElementNode
import Quartz.CoreGraphics as CG
from Foundation import NSArray, NSMutableArray
from PIL import ImageFont  # Add this import
from AppKit import NSScreen

def convert_nsarray(value):
    """Convert NSArray/NSMutableArray to Python list recursively"""
    if isinstance(value, (NSArray, NSMutableArray)):
        return [convert_nsarray(item) for item in value]
    return value

logger = logging.getLogger(__name__)


class MacUITreeBuilder:
    def __init__(self):
        self.highlight_index = 0
        self._element_cache = {}
        self._observers = {}
        self._processed_elements = set()
        self._current_app_pid = None
        self.max_depth = 30
        self.max_children = 250
        self._screenshot = None
        self._annotated_screenshot = None
        self.app_window = None
        self.window_count = 0

        # Define interactive actions we care about
        self.INTERACTIVE_ACTIONS = {
            'AXPress',            # Most buttons and clickable elements
            'AXShowMenu',         # Menu buttons
            'AXIncrement',        # Spinners/steppers
            'AXDecrement',
            'AXConfirm',         # Dialogs
            'AXCancel',
            'AXRaise',           # Windows
            'AXSetValue'         # Text fields/inputs
        }

        # Actions that require scrolling
        self.SCROLL_ACTIONS = {
            'AXScrollLeftByPage',
            'AXScrollRightByPage',
            'AXScrollUpByPage',
            'AXScrollDownByPage'
        }

    def _setup_observer(self, pid: int) -> bool:
        """Setup accessibility observer for an application"""
        return True  #  Temporarily always return True

    def _get_attribute(self, element: 'AXUIElement', attribute: str) -> any:
        """Safely get an accessibility attribute with error reporting"""
        try:
            error, value_ref = AXUIElementCopyAttributeValue(element, attribute, None)
            if error == kAXErrorSuccess:
                return value_ref
            elif error == kAXErrorAttributeUnsupported:
                # logger.debug(f"Attribute '{attribute}' is not supported for this element.")
                return None
            else:
                # logger.debug(f"Error getting attribute '{attribute}': {error}")
                return None
        except Exception as e:
            # logger.debug(f"Exception getting attribute '{attribute}': {str(e)}")
            return None

    def _get_actions(self, element: 'AXUIElement') -> List[str]:
        """Get available actions for an element with proper error handling"""
        try:
            error, actions = AXUIElementCopyActionNames(element, None)
            if error == kAXErrorSuccess and actions:
                # Convert NSArray to Python list
                return list(actions)
            return []
        except Exception as e:
            logger.debug(f'Error getting actions: {e}')
            return []

    def _get_all_attributes(self, element: 'AXUIElement') -> Dict[str, any]:
        """
        Retrieve all available attributes from an accessibility element.
        This uses AXUIElementCopyAttributeNames to get a list of all supported attributes,
        then fetches each attribute's value.
        """
        attributes = {}
        try:
            error, attribute_names = AXUIElementCopyAttributeNames(element, None)
            if error == kAXErrorSuccess and attribute_names:
                for attr in list(attribute_names):
                    attributes[attr] = self._get_attribute(element, attr)
        except Exception as e:
            logger.debug(f"Error retrieving all attributes: {e}")
        return attributes

    def _is_interactive(self, element: 'AXUIElement', role: str, actions: List[str]) -> bool:
        """Determine if an element is truly interactive based on its role and actions."""
        if not actions:
            return False

        # Check if element has any interactive actions
        has_interactive = any(action in self.INTERACTIVE_ACTIONS for action in actions)
        has_scroll = any(action in self.SCROLL_ACTIONS for action in actions)

        # Special handling for text input fields
        if 'AXSetValue' in actions and role == 'AXTextField':
            enabled = self._get_attribute(element, 'AXEnabled')
            return bool(enabled)

        # Special handling for buttons with AXPress
        if 'AXPress' in actions and role in ['AXButton', 'AXLink']:
            enabled = self._get_attribute(element, 'AXEnabled')
            return bool(enabled)

        return has_interactive or has_scroll

    async def _process_element(self, element: 'AXUIElement', pid: int, parent: Optional[MacElementNode] = None, depth: int = 0) -> Optional[MacElementNode]:
        """Process a single UI element"""
        element_identifier = str(element)

        if element_identifier in self._processed_elements:
            return None

        self._processed_elements.add(element_identifier)

        try:
            role = self._get_attribute(element, kAXRoleAttribute)
            if not role:
                return None

            actions = self._get_actions(element)

            # Create node with enhanced attributes
            node = MacElementNode(
                role=role,
                identifier=element_identifier,
                attributes={},
                is_visible=True, # it means accessible, but may not be on the screen
                on_screen=False,  # it means on the screen
                parent=parent,
                app_pid=pid,
            )
            node._element = element

            # Store the actions in the node's attributes for reference
            if actions:
                node.attributes['actions'] = actions

            title = self._get_attribute(element, kAXTitleAttribute)
            value = self._get_attribute(element, kAXValueAttribute)
            description = self._get_attribute(element, kAXDescriptionAttribute)
            is_enabled = self._get_attribute(element, 'AXEnabled')
            subrole = self._get_attribute(element, 'AXSubrole')
            if title:
                node.attributes['title'] = title
            if value:
                node.attributes['value'] = value
            if description:
                node.attributes['description'] = description
            if is_enabled is not None:
                node.is_visible = bool(is_enabled)
                node.attributes['enabled'] = bool(is_enabled)
            if subrole:
                node.attributes['subrole'] = subrole

            raw_pos  = self._convert_axvalue_to_point(self._get_attribute(element, 'AXPosition'))
            raw_size = self._convert_axvalue_to_size(self._get_attribute(element, 'AXSize'))

            # NEW: round each float to 3 dp before saving
            position = tuple(round(v, 3) for v in raw_pos)     # (x, y) → (x.xxx, y.yyy)
            size     = tuple(round(v, 3) for v in raw_size)
            x0, y0 = position
            w, h = size
            x0 = x0 + 0.1*w
            y0 = y0 + 0.1*h
            w = w * 0.8
            h = h * 0.8
            position = (x0, y0)  # Now stored as (x,y) tuple
            size = (w, h)        # Now stored as (w,h) tuple

            node.attributes.update({
                'position': position,  # Now stored as (x,y) tuple
                'size': size           # Now stored as (w,h) tuple
            })

            def is_visible(element):
                if not self.app_window:
                    return False
                # Element must have valid position/size data
                screen_width, screen_height = self._screenshot.size
                wx, wy = self.app_window['position']
                ww, wh = self.app_window['size']
                window_bounds = (wx, wy, wx + ww, wy + wh)

                pos = element.attributes.get('position')
                size = element.attributes.get('size')
                if not pos or not size:
                    return False

                x, y = pos
                w, h = size
                elem_right = x + w
                elem_bottom = y + h

                # 1. Check screen boundaries
                on_screen = not (
                    elem_right <= 0 or
                    x >= screen_width or
                    elem_bottom <= 0 or
                    y >= screen_height
                )
                if not on_screen:
                    return False

                # 2. Check window boundaries if available
                if window_bounds:
                    wx1, wy1, wx2, wy2 = window_bounds
                    window_overlap = (
                        x >= wx1-5 and
                        elem_right <= wx2+5 and
                        y >= wy1-5 and
                        elem_bottom <= wy2+5
                    )
                    if not window_overlap:
                        return False

                return True

            if is_visible(node):
                node.on_screen = True
            else:
                node.on_screen = False

            node.is_interactive = self._is_interactive(element, role, actions)
            important_attrs = ['title', 'value', 'description', 'enabled','position','size']
            should_add = False
            x0,y0 = node.attributes.get('position', (0, 0))
            w,h = node.attributes.get('size', (0, 0))
            x1 = x0 + w
            y1 = y0 + h
            if w > 0.005 and h > 0.005 and w< 0.4 and h < 0.4 and x0 >= 0 and y0 >= 0 and x1 <= 1 and y1 <= 1:
                for attr in important_attrs:
                    if attr in node.attributes and node.attributes[attr] is not None:
                        should_add = True
            if should_add:
                if node.is_interactive and node not in ['AXGroup', 'AXImage', 'AXSplitGroup', 'AXScrollArea']:
                    node.highlight_index = self.highlight_index
                    self._element_cache[self.highlight_index] = node
                    self.highlight_index += 1
                else:
                    node.highlight_index = None
                    self._element_cache[f'ctx_{element_identifier}'] = node

            # Process children
            children_ref = self._get_attribute(element, kAXChildrenAttribute)
            if children_ref and depth < self.max_depth:
                try:
                    children_count = len(list(children_ref))
                    if children_count > self.max_children:
                        logger.error(f"Max children limit ({self.max_children}) exceeded for element {role}. Found {children_count} children. Some elements will not be processed.")

                    children_list = convert_nsarray(children_ref)
                    for child in children_list:
                        child_node = await self._process_element(child, pid, node, depth + 1)
                        if child_node:
                            node.children.append(child_node)
                except Exception as e:
                    logger.warning(f"Error processing children: {e}")
            elif children_ref and depth >= self.max_depth:
                logger.error(f"Max depth limit ({self.max_depth}) reached for element {role}. Children at depth {depth} will not be processed.")

            return node

        except Exception as e:
            logger.error(f'Error processing element: {str(e)}')
            return None

    def cleanup(self):
        """Cleanup observers and release resources"""
        # Clear the element cache to prevent holding on to stale references
        self._element_cache.clear()
        # Clear processed elements set
        self._processed_elements.clear()
        # Reset highlight index
        self.highlight_index = 0
        # Reset current app PID
        self._current_app_pid = None

        # Force garbage collection to release any Objective-C references
        import gc
        gc.collect()

        # Log the cleanup
        logger.debug("MacUITreeBuilder cleanup completed: all references released")

    def reset_state(self):
        """Reset the state between major steps"""
        self.highlight_index = 0  # Reset index
        self._element_cache.clear()  # Clear cache
        self._processed_elements.clear()  # Clear processed set

        # Don't reset _current_app_pid here as it's needed for continuity between steps

        # Log the reset
        logger.debug("MacUITreeBuilder state reset")

    def capture_screenshot(self) -> Image.Image:
        """Capture a screenshot of the current screen"""
        try:
            logger.debug('Capturing screenshot............................................................')
            screenshot = pyautogui.screenshot()
            screenshot.thumbnail((screenshot.width // 2, screenshot.height // 2))
            self._screenshot = screenshot
            return self._screenshot
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None

    def _convert_axvalue_to_point(self, axvalue) -> Optional[tuple]:
        """Convert AXValue (CGPoint) to Python tuple (x, y)"""
        if axvalue and AXValueGetType(axvalue) == 1:
            axvalue = str(axvalue)
            pattern = r'x:([-+]?\d+\.?\d*)\s+y:([-+]?\d+\.?\d*)'
            match = re.search(pattern, axvalue)

            if match:
                # divide the coordinates by the screen size to normalize them
                x = float(match.group(1)) / pyautogui.size()[0]
                y = float(match.group(2)) / pyautogui.size()[1]
                return (x, y)
            else:
                logger.debug(f'Failed to match pattern: {axvalue}')
        return None

    def _convert_axvalue_to_size(self, axvalue) -> Optional[tuple]:
        """Convert AXValue (CGSize) to Python tuple (width, height)"""
        if axvalue and AXValueGetType(axvalue) == 2:
            axvalue = str(axvalue)
            pattern = r'w:([\d.]+)\s+h:([\d.]+)'
            match = re.search(pattern, axvalue)

            if match:
                width = float(match.group(1)) / pyautogui.size()[0]
                height = float(match.group(2)) / pyautogui.size()[1]
                return (width, height)
            else:
                logger.debug(f'Failed to match pattern: {axvalue}')
        return None

    def annotate_screenshot(self, root: MacElementNode) -> Optional[Image.Image]:
        if not self._screenshot:
            logger.debug('No screenshot available to annotate.')
            return None

        annotated = self._screenshot.copy()
        draw = ImageDraw.Draw(annotated)
        screen_width, screen_height = self._screenshot.size
        font_size = 16  # Increase font size for visibility
        font = ImageFont.load_default().font_variant(size=font_size)  # [1,4](@ref)
        color_palette = ['red', 'blue', 'green', 'yellow', 'purple']
        # Get main window boundaries
        window_bounds = None
        try:
            if self.window_count == 1:
                wx, wy = self.app_window['position']
                wx *= screen_width
                wy *= screen_height
                ww, wh = self.app_window['size']
                ww *= screen_width
                wh *= screen_height
                window_bounds = (wx, wy, wx + ww, wy + wh)
        except:
            ww, wh = screen_width, screen_height
            window_bounds = (0, 0, ww, wh)
            logger.error('Error getting window bounds')

        def process_element(element):
            try:
                if element.on_screen and element.highlight_index is not None:
                    x, y = element.attributes['position']
                    x *= screen_width
                    y *= screen_height
                    w, h = element.attributes['size']
                    w *= screen_width
                    h *= screen_height
                    wx1, wy1, wx2, wy2 = window_bounds
                    right = min(x + w, wx2)
                    x = max(x,wx1)
                    bottom = min(y + h, wy2)
                    y = max(y, wy1)
                    # Draw annotation
                    number = int(element.highlight_index)
                    color = color_palette[number % len(color_palette)]
                    draw.rectangle([x, y, right, bottom], width=1, outline=color)

                    text = str(number)
                    text_bbox = draw.textbbox((0, 0), text, font=font)  # Returns (left, top, right, bottom)
                    text_height = text_bbox[3] - text_bbox[1]
                    draw.text((x, y), text, fill=color, font=font)
            except Exception as e:
                # logger.warning(f"Annotation error: {str(e)}")
                pass

            for child in element.children:
                process_element(child)

        if root:
            logger.debug(f'Starting annotation from root: {root.role}')
            process_element(root)
        self._annotated_screenshot = annotated
        return annotated

    def get_vision_context(self) -> dict:
        """Get both UI tree and vision information"""
        if not self._annotated_screenshot:
            return None

        return {
            'screenshot': self._annotated_screenshot,
            # 'ui_tree': self._element_cache
        }

    async def build_tree(self, pid: Optional[int] = None) -> Optional[MacElementNode]:
        """Build UI tree for a specific application"""
        try:
            # Reset processed elements and cache before building new tree
            self._processed_elements.clear()
            self._element_cache.clear()
            self.highlight_index = 0

            if pid is None and self._current_app_pid is None:
                logger.debug('No app is currently open - waiting for app to be launched')
                raise ValueError('No app is currently open')

            if pid is not None:
                # Always update with the latest PID if provided
                self._current_app_pid = pid

            # Verify the process is still running
            import subprocess
            try:
                result = subprocess.run(['ps', '-p', str(self._current_app_pid)], capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Process with PID {self._current_app_pid} is no longer running")
                    self._current_app_pid = None
                    self.cleanup()
                    return None
            except Exception as e:
                logger.error(f"Error checking process status: {e}")

            if not self._setup_observer(self._current_app_pid):
                logger.warning('Failed to setup accessibility observer')
                return None

            logger.debug(f'Creating AX element for pid {self._current_app_pid}')
            app_ref = AXUIElementCreateApplication(self._current_app_pid)

            logger.debug('Testing accessibility permissions (Role)...')
            error, role_attr = AXUIElementCopyAttributeValue(app_ref, kAXRoleAttribute, None)
            if error == kAXErrorSuccess:
                logger.debug(f'Successfully got role attribute: ({error}, {role_attr})')
            else:
                logger.error(f'Error getting role attribute: {error}')
                if error == kAXErrorAPIDisabled:
                    logger.error('Accessibility is not enabled. Please enable it in System Settings.')
                elif error == -25204:
                    logger.error(f'Error -25204: Accessibility connection failed. The app may have been closed or restarted.')
                    # Reset current app PID as it's no longer valid
                    self._current_app_pid = None
                    # Force cleanup to release any hanging references
                    self.cleanup()
                return None

            root = MacElementNode(
                role='application',
                identifier=str(app_ref),
                attributes={},
                is_visible=True,
                app_pid=self._current_app_pid,
                on_screen=True
            )
            root._element = app_ref

            logger.debug('Trying to get the main window...')
            error, main_window_ref = AXUIElementCopyAttributeValue(app_ref, kAXMainWindowAttribute, None)
            if error == '-25212':
                return None, "Window not found"
            if error != kAXErrorSuccess or not main_window_ref:
                logger.warning(f'Could not get main window (error: {error}), trying fallback attribute AXWindows')
                error, windows = AXUIElementCopyAttributeValue(app_ref, kAXWindowsAttribute, None)
                if error == kAXErrorSuccess and windows:
                    try:
                        windows_list = list(windows)
                        if windows_list:
                            main_window_ref = windows_list[0]
                            logger.debug(f'Fallback: selected first window from AXWindows: {main_window_ref}')
                        else:
                            logger.warning("Fallback: AXWindows returned an empty list")
                    except Exception as e:
                        logger.error(f'Failed to iterate over AXWindows: {e}')
                else:
                    logger.error(f'Fallback failed: could not get AXWindows (error: {error})')

            if main_window_ref:
                logger.debug(f'Found main window: {main_window_ref}')
                window_node = await self._process_element(main_window_ref, self._current_app_pid, root)
                if window_node:
                    root.children.append(window_node)
                # Now that we have the main window node, store its position and size in self.app_window
                main_pos = window_node.attributes.get('position')
                main_size = window_node.attributes.get('size')
                if main_pos and main_size:
                    self.app_window = {
                        'position': main_pos,
                        'size': main_size
                    }
                    self.window_count = 1
            else:
                logger.error('Could not determine a main window for the application.')

            return root

        except Exception as e:
            if 'No app is currently open' not in str(e):
                logger.error(f'Error building tree: {str(e)}')
                import traceback
                traceback.print_exc()
            return None
