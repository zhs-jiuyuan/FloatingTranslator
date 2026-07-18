import pytest

from engine.local_model import _get_llama


class TestGetLlama:
    def test_missing_file_raises_friendly_error(self, tmp_path):
        missing = str(tmp_path / "nope.gguf")
        with pytest.raises(FileNotFoundError, match="模型文件不存在"):
            _get_llama(missing)

    def test_tilde_expanded_before_check(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        with pytest.raises(FileNotFoundError, match=str(tmp_path)):
            _get_llama("~/missing.gguf")
