"""
Cross-platform window management for screenshot and window finding.
Supports Windows (using Win32 API) and Linux (using python-xlib and ewmh).
"""

import sys
from typing import Tuple, Any

import pyautogui as gui
from PIL.Image import Image

from .log import log

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

# Platform-specific imports
if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes as wintypes
    import pygetwindow as gw  # type: ignore[import-untyped]

    # Import Windows API
    user32 = ctypes.WinDLL("user32", use_last_error=True)


class LinuxWindow:
    """
    A wrapper class for Linux windows that mimics the pygetwindow interface.
    Uses python-xlib and ewmh for X11 window management.
    """

    def __init__(self, window_id: int, display, ewmh_instance):
        self._window_id = window_id
        self._display = display
        self._ewmh = ewmh_instance
        self._window = display.create_resource_object("window", window_id)

    @property
    def title(self) -> str:
        """Get the window title."""
        try:
            name = self._ewmh.getWmName(self._window)
            if name:
                return (
                    name
                    if isinstance(name, str)
                    else name.decode("utf-8", errors="replace")
                )
            # Fallback to WM_NAME
            name = self._window.get_wm_name()
            if name:
                return name if isinstance(name, str) else str(name)
            return ""
        except Exception as e:
            log.debug(f"Could not get window title: {e}")
            return ""

    @property
    def isActive(self) -> bool:
        """Check if the window is currently active/focused."""
        try:
            active = self._ewmh.getActiveWindow()
            return active is not None and active.id == self._window_id
        except Exception:
            return False

    @property
    def isMaximized(self) -> bool:
        """Check if the window is maximized."""
        try:
            states = self._ewmh.getWmState(self._window, str=True)
            if states:
                return (
                    "_NET_WM_STATE_MAXIMIZED_VERT" in states
                    and "_NET_WM_STATE_MAXIMIZED_HORZ" in states
                )
            return False
        except Exception:
            return False

    @property
    def left(self) -> int:
        """Get the left edge of the window."""
        geom = self._get_geometry()
        return geom[0]

    @property
    def top(self) -> int:
        """Get the top edge of the window."""
        geom = self._get_geometry()
        return geom[1]

    @property
    def width(self) -> int:
        """Get the width of the window."""
        geom = self._get_geometry()
        return geom[2]

    @property
    def height(self) -> int:
        """Get the height of the window."""
        geom = self._get_geometry()
        return geom[3]

    def _get_geometry(self) -> Tuple[int, int, int, int]:
        """Get window geometry as (x, y, width, height) in screen coordinates."""
        try:
            # Get the window geometry
            geom = self._window.get_geometry()

            # Translate coordinates to root window (screen coordinates)
            root = self._display.screen().root
            coords = root.translate_coords(self._window, 0, 0)

            # Account for window decorations by getting the frame extents
            try:
                from Xlib import Xatom

                frame_extents_atom = self._display.intern_atom("_NET_FRAME_EXTENTS")
                frame_extents = self._window.get_full_property(
                    frame_extents_atom, Xatom.CARDINAL
                )
                if frame_extents and frame_extents.value:
                    left_border, right_border, top_border, bottom_border = (
                        frame_extents.value[:4]
                    )
                    # The translate_coords already gives us the content area position
                    return (coords.x, coords.y, geom.width, geom.height)
            except Exception:
                pass

            return (coords.x, coords.y, geom.width, geom.height)
        except Exception as e:
            log.error(f"Could not get window geometry: {e}")
            return (0, 0, 800, 600)

    def activate(self):
        """Bring the window to the foreground and focus it."""
        try:
            self._ewmh.setActiveWindow(self._window)
            self._ewmh.display.flush()
        except Exception as e:
            log.error(f"Could not activate window: {e}")

    def maximize(self):
        """Maximize the window."""
        try:
            # Add maximized states
            self._ewmh.setWmState(self._window, 1, "_NET_WM_STATE_MAXIMIZED_VERT")
            self._ewmh.setWmState(self._window, 1, "_NET_WM_STATE_MAXIMIZED_HORZ")
            self._ewmh.display.flush()
        except Exception as e:
            log.error(f"Could not maximize window: {e}")

    def moveTo(self, x: int, y: int):
        """Move the window to the specified position."""
        try:
            self._ewmh.setMoveResizeWindow(self._window, x=x, y=y)
            self._ewmh.display.flush()
        except Exception as e:
            log.error(f"Could not move window: {e}")


