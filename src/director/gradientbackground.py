"""Gradient background utilities for creating textured gradient backgrounds in VTK views."""

import numpy as np

try:
    from scipy.interpolate import interp1d

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

import director.vtkAll as vtk
from director import vtkNumpy as vnp


def create_radial_gradient(w, h, center=None):
    """Create a radial gradient image.

    Args:
        w: Width of the image
        h: Height of the image
        center: Optional (x, y) center point. Defaults to image center.

    Returns:
        Numpy array of shape (h, w, 1) with distance values
    """
    if center is None:
        center = [int(w / 2), int(h / 2)]
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
    dist_from_center.shape = (h, w, 1)
    return dist_from_center


def cubic_bezier(x1, y1, x2, y2, resolution=500):
    """Create a cubic bezier easing function.

    Args:
        x1, y1: First control point
        x2, y2: Second control point
        resolution: Number of points to sample

    Returns:
        Interpolation function
    """
    if not SCIPY_AVAILABLE:
        # Fallback to linear interpolation
        return lambda x: x

    p0 = np.array([0.0, 0.0])
    p1 = np.array([x1, y1])
    p2 = np.array([x2, y2])
    p3 = np.array([1.0, 1.0])

    def r(t):
        return (1 - t) ** 3 * p0 + 3 * t * (1 - t) ** 2 * p1 + 3 * t**2 * (1 - t) * p2 + t**3 * p3

    xy = np.array([r(t) for t in np.linspace(0, 1, resolution)]).T
    f = interp1d(xy[0], xy[1], kind="linear")
    return f


# Pre-defined easing functions
cubic_inout = cubic_bezier(0.645, 0.045, 0.355, 1)
cubic_out = cubic_bezier(0.215, 0.61, 0.355, 1)
cubic_in = cubic_bezier(0.55, 0.055, 0.675, 0.19)
quad_inout = cubic_bezier(0.455, 0.03, 0.515, 0.955)
quart_inout = cubic_bezier(0.77, 0, 0.175, 1)
quint_inout = cubic_bezier(0.86, 0, 0.07, 1)
circ_inout = cubic_bezier(0.785, 0.135, 0.15, 0.86)
sin_inout = cubic_bezier(0.445, 0.05, 0.55, 0.95)
expo_inout = cubic_bezier(1, 0, 0, 1)
back_inout = cubic_bezier(0.68, -0.55, 0.265, 1.55)
linear_inout = cubic_bezier(0.5, 0.5, 0.5, 0.5)


def get_gradient_img(w, h, c1, c2, center=None, func=None, exp=1.0, invert=False):
    """Create a gradient image with custom easing.

    Args:
        w: Width of the image
        h: Height of the image
        c1: First color as RGB array [0-255]
        c2: Second color as RGB array [0-255]
        center: Optional (x, y) center point
        func: Easing function (defaults to sin_inout)
        exp: Exponent to apply to gradient
        invert: Whether to invert the gradient

    Returns:
        vtkImageData with the gradient
    """
    if func is None:
        func = sin_inout

    img = create_radial_gradient(150, 100, center=(75, 75))
    img = img / img.max()
    if invert:
        img = 1 - img
    img = func(img)
    img = img**exp
    img = (np.array(c1) * (1 - img)) + (np.array(c2) * img)
    return vnp.numpyToImageData(img.astype(np.uint8))


def set_textured_background(view, vtkimg):
    """Set a textured background on a view.

    Args:
        view: VTKWidget view instance
        vtkimg: vtkImageData to use as texture
    """
    tex = vtk.vtkTexture()
    tex.SetInputData(vtkimg)
    ren = view.renderer()
    ren.SetBackgroundTexture(tex)
    ren.TexturedBackgroundOn()
    view.render()


def set_gradient_background(view, c1=None, c2=None, center=None, exp=0.5):
    """Set a radial gradient background on a view.

    Args:
        view: VTKWidget view instance
        c1: Inner color as RGB array [0-255]. Defaults to [40, 40, 45]
        c2: Outer color as RGB array [0-255]. Defaults to [10, 10, 15]
        center: Gradient center point. Defaults to [75, 75]
        exp: Exponent for gradient curve. Defaults to 0.5
    """
    if c1 is None:
        c1 = [40, 40, 45]
    if c2 is None:
        c2 = [10, 10, 15]
    if center is None:
        center = [75, 75]

    img = get_gradient_img(w=150, h=100, center=center, c1=c1, c2=c2, exp=exp)
    set_textured_background(view, img)
