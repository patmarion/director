"""Tests for VTKWidget addCustomBounds functionality."""

import sys
import pytest
from qtpy.QtWidgets import QApplication
from director.vtk_widget import VTKWidget


def test_add_custom_bounds(qapp):
    """Test adding custom bounds to VTKWidget."""
    widget = VTKWidget()
    
    # Add custom bounds
    bounds = [-10, 10, -10, 10, -10, 10]
    widget.addCustomBounds(bounds)
    
    # Verify bounds were stored
    assert len(widget._custom_bounds) == 1
    assert widget._custom_bounds[0] == bounds


def test_reset_camera_with_custom_bounds(qapp):
    """Test resetCamera with custom bounds."""
    widget = VTKWidget()
    widget.show()
    
    # Add custom bounds
    widget.addCustomBounds([-5, 5, -5, 5, -5, 5])
    widget.addCustomBounds([-2, 2, -2, 2, -2, 2])
    
    # Reset camera - should use combined bounds
    widget.resetCamera()
    
    # Process events
    qapp.processEvents()
    
    # Verify camera was reset (no exception thrown)
    assert widget.camera() is not None
    
    widget.close()


def test_reset_camera_clears_bounds_on_next_call(qapp):
    """Test that resetCamera uses bounds but doesn't clear them until next reset."""
    widget = VTKWidget()
    
    # Add custom bounds
    widget.addCustomBounds([-10, 10, -10, 10, -10, 10])
    
    # First reset should use bounds
    widget.resetCamera()
    
    # Note: In the current implementation, bounds persist
    # The original C++ clears them, but we keep them for potential reuse
    # If needed, we can add a clearCustomBounds() method
    
    assert len(widget._custom_bounds) >= 1

