"""MuJoCo model loader and visualization for Director.

This module provides utilities to load MuJoCo MJCF XML files, perform forward
kinematics, and visualize the model geometry in Director using PolyDataItem objects.
"""

import copy
import math
import os
from dataclasses import dataclass, field
from typing import Any

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

import director.vtkAll as vtk
from director import filterUtils, ioUtils, transformUtils
from director import objectmodel as om
from director import visualization as vis


class MujocoMeshResolver:
    """
    Resolves mesh names to file paths and provides source geom transforms.

    Uses MjSpec to inspect the parsed-but-not-compiled model so that:
    - Mesh file paths are resolved using modelfiledir + compiler meshdir.
    - Geom transforms reflect the original XML pos/quat/euler values, not the
      compiled values (MuJoCo re-centers mesh vertices during compilation and
      adjusts geom poses to compensate).
    - Include directives are handled automatically by MjSpec.
    """

    def __init__(self):
        self.mesh_name_to_file: dict[str, str] = {}
        # Source (pre-compilation) body-to-geom transforms keyed by geom index.
        self.geom_source_transforms: dict[int, np.ndarray] = {}

    def load_from_spec(self, spec) -> None:
        """Populate mesh file paths and geom source transforms from an MjSpec."""
        self._build_mesh_file_map(spec)
        self._build_geom_source_transforms(spec)

    def resolve_mesh_file(self, mesh_name: str) -> str | None:
        """Resolve a mesh name to its absolute file path, or None if not found."""
        return self.mesh_name_to_file.get(mesh_name)

    def get_geom_source_transform(self, geom_id: int) -> np.ndarray | None:
        """Return the source (pre-compilation) body-to-geom transform."""
        return self.geom_source_transforms.get(geom_id)

    def _build_mesh_file_map(self, spec) -> None:
        """Resolve mesh file paths using spec.modelfiledir and compiler meshdir."""
        base_dir = spec.modelfiledir
        meshdir = spec.compiler.meshdir
        if meshdir:
            if os.path.isabs(meshdir):
                resolved_meshdir = meshdir
            else:
                resolved_meshdir = os.path.normpath(os.path.join(base_dir, meshdir))
        else:
            resolved_meshdir = base_dir

        for mesh in spec.meshes:
            if not mesh.name or not mesh.file:
                continue
            if os.path.isabs(mesh.file):
                abs_path = mesh.file
            else:
                abs_path = os.path.join(resolved_meshdir, mesh.file)
            self.mesh_name_to_file[mesh.name] = os.path.normpath(abs_path)

    def _build_geom_source_transforms(self, spec) -> None:
        """
        Build source transforms from MjSpec for every geom.

        MjSpec preserves the original XML pos/quat/euler values before MuJoCo's
        compilation step.  Iteration order of spec.geoms matches compiled-model
        geom indices.
        """
        is_degree = bool(spec.compiler.degree)
        euler_seq_raw = spec.compiler.eulerseq
        euler_seq = "".join(list(euler_seq_raw)) if euler_seq_raw else "xyz"
        # MuJoCo euler sequences use intrinsic (body-fixed) axes; scipy uses
        # the opposite letter case for intrinsic vs extrinsic.
        scipy_euler_seq = euler_seq.swapcase()

        for geom_id, geom in enumerate(spec.geoms):
            pos = np.array(geom.pos)
            orientation_type = geom.alt.type

            if orientation_type == mujoco.mjtOrientation.mjORIENTATION_EULER:
                euler_vals = np.array(geom.alt.euler)
                if is_degree:
                    euler_vals = np.deg2rad(euler_vals)
                rot = Rotation.from_euler(scipy_euler_seq, euler_vals)
            else:
                # Covers explicit quat AND the default identity case.
                quat_wxyz = np.array(geom.quat)
                quat_xyzw = [quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]]
                rot = Rotation.from_quat(quat_xyzw)

            transform = np.eye(4)
            transform[:3, :3] = rot.as_matrix()
            transform[:3, 3] = pos
            self.geom_source_transforms[geom_id] = transform


