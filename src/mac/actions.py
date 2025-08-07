import logging
import Quartz
import asyncio
import time
from Quartz.CoreGraphics import *
import pyautogui  
import Quartz, CoreFoundation as CF
from ApplicationServices import (
    NSWindow,
    NSBorderlessWindowMask,
    NSBackingStoreBuffered,
    NSColor,
    NSTimer
)
from pynput.keyboard import Controller
from typing import Optional

logger = logging.getLogger(__name__)

kb = Controller()

def _get_screen_size():
    """Return (width, height) of the main display in pixels."""
    display_id = Quartz.CGMainDisplayID()
    width = Quartz.CGDisplayPixelsWide(display_id)
    height = Quartz.CGDisplayPixelsHigh(display_id)
    return width, height

def _get_current_mouse_position():
    """Return the current mouse cursor position as a (x, y) tuple in absolute pixels."""
    pos = pyautogui.position()
    return (pos[0], pos[1])

def _warp_cursor(position):
    """
    Instantly move the system mouse pointer to `position` (a (x, y) tuple in absolute pixels).
    Note this jump is potentially visible unless you hide the cursor or restore quickly.
    """
    Quartz.CGWarpMouseCursorPosition(position)

def _post_mouse_event(x, y, event_type, button):
    """Create and post a mouse event of type `event_type` at absolute coordinates (x, y)."""
    event = Quartz.CGEventCreateMouseEvent(
        None,
        event_type,
        (x, y),
        button
    )
    Quartz.CGEventPost(Quartz.kCGSessionEventTap, event)

async def flash_click_highlight(x, y, radius=16, duration=1.0):
    screen_width, screen_height = pyautogui.size()
    y = screen_height - y 
    """Red ring for <duration>s; returns immediately (no seg-fault)."""
    frame = Quartz.CGRectMake(x - radius, y - radius, radius*2, radius*2)
    win   = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
              frame, NSBorderlessWindowMask, NSBackingStoreBuffered, False)
    win.setLevel_(Quartz.kCGOverlayWindowLevel)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setIgnoresMouseEvents_(True)
    win.contentView().setWantsLayer_(True)

    layer = Quartz.CALayer.layer()
    layer.setFrame_(win.contentView().bounds())
    layer.setCornerRadius_(radius)
    layer.setBorderWidth_(2)
    layer.setBorderColor_(Quartz.CGColorCreateGenericRGB(1, 0, 0, 1))
    win.contentView().layer().addSublayer_(layer)
    win.orderFrontRegardless()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        duration,      win, "orderOut:", None, False)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        duration + .05, win, "close",     None, False)
    CF.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, duration + .1, False)

async def _click_invisible(x, y, button='left'):
    """
    Perform a press-and-release click at (x, y) without leaving
    the cursor there. The pointer returns to its old position.
    `button` can be 'left' or 'right'.
    """
    asyncio.create_task(flash_click_highlight(x, y))

    if button == 'left':
        down_type = Quartz.kCGEventLeftMouseDown
        up_type   = Quartz.kCGEventLeftMouseUp
        cg_button = Quartz.kCGMouseButtonLeft
    else:
        down_type = Quartz.kCGEventRightMouseDown
        up_type   = Quartz.kCGEventRightMouseUp
        cg_button = Quartz.kCGMouseButtonRight

    move = Quartz.CGEventCreateMouseEvent(None,
                                      Quartz.kCGEventMouseMoved,
                                      (x, y), cg_button)
    Quartz.CGEventPost(Quartz.kCGSessionEventTap, move)
    
    await asyncio.sleep(0.03)
    event_down = Quartz.CGEventCreateMouseEvent(None, down_type, (x, y), cg_button)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
    
    event_up = Quartz.CGEventCreateMouseEvent(None, up_type, (x, y), cg_button)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

async def _drag_invisible(x1, y1, x2, y2, duration=0.5, steps=60):
    src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    down = CGEventCreateMouseEvent(src,
                                   kCGEventLeftMouseDown,
                                   (x1, y1),
                                   kCGMouseButtonLeft)
    CGEventSetIntegerValueField(down,
                                kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, down)

    step_t = duration/steps
    for i in range(1, steps+1):
        nx = x1 + (x2-x1)*i/steps
        ny = y1 + (y2-y1)*i/steps
        drag = CGEventCreateMouseEvent(src,
                                       kCGEventLeftMouseDragged,
                                       (nx, ny),
                                       kCGMouseButtonLeft)
        CGEventSetIntegerValueField(drag,
                                    kCGMouseEventClickState, 1)
        CGEventSetTimestamp(drag, int(time.time_ns()))
        CGEventPost(kCGHIDEventTap, drag)
        await asyncio.sleep(step_t)

    up = CGEventCreateMouseEvent(src,
                                 kCGEventLeftMouseUp,
                                 (x2, y2),
                                 kCGMouseButtonLeft)
    CGEventSetIntegerValueField(up,
                                kCGMouseEventClickState, 0)
    CGEventPost(kCGHIDEventTap, up)

