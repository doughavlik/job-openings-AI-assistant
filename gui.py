"""PySide6 GUI for the Job Openings Tracker.

Layout
------
Window
 ├─ Toolbar   (Import PDF | Add Row | [search box] | Show Archived toggle)
 ├─ Job Table (inline-editable, sortable)
 └─ Detail Pane (collapsible splitter; Resume tab | Job Description tab | People tab)

Columns: ID · Company · Job Title · JD · Resume · People · Application URL · Created · Actions
"""

import sys
from pathlib import Path

from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QThread, Signal, QObject, QModelIndex
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QPushButton, QLineEdit, QCheckBox, QTableView, QHeaderView,
    QSplitter, QTabWidget, QTextEdit, QLabel, QAbstractItemView,
    QFileDialog, QMessageBox, QStyledItemDelegate, QStyleOptionViewItem,
    QSizePolicy, QFrame,
)

import db
import pdf_importer


# ---------------------------------------------------------------------------
# Column index constants
# ---------------------------------------------------------------------------
COL_ID       = 0
COL_COMPANY  = 1
COL_TITLE    = 2
COL_JD       = 3
COL_RESUME   = 4
COL_PEOPLE   = 5
COL_URL      = 6
COL_CREATED  = 7
COL_ACTIONS  = 8
NUM_COLS     = 9

COL_HEADERS = ["ID", "Company", "Job Title", "JD", "Resume", "People", "Application URL", "Created", "Actions"]

# Columns that hold real text the user can edit
EDITABLE_COLS = {COL_COMPANY, COL_TITLE, COL_URL}

# Map column → db field name for inline edits
COL_TO_FIELD = {
    COL_COMPANY: "customer_name",
    COL_TITLE:   "job_title",
    COL_URL:     "application_url",
}

DOT_FULL  = "●"
DOT_EMPTY = "○"


# ---------------------------------------------------------------------------
# Custom proxy: handles both text search and archived-row visibility
# ---------------------------------------------------------------------------

class JobProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_archived = False
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)

    def set_show_archived(self, value: bool):
        self._show_archived = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        id_item = self.sourceModel().item(source_row, COL_ID)
        if id_item is None:
            return False
        archived = bool(id_item.data(Qt.ItemDataRole.UserRole + 1))
        if archived and not self._show_archived:
            return False
        # Apply text filter across all columns
        return super().filterAcceptsRow(source_row, source_parent)


# ---------------------------------------------------------------------------
# Worker: run PDF import on a background thread so the UI stays responsive
# ---------------------------------------------------------------------------

class ImportWorker(QObject):
    # job_id (-1 on hard failure), error_message (empty on full success)
    finished = Signal(int, str)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self):
        try:
            job_id, error_msg = pdf_importer.import_pdf(self._path)
            self.finished.emit(job_id, error_msg)
        except Exception as exc:
            self.finished.emit(-1, str(exc))


# ---------------------------------------------------------------------------
# Custom delegate: render indicator columns and prevent editing them
# ---------------------------------------------------------------------------

class TableDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        col = index.column()
        if col in (COL_JD, COL_RESUME, COL_PEOPLE):
            option.displayAlignment = Qt.AlignmentFlag.AlignCenter

    def createEditor(self, parent, option, index):
        # Only allow editing on editable text columns
        if index.column() not in EDITABLE_COLS:
            return None
        return super().createEditor(parent, option, index)


# ---------------------------------------------------------------------------
# Archive button widget embedded in each table row
# ---------------------------------------------------------------------------

