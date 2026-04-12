"""Demo for selectively enabling FrameItem translation and rotation handles."""

from director import mainwindowapp
from director import objectmodel as om
from director import visualization as vis
from director import vtkAll as vtk


def make_frame(name, translation):
    transform = vtk.vtkTransform()
    transform.Translate(*translation)
    frame = vis.showFrame(transform, name, parent="Frame Axis Controls")
    frame.addFrameProperties()
    frame.properties.edit = True
    return frame


fields = mainwindowapp.construct()

full_frame = make_frame("full controls", (0.0, 0.0, 0.0))

x_only_frame = make_frame("translate X only", (-0.8, 0.0, 0.0))
x_only_frame.setTranslateAxisEnabled(1, False)
x_only_frame.setTranslateAxisEnabled(2, False)
x_only_frame.setRotateAxisEnabled(0, False)
x_only_frame.setRotateAxisEnabled(1, False)
x_only_frame.setRotateAxisEnabled(2, False)

xy_plane_frame = make_frame("XY plane / rotate Z", (0.8, 0.0, 0.0))
xy_plane_frame.setTranslateAxisEnabled(0, False)
xy_plane_frame.setTranslateAxisEnabled(1, False)
xy_plane_frame.setTranslateAxisEnabled(2, False)
xy_plane_frame.setRotateAxisEnabled(0, False)
xy_plane_frame.setRotateAxisEnabled(1, False)

translate_only_frame = make_frame("translate axes only", (0.0, 0.8, 0.0))
translate_only_frame.setRotateAxisEnabled(0, False)
translate_only_frame.setRotateAxisEnabled(1, False)
translate_only_frame.setRotateAxisEnabled(2, False)

om.setSelectedObject(full_frame)

print("FrameItem axis control demo:")
print("  - full controls: default translation axes and rotation rings")
print("  - translate X only: one translation handle, no rings")
print("  - XY plane / rotate Z: plane handle in XY plus rotation about Z")
print("  - translate axes only: all three translation axes, no rings")

fields.app.start()
