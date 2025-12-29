"""Mouse-look camera control for FPS-style navigation."""

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets

from director import transformUtils
from director.timercallback import TimerCallback


def getCameraTransform(camera):
    """Get transform representing camera position and orientation."""
    return transformUtils.getLookAtTransform(camera.GetFocalPoint(), camera.GetPosition(), camera.GetViewUp())


def setCameraTransform(camera, transform):
    """Set camera transform so that view direction is +X and view up is Z."""
    origin = np.array(transform.GetPosition())
    axes = transformUtils.getAxesFromTransform(transform)
    camera.SetFocalPoint(origin + axes[0])
    camera.SetPosition(origin)
    camera.SetViewUp(axes[2])


class KeyPressState:
    """Tracks global key press state for arrow key navigation."""

    _globalInstance = None

    @classmethod
    def get(cls, key):
        """Get the current state of a key.

        Args:
            key: Qt key code (e.g., QtCore.Qt.Key_Left)

        Returns:
            True if key is pressed, False otherwise
        """
        if cls._globalInstance is None:
            cls._globalInstance = KeyPressState()
        return cls._globalInstance._getKeyState(key)

    def __init__(self):
        self.keyState = {}
        self._installEventFilter(QtWidgets.QApplication.instance())

    def _getKeyState(self, key):
        return self.keyState.get(key, False)

    def _installEventFilter(self, qobj):
        self.eventFilter = KeyPressEventFilter(self)
        qobj.installEventFilter(self.eventFilter)

    def _onKeyPress(self, key):
        self.keyState[key] = True

    def _onKeyRelease(self, key):
        self.keyState[key] = False


class KeyPressEventFilter(QtCore.QObject):
    """Event filter for tracking key press state."""

    def __init__(self, keyPressState):
        super().__init__()
        self.keyPressState = keyPressState

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if not event.isAutoRepeat():
                self.keyPressState._onKeyPress(event.key())
        elif event.type() == QtCore.QEvent.KeyRelease:
            if not event.isAutoRepeat():
                self.keyPressState._onKeyRelease(event.key())
        return False


class MouseLook:
    """FPS-style mouse-look camera control.

    When enabled, the mouse controls camera rotation and arrow keys control movement.
    """

    def __init__(self, view):
        """Initialize MouseLook.

        Args:
            view: VTKWidget view instance
        """
        self.enabled = False
        self.view = view
        self.camRPY = np.array([0.0, 0.0, 0.0])
        self.camPos = np.array([-20.0, 0.0, 4.0])

        self.yawScale = -10.0
        self.pitchScale = 10.0
        self.velScale = 50.0
        self.lastDelta = np.zeros(2)
        self.lastVel = np.zeros(3)
        self.alpha = 0.93

        self.forceRender = True
        self.requestRender = False

        self.warpMouse = True
        self.warpPos = (500, 500)
        if self.warpMouse:
            QtGui.QCursor.setPos(*self.warpPos)
        self.mousePos = QtGui.QCursor.pos()
        self.timer = TimerCallback(targetFps=60, callback=self._onTimer)
        self.delta = QtCore.QPoint(0, 0)

    def toggle(self):
        """Toggle mouse-look mode on/off."""
        self.setEnabled(not self.enabled)

    def setEnabled(self, enabled):
        """Enable or disable mouse-look mode.

        Args:
            enabled: True to enable, False to disable
        """
        if enabled == self.enabled:
            return
        self.enabled = enabled
        if enabled:
            t = getCameraTransform(self.view.camera())
            self.camRPY = np.degrees(transformUtils.rollPitchYawFromTransform(t))
            self.camPos = np.array(t.GetPosition())
            self.hideMouse()
            self.warpMouse = True
            self.timer.start()
        else:
            self.restoreMouse()
            self.warpMouse = False
            self.timer.stop()

    def restoreMouse(self):
        """Restore normal mouse cursor."""
        QtWidgets.QApplication.restoreOverrideCursor()

    def hideMouse(self):
        """Hide the mouse cursor."""
        c = QtGui.QCursor(QtCore.Qt.BlankCursor)
        QtWidgets.QApplication.setOverrideCursor(c)

    def onDelta(self, delta, vel):
        """Process mouse and velocity delta.

        Args:
            delta: Mouse movement delta (x, y)
            vel: Velocity vector (x, y, z)
        """
        alpha = self.alpha

        vel = alpha * self.lastVel + (1 - alpha) * vel
        self.lastVel = vel

        delta = alpha * self.lastDelta + (1 - alpha) * delta
        self.lastDelta = delta

        self.camRPY[1] += delta[1] * self.pitchScale
        self.camRPY[2] += delta[0] * self.yawScale

        t = getCameraTransform(self.view.camera())
        _, _, yaw = transformUtils.rollPitchYawFromTransform(t)
        t = transformUtils.frameFromPositionAndRPY([0.0, 0.0, 0.0], [0.0, 0.0, np.degrees(yaw)])
        posDelta = t.TransformVector(vel)

        self.camPos += np.array(posDelta)

        cameraToWorld = transformUtils.frameFromPositionAndRPY(self.camPos, self.camRPY)
        setCameraTransform(self.view.camera(), cameraToWorld)
        if self.forceRender:
            self.view.forceRender()
        elif self.requestRender:
            self.view.render()

    def _onTimer(self):
        """Timer callback for processing mouse-look."""
        newPos = QtGui.QCursor.pos()
        self.delta = newPos - self.mousePos
        self.mousePos = newPos
        if self.warpMouse:
            QtGui.QCursor.setPos(*self.warpPos)
            self.mousePos = QtGui.QCursor.pos()

        leftPress = KeyPressState.get(QtCore.Qt.Key_Left)
        rightPress = KeyPressState.get(QtCore.Qt.Key_Right)
        upPress = KeyPressState.get(QtCore.Qt.Key_Up)
        downPress = KeyPressState.get(QtCore.Qt.Key_Down)

        vel = [0.0, 0.0, 0.0]

        if leftPress:
            vel[1] += 1.0
        if rightPress:
            vel[1] -= 1.0
        if upPress:
            vel[0] += 1.0
        if downPress:
            vel[0] -= 1.0

        dt = self.timer.elapsed
        vel = np.array(vel)
        velNorm = np.linalg.norm(vel)
        if velNorm > 0.0:
            vel *= 1 / velNorm
        vel *= dt * self.velScale

        self.onDelta(np.array([self.delta.x() * dt, self.delta.y() * dt], dtype=float), vel)
