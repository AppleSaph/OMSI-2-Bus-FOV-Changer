from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
)


@dataclass(slots=True)
class SourceSection:
    group: QGroupBox
    folder_radio: QRadioButton
    file_radio: QRadioButton
    source_input: QLineEdit


@dataclass(slots=True)
class OptionsSection:
    group: QGroupBox
    only_buses_checkbox: QCheckBox
    recursive_checkbox: QCheckBox
    backup_checkbox: QCheckBox


@dataclass(slots=True)
class ActionSection:
    group: QGroupBox
    bulk_fov_input: QLineEdit
    bulk_apply_button: QPushButton
    save_button: QPushButton


def build_source_section(on_browse: Callable[[], None]) -> SourceSection:
    group = QGroupBox("Source")
    grid = QGridLayout(group)

    folder_radio = QRadioButton("Folder")
    file_radio = QRadioButton("Single File")
    folder_radio.setChecked(True)

    source_input = QLineEdit()
    source_input.setPlaceholderText("Select folder or file containing .bus files")
    browse_button = QPushButton("Browse")
    browse_button.clicked.connect(on_browse)

    grid.addWidget(QLabel("Source Type:"), 0, 0)
    grid.addWidget(folder_radio, 0, 1)
    grid.addWidget(file_radio, 0, 2)
    grid.addWidget(QLabel("Path:"), 1, 0)
    grid.addWidget(source_input, 1, 1)
    grid.addWidget(browse_button, 1, 2)

    return SourceSection(
        group=group,
        folder_radio=folder_radio,
        file_radio=file_radio,
        source_input=source_input,
    )


def build_options_section() -> OptionsSection:
    group = QGroupBox("Options")
    grid = QGridLayout(group)

    only_buses_checkbox = QCheckBox("Only .bus files")
    only_buses_checkbox.setChecked(True)
    recursive_checkbox = QCheckBox("Include subfolders")
    backup_checkbox = QCheckBox("Create .bak backups")
    backup_checkbox.setChecked(True)

    grid.addWidget(only_buses_checkbox, 0, 0)
    grid.addWidget(recursive_checkbox, 0, 1)
    grid.addWidget(backup_checkbox, 0, 2)

    return OptionsSection(
        group=group,
        only_buses_checkbox=only_buses_checkbox,
        recursive_checkbox=recursive_checkbox,
        backup_checkbox=backup_checkbox,
    )


def build_action_section(
    on_apply_bulk: Callable[[], None],
    on_save: Callable[[], None],
) -> ActionSection:
    group = QGroupBox("FOV Actions")
    grid = QGridLayout(group)

    bulk_fov_input = QLineEdit()
    bulk_fov_input.setPlaceholderText("Bulk value for selected camera positions")
    bulk_fov_input.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    validator = QDoubleValidator(bulk_fov_input)
    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    bulk_fov_input.setValidator(validator)
    bulk_apply_button = QPushButton("Apply Bulk FOV to Selected")
    bulk_apply_button.clicked.connect(on_apply_bulk)
    save_button = QPushButton("Save 0 changes")
    save_button.setEnabled(False)
    save_button.clicked.connect(on_save)

    grid.addWidget(QLabel("Bulk FOV:"), 0, 0)
    grid.addWidget(bulk_fov_input, 0, 1)
    grid.addWidget(bulk_apply_button, 0, 2)
    grid.addWidget(save_button, 0, 3)

    return ActionSection(
        group=group,
        bulk_fov_input=bulk_fov_input,
        bulk_apply_button=bulk_apply_button,
        save_button=save_button,
    )

