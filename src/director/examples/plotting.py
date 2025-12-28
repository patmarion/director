"""Example demonstrating PlotWidget with sin waves and random points."""

import numpy as np
import pyqtgraph as pg
from qtpy.QtWidgets import QApplication

from director.plot_widget import PlotWidget


def main():
    app = QApplication([])

    plot_widget = PlotWidget()

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

    # Set the second plot's series to points-only style
    entry = plot_widget._plot_entries[plot2]
    for series in entry.line_series:
        # Get the current color from the pen
        current_pen = series.opts.get("pen")
        color = pg.mkPen(current_pen).color() if current_pen else pg.mkColor("w")
        pen = pg.mkPen(color, width=2)
        brush = pg.mkBrush(color)

        # Set to points only
        series.setPen(None)
        series.setSymbol("o")
        series.setSymbolPen(pen)
        series.setSymbolBrush(brush)
        series.setSymbolSize(5)

    plot_widget.add_horizontal_lines(plot2, [1.0, -1.0, 0.0])

    widget = plot_widget.plot_widget
    widget.setWindowTitle("PlotWidget Example")
    widget.resize(800, 600)
    widget.show()

    app.exec_()


if __name__ == "__main__":
    main()
