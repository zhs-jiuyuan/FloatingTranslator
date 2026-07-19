"""翻译引擎抽象基类——所有引擎必须在 QThread 中执行翻译并通过信号返回结果。"""
from __future__ import annotations

import logging
from abc import ABC, ABCMeta, abstractmethod

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)


class _QABCMeta(ABCMeta, type(QObject)):
    pass


class TranslationEngine(QObject, ABC, metaclass=_QABCMeta):
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        ...

    @property
    @abstractmethod
    def engine_name(self) -> str:
        ...

    def _emit_result(self, result: str) -> None:
        logger.info("[%s] 翻译成功: %s...", self.engine_name, result[:50])
        self.result_ready.emit(result)

    def _emit_error(self, error: str) -> None:
        logger.error("[%s] 翻译失败: %s", self.engine_name, error)
        self.error_occurred.emit(error)

    def _detach_previous_thread(self) -> None:
        if self._thread is None:
            return
        try:
            self._thread.result_ready.disconnect()
        except (RuntimeError, TypeError):
            logger.debug("result_ready 信号未连接，跳过断开")
        try:
            self._thread.error_occurred.disconnect()
        except (RuntimeError, TypeError):
            logger.debug("error_occurred 信号未连接，跳过断开")
        try:
            self._thread.finished.disconnect()
        except (RuntimeError, TypeError):
            logger.debug("finished 信号未连接，跳过断开")
        if self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(3000):
                logger.warning("上一翻译线程未能在3秒内退出")
        self._thread.deleteLater()
