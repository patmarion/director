from director import mainwindowapp
from director import objectmodel as om
from director import visualization as vis
from director import vtkAll as vtk

fields = mainwindowapp.construct()

transform = vtk.vtkTransform()
frame_item = vis.showFrame(transform, "frame")

frame_item.addFrameProperties()
frame_item.properties.edit = True

om.setSelectedObject(frame_item)

fields.app.start()
