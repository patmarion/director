"""Example demonstrating Image2DItem for displaying 2D image overlays."""

import sys
import numpy as np
import director.vtkAll as vtk
from director import mainwindowapp
from director.visualization import Image2DItem
from director.debugVis import DebugData


def create_test_image(width, height, pattern="gradient"):
    """Create a test vtkImageData with a pattern.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        pattern: Pattern type ('gradient', 'checkerboard', 'color')

    Returns:
        vtkImageData instance
    """
    image = vtk.vtkImageData()
    image.SetDimensions(width, height, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

    scalars = image.GetPointData().GetScalars()
    dims = image.GetDimensions()

    if pattern == "gradient":
        # Create a gradient from black to white
        for y in range(dims[1]):
            for x in range(dims[0]):
                idx = image.ComputePointId((x, y, 0))
                intensity = int(255 * (x / float(dims[0])))
                scalars.SetTuple3(idx, intensity, intensity, intensity)
    elif pattern == "checkerboard":
        # Create a checkerboard pattern
        for y in range(dims[1]):
            for x in range(dims[0]):
                idx = image.ComputePointId((x, y, 0))
                check = ((x // 10) + (y // 10)) % 2
                color = 255 if check else 128
                scalars.SetTuple3(idx, color, color, color)
    elif pattern == "color":
        # Create a colorful pattern
        for y in range(dims[1]):
            for x in range(dims[0]):
                idx = image.ComputePointId((x, y, 0))
                r = int(255 * (x / float(dims[0])))
                g = int(255 * (y / float(dims[1])))
                b = 128
                scalars.SetTuple3(idx, r, g, b)

    return image


def main():
    """Main function to demonstrate Image2DItem."""
    # Construct the main window application
    fields = mainwindowapp.construct()
    view = fields.view

    # Add some 3D geometry to the scene
    dd = DebugData()
    dd.addSphere(center=(0, 0, 0), radius=0.5)
    dd.addCylinder(center=(0.5, 0, 0), axis=(0, 1, 0), length=1.0, radius=0.3)
    dd.addCube(dimensions=(0.5, 0.5, 0.5), center=(0, 1, 0))

    from director.visualization import showPolyData

    sphere = showPolyData(dd.getPolyData(), name="test_geometry", view=view)

    # Reset camera to show the geometry
    view.resetCamera()
    view.render()

    # Create several test images with different patterns
    print("Creating test images...")

    # Image 1: Gradient pattern in top-left corner
    image1 = create_test_image(200, 150, pattern="gradient")
    item1 = Image2DItem("gradient_image", image1, view)
    item1.setProperty("Anchor", 0)  # Top Left
    item1.setProperty("Width", 200)
    item1.setProperty("Keep Aspect Ratio", True)  # Height will auto-update to 150
    item1.setProperty("Alpha", 0.9)

    # Image 2: Checkerboard pattern in top-right corner
    image2 = create_test_image(150, 150, pattern="checkerboard")
    item2 = Image2DItem("checkerboard_image", image2, view)
    item2.setProperty("Anchor", 1)  # Top Right
    item2.setProperty("Width", 150)
    item2.setProperty("Keep Aspect Ratio", True)  # Height will auto-update to 150 (square)
    item2.setProperty("Alpha", 0.8)

    # Image 3: Colorful pattern in bottom-left corner
    image3 = create_test_image(180, 120, pattern="color")
    item3 = Image2DItem("color_image", image3, view)
    item3.setProperty("Anchor", 2)  # Bottom Left
    item3.setProperty("Width", 180)
    item3.setProperty("Keep Aspect Ratio", True)  # Height will auto-update to 120
    item3.setProperty("Alpha", 0.85)

    # Add items to object model
    import director.objectmodel as om

    om.addToObjectModel(item1, parentObj=om.getOrCreateContainer("scene"))
    om.addToObjectModel(item2, parentObj=om.getOrCreateContainer("scene"))
    om.addToObjectModel(item3, parentObj=om.getOrCreateContainer("scene"))

    print("\nImage2DItem example loaded!")
    print("Three test images are displayed in the viewport:")
    print("  - Top Left: Gradient pattern (200x150)")
    print("  - Top Right: Checkerboard pattern (150x150)")
    print("  - Bottom Left: Colorful pattern (180x120)")
    print("\nYou can:")
    print("  - Adjust properties in the Properties Panel")
    print("  - Change Anchor position (Top Left, Top Right, Bottom Left, Bottom Right)")
    print("  - Adjust Width, Height, and Alpha")
    print("  - Toggle 'Keep Aspect Ratio' to maintain image proportions")
    print("  - Toggle Visible property")
    print("\nTry changing the properties:")
    print("  item1.setProperty('Anchor', 3)  # Move to bottom-right")
    print("  item1.setProperty('Width', 300)  # Make it larger (Height auto-updates if Keep Aspect Ratio=True)")
    print("  item1.setProperty('Height', 200)  # Change height (Width auto-updates if Keep Aspect Ratio=True)")
    print("  item1.setProperty('Keep Aspect Ratio', False)  # Disable auto-update")
    print("  item1.setProperty('Alpha', 0.5)  # Make it semi-transparent")

    # Start the application
    fields.app.start()


if __name__ == "__main__":
    sys.exit(main())
