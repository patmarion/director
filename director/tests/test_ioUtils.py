"""Tests for ioUtils module."""

import os
import tempfile

import pytest

import director.ioUtils as io
import director.vtkAll as vtk


def test_save_and_read_data():
    """Test saveDataToFile and readDataFromFile functions."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        filename = tmp_file.name

    try:
        # Generate test data
        test_data = {
            "int_value": 42,
            "float_value": 3.14159,
            "string_value": "test string",
            "list_value": [1, 2, 3, 4, 5],
            "dict_value": {"nested_key": "nested_value", "nested_number": 100},
            "bool_value": True,
            "none_value": None,
        }

        # Write data to file
        io.saveDataToFile(filename, test_data, overwrite=True)

        # Verify file was created
        assert os.path.isfile(filename)

        # Read data back
        read_data = io.readDataFromFile(filename)

        # Verify data matches
        assert read_data == test_data
        assert read_data["int_value"] == 42
        assert read_data["float_value"] == 3.14159
        assert read_data["string_value"] == "test string"
        assert read_data["list_value"] == [1, 2, 3, 4, 5]
        assert read_data["dict_value"]["nested_key"] == "nested_value"
        assert read_data["bool_value"] is True
        assert read_data["none_value"] is None

    finally:
        # Clean up
        if os.path.isfile(filename):
            os.remove(filename)
        # Also remove .db file created by shelve
        if os.path.isfile(filename):
            os.remove(filename)


def test_save_data_overwrite_false():
    """Test that saveDataToFile raises error when overwrite=False and file exists."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        filename = tmp_file.name

    try:
        test_data = {"key": "value"}

        # Write data first time (should succeed)
        io.saveDataToFile(filename, test_data, overwrite=True)

        # Try to write again with overwrite=False (should raise error)
        with pytest.raises(ValueError, match="file already exists"):
            io.saveDataToFile(filename, test_data, overwrite=False)

    finally:
        if os.path.isfile(filename):
            os.remove(filename)


def test_write_and_read_polydata():
    """Test writePolyData and readPolyData functions."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".vtp") as tmp_file:
        filename = tmp_file.name

    try:
        # Generate test poly data (a simple sphere)
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(1.0)
        sphere.SetThetaResolution(20)
        sphere.SetPhiResolution(20)
        sphere.Update()

        original_poly_data = sphere.GetOutput()

        # Write poly data to file
        io.writePolyData(original_poly_data, filename)

        # Verify file was created
        assert os.path.isfile(filename)

        # Read poly data back
        read_poly_data = io.readPolyData(filename)

        # Verify poly data matches (check point count and cell count)
        assert read_poly_data.GetNumberOfPoints() == original_poly_data.GetNumberOfPoints()
        assert read_poly_data.GetNumberOfCells() == original_poly_data.GetNumberOfCells()

    finally:
        # Clean up
        if os.path.isfile(filename):
            os.remove(filename)


def test_read_polydata_with_normals():
    """Test readPolyData with computeNormals=True."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".vtp") as tmp_file:
        filename = tmp_file.name

    try:
        # Generate test poly data
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(1.0)
        sphere.SetThetaResolution(10)
        sphere.SetPhiResolution(10)
        sphere.Update()

        original_poly_data = sphere.GetOutput()

        # Write poly data to file
        io.writePolyData(original_poly_data, filename)

        # Read with normals
        read_poly_data = io.readPolyData(filename, computeNormals=True)

        # Verify normals were computed
        normals = read_poly_data.GetPointData().GetNormals()
        assert normals is not None
        assert normals.GetNumberOfTuples() == read_poly_data.GetNumberOfPoints()

    finally:
        if os.path.isfile(filename):
            os.remove(filename)


def test_write_polydata_unknown_extension():
    """Test that writePolyData raises error for unknown file extension."""
    # Create test poly data
    sphere = vtk.vtkSphereSource()
    sphere.Update()
    poly_data = sphere.GetOutput()

    # Try to write with unknown extension
    with pytest.raises(Exception, match="Unknown file extension"):
        io.writePolyData(poly_data, "test.unknown")


def test_read_polydata_unknown_extension():
    """Test that readPolyData raises error for unknown file extension."""
    with pytest.raises(Exception, match="Unknown file extension"):
        io.readPolyData("test.unknown")
