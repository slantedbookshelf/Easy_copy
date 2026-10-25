from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFrame

from easy_copy.cards import TextCard
from easy_copy.config import AppSettings
from easy_copy.controller import ClipboardController
from easy_copy.main_window import MainPanel
from easy_copy.model import RecordStore, TextRecord
from easy_copy.settings_dialog import SettingsForm
from easy_copy.storage import JsonStorage
from test_clipboard_controller import FakeClipboard


def test_long_text_collapses_and_expands_without_changing_source(qtbot):
    text = "\n".join(f"第 {index} 行长文本" for index in range(20))
    card = TextCard(TextRecord.create(text))
    qtbot.addWidget(card)
    card.show()
    qtbot.wait(30)

    assert card.is_long
    assert not card.expanded
    assert card.expand_button.text() == "展开全文"
    assert card.record.text == text

    card.toggle_expanded()
    assert card.expanded
    assert card.expand_button.text() == "收起"
    assert card.text_edit.toPlainText() == text
    assert card.text_edit.height() <= card.EXPANDED_MAX_HEIGHT

    card.toggle_expanded()
    assert not card.expanded


def test_short_text_has_no_expand_button(qtbot):
    card = TextCard(TextRecord.create("短文本"))
    qtbot.addWidget(card)
    card.show()
    qtbot.wait(30)
    assert not card.is_long
    assert card.expand_button.isHidden()


def test_full_copy_uses_original_text(qtbot):
    text = "完整原文\n" * 20
    card = TextCard(TextRecord.create(text))
    qtbot.addWidget(card)
    copied = []
    card.copy_requested.connect(lambda record_id, value, button: copied.append(value))
    card.copy_button.click()
    assert copied == [text]


def test_card_has_no_delete_button(qtbot):
    card = TextCard(TextRecord.create("文本"))
    qtbot.addWidget(card)
    assert not hasattr(card, "delete_button")


def test_ctrl_c_copies_only_selected_text(qtbot):
    card = TextCard(TextRecord.create("选择其中一句话"))
    qtbot.addWidget(card)
    copied = []
    card.copy_requested.connect(lambda record_id, value, button: copied.append(value))
    cursor = card.text_edit.textCursor()
    cursor.setPosition(2)
    cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
    card.text_edit.setTextCursor(cursor)
    card.text_edit.setFocus()

    QTest.keyClick(card.text_edit, Qt.Key_C, Qt.ControlModifier)
    assert copied == ["其中一"]


def make_panel(qtbot, tmp_path: Path):
    clipboard = FakeClipboard()
    storage = JsonStorage(tmp_path / "records.json")
    controller = ClipboardController(clipboard, storage, RecordStore())
    native_settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings = AppSettings(native_settings)
    panel = MainPanel(controller, settings)
    qtbot.addWidget(panel)
    return clipboard, controller, panel


