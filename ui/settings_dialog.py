"""设置对话框——修改目标语言、引擎、API Key 等配置。"""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import AppConfig, ConfigManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    opacity_preview = Signal(float)

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

        # 用 QStackedWidget 承载各引擎的专属设置面板：面板区尺寸恒为最大页，
        # 切换引擎只翻页、不改变对话框大小，避免窗口反复缩放导致的闪烁。
        self._engine_stack = QStackedWidget()
        self._llm_group = self._create_llm_group()
        self._local_group = self._create_local_group()
        self._engine_pages = {
            "free_online": self._create_free_page(),
            "llm_api": self._llm_group,
            "local_model": self._local_group,
        }
        for page in self._engine_pages.values():
            self._engine_stack.addWidget(page)
        layout.addWidget(self._engine_stack)

        layout.addStretch(1)

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

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(20, 100)
        self._opacity_slider.setTickInterval(20)
        self._opacity_label = QLabel("92%")
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        self._opacity_slider.valueChanged.connect(
            lambda v: self.opacity_preview.emit(v / 100.0)
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
            ("free_online", "免费在线"),
            ("llm_api", "大模型 API (OpenAI/DeepSeek)"),
            ("local_model", "本地模型 (llama.cpp)"),
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

        model_row = QHBoxLayout()
        self._llm_model_combo = QComboBox()
        self._llm_model_combo.setEditable(True)
        self._llm_model_combo.setMinimumWidth(200)
        model_row.addWidget(self._llm_model_combo, 1)
        fetch_btn = QPushButton("获取模型")
        fetch_btn.clicked.connect(self._on_fetch_models)
        model_row.addWidget(fetch_btn)
        form.addRow("模型名:", model_row)

        self._llm_prompt_edit = QPlainTextEdit()
        self._llm_prompt_edit.setMaximumHeight(100)
        form.addRow("系统提示词:", self._llm_prompt_edit)

        return group

    def _create_local_group(self) -> QGroupBox:
        group = QGroupBox("本地模型设置")
        form = QFormLayout(group)

        dir_row = QHBoxLayout()
        self._local_dir_edit = QLineEdit()
        self._local_dir_edit.setPlaceholderText("存放 GGUF 模型的目录")
        self._local_dir_edit.editingFinished.connect(self._scan_gguf_models)
        dir_row.addWidget(self._local_dir_edit, 1)
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._on_browse_model_dir)
        dir_row.addWidget(browse_btn)
        form.addRow("模型目录:", dir_row)

        self._local_model_combo = QComboBox()
        form.addRow("选择模型:", self._local_model_combo)

        return group

    def _on_browse_model_dir(self) -> None:
        start_dir = os.path.expanduser(self._local_dir_edit.text().strip() or "~")
        path = QFileDialog.getExistingDirectory(self, "选择模型目录", start_dir)
        if path:
            self._local_dir_edit.setText(path)
            self._scan_gguf_models()

    def _scan_gguf_models(self) -> None:
        directory = os.path.expanduser(self._local_dir_edit.text().strip())
        self._local_model_combo.clear()
        files: list[str] = []
        if directory and os.path.isdir(directory):
            files = sorted(
                f for f in os.listdir(directory) if f.lower().endswith(".gguf")
            )
        if files:
            self._local_model_combo.addItems(files)
            self._local_model_combo.setEnabled(True)
        else:
            self._local_model_combo.addItem("未找到 GGUF 文件")
            self._local_model_combo.setEnabled(False)

    def _create_free_page(self) -> QWidget:
        page = QGroupBox("免费在线引擎")
        layout = QVBoxLayout(page)
        label = QLabel("免费在线引擎 (MyMemory) 无需额外配置。")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
        return page

    def _load_config(self) -> None:
        self._target_lang_combo.setCurrentText(self._config.target_lang)
        self._opacity_slider.setValue(int(self._config.opacity * 100))
        self._hide_seconds_spin.setValue(self._config.auto_hide_seconds)

        radio = self._engine_radios.get(self._config.engine_type)
        if radio:
            radio.setChecked(True)

        self._llm_api_key_edit.setText(self._config.llm_api_key)
        self._llm_api_url_edit.setText(self._config.llm_api_url)
        self._llm_model_combo.setCurrentText(self._config.llm_model)
        self._llm_prompt_edit.setPlainText(self._config.llm_system_prompt)

        if self._config.local_model_path:
            saved = os.path.expanduser(self._config.local_model_path)
            if os.path.isdir(saved):
                self._local_dir_edit.setText(saved)
            else:
                self._local_dir_edit.setText(os.path.dirname(saved))
        else:
            self._local_dir_edit.setText(os.path.expanduser("~/model"))
        self._scan_gguf_models()
        if self._config.local_model_path:
            idx = self._local_model_combo.findText(
                os.path.basename(self._config.local_model_path)
            )
            if idx != -1:
                self._local_model_combo.setCurrentIndex(idx)

        self._on_engine_toggled()

    def _on_engine_toggled(self) -> None:
        for key, radio in self._engine_radios.items():
            if radio.isChecked():
                self._engine_stack.setCurrentWidget(self._engine_pages[key])
                break

    def _on_fetch_models(self) -> None:
        api_key = self._llm_api_key_edit.text().strip()
        api_url = self._llm_api_url_edit.text().strip().rstrip("/")
        if not api_url:
            QMessageBox.warning(self, "提示", "请先填写 API URL。")
            return

        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            resp = requests.get(
                f"{api_url}/models", headers=headers, timeout=10,
            )
            if resp.status_code != 200:
                QMessageBox.warning(
                    self, "获取失败",
                    f"API 返回 HTTP {resp.status_code}\n{resp.text[:200]}",
                )
                return
            data = resp.json()
            models = sorted(
                [m["id"] for m in data.get("data", [])],
                key=str.lower,
            )
            if not models:
                QMessageBox.information(self, "提示", "未获取到模型列表。")
                return
            current = self._llm_model_combo.currentText()
            self._llm_model_combo.clear()
            self._llm_model_combo.addItems(models)
            if self._llm_model_combo.findText(current) != -1:
                self._llm_model_combo.setCurrentText(current)
            self._llm_model_combo.showPopup()
            logger.info("获取到 %d 个模型", len(models))
        except ImportError:
            QMessageBox.critical(
                self, "错误", "requests 库未安装，无法获取模型列表。",
            )
        except Exception as e:
            logger.exception("获取模型列表失败")
            QMessageBox.warning(self, "获取失败", f"无法获取模型列表:\n{e}")

    def _on_save(self) -> None:
        selected_engine = "free_online"
        for key, radio in self._engine_radios.items():
            if radio.isChecked():
                selected_engine = key
                break

        self._config.target_lang = self._target_lang_combo.currentText()
        self._config.opacity = self._opacity_slider.value() / 100.0
        self._config.auto_hide_seconds = self._hide_seconds_spin.value()
        self._config.engine_type = selected_engine
        self._config.llm_api_key = self._llm_api_key_edit.text()
        self._config.llm_api_url = self._llm_api_url_edit.text()
        self._config.llm_model = self._llm_model_combo.currentText()
        self._config.llm_system_prompt = self._llm_prompt_edit.toPlainText()
        if self._local_model_combo.isEnabled():
            self._config.local_model_path = os.path.join(
                os.path.expanduser(self._local_dir_edit.text().strip()),
                self._local_model_combo.currentText(),
            )
        else:
            self._config.local_model_path = ""

        try:
            ConfigManager.save(self._config, self._config_path)
            QMessageBox.information(self, "保存成功", "配置已保存。部分设置需要重启后生效。")
            self.accept()
        except Exception as e:
            logger.exception("保存配置失败")
            QMessageBox.critical(self, "保存失败", f"无法保存配置: {e}")

    def get_config(self) -> AppConfig:
        return self._config
