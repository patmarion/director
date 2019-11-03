import os
import math
import numpy as np
import urllib.request
import functools

try:
  import pyproj
  HAVE_PYPROJ = True
except ImportError:
  HAVE_PYPROJ  = False


from director.debugVis import DebugData
from director import visualization as vis
from director import mainwindowapp
from director import vtkNumpy as vnp
from director import ioUtils
from director import applogic
from director import segmentationroutines
from director import objectmodel as om
from director import transformUtils
from director import filterUtils
from director import vtkAll as vtk
from director.taskrunner import TaskRunner
from director.thirdparty import osm_utils


class PyProjCoordinates(object):

  def __init__(self):
    self.proj_ecef = pyproj.Proj(proj='geocent', ellps='WGS84')
    self.proj_lla = pyproj.Proj(proj='latlong', ellps='WGS84')
    self.proj_utm = pyproj.Proj(proj='utm', zone=10, ellps='WGS84')
    self.transform = pyproj.transform

  def lat_lon_to_utm(self, lat, lon):
    e, n = self.proj_utm(lon, lat)
    return np.array([e, n, 0.0])

  def lat_lon_to_ecef(self, lat, lon, alt=0.0):
    return self.transform(self.proj_lla, self.proj_ecef, lon, lat, alt, radians=False)

  def ecef_to_lat_lon(self, pos):
    lon, lat, alt = self.transform(self.proj_ecef, self.proj_lla, pos[0], pos[1], pos[2])
    return lat, lon

  def utm_to_lat_lon(self, easting, northing):
    lon, lat = self.proj_utm(easting, northing, inverse=True)
    return lat, lon

  def init_utm_offset(self, x, y, zoom):
    s, w, n, e = osm_utils.tileEdges(x, y, zoom)
    e, n, alt = self.lat_lon_to_utm(s, w)
    self.utm_offset = np.array([e, n, alt])

  def init_ecef_offset(self, x, y, zoom):
    s, w, n, e = osm_utils.tileEdges(x, y, zoom)

    ecef1 = self.lat_lon_to_ecef(s, w)
    ecef2 = self.lat_lon_to_ecef(s, e)
    ecef3 = self.lat_lon_to_ecef(n, w)

    xaxis = np.array(ecef2) - np.array(ecef1)
    yaxis = np.array(ecef3) - np.array(ecef1)
    zaxis = np.cross(xaxis, yaxis)
    zaxis /= np.linalg.norm(zaxis)
    xaxis /= np.linalg.norm(xaxis)
    yaxis = np.cross(zaxis, xaxis)

    if INIT_LOCAL_TO_ECEF is not None:
      self.local_to_ecef = INIT_LOCAL_TO_ECEF
    else:
      self.local_to_ecef = transformUtils.getTransformFromAxesAndOrigin(xaxis, yaxis, zaxis, ecef1)
    self.ecef_to_local = self.local_to_ecef.GetLinearInverse()


if HAVE_PYPROJ:
  coords = PyProjCoordinates()

# the coordinate system will be initialized to have
# its origin at this geo position
INIT_LAT_LON = (37.395648, -122.077783)
INIT_LOCAL_TO_ECEF = None
USE_UTM = False
OFFLINE = True
IMAGE_CACHE_DIR = 'tiles'
ROOT_FOLDER_NAME = 'map tile viewer'


def ensure_directory_exists(filename):
  dirname = os.path.dirname(filename)
  if not os.path.exists(dirname):
    try:
      os.makedirs(dirname)
    except:
      pass


def download_url(url, filename):
  if OFFLINE or not url:
    return

  if not os.path.isfile(filename):
    ensure_directory_exists(filename)
    print('downloading:', url)
    try:
      urllib.request.urlretrieve(url, filename)
    except:
      print('url download failed')


def get_mapbox_token():
  return os.environ.get('MAPBOX_ACCESS_TOKEN', '')