def test_panel_collects_five_records_in_stable_order(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    for index in range(5):
        clipboard.setText(f"记录 {index}")
    panel.apply_pending_refresh()
    qtbot.wait(20)
    assert panel.count_label.text() == "5 条"
    assert [card.record.text for card in panel.cards] == [
        "记录 4",
        "记录 3",
        "记录 2",
        "记录 1",
        "记录 0",
    ]
    separators = [
        w for w in panel.list_content.findChildren(QFrame) if w.objectName() == "recordSeparator"
    ]
    assert len(separators) == 4


def test_copy_while_visible_waits_for_next_interaction(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("旧文本")
    panel.apply_pending_refresh()
    panel.show()
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["旧文本"]

    clipboard.setText("新文本")
    assert panel._pending_refresh is True
    assert [card.record.text for card in panel.cards] == ["旧文本"]

    panel.apply_pending_refresh()
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["新文本", "旧文本"]


def test_duplicate_copy_still_moves_to_top_on_refresh(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("第一条")
    panel.apply_pending_refresh()
    clipboard.setText("第二条")
    panel.apply_pending_refresh()
    clipboard.setText("第一条")
    panel.apply_pending_refresh()
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["第一条", "第二条"]


def test_right_click_delete_removes_record(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("保留")
    panel.apply_pending_refresh()
    clipboard.setText("删除")
    panel.apply_pending_refresh()
    qtbot.wait(20)

    target = panel.cards[0].record.record_id
    panel.cards[0].delete_requested.emit(target)
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["保留"]
    assert controller.store.count == 1


def test_idle_collapse_is_blocked_by_selection(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("可以选择的文本")
    panel.apply_pending_refresh()
    panel.settings.update({"auto_hide_enabled": True})
    panel.show_without_focus()
    qtbot.wait(20)
    collapsed = []
    panel.collapse_requested.connect(lambda: collapsed.append(True))

    cursor = panel.cards[0].text_edit.textCursor()
    cursor.select(cursor.SelectionType.WordUnderCursor)
    panel.cards[0].text_edit.setTextCursor(cursor)
    panel._idle_timeout()
    assert collapsed == []

    cursor.clearSelection()
    panel.cards[0].text_edit.setTextCursor(cursor)
    panel._idle_timeout()
    assert collapsed == [True]


def test_idle_does_not_hide_when_auto_hide_disabled(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("保持显示的文本")
    panel.apply_pending_refresh()
    panel.settings.update({"auto_hide_enabled": False})
    panel.show_without_focus()
    qtbot.wait(20)
    collapsed = []
    panel.collapse_requested.connect(lambda: collapsed.append(True))
    panel._idle_timeout()
    assert collapsed == []


def test_settings_update_capacity_and_idle_time(qtbot, tmp_path, monkeypatch):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    for value in ["1", "2", "3"]:
        clipboard.setText(value)
    panel.apply_pending_refresh()
    monkeypatch.setattr(AppSettings, "set_autostart", staticmethod(lambda enabled: None))
    panel._apply_settings(
        {"max_records": 2, "idle_seconds": 12, "theme": "light", "autostart": False}
    )
    assert controller.store.count == 2
    assert panel.settings.get("idle_seconds") == 12


def test_idle_seconds_enabled_only_when_auto_hide_on(qtbot):
    form = SettingsForm({"auto_hide_enabled": False, "idle_seconds": 8})
    qtbot.addWidget(form)
    assert not form.idle_seconds.isEnabled()

    form.auto_hide_enabled.setChecked(True)
    assert form.idle_seconds.isEnabled()

    form.auto_hide_enabled.setChecked(False)
    assert not form.idle_seconds.isEnabled()


def test_partial_selection_copies_as_new_record(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("选择其中一句话")
    panel.apply_pending_refresh()
    edit = panel.cards[0].text_edit
    cursor = edit.textCursor()
    cursor.setPosition(2)
    cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
    edit.setTextCursor(cursor)
    edit.setFocus()

    QTest.keyClick(edit, Qt.Key_C, Qt.ControlModifier)
    assert clipboard.value == "其中一"
    # The selected snippet becomes a brand-new record on top.
    assert controller.store.count == 2
    assert [record.text for record in controller.store.records] == ["其中一", "选择其中一句话"]


def test_partial_copy_of_second_record_adds_snippet_to_top(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("你好")
    panel.apply_pending_refresh()
    clipboard.setText("我喜欢编程")
    panel.apply_pending_refresh()
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["我喜欢编程", "你好"]

    # Select "编程" inside the second (top) record and copy it.
    edit = panel.cards[0].text_edit
    cursor = edit.textCursor()
    cursor.setPosition(3)
    cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
    edit.setTextCursor(cursor)
    edit.setFocus()
    QTest.keyClick(edit, Qt.Key_C, Qt.ControlModifier)

    assert clipboard.value == "编程"
    # The snippet "编程" is a new top record, not a reorder of "我喜欢编程".
    assert controller.store.count == 3
    assert [record.text for record in controller.store.records] == ["编程", "我喜欢编程", "你好"]


def test_full_copy_promotes_record_to_top(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("第一条")
    panel.apply_pending_refresh()
    clipboard.setText("第二条")
    panel.apply_pending_refresh()
    qtbot.wait(20)
    assert [card.record.text for card in panel.cards] == ["第二条", "第一条"]

    # Copy the non-top record ("第一条") using its own copy button.
    first_card = panel.cards[1]
    assert first_card.record.text == "第一条"
    first_card.copy_button.click()
    assert clipboard.value == "第一条"
    assert controller.store.count == 2
    # The copied record should now be at the top.
    assert [record.text for record in controller.store.records] == ["第一条", "第二条"]


def test_copy_does_not_add_duplicate_record(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("完整文本")
    panel.apply_pending_refresh()
    before = panel.cards[0].record.record_id
    panel.cards[0].copy_button.click()
    assert clipboard.value == "完整文本"
    assert controller.store.count == 1
    assert controller.store.records[0].record_id == before


def test_double_click_enters_edit_and_focus_out_commits(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("待编辑文本")
    panel.apply_pending_refresh()
    edit = panel.cards[0].text_edit
    assert edit.isReadOnly()  # read-only initially

    # Enter edit mode (double-click handler calls begin_edit internally).
    edit.begin_edit()
    qtbot.wait(10)
    assert edit.editing
    assert not edit.isReadOnly()

    # Replace the text and commit (end_edit is triggered by focus-out).
    edit.setPlainText("已修改")
    edit.end_edit()
    qtbot.wait(10)
    assert not edit.editing
    # The store now holds the edited text (cards are rebuilt on commit).
    assert controller.store.records[0].text == "已修改"
    assert controller.store.count == 1
    assert panel.cards[0].text_edit.isReadOnly()


def test_edit_to_blank_removes_record(qtbot, tmp_path):
    clipboard, controller, panel = make_panel(qtbot, tmp_path)
    clipboard.setText("将被清空")
    panel.apply_pending_refresh()
    edit = panel.cards[0].text_edit
    edit.begin_edit()
    edit.setPlainText("   ")
    # end_edit is normally triggered by focusOutEvent; call it directly for
    # determinism in the offscreen test environment.
    edit.end_edit()
    qtbot.wait(10)
    assert controller.store.count == 0
