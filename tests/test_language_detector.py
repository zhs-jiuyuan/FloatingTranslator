import pytest
from utils.language_detector import LanguageDetector


class TestLanguageDetector:
    @pytest.mark.parametrize("text,expected", [
        ("hello world how are you", "en"),
        ("你好世界今天天气真好", "zh"),
        ("こんにちは世界", "ja"),
        ("안녕하세요 세계", "ko"),
        ("this is an english text", "en"),
    ])
    def test_detect_by_charset(self, text, expected):
        result = LanguageDetector.detect(text)
        assert result == expected

    def test_detect_empty_text(self):
        assert LanguageDetector.detect("") == "en"

    def test_detect_mixed_cjk_defaults_to_zh(self):
        result = LanguageDetector.detect("hello 你好 world")
        assert result == "zh"
