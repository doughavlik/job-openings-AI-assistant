"""Settings window: manage AI Prompt Builder actions.

Reachable from the main window's Edit menu (or gear icon).
Allows the user to add, edit, delete, and reorder prompt actions.
Changes are written immediately to the user's local config.db.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QLineEdit, QTextEdit, QCheckBox, QFrame, QMessageBox,
    QScrollArea, QSizePolicy,
)

import config_db


class SettingsWindow(QDialog):
    """Modal dialog for managing AI Prompt Builder actions."""

    # Emitted when any action is created, edited, or deleted —
    # so the main window can refresh its Actions menu.
    actions_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — AI Prompt Builder Actions")
        self.resize(900, 620)
        self._current_action_id: int | None = None
        self._suppress_save = False

        self._build_ui()
        self._load_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Left panel: action list + list buttons -------------------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        left_layout.addWidget(QLabel("Actions"))

        self._list = QListWidget()
        self._list.setMinimumWidth(200)
        self._list.currentRowChanged.connect(self._on_list_selection_changed)
        left_layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_add    = QPushButton("＋ New")
        self._btn_delete = QPushButton("Delete")
        self._btn_up     = QPushButton("▲")
        self._btn_down   = QPushButton("▼")
        for btn in (self._btn_add, self._btn_delete, self._btn_up, self._btn_down):
            btn.setFixedHeight(26)
        self._btn_up.setFixedWidth(30)
        self._btn_down.setFixedWidth(30)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_up)
        btn_row.addWidget(self._btn_down)
        left_layout.addLayout(btn_row)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_up.clicked.connect(self._on_move_up)
        self._btn_down.clicked.connect(self._on_move_down)

        splitter.addWidget(left)

        # ---- Right panel: detail editor -------------------------------
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        self._detail_placeholder = QLabel("Select an action to edit, or click \u201c+ New\u201d to create one.")
        self._detail_placeholder.setStyleSheet("color: #888; font-style: italic;")
        right_layout.addWidget(self._detail_placeholder)

        self._detail_widget = QWidget()
        self._detail_widget.setVisible(False)
        detail_layout = QVBoxLayout(self._detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(6)

        # Name
        detail_layout.addWidget(QLabel("Action Name"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Generate Interview Prep Report")
        self._name_edit.textChanged.connect(self._on_field_changed)
        detail_layout.addWidget(self._name_edit)

        # Context flags
        flags_label = QLabel("Include in prompt:")
        detail_layout.addWidget(flags_label)
        flags_row = QHBoxLayout()
        self._chk_company  = QCheckBox("Company")
        self._chk_job_desc = QCheckBox("Job Description")
        self._chk_resume   = QCheckBox("Resume")
        self._chk_person   = QCheckBox("Person")
        self._chk_person_required = QCheckBox("Person required")
        for chk in (self._chk_company, self._chk_job_desc, self._chk_resume,
                    self._chk_person, self._chk_person_required):
            flags_row.addWidget(chk)
            chk.stateChanged.connect(self._on_field_changed)
        # person_required only makes sense when person is checked
        self._chk_person.stateChanged.connect(self._on_person_toggled)
        flags_row.addStretch()
        detail_layout.addLayout(flags_row)

        # Instructions
        detail_layout.addWidget(QLabel("Instructions (prepended to every assembled prompt)"))
        self._instructions_edit = QTextEdit()
        self._instructions_edit.setPlaceholderText(
            "Enter the action-specific instructions here.\n\n"
            "These will appear at the top of the assembled prompt, before the context components."
        )
        self._instructions_edit.textChanged.connect(self._on_field_changed)
        detail_layout.addWidget(self._instructions_edit, stretch=1)

        right_layout.addWidget(self._detail_widget, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([220, 660])

        root.addWidget(splitter, stretch=1)

        # ---- Bottom close button --------------------------------------
        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _load_list(self):
        """Reload the action list from DB, preserving selection if possible."""
        selected_id = self._current_action_id
        self._list.blockSignals(True)
        self._list.clear()
        for action in config_db.list_actions():
            item = QListWidgetItem(action["name"] or "(unnamed)")
            item.setData(Qt.ItemDataRole.UserRole, action["id"])
            self._list.addItem(item)
        self._list.blockSignals(False)

        # Restore selection
        if selected_id is not None:
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._list.setCurrentRow(i)
                    return
        # Default: select first row
        if self._list.count():
            self._list.setCurrentRow(0)
        else:
            self._show_detail(False)

    def _on_list_selection_changed(self, row: int):
        if row < 0:
            self._show_detail(False)
            return
        action_id = self._list.item(row).data(Qt.ItemDataRole.UserRole)
        self._load_action(action_id)

    def _show_detail(self, visible: bool):
        self._detail_widget.setVisible(visible)
        self._detail_placeholder.setVisible(not visible)

    # ------------------------------------------------------------------
    # Action detail
    # ------------------------------------------------------------------

    def _load_action(self, action_id: int):
        action = config_db.get_action(action_id)
        if action is None:
            self._show_detail(False)
            return
        self._current_action_id = action_id
        self._suppress_save = True

        self._name_edit.setText(action["name"] or "")
        self._chk_company.setChecked(bool(action["use_company"]))
        self._chk_job_desc.setChecked(bool(action["use_job_desc"]))
        self._chk_resume.setChecked(bool(action["use_resume"]))
        self._chk_person.setChecked(bool(action["use_person"]))
        self._chk_person_required.setChecked(bool(action["person_required"]))
        self._chk_person_required.setEnabled(bool(action["use_person"]))
        self._instructions_edit.setPlainText(action["instructions"] or "")

        self._suppress_save = False
        self._show_detail(True)

    def _on_person_toggled(self, state):
        enabled = self._chk_person.isChecked()
        self._chk_person_required.setEnabled(enabled)
        if not enabled:
            self._chk_person_required.setChecked(False)

    def _on_field_changed(self):
        """Auto-save whenever any field changes."""
        if self._suppress_save or self._current_action_id is None:
            return
        config_db.update_action(
            self._current_action_id,
            name=self._name_edit.text().strip() or "(unnamed)",
            instructions=self._instructions_edit.toPlainText(),
            use_company=self._chk_company.isChecked(),
            use_job_desc=self._chk_job_desc.isChecked(),
            use_resume=self._chk_resume.isChecked(),
            use_person=self._chk_person.isChecked(),
            person_required=self._chk_person.isChecked() and self._chk_person_required.isChecked(),
        )
        # Update list label
        current_item = self._list.currentItem()
        if current_item:
            current_item.setText(self._name_edit.text().strip() or "(unnamed)")
        self.actions_changed.emit()

    # ------------------------------------------------------------------
    # Add / Delete / Reorder
    # ------------------------------------------------------------------

    def _on_add(self):
        # Compute next sort_order
        actions = config_db.list_actions()
        next_order = (max((a["sort_order"] for a in actions), default=0) + 10)
        action_id = config_db.insert_action(
            name="New Action",
            instructions="",
            use_company=True,
            use_job_desc=True,
            use_resume=True,
            use_person=False,
            person_required=False,
            sort_order=next_order,
        )
        self._current_action_id = action_id
        self._load_list()
        self.actions_changed.emit()
        # Focus the name field so the user can type immediately
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _on_delete(self):
        if self._current_action_id is None:
            return
        action = config_db.get_action(self._current_action_id)
        name = action["name"] if action else "this action"
        reply = QMessageBox.question(
            self, "Delete action?",
            f"Permanently delete \u201c{name}\u201d?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        config_db.delete_action(self._current_action_id)
        self._current_action_id = None
        self._load_list()
        self.actions_changed.emit()

    def _on_move_up(self):
        self._swap_with_neighbour(direction=-1)

    def _on_move_down(self):
        self._swap_with_neighbour(direction=1)

    def _swap_with_neighbour(self, direction: int):
        """Swap the sort_order of the current action with its neighbour."""
        if self._current_action_id is None:
            return
        actions = config_db.list_actions()
        ids = [a["id"] for a in actions]
        orders = [a["sort_order"] for a in actions]
        try:
            idx = ids.index(self._current_action_id)
        except ValueError:
            return
        neighbour_idx = idx + direction
        if neighbour_idx < 0 or neighbour_idx >= len(ids):
            return
        # Swap sort_order values
        config_db.update_action(ids[idx],          sort_order=orders[neighbour_idx])
        config_db.update_action(ids[neighbour_idx], sort_order=orders[idx])
        self._load_list()
        self.actions_changed.emit()
