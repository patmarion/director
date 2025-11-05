"""Qt utility functions."""

import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets


def addWidgetsToDict(widgets, d):
    """Recursively add widgets to a dictionary by their objectName."""
    for widget in widgets:
        if hasattr(widget, 'objectName') and widget.objectName():
            d[str(widget.objectName())] = widget
        addWidgetsToDict(widget.children(), d)


class WidgetDict(object):
    """Dictionary-like access to widgets by objectName."""
    
    def __init__(self, widgets):
        addWidgetsToDict(widgets, self.__dict__)


def clearLayout(widget):
    """Clear all child widgets from a layout."""
    children = widget.findChildren(QtWidgets.QWidget)
    for child in children:
        child.deleteLater()


def loadUi(filename):
    """Load a .ui file using QUiLoader.
    
    Note: This requires QtUiTools which may not be available in all Qt bindings.
    """
    try:
        from qtpy import uic
        widget = uic.loadUi(filename)
        ui = WidgetDict(widget.children())
        return widget, ui
    except ImportError:
        try:
            from qtpy.QtUiTools import QUiLoader
            loader = QUiLoader()
            uifile = QtCore.QFile(filename)
            if not uifile.open(QtCore.QFile.ReadOnly):
                raise IOError(f"Could not open UI file: {filename}")
            widget = loader.load(uifile)
            ui = WidgetDict(widget.children())
            return widget, ui
        except ImportError:
            raise ImportError("QtUiTools not available. Cannot load UI files.")


class BlockSignals(object):
    """Context manager to block signals on QObjects.
    
    Example:
        with BlockSignals(self.widget):
            self.widget.setValue(42)  # No signals emitted
    """
    
    def __init__(self, *args):
        """Initialize with one or more QObjects to block signals on.
        
        Args:
            *args: QObject instances to block signals for
        """
        self.objects = args
    
    def enable(self, value):
        """Enable or disable signal blocking for all objects.
        
        Args:
            value: True to block signals, False to unblock
        """
        for obj in self.objects:
            if hasattr(obj, 'blockSignals'):
                obj.blockSignals(value)
    
    def __enter__(self):
        """Enter context manager - block signals."""
        self.enable(True)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager - unblock signals."""
        self.enable(False)

