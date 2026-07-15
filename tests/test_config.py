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
        assert cfg.auto_hide_seconds == 0
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
