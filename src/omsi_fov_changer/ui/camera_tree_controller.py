from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QFontMetrics, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QLineEdit, QTreeView

from omsi_fov_changer.domain.models import BusFileInfo, CameraPosition
from omsi_fov_changer.ui.fov_editor_delegate import FovEditorDelegate
from omsi_fov_changer.ui.view_utils import set_item_modified_style

PendingChangeCallback = Callable[[], None]
logger = logging.getLogger(__name__)


def _sync_checkbox_state(item: QStandardItem) -> None:
    parent_item = item.parent()
    if parent_item is None:
        state = item.checkState()
        if state == Qt.CheckState.PartiallyChecked:
            return
        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child is not None:
                child.setCheckState(state)
        return

    checked = 0
    unchecked = 0
    total = parent_item.rowCount()
    for row in range(total):
        child = parent_item.child(row, 0)
        if child is None:
            continue
        state = child.checkState()
        if state == Qt.CheckState.Checked:
            checked += 1
        elif state == Qt.CheckState.Unchecked:
            unchecked += 1

    if checked == total and total > 0:
        parent_item.setCheckState(Qt.CheckState.Checked)
    elif unchecked == total and total > 0:
        parent_item.setCheckState(Qt.CheckState.Unchecked)
    else:
        parent_item.setCheckState(Qt.CheckState.PartiallyChecked)


