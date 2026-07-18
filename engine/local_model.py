"""本地模型翻译引擎——基于 llama-cpp-python 加载 GGUF 模型，同样支持角色设定。"""
from __future__ import annotations

import logging
import os
import threading

from PySide6.QtCore import QThread, Signal

from engine.base import TranslationEngine

logger = logging.getLogger(__name__)

_llm_lock = threading.Lock()
_llm_cache: dict[str, object] = {}


def _get_llama(model_path: str):
    path = os.path.expanduser(model_path)
    if path not in _llm_cache:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"模型文件不存在: {path}")
        from llama_cpp import Llama

        logger.info("加载 GGUF 模型: %s", path)
        _llm_cache[path] = Llama(
            model_path=path, n_ctx=2048, verbose=False
        )
    return _llm_cache[path]


class LocalModelEngine(TranslationEngine):
    def __init__(
        self,
        model_type: str = "llama_cpp",
        model_path: str = "",
        system_prompt: str = "你是一个专业的翻译助手，直接输出翻译结果，不要解释、不要补充、不要聊天。",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model_type = model_type
        self._model_path = model_path
        self._system_prompt = system_prompt

    @property
    def engine_name(self) -> str:
        return f"Local ({self._model_type}:{self._model_path})"

    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        if not text or not text.strip():
            self._emit_error("待翻译文本为空")
            return

        self._detach_previous_thread()

        self._thread = _LocalTranslateThread(
            model_type=self._model_type,
            model_path=self._model_path,
            system_prompt=self._system_prompt,
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self._thread.result_ready.connect(self._emit_result)
        self._thread.error_occurred.connect(self._emit_error)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()


class _LocalTranslateThread(QThread):
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        model_type: str,
        model_path: str,
        system_prompt: str,
        text: str,
        source_lang: str,
        target_lang: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model_type = model_type
        self._model_path = model_path
        self._system_prompt = system_prompt
        self._text = text
        self._source_lang = source_lang
        self._target_lang = target_lang

    def run(self) -> None:
        try:
            if self._model_type == "llama_cpp":
                self._run_llama_cpp()
            else:
                self.error_occurred.emit(f"不支持的本地模型类型: {self._model_type}")
        except Exception as e:
            logger.exception("本地模型翻译异常")
            self.error_occurred.emit(f"本地模型翻译失败: {e}")

    def _run_llama_cpp(self) -> None:
        try:
            with _llm_lock:
                llm = _get_llama(self._model_path)
                output = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"将以下{self._source_lang}文本翻译成"
                                f"{self._target_lang}：\n\n{self._text}"
                            ),
                        },
                    ],
                    max_tokens=512,
                    temperature=0.3,
                )
            result = output["choices"][0]["message"]["content"].strip()
            if result:
                self.result_ready.emit(result)
            else:
                self.error_occurred.emit("llama.cpp 未返回翻译结果")
        except ImportError:
            self.error_occurred.emit(
                "llama-cpp-python 库未安装，请执行 pip install llama-cpp-python"
            )
        except Exception as e:
            self.error_occurred.emit(f"llama.cpp 翻译失败: {e}")
