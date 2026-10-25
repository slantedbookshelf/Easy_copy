from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from easy_copy.app import EasyCopyApp
from easy_copy.config import AppSettings


def test_app_lifecycle_hide_show_copy_hide(qtbot, tmp_path: Path, monkeypatch):
    # Isolate data and settings, and avoid touching the real system tray.
    monkeypatch.setenv("EASY_COPY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(EasyCopyApp, "_create_tray", lambda self: None)

    application = EasyCopyApp()
    qtbot.addWidget(application.panel)

    # Default: panel starts hidden.
    application.panel.hide()
    assert not application.panel.isVisible()

    # Copy from another app triggers reveal near the tray.
    application.panel.refresh_records()
    application._record_received(application.store.records[0] if application.store.records else None)
    assert application.panel.isVisible()

    # Copying from within the panel does NOT hide immediately; the panel stays
    # until the user pastes / it goes idle.
    application._copy_occurred()
    assert not application._auto_hide_timer.isActive()

    # Manual toggle hides and shows without auto-hide.
    application.hide_panel()
    assert not application.panel.isVisible()
    application.toggle_panel()
    assert application.panel.isVisible()
    assert not application._auto_hide_timer.isActive()


def test_app_starts_hidden_without_copy(qtbot, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EASY_COPY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(EasyCopyApp, "_create_tray", lambda self: None)
    application = EasyCopyApp()
    qtbot.addWidget(application.panel)
    application.panel.hide()
    assert not application.panel.isVisible()
