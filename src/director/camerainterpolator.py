"""Camera interpolation utilities for smooth camera transitions."""

import math
import time

import numpy as np
from qtpy import QtCore

import director.vtkAll as vtk
from director import cameracontrol, transformUtils
from director import objectmodel as om
from director import visualization as vis
from director.debugVis import DebugData
from director.timercallback import TimerCallback
from director.vieweventfilter import ViewEventFilter


def getCameraTransform(camera):
    """Get the transform representing the camera's position and orientation.

    Args:
        camera: vtkCamera instance

    Returns:
        vtkTransform representing the camera pose
    """
    return transformUtils.getLookAtTransform(camera.GetFocalPoint(), camera.GetPosition(), camera.GetViewUp())


def setCameraTransform(camera, transform, distance=1.0):
    """Set camera transform so that view direction is +X and view up is Z.

    Args:
        camera: vtkCamera instance
        transform: vtkTransform to apply
        distance: Distance from position to focal point
    """
    origin = np.array(transform.GetPosition())
    axes = transformUtils.getAxesFromTransform(transform)
    camera.SetFocalPoint(origin + axes[0] * distance)
    camera.SetPosition(origin)
    camera.SetViewUp(axes[2])


def copyCamera(camera):
    """Create a deep copy of a camera.

    Args:
        camera: vtkCamera to copy

    Returns:
        New vtkCamera instance
    """
    newCamera = vtk.vtkCamera()
    newCamera.DeepCopy(camera)
    return newCamera


def BackEaseOut(p):
    """Back ease-out easing function."""
    f = 1 - p
    return 1 - (f * f * f - f * math.sin(f * math.pi))


def QuinticEaseInOut(p):
    """Quintic ease-in-out easing function."""
    if p < 0.5:
        return 16 * p * p * p * p * p
    else:
        f = (2 * p) - 2
    return 0.5 * f * f * f * f * f + 1


def QuinticEaseOut(p):
    """Quintic ease-out easing function."""
    f = p - 1
    return f * f * f * f * f + 1


def QuarticEaseOut(p):
    """Quartic ease-out easing function."""
    f = p - 1
    return f * f * f * (1 - p) + 1


def CubicEaseOut(p):
    """Cubic ease-out easing function."""
    f = p - 1
    return f * f * f + 1


def QuadraticEaseOut(p):
    """Quadratic ease-out easing function."""
    return -(p * (p - 2))


class CameraInterpolator:
    """Interpolates camera between saved positions with smooth animation."""

    def __init__(self, view):
        """Initialize CameraInterpolator.

        Args:
            view: VTKWidget view instance
        """
        self.timer = TimerCallback(callback=self.tick)
        self.view = view
        self.flyTime = 0.3
        self.startTime = 0.0
        self.cameras = []
        self.pose1 = None
        self.pose2 = None

    def push(self, camera=None):
        """Push a camera position to the interpolation stack.

        Args:
            camera: Optional camera to push. If None, uses current view camera.
        """
        camera = camera or self.view.camera()
        self.cameras.append(copyCamera(camera))

    def fly(self):
        """Start flying between saved camera positions."""
        assert len(self.cameras) > 1
        self.pose1 = getCameraTransform(self.cameras[0])
        self.pose2 = getCameraTransform(self.cameras[-1])
        self.startTime = time.time()
        self.timer.start()

    def tick(self):
        """Timer callback for animation."""
        elapsed = time.time() - self.startTime
        t = (elapsed / float(self.flyTime)) if self.flyTime > 0 else 1.0
        t = min(t, 1.0)

        t = BackEaseOut(t)

        result = transformUtils.frameInterpolate(self.pose1, self.pose2, t)
        setCameraTransform(self.view.camera(), result)
        self.view.render()

        if t >= 1.0:
            return False


def smoothDamp(current, target, currentVelocity, smoothTime, maxSpeed=float("inf"), deltaTime=None):
    """Smooth damp a value towards a target.

    Args:
        current: Current value (scalar or array)
        target: Target value
        currentVelocity: Current velocity (modified in place)
        smoothTime: Approximate time to reach target
        maxSpeed: Maximum speed
        deltaTime: Time since last call

    Returns:
        Tuple of (new_value, new_velocity)
    """
    if deltaTime is None:
        deltaTime = 1.0 / 60.0

    smoothTime = max(0.0001, smoothTime)
    omega = 2.0 / smoothTime

    x = omega * deltaTime
    exp_factor = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

    change = current - target
    originalTarget = target

    # Clamp maximum speed
    maxChange = maxSpeed * smoothTime
    change = np.clip(change, -maxChange, maxChange)
    target = current - change

    temp = (currentVelocity + omega * change) * deltaTime
    newVelocity = (currentVelocity - omega * temp) * exp_factor
    newValue = target + (change + temp) * exp_factor

    # Prevent overshooting
    if np.all((originalTarget - current) * (newValue - originalTarget) > 0):
        newValue = originalTarget
        newVelocity = (newValue - originalTarget) / deltaTime

    return newValue, newVelocity


