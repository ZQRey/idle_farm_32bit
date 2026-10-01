"""
Windows Desktop Integration Module.
Handles:
- Positioning the game window above the taskbar
- Making the window borderless/frameless
- Removing from taskbar/Alt+Tab
- Click-through mode
- DPI awareness
- Desktop layer integration (WorkerW/Progman)
"""
import ctypes
import ctypes.wintypes
import logging
import platform
import struct

logger = logging.getLogger("windows")

# Windows API constants
GWL_EXSTYLE = -20
GWL_STYLE = -16

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000

WS_EX_TOOLWINDOW = 0x00000080  # Hides from Alt+Tab
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020  # Click-through
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_APPWINDOW = 0x00040000  # Shows in taskbar (we want to REMOVE this)

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020

HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_TOP = 0

LWA_ALPHA = 0x02
LWA_COLORKEY = 0x01

SM_CXSCREEN = 0
SM_CYSCREEN = 1

SPI_GETWORKAREA = 48

MONITOR_DEFAULTTOPRIMARY = 1
MONITOR_DEFAULTTONEAREST = 2

# SendMessage for WorkerW discovery
WM_USER = 0x0400
SMTO_NORMAL = 0x0000

# Structures
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_uint),
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hWnd", ctypes.c_void_p),
        ("uCallbackMessage", ctypes.c_uint),
        ("uEdge", ctypes.c_uint),
        ("rc", RECT),
        ("lParam", ctypes.c_long),
    ]


# Windows API function bindings
user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
dwmapi = None
try:
    dwmapi = ctypes.windll.dwmapi
except Exception:
    pass


def get_screen_info():
    """Get screen resolution and DPI information."""
    info = {}

    # Screen resolution
    info["screen_width"] = user32.GetSystemMetrics(SM_CXSCREEN)
    info["screen_height"] = user32.GetSystemMetrics(SM_CYSCREEN)

    # Work area (excluding taskbar)
    work_area = RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work_area), 0)
    info["work_left"] = work_area.left
    info["work_top"] = work_area.top
    info["work_right"] = work_area.right
    info["work_bottom"] = work_area.bottom
    info["work_width"] = work_area.right - work_area.left
    info["work_height"] = work_area.bottom - work_area.top

    # DPI
    try:
        hdc = user32.GetDC(0)
        dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
        user32.ReleaseDC(0, hdc)
        info["dpi_x"] = dpi_x
        info["dpi_y"] = dpi_y
        info["dpi_scale"] = dpi_x / 96.0
    except Exception:
        info["dpi_x"] = 96
        info["dpi_y"] = 96
        info["dpi_scale"] = 1.0

    # Determine taskbar edge from work area vs screen comparison
    # This is more reliable than SHAppBarMessage
    screen_w = info["screen_width"]
    screen_h = info["screen_height"]
    
    bottom_gap = screen_h - work_area.bottom
    top_gap = work_area.top
    left_gap = work_area.left
    right_gap = screen_w - work_area.right
    
    max_gap = max(bottom_gap, top_gap, left_gap, right_gap)
    if max_gap <= 0:
        # No gap detected, assume bottom taskbar with default size
        info["taskbar_edge"] = 3
        info["taskbar_size"] = 40
    elif bottom_gap == max_gap:
        info["taskbar_edge"] = 3  # bottom
        info["taskbar_size"] = bottom_gap
    elif top_gap == max_gap:
        info["taskbar_edge"] = 1  # top
        info["taskbar_size"] = top_gap
    elif left_gap == max_gap:
        info["taskbar_edge"] = 0  # left
        info["taskbar_size"] = left_gap
    else:
        info["taskbar_edge"] = 2  # right
        info["taskbar_size"] = right_gap
    
    info["taskbar_rect"] = (0, 0, 0, 0)  # Not used anymore

    return info


def calculate_window_rect(scene_height: int = 180, monitor_index: int = 0):
    """Calculate where the game window should be positioned."""
    screen_info = get_screen_info()

    taskbar_edge = screen_info["taskbar_edge"]

    if taskbar_edge == 3:  # Bottom taskbar (most common)
        x = screen_info["work_left"]
        y = screen_info["work_bottom"] - scene_height
        width = screen_info["work_width"]
        height = scene_height
    elif taskbar_edge == 1:  # Top taskbar
        x = screen_info["work_left"]
        y = screen_info["work_top"]
        width = screen_info["work_width"]
        height = scene_height
    elif taskbar_edge == 0:  # Left taskbar
        x = screen_info["work_left"]
        y = screen_info["work_bottom"] - scene_height
        width = screen_info["work_width"]
        height = scene_height
    elif taskbar_edge == 2:  # Right taskbar
        x = screen_info["work_left"]
        y = screen_info["work_bottom"] - scene_height
        width = screen_info["work_width"]
        height = scene_height
    else:
        x = 0
        y = screen_info["screen_height"] - scene_height - 40
        width = screen_info["screen_width"]
        height = scene_height

    logger.info(f"Window rect: x={x}, y={y}, w={width}, h={height}")
    logger.info(f"Taskbar edge: {taskbar_edge} (0=left, 1=top, 2=right, 3=bottom)")
    logger.info(f"Screen: {screen_info['screen_width']}x{screen_info['screen_height']}")
    logger.info(f"Work area: {screen_info['work_left']},{screen_info['work_top']} - "
                f"{screen_info['work_right']},{screen_info['work_bottom']}")
    logger.info(f"DPI scale: {screen_info['dpi_scale']}")

    return x, y, width, height, screen_info


