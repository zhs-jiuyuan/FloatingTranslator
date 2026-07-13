"""全局热键管理器——Windows 使用 keyboard 库，Linux 使用 pynput 库。
注意：Windows 上 keyboard 库需要管理员权限才能捕获全局按键。"""
from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, hotkey: str = "ctrl+q", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        if sys.platform == "win32":
            self._start_keyboard()
        else:
            self._start_pynput()

    def _start_keyboard(self) -> None:
        try:
            import keyboard
            keyboard.add_hotkey(self._hotkey, self._on_triggered)
            logger.info("热键 %s 已注册 (keyboard, Windows)", self._hotkey)
        except ImportError:
            logger.error("keyboard 库未安装，无法注册全局热键")
        except Exception as e:
            logger.error("注册热键失败 (keyboard): %s", e)

    def _start_pynput(self) -> None:
        try:
            from pynput import keyboard as pynput_keyboard
        except ImportError:
            logger.error("pynput 库未安装，无法注册全局热键")
            return

        hotkey_parts = self._hotkey.split("+")
        # pynput 对修饰键返回具体变体 (ctrl_l/ctrl_r)，而非通用名 (ctrl)
        modifier_variants = {
            "ctrl": {pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r},
            "shift": {pynput_keyboard.Key.shift, pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r},
            "alt": {pynput_keyboard.Key.alt, pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt_gr},
        }
        current_keys: set = set()

        def on_press(key: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            current_keys.add(key)
            if self._check_combo(current_keys, modifier_variants, hotkey_parts):
                self._on_triggered()

        def on_release(key: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            current_keys.discard(key)

        def run() -> None:
            logger.info("热键 %s 已注册 (pynput, Linux)", self._hotkey)
            with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def _check_combo(self, current_keys: set, modifier_variants: dict, parts: list[str]) -> bool:
        for part in parts:
            found = False
            if part in modifier_variants:
                if current_keys & modifier_variants[part]:
                    found = True
            else:
                try:
                    from pynput.keyboard import KeyCode
                    if KeyCode.from_char(part) in current_keys:
                        found = True
                except Exception:
                    pass
            if not found:
                return False
        return True

    def _on_triggered(self) -> None:
        logger.info("热键 %s 触发", self._hotkey)
        self.triggered.emit()

    def stop(self) -> None:
        self._running = False
        if sys.platform == "win32":
            try:
                import keyboard
                keyboard.remove_all_hotkeys()
                logger.info("热键已注销")
            except Exception:
                pass
