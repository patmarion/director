"""Tests for applogic module."""

import sys
import pytest
import numpy as np
from qtpy.QtWidgets import QApplication
from director.applogic import resetCamera, setBackgroundColor
from director.vtk_widget import VTKWidget


def test_reset_camera(qapp):
    """Test resetCamera function."""
    widget = VTKWidget()
    widget.show()

    # Should not raise
    resetCamera(view=widget)

    widget.close()
    print("test_reset_camera returned")


def test_set_background_color(qapp):
    """Test setBackgroundColor function."""
    widget = VTKWidget()
    widget.show()

    # Should not raise
    setBackgroundColor([0.5, 0.5, 0.5], view=widget)
    widget.close()
    print("test_set_background_color returned")
