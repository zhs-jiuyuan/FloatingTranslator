"""引擎基类测试"""
import pytest
from PySide6.QtCore import QThread

from engine.base import TranslationEngine, _TranslateWorker


class _SimpleWorker(_TranslateWorker):
    def __init__(self, result_text="ok", should_fail=False, parent=None):
        super().__init__(parent)
        self._result = result_text
        self._should_fail = should_fail

    def run(self):
        if self._should_fail:
            self.error_occurred.emit("test error")
        else:
            self.result_ready.emit(self._result)


class _TestEngine(TranslationEngine):
    def __init__(self, result="ok", should_fail=False, parent=None):
        super().__init__(parent)
        self._result = result
        self._should_fail = should_fail

    @property
    def engine_name(self) -> str:
        return "TestEngine"

    def _create_worker(self, text, source_lang, target_lang):
        return _SimpleWorker(
            result_text=self._result,
            should_fail=self._should_fail,
        )


class TestTranslateWorker:
    def test_worker_has_signals(self):
        worker = _SimpleWorker()
        assert hasattr(worker, "result_ready")
        assert hasattr(worker, "error_occurred")


class TestTranslationEngine:
    def test_translate_emits_result(self, qtbot):
        engine = _TestEngine(result="hello")
        with qtbot.waitSignal(engine.result_ready, timeout=3000) as blocker:
            engine.translate("test", "en", "zh")
        assert blocker.args[0] == "hello"

    def test_translate_emits_error(self, qtbot):
        engine = _TestEngine(should_fail=True)
        with qtbot.waitSignal(engine.error_occurred, timeout=3000) as blocker:
            engine.translate("test", "en", "zh")
        assert blocker.args[0] == "test error"

    def test_translate_empty_text(self, qtbot):
        engine = _TestEngine()
        with qtbot.waitSignal(engine.error_occurred, timeout=3000) as blocker:
            engine.translate("", "en", "zh")
        assert "为空" in blocker.args[0]

    def test_thread_cleaned_up_after_translate(self, qtbot):
        engine = _TestEngine()
        with qtbot.waitSignal(engine.result_ready, timeout=3000):
            engine.translate("test", "en", "zh")
        qtbot.wait(500)
        try:
            running = engine._thread.isRunning()
        except RuntimeError:
            running = False
        assert engine._thread is None or not running

    def test_consecutive_translate_no_signal_leak(self, qtbot):
        engine = _TestEngine()
        results = []
        engine.result_ready.connect(results.append)
        engine.translate("first", "en", "zh")
        qtbot.wait(500)
        engine.translate("second", "en", "zh")
        qtbot.wait(500)
        assert len(results) == 2
