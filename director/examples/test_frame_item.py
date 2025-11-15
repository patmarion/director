"""Test program for FrameItem with frame widget integration."""

import sys
from qtpy.QtWidgets import QPushButton

from director import mainwindowapp
from director import visualization as vis
from director import vtkAll as vtk
from director.frame_properties import FrameProperties, FrameSync


def main():
    fields = mainwindowapp.construct()
    
    t = vtk.vtkTransform()
    t.RotateZ(45)
    t.RotateX(45)
    obj = vis.showFrame(t, "frame widget")
    obj.properties.edit = True
    undo_stack = getattr(fields, "undoStack", None)
    obj.frameProperties = FrameProperties(obj, undo_stack=undo_stack)

    sync = FrameSync()
    sync.addFrame(obj)

    def add_frame_sync():
        t2 = vtk.vtkTransform()
        t2.Translate(0.3, 0.3, 0.0)
        t2.RotateY(20)
        child = vis.showFrame(t2, "synced frame", parent='data')
        child.properties.edit = True
        undo_stack = getattr(fields, "undoStack", None)
        child.frameProperties = FrameProperties(child, undo_stack=undo_stack)
        sync.addFrame(child)
        return child

    add_frame_sync()

    def reset_frame():
        obj.copyFrame(vtk.vtkTransform())
    
    button = QPushButton("Reset Frame")
    fields.mainToolbar.addWidget(button)
    button.clicked.connect(reset_frame)

    # Make undo history visible to demonstrate frame edits in the stack
    if hasattr(fields, "undoDock"):
        fields.undoDock.show()

    # Run the application
    return fields.app.start()


if __name__ == "__main__":
    sys.exit(main())

