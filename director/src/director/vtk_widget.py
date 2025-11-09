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
        self._renderer.SetBackground(25/255, 25/255, 30/255)
        self._renderer.SetBackground2(45/255, 45/255, 55/255)
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
        
        # Custom bounds for camera reset
        self._custom_bounds = []
        
        # Render pending flag
        self._render_pending = False
        
        # Setup render timer (60 FPS)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._on_render_timer)
        #self._render_timer.start(int(1000 / 60))
        
        # Connect render events to update FPS counter
        self._render_window.AddObserver(
            vtk.vtkCommand.EndEvent, 
            self._on_end_render
        )
        
        # Initialize VTK interactor
        #self._vtk_widget.Initialize()
        #self._vtk_widget.Start()
        
        # Set terrain interactor style by default (natural view up, azimuth/elevation camera control)
        self.setTerrainInteractor()
        
        # Set initial camera position for terrain mode
        camera = self._renderer.GetActiveCamera()
        if camera:
            camera.SetPosition(10.0, 10.0, 10.0)
            camera.SetFocalPoint(0.0, 0.0, 0.0)
            camera.SetViewUp(0.0, 0.0, 1.0)
        

        
        # Grid will be added later when object model is initialized
        self._grid_obj = None
        
        # Reset camera (will adjust to scene bounds if actors exist)
        self._renderer.ResetCamera()
    
    def initializeGrid(self):
        """Initialize the default grid (called after object model is set up)."""
        if self._grid_obj is None:
            from director import visualization as vis
            try:
                self._grid_obj = vis.showGrid(self, name='grid', parent='scene', 
                                            cellSize=0.5, numberOfCells=25,
                                            alpha=0.3, color=[0.5, 0.5, 0.5])
            except:
                # Object model might not be ready yet, ignore
                pass
    
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
            self._render_timer.start()
    
    def forceRender(self):
        """Force an immediate render."""
        self._render_pending = False
        self._render_timer.stop()
        self._renderer.ResetCameraClippingRange()
        self._render_window.Render()
    
    def addQuitShortcut(self, key_sequence='Ctrl+Q'):
        """Add a keyboard shortcut to quit the application.
        
        Args:
            key_sequence: Key sequence string (default: 'Ctrl+Q')
            
        Returns:
            QShortcut: The created shortcut object
        """
        from qtpy.QtWidgets import QShortcut
        from qtpy.QtGui import QKeySequence
        from qtpy.QtWidgets import QApplication
        
        shortcut = QShortcut(QKeySequence(key_sequence), self)
        shortcut.activated.connect(QApplication.instance().quit)
        return shortcut
    
    def setTerrainInteractor(self, allow_inversion=False):
        """Set the terrain interactor style (azimuth/elevation rotation, Z-up).
        
        Args:
            allow_inversion: If True, allows elevation to go past ±90 degrees to enable
                            inverted views. If False (default), clamps elevation.
        """
        interactor = self._render_window.GetInteractor()
        if interactor:
            from director.terrain_interactor import setTerrainInteractor
            setTerrainInteractor(self, allow_inversion=allow_inversion)
            # Ensure view up is Z-axis for terrain mode
            camera = self._renderer.GetActiveCamera()
            if camera:
                camera.SetViewUp(0.0, 0.0, 1.0)
            self.render()
    
    def setTrackballInteractor(self):
        """Set the trackball interactor style (standard VTK trackball camera)."""
        interactor = self._render_window.GetInteractor()
        if interactor:
            interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
            self.render()
    
    def isTerrainInteractor(self):
        """Check if terrain interactor is currently active.
        
        Returns:
            bool: True if terrain interactor is active, False if trackball is active.
        """
        interactor = self._render_window.GetInteractor()
        if not interactor:
            return False
        style = interactor.GetInteractorStyle()
        from director.terrain_interactor import TerrainInteractorStyle
        return isinstance(style, TerrainInteractorStyle)
    
    def addCustomBounds(self, bounds):
        """Add custom bounds for camera reset calculation."""
        # bounds should be a list/tuple of 6 values [xmin, xmax, ymin, ymax, zmin, zmax]
        if len(bounds) == 6:
            self._custom_bounds.append(list(bounds))
    
    def resetCamera(self):
        """Reset the camera to fit all actors, excluding the grid if present."""
        # Try to compute bounds excluding grid
        bounds = None
        if hasattr(self, '_grid_obj') and self._grid_obj:
            try:
                from director.viewbounds import computeViewBoundsNoGrid
                bounds = computeViewBoundsNoGrid(self, self._grid_obj)
                # Check if bounds are valid
                if bounds is not None and len(bounds) == 6:
                    # Check if bounds are initialized (not all zeros)
                    if not all(abs(b) < 1e-9 for b in bounds):
                        bounds_array = [float(b) for b in bounds]
                        self._renderer.ResetCamera(bounds_array)
                        self._renderer.ResetCameraClippingRange()
                        return
            except:
                pass
        
        # Fall back to custom bounds if available
        if self._custom_bounds:
            # Use vtkBoundingBox to combine all custom bounds
            bbox = vtk.vtkBoundingBox()
            for bounds in self._custom_bounds:
                bounds_array = [float(b) for b in bounds]
                bbox.AddBounds(bounds_array)
            
            if bbox.IsValid():
                result_bounds = [0.0] * 6
                bbox.GetBounds(result_bounds)
                self._renderer.ResetCamera(result_bounds)
            else:
                self._renderer.ResetCamera()
        else:
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
    
    def _on_end_render(self, obj, event):
        """Handle end render event to update FPS counter."""
        self._fps_counter.update()
    
    def closeEvent(self, event):
        """Handle widget close event with proper cleanup."""
        # Stop render timer first
        if hasattr(self, '_render_timer'):
            self._render_timer.stop()
            try:
                self._render_timer.timeout.disconnect(self._on_render_timer)
            except (TypeError, RuntimeError):
                pass
        
        # Remove observer for render events
        if hasattr(self, '_render_window') and self._render_window:
            try:
                self._render_window.RemoveObserver(self._on_end_render)
            except:
                pass
        
        # Call parent closeEvent (VTK widget will clean itself up now that it's patched)
        super().closeEvent(event)
    
    # def resizeEvent(self, event):
    #     """Handle widget resize events."""
    #     if hasattr(self, '_vtk_widget') and self._vtk_widget:
    #         self._vtk_widget.resize(self.width(), self.height())
    #         if self._render_window:
    #             self._render_window.SetSize(self.width(), self.height())
    #     super().resizeEvent(event)

