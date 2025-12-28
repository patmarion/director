"""Test program for FrameItem with frame widget integration."""

import sys

from qtpy.QtWidgets import QPushButton

from director import mainwindowapp
from director import visualization as vis
from director import vtkAll as vtk


def main():
    fields = mainwindowapp.construct()

    undo_stack = fields.undoStack

    t = vtk.vtkTransform()
    obj = vis.showFrame(t, "parent frame", parent="Frame Demo")
    obj.properties.edit = True
    obj.addFrameProperties(undo_stack=undo_stack)

    sync = obj.getFrameSync()

    t2 = vtk.vtkTransform()
    t2.Translate(0.5, -1.0, 0.0)
    t2.RotateY(20)
    t2.RotateZ(45)
    child = vis.showFrame(t2, "child frame", parent="Frame Demo")
    child.properties.edit = True
    child.addFrameProperties(undo_stack=undo_stack)
    sync.addFrame(child, ignoreIncoming=True)

    def reset_frame():
        obj.copyFrame(vtk.vtkTransform())

    button = QPushButton("Reset Frame")
    fields.mainToolbar.addWidget(button)
    button.clicked.connect(reset_frame)

    fields.undoDock.show()

    # Run the application
    return fields.app.start()


if __name__ == "__main__":
    sys.exit(main())
