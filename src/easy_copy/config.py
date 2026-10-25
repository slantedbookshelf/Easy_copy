from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings


DEFAULTS = {
    "max_records": 20,
    "idle_seconds": 8,
    "theme": "light",
    "autostart": False,
    "always_on_top": True,
    "auto_hide_enabled": False,
}


class AppSettings:
    def __init__(self, settings: QSettings | None = None):
        self.settings = settings or QSettings("Easy-copy", "Easy-copy")

    def get(self, key: str):
        default = DEFAULTS[key]
        value = self.settings.value(key, default)
        if isinstance(default, bool):
            return str(value).lower() in ("1", "true", "yes") if not isinstance(value, bool) else value
        if isinstance(default, int):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return str(value)

    def update(self, values: dict) -> None:
        for key, value in values.items():
            if key in DEFAULTS:
                self.settings.setValue(key, value)
        self.settings.sync()

    def save_geometry(self, geometry: bytes) -> None:
        self.settings.setValue("window_geometry", geometry)

    def geometry(self):
        return self.settings.value("window_geometry")

    @staticmethod
    def set_autostart(enabled: bool) -> None:
        if sys.platform != "win32":
            return
        run_key = QSettings(
            r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run",
            QSettings.NativeFormat,
        )
        if enabled:
            if getattr(sys, "frozen", False):
                command = f'"{sys.executable}"'
            else:
                command = f'"{sys.executable}" -m easy_copy'
            run_key.setValue("Easy-copy", command)
        else:
            run_key.remove("Easy-copy")
        run_key.sync()
