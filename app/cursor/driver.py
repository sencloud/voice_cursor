import ctypes
import logging
import platform
import subprocess
import time

import pyautogui
import pyperclip
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

_IS_WIN = platform.system() == "Windows"
_IS_MAC = platform.system() == "Darwin"


# ── Window management ──────────────────────────────────────

def _find_cursor_windows_win() -> list[tuple[int, str]]:
    """Return [(hwnd, title), ...] for all visible Cursor editor windows."""
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    results = []

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if "cursor" in title.lower() and not title.startswith("Voice Cursor"):
            results.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    print(f"[driver] Found {len(results)} Cursor window(s):")
    for hwnd, title in results:
        print(f"  hwnd={hwnd}  title={title!r}")
    return results


def _force_foreground_win(hwnd: int):
    """Reliably bring a window to foreground on Windows."""
    user32 = ctypes.windll.user32
    SW_RESTORE = 9

    is_iconic = user32.IsIconic(hwnd)
    print(f"[driver] _force_foreground: hwnd={hwnd}, minimized={bool(is_iconic)}")

    if is_iconic:
        user32.ShowWindow(hwnd, SW_RESTORE)
        print("[driver]   restored from minimized")

    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    print(f"[driver]   current_thread={current_thread}, target_thread={target_thread}")

    attached = False
    if current_thread != target_thread:
        attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))
        print(f"[driver]   AttachThreadInput={attached}")

    r1 = user32.BringWindowToTop(hwnd)
    r2 = user32.SetForegroundWindow(hwnd)
    print(f"[driver]   BringWindowToTop={r1}, SetForegroundWindow={r2}")

    if attached:
        user32.AttachThreadInput(current_thread, target_thread, False)

    fg = user32.GetForegroundWindow()
    print(f"[driver]   after: foreground_hwnd={fg}, match={fg == hwnd}")