def get_tile_url_templates():
  token = 'access_token=' + get_mapbox_token()
  styles_url = 'https://api.mapbox.com/styles/v1/mapbox/'
  return {
    'placeholder': '',
    'openstreetmap': 'https://tile.openstreetmap.org/{}/{}/{}.png',
    'mapbox-streets': styles_url + 'streets-v10/tiles/512/{}/{}/{}?' + token,
    'mapbox-outdoors': styles_url + 'outdoors-v10/tiles/512/{}/{}/{}?' + token,
    'mapbox-light': styles_url + 'light-v9/tiles/512/{}/{}/{}?' + token,
    'mapbox-dark': styles_url + 'dark-v9/tiles/512/{}/{}/{}?' + token,
    'mapbox-satellite': styles_url + 'satellite-v9/tiles/512/{}/{}/{}?' + token,
    'mapbox-satellite-streets': styles_url + 'satellite-streets-v10/tiles/512/{}/{}/{}?' + token,
    'mapbox-navigation-day': styles_url + 'navigation-guidance-day-v2/tiles/512/{}/{}/{}?' + token,
    'mapbox-navigation-night': styles_url + 'navigation-guidance-night-v2/tiles/512/{}/{}/{}?' + token,
    }


def get_tile_url(x, y, z, style):
  url = get_tile_url_templates()[style]
  return url.format(z, x, y) if url else url


def get_tiles_folder():
  return om.getOrCreateContainer(ROOT_FOLDER_NAME)


def get_zoom_folder(zoom):
  return om.getOrCreateContainer('zoom {}'.format(zoom), parentObj=get_tiles_folder())


def offset_tile_points(pts):
  if USE_UTM:
    pts -= coords.utm_offset
  else:
    z_offset = get_options().getProperty('Z Offset')
    for i in range(len(pts)):
      pts[i] = np.array(coords.ecef_to_local.TransformPoint(pts[i]))
      pts[i][2] = 0.0 + z_offset


def rebuild_tiles():
  get_tile_obj.cache_clear()
  on_style_changed()


def get_tile_corner_points(x, y, zoom):
  convert_lat_lon = coords.lat_lon_to_utm if USE_UTM else coords.lat_lon_to_ecef
  s, w, n, e = osm_utils.tileEdges(x, y, zoom)
  return np.array([
    convert_lat_lon(n, w),
    convert_lat_lon(n, e),
    convert_lat_lon(s, e),
    convert_lat_lon(s, w)])


@functools.lru_cache()
def get_tile_obj(x, y, zoom):

  pts = get_tile_corner_points(x, y, zoom)
  offset_tile_points(pts)

  d = DebugData()
  d.addPolygon(pts)
  poly_data = d.getPolyData()

  tcoords = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float32)
  vnp.addNumpyToVtk(poly_data, tcoords, 'tcoords')
  poly_data.GetPointData().SetTCoords(poly_data.GetPointData().GetArray('tcoords'))

  obj = vis.PolyDataItem('{}, {}'.format(x, y), poly_data, view=None)
  obj.textures = {}
  return obj


@functools.lru_cache(maxsize=100)
def get_placeholder_image(x, y, zoom):
  #import cv2
  img = np.ones((512, 512, 3), np.uint8) * 245
  #font = cv2.FONT_HERSHEY_SIMPLEX
  #text = 'zoom={}, x={}, y={}'.format(zoom, x, y)
  #color = (0, 0, 0)
  #cv2.putText(img, text, (140, 256), font, 0.5, color, thickness=1, lineType=cv2.LINE_AA)
  return vnp.numpyToImageData(img)  #cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def draw_tile(x, y, zoom):

  obj = get_tile_obj(x, y, zoom)
  obj.addToView(fields.view)
  om.addToObjectModel(obj, parentObj=get_zoom_folder(zoom))

  style_name = get_options().getPropertyEnumValue('Style')
  url = get_tile_url(x, y, zoom, style_name)
  extension = '.jpg' if 'satellite' in url else '.png'
  filename = os.path.join(IMAGE_CACHE_DIR, style_name, str(zoom), str(x), str(y)) + extension
  #print(url)
  #print(filename)

  surface_mode = 'Surface with edges' if get_options().getProperty('Draw Tile Borders') else 'Surface'
  obj.setProperty('Surface Mode', surface_mode)
  obj.setProperty('Visible', True)

  def set_texture():
    tex = vtk.vtkTexture()
    tex.SetInputData(obj.textures[filename])
    tex.RepeatOff()
    tex.InterpolateOn()
    tex.EdgeClampOn()
    obj.actor.SetTexture(tex)
    if get_options().getProperty('Draw Lighting'):
      obj.actor.GetProperty().LightingOn()
    else:
      obj.actor.GetProperty().LightingOff()

  def init_texture():
    download_url(url, filename)
    if os.path.isfile(filename):
      img = ioUtils.readImage(filename)
    else:
      img = get_placeholder_image(x, y, zoom)
    obj.textures[filename] = img
    set_texture()
    obj._renderAllViews()

  if filename in obj.textures:
    set_texture()
  else:
    obj.actor.SetTexture(None)
    obj.actor.GetProperty().LightingOn()
    fields.task_runner.callOnThread(init_texture)

  return obj


