"""系统托盘图标与右键菜单。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from config import AppConfig

logger = logging.getLogger(__name__)


class TrayIcon(QSystemTrayIcon):
    engine_changed = Signal(str)
    settings_requested = Signal()
    translate_requested = Signal()

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._engine_actions: dict[str, QAction] = {}

        icon = self._create_icon()
        self.setIcon(icon)
        self.setToolTip("FloatingTranslator")

        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _create_icon(self) -> QIcon:
        from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#5af"))
        painter.setPen(QColor("#5af"))
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QColor("#141414"))
        font = QFont("sans-serif", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        menu = QMenu()

        engine_menu = menu.addMenu("切换引擎")
        for key, label in [
            ("free_online", "免费在线 (MyMemory)"),
            ("llm_api", "大模型 API"),
            ("local_model", "本地模型"),
        ]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(key == self._config.engine_type)
            action.triggered.connect(lambda checked, k=key: self.engine_changed.emit(k))
            engine_menu.addAction(action)
            self._engine_actions[key] = action

        menu.addSeparator()

        translate_action = QAction("手动翻译 (读取剪贴板)", self)
        translate_action.triggered.connect(self.translate_requested.emit)
        menu.addAction(translate_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def update_engine_check(self, engine_type: str) -> None:
        for key, action in self._engine_actions.items():
            action.setChecked(key == engine_type)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.translate_requested.emit()

    def show_message(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
