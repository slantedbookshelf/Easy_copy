from __future__ import annotations

from PySide6.QtCore import QByteArray, QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .cards import EmptyState, TextCard
from .config import AppSettings
from .controller import ClipboardController
from .settings_dialog import SettingsForm


class ResizeGrip(QWidget):
    """A frameless-window resize handle that works without Qt.SubWindow flags.

    Prefers the OS-native resize loop (``startSystemResize``), which handles
    mouse capture and event delivery reliably even for a non-activating tool
    window. Falls back to manual grabMouse-based resizing if the native path is
    unavailable.
    """

    activity = Signal()
    resized = Signal()

    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._window = window
        self.setCursor(Qt.SizeFDiagCursor)
        self.setFixedSize(20, 20)
        self._origin = None
        self._start_geom = None
        self._manual = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.activity.emit()
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemResize(
                Qt.Edge.RightEdge | Qt.Edge.BottomEdge
            ):
                self._manual = False
            else:
                # Manual fallback: capture the pointer and resize by hand.
                self._manual = True
                self._origin = event.globalPosition().toPoint()
                self._start_geom = self._window.geometry()
                self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._manual and self._origin is not None and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._origin
            geom = self._start_geom
            width = max(self._window.minimumWidth(), geom.width() + delta.x())
            height = max(self._window.minimumHeight(), geom.height() + delta.y())
            self._window.setGeometry(geom.x(), geom.y(), width, height)
            self.activity.emit()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._manual:
                self.releaseMouse()
            self._manual = False
            self._origin = None
            self.resized.emit()
            event.accept()


class CollapsedTag(QFrame):
    expand_requested = Signal()
    activity = Signal()

    def __init__(self, icon: QIcon):
        super().__init__()
        self.setObjectName("collapsedTag")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(92, 40)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(20, 20))
        self.count_label = QLabel("0 条")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.count_label)
        self._drag_origin = None
        self._window_origin = None
        self._moved = False

    def set_count(self, count: int):
        self.count_label.setText(f"{count} 条")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = self.pos()
            self._moved = False
            self.activity.emit()

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_origin
            if delta.manhattanLength() > 4:
                self._moved = True
                self.move(self._window_origin + delta)
                self.activity.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._moved:
            self.expand_requested.emit()
        self._drag_origin = None


