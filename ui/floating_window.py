"""悬浮翻译窗口——无边框、置顶、半透明、鼠标跟随。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QCursor, QFont, QFontMetrics, QMouseEvent
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


class FloatingWindow(QWidget):
    close_requested = Signal()

    def __init__(
        self, opacity: float = 0.92, parent=None
    ) -> None:
        super().__init__(parent)
        self._dragging = False
        self._drag_pos = None
        self._track_timer: QTimer | None = None

        self._auto_hide_seconds = 0
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.close_requested.emit)

        self._xd = None
        try:
            from Xlib import display as xdisplay
            self._xd = xdisplay.Display()
        except Exception:
            pass

        self._setup_ui()
        self._setup_window(opacity)

    def _setup_window(self, opacity: float) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowOpacity(opacity)

    def _setup_ui(self) -> None:
        self.setFixedWidth(WINDOW_WIDTH)
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
        self._source_text.setMinimumHeight(0)
        self._source_text.setStyleSheet(
            "color: #aaa; font-size: 12px; background: transparent;"
            "border: none; border-left: 2px solid #5af;"
        )
        self._source_text.setVisible(False)
        layout.addWidget(self._source_text)

        self._result_label = QLabel("翻译结果将在此处显示")
        self._result_label.setWordWrap(True)
        self._result_label.setMinimumHeight(0)
        font = QFont()
        font.setPointSize(13)
        self._result_label.setFont(font)
        self._result_label.setStyleSheet(
            "color: #8f8; font-size: 13px; background: transparent;"
            "border: none; border-left: 2px solid #8f8;"
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
        self._fit_content()
        self._follow_cursor()
        self._reset_auto_hide()
        self.show()

    def show_error(self, error: str) -> None:
        self._error_label.setText(f"\u26a0 {error}")
        self._error_label.setVisible(True)
        self._result_label.setText("")
        self._source_text.setVisible(False)
        self._fit_content()
        self._follow_cursor()
        self._reset_auto_hide()
        self.show()

    def clear_content(self) -> None:
        self._source_label.setText("原文")
        self._source_text.clear()
        self._source_text.setVisible(False)
        self._direction_label.setText("")
        self._result_label.setText("翻译结果将在此处显示")
        self._error_label.clear()
        self._error_label.setVisible(False)

    def start_tracking(self) -> None:
        self._track_timer = QTimer(self)
        self._track_timer.setInterval(50)
        self._track_timer.timeout.connect(self._follow_cursor)
        self._fit_content()
        self.show()
        self._track_timer.start()
        logger.info("鼠标追踪已启动")

    def set_auto_hide_seconds(self, seconds: int) -> None:
        self._auto_hide_seconds = seconds

    def set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(opacity)

    def set_result(self, text: str) -> None:
        self._result_label.setText(text)
        self._fit_content()

    def _reset_auto_hide(self) -> None:
        if self._auto_hide_seconds > 0:
            self._auto_hide_timer.start(self._auto_hide_seconds * 1000)
        else:
            self._auto_hide_timer.stop()

    def _fit_content(self) -> None:
        margins = self.layout().contentsMargins()
        spacing = self.layout().spacing()
        win_w = self.width()
        if win_w <= 0:
            win_w = WINDOW_WIDTH
        text_w = win_w - margins.left() - margins.right()

        h = margins.top() + margins.bottom()
        h += self._source_label.sizeHint().height() + spacing

        if self._source_text.isVisible():
            src_h = self._label_height(self._source_text, text_w)
            self._source_text.setMinimumHeight(src_h)
            self._source_text.setMaximumHeight(src_h)
            h += src_h + spacing

        result_h = self._label_height(self._result_label, text_w)
        self._result_label.setMinimumHeight(result_h)
        self._result_label.setMaximumHeight(result_h)
        h += result_h

        if self._error_label.isVisible():
            h += spacing + self._error_label.sizeHint().height()
        self.adjustSize()
        self.repaint()

    @staticmethod
    def _label_height(label: QLabel, width: int) -> int:
        text = label.text() or " "
        fm = QFontMetrics(label.font())
        rect = fm.boundingRect(
            QRect(0, 0, max(width, 50), 0),
            Qt.TextFlag.TextWordWrap,
            text,
        )
        line_spacing = fm.lineSpacing()
        raw_h = max(rect.height(), 1)
        lines = max(1, int(raw_h / max(line_spacing, 1)))
        return lines * line_spacing + 24

    def _follow_cursor(self) -> None:
        if self._dragging:
            return
        if self._xd is not None:
            try:
                data = self._xd.screen().root.query_pointer()
                cx, cy = data.root_x, data.root_y
            except Exception:
                p = QCursor.pos()
                cx, cy = p.x(), p.y()
        else:
            p = QCursor.pos()
            cx, cy = p.x(), p.y()

        cursor_global = QPoint(cx, cy)
        screen = QApplication.screenAt(cursor_global)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()

        x = cx + 16
        y = cy + 16

        if x + self.width() > screen_geom.right():
            x = screen_geom.right() - self.width() - 8
        if y + self.height() > screen_geom.bottom():
            y = cy - self.height() - 16
        if x < screen_geom.left():
            x = screen_geom.left() + 8
        if y < screen_geom.top():
            y = screen_geom.top() + 8

        old_x, old_y = self.x(), self.y()
        if abs(old_x - x) > 2 or abs(old_y - y) > 2:
            self.move(x, y)
            self.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._auto_hide_timer.stop()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._drag_pos = None
        self._reset_auto_hide()

    def closeEvent(self, event) -> None:
        if self._xd is not None:
            self._xd.close()
            self._xd = None
        super().closeEvent(event)
