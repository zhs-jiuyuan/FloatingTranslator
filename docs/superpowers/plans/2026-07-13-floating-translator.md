# FloatingTranslator 实现计划

> **面向 AI 代理的工作者：** 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 从零搭建 FloatingTranslator 桌面划词翻译器脚手架，main.py 可直接启动并弹出悬浮翻译窗。

**架构：** QThread + 信号槽驱动，main.py 作为依赖注入中心，连接热键→文本获取→语言检测→翻译引擎→悬浮窗。自底向上构建：工具模块 → 引擎 → UI → 入口。

**技术栈：** Python 3.10+, PySide6, dataclasses, QThread, logging

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `requirements.txt` | 第三方依赖清单 |
| `config.py` | AppConfig 数据模型 + ConfigManager JSON 读写 |
| `engine/__init__.py` | 包初始化 |
| `engine/base.py` | TranslationEngine 抽象基类 (QObject + Signal) |
| `engine/free_online.py` | MyMemory 免费翻译引擎 |
| `engine/llm_api.py` | LLM API 引擎（openai 兼容） |
| `engine/local_model.py` | 本地模型引擎（ollama/llama-cpp） |
| `ui/__init__.py` | 包初始化 |
| `ui/floating_window.py` | 悬浮翻译窗（无边框、置顶、半透明） |
| `ui/tray_icon.py` | 系统托盘图标 + 右键菜单 |
| `ui/settings_dialog.py` | 设置对话框 |
| `utils/__init__.py` | 包初始化 |
| `utils/hotkey.py` | 全局热键管理器（Win/Linux 双后端） |
| `utils/text_selector.py` | 剪贴板获取选中文本 + 还原 |
| `utils/language_detector.py` | 语言检测 + 自动反向 |
| `resources/style.qss` | 全局暗色 QSS 样式表 |
| `main.py` | 应用入口，组装所有组件 |

---

### 任务 1：项目基础设施

**文件：**
- 创建：`requirements.txt`
- 创建：`engine/__init__.py`
- 创建：`ui/__init__.py`
- 创建：`utils/__init__.py`
- 创建：`logs/.gitkeep`

- [ ] **步骤 1：编写 requirements.txt**

```
PySide6>=6.5.0
keyboard>=0.13.5
pynput>=1.7.6
pyperclip>=1.8.2
pyautogui>=0.9.54
langdetect>=1.0.9
openai>=1.0.0
ollama>=0.1.0
requests>=2.28.0
```

- [ ] **步骤 2：创建空的 __init__.py 文件**

```bash
touch engine/__init__.py ui/__init__.py utils/__init__.py logs/.gitkeep
```

- [ ] **步骤 3：安装依赖**

运行：`conda run -n spider pip install -r requirements.txt`

- [ ] **步骤 4：Commit**

```bash
git add requirements.txt engine/__init__.py ui/__init__.py utils/__init__.py logs/.gitkeep
git commit -m "chore: 项目基础设施 — 依赖清单与包初始化"
```

---

### 任务 2：config.py — 配置数据模型

**文件：**
- 创建：`config.py`
- 创建：`tests/test_config.py`

- [ ] **步骤 1：编写测试**

