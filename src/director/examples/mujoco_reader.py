"""Interactive example for loading and visualizing MuJoCo models in Director.

This demonstrates loading a MuJoCo MJCF XML file, performing forward kinematics,
and visualizing the model geometry using PolyDataItem objects.
"""

import argparse
import os
import sys

import qtpy.QtCore as QtCore

from director import applogic, mainwindowapp, mujoco_model


def main():
    """Main entry point for the MuJoCo model visualization example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Load and visualize a MuJoCo MJCF model in Director",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model-path path/to/model.xml
        """,
    )

    parser.add_argument("--model-path", dest="model_path", default=None, help="Path to MuJoCo MJCF XML file")

    # Parse arguments (using parse_known_args to handle any remaining args)
    args = parser.parse_args()

    # argutils.add_standard_args(parser)

    # Get path to model file
    if args.model_path:
        model_path = args.model_path
    else:
        # Use the test model from tests directory as default
        test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "../../tests")
        model_path = os.path.join(test_dir, "test_simple_mujoco_model.xml")

    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        parser.print_help()
        sys.exit(1)

    fields = mainwindowapp.construct()

    print(f"Loading MuJoCo model from: {model_path}")
    print("=" * 60)

    # Create and visualize the robot model
    robot_model = mujoco_model.MujocoRobotModel(model_path)
    robot_model.show_model()

    # Create properties panel for joint control
    joint_properties_panel = None
    show_joint_properties = False
    if show_joint_properties:
        from director.propertiespanel import PropertiesPanel

        joint_properties_panel = PropertiesPanel()
        joint_properties_panel.setWindowTitle("MuJoCo Joint Control")
        joint_properties_panel.connectProperties(robot_model.joint_properties_item.properties)
        fields.app.addWidgetToDock(joint_properties_panel, QtCore.Qt.RightDockWidgetArea, visible=True)

    # Add to fields for access in console
    fields._add_fields(robot_model=robot_model, joint_properties_panel=joint_properties_panel)

    # Reset camera to view the model
    applogic.resetCamera(viewDirection=[-1, -1, -0.3])

    fields.app.start()


if __name__ == "__main__":
    main()
