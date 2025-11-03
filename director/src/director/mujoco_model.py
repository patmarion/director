"""MuJoCo model loader and visualization for Director.

This module provides utilities to load MuJoCo MJCF XML files, perform forward
kinematics, and visualize the model geometry in Director using PolyDataItem objects.
"""

import os
import numpy as np
try:
    import mujoco
    MUJOCO_AVAILABLE = True
except ImportError:
    MUJOCO_AVAILABLE = False

try:
    from scipy.spatial.transform import Rotation
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

import director.vtkAll as vtk
from director import transformUtils
from director import ioUtils
from director import visualization as vis
from director import objectmodel as om


def mj_matrix_to_vtk_transform(matrix):
    """
    Convert a MuJoCo 4x4 transformation matrix to a vtkTransform.
    
    Args:
        matrix: numpy array of shape (4, 4) representing a homogeneous transformation matrix
        
    Returns:
        vtk.vtkTransform object
    """
    return transformUtils.getTransformFromNumpy(matrix)


def load_mjcf_xml(xml_path):
    """
    Load a MuJoCo MJCF XML file.
    
    Args:
        xml_path: Path to the MJCF XML file
        
    Returns:
        mjModel: MuJoCo model object
        
    Raises:
        ImportError: If mujoco is not available
        Exception: If file cannot be loaded
    """
    if not MUJOCO_AVAILABLE:
        raise ImportError("MuJoCo is not available. Please install mujoco: pip install mujoco")
    
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"MJCF XML file not found: {xml_path}")
    
    return mujoco.MjModel.from_xml_path(xml_path)


def print_model_info(model):
    """
    Print information about bodies, geoms, joints, and meshes in the model.
    
    Args:
        model: MuJoCo model object
    """
    print("=" * 60)
    print("MuJoCo Model Information")
    print("=" * 60)
    
    print(f"\nBodies: {model.nbody}")
    for i in range(model.nbody):
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, f"body_{i}" if i > 0 else "world")
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
        if body_name:
            print(f"  [{i:3d}] {body_name}")
    
    print(f"\nGeoms: {model.ngeom}")
    for i in range(model.ngeom):
        geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, i)
        geom_type = model.geom_type[i]
        geom_type_name = ['plane', 'hfield', 'sphere', 'capsule', 'ellipse', 'box', 'mesh'][geom_type] if geom_type < 7 else 'unknown'
        if geom_name:
            print(f"  [{i:3d}] {geom_name} (type: {geom_type_name})")
    
    print(f"\nJoints: {model.njnt}")
    for i in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        joint_type = model.jnt_type[i]
        joint_type_name = ['free', 'ball', 'slide', 'hinge'][joint_type]
        if joint_name:
            print(f"  [{i:3d}] {joint_name} (type: {joint_type_name})")
    
    print(f"\nMeshes: {model.nmesh}")
    for i in range(model.nmesh):
        mesh_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, i)
        if mesh_name:
            vert_count = model.mesh_vertnum[i]
            face_count = model.mesh_facenum[i]
            print(f"  [{i:3d}] {mesh_name} ({vert_count} vertices, {face_count} faces)")


def build_body_to_geom_mapping(model):
    """
    Build a dictionary mapping body IDs to their geoms.
    
    Args:
        model: MuJoCo model object
        
    Returns:
        dict: Mapping from body ID to list of geom IDs
    """
    body_to_geom = {}
    for geom_id in range(model.ngeom):
        body_id = model.geom_bodyid[geom_id]
        if body_id not in body_to_geom:
            body_to_geom[body_id] = []
        body_to_geom[body_id].append(geom_id)
    return body_to_geom


def print_body_geom_tree(model, body_to_geom):
    """
    Print the tree structure of bodies and their geoms.
    
    Args:
        model: MuJoCo model object
        body_to_geom: Dictionary mapping body IDs to geom IDs
    """
    print("\n" + "=" * 60)
    print("Body-Geom Tree Structure")
    print("=" * 60)
    
    visited = set()  # Track visited bodies to prevent infinite recursion
    
    def print_body_recursive(body_id, indent=0):
        """Recursively print body and its geoms."""
        # Prevent infinite recursion
        if body_id in visited:
            return
        visited.add(body_id)
        
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        prefix = "  " * indent
        
        if body_name:
            print(f"{prefix}BODY: {body_name} (id: {body_id})")
        else:
            print(f"{prefix}BODY: body_{body_id}")
        
        # Print geoms for this body
        if body_id in body_to_geom:
            for geom_id in body_to_geom[body_id]:
                geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
                geom_type = model.geom_type[geom_id]
                geom_type_name = ['plane', 'hfield', 'sphere', 'capsule', 'ellipse', 'box', 'mesh'][geom_type] if geom_type < 7 else 'unknown'
                if geom_name:
                    print(f"{prefix}  GEOM: {geom_name} (id: {geom_id}, type: {geom_type_name})")
                else:
                    print(f"{prefix}  GEOM: geom_{geom_id} (type: {geom_type_name})")
        
        # Print child bodies (direct children only)
        for child_id in range(model.nbody):
            if model.body_parentid[child_id] == body_id and child_id not in visited:
                print_body_recursive(child_id, indent + 1)
    
    # Start from world body (id 0)
    print_body_recursive(0)


