from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout,
    QDoubleSpinBox, QGroupBox,
)

from app.config import AppConfig, LLMConfig, WhisperConfig, CursorConfig
from app.ui.styles import SETTINGS_DIALOG_STYLE


class SettingsDialog(QDialog):
    """Settings dialog for API configuration, Whisper model, and Cursor shortcuts."""

    config_saved = Signal(object)  # emits AppConfig

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Voice Cursor 设置")
        self.setFixedSize(520, 480)
        self.setStyleSheet(SETTINGS_DIALOG_STYLE)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._create_llm_tab(), "LLM 配置")
        tabs.addTab(self._create_whisper_tab(), "Whisper 模型")
        tabs.addTab(self._create_cursor_tab(), "Cursor 快捷键")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn = QPushButton("保存")
        self._save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

    def _create_llm_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        qwen_group = QGroupBox("阿里 Qwen (dashscope)")
        qf = QFormLayout(qwen_group)
        self._llm_provider = QComboBox()
        self._llm_provider.addItems(["qwen", "vllm"])
        self._llm_provider.currentTextChanged.connect(self._on_provider_changed)
        qf.addRow("当前模式:", self._llm_provider)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        qf.addRow("API Key:", self._api_key_edit)

        self._base_url_edit = QLineEdit()
        qf.addRow("Base URL:", self._base_url_edit)

        self._model_edit = QLineEdit()
        qf.addRow("模型名称:", self._model_edit)
        layout.addWidget(qwen_group)

        vllm_group = QGroupBox("本地 vllm")
        vf = QFormLayout(vllm_group)
        self._vllm_url_edit = QLineEdit()
        vf.addRow("vllm URL:", self._vllm_url_edit)

        self._vllm_model_edit = QLineEdit()
        vf.addRow("模型名称:", self._vllm_model_edit)
        layout.addWidget(vllm_group)

        layout.addStretch()
        return widget

    def _create_whisper_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Whisper 本地模型配置")
        form = QFormLayout(group)

        self._whisper_model = QComboBox()
        self._whisper_model.addItems(["tiny", "base", "small", "medium", "large-v3"])
        form.addRow("模型大小:", self._whisper_model)

        self._whisper_device = QComboBox()
        self._whisper_device.addItems(["auto", "cpu", "cuda"])
        form.addRow("计算设备:", self._whisper_device)

        self._whisper_lang = QComboBox()
        self._whisper_lang.addItems(["zh", "en", "ja", "ko", "auto"])
        form.addRow("语言:", self._whisper_lang)

        layout.addWidget(group)

        hint = QLabel(
            "提示: medium 模型约 1.5GB，首次使用会自动下载。\n"
            "GPU 可用时建议选 cuda 以获得更快速度。"
        )
        hint.setStyleSheet("color: rgba(255,255,255,100); font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        return widget

    def _create_cursor_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Cursor IDE 快捷键配置")
        form = QFormLayout(group)

        self._shortcut_open = QLineEdit()
        form.addRow("打开 Chat:", self._shortcut_open)

        self._shortcut_paste = QLineEdit()
        form.addRow("粘贴:", self._shortcut_paste)

        self._shortcut_send = QLineEdit()
        form.addRow("发送:", self._shortcut_send)

        self._delay_open = QDoubleSpinBox()
        self._delay_open.setRange(0.1, 5.0)
        self._delay_open.setSingleStep(0.1)
        self._delay_open.setSuffix(" 秒")
        form.addRow("打开后延迟:", self._delay_open)

        self._delay_paste = QDoubleSpinBox()
        self._delay_paste.setRange(0.1, 5.0)
        self._delay_paste.setSingleStep(0.1)
        self._delay_paste.setSuffix(" 秒")
        form.addRow("粘贴后延迟:", self._delay_paste)

        layout.addWidget(group)

        hint = QLabel(
            "macOS 上 ctrl 会自动替换为 command。\n"
            "如果发送失败，可尝试增加延迟时间。"
        )
        hint.setStyleSheet("color: rgba(255,255,255,100); font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        return widget

    def _on_provider_changed(self, provider: str):
        is_qwen = provider == "qwen"
        self._api_key_edit.setEnabled(is_qwen)
        self._base_url_edit.setEnabled(is_qwen)
        self._model_edit.setEnabled(is_qwen)
        self._vllm_url_edit.setEnabled(not is_qwen)
        self._vllm_model_edit.setEnabled(not is_qwen)

    def _load_values(self):
        c = self._config

        self._llm_provider.setCurrentText(c.llm.provider)
        self._api_key_edit.setText(c.llm.api_key)
        self._base_url_edit.setText(c.llm.base_url)
        self._model_edit.setText(c.llm.model)
        self._vllm_url_edit.setText(c.llm.vllm_base_url)
        self._vllm_model_edit.setText(c.llm.vllm_model)
        self._on_provider_changed(c.llm.provider)

        self._whisper_model.setCurrentText(c.whisper.model_size)
        self._whisper_device.setCurrentText(c.whisper.device)
        idx = self._whisper_lang.findText(c.whisper.language)
        if idx >= 0:
            self._whisper_lang.setCurrentIndex(idx)

        self._shortcut_open.setText(c.cursor.shortcut_open_chat)
        self._shortcut_paste.setText(c.cursor.shortcut_paste)
        self._shortcut_send.setText(c.cursor.shortcut_send)
        self._delay_open.setValue(c.cursor.delay_after_open)
        self._delay_paste.setValue(c.cursor.delay_after_paste)

    def _save(self):
        self._config.llm = LLMConfig(
            provider=self._llm_provider.currentText(),
            api_key=self._api_key_edit.text().strip(),
            base_url=self._base_url_edit.text().strip(),
            model=self._model_edit.text().strip(),
            vllm_base_url=self._vllm_url_edit.text().strip(),
            vllm_model=self._vllm_model_edit.text().strip(),
        )
        self._config.whisper = WhisperConfig(
            model_size=self._whisper_model.currentText(),
            device=self._whisper_device.currentText(),
            language=self._whisper_lang.currentText(),
        )
        self._config.cursor = CursorConfig(
            shortcut_open_chat=self._shortcut_open.text().strip(),
            shortcut_paste=self._shortcut_paste.text().strip(),
            shortcut_send=self._shortcut_send.text().strip(),
            delay_after_open=self._delay_open.value(),
            delay_after_paste=self._delay_paste.value(),
        )
        self._config.save()
        self.config_saved.emit(self._config)
        self.accept()
