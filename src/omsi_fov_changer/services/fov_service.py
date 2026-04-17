from __future__ import annotations

from pathlib import Path
from typing import Iterable

from omsi_fov_changer.domain.models import BatchResult, BusFileInfo, CameraPosition, ChangeRecord, FileResult

SUPPORTED_CAMERA_TAGS = ["[add_camera_driver]"]


def discover_files(folder: Path, only_buses: bool, recursive: bool = False) -> list[Path]:
    if recursive:
        candidates = [path for path in folder.rglob("*") if path.is_file()]
    else:
        candidates = [path for path in folder.iterdir() if path.is_file()]

    filtered: list[Path] = []
    for path in candidates:
        if path.name.endswith(".bak"):
            continue
        if only_buses and path.suffix.lower() != ".bus":
            continue
        filtered.append(path)

    return sorted(filtered)


class FovService:
    """Provides file discovery, FOV replacement, and camera parsing operations."""

    def parse_cameras_from_file(self, file_path: Path) -> BusFileInfo | None:
        """Parse a .bus file and extract driver camera positions with descriptions."""
        lines = self._read_text_lines(file_path)
        if lines is None:
            return None

        cameras: list[CameraPosition] = []

        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped not in SUPPORTED_CAMERA_TAGS:
                continue

            fov_line_index = index + 5
            if fov_line_index >= len(lines):
                continue

            current_fov = lines[fov_line_index].strip()

            description: str | None = None
            if index > 0:
                prev_line = lines[index - 1].strip()
                if prev_line and (prev_line.startswith(";") or prev_line[0].isdigit()):
                    description = prev_line
                elif index > 1:
                    prev_prev_line = lines[index - 2].strip()
                    if prev_prev_line and (prev_prev_line.startswith(";") or prev_prev_line[0].isdigit()):
                        description = prev_prev_line

            cameras.append(
                CameraPosition(
                    tag=stripped,
                    description=description,
                    line_number=index + 1,
                    fov_line_number=fov_line_index + 1,
                    current_fov=current_fov,
                )
            )

        return BusFileInfo(path=file_path, cameras=cameras, bus_name=self._extract_bus_name(lines))

    def replace_in_files(
            self,
            files: Iterable[Path],
            backup: bool,
            updates_by_file: dict[Path, dict[int, str]],
            fov_line_offset: int = 5,
    ) -> BatchResult:
        results = [
            self.replace_in_file(
                file_path=file_path,
                backup=backup,
                updates_by_line_number=updates_by_file.get(file_path, {}),
                fov_line_offset=fov_line_offset,
            )
            for file_path in files
        ]
        return BatchResult(file_results=results)

    def replace_in_file(
            self,
            file_path: Path,
            backup: bool,
            updates_by_line_number: dict[int, str],
            fov_line_offset: int = 5,
    ) -> FileResult:
        encodings = ("utf-8", "latin-1")
        original_lines: list[str] = []
        chosen_encoding: str | None = None

        for encoding in encodings:
            try:
                original_lines = file_path.read_text(encoding=encoding).splitlines(keepends=True)
                chosen_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if chosen_encoding is None:
            return FileResult(
                file_path=file_path,
                changed=False,
                change_count=0,
                warnings=[f"Could not decode file: {file_path}"],
            )

        lines = original_lines.copy()
        changes: list[ChangeRecord] = []
        warnings: list[str] = []
        line_ending = self._detect_line_ending(original_lines)

        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped not in SUPPORTED_CAMERA_TAGS:
                continue

            value_index = index + fov_line_offset
            if value_index >= len(lines):
                warnings.append(
                    f"Unexpected end of file after {stripped} in {file_path} (line {index + 1})"
                )
                continue

            line_number = value_index + 1
            if line_number not in updates_by_line_number:
                continue

            new_value = updates_by_line_number[line_number]
            old_value = lines[value_index].strip()
            if old_value == new_value:
                continue

            lines[value_index] = f"{new_value}{line_ending}"
            changes.append(
                ChangeRecord(
                    file_path=file_path,
                    line_number=line_number,
                    camera_tag=stripped,
                    old_value=old_value,
                    new_value=new_value,
                )
            )

        if not changes:
            return FileResult(
                file_path=file_path,
                changed=False,
                change_count=0,
                changes=[],
                warnings=warnings,
            )

        if backup:
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            backup_path.write_text("".join(original_lines), encoding=chosen_encoding)

        file_path.write_text("".join(lines), encoding=chosen_encoding)

        return FileResult(
            file_path=file_path,
            changed=True,
            change_count=len(changes),
            changes=changes,
            warnings=warnings,
        )

    @staticmethod
    def _detect_line_ending(lines: list[str]) -> str:
        for line in lines:
            if line.endswith("\r\n"):
                return "\r\n"
            if line.endswith("\n"):
                return "\n"
        return "\n"

    @staticmethod
    def _read_text_lines(file_path: Path) -> list[str] | None:
        for encoding in ("utf-8", "latin-1"):
            try:
                return file_path.read_text(encoding=encoding).splitlines()
            except UnicodeDecodeError:
                continue
        return None

    @staticmethod
    def _extract_bus_name(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if line.strip().lower() != "[friendlyname]":
                continue

            name_lines: list[str] = []
            for candidate in lines[index + 1:]:
                stripped = candidate.strip()
                if not stripped:
                    if name_lines:
                        break
                    continue
                if stripped.startswith("["):
                    break
                name_lines.append(stripped)

            if name_lines:
                return " - ".join(name_lines)
            return None

        return None


