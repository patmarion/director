"""Tests for vtkNumpy module."""

import vtk
import numpy as np
import pytest
from director.vtkNumpy import (
    numpyToPolyData,
    getNumpyFromVtk,
    getVtkPointsFromNumpy,
    addNumpyToVtk,
    numpyToImageData,
    getNumpyImageFromVtk,
)


def test_numpy_to_polydata():
    """Test converting numpy points to VTK PolyData."""
    # Create some points
    points = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)

    polyData = numpyToPolyData(points, createVertexCells=True)

    assert polyData is not None
    assert polyData.GetNumberOfPoints() == 4
    assert polyData.GetNumberOfCells() == 4  # Vertex cells


def test_numpy_to_polydata_with_point_data():
    """Test converting numpy points with point data to VTK PolyData."""
    points = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.float64)
    pointData = {"labels": np.array([0, 1], dtype=np.int32)}

    polyData = numpyToPolyData(points, pointData=pointData, createVertexCells=True)

    assert polyData is not None
    assert polyData.GetNumberOfPoints() == 2
    assert polyData.GetPointData().GetArray("labels") is not None


def test_get_numpy_from_vtk_points():
    """Test getting numpy array from VTK PolyData points."""
    # Create a simple sphere
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    sphere.Update()
    polyData = sphere.GetOutput()

    points = getNumpyFromVtk(polyData, "Points")

    assert points is not None
    assert isinstance(points, np.ndarray)
    assert points.shape[1] == 3  # 3D points
    assert points.shape[0] == polyData.GetNumberOfPoints()


def test_add_numpy_to_vtk():
    """Test adding numpy array to VTK PolyData."""
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    sphere.Update()
    polyData = sphere.GetOutput()

    # Create some scalar data
    scalars = np.arange(polyData.GetNumberOfPoints(), dtype=np.float64)
    addNumpyToVtk(polyData, scalars, "my_scalars", arrayType="points")

    array = polyData.GetPointData().GetArray("my_scalars")
    assert array is not None
    assert array.GetNumberOfTuples() == polyData.GetNumberOfPoints()


def test_numpy_to_image_data():
    """Test converting numpy image to VTK ImageData."""
    # Create a simple 2D image
    img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

    imageData = numpyToImageData(img, flip=False)

    assert imageData is not None
    assert imageData.GetDimensions() == (100, 100, 1)
    assert imageData.GetNumberOfScalarComponents() == 1


def test_numpy_to_image_data_color():
    """Test converting numpy color image to VTK ImageData."""
    # Create a simple RGB image
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    imageData = numpyToImageData(img, flip=False)

    assert imageData is not None
    assert imageData.GetDimensions() == (100, 100, 1)
    assert imageData.GetNumberOfScalarComponents() == 3


def test_get_numpy_image_from_vtk():
    """Test converting VTK ImageData to numpy image."""
    # Create VTK image
    img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    imageData = numpyToImageData(img, flip=False)

    # Convert back
    img2 = getNumpyImageFromVtk(imageData, flip=False)

    assert img2 is not None
    assert isinstance(img2, np.ndarray)
    assert img2.shape == img.shape


def test_get_vtk_points_from_numpy():
    """Test converting numpy array to VTK points."""
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)

    vtkPoints = getVtkPointsFromNumpy(points)

    assert vtkPoints is not None
    assert vtkPoints.GetNumberOfPoints() == 3
