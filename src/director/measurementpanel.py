import os

import numpy as np
from qtpy import QtCore

from director import objectmodel as om
from director import vieweventfilter
from director import visualization as vis
from director import vtkAll as vtk
from director.debugVis import DebugData
from director.qtutils import loadUi


class MeasurementEventFilter(vieweventfilter.ViewEventFilter):
    def __init__(self, view, panel):
        super().__init__(view)
        self.panel = panel

    def onMouseMove(self, event):
        displayPoint = self.getMousePositionInView(event)
        self.panel.onMouseMove(displayPoint)
        return False

    def onLeftMousePress(self, event):
        # Consume the press event when shift is held to prevent the terrain
        # interactor from starting a camera rotation operation
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            return True
        return False

    def onLeftClick(self, event):
        displayPoint = self.getMousePositionInView(event)

        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.panel.onShiftMouseClick(displayPoint)
            return True

        return False


def computeViewScale(view, position):
    camera = view.camera()
    if camera.GetParallelProjection():
        worldHeight = 2 * camera.GetParallelScale()
    else:
        mat = camera.GetViewTransformMatrix()
        cvz = np.zeros(3)
        cvz[0] = mat.GetElement(2, 0)
        cvz[1] = mat.GetElement(2, 1)
        cvz[2] = mat.GetElement(2, 2)

        cameraPosition = np.array(camera.GetPosition())
        v = cameraPosition - np.array(position)
        worldHeight = 2 * (np.dot(v, cvz) * np.tan(0.5 * camera.GetViewAngle() / 57.296))
    windowHeight = view.renderer().GetSize()[1]
    return worldHeight / windowHeight


def computeAngle(p1, p2, p3):
    """Compute angle at p2 formed by vectors p2->p1 and p2->p3.

    Returns angle in degrees.
    """
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)

    len1 = np.linalg.norm(v1)
    len2 = np.linalg.norm(v2)

    if len1 < 1e-9 or len2 < 1e-9:
        return 0.0

    v1 = v1 / len1
    v2 = v2 / len2

    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    angle_rad = np.arccos(dot)
    return np.degrees(angle_rad)