def on_draw_tile_borders_changed(enabled):
  for folder in get_tiles_folder().children():
    for obj in folder.children():
      obj.setProperty('Surface Mode', 'Surface with edges' if enabled else 'Surface')


def on_draw_lighting_changed(enabled):
  for folder in get_tiles_folder().children():
    for obj in folder.children():
      if enabled:
        obj.actor.GetProperty().LightingOn()
      else:
        obj.actor.GetProperty().LightingOff()


def on_alpha_changed(alpha):
  for folder in get_tiles_folder().children():
    for obj in folder.children():
      obj.setProperty('Alpha', alpha)


def on_style_changed():
  for i in range(21):
    om.removeFromObjectModel(get_zoom_folder(i))
  update_visible_tiles()

    
def get_view_direction_intersect_with_plane(plane_origin=(0, 0, 0), plane_normal=(0,0,1)):
  cam = fields.view.camera()
  pos = np.array(cam.GetPosition())
  focal = np.array(cam.GetFocalPoint())
  return segmentationroutines.intersectLineWithPlane(pos, focal-pos, plane_origin, plane_normal)


def get_center_tile():

  pos = get_view_direction_intersect_with_plane()
  if USE_UTM:
    pos += coords.utm_offset
    lat, lon = coords.utm_to_lat_lon(pos[0], pos[1])
  else:
    pos = np.array(coords.local_to_ecef.TransformPoint(pos))
    lat, lon = coords.ecef_to_lat_lon(pos)

  zoom = get_zoom()
  x, y = osm_utils.tileXY(lat, lon, zoom)

  return x, y, zoom


def get_zoom():
  return get_options().getProperty('Zoom')


def set_zoom(zoom):
  get_options().setProperty('Zoom', int(zoom))


def go_to_lat_lon(lat, lon):
  ecef_pos = coords.lat_lon_to_ecef(lat, lon)
  local_pos = coords.ecef_to_local.TransformPoint(ecef_pos)
  camera = fields.view.camera()
  camera_focal = np.array(camera.GetFocalPoint())
  camera_pos = np.array(camera.GetPosition())
  camera_translation = local_pos - camera_focal
  camera.SetFocalPoint(local_pos)
  camera.SetPosition(camera_pos + camera_translation)
  fields.view.render()


def on_zoom_changed(zoom):
  folder = get_zoom_folder(zoom)
  folder.setProperty('Visible', True)
  for obj in get_tiles_folder().children():
    if obj is not folder and obj.getProperty('Visible'):
      obj.setProperty('Visible', False)
  #vis.updateText('Zoom {}'.format(zoom), 'zoom text')


def get_padded_tiles(x, y, zoom, padding_size):

  offsets = list(range(-padding_size, padding_size+1))
  num_tiles = int(osm_utils.numTiles(zoom))

  tiles = set()
  for x_offset in offsets:
    for y_offset in offsets:
      xx = (x + x_offset) % num_tiles
      yy = (y + y_offset) % num_tiles
      tiles.add((xx, yy, zoom))

  return sorted(list(tiles))


def update_visible_tiles():
  x, y, zoom = get_center_tile()
  tiles = get_padded_tiles(x, y, zoom, get_tile_padding())

  folder = get_zoom_folder(zoom)

  names = dict()
  for obj in folder.children():
    names[obj.getProperty('Name')] = obj

  for tile in tiles:
    x, y, zoom = tile
    name = '{}, {}'.format(x, y)
    if name in names:
      del names[name]
    else:
      draw_tile(x, y, zoom)

  for obj in names.values():
    om.removeFromObjectModel(obj)


def update_auto_zoom():
  pos = get_view_direction_intersect_with_plane()
  distance = np.linalg.norm(pos - np.array(fields.view.camera().GetPosition()))
  count = math.floor(math.log2(distance) - math.log2(get_auto_zoom_distance()))
  zoom = np.clip(20 - count, 0, 20)
  set_zoom(zoom)


def on_start_render(o, e):
  if not get_tiles_folder().getProperty('Visible'):
    return
  if get_auto_zoom():
    update_auto_zoom()
  if get_auto_scroll():
    update_visible_tiles()