```python
# tests/test_config.py
import json
import os
import tempfile
import pytest
from config import AppConfig, ConfigManager


class TestAppConfig:
    def test_default_values(self):
        cfg = AppConfig()
        assert cfg.target_lang == "zh"
        assert cfg.source_lang == "auto"
        assert cfg.engine_type == "free_online"
        assert cfg.hotkey == "ctrl+q"
        assert cfg.opacity == 0.92
        assert cfg.auto_hide_seconds == 5
        assert cfg.llm_api_key == ""
        assert cfg.llm_api_url == "https://api.openai.com/v1"
        assert cfg.llm_model == "gpt-3.5-turbo"
        assert cfg.local_model_type == "ollama"
        assert cfg.local_model_path == ""

    def test_custom_values(self):
        cfg = AppConfig(
            target_lang="en",
            engine_type="llm_api",
            llm_api_key="sk-test",
            llm_model="gpt-4",
        )
        assert cfg.target_lang == "en"
        assert cfg.engine_type == "llm_api"
        assert cfg.llm_api_key == "sk-test"
        assert cfg.llm_model == "gpt-4"


class TestConfigManager:
    def test_save_and_load(self):
        cfg = AppConfig(target_lang="ja", engine_type="local_model")
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            path = f.name
        try:
            ConfigManager.save(cfg, path)
            loaded = ConfigManager.load(path)
            assert loaded.target_lang == "ja"
            assert loaded.engine_type == "local_model"
        finally:
            os.unlink(path)

    def test_load_nonexistent_file_returns_default(self):
        cfg = ConfigManager.load("/nonexistent/path/config.json")
        assert isinstance(cfg, AppConfig)
        assert cfg.target_lang == "zh"

    def test_load_corrupted_json_returns_default(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("not valid json{{{")
            path = f.name
        try:
            cfg = ConfigManager.load(path)
            assert isinstance(cfg, AppConfig)
            assert cfg.target_lang == "zh"
        finally:
            os.unlink(path)

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "config.json")
            cfg = AppConfig()
            ConfigManager.save(cfg, path)
            assert os.path.exists(path)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`conda run -n spider python -m pytest tests/test_config.py -v`
预期：FAIL, `ModuleNotFoundError: No module named 'config'`

- [ ] **步骤 3：实现 config.py**

```python
"""配置数据模型与 JSON 持久化。"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    target_lang: str = "zh"
    source_lang: str = "auto"
    engine_type: str = "free_online"
    hotkey: str = "ctrl+q"
    opacity: float = 0.92
    auto_hide_seconds: int = 5

    llm_api_key: str = ""
    llm_api_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    llm_system_prompt: str = "你是一个专业的翻译助手，请准确、简洁地翻译用户输入的内容。"

    local_model_type: str = "ollama"
    local_model_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class ConfigManager:
    @staticmethod
    def load(path: str) -> AppConfig:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = AppConfig.from_dict(data)
            logger.info("配置已从 %s 加载", path)
            return cfg
        except FileNotFoundError:
            logger.info("配置文件 %s 不存在，使用默认配置", path)
            return AppConfig()
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("配置文件 %s 解析失败: %s，使用默认配置", path, e)
            return AppConfig()

    @staticmethod
    def save(config: AppConfig, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("配置已保存到 %s", path)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`conda run -n spider python -m pytest tests/test_config.py -v`
预期：5 PASSED

- [ ] **步骤 5：Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: 配置数据模型 AppConfig + ConfigManager JSON 读写"
```

---

### 任务 3：utils/language_detector.py — 语言检测

**文件：**
- 创建：`utils/language_detector.py`
- 创建：`tests/test_language_detector.py`

- [ ] **步骤 1：编写测试**

```python
# tests/test_language_detector.py
import pytest
from utils.language_detector import LanguageDetector


class TestLanguageDetector:
    @pytest.mark.parametrize("text,expected", [
        ("hello world how are you", "en"),
        ("你好世界今天天气真好", "zh"),
        ("こんにちは世界", "ja"),
        ("안녕하세요 세계", "ko"),
        ("Bonjour le monde", "en"),
    ])
    def test_detect_by_charset(self, text, expected):
        result = LanguageDetector.detect(text)
        assert result == expected

    def test_detect_empty_text(self):
        assert LanguageDetector.detect("") == "en"

    def test_detect_mixed_cjk_defaults_to_zh(self):
        result = LanguageDetector.detect("hello 你好 world")
        assert result == "zh"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`conda run -n spider python -m pytest tests/test_language_detector.py -v`

- [ ] **步骤 3：实现 utils/language_detector.py**

```python
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
            from langdetect import detect
            result = detect(text)
            logger.debug("langdetect 检测结果: %s", result)
            return result
        except Exception:
            logger.debug("langdetect 检测失败，默认返回 en")
            return "en"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`conda run -n spider python -m pytest tests/test_language_detector.py -v`
预期：7 PASSED

- [ ] **步骤 5：Commit**

```bash
git add utils/language_detector.py tests/test_language_detector.py
git commit -m "feat: 语言检测模块 — 字符集判断 + langdetect 兜底"
```

---

### 任务 4：utils/text_selector.py — 选中文本获取

**文件：**
- 创建：`utils/text_selector.py`

- [ ] **步骤 1：实现 utils/text_selector.py**

```python
"""获取用户选中的文本——通过模拟 Ctrl+C 复制并还原剪贴板。"""
from __future__ import annotations

import logging
import time

import pyautogui
import pyperclip

logger = logging.getLogger(__name__)


class TextSelector:
    COPY_DELAY = 0.15

    @classmethod
    def get_selected_text(cls) -> str:
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = ""
            logger.debug("无法读取剪贴板原始内容")

        try:
            pyautogui.hotkey("ctrl", "c")
            time.sleep(cls.COPY_DELAY)
            text = pyperclip.paste()
        except Exception as e:
            logger.error("模拟 Ctrl+C 复制失败: %s", e)
            text = ""
        finally:
            try:
                pyperclip.copy(old_clipboard)
            except Exception as e:
                logger.debug("还原剪贴板失败: %s", e)

        if text and text.strip():
            logger.info("获取到选中文本: %s...", text[:50])
        else:
            logger.info("未获取到选中文本")
        return text.strip() if text else ""
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from utils.text_selector import TextSelector; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add utils/text_selector.py
git commit -m "feat: 文本选择器 — Ctrl+C 模拟复制 + 剪贴板还原"
```

---

### 任务 5：utils/hotkey.py — 全局热键管理器

**文件：**
- 创建：`utils/hotkey.py`

- [ ] **步骤 1：实现 utils/hotkey.py**

```python
"""全局热键管理器——Windows 使用 keyboard 库，Linux 使用 pynput 库。
注意：Windows 上 keyboard 库需要管理员权限才能捕获全局按键。"""
from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, hotkey: str = "ctrl+q", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        if sys.platform == "win32":
            self._start_keyboard()
        else:
            self._start_pynput()

    def _start_keyboard(self) -> None:
        try:
            import keyboard
            keyboard.add_hotkey(self._hotkey, self._on_triggered)
            logger.info("热键 %s 已注册 (keyboard, Windows)", self._hotkey)
        except ImportError:
            logger.error("keyboard 库未安装，无法注册全局热键")
        except Exception as e:
            logger.error("注册热键失败 (keyboard): %s", e)

    def _start_pynput(self) -> None:
        try:
            from pynput import keyboard as pynput_keyboard
        except ImportError:
            logger.error("pynput 库未安装，无法注册全局热键")
            return

        hotkey_parts = self._hotkey.split("+")
        key_map = {
            "ctrl": pynput_keyboard.Key.ctrl,
            "ctrl_l": pynput_keyboard.Key.ctrl_l,
            "ctrl_r": pynput_keyboard.Key.ctrl_r,
            "shift": pynput_keyboard.Key.shift,
            "alt": pynput_keyboard.Key.alt,
        }
        current_keys: set = set()

        def on_press(key: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            current_keys.add(key)
            if self._check_combo(current_keys, key_map, hotkey_parts):
                self._on_triggered()

        def on_release(key: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            current_keys.discard(key)

        def run() -> None:
            logger.info("热键 %s 已注册 (pynput, Linux)", self._hotkey)
            with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def _check_combo(self, current_keys: set, key_map: dict, parts: list[str]) -> bool:
        required = set()
        for part in parts:
            if part in key_map:
                required.add(key_map[part])
            else:
                try:
                    from pynput.keyboard import KeyCode
                    required.add(KeyCode.from_char(part))
                except Exception:
                    pass
        return required and required.issubset(current_keys)

    def _on_triggered(self) -> None:
        logger.info("热键 %s 触发", self._hotkey)
        self.triggered.emit()

    def stop(self) -> None:
        self._running = False
        if sys.platform == "win32":
            try:
                import keyboard
                keyboard.remove_all_hotkeys()
                logger.info("热键已注销")
            except Exception:
                pass
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from utils.hotkey import HotkeyManager; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add utils/hotkey.py
git commit -m "feat: 全局热键管理器 — Win(keyboard)/Linux(pynput) 双后端"
```

---

### 任务 6：engine/base.py — 翻译引擎抽象基类

**文件：**
- 创建：`engine/base.py`

- [ ] **步骤 1：实现 engine/base.py**

```python
"""翻译引擎抽象基类——所有引擎必须在 QThread 中执行翻译并通过信号返回结果。"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    pass