def mj_matrix_to_vtk_transform(matrix):
    """
    Convert a MuJoCo 4x4 transformation matrix to a vtkTransform.

    Args:
        matrix: numpy array of shape (4, 4) representing a homogeneous transformation matrix

    Returns:
        vtk.vtkTransform object
    """
    return transformUtils.getTransformFromNumpy(matrix)


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
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
        if body_name:
            print(f"  [{i:3d}] {body_name}")

    print(f"\nGeoms: {model.ngeom}")
    for i in range(model.ngeom):
        geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, i)
        geom_type = model.geom_type[i]
        geom_type_name = (
            ["plane", "hfield", "sphere", "capsule", "ellipse", "box", "mesh"][geom_type]
            if geom_type < 7
            else "unknown"
        )
        if geom_name:
            print(f"  [{i:3d}] {geom_name} (type: {geom_type_name})")

    print(f"\nJoints: {model.njnt}")
    for i in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        joint_type = model.jnt_type[i]
        joint_type_name = ["free", "ball", "slide", "hinge"][joint_type]
        if joint_name:
            print(f"  [{i:3d}] {joint_name} (type: {joint_type_name})")

    print(f"\nMeshes: {model.nmesh}")
    for i in range(model.nmesh):
        mesh = model.mesh(i)
        print(mesh, mesh.name)
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
                geom_type_name = (
                    ["plane", "hfield", "sphere", "capsule", "ellipse", "box", "mesh"][geom_type]
                    if geom_type < 7
                    else "unknown"
                )
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


def forward_kinematics(model, data, qpos):
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

    # Set joint positions
    if len(qpos) != model.nq:
        raise ValueError(f"qpos length ({len(qpos)}) must match model.nq ({model.nq})")
    data.qpos[:] = qpos

    # Forward kinematics
    mujoco.mj_forward(model, data)

    return compute_body_poses(model, data), compute_site_poses(model, data)


def compute_body_poses(model, data):
    body_poses = {}

    for body_id in range(model.nbody):
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        body_name = body_name or f"body_{body_id}"

        pos = data.xpos[body_id]
        rot_matrix = data.xmat[body_id].reshape(3, 3)
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rot_matrix
        transform_matrix[:3, 3] = pos

        body_poses[body_name] = transform_matrix

    return body_poses


def compute_site_poses(model, data):
    site_poses = {}

    for site_id in range(model.nsite):
        site_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SITE, site_id)
        site_name = site_name or f"site_{site_id}"

        pos = data.site_xpos[site_id]
        rot_matrix = data.site_xmat[site_id].reshape(3, 3)
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rot_matrix
        transform_matrix[:3, 3] = pos

        site_poses[site_name] = transform_matrix

    return site_poses


_MUJOCO_DEFAULT_GEOM_RGBA = np.array([0.5, 0.5, 0.5, 1.0])


def resolve_geom_rgba(model, geom_id) -> list[float]:
    """
    Resolve the effective RGBA color for a geom using MuJoCo's compiled material system.

    MuJoCo resolves the full material chain during compilation: geom material > mesh material.
    An explicit geom rgba (differing from the default) overrides any material.
    """
    geom_rgba = model.geom_rgba[geom_id]

    if not np.allclose(geom_rgba, _MUJOCO_DEFAULT_GEOM_RGBA):
        return [float(geom_rgba[i]) for i in range(4)]

    mat_id = model.geom_matid[geom_id]
    if mat_id >= 0:
        mat_rgba = model.mat_rgba[mat_id]
        return [float(mat_rgba[i]) for i in range(4)]

    return [float(geom_rgba[i]) for i in range(4)]


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
    rotation = Rotation.from_quat([geom_quat[1], geom_quat[2], geom_quat[3], geom_quat[0]])
    rot_matrix = rotation.as_matrix()

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
        vertices = model.mesh_vert[vert_start : vert_start + vert_count]

        face_start = model.mesh_faceadr[mesh_id]
        face_count = model.mesh_facenum[mesh_id]
        faces = model.mesh_face[face_start : face_start + face_count]

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


