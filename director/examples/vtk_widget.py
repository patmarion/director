"""Example demonstrating VTK widget with a cone using debug vis."""

import sys
from qtpy.QtWidgets import QApplication

from director.vtk_widget import VTKWidget
from director.debugVis import DebugData
from director import visualization as vis


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("vtk_widget")
    
    # Create VTK widget
    widget = VTKWidget()
    widget.setWindowTitle("VTK Widget - Cone Example")
    widget.setGeometry(100, 100, 800, 600)
    
    # Get the view (renderer)
    view = widget
    
    # Create a cone using debug vis
    d = DebugData()
    d.addCone((0, 0, 0), (0, 0, 1), 1.0, 2.0)
    
    # Show the cone in the view (will not add to object model since it's not initialized)
    cone_obj = vis.showPolyData(d.getPolyData(), 'cone', color=[0.8, 0.2, 0.2], view=view)
    
    # Reset camera to fit the scene
    widget.resetCamera()
    
    # Show the widget
    widget.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

