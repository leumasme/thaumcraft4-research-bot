import ctypes
import ctypes.wintypes as wintypes
import pygetwindow as gw
import pyautogui as gui
from PIL.Image import Image
from typing import Tuple

from .config import Config
from .log import log

# Import Windows API
user32 = ctypes.WinDLL("user32", use_last_error=True)

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


def find_game(title: str) -> gw.Win32Window:
    windows = [
        win
        for win in gw.getWindowsWithTitle(title)
        if win.title.startswith(title)
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
