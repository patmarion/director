"""Application logic utilities (simplified from original Director)."""

from qtpy.QtWidgets import QApplication, QMessageBox

# Global variable to store the current render view
_defaultRenderView = None


def setCurrentRenderView(view):
    """Set the default render view."""
    global _defaultRenderView
    _defaultRenderView = view


def getCurrentRenderView():
    """Get the current render view."""
    return _defaultRenderView


def resetCamera(viewDirection=None, view=None):
    """Reset camera for a view."""
    if view is None:
        return

    camera = view.camera()
    if camera is None:
        return

    if viewDirection is not None:
        camera.SetPosition([0, 0, 0])
        camera.SetFocalPoint(viewDirection)
        camera.SetViewUp([0, 0, 1])

    # Reset camera (works with both VTKWidget and other views)
    if hasattr(view, "resetCamera"):
        view.resetCamera()
    else:
        view.renderer().ResetCamera()
        view.renderer().ResetCameraClippingRange()

    # Render
    if hasattr(view, "render"):
        view.render()
    elif hasattr(view, "vtk_widget"):
        view.vtk_widget.render()


def setBackgroundColor(color, color2=None, view=None):
    """Set background color for a view."""
    if view is None:
        return

    if color2 is None:
        color2 = color

    # Get renderer from view (handle both VTKWidget and other views)
    renderer = None
    if hasattr(view, "backgroundRenderer"):
        renderer = view.backgroundRenderer()
    elif hasattr(view, "renderer"):
        renderer = view.renderer()
    elif hasattr(view, "vtk_widget") and hasattr(view.vtk_widget, "renderer"):
        renderer = view.vtk_widget.renderer()

    if renderer:
        renderer.SetBackground(color)
        renderer.SetBackground2(color2)


def showErrorMessage(message, title="Error", parent=None):
    """Show an error message dialog."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    QMessageBox.warning(parent, title, message)


def showInfoMessage(message, title="Info", parent=None):
    """Show an info message dialog."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    QMessageBox.information(parent, title, message)


def boolPrompt(title, message, parent=None):
    """Show a yes/no prompt and return True if Yes."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    result = QMessageBox.question(parent, title, message, QMessageBox.Yes | QMessageBox.No)
    return result == QMessageBox.Yes


def addShortcut(widget, keySequence, func):
    """Add a keyboard shortcut to a widget."""
    from qtpy.QtGui import QKeySequence
    from qtpy.QtWidgets import QShortcut

    shortcut = QShortcut(QKeySequence(keySequence), widget)
    shortcut.activated.connect(func)
    return shortcut


class ActionToggleHelper:
    """Helper class for managing toggle actions with getter/setter functions."""

    def __init__(self, action, getValue, setValue):
        """
        Initialize toggle helper.

        Args:
            action: QAction to toggle
            getValue: Function that returns current state (bool)
            setValue: Function that sets state (takes bool)
        """
        self.action = action
        self.getValue = getValue
        self.setValue = setValue

        action.setCheckable(True)
        action.setChecked(self.getValue())
        action.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        """Handle action trigger - toggle the state."""
        newState = not self.getValue()
        self.setValue(newState)
        self.action.setChecked(newState)


def MenuActionToggleHelper(menuName, actionName, getValue, setValue):
    """
    Add a toggle action to a menu.

    Args:
        menuName: Name of the menu (e.g., 'Tools')
        actionName: Name of the action
        getValue: Function that returns current state (bool)
        setValue: Function that sets state (takes bool)

    Note: This is a simplified version. The menu must be accessible via getMainWindow().
    """
    # This requires access to the main window's menu
    # For now, this is a stub that would need the main window instance
    # In practice, this should be called from MainWindowApp context
    pass  # TODO: Implement if needed
