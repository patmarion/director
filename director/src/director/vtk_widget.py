"""VTKWidget class implementing the Director VTK widget API."""

import time
import vtk
from qtpy.QtWidgets import QWidget, QVBoxLayout
from qtpy.QtCore import QTimer, QObject, Signal


class FPSCounter:
    """Exponential moving average FPS counter."""
    
    def __init__(self, alpha=0.9, time_window=1.0):
        self.alpha = alpha
        self.time_window = time_window
        self.average_fps = 0.0
        self.frames_this_window = 0
        self.start_time = time.time()
    
    def update(self):
        """Update the FPS counter with a new frame."""
        self.frames_this_window += 1
        self._update_average()
    
    def get_average_fps(self):
        """Get the current average FPS."""
        self._update_average()
        return self.average_fps
    
    def _update_average(self):
        """Update the moving average FPS."""
        elapsed_time = time.time() - self.start_time
        
        if elapsed_time > self.time_window:
            # Compute FPS for this time window
            average_fps_this_window = self.frames_this_window / elapsed_time
            
            # Update moving average
            self.average_fps = (
                self.alpha * average_fps_this_window + 
                (1.0 - self.alpha) * self.average_fps
            )
            
            # Reset counters
            self.start_time = time.time()
            self.frames_this_window = 0


class VTKWidget(QWidget):
    """VTK widget that provides Director-compatible API."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create VTK render window interactor widget
        try:
            from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        except ImportError:
            from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        
        self._vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self._vtk_widget)
        
        # Get render window
        self._render_window = self._vtk_widget.GetRenderWindow()
        
        # Configure render window
        self._render_window.SetMultiSamples(8)  # Anti-aliasing
        self._render_window.SetSize(self.width(), self.height())
        
        # Create renderer
        self._renderer = vtk.vtkRenderer()
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground(0.0, 0.0, 0.0)
        self._renderer.SetBackground2(0.3, 0.3, 0.3)
        self._render_window.AddRenderer(self._renderer)
        
        # Create light kit
        self._light_kit = vtk.vtkLightKit()
        self._light_kit.SetKeyLightWarmth(0.5)
        self._light_kit.SetFillLightWarmth(0.5)
        self.setLightKitEnabled(True)
        
        # Setup orientation marker
        self._setup_orientation_marker()
        
        # FPS counter
        self._fps_counter = FPSCounter()
        
        # Render pending flag
        self._render_pending = False
        
        # Setup render timer (60 FPS)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(False)
        self._render_timer.timeout.connect(self._on_render_timer)
        self._render_timer.start(int(1000 / 60))
        
        # Connect render events to update FPS counter
        self._render_window.AddObserver(
            vtk.vtkCommand.EndEvent, 
            self._on_end_render
        )
        
        # Initialize VTK interactor
        self._vtk_widget.Initialize()
        self._vtk_widget.Start()
        
        # Reset camera
        self._renderer.ResetCamera()
    
    def renderWindow(self):
        """Return the VTK render window."""
        return self._render_window
    
    def renderer(self):
        """Return the main renderer."""
        return self._renderer
    
    def backgroundRenderer(self):
        """Return the background renderer (same as main renderer for now)."""
        return self._renderer
    
    def camera(self):
        """Return the active camera."""
        return self._renderer.GetActiveCamera()
    
    def lightKit(self):
        """Return the light kit."""
        return self._light_kit
    
    def vtkWidget(self):
        """Return the QVTK widget."""
        return self._vtk_widget
    
    def orientationMarkerWidget(self):
        """Return the orientation marker widget."""
        return self._orientation_widget
    
    def render(self):
        """Request a render (queued, will render on next timer tick)."""
        if not self._render_pending:
            self._render_pending = True
    
    def forceRender(self):
        """Force an immediate render."""
        self._renderer.ResetCameraClippingRange()
        self._render_window.Render()
    
    def resetCamera(self):
        """Reset the camera to fit all actors."""
        self._renderer.ResetCamera()
        self._renderer.ResetCameraClippingRange()
    
    def getAverageFramesPerSecond(self):
        """Get the average frames per second."""
        return self._fps_counter.get_average_fps()
    
    def setLightKitEnabled(self, enabled):
        """Enable or disable the light kit."""
        self._renderer.RemoveAllLights()
        if enabled:
            self._light_kit.AddLightsToRenderer(self._renderer)
    
    def _setup_orientation_marker(self):
        """Setup the orientation marker widget."""
        # Disable interactor temporarily
        interactor = self._render_window.GetInteractor()
        interactor.Disable()
        
        # Create axes actor
        axes_actor = vtk.vtkAxesActor()
        
        # Setup text properties
        for prop in [
            axes_actor.GetXAxisCaptionActor2D().GetCaptionTextProperty(),
            axes_actor.GetYAxisCaptionActor2D().GetCaptionTextProperty(),
            axes_actor.GetZAxisCaptionActor2D().GetCaptionTextProperty(),
        ]:
            prop.ShadowOff()
            prop.BoldOff()
            prop.ItalicOff()
        
        # Create orientation marker widget
        self._orientation_widget = vtk.vtkOrientationMarkerWidget()
        self._orientation_widget.SetOutlineColor(1.0, 1.0, 1.0)
        self._orientation_widget.SetOrientationMarker(axes_actor)
        self._orientation_widget.SetInteractor(interactor)
        self._orientation_widget.SetViewport(0.0, 0.0, 0.2, 0.2)
        self._orientation_widget.SetEnabled(1)
        self._orientation_widget.InteractiveOff()
        
        # Re-enable interactor
        interactor.Enable()
    
    def _on_render_timer(self):
        """Handle render timer timeout."""
        if self._render_pending:
            self.forceRender()
            self._render_pending = False
    
    def _on_end_render(self, obj, event):
        """Handle end render event to update FPS counter."""
        self._fps_counter.update()
    
    # def resizeEvent(self, event):
    #     """Handle widget resize events."""
    #     if hasattr(self, '_vtk_widget') and self._vtk_widget:
    #         self._vtk_widget.resize(self.width(), self.height())
    #         if self._render_window:
    #             self._render_window.SetSize(self.width(), self.height())
    #     super().resizeEvent(event)

