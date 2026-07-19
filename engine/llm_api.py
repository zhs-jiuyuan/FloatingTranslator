"""大模型 API 翻译引擎——兼容 OpenAI / DeepSeek 等 API，支持角色提示词。"""
from __future__ import annotations

import logging

from engine.base import TranslationEngine, _TranslateWorker
from config import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMAPIEngine(TranslationEngine):
    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._api_key = api_key
        self._api_url = api_url
        self._model = model
        self._system_prompt = system_prompt

    @property
    def engine_name(self) -> str:
        return f"LLM ({self._model})"

    def _create_worker(self, text: str, source_lang: str, target_lang: str) -> _TranslateWorker:
        return _LLMTranslateThread(
            api_key=self._api_key,
            api_url=self._api_url,
            model=self._model,
            system_prompt=self._system_prompt,
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )


class _LLMTranslateThread(_TranslateWorker):
    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str,
        system_prompt: str,
        text: str,
        source_lang: str,
        target_lang: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._api_key = api_key
        self._api_url = api_url
        self._model = model
        self._system_prompt = system_prompt
        self._text = text
        self._source_lang = source_lang
        self._target_lang = target_lang

    def run(self) -> None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key, base_url=self._api_url)

            user_message = (
                f"将以下{self._source_lang}文本翻译成{self._target_lang}：\n\n{self._text}"
            )

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
            )

            result = response.choices[0].message.content
            if result:
                self.result_ready.emit(result.strip())
            else:
                self.error_occurred.emit("LLM 未返回翻译结果")
        except ImportError:
            self.error_occurred.emit("openai 库未安装，请执行 pip install openai")
        except Exception as e:
            logger.exception("LLM API 翻译异常")
            self.error_occurred.emit(f"LLM 翻译失败: {e}")
