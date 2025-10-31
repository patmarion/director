"""Tests for hello_world module."""

import sys
import pytest
from qtpy.QtWidgets import QApplication
from director.hello_world import VTKWidget, MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        yield app
        app.quit()
    else:
        yield QApplication.instance()


def test_vtk_widget_construction(qapp):
    """Test that VTKWidget can be constructed."""
    widget = VTKWidget()
    assert widget is not None
    assert widget.renderer is not None
    assert widget.render_window is not None
    assert widget.vtk_widget is not None


def test_vtk_widget_show(qapp):
    """Test that VTKWidget can be shown and then closed."""
    widget = VTKWidget()
    widget.show()
    
    # Process events to allow the widget to render
    qapp.processEvents()
    
    # Verify widget is visible
    assert widget.isVisible()
    
    # Close the widget
    widget.close()


def test_main_window_construction(qapp):
    """Test that MainWindow can be constructed with VTKWidget."""
    window = MainWindow()
    assert window is not None
    assert window.vtk_widget is not None
    assert isinstance(window.vtk_widget, VTKWidget)


def test_main_window_show_and_exit(qapp):
    """Test that MainWindow can be shown and then closed."""
    window = MainWindow()
    window.show()
    
    # Process events to allow the window to render
    qapp.processEvents()
    
    # Verify window is visible
    assert window.isVisible()
    
    # Close the window
    window.close()
    
    # Process events to complete the close
    qapp.processEvents()