# Global cache for mesh file PolyData
_mesh_file_cache: dict[str, vtk.vtkPolyData] = {}


def load_geom_mesh(model, geom_id, mesh_resolver):
    """
    Load mesh geometry for a geom.

    For mesh types: tries to load from file using mesh resolver, then falls back to direct conversion.
    For primitive types: creates geometry using VTK sources.

    Args:
        model: MuJoCo model object
        geom_id: Geom ID
        model_dir: Directory containing mesh files (optional, deprecated - use mesh_resolver instead)
        mesh_resolver: MujocoMeshResolver instance for resolving mesh file paths (optional)

    Returns:
        vtkPolyData: Mesh geometry, or None if geom cannot be loaded
    """
    geom_type = model.geom_type[geom_id]

    # Handle primitive geoms
    if geom_type in [
        mujoco.mjtGeom.mjGEOM_SPHERE,
        mujoco.mjtGeom.mjGEOM_BOX,
        mujoco.mjtGeom.mjGEOM_CYLINDER,
        mujoco.mjtGeom.mjGEOM_CAPSULE,
        mujoco.mjtGeom.mjGEOM_ELLIPSOID,
        mujoco.mjtGeom.mjGEOM_PLANE,
    ]:
        return create_primitive_geom(model, geom_id)

    # Handle mesh types
    if geom_type != mujoco.mjtGeom.mjGEOM_MESH:
        return None

    mesh_id = model.geom_dataid[geom_id]
    if mesh_id < 0 or mesh_id >= model.nmesh:
        return None

    # Get mesh name
    mesh_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh_id)

    # Try to resolve mesh file using resolver
    if mesh_resolver and mesh_name:
        mesh_file = mesh_resolver.resolve_mesh_file(mesh_name)
        if mesh_file:
            # Check cache first
            if mesh_file in _mesh_file_cache:
                return _mesh_file_cache[mesh_file]

            # Load mesh file
            if os.path.exists(mesh_file):
                print("loading mesh file", mesh_file)
                polyData = ioUtils.readPolyData(mesh_file)
                if not polyData.GetNumberOfPoints():
                    print(f"Error: Mesh file {mesh_file} has no points")

                # print("Loaded", polyData.GetNumberOfPoints(), "points")
                # print("Loaded", polyData.GetNumberOfCells(), "cells")
                if not polyData.GetPointData().GetNormals():
                    polyData = filterUtils.computeNormals(polyData)
                # Cache the result
                _mesh_file_cache[mesh_file] = polyData
                return polyData
            else:
                print(f"Error: Mesh file not found '{mesh_file}' for mesh '{mesh_name}'")
        else:
            print(f"Error: Could not resolve mesh file for mesh name '{mesh_name}'")

    # Fallback: convert MuJoCo mesh data directly
    print(f"Mesh {mesh_id} {mesh_name} not found in mesh resolver, converting to mjMesh tovtkPolyData")
    polyData = mj_mesh_to_vtk_polydata(model, mesh_id)
    if polyData is not None:
        return polyData

    return None


@dataclass
class ShowOptions:
    """Options for controlling how MuJoCo models are visualized."""

    ignore_group_ids: list[int] = field(default_factory=list)
    max_group_id: float = math.inf
    ignore_mocap_bodies: bool = False
    scene_body_names: list[str] = field(default_factory=list)
    ignore_scene_bodies: bool = False
    ignore_body_names: list[str] = field(default_factory=list)
    ignore_geom_names: list[str] = field(default_factory=list)
    finalize_callback = None


