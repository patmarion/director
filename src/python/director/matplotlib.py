import matplotlib
matplotlib.use('Qt5Agg')

import matplotlib.pyplot as plt
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore",category=matplotlib.cbook.mplDeprecation)


class PlotWidget(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.axes = self.figure.subplots()
        self.clear = self.axes.clear
        self.plot = self.axes.plot
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)

    def redraw(self):
        self.canvas.draw()


def plot(*args, **kwargs):
    plot = PlotWidget()
    plot.plot(*args, **kwargs)
    plot.show()
    return plot


def addToTabWidget(widget, title='Figure'):
    tabWidget = getMainWindow().findChild(QtWidgets.QTabWidget)
    tabWidget.addTab(widget, title)
    tabWidget.setCurrentIndex(tabWidget.count() - 1)


def getMainWindow():
    widgets = QtCore.QCoreApplication.instance().topLevelWidgets()
    for widget in widgets:
        if isinstance(widget, QtWidgets.QMainWindow):
            return widget
    return None