def _get_linux_display_and_ewmh():
    """Get or create the X display and EWMH instance."""
    from Xlib import display as xdisplay
    from ewmh import EWMH

    disp = xdisplay.Display()
    ewmh_instance = EWMH(disp)
    return disp, ewmh_instance


def find_game_linux(title: str) -> LinuxWindow:
    """
    Find a game window by its title on Linux using X11.
    """
    disp, ewmh_instance = _get_linux_display_and_ewmh()

    # Get all windows
    windows = ewmh_instance.getClientList()

    matching_windows = []
    for win in windows:
        try:
            win_title = ewmh_instance.getWmName(win)
            if win_title:
                if isinstance(win_title, bytes):
                    win_title = win_title.decode("utf-8", errors="replace")
                if win_title.startswith(title):
                    matching_windows.append(LinuxWindow(win.id, disp, ewmh_instance))  # type: ignore[union-attr]
        except Exception as e:
            log.debug(f"Error checking window: {e}")
            continue

    if len(matching_windows) != 1:
        for window in matching_windows:
            log.error(f"Found window: {window.title}")
        if len(matching_windows) == 0:
            raise Exception(f"No game window found with title starting with: '{title}'")
        raise Exception(f"Wrong number of game windows: {len(matching_windows)}")

    return matching_windows[0]


def find_game_windows(title: str):
    """
    Find a game window by its title on Windows.
    """
    windows = [
        win
        for win in gw.getWindowsWithTitle(title)  # type: ignore[possibly-undefined]
        if win.title.startswith(title)
    ]
    if len(windows) != 1:
        for window in windows:
            log.error(window)
        if len(windows) == 0:
            raise Exception(f"No game window found with title starting with: '{title}'")
        raise Exception("Wrong number of game windows: " + str(len(windows)))
    return windows[0]


def find_game(title: str) -> Any:
    """
    Find a game window by its title.
    Returns the window object (platform-specific type).
    """
    if IS_WINDOWS:
        return find_game_windows(title)
    elif IS_LINUX:
        return find_game_linux(title)
    else:
        raise NotImplementedError(f"Platform {sys.platform} is not supported")


def screenshot_window_windows(window) -> Tuple[Image, Tuple[int, int]]:
    """Windows-specific screenshot implementation using Win32 API."""
    hwnd = window._hWnd
    client_rect = wintypes.RECT()  # type: ignore[possibly-undefined]

    # Get the client area of the window
    if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):  # type: ignore[possibly-undefined]
        raise ctypes.WinError(ctypes.get_last_error())  # type: ignore[possibly-undefined]

    # Convert client coordinates to screen coordinates
    top_left = wintypes.POINT(client_rect.left, client_rect.top)  # type: ignore[possibly-undefined]
    bottom_right = wintypes.POINT(client_rect.right, client_rect.bottom)  # type: ignore[possibly-undefined]
    user32.ClientToScreen(hwnd, ctypes.byref(top_left))  # type: ignore[possibly-undefined]
    user32.ClientToScreen(hwnd, ctypes.byref(bottom_right))  # type: ignore[possibly-undefined]

    # Calculate the width and height
    width = bottom_right.x - top_left.x
    height = bottom_right.y - top_left.y

    # Take a screenshot of the specified region
    image = gui.screenshot(region=(top_left.x, top_left.y, width, height))
    return (image.convert("RGB"), (top_left.x, top_left.y))


def _is_wayland() -> bool:
    """Check if we're running on Wayland."""
    import os

    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


