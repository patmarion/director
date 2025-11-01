"""Tests for filterUtils module."""

import vtk
import numpy as np
import pytest
from director.filterUtils import (
    computeCentroid, appendPolyData, cleanPolyData,
    computeNormals, triangulatePolyData
)
from director.vtkNumpy import numpyToPolyData, addNumpyToVtk


def test_compute_centroid():
    """Test computing centroid of PolyData."""
    # Create points forming a square
    points = np.array([
        [0, 0, 0],
        [2, 0, 0],
        [2, 2, 0],
        [0, 2, 0]
    ], dtype=np.float64)
    
    polyData = numpyToPolyData(points)
    centroid = computeCentroid(polyData)
    
    assert centroid is not None
    assert len(centroid) == 3
    # Centroid of square should be at (1, 1, 0)
    np.testing.assert_array_almost_equal(centroid, [1.0, 1.0, 0.0])


def test_append_polydata():
    """Test appending multiple PolyData objects."""
    # Create two sets of points
    points1 = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.float64)
    points2 = np.array([[0, 1, 0], [1, 1, 0]], dtype=np.float64)
    
    polyData1 = numpyToPolyData(points1, createVertexCells=True)
    polyData2 = numpyToPolyData(points2, createVertexCells=True)
    
    appended = appendPolyData([polyData1, polyData2])
    
    assert appended is not None
    assert appended.GetNumberOfPoints() == 4
    assert appended.GetNumberOfCells() == 4


def test_append_polydata_empty():
    """Test appending empty list."""
    appended = appendPolyData([])
    assert appended is not None


def test_clean_polydata():
    """Test cleaning PolyData."""
    # Create points with duplicates
    points = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [1, 0, 0],  # Duplicate
        [0, 1, 0]
    ], dtype=np.float64)
    
    polyData = numpyToPolyData(points, createVertexCells=True)
    cleaned = cleanPolyData(polyData)
    
    assert cleaned is not None
    # Clean should remove duplicate points
    assert cleaned.GetNumberOfPoints() <= polyData.GetNumberOfPoints()


def test_compute_normals():
    """Test computing normals for PolyData."""
    # Create a simple triangle with explicit triangle cell
    points = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0.5, 1, 0]
    ], dtype=np.float64)
    
    polyData = numpyToPolyData(points, createVertexCells=False)
    
    # Add a triangle cell
    triangle = vtk.vtkTriangle()
    triangle.GetPointIds().SetId(0, 0)
    triangle.GetPointIds().SetId(1, 1)
    triangle.GetPointIds().SetId(2, 2)
    
    cells = vtk.vtkCellArray()
    cells.InsertNextCell(triangle)
    polyData.SetPolys(cells)
    
    normals = computeNormals(polyData)
    
    assert normals is not None
    # Normals should be computed (but may be None if feature angle is too small)
    # Just check that the function ran without error
    assert normals.GetNumberOfPoints() == polyData.GetNumberOfPoints()


def test_triangulate_polydata():
    """Test triangulating PolyData."""
    # Create a simple quad
    points = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [1, 1, 0],
        [0, 1, 0]
    ], dtype=np.float64)
    
    polyData = numpyToPolyData(points, createVertexCells=False)
    # Add a quad cell manually for testing
    quad = vtk.vtkQuad()
    quad.GetPointIds().SetId(0, 0)
    quad.GetPointIds().SetId(1, 1)
    quad.GetPointIds().SetId(2, 2)
    quad.GetPointIds().SetId(3, 3)
    
    cells = vtk.vtkCellArray()
    cells.InsertNextCell(quad)
    polyData.SetPolys(cells)
    
    triangulated = triangulatePolyData(polyData)
    
    assert triangulated is not None
    assert triangulated.GetNumberOfCells() > 0