def visualize_mujoco_model(model_folder, model, body_to_geom, mesh_resolver, show_options: ShowOptions = None):
    """
    Visualize MuJoCo model geoms using PolyDataItem objects, organized by group in folders.

    Args:
        model: MuJoCo model object
        body_to_geom: Dictionary mapping body IDs to geom IDs
        mesh_resolver: MujocoMeshResolver instance for resolving mesh file paths (optional)

    Returns:
        ObjectModelItem: Folder containing the model, robot, and body frames
    """
    geom_items = {}
    # Dictionary to cache group folders
    group_folders = {}
    # Create Robot folder for Group folders
    robot_folder = om.getOrCreateContainer("Robot", parentObj=model_folder)

    body_frame_folder = om.getOrCreateContainer("Body Frames", parentObj=model_folder)

    if not show_options:
        show_options = ShowOptions()

    # Helper function to check if a body should go in the Scene folder
    def get_is_scene_body(body_id):
        """Check if body should be in Scene folder (floor geom, plane type, or named 'table')."""
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if body_name and body_name in show_options.scene_body_names:
            return True
        if body_id not in body_to_geom:
            return False
        for geom_id in body_to_geom[body_id]:
            geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
            if geom_name and geom_name in show_options.scene_body_names:
                return True
            # if model.geom_type[geom_id] == mujoco.mjtGeom.mjGEOM_PLANE:
            #   return True
        return False

    # Helper function to check if a body is a mocap body
    def get_is_mocap_body(body_id):
        """Check if body is a mocap body."""
        body_info = model.body(body_id)
        return body_info.mocapid.size > 0 and body_info.mocapid[0] >= 0

    for body_id in range(model.nbody):
        is_scene_body = get_is_scene_body(body_id)
        is_mocap_body = get_is_mocap_body(body_id)
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if not body_name:
            body_name = f"body_{body_id}"

        if is_scene_body and show_options.ignore_scene_bodies:
            continue
        if is_mocap_body and show_options.ignore_mocap_bodies:
            continue
        if body_name in show_options.ignore_body_names:
            continue

        frame_obj = vis.showFrame(vtk.vtkTransform(), body_name, parent=body_frame_folder)
        frame_obj.properties.scale = 0.1
        frame_obj.setPropertyAttribute("Edit", "readOnly", True)

        # Process geoms for this body
        if body_id in body_to_geom:
            for geom_id in body_to_geom[body_id]:
                geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
                if geom_name and geom_name in show_options.ignore_geom_names:
                    continue
                geom_group = int(model.geom_group[geom_id])
                if geom_group in show_options.ignore_group_ids or geom_group > show_options.max_group_id:
                    continue
                if not geom_name:
                    geom_name = f"geom_{geom_id}"

                # Determine folder based on special rules, then fall back to geom group
                group_folder = None
                if is_scene_body:
                    folder_name = "Scene"
                    group_key = folder_name
                    parent_for_folder = model_folder
                elif is_mocap_body:
                    folder_name = "mocap"
                    group_key = folder_name
                    parent_for_folder = model_folder
                else:
                    # Get geom group (MuJoCo geom groups are integers, typically 0-5)
                    folder_name = f"Group {geom_group}"
                    group_key = f"group_{geom_group}"
                    parent_for_folder = robot_folder

                # Get or create folder for this group
                if group_key not in group_folders:
                    group_folders[group_key] = om.getOrCreateContainer(folder_name, parentObj=parent_for_folder)

                group_folder = group_folders[group_key]

                geom_type = model.geom_type[geom_id]

                # For mesh geoms use the source (pre-compilation) transform
                # because we load native mesh files whose vertices have not
                # been re-centered by MuJoCo.  For primitives the compiled
                # transform is correct.
                if geom_type == mujoco.mjtGeom.mjGEOM_MESH:
                    geom_pose_in_body = mesh_resolver.get_geom_source_transform(geom_id)
                else:
                    geom_pose_in_body = get_geom_pose_in_body(model, geom_id)

                # Load geometry for this geom (mesh or primitive)
                geom_polydata = load_geom_mesh(model, geom_id, mesh_resolver)
                assert geom_polydata is not None

                if geom_pose_in_body is not None:
                    geom_polydata = filterUtils.transformPolyData(
                        geom_polydata, mj_matrix_to_vtk_transform(geom_pose_in_body)
                    )

                # Resolve color via MuJoCo's compiled material system
                # (handles geom rgba, geom material, and mesh material inheritance)
                geom_rgba = resolve_geom_rgba(model, geom_id)
                geom_color = geom_rgba[:3]
                geom_alpha = geom_rgba[3]

                # Create PolyDataItem for the geometry, adding it to the group folder
                obj = vis.showPolyData(
                    geom_polydata, geom_name, parent=group_folder, color=geom_color, alpha=geom_alpha
                )

                obj.body_name = get_body_name(model, body_id)
                obj.geom_id = geom_id
                prop = obj.actor.GetProperty()
                prop.SetSpecular(0.4)
                prop.SetSpecularPower(40)

                # Set geom pose using child frame
                child_frame = vis.addChildFrame(obj)
                child_frame.setPropertyAttribute("Edit", "readOnly", True)

                geom_items[geom_id] = obj

    # Set visibility to false for Scene, mocap, and Group 3 folders
    for folder_key, folder_obj in group_folders.items():
        if folder_key in ["Scene", "mocap", "group_2", "group_3", "group_4", "group_5"]:
            if folder_obj.hasProperty("Visible"):
                folder_obj.setProperty("Visible", False)
        om.addChildPropertySync(folder_obj)

    body_frame_folder.properties.visible = False
    model_folder.geom_items = geom_items
    if show_options.finalize_callback:
        show_options.finalize_callback(model_folder)
    return model_folder


