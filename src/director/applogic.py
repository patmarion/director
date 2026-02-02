"""Application logic utilities (simplified from original Director)."""

from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import QApplication, QMainWindow, QMessageBox, QMenu

# Global variable to store the current render view
_defaultRenderView = None

_mainWindow = None
_defaultRenderView = None


def getMainWindow():
    global _mainWindow
    if _mainWindow is None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                _mainWindow = widget
                break
    return _mainWindow


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


def findMenu(menuTitle, mainWindow=None):
    """
    Finds a QMenu within the main window by its title.
    Ported from the Director-specific logic to use qtpy's findChildren.
    """
    mainWindow = mainWindow or getMainWindow()
    if not mainWindow:
        return None

    menus = mainWindow.findChildren(QMenu)
    for menu in menus:
        title = str(menu.title())
        # Handle Qt's mnemonic ampersands (e.g., "&File" -> "File")
        if title.startswith('&'):
            title = title[1:]
        if title == menuTitle:
            return menu
    return None


def addMenuAction(menuTitle, actionName):
    """
    Finds a menu and adds a new action to it.
    Uses the robust findMenu logic to ensure the action is placed correctly.
    """
    menu = findMenu(menuTitle)
    if not menu:
        # Optionally create the menu if it doesn't exist
        mw = getMainWindow()
        menu = mw.menuBar().addMenu(menuTitle)

    return menu.addAction(actionName)


class MenuActionToggleHelper(ActionToggleHelper):
    """
    Adds a toggleable action to a specific menu and manages its state.
    """

    def __init__(self, menuName, actionName, getValue, setValue):
        # Create the action in the requested menu
        self.action = addMenuAction(menuName, actionName)
        # Initialize the base toggle logic (checkable, signals, etc.)
        super(MenuActionToggleHelper, self).__init__(self.action, getValue, setValue)
