"""View event filter for handling mouse and keyboard events in VTK views."""

from qtpy.QtCore import QObject, QEvent, Qt, QPoint
from qtpy.QtGui import QCursor


class ViewEventFilter(QObject):
    """Event filter for VTK views using Qt event filtering."""

    LEFT_DOUBLE_CLICK_EVENT = "LEFT_DOUBLE_CLICK_EVENT"

    def __init__(self, view):
        super().__init__()
        self.view = view
        self._leftMouseStart = None
        self._rightMouseStart = None
        self._handlers = {}

        # Install event filter on the VTK widget
        vtk_widget = view.vtkWidget()
        if vtk_widget:
            vtk_widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Qt event filter implementation. Returns True to consume event, False to continue."""
        consumed = False

        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            consumed = self.onLeftDoubleClick(event) or consumed

        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._leftMouseStart = QPoint(event.pos())
            consumed = self.onLeftMousePress(event) or consumed

        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self._rightMouseStart = QPoint(event.pos())
            consumed = self.onRightMousePress(event) or consumed

        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.MiddleButton:
            consumed = self.onMiddleMousePress(event) or consumed

        elif event.type() == QEvent.MouseMove:
            if self._rightMouseStart is not None:
                delta = QPoint(event.pos()) - self._rightMouseStart
                if delta.manhattanLength() > 3:
                    self._rightMouseStart = None

            if self._leftMouseStart is not None:
                delta = QPoint(event.pos()) - self._leftMouseStart
                if delta.manhattanLength() > 3:
                    self._leftMouseStart = None

            if self._rightMouseStart is None and self._leftMouseStart is None:
                consumed = self.onMouseMove(event) or consumed

        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            consumed = self.onLeftMouseRelease(event) or consumed
            if self._leftMouseStart is not None:
                self._leftMouseStart = None
                consumed = self.onLeftClick(event) or consumed

        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
            consumed = self.onRightMouseRelease(event) or consumed
            if self._rightMouseStart is not None:
                self._rightMouseStart = None
                consumed = self.onRightClick(event) or consumed

        elif event.type() == QEvent.Wheel:
            consumed = self.onMouseWheel(event) or consumed

        elif event.type() == QEvent.KeyPress:
            if not event.isAutoRepeat():
                consumed = self.onKeyPress(event) or consumed
            consumed = self.onKeyPressRepeat(event) or consumed

        elif event.type() == QEvent.KeyRelease and not event.isAutoRepeat():
            consumed = self.onKeyRelease(event) or consumed

        # Return True to consume event (stop propagation), False to continue
        return consumed

    def addHandler(self, eventType, handler):
        """Add an event handler."""
        self._handlers.setdefault(eventType, []).append(handler)

    def callHandler(self, eventType, *args, **kwargs):
        """Call handlers for an event type."""
        for handler in self._handlers.get(eventType, []):
            if handler(*args, **kwargs):
                return True
        return False

    def getMousePositionInView(self, event):
        """Get mouse position in view coordinates."""
        mousePosition = event.pos()
        widget = self.view.vtkWidget()
        if widget:
            return mousePosition.x(), widget.height() - mousePosition.y()
        return mousePosition.x(), mousePosition.y()

    def getCursorDisplayPosition(self):
        """Get cursor display position."""
        vtk_widget = self.view.vtkWidget()
        if not vtk_widget:
            return (0, 0)
        cursorPos = vtk_widget.mapFromGlobal(QCursor.pos())
        return cursorPos.x(), vtk_widget.height() - cursorPos.y()

    def onMouseWheel(self, event):
        """Override in subclass for mouse wheel events. Return True to consume event."""
        return False

    def onMouseMove(self, event):
        """Override in subclass for mouse move events. Return True to consume event."""
        return False

    def onLeftMousePress(self, event):
        """Override in subclass for left mouse press events. Return True to consume event."""
        return False

    def onRightMousePress(self, event):
        """Override in subclass for right mouse press events. Return True to consume event."""
        return False

    def onMiddleMousePress(self, event):
        """Override in subclass for middle mouse press events. Return True to consume event."""
        return False

    def onLeftMouseRelease(self, event):
        """Override in subclass for left mouse release events. Return True to consume event."""
        return False

    def onRightMouseRelease(self, event):
        """Override in subclass for right mouse release events. Return True to consume event."""
        return False

    def onLeftDoubleClick(self, event):
        """Override in subclass for left double click events. Return True to consume event."""
        return False

    def onLeftClick(self, event):
        """Override in subclass for left click events. Return True to consume event."""
        return False

    def onRightClick(self, event):
        """Override in subclass for right click events. Return True to consume event."""
        return False

    def onKeyPress(self, event):
        """Override in subclass for key press events. Return True to consume event."""
        return False

    def onKeyPressRepeat(self, event):
        """Override in subclass for repeated key press events. Return True to consume event."""
        return False

    def onKeyRelease(self, event):
        """Override in subclass for key release events. Return True to consume event."""
        return False

    def removeEventFilter(self):
        """Remove the event filter."""
        vtk_widget = self.view.vtkWidget()
        if vtk_widget:
            vtk_widget.removeEventFilter(self)
