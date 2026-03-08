import sys
import os
import logging

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.config import AppConfig
from app.ui.floating_window import FloatingWindow
from app.ui.tray_icon import TrayIcon


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = AppConfig.load()

    window = FloatingWindow(config)
    tray = TrayIcon(window, config)
    tray.show()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
