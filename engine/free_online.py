"""MyMemory 免费在线翻译引擎——无需 API Key，通过 REST API 翻译。"""
from __future__ import annotations

import logging

import requests

from engine.base import TranslationEngine, _TranslateWorker

logger = logging.getLogger(__name__)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"


class FreeOnlineEngine(TranslationEngine):
    @property
    def engine_name(self) -> str:
        return "MyMemory"

    def _create_worker(self, text: str, source_lang: str, target_lang: str) -> _TranslateWorker:
        lang_pair = f"{source_lang}|{target_lang}"
        return _TranslateThread(
            url=MYMEMORY_URL,
            text=text,
            lang_pair=lang_pair,
        )


class _TranslateThread(_TranslateWorker):
    def __init__(
        self, url: str, text: str, lang_pair: str, parent=None
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._text = text
        self._lang_pair = lang_pair

    def run(self) -> None:
        try:
            params = {"q": self._text, "langpair": self._lang_pair}
            resp = requests.get(self._url, params=params, timeout=10)
            if resp.status_code != 200:
                self.error_occurred.emit(
                    f"MyMemory API 返回 HTTP {resp.status_code}"
                )
                return
            data = resp.json()
            result = data.get("responseData", {}).get("translatedText", "")
            if result:
                self.result_ready.emit(result)
            else:
                self.error_occurred.emit("MyMemory 未返回翻译结果")
        except requests.RequestException as e:
            self.error_occurred.emit(f"网络请求失败: {e}")
        except Exception as e:
            self.error_occurred.emit(f"翻译异常: {e}")