class TranslationEngine(QObject, ABC):
    result_ready = Signal(str)
    error_occurred = Signal(str)

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        """在工作线程中执行翻译，完成后通过 result_ready 信号返回结果。
        若出错则通过 error_occurred 信号返回错误信息。

        Args:
            text: 待翻译文本
            source_lang: 源语言代码 (en/zh/ja/ko/auto)
            target_lang: 目标语言代码
        """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎显示名称。"""

    def _emit_result(self, result: str) -> None:
        logger.info("[%s] 翻译成功: %s...", self.engine_name, result[:50])
        self.result_ready.emit(result)

    def _emit_error(self, error: str) -> None:
        logger.error("[%s] 翻译失败: %s", self.engine_name, error)
        self.error_occurred.emit(error)
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from engine.base import TranslationEngine, TranslationError; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add engine/base.py
git commit -m "feat: 翻译引擎抽象基类 — QObject + 信号槽接口"
```

---

### 任务 7：engine/free_online.py — MyMemory 免费引擎

**文件：**
- 创建：`engine/free_online.py`
- 创建：`tests/test_free_online.py`

- [ ] **步骤 1：编写测试**

```python
# tests/test_free_online.py
from unittest.mock import patch, MagicMock
import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication([])

from engine.free_online import FreeOnlineEngine


class TestFreeOnlineEngine:
    def test_engine_name(self):
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

    def test_translate_emits_error_on_network_failure(self, qtbot):
        engine = FreeOnlineEngine()
        with patch("requests.get", side_effect=Exception("Network error")):
            with qtbot.waitSignal(engine.error_occurred, timeout=3000) as blocker:
                engine.translate("Hello", "en", "zh")
            assert "Network error" in blocker.args[0]

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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`conda run -n spider python -m pytest tests/test_free_online.py -v`
预期：FAIL (FreeOnlineEngine not defined)

- [ ] **步骤 3：实现 engine/free_online.py**

```python
"""MyMemory 免费在线翻译引擎——无需 API Key，通过 REST API 翻译。"""
from __future__ import annotations

import logging

import requests
from PySide6.QtCore import QThread

from engine.base import TranslationEngine, TranslationError

logger = logging.getLogger(__name__)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"


class FreeOnlineEngine(TranslationEngine):
    @property
    def engine_name(self) -> str:
        return "MyMemory"

    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        if not text or not text.strip():
            self._emit_error("待翻译文本为空")
            return

        lang_pair = f"{source_lang}|{target_lang}"
        if source_lang == "auto":
            lang_pair = f"|{target_lang}"

        self._thread = _TranslateThread(
            url=MYMEMORY_URL,
            text=text,
            lang_pair=lang_pair,
        )
        self._thread.result_ready.connect(self._emit_result)
        self._thread.error_occurred.connect(self._emit_error)
        self._thread.start()


class _TranslateThread(QThread):
    result_ready = Signal(str)
    error_occurred = Signal(str)

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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`conda run -n spider python -m pytest tests/test_free_online.py -v`
预期：4 PASSED

- [ ] **步骤 5：Commit**

```bash
git add engine/free_online.py tests/test_free_online.py
git commit -m "feat: MyMemory 免费翻译引擎 — QThread 异步翻译"
```

---

### 任务 8：engine/llm_api.py — 大模型 API 引擎

**文件：**
- 创建：`engine/llm_api.py`

- [ ] **步骤 1：实现 engine/llm_api.py**

```python
"""大模型 API 翻译引擎——兼容 OpenAI / DeepSeek 等 API，支持角色提示词。"""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from engine.base import TranslationEngine

logger = logging.getLogger(__name__)


class LLMAPIEngine(TranslationEngine):
    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        system_prompt: str = "你是一个专业的翻译助手，请准确、简洁地翻译用户输入的内容。",
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

    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        if not text or not text.strip():
            self._emit_error("待翻译文本为空")
            return

        self._thread = _LLMTranslateThread(
            api_key=self._api_key,
            api_url=self._api_url,
            model=self._model,
            system_prompt=self._system_prompt,
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self._thread.result_ready.connect(self._emit_result)
        self._thread.error_occurred.connect(self._emit_error)
        self._thread.start()


class _LLMTranslateThread(QThread):
    result_ready = Signal(str)
    error_occurred = Signal(str)

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
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from engine.llm_api import LLMAPIEngine; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add engine/llm_api.py
git commit -m "feat: LLM API 翻译引擎 — OpenAI/DeepSeek 兼容 + 角色提示词"
```

---

### 任务 9：engine/local_model.py — 本地模型引擎

**文件：**
- 创建：`engine/local_model.py`

- [ ] **步骤 1：实现 engine/local_model.py**

```python
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
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from engine.local_model import LocalModelEngine; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add engine/local_model.py
git commit -m "feat: 本地模型翻译引擎 — Ollama + llama-cpp-python 支持"
```

---

### 任务 10：resources/style.qss — 全局暗色样式表

**文件：**
- 创建：`resources/style.qss`

- [ ] **步骤 1：实现 resources/style.qss**

```css
/* FloatingTranslator — 极简暗色主题 */

QWidget {
    background-color: #141414;
    color: #e0e0e0;
    font-family: "Microsoft YaHei UI", "Segoe UI", "Noto Sans CJK SC", sans-serif;
    font-size: 13px;
}

QMenu {
    background-color: #1e1e1e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2a2a2a;
    color: #5af;
}

QMenu::separator {
    height: 1px;
    background: #333;
    margin: 4px 8px;
}

QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px 8px;
    color: #e0e0e0;
}

QComboBox:hover {
    border-color: #5af;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #333;
    border-radius: 4px;
    selection-background-color: #2a2a2a;
    selection-color: #5af;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px 8px;
    color: #e0e0e0;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #5af;
}

QPushButton {
    background-color: #2a2a2a;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 6px 18px;
    color: #e0e0e0;
}

QPushButton:hover {
    background-color: #333;
    border-color: #5af;
}

QPushButton:pressed {
    background-color: #1e1e1e;
}

QPushButton[primary="true"] {
    background-color: #5af;
    color: #141414;
    border: none;
    font-weight: bold;
}

QPushButton[primary="true"]:hover {
    background-color: #7bf;
}

QSlider::groove:horizontal {
    background: #2a2a2a;
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #5af;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QScrollBar:vertical {
    background: #141414;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #333;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QGroupBox {
    border: 1px solid #333;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #888;
}

QRadioButton {
    spacing: 6px;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid #555;
}

QRadioButton::indicator:checked {
    border-color: #5af;
    background-color: #5af;
}

QLabel {
    color: #e0e0e0;
    background: transparent;
}
```

- [ ] **步骤 2：验证文件存在**

运行：`ls -la resources/style.qss`

- [ ] **步骤 3：Commit**

```bash
git add resources/style.qss
git commit -m "feat: 全局暗色 QSS 样式表 — 极简暗色主题"
```

---

### 任务 11：ui/floating_window.py — 悬浮翻译窗

**文件：**
- 创建：`ui/floating_window.py`

- [ ] **步骤 1：实现 ui/floating_window.py**

```python
"""悬浮翻译窗口——无边框、置顶、半透明、自动隐藏。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 380
WINDOW_MAX_HEIGHT = 300


