"""Camera control utilities for smooth camera animations."""

import time
import numpy as np
from director.timercallback import TimerCallback
import director.vtkAll as vtk


class Flyer(TimerCallback):
    """Smooth camera animation to zoom to a focal point."""
    
    def __init__(self, view):
        TimerCallback.__init__(self)
        self.view = view
        self.flyTime = 0.5
        self.startTime = 0.0
        self.maintainViewDirection = False
        self.positionZoom = 0.7
    
    def getCameraCopy(self):
        """Get a deep copy of the current camera."""
        camera = vtk.vtkCamera()
        camera.DeepCopy(self.view.camera())
        return camera
    
    def zoomTo(self, newFocalPoint, newPosition=None):
        """Zoom camera to a new focal point with smooth animation."""
        self.interp = vtk.vtkCameraInterpolator()
        self.interp.AddCamera(0.0, self.getCameraCopy())
        
        c = self.getCameraCopy()
        newFocalPoint = np.array(newFocalPoint)
        oldFocalPoint = np.array(c.GetFocalPoint())
        oldViewUp = np.array(c.GetViewUp())
        oldPosition = np.array(c.GetPosition())
        
        if newPosition is None:
            if self.maintainViewDirection:
                newPosition = oldPosition + (newFocalPoint - oldFocalPoint)
            else:
                newPosition = oldPosition
            newPosition += self.positionZoom * (newFocalPoint - newPosition)
        
        c.SetFocalPoint(newFocalPoint)
        c.SetPosition(newPosition)
        c.SetViewUp(oldViewUp)
        
        self.interp.AddCamera(1.0, c)
        self.startTime = time.time()
        self.start()
    
    def tick(self):
        """Timer callback to update camera position during animation."""
        elapsed = time.time() - self.startTime
        t = (elapsed / float(self.flyTime)) if self.flyTime > 0 else 1.0
        
        self.interp.InterpolateCamera(t, self.view.camera())
        self.view.render()
        
        if t >= 1.0:
            return False