def draw_ecef_sphere():
  d = DebugData()
  d.addSphere((0,0,0), radius=6378137, resolution=100)
  poly_data = filterUtils.transformPolyData(d.getPolyData(), coords.ecef_to_local)
  vis.showPolyData(poly_data, 'earth', parent='scene', alpha=0.2, visible=False)


def on_map_options_changed(propertyObj, propertyName):

  propertyValue = propertyObj.getProperty(propertyName)
  if propertyName == 'Auto Zoom':
    propertyObj.setPropertyAttribute('Zoom', 'hidden', propertyValue)
    propertyObj.setPropertyAttribute('Auto Zoom Distance', 'hidden', not propertyValue)
  elif propertyName == 'Zoom':
    on_zoom_changed(propertyValue)
  elif propertyName == 'Style':
    on_style_changed()
  elif propertyName == 'Z Offset':
    rebuild_tiles()
  elif propertyName == 'Alpha':
    on_alpha_changed(propertyValue)
  elif propertyName == 'Draw Tile Borders':
    on_draw_tile_borders_changed(propertyValue)
  elif propertyName == 'Draw Lighting':
    on_draw_lighting_changed(propertyValue)
  elif propertyName == 'Visible' and propertyValue:
    on_zoom_changed(propertyObj.getProperty('Zoom'))

  if propertyName in ('Tile Padding', 'Zoom') and not get_auto_scroll():
    update_visible_tiles()
  fields.view.render()


def get_auto_scroll():
  return get_options().getProperty('Auto Scroll')


def get_auto_zoom():
  return get_options().getProperty('Auto Zoom')


def get_auto_zoom_distance():
  return get_options().getProperty('Auto Zoom Distance')


def get_tile_padding():
  return get_options().getProperty('Tile Padding')


def get_options():
  return get_tiles_folder()

def reset_view():
  applogic.resetCamera(viewDirection=[0, 0.1, -1])

def init_options(options):
  style_names = list(sorted(get_tile_url_templates().keys()))
  options.addProperty('Style', style_names.index('mapbox-streets'), om.PropertyAttributes(enumNames=style_names))
  options.addProperty('Auto Scroll', True)
  options.addProperty('Auto Zoom', True)
  options.addProperty('Auto Zoom Distance', 50, om.PropertyAttributes(minimum=1, maximum=1000))
  options.addProperty('Zoom', 15, om.PropertyAttributes(minimum=0, maximum=20, hidden=True))
  options.addProperty('Tile Padding', 2, om.PropertyAttributes(minimum=0, maximum=20))
  options.addProperty('Alpha', 1.0, om.PropertyAttributes(minimum=0, maximum=1.0, decimals=2, singleStep=0.1))
  options.addProperty('Draw Tile Borders', False)
  options.addProperty('Draw Lighting', False)
  options.addProperty('Z Offset', 0.0, om.PropertyAttributes(singleStep=1.0))

  options.properties.connectPropertyChanged(on_map_options_changed)


def init_default_tile_view(reset_camera=True, draw_sphere=False):

  om.removeFromObjectModel(get_tiles_folder())
  om.removeFromObjectModel(om.findObjectByName('earth'))

  folder = get_tiles_folder()
  om.collapse(folder)
  init_options(folder)
  om.setActiveObject(folder)
  observer = fields.view.renderWindow().AddObserver('StartEvent', on_start_render)
  def remove_observer(tree, obj):
    fields.view.renderWindow().RemoveObserver(observer)
  folder.connectRemovedFromObjectModel(remove_observer)

  if INIT_LOCAL_TO_ECEF is not None:
    lat, lon = coords.ecef_to_lat_lon(INIT_LOCAL_TO_ECEF.GetPosition())
  else:
    lat, lon = INIT_LAT_LON

  zoom = get_zoom()
  x, y = osm_utils.tileXY(lat, lon, zoom)

  coords.init_utm_offset(x, y, zoom)
  coords.init_ecef_offset(x, y, zoom)

  if draw_sphere:
    draw_ecef_sphere()

  draw_tile(x, y, zoom)
  if reset_camera:
    reset_view()

def init(fields_, reset_camera=True):
  global fields
  fields = fields_
  init_default_tile_view(reset_camera)


def main():
  fields = mainwindowapp.construct(globals())
  fields._add_fields(task_runner=TaskRunner())

  init(fields)

  fields.gridObj.setProperty('Visible', False)
  fields.viewOptions.setProperty('Orientation widget', False)
  fields.app.start()


if __name__ == "__main__":
  main()
