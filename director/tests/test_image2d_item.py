"""Tests for Image2DItem."""

import sys
import pytest
import numpy as np
import director.vtkAll as vtk
from director.visualization import Image2DItem
from director.vtk_widget import VTKWidget


def test_image2d_item_construction(qapp):
    """Test that Image2DItem can be constructed."""
    widget = VTKWidget()
    
    # Create a simple test image
    image = vtk.vtkImageData()
    image.SetDimensions(100, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    # Fill with a simple pattern
    dims = image.GetDimensions()
    for y in range(dims[1]):
        for x in range(dims[0]):
            idx = image.ComputePointId((x, y, 0))
            scalars = image.GetPointData().GetScalars()
            scalars.SetTuple3(idx, x % 255, y % 255, 128)
    
    item = Image2DItem('test_image', image, widget)
    assert item is not None
    assert item.image == image
    assert item.actor is not None
    assert item.getProperty('Visible') == True
    assert item.getProperty('Width') == 300
    assert item.getProperty('Height') == 300  # Square image, so height should match width
    assert item.getProperty('Keep Aspect Ratio') == True
    assert item.getProperty('Alpha') == 1.0


def test_image2d_item_properties(qapp):
    """Test Image2DItem property changes."""
    widget = VTKWidget()
    
    # Create a simple test image
    image = vtk.vtkImageData()
    image.SetDimensions(50, 50, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    # Test Alpha property
    item.setProperty('Alpha', 0.5)
    assert item.getProperty('Alpha') == 0.5
    
    # Test Visible property
    item.setProperty('Visible', False)
    assert item.getProperty('Visible') == False
    
    # Test Width property
    item.setProperty('Width', 200)
    assert item.getProperty('Width') == 200
    
    # Test Anchor property
    item.setProperty('Anchor', 2)  # Bottom Left
    assert item.properties.getPropertyEnumValue('Anchor') == 'Bottom Left'
    
    # Test Height property
    item.setProperty('Height', 200)
    assert item.getProperty('Height') == 200
    
    # Test Keep Aspect Ratio property
    assert item.getProperty('Keep Aspect Ratio') == True
    item.setProperty('Keep Aspect Ratio', False)
    assert item.getProperty('Keep Aspect Ratio') == False


def test_image2d_item_set_image(qapp):
    """Test updating the image."""
    widget = VTKWidget()
    
    # Create initial image
    image1 = vtk.vtkImageData()
    image1.SetDimensions(100, 100, 1)
    image1.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image1, widget)
    assert item.image == image1
    
    # Create new image
    image2 = vtk.vtkImageData()
    image2.SetDimensions(200, 200, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item.setImage(image2)
    assert item.image == image2


def test_image2d_item_has_dataset(qapp):
    """Test hasDataSet method."""
    widget = VTKWidget()
    
    image = vtk.vtkImageData()
    image.SetDimensions(50, 50, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    assert item.hasDataSet(image) == True
    
    other_image = vtk.vtkImageData()
    other_image.SetDimensions(50, 50, 1)
    other_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    assert item.hasDataSet(other_image) == False


def test_image2d_item_has_actor(qapp):
    """Test hasActor method."""
    widget = VTKWidget()
    
    image = vtk.vtkImageData()
    image.SetDimensions(50, 50, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    assert item.hasActor(item.actor) == True
    
    other_actor = vtk.vtkActor()
    assert item.hasActor(other_actor) == False


def test_image2d_item_anchor_positions(qapp):
    """Test different anchor positions."""
    widget = VTKWidget()
    widget.show()
    qapp.processEvents()
    
    image = vtk.vtkImageData()
    image.SetDimensions(80, 60, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    # Test all anchor positions
    anchors = ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']
    for i, anchor_name in enumerate(anchors):
        item.setProperty('Anchor', i)
        assert item.properties.getPropertyEnumValue('Anchor') == anchor_name
    
    widget.close()


def test_image2d_item_height_for_width(qapp):
    """Test _getHeightForWidth method."""
    widget = VTKWidget()
    
    # Create a 2:1 aspect ratio image (wider than tall)
    image = vtk.vtkImageData()
    image.SetDimensions(200, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    # For width=300, height should be 150 (maintaining 2:1 ratio)
    height = item._getHeightForWidth(image, 300)
    assert height == 150
    
    # For width=100, height should be 50
    height = item._getHeightForWidth(image, 100)
    assert height == 50
    
    # Create a 1:2 aspect ratio image (taller than wide)
    image2 = vtk.vtkImageData()
    image2.SetDimensions(100, 200, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item2 = Image2DItem('test_image2', image2, widget)
    
    # For width=100, height should be 200 (maintaining 1:2 ratio)
    height = item2._getHeightForWidth(image2, 100)
    assert height == 200


def test_image2d_item_aspect_ratio_sync(qapp):
    """Test that Width and Height sync when Keep Aspect Ratio is enabled."""
    widget = VTKWidget()
    
    # Create a 2:1 aspect ratio image (wider than tall)
    image = vtk.vtkImageData()
    image.SetDimensions(200, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    # Initially, width=300, height should be calculated from aspect ratio
    initial_width = item.getProperty('Width')
    initial_height = item.getProperty('Height')
    assert initial_width == 300
    # Height should be 150 (300 / 2.0 aspect ratio)
    assert initial_height == 150
    
    # With Keep Aspect Ratio enabled, changing width should update height
    item.setProperty('Keep Aspect Ratio', True)
    item.setProperty('Width', 400)
    assert item.getProperty('Width') == 400
    # Height should be 200 (400 / 2.0 aspect ratio)
    assert item.getProperty('Height') == 200
    
    # Changing height should update width
    item.setProperty('Height', 100)
    assert item.getProperty('Height') == 100
    # Width should be 200 (100 * 2.0 aspect ratio)
    assert item.getProperty('Width') == 200
    
    # With Keep Aspect Ratio disabled, changing width should NOT update height
    item.setProperty('Keep Aspect Ratio', False)
    item.setProperty('Width', 500)
    assert item.getProperty('Width') == 500
    # Height should remain unchanged
    assert item.getProperty('Height') == 100
    
    # Changing height should NOT update width when aspect ratio is disabled
    item.setProperty('Height', 250)
    assert item.getProperty('Height') == 250
    # Width should remain unchanged
    assert item.getProperty('Width') == 500


def test_image2d_item_width_for_height(qapp):
    """Test _getWidthForHeight method."""
    widget = VTKWidget()
    
    # Create a 2:1 aspect ratio image (wider than tall)
    image = vtk.vtkImageData()
    image.SetDimensions(200, 100, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item = Image2DItem('test_image', image, widget)
    
    # For height=150, width should be 300 (maintaining 2:1 ratio)
    width = item._getWidthForHeight(image, 150)
    assert width == 300
    
    # For height=50, width should be 100
    width = item._getWidthForHeight(image, 50)
    assert width == 100
    
    # Create a 1:2 aspect ratio image (taller than wide)
    image2 = vtk.vtkImageData()
    image2.SetDimensions(100, 200, 1)
    image2.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)
    
    item2 = Image2DItem('test_image2', image2, widget)
    
    # For height=200, width should be 100 (maintaining 1:2 ratio)
    width = item2._getWidthForHeight(image2, 200)
    assert width == 100

