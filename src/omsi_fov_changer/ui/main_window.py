from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QMessageBox, QTextEdit, QTreeView, QVBoxLayout, QWidget, QLabel, QFileDialog

from omsi_fov_changer.domain.models import BusFileInfo
from omsi_fov_changer.services.fov_service import FovService, discover_files
from omsi_fov_changer.ui.camera_tree_controller import CameraTreeController
from omsi_fov_changer.ui.main_window_sections import (
    build_action_section,
    build_options_section,
    build_source_section,
)


class MainWindow(QMainWindow):
    """Main desktop window for the OMSI FOV changer."""

    def __init__(self, service: FovService) -> None:
        super().__init__()
        self.service = service
        self.selected_files: list[Path] = []

        self.setWindowTitle("OMSI 2 Bus FOV Changer")
        self.resize(1120, 760)
        self._build_ui()
        self._refresh_save_button_label()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        self.source_section = build_source_section(self.choose_source)
        self.options_section = build_options_section()
        self.action_section = build_action_section(self.apply_bulk_fov, self.save_changes)

        self.folder_radio = self.source_section.folder_radio
        self.file_radio = self.source_section.file_radio
        self.source_input = self.source_section.source_input

        self.only_buses_checkbox = self.options_section.only_buses_checkbox
        self.recursive_checkbox = self.options_section.recursive_checkbox
        self.backup_checkbox = self.options_section.backup_checkbox

        self.bulk_fov_input = self.action_section.bulk_fov_input
        self.bulk_apply_button = self.action_section.bulk_apply_button
        self.save_button = self.action_section.save_button

        layout.addWidget(self.source_section.group)
        layout.addWidget(self.options_section.group)
        layout.addWidget(self.action_section.group)
        layout.addWidget(self._build_camera_group())

        self.summary_label = QLabel("No folder or file selected")
        layout.addWidget(self.summary_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setCentralWidget(central)

    def _build_camera_group(self) -> QWidget:
        group = QWidget(self)
        layout = QVBoxLayout(group)

        self.camera_tree = QTreeView()
        self.tree_controller = CameraTreeController(
            self.camera_tree,
            on_pending_changes_changed=self._refresh_save_button_label,
        )
        layout.addWidget(self.camera_tree)
        return group

    def choose_source(self) -> None:
        if self.folder_radio.isChecked():
            folder = self._browse_for_folder()
            if folder:
                if not self._confirm_discard_pending_changes(folder):
                    return
                self._set_source(folder, is_file=False)
                self.scan_files()
        else:
            file_path = self._browse_for_file()
            if file_path:
                if not self._confirm_discard_pending_changes(file_path):
                    return
                self._set_source(file_path, is_file=True)
                self.scan_files()

    def scan_files(self) -> None:
        source = self._read_source()
        if source is None:
            return

        self.selected_files = self._discover_files(source)
        file_infos = self._parse_camera_infos(self.selected_files)

        total_positions = sum(len(info.cameras) for info in file_infos)
        self.summary_label.setText(
            f"Found {len(self.selected_files)} file(s) with {total_positions} driver camera position(s)"
        )
        self._log(
            f"Found {len(self.selected_files)} files with {total_positions} driver camera positions"
        )
        self.tree_controller.load(file_infos)
        self._fit_tree_columns()

    def apply_bulk_fov(self) -> None:
        try:
            bulk_value = self._read_bulk_fov()
        except ValueError:
            QMessageBox.warning(self, "Invalid FOV", "Bulk FOV must be a valid number.")
            return

        targets = self.tree_controller.collect_bulk_targets()
        if not targets:
            QMessageBox.information(
                self,
                "No checked positions",
                "Check one or more camera positions before applying the bulk FOV.",
            )
            return

        self.tree_controller.apply_bulk_value(targets, bulk_value)
        self._log(f"Applied bulk FOV {bulk_value} to {len(targets)} selected camera position(s).")
        self._refresh_save_button_label()

    def save_changes(self) -> None:
        source = self._read_source()
        if source is None:
            return

        self.tree_controller.sync_persistent_editors_to_model()

        if not self.selected_files:
            self.scan_files()

        if not self.selected_files:
            QMessageBox.information(self, "No files found", "No matching files were found.")
            return

        updates_by_file = self.tree_controller.collect_updates_by_file()
        pending = sum(len(items) for items in updates_by_file.values())
        self.save_button.setText(f"Save {pending} changes")
        if not updates_by_file:
            QMessageBox.information(self, "No changes", "No edited FOV values were found to save.")
            return

        batch = self.service.replace_in_files(
            files=self.selected_files,
            backup=self.backup_checkbox.isChecked(),
            updates_by_file=updates_by_file,
        )
        self._render_batch_result(batch)

        # Reload from disk so the model reflects what was just saved.
        self.scan_files()
        self._refresh_save_button_label()

    def _confirm_discard_pending_changes(self, next_source: str) -> bool:
        self.tree_controller.sync_persistent_editors_to_model()
        pending = self.tree_controller.count_pending_changes()
        if pending == 0:
            return True

        current_source = self.source_input.text().strip()
        if current_source == next_source:
            message = (
                f"You have {pending} unsaved changes.\n\n"
                "You are reloading the same source. Continue and discard pending edits?"
            )
        else:
            message = (
                f"You have {pending} unsaved changes.\n\n"
                "Are you sure you want to continue? Unsaved edits will be lost."
            )

        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _refresh_save_button_label(self) -> None:
        pending = self.tree_controller.count_pending_changes()
        self.save_button.setText(f"Save {pending} changes")
        self.save_button.setEnabled(pending > 0)

    def _render_batch_result(self, batch) -> None:
        self._log(
            f"Processed {batch.processed_file_count} files, changed {batch.changed_file_count} files, "
            f"updated {batch.total_changes} value(s)."
        )

        for file_result in batch.file_results:
            for warning in file_result.warnings:
                self._log(f"WARNING: {warning}")

            for change in file_result.changes:
                self._log(
                    f"{change.file_path.name}:{change.line_number} {change.camera_tag} "
                    f"{change.old_value} -> {change.new_value}"
                )

        QMessageBox.information(
            self,
            "Finished",
            "Completed FOV update. Check the log for detailed output.",
        )

    def _browse_for_folder(self) -> str:
        return QFileDialog.getExistingDirectory(self, "Select folder")

    def _browse_for_file(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select .bus file", "", "Bus Files (*.bus);;All Files (*)"
        )
        return file_path

    def _set_source(self, source_text: str, *, is_file: bool) -> None:
        if is_file:
            self.file_radio.setChecked(True)
            self.folder_radio.setChecked(False)
            self.summary_label.setText(f"Selected file: {source_text}")
        else:
            self.folder_radio.setChecked(True)
            self.file_radio.setChecked(False)
            self.summary_label.setText(f"Selected folder: {source_text}")
        self.source_input.setText(source_text)

    def _discover_files(self, source: Path) -> list[Path]:
        if source.is_file():
            return [source]
        return discover_files(
            folder=source,
            only_buses=self.only_buses_checkbox.isChecked(),
            recursive=self.recursive_checkbox.isChecked(),
        )

    def _parse_camera_infos(self, files: list[Path]) -> list[BusFileInfo]:
        file_infos = []
        for file_path in files:
            info = self.service.parse_cameras_from_file(file_path)
            if info is not None:
                file_infos.append(info)
        return file_infos

    def _read_source(self) -> Path | None:
        source_text = self.source_input.text().strip()
        if not source_text:
            QMessageBox.warning(self, "Missing source", "Please select a folder or file first.")
            return None

        source = Path(source_text)
        if not source.exists():
            QMessageBox.warning(self, "Invalid source", "The selected path does not exist.")
            return None

        if source.is_file():
            self.file_radio.setChecked(True)
            self.folder_radio.setChecked(False)
        elif source.is_dir():
            self.folder_radio.setChecked(True)
            self.file_radio.setChecked(False)
        else:
            QMessageBox.warning(self, "Invalid source", "The selected path is neither a file nor a folder.")
            return None

        return source

    def _read_bulk_fov(self) -> str:
        bulk_text = self.bulk_fov_input.text().strip()
        if not bulk_text:
            raise ValueError("Bulk FOV field is empty.")
        float(bulk_text)  # raises ValueError for non-numeric input
        return bulk_text

    def _fit_tree_columns(self) -> None:
        self.tree_controller.fit_columns()

    def _log(self, message: str) -> None:
        self.log_output.append(message)

