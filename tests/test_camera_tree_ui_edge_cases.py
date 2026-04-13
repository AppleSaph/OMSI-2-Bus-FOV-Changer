"""Test suite for camera tree UI handling of edge cases with descriptions."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeView

from omsi_fov_changer.domain.models import BusFileInfo, CameraPosition
from omsi_fov_changer.ui.camera_tree_controller import CameraTreeController


# Ensure QApplication exists for tests
_app = QApplication.instance() or QApplication([])


def _create_tree_controller() -> CameraTreeController:
    """Create a CameraTreeController with a fresh tree view for testing."""
    tree_view = QTreeView()
    controller = CameraTreeController(tree_view)
    return controller


def test_camera_with_none_description_displays_fallback_label() -> None:
    """Test that a camera with None description shows the fallback label."""
    controller = _create_tree_controller()

    # Create a camera with None description
    camera = CameraPosition(
        tag="[add_camera_driver]",
        description=None,
        line_number=42,
        fov_line_number=47,
        current_fov="55",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Get the parent (bus) item
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None

    # Get the child (camera) item
    child_item = parent_item.child(0, 0)
    assert child_item is not None

    # Verify the fallback description is used
    expected_description = "Driver camera at line 42"
    assert child_item.text() == expected_description


def test_camera_with_empty_string_description_displays_fallback_label() -> None:
    """Test that a camera with empty string description shows the fallback label."""
    controller = _create_tree_controller()

    # Create a camera with empty string description
    camera = CameraPosition(
        tag="[add_camera_driver]",
        description="",
        line_number=15,
        fov_line_number=20,
        current_fov="45",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Get the parent (bus) item
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None

    # Get the child (camera) item
    child_item = parent_item.child(0, 0)
    assert child_item is not None

    # Verify the fallback description is used
    expected_description = "Driver camera at line 15"
    assert child_item.text() == expected_description


def test_camera_with_valid_description_displays_description() -> None:
    """Test that a camera with a valid description displays it correctly."""
    controller = _create_tree_controller()

    # Create a camera with a valid description
    camera = CameraPosition(
        tag="[add_camera_driver]",
        description="0: Looking leftmost",
        line_number=10,
        fov_line_number=15,
        current_fov="60",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Get the parent (bus) item
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None

    # Get the child (camera) item
    child_item = parent_item.child(0, 0)
    assert child_item is not None

    # Verify the actual description is used
    assert child_item.text() == "0: Looking leftmost"


def test_multiple_cameras_with_mixed_description_types() -> None:
    """Test that multiple cameras with various description types are handled correctly."""
    controller = _create_tree_controller()

    cameras = [
        CameraPosition(
            tag="[add_camera_driver]",
            description="0: Looking leftmost",
            line_number=5,
            fov_line_number=10,
            current_fov="55",
        ),
        CameraPosition(
            tag="[add_camera_driver]",
            description=None,
            line_number=20,
            fov_line_number=25,
            current_fov="45",
        ),
        CameraPosition(
            tag="[add_camera_driver]",
            description="",
            line_number=35,
            fov_line_number=40,
            current_fov="50",
        ),
        CameraPosition(
            tag="[add_camera_driver]",
            description="3: Passenger view",
            line_number=50,
            fov_line_number=55,
            current_fov="35",
        ),
    ]

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=cameras,
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Get the parent (bus) item
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    assert parent_item.rowCount() == 4

    # Verify each camera's description
    descriptions = []
    for i in range(4):
        child = parent_item.child(i, 0)
        assert child is not None
        descriptions.append(child.text())

    assert descriptions == [
        "0: Looking leftmost",
        "Driver camera at line 20",
        "Driver camera at line 35",
        "3: Passenger view",
    ]


def test_camera_child_row_structure_with_none_description() -> None:
    """Test that the complete child row structure is created correctly for None descriptions."""
    controller = _create_tree_controller()

    camera = CameraPosition(
        tag="[add_camera_driver]",
        description=None,
        line_number=25,
        fov_line_number=30,
        current_fov="60",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None

    # Check all three columns exist
    position_item = parent_item.child(0, 0)
    current_fov_item = parent_item.child(0, 1)
    new_fov_item = parent_item.child(0, 2)

    assert position_item is not None
    assert current_fov_item is not None
    assert new_fov_item is not None

    # Verify the content
    assert position_item.text() == "Driver camera at line 25"
    assert current_fov_item.text() == "60"
    assert new_fov_item.text() == "60"

    # Verify item roles and user data
    camera_data = position_item.data(Qt.ItemDataRole.UserRole)
    assert camera_data is not None
    assert isinstance(camera_data, dict)
    assert camera_data.get("type") == "camera"
    assert camera_data.get("fov_line_number") == 30
    assert camera_data.get("current_fov") == "60"


def test_bulk_apply_works_with_none_description_cameras() -> None:
    """Test that bulk FOV application works correctly for cameras with None descriptions."""
    controller = _create_tree_controller()

    cameras = [
        CameraPosition(
            tag="[add_camera_driver]",
            description=None,
            line_number=10,
            fov_line_number=15,
            current_fov="55",
        ),
    ]

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=cameras,
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Get the camera item and check it
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    camera_item = parent_item.child(0, 0)
    assert camera_item is not None

    # Check the camera and collect targets
    camera_item.setCheckState(Qt.CheckState.Checked)
    targets = controller.collect_bulk_targets()
    assert len(targets) == 1

    # Apply bulk value
    controller.apply_bulk_value(targets, "70")

    # Verify the new FOV was set
    new_fov_item = parent_item.child(0, 2)
    assert new_fov_item is not None
    assert new_fov_item.text() == "70"


def test_pending_changes_count_includes_modified_cameras_with_none_description() -> None:
    """Test that pending changes are correctly counted for cameras with None descriptions."""
    controller = _create_tree_controller()

    camera = CameraPosition(
        tag="[add_camera_driver]",
        description=None,
        line_number=10,
        fov_line_number=15,
        current_fov="55",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    # Initially no changes
    assert controller.count_pending_changes() == 0

    # Modify the camera
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    camera_item = parent_item.child(0, 0)
    assert camera_item is not None
    camera_item.setCheckState(Qt.CheckState.Checked)

    new_fov_item = parent_item.child(0, 2)
    assert new_fov_item is not None
    new_fov_item.setText("70")

    # Should now have 1 pending change
    assert controller.count_pending_changes() == 1


def test_collect_updates_filters_cameras_with_empty_new_fov_values() -> None:
    """Test that cameras with None descriptions but empty new FOV values are excluded."""
    controller = _create_tree_controller()

    camera = CameraPosition(
        tag="[add_camera_driver]",
        description=None,
        line_number=10,
        fov_line_number=15,
        current_fov="55",
    )

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])

    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    camera_item = parent_item.child(0, 0)
    assert camera_item is not None
    camera_item.setCheckState(Qt.CheckState.Checked)

    # Set new FOV to empty string
    new_fov_item = parent_item.child(0, 2)
    assert new_fov_item is not None
    new_fov_item.setText("")

    # Should not include this in updates
    updates = controller.collect_updates_by_file()
    assert len(updates) == 0


def test_tree_loads_without_errors_for_only_none_description_cameras() -> None:
    """Test that the tree loads successfully when all cameras have None descriptions."""
    controller = _create_tree_controller()

    cameras = [
        CameraPosition(
            tag="[add_camera_driver]",
            description=None,
            line_number=i,
            fov_line_number=i + 5,
            current_fov="55",
        )
        for i in range(5)
    ]

    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=cameras,
        bus_name="Test Bus",
    )

    # This should not raise an exception
    controller.load([bus_info])

    # Verify the tree was populated correctly
    parent_item = controller.camera_model.item(0, 0)
    assert parent_item is not None
    assert parent_item.rowCount() == 5

    # Verify all children have fallback descriptions
    for i in range(5):
        child = parent_item.child(i, 0)
        assert child is not None
        assert child.text() == f"Driver camera at line {i}"


def test_sync_persistent_editors_logs_warning_on_count_mismatch(monkeypatch, caplog) -> None:
    """Test that a warning is logged when editor widgets and camera rows do not match."""
    controller = _create_tree_controller()

    camera = CameraPosition(
        tag="[add_camera_driver]",
        description="0: Looking leftmost",
        line_number=10,
        fov_line_number=15,
        current_fov="55",
    )
    bus_info = BusFileInfo(
        path=Path("/test/bus.bus"),
        cameras=[camera],
        bus_name="Test Bus",
    )

    controller.load([bus_info])
    monkeypatch.setattr(controller.tree_view, "findChildren", lambda *args, **kwargs: [], raising=False)

    with caplog.at_level(logging.WARNING):
        controller.sync_persistent_editors_to_model()

    assert "Persistent editor count mismatch" in caplog.text



