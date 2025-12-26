import numpy as np

import director.objectmodel as om
from director import vtkAll as vtk


class FrameTraceVisualizer:
    def __init__(self, frame):
        self.frame = frame
        self.last_position = np.array(frame.transform.GetPosition())
        self.callback_id = frame.connectFrameModified(self.on_frame_modified)

    def remove(self):
        self.frame.disconnectFrameModified(self.callback_id)
        om.removeFromObjectModel(self._item())

    def _reset(self):
        self.points = vtk.vtkPoints()
        self.points.SetDataTypeToDouble()
        self.points.InsertNextPoint(self.last_position)
        self.cells = vtk.vtkCellArray()
        self.polyData = vtk.vtkPolyData()
        self.polyData.SetPoints(self.points)
        self.polyData.SetLines(self.cells)
        self._update_polyline()

    def _update_polyline(self):
        """Rebuild the polyline cell with all current points."""
        numberOfPoints = self.points.GetNumberOfPoints()
        if numberOfPoints < 1:
            return

        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(numberOfPoints)
        for i in range(numberOfPoints):
            polyline.GetPointIds().SetId(i, i)

        self.cells.Reset()
        self.cells.InsertNextCell(polyline)

    def _add_point(self, point):
        self.points.InsertNextPoint(point)
        self._update_polyline()
        self.points.Modified()
        self.cells.Modified()
        self.polyData.Modified()

    def _name(self):
        frame_name = self.frame.properties.name
        return f"{frame_name} trace"

    def _item(self):
        return self.frame.findChild(self._name())

    def on_frame_modified(self, frame):
        position = np.array(frame.transform.GetPosition())
        if np.allclose(position, self.last_position):
            return

        item = self._item()
        if not item:
            self._reset()
            from director import visualization as vis

            item = vis.showPolyData(self.polyData, self._name(), parent=self.frame)

        self._add_point(position)
        self.last_position = position
        item._renderAllViews()