def find_desktop_workerw():
    """
    Find the WorkerW window behind desktop icons for wallpaper-level rendering.
    This allows the game to appear between the wallpaper and desktop icons.
    """
    try:
        progman = user32.FindWindowW("Progman", None)
        if not progman:
            logger.warning("Progman not found")
            return None

        # Send message to Progman to spawn a WorkerW
        result = ctypes.c_ulong()
        user32.SendMessageTimeoutW(
            progman,
            0x052C,  # Undocumented message to spawn WorkerW
            0xD, 0,
            SMTO_NORMAL,
            1000,
            ctypes.byref(result)
        )

        workerw = None

        # Callback to find the right WorkerW
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
        def enum_callback(hwnd, lparam):
            nonlocal workerw
            shell_view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
            if shell_view:
                # The WorkerW AFTER this one is what we want
                workerw = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            return True

        user32.EnumWindows(enum_callback, 0)

        if workerw:
            logger.info(f"Found desktop WorkerW: {workerw}")
        else:
            logger.info("WorkerW not found, will use alternative positioning")

        return workerw

    except Exception as e:
        logger.error(f"Error finding WorkerW: {e}")
        return None


def setup_game_window(hwnd: int, scene_height: int = 180, click_through: bool = True):
    """
    Configure the game window for desktop integration.
    Returns the calculated window rectangle.
    """
    logger.info(f"Setting up game window: hwnd={hwnd}")

    x, y, width, height, screen_info = calculate_window_rect(scene_height)

    # Remove standard window styles, set to popup
    style = WS_POPUP | WS_VISIBLE
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)

    # Set extended styles: tool window (no taskbar/alt+tab) + layered + no-activate
    ex_style = WS_EX_TOOLWINDOW | WS_EX_LAYERED | WS_EX_NOACTIVATE
    if click_through:
        ex_style |= WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    # Position the window
    user32.SetWindowPos(
        hwnd, HWND_BOTTOM,
        x, y, width, height,
        SWP_NOACTIVATE | SWP_FRAMECHANGED
    )

    # Set color key for transparency (magenta = transparent)
    user32.SetLayeredWindowAttributes(hwnd, 0xFF00FF, 0, LWA_COLORKEY)

    # Log diagnostics
    log_window_diagnostics(hwnd, screen_info)

    return x, y, width, height


def set_click_through(hwnd: int, enabled: bool):
    """Enable or disable click-through mode."""
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enabled:
        ex_style |= WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    logger.info(f"Click-through: {'enabled' if enabled else 'disabled'}")


def set_window_bottom(hwnd: int):
    """Push window to bottom of Z-order (behind other apps, above desktop)."""
    user32.SetWindowPos(
        hwnd, HWND_BOTTOM,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )


def try_embed_in_desktop(hwnd: int):
    """
    Try to embed the game window as a child of the desktop WorkerW layer.
    This makes it appear at wallpaper level.
    Returns True if successful, False if fallback positioning is needed.
    """
    workerw = find_desktop_workerw()
    if workerw:
        try:
            # Set as child of WorkerW
            user32.SetParent(hwnd, workerw)
            logger.info("Successfully embedded in desktop WorkerW layer")
            return True
        except Exception as e:
            logger.warning(f"Failed to embed in WorkerW: {e}")
            return False
    return False


def is_fullscreen_app_running():
    """Check if a fullscreen application is running."""
    try:
        fg_hwnd = user32.GetForegroundWindow()
        if not fg_hwnd:
            return False

        fg_rect = RECT()
        user32.GetWindowRect(fg_hwnd, ctypes.byref(fg_rect))

        screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
        screen_h = user32.GetSystemMetrics(SM_CYSCREEN)

        # Check if foreground window covers entire screen
        if (fg_rect.left <= 0 and fg_rect.top <= 0 and
                fg_rect.right >= screen_w and fg_rect.bottom >= screen_h):
            return True

        return False
    except Exception:
        return False


def log_window_diagnostics(hwnd: int, screen_info: dict = None):
    """Log detailed window diagnostics for debugging."""
    if screen_info is None:
        screen_info = get_screen_info()

    logger.info("=== Window Diagnostics ===")
    logger.info(f"  Window handle: {hwnd}")
    logger.info(f"  Screen: {screen_info['screen_width']}x{screen_info['screen_height']}")
    logger.info(f"  Work area: ({screen_info['work_left']}, {screen_info['work_top']}) - "
                f"({screen_info['work_right']}, {screen_info['work_bottom']})")
    logger.info(f"  DPI: {screen_info['dpi_x']}x{screen_info['dpi_y']} "
                f"(scale: {screen_info['dpi_scale']:.0%})")
    logger.info(f"  Taskbar edge: {screen_info['taskbar_edge']}")
    logger.info(f"  Taskbar rect: {screen_info['taskbar_rect']}")

    # Get actual window rect
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    logger.info(f"  Window rect: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})")

    # Get window styles
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    logger.info(f"  Window style: 0x{style & 0xFFFFFFFF:08X}")
    logger.info(f"  Extended style: 0x{ex_style & 0xFFFFFFFF:08X}")
    logger.info(f"  Is tool window: {bool(ex_style & WS_EX_TOOLWINDOW)}")
    logger.info(f"  Is click-through: {bool(ex_style & WS_EX_TRANSPARENT)}")
    logger.info(f"  Is layered: {bool(ex_style & WS_EX_LAYERED)}")
    logger.info(f"  Platform: {platform.platform()}")
    logger.info("=== End Diagnostics ===")