class CameraTreeController:
    """Encapsulates model/view behavior for the camera positions tree."""

    def __init__(self, tree_view: QTreeView, on_pending_changes_changed: PendingChangeCallback | None = None) -> None:
        self.tree_view = tree_view
        self._on_pending_changes_changed = on_pending_changes_changed
        self._updating_model = False
        self.camera_model = self._create_camera_model()
        self.delegate = FovEditorDelegate(self.tree_view)

        self.tree_view.setModel(self.camera_model)
        self.tree_view.setItemDelegateForColumn(2, self.delegate)
        self._configure_tree_columns()

    def load(self, file_infos: list[BusFileInfo]) -> None:
        old_model = self.camera_model
        self._updating_model = True
        self.tree_view.setModel(None)

        self.camera_model = self._create_camera_model()
        self.tree_view.setModel(self.camera_model)
        self.tree_view.setItemDelegateForColumn(2, self.delegate)
        self._configure_tree_columns()
        self.camera_model.blockSignals(True)

        if not file_infos:
            self.camera_model.appendRow(
                [
                    self._make_text_item("No driver camera positions found."),
                    self._make_text_item(""),
                    self._make_text_item(""),
                ]
            )
            self.camera_model.blockSignals(False)
            self._updating_model = False
            old_model.deleteLater()
            self._notify_pending_changes_changed()
            return

        for info in file_infos:
            self.camera_model.appendRow(self._create_bus_parent_row(info))
            parent_index = self.camera_model.index(self.camera_model.rowCount() - 1, 0)
            self.tree_view.expand(parent_index)
            self._open_persistent_editors_for_parent(parent_index)

        self.camera_model.blockSignals(False)
        self._updating_model = False
        old_model.deleteLater()
        self._notify_pending_changes_changed()

    def fit_columns(self) -> None:
        self._configure_tree_columns()

    def sync_persistent_editors_to_model(self) -> None:
        """Sync text from persistent QLineEdit editors back into the model.

        Uses tree_view.indexWidget(index) for deterministic 1:1 mapping between
        each column-2 QModelIndex and its editor widget, avoiding reliance on
        findChildren() ordering which Qt does not guarantee.
        """
        for row in range(self.camera_model.rowCount()):
            parent = self.camera_model.item(row, 0)
            if parent is None:
                continue
            parent_data = parent.data(Qt.ItemDataRole.UserRole)
            if not isinstance(parent_data, dict) or parent_data.get("type") != "parent":
                continue

            for child_row in range(parent.rowCount()):
                position_item = parent.child(child_row, 0)
                new_item = parent.child(child_row, 2)
                if position_item is None or new_item is None:
                    continue

                # Get the QModelIndex for column 2 of this row and query its editor directly.
                child_index = position_item.index()
                new_index = child_index.sibling(child_index.row(), 2)
                editor_text = self._get_editor_text(new_index)
                if editor_text is not None:
                    stripped = editor_text.strip()
                    if new_item.text() != stripped:
                        new_item.setText(stripped)

    def _get_editor_text(self, index) -> str | None:
        """Return the text from the persistent editor for a given QModelIndex."""
        widget = self.tree_view.indexWidget(index)
        if widget is not None and isinstance(widget, QLineEdit):
            return widget.text()
        return None

    def count_pending_changes(self) -> int:
        return sum(len(items) for items in self.collect_updates_by_file().values())

    def collect_bulk_targets(self) -> list[QStandardItem]:
        targets: list[QStandardItem] = []
        seen: set[int] = set()

        for row in range(self.camera_model.rowCount()):
            parent = self.camera_model.item(row, 0)
            if parent is None or parent.data(Qt.ItemDataRole.UserRole) is None:
                continue
            if parent.checkState() == Qt.CheckState.Checked:
                for child_row in range(parent.rowCount()):
                    child = parent.child(child_row, 0)
                    if child is not None and id(child) not in seen:
                        seen.add(id(child))
                        targets.append(child)
                continue

            for child_row in range(parent.rowCount()):
                child = parent.child(child_row, 0)
                if child is None:
                    continue
                if child.checkState() != Qt.CheckState.Checked:
                    continue
                if id(child) in seen:
                    continue
                seen.add(id(child))
                targets.append(child)

        return targets

    def apply_bulk_value(self, targets: list[QStandardItem], bulk_value: str) -> None:
        """Applies a single value to multiple camera FOV fields."""
        self._updating_model = True
        try:
            for item in targets:
                new_item = item.parent().child(item.row(), 2) if item.parent() is not None else None
                if new_item is None:
                    continue
                new_item.setText(bulk_value)
                # _on_item_changed returns early when _updating_model=True, so we set
                # modified state here directly instead of relying on the signal callback.
                self._set_row_modified(item.parent(), item.row(), modified=True)

            self._notify_pending_changes_changed()
        finally:
            self._updating_model = False

    def collect_updates_by_file(self) -> dict[Path, dict[int, str]]:
        updates_by_file: dict[Path, dict[int, str]] = {}

        for row in range(self.camera_model.rowCount()):
            parent = self.camera_model.item(row, 0)
            if parent is None:
                continue

            parent_data = parent.data(Qt.ItemDataRole.UserRole)
            if not isinstance(parent_data, dict) or parent_data.get("type") != "parent":
                continue

            file_path = Path(parent_data["file_path"])
            for child_row in range(parent.rowCount()):
                position_item = parent.child(child_row, 0)
                current_item = parent.child(child_row, 1)
                new_item = parent.child(child_row, 2)
                if position_item is None or current_item is None or new_item is None:
                    continue

                child_data = position_item.data(Qt.ItemDataRole.UserRole)
                if not isinstance(child_data, dict) or child_data.get("type") != "camera":
                    continue

                new_value = new_item.text().strip()
                if not new_value:
                    continue

                if new_value == current_item.text().strip():
                    continue

                updates_by_file.setdefault(file_path, {})[int(child_data["fov_line_number"])] = new_value

        return updates_by_file

    def _create_camera_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 3, self.tree_view)
        model.setHorizontalHeaderLabels(["Bus / Camera Position", "Current FOV", "New FOV"])
        model.itemChanged.connect(self._on_item_changed)
        return model

    def _create_bus_parent_row(self, info: BusFileInfo) -> list[QStandardItem]:
        bus_name = info.bus_name or "Unknown bus"
        parent_label = self._make_text_item(f"{info.path.name} | {bus_name}")
        parent_label.setCheckable(True)
        parent_label.setCheckState(Qt.CheckState.Unchecked)
        parent_label.setEditable(False)
        parent_label.setData({"type": "parent", "file_path": str(info.path)}, Qt.ItemDataRole.UserRole)

        parent_current = self._make_text_item(f"{len(info.cameras)} position(s)")
        parent_current.setEditable(False)
        parent_new = self._make_text_item("")
        parent_new.setEditable(False)

        for camera in info.cameras:
            parent_label.appendRow(self._create_camera_child_row(info.path, camera))

        return [parent_label, parent_current, parent_new]

    def _create_camera_child_row(self, file_path: Path, camera: CameraPosition) -> list[QStandardItem]:
        description = camera.description or f"Driver camera at line {camera.line_number}"
        position_item = self._make_text_item(description)
        position_item.setCheckable(True)
        position_item.setCheckState(Qt.CheckState.Unchecked)
        position_item.setEditable(False)
        position_item.setData(
            {
                "type": "camera",
                "file_path": str(file_path),
                "fov_line_number": camera.fov_line_number,
                "current_fov": camera.current_fov,
            },
            Qt.ItemDataRole.UserRole,
        )

        current_item = self._make_text_item(camera.current_fov)
        current_item.setEditable(False)

        new_item = self._make_text_item(camera.current_fov)
        new_item.setEditable(True)
        new_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return [position_item, current_item, new_item]

    def _open_persistent_editors_for_parent(self, parent_index: QModelIndex) -> None:
        parent_item = self.camera_model.itemFromIndex(parent_index)
        if parent_item is None:
            return

        for row in range(parent_item.rowCount()):
            child_position_item = parent_item.child(row, 0)
            if child_position_item is None:
                continue
            child_index = child_position_item.index()
            new_index = child_index.sibling(child_index.row(), 2)
            self.tree_view.openPersistentEditor(new_index)

    def _configure_tree_columns(self) -> None:
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)

        fov_width = self._fov_column_pixel_width()
        self.tree_view.setColumnWidth(1, fov_width)
        self.tree_view.setColumnWidth(2, fov_width)

    def _fov_column_pixel_width(self) -> int:
        metrics = QFontMetrics(self.tree_view.font())
        return metrics.horizontalAdvance("0" * 16) + 24

    @staticmethod
    def _make_text_item(text: str) -> QStandardItem:
        item = QStandardItem(text)
        item.setEditable(False)
        return item

    def _on_item_changed(self, item: QStandardItem) -> None:
        if self._updating_model:
            return

        self._updating_model = True
        try:
            if item.column() == 0 and item.isCheckable():
                _sync_checkbox_state(item)
            elif item.column() == 2:
                self._sync_modified_state(item)
        finally:
            self._updating_model = False
            self._notify_pending_changes_changed()

    def _sync_modified_state(self, item: QStandardItem) -> None:
        parent_item = item.parent()
        if parent_item is None:
            return

        current_item = parent_item.child(item.row(), 1)
        if current_item is None:
            return

        if item.text().strip() == current_item.text().strip():
            self._set_row_modified(parent_item, item.row(), modified=False)
        else:
            self._set_row_modified(parent_item, item.row(), modified=True)

    def _set_row_modified(self, parent_item: QStandardItem, row: int, modified: bool) -> None:
        position_item = parent_item.child(row, 0)
        current_item = parent_item.child(row, 1)
        new_item = parent_item.child(row, 2)
        if position_item is None or current_item is None or new_item is None:
            return

        suffix = " *"
        label = position_item.text().removesuffix(suffix)
        position_item.setText(f"{label}{suffix}" if modified else label)

        for item in (position_item, current_item, new_item):
            set_item_modified_style(item, modified)

    def _notify_pending_changes_changed(self) -> None:
        if self._on_pending_changes_changed is not None:
            self._on_pending_changes_changed()

    @property
    def model(self) -> QStandardItemModel:
        return self.camera_model