def _screenshot_with_spectacle(left: int, top: int, width: int, height: int) -> Image:
    """Take a screenshot using KDE Spectacle (works on Wayland)."""
    import subprocess
    import tempfile
    import os
    from PIL import Image as PILImage

    # Create a temporary file for the screenshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Use spectacle to capture the full screen in background mode
        result = subprocess.run(
            ["spectacle", "-b", "-n", "-f", "-o", tmp_path],
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise RuntimeError(f"spectacle failed: {result.stderr.decode()}")

        # Load the full screenshot
        full_image = PILImage.open(tmp_path)

        # Crop to the requested region
        image = full_image.crop((left, top, left + width, top + height))
        return image.convert("RGB")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _screenshot_with_grim(left: int, top: int, width: int, height: int) -> Image:
    """Take a screenshot using grim (Wayland-native for wlroots compositors)."""
    import subprocess
    import tempfile
    import os
    from PIL import Image as PILImage

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # grim can capture a specific region with -g
        geometry = f"{left},{top} {width}x{height}"
        result = subprocess.run(
            ["grim", "-g", geometry, tmp_path],
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.decode()}")

        image = PILImage.open(tmp_path)
        return image.convert("RGB")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _screenshot_with_import(left: int, top: int, width: int, height: int) -> Image:
    """Take a screenshot using ImageMagick import command."""
    import subprocess
    import tempfile
    import os
    from PIL import Image as PILImage

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # ImageMagick import can capture a specific region
        geometry = f"{width}x{height}+{left}+{top}"
        result = subprocess.run(
            ["import", "-window", "root", "-crop", geometry, tmp_path],
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise RuntimeError(f"import failed: {result.stderr.decode()}")

        image = PILImage.open(tmp_path)
        return image.convert("RGB")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _screenshot_with_mss(left: int, top: int, width: int, height: int) -> Image:
    """Take a screenshot using mss (works on X11)."""
    import mss
    from PIL import Image as PILImage

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        sct_img = sct.grab(monitor)
        image = PILImage.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    return image


def _find_available_screenshot_method():
    """Find which screenshot tool is available on the system."""
    import shutil

    # On Wayland, prefer tools that work natively with Wayland
    if _is_wayland():
        # spectacle works great on KDE Wayland
        if shutil.which("spectacle"):
            return "spectacle"
        # grim is the standard for wlroots-based compositors (Sway, etc.)
        if shutil.which("grim"):
            return "grim"

    # Try mss first for X11 (fastest, no subprocess)
    # Then fall back to command-line tools
    if shutil.which("import"):
        return "import"

    return "mss"  # Default fallback


# Cache the screenshot method to avoid repeated checks
_screenshot_method = None


def screenshot_window_linux(window: LinuxWindow) -> Tuple[Image, Tuple[int, int]]:
    """
    Linux screenshot implementation with multiple backend support.
    Supports both X11 and Wayland through various tools.
    """
    global _screenshot_method

    left = window.left
    top = window.top
    width = window.width
    height = window.height

    log.debug(f"Taking screenshot: region=({left}, {top}, {width}, {height})")

    # Find the best available method if not cached
    if _screenshot_method is None:
        _screenshot_method = _find_available_screenshot_method()
        log.info(f"Using screenshot method: {_screenshot_method}")

    errors = []

    # Try the preferred method first
    methods_to_try = [_screenshot_method]

    # Add fallbacks
    if _is_wayland():
        if "spectacle" not in methods_to_try:
            methods_to_try.append("spectacle")
        if "grim" not in methods_to_try:
            methods_to_try.append("grim")
    if "import" not in methods_to_try:
        methods_to_try.append("import")
    if "mss" not in methods_to_try:
        methods_to_try.append("mss")

    for method in methods_to_try:
        try:
            if method == "spectacle":
                image = _screenshot_with_spectacle(left, top, width, height)
            elif method == "grim":
                image = _screenshot_with_grim(left, top, width, height)
            elif method == "import":
                image = _screenshot_with_import(left, top, width, height)
            else:  # mss
                image = _screenshot_with_mss(left, top, width, height)

            # Update the cached method if this one worked
            _screenshot_method = method
            return (image, (left, top))

        except Exception as e:
            errors.append(f"{method}: {e}")
            log.debug(f"Screenshot method {method} failed: {e}")
            continue

    # All methods failed
    error_details = "\n".join(errors)
    raise RuntimeError(
        f"All screenshot methods failed:\n{error_details}\n\n"
        "Please install one of the following:\n"
        "- KDE: spectacle (usually pre-installed)\n"
        "- Wayland/Sway: grim (`sudo pacman -S grim` or `sudo apt install grim`)\n"
        "- X11: ImageMagick (`sudo pacman -S imagemagick` or `sudo apt install imagemagick`)"
    )


def screenshot_window(window) -> Tuple[Image, Tuple[int, int]]:
    """
    Take a screenshot of the given window's client area.
    Automatically uses the appropriate method based on the platform.
    """
    if IS_WINDOWS:
        return screenshot_window_windows(window)
    elif IS_LINUX:
        return screenshot_window_linux(window)
    else:
        # Fallback for other platforms (macOS, etc.)
        # Use basic pyautogui screenshot with window bounds
        left = window.left
        top = window.top
        width = window.width
        height = window.height
        image = gui.screenshot(region=(left, top, width, height))
        return (image.convert("RGB"), (left, top))


def add_offset(base: Tuple[int, int], coord: Tuple[int, int]) -> Tuple[int, int]:
    bx, by = base
    cx, cy = coord
    return (bx + cx, by + cy)
