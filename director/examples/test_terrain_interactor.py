"""Example demonstrating the pure Python terrain interactor.

This example creates a VTKWidget with the terrain interactor style.
Shows a simple scene with some geometries that can be viewed with terrain-style controls.
"""

import sys
from qtpy.QtWidgets import QApplication, QMainWindow

from director import vtk_widget
from director.terrain_interactor import setTerrainInteractor
from director.debugVis import DebugData
from director import visualization as vis


def main():
    """Main entry point for the terrain interactor example."""
    app = QApplication(sys.argv)
    app.setApplicationName("Director 2.0 - Terrain Interactor Example")
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Director 2.0 - Terrain Interactor Example")
    window.resize(800, 600)
    
    # Create VTK widget
    view = vtk_widget.VTKWidget()
    window.setCentralWidget(view)
    
    # Set terrain interactor
    terrain_style = setTerrainInteractor(view)
    if terrain_style:
        print("Terrain interactor enabled")
        print("Controls:")
        print("  Left mouse drag: Rotate camera (azimuth/elevation)")
        print("  Right mouse drag: Zoom")
        print("  Shift + Left mouse drag: Pan/translate")
        print("  Mouse wheel: Zoom in/out")
        print("  Ctrl+Q: Quit")
    else:
        print("Failed to set terrain interactor")
        return 1
    
    # Add Ctrl+Q quit shortcut
    view.addQuitShortcut()
    
    # Create some test geometry
    d = DebugData()
    
    # Add a grid on the ground
    d.addSphere([0, 0, 0], radius=0.5, color=[1, 0, 0])  # Red sphere at origin
    d.addSphere([2, 0, 1], radius=0.5, color=[0, 1, 0])  # Green sphere
    d.addSphere([-2, 0, 1], radius=0.5, color=[0, 0, 1])  # Blue sphere
    d.addSphere([0, 2, 1], radius=0.5, color=[1, 1, 0])   # Yellow sphere
    d.addSphere([0, -2, 1], radius=0.5, color=[1, 0, 1])  # Magenta sphere
    
    # Add some boxes
    d.addCube([1, 1, 1], center=[0, 0, 2], color=[0.5, 0.5, 1])
    d.addCube([0.5, 0.5, 0.5], center=[3, 3, 0.5], color=[1, 0.5, 0.5])
    
    # Add a cylinder
    d.addCylinder([-3, -3, 1], axis=[0, 0, 1], length=2, radius=0.3, color=[0.5, 1, 0.5])
    
    # Show the geometry
    polyData = d.getPolyData()
    obj = vis.showPolyData(polyData, 'test_geometry', view=view, color=[0.8, 0.8, 0.8])
    
    # Set up initial camera position for terrain view
    camera = view.camera()
    camera.SetPosition(10, 10, 10)
    camera.SetFocalPoint(0, 0, 0)
    camera.SetViewUp(0, 0, 1)
    
    # Reset camera to fit scene
    view.resetCamera()
    
    # Show window
    window.show()
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

