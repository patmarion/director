"""Qt utility functions."""

from qtpy import QtCore, QtGui, QtWidgets
import numpy as np

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


def pixmapToNumpy(pixmap):
    """
    Converts a QPixmap object into a numpy ndarray image (h, w, 3 uint8).
    """
    # 1. Convert QPixmap to QImage (preferred format for pixel access)
    # Use QImage.Format_RGB32 for a standard, easy-to-convert format.
    image = pixmap.toImage()

    # Ensure the image is in the correct format for direct buffer access
    if image.format() != QtGui.QImage.Format.Format_RGB32:
        image = image.convertToFormat(QtGui.QImage.Format.Format_RGB32)

    # 2. Access the raw pixel data using the QImage buffer
    # The data is typically in BGRA order in memory for RGB32 format on most platforms
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    arr = np.array(ptr).reshape(image.height(), image.width(), 4) # H, W, BGRA

    # 3. Convert from BGRA (or RGBA depending on system) to RGB and drop the alpha channel
    # The order depends on the specific system's byte order (little-endian vs big-endian)
    # A common format is BGRA. We can use slicing to reorder and drop A.

    # Reorder channels from BGR(A) to RGB
    # Note: If your array is already RGB(A), you only need arr[:, :, :3]
    # For common BGRA format:
    rgb_arr = arr[:, :, [2, 1, 0]]

    # Ensure the data type is uint8
    return rgb_arr.astype(np.uint8)


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

