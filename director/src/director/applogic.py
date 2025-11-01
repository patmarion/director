"""Application logic utilities (simplified from original Director)."""

from qtpy.QtWidgets import QMessageBox, QApplication
from qtpy.QtCore import Qt
import director.vtkAll as vtk

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
    if hasattr(view, 'resetCamera'):
        view.resetCamera()
    else:
        view.renderer().ResetCamera()
        view.renderer().ResetCameraClippingRange()
    
    # Render
    if hasattr(view, 'render'):
        view.render()
    elif hasattr(view, 'vtk_widget'):
        view.vtk_widget.render()


def setBackgroundColor(color, color2=None, view=None):
    """Set background color for a view."""
    if view is None:
        return
    
    if color2 is None:
        color2 = color
    
    # Get renderer from view (handle both VTKWidget and other views)
    renderer = None
    if hasattr(view, 'backgroundRenderer'):
        renderer = view.backgroundRenderer()
    elif hasattr(view, 'renderer'):
        renderer = view.renderer()
    elif hasattr(view, 'vtk_widget') and hasattr(view.vtk_widget, 'renderer'):
        renderer = view.vtk_widget.renderer()
    
    if renderer:
        renderer.SetBackground(color)
        renderer.SetBackground2(color2)


def showErrorMessage(message, title='Error', parent=None):
    """Show an error message dialog."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    QMessageBox.warning(parent, title, message)


def showInfoMessage(message, title='Info', parent=None):
    """Show an info message dialog."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    QMessageBox.information(parent, title, message)


def boolPrompt(title, message, parent=None):
    """Show a yes/no prompt and return True if Yes."""
    if parent is None:
        parent = QApplication.instance().activeWindow()
    result = QMessageBox.question(parent, title, message, 
                                   QMessageBox.Yes | QMessageBox.No)
    return result == QMessageBox.Yes


def getCameraTerrainModeEnabled(view):
    """Check if camera terrain mode is enabled."""
    if view is None:
        return False
    interactor = view.renderWindow().GetInteractor()
    if interactor is None:
        return False
    style = interactor.GetInteractorStyle()
    # Check for both vtkInteractorStyleTerrain (standard) and vtkInteractorStyleTerrain2 (custom)
    return isinstance(style, (vtk.vtkInteractorStyleTerrain, 
                             getattr(vtk, 'vtkInteractorStyleTerrain2', type(None))))


def setCameraTerrainModeEnabled(view, enabled):
    """Enable or disable camera terrain mode."""
    if view is None:
        return
    
    if getCameraTerrainModeEnabled(view) == enabled:
        return
    
    renderWindow = view.renderWindow()
    interactor = renderWindow.GetInteractor()
    
    if enabled:
        # Use standard VTK terrain interactor (vtkInteractorStyleTerrain2 is a custom C++ class)
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTerrain())
        camera = view.camera()
        if camera:
            camera.SetViewUp(0, 0, 1)
    else:
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
    
    view.render()


def toggleCameraTerrainMode(view=None):
    """Toggle camera terrain mode."""
    if view is None:
        return
    setCameraTerrainModeEnabled(view, not getCameraTerrainModeEnabled(view))

