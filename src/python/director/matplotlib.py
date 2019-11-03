import matplotlib
matplotlib.use('Qt5Agg')


import time
import numpy as np

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
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)
        #self.plot_demo()

    def plot_demo(self):
        self.axes.clear()
        t = np.linspace(0, 10, 101)
        self.axes.plot(t, np.sin(t + time.time()))
        self.canvas.draw()

    def redraw(self):
        self.canvas.draw()


def plot(*args, **kwargs):
    plot = PlotWidget()
    tab = get_tab_widget()
    tab.addTab(plot, 'Figure')
    tab.setCurrentIndex(tab.count()-1)
    plot.plot(*args, **kwargs)
    return plot


def plot_widget_demo():
    plot = PlotWidget()
    tab = get_tab_widget()
    tab.addTab(plot, 'Figure')
    tab.setCurrentIndex(tab.count()-1)
    return plot


def get_tab_widget():
    widgets = QtCore.QCoreApplication.instance().topLevelWidgets()
    for mainWindow in widgets:
        try:
            return mainWindow.centralWidget()
        except AttributeError:
            pass
    raise Exception('Tab widget not found')


if __name__ == "__main__":
    plot_widget_demo()
