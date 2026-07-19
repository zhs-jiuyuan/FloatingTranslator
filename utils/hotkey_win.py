"""Windows 全局鼠标钩子——检测划词、模拟 Ctrl+C 取回选中文字。"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import time

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
#  ctypes 准备
# ---------------------------------------------------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

_DRAG_THRESHOLD = 5
_POST_DRAG_DELAY = 0.05
_COPY_DELAY = 0.05


def _send_ctrl_c() -> None:
    import win32api
    import win32con

    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(0x43, 0, 0, 0)  # C
    win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


def _capture_selection() -> str:
    import win32con
    import win32clipboard

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

    _send_ctrl_c()
    time.sleep(_COPY_DELAY)

    text = ""
    try:
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception:
            pass
        win32clipboard.EmptyClipboard()
        if saved:
            try:
                win32clipboard.SetClipboardText(saved, win32con.CF_UNICODETEXT)
            except Exception:
                pass
        win32clipboard.CloseClipboard()
    except Exception:
        pass

    return text.strip() if text else ""


# ---------------------------------------------------------------
#  Qt 封装
# ---------------------------------------------------------------

class WinSelectionMonitor(QThread):
    text_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hook_id: int | None = None
        self._callback = None
        self._start_x = 0
        self._start_y = 0
        self._button_down = False

    def run(self) -> None:
        self._callback = HOOKPROC(self._hook_proc)
        module = kernel32.GetModuleHandleW(None)
        self._hook_id = user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._callback, module, 0
        )
        if not self._hook_id:
            logger.error("SetWindowsHookEx 失败")
            return

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
        if self._hook_id:
            user32.PostThreadMessageW(
                kernel32.GetCurrentThreadId(), 0x0012, 0, 0  # WM_QUIT
            )

    def _hook_proc(self, nCode: int, wParam: int, lParam: int) -> int:
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
                text = _capture_selection()
                if text:
                    self.text_selected.emit(text)

        return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)
