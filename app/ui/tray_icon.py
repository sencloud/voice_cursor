import sys

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from app.config import AppConfig
from app.ui.settings_dialog import SettingsDialog


def _create_default_icon() -> QIcon:
    """Generate a simple microphone icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(QColor(0, 0, 0, 0))
    painter.setBrush(QColor(80, 140, 255))
    painter.drawRoundedRect(8, 8, 48, 48, 12, 12)

    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(24, 14, 16, 24, 8, 8)

    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(QColor(0, 0, 0, 0))
    pen = painter.pen()
    pen.setWidth(3)
    painter.setPen(pen)
    painter.drawArc(18, 22, 28, 24, 0, -180 * 16)

    painter.drawLine(32, 46, 32, 52)
    painter.drawLine(24, 52, 40, 52)

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu."""

    def __init__(self, floating_window, config: AppConfig):
        super().__init__()
        self._window = floating_window
        self._config = config

        self.setIcon(_create_default_icon())
        self.setToolTip("Voice Cursor")

        self._build_menu()
        self.activated.connect(self._on_activated)
        self._window.request_settings.connect(self._open_settings)

    def _build_menu(self):
        menu = QMenu()

        show_action = QAction("显示窗口", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        settings_action = QAction("设置", menu)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def _show_window(self):
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    @Slot()
    def _open_settings(self):
        dlg = SettingsDialog(self._config, self._window)
        dlg.config_saved.connect(self._on_config_saved)
        dlg.exec()

    def _on_config_saved(self, config):
        self._config = config
        self._window.reload_config(config)

    def _quit(self):
        QApplication.quit()
