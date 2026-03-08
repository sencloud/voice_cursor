FLOATING_WINDOW_STYLE = """
QLabel#titleLabel {
    color: #b0b8c8;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}

QLabel#statusLabel {
    color: #7a8494;
    font-size: 11px;
}

QLabel#timerLabel {
    color: #e8ecf2;
    font-size: 26px;
    font-weight: bold;
    font-family: 'Cascadia Mono', 'Consolas', 'Menlo', monospace;
}

QPushButton#settingsBtn {
    background-color: transparent;
    border: none;
    color: #6b7280;
    font-size: 15px;
    padding: 2px;
}
QPushButton#settingsBtn:hover {
    color: #a0a8b8;
}

QPushButton#closeBtn {
    background-color: transparent;
    border: none;
    color: #4b5260;
    font-size: 12px;
    font-weight: bold;
    padding: 2px 4px;
}
QPushButton#closeBtn:hover {
    color: #e05454;
}

QProgressBar#progressBar {
    background-color: #2a2d38;
    border: none;
    border-radius: 2px;
    max-height: 4px;
}
QProgressBar#progressBar::chunk {
    background-color: #5b9cf5;
    border-radius: 2px;
}
"""

SETTINGS_DIALOG_STYLE = """
QDialog {
    background-color: #1c1e26;
    color: #d0d4dc;
}

QTabWidget::pane {
    border: 1px solid #2e3140;
    border-radius: 6px;
    background-color: #22242e;
}

QTabBar::tab {
    background-color: #22242e;
    color: #7a8494;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #2a2d38;
    color: #e8ecf2;
    border-color: #2e3140;
}
QTabBar::tab:hover {
    color: #b0b8c8;
}

QLabel {
    color: #b0b8c8;
    font-size: 12px;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #22242e;
    border: 1px solid #2e3140;
    border-radius: 6px;
    padding: 7px 10px;
    color: #d0d4dc;
    font-size: 12px;
    selection-background-color: #3d5a99;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #5b9cf5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #22242e;
    color: #d0d4dc;
    selection-background-color: #3d5a99;
    border: 1px solid #2e3140;
    outline: 0;
}

QPushButton {
    background-color: #5b9cf5;
    border: none;
    border-radius: 6px;
    padding: 8px 24px;
    color: #ffffff;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #6eaaf8;
}
QPushButton:pressed {
    background-color: #4a8be0;
}

QPushButton#cancelBtn {
    background-color: #2e3140;
    color: #b0b8c8;
}
QPushButton#cancelBtn:hover {
    background-color: #3a3e50;
}

QGroupBox {
    border: 1px solid #2e3140;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    color: #8890a0;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
"""
