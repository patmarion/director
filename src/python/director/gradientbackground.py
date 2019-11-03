from director import vtkNumpy as vnp
from director import vtkAll as vtk

from scipy.interpolate import interp1d
import numpy as np


def create_img(w, h, center=None):
    if center is None:
        center = [int(w/2), int(h/2)]
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0])**2 + (y-center[1])**2)
    dist_from_center.shape = (h, w, 1)
    return dist_from_center


def cubic_bezier(x1, y1, x2, y2, resolution=500):
    p0 = np.array([0.0, 0.0])
    p1 = np.array([x1, y1])
    p2 = np.array([x2, y2])
    p3 = np.array([1.0, 1.0])
    def r(t):
        return (1-t)**3 * p0 + 3 * t * (1-t)**2 * p1 + 3 * t**2 * (1-t) * p2 + t**3 * p3
    xy = np.array([r(t) for t in np.linspace(0, 1, resolution)]).T
    f = interp1d(xy[0], xy[1], kind='linear')
    return f


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


def get_gradient_img(w, h, c1, c2, center=None, func=sin_inout, exp=1.0, invert=False):
    img = create_img(150, 100, center=(75, 75))
    img /= img.max()
    if invert:
        img = 1 - img
    img = func(img)
    img = img ** exp
    img = (c1 * (1-img)) + (c2 * img)
    return vnp.numpyToImageData(img.astype(np.uint8))


def set_textured_background(view, vtkimg):
    tex = vtk.vtkTexture()
    tex.SetInputData(vtkimg)
    ren = view.renderer()
    ren.SetBackgroundTexture(tex)
    ren.TexturedBackgroundOn()
    view.render()


def set_gradient_background(view):
    img = get_gradient_img(w=150, h=100, center=[75, 75], c1=[40, 40, 45], c2=[10, 10, 15], exp=0.5)
    set_textured_background(view, img)
