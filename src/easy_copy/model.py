from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class TextRecord:
    text: str
    record_id: str
    copied_at: float

    @classmethod
    def create(cls, text: str, now: float | None = None) -> "TextRecord":
        return cls(
            text=text,
            record_id=uuid4().hex,
            copied_at=now if now is not None else datetime.now().timestamp(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextRecord":
        return cls(
            text=str(data["text"]),
            record_id=str(data["record_id"]),
            copied_at=float(data["copied_at"]),
        )


class RecordStore:
    """In-memory record rules; persistence is deliberately kept outside."""

    def __init__(self, records: list[TextRecord] | None = None, max_records: int = 20):
        self.records = records or []
        self.max_records = max_records
        self._trim()

    @property
    def count(self) -> int:
        return len(self.records)

    def set_max_records(self, value: int) -> None:
        self.max_records = max(1, min(200, int(value)))
        self._trim()

    def add(self, text: str, now: float | None = None) -> tuple[TextRecord | None, bool]:
        """Return (record, changed). Blank input is ignored; duplicates move to top."""
        if not text or not text.strip():
            return None, False

        for index, record in enumerate(self.records):
            if record.text == text:
                self.records.pop(index)
                record.copied_at = now if now is not None else datetime.now().timestamp()
                self.records.insert(0, record)
                return record, True

        record = TextRecord.create(text, now)
        self.records.insert(0, record)
        self._trim()
        return record, True

    def remove(self, record_id: str) -> bool:
        original_count = self.count
        self.records = [item for item in self.records if item.record_id != record_id]
        return self.count != original_count

    def update(self, record_id: str, text: str) -> TextRecord | None:
        """Replace the text of an existing record. Blank text removes it."""
        for record in self.records:
            if record.record_id == record_id:
                if not text or not text.strip():
                    self.records.remove(record)
                    return None
                record.text = text
                return record
        return None

    def promote(self, record_id: str) -> TextRecord | None:
        """Move an existing record to the top without changing its text."""
        for index, record in enumerate(self.records):
            if record.record_id == record_id:
                self.records.pop(index)
                self.records.insert(0, record)
                return record
        return None

    def clear(self) -> None:
        self.records.clear()

    def _trim(self) -> None:
        if len(self.records) > self.max_records:
            del self.records[self.max_records :]
