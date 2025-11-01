"""Interactive test for FrameWidget."""

import sys
import vtk
from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from qtpy.QtCore import Qt

from director.vtk_widget import VTKWidget
from director.framewidget import FrameWidget


class TestWindow(QMainWindow):
    """Test window for FrameWidget."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Widget Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Instructions label
        instructions = QLabel("""
        <h3>Frame Widget Test</h3>
        <p><b>Instructions:</b></p>
        <ul>
        <li><b>Left-click + drag on axis:</b> Translate along axis</li>
        <li><b>Right-click + drag on axis:</b> Rotate about axis</li>
        <li><b>Left-click + drag on ring:</b> Translate in plane</li>
        <li><b>Right-click + drag on ring:</b> Rotate about plane normal</li>
        <li><b>Hover:</b> Colors brighten to show what you can interact with</li>
        </ul>
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create VTK widget
        self.vtk_widget = VTKWidget()
        layout.addWidget(self.vtk_widget)
        
        # Add a reference sphere to visualize the frame
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetRadius(0.3)
        sphere_source.SetThetaResolution(50)
        sphere_source.SetPhiResolution(50)
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere_source.GetOutputPort())
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.7, 0.7, 0.7)
        
        self.vtk_widget.renderer().AddActor(actor)
        
        # Create a transform for the frame
        frame_transform = vtk.vtkTransform()
        frame_transform.PostMultiply()
        frame_transform.Translate(0, 0, 0)  # Start at origin
        
        # Create frame widget
        self.frame_widget = FrameWidget(
            self.vtk_widget,
            frame_transform,
            scale=0.5,
            useTubeFilter=True,
            useDiskRings=False  # Set to True for flat disks
        )
        
        # Reset camera
        self.vtk_widget.resetCamera()
        self.vtk_widget.render()
        
        # Connect transform modified event to update display
        frame_transform.AddObserver('ModifiedEvent', self._onTransformModified)
    
    def _onTransformModified(self, obj, event):
        """Callback when transform is modified."""
        self.vtk_widget.render()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

