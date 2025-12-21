"""Hello World example demonstrating Director api."""

from director import mainwindowapp
from director import visualization as vis
from director.debugVis import DebugData


def main():
    """Main entry point for the application."""
    # Construct the application using MainWindowApp
    fields = mainwindowapp.construct(windowTitle="Director 2.0 - Hello World")

    # Create a sphere
    d = DebugData()
    d.addSphere([0, 0, 0], radius=1.0)
    sphere_polydata = d.getPolyData()

    # Show the sphere using showPolyData
    sphere_obj = vis.showPolyData(sphere_polydata, "hello_sphere", color=[0.7, 0.3, 0.3])

    # Reset camera to fit the scene
    fields.view.resetCamera()

    # Start the event loop
    return fields.app.start()


if __name__ == "__main__":
    main()
