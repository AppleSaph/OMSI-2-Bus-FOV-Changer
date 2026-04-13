from __future__ import annotations

from pathlib import Path

from omsi_fov_changer.services.fov_service import FovService, discover_files


def _sample_bus(
    camera_tag: str = "[add_camera_driver]",
    fov: str = "55",
    description: str | None = None,
) -> str:
    lines = ["[friendlyname]", "My Test Bus", "", "header"]
    if description:
        lines.append(description)
    lines.extend(
        [
            camera_tag,
            "x",
            "y",
            "z",
            "rot",
            fov,
            "yaw",
            "pitch",
            "",
        ]
    )
    return "\n".join(lines)


def _sample_multi_driver_bus() -> str:
    return "\n".join(
        [
            "[friendlyname]",
            "My Test Bus",
            "Variant A",
            "",
            "header",
            "0: Looking leftmost",
            "[add_camera_driver]",
            "x",
            "y",
            "z",
            "rot",
            "55",
            "yaw",
            "pitch",
            "",
            "1: Looking rightmost",
            "[add_camera_driver]",
            "x",
            "y",
            "z",
            "rot",
            "45",
            "yaw",
            "pitch",
            "",
            "2: Passenger view",
            "[add_camera_pax]",
            "x",
            "y",
            "z",
            "rot",
            "35",
            "yaw",
            "pitch",
            "",
        ]
    )



def test_discover_files_only_bus(tmp_path: Path) -> None:


    (tmp_path / "a.bus").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    (tmp_path / "c.bus.bak").write_text("x", encoding="utf-8")

    files = discover_files(
        folder=tmp_path,
        only_buses=True,
        recursive=False,
    )

    assert [file.name for file in files] == ["a.bus"]


def test_replace_in_file_updates_only_requested_line_numbers(tmp_path: Path) -> None:
    service = FovService()
    bus_file = tmp_path / "test.bus"
    bus_file.write_text(_sample_multi_driver_bus(), encoding="utf-8")

    parsed = service.parse_cameras_from_file(bus_file)
    assert parsed is not None
    assert len(parsed.cameras) == 2

    first_fov_line = parsed.cameras[0].fov_line_number

    result = service.replace_in_file(
        file_path=bus_file,
        backup=False,
        updates_by_line_number={first_fov_line: "70"},
    )

    content = bus_file.read_text(encoding="utf-8")
    assert result.changed is True
    assert result.change_count == 1
    assert "\n70\n" in content
    assert "\n45\n" in content


def test_replace_in_file_creates_backup(tmp_path: Path) -> None:
    service = FovService()
    bus_file = tmp_path / "test.bus"
    original = _sample_bus(fov="40")
    bus_file.write_text(original, encoding="utf-8")

    parsed = service.parse_cameras_from_file(bus_file)
    assert parsed is not None

    service.replace_in_file(
        file_path=bus_file,
        backup=True,
        updates_by_line_number={parsed.cameras[0].fov_line_number: "65"},
    )

    backup_file = tmp_path / "test.bus.bak"
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == original


def test_replace_in_file_ignores_non_driver_camera_tag(tmp_path: Path) -> None:
    service = FovService()
    bus_file = tmp_path / "test.bus"
    bus_file.write_text(_sample_bus(camera_tag="[add_camera_pax]", fov="45"), encoding="utf-8")

    parsed = service.parse_cameras_from_file(bus_file)
    assert parsed is not None
    assert parsed.cameras == []

    result = service.replace_in_file(
        file_path=bus_file,
        backup=False,
        updates_by_line_number={},
    )

    assert result.changed is False
    assert result.change_count == 0
    assert "45" in bus_file.read_text(encoding="utf-8")


def test_replace_in_files_supports_multiple_files_and_values(tmp_path: Path) -> None:
    service = FovService()

    first = tmp_path / "one.bus"
    second = tmp_path / "two.bus"
    first.write_text(_sample_bus(fov="30"), encoding="utf-8")
    second.write_text(_sample_bus(fov="40"), encoding="utf-8")

    first_info = service.parse_cameras_from_file(first)
    second_info = service.parse_cameras_from_file(second)
    assert first_info is not None and second_info is not None

    batch = service.replace_in_files(
        files=[first, second],
        backup=False,
        updates_by_file={
            first: {first_info.cameras[0].fov_line_number: "55"},
            second: {second_info.cameras[0].fov_line_number: "65"},
        },
    )

    assert batch.processed_file_count == 2
    assert batch.changed_file_count == 2
    assert "55" in first.read_text(encoding="utf-8")
    assert "65" in second.read_text(encoding="utf-8")


def test_parse_cameras_from_file_extracts_driver_positions_and_bus_name(tmp_path: Path) -> None:
    service = FovService()
    bus_file = tmp_path / "test.bus"
    bus_file.write_text(_sample_multi_driver_bus(), encoding="utf-8")

    bus_info = service.parse_cameras_from_file(bus_file)

    assert bus_info is not None
    assert bus_info.bus_name == "My Test Bus - Variant A"
    assert len(bus_info.cameras) == 2
    assert bus_info.cameras[0].tag == "[add_camera_driver]"
    assert bus_info.cameras[0].description == "0: Looking leftmost"
    assert bus_info.cameras[1].description == "1: Looking rightmost"


def test_parse_cameras_ignores_non_driver_sections(tmp_path: Path) -> None:
    service = FovService()
    bus_file = tmp_path / "test.bus"
    bus_file.write_text(_sample_bus(camera_tag="[add_camera_pax]", description="Passenger"), encoding="utf-8")

    bus_info = service.parse_cameras_from_file(bus_file)

    assert bus_info is not None
    assert bus_info.cameras == []
