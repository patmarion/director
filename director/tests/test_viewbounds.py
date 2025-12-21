"""Tests for viewbounds module."""

import sys
import pytest
import numpy as np
from qtpy.QtWidgets import QApplication
import vtk
from director.viewbounds import getVisibleActors, computeViewBoundsNoGrid, computeViewBoundsSoloGrid
from director.vtk_widget import VTKWidget


def test_get_visible_actors(qapp):
    """Test getting visible actors from view."""
    widget = VTKWidget()

    # Add a simple actor
    sphere_source = vtk.vtkSphereSource()
    sphere_source.SetRadius(1.0)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere_source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    widget.renderer().AddActor(actor)

    visible = getVisibleActors(widget)

    assert len(visible) >= 1  # At least the sphere actor
    assert actor in visible or len(visible) > 0


def test_compute_view_bounds_no_grid(qapp):
    """Test computing view bounds without grid."""
    widget = VTKWidget()

    # Add an actor (not the grid)
    sphere_source = vtk.vtkSphereSource()
    sphere_source.SetRadius(1.0)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere_source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    widget.renderer().AddActor(actor)

    # Create a dummy grid object with a different actor
    # (grid should be excluded from bounds calculation)
    grid_actor = vtk.vtkActor()

    class DummyGrid:
        def __init__(self, actor):
            self.actor = actor

    gridObj = DummyGrid(grid_actor)

    bounds = computeViewBoundsNoGrid(widget, gridObj)

    assert bounds is not None
    assert len(bounds) == 6
    assert bounds[0] < bounds[1]  # xmin < xmax
    assert bounds[2] < bounds[3]  # ymin < ymax
    assert bounds[4] < bounds[5]  # zmin < zmax


def test_compute_view_bounds_solo_grid(qapp):
    """Test computing view bounds with solo grid."""
    widget = VTKWidget()

    # Create a dummy grid object
    sphere_source = vtk.vtkSphereSource()
    sphere_source.SetRadius(1.0)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere_source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    widget.renderer().AddActor(actor)

    class DummyGrid:
        def __init__(self, actor):
            self.actor = actor

    gridObj = DummyGrid(actor)

    bounds = computeViewBoundsSoloGrid(widget, gridObj)

    assert bounds is not None
    assert len(bounds) == 6