def get_body_name(model, body_id):
    body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
    body_name = body_name or f"body_{body_id}"
    return body_name


class KinematicsUpdater:
    def __init__(self, model):
        self.model = model
        self.dof_names = model.get_1dof_joint_names()
        self.pending_q_dict = {}
        self.pending_world_T_base = None
        self.body_poses = {}
        self.site_poses = {}
        self.reset()

    def reset(self):
        self.pending_q_dict = {}
        self.pending_world_T_base = None
        self.q_dict = dict[Any, Any](zip(self.dof_names, np.zeros(len(self.dof_names))))
        self.world_T_base = np.eye(4)
        self.body_poses = {}
        self.site_poses = {}

    def push_q_dict(self, q_dict: dict[str, float]):
        self.pending_q_dict.update(q_dict)
        return self

    def push_world_T_base(self, world_T_base: np.ndarray):
        self.pending_world_T_base = world_T_base
        return self

    def commit(self, name_or_folder=None):
        if self.pending_q_dict or self.pending_world_T_base is not None:
            self.q_dict.update(self.pending_q_dict)
            if self.pending_world_T_base is not None:
                self.world_T_base = self.pending_world_T_base
            self.pending_q_dict = {}
            self.pending_world_T_base = None
            body_poses, site_poses = self.model.show_forward_kinematics(self.q_dict, self.world_T_base, name_or_folder)
            self.body_poses = body_poses
            self.site_poses = site_poses


