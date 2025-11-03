"""Tests for hello_world module."""

import sys
import pytest
from qtpy.QtWidgets import QApplication
from director.vtk_widget import VTKWidget
from director import mainwindowapp


def test_vtk_widget_construction(qapp):
    """Test that VTKWidget can be constructed."""
    widget = VTKWidget()
    assert widget is not None
    assert widget.renderer() is not None
    assert widget.renderWindow() is not None
    assert widget.vtkWidget() is not None


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


def test_mainwindowapp_construction(qapp):
    """Test that MainWindowApp can be constructed."""
    fields = mainwindowapp.construct()
    assert fields is not None
    assert fields.view is not None
    assert fields.mainWindow is not None
    assert isinstance(fields.view, VTKWidget)


def test_mainwindowapp_show_and_exit(qapp):
    """Test that MainWindowApp can be shown and then closed."""
    fields = mainwindowapp.construct()
    fields.mainWindow.show()
    
    # Process events to allow the window to render
    qapp.processEvents()
    
    # Verify window is visible
    assert fields.mainWindow.isVisible()
    
    # Close the window
    fields.mainWindow.close()
    
    # Process events to complete the close
    qapp.processEvents()

