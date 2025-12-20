import os
from qtpy import QtWidgets, QtGui
import functools

class Icons(object):

  Directory = QtWidgets.QStyle.StandardPixmap.SP_DirIcon
  Axes = 'axes_icon.png'
  Eye = 'eye_icon.png'
  EyeOff = 'eye_icon_gray.png'
  Python = 'python_logo.png'
  ResetCamera = 'reset_camera.png'
  CameraRotate = 'camera_mode.png'
  Chart = 'chart.png'
  Empty = ''

  @staticmethod
  @functools.lru_cache(maxsize=None)
  def getIcon(iconId):
      '''
      Return a QIcon given an icon id as a string (filename) or StandardPixmap enum.
      '''
      if isinstance(iconId, QtGui.QIcon):
          return iconId
      elif isinstance(iconId, QtWidgets.QStyle.StandardPixmap):
          return QtWidgets.QApplication.instance().style().standardIcon(iconId)
      elif isinstance(iconId, str):
          icon_path = os.path.join(os.path.dirname(__file__), 'assets', iconId)
          if os.path.exists(icon_path):
              return QtGui.QIcon(icon_path)
          else:
              print("Icon path not found: ", icon_path)

      return QtGui.QIcon()