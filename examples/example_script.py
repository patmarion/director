import director.visualization as vis
from director.debugVis import DebugData


def main():
    d = DebugData()
    d.addSphere([0, 0, 0], radius=1.0)
    sphere_polydata = d.getPolyData()
    vis.showPolyData(sphere_polydata, "sphere")


if __name__ == "__main__":
    main()
