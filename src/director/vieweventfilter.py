"""View event filter for handling mouse and keyboard events in VTK views."""

import vtk
from qtpy.QtCore import QEvent, QObject, QPoint, Qt
from qtpy.QtGui import QCursor

from director.vtk_widget import get_qt_mouse_event_position


class ViewEventFilter(QObject):
    """Event filter for VTK views using Qt event filtering."""

    START_RENDER_EVENT = "START_RENDER_EVENT"
    END_RENDER_EVENT = "END_RENDER_EVENT"
    LEFT_DOUBLE_CLICK_EVENT = "LEFT_DOUBLE_CLICK_EVENT"

    def __init__(self, view):
        super().__init__()
        self.view = view
        self._leftMouseStart = None
        self._rightMouseStart = None
        self._handlers = {}
        self._render_observers = []

        # Install event filter on the VTK widget
        vtk_widget = view.vtkWidget()
        if vtk_widget:
            vtk_widget.installEventFilter(self)

        render_window = getattr(view, "renderWindow", None)
        if callable(render_window):
            render_window = view.renderWindow()
            if render_window:
                self._render_observers.append(render_window.AddObserver(vtk.vtkCommand.StartEvent, self._onStartRender))
                self._render_observers.append(render_window.AddObserver(vtk.vtkCommand.EndEvent, self._onEndRender))

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
        """Get the mouse position in VTK display coordinates."""
        return self.view.logicalToDisplayCoordinates(get_qt_mouse_event_position(event))

    def getCursorDisplayPosition(self):
        """Get the cursor position in VTK display coordinates."""
        vtk_widget = self.view.vtkWidget()
        if not vtk_widget:
            return (0, 0)
        cursorPos = vtk_widget.mapFromGlobal(QCursor.pos())
        return self.view.logicalToDisplayCoordinates((cursorPos.x(), cursorPos.y()))

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

        if self._render_observers:
            render_window = getattr(self.view, "renderWindow", None)
            if callable(render_window):
                render_window = self.view.renderWindow()
                if render_window:
                    for observer in self._render_observers:
                        render_window.RemoveObserver(observer)
            self._render_observers = []

    def _onStartRender(self, obj, event):
        self.onStartRender()

    def _onEndRender(self, obj, event):
        self.onEndRender()

    def onStartRender(self):
        """Override in subclass for render start events."""
        return self.callHandler(self.START_RENDER_EVENT, self.view)

    def onEndRender(self):
        """Override in subclass for render end events."""
        return self.callHandler(self.END_RENDER_EVENT, self.view)
