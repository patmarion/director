import vtk
import time
import math
import numpy as np
from director import transformUtils
from director.timercallback import TimerCallback
from director import objectmodel as om
from director import vieweventfilter
from director import visualization as vis
from director import vtkAll as vtk
from director import cameracontrol
from director.debugVis import DebugData

from PythonQt import QtCore


def getCameraTransform(camera):
    return transformUtils.getLookAtTransform(
              camera.GetFocalPoint(),
              camera.GetPosition(),
              camera.GetViewUp())


def setCameraTransform(camera, transform, distance=1.0):
    '''Set camera transform so that view direction is +X and view up is Z'''
    origin = np.array(transform.GetPosition())
    axes = transformUtils.getAxesFromTransform(transform)
    camera.SetFocalPoint(origin+axes[0]*distance)
    camera.SetPosition(origin)
    camera.SetViewUp(axes[2])


def copyCamera(camera):
    newCamera = vtk.vtkCamera()
    newCamera.DeepCopy(camera)
    return newCamera


def BackEaseOut(p):
    f = (1 - p)
    return 1 - (f * f * f - f * math.sin(f * math.pi))


class CameraInterpolator(object):

    def __init__(self, view):
        self.timer = TimerCallback(callback=self.tick)
        self.view = view
        self.flyTime = 0.3
        self.startTime = 0.0
        self.cameras = []

    def push(self, camera=None):
        camera = camera or self.view.camera()
        self.cameras.append(copyCamera(camera))

    def fly(self):
        assert len(self.cameras) > 1
        self.pose1 = getCameraTransform(self.cameras[0])
        self.pose2 = getCameraTransform(self.cameras[-1])
        self.startTime = time.time()
        self.timer.start()

    def tick(self):

        elapsed = time.time() - self.startTime
        t = (elapsed / float(self.flyTime)) if self.flyTime > 0 else 1.0
        t = min(t, 1.0)
        t0 = t

        #t = t* t * (3.0 - 2.0 * t)
        #t = t*t*t * (t * (6.0*t - 15.0) + 10.0)
        t = BackEaseOut(t)

        result = transformUtils.frameInterpolate(self.pose1, self.pose2, t)
        setCameraTransform(view.camera(), result)
        self.view.render()

        if t >= 1.0:
            return False



def QuinticEaseInOut(p):
    if (p < 0.5):
        return 16 * p * p * p * p * p
    else:
        f = ((2 * p) - 2)
    return 0.5 * f * f * f * f * f + 1


def QuinticEaseOut(p):
    f = (p - 1)
    return f * f * f * f * f + 1


def QuarticEaseOut(p):
    f = (p - 1)
    return f * f * f * (1 - p) + 1


def CubicEaseOut(p):
    f = (p - 1)
    return f * f * f + 1


def QuadraticEaseOut(p):
    return -(p * (p - 2))



class VectorInterpolator():

    def __init__(self, startValue, targetValue, callback):
        self.timer = TimerCallback(targetFps=60, callback=self.tick)
        self.currentValue = np.array(startValue)
        self.targetValue = np.array(targetValue)
        self.smoothTime = 0.2
        self.maxSpeed = 1000.0
        self.currentVelocity = np.zeros(len(startValue))
        self.callback = callback

    def start(self):
        self.timer.start()

    def tick(self):

        elapsed = self.timer.elapsed

        self.currentValue, self.currentVelocity = cameracontrol.smoothDamp(self.currentValue, self.targetValue, self.currentVelocity, self.smoothTime, maxSpeed=self.maxSpeed, deltaTime=elapsed)

        result = True
        if np.linalg.norm(self.currentValue - self.targetValue) < 1e-3:
            self.currentValue = np.array(self.targetValue)
            result = False

        self.callback(self.currentValue)
        return result



class MyCameraInteractor(vieweventfilter.ViewEventFilter):

    def __init__(self, view):
        vieweventfilter.ViewEventFilter.__init__(self, view)
        self.interp = VectorInterpolator(np.zeros(4), np.zeros(0), None)
        self.zoom = 0.0
        self.groundFrame = vtk.vtkTransform()

    def getIntersectionPoint(self, event):
        displayPoint = self.getMousePositionInView(event)
        worldPt1, worldPt2 = vis.getRayFromDisplayPoint(self.view, displayPoint)
        planeOrigin = self.groundFrame.GetPosition()
        planeNormal = self.groundFrame.TransformVector([0.0, 0.0, 1.0])
        intersectionPoint = [0.0, 0.0, 0.0]
        t = vtk.mutable(0.0)
        vtk.vtkPlane.IntersectWithLine(worldPt1, worldPt2, planeNormal, planeOrigin, t, intersectionPoint)
        return np.array(intersectionPoint)

    def onMouseMove(self, event):
        intersectionPoint = self.getIntersectionPoint(event)
        planeNormal = [0, 0, 1]

        d = DebugData()
        d.addCircle(intersectionPoint, planeNormal, radius=0.5)
        d.addLine(intersectionPoint, intersectionPoint + 10*np.array(planeNormal))
        vis.updatePolyData(d.getPolyData(), 'hit point', color=[1.0, 0.0, 0.0], visible=False, parent=om.findObjectByName('grid'))

    def onLeftMousePress(self, event):
        if event.modifiers() != QtCore.Qt.ControlModifier:
            return
        intersectionPoint = self.getIntersectionPoint(event)
        self.flyTo(intersectionPoint)

    def flyTo(self, targetPosition):

        focalPoint = np.array(self.view.camera().GetFocalPoint())
        lookVector = focalPoint - self.view.camera().GetPosition()
        length = np.linalg.norm(lookVector)
        lookVector /= length

        def f(newFocal):
            self.view.camera().SetFocalPoint(newFocal[:3])
            self.view.camera().SetPosition(newFocal[:3] - lookVector*newFocal[3])
            self.view.render()

        focalPoint = np.array([*focalPoint, length])
        targetPosition = np.array([*targetPosition, length*(1-self.zoom)])
        self.interp.targetValue = targetPosition
        self.interp.currentValue = focalPoint
        self.interp.callback = f
        self.interp.start()


    def flyTo2(self, targetPosition):

        currentFocal = np.array(self.view.camera().GetFocalPoint())
        delta = targetPosition - currentFocal
        distance = np.linalg.norm(delta)

        flyTime = 0.6

        flyer = cameracontrol.Flyer(self.view)
        flyer.maintainViewDirection = True
        flyer.positionZoom = 0.0
        flyer.interpFunction = lambda t: CubicEaseOut(t)
        flyer.flyTime = flyTime
        flyer.zoomTo(targetPosition)
