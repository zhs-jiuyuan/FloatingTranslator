"""悬浮翻译窗口——无边框、置顶、半透明、自动隐藏。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 380
WINDOW_MAX_HEIGHT = 300


class FloatingWindow(QWidget):
    close_requested = Signal()

    def __init__(
        self, opacity: float = 0.92, parent=None
    ) -> None:
        super().__init__(parent)
        self._opacity = opacity
        self._dragging = False
        self._drag_pos = None

        self._mouse_track_timer = QTimer(self)
        self._mouse_track_timer.setInterval(50)
        self._mouse_track_timer.timeout.connect(self._position_near_cursor)

        self._setup_ui()
        self._setup_window_flags()

    def _setup_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setWindowOpacity(self._opacity)

    def _setup_ui(self) -> None:
        self.setFixedWidth(WINDOW_WIDTH)
        self.setMaximumHeight(WINDOW_MAX_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setStyleSheet(
            """
            FloatingWindow {
                background-color: rgba(20, 20, 20, 235);
                border-radius: 10px;
                border: 1px solid #333;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._source_label = QLabel("原文")
        self._source_label.setStyleSheet(
            "color: #888; font-size: 11px; font-weight: bold; background: transparent;"
        )
        header.addWidget(self._source_label)

        self._direction_label = QLabel("")
        self._direction_label.setStyleSheet(
            "color: #666; font-size: 10px; background: transparent;"
        )
        header.addWidget(self._direction_label)

        header.addStretch()

        close_btn = QLabel("✕")
        close_btn.setStyleSheet(
            "color: #555; font-size: 14px; background: transparent; padding: 2px;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close_requested.emit()
        header.addWidget(close_btn)

        layout.addLayout(header)

        self._source_text = QLabel("")
        self._source_text.setWordWrap(True)
        self._source_text.setStyleSheet(
            "color: #aaa; font-size: 12px; background: transparent;"
            "padding: 6px 8px; border-left: 2px solid #5af;"
        )
        self._source_text.setVisible(False)
        layout.addWidget(self._source_text)

        self._result_label = QLabel("翻译结果将在此处显示")
        self._result_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(13)
        self._result_label.setFont(font)
        self._result_label.setStyleSheet(
            "color: #8f8; font-size: 13px; background: transparent;"
            "padding: 8px 10px; border-left: 2px solid #8f8;"
        )
        layout.addWidget(self._result_label)

        self._error_label = QLabel("")
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "color: #f55; font-size: 11px; background: transparent; padding: 4px 8px;"
        )
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

    def show_translation(
        self, source_text: str, result: str, source_lang: str, target_lang: str
    ) -> None:
        self._source_text.setText(source_text)
        self._source_text.setVisible(bool(source_text.strip()))
        self._source_label.setText("原文" if source_lang.startswith("zh") else "Source")

        self._direction_label.setText(f"{source_lang} → {target_lang}")
        self._result_label.setText(result)
        self._error_label.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()

    def show_error(self, error: str) -> None:
        self._error_label.setText(f"⚠ {error}")
        self._error_label.setVisible(True)
        self._result_label.setText("")
        self._source_text.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()

    def show_placeholder(self, text: str = "") -> None:
        display = text or "翻译结果将在此处显示"
        self._source_text.setVisible(False)
        self._direction_label.setText("")
        self._result_label.setText(display)
        self._error_label.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()

    def _position_near_cursor(self) -> None:
        screen = QApplication.screenAt(self.cursor().pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()

        cursor_pos = self.cursor().pos()
        x = cursor_pos.x() + 16
        y = cursor_pos.y() + 16

        if x + self.width() > screen_geom.right():
            x = screen_geom.right() - self.width() - 8
        if y + self.height() > screen_geom.bottom():
            y = cursor_pos.y() - self.height() - 8
        if x < screen_geom.left():
            x = screen_geom.left() + 8
        if y < screen_geom.top():
            y = screen_geom.top() + 8

        self.move(x, y)

    def clear_content(self) -> None:
        self._source_text.clear()
        self._source_text.setVisible(False)
        self._direction_label.setText("")
        self._result_label.setText("翻译结果将在此处显示")
        self._error_label.clear()
        self._error_label.setVisible(False)

    def start_tracking(self) -> None:
        self._position_near_cursor()
        self.show()
        self._mouse_track_timer.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._drag_pos = None