def forward_kinematics(model, qpos=None):
    """
    Perform forward kinematics to compute body poses.
    
    Args:
        model: MuJoCo model object
        qpos: Joint positions (optional, defaults to model default qpos)
        
    Returns:
        dict: Mapping from body name to 4x4 transformation matrix (numpy array)
        
    Raises:
        ImportError: If scipy is not available
    """
    if not SCIPY_AVAILABLE:
        raise ImportError("scipy is required for forward kinematics. Please install: pip install scipy")
    
    # Create data object
    data = mujoco.MjData(model)
    
    # Set joint positions
    if qpos is not None:
        if len(qpos) != model.nq:
            raise ValueError(f"qpos length ({len(qpos)}) must match model.nq ({model.nq})")
        data.qpos[:] = qpos
    else:
        data.qpos[:] = model.qpos0
    
    # Forward kinematics
    mujoco.mj_forward(model, data)
    
    # Build mapping of body name to 4x4 matrix
    body_poses = {}
    
    for body_id in range(model.nbody):
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        
        # Get position and quaternion from MuJoCo
        pos = data.xpos[body_id]
        quat = data.xquat[body_id]  # w, x, y, z format
        
        # Convert quaternion to rotation matrix using scipy
        # scipy uses x, y, z, w format
        rotation = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
        rot_matrix = rotation.as_matrix()
        
        # Build 4x4 transformation matrix
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rot_matrix
        transform_matrix[:3, 3] = pos
        
        # Use body name as key (or generate one if no name)
        if body_name:
            body_poses[body_name] = transform_matrix
        else:
            body_poses[f"body_{body_id}"] = transform_matrix
    
    return body_poses


def get_geom_pose_in_body(model, geom_id):
    """
    Get the pose of a geom relative to its parent body.
    
    Args:
        model: MuJoCo model object
        geom_id: Geom ID
        
    Returns:
        numpy array: 4x4 transformation matrix
    """
    # Get geom pose (position and quaternion)
    geom_pos = model.geom_pos[geom_id]
    geom_quat = model.geom_quat[geom_id]  # w, x, y, z format
    
    # Convert quaternion to rotation matrix
    if SCIPY_AVAILABLE:
        rotation = Rotation.from_quat([geom_quat[1], geom_quat[2], geom_quat[3], geom_quat[0]])
        rot_matrix = rotation.as_matrix()
    else:
        # Fallback: use identity if scipy not available
        rot_matrix = np.eye(3)
    
    # Build 4x4 transformation matrix
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = rot_matrix
    transform_matrix[:3, 3] = geom_pos
    
    return transform_matrix


def mj_mesh_to_vtk_polydata(model, mesh_id):
    """
    Convert MuJoCo mesh data to vtkPolyData.
    
    Args:
        model: MuJoCo model object
        mesh_id: Mesh ID
        
    Returns:
        vtkPolyData: Mesh geometry, or None if conversion fails
    """
    if mesh_id < 0 or mesh_id >= model.nmesh:
        return None
    
    try:
        import director.vtkNumpy as vnp
        
        # Get mesh vertex and face data from MuJoCo
        vert_start = model.mesh_vertadr[mesh_id]
        vert_count = model.mesh_vertnum[mesh_id]
        vertices = model.mesh_vert[vert_start:vert_start + vert_count]
        
        face_start = model.mesh_faceadr[mesh_id]
        face_count = model.mesh_facenum[mesh_id]
        faces = model.mesh_face[face_start:face_start + face_count]
        
        # MuJoCo uses (vertex_count, 3) array for vertices
        # Convert to vtkPolyData using vtkNumpy
        polyData = vnp.numpyToPolyData(vertices)
        
        # Add faces if available
        if face_count > 0 and len(faces.shape) == 2:
            # MuJoCo faces are (n, 3) arrays with vertex indices
            # Convert to VTK cell array format
            cells = vtk.vtkCellArray()
            for face in faces:
                # Handle both int and uint types
                if len(face) == 3:
                    triangle = vtk.vtkTriangle()
                    triangle.GetPointIds().SetId(0, int(face[0]))
                    triangle.GetPointIds().SetId(1, int(face[1]))
                    triangle.GetPointIds().SetId(2, int(face[2]))
                    cells.InsertNextCell(triangle)
            polyData.SetPolys(cells)
        
        return polyData
    except Exception as e:
        print(f"Warning: Failed to convert MuJoCo mesh {mesh_id} to vtkPolyData: {e}")
        return None


