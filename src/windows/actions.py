import asyncio
import logging
import time
from typing import Optional, Dict, Any, Tuple
import pyautogui
import win32gui
import win32con
import win32api
import win32clipboard


logger = logging.getLogger(__name__)


class WindowsActions:
    """Windows-specific UI actions using Windows API and PyAutoGUI"""
    
    def __init__(self):
        pass

    def getscreen_size(self) -> Tuple[int, int]:
        """Get the size of the primary screen"""
        try:
            screen_width, screen_height = pyautogui.size()
            return screen_width, screen_height
        except Exception as e:
            logger.error(f"Error getting screen size: {e}")
            return 1920, 1080
        
    async def click(self, x: float, y: float, button: str = 'left') -> bool:
        """Click at specified coordinates"""
        pos_x = self.getscreen_size()[0] * x
        pos_y = self.getscreen_size()[1] * y
        try:
            if button == 'left':
                pyautogui.click(pos_x, pos_y)
            elif button == 'right':
                pyautogui.rightClick(pos_x, pos_y)
            elif button == 'double':
                pyautogui.doubleClick(pos_x, pos_y)

            await asyncio.sleep(0.1)  # Small delay after click
            return True
        except Exception as e:
            logger.error(f"Error clicking at ({x}, {y}): {e}")
            return False

    async def drag(self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float = 0.5) -> bool:
        """Drag from start to end position"""
        pos_start_x = self.getscreen_size()[0] * start_x
        pos_start_y = self.getscreen_size()[1] * start_y
        pos_end_x = self.getscreen_size()[0] * end_x
        pos_end_y = self.getscreen_size()[1] * end_y
        try:
            pyautogui.drag(pos_end_x - pos_start_x, pos_end_y - pos_start_y, duration=duration, button='left')
            return True
        except Exception as e:
            logger.error(f"Error dragging from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}")
            return False

    async def scroll(self, x: float, y: float, clicks: int) -> bool:
        """Scroll at specified position"""
        pos_x = self.getscreen_size()[0] * x
        pos_y = self.getscreen_size()[1] * y
        try:
            pyautogui.scroll(clicks, x=pos_x, y=pos_y)
            return True
        except Exception as e:
            logger.error(f"Error scrolling at ({x}, {y}): {e}")
            return False
    
    async def type_text(self, text: str) -> bool:
        """
        Type text using clipboard method to handle both English and Chinese characters
        This method bypasses input method editors (IMEs) and works reliably
        """
        try:
            if not text:
                return True
                
            # Save current clipboard content
            original_clipboard = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    original_clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except:
                pass
            
            # Set text to clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            
            # Paste using Ctrl+V
            await asyncio.sleep(0.05)  # Small delay
            pyautogui.hotkey('ctrl', 'v')
            await asyncio.sleep(0.1)  # Wait for paste to complete
            
            # Restore original clipboard content
            if original_clipboard is not None:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, original_clipboard)
                    win32clipboard.CloseClipboard()
                except:
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Error typing text '{text}': {e}")
            return False
    
    async def press_key(self, key: str) -> bool:
        """Press a single key"""
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            logger.error(f"Error pressing key '{key}': {e}")
            return False

    async def press_hotkey(self, key1: str, key2: str, key3: Optional[str] = None) -> bool:
        """Press a combination of keys"""
        try:
            if key3 is not None:
                pyautogui.keyDown(key1)
                pyautogui.keyDown(key2)
                pyautogui.keyDown(key3)
                pyautogui.keyUp(key3)
                pyautogui.keyUp(key2)
                pyautogui.keyUp(key1)
            else:
                pyautogui.keyDown(key1)
                pyautogui.keyDown(key2)
                pyautogui.keyUp(key2)
                pyautogui.keyUp(key1)    
            return True
        except Exception as e:
            logger.error(f"Error pressing hotkey {key1, key2, key3}: {e}")
            return False

    async def take_screenshot(self, save_path: Optional[str] = None) -> bool:
        """Take a screenshot"""
        try:
            screenshot = pyautogui.screenshot()
            if save_path:
                screenshot.save(save_path)
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
    
    async def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        try:
            return pyautogui.position()
        except Exception as e:
            logger.error(f"Error getting mouse position: {e}")
            return (0, 0)

    async def move_mouse(self, x: float, y: float, duration: float = 0.0) -> bool:
        """Move mouse to specified position"""
        pos_x = self.getscreen_size()[0] * x
        pos_y = self.getscreen_size()[1] * y
        try:
            pyautogui.moveTo(pos_x, pos_y, duration=duration)
            return True
        except Exception as e:
            logger.error(f"Error moving mouse to ({x}, {y}): {e}")
            return False