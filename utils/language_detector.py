"""语言检测模块——基于字符集快速判断，langdetect 兜底。"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class LanguageDetector:
    CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
    HIRAGANA_RE = re.compile(r"[\u3040-\u309f]")
    KATAKANA_RE = re.compile(r"[\u30a0-\u30ff]")
    HANGUL_RE = re.compile(r"[\uac00-\ud7af]")

    @classmethod
    def detect(cls, text: str) -> str:
        if not text or not text.strip():
            return "en"

        if cls.HANGUL_RE.search(text):
            logger.debug("检测到韩文字符")
            return "ko"
        if cls.HIRAGANA_RE.search(text) or cls.KATAKANA_RE.search(text):
            logger.debug("检测到日文字符")
            return "ja"
        if cls.CJK_RE.search(text):
            logger.debug("检测到 CJK 字符，判断为中文")
            return "zh"

        try:
            text.encode("ascii")
            logger.debug("纯 ASCII 文本，判断为英文")
            return "en"
        except UnicodeEncodeError:
            pass

        try:
            from langdetect import detect
            result = detect(text)
            logger.debug("langdetect 检测结果: %s", result)
            return result
        except Exception:
            logger.debug("langdetect 检测失败，默认返回 en")
            return "en"
