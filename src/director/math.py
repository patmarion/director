import numpy as np
from scipy.spatial.transform import Rotation


def pos_quat_to_transform(pos_xyz: np.ndarray, quat_wxyz: np.ndarray) -> np.ndarray:
    """
    Create a 4x4 homogeneous transform from position (xyz) and quaternion (wxyz).

    Args:
        pos_xyz: array-like of shape (3,)
        quat_wxyz: array-like of shape (4,) in (w, x, y, z) order

    Returns:
        A 4x4 numpy array representing the homogeneous transformation matrix
    """
    # Convert quaternion from (w, x, y, z) to (x, y, z, w) for scipy
    quat_xyzw = np.array([quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]])
    rot = Rotation.from_quat(quat_xyzw)
    mat = np.eye(4)
    mat[:3, :3] = rot.as_matrix()
    mat[:3, 3] = pos_xyz
    return mat


def pos_euler_to_transform(pos_xyz: np.ndarray, euler_rpy: np.ndarray, euler_mode: str = "XYZ") -> np.ndarray:
    """
    Create a 4x4 homogeneous transform from position (xyz) and Euler angles (rpy).

    Args:
        pos_xyz: array-like of shape (3,)
        euler_rpy: array-like of shape (3,) in (roll, pitch, yaw) order (in radians)
        euler_mode: string specifying the Euler angle convention (default: "XYZ")
                    Common options: "XYZ", "ZYX", "ZYZ", etc.

    Returns:
        A 4x4 numpy array representing the homogeneous transformation matrix
    """
    assert len(pos_xyz) == 3
    assert len(euler_rpy) == 3
    rot = Rotation.from_euler(euler_mode, euler_rpy)
    mat = np.eye(4)
    mat[:3, :3] = rot.as_matrix()
    mat[:3, 3] = pos_xyz
    return mat


def transform_points(pts: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Transform a (N, 3) array of points with a 4x4 transform."""
    pts_hom = np.hstack([pts, np.ones((pts.shape[0], 1))])
    pts_transformed_hom = pts_hom @ transform.T
    return pts_transformed_hom[:, :3]
