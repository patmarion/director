"""Hello World example demonstrating VTK embedded in Qt using qtpy."""

import sys
import vtk
from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from qtpy.QtCore import Qt

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class VTKWidget(QWidget):
    """A Qt widget that contains a VTK render window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create VTK renderer, render window, and interactor
        self.renderer = vtk.vtkRenderer()
        self.vtk_widget = QVTKRenderWindowInteractor(self)         
        self.render_window = self.vtk_widget.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        self.interactor = self.render_window.GetInteractor()
        
        # Create a simple VTK scene - a sphere
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetRadius(1.0)
        sphere_source.SetThetaResolution(50)
        sphere_source.SetPhiResolution(50)
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere_source.GetOutputPort())
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.7, 0.3, 0.3)  # Reddish color
        
        self.renderer.AddActor(actor)
        self.renderer.SetBackground(0.2, 0.2, 0.3)  # Dark blue background
        self.renderer.ResetCamera()

        self.interactor.Initialize()
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.vtk_widget)
    


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Director 2.0 - Hello World")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget with VTK
        self.vtk_widget = VTKWidget(self)
        self.setCentralWidget(self.vtk_widget)


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Director 2.0")
    app.setApplicationVersion("2.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

