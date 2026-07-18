from unittest.mock import patch, MagicMock
import pytest

from engine.free_online import FreeOnlineEngine


class TestFreeOnlineEngine:
    def test_engine_name(self, qtbot):
        engine = FreeOnlineEngine()
        assert engine.engine_name == "MyMemory"

    def test_translate_emits_result(self, qtbot):
        engine = FreeOnlineEngine()
        mock_response = {"responseData": {"translatedText": "你好世界"}}

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            with qtbot.waitSignal(engine.result_ready, timeout=3000) as blocker:
                engine.translate("Hello world", "en", "zh")
            assert blocker.args[0] == "你好世界"
        self._cleanup_thread(engine)

    def test_translate_emits_error_on_network_failure(self, qtbot):
        engine = FreeOnlineEngine()
        with patch("requests.get", side_effect=Exception("Network error")):
            with qtbot.waitSignal(engine.error_occurred, timeout=3000) as blocker:
                engine.translate("Hello", "en", "zh")
            assert "Network error" in blocker.args[0]
        self._cleanup_thread(engine)

    def test_translate_emits_error_on_bad_response(self, qtbot):
        engine = FreeOnlineEngine()
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=500,
                json=lambda: {"error": "Server error"},
            )
            with qtbot.waitSignal(engine.error_occurred, timeout=3000) as blocker:
                engine.translate("Hello", "en", "zh")
            assert "500" in blocker.args[0]
        self._cleanup_thread(engine)

    @staticmethod
    def _cleanup_thread(engine):
        if hasattr(engine, "_thread") and engine._thread is not None:
            try:
                engine._thread.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            if engine._thread.isRunning():
                engine._thread.wait(3000)
            engine._thread = None
