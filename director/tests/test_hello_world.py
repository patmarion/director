"""Tests for hello_world module."""

from director.vtk_widget import VTKWidget
from director import mainwindowapp


def test_vtk_widget(qapp):
    """Test that VTKWidget can be shown and then closed."""
    widget = VTKWidget()
    widget.show()
    assert widget.isVisible()
    widget.close()


def test_mainwindowapp_construction(qapp):
    """Test that MainWindowApp can be constructed."""
    fields = mainwindowapp.construct()
    assert fields is not None
    assert fields.view is not None
    assert fields.mainWindow is not None
    assert isinstance(fields.view, VTKWidget)
