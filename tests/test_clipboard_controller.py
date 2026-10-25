from pathlib import Path

from PySide6.QtCore import QObject, Signal

from easy_copy.controller import ClipboardController
from easy_copy.model import RecordStore
from easy_copy.storage import JsonStorage


class FakeClipboard(QObject):
    dataChanged = Signal()

    def __init__(self):
        super().__init__()
        self.value = ""

    def text(self, mode=None):
        return self.value

    def setText(self, value, mode=None):
        self.value = value
        self.dataChanged.emit()


def make_controller(tmp_path: Path):
    clipboard = FakeClipboard()
    controller = ClipboardController(
        clipboard, JsonStorage(tmp_path / "records.json"), RecordStore()
    )
    return clipboard, controller


def test_external_clipboard_changes_are_collected(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    received = []
    controller.record_received.connect(received.append)

    clipboard.setText("第一段")
    clipboard.setText("第二段")

    assert [item.text for item in controller.store.records] == ["第二段", "第一段"]
    assert len(received) == 2


def test_own_copy_does_not_create_record(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    clipboard.setText("原始文本")
    controller.copy_text("原始文本")
    controller.copy_text("部分文本")

    assert controller.store.count == 1
    assert clipboard.value == "部分文本"


def test_pause_ignores_changes_and_resume_recovers(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    controller.set_paused(True)
    clipboard.setText("暂停期间")
    assert controller.store.count == 0

    controller.set_paused(False)
    clipboard.setText("恢复之后")
    assert [item.text for item in controller.store.records] == ["恢复之后"]


def test_delete_and_clear_are_persisted(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    clipboard.setText("保留")
    clipboard.setText("删除")
    record_id = controller.store.records[0].record_id

    controller.delete_record(record_id)
    assert [item.text for item in JsonStorage(tmp_path / "records.json").load()] == ["保留"]
    controller.clear_records()
    assert JsonStorage(tmp_path / "records.json").load() == []


def test_promote_moves_existing_record_to_top(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    clipboard.setText("第一条")
    clipboard.setText("第二条")
    clipboard.setText("第三条")
    target = controller.store.records[2].record_id  # "第一条"

    controller.promote_record(target)
    assert [item.text for item in controller.store.records] == ["第一条", "第三条", "第二条"]
    # Persisted too.
    assert [item.text for item in JsonStorage(tmp_path / "records.json").load()] == [
        "第一条",
        "第三条",
        "第二条",
    ]


def test_promote_unknown_record_is_noop(qtbot, tmp_path):
    clipboard, controller = make_controller(tmp_path)
    clipboard.setText("只有一条")
    controller.promote_record("不存在的id")
    assert [item.text for item in controller.store.records] == ["只有一条"]