class MainPanel(QMainWindow):
    collapse_requested = Signal()
    quit_requested = Signal()
    theme_changed = Signal(str)
    copy_occurred = Signal()

    def __init__(self, controller: ClipboardController, settings: AppSettings):
        super().__init__()
        self.controller = controller
        self.settings = settings
        self.cards: list[TextCard] = []
        self._expanded_ids: set[str] = set()
        self._drag_origin = None
        self._window_origin = None
        self._settings_form = None
        self._quitting = False
        self._geometry_restored = False
        self._pending_refresh = False

        self.setObjectName("panel")
        self.setWindowTitle("随记板")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMinimumSize(280, 240)
        self.resize(320, 380)

        central = QWidget()
        central.setObjectName("panel")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.installEventFilter(self)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(3, 0, 0, 0)
        title_layout.setSpacing(4)
        title = QLabel("随记板")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)
        self.count_label = QLabel("0 条")
        self.count_label.setObjectName("countLabel")
        title_layout.addWidget(self.count_label)
        title_layout.addStretch()

        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.setToolTip("收起到悬浮标签；从托盘菜单可退出")
        close_button.setFocusPolicy(Qt.NoFocus)
        title_layout.addWidget(close_button)
        root.addWidget(self.title_bar)

        # List page: the scrollable record list plus the bottom action bar.
        self.list_page = QWidget()
        list_page_layout = QVBoxLayout(self.list_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(8)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setMouseTracking(True)
        self.list_content = QWidget()
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setContentsMargins(1, 1, 3, 1)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_content)
        list_page_layout.addWidget(self.scroll, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(3)
        self.pause_button = QPushButton("暂停收集")
        self.pause_button.setCheckable(True)
        self.pause_button.setFocusPolicy(Qt.NoFocus)
        clear_button = QPushButton("清空")
        clear_button.setObjectName("dangerButton")
        clear_button.setFocusPolicy(Qt.NoFocus)
        settings_button = QPushButton("设置")
        settings_button.setFocusPolicy(Qt.NoFocus)
        bottom.addWidget(self.pause_button)
        bottom.addWidget(clear_button)
        bottom.addWidget(settings_button)
        bottom.addStretch()
        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("hintLabel")
        bottom.addWidget(self.feedback_label)
        list_page_layout.addLayout(bottom)

        # Settings page: built lazily on first open, swapped in via the stack.
        self.settings_page = QWidget()
        settings_page_layout = QVBoxLayout(self.settings_page)
        settings_page_layout.setContentsMargins(0, 0, 0, 0)
        settings_page_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_page)      # index 0
        self.stack.addWidget(self.settings_page)  # index 1
        root.addWidget(self.stack, 1)

        # Resize handle: a direct child of the panel positioned at the exact
        # bottom-right corner, overlaid on top of the content.
        self.size_grip = ResizeGrip(self)
        self.size_grip.activity.connect(self.reset_idle_timer)
        self.size_grip.resized.connect(self._save_geometry)
        self.size_grip.raise_()

        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._idle_timeout)
        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(lambda: self.feedback_label.setText(""))
        close_button.clicked.connect(self.collapse_requested)
        self.pause_button.toggled.connect(self.controller.set_paused)
        clear_button.clicked.connect(self._clear_records)
        settings_button.clicked.connect(self.open_settings)
        # Esc: on the settings page, go back to the list; otherwise hide the panel.
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.esc_shortcut.setContext(Qt.WindowShortcut)
        self.esc_shortcut.activated.connect(self._handle_esc)
        self.controller.records_changed.connect(self._records_changed)
        self.controller.record_received.connect(self._record_received)
        self.controller.pause_changed.connect(self._pause_changed)

        QApplication.instance().installEventFilter(self)
        self.refresh_records()

    def show_without_focus(self, near_tray: bool = False, auto_hide: bool = True):
        if not self._geometry_restored:
            geometry = self.settings.geometry()
            if geometry is not None:
                self.restoreGeometry(QByteArray(geometry))
            else:
                self._position_default()
            self._geometry_restored = True
        elif near_tray and not self._has_user_position():
            # Only fall back to the tray-side default when the user has never
            # moved the window; otherwise keep their chosen position.
            self._position_default()
        self.show()
        self.raise_()
        if auto_hide:
            self.reset_idle_timer()
        else:
            self.idle_timer.stop()

    def _has_user_position(self) -> bool:
        return self.settings.geometry() is not None

    def _position_default(self):
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        self.move(available.right() - self.width() - 20, available.top() + 80)

    def reset_idle_timer(self):
        if self.isVisible():
            self.idle_timer.start(self.settings.get("idle_seconds") * 1000)

    def _idle_timeout(self):
        if self.stack.currentIndex() == 1:
            self.reset_idle_timer()
            return
        if any(card.has_selection() for card in self.cards):
            self.idle_timer.start(1000)
            return
        # Only auto-hide when the user explicitly enabled it in settings.
        if self.settings.get("auto_hide_enabled"):
            self.collapse_requested.emit()

    def eventFilter(self, watched, event):
        if watched == self.title_bar:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_origin = event.globalPosition().toPoint()
                self._window_origin = self.pos()
            elif event.type() == QEvent.MouseMove and self._drag_origin is not None:
                if event.buttons() & Qt.LeftButton:
                    self.move(self._window_origin + event.globalPosition().toPoint() - self._drag_origin)
            elif event.type() == QEvent.MouseButtonRelease:
                self._drag_origin = None
                self._save_geometry()

        if self.isVisible() and isinstance(watched, QWidget):
            if watched == self or self.isAncestorOf(watched):
                if event.type() == QEvent.MouseButtonPress and self._pending_refresh:
                    QTimer.singleShot(0, self.apply_pending_refresh)
                if event.type() == QEvent.MouseButtonPress:
                    self._end_edit_if_outside(watched)
                if event.type() in (
                    QEvent.MouseMove,
                    QEvent.MouseButtonPress,
                    QEvent.KeyPress,
                    QEvent.Wheel,
                ):
                    self.reset_idle_timer()
        return super().eventFilter(watched, event)

    def _end_edit_if_outside(self, watched: QWidget):
        for card in self.cards:
            edit = card.text_edit
            if not edit.editing:
                continue
            # If the press landed outside the editing widget (not itself nor a
            # descendant), commit the edit.
            if watched is not edit and not edit.isAncestorOf(watched):
                edit.end_edit()
                break

    def _records_changed(self):
        if self.isVisible():
            self._pending_refresh = True
        else:
            self.refresh_records()

    def _record_received(self, record):
        if self.isVisible():
            self._pending_refresh = True
            self.reset_idle_timer()
        else:
            self.refresh_records(recent_id=record.record_id)
            self.show_without_focus()
            self.scroll.verticalScrollBar().setValue(0)

    def apply_pending_refresh(self):
        if self._pending_refresh:
            self.refresh_records()

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_pending_refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep the resize handle glued to the exact bottom-right corner.
        grip = self.size_grip
        grip.move(self.width() - grip.width(), self.height() - grip.height())
        grip.raise_()

    def refresh_records(self, recent_id: str | None = None):
        self._pending_refresh = False
        for card in self.cards:
            if card.expanded:
                self._expanded_ids.add(card.record.record_id)
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        records = self.controller.store.records
        self.count_label.setText(f"{len(records)} 条")
        if not records:
            self.list_layout.addWidget(EmptyState())
        else:
            for index, record in enumerate(records):
                card = TextCard(record)
                if record.record_id in self._expanded_ids:
                    card.expanded = True
                card.copy_requested.connect(self._copy_text)
                card.delete_requested.connect(self._delete_record)
                card.edit_requested.connect(self._edit_record)
                card.expand_changed.connect(lambda card=card: self._remember_expansion(card))
                card.activity.connect(self.reset_idle_timer)
                self.list_layout.addWidget(card)
                self.cards.append(card)
                if record.record_id == recent_id:
                    card.mark_recent()
                if index < len(records) - 1:
                    separator = QFrame()
                    separator.setObjectName("recordSeparator")
                    separator.setFrameShape(QFrame.HLine)
                    self.list_layout.addWidget(separator)
        self.list_layout.addStretch()
        self.reset_idle_timer()

    def _delete_record(self, record_id: str):
        self._expanded_ids.discard(record_id)
        self.controller.delete_record(record_id)
        self.refresh_records()

    def _edit_record(self, record_id: str, new_text: str):
        self.reset_idle_timer()
        self.controller.update_record(record_id, new_text)
        self.refresh_records()

    def _remember_expansion(self, card: TextCard):
        if card.expanded:
            self._expanded_ids.add(card.record.record_id)
        else:
            self._expanded_ids.discard(card.record.record_id)

    def _copy_text(self, record_id: str, text: str, button=None):
        self.controller.copy_text(text)
        if button is not None:
            # Full copy: the text equals the source record, so bring that
            # existing record to the top (dedup, no new entry).
            self.controller.promote_record(record_id)
        else:
            # Partial selection copy: the text is a new snippet, so add it as a
            # brand-new record at the top instead of reordering the source.
            self.controller.add_record(text)
        self.reset_idle_timer()
        self.copy_occurred.emit()
        if button is not None:
            button.setText("已复制")
            timer = QTimer(button)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: button.setText("复制"))
            timer.start(1200)
        else:
            self.feedback_label.setText("已复制所选内容")
            self.feedback_timer.start(1200)

    def _clear_records(self):
        self.reset_idle_timer()
        self._expanded_ids.clear()
        self.controller.clear_records()
        self.refresh_records()
        self.feedback_label.setText("已清空")
        self.feedback_timer.start(1200)

    def _pause_changed(self, paused: bool):
        self.pause_button.setText("恢复收集" if paused else "暂停收集")
        self.pause_button.setChecked(paused)
        self.reset_idle_timer()

    def open_settings(self):
        self.reset_idle_timer()
        # Rebuild the form each time so it reflects the latest settings.
        self._reload_settings_form()
        self.stack.setCurrentIndex(1)
        self.reset_idle_timer()

    def _reload_settings_form(self):
        old = self._settings_form
        if old is not None:
            self.settings_page.layout().removeWidget(old)
            old.deleteLater()
        form = SettingsForm(
            {key: self.settings.get(key) for key in ("max_records", "idle_seconds", "theme", "autostart", "auto_hide_enabled")},
            self.settings_page,
        )
        form.settings_accepted.connect(self._apply_settings)
        form.back_requested.connect(self._leave_settings)
        self.settings_page.layout().addWidget(form)
        self._settings_form = form

    def _leave_settings(self):
        self.stack.setCurrentIndex(0)
        self.reset_idle_timer()

    def _handle_esc(self):
        if self.stack.currentIndex() == 1:
            self._leave_settings()
        else:
            self.collapse_requested.emit()

    def _apply_settings(self, values: dict):
        old_theme = self.settings.get("theme")
        self.settings.update(values)
        self.controller.set_max_records(values["max_records"])
        self.settings.set_autostart(values["autostart"])
        if values["theme"] != old_theme:
            self.theme_changed.emit(values["theme"])
        self._leave_settings()
        self.reset_idle_timer()

    def prepare_to_quit(self):
        self._quitting = True
        self._save_geometry()

    def _save_geometry(self):
        self.settings.save_geometry(bytes(self.saveGeometry()))

    def hideEvent(self, event):
        if not self._quitting:
            self._save_geometry()
        super().hideEvent(event)

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
        else:
            event.ignore()
            self.collapse_requested.emit()
