from PySide6.QtGui import QColor, QFont, QStandardItem
from PySide6.QtCore import Qt


def set_item_modified_style(item: 'QStandardItem', modified: bool) -> None:
    if modified:
        item.setData(QColor("#fff3cd"), Qt.ItemDataRole.BackgroundRole)
        item.setData(QColor("#7a4b00"), Qt.ItemDataRole.ForegroundRole)
        font: QFont = item.font()
        font.setBold(True)
        item.setData(font, Qt.ItemDataRole.FontRole)
    else:
        item.setData(None, Qt.ItemDataRole.BackgroundRole)
        item.setData(None, Qt.ItemDataRole.ForegroundRole)
        font: QFont = item.font()
        font.setBold(False)
        item.setData(font, Qt.ItemDataRole.FontRole)
