"""Tests for applogic module."""

import sys
import pytest
import numpy as np
from qtpy.QtWidgets import QApplication
from director.applogic import (
    resetCamera, setBackgroundColor, showErrorMessage,
    showInfoMessage, boolPrompt, getCameraTerrainModeEnabled,
    setCameraTerrainModeEnabled
)
from director.vtk_widget import VTKWidget


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        yield app
        app.quit()
    else:
        yield QApplication.instance()


def test_reset_camera(qapp):
    """Test resetCamera function."""
    widget = VTKWidget()
    widget.show()
    qapp.processEvents()
    
    # Should not raise
    resetCamera(view=widget)
    
    widget.close()


def test_set_background_color(qapp):
    """Test setBackgroundColor function."""
    widget = VTKWidget()
    widget.show()
    qapp.processEvents()
    
    # Should not raise
    setBackgroundColor([0.5, 0.5, 0.5], view=widget)
    
    widget.close()


def test_camera_terrain_mode(qapp):
    """Test camera terrain mode functions."""
    widget = VTKWidget()
    widget.show()
    qapp.processEvents()
    
    # Initially should be False
    assert getCameraTerrainModeEnabled(widget) == False
    
    # Enable terrain mode
    setCameraTerrainModeEnabled(widget, True)
    assert getCameraTerrainModeEnabled(widget) == True
    
    # Disable terrain mode
    setCameraTerrainModeEnabled(widget, False)
    assert getCameraTerrainModeEnabled(widget) == False
    
    widget.close()

