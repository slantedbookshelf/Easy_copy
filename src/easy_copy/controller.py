from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QClipboard

from .model import RecordStore, TextRecord
from .storage import JsonStorage


class ClipboardController(QObject):
    records_changed = Signal()
    record_received = Signal(object)
    pause_changed = Signal(bool)
    copy_succeeded = Signal()

    def __init__(self, clipboard: QClipboard, storage: JsonStorage, store: RecordStore):
        super().__init__()
        self.clipboard = clipboard
        self.storage = storage
        self.store = store
        self.paused = False
        self._own_copy_text: str | None = None
        self.clipboard.dataChanged.connect(self._read_system_clipboard)

    def set_paused(self, paused: bool) -> None:
        self.paused = bool(paused)
        self.pause_changed.emit(self.paused)

    def copy_text(self, text: str) -> None:
        """Write once and suppress the resulting clipboard notification."""
        self._own_copy_text = text
        self.clipboard.setText(text, QClipboard.Clipboard)
        self.copy_succeeded.emit()

    def promote_record(self, record_id: str) -> None:
        """Move an existing record to the top (reusing dedup behaviour)."""
        record = self.store.promote(record_id)
        if record is None:
            return
        self._save()
        self.records_changed.emit()

    def add_record(self, text: str) -> TextRecord | None:
        """Add a brand-new record directly (used for partial selection copy).

        Unlike the clipboard listener, this bypasses `_own_copy_text` suppression:
        a partial selection is a new snippet that should appear as its own record
        at the top, not merely reorder the source record.
        """
        record, changed = self.store.add(text)
        if not changed:
            return record
        self._save()
        self.records_changed.emit()
        return record

    def _read_system_clipboard(self) -> None:
        if self.paused:
            self._own_copy_text = None
            return
        try:
            text = self.clipboard.text(QClipboard.Clipboard)
        except (RuntimeError, OSError):
            # Another process may temporarily own the clipboard; a later change can retry.
            return

        if self._own_copy_text is not None:
            if text == self._own_copy_text:
                self._own_copy_text = None
                return
            self._own_copy_text = None

        record, changed = self.store.add(text)
        if not changed:
            return
        self._save()
        self.records_changed.emit()
        self.record_received.emit(record)

    def delete_record(self, record_id: str) -> None:
        if self.store.remove(record_id):
            self._save()
            self.records_changed.emit()

    def update_record(self, record_id: str, text: str) -> None:
        """Update the text of an existing record (used by inline editing)."""
        record = self.store.update(record_id, text)
        if record is None:
            # Blank edit removes the record; a missing id is a no-op.
            self._save()
            self.records_changed.emit()
            return
        self._save()
        self.records_changed.emit()

    def clear_records(self) -> None:
        self.store.clear()
        self._save()
        self.records_changed.emit()

    def set_max_records(self, maximum: int) -> None:
        self.store.set_max_records(maximum)
        self._save()
        self.records_changed.emit()

    def _save(self) -> None:
        try:
            self.storage.save(self.store)
        except OSError:
            # Keep the current in-memory records usable if the disk is unavailable.
            pass
