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

        self._llm_group = self._create_llm_group()
        layout.addWidget(self._llm_group)

        self._local_group = self._create_local_group()
        layout.addWidget(self._local_group)

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
        self._llm_group.setVisible(is_llm)
        self._local_group.setVisible(is_local)

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
