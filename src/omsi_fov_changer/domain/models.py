from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CameraPosition:
    """Represents a single camera position in a .bus file."""

    tag: str
    description: str | None
    line_number: int
    fov_line_number: int
    current_fov: str


@dataclass(slots=True)
class BusFileInfo:
    """Metadata about a .bus file and its cameras."""

    path: Path
    cameras: list[CameraPosition]
    bus_name: str | None = None


@dataclass(slots=True)
class ChangeRecord:
    """Represents one changed FOV value in a file."""

    file_path: Path
    line_number: int
    camera_tag: str
    old_value: str
    new_value: str


@dataclass(slots=True)
class FileResult:
    """Result of processing a single file."""

    file_path: Path
    changed: bool
    change_count: int
    changes: list[ChangeRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BatchResult:
    """Result of processing multiple files."""

    file_results: list[FileResult] = field(default_factory=list)

    @property
    def processed_file_count(self) -> int:
        return len(self.file_results)

    @property
    def changed_file_count(self) -> int:
        return sum(1 for item in self.file_results if item.changed)

    @property
    def total_changes(self) -> int:
        return sum(item.change_count for item in self.file_results)