class FloatingWindow(QWidget):
    close_requested = Signal()

    def __init__(
        self, opacity: float = 0.92, auto_hide_seconds: int = 5, parent=None
    ) -> None:
        super().__init__(parent)
        self._opacity = opacity
        self._auto_hide_seconds = auto_hide_seconds
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._dragging = False
        self._drag_pos = None

        self._setup_ui()
        self._setup_window_flags()

    def _setup_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setWindowOpacity(self._opacity)

    def _setup_ui(self) -> None:
        self.setFixedWidth(WINDOW_WIDTH)
        self.setMaximumHeight(WINDOW_MAX_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setStyleSheet(
            """
            FloatingWindow {
                background-color: rgba(20, 20, 20, 235);
                border-radius: 10px;
                border: 1px solid #333;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._source_label = QLabel("原文")
        self._source_label.setStyleSheet(
            "color: #888; font-size: 11px; font-weight: bold; background: transparent;"
        )
        header.addWidget(self._source_label)

        self._direction_label = QLabel("")
        self._direction_label.setStyleSheet(
            "color: #666; font-size: 10px; background: transparent;"
        )
        header.addWidget(self._direction_label)

        header.addStretch()

        close_btn = QLabel("✕")
        close_btn.setStyleSheet(
            "color: #555; font-size: 14px; background: transparent; padding: 2px;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close_requested.emit()
        header.addWidget(close_btn)

        layout.addLayout(header)

        self._source_text = QLabel("")
        self._source_text.setWordWrap(True)
        self._source_text.setStyleSheet(
            "color: #aaa; font-size: 12px; background: transparent;"
            "padding: 6px 8px; border-left: 2px solid #5af;"
        )
        self._source_text.setVisible(False)
        layout.addWidget(self._source_text)

        self._result_label = QLabel("翻译结果将在此处显示")
        self._result_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(13)
        self._result_label.setFont(font)
        self._result_label.setStyleSheet(
            "color: #8f8; font-size: 13px; background: transparent;"
            "padding: 8px 10px; border-left: 2px solid #8f8;"
        )
        layout.addWidget(self._result_label)

        self._error_label = QLabel("")
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "color: #f55; font-size: 11px; background: transparent; padding: 4px 8px;"
        )
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

    def show_translation(
        self, source_text: str, result: str, source_lang: str, target_lang: str
    ) -> None:
        self._source_text.setText(source_text)
        self._source_text.setVisible(bool(source_text.strip()))
        self._source_label.setText("原文" if source_lang.startswith("zh") else "Source")

        self._direction_label.setText(f"{source_lang} → {target_lang}")
        self._result_label.setText(result)
        self._error_label.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()
        self._reset_hide_timer()

    def show_error(self, error: str) -> None:
        self._error_label.setText(f"⚠ {error}")
        self._error_label.setVisible(True)
        self._result_label.setText("")
        self._source_text.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()
        self._reset_hide_timer()

    def show_placeholder(self, text: str = "") -> None:
        display = text or "翻译结果将在此处显示"
        self._source_text.setVisible(False)
        self._direction_label.setText("")
        self._result_label.setText(display)
        self._error_label.setVisible(False)
        self.adjustSize()
        self._position_near_cursor()
        self.show()
        self._reset_hide_timer()

    def _position_near_cursor(self) -> None:
        screen = QApplication.screenAt(self.cursor().pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()

        cursor_pos = self.cursor().pos()
        x = cursor_pos.x() + 16
        y = cursor_pos.y() + 16

        if x + self.width() > screen_geom.right():
            x = screen_geom.right() - self.width() - 8
        if y + self.height() > screen_geom.bottom():
            y = cursor_pos.y() - self.height() - 8
        if x < screen_geom.left():
            x = screen_geom.left() + 8
        if y < screen_geom.top():
            y = screen_geom.top() + 8

        self.move(x, y)

    def _reset_hide_timer(self) -> None:
        self._hide_timer.stop()
        if self._auto_hide_seconds > 0:
            self._hide_timer.start(self._auto_hide_seconds * 1000)

    def enterEvent(self, event) -> None:
        self._hide_timer.stop()

    def leaveEvent(self, event) -> None:
        self._reset_hide_timer()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._drag_pos = None
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from ui.floating_window import FloatingWindow; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add ui/floating_window.py
git commit -m "feat: 悬浮翻译窗 — 无边框、置顶、半透明、自动隐藏"
```

---

### 任务 12：ui/settings_dialog.py — 设置对话框

**文件：**
- 创建：`ui/settings_dialog.py`

- [ ] **步骤 1：实现 ui/settings_dialog.py**

```python
"""设置对话框——修改目标语言、引擎、API Key 等配置。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import AppConfig, ConfigManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, config_path: str, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._config_path = config_path
        self._engine_radios: dict[str, QRadioButton] = {}

        self.setWindowTitle("FloatingTranslator 设置")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._create_general_group())
        layout.addWidget(self._create_engine_group())
        layout.addWidget(self._create_llm_group())
        layout.addWidget(self._create_local_group())

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _create_general_group(self) -> QGroupBox:
        group = QGroupBox("通用设置")
        form = QFormLayout(group)

        self._target_lang_combo = QComboBox()
        self._target_lang_combo.addItems(["zh", "en", "ja", "ko", "fr", "de", "es", "ru"])
        form.addRow("目标语言:", self._target_lang_combo)

        self._hotkey_edit = QLineEdit()
        form.addRow("快捷键:", self._hotkey_edit)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(50, 100)
        self._opacity_slider.setTickInterval(10)
        self._opacity_label = QLabel("92%")
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        form.addRow("不透明度:", opacity_row)

        self._hide_seconds_spin = QSpinBox()
        self._hide_seconds_spin.setRange(0, 60)
        self._hide_seconds_spin.setSuffix(" 秒")
        self._hide_seconds_spin.setToolTip("0 表示不自动隐藏")
        form.addRow("自动隐藏:", self._hide_seconds_spin)

        return group

    def _create_engine_group(self) -> QGroupBox:
        group = QGroupBox("翻译引擎")
        layout = QVBoxLayout(group)

        for key, label in [
            ("free_online", "免费在线 (MyMemory)"),
            ("llm_api", "大模型 API (OpenAI/DeepSeek)"),
            ("local_model", "本地模型 (Ollama/llama.cpp)"),
        ]:
            radio = QRadioButton(label)
            radio.toggled.connect(self._on_engine_toggled)
            self._engine_radios[key] = radio
            layout.addWidget(radio)

        return group

    def _create_llm_group(self) -> QGroupBox:
        group = QGroupBox("大模型 API 设置")
        form = QFormLayout(group)

        self._llm_api_key_edit = QLineEdit()
        self._llm_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key:", self._llm_api_key_edit)

        self._llm_api_url_edit = QLineEdit()
        form.addRow("API URL:", self._llm_api_url_edit)

        self._llm_model_edit = QLineEdit()
        form.addRow("模型名:", self._llm_model_edit)

        self._llm_prompt_edit = QPlainTextEdit()
        self._llm_prompt_edit.setMaximumHeight(100)
        form.addRow("系统提示词:", self._llm_prompt_edit)

        return group

    def _create_local_group(self) -> QGroupBox:
        group = QGroupBox("本地模型设置")
        form = QFormLayout(group)

        self._local_type_combo = QComboBox()
        self._local_type_combo.addItems(["ollama", "llama_cpp"])
        form.addRow("模型类型:", self._local_type_combo)

        self._local_path_edit = QLineEdit()
        self._local_path_edit.setPlaceholderText("Ollama 模型名 或 GGUF 文件路径")
        form.addRow("模型名称/路径:", self._local_path_edit)

        return group

    def _load_config(self) -> None:
        self._target_lang_combo.setCurrentText(self._config.target_lang)
        self._hotkey_edit.setText(self._config.hotkey)
        self._opacity_slider.setValue(int(self._config.opacity * 100))
        self._hide_seconds_spin.setValue(self._config.auto_hide_seconds)

        radio = self._engine_radios.get(self._config.engine_type)
        if radio:
            radio.setChecked(True)

        self._llm_api_key_edit.setText(self._config.llm_api_key)
        self._llm_api_url_edit.setText(self._config.llm_api_url)
        self._llm_model_edit.setText(self._config.llm_model)
        self._llm_prompt_edit.setPlainText(self._config.llm_system_prompt)

        self._local_type_combo.setCurrentText(self._config.local_model_type)
        self._local_path_edit.setText(self._config.local_model_path)

        self._on_engine_toggled()

    def _on_engine_toggled(self) -> None:
        is_llm = self._engine_radios.get("llm_api", QRadioButton()).isChecked()
        is_local = self._engine_radios.get("local_model", QRadioButton()).isChecked()
        self._create_llm_group().setVisible(is_llm)
        self._create_local_group().setVisible(is_local)

    def _on_save(self) -> None:
        selected_engine = "free_online"
        for key, radio in self._engine_radios.items():
            if radio.isChecked():
                selected_engine = key
                break

        self._config.target_lang = self._target_lang_combo.currentText()
        self._config.hotkey = self._hotkey_edit.text() or "ctrl+q"
        self._config.opacity = self._opacity_slider.value() / 100.0
        self._config.auto_hide_seconds = self._hide_seconds_spin.value()
        self._config.engine_type = selected_engine
        self._config.llm_api_key = self._llm_api_key_edit.text()
        self._config.llm_api_url = self._llm_api_url_edit.text()
        self._config.llm_model = self._llm_model_edit.text()
        self._config.llm_system_prompt = self._llm_prompt_edit.toPlainText()
        self._config.local_model_type = self._local_type_combo.currentText()
        self._config.local_model_path = self._local_path_edit.text()

        try:
            ConfigManager.save(self._config, self._config_path)
            QMessageBox.information(self, "保存成功", "配置已保存。部分设置需要重启后生效。")
            self.accept()
        except Exception as e:
            logger.exception("保存配置失败")
            QMessageBox.critical(self, "保存失败", f"无法保存配置: {e}")

    def get_config(self) -> AppConfig:
        return self._config
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from ui.settings_dialog import SettingsDialog; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add ui/settings_dialog.py
git commit -m "feat: 设置对话框 — 语言/引擎/API/本地模型配置"
```

---

### 任务 13：ui/tray_icon.py — 系统托盘

**文件：**
- 创建：`ui/tray_icon.py`

- [ ] **步骤 1：实现 ui/tray_icon.py**

```python
"""系统托盘图标与右键菜单。"""
from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from config import AppConfig

logger = logging.getLogger(__name__)


class TrayIcon(QSystemTrayIcon):
    engine_changed = Signal(str)
    settings_requested = Signal()
    translate_requested = Signal()

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._engine_actions: dict[str, QAction] = {}

        icon = self._create_icon()
        self.setIcon(icon)
        self.setToolTip("FloatingTranslator")

        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _create_icon(self) -> QIcon:
        from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#5af"))
        painter.setPen(QColor("#5af"))
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QColor("#141414"))
        font = QFont("sans-serif", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        menu = QMenu()

        engine_menu = menu.addMenu("切换引擎")
        for key, label in [
            ("free_online", "免费在线 (MyMemory)"),
            ("llm_api", "大模型 API"),
            ("local_model", "本地模型"),
        ]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(key == self._config.engine_type)
            action.triggered.connect(lambda checked, k=key: self.engine_changed.emit(k))
            engine_menu.addAction(action)
            self._engine_actions[key] = action

        menu.addSeparator()

        translate_action = QAction("手动翻译 (读取剪贴板)", self)
        translate_action.triggered.connect(self.translate_requested.emit)
        menu.addAction(translate_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def update_engine_check(self, engine_type: str) -> None:
        for key, action in self._engine_actions.items():
            action.setChecked(key == engine_type)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.translate_requested.emit()

    def show_message(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
```

- [ ] **步骤 2：验证可导入**

运行：`conda run -n spider python -c "from ui.tray_icon import TrayIcon; print('OK')"`
预期：OK

- [ ] **步骤 3：Commit**

```bash
git add ui/tray_icon.py
git commit -m "feat: 系统托盘 — 右键菜单切换引擎/设置/退出"
```

---

### 任务 14：main.py — 应用入口

**文件：**
- 创建：`main.py`

- [ ] **步骤 1：实现 main.py**

```python
"""FloatingTranslator 应用入口——组装所有组件并启动事件循环。"""
from __future__ import annotations

import logging
import os
import signal
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config import AppConfig, ConfigManager
from engine.base import TranslationEngine
from engine.free_online import FreeOnlineEngine
from engine.llm_api import LLMAPIEngine
from engine.local_model import LocalModelEngine
from ui.floating_window import FloatingWindow
from ui.settings_dialog import SettingsDialog
from ui.tray_icon import TrayIcon
from utils.hotkey import HotkeyManager
from utils.language_detector import LanguageDetector
from utils.text_selector import TextSelector


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def create_engine(config: AppConfig) -> TranslationEngine:
    if config.engine_type == "llm_api":
        return LLMAPIEngine(
            api_key=config.llm_api_key,
            api_url=config.llm_api_url,
            model=config.llm_model,
            system_prompt=config.llm_system_prompt,
        )
    elif config.engine_type == "local_model":
        return LocalModelEngine(
            model_type=config.local_model_type,
            model_path=config.local_model_path,
            system_prompt=config.llm_system_prompt,
        )
    else:
        return FreeOnlineEngine()


class FloatingTranslatorApp:
    def __init__(self) -> None:
        self._config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.json"
        )
        self._config = ConfigManager.load(self._config_path)
        self._engine = create_engine(self._config)

        self._floating_window = FloatingWindow(
            opacity=self._config.opacity,
            auto_hide_seconds=self._config.auto_hide_seconds,
        )
        self._floating_window.close_requested.connect(self._floating_window.hide)

        self._tray_icon = TrayIcon(self._config)
        self._tray_icon.engine_changed.connect(self._on_engine_changed)
        self._tray_icon.settings_requested.connect(self._open_settings)
        self._tray_icon.translate_requested.connect(self._on_translate_triggered)
        self._tray_icon.show()

        self._hotkey = HotkeyManager(hotkey=self._config.hotkey)
        self._hotkey.triggered.connect(self._on_translate_triggered)
        self._hotkey.start()

        self._connect_engine_signals()

    def _connect_engine_signals(self) -> None:
        self._engine.result_ready.disconnect()
        self._engine.error_occurred.disconnect()
        self._engine.result_ready.connect(self._on_result_ready)
        self._engine.error_occurred.connect(self._on_error_occurred)

    def _on_engine_changed(self, engine_type: str) -> None:
        self._config.engine_type = engine_type
        self._engine = create_engine(self._config)
        self._connect_engine_signals()
        self._tray_icon.update_engine_check(engine_type)
        logger.info("引擎已切换为: %s", self._engine.engine_name)
        self._tray_icon.show_message(
            "引擎已切换", f"当前引擎: {self._engine.engine_name}"
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._config_path)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self._config = dialog.get_config()
            self._engine = create_engine(self._config)
            self._connect_engine_signals()
            self._floating_window._opacity = self._config.opacity
            self._floating_window.setWindowOpacity(self._config.opacity)
            self._floating_window._auto_hide_seconds = self._config.auto_hide_seconds
            self._tray_icon.update_engine_check(self._config.engine_type)
            logger.info("配置已更新")

    def _on_translate_triggered(self) -> None:
        text = TextSelector.get_selected_text()
        if not text:
            self._floating_window.show_error("未检测到选中文本，请先选中文字再按快捷键")
            return

        source_lang = LanguageDetector.detect(text)
        target_lang = self._config.target_lang

        if source_lang == target_lang:
            target_lang = "en" if target_lang == "zh" else "zh"
            logger.info("语言自动反向: %s -> %s", source_lang, target_lang)

        self._floating_window.show_translation(
            source_text=text,
            result="翻译中...",
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self._engine.translate(text, source_lang, target_lang)

    def _on_result_ready(self, result: str) -> None:
        self._floating_window._result_label.setText(result)

    def _on_error_occurred(self, error: str) -> None:
        self._floating_window.show_error(error)


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("FloatingTranslator 启动")

    # 允许 Ctrl+C 退出
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("FloatingTranslator")
    app.setQuitOnLastWindowClosed(False)

    # 加载 QSS 样式
    style_path = os.path.join(os.path.dirname(__file__), "resources", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    translator = FloatingTranslatorApp()

    logger.info("应用已启动，等待热键触发...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：验证应用可启动（无报错退出）**

运行：`timeout 3 conda run -n spider python main.py; echo "exit code: $?"`

- [ ] **步骤 3：Commit**

```bash
git add main.py
git commit -m "feat: 应用入口 — 依赖注入组装所有组件"
```

---

### 任务 15：集成验证与文档更新

**文件：**
- 修改：`README.md`

- [ ] **步骤 1：更新 README.md**

```markdown
# FloatingTranslator

桌面划词翻译器 — 选中文本 + 快捷键 → 悬浮翻译窗

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python main.py
```

## 使用方式

1. 选中任意文本
2. 按下 `Ctrl+Q`
3. 翻译结果在鼠标位置弹出

## 系统要求

- Python 3.10+
- **Windows**: 需要管理员权限运行（keyboard 库限制）
- **Linux**: 需要 X11 环境（Wayland 下部分功能受限）

## 功能

- 多引擎支持：免费 MyMemory / LLM API / 本地模型
- 语言自动检测与反向翻译
- 悬浮窗自动隐藏、智能避让屏幕边界
- 系统托盘最小化

## 配置文件

首次运行时自动生成 `config.json`，也可通过设置界面修改。
```

- [ ] **步骤 2：运行完整测试套件**

运行：`conda run -n spider python -m pytest tests/ -v`
预期：所有已有测试通过

- [ ] **步骤 3：验证应用启动流程**

```bash
# 测试导入所有模块
conda run -n spider python -c "
from config import AppConfig, ConfigManager
from engine.base import TranslationEngine, TranslationError
from engine.free_online import FreeOnlineEngine
from engine.llm_api import LLMAPIEngine
from engine.local_model import LocalModelEngine
from ui.floating_window import FloatingWindow
from ui.tray_icon import TrayIcon
from ui.settings_dialog import SettingsDialog
from utils.hotkey import HotkeyManager
from utils.text_selector import TextSelector
from utils.language_detector import LanguageDetector
print('All modules imported successfully')
"
```

- [ ] **步骤 4：Commit**

```bash
git add README.md
git commit -m "docs: 更新 README 快速入门指南"
```
