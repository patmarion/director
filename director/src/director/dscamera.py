import json
from functools import lru_cache
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

with_torch = False


class DSCamera(object):
    """DSCamera class. https://github.com/matsuren/dscamera
    V. Usenko, N. Demmel, and D. Cremers, "The Double Sphere Camera Model",
    Proc. of the Int. Conference on 3D Vision (3DV), 2018.
    """

    def __init__(
        self,
        img_size: Tuple[int, int] = (0, 0),
        intrinsic: Optional[Dict[str, float]] = None,
        fov: float = 180,
    ):
        # Fisheye camera parameters
        self.h, self.w = img_size
        self.fx = intrinsic["fx"]
        self.fy = intrinsic["fy"]
        self.cx = intrinsic["cx"]
        self.cy = intrinsic["cy"]
        self.xi = intrinsic["xi"]
        self.alpha = intrinsic["alpha"]
        self.fov = fov
        fov_rad = self.fov / 180 * np.pi
        self.fov_cos = np.cos(fov_rad / 2)
        self.intrinsic_keys = ["fx", "fy", "cx", "cy", "xi", "alpha"]

        # Valid mask for fisheye image
        self._valid_mask = None

    @property
    def img_size(self) -> Tuple[int, int]:
        return self.h, self.w

    @img_size.setter
    def img_size(self, img_size: Tuple[int, int]):
        self.h, self.w = map(int, img_size)

    @property
    def intrinsic(self) -> Dict[str, float]:
        intrinsic = {key: self.__dict__[key] for key in self.intrinsic_keys}
        return intrinsic

    @intrinsic.setter
    def intrinsic(self, intrinsic: Dict[str, float]):
        for key in self.intrinsic_keys:
            self.__dict__[key] = intrinsic[key]

    @property
    def valid_mask(self):
        if self._valid_mask is None:
            # Calculate and cache valid mask
            x = np.arange(self.w)
            y = np.arange(self.h)
            x_grid, y_grid = np.meshgrid(x, y, indexing="xy")
            _, valid_mask = self.cam2world([x_grid, y_grid])
            self._valid_mask = valid_mask

        return self._valid_mask

    def __repr__(self):
        return (
            f"[{self.__class__.__name__}]\n img_size:{self.img_size},fov:{self.fov},\n"
            f" intrinsic:{json.dumps(self.intrinsic, indent=2)}"
        )

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def cam2world(self, point2D):
        """cam2world(point2D) projects a 2D point onto the unit sphere.
        point3D coord: x:right direction, y:down direction, z:front direction
        point2D coord: x:row direction, y:col direction (OpenCV image coordinate)
        Parameters
        ----------
        point2D : numpy array or list([u,v])
            array of point in image
        Returns
        -------
        unproj_pts : numpy array
            array of point on unit sphere
        valid_mask : numpy array
            array of valid mask
        """
        # Case: point2D = list([u, v]) or np.array()
        if isinstance(point2D, (list, np.ndarray)):
            u, v = point2D
        # Case: point2D = list([Scalar, Scalar])
        if not hasattr(u, "__len__"):
            u, v = np.array([u]), np.array([v])

        # Decide numpy or torch
        if isinstance(u, np.ndarray):
            xp = np
        else:
            xp = torch

        mx = (u - self.cx) / self.fx
        my = (v - self.cy) / self.fy
        r2 = mx * mx + my * my

        # Check valid area
        s = 1 - (2 * self.alpha - 1) * r2
        valid_mask = s >= 0
        s[~valid_mask] = 0.0
        mz = (1 - self.alpha * self.alpha * r2) / (
            self.alpha * xp.sqrt(s) + 1 - self.alpha
        )

        mz2 = mz * mz
        k1 = mz * self.xi + xp.sqrt(mz2 + (1 - self.xi * self.xi) * r2)
        k2 = mz2 + r2
        k = k1 / k2

        # Unprojected unit vectors
        if xp == np:
            unproj_pts = k[..., np.newaxis] * np.stack([mx, my, mz], axis=-1)
        else:
            unproj_pts = k.unsqueeze(-1) * torch.stack([mx, my, mz], dim=-1)
        unproj_pts[..., 2] -= self.xi

        # Calculate fov
        unprojected_fov_cos = unproj_pts[..., 2]  # unproj_pts @ z_axis
        fov_mask = unprojected_fov_cos >= self.fov_cos
        valid_mask *= fov_mask
        return unproj_pts, valid_mask

    def world2cam(self, point3D):
        """world2cam(point3D) projects a 3D point on to the image.
        point3D coord: x:right direction, y:down direction, z:front direction
        point2D coord: x:row direction, y:col direction (OpenCV image coordinate).
        Parameters
        ----------
        point3D : numpy array or list([x, y, z])
            array of points in camera coordinate
        Returns
        -------
        proj_pts : numpy array
            array of points in image
        valid_mask : numpy array
            array of valid mask
        """
        x, y, z = point3D[..., 0], point3D[..., 1], point3D[..., 2]
        # Decide numpy or torch
        if isinstance(x, np.ndarray):
            xp = np
        else:
            xp = torch

        # Calculate fov
        point3D_fov_cos = point3D[..., 2]  # point3D @ z_axis
        fov_mask = point3D_fov_cos >= self.fov_cos

        # Calculate projection
        x2 = x * x
        y2 = y * y
        z2 = z * z
        d1 = xp.sqrt(x2 + y2 + z2)
        zxi = self.xi * d1 + z
        d2 = xp.sqrt(x2 + y2 + zxi * zxi)

        div = self.alpha * d2 + (1 - self.alpha) * zxi
        u = self.fx * x / div + self.cx
        v = self.fy * y / div + self.cy

        # Projected points on image plane
        if xp == np:
            proj_pts = np.stack([u, v], axis=-1)
        else:
            proj_pts = torch.stack([u, v], dim=-1)

        # Check valid area
        if self.alpha <= 0.5:
            w1 = self.alpha / (1 - self.alpha)
        else:
            w1 = (1 - self.alpha) / self.alpha
        w2 = w1 + self.xi / xp.sqrt(2 * w1 * self.xi + self.xi * self.xi + 1)
        valid_mask = z > -w2 * d1
        valid_mask *= fov_mask

        return proj_pts, valid_mask

    def _warp_img(self, img, img_pts, valid_mask):
        # Remap
        img_pts = img_pts.astype(np.float32)
        out = cv2.remap(img, img_pts[..., 0], img_pts[..., 1], cv2.INTER_LINEAR)
        out[~valid_mask] = 0.0
        return out

    @lru_cache(maxsize=30)
    def _get_perspective_img_pts_and_valid_mask(self, img_size, f):
        # Generate 3D points
        h, w = img_size
        z = f * min(img_size)
        x = np.arange(w) - w / 2
        y = np.arange(h) - h / 2
        x_grid, y_grid = np.meshgrid(x, y, indexing="xy")
        point3D = np.stack([x_grid, y_grid, np.full_like(x_grid, z)], axis=-1)

        # Project on image plane
        img_pts, valid_mask = self.world2cam(point3D)
        img_pts = img_pts.astype(np.float32)
        return img_pts, valid_mask

    def to_perspective(self, img, img_size=(512, 512), f=0.25):
        img_pts, valid_mask = self._get_perspective_img_pts_and_valid_mask(img_size, f)
        out = self._warp_img(img, img_pts, valid_mask)
        return out

    def to_equirect(self, img, img_size=(256, 512)):
        # Generate 3D points
        h, w = img_size
        phi = -np.pi + (np.arange(w) + 0.5) * 2 * np.pi / w
        theta = -np.pi / 2 + (np.arange(h) + 0.5) * np.pi / h
        phi_xy, theta_xy = np.meshgrid(phi, theta, indexing="xy")

        x = np.sin(phi_xy) * np.cos(theta_xy)
        y = np.sin(theta_xy)
        z = np.cos(phi_xy) * np.cos(theta_xy)
        point3D = np.stack([x, y, z], axis=-1)

        # Project on image plane
        img_pts, valid_mask = self.world2cam(point3D)
        out = self._warp_img(img, img_pts, valid_mask)
        return out

    def from_perspective(self, img_persp, img_size=None, f=0.25):
        """
        Inverse of to_perspective(): warp a perspective (rectified) image
        back into the Double Sphere fisheye image domain.

        Parameters
        ----------
        img_persp : np.ndarray
            Rectified pinhole image (output of to_perspective()).
        img_size : (h, w), optional
            Output size of fisheye image (default: self.img_size).
        f : float
            The 'f' parameter used in to_perspective().

        Returns
        -------
        np.ndarray
            Warped fisheye image.
        """
        if img_size is None:
            h, w = self.img_size
        else:
            h, w = img_size

        # Compute the intrinsics of the perspective image
        h_p, w_p = img_persp.shape[:2]
        map_xy, valid_mask = self._get_from_perspective_img_pts_and_valid_mask(
            (h_p, w_p), img_size, f
        )

        # Remap from perspective to fisheye
        img_fisheye = cv2.remap(
            img_persp, map_xy[..., 0], map_xy[..., 1], interpolation=cv2.INTER_LINEAR
        )

        # Mask out invalid regions
        img_fisheye[~valid_mask] = 0.0
        return img_fisheye

    @lru_cache(maxsize=30)
    def _get_from_perspective_img_pts_and_valid_mask(
        self, input_img_size, output_img_size, f
    ):
        h_p, w_p = input_img_size
        focal = f * min(h_p, w_p)
        fx_p = fy_p = focal
        cx_p = w_p / 2.0
        cy_p = h_p / 2.0

        # Generate pixel grid for fisheye output
        h, w = output_img_size
        x = np.arange(w)
        y = np.arange(h)
        x_grid, y_grid = np.meshgrid(x, y, indexing="xy")

        # Get corresponding 3D rays from fisheye pixels
        dirs, valid_mask = self.cam2world([x_grid, y_grid])

        # Project those 3D directions into the perspective image plane
        X, Y, Z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
        u_p = fx_p * (X / Z) + cx_p
        v_p = fy_p * (Y / Z) + cy_p

        # Stack into mapping coordinates
        map_xy = np.stack([u_p, v_p], axis=-1).astype(np.float32)
        return map_xy, valid_mask