def create_primitive_geom(model, geom_id):
    """
    Create vtkPolyData for primitive geoms (sphere, box, cylinder, capsule, ellipsoid).
    
    Args:
        model: MuJoCo model object
        geom_id: Geom ID
        
    Returns:
        vtkPolyData: Primitive geometry, or None if geom is not a primitive type
    """
    geom_type = model.geom_type[geom_id]
    geom_size = model.geom_size[geom_id]
    
    from director.debugVis import DebugData
    
    d = DebugData()
    
    try:
        if geom_type == mujoco.mjtGeom.mjGEOM_SPHERE:
            radius = geom_size[0]
            d.addSphere(center=[0, 0, 0], radius=radius)
            
        elif geom_type == mujoco.mjtGeom.mjGEOM_BOX:
            # geom_size is half-widths
            dimensions = geom_size[:3] * 2.0
            d.addCube(dimensions=dimensions, center=[0, 0, 0])
            
        elif geom_type == mujoco.mjtGeom.mjGEOM_CYLINDER:
            radius = geom_size[0]
            height = geom_size[1] * 2.0  # MuJoCo uses half-height
            # MuJoCo cylinders are along Z-axis by default
            d.addCylinder(center=[0, 0, 0], axis=[0, 0, 1], length=height, radius=radius)
            
        elif geom_type == mujoco.mjtGeom.mjGEOM_CAPSULE:
            radius = geom_size[0]
            height = geom_size[1] * 2.0  # MuJoCo uses half-height
            # MuJoCo capsules are along Z-axis by default
            d.addCapsule(center=[0, 0, 0], axis=[0, 0, 1], length=height, radius=radius)
            
        elif geom_type == mujoco.mjtGeom.mjGEOM_ELLIPSOID:
            # geom_size is half-radii
            radii = geom_size[:3]
            d.addEllipsoid(center=[0, 0, 0], radii=radii)
            
        elif geom_type == mujoco.mjtGeom.mjGEOM_PLANE:
            # Plane is infinite, create a finite representation
            width = 10.0  # Default size for visualization
            height = 10.0
            # MuJoCo plane normal is +Z by default
            d.addPlane(origin=[0, 0, 0], normal=[0, 0, 1], width=width, height=height)
            
        else:
            return None
        
        return d.getPolyData()
    except Exception as e:
        print(f"Warning: Failed to create primitive for geom {geom_id}, type {geom_type}: {e}")
        return None


def load_geom_mesh(model, geom_id, model_dir=None):
    """
    Load mesh geometry for a geom.
    
    For mesh types: tries to convert MuJoCo mesh data directly, then falls back to file loading.
    For primitive types: creates geometry using VTK sources.
    
    Args:
        model: MuJoCo model object
        geom_id: Geom ID
        model_dir: Directory containing mesh files (optional, defaults to model file directory)
        
    Returns:
        vtkPolyData: Mesh geometry, or None if geom cannot be loaded
    """
    geom_type = model.geom_type[geom_id]
    
    # Handle primitive geoms
    if geom_type in [mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_BOX,
                     mujoco.mjtGeom.mjGEOM_CYLINDER, mujoco.mjtGeom.mjGEOM_CAPSULE,
                     mujoco.mjtGeom.mjGEOM_ELLIPSOID, mujoco.mjtGeom.mjGEOM_PLANE]:
        return create_primitive_geom(model, geom_id)
    
    # Handle mesh types
    if geom_type != mujoco.mjtGeom.mjGEOM_MESH:
        return None
    
    mesh_id = model.geom_dataid[geom_id]
    if mesh_id < 0 or mesh_id >= model.nmesh:
        return None
    
    # First, try to convert MuJoCo mesh data directly
    polyData = mj_mesh_to_vtk_polydata(model, mesh_id)
    if polyData is not None:
        return polyData
    
    # Fallback: try to load from file
    try:
        mesh_file_id = model.mesh_fileid[mesh_id]
        if mesh_file_id >= 0 and mesh_file_id < model.nfile:
            # Try to get filename from MuJoCo
            # Note: MuJoCo API for getting filenames may vary by version
            # This is a fallback approach
            mesh_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh_id)
            if mesh_name:
                # Try common mesh file extensions
                for ext in ['.stl', '.obj', '.ply', '.vtp', '.vtk']:
                    mesh_path = os.path.join(model_dir, mesh_name + ext) if model_dir else (mesh_name + ext)
                    if os.path.exists(mesh_path):
                        return ioUtils.readPolyData(mesh_path)
    except Exception:
        pass
    
    return None


