"""Tests for shallowCopy module."""

import vtk
import pytest
from director.shallowCopy import shallowCopy, deepCopy


def test_shallow_copy_polydata():
    """Test shallow copying a PolyData object."""
    # Create a simple sphere
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    sphere.Update()

    original = sphere.GetOutput()
    shallow = shallowCopy(original)

    assert shallow is not None
    assert shallow.GetNumberOfPoints() == original.GetNumberOfPoints()
    assert shallow.GetNumberOfCells() == original.GetNumberOfCells()

    # Shallow copy should share the same data arrays
    assert shallow.GetPoints() == original.GetPoints()


def test_deep_copy_polydata():
    """Test deep copying a PolyData object."""
    # Create a simple sphere
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    sphere.Update()

    original = sphere.GetOutput()
    deep = deepCopy(original)

    assert deep is not None
    assert deep.GetNumberOfPoints() == original.GetNumberOfPoints()
    assert deep.GetNumberOfCells() == original.GetNumberOfCells()

    # Deep copy should have different data arrays
    assert deep.GetPoints() != original.GetPoints()


def test_shallow_copy_image_data():
    """Test shallow copying an ImageData object."""
    image = vtk.vtkImageData()
    image.SetDimensions(10, 10, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

    shallow = shallowCopy(image)

    assert shallow is not None
    assert shallow.GetDimensions() == image.GetDimensions()


def test_deep_copy_image_data():
    """Test deep copying an ImageData object."""
    image = vtk.vtkImageData()
    image.SetDimensions(10, 10, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

    deep = deepCopy(image)

    assert deep is not None
    assert deep.GetDimensions() == image.GetDimensions()
