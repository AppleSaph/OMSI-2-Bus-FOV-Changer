from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate


class FovEditorDelegate(QStyledItemDelegate):
    """Delegate that provides a visible numeric text editor for the New FOV column."""

    def createEditor(self, parent, option, index):  # noqa: N802
        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        validator = QDoubleValidator(editor)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QLineEdit, index):  # noqa: N802
        value = index.data(Qt.ItemDataRole.EditRole)
        editor.setText("" if value is None else str(value))
        self._clear_selection(editor)
        # Qt can still re-select text after delegate setup; clear again on next tick.
        QTimer.singleShot(0, lambda: self._clear_selection(editor))

    def setModelData(self, editor: QLineEdit, model, index):  # noqa: N802
        model.setData(index, editor.text().strip(), Qt.ItemDataRole.EditRole)

    @staticmethod
    def _clear_selection(editor: QLineEdit) -> None:
        editor.setSelection(0, 0)
        editor.deselect()
        editor.setCursorPosition(len(editor.text()))

