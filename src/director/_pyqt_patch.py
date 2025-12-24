from qtpy.QtWidgets import QTreeWidgetItem

# PyQt6 does not make QTreeWidgetItem hashable by default (unlike PySide6),
# so we patch it to allow using items as dict keys.
if not hasattr(QTreeWidgetItem, "__hash__") or QTreeWidgetItem.__hash__ is None:
    QTreeWidgetItem.__hash__ = lambda self: id(self)
