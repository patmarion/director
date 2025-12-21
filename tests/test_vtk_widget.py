"""Tests for vtk_widget module."""

import vtk

from director.vtk_widget import FPSCounter, VTKWidget


def test_fps_counter():
    """Test FPS counter functionality."""
    counter = FPSCounter(alpha=0.9, time_window=0.1)

    # Initially should be 0
    assert counter.get_average_fps() == 0.0

    # Update a few times
    counter.update()
    counter.update()

    # After updates, should have some value (might still be 0 if time window not elapsed)
    fps = counter.get_average_fps()
    assert fps >= 0.0


def test_vtk_widget_construction(qapp):
    """Test that VTKWidget can be constructed."""
    widget = VTKWidget()
    assert widget is not None


def test_vtk_widget_render_window(qapp):
    """Test renderWindow() method."""
    widget = VTKWidget()
    render_window = widget.renderWindow()
    assert render_window is not None
    assert isinstance(render_window, vtk.vtkRenderWindow)


def test_vtk_widget_renderer(qapp):
    """Test renderer() method."""
    widget = VTKWidget()
    renderer = widget.renderer()
    assert renderer is not None
    assert isinstance(renderer, vtk.vtkRenderer)


def test_vtk_widget_background_renderer(qapp):
    """Test backgroundRenderer() method."""
    widget = VTKWidget()
    bg_renderer = widget.backgroundRenderer()
    assert bg_renderer is not None
    assert isinstance(bg_renderer, vtk.vtkRenderer)
    # Should return the same renderer as renderer() for now
    assert bg_renderer == widget.renderer()


def test_vtk_widget_camera(qapp):
    """Test camera() method."""
    widget = VTKWidget()
    camera = widget.camera()
    assert camera is not None
    assert isinstance(camera, vtk.vtkCamera)


def test_vtk_widget_light_kit(qapp):
    """Test lightKit() method."""
    widget = VTKWidget()
    light_kit = widget.lightKit()
    assert light_kit is not None
    assert isinstance(light_kit, vtk.vtkLightKit)


def test_vtk_widget_vtk_widget(qapp):
    """Test vtkWidget() method."""
    widget = VTKWidget()
    vtk_w = widget.vtkWidget()
    assert vtk_w is not None


def test_vtk_widget_orientation_marker(qapp):
    """Test orientationMarkerWidget() method."""
    widget = VTKWidget()
    orientation_widget = widget.orientationMarkerWidget()
    assert orientation_widget is not None
    assert isinstance(orientation_widget, vtk.vtkOrientationMarkerWidget)


def test_vtk_widget_render(qapp):
    """Test render() method."""
    widget = VTKWidget()
    # Should not raise
    widget.render()


def test_vtk_widget_force_render(qapp):
    """Test forceRender() method."""
    widget = VTKWidget()
    # Should not raise
    widget.forceRender()


def test_vtk_widget_reset_camera(qapp):
    """Test resetCamera() method."""
    widget = VTKWidget()
    # Add a simple actor to test camera reset
    sphere_source = vtk.vtkSphereSource()
    sphere_source.SetRadius(1.0)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere_source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    widget.renderer().AddActor(actor)

    # Reset camera should not raise
    widget.resetCamera()


def test_vtk_widget_get_average_fps(qapp):
    """Test getAverageFramesPerSecond() method."""
    widget = VTKWidget()
    # Initially might be 0 or have some value
    fps = widget.getAverageFramesPerSecond()
    assert fps >= 0.0

    # Trigger some renders
    widget.forceRender()

    # FPS might still be 0 or have a value depending on timing
    fps = widget.getAverageFramesPerSecond()
    assert fps >= 0.0


def test_vtk_widget_show_and_close(qapp):
    """Test that VTKWidget can be shown and closed."""
    widget = VTKWidget()
    widget.show()

    # Verify widget is visible
    assert widget.isVisible()
