"""配置数据模型与 JSON 持久化。"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "你是一个专业的翻译助手，直接输出翻译结果，不要解释、不要补充、不要聊天。"
)


@dataclass
class AppConfig:
    target_lang: str = "zh"

    engine_type: str = "free_online"
    opacity: float = 0.92
    auto_hide_seconds: int = 0

    llm_api_key: str = ""
    llm_api_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    llm_system_prompt: str = DEFAULT_SYSTEM_PROMPT

    local_model_type: str = "llama_cpp"
    local_model_path: str = ""
    local_system_prompt: str = DEFAULT_SYSTEM_PROMPT

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
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("配置已保存到 %s", path)
