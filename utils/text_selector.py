"""获取用户选中的文本——通过模拟 Ctrl+C 复制并还原剪贴板。"""
from __future__ import annotations

import logging
import time

import pyautogui
import pyperclip

logger = logging.getLogger(__name__)


class TextSelector:
    COPY_DELAY = 0.15

    @classmethod
    def get_selected_text(cls) -> str:
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = ""
            logger.debug("无法读取剪贴板原始内容")

        try:
            pyautogui.hotkey("ctrl", "c")
            time.sleep(cls.COPY_DELAY)
            text = pyperclip.paste()
        except Exception as e:
            logger.error("模拟 Ctrl+C 复制失败: %s", e)
            text = ""
        finally:
            try:
                pyperclip.copy(old_clipboard)
            except Exception as e:
                logger.debug("还原剪贴板失败: %s", e)

        if text and text.strip():
            logger.info("获取到选中文本: %s...", text[:50])
        else:
            logger.info("未获取到选中文本")
        return text.strip() if text else ""
