"""Example demonstrating VTK widget with a cone using debug vis."""

import sys

from qtpy.QtWidgets import QApplication

from director import visualization as vis
from director.debugVis import DebugData
from director.vtk_widget import VTKWidget


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("vtk_widget")

    # Create VTK widget
    view = VTKWidget()
    view.setWindowTitle("VTK Widget - Cone Example")
    view.resize(800, 600)

    # Create a cone using debug vis
    d = DebugData()
    d.addCone((0, 0, 0), (0, 0, 1), 1.0, 2.0)

    # Show the cone in the view
    cone_obj = vis.showPolyData(d.getPolyData(), "cone", color=[0.8, 0.2, 0.2], view=view)

    # Reset camera to fit the scene
    view.resetCamera()

    # Show the widget
    view.show()

    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
