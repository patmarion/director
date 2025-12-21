from director.debugVis import DebugData
from director.script_context import fields
from director import visualization as vis


def main():
    # Create a sphere
    d = DebugData()
    d.addSphere([0, 0, 0], radius=1.0)
    sphere_polydata = d.getPolyData()

    # Show the sphere using showPolyData
    sphere_obj = vis.showPolyData(sphere_polydata, "hello sphere", color=[0.7, 0.3, 0.3])

    # Reset camera to fit the scene
    fields.view.resetCamera()


if __name__ == "__main__":
    main()
