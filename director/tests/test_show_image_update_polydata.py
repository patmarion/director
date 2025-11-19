"""Tests for showImage, updateImage, and updatePolyData functions."""

import sys
import pytest
import director.vtkAll as vtk
from director.visualization import showImage, updateImage, updatePolyData, showPolyData
from director.vtk_widget import VTKWidget
import director.objectmodel as om


def test_show_image(qapp):
    """Test showImage function."""
    widget = VTKWidget()
    
    # Create a test image
    image = vtk.vtkImageData()
    image.SetDimensions(100, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    # Initialize object model
    om.init()
    
    # Test with string anchor
    item = showImage(image, 'test_image', anchor='Top Left', view=widget)
    assert item is not None
    assert item.properties.getPropertyEnumValue('Anchor') == 'Top Left'
    
    # Test with different anchor
    image2 = vtk.vtkImageData()
    image2.SetDimensions(50, 50, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    item2 = showImage(image2, 'test_image2', anchor='Bottom Right', view=widget)
    assert item2.properties.getPropertyEnumValue('Anchor') == 'Bottom Right'
    
    # Test with integer anchor
    item3 = showImage(image, 'test_image3', anchor=2, view=widget)  # Bottom Left
    assert item3.properties.getPropertyEnumValue('Anchor') == 'Bottom Left'


def test_update_image(qapp):
    """Test updateImage function - should update existing or create new."""
    widget = VTKWidget()
    
    # Initialize object model
    om.init()
    
    # Create initial image
    image1 = vtk.vtkImageData()
    image1.SetDimensions(100, 100, 1)
    image1.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    # First call should create new item
    item = updateImage(image1, 'update_test_image', view=widget)
    assert item is not None
    assert item.image == image1
    
    # Second call should update existing item
    image2 = vtk.vtkImageData()
    image2.SetDimensions(200, 200, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item2 = updateImage(image2, 'update_test_image', view=widget)
    assert item2 == item  # Should be the same object
    assert item2.image == image2  # But image should be updated


def test_update_polydata(qapp):
    """Test updatePolyData function - should update existing or create new."""
    widget = VTKWidget()
    
    # Initialize object model
    om.init()
    
    # Create initial polyData
    sphere1 = vtk.vtkSphereSource()
    sphere1.SetRadius(1.0)
    sphere1.Update()
    polyData1 = sphere1.GetOutput()
    
    # First call should create new item
    item = updatePolyData(polyData1, 'update_test_polydata', view=widget)
    assert item is not None
    assert item.polyData == polyData1
    
    # Second call should update existing item
    sphere2 = vtk.vtkSphereSource()
    sphere2.SetRadius(2.0)
    sphere2.Update()
    polyData2 = sphere2.GetOutput()
    
    item2 = updatePolyData(polyData2, 'update_test_polydata', view=widget)
    assert item2 == item  # Should be the same object
    assert item2.polyData == polyData2  # But polyData should be updated


def test_update_polydata_with_kwargs(qapp):
    """Test that updatePolyData passes kwargs to showPolyData when creating new item."""
    widget = VTKWidget()
    
    # Initialize object model
    om.init()
    
    # Create polyData
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    sphere.Update()
    polyData = sphere.GetOutput()
    
    # Create with color
    item = updatePolyData(polyData, 'update_test_color', view=widget, color=[1.0, 0.0, 0.0])
    assert item is not None
    color = item.getProperty('Color')
    # PropertySet normalizes sequences to tuples
    assert color == (1.0, 0.0, 0.0)
    
    # Update existing - kwargs should be ignored (only updates polyData)
    sphere2 = vtk.vtkSphereSource()
    sphere2.SetRadius(2.0)
    sphere2.Update()
    polyData2 = sphere2.GetOutput()
    
    item2 = updatePolyData(polyData2, 'update_test_color', view=widget, color=[0.0, 1.0, 0.0])
    assert item2 == item
    assert item2.polyData == polyData2
    # Color should remain unchanged (updatePolyData only updates polyData, not other properties)
    color = item2.getProperty('Color')
    # PropertySet normalizes sequences to tuples
    assert color == (1.0, 0.0, 0.0)


def test_update_image_with_parent(qapp):
    """Test updateImage with parent container."""
    widget = VTKWidget()
    
    # Initialize object model
    om.init()
    
    # Create image
    image = vtk.vtkImageData()
    image.SetDimensions(100, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    # Create with parent
    parent = om.getOrCreateContainer('test_container')
    item = updateImage(image, 'parent_test_image', view=widget, parent=parent)
    assert item is not None
    assert item.parent() == parent
    
    # Update should find item in parent
    image2 = vtk.vtkImageData()
    image2.SetDimensions(200, 200, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item2 = updateImage(image2, 'parent_test_image', view=widget, parent=parent)
    assert item2 == item
    assert item2.image == image2

