"""Interactive test application for DebugData and visualization classes.

This demonstrates creating various 3D shapes using DebugData and displaying
them as PolyDataItem objects in the object model."""

import sys
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer

from director.mainwindow import MainWindow, _setup_signal_handlers
from director.debugVis import DebugData
from director import objectmodel as om
from director import visualization as vis
from director import vtkNumpy as vnp
from director import vtkAll as vtk
from director import applogic
from director.vieweventfilter import ViewEventFilter
import numpy as np


class ObjectPickingEventFilter(ViewEventFilter):
    """Event filter for object picking and hover highlighting."""
    
    def __init__(self, view):
        super().__init__(view)
        self.hovered_obj = None
        self.hovered_original_ambient = None
    
    def onLeftClick(self, event):
        """Handle single click to select object."""
        display_point = self.getMousePositionInView(event)
        obj, picked_point = vis.findPickedObject(display_point, self.view)
        
        if obj:
            om.setActiveObject(obj)
            print(f"Selected object: {obj.getProperty('Name')}")
            return False  # Don't consume event - allow camera interaction
        return False
    
    def onMouseMove(self, event):
        """Handle mouse move to highlight hovered objects."""
        display_point = self.getMousePositionInView(event)
        obj, picked_point = vis.findPickedObject(display_point, self.view)
        
        # Remove highlight from previous object
        if self.hovered_obj and self.hovered_obj != obj:
            self._removeHighlight(self.hovered_obj)
            self.hovered_obj = None
            self.hovered_original_ambient = None
        
        # Add highlight to new object
        if obj and self.hovered_obj != obj:
            self._addHighlight(obj)
            self.hovered_obj = obj
        
        # If no object is picked, remove highlight
        if not obj and self.hovered_obj:
            self._removeHighlight(self.hovered_obj)
            self.hovered_obj = None
            self.hovered_original_ambient = None
        
        return False  # Don't consume event - allow camera interaction
    
    def _addHighlight(self, obj):
        """Add highlight to an object by increasing ambient lighting."""
        if not hasattr(obj, 'actor'):
            return
        
        prop = obj.actor.GetProperty()
        if prop:
            # Store original ambient value if not already stored
            if not hasattr(prop, '_originalAmbient'):
                prop._originalAmbient = prop.GetAmbient()
            
            # Increase ambient for "glow" effect
            new_ambient = min(1.0, prop._originalAmbient + 0.4)
            prop.SetAmbient(new_ambient)
            self.view.render()
    
    def _removeHighlight(self, obj):
        """Remove highlight from an object by restoring original ambient lighting."""
        if not hasattr(obj, 'actor'):
            return
        
        prop = obj.actor.GetProperty()
        if prop and hasattr(prop, '_originalAmbient'):
            prop.SetAmbient(prop._originalAmbient)
            self.view.render()


def show(data, offset=[0,0,0], view=None):
    """Helper function to show DebugData with an offset."""
    polyData = data.getPolyData()
    folder = om.getOrCreateContainer('data')
    obj = vis.showPolyData(polyData, 'geometry', colorByName='RGB255', view=view, parent=folder)
    om.collapse(obj)
    t = vtk.vtkTransform()
    t.Translate(offset)
    vis.addChildFrame(obj).copyFrame(t)
    return obj


def getHelixPoints(numberOfPoints=1000):
    """Generate points for a helix curve."""
    theta = np.linspace(0, np.pi*10, numberOfPoints)
    x = theta
    z = np.sin(theta)
    y = np.cos(theta)
    pts = np.vstack((x, y, z)).T.copy()
    pts /= np.max(pts)
    return pts


def main():
    """Main entry point for the debug visualization test."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Director 2.0 - Debug Visualization Test")
    app.setApplicationVersion("2.0.0")
    
    # Setup signal handlers for Ctrl+C
    _setup_signal_handlers(app)
    
    # Create and show main window
    window = MainWindow(window_title="Director 2.0 - Debug Visualization Test")
    
    # Get the view (VTKWidget) for showing objects
    view = window.vtk_widget
    applogic.setCurrentRenderView(view)
    
    # Install object picking and hover highlighting event filter
    picking_filter = ObjectPickingEventFilter(view)
    
    # Create various shapes using DebugData
    # Line
    d = DebugData()
    d.addLine((0,0,0), (1,0,0), radius=0.03)
    show(d, (0, 0, 0), view=view)
    
    # Polygon
    d = DebugData()
    d.addPolygon([[0,0,0], [0.8, 0, 0], [1, 0.6, 0], [0.4, 1, 0], [-0.2, 0.6, 0]])
    show(d, (2, 0, 0), view=view)
    
    # PolyLine (helix)
    d = DebugData()
    d.addPolyLine(getHelixPoints(), radius=0.01)
    show(d, (4, 0, 0), view=view)
    
    # Sphere
    d = DebugData()
    d.addSphere([0, 0, 0], radius=0.3)
    show(d, (6, 0, 0), view=view)
    
    # Frame
    d = DebugData()
    frame_transform = vtk.vtkTransform()
    d.addFrame(frame_transform, scale=0.5, tubeRadius=0.03)
    show(d, (0, 2, 0), view=view)
    
    # Arrow
    d = DebugData()
    d.addArrow((0, 0, 0), (0, 1, 0))
    show(d, (2, 2, 0), view=view)
    
    # Ellipsoid
    d = DebugData()
    d.addEllipsoid((0, 0, 0), radii=(0.5, 0.35, 0.2))
    show(d, (4, 2, 0), view=view)
    
    # Torus
    d = DebugData()
    d.addTorus(radius=0.5, thickness=0.2)
    show(d, (6, 2, 0), view=view)
    
    # Cone
    d = DebugData()
    d.addCone(origin=(0,0,0), normal=(0,1,0), radius=0.3, height=0.8, color=[1, 1, 0])
    show(d, (0, 4, 0), view=view)
    
    # Cube
    d = DebugData()
    d.addCube(dimensions=[0.8, 0.5, 0.3], center=[0, 0, 0], color=[0, 1, 1])
    show(d, (2, 4, 0), view=view)
    
    # Plane
    d = DebugData()
    d.addPlane(origin=[0, 0, 0], normal=[0, 0, 1], width=0.8, height=0.7, resolution=10, color=[0, 1, 0])
    obj = show(d, (4, 4, 0), view=view)
    obj.setProperty('Surface Mode', 'Surface with edges')
    
    # Capsule
    d = DebugData()
    d.addCapsule(center=[0, 0, 0], axis=[1, 0, 0], length=1.0, radius=0.1, color=[0.5, 0.5, 1])
    show(d, (6, 4, 0), view=view)
    
    # Random point cloud
    d = DebugData()
    polyData = vnp.numpyToPolyData(np.random.random((1000, 3)))
    vnp.addNumpyToVtk(polyData, np.arange(polyData.GetNumberOfPoints()), 'point_ids')
    d.addPolyData(polyData)
    obj = show(d, (2.5, 5, 0), view=view)
    obj.setProperty('Color By', 'point_ids')
    
    # Reset camera
    applogic.resetCamera(viewDirection=[0, 0.1, -1], view=view)
    
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

