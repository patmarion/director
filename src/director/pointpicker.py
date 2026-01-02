import numpy as np
from qtpy import QtCore

import director.objectmodel as om
import director.visualization as vis
from director import callbacks
from director.debugVis import DebugData


class PointPicker(QtCore.QObject):
    def __init__(self, view, obj=None, callback=None, numberOfPoints=2, drawLines=True, abortCallback=None):
        super().__init__()
        self.view = view
        self.obj = obj
        self.pickType = "points"
        self.tolerance = 0.01
        self.numberOfPoints = numberOfPoints
        self.drawLines = drawLines
        self.drawClosedLoop = False
        self.annotationObj = None
        self.annotationFunc = callback
        self.abortFunc = abortCallback
        self.annotationName = "annotation"
        self.annotationFolder = "segmentation"
        self._filterInstalled = False
        self.clear()

    def start(self):
        self.installEventFilter(self)
        self.clear()

    def stop(self):
        self.removeEventFilter(self)

    def installEventFilter(self, filterObj):
        if not self._filterInstalled:
            self.view.vtkWidget().installEventFilter(filterObj)
            self._filterInstalled = True

    def removeEventFilter(self, filterObj):
        if self._filterInstalled:
            self.view.vtkWidget().removeEventFilter(filterObj)
            self._filterInstalled = False

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            self.clear()
            if self.abortFunc is not None:
                self.abortFunc()
            return False

        if event.modifiers() != QtCore.Qt.ShiftModifier:
            if self.annotationObj:
                self.annotationObj.setProperty("Visible", False)
            return False

        if self.annotationObj:
            self.annotationObj.setProperty("Visible", True)

        if event.type() == QtCore.QEvent.MouseMove:
            self.onMouseMove(vis.mapMousePosition(watched, event), event.modifiers())
        elif event.type() == QtCore.QEvent.MouseButtonPress:
            self.onMousePress(vis.mapMousePosition(watched, event), event.modifiers())

        return False

    def clear(self):
        if self.annotationObj:
            self.annotationObj.setProperty("Visible", False)
        self.annotationObj = None
        self.points = [None for i in range(self.numberOfPoints)]
        self.hoverPos = None
        self.lastMovePos = [0, 0]

    def onMouseMove(self, displayPoint, modifiers=None):
        self.lastMovePos = displayPoint
        self.tick()

    def onMousePress(self, displayPoint, modifiers=None):
        for i in range(self.numberOfPoints):
            if self.points[i] is None:
                self.points[i] = self.hoverPos
                break

        if self.points[-1] is not None:
            self.finish()

    def finish(self):
        points = [p.copy() for p in self.points]
        if self.annotationFunc is not None:
            self.annotationFunc(*points)

        self.clear()

    def draw(self):
        d = DebugData()

        points = [p if p is not None else self.hoverPos for p in self.points]

        # draw points
        for p in points:
            if p is not None:
                d.addSphere(p, radius=0.008)

        if self.drawLines:
            # draw lines
            for a, b in zip(points, points[1:]):
                if b is not None:
                    d.addLine(a, b)

            # connect end points
            if points[-1] is not None and self.drawClosedLoop:
                d.addLine(points[0], points[-1])

        self.annotationObj = vis.updatePolyData(
            d.getPolyData(), self.annotationName, parent=self.annotationFolder, view=self.view
        )
        self.annotationObj.setProperty("Color", [1, 0, 0])
        self.annotationObj.actor.SetPickable(False)

    def tick(self):
        if self.obj is None:
            pickedPointFields = vis.pickPoint(
                self.lastMovePos, self.view, pickType=self.pickType, tolerance=self.tolerance
            )
            self.hoverPos = pickedPointFields.pickedPoint
            prop = pickedPointFields.pickedProp
            if prop is None:
                self.hoverPos = None
        else:
            pickedPointFields = vis.pickPoint(
                self.lastMovePos, self.view, obj=self.obj, pickType=self.pickType, tolerance=self.tolerance
            )
            self.hoverPos = pickedPointFields.pickedPoint

        self.draw()


