import numpy as np
import PythonQt
from PythonQt import QtCore, QtGui
from director import transformUtils
from director.timercallback import TimerCallback


def getCameraTransform(camera):
    return transformUtils.getLookAtTransform(
        camera.GetFocalPoint(),
        camera.GetPosition(),
        camera.GetViewUp())


def setCameraTransform(camera, transform):
    origin = np.array(transform.GetPosition())
    axes = transformUtils.getAxesFromTransform(transform)
    camera.SetFocalPoint(origin+axes[0])
    camera.SetPosition(origin)
    camera.SetViewUp(axes[2])


class KeyPressState:

    _globalInstance = None

    @classmethod
    def get(cls, key):
        if cls._globalInstance is None:
            cls._globalInstance = KeyPressState()
        return cls._globalInstance._getKeyState(key)

    def __init__(self):
        self.keyState = {}
        self._installEventFilter(QtGui.QApplication.instance())

    def _getKeyState(self, key):
        return self.keyState.get(key, False)

    def _installEventFilter(self, qobj):
        self.eventFilter = PythonQt.dd.ddPythonEventFilter()
        self.eventFilter.connect('handleEvent(QObject*, QEvent*)', self._filterEvent)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.KeyPress)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.KeyRelease)
        qobj.installEventFilter(self.eventFilter)

    def _filterEvent(self, obj, event):
        if event.isAutoRepeat():
            return
        elif event.type() == QtCore.QEvent.KeyPress:
            self.keyState[event.key()] = True
        elif event.type() == QtCore.QEvent.KeyRelease:
            self.keyState[event.key()] = False


class MouseLook:
    def __init__(self, view):

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

    def toggle(self):
        self.setEnabled(not self.enabled)

    def setEnabled(self, enabled):
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
        QtGui.QApplication.restoreOverrideCursor()

    def hideMouse(self):
        c = QtGui.QCursor(QtCore.Qt.BlankCursor)
        QtGui.QApplication.setOverrideCursor(c)

    def onDelta(self, delta, vel):

        alpha = self.alpha

        vel = alpha*self.lastVel + (1-alpha)*vel
        self.lastVel = vel

        delta = alpha*self.lastDelta + (1-alpha)*delta
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
            vel *= 1/velNorm
        vel *= dt * self.velScale

        self.onDelta(np.array([self.delta.x()*dt, self.delta.y()*dt], dtype=float), vel)




if __name__ == '__main__':

    import director.visualization as vis
    from director import applogic
    from director.debugVis import DebugData

    def addSphere(nspheres=100, maxDistance=20.0):
        d = DebugData()
        for i in range(nspheres):
            pos = (np.array([-0.5, -0.5, -0.5]) + np.random.random(3)) * 20.0
            radius = 0.2 + 1.0 * np.random.random()
            d.addSphere(pos, radius)
        vis.showPolyData(d.getPolyData(), 'spheres')

    addSpheres(200, 100.0)

    m = MouseLook(fields.view)
    applogic.addShortcut(fields.mainWindow, 'F2', m.toggle)
    fields.gridObj.setProperty('Show Text', False)
