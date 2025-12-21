"""Tests for transformUtils module."""

import numpy as np
import vtk

from director.transformUtils import (
    concatenateTransforms,
    copyFrame,
    getAxesFromTransform,
    getNumpyFromTransform,
    getTransformFromAxes,
    getTransformFromAxesAndOrigin,
    getTransformFromNumpy,
)


def test_get_transform_from_numpy():
    """Test creating transform from numpy 4x4 matrix."""
    # Identity matrix
    mat = np.eye(4)

    transform = getTransformFromNumpy(mat)

    assert transform is not None
    assert isinstance(transform, vtk.vtkTransform)

    # Check it's identity
    result = getNumpyFromTransform(transform)
    np.testing.assert_array_almost_equal(result, mat)


def test_get_numpy_from_transform():
    """Test converting transform to numpy matrix."""
    transform = vtk.vtkTransform()
    transform.Translate(1, 2, 3)

    mat = getNumpyFromTransform(transform)

    assert mat is not None
    assert mat.shape == (4, 4)
    # Translation should be in last column
    np.testing.assert_array_almost_equal(mat[:3, 3], [1, 2, 3])


def test_get_transform_from_axes():
    """Test creating transform from axes."""
    xaxis = [1, 0, 0]
    yaxis = [0, 1, 0]
    zaxis = [0, 0, 1]

    transform = getTransformFromAxes(xaxis, yaxis, zaxis)

    assert transform is not None

    # Check axes
    result_x, result_y, result_z = getAxesFromTransform(transform)
    np.testing.assert_array_almost_equal(result_x, xaxis)
    np.testing.assert_array_almost_equal(result_y, yaxis)
    np.testing.assert_array_almost_equal(result_z, zaxis)


def test_get_transform_from_axes_and_origin():
    """Test creating transform from axes and origin."""
    xaxis = [1, 0, 0]
    yaxis = [0, 1, 0]
    zaxis = [0, 0, 1]
    origin = [5, 10, 15]

    transform = getTransformFromAxesAndOrigin(xaxis, yaxis, zaxis, origin)

    assert transform is not None

    # Transform origin should match
    result_origin = np.array(transform.TransformPoint(0, 0, 0))
    np.testing.assert_array_almost_equal(result_origin, origin)


def test_get_axes_from_transform():
    """Test extracting axes from transform."""
    transform = vtk.vtkTransform()
    transform.RotateZ(45)

    xaxis, yaxis, zaxis = getAxesFromTransform(transform)

    assert xaxis is not None
    assert yaxis is not None
    assert zaxis is not None
    assert len(xaxis) == 3
    assert len(yaxis) == 3
    assert len(zaxis) == 3


def test_copy_frame():
    """Test copying a transform frame."""
    original = vtk.vtkTransform()
    original.Translate(1, 2, 3)
    original.RotateZ(45)

    copied = copyFrame(original)

    assert copied is not None
    assert copied != original

    # Matrices should be the same
    mat_orig = getNumpyFromTransform(original)
    mat_copy = getNumpyFromTransform(copied)
    np.testing.assert_array_almost_equal(mat_orig, mat_copy)


def test_concatenate_transforms():
    """Test concatenating multiple transforms."""
    t1 = vtk.vtkTransform()
    t1.Translate(1, 0, 0)

    t2 = vtk.vtkTransform()
    t2.Translate(0, 1, 0)

    result = concatenateTransforms([t1, t2])

    assert result is not None

    # Result should have both transformations applied
    point = np.array(result.TransformPoint(0, 0, 0))
    # Should be translated by (1, 1, 0) due to post-multiply
    np.testing.assert_array_almost_equal(point, [1, 1, 0], decimal=4)