class ImagePointPicker(QtCore.QObject):
    DOUBLE_CLICK_EVENT = "DOUBLE_CLICK_EVENT"

    def __init__(self, imageView, obj=None, callback=None, numberOfPoints=1, drawLines=True):
        super().__init__()
        self.imageView = imageView
        self.view = imageView.view
        self.obj = obj
        self.drawLines = drawLines
        self.annotationObj = None
        self.annotationFunc = callback
        self._filterInstalled = False
        self.numberOfPoints = numberOfPoints
        self.showCursor = False
        self.cursorObj = None
        self.callbacks = callbacks.CallbackRegistry([self.DOUBLE_CLICK_EVENT])
        self.clear()

    def start(self):
        self.installEventFilter(self)
        self.clear()

    def stop(self):
        self.removeEventFilter(self)

    def installEventFilter(self, filterObj):
        if not self._filterInstalled:
            self.view.vtkWidget().installEventFilter(filterObj)
            self._filterInstalled = True

    def removeEventFilter(self, filterObj):
        if self._filterInstalled:
            self.view.vtkWidget().removeEventFilter(filterObj)
            self._filterInstalled = False

    def connectDoubleClickEvent(self, func):
        return self.callbacks.connect(self.DOUBLE_CLICK_EVENT, func)

    def disconnectDoubleClickEvent(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.MouseButtonDblClick and event.button() == QtCore.Qt.LeftButton:
            self.callbacks.process(
                self.DOUBLE_CLICK_EVENT, vis.mapMousePosition(watched, event), event.modifiers(), self.imageView
            )

        if event.type() in (QtCore.QEvent.MouseMove, QtCore.QEvent.MouseButtonPress, QtCore.QEvent.Wheel):
            if self.showCursor:
                self.updateCursor(vis.mapMousePosition(watched, event))
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Shift:
                self.showCursor = True

        elif event.type() == QtCore.QEvent.KeyRelease:
            if event.key() == QtCore.Qt.Key_Shift:
                self.showCursor = False
                self.hideCursor()

        if hasattr(event, "modifiers") and event.modifiers() != QtCore.Qt.ShiftModifier:
            self.showCursor = False
            if self.annotationObj:
                self.hoverPos = None
                self.draw()
                self.annotationObj.setProperty("Color", [1, 0, 0])
                self.clear()
            return False

        if self.annotationObj:
            self.annotationObj.setProperty("Visible", True)

        if event.type() == QtCore.QEvent.MouseMove:
            self.onMouseMove(vis.mapMousePosition(watched, event), event.modifiers())

        elif event.type() == QtCore.QEvent.MouseButtonPress:
            self.onMousePress(vis.mapMousePosition(watched, event), event.modifiers())

        return False

    def clear(self):
        if self.annotationObj:
            self.annotationObj.setProperty("Visible", False)
        self.annotationObj = None
        self.points = []
        self.hoverPos = None
        self.lastMovePos = [0, 0]

    def onMouseMove(self, displayPoint, modifiers=None):
        self.lastMovePos = displayPoint
        self.hoverPos = self.displayPointToImagePoint(self.lastMovePos)
        self.draw()

    def onMousePress(self, displayPoint, modifiers=None):
        point = self.displayPointToImagePoint(displayPoint)
        if point is None:
            return

        self.points.append(point)

        if len(self.points) == self.numberOfPoints:
            self.finish()

    def finish(self):
        points = [np.array(p) for p in self.points]
        self.clear()
        if self.annotationFunc is not None:
            self.annotationFunc(*points)

    def draw(self):
        d = DebugData()

        points = list(self.points)
        if self.hoverPos is not None:
            points.append(self.hoverPos)

        # draw points
        radius = 5
        scale = (2 * self.view.camera().GetParallelScale()) / (self.view.renderer().GetSize()[1])
        for p in points:
            d.addSphere(p, radius=radius * scale)

        if self.drawLines and len(points) > 1:
            for a, b in zip(points, points[1:]):
                d.addLine(a, b)

            # connect end points
            # d.addLine(points[0], points[-1])

        if self.annotationObj:
            self.annotationObj.setPolyData(d.getPolyData())
        else:
            self.annotationObj = vis.updatePolyData(
                d.getPolyData(), "annotation", parent="segmentation", color=[1, 0, 0], view=self.view
            )
            self.annotationObj.addToView(self.view)
            self.annotationObj.actor.SetPickable(False)
            self.annotationObj.actor.GetProperty().SetLineWidth(2)

    def hideCursor(self):
        if self.cursorObj:
            om.removeFromObjectModel(self.cursorObj)

    def updateCursor(self, displayPoint):
        center = self.displayPointToImagePoint(displayPoint, restrictToImageDimensions=False)
        center = np.array(center)

        d = DebugData()
        d.addLine(center + [0, -3000, 0], center + [0, 3000, 0])
        d.addLine(center + [-3000, 0, 0], center + [3000, 0, 0])
        self.cursorObj = vis.updatePolyData(d.getPolyData(), "cursor", alpha=0.5, view=self.view)
        self.cursorObj.addToView(self.view)
        self.cursorObj.actor.SetUseBounds(False)
        self.cursorObj.actor.SetPickable(False)
        self.view.render()

    def displayPointToImagePoint(self, displayPoint, restrictToImageDimensions=True):
        point = self.imageView.getImagePixel(displayPoint, restrictToImageDimensions)
        if point is not None:
            point[2] = np.sign(self.view.camera().GetPosition()[2])
            return point


class PlacerWidget(QtCore.QObject):
    def __init__(self, view, handle, points):
        super().__init__()
        assert handle.actor
        assert handle.actor.GetUserTransform()

        self.view = view
        self.handle = handle
        self.points = points
        self.moving = False
        self._filterInstalled = False
        self._consumeEvent = False

    def start(self):
        self.installEventFilter(self)

    def stop(self):
        self.removeEventFilter(self)

    def installEventFilter(self, filterObj):
        if not self._filterInstalled:
            self.view.vtkWidget().installEventFilter(filterObj)
            self._filterInstalled = True

    def removeEventFilter(self, filterObj):
        if self._filterInstalled:
            self.view.vtkWidget().removeEventFilter(filterObj)
            self._filterInstalled = False

    def eventFilter(self, watched, event):
        self._consumeEvent = False

        if event.type() == QtCore.QEvent.MouseMove:
            self.onMouseMove(vis.mapMousePosition(watched, event), event.modifiers())
        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            self.onMousePress(vis.mapMousePosition(watched, event), event.modifiers())
        elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
            self.onMouseRelease(vis.mapMousePosition(watched, event), event.modifiers())

        return self._consumeEvent

    def onMouseMove(self, displayPoint, modifiers=None):
        self.updateHighlight(displayPoint)

        if not self.moving:
            return

        self._consumeEvent = True

        pickPoint = self.getPointPick(displayPoint)

        if pickPoint is not None:
            t = self.handle.actor.GetUserTransform()
            assert t
            currentPos = np.array(t.GetPosition())
            t.Translate(np.array(pickPoint - currentPos))
            t.Modified()
            self.handle._renderAllViews()

    def onMousePress(self, displayPoint, modifiers=None):
        picked = self.getHandlePick(displayPoint)
        if picked is not None:
            self.moving = True
            self._consumeEvent = True

    def onMouseRelease(self, displayPoint, modifiers=None):
        if self.moving:
            self._consumeEvent = True
            self.moving = False

    def updateHighlight(self, displayPoint):
        if self.getHandlePick(displayPoint) is not None:
            self.handle.actor.GetProperty().SetAmbient(0.5)
            self.handle._renderAllViews()
        else:
            self.handle.actor.GetProperty().SetAmbient(0.0)
            self.handle._renderAllViews()

    def getHandlePick(self, displayPoint):
        pickData = vis.pickPoint(displayPoint, self.view, obj=self.handle, pickType="cells", tolerance=0.01)
        return pickData.pickedPoint

    def getPointPick(self, displayPoint):
        pickData = vis.pickPoint(displayPoint, self.view, obj=self.points, pickType="cells", tolerance=0.01)
        return pickData.pickedPoint


class ObjectPicker(QtCore.QObject):
    def __init__(
        self,
        view,
        callback=None,
        abortCallback=None,
        numberOfObjects=1,
        getObjectsFunction=None,
        hoverColor=[1.0, 0.8, 0.8, 1.0],
    ):
        super().__init__()
        self.view = view
        self.tolerance = 0.01
        self.numberOfObjects = numberOfObjects
        self.getObjectsFunction = getObjectsFunction
        self.callbackFunc = callback
        self.abortFunc = abortCallback
        self.hoverColor = hoverColor[0:3]
        self.hoverAlpha = hoverColor[3]
        self.modifier = 0
        self.mouseSelectionEventType = QtCore.QEvent.MouseButtonPress
        self._filterInstalled = False
        self.pickedObj = None
        self.storedProps = {}
        self.repeat = False
        self.clear()

    def start(self):
        self.installEventFilter(self)
        self.clear()

    def stop(self):
        self.removeEventFilter(self)

    def installEventFilter(self, filterObj):
        if not self._filterInstalled:
            self.view.vtkWidget().installEventFilter(filterObj)
            self._filterInstalled = True

    def removeEventFilter(self, filterObj):
        if self._filterInstalled:
            self.view.vtkWidget().removeEventFilter(filterObj)
            self._filterInstalled = False

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            self.clear()
            if self.abortFunc is not None:
                self.abortFunc()
            return False

        if event.type() == QtCore.QEvent.MouseMove:
            self.onMouseMove(vis.mapMousePosition(watched, event), event.modifiers())
        elif event.type() == self.mouseSelectionEventType and event.button() == QtCore.Qt.LeftButton:
            self.onMousePress(vis.mapMousePosition(watched, event), event.modifiers())

        return False

    def clear(self):
        self.objects = [None for i in range(self.numberOfObjects)]
        self.hoverPos = None
        self.lastMovePos = [0, 0]
        self.unsetHoverProperties(self.pickedObj)
        self.pickedObj = None

    def onMouseMove(self, displayPoint, modifiers=None):
        self.lastMovePos = displayPoint
        if modifiers == self.modifier:
            self.tick()
        else:
            self.unsetHoverProperties(self.pickedObj)

    def onMousePress(self, displayPoint, modifiers=None):
        if modifiers != self.modifier:
            return

        for i in range(self.numberOfObjects):
            if self.objects[i] is None:
                self.objects[i] = self.pickedObj
                break

        if self.objects[-1] is not None:
            self.finish()

    def finish(self):
        if self.callbackFunc is not None:
            try:
                self.callbackFunc(self.objects)
            finally:
                self.clear()
                if not self.repeat:
                    self.stop()

    def unsetHoverProperties(self, obj):
        if obj is None:
            return

        for propName, value in list(self.storedProps.items()):
            if obj.hasProperty(propName):
                obj.setProperty(propName, value)
        self.storedProps = {}

    def setHoverProperties(self, obj):
        if obj is None:
            return

        for propName, value in [["Color", self.hoverColor], ["Color By", "Solid Color"], ["Alpha", self.hoverAlpha]]:
            if obj.hasProperty(propName):
                self.storedProps[propName] = obj.getProperty(propName)
                obj.setProperty(propName, value)

    def tick(self):
        objs = self.getObjectsFunction() if self.getObjectsFunction else None

        pickedPointFields = vis.pickPoint(
            self.lastMovePos, self.view, pickType="cells", tolerance=self.tolerance, obj=objs
        )
        self.hoverPos = pickedPointFields.pickedPoint
        prop = pickedPointFields.pickedProp

        prevPickedObj = self.pickedObj
        curPickedObj = vis.getObjectByProp(prop)

        if curPickedObj is not prevPickedObj:
            self.unsetHoverProperties(prevPickedObj)
            self.setHoverProperties(curPickedObj)
            self.pickedObj = curPickedObj
