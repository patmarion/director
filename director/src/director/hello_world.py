"""Hello World example demonstrating VTK embedded in Qt using qtpy."""

import sys
import signal
import vtk
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer

from director.mainwindow import MainWindow, _setup_signal_handlers
from director.objectmodel import ObjectModelItem


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Director 2.0")
    app.setApplicationVersion("2.0.0")
    
    # Setup signal handlers for Ctrl+C
    _setup_signal_handlers(app)
    
    # Create and show main window
    window = MainWindow(window_title="Director 2.0 - Hello World")
    
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
    
    # Add actor to the renderer using the VTKWidget API
    window.vtk_widget.renderer().AddActor(actor)
    
    # Add test object to the object model
    test_obj = ObjectModelItem("test obj")
    window.object_model.addToObjectModel(test_obj)
    
    # Reset camera to fit the scene
    window.vtk_widget.resetCamera()
    
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

