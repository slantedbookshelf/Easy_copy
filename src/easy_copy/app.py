from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import AppSettings
from .controller import ClipboardController
from .main_window import MainPanel
from .model import RecordStore
from .storage import JsonStorage, RECORDS_FILENAME, default_data_dir
from .styles import stylesheet


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name


class EasyCopyApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("随记板")
        self.app.setOrganizationName("Easy-copy")
        self.app.setQuitOnLastWindowClosed(False)
        self.settings = AppSettings()
        self.storage = JsonStorage(default_data_dir() / RECORDS_FILENAME)
        self.store = RecordStore(
            self.storage.load(), max_records=self.settings.get("max_records")
        )
        self.controller = ClipboardController(
            self.app.clipboard(), self.storage, self.store
        )
        self.icon = QIcon(str(resource_path("easy-copy.svg")))
        self.app.setWindowIcon(self.icon)
        self.app.setStyleSheet(stylesheet(self.settings.get("theme")))

        self.panel = MainPanel(self.controller, self.settings)
        self.panel.setWindowIcon(self.icon)
        self.panel.collapse_requested.connect(self.hide_panel)
        self.panel.quit_requested.connect(self.quit)
        self.panel.copy_occurred.connect(self._copy_occurred)
        self.panel.theme_changed.connect(
            lambda theme: self.app.setStyleSheet(stylesheet(theme))
        )
        self.controller.record_received.connect(self._record_received)
        self._create_tray()

        self._auto_hide_timer = QTimer(self.app)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_panel)

    def _create_tray(self):
        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip("随记板 - 本地文本暂存")
        menu = QMenu()
        toggle_action = menu.addAction("打开/隐藏窗口")
        toggle_action.triggered.connect(self.toggle_panel)
        self.tray_pause_action = menu.addAction("暂停收集")
        self.tray_pause_action.setCheckable(True)
        self.tray_pause_action.toggled.connect(self.controller.set_paused)
        self.controller.pause_changed.connect(self.tray_pause_action.setChecked)
        menu.addSeparator()
        quit_action = menu.addAction("退出随记板")
        quit_action.triggered.connect(self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_panel()

    def toggle_panel(self):
        if self.panel.isVisible():
            self.hide_panel()
        else:
            self.show_panel(manual=True)

    def show_panel(self, manual: bool = False):
        self._auto_hide_timer.stop()
        # The panel stays visible until the user closes it (or until the idle
        # timeout when auto-hide is enabled in settings). Copy-triggered reveal
        # keeps the user's chosen position.
        self.panel.show_without_focus(near_tray=not manual, auto_hide=True)

    def hide_panel(self):
        self._auto_hide_timer.stop()
        self.panel.hide()

    def _record_received(self, record):
        # A new copy from another app: reveal the panel near the tray without
        # stealing focus, then hide it again after the idle timeout.
        if not self.controller.paused:
            self.panel.apply_pending_refresh()
            self.show_panel(manual=False)

    def _copy_occurred(self):
        # The user copied from within the panel. Do NOT hide immediately: they
        # are about to switch to the target app and paste. Let the panel stay
        # visible until it loses focus / goes idle, then hide.
        self._auto_hide_timer.stop()

    def quit(self):
        self.panel.prepare_to_quit()
        self.tray.hide()
        self.panel.hide()
        self.app.quit()

    def run(self) -> int:
        # Start hidden; the panel appears only on copy or when opened from tray.
        return self.app.exec()


def main() -> int:
    application = EasyCopyApp()
    return application.run()
