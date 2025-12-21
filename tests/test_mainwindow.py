"""Tests for mainwindowapp module."""

from director import mainwindowapp
from director.vtk_widget import VTKWidget


def test_mainwindowapp(qapp):
    """Test that MainWindowApp can be constructed."""
    fields = mainwindowapp.construct()
    assert fields is not None
    assert fields.view is not None
    assert fields.mainWindow is not None
    assert isinstance(fields.view, VTKWidget)