class VectorInterpolator:
    """Interpolates a vector value with smooth damping."""

    def __init__(self, startValue, targetValue, callback):
        """Initialize VectorInterpolator.

        Args:
            startValue: Initial value
            targetValue: Target value to interpolate to
            callback: Function to call with new value on each tick
        """
        self.timer = TimerCallback(targetFps=60, callback=self.tick)
        self.currentValue = np.array(startValue)
        self.targetValue = np.array(targetValue)
        self.smoothTime = 0.2
        self.maxSpeed = 1000.0
        self.currentVelocity = np.zeros(len(startValue))
        self.callback = callback

    def start(self):
        """Start the interpolation."""
        self.timer.start()

    def tick(self):
        """Timer callback."""
        elapsed = self.timer.elapsed

        self.currentValue, self.currentVelocity = smoothDamp(
            self.currentValue,
            self.targetValue,
            self.currentVelocity,
            self.smoothTime,
            maxSpeed=self.maxSpeed,
            deltaTime=elapsed,
        )

        result = True
        if np.linalg.norm(self.currentValue - self.targetValue) < 1e-3:
            self.currentValue = np.array(self.targetValue)
            result = False

        self.callback(self.currentValue)
        return result


class CameraInteractor(ViewEventFilter):
    """Camera interactor for click-to-fly navigation."""

    def __init__(self, view):
        """Initialize CameraInteractor.

        Args:
            view: VTKWidget view instance
        """
        super().__init__(view)
        self.interp = VectorInterpolator(np.zeros(4), np.zeros(4), None)
        self.zoom = 0.0
        self.groundFrame = vtk.vtkTransform()

    def getIntersectionPoint(self, event):
        """Get intersection point of mouse ray with ground plane.

        Args:
            event: Qt mouse event

        Returns:
            Intersection point as numpy array
        """
        displayPoint = self.getMousePositionInView(event)
        worldPt1, worldPt2 = vis.getRayFromDisplayPoint(self.view, displayPoint)
        planeOrigin = self.groundFrame.GetPosition()
        planeNormal = self.groundFrame.TransformVector([0.0, 0.0, 1.0])
        intersectionPoint = [0.0, 0.0, 0.0]
        t = vtk.mutable(0.0)
        vtk.vtkPlane.IntersectWithLine(worldPt1, worldPt2, planeNormal, planeOrigin, t, intersectionPoint)
        return np.array(intersectionPoint)

    def onMouseMove(self, event):
        """Handle mouse move events."""
        intersectionPoint = self.getIntersectionPoint(event)
        planeNormal = [0, 0, 1]

        d = DebugData()
        d.addCircle(intersectionPoint, planeNormal, radius=0.5)
        d.addLine(intersectionPoint, intersectionPoint + 10 * np.array(planeNormal))
        vis.updatePolyData(
            d.getPolyData(),
            "hit point",
            color=[1.0, 0.0, 0.0],
            visible=False,
            parent=om.findObjectByName("grid"),
        )
        return False

    def onLeftMousePress(self, event):
        """Handle left mouse press events."""
        if event.modifiers() != QtCore.Qt.ControlModifier:
            return False
        intersectionPoint = self.getIntersectionPoint(event)
        self.flyTo(intersectionPoint)
        return True

    def flyTo(self, targetPosition):
        """Fly the camera to a target position.

        Args:
            targetPosition: Target focal point position
        """
        focalPoint = np.array(self.view.camera().GetFocalPoint())
        lookVector = focalPoint - self.view.camera().GetPosition()
        length = np.linalg.norm(lookVector)
        lookVector /= length

        def f(newFocal):
            self.view.camera().SetFocalPoint(newFocal[:3])
            self.view.camera().SetPosition(newFocal[:3] - lookVector * newFocal[3])
            self.view.render()

        focalPoint = np.array([*focalPoint, length])
        targetPosition = np.array([*targetPosition, length * (1 - self.zoom)])
        self.interp.targetValue = targetPosition
        self.interp.currentValue = focalPoint
        self.interp.callback = f
        self.interp.start()

    def flyTo2(self, targetPosition):
        """Alternative fly-to using Flyer class.

        Args:
            targetPosition: Target focal point position
        """
        flyTime = 0.6

        flyer = cameracontrol.Flyer(self.view)
        flyer.maintainViewDirection = True
        flyer.positionZoom = 0.0
        flyer.flyTime = flyTime
        flyer.zoomTo(targetPosition)