class MujocoRobotModel:
    """
    A class for loading and visualizing MuJoCo robot models in Director.

    This class provides methods to load a MuJoCo model, visualize it, and
    update its pose using forward kinematics.
    """

    def __init__(self, xml_path: str, default_folder_name: str = "mujoco_model"):
        """
        Initialize the MuJoCo robot model.

        Args:
            xml_path: Path to the MJCF XML file
        """
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"MJCF XML file not found: {xml_path}")

        self.xml_path = os.path.abspath(xml_path)
        self.default_folder_name = default_folder_name
        self.spec = mujoco.MjSpec.from_file(xml_path)
        self.model = self.spec.compile()
        self.data = mujoco.MjData(self.model)
        self.kin_cache = {}
        self.mesh_resolver = MujocoMeshResolver()
        self.mesh_resolver.load_from_spec(self.spec)
        self.body_to_geom = build_body_to_geom_mapping(self.model)
        self._create_joint_properties_item()

        self.default_show_options = ShowOptions()
        self.default_show_options.scene_body_names.extend(["table", "floor"])
        self.named_show_options = {}

    def get_kinematics_cache(self, name):
        cache = self.kin_cache.get(name)
        if not cache:
            cache = KinematicsUpdater(self)
            self.kin_cache[name] = cache
        return cache

    def get_default_show_options(self) -> ShowOptions:
        return copy.deepcopy(self.default_show_options)

    def set_show_options(self, name: str, show_options: ShowOptions):
        self.named_show_options[name] = show_options

    def get_body_names(self) -> list[str]:
        """
        Get a list of all body names in the model.

        Returns:
            List of body names
        """
        body_names = []
        for body_id in range(self.model.nbody):
            body_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, body_id)
            body_name = body_name or f"body_{body_id}"
            body_names.append(body_name)
        return body_names

    def get_joint_names(self) -> list[str]:
        """
        Get a list of all joint names in the model.

        Returns:
            List of joint names
        """
        joint_names = []
        for joint_id in range(self.model.njnt):
            joint_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if joint_name:
                joint_names.append(joint_name)
        return joint_names

    def get_1dof_joint_names(self) -> list[str]:
        """
        Get a list of 1 DOF joint names (hinge and slide joints).

        Returns:
            List of 1 DOF joint names
        """
        joint_names = []
        for joint_id in range(self.model.njnt):
            joint_type = self.model.jnt_type[joint_id]
            # Only include hinge and slide joints (1 DOF)
            if joint_type in [mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE]:
                joint_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
                if joint_name:
                    joint_names.append(joint_name)
        return joint_names

    def get_joint_ranges(self) -> dict[str, tuple[float, float]]:
        """
        Get joint position ranges (min, max) for all 1 DOF joints.

        Returns:
            Dictionary mapping joint names to (min, max) tuples
        """
        ranges = {}
        for joint_id in range(self.model.njnt):
            joint_type = self.model.jnt_type[joint_id]
            # Only include hinge and slide joints (1 DOF)
            if joint_type in [mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE]:
                joint_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
                if joint_name:
                    # Get range from joint limits
                    range_min = self.model.jnt_range[joint_id, 0]
                    range_max = self.model.jnt_range[joint_id, 1]
                    ranges[joint_name] = (float(range_min), float(range_max))
        return ranges

    def get_model_folder(self, name_or_folder=None, show_options: ShowOptions = None):
        if name_or_folder is None:
            name_or_folder = self.default_folder_name
        if isinstance(name_or_folder, str):
            folder = om.getOrCreateContainer(name_or_folder)
            if not show_options:
                show_options = self.named_show_options.get(name_or_folder)
        elif isinstance(name_or_folder, om.ObjectModelItem):
            folder = name_or_folder
        else:
            raise ValueError(f"Invalid type for name_or_folder: {type(name_or_folder)}")
        if not folder.children():
            self._populate_model_folder(folder, show_options)
        folder.robot_model = self
        return folder

    def _populate_model_folder(self, model_folder, show_options: ShowOptions = None):
        show_options = show_options or self.get_default_show_options()
        visualize_mujoco_model(model_folder, self.model, self.body_to_geom, self.mesh_resolver, show_options)

    def show_model(self, name_or_folder=None):
        """
        Visualize the model with the default zero pose.
        """
        return self.show_forward_kinematics({}, name_or_folder=name_or_folder)

    def show_forward_kinematics(
        self, q_dict: dict[str, float], world_T_base: np.ndarray | None = None, name_or_folder=None
    ):
        """
        Update the model pose using forward kinematics with specified joint positions.

        Args:
            q_dict: Dictionary mapping joint names to joint positions.
                   Can contain a subset of joints; unspecified joints use previous values.
            world_T_base: Optional 4x4 numpy array representing world_T_base transform.
                        If None, uses identity matrix. If not provided, uses previous value.
        """
        model_folder = self.get_model_folder(name_or_folder)

        q = np.zeros(self.model.nq)

        # Fill in specified joint positions
        for joint_name, joint_value in q_dict.items():
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if joint_id < 0:
                print(f"Warning: Joint '{joint_name}' not found in model")
                continue

            # Get qpos address for this joint
            qpos_addr = self.model.jnt_qposadr[joint_id]
            joint_type = self.model.jnt_type[joint_id]

            # Handle different joint types
            if joint_type == mujoco.mjtJoint.mjJNT_FREE:
                # Free joint has 7 DOF (3 pos + 4 quat)
                if isinstance(joint_value, (list, tuple, np.ndarray)) and len(joint_value) == 7:
                    q[qpos_addr : qpos_addr + 7] = joint_value
                else:
                    print(f"Warning: Free joint '{joint_name}' requires 7 values (pos[3] + quat[4])")
            elif joint_type == mujoco.mjtJoint.mjJNT_BALL:
                # Ball joint has 4 DOF (quaternion)
                if isinstance(joint_value, (list, tuple, np.ndarray)) and len(joint_value) == 4:
                    q[qpos_addr : qpos_addr + 4] = joint_value
                else:
                    print(f"Warning: Ball joint '{joint_name}' requires 4 values (quaternion)")
            else:
                # Hinge or slide joint has 1 DOF
                q[qpos_addr] = float(joint_value)

        # Handle world_T_base transform
        if world_T_base is None:
            world_T_base = np.eye(4)
        else:
            # Validate shape
            if world_T_base.shape != (4, 4):
                raise ValueError(f"world_T_base must be a 4x4 matrix, got shape {world_T_base.shape}")

        # Perform forward kinematics (returns base_T_body transforms)
        base_T_body_poses, base_T_site_poses = forward_kinematics(self.model, self.data, q)

        if np.array_equal(world_T_base, np.eye(4)):
            body_poses = base_T_body_poses
            site_poses = base_T_site_poses
        else:
            body_poses = {}
            for body_name, base_T_body in base_T_body_poses.items():
                world_T_body = world_T_base @ base_T_body
                body_poses[body_name] = world_T_body

            site_poses = {}
            for site_name, base_T_site in base_T_site_poses.items():
                world_T_site = world_T_base @ base_T_site
                site_poses[site_name] = world_T_site

        # Apply body poses to geom items
        self._update_body_frames(body_poses, model_folder)
        model_folder.site_poses = site_poses
        model_folder.body_poses = body_poses
        return body_poses, site_poses

    def get_site_names(self) -> list[str]:
        return [mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_SITE, i) for i in range(self.model.nsite)]

    def get_site_body_name(self, site_name: str) -> str:
        site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, site_name)
        parent_body_id = self.model.site_bodyid[site_id]
        return mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, parent_body_id)

    def get_body_T_site(self, site_name: str) -> np.ndarray:
        site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, site_name)
        pos = self.model.site_pos[site_id]
        rot_matrix_3x3 = self.model.site_mat[site_id].reshape(3, 3)

        body_T_site = np.eye(4)
        body_T_site[:3, :3] = rot_matrix_3x3
        body_T_site[:3, 3] = pos
        return body_T_site

    def _update_body_frames(self, body_poses, model_folder):
        vtk_frames = {body_name: mj_matrix_to_vtk_transform(body_pose) for body_name, body_pose in body_poses.items()}
        # update geom frames
        for geom_item in model_folder.geom_items.values():
            # if the item has been removed then skip it
            # todo, don't store these items in a dict, look them up as needed
            if not geom_item._tree:
                continue
            world_T_body = vtk_frames[geom_item.body_name]
            geom_item.getChildFrame().copyFrame(world_T_body)

        # update body frames
        body_frame_folder = model_folder.findChild("Body Frames")
        if body_frame_folder:
            for body_name, world_T_body in vtk_frames.items():
                frame_obj = body_frame_folder.findChild(body_name)
                if frame_obj:
                    frame_obj.copyFrame(world_T_body)

    def _create_joint_properties_item(self):
        """Create an ObjectModelItem with properties for each 1 DOF joint."""
        # Create the item
        self.joint_properties_item = om.ObjectModelItem("MuJoCo Joints")

        # Get 1 DOF joint names and ranges
        joint_names = self.get_1dof_joint_names()
        joint_ranges = self.get_joint_ranges()

        # Get initial joint positions from qpos0
        initial_qpos = {}
        for joint_name in joint_names:
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if joint_id >= 0:
                qpos_addr = self.model.jnt_qposadr[joint_id]
                initial_qpos[joint_name] = float(self.model.qpos0[qpos_addr])

        # Add properties for each joint
        for joint_name in joint_names:
            initial_value = initial_qpos.get(joint_name, 0.0)
            range_min, range_max = joint_ranges.get(joint_name, (-np.inf, np.inf))

            # Create property attributes with range
            attrs = om.PropertyAttributes(minimum=range_min, maximum=range_max, decimals=4, singleStep=0.01)
            self.joint_properties_item.addProperty(joint_name, initial_value, attributes=attrs)

        # Connect property changed callback
        self.joint_properties_item.properties.connectPropertyChanged(self._on_joint_property_changed)

    def _on_joint_property_changed(self, propertySet, propertyName):
        """Callback when a joint property is changed."""
        # Build q_dict from all joint properties
        q_dict = {}
        for joint_name in self.get_1dof_joint_names():
            if self.joint_properties_item.hasProperty(joint_name):
                q_dict[joint_name] = self.joint_properties_item.getProperty(joint_name)

        # Update forward kinematics
        self.show_forward_kinematics(q_dict)

    def print_model_info(self):
        model = self.model
        print_model_info(self.model)

        print("\n" + "=" * 60)
        print(f"  Num bodies: {model.nbody}")
        print(f"  Num geoms: {model.ngeom}")
        print(f"  Joint names: {self.get_joint_names()}")
        print(f"  1 DOF joints: {self.get_1dof_joint_names()}")
        print("=" * 60)

    def print_body_poses(self):
        """
        Print the pose of each body in world and base (body 0) frames.
        World-to-body: the pose in world coordinates.
        Base-to-body: the pose in body 0 (world) coordinates.
        """
        model = self.model
        data = self.data

        # For MuJoCo, body 0 is always the world
        print("=" * 60)
        print("MuJoCo Body Poses")
        print("=" * 60)
        print(
            "{:>3}  {:<30} {:>10} {:>10} {:>10} {:>10} {:>10} {:>10}".format(
                "ID", "Body Name", "X [world]", "Y [world]", "Z [world]", "X [base]", "Y [base]", "Z [base]"
            )
        )

        base_pos = data.xpos[0].copy()
        base_mat = data.xmat[0].reshape(3, 3).copy()

        for body_id in range(model.nbody):
            body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
            body_pos = data.xpos[body_id]  # World position of body origin

            # Compute base-to-body transform: base_T_body = inv(base_M) dot body_M
            # For position: p_base = R_base^T @ (p_body - p_base)
            rel_pos = np.dot(base_mat.T, body_pos - base_pos)

            print(
                "{:>3}  {:<30} {:10.4f} {:10.4f} {:10.4f} {:10.4f} {:10.4f} {:10.4f}".format(
                    body_id,
                    body_name if body_name is not None else f"body_{body_id}",
                    body_pos[0],
                    body_pos[1],
                    body_pos[2],
                    rel_pos[0],
                    rel_pos[1],
                    rel_pos[2],
                )
            )
        print("=" * 60)
