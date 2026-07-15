"""本地模型翻译引擎——支持 Ollama 和 llama-cpp-python，同样支持角色设定。"""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from engine.base import TranslationEngine

logger = logging.getLogger(__name__)


class LocalModelEngine(TranslationEngine):
    def __init__(
        self,
        model_type: str = "ollama",
        model_path: str = "",
        system_prompt: str = "你是一个专业的翻译助手，请准确、简洁地翻译用户输入的内容。",
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
            if self._model_type == "ollama":
                self._run_ollama()
            elif self._model_type == "llama_cpp":
                self._run_llama_cpp()
            else:
                self.error_occurred.emit(f"不支持的本地模型类型: {self._model_type}")
        except Exception as e:
            logger.exception("本地模型翻译异常")
            self.error_occurred.emit(f"本地模型翻译失败: {e}")

    def _run_ollama(self) -> None:
        try:
            import ollama

            prompt = (
                f"{self._system_prompt}\n\n"
                f"将以下{self._source_lang}文本翻译成{self._target_lang}：\n\n{self._text}"
            )

            response = ollama.chat(
                model=self._model_path,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response["message"]["content"]
            if result:
                self.result_ready.emit(result.strip())
            else:
                self.error_occurred.emit("Ollama 未返回翻译结果")
        except ImportError:
            self.error_occurred.emit("ollama 库未安装，请执行 pip install ollama")
        except Exception as e:
            self.error_occurred.emit(f"Ollama 翻译失败: {e}")

    def _run_llama_cpp(self) -> None:
        try:
            from llama_cpp import Llama

            llm = Llama(model_path=self._model_path, n_ctx=2048, verbose=False)
            prompt = (
                f"{self._system_prompt}\n\n"
                f"将以下{self._source_lang}文本翻译成{self._target_lang}：\n\n{self._text}"
            )
            output = llm(prompt, max_tokens=512, temperature=0.3)
            result = output["choices"][0]["text"].strip()
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