class ArchiveButton(QPushButton):
    def __init__(self, job_id: int, parent=None):
        super().__init__("Archive", parent)
        self.job_id = job_id
        self.setToolTip("Click to archive this job opening")
        self.setFixedWidth(70)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { color: #888; font-size: 11px; border: 1px solid #ccc; border-radius: 3px; padding: 2px 4px; }"
            "QPushButton:hover { color: #c00; border-color: #c00; }"
        )


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Job Openings Tracker")
        self.resize(1200, 750)

        # Pending inline edits: {job_id: {field: value}}
        self._pending: dict[int, dict] = {}

        self._build_ui()
        self._load_table()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_table())
        splitter.addWidget(self._build_detail_pane())
        splitter.setSizes([480, 240])
        splitter.setChildrenCollapsible(True)

        root.addWidget(splitter)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        btn_import = QPushButton("⬆ Import PDF")
        btn_import.setToolTip("Import a PDF and convert it to Markdown via Gemini")
        btn_import.clicked.connect(self._on_import)

        btn_add = QPushButton("＋ Add Row")
        btn_add.setToolTip("Add a blank job opening")
        btn_add.clicked.connect(self._on_add_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._on_filter_changed)

        self._show_archived = QCheckBox("Show Archived")
        self._show_archived.stateChanged.connect(self._on_filter_changed)

        layout.addWidget(btn_import)
        layout.addWidget(btn_add)
        layout.addStretch()
        layout.addWidget(self._search)
        layout.addWidget(self._show_archived)
        return bar

    def _build_table(self) -> QWidget:
        self._model = QStandardItemModel(0, NUM_COLS)
        self._model.setHorizontalHeaderLabels(COL_HEADERS)
        self._model.itemChanged.connect(self._on_item_changed)

        self._proxy = JobProxyModel()
        self._proxy.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setItemDelegate(TableDelegate(self._table))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                    QAbstractItemView.EditTrigger.SelectedClicked)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(True)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(COL_ID,      QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_COMPANY,  QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_TITLE,    QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_JD,       QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_RESUME,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_PEOPLE,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_URL,      QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(COL_CREATED,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_ACTIONS,  QHeaderView.ResizeMode.ResizeToContents)

        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._proxy.layoutChanged.connect(self._place_archive_buttons)

        return self._table

    def _build_detail_pane(self) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)

        self._detail_label = QLabel("Select a row to view details.")
        self._detail_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self._detail_label)

        self._tabs = QTabWidget()
        self._tabs.setVisible(False)

        # Resume tab
        resume_widget, self._resume_text, self._resume_edit_btn, \
            self._resume_save_btn, self._resume_cancel_btn = self._build_detail_tab()
        self._tabs.addTab(resume_widget, "Resume")

        # Job Description tab
        jd_widget, self._jd_text, self._jd_edit_btn, \
            self._jd_save_btn, self._jd_cancel_btn = self._build_detail_tab()
        self._tabs.addTab(jd_widget, "Job Description")

        # People tab
        self._tabs.addTab(self._build_people_tab(), "People")

        layout.addWidget(self._tabs)
        return frame

    def _build_people_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        # Toolbar row: Add Person button
        btn_row = QHBoxLayout()
        add_btn = QPushButton("＋ Add Person")
        add_btn.setToolTip("Add a new person to this job opening")
        add_btn.clicked.connect(self._on_add_person)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # People table
        self._people_model = QStandardItemModel(0, 4)
        self._people_model.setHorizontalHeaderLabels(["Name", "Title", "Details", "Actions"])
        self._people_model.itemChanged.connect(self._on_person_item_changed)

        self._people_table = QTableView()
        self._people_table.setModel(self._people_model)
        self._people_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._people_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._people_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                           QAbstractItemView.EditTrigger.SelectedClicked)
        self._people_table.verticalHeader().setVisible(False)
        self._people_table.setAlternatingRowColors(True)

        ph = self._people_table.horizontalHeader()
        ph.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)   # Name
        ph.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)   # Title
        ph.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)       # Details
        ph.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Actions

        layout.addWidget(self._people_table)
        return widget

    def _build_detail_tab(self):
        """Return (widget, text_edit, edit_btn, save_btn, cancel_btn)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        text = QTextEdit()
        text.setReadOnly(True)
        mono = QFont("Consolas", 9)
        text.setFont(mono)
        layout.addWidget(text)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        save_btn = QPushButton("Save")
        save_btn.setVisible(False)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setVisible(False)
        btn_row.addStretch()
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        def on_edit():
            text.setReadOnly(False)
            text.setStyleSheet("background: #fffde7;")
            edit_btn.setVisible(False)
            save_btn.setVisible(True)
            cancel_btn.setVisible(True)

        def on_cancel():
            # reload from DB to discard changes
            self._refresh_detail_pane()
            text.setReadOnly(True)
            text.setStyleSheet("")
            edit_btn.setVisible(True)
            save_btn.setVisible(False)
            cancel_btn.setVisible(False)

        edit_btn.clicked.connect(on_edit)
        cancel_btn.clicked.connect(on_cancel)

        return widget, text, edit_btn, save_btn, cancel_btn

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_table(self):
        """Fetch all rows from DB (active + archived) and populate the model."""
        self._model.itemChanged.disconnect(self._on_item_changed)
        self._model.setRowCount(0)

        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, job_title, customer_name, application_url, "
                "job_description_contents, teal_import_raw, archived, created_at "
                "FROM job_openings ORDER BY id"
            ).fetchall()

        for row in rows:
            self._append_row(row, db.job_has_people(row["id"]))

        self._model.itemChanged.connect(self._on_item_changed)
        self._place_archive_buttons()
        self._on_filter_changed()

    def _append_row(self, row, has_people: bool = False):
        job_id    = row["id"]
        archived  = bool(row["archived"])
        has_jd    = bool(row["job_description_contents"])
        has_res   = bool(row["teal_import_raw"])
        created   = (row["created_at"] or "")[:10]  # date portion only

        def item(text, editable=False):
            it = QStandardItem(text or "")
            it.setEditable(editable)
            if archived:
                it.setForeground(QColor("#aaa"))
            return it

        id_item = item(str(job_id))
        id_item.setData(job_id, Qt.ItemDataRole.UserRole)          # store int id
        id_item.setData(archived, Qt.ItemDataRole.UserRole + 1)    # archived flag

        items = [
            id_item,
            item(row["customer_name"], editable=not archived),
            item(row["job_title"],     editable=not archived),
            item(DOT_FULL if has_jd     else DOT_EMPTY),
            item(DOT_FULL if has_res    else DOT_EMPTY),
            item(DOT_FULL if has_people else DOT_EMPTY),
            item(row["application_url"], editable=not archived),
            item(created),
            item(""),  # Actions column — button set via setIndexWidget below
        ]
        for it in items:
            it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # Center the dot columns
        items[COL_JD].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        items[COL_RESUME].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        items[COL_PEOPLE].setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self._model.appendRow(items)
        model_row = self._model.rowCount() - 1

        # Archive buttons are placed in bulk by _place_archive_buttons()
        # after all rows are appended, so proxy indices are stable.

    # ------------------------------------------------------------------
    # Filter / search
    # ------------------------------------------------------------------

    def _on_filter_changed(self):
        self._proxy.set_show_archived(self._show_archived.isChecked())
        self._proxy.setFilterFixedString(self._search.text().strip())

    def _place_archive_buttons(self):
        """(Re-)place Archive buttons in every active row using current proxy indices."""
        for source_row in range(self._model.rowCount()):
            id_item = self._model.item(source_row, COL_ID)
            archived = bool(id_item.data(Qt.ItemDataRole.UserRole + 1))
            if archived:
                continue
            job_id = id_item.data(Qt.ItemDataRole.UserRole)
            proxy_idx = self._proxy.mapFromSource(
                self._model.index(source_row, COL_ACTIONS)
            )
            if not proxy_idx.isValid():
                continue
            btn = ArchiveButton(job_id)
            btn.clicked.connect(lambda checked=False, jid=job_id: self._on_archive(jid))
            self._table.setIndexWidget(proxy_idx, btn)

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to import", "", "PDF Files (*.pdf)"
        )
        if not path:
            return

        self._import_btn_label = "⬆ Import PDF"
        # Find and disable the import button while working
        toolbar_widget = self.centralWidget().layout().itemAt(0).widget()
        import_btn = toolbar_widget.layout().itemAt(0).widget()
        import_btn.setEnabled(False)
        import_btn.setText("Importing…")

        self._thread = QThread()
        self._worker = ImportWorker(path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_import_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

        self._import_btn = import_btn

    def _on_import_done(self, job_id: int, error_msg: str):
        self._import_btn.setEnabled(True)
        self._import_btn.setText("⬆ Import PDF")
        self._load_table()
        if job_id == -1:
            # Hard failure: record was not created (e.g. file not found)
            QMessageBox.critical(self, "Import Failed", error_msg)
        elif error_msg:
            # Gemini failed: record was created with error text in Resume field
            QMessageBox.warning(
                self,
                "Import Warning — Gemini Error",
                f"A record was created but Gemini could not convert the PDF.\n\n"
                f"{error_msg}\n\n"
                "The error details are shown in the Resume tab for this record."
            )
        else:
            QMessageBox.information(
                self, "Import Complete",
                "Record imported successfully.\n\nEdit the Company and Job Title fields in the table."
            )

    def _on_add_row(self):
        job_id = db.insert_job(teal_import_raw="", job_title=None, customer_name=None)
        self._load_table()
        # Select the new row
        for source_row in range(self._model.rowCount()):
            if self._model.item(source_row, COL_ID).data(Qt.ItemDataRole.UserRole) == job_id:
                proxy_idx = self._proxy.mapFromSource(self._model.index(source_row, COL_COMPANY))
                self._table.setCurrentIndex(proxy_idx)
                self._table.scrollTo(proxy_idx)
                self._table.edit(proxy_idx)
                break

    # ------------------------------------------------------------------
    # Inline editing
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QStandardItem):
        col = item.column()
        if col not in COL_TO_FIELD:
            return
        source_row = item.row()
        id_item = self._model.item(source_row, COL_ID)
        job_id = id_item.data(Qt.ItemDataRole.UserRole)
        field = COL_TO_FIELD[col]
        value = item.text().strip() or None
        db.update_job(job_id, **{field: value})

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def _on_archive(self, job_id: int):
        row = db.get_job(job_id)
        title = row["job_title"] or "(no title)"
        company = row["customer_name"] or "(no company)"
        reply = QMessageBox.question(
            self,
            "Archive job?",
            f'Archive \u201c{title} @ {company}\u201d?\n\nIt will be hidden from the table but kept in the database.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.archive_job(job_id)
            self._load_table()

    # ------------------------------------------------------------------
    # Detail pane
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        self._refresh_detail_pane()

    def _selected_job_id(self) -> int | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_idx = self._proxy.mapToSource(indexes[0])
        id_item = self._model.item(source_idx.row(), COL_ID)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _refresh_detail_pane(self):
        job_id = self._selected_job_id()
        if job_id is None:
            self._tabs.setVisible(False)
            self._detail_label.setVisible(True)
            return

        row = db.get_job(job_id)
        if row is None:
            return

        self._tabs.setVisible(True)
        self._detail_label.setVisible(False)

        self._resume_text.setPlainText(row["teal_import_raw"] or "")
        self._jd_text.setPlainText(row["job_description_contents"] or "")
        self._refresh_people_tab(job_id)

        # Reset both tabs to read-only
        for text, edit_btn, save_btn, cancel_btn in [
            (self._resume_text, self._resume_edit_btn, self._resume_save_btn, self._resume_cancel_btn),
            (self._jd_text,     self._jd_edit_btn,     self._jd_save_btn,     self._jd_cancel_btn),
        ]:
            text.setReadOnly(True)
            text.setStyleSheet("")
            edit_btn.setVisible(True)
            save_btn.setVisible(False)
            cancel_btn.setVisible(False)

        # Wire Save buttons (disconnect first to avoid double connections)
        try:
            self._resume_save_btn.clicked.disconnect()
        except RuntimeError:
            pass
        try:
            self._jd_save_btn.clicked.disconnect()
        except RuntimeError:
            pass

        self._resume_save_btn.clicked.connect(
            lambda: self._save_detail(job_id, "teal_import_raw",
                                      self._resume_text, self._resume_edit_btn,
                                      self._resume_save_btn, self._resume_cancel_btn)
        )
        self._jd_save_btn.clicked.connect(
            lambda: self._save_detail(job_id, "job_description_contents",
                                      self._jd_text, self._jd_edit_btn,
                                      self._jd_save_btn, self._jd_cancel_btn)
        )

    def _save_detail(self, job_id: int, field: str, text_edit: QTextEdit,
                     edit_btn: QPushButton, save_btn: QPushButton, cancel_btn: QPushButton):
        value = text_edit.toPlainText().strip() or None

        # job_description_contents is in update_job's allowed set;
        # teal_import_raw is not (it's the raw import), so handle separately.
        if field == "job_description_contents":
            db.update_job(job_id, job_description_contents=value)
        elif field == "teal_import_raw":
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE job_openings SET teal_import_raw = ?, updated_at = ? WHERE id = ?",
                    (value, db._now(), job_id)
                )
                conn.commit()

        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("")
        edit_btn.setVisible(True)
        save_btn.setVisible(False)
        cancel_btn.setVisible(False)

        # Refresh dot indicators in the table
        self._update_row_indicators(job_id)

    def _update_row_indicators(self, job_id: int):
        """Refresh the JD/Resume/People dot columns for a given job_id after a save."""
        row = db.get_job(job_id)
        if row is None:
            return
        has_jd     = bool(row["job_description_contents"])
        has_res    = bool(row["teal_import_raw"])
        has_people = db.job_has_people(job_id)
        for source_row in range(self._model.rowCount()):
            if self._model.item(source_row, COL_ID).data(Qt.ItemDataRole.UserRole) == job_id:
                self._model.itemChanged.disconnect(self._on_item_changed)
                self._model.item(source_row, COL_JD).setText(DOT_FULL if has_jd else DOT_EMPTY)
                self._model.item(source_row, COL_RESUME).setText(DOT_FULL if has_res else DOT_EMPTY)
                self._model.item(source_row, COL_PEOPLE).setText(DOT_FULL if has_people else DOT_EMPTY)
                self._model.itemChanged.connect(self._on_item_changed)
                break

    # ------------------------------------------------------------------
    # People tab
    # ------------------------------------------------------------------

    def _refresh_people_tab(self, job_id: int):
        """Reload the people table for the given job opening."""
        self._people_model.itemChanged.disconnect(self._on_person_item_changed)
        self._people_model.setRowCount(0)
        self._current_job_id = job_id

        for person in db.get_people_for_job(job_id):
            self._append_person_row(person, job_id)

        self._people_model.itemChanged.connect(self._on_person_item_changed)

    def _append_person_row(self, person, job_id: int):
        def cell(text, editable=True):
            it = QStandardItem(text or "")
            it.setEditable(editable)
            return it

        person_id = person["id"]
        name_item = cell(person["name"])
        name_item.setData(person_id, Qt.ItemDataRole.UserRole)  # store person_id

        items = [
            name_item,
            cell(person["title"]),
            cell(person["details"]),
            cell("", editable=False),  # Actions — button placed below
        ]
        self._people_model.appendRow(items)
        model_row = self._people_model.rowCount() - 1

        btn = QPushButton("Remove")
        btn.setToolTip("Unlink this person from the job opening")
        btn.setFixedWidth(65)
        btn.setFlat(True)
        btn.setStyleSheet(
            "QPushButton { color: #888; font-size: 11px; border: 1px solid #ccc; border-radius: 3px; padding: 2px 4px; }"
            "QPushButton:hover { color: #c00; border-color: #c00; }"
        )
        btn.clicked.connect(lambda checked=False, jid=job_id, pid=person_id: self._on_remove_person(jid, pid))
        self._people_table.setIndexWidget(self._people_model.index(model_row, 3), btn)

    def _on_add_person(self):
        job_id = getattr(self, "_current_job_id", None)
        if job_id is None:
            return
        person_id = db.insert_person(job_id)
        self._refresh_people_tab(job_id)
        self._update_row_indicators(job_id)
        # Put the Name cell of the new row into edit mode
        new_row = self._people_model.rowCount() - 1
        if new_row >= 0:
            idx = self._people_model.index(new_row, 0)
            self._people_table.setCurrentIndex(idx)
            self._people_table.edit(idx)

    def _on_remove_person(self, job_id: int, person_id: int):
        reply = QMessageBox.question(
            self,
            "Remove person?",
            "Remove this person from the job opening?\n\nThey will not be deleted from the database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.unlink_person(job_id, person_id)
            self._refresh_people_tab(job_id)
            self._update_row_indicators(job_id)

    def _on_person_item_changed(self, item: QStandardItem):
        col = item.column()
        col_to_field = {0: "name", 1: "title", 2: "details"}
        if col not in col_to_field:
            return
        # person_id is stored on the Name cell (column 0)
        name_item = self._people_model.item(item.row(), 0)
        person_id = name_item.data(Qt.ItemDataRole.UserRole)
        if person_id is None:
            return
        db.update_person(person_id, **{col_to_field[col]: item.text().strip() or None})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    db.init_db()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