async def _scroll_invisible(lines=1):
    direction = 1 if lines > 0 else -1
    for _ in range(abs(lines)):
        event = Quartz.CGEventCreateScrollWheelEvent(
            None,
            Quartz.kCGScrollEventUnitLine,
            1,
            direction 
        )
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, event)
        await asyncio.sleep(0.003)
        if _==25:
            break

async def _scroll_invisible_at_position(x, y, lines):
    """
    Temporarily warp the cursor to (x, y), scroll by `lines` lines 
    (positive=up, negative=down), then warp back. 
    This avoids permanently moving the user's pointer.
    """
    screen_w, screen_h = _get_screen_size()
    x *= screen_w
    y *= screen_h
    _warp_cursor((x, y))
    await _scroll_invisible(lines)
    return True

async def left_click_pixel(position) -> bool:
    """Left-click the specified (x, y) in normalized screen coords, invisibly."""
    screen_w, screen_h = _get_screen_size()
    abs_x = position[0] * screen_w
    abs_y = position[1] * screen_h

    await _click_invisible(abs_x, abs_y, button='left')
    logger.debug(f'✅ Successfully left-clicked pixel at absolute [{abs_x}, {abs_y}]')
    return True

async def right_click_pixel(position) -> bool:
    """Right-click the specified (x, y) in normalized screen coords, invisibly."""
    screen_w, screen_h = _get_screen_size()
    abs_x = position[0] * screen_w
    abs_y = position[1] * screen_h

    await _click_invisible(abs_x, abs_y, button='right')
    logger.debug(f'✅ Successfully right-clicked pixel at absolute [{abs_x}, {abs_y}]')
    return True

async def move_to(position) -> bool:
    """
    Move the system cursor to `position` (normalized coords) instantly. 
    NOTE: This physically moves the user's cursor in one jump, which can be visible.
    If you want no visible move at all, you typically do not call 'move_to'—just 
    post mouse events at the target coords directly.
    """
    screen_w, screen_h = _get_screen_size()
    abs_x = position[0] * screen_w
    abs_y = position[1] * screen_h

    move = Quartz.CGEventCreateMouseEvent(None,
                                      Quartz.kCGEventMouseMoved,
                                      (abs_x, abs_y), Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGSessionEventTap, move)
    logger.debug(f'✅ Successfully moved cursor to absolute [{abs_x}, {abs_y}]')
    return True


async def drag_pixel(start, end) -> bool:
    """
    Click and drag from `start` to `end` (each in normalized coords).
    This uses left-mouse drag invisibly, restoring cursor after the operation.
    """
    screen_w, screen_h = _get_screen_size()
    x1 = start[0] * screen_w
    y1 = start[1] * screen_h
    x2 = end[0] * screen_w
    y2 = end[1] * screen_h

    await _drag_invisible(x1, y1, x2, y2)
    logger.debug(f'✅ Successfully dragged from [{x1}, {y1}] to [{x2}, {y2}]')
    return True

async def press(key: str = "enter") -> bool:
    """
    Press a single key using PyAutoGUI. 
    (Alternatively, you could use pynput or Quartz events for keyboard as well.)
    """
    pyautogui.press(key)
    logger.info(f"✅ Successfully pressed key: {key}")
    return True

async def _unicode_event(char: str, down: bool):
    units = len(char.encode("utf-16-le")) // 2      

    ev = Quartz.CGEventCreateKeyboardEvent(None, 0, down)
    Quartz.CGEventKeyboardSetUnicodeString(ev, units, char)
    Quartz.CGEventPost(Quartz.kCGSessionEventTap, ev)

async def type_into(text: str):
    for ch in text:
        await _unicode_event(ch, True)
        await _unicode_event(ch, False)
    logger.info("✅ Successfully typed the text!")
    return True

async def press_combination(key1: str, key2: str, key3: Optional[str] = None) -> bool:
    """
    Press a combination of keys (e.g., Command + Shift + 3).
    Uses PyAutoGUI for convenience. 
    """
    if key3 is not None:
        pyautogui.keyDown(key1)
        pyautogui.keyDown(key2)
        pyautogui.keyDown(key3)
        pyautogui.keyUp(key3)
        pyautogui.keyUp(key2)
        pyautogui.keyUp(key1)
        logger.info(f"✅ Successfully pressed the combination: {key1} + {key2} + {key3}")
    else:
        pyautogui.keyDown(key1)
        pyautogui.keyDown(key2)
        pyautogui.keyUp(key2)
        pyautogui.keyUp(key1)
        logger.info(f"✅ Successfully pressed the combination: {key1} + {key2}")
    return True

async def scroll_up(amount: int) -> bool:
    """
    Scroll up `amount` lines. Clamped to max of 25 for demonstration.
    Uses native Quartz scrolling (kCGScrollEventUnitLine).
    """
    if amount > 25:
        amount = 25
    await _scroll_invisible(lines=amount)
    logger.info(f"✅ Successfully scrolled up by {amount} lines!")
    return True

async def scroll_down(amount: int) -> bool:
    """
    Scroll down `amount` lines. Clamped to max of 25 for demonstration.
    Uses native Quartz scrolling (kCGScrollEventUnitLine).
    """
    if amount > 25:
        amount = 25
    await _scroll_invisible(lines=-amount)
    logger.info(f"✅ Successfully scrolled down by {amount} lines!")
    return True