class MeasurementPanel:
    def __init__(self, app, view):
        self.view = view

        # Load UI from file
        ui_file = os.path.join(os.path.dirname(__file__), "assets", "measurement_panel.ui")
        self.widget, self.ui = loadUi(ui_file)

        self.ui.enabledCheck.toggled.connect(self.onEnabledCheckBox)
        self.ui.clearButton.clicked.connect(self.onClear)

        self.eventFilter = MeasurementEventFilter(view, self)
        self.annotation = vis.PolyDataItem("annotation", self.makeSphere((0, 0, 0)), view)
        self.annotation.setProperty("Color", [0, 1, 0])
        self.annotation.actor.SetPickable(False)
        self.annotation.actor.SetUserTransform(vtk.vtkTransform())
        self.pickPoints = []

        # Hover visualization objects
        self.hoverLineObj = None
        self.hoverDistanceText = None
        self.hoverAngleText = None

        # Permanent visualization objects for recorded points
        self.lineObjs = []  # Lines between recorded points
        self.distanceTextObjs = []  # Distance labels
        self.angleTextObjs = []  # Angle labels

        self.setEnabled(False)

    def onEnabledCheckBox(self):
        self.setEnabled(self.isEnabled())

    def isEnabled(self):
        return bool(self.ui.enabledCheck.isChecked())

    def setEnabled(self, enabled):
        self.ui.enabledCheck.setChecked(enabled)

        self.annotation.setProperty("Visible", False)
        self._removeHoverVisuals()

        folder = self.getRootFolder(create=False)
        if folder:
            for obj in folder.children():
                if hasattr(obj, "actor"):
                    obj.actor.SetPickable(not enabled)

        if self.isEnabled():
            # Install the event filter on the VTK widget
            vtk_widget = self.view.vtkWidget()
            if vtk_widget:
                vtk_widget.installEventFilter(self.eventFilter)
        else:
            self.eventFilter.removeEventFilter()

        self.ui.panelContents.setEnabled(enabled)

    def onClear(self):
        self.ui.textEdit.clear()
        self._removeHoverVisuals()
        om.removeFromObjectModel(self.getRootFolder())
        self.pickPoints = []
        self.lineObjs = []
        self.distanceTextObjs = []
        self.angleTextObjs = []

    def _removeHoverVisuals(self):
        """Remove all hover visualization objects from the object model."""
        if self.hoverLineObj is not None:
            om.removeFromObjectModel(self.hoverLineObj)
            self.hoverLineObj = None
        if self.hoverDistanceText is not None:
            om.removeFromObjectModel(self.hoverDistanceText)
            self.hoverDistanceText = None
        if self.hoverAngleText is not None:
            om.removeFromObjectModel(self.hoverAngleText)
            self.hoverAngleText = None

    def _updateHoverVisuals(self, hoverPoint):
        """Update hover line and text to show distance/angle to previous point."""
        if len(self.pickPoints) == 0:
            self._removeHoverVisuals()
            return

        # Remove old hover visuals and create fresh ones
        self._removeHoverVisuals()

        folder = self.getRootFolder()
        prevPoint = self.pickPoints[-1]
        hoverPoint = np.array(hoverPoint)

        # Create hover line
        d = DebugData()
        d.addLine(prevPoint, hoverPoint)
        self.hoverLineObj = vis.showPolyData(
            d.getPolyData(),
            "hover line",
            color=[0, 1, 0],
            alpha=0.5,
            parent=folder,
            view=self.view,
        )
        self.hoverLineObj.actor.SetPickable(False)

        # Create distance text
        distance = np.linalg.norm(hoverPoint - prevPoint)
        midpoint = (prevPoint + hoverPoint) / 2.0
        self.hoverDistanceText = vis.showText(
            f"{distance:.3f}", "hover distance", fontSize=14, parent=folder, view=self.view
        )
        self.hoverDistanceText.setProperty("Coordinates", 1)  # World
        self.hoverDistanceText.setProperty("World Position", midpoint.tolist())
        self.hoverDistanceText.setProperty("Background Alpha", 0.6)
        self.hoverDistanceText.setProperty("Color", [1.0, 1.0, 0.0])

        # Create angle text if we have at least 2 recorded points
        if len(self.pickPoints) >= 2:
            prevPrevPoint = self.pickPoints[-2]
            angle = computeAngle(prevPrevPoint, prevPoint, hoverPoint)
            self.hoverAngleText = vis.showText(
                f"{angle:.1f}°", "hover angle", fontSize=14, parent=folder, view=self.view
            )
            self.hoverAngleText.setProperty("Coordinates", 1)  # World
            self.hoverAngleText.setProperty("World Position", prevPoint.tolist())
            self.hoverAngleText.setProperty("Background Alpha", 0.6)
            self.hoverAngleText.setProperty("Color", [0.0, 1.0, 1.0])

    def pickIsValid(self):
        return self.ui.objName.text() != "none"

    def getRootFolder(self, create=True):
        name = "measurements"
        if create:
            return om.getOrCreateContainer(name)
        else:
            return om.findObjectByName(name)

    def makeSphere(self, position, radius=1.0):
        d = DebugData()
        d.addSphere(position, radius=radius)
        return d.getPolyData()

    def _createPermanentLine(self, p1, p2, index):
        """Create a permanent line between two recorded points."""
        folder = self.getRootFolder()
        d = DebugData()
        d.addLine(p1, p2)
        lineObj = vis.showPolyData(
            d.getPolyData(),
            f"line {index}",
            color=[1, 0.5, 0],
            alpha=0.7,
            parent=folder,
            view=self.view,
        )
        lineObj.actor.SetPickable(False)
        return lineObj

    def _createDistanceLabel(self, p1, p2, index):
        """Create a distance label at the midpoint of a line."""
        folder = self.getRootFolder()
        distance = np.linalg.norm(np.array(p2) - np.array(p1))
        midpoint = (np.array(p1) + np.array(p2)) / 2.0

        textObj = vis.showText(f"{distance:.3f}", f"dist {index}", fontSize=12, parent=folder, view=self.view)
        textObj.setProperty("Coordinates", 1)  # World
        textObj.setProperty("World Position", midpoint.tolist())
        textObj.setProperty("Background Alpha", 0.5)
        textObj.setProperty("Color", [1.0, 0.8, 0.0])
        return textObj

    def _createAngleLabel(self, p1, p2, p3, index):
        """Create an angle label at the vertex p2."""
        folder = self.getRootFolder()
        angle = computeAngle(p1, p2, p3)

        textObj = vis.showText(f"{angle:.1f}°", f"angle {index}", fontSize=12, parent=folder, view=self.view)
        textObj.setProperty("Coordinates", 1)  # World
        textObj.setProperty("World Position", list(p2))
        textObj.setProperty("Background Alpha", 0.5)
        textObj.setProperty("Color", [0.5, 1.0, 1.0])
        return textObj

    def snapshotGeometry(self):
        if not self.pickIsValid():
            return

        p = np.array([float(x) for x in self.ui.pickPt.text().split(", ")])

        # Create sphere for the new point
        polyData = self.makeSphere((0, 0, 0))
        folder = self.getRootFolder()
        pointIndex = len(self.pickPoints)
        obj = vis.showPolyData(polyData, f"point {pointIndex}", color=[1, 0, 0], parent=folder, view=self.view)
        obj.actor.SetPickable(False)

        scale = computeViewScale(self.view, p)
        scale = scale * 10
        t = vtk.vtkTransform()
        t.Translate(p)
        t.Scale(scale, scale, scale)
        obj.actor.SetUserTransform(t)

        # Create permanent line and distance label if we have a previous point
        if len(self.pickPoints) > 0:
            prevPoint = self.pickPoints[-1]
            lineIndex = len(self.lineObjs)

            lineObj = self._createPermanentLine(prevPoint, p, lineIndex)
            self.lineObjs.append(lineObj)

            distTextObj = self._createDistanceLabel(prevPoint, p, lineIndex)
            self.distanceTextObjs.append(distTextObj)

        # Create angle label if we have at least 2 previous points
        if len(self.pickPoints) >= 2:
            prevPrevPoint = self.pickPoints[-2]
            prevPoint = self.pickPoints[-1]
            angleIndex = len(self.angleTextObjs)

            angleTextObj = self._createAngleLabel(prevPrevPoint, prevPoint, p, angleIndex)
            self.angleTextObjs.append(angleTextObj)

        # Add the point to our list
        self.pickPoints.append(p)

    def snapshotText(self):
        if not self.pickIsValid():
            return

        if len(self.pickPoints) > 1:
            dist = np.linalg.norm(self.pickPoints[-1] - self.pickPoints[-2])
        else:
            dist = 0.0

        s = "pick_point " + self.ui.pickPt.text() + "\n"
        s += "pick_normal " + self.ui.pickNormal.text() + "\n"
        s += "dist_to_previous_point " + "%f" % dist + "\n"

        # Add angle info if available
        if len(self.pickPoints) >= 3:
            angle = computeAngle(self.pickPoints[-3], self.pickPoints[-2], self.pickPoints[-1])
            s += "angle_at_previous_point " + "%.1f" % angle + "°\n"

        s += "\n"

        self.ui.textEdit.append(s.replace("\n", "<br/>"))

    def onShiftMouseClick(self, displayPoint):
        self.updatePick(displayPoint)
        self.snapshotGeometry()
        self.snapshotText()
        self.annotation.setProperty("Visible", False)
        self._removeHoverVisuals()

    def onMouseMove(self, displayPoint):
        self.updatePick(displayPoint)

    def updatePick(self, displayPoint):
        pickType = str(self.ui.pickTypeCombo.currentText())
        if "render" in pickType:
            pickType = "render"
        elif "vertex" in pickType:
            pickType = "points"
        elif "surface" in pickType:
            pickType = "cells"
        else:
            raise Exception("unknown pick type")

        tolerance = self.ui.toleranceSpinBox.value()
        pickPointFields = vis.pickPoint(displayPoint, self.view, pickType=pickType, tolerance=tolerance)
        worldPoint = pickPointFields.pickedPoint
        prop = pickPointFields.pickedProp
        dataset = pickPointFields.pickedDataset
        normal = pickPointFields.pickedNormal

        if not prop:
            worldPoint = np.zeros(3)
            normal = np.zeros(3)
            self._removeHoverVisuals()
        else:
            # Update hover visuals when we have a valid pick
            self._updateHoverVisuals(worldPoint)

        obj = vis.getObjectByProp(prop)

        self.ui.displayPt.setText("%d, %d" % tuple(displayPoint))
        self.ui.worldPt.setText("%.5f, %.5f, %.5f" % tuple(worldPoint))
        self.ui.pickPt.setText("%.5f, %.5f, %.5f" % tuple(worldPoint))

        if normal is not None:
            self.ui.pickNormal.setText("%.5f, %.5f, %.5f" % tuple(normal))
        else:
            self.ui.pickNormal.setText("not available")

        scale = computeViewScale(self.view, worldPoint)
        scale = scale * 10

        self.annotation.setProperty("Visible", prop is not None)
        t = vtk.vtkTransform()
        t.Translate(worldPoint)
        t.Scale(scale, scale, scale)
        self.annotation.actor.SetUserTransform(t)
        self.annotation._renderAllViews()

        if obj:
            self.ui.objName.setText(obj.getProperty("Name"))
        else:
            self.ui.objName.setText("none")

        if dataset:
            self.ui.numPts.setText(str(dataset.GetNumberOfPoints()))
            self.ui.numCells.setText(str(dataset.GetNumberOfCells()))
        else:
            self.ui.numPts.setText("0")
            self.ui.numCells.setText("0")
