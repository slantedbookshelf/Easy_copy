from pathlib import Path

import pytest

from easy_copy.model import RecordStore
from easy_copy.storage import JsonStorage


def test_add_keeps_order_and_multiple_records():
    store = RecordStore()
    for value in ["一", "二", "三", "四", "五"]:
        store.add(value)
    assert [item.text for item in store.records] == ["五", "四", "三", "二", "一"]


def test_duplicate_moves_existing_record_to_top():
    store = RecordStore()
    store.add("甲", now=1)
    store.add("乙", now=2)
    original_id = store.records[1].record_id
    record, changed = store.add("甲", now=3)
    assert changed is True
    assert store.count == 2
    assert record.record_id == original_id
    assert record.copied_at == 3
    assert [item.text for item in store.records] == ["甲", "乙"]


@pytest.mark.parametrize("value", ["", " ", "\n\t"])
def test_blank_text_is_ignored(value):
    store = RecordStore()
    assert store.add(value) == (None, False)


def test_capacity_removes_oldest():
    store = RecordStore(max_records=3)
    for value in ["1", "2", "3", "4"]:
        store.add(value)
    assert [item.text for item in store.records] == ["4", "3", "2"]


def test_remove_and_clear_only_affect_expected_records():
    store = RecordStore()
    store.add("保留")
    removed, _ = store.add("删除")
    assert store.remove(removed.record_id)
    assert [item.text for item in store.records] == ["保留"]
    store.clear()
    assert store.count == 0


def test_update_replaces_text_in_place():
    store = RecordStore()
    record, _ = store.add("原始文本")
    updated = store.update(record.record_id, "修改后的文本")
    assert updated is not None
    assert store.records[0].text == "修改后的文本"
    assert store.records[0].record_id == record.record_id
    assert store.count == 1


def test_update_with_blank_text_removes_record():
    store = RecordStore()
    record, _ = store.add("将被清空")
    assert store.update(record.record_id, "  ") is None
    assert store.count == 0


def test_json_storage_round_trip_and_corruption_recovery(tmp_path: Path):
    path = tmp_path / "records.json"
    storage = JsonStorage(path)
    store = RecordStore()
    store.add("多行文本\n第二行", now=123)
    storage.save(store)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "多行文本\n第二行"
    assert loaded[0].copied_at == 123

    path.write_text("not-json", encoding="utf-8")
    assert storage.load() == []
