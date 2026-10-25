from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsForm(QWidget):
    """Embedded settings form shown inside the main panel.

    It is a plain widget (not a dialog) so switching to settings happens
    in-place within the same window. It emits the collected values via
    `settings_accepted` when the user clicks 保存, and `back_requested` when
    they click 返回.
    """

    settings_accepted = Signal(dict)
    back_requested = Signal()

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Top row: back button on the left.
        top = QHBoxLayout()
        back_button = QPushButton("← 返回")
        back_button.setObjectName("backButton")
        back_button.setFocusPolicy(Qt.NoFocus)
        back_button.clicked.connect(self.back_requested)
        top.addWidget(back_button)
        top.addStretch()
        root.addLayout(top)

        form = QFormLayout()
        form.setSpacing(14)

        self.max_records = QSpinBox()
        self.max_records.setRange(1, 200)
        self.max_records.setValue(int(settings.get("max_records", 20)))
        self.max_records.setSuffix(" 条")
        form.addRow("最多保留", self.max_records)

        self.auto_hide_enabled = QCheckBox("闲置一段时间后自动关闭窗口")
        self.auto_hide_enabled.setChecked(bool(settings.get("auto_hide_enabled", False)))
        self.auto_hide_enabled.toggled.connect(self._update_idle_enabled)
        form.addRow("自动关闭", self.auto_hide_enabled)

        self.idle_seconds = QSpinBox()
        self.idle_seconds.setRange(3, 120)
        self.idle_seconds.setValue(int(settings.get("idle_seconds", 8)))
        self.idle_seconds.setSuffix(" 秒")
        self.idle_seconds.setEnabled(bool(settings.get("auto_hide_enabled", False)))
        form.addRow("闲置后收起", self.idle_seconds)

        self.theme = QComboBox()
        self.theme.addItem("浅色", "light")
        self.theme.addItem("深色", "dark")
        self.theme.setCurrentIndex(1 if settings.get("theme") == "dark" else 0)
        form.addRow("界面主题", self.theme)

        self.autostart = QCheckBox("登录 Windows 后自动启动")
        self.autostart.setChecked(bool(settings.get("autostart", False)))
        form.addRow("开机启动", self.autostart)

        root.addLayout(form)
        root.addStretch()

        privacy = QLabel("记录仅保存在本机，不上传、不联网。\n关闭窗口不会清空记录；从托盘图标可随时重新打开。")
        privacy.setObjectName("hintLabel")
        privacy.setWordWrap(True)
        root.addWidget(privacy)

        save_button = QPushButton("保存")
        save_button.setObjectName("primaryButton")
        save_button.setFocusPolicy(Qt.NoFocus)
        save_button.clicked.connect(self._accept)
        root.addWidget(save_button)

    def _accept(self):
        self.settings_accepted.emit(self.values())

    def _update_idle_enabled(self, enabled: bool):
        # The idle timeout is only meaningful when auto-hide is on.
        self.idle_seconds.setEnabled(enabled)

    def values(self) -> dict:
        return {
            "max_records": self.max_records.value(),
            "idle_seconds": self.idle_seconds.value(),
            "auto_hide_enabled": self.auto_hide_enabled.isChecked(),
            "theme": self.theme.currentData(),
            "autostart": self.autostart.isChecked(),
        }
