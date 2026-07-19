"""平台抽象层——选区捕获、光标读取、监听器工厂。"""
from __future__ import annotations

import logging
import subprocess
import sys
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def read_selection() -> str:
    """读取当前选中的文本。"""
    if sys.platform == "linux":
        return _read_selection_linux()
    return _read_selection_windows()


def _read_selection_linux() -> str:
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True, text=True, timeout=1,
        )
        if result.returncode == 0:
            return result.stdout
        return ""
    except FileNotFoundError:
        if not _read_selection_linux._warned:
            logger.warning("xclip 未安装，无法读取鼠标选区翻译，请安装 xclip")
            _read_selection_linux._warned = True
        return ""
    except Exception as e:
        logger.debug("读取选区失败: %s", e)
        return ""


_read_selection_linux._warned = False


def _read_selection_windows() -> str:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        return clipboard.text()
    return ""


# --- Cursor Position ---

_xd = None

def _init_xdisplay():
    global _xd
    if _xd is not None:
        return
    try:
        from Xlib import display as xdisplay
        _xd = xdisplay.Display()
    except Exception:
        pass


def get_cursor_pos() -> tuple[int, int]:
    """获取全局光标坐标。"""
    if sys.platform == "linux":
        _init_xdisplay()
        if _xd is not None:
            try:
                data = _xd.screen().root.query_pointer()
                return data.root_x, data.root_y
            except Exception:
                pass
    p = QCursor.pos()
    return p.x(), p.y()


# --- Selection Monitor ---

class SelectionMonitor(QObject):
    """选区监听器——不同平台不同实现，统一 text_selected 信号接口。"""
    text_selected = Signal(str)

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class _LinuxClipboardMonitor(SelectionMonitor):
    CLIPBOARD_POLL_MS = 300

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_clipboard = ""
        self._translating = False
        self._timer: QTimer | None = None

    def set_translating(self, value: bool) -> None:
        self._translating = value

    def reset_last(self) -> None:
        self._last_clipboard = ""

    def start(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.CLIPBOARD_POLL_MS)
        logger.info("鼠标选区监听已启动 (间隔 %dms)", self.CLIPBOARD_POLL_MS)

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def _poll(self) -> None:
        if self._translating:
            return
        text = read_selection()
        if not text:
            if self._last_clipboard:
                self._last_clipboard = ""
            return
        if text != self._last_clipboard:
            logger.debug("检测到选区变化: %s...", text[:80])
            self._last_clipboard = text
            self.text_selected.emit(text)


class _WinMouseHookMonitor(SelectionMonitor):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread = _WinHookThread()
        self._thread.text_selected.connect(self.text_selected.emit)

    def start(self) -> None:
        self._thread.start()
        QApplication.instance().aboutToQuit.connect(self._thread.stop)
        logger.info("Windows 鼠标钩子已启动")

    def stop(self) -> None:
        self._thread.stop()


class _WinHookThread(QThread):
    text_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hook_id: int | None = None
        self._callback = None
        self._thread_id = 0
        self._start_x = 0
        self._start_y = 0
        self._button_down = False

    def run(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_long
        user32.GetMessageW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        user32.GetMessageW.restype = ctypes.c_long
        user32.PostThreadMessageW.argtypes = [ctypes.c_uint, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostThreadMessageW.restype = ctypes.c_long

        WH_MOUSE_LL = 14
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        _DRAG_THRESHOLD = 5
        _POST_DRAG_DELAY = 0.05

        def hook_proc(nCode, wParam, lParam):
            if nCode < 0:
                return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)
            if wParam == WM_LBUTTONDOWN:
                import win32api
                self._start_x, self._start_y = win32api.GetCursorPos()
                self._button_down = True
            elif wParam == WM_LBUTTONUP and self._button_down:
                self._button_down = False
                import win32api
                end_x, end_y = win32api.GetCursorPos()
                if (abs(end_x - self._start_x) > _DRAG_THRESHOLD
                        or abs(end_y - self._start_y) > _DRAG_THRESHOLD):
                    time.sleep(_POST_DRAG_DELAY)
                    text = self._capture_selection()
                    if text:
                        self.text_selected.emit(text)
            return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)

        self._callback = HOOKPROC(hook_proc)
        self._thread_id = kernel32.GetCurrentThreadId()
        self._hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, self._callback, None, 0)
        if not self._hook_id:
            logger.error("SetWindowsHookExW 失败 (错误码: %d)", kernel32.GetLastError())
            return
        logger.info("Windows 鼠标钩子安装成功")

        msg = wintypes.MSG()
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)

    def stop(self) -> None:
        import ctypes
        if self._hook_id:
            user32 = ctypes.windll.user32
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)

    @staticmethod
    def _capture_selection() -> str:
        import win32con
        import win32clipboard
        import win32api

        _COPY_DELAY = 0.05

        saved = ""
        try:
            win32clipboard.OpenClipboard()
            try:
                saved = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except Exception:
                pass
            win32clipboard.CloseClipboard()
        except Exception:
            pass

        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x43, 0, 0, 0)
        win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(_COPY_DELAY)

        text = ""
        try:
            win32clipboard.OpenClipboard()
            try:
                text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except Exception:
                pass
            if saved:
                win32clipboard.EmptyClipboard()
                try:
                    win32clipboard.SetClipboardText(saved, win32con.CF_UNICODETEXT)
                except Exception:
                    pass
            win32clipboard.CloseClipboard()
        except Exception:
            pass

        if text == saved:
            return ""
        return text.strip() if text else ""


def create_monitor() -> SelectionMonitor:
    """工厂函数——返回当前平台的选区监听器。"""
    if sys.platform == "win32":
        return _WinMouseHookMonitor()
    return _LinuxClipboardMonitor()
