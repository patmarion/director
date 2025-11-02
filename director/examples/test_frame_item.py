"""Test program for FrameItem with frame widget integration."""

import sys
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from qtpy.QtCore import Qt

from director.mainwindow import MainWindow, _setup_signal_handlers
from director.debugVis import DebugData
from director import visualization as vis
from director import objectmodel as om
from director import applogic
from director import vtkAll as vtk


class FrameItemTestWindow(QWidget):
    """Test window with a button to reset the frame."""
    
    def __init__(self, main_window, sphere_obj):
        super().__init__()
        self.main_window = main_window
        self.sphere_obj = sphere_obj
        self.setWindowTitle("Frame Item Test Controls")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        reset_button = QPushButton("Reset Frame to Origin")
        reset_button.clicked.connect(self.reset)
        layout.addWidget(reset_button)
        
        self.setLayout(layout)
        self.setFixedSize(200, 60)
    
    def reset(self):
        """Reset the frame to origin by calling copyFrame with identity transform."""
        child_frame = self.sphere_obj.getChildFrame()
        if child_frame:
            identity_transform = vtk.vtkTransform()
            child_frame.copyFrame(identity_transform)
            print("Frame reset to origin")


def main():
    """Main entry point for the frame item test."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Director 2.0 - Frame Item Test")
    app.setApplicationVersion("2.0.0")
    
    # Setup signal handlers for Ctrl+C
    _setup_signal_handlers(app)
    
    # Create and show main window
    window = MainWindow(window_title="Director 2.0 - Frame Item Test")
    
    # Get the view (VTKWidget) for showing objects
    view = window.vtk_widget
    applogic.setCurrentRenderView(view)
    
    # Create a sphere using DebugData
    d = DebugData()
    d.addSphere([0, 0, 0], radius=0.3)
    polyData = d.getPolyData()
    
    # Show the sphere in the view
    sphere_obj = vis.showPolyData(polyData, 'test_sphere', view=view)
    
    # Add a child frame to the sphere
    child_frame = vis.addChildFrame(sphere_obj)
    
    # Verify child frame was created
    if not child_frame:
        print("ERROR: Failed to create child frame")
        return app.exec_()
    
    # Expand sphere in object model and select child frame
    om.setSelectedObject(sphere_obj.getChildFrame())
    
    print(f"Child frame created: {child_frame.getProperty('Name')}")
    print(f"  Frame visible property: {child_frame.getProperty('Visible')}")
    print(f"  Frame Edit property: {child_frame.getProperty('Edit')}")
    
    # Make the sphere semi-transparent so we can see the frame widget
    sphere_obj.setProperty('Alpha', 0.2)
    
    # Enable frame widget editing
    print("\nSetting Edit=True on frame...")
    child_frame.setProperty('Edit', True)
    print(f"Frame widget Edit property is now: {child_frame.getProperty('Edit')}")
    
    # Test 1: Verify frame widget exists after setting Edit=True
    if hasattr(child_frame, 'frameWidget') and child_frame.frameWidget is not None:
        print("✓ Test 1 PASSED: FrameWidget was created")
        # Check if actors are in renderer
        renderer = view.renderer()
        axis_count = sum(1 for actor in child_frame.frameWidget.axisActors if actor in renderer.GetActors())
        ring_count = sum(1 for actor in child_frame.frameWidget.ringActors if actor in renderer.GetActors())
        print(f"  - Axis actors in renderer: {axis_count}/{len(child_frame.frameWidget.axisActors)}")
        print(f"  - Ring actors in renderer: {ring_count}/{len(child_frame.frameWidget.ringActors)}")
        if axis_count == len(child_frame.frameWidget.axisActors) and ring_count == len(child_frame.frameWidget.ringActors):
            print("✓ Test 2 PASSED: All frame widget actors are in renderer")
        else:
            print("✗ Test 2 FAILED: Not all actors are in renderer")
    else:
        print("✗ Test 1 FAILED: FrameWidget was not created")
    
    # Test 3: Verify frame widget shows even when frame is not visible
    print("\nTest 3: Setting frame Visible=False (widget should still show)")
    child_frame.setProperty('Visible', False)
    if child_frame.frameWidget:
        # Check visibility of actors
        axis_visible = sum(1 for actor in child_frame.frameWidget.axisActors if actor.GetVisibility())
        ring_visible = sum(1 for actor in child_frame.frameWidget.ringActors if actor.GetVisibility())
        print(f"  - Axis actors visible: {axis_visible}/{len(child_frame.frameWidget.axisActors)}")
        print(f"  - Ring actors visible: {ring_visible}/{len(child_frame.frameWidget.ringActors)}")
        if axis_visible == len(child_frame.frameWidget.axisActors) and ring_visible == len(child_frame.frameWidget.ringActors):
            print("✓ Test 3 PASSED: Frame widget is visible even when frame item is not visible")
        else:
            print("✗ Test 3 FAILED: Frame widget actors are not all visible")
    
    # Test 4: Toggle Edit off and on
    print("\nTest 4: Toggling Edit property")
    print("  - Setting Edit=False...")
    child_frame.setProperty('Edit', False)
    if child_frame.frameWidget:
        axis_visible = sum(1 for actor in child_frame.frameWidget.axisActors if actor.GetVisibility())
        ring_visible = sum(1 for actor in child_frame.frameWidget.ringActors if actor.GetVisibility())
        if axis_visible == 0 and ring_visible == 0:
            print("✓ Test 4a PASSED: Frame widget is hidden when Edit=False")
        else:
            print("✗ Test 4a FAILED: Frame widget actors are still visible")
    
    print("  - Setting Edit=True again...")
    child_frame.setProperty('Edit', True)
    view.render()
    if child_frame.frameWidget:
        axis_visible = sum(1 for actor in child_frame.frameWidget.axisActors if actor.GetVisibility())
        ring_visible = sum(1 for actor in child_frame.frameWidget.ringActors if actor.GetVisibility())
        if axis_visible == len(child_frame.frameWidget.axisActors) and ring_visible == len(child_frame.frameWidget.ringActors):
            print("✓ Test 4b PASSED: Frame widget is visible again when Edit=True")
        else:
            print("✗ Test 4b FAILED: Frame widget actors are not all visible")
    
    # Make frame visible again for visual testing
    child_frame.setProperty('Visible', True)
    
    # Move the frame away from origin for testing
    test_transform = vtk.vtkTransform()
    test_transform.Translate(2.0, 1.0, 0.5)
    test_transform.RotateZ(45.0)
    child_frame.copyFrame(test_transform)
    print("Frame moved to (2, 1, 0.5) with 45 degree Z rotation")
    
    # Create a control window with reset button
    control_window = FrameItemTestWindow(window, sphere_obj)
    control_window.show()
    
    # Connect to frame modified signal to verify it's working
    def onFrameModified(frame_item):
        print(f"FrameModified signal received from {frame_item.getProperty('Name')}")
        pos = frame_item.transform.GetPosition()
        print(f"  New position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
    
    child_frame.connectFrameModified(onFrameModified)
    
    # Reset camera
    view.resetCamera()
    view.render()
    
    window.show()
    
    print("\nFrame Item Test Instructions:")
    print("  - The frame widget should be visible (axes and rings)")
    print("  - Drag axes to translate along axis")
    print("  - Drag rings to translate in plane")
    print("  - Right-drag axes to rotate about axis")
    print("  - Right-drag rings to rotate about plane normal")
    print("  - Click 'Reset Frame to Origin' button to jump frame back to origin")
    print("  - The sphere should move with the frame")
    print("  - FrameModified signals should be printed when dragging")
    
    # Run the application
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

