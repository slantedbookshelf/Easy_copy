from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .model import TextRecord


class SelectableTextEdit(QPlainTextEdit):
    activity = Signal()
    partial_copy = Signal(str)
    context_requested = Signal(object)
    edit_started = Signal()
    edit_finished = Signal(str)

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.document().setDocumentMargin(0)
        self.selectionChanged.connect(self.activity)
        self.setMouseTracking(True)
        self._editing = False

    @property
    def editing(self) -> bool:
        return self._editing

    def begin_edit(self, cursor=None):
        if self._editing:
            return
        self._editing = True
        self.setReadOnly(False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        if cursor is None:
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._refresh_editing_style()
        self.edit_started.emit()

    def end_edit(self):
        if not self._editing:
            return
        self._editing = False
        self.setReadOnly(True)
        self._refresh_editing_style()
        text = self.toPlainText()
        self.edit_finished.emit(text)

    def _refresh_editing_style(self):
        self.setProperty("editing", "true" if self._editing else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseDoubleClickEvent(self, event):
        self.activity.emit()
        # Place the caret at the double-click position instead of letting Qt
        # select the whole word/block.
        caret = self.cursorForPosition(event.position().toPoint())
        self.begin_edit(caret)
        event.accept()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._editing:
            self.end_edit()

    def keyPressEvent(self, event):
        self.activity.emit()
        if self._editing:
            # In edit mode, Esc finishes editing (without reverting) and the
            # panel-level Esc shortcut still collapses the window.
            if event.key() == Qt.Key_Escape:
                self.clearFocus()
                self.end_edit()
                event.accept()
                return
            if event.matches(QKeySequence.Copy) and self.textCursor().hasSelection():
                self.partial_copy.emit(self.textCursor().selectedText().replace("\u2029", "\n"))
                event.accept()
                return
            super().keyPressEvent(event)
            return
        if event.matches(QKeySequence.Copy) and self.textCursor().hasSelection():
            self.partial_copy.emit(self.textCursor().selectedText().replace("\u2029", "\n"))
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.activity.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons():
            self.activity.emit()
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        self.activity.emit()
        self.context_requested.emit(event.globalPos())
        event.accept()


class TextCard(QFrame):
    copy_requested = Signal(str, str, object)  # record_id, text, button (None for partial)
    delete_requested = Signal(str)
    edit_requested = Signal(str, str)  # record_id, new_text
    expand_changed = Signal()
    activity = Signal()

    COLLAPSED_LINES = 4
    EXPANDED_MAX_HEIGHT = 260

    def __init__(self, record: TextRecord):
        super().__init__()
        self.record = record
        self.expanded = False
        self.is_long = False
        self.setObjectName("recordCard")
        self.setProperty("recent", "false")
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 8, 8)
        root.setSpacing(3)

        self.text_edit = SelectableTextEdit()
        self.text_edit.setPlainText(record.text)
        self.text_edit.setAccessibleName("记录文本，可拖选后按 Ctrl+C 复制，右键可删除记录")
        root.addWidget(self.text_edit)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        self.expand_button = QPushButton("展开全文")
        self.expand_button.setObjectName("expandButton")
        self.expand_button.setFocusPolicy(Qt.NoFocus)
        self.expand_button.setCursor(Qt.PointingHandCursor)
        actions.addWidget(self.expand_button, 0, Qt.AlignLeft)
        actions.addStretch()
        self.copy_button = QPushButton("复制")
        self.copy_button.setObjectName("primaryButton")
        self.copy_button.setToolTip("复制完整原文；拖选文字后按 Ctrl+C 只复制所选部分")
        self.copy_button.setFocusPolicy(Qt.NoFocus)
        actions.addWidget(self.copy_button)
        root.addLayout(actions)

        self.copy_button.clicked.connect(self._copy_full)
        self.expand_button.clicked.connect(self.toggle_expanded)
        self.text_edit.activity.connect(self.activity)
        self.text_edit.partial_copy.connect(self._copy_partial)
        self.text_edit.context_requested.connect(self.show_context_menu)
        self.text_edit.edit_finished.connect(self._finish_edit)
        self.customContextMenuRequested.connect(
            lambda point: self.show_context_menu(self.mapToGlobal(point))
        )

        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.timeout.connect(self.update_text_layout)
        self.recent_timer = QTimer(self)
        self.recent_timer.setSingleShot(True)
        self.recent_timer.timeout.connect(self._clear_recent)
        self.layout_timer.start(0)

    def _copy_full(self):
        self.activity.emit()
        self.copy_requested.emit(self.record.record_id, self.record.text, self.copy_button)

    def _copy_partial(self, text: str):
        self.activity.emit()
        self.copy_requested.emit(self.record.record_id, text, None)

    def _finish_edit(self, text: str):
        self.activity.emit()
        if text != self.record.text:
            self.record.text = text
            self.edit_requested.emit(self.record.record_id, text)
        self.update_text_layout()

    def show_context_menu(self, global_pos):
        self.activity.emit()
        menu = QMenu(self)
        selected = self.text_edit.textCursor().selectedText().replace("\u2029", "\n")
        copy_selected = menu.addAction("复制所选内容")
        copy_selected.setEnabled(bool(selected))
        copy_selected.triggered.connect(lambda: self._copy_partial(selected))
        copy_all = menu.addAction("复制完整原文")
        copy_all.triggered.connect(self._copy_full)
        if self.is_long:
            toggle = menu.addAction("收起" if self.expanded else "展开全文")
            toggle.triggered.connect(self.toggle_expanded)
        menu.addSeparator()
        delete_action = menu.addAction("删除记录")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.record.record_id)
        )
        menu.exec(global_pos)

    def toggle_expanded(self):
        self.expanded = not self.expanded
        self.activity.emit()
        self.update_text_layout()
        self.expand_changed.emit()

    def has_selection(self) -> bool:
        return self.text_edit.textCursor().hasSelection()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_timer.start(0)

    def update_text_layout(self):
        line_height = self.text_edit.fontMetrics().lineSpacing()
        collapsed_height = self.COLLAPSED_LINES * line_height + 8
        document = self.text_edit.document()
        layout = document.documentLayout()
        content_height = 8
        height_limit = self.EXPANDED_MAX_HEIGHT if self.expanded else collapsed_height
        block = document.firstBlock()
        while block.isValid():
            content_height += int(layout.blockBoundingRect(block).height())
            if content_height > height_limit:
                break
            block = block.next()
        self.is_long = content_height > collapsed_height + 2
        self.expand_button.setVisible(self.is_long)

        if not self.is_long:
            height = max(line_height + 8, content_height)
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elif self.expanded:
            height = min(self.EXPANDED_MAX_HEIGHT, content_height)
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            height = collapsed_height
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.text_edit.verticalScrollBar().setValue(0)

        self.text_edit.setFixedHeight(height)
        self.expand_button.setText("收起" if self.expanded else "展开全文")
        self.expand_changed.emit()

    def mark_recent(self):
        self.setProperty("recent", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        self.recent_timer.start(900)

    def _clear_recent(self):
        self.setProperty("recent", "false")
        self.style().unpolish(self)
        self.style().polish(self)


class EmptyState(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 60, 20, 30)
        title = QLabel("复制即收集")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        hint = QLabel("在任意应用中复制文本\n记录会按先后顺序出现在这里\n\n选中文字后按 Ctrl+C 可复制所选部分")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(hint)
        layout.addStretch()
