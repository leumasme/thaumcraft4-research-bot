import ctypes
import ctypes.wintypes as wintypes
import pygetwindow as gw
import pyautogui as gui
from PIL.Image import Image
from typing import Tuple

from ..utils.log import log

# Import necessary Windows API functions and types
user32 = ctypes.WinDLL("user32", use_last_error=True)

# Define constants
GWL_STYLE = -16
GWL_EXSTYLE = -20


def resize_window_to_content_size(
    window: gw.Win32Window, content_width: int, content_height: int
) -> None:
    hwnd = window._hWnd
    rect = wintypes.RECT()

    # Get the current window rect to determine style
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())

    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

    # Desired content area size
    rect.right = rect.left + content_width
    rect.bottom = rect.top + content_height

    # Adjust the rectangle to include the window frame
    user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, ex_style)

    # Calculate the total window width and height
    new_width = rect.right - rect.left
    new_height = rect.bottom - rect.top

    # Resize the window
    user32.SetWindowPos(hwnd, None, rect.left, rect.top, new_width, new_height, 0)


def screenshot_window(window: gw.Win32Window) -> Tuple[Image, Tuple[int, int]]:
    hwnd = window._hWnd
    client_rect = wintypes.RECT()

    # Get the client area of the window
    if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
        raise ctypes.WinError(ctypes.get_last_error())

    # Convert client coordinates to screen coordinates
    top_left = wintypes.POINT(client_rect.left, client_rect.top)
    bottom_right = wintypes.POINT(client_rect.right, client_rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(top_left))
    user32.ClientToScreen(hwnd, ctypes.byref(bottom_right))

    # Calculate the width and height
    width = bottom_right.x - top_left.x
    height = bottom_right.y - top_left.y

    # Take a screenshot of the specified region
    image = gui.screenshot(region=(top_left.x, top_left.y, width, height))
    return (image.convert("RGB"), (top_left.x, top_left.y))


def find_game() -> gw.Win32Window:
    windows = [
        win
        for win in gw.getWindowsWithTitle("GT: New Horizons")
        if win.title.startswith("GT: New Horizons")
    ]
    if len(windows) != 1:
        for window in windows:
            log.error(window)
        raise Exception("Wrong number of game windows: " + str(len(windows)))
    return windows[0]


def add_offset(base: Tuple[int, int], coord: Tuple[int, int]) -> Tuple[int, int]:
    bx, by = base
    cx, cy = coord
    return (bx + cx, by + cy)
