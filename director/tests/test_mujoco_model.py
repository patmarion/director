"""Tests for mujoco_model module."""

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
class TestMuJoCoModel:
    """Test MuJoCo model loading and processing."""
    
    @pytest.fixture
    def model(self, test_model_path):
        """Load test model."""
        from director.mujoco_model import load_mjcf_xml
        return load_mjcf_xml(test_model_path)
    
    def test_load_model(self, test_model_path):
        """Test loading a MuJoCo model."""
        from director.mujoco_model import load_mjcf_xml
        
        model = load_mjcf_xml(test_model_path)
        assert model is not None
        assert model.nbody > 0
        assert model.ngeom > 0
    
    def test_print_model_info(self, model, capsys):
        """Test printing model information."""
        from director.mujoco_model import print_model_info
        
        print_model_info(model)
        output = capsys.readouterr().out
        assert "Bodies:" in output
        assert "Geoms:" in output
        assert "Joints:" in output
    
    def test_build_body_to_geom_mapping(self, model):
        """Test building body to geom mapping."""
        from director.mujoco_model import build_body_to_geom_mapping
        
        body_to_geom = build_body_to_geom_mapping(model)
        assert isinstance(body_to_geom, dict)
        assert len(body_to_geom) > 0
        
        # Check that each body maps to at least one geom
        for body_id, geom_ids in body_to_geom.items():
            assert isinstance(geom_ids, list)
            assert len(geom_ids) > 0
            assert all(isinstance(gid, (int, np.integer)) for gid in geom_ids)
    
    def test_print_body_geom_tree(self, model, capsys):
        """Test printing body-geom tree."""
        from director.mujoco_model import build_body_to_geom_mapping, print_body_geom_tree
        
        body_to_geom = build_body_to_geom_mapping(model)
        print_body_geom_tree(model, body_to_geom)
        output = capsys.readouterr().out
        assert "Body-Geom Tree Structure" in output
        assert "BODY:" in output or "GEOM:" in output
    
    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not available")
    def test_forward_kinematics(self, model):
        """Test forward kinematics."""
        from director.mujoco_model import forward_kinematics
        
        body_poses = forward_kinematics(model)
        assert isinstance(body_poses, dict)
        assert len(body_poses) > 0
        
        # Check that all poses are 4x4 matrices
        for body_name, pose in body_poses.items():
            assert isinstance(body_name, str)
            assert pose.shape == (4, 4)
            assert np.allclose(pose[3, :], [0, 0, 0, 1])  # Last row should be [0,0,0,1]
            assert np.allclose(pose[:3, :3] @ pose[:3, :3].T, np.eye(3), atol=1e-6)  # Rotation should be orthonormal
    
    def test_get_geom_pose_in_body(self, model):
        """Test getting geom pose relative to body."""
        from director.mujoco_model import get_geom_pose_in_body
        
        # Test with first geom
        if model.ngeom > 0:
            geom_pose = get_geom_pose_in_body(model, 0)
            assert geom_pose.shape == (4, 4)
            assert np.allclose(geom_pose[3, :], [0, 0, 0, 1])
    
    def test_create_primitive_geom(self, model):
        """Test creating primitive geoms."""
        from director.mujoco_model import create_primitive_geom
        import director.vtkAll as vtk
        
        # Find primitive geoms in the model
        for geom_id in range(model.ngeom):
            geom_type = model.geom_type[geom_id]
            if geom_type in [mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_BOX,
                            mujoco.mjtGeom.mjGEOM_CYLINDER, mujoco.mjtGeom.mjGEOM_CAPSULE,
                            mujoco.mjtGeom.mjGEOM_ELLIPSOID, mujoco.mjtGeom.mjGEOM_PLANE]:
                polyData = create_primitive_geom(model, geom_id)
                assert polyData is not None
                assert isinstance(polyData, vtk.vtkPolyData)
                assert polyData.GetNumberOfPoints() > 0
                break  # Just test one primitive
    
    def test_mj_matrix_to_vtk_transform(self):
        """Test converting MuJoCo matrix to vtkTransform."""
        from director.mujoco_model import mj_matrix_to_vtk_transform
        import director.vtkAll as vtk
        
        # Test identity matrix
        identity = np.eye(4)
        transform = mj_matrix_to_vtk_transform(identity)
        assert isinstance(transform, vtk.vtkTransform)
        
        # Test translation matrix
        translation = np.eye(4)
        translation[:3, 3] = [1, 2, 3]
        transform = mj_matrix_to_vtk_transform(translation)
        pos = transform.GetPosition()
        assert np.allclose(pos, [1, 2, 3], atol=1e-6)
    
    def test_load_geom_mesh(self, model, test_model_path):
        """Test loading geom mesh/geometry."""
        from director.mujoco_model import load_geom_mesh
        import director.vtkAll as vtk
        
        model_dir = os.path.dirname(test_model_path)
        
        # Test with each geom
        for geom_id in range(model.ngeom):
            geom_type = model.geom_type[geom_id]
            # Skip hfield for now
            if geom_type == mujoco.mjtGeom.mjGEOM_HFIELD:
                continue
                
            polyData = load_geom_mesh(model, geom_id, model_dir)
            if polyData is not None:
                assert isinstance(polyData, vtk.vtkPolyData)
                assert polyData.GetNumberOfPoints() > 0
                # If we got one, that's good enough for the test
                break


@pytest.mark.skipif(not MUJOCO_AVAILABLE, reason="MuJoCo not available")
@pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not available")
class TestFullPipeline:
    """Test the full pipeline integration."""
    
    def test_full_pipeline(self, test_model_path):
        """Test the full pipeline: load, FK, visualize."""
        from director.mujoco_model import (
            load_mjcf_xml, build_body_to_geom_mapping, 
            forward_kinematics, load_geom_mesh
        )
        
        # Load model
        model = load_mjcf_xml(test_model_path)
        assert model is not None
        
        # Build mapping
        body_to_geom = build_body_to_geom_mapping(model)
        assert len(body_to_geom) > 0
        
        # Forward kinematics
        body_poses = forward_kinematics(model)
        assert len(body_poses) > 0
        
        # Check that we can load geometry for each geom
        model_dir = os.path.dirname(test_model_path)
        loaded_count = 0
        for body_id in body_to_geom:
            for geom_id in body_to_geom[body_id]:
                geom_type = model.geom_type[geom_id]
                # Skip hfield
                if geom_type == mujoco.mjtGeom.mjGEOM_HFIELD:
                    continue
                geom_data = load_geom_mesh(model, geom_id, model_dir)
                if geom_data is not None:
                    loaded_count += 1
        
        # Should have loaded at least some geometries
        assert loaded_count > 0


@pytest.fixture
def test_model_path():
    """Fixture to provide path to test MJCF XML file."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, 'test_simple_mujoco_model.xml')

