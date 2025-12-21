"""Frame updating utilities for frame editing (simplified from original Director)."""

from qtpy.QtCore import Qt
import director.vtkAll as vtk

# Global state for frame editing
lastEditedFrame = None


def registerFrame(frame):
    """Register a frame for editing."""
    global lastEditedFrame
    lastEditedFrame = frame


def applyFrameTransform(x, y, z, yaw):
    """Apply a transform to the currently edited frame."""
    global lastEditedFrame
    if lastEditedFrame is not None and lastEditedFrame.getProperty("Edit"):
        t = vtk.vtkTransform()
        t.Concatenate(lastEditedFrame.transform)
        t.RotateZ(yaw)
        t.Translate(x, y, z)
        lastEditedFrame.copyFrame(t)


def disableFrameEdit():
    """Disable frame editing mode."""
    global lastEditedFrame
    if lastEditedFrame is not None and lastEditedFrame.getProperty("Edit"):
        lastEditedFrame.setProperty("Edit", False)


def shiftFrameX(amount):
    """Shift frame along X axis."""
    applyFrameTransform(amount, 0, 0, 0)


def shiftFrameY(amount):
    """Shift frame along Y axis."""
    applyFrameTransform(0, amount, 0, 0)


def shiftFrameYaw(amount):
    """Rotate frame around Z axis (yaw)."""
    applyFrameTransform(0, 0, 0, amount)


def shiftFrameZ(amount):
    """Shift frame along Z axis."""
    applyFrameTransform(0, 0, amount, 0)


def handleKey(event):
    """Handle keyboard events for frame editing."""
    linearDisplacement = 0.005
    angularDisplacement = 1
    multiplier = 5

    if event.modifiers() & Qt.ControlModifier:
        linearDisplacement *= multiplier
        angularDisplacement *= multiplier

    if event.key() == Qt.Key_Left:
        if event.modifiers() & Qt.ShiftModifier:
            shiftFrameYaw(angularDisplacement)
        else:
            shiftFrameY(-linearDisplacement)
        return True
    elif event.key() == Qt.Key_Right:
        if event.modifiers() & Qt.ShiftModifier:
            shiftFrameYaw(-angularDisplacement)
        else:
            shiftFrameY(linearDisplacement)
        return True
    elif event.key() == Qt.Key_Up:
        if event.modifiers() & Qt.ShiftModifier:
            shiftFrameZ(linearDisplacement)
        else:
            shiftFrameX(linearDisplacement)
        return True
    elif event.key() == Qt.Key_Down:
        if event.modifiers() & Qt.ShiftModifier:
            shiftFrameZ(-linearDisplacement)
        else:
            shiftFrameX(-linearDisplacement)
        return True
    elif event.key() == Qt.Key_Escape:
        disableFrameEdit()
        return True

    return False
