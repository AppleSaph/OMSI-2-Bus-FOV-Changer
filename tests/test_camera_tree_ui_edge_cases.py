"""Test suite for camera tree UI handling of edge cases with descriptions."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QApplication, QTreeView

from omsi_fov_changer.domain.models import BusFileInfo, CameraPosition
from omsi_fov_changer.ui.camera_tree_controller import CameraTreeController


# Ensure QApplication exists for tests
_app = QApplication.instance() or QApplication([])


def _make_camera(
    line_number: int = 10,
    description: str | None = "test",
    current_fov: str = "55",
) -> CameraPosition:
    return CameraPosition(
        tag="[add_camera_driver]",
        description=description,
        line_number=line_number,
        fov_line_number=line_number + 5,
        current_fov=current_fov,
    )


def _load_controller(cameras: list[CameraPosition]) -> tuple[CameraTreeController, Path]:
    bus_info = BusFileInfo(path=Path("/test/bus.bus"), cameras=cameras, bus_name="Test Bus")
    tree_view = QTreeView()
    controller = CameraTreeController(tree_view)
    controller.load([bus_info])
    return controller, bus_info.path


def _get_items(controller: CameraTreeController) -> tuple[QStandardItem, QStandardItem]:
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    child_item = parent_item.child(0, 0)
    assert child_item is not None
    return parent_item, child_item


def test_camera_with_none_description_displays_fallback_label() -> None:
    controller, _ = _load_controller([_make_camera(description=None)])
    _, child_item = _get_items(controller)
    assert child_item.text() == "Driver camera at line 10"


def test_camera_with_empty_string_description_displays_fallback_label() -> None:
    controller, _ = _load_controller([_make_camera(line_number=15, description="")])
    parent_item, _ = _get_items(controller)
    assert parent_item.child(0, 0).text() == "Driver camera at line 15"


def test_camera_with_valid_description_displays_description() -> None:
    controller, _ = _load_controller([_make_camera(description="0: Looking leftmost")])
    _, child_item = _get_items(controller)
    assert child_item.text() == "0: Looking leftmost"


def test_multiple_cameras_with_mixed_description_types() -> None:
    cameras = [
        _make_camera(line_number=5, description="0: Looking leftmost"),
        _make_camera(line_number=20, description=None),
        _make_camera(line_number=35, description=""),
        _make_camera(line_number=50, description="3: Passenger view"),
    ]
    controller, _ = _load_controller(cameras)
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None and parent_item.rowCount() == 4

    descriptions = [parent_item.child(i, 0).text() for i in range(4)]
    assert descriptions == [
        "0: Looking leftmost",
        "Driver camera at line 20",
        "Driver camera at line 35",
        "3: Passenger view",
    ]


def test_camera_child_row_structure_with_none_description() -> None:
    controller, _ = _load_controller([_make_camera(line_number=25, description=None, current_fov="60")])
    parent_item, child_item = _get_items(controller)

    assert parent_item.child(0, 0).text() == "Driver camera at line 25"
    assert parent_item.child(0, 1).text() == "60"
    assert parent_item.child(0, 2).text() == "60"

    data = child_item.data(Qt.ItemDataRole.UserRole)
    assert isinstance(data, dict) and data.get("type") == "camera"
    assert data.get("fov_line_number") == 30
    assert data.get("current_fov") == "60"


def test_bulk_apply_works_with_none_description_cameras() -> None:
    controller, _ = _load_controller([_make_camera(line_number=10, description=None)])
    parent_item, camera_item = _get_items(controller)

    camera_item.setCheckState(Qt.CheckState.Checked)
    assert len(controller.collect_bulk_targets()) == 1

    controller.apply_bulk_value(controller.collect_bulk_targets(), "70")
    assert parent_item.child(0, 2).text() == "70"


def test_pending_changes_count_includes_modified_cameras_with_none_description() -> None:
    controller, _ = _load_controller([_make_camera(line_number=10, description=None)])
    assert controller.count_pending_changes() == 0

    parent_item, camera_item = _get_items(controller)
    camera_item.setCheckState(Qt.CheckState.Checked)
    parent_item.child(0, 2).setText("70")

    assert controller.count_pending_changes() == 1


def test_collect_updates_filters_cameras_with_empty_new_fov_values() -> None:
    controller, _ = _load_controller([_make_camera(line_number=10, description=None)])
    parent_item, camera_item = _get_items(controller)

    camera_item.setCheckState(Qt.CheckState.Checked)
    parent_item.child(0, 2).setText("")

    assert len(controller.collect_updates_by_file()) == 0


def test_tree_loads_without_errors_for_only_none_description_cameras() -> None:
    cameras = [_make_camera(line_number=i, description=None) for i in range(5)]
    controller, _ = _load_controller(cameras)

    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None and parent_item.rowCount() == 5

    for i in range(5):
        child = parent_item.child(i, 0)
        assert child is not None and child.text() == f"Driver camera at line {i}"


def test_sync_persistent_editors_updates_model_from_editor(monkeypatch: object) -> None:
    controller, _ = _load_controller([_make_camera(description="0: Looking leftmost")])
    parent_item = controller.camera_model.item(0, 0)
    new_fov_item = parent_item.child(0, 2)
    assert new_fov_item.text() == "55"

    monkeypatch.setattr(controller, "_get_editor_text", lambda idx: "72")
    controller.sync_persistent_editors_to_model()
    assert new_fov_item.text() == "72"


def test_sync_persistent_editors_skips_unchanged(monkeypatch: object) -> None:
    controller, _ = _load_controller([_make_camera(description="0: Looking leftmost")])
    parent_item = controller.camera_model.item(0, 0)
    new_fov_item = parent_item.child(0, 2)
    original_text = new_fov_item.text()

    monkeypatch.setattr(controller, "_get_editor_text", lambda idx: "55")
    controller.sync_persistent_editors_to_model()
    assert new_fov_item.text() == original_text
