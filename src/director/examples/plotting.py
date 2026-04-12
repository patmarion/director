"""Example demonstrating PlotWidget with sin waves and random points."""

import numpy as np
from qtpy import QtCore
from qtpy.QtWidgets import QApplication, QDockWidget, QMainWindow, QSplitter

from director.objectmodel import ObjectModelTree
from director.plot_widget import PlotWidget
from director.propertiespanel import PropertiesPanel


def connect_to_object_model(plot_widget):
    model = ObjectModelTree()
    model.init(propertiesPanel=PropertiesPanel())
    plot_widget.set_object_model(model)
    return model


def main():
    app = QApplication([])

    plot_widget = PlotWidget()

    # Optional, use the object model to show plot objects and properties
    model = connect_to_object_model(plot_widget)

    # Generate time array
    t = np.linspace(0, 4 * np.pi, 500)

    # --- First plot: Multiple sin wave line series ---
    plot1 = plot_widget.add_plot(title="Sin Waves", y_label="Amplitude", y_units="V")
    sin1 = np.sin(t)
    sin2 = np.sin(2 * t) * 0.7
    sin3 = np.sin(0.5 * t + np.pi / 4) * 1.2
    plot_widget.add_data_to_plot(
        plot1,
        t,
        [
            ("sin(t)", sin1),
            ("sin(2t)", sin2),
            ("sin(0.5t + π/4)", sin3),
        ],
    )
    plot_widget.add_horizontal_lines(plot1, [0.5, -0.5, 1.0, -1.0])

    # --- Second plot: Random points around a sin wave ---
    plot2 = plot_widget.add_plot(title="Noisy Sin Points", y_label="Value", y_units="")

    # Create noisy data around sin waves
    noise1 = np.sin(t) + np.random.normal(0, 0.15, len(t))
    noise2 = np.sin(t + np.pi) + np.random.normal(0, 0.15, len(t))
    plot_widget.add_data_to_plot(
        plot2,
        t,
        [
            ("noisy sin", noise1),
            ("noisy -sin", noise2),
        ],
    )

    # Use the high-level plot item to apply the same style to all series.
    plot2_item = plot_widget.get_plot_object_item(plot2)
    if plot2_item is not None:
        plot2_item.setProperty("Style", plot2_item.style_names.index("Points"))
        plot2_item.setProperty("Line Width", 2)
        plot2_item.setProperty("Point Size", 5)

    plot_widget.add_horizontal_lines(plot2, [1.0, -1.0, 0.0])

    window = QMainWindow()
    window.setWindowTitle("PlotWidget Example")
    window.resize(1200, 800)
    window.setCentralWidget(plot_widget.plot_widget)

    left_panel = QSplitter(QtCore.Qt.Vertical)
    left_panel.addWidget(model.treeView)
    left_panel.addWidget(model.getPropertiesPanel())

    properties_dock = QDockWidget("Properties", window)
    properties_dock.setObjectName("PropertiesDock")
    properties_dock.setWidget(left_panel)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, properties_dock)
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()
