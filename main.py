"""FloatingTranslator 应用入口——组装所有组件并启动事件循环。"""
from __future__ import annotations

import os
import sys

if sys.platform == "linux":
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

# 修复 PySide6 shiboken 与 six 库的兼容性问题
import six  # noqa: F401
if not hasattr(six._SixMetaPathImporter, "_path"):
    six._SixMetaPathImporter._path = None

import logging
import signal
import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config import AppConfig, ConfigManager
from engine.base import TranslationEngine
from engine.free_online import FreeOnlineEngine
from engine.llm_api import LLMAPIEngine
from engine.local_model import LocalModelEngine
from ui.floating_window import FloatingWindow
from ui.settings_dialog import SettingsDialog
from ui.tray_icon import TrayIcon
from utils.language_detector import LanguageDetector

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def create_engine(config: AppConfig) -> TranslationEngine:
    if config.engine_type == "llm_api":
        return LLMAPIEngine(
            api_key=config.llm_api_key,
            api_url=config.llm_api_url,
            model=config.llm_model,
            system_prompt=config.llm_system_prompt,
        )
    elif config.engine_type == "local_model":
        return LocalModelEngine(
            model_type=config.local_model_type,
            model_path=config.local_model_path,
            system_prompt=config.local_system_prompt,
        )
    else:
        return FreeOnlineEngine()


class FloatingTranslatorApp:
    CLIPBOARD_POLL_MS = 300  # 剪贴板轮询间隔

    def __init__(self) -> None:
        self._config_path = os.path.join(BASE_DIR, "config.json")
        self._config = ConfigManager.load(self._config_path)
        self._engine = create_engine(self._config)
        self._last_clipboard = ""
        self._translating = False

        self._floating_window = FloatingWindow(
            opacity=self._config.opacity,
        )
        self._floating_window.set_auto_hide_seconds(self._config.auto_hide_seconds)
        self._floating_window.close_requested.connect(self._floating_window.hide)
        self._floating_window.start_tracking()

        self._tray_icon = TrayIcon(self._config)
        self._tray_icon.engine_changed.connect(self._on_engine_changed)
        self._tray_icon.settings_requested.connect(self._open_settings)
        self._tray_icon.show()

        self._connect_engine()

        # 启动剪贴板轮询
        self._clipboard_timer = QTimer()
        self._clipboard_timer.timeout.connect(self._poll_clipboard)
        self._clipboard_timer.start(self.CLIPBOARD_POLL_MS)
        logger.info("鼠标选区监听已启动 (间隔 %dms)", self.CLIPBOARD_POLL_MS)

    def _disconnect_engine(self) -> None:
        try:
            self._engine.result_ready.disconnect()
        except RuntimeError:
            pass
        try:
            self._engine.error_occurred.disconnect()
        except RuntimeError:
            pass

    def _connect_engine(self) -> None:
        self._engine.result_ready.connect(self._on_result_ready)
        self._engine.error_occurred.connect(self._on_error_occurred)

    def _swap_engine(self) -> None:
        self._disconnect_engine()
        self._engine = create_engine(self._config)
        self._connect_engine()
        self._translating = False
        self._last_clipboard = ""

    def _poll_clipboard(self) -> None:
        if self._translating:
            return
        text = self._read_primary_selection()
        if not text:
            if self._last_clipboard:
                self._last_clipboard = ""
                self._floating_window.clear_content()
            return
        if text != self._last_clipboard:
            logger.debug("检测到选区变化: %s...", text[:80])
            self._last_clipboard = text
            self._translate(text)

    @staticmethod
    def _read_primary_selection() -> str:
        try:
            result = subprocess.run(
                ["xclip", "-o", "-selection", "primary"],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except FileNotFoundError:
            if not _read_primary_selection._warned:
                logger.warning("xclip 未安装，无法读取鼠标选区翻译，请安装 xclip")
                _read_primary_selection._warned = True
            return ""
        except Exception as e:
            logger.debug("读取选区失败: %s", e)
            return ""

    def _on_engine_changed(self, engine_type: str) -> None:
        self._config.engine_type = engine_type
        self._swap_engine()
        self._tray_icon.update_engine_check(engine_type)
        logger.info("引擎已切换为: %s", self._engine.engine_name)
        self._tray_icon.show_message(
            "引擎已切换", f"当前引擎: {self._engine.engine_name}"
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._config_path)
        dialog.opacity_preview.connect(self._floating_window.set_opacity)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self._config = dialog.get_config()
            self._swap_engine()
            self._floating_window.set_opacity(self._config.opacity)
            self._floating_window.set_auto_hide_seconds(self._config.auto_hide_seconds)
            self._tray_icon.update_engine_check(self._config.engine_type)
            logger.info("配置已更新")

    def _translate(self, text: str) -> None:
        self._translating = True
        source_lang = LanguageDetector.detect(text)
        target_lang = self._config.target_lang

        if source_lang == target_lang:
            target_lang = "en" if target_lang == "zh" else "zh"
            logger.info("语言自动反向: %s -> %s", source_lang, target_lang)

        self._floating_window.show_translation(
            source_text=text,
            result="翻译中...",
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self._engine.translate(text, source_lang, target_lang)

    def _on_result_ready(self, result: str) -> None:
        self._translating = False
        self._floating_window.set_result(result)

    def _on_error_occurred(self, error: str) -> None:
        self._translating = False
        self._floating_window.show_error(error)


FloatingTranslatorApp._read_primary_selection._warned = False


def main() -> None:
    setup_logging()
    logger.info("FloatingTranslator 启动")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("FloatingTranslator")
    app.setQuitOnLastWindowClosed(False)

    style_path = os.path.join(BASE_DIR, "resources", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    translator = FloatingTranslatorApp()

    logger.info("应用已启动，鼠标划选文字即可翻译...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
