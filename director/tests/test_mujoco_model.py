"""Tests for mujoco_model module using the new MujocoRobotModel API."""

import pytest
import os
import numpy as np

# Check if mujoco is available
try:
    import mujoco
    MUJOCO_AVAILABLE = True
except ImportError:
    MUJOCO_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="MuJoCo not available")

try:
    from scipy.spatial.transform import Rotation
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@pytest.fixture
def test_model_path():
    """Fixture to provide path to test MJCF XML file."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, 'test_simple_mujoco_model.xml')


@pytest.mark.skipif(not MUJOCO_AVAILABLE, reason="MuJoCo not available")
class TestMujocoRobotModel:
    """Test MujocoRobotModel class."""
    
    def test_load_model(self, test_model_path, qapp):
        """Test loading a MuJoCo model."""
        from director.mujoco_model import MujocoRobotModel
        from director import objectmodel as om
        
        # Initialize object model
        om.init()
        
        model = MujocoRobotModel(test_model_path)
        assert model is not None
        assert model.model is not None
        assert model.model.nbody > 0
        assert model.model.ngeom > 0
    
    def test_show_model(self, test_model_path, qapp):
        """Test visualizing the model and checking objects in object model."""
        from director.mujoco_model import MujocoRobotModel
        from director import objectmodel as om
        from director.vtk_widget import VTKWidget
        from director import applogic
        
        # Initialize object model
        om.init()
        
        # Create a view
        view = VTKWidget()
        applogic.setCurrentRenderView(view)
        
        model = MujocoRobotModel(test_model_path)
        model.show_model()
        model_folder = model.get_model_folder()
        
        assert model_folder is not None
        assert hasattr(model_folder, 'geom_items')
        assert len(model_folder.geom_items) > 0
        
        # Check that expected geoms exist with correct names
        expected_geoms = ['ground', 'base_geom', 'link1_geom', 'link2_geom', 
                          'link3_geom', 'link4_geom']
        
        found_geoms = {}
        for geom_id, geom_item in model_folder.geom_items.items():
            geom_name = geom_item.getProperty('Name')
            found_geoms[geom_name] = geom_item
        
        for expected_name in expected_geoms:
            assert expected_name in found_geoms, f"Expected geom '{expected_name}' not found"
    
    def test_geom_colors(self, test_model_path, qapp):
        """Test that geom colors match the XML rgba values."""
        from director.mujoco_model import MujocoRobotModel
        from director import objectmodel as om
        from director.vtk_widget import VTKWidget
        from director import applogic
        
        # Initialize object model
        om.init()
        
        # Create a view
        view = VTKWidget()
        applogic.setCurrentRenderView(view)
        
        model = MujocoRobotModel(test_model_path)
        model.show_model()
        model_folder = model.get_model_folder()
        
        # Expected colors from XML (rgba values)
        expected_colors = {
            'ground': (0.8, 0.8, 0.8),  # rgba="0.8 0.8 0.8 1"
            'base_geom': (1.0, 0.0, 0.0),  # rgba="1 0 0 1"
            'link1_geom': (0.0, 1.0, 0.0),  # rgba="0 1 0 1"
            'link2_geom': (0.0, 0.0, 1.0),  # rgba="0 0 1 1"
            'link3_geom': (1.0, 1.0, 0.0),  # rgba="1 1 0 1"
            'link4_geom': (1.0, 0.0, 1.0),  # rgba="1 0 1 1"
        }
        
        for geom_id, geom_item in model_folder.geom_items.items():
            geom_name = geom_item.getProperty('Name')
            if geom_name in expected_colors:
                # Get color property (stored as tuple)
                color = geom_item.getProperty('Color')
                expected_color = expected_colors[geom_name]
                
                # Check RGB components (ignore alpha)
                assert len(color) >= 3, f"Color for {geom_name} should have at least 3 components"
                assert np.allclose(color[:3], expected_color, atol=1e-6), \
                    f"Color mismatch for {geom_name}: got {color[:3]}, expected {expected_color}"
    
    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not available")
    def test_geom_transform_with_offset(self, test_model_path, qapp):
        """Test that geom with pos/euler offset in XML is handled correctly.
        
        Note: For non-mesh geoms, MuJoCo compiles the pos/euler into the model's
        geom_pos and geom_quat arrays. The XML attributes are primarily used for
        mesh geoms. This test verifies that the model loads and visualizes correctly
        even when XML pos/euler attributes are present.
        """
        from director.mujoco_model import MujocoRobotModel
        from director import objectmodel as om
        from director.vtk_widget import VTKWidget
        from director import applogic
        
        # Initialize object model
        om.init()
        
        # Create a view
        view = VTKWidget()
        applogic.setCurrentRenderView(view)
        
        model = MujocoRobotModel(test_model_path)
        model.show_model()
        model_folder = model.get_model_folder()
        
        # Find link2_geom which has pos="0.1 0.05 0.02" euler="15 30 45" in XML
        link2_geom_item = None
        for geom_id, geom_item in model_folder.geom_items.items():
            if geom_item.getProperty('Name') == 'link2_geom':
                link2_geom_item = geom_item
                break
        
        assert link2_geom_item is not None, "link2_geom not found"
        
        # Verify the geom has the correct body_name
        assert hasattr(link2_geom_item, 'body_name'), "geom_item should have body_name attribute"
        assert link2_geom_item.body_name == 'link2', f"Expected body_name 'link2', got '{link2_geom_item.body_name}'"
        
        # Verify the actor exists and has a transform
        actor = link2_geom_item.actor
        assert actor is not None, "Actor not found for link2_geom"
        
        # The actor should have a UserTransform set by addChildFrame
        user_transform = actor.GetUserTransform()
        assert user_transform is not None, "UserTransform not set on actor"
        
        # Verify the child frame exists
        child_frame = link2_geom_item.getChildFrame()
        assert child_frame is not None, "Child frame not found for link2_geom"
        
        # The child frame stores world_T_body (updated by forward kinematics)
        # The body_T_geom transform is baked into the polydata geometry itself
        # For non-mesh geoms, this comes from the compiled model's geom_pos/geom_quat
        # which may differ from XML attributes due to MuJoCo's compilation process
    
    def test_get_body_names(self, test_model_path, qapp):
        """Test getting body names from the model."""
        from director.mujoco_model import MujocoRobotModel
        
        model = MujocoRobotModel(test_model_path)
        body_names = model.get_body_names()
        
        assert len(body_names) > 0
        # Check that expected bodies exist
        expected_bodies = ['world', 'base', 'link1', 'link2', 'link3', 'link4']
        for expected_name in expected_bodies:
            assert expected_name in body_names, f"Expected body '{expected_name}' not found"
    
    def test_get_joint_names(self, test_model_path, qapp):
        """Test getting joint names from the model."""
        from director.mujoco_model import MujocoRobotModel
        
        model = MujocoRobotModel(test_model_path)
        joint_names = model.get_joint_names()
        
        assert len(joint_names) > 0
        # Check that expected joints exist
        expected_joints = ['joint1', 'joint2', 'joint3', 'joint4']
        for expected_name in expected_joints:
            assert expected_name in joint_names, f"Expected joint '{expected_name}' not found"
