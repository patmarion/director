from qtpy import QtWidgets

from director import applogic, cameracontrol


class CameraBookmarks:
    def __init__(self, view):
        self.bookmarks = {}
        self.view = view
        self.flyer = cameracontrol.Flyer(view)
        self.flyer.flyTime = 1.0

    def storeCameraBookmark(self, key):
        camera = self.view.camera()
        focal, position = camera.GetFocalPoint(), camera.GetPosition()
        self.bookmarks[key] = (focal, position)

    def clear(self):
        self.bookmarks = {}

    def getBookmark(self, key):
        return self.bookmarks.get(key)

    def flyToBookmark(self, key):
        focal, position = self.getBookmark(key)
        self.flyer.zoomTo(focal, position)


class CameraBookmarkWidget:
    def __init__(self, view):
        self.bookmarks = CameraBookmarks(view)
        self.widget = QtWidgets.QScrollArea()
        self.widget.setWindowTitle("Camera Bookmarks")
        self.numberOfBookmarks = 8
        self.updateLayout()

    def updateLayout(self):
        self.storeButtons = []
        self.flyButtons = []

        w = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(w)

        for i in range(self.numberOfBookmarks):
            storeButton = QtWidgets.QPushButton("set")
            flyButton = QtWidgets.QPushButton("fly")
            textEdit = QtWidgets.QLineEdit("camera %d" % i)

            # Use lambda with default argument to capture current index
            storeButton.clicked.connect(lambda checked, idx=i: self.onStoreCamera(idx))
            flyButton.clicked.connect(lambda checked, idx=i: self.onFlyToCamera(idx))

            self.storeButtons.append(storeButton)
            self.flyButtons.append(flyButton)
            layout.addWidget(storeButton, i, 0)
            layout.addWidget(flyButton, i, 1)
            layout.addWidget(textEdit, i, 2)
            flyButton.setEnabled(False)

        self.flySpeedSpinner = QtWidgets.QDoubleSpinBox()
        self.flySpeedSpinner.setMinimum(0)
        self.flySpeedSpinner.setMaximum(60)
        self.flySpeedSpinner.setDecimals(1)
        self.flySpeedSpinner.setSingleStep(0.5)
        self.flySpeedSpinner.setSuffix(" seconds")
        self.flySpeedSpinner.setValue(1.0)

        layout.addWidget(QtWidgets.QLabel("Fly speed:"), i + 1, 0, 1, 2)
        layout.addWidget(self.flySpeedSpinner, i + 1, 2)

        self.widget.setWidget(w)

    def onStoreCamera(self, index):
        self.bookmarks.storeCameraBookmark(index)
        self.flyButtons[index].setEnabled(True)

    def onFlyToCamera(self, index):
        self.bookmarks.flyer.flyTime = self.flySpeedSpinner.value()
        self.bookmarks.flyToBookmark(index)


def init(view):
    global widget, dock
    widget = CameraBookmarkWidget(view)
    dock = applogic.addWidgetToDock(widget.widget, action=None)
    dock.hide()
