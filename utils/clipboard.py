"""平台选区/剪贴板读取——Linux 读 Primary Selection，Windows 读剪贴板。"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

if sys.platform == "linux":

    import subprocess

    def read_selection() -> str:
        try:
            result = subprocess.run(
                ["xclip", "-o", "-selection", "primary"],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except FileNotFoundError:
            if not read_selection._warned:
                logger.warning("xclip 未安装，无法读取鼠标选区翻译，请安装 xclip")
                read_selection._warned = True
            return ""
        except Exception as e:
            logger.debug("读取选区失败: %s", e)
            return ""

    read_selection._warned = False

elif sys.platform == "win32":

    from PySide6.QtWidgets import QApplication

    def read_selection() -> str:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            return clipboard.text()
        return ""
