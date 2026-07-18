from PySide6.QtWidgets import QMessageBox

from config import AppConfig
from ui.settings_dialog import SettingsDialog


def make_dialog(qtbot, tmp_path, cfg=None):
    cfg = cfg or AppConfig()
    dlg = SettingsDialog(cfg, str(tmp_path / "config.json"))
    qtbot.addWidget(dlg)
    return dlg


class TestLocalModelScan:
    def test_scan_lists_gguf_sorted(self, qtbot, tmp_path):
        (tmp_path / "b.gguf").touch()
        (tmp_path / "a.gguf").touch()
        (tmp_path / "c.txt").touch()
        dlg = make_dialog(qtbot, tmp_path)
        dlg._local_dir_edit.setText(str(tmp_path))
        dlg._scan_gguf_models()
        items = [
            dlg._local_model_combo.itemText(i)
            for i in range(dlg._local_model_combo.count())
        ]
        assert items == ["a.gguf", "b.gguf"]
        assert dlg._local_model_combo.isEnabled()

    def test_empty_dir_disables_combo(self, qtbot, tmp_path):
        dlg = make_dialog(qtbot, tmp_path)
        dlg._local_dir_edit.setText(str(tmp_path))
        dlg._scan_gguf_models()
        assert not dlg._local_model_combo.isEnabled()
        assert dlg._local_model_combo.itemText(0) == "未找到 GGUF 文件"


class TestLocalModelLoadSave:
    def test_load_config_selects_existing_model(self, qtbot, tmp_path):
        model = tmp_path / "qwen.gguf"
        model.touch()
        cfg = AppConfig(local_model_path=str(model))
        dlg = make_dialog(qtbot, tmp_path, cfg)
        assert dlg._local_dir_edit.text() == str(tmp_path)
        assert dlg._local_model_combo.currentText() == "qwen.gguf"

    def test_load_config_with_legacy_dir_value(self, qtbot, tmp_path):
        (tmp_path / "m.gguf").touch()
        cfg = AppConfig(local_model_path=str(tmp_path))
        dlg = make_dialog(qtbot, tmp_path, cfg)
        assert dlg._local_dir_edit.text() == str(tmp_path)
        assert dlg._local_model_combo.currentText() == "m.gguf"

    def test_save_writes_absolute_path(self, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
        model = tmp_path / "qwen.gguf"
        model.touch()
        cfg = AppConfig(engine_type="local_model")
        dlg = make_dialog(qtbot, tmp_path, cfg)
        dlg._local_dir_edit.setText(str(tmp_path))
        dlg._scan_gguf_models()
        dlg._on_save()
        assert cfg.local_model_path == str(model)

    def test_save_empty_when_no_model(self, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
        cfg = AppConfig(local_model_path="/nonexistent/x.gguf")
        dlg = make_dialog(qtbot, tmp_path, cfg)
        dlg._local_dir_edit.setText(str(tmp_path))
        dlg._scan_gguf_models()
        dlg._on_save()
        assert cfg.local_model_path == ""

    def test_local_prompt_load_and_save_independent(
        self, qtbot, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
        cfg = AppConfig(
            llm_system_prompt="API提示词", local_system_prompt="本地提示词"
        )
        dlg = make_dialog(qtbot, tmp_path, cfg)
        assert dlg._local_prompt_edit.toPlainText() == "本地提示词"
        dlg._local_prompt_edit.setPlainText("新本地提示词")
        dlg._on_save()
        assert cfg.local_system_prompt == "新本地提示词"
        assert cfg.llm_system_prompt == "API提示词"
