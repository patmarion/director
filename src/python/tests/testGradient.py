from scipy.interpolate import interp1d
import numpy as np



def create_img(w, h, center=None):
    if center is None:
        center = [int(w/2), int(h/2)]
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0])**2 + (y-center[1])**2)
    dist_from_center.shape = (h, w, 1)
    return dist_from_center


def cubic_bezier(x1, y1, x2, y2, resolution=1000):
    p0 = np.array([0.0, 0.0])
    p1 = np.array([x1, y1])
    p2 = np.array([x2, y2])
    p3 = np.array([1.0, 1.0])
    def R(t):
        return (1-t)**3 * p0 + 3 * t * (1-t)**2 * p1 + 3 * t**2 * (1-t) * p2 + t**3 * p3
    xy = np.array([R(t) for t in np.linspace(0, 1, 500)]).T
    f = interp1d(xy[0], xy[1], kind='linear')
    return f



#img = create_img(100, 150, center=(50, 85))
img = create_img(150, 100, center=(75, 75))
#img = create_img(100, 100)

img = (1 - (img / img.max()))

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


f = sin_inout

img = f(img)

#img = (np.sin(  img*np.pi - np.pi/2.0  ) + 1) * 0.5



img = img ** 0.5



c1 = [80, 80, 85]
c2 = [10, 10, 15]

colorimg = (c1 * img) + (c2 * (1-img))

vtkimg = vnp.numpyToImageData(colorimg)


tex = vtk.vtkTexture()
tex.SetInputData(vtkimg)
ren = view.renderer()
ren.SetBackgroundTexture(tex)
ren.TexturedBackgroundOn()
view.render()



viewBackgroundLightHandler.toggle()