def visualize_mujoco_model(model, body_poses, body_to_geom, view, model_dir=None, parent_obj=None):
    """
    Visualize MuJoCo model geoms using PolyDataItem objects, organized by group in folders.
    
    Args:
        model: MuJoCo model object
        body_poses: Dictionary mapping body names to 4x4 transformation matrices
        body_to_geom: Dictionary mapping body IDs to geom IDs
        view: VTK view widget
        model_dir: Directory containing mesh files (optional)
        parent_obj: Parent object in object model (optional)
        
    Returns:
        dict: Mapping from geom IDs to PolyDataItem objects
    """
    if parent_obj is None:
        parent_obj = om.getOrCreateContainer('mujoco_model')
    
    geom_items = {}
    # Dictionary to cache group folders
    group_folders = {}
    
    for body_id in range(model.nbody):
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if not body_name:
            body_name = f"body_{body_id}"
        
        # Get body pose
        if body_name not in body_poses:
            continue
        
        body_pose = body_poses[body_name]
        
        # Process geoms for this body
        if body_id in body_to_geom:
            for geom_id in body_to_geom[body_id]:
                geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
                if not geom_name:
                    geom_name = f"geom_{geom_id}"
                
                # Get geom group (MuJoCo geom groups are integers, typically 0-5)
                geom_group = int(model.geom_group[geom_id])
                
                # Get or create folder for this group
                group_key = f"group_{geom_group}"
                if group_key not in group_folders:
                    group_folders[group_key] = om.getOrCreateContainer(
                        f"Group {geom_group}", 
                        parentObj=parent_obj
                    )
                
                group_folder = group_folders[group_key]
                
                # Get geom pose relative to body
                geom_pose_in_body = get_geom_pose_in_body(model, geom_id)
                
                # Compute geom pose in world frame: body_pose * geom_pose_in_body
                geom_pose_world = body_pose @ geom_pose_in_body
                
                # Load geometry for this geom (mesh or primitive)
                geom_polydata = load_geom_mesh(model, geom_id, model_dir)
                
                if geom_polydata is None:
                    # Skip geoms that can't be loaded
                    continue
                
                # Get geom color and alpha from MuJoCo
                geom_rgba = model.geom_rgba[geom_id]
                # Convert numpy array to Python list for compatibility
                geom_color = [float(geom_rgba[i]) for i in range(3)]  # RGB components [0-1]
                geom_alpha = float(geom_rgba[3])   # Alpha component [0-1]
                
                # Create PolyDataItem for the geometry, adding it to the group folder
                obj = vis.showPolyData(
                    geom_polydata, 
                    geom_name, 
                    view=view, 
                    parent=group_folder,
                    color=geom_color,
                    alpha=geom_alpha
                )
                
                # Set geom pose using child frame
                vtk_transform = mj_matrix_to_vtk_transform(geom_pose_world)
                child_frame = vis.addChildFrame(obj)
                if child_frame:
                    child_frame.copyFrame(vtk_transform)
                
                geom_items[geom_id] = obj
    
    return geom_items


def load_and_visualize_mujoco_model(xml_path, view, qpos=None, parent_obj=None):
    """
    Load a MuJoCo model and visualize it in Director.
    
    This is a convenience function that combines loading, FK, and visualization.
    
    Args:
        xml_path: Path to MJCF XML file
        view: VTK view widget
        qpos: Joint positions (optional)
        parent_obj: Parent object in object model (optional)
        
    Returns:
        tuple: (model, data, body_poses, geom_items)
            - model: MuJoCo model
            - data: MuJoCo data (None if not available)
            - body_poses: Dictionary of body name to 4x4 matrix
            - geom_items: Dictionary of geom ID to PolyDataItem
    """
    # Load model
    model = load_mjcf_xml(xml_path)
    
    # Get model directory for resolving mesh paths
    model_dir = os.path.dirname(os.path.abspath(xml_path))
    
    # Print model information
    print_model_info(model)
    
    # Build body to geom mapping
    body_to_geom = build_body_to_geom_mapping(model)
    
    # Print body-geom tree
    print_body_geom_tree(model, body_to_geom)
    
    # Perform forward kinematics
    body_poses = forward_kinematics(model, qpos=qpos)
    
    # Visualize
    geom_items = visualize_mujoco_model(
        model, body_poses, body_to_geom, view, 
        model_dir=model_dir, parent_obj=parent_obj
    )
    
    # Return data if available
    data = None
    if MUJOCO_AVAILABLE:
        data = mujoco.MjData(model)
        if qpos is not None:
            data.qpos[:] = qpos
        else:
            data.qpos[:] = model.qpos0
        mujoco.mj_forward(model, data)
    
    return model, data, body_poses, geom_items

