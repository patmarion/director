"""Tests for gridSource module."""

import vtk

from director.gridSource import makeGridPolyData


def test_make_grid_polydata():
    """Test creating grid PolyData."""
    grid = makeGridPolyData(
        gridHalfWidth=10.0, majorTickSize=2.0, minorTickSize=0.5, majorGridRings=False, minorGridRings=False
    )

    assert grid is not None
    assert isinstance(grid, vtk.vtkPolyData)
    assert grid.GetNumberOfPoints() > 0


def test_make_grid_with_rings():
    """Test creating grid with rings enabled."""
    grid = makeGridPolyData(
        gridHalfWidth=10.0, majorTickSize=2.0, minorTickSize=1.0, majorGridRings=True, minorGridRings=False
    )

    assert grid is not None
    assert isinstance(grid, vtk.vtkPolyData)


def test_make_grid_different_sizes():
    """Test creating grid with different major/minor tick sizes."""
    grid = makeGridPolyData(
        gridHalfWidth=10.0, majorTickSize=5.0, minorTickSize=1.0, majorGridRings=False, minorGridRings=False
    )

    assert grid is not None
    assert grid.GetNumberOfPoints() > 0


def test_make_grid_custom_origin():
    """Test creating grid with custom origin."""
    origin = (5, 5, 0)
    grid = makeGridPolyData(gridHalfWidth=10.0, majorTickSize=2.0, origin=origin)

    assert grid is not None
    # Grid should have points around the origin
    assert grid.GetNumberOfPoints() > 0
