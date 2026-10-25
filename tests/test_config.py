from PySide6.QtCore import QByteArray, QSettings

from easy_copy.config import AppSettings


def test_settings_and_geometry_survive_recreation(tmp_path):
    path = str(tmp_path / "settings.ini")
    settings = AppSettings(QSettings(path, QSettings.IniFormat))
    settings.update({"max_records": 35, "idle_seconds": 10, "theme": "dark"})
    geometry = QByteArray(b"window-state")
    settings.save_geometry(bytes(geometry))

    restored = AppSettings(QSettings(path, QSettings.IniFormat))
    assert restored.get("max_records") == 35
    assert restored.get("idle_seconds") == 10
    assert restored.get("theme") == "dark"
    assert bytes(restored.geometry()) == b"window-state"
