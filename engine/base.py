"""翻译引擎抽象基类——所有引擎必须在 QThread 中执行翻译并通过信号返回结果。"""
from __future__ import annotations

import logging
from abc import ABC, ABCMeta, abstractmethod

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    pass


class _QABCMeta(type(QObject), ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        abstracts = set()
        for base in bases:
            for attr_name, attr_value in base.__dict__.items():
                if getattr(attr_value, "__isabstractmethod__", False):
                    abstracts.add(attr_name)
            abstracts.update(getattr(base, "__abstractmethods__", ()))
        for attr_name, attr_value in namespace.items():
            if getattr(attr_value, "__isabstractmethod__", False):
                abstracts.add(attr_name)
            else:
                abstracts.discard(attr_name)
        cls.__abstractmethods__ = frozenset(abstracts)
        return cls

    def __call__(cls, *args, **kwargs):
        if getattr(cls, "__abstractmethods__", None):
            raise TypeError(
                f"Can't instantiate abstract class {cls.__name__} "
                f"without an implementation for abstract "
                f"{'methods' if len(cls.__abstractmethods__) > 1 else 'method'}: "
                f"{', '.join(sorted(cls.__abstractmethods__))}"
            )
        return super().__call__(*args, **kwargs)


class TranslationEngine(QObject, ABC, metaclass=_QABCMeta):
    result_ready = Signal(str)
    error_occurred = Signal(str)

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
        if not hasattr(self, '_thread') or self._thread is None:
            return
        for signal_name in ('result_ready', 'error_occurred'):
            try:
                getattr(self._thread, signal_name).disconnect()
            except (RuntimeError, TypeError):
                pass
