LIGHT = """
QWidget { color: #252a31; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QWidget#panel, QWidget#collapsedTag { background: #f7f8fa; border: 1px solid #dfe3e8; border-radius: 10px; }
QFrame#titleBar { background: transparent; }
QLabel#appTitle { font-size: 15px; font-weight: 600; color: #1f2933; }
QLabel#countLabel, QLabel#hintLabel { color: #7a8491; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QFrame#recordCard { background: transparent; border: none; border-radius: 4px; }
QFrame#recordCard[recent="true"] { background: #eef4fa; }
QFrame#recordSeparator { background: #e4e8ed; border: none; max-height: 1px; min-height: 1px; }
QPlainTextEdit { background: transparent; border: none; color: #30363d; selection-background-color: #bcd7f5; selection-color: #17202a; padding: 0px; }
QPlainTextEdit[editing="true"] { background: #ffffff; border: 1px solid #32689f; border-radius: 4px; padding: 4px 6px; }
QPushButton { background: transparent; border: none; border-radius: 5px; padding: 5px 8px; color: #606b78; }
QPushButton:hover { background: #e9edf2; color: #26313d; }
QPushButton:pressed { background: #dfe5ec; }
QPushButton#primaryButton { color: #32689f; }
QPushButton#backButton { color: #32689f; padding: 5px 2px; }
QPushButton#dangerButton:hover { color: #b34040; background: #fbecec; }
QPushButton#expandButton { color: #52769b; padding: 3px 0px; font-size: 12px; }
QPushButton#iconButton { font-size: 15px; padding: 4px 6px; }
QPushButton#closeButton { font-size: 18px; font-weight: 600; padding: 2px 10px; border-radius: 6px; }
QPushButton#closeButton:hover { background: #fbecec; color: #b34040; }
QPushButton:checked { background: #dfeaf5; color: #285f91; }
QDialog { background: #f7f8fa; }
QSpinBox, QComboBox { background: #ffffff; border: 1px solid #d6dce3; border-radius: 5px; padding: 5px; min-height: 20px; }
QCheckBox { spacing: 8px; }
QToolTip { background: #ffffff; color: #30363d; border: 1px solid #d8dde3; padding: 4px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd2da; border-radius: 3px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QMenu { background: #ffffff; border: 1px solid #dce1e6; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background: #e9edf2; }
"""

DARK = """
QWidget { color: #e3e7eb; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QWidget#panel, QWidget#collapsedTag { background: #20242a; border: 1px solid #3b424b; border-radius: 10px; }
QLabel#appTitle { font-size: 15px; font-weight: 600; color: #f0f2f4; }
QLabel#countLabel, QLabel#hintLabel { color: #9aa4af; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QFrame#recordCard { background: transparent; border: none; border-radius: 4px; }
QFrame#recordCard[recent="true"] { background: #2d3845; }
QFrame#recordSeparator { background: #3d444e; border: none; max-height: 1px; min-height: 1px; }
QPlainTextEdit { background: transparent; border: none; color: #e0e4e8; selection-background-color: #456482; selection-color: #ffffff; padding: 0px; }
QPlainTextEdit[editing="true"] { background: #292e35; border: 1px solid #8ab8e3; border-radius: 4px; padding: 4px 6px; }
QPushButton { background: transparent; border: none; border-radius: 5px; padding: 5px 8px; color: #b1bac4; }
QPushButton:hover { background: #363d46; color: #f0f2f4; }
QPushButton:pressed { background: #424a54; }
QPushButton#primaryButton { color: #8ab8e3; }
QPushButton#backButton { color: #8ab8e3; padding: 5px 2px; }
QPushButton#dangerButton:hover { color: #f0a0a0; background: #493334; }
QPushButton#expandButton { color: #8ab8e3; padding: 3px 0px; font-size: 12px; }
QPushButton#iconButton { font-size: 15px; padding: 4px 6px; }
QPushButton#closeButton { font-size: 18px; font-weight: 600; padding: 2px 10px; border-radius: 6px; }
QPushButton#closeButton:hover { background: #493334; color: #f0a0a0; }
QPushButton:checked { background: #354b60; color: #b7d9f5; }
QDialog { background: #20242a; }
QSpinBox, QComboBox { background: #292e35; border: 1px solid #48515b; border-radius: 5px; padding: 5px; min-height: 20px; }
QCheckBox { spacing: 8px; }
QToolTip { background: #292e35; color: #e3e7eb; border: 1px solid #48515b; padding: 4px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #525c67; border-radius: 3px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QMenu { background: #292e35; border: 1px solid #48515b; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background: #3a424c; }
"""


def stylesheet(theme: str) -> str:
    return DARK if theme == "dark" else LIGHT