def _find_and_focus_cursor_mac() -> bool:
    script = '''
    tell application "System Events"
        set cursorProcs to every process whose name contains "Cursor"
        if (count of cursorProcs) > 0 then
            set frontmost of item 1 of cursorProcs to true
            return "ok"
        end if
    end tell
    return "none"
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip() == "ok"
    except Exception:
        return False


def _find_and_focus_cursor_linux() -> bool:
    try:
        result = subprocess.run(
            ["wmctrl", "-l"], capture_output=True, text=True, timeout=3,
        )
        for line in result.stdout.splitlines():
            if "cursor" in line.lower() and "voice cursor" not in line.lower():
                wid = line.split()[0]
                subprocess.run(["wmctrl", "-i", "-a", wid], timeout=3)
                return True
    except FileNotFoundError:
        logger.warning("wmctrl not installed")
    except Exception:
        pass
    return False


def _is_foreground_win(hwnd: int) -> bool:
    """Check if the given window is currently the foreground window."""
    return ctypes.windll.user32.GetForegroundWindow() == hwnd


# ── Driver ─────────────────────────────────────────────────

class CursorDriver(QObject):
    """Automates sending text to Cursor's Agent Chat.

    Robust flow:
      1. Focus Cursor window (with retry)
      2. Escape to clear any active state
      3. Ctrl+Shift+L to open a NEW Agent chat
      4. Wait for Agent input to be ready
      5. Paste text
      6. Enter to send
    """

    send_started = Signal()
    send_done = Signal()
    progress_updated = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, shortcut_open_chat="ctrl+shift+l",
                 shortcut_paste="ctrl+v", shortcut_send="enter",
                 delay_after_open=1.2, delay_after_paste=0.3):
        super().__init__()
        self._shortcut_open = shortcut_open_chat
        self._shortcut_paste = shortcut_paste
        self._shortcut_send = shortcut_send
        self._delay_open = delay_after_open
        self._delay_paste = delay_after_paste

    def update_config(self, shortcut_open_chat: str, shortcut_paste: str,
                      shortcut_send: str, delay_after_open: float,
                      delay_after_paste: float):
        self._shortcut_open = shortcut_open_chat
        self._shortcut_paste = shortcut_paste
        self._shortcut_send = shortcut_send
        self._delay_open = delay_after_open
        self._delay_paste = delay_after_paste

    def _adapt_shortcut(self, shortcut: str) -> str:
        if _IS_MAC:
            return shortcut.replace("ctrl", "command")
        return shortcut

    def _press_shortcut(self, shortcut: str):
        keys = [k.strip() for k in shortcut.split("+")]
        keys = [k for k in keys if k]
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)

    def _focus_cursor_window(self) -> bool:
        """Find and reliably bring a Cursor window to foreground."""
        self.progress_updated.emit("正在定位 Cursor 窗口...")

        if _IS_WIN:
            windows = _find_cursor_windows_win()
            if not windows:
                self.error_occurred.emit(
                    "未找到 Cursor 窗口，请确保 Cursor 已打开"
                )
                return False

            hwnd, title = windows[0]
            logger.info("Focusing Cursor: %s (hwnd=%d)", title, hwnd)

            for attempt in range(3):
                _force_foreground_win(hwnd)
                time.sleep(0.2)
                if _is_foreground_win(hwnd):
                    logger.info("Cursor focused on attempt %d", attempt + 1)
                    return True
                time.sleep(0.3)

            logger.warning("Could not verify foreground, proceeding anyway")
            return True

        if _IS_MAC:
            if _find_and_focus_cursor_mac():
                time.sleep(0.4)
                return True
            self.error_occurred.emit("未找到 Cursor 窗口，请确保 Cursor 已打开")
            return False

        if _find_and_focus_cursor_linux():
            time.sleep(0.4)
            return True
        logger.warning("Could not focus Cursor window, sending to active window")
        return True

    def send_to_cursor(self, text: str):
        """Send text to Cursor's NEW Agent Chat reliably."""
        print(f"\n[driver] === send_to_cursor START ({len(text)} chars) ===")
        print(f"[driver] config: open={self._shortcut_open!r}  paste={self._shortcut_paste!r}  "
              f"send={self._shortcut_send!r}  delay_open={self._delay_open}  delay_paste={self._delay_paste}")

        if not text.strip():
            print("[driver] ERROR: empty text")
            self.error_occurred.emit("没有可发送的内容")
            return

        self.send_started.emit()

        print("[driver] Step 1: focus Cursor window")
        if not self._focus_cursor_window():
            print("[driver] FAILED: could not focus Cursor")
            return

        try:
            print("[driver] Step 2: copy to clipboard")
            pyperclip.copy(text)
            clip_check = pyperclip.paste()
            print(f"[driver]   clipboard verify: {len(clip_check)} chars, match={clip_check == text}")

            print("[driver] Step 3: Escape x2 to clear state")
            self.progress_updated.emit("准备 Cursor 环境...")
            pyautogui.press("escape")
            time.sleep(0.15)
            pyautogui.press("escape")
            time.sleep(0.2)

            if _IS_WIN:
                fg = ctypes.windll.user32.GetForegroundWindow()
                print(f"[driver]   after escape: foreground_hwnd={fg}")

            print(f"[driver] Step 4: open New Agent with {self._shortcut_open!r}")
            self.progress_updated.emit("打开新 Agent 对话...")
            shortcut = self._adapt_shortcut(self._shortcut_open)
            print(f"[driver]   adapted shortcut: {shortcut!r}")
            self._press_shortcut(shortcut)
            print(f"[driver]   waiting {self._delay_open}s for Agent panel...")
            time.sleep(self._delay_open)

            if _IS_WIN:
                fg = ctypes.windll.user32.GetForegroundWindow()
                print(f"[driver]   after open: foreground_hwnd={fg}")

            print(f"[driver] Step 5: paste with {self._shortcut_paste!r}")
            self.progress_updated.emit("粘贴内容...")
            paste_shortcut = self._adapt_shortcut(self._shortcut_paste)
            self._press_shortcut(paste_shortcut)
            time.sleep(self._delay_paste)

            print(f"[driver] Step 6: send with {self._shortcut_send!r}")
            self.progress_updated.emit("发送...")
            send_shortcut = self._adapt_shortcut(self._shortcut_send)
            self._press_shortcut(send_shortcut)

            print("[driver] === send_to_cursor DONE ===\n")
            self.progress_updated.emit("已发送到 Cursor Agent Chat")
            self.send_done.emit()

        except Exception as e:
            print(f"[driver] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"发送到 Cursor 失败: {e}")
