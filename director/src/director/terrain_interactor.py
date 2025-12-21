"""Pure Python terrain camera interactor for Director.

This interactor provides terrain-style camera controls:
- Left mouse: rotate (azimuth/elevation around focal point)
- Right mouse: zoom
- Shift + Left mouse: pan/translate
- Middle mouse: pan/translate

The view up is kept aligned with the Z-axis (vertical).
"""

import director.vtkAll as vtk
import math


class TerrainInteractorStyle(vtk.vtkInteractorStyle):
    """Pure Python terrain camera interactor style.

    Provides terrain-style camera controls using pure Python camera manipulation.
    All camera movement is done through vtkCamera - no C++ dependencies.
    """

    def __init__(self, allow_inversion=False):
        """Initialize the terrain interactor style.

        Args:
            allow_inversion: If True, allows elevation to go past ±90 degrees to enable
                            inverted views. If False (default), clamps elevation to ±89
                            degrees to avoid gimbal lock.
        """
        vtk.vtkInteractorStyle.__init__(self)

        # Feature flag: allow elevation inversion past 90 degrees
        self._allow_inversion = allow_inversion

        # Mouse state tracking
        self._last_pos = None
        self._left_button_pressed = False
        self._right_button_pressed = False
        self._middle_button_pressed = False
        self._pan_start_focal_point = None  # Store focal point when pan starts
        self._pan_start_3d_point = None  # Store the 3D point that was clicked (for panning)

        # Camera state for rotation
        self._rotation_factor = 0.3  # Sensitivity factor for rotation (degrees per pixel) - scaled down
        self._zoom_factor = 0.01  # Sensitivity factor for zoom
        self._pan_factor = 0.01  # Sensitivity factor for pan

        # Use observers to intercept events (more reliable than overriding methods)
        self.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, self._on_left_press)
        self.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, self._on_left_release)
        self.AddObserver(vtk.vtkCommand.RightButtonPressEvent, self._on_right_press)
        self.AddObserver(vtk.vtkCommand.RightButtonReleaseEvent, self._on_right_release)
        self.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, self._on_middle_press)
        self.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, self._on_middle_release)
        self.AddObserver(vtk.vtkCommand.MouseMoveEvent, self._on_mouse_move)
        self.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, self._on_wheel_forward)
        self.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, self._on_wheel_backward)

    def _get_interactor_state(self):
        """Get interactor state and find renderer at mouse position.

        Returns:
            tuple: (interactor, x, y, renderer) or (None, None, None, None) if invalid
        """
        interactor = self.GetInteractor()
        if not interactor:
            return (None, None, None, None)

        x, y = interactor.GetEventPosition()
        self.FindPokedRenderer(x, y)
        renderer = self.GetCurrentRenderer()

        return (interactor, x, y, renderer)

    def _init_pan_state(self, renderer, x, y):
        """Initialize pan state by storing focal point and 3D intersection point.

        Args:
            renderer: vtkRenderer instance
            x: Mouse X position
            y: Mouse Y position
        """
        if not renderer:
            self._pan_start_focal_point = None
            self._pan_start_3d_point = None
            return

        camera = renderer.GetActiveCamera()
        if not camera:
            self._pan_start_focal_point = None
            self._pan_start_3d_point = None
            return

        self._pan_start_focal_point = camera.GetFocalPoint()[:3]
        # Compute 3D point under mouse cursor (intersection with vertical plane)
        plane_point = self._pan_start_focal_point
        plane_normal = [0.0, 0.0, 1.0]  # Vertical plane

        # Convert display to world coordinates
        world_pt1 = [0.0, 0.0, 0.0, 1.0]
        world_pt2 = [0.0, 0.0, 0.0, 1.0]
        vtk.vtkInteractorObserver.ComputeDisplayToWorld(renderer, x, y, 0.0, world_pt1)
        vtk.vtkInteractorObserver.ComputeDisplayToWorld(renderer, x, y, 1.0, world_pt2)

        ray_start = world_pt1[:3]
        ray_end = world_pt2[:3]
        intersection = self._ray_plane_intersection(ray_start, ray_end, plane_point, plane_normal)
        self._pan_start_3d_point = intersection

    def _clear_pan_state(self):
        """Clear pan state."""
        self._pan_start_focal_point = None
        self._pan_start_3d_point = None

    def _on_left_press(self, obj, event):
        """Handle left mouse button press."""
        interactor, x, y, renderer = self._get_interactor_state()
        if not interactor:
            return

        # Initialize pan state if shift is pressed, otherwise clear it
        if interactor.GetShiftKey():
            self._init_pan_state(renderer, x, y)
        else:
            self._clear_pan_state()

        self._left_button_pressed = True
        self._last_pos = (x, y)

    def _on_left_release(self, obj, event):
        """Handle left mouse button release."""
        self._left_button_pressed = False
        self._last_pos = None
        self._clear_pan_state()

    def _on_right_press(self, obj, event):
        """Handle right mouse button press."""
        interactor, x, y, renderer = self._get_interactor_state()
        if not interactor:
            return

        self._right_button_pressed = True
        self._last_pos = (x, y)

    def _on_right_release(self, obj, event):
        """Handle right mouse button release."""
        self._right_button_pressed = False
        self._last_pos = None

    def _on_middle_press(self, obj, event):
        """Handle middle mouse button press."""
        interactor, x, y, renderer = self._get_interactor_state()
        if not interactor:
            return

        # Initialize pan state for middle button
        self._init_pan_state(renderer, x, y)

        self._middle_button_pressed = True
        self._last_pos = (x, y)

    def _on_middle_release(self, obj, event):
        """Handle middle mouse button release."""
        self._middle_button_pressed = False
        self._last_pos = None
        self._clear_pan_state()

    def _on_mouse_move(self, obj, event):
        """Handle mouse movement."""
        if not (self._left_button_pressed or self._right_button_pressed or self._middle_button_pressed):
            return

        interactor = self.GetInteractor()
        if not interactor:
            return

        # Find the renderer at the mouse position
        x, y = interactor.GetEventPosition()
        self.FindPokedRenderer(x, y)

        # Get current renderer (use GetCurrentRenderer() method)
        renderer = self.GetCurrentRenderer()
        if not renderer:
            # Fallback: get first renderer from render window
            renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
        if not renderer:
            return

        camera = renderer.GetActiveCamera()
        if not camera:
            return

        if self._last_pos is None:
            self._last_pos = (x, y)
            return

        # Calculate delta
        dx = x - self._last_pos[0]
        dy = y - self._last_pos[1]

        # Get modifiers
        shift_pressed = interactor.GetShiftKey()

        if self._left_button_pressed:
            if shift_pressed:
                # Shift + Left mouse: Pan/translate
                self._pan_camera(camera, dx, dy, renderer)
            else:
                # Left mouse: Rotate (azimuth/elevation)
                self._rotate_camera(camera, dx, dy, renderer)

        elif self._right_button_pressed:
            # Right mouse: Zoom
            self._zoom_camera(camera, dx, dy, renderer)

        elif self._middle_button_pressed:
            # Middle mouse: Pan/translate
            self._pan_camera(camera, dx, dy, renderer)

        self._last_pos = (x, y)

        self._render()

    def _on_wheel_forward(self, obj, event):
        """Handle mouse wheel forward (zoom in)."""
        interactor = self.GetInteractor()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
        if renderer:
            camera = renderer.GetActiveCamera()
            if camera:
                self._zoom_camera_wheel(camera, -1, renderer)
                self._render()

    def _on_wheel_backward(self, obj, event):
        """Handle mouse wheel backward (zoom out)."""
        interactor = self.GetInteractor()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
        if renderer:
            camera = renderer.GetActiveCamera()
            if camera:
                self._zoom_camera_wheel(camera, 1, renderer)
                self._render()

    def _render(self):
        interactor = self.GetInteractor()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
        renderer.ResetCameraClippingRange()
        interactor.Render()

    # Override base class methods to prevent default camera behavior
    # but still allow FindPokedRenderer and other setup
    def OnLeftButtonDown(self):
        """Override to prevent default left button camera behavior."""
        # Don't call parent - we handle rotation/pan in observers
        pass

    def OnLeftButtonUp(self):
        """Override to prevent default left button camera behavior."""
        # Don't call parent
        pass

    def OnRightButtonDown(self):
        """Override to prevent default right button camera behavior."""
        # Don't call parent - we handle zoom in observers
        pass

    def OnRightButtonUp(self):
        """Override to prevent default right button camera behavior."""
        # Don't call parent
        pass

    def OnMiddleButtonDown(self):
        """Override to prevent default middle button camera behavior."""
        # Don't call parent - we handle pan in observers
        pass

    def OnMiddleButtonUp(self):
        """Override to prevent default middle button camera behavior."""
        # Don't call parent
        pass

    def OnMouseMove(self):
        """Override to prevent default mouse move camera behavior."""
        # Don't call parent - we handle movement in observers
        pass

    def _rotate_camera(self, camera, dx, dy, renderer=None):
        """Rotate camera around focal point using azimuth and elevation.

        Args:
            camera: vtkCamera instance
            dx: Horizontal mouse delta (pixels)
            dy: Vertical mouse delta (pixels)
            renderer: vtkRenderer instance (optional, for clipping range)
        """
        # Get current camera state
        focal_point = camera.GetFocalPoint()
        position = camera.GetPosition()

        # Calculate vector from focal point to camera position
        view_vector = [position[i] - focal_point[i] for i in range(3)]
        distance = math.sqrt(sum(v * v for v in view_vector))

        if distance < 1e-6:
            # Camera is at focal point, move it away
            camera.SetPosition(focal_point[0], focal_point[1], focal_point[2] + 10.0)
            position = camera.GetPosition()
            view_vector = [position[i] - focal_point[i] for i in range(3)]
            distance = math.sqrt(sum(v * v for v in view_vector))

        # Normalize view vector
        if distance > 1e-6:
            view_vector = [v / distance for v in view_vector]

        # Calculate current azimuth and elevation using spherical coordinates
        # We use atan2 to handle the full range and track elevation continuously
        azimuth = math.atan2(view_vector[1], view_vector[0]) * 180.0 / math.pi

        # Calculate elevation: -90 (straight down) to 90 (straight up)
        # Use atan2 to get proper quadrant information for continuity
        xy_magnitude = math.sqrt(view_vector[0] ** 2 + view_vector[1] ** 2)
        elevation = math.atan2(view_vector[2], xy_magnitude) * 180.0 / math.pi

        # Update azimuth and elevation based on mouse movement
        azimuth -= dx * self._rotation_factor  # Flip sign for correct azimuth direction
        elevation -= dy * self._rotation_factor  # Invert dy for natural feel

        # Normalize azimuth to [-180, 180]
        while azimuth > 180.0:
            azimuth -= 360.0
        while azimuth < -180.0:
            azimuth += 360.0

        if self._allow_inversion:
            # Allow elevation to go beyond ±90 degrees to enable inverted views
            # However, add a small offset when very close to exactly ±90 to avoid
            # gimbal lock (when view direction is exactly parallel to Z-axis)
            # This prevents VTK from resetting the view-up vector
            # We "jump" past the gimbal lock zone by adding a small offset
            gimbal_lock_epsilon = 1.0  # Larger margin in degrees to avoid exact alignment

            elevation_before = elevation

            if elevation > 90.0 - gimbal_lock_epsilon and elevation < 90.0 + gimbal_lock_epsilon:
                # When in the gimbal lock zone near straight down (90°), jump past it
                if elevation >= 90.0:
                    # Already at or past 90°, jump to just past it
                    elevation = 90.0 + gimbal_lock_epsilon
                else:
                    # Approaching 90° from below, jump to just past it
                    elevation = 90.0 + gimbal_lock_epsilon
                print(f"Gimbal lock avoidance: elevation {elevation_before:.3f}° -> {elevation:.3f}° (jumped past 90°)")
            elif elevation < -90.0 + gimbal_lock_epsilon and elevation > -90.0 - gimbal_lock_epsilon:
                # When in the gimbal lock zone near straight up (-90°), jump past it
                if elevation <= -90.0:
                    # Already at or past -90°, jump to just past it
                    elevation = -90.0 - gimbal_lock_epsilon
                else:
                    # Approaching -90° from above, jump to just past it
                    elevation = -90.0 - gimbal_lock_epsilon
                print(
                    f"Gimbal lock avoidance: elevation {elevation_before:.3f}° -> {elevation:.3f}° (jumped past -90°)"
                )

            # Debug: print elevation values to track rotation
            if abs(elevation) > 85.0:  # Only print when close to gimbal lock zone
                print(f"Elevation: {elevation:.3f}°, Azimuth: {azimuth:.3f}°, View vector Z: {view_vector[2]:.6f}")
        else:
            # Default: clamp elevation to avoid gimbal lock
            # Use a tighter range to avoid VTK warnings about parallel view-up
            # This keeps us far enough from 90 degrees that VTK doesn't complain
            elevation = max(-85.0, min(85.0, elevation))

        # Convert back to cartesian coordinates
        azimuth_rad = azimuth * math.pi / 180.0
        elevation_rad = elevation * math.pi / 180.0

        # Use standard spherical coordinate conversion
        cos_elev = math.cos(elevation_rad)
        new_view_vector = [
            distance * cos_elev * math.cos(azimuth_rad),
            distance * cos_elev * math.sin(azimuth_rad),
            distance * math.sin(elevation_rad),
        ]

        # Update camera position
        new_position = [focal_point[i] + new_view_vector[i] for i in range(3)]
        camera.SetPosition(new_position)

        # Compute view up vector
        # If inversion is disabled, use Z-axis as view up (standard terrain mode)
        # but compute orthogonally when very close to poles to avoid VTK warnings
        # If inversion is enabled, always compute view up orthogonally
        view_dir_normalized = [new_view_vector[i] / distance for i in range(3)]
        view_z_component = abs(view_dir_normalized[2])

        if not self._allow_inversion:
            # Standard terrain mode: always use Z-axis as view up
            # With elevation clamped to ±85 degrees, we should never get close enough
            # to the pole to trigger VTK's parallel view-up warning
            camera.SetViewUp(0.0, 0.0, 1.0)
            # Reset camera clipping range
            if renderer:
                renderer.ResetCameraClippingRange()
            return

        # Inversion enabled: compute view up that is orthogonal to the view direction
        # When the view direction is nearly parallel to Z-axis, we can't use Z as view up
        # Instead, compute a view up that's always orthogonal to the view direction
        view_z_component = abs(view_dir_normalized[2])

        # Use the azimuth to pick a reference vector that's perpendicular to the view direction
        # For terrain mode, we want view up to be as close to Z as possible when not near poles
        if view_z_component > 0.99:
            # View is very close to Z-axis (nearly straight down/up), use azimuth-based reference
            # Use a vector in the XY plane perpendicular to the view direction's projection
            # This ensures we get a good view up even at the pole
            azimuth_rad = math.atan2(view_dir_normalized[1], view_dir_normalized[0])
            # Use a vector perpendicular in XY plane
            reference = [-math.sin(azimuth_rad), math.cos(azimuth_rad), 0.0]
        elif view_z_component > 0.9:
            # View is moderately close to Z-axis, use Y-axis as reference
            reference = [0.0, 1.0, 0.0]
        else:
            # View is not near Z-axis, use Z-axis as reference (terrain mode)
            reference = [0.0, 0.0, 1.0]

        # Compute view up as orthogonal to view direction using Gram-Schmidt
        # view_up = reference - (reference . view_dir) * view_dir
        dot_product = sum(reference[i] * view_dir_normalized[i] for i in range(3))
        view_up = [reference[i] - dot_product * view_dir_normalized[i] for i in range(3)]

        # Normalize view up vector
        view_up_magnitude = math.sqrt(sum(v * v for v in view_up))
        if view_up_magnitude > 1e-4:  # Use larger threshold
            view_up = [v / view_up_magnitude for v in view_up]
        else:
            # Fallback: use cross product to find orthogonal vector
            # If view_dir is close to Z, use X cross view_dir
            if view_z_component > 0.9:
                # Cross product: X-axis x view_dir
                x_axis = [1.0, 0.0, 0.0]
                view_up = [
                    x_axis[1] * view_dir_normalized[2] - x_axis[2] * view_dir_normalized[1],
                    x_axis[2] * view_dir_normalized[0] - x_axis[0] * view_dir_normalized[2],
                    x_axis[0] * view_dir_normalized[1] - x_axis[1] * view_dir_normalized[0],
                ]
            else:
                # Cross product: Z-axis x view_dir
                z_axis = [0.0, 0.0, 1.0]
                view_up = [
                    z_axis[1] * view_dir_normalized[2] - z_axis[2] * view_dir_normalized[1],
                    z_axis[2] * view_dir_normalized[0] - z_axis[0] * view_dir_normalized[2],
                    z_axis[0] * view_dir_normalized[1] - z_axis[1] * view_dir_normalized[0],
                ]
            view_up_magnitude = math.sqrt(sum(v * v for v in view_up))
            if view_up_magnitude > 1e-6:
                view_up = [v / view_up_magnitude for v in view_up]
            else:
                # Last resort: use a fixed vector based on view direction
                if abs(view_dir_normalized[0]) < 0.9:
                    view_up = [1.0, 0.0, 0.0]
                elif abs(view_dir_normalized[1]) < 0.9:
                    view_up = [0.0, 1.0, 0.0]
                else:
                    view_up = [0.0, 0.0, 1.0]

        # Verify orthogonality: view_up should be perpendicular to view_dir
        dot_product = sum(view_up[i] * view_dir_normalized[i] for i in range(3))

        camera.SetViewUp(view_up)

        # Debug: print view up info when near gimbal lock zone
        if abs(view_dir_normalized[2]) > 0.9:
            print(
                f"View dir: [{view_dir_normalized[0]:.3f}, {view_dir_normalized[1]:.3f}, {view_dir_normalized[2]:.6f}]"
            )
            print(f"View up: [{view_up[0]:.3f}, {view_up[1]:.3f}, {view_up[2]:.6f}]")
            print(f"View up magnitude: {math.sqrt(sum(v * v for v in view_up)):.6f}")
            print(f"Dot product (view_dir . view_up): {dot_product:.6f} (should be ~0)")
            print(f"Elevation: {elevation:.3f}°")

        # Reset camera clipping range
        if renderer:
            renderer.ResetCameraClippingRange()

    def _zoom_camera(self, camera, dx, dy, renderer=None):
        """Zoom camera by moving it closer to or farther from focal point.

        Args:
            camera: vtkCamera instance
            dx: Horizontal mouse delta (unused for zoom)
            dy: Vertical mouse delta (positive = zoom in, negative = zoom out)
            renderer: vtkRenderer instance (optional, for clipping range)
        """
        # Check if camera is in parallel projection mode
        if camera.GetParallelProjection():
            # In parallel projection mode, zoom by adjusting parallel scale
            # Decreasing parallel scale = zoom in (more detail visible)
            # Increasing parallel scale = zoom out (less detail visible)
            current_scale = camera.GetParallelScale()
            if current_scale > 1e-6:
                # Zoom factor based on current scale (proportional zoom)
                zoom_delta = -dy * self._zoom_factor * current_scale
                new_scale = max(1e-6, current_scale + zoom_delta)
                camera.SetParallelScale(new_scale)
            else:
                # Very small scale, use absolute zoom
                zoom_delta = -dy * self._zoom_factor * 1.0
                new_scale = max(1e-6, current_scale + zoom_delta)
                camera.SetParallelScale(new_scale)
        else:
            # Perspective projection mode: move camera along view vector
            focal_point = camera.GetFocalPoint()
            position = camera.GetPosition()

            # Calculate vector from focal point to camera position
            view_vector = [position[i] - focal_point[i] for i in range(3)]
            distance = math.sqrt(sum(v * v for v in view_vector))

            # Zoom factor based on distance (proportional zoom)
            zoom_delta = -dy * self._zoom_factor * distance

            # Apply zoom (move camera along view vector)
            # Allow zooming to arbitrarily close (remove the 0.1 minimum limit)
            min_distance = 1e-6  # Very small minimum to avoid numerical issues
            if distance > min_distance:
                view_vector_normalized = [v / distance for v in view_vector]
                new_distance = max(min_distance, distance + zoom_delta)
                new_position = [focal_point[i] + view_vector_normalized[i] * new_distance for i in range(3)]
                camera.SetPosition(new_position)
            else:
                # Already very close, use normalized direction from current position
                if distance > 1e-9:
                    view_vector_normalized = [v / distance for v in view_vector]
                else:
                    # Distance is essentially zero, use camera's view direction
                    view_dir = camera.GetDirectionOfProjection()
                    mag = math.sqrt(sum(v * v for v in view_dir))
                    if mag > 1e-6:
                        view_vector_normalized = [-v / mag for v in view_dir]
                    else:
                        # Fallback: use a default direction
                        view_vector_normalized = [0.0, 0.0, -1.0]

                # Apply zoom by moving camera closer
                new_distance = max(min_distance, distance + zoom_delta)
                new_position = [focal_point[i] + view_vector_normalized[i] * new_distance for i in range(3)]
                camera.SetPosition(new_position)

        # Reset camera clipping range after zoom (this adjusts near/far planes for visibility)
        if renderer:
            renderer.ResetCameraClippingRange()

    def _zoom_camera_wheel(self, camera, direction, renderer=None):
        """Zoom camera using mouse wheel.

        Args:
            camera: vtkCamera instance
            direction: -1 for zoom in, 1 for zoom out
            renderer: vtkRenderer instance (optional, for clipping range)
        """
        # Check if camera is in parallel projection mode
        if camera.GetParallelProjection():
            # In parallel projection mode, zoom by adjusting parallel scale
            # Decreasing parallel scale = zoom in (more detail visible)
            # Increasing parallel scale = zoom out (less detail visible)
            current_scale = camera.GetParallelScale()
            if current_scale > 1e-6:
                # Zoom factor (10% per wheel step)
                zoom_factor = 0.1
                zoom_delta = direction * zoom_factor * current_scale
                new_scale = max(1e-6, current_scale + zoom_delta)
                camera.SetParallelScale(new_scale)
            else:
                # Very small scale, use absolute zoom
                zoom_factor = 0.1
                zoom_delta = direction * zoom_factor * 1.0
                new_scale = max(1e-6, current_scale + zoom_delta)
                camera.SetParallelScale(new_scale)
        else:
            # Perspective projection mode: move camera along view vector
            focal_point = camera.GetFocalPoint()
            position = camera.GetPosition()

            # Calculate vector from focal point to camera position
            view_vector = [position[i] - focal_point[i] for i in range(3)]
            distance = math.sqrt(sum(v * v for v in view_vector))

            # Zoom factor (10% per wheel step)
            zoom_factor = 0.1
            zoom_delta = direction * zoom_factor * distance

            # Apply zoom - allow zooming to arbitrarily close
            min_distance = 1e-6  # Very small minimum to avoid numerical issues
            if distance > min_distance:
                view_vector_normalized = [v / distance for v in view_vector]
                new_distance = max(min_distance, distance + zoom_delta)
                new_position = [focal_point[i] + view_vector_normalized[i] * new_distance for i in range(3)]
                camera.SetPosition(new_position)
            else:
                # Already very close, use normalized direction
                if distance > 1e-9:
                    view_vector_normalized = [v / distance for v in view_vector]
                else:
                    # Use camera's view direction
                    view_dir = camera.GetDirectionOfProjection()
                    mag = math.sqrt(sum(v * v for v in view_dir))
                    if mag > 1e-6:
                        view_vector_normalized = [-v / mag for v in view_dir]
                    else:
                        view_vector_normalized = [0.0, 0.0, -1.0]

                new_distance = max(min_distance, distance + zoom_delta)
                new_position = [focal_point[i] + view_vector_normalized[i] * new_distance for i in range(3)]
                camera.SetPosition(new_position)

        # Reset camera clipping range after zoom
        if renderer:
            renderer.ResetCameraClippingRange()

    def _pan_camera(self, camera, dx, dy, renderer=None):
        """Pan camera - exact replica of vtkInteractorStyleTerrain2::Pan().

        Args:
            camera: vtkCamera instance
            dx: Horizontal mouse delta (unused, we compute from positions)
            dy: Vertical mouse delta (unused, we compute from positions)
            renderer: vtkRenderer instance (required)
        """
        if not renderer:
            return

        interactor = self.GetInteractor()
        if not interactor:
            return

        if self._last_pos is None:
            return

        # Get the vector of motion (following C++ exactly)
        pos = list(camera.GetPosition())
        fp = list(camera.GetFocalPoint())

        # Compute focal point in display coordinates (focalPoint[2] is the z-depth)
        focal_point_display = [0.0, 0.0, 0.0]
        vtk.vtkInteractorObserver.ComputeWorldToDisplay(renderer, fp[0], fp[1], fp[2], focal_point_display)

        # Get event positions
        event_pos = list(interactor.GetEventPosition())
        last_event_pos = list(self._last_pos)

        # Handle Control key constraint (horizontal or vertical only)
        if interactor.GetControlKey():
            mouse_delta = [event_pos[0] - last_event_pos[0], event_pos[1] - last_event_pos[1]]
            if abs(mouse_delta[0]) >= abs(mouse_delta[1]):
                event_pos[1] = last_event_pos[1]  # Lock Y
            else:
                event_pos[0] = last_event_pos[0]  # Lock X

        # Compute world points at the focal plane depth for both positions
        p1 = [0.0, 0.0, 0.0, 1.0]  # Current event position
        p2 = [0.0, 0.0, 0.0, 1.0]  # Last event position

        vtk.vtkInteractorObserver.ComputeDisplayToWorld(
            renderer, event_pos[0], event_pos[1], focal_point_display[2], p1
        )
        vtk.vtkInteractorObserver.ComputeDisplayToWorld(
            renderer, last_event_pos[0], last_event_pos[1], focal_point_display[2], p2
        )

        # Compute pan vector: v = p2 - p1 (movement from last to current)
        v = [p2[i] - p1[i] for i in range(3)]

        # Move both position and focal point by v
        for i in range(3):
            pos[i] += v[i]
            fp[i] += v[i]

        camera.SetPosition(pos)
        camera.SetFocalPoint(fp)

        # Reset camera clipping range
        if renderer:
            renderer.ResetCameraClippingRange()

    def _ray_plane_intersection(self, ray_start, ray_end, plane_point, plane_normal):
        """Compute intersection of a ray with a plane.

        Args:
            ray_start: Start point of ray [x, y, z]
            ray_end: End point of ray [x, y, z]
            plane_point: Point on plane [x, y, z]
            plane_normal: Normal vector of plane [x, y, z]

        Returns:
            Intersection point [x, y, z] or None if ray is parallel to plane
        """
        # Ray direction
        ray_dir = [ray_end[i] - ray_start[i] for i in range(3)]
        ray_length = math.sqrt(sum(d * d for d in ray_dir))

        if ray_length < 1e-6:
            return None

        ray_dir_normalized = [d / ray_length for d in ray_dir]

        # Compute intersection parameter t
        # Plane equation: normal . (point - plane_point) = 0
        # Ray: point = ray_start + t * ray_dir
        # normal . (ray_start + t * ray_dir - plane_point) = 0
        # normal . (ray_start - plane_point) + t * (normal . ray_dir) = 0

        ray_to_plane = [ray_start[i] - plane_point[i] for i in range(3)]
        denom = sum(plane_normal[i] * ray_dir_normalized[i] for i in range(3))

        if abs(denom) < 1e-6:
            # Ray is parallel to plane
            return None

        t = -sum(plane_normal[i] * ray_to_plane[i] for i in range(3)) / denom

        # Compute intersection point
        intersection = [ray_start[i] + t * ray_dir_normalized[i] * ray_length for i in range(3)]

        return intersection


def setTerrainInteractor(view, allow_inversion=False):
    """Set terrain interactor style on a view.

    Args:
        view: VTKWidget instance
        allow_inversion: If True, allows elevation to go past ±90 degrees to enable
                        inverted views. If False (default), clamps elevation to ±89
                        degrees to avoid gimbal lock.

    Returns:
        TerrainInteractorStyle instance
    """
    interactor = view.renderWindow().GetInteractor()
    if interactor:
        style = TerrainInteractorStyle(allow_inversion=allow_inversion)
        interactor.SetInteractorStyle(style)

        # Ensure view up is Z-axis (if inversion disabled, this will be maintained)
        camera = view.camera()
        if camera:
            camera.SetViewUp(0.0, 0.0, 1.0)

        return style
    return None
