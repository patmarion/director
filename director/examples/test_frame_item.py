"""Test program for FrameItem with frame widget integration."""

import sys
from qtpy.QtWidgets import QPushButton

from director import mainwindowapp
from director import visualization as vis
from director import objectmodel as om
from director import vtkAll as vtk




def main():
    fields = mainwindowapp.construct()
    
    t = vtk.vtkTransform()
    t.RotateX(90)
    obj = vis.showFrame(t, "frame widget")
    obj.properties.edit = True

    t.PostMultiply()
    
    def reset_frame():
        obj.copyFrame(vtk.vtkTransform())
    
    button = QPushButton("Reset Frame")
    fields.mainToolbar.addWidget(button)
    button.clicked.connect(reset_frame)
    # Run the application
    return fields.app.start()


if __name__ == "__main__":
    sys.exit(main())

