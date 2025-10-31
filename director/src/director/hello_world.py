"""Hello World example demonstrating VTK embedded in Qt using qtpy."""

import sys
import vtk
from qtpy.QtWidgets import QApplication, QMainWindow, QDockWidget, QTreeWidget
from qtpy.QtCore import Qt

from director.vtk_widget import VTKWidget
from director.objectmodel import ObjectModelTree, ObjectModelItem


class DummyPropertiesPanel:
    """Dummy properties panel for hello world example."""
    
    def clear(self):
        """Clear the panel."""
        pass
    
    def setBrowserModeToWidget(self):
        """Set browser mode to widget."""
        pass



class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Director 2.0 - Hello World")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget with VTK
        self.vtk_widget = VTKWidget(self)
        self.setCentralWidget(self.vtk_widget)
        
        # Create object model dock widget
        self._setup_object_model()
        
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
        self.vtk_widget.renderer().AddActor(actor)
        
        # Reset camera to fit the scene
        self.vtk_widget.resetCamera()
    
    def _setup_object_model(self):
        """Setup the object model as a dock widget."""
        # Create dock widget for object model
        dock = QDockWidget("Object Model", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create tree widget
        tree_widget = QTreeWidget()
        
        # Create object model tree and initialize it
        self.object_model = ObjectModelTree()
        properties_panel = DummyPropertiesPanel()
        self.object_model.init(tree_widget, properties_panel)
        
        # Add test object to the object model
        test_obj = ObjectModelItem("test obj")
        self.object_model.addToObjectModel(test_obj)
        
        # Set tree widget as the dock widget's widget
        dock.setWidget(tree_widget)
        
        # Add dock widget to the left side
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)


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

