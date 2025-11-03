"""Interactive example for loading and visualizing MuJoCo models in Director.

This demonstrates loading a MuJoCo MJCF XML file, performing forward kinematics,
and visualizing the model geometry using PolyDataItem objects.
"""

import sys
import os
import argparse
from qtpy.QtWidgets import QApplication

from director import mainwindowapp
from director import mujoco_model
from director import applogic
from director import argutils


def main():
    """Main entry point for the MuJoCo model visualization example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Load and visualize a MuJoCo MJCF model in Director',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --model-path path/to/model.xml
        '''
    )

    parser.add_argument(
        '--model-path',
        dest='model_path',
        default=None,
        help='Path to MuJoCo MJCF XML file'
    )
    
    # Add standard Director arguments
    argutils.add_standard_args(parser)
    
    # Parse arguments (using parse_known_args to handle any remaining args)
    args = parser.parse_known_args()[0]
    
    # Check if MuJoCo is available
    if not mujoco_model.MUJOCO_AVAILABLE:
        print("Error: MuJoCo is not available.")
        print("Please install mujoco: pip install mujoco")
        sys.exit(1)
    
    # Check if scipy is available
    if not mujoco_model.SCIPY_AVAILABLE:
        print("Warning: scipy is not available. Forward kinematics will fail.")
        print("Please install scipy: pip install scipy")
    
    # Construct the main window using component factory with command line args
    fields = mainwindowapp.construct(
        command_line_args=args,
        windowTitle="Director 2.0 - MuJoCo Model Visualization"
    )
    
    # Get the view from fields
    view = fields.view
    applogic.setCurrentRenderView(view)
    
    # Get path to model file
    if args.model_path:
        model_path = args.model_path
    else:
        # Use the test model from tests directory as default
        test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests')
        model_path = os.path.join(test_dir, 'test_simple_mujoco_model.xml')
    
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        parser.print_help()
        sys.exit(1)
    
    print(f"Loading MuJoCo model from: {model_path}")
    print("=" * 60)
    
    # Load and visualize the model
    try:
        model, data, body_poses, geom_items = mujoco_model.load_and_visualize_mujoco_model(
            model_path, 
            view,
            qpos=None,  # Use default joint positions
            parent_obj=None
        )
        
        print("\n" + "=" * 60)
        print(f"Successfully loaded and visualized model")
        print(f"  Bodies: {model.nbody}")
        print(f"  Geoms: {model.ngeom}")
        print(f"  Visualized geoms: {len(geom_items)}")
        print("=" * 60)
        
        # Print available body poses
        if body_poses:
            print("\nBody poses (forward kinematics):")
            for body_name, pose in sorted(body_poses.items()):
                pos = pose[:3, 3]
                print(f"  {body_name}: position = [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")
        
    except Exception as e:
        print(f"Error loading/visualizing model: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Reset camera to view the model
    applogic.resetCamera(viewDirection=[-1, -1, -0.3], view=view)
    
    # Start the application (shows main window and enters event loop)
    fields.app.start()


if __name__ == "__main__":
    main()

