from qtpy import QtWidgets, QtCore, QtGui
import json
from typing import Any


class DictTableWidget(QtWidgets.QWidget):
    """Two-column widget for presenting dictionary entries."""

    def __init__(self, data: dict[str, Any] | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._table = QtWidgets.QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Key", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._table.setAlternatingRowColors(True)

        palette = self._table.palette()
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#ffffff"))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#f5f5f5"))
        self._table.setPalette(palette)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._table)

        self.set_data(data or {})

    def set_data(self, data: dict[str, Any]) -> None:
        """Populate the table with dictionary key/value pairs."""
        self._table.setRowCount(len(data))
        for row, (key, value) in enumerate(data.items()):
            key_item = QtWidgets.QTableWidgetItem(str(key))
            key_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            font = key_item.font()
            font.setBold(True)
            key_item.setFont(font)
            self._table.setItem(row, 0, key_item)

            value_item = QtWidgets.QTableWidgetItem(self._stringify(value))
            value_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            value_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self._table.setItem(row, 1, value_item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, (list, tuple)):
            return "\n".join(str(v) for v in value)
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        return str(value)
