from dataclasses import dataclass, field
from typing import Iterable

import director.objectmodel as om
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.dockarea.Dock import DockLabel
import qtpy.QtCore as QtCore
from qtpy import QtWidgets


@dataclass
class PlotEntry:
    plot_item: pg.PlotItem
    line_series: list[pg.PlotDataItem] = field(default_factory=list)
    vline: pg.InfiniteLine | None = None
    horizontal_lines: list[pg.InfiniteLine] = field(default_factory=list)
    legend: pg.LegendItem | None = None
    object_item: "PlotObjItem | None" = None
    series_items: "dict[pg.PlotDataItem, PlotSeriesItem]" = field(default_factory=dict)


class DirectorPlotWidget(pg.PlotWidget):
    sigDropped = QtCore.Signal(object, list)

    def __init__(self, parent=None, background="default", plotItem=None, **kargs):
        super().__init__(parent, background, plotItem, **kargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasFormat("application/x-director-fields"):
            ev.accept()
        else:
            ev.ignore()

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasFormat("application/x-director-fields"):
            ev.accept()
        else:
            ev.ignore()

    def dropEvent(self, ev):
        data = ev.mimeData().data("application/x-director-fields")
        import json

        try:
            fields = json.loads(data.data().decode("utf-8"))
            self.sigDropped.emit(self.getPlotItem(), fields)
        except Exception:
            pass


class PlotObjItem(om.ObjectModelItem):
    def __init__(self, plot_widget, plot_item, title):
        om.ObjectModelItem.__init__(self, title or "Plot", icon=om.Icons.Chart)
        self.plot_widget = plot_widget
        self.plot_item = plot_item

        self.addProperty("Title", title or " ")
        self.addProperty("X Label", "Time")
        self.addProperty("Y Label", "")
        self.addProperty("Y Units", "")
        self.addProperty("Visible", True)

    def _onPropertyChanged(self, propertySet, propertyName):
        om.ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)
        if propertyName == "Title":
            self.plot_widget.set_plot_title(self.plot_item, self.getProperty(propertyName))
        elif propertyName == "X Label":
            self.plot_item.setLabel("bottom", text=self.getProperty(propertyName))
        elif propertyName == "Y Label":
            self.plot_item.setLabel("left", text=self.getProperty(propertyName))
        elif propertyName == "Y Units":
            self.plot_item.setLabel("left", units=self.getProperty(propertyName))
        elif propertyName == "Visible":
            dock = self.plot_widget._plot_docks.get(self.plot_item)
            if dock:
                dock.setVisible(self.getProperty(propertyName))

    def onRemoveFromObjectModel(self):
        om.ObjectModelItem.onRemoveFromObjectModel(self)
        self.plot_widget.remove_plot(self.plot_item, from_om=True)


class PlotSeriesItem(om.ObjectModelItem):
    def __init__(self, plot_widget, plot_item, series, name):
        om.ObjectModelItem.__init__(self, name)
        self.plot_widget = plot_widget
        self.plot_item = plot_item
        self.series = series

        self.addProperty("Visible", True)
        self.addProperty("Color", [1.0, 1.0, 1.0])
        self.addProperty("Style", 0, attributes=om.PropertyAttributes(enumNames=["Line", "Points", "Line + Points"]))
        self.addProperty("Line Width", 2, attributes=om.PropertyAttributes(minimum=1, maximum=10))
        self.addProperty("Point Size", 5, attributes=om.PropertyAttributes(minimum=1, maximum=20))

        color = self._get_color_from_series()
        if color:
            self.setProperty("Color", color)

    def _get_color_from_series(self):
        opts = self.series.opts
        pen = opts.get("pen")
        if pen is None:
            pen = opts.get("symbolPen")

        if pen is not None:
            c = pg.mkPen(pen).color()
            return [c.redF(), c.greenF(), c.blueF()]
        return [1.0, 1.0, 1.0]

    def _onPropertyChanged(self, propertySet, propertyName):
        om.ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)
        if propertyName == "Visible":
            self.series.setVisible(self.getProperty(propertyName))
        elif propertyName == "Name":
            # OM handles name change, we might want to update series name if possible
            pass
        elif propertyName in ["Color", "Style", "Line Width", "Point Size"]:
            self._update_style()

    def _update_style(self):
        style_idx = self.getProperty("Style")
        color_list = self.getProperty("Color")
        line_width = self.getProperty("Line Width")
        point_size = self.getProperty("Point Size")

        color = pg.mkColor(int(color_list[0] * 255), int(color_list[1] * 255), int(color_list[2] * 255))
        pen = pg.mkPen(color, width=line_width)
        brush = pg.mkBrush(color)

        if style_idx == 0:  # Line
            self.series.setPen(pen)
            self.series.setSymbol(None)
        elif style_idx == 1:  # Points
            self.series.setPen(None)
            self.series.setSymbol("o")
            self.series.setSymbolPen(pen)
            self.series.setSymbolBrush(brush)
            self.series.setSymbolSize(point_size)
        elif style_idx == 2:  # Both
            self.series.setPen(pen)
            self.series.setSymbol("o")
            self.series.setSymbolPen(pen)
            self.series.setSymbolBrush(brush)
            self.series.setSymbolSize(point_size)

    def onRemoveFromObjectModel(self):
        om.ObjectModelItem.onRemoveFromObjectModel(self)
        self.plot_widget.remove_series(self.plot_item, self.series, from_om=True)


class PlotWidget(QtCore.QObject):
    """Utility for creating synchronized plots from log channels."""

    sigPlotsDropped = QtCore.Signal(object, list)

    def __init__(self):
        super().__init__()
        self.time_slider = None
        self.plot_widget = DockArea()
        self._plots: list[pg.PlotItem] = []
        self._plot_entries: dict[pg.PlotItem, PlotEntry] = {}
        self._plot_docks: dict[pg.PlotItem, Dock] = {}
        self._x_link_source = None
        self.auto_scroll = True
        self.start_time_s = 0.0
        self._suspend_auto_scroll = False
        self._selected_plot: pg.PlotItem | None = None
        self.object_model = None
        self._plots_removing_from_om = set()

        # Apply custom styling patch
        DockLabel.updateStyle = updateStylePatched

    def set_object_model(self, object_model):
        self.object_model = object_model

    def set_plot_title(self, plot_item: pg.PlotItem, title: str):
        if plot_item in self._plot_docks:
            self._plot_docks[plot_item].setTitle(title or " ")

    def add_horizontal_line_dialog(self, plot_item: pg.PlotItem):
        value, ok = QtWidgets.QInputDialog.getDouble(
            self.plot_widget, "Add Horizontal Line", "Y Value:", 0.0, decimals=4
        )
        if ok:
            self.add_horizontal_lines(plot_item, [value])

    def clear_horizontal_lines(self, plot_item: pg.PlotItem):
        entry = self._plot_entries.get(plot_item)
        if not entry:
            return
        for line in entry.horizontal_lines:
            plot_item.removeItem(line)
        entry.horizontal_lines.clear()

    def connect_time_slider(self, time_slider):
        assert self.time_slider is None
        self.time_slider = time_slider
        self.start_time_s = time_slider.get_time_range()[0]
        self.time_slider.connect_on_time_changed(self._on_time_slider_changed)

    def add_plot_with_data(
        self,
        timestamps_s: np.ndarray,
        series_list: Iterable[tuple[str, np.ndarray]],
        title: str,
        y_label: str,
        y_units: str,
        horizontal_lines: Iterable[float] | None = None,
    ):
        """Add a plot for the given channel/fields."""
        timestamps_s = np.array(timestamps_s)
        series = list(series_list)
        if timestamps_s.size == 0 or not series:
            print("plot_widget: timestamps and series data are required.")
            return

        plot_item = self.add_plot(title, y_label, y_units)
        self.add_data_to_plot(plot_item, timestamps_s, series)
        self.add_horizontal_lines(plot_item, horizontal_lines)

    def add_plot(self, title: str = None, y_label: str = None, y_units: str = None) -> pg.PlotItem:
        dock_name = title if title else " "
        dock = Dock(dock_name, size=(500, 300), closable=True)

        view_box = PlotInteractionViewBox(plot_widget=self)
        plot_widget = DirectorPlotWidget(viewBox=view_box)
        plot_widget.sigDropped.connect(self.sigPlotsDropped)
        plot_widget.setBackground((240, 240, 240))
        dock.addWidget(plot_widget)

        dock.sigClosed.connect(self._on_plot_closed)

        if not self._plots:
            self.plot_widget.addDock(dock, "top")
        else:
            self.plot_widget.addDock(dock, "bottom")

        plot_item = plot_widget.getPlotItem()
        view_box.setPlotItem(plot_item)

        dock.label.sigClicked.connect(lambda label, ev: self._on_plot_clicked(plot_item))

        if self._x_link_source is None:
            self._x_link_source = plot_item
        else:
            plot_item.setXLink(self._x_link_source)

        plot_item.setLabel("left", y_label, units=y_units)
        plot_item.setLabel("bottom", "Time", units="seconds")
        legend = plot_item.addLegend(offset=(-10, 10))
        legend.anchor((1, 0), (1, 0))

        plot_item.showGrid(x=True, y=True, alpha=0.25)
        vline = self._attach_vline(plot_item)
        self._plots.append(plot_item)
        self._plot_entries[plot_item] = PlotEntry(plot_item=plot_item, vline=vline, legend=legend)
        self._plot_docks[plot_item] = dock
        self._on_plot_clicked(plot_item)

        if self.object_model:
            plots_folder = self.object_model.getOrCreateContainer("Plots")
            obj_item = PlotObjItem(self, plot_item, title)
            self._plot_entries[plot_item].object_item = obj_item
            if y_label:
                obj_item.setProperty("Y Label", y_label)
            if y_units:
                obj_item.setProperty("Y Units", y_units)
            self.object_model.addToObjectModel(obj_item, parentObj=plots_folder)

        return plot_item

    def get_selected_plot(self) -> pg.PlotItem | None:
        return self._selected_plot

    def get_title(self, plot_item: pg.PlotItem) -> str:
        return self._plot_docks[plot_item].title()

    def _on_plot_clicked(self, plot_item: pg.PlotItem):
        self._selected_plot = plot_item
        for p, d in self._plot_docks.items():
            if d.label:
                d.label.setDim(p != plot_item)

        if self.object_model:
            entry = self._plot_entries.get(plot_item)
            if entry and entry.object_item:
                self.object_model.setActiveObject(entry.object_item)

    def get_plots(self) -> list[pg.PlotItem]:
        return list(self._plots)

    def get_series_names(self, plot_item: pg.PlotItem) -> list[str]:
        entry = self._plot_entries.get(plot_item)
        if not entry:
            return []
        return [item.name() for item in entry.line_series]

    def remove_series(self, plot_item: pg.PlotItem, series: str | pg.PlotDataItem, from_om=False):
        entry = self._plot_entries.get(plot_item)
        if not entry:
            return

        to_remove = []
        if isinstance(series, str):
            to_remove = [item for item in entry.line_series if item.name() == series]
        else:
            if series in entry.line_series:
                to_remove = [series]

        for item in to_remove:
            plot_item.removeItem(item)
            entry.line_series.remove(item)

            if item in entry.series_items:
                series_item = entry.series_items.pop(item)
                if not from_om and self.object_model and series_item.getObjectTree():
                    self.object_model.removeFromObjectModel(series_item)

    def remove_plot(self, plot_item: pg.PlotItem, from_om=False):
        if plot_item not in self._plots:
            return

        if from_om:
            self._plots_removing_from_om.add(plot_item)

        self._plot_docks[plot_item].close()

        if from_om:
            self._plots_removing_from_om.discard(plot_item)

    def _on_plot_closed(self, dock):
        # Find the plot item associated with this dock
        for plot_item, d in self._plot_docks.items():
            if d == dock:
                break
        else:
            return

        # Handle Selection before removal
        if self._selected_plot == plot_item:
            # try to select previous plot
            idx = self._plots.index(plot_item)
            if idx > 0:
                new_selection = self._plots[idx - 1]
                self._on_plot_clicked(new_selection)
            elif len(self._plots) > 1:
                # If it was the first one, select the next one (which will become the first)
                new_selection = self._plots[idx + 1]
                self._on_plot_clicked(new_selection)
            else:
                self._selected_plot = None

        # Perform cleanup
        if self.object_model and plot_item not in self._plots_removing_from_om:
            entry = self._plot_entries.get(plot_item)
            if entry and entry.object_item and entry.object_item.getObjectTree():
                self.object_model.removeFromObjectModel(entry.object_item)

        self._plots.remove(plot_item)
        del self._plot_entries[plot_item]
        del self._plot_docks[plot_item]

        # Handle X-Link
        if not self._plots:
            self._x_link_source = None

        if self._x_link_source == plot_item:
            self._x_link_source = self._plots[0] if self._plots else None
            if self._x_link_source:
                for p in self._plots:
                    p.setXLink(self._x_link_source)

    def _attach_vline(self, plot_item: pg.PlotItem) -> pg.InfiniteLine:
        vline = pg.InfiniteLine(angle=90, movable=True)
        plot_item.addItem(vline, ignoreBounds=True)
        vline.sigDragged.connect(self._make_drag_handler(vline))
        return vline

    def add_data_to_plot(
        self,
        plot_item: pg.PlotItem,
        timestamps_s: np.ndarray,
        series_list: Iterable[tuple[str, np.ndarray]],
    ) -> None:
        entry = self._plot_entries[plot_item]
        color_index = len(entry.line_series)

        time_offsets_s = timestamps_s - self.start_time_s

        for label, values in series_list:
            values = np.asarray(values)
            if values.ndim == 1:
                values = values[:, None]

            for column in range(values.shape[1]):
                column_name = label if values.shape[1] == 1 else f"{label}[{column}]"
                pen = self._pen_for_index(color_index)
                color_index += 1
                line_series = plot_item.plot(time_offsets_s, values[:, column], name=column_name, pen=pen)
                entry.line_series.append(line_series)

                if self.object_model and entry.object_item:
                    series_item = PlotSeriesItem(self, plot_item, line_series, column_name)
                    entry.series_items[line_series] = series_item
                    self.object_model.addToObjectModel(series_item, parentObj=entry.object_item)

    def add_horizontal_lines(
        self,
        plot_item: pg.PlotItem,
        horizontal_lines: Iterable[float] | None,
    ) -> None:
        if not horizontal_lines:
            return

        entry = self._plot_entries[plot_item]
        for value in horizontal_lines:
            hline = pg.InfiniteLine(
                angle=0,
                movable=False,
                pen=pg.mkPen(color="black", style=QtCore.Qt.PenStyle.DashLine),
            )
            plot_item.addItem(hline, ignoreBounds=True)
            hline.setPos(value)
            entry.horizontal_lines.append(hline)

    @staticmethod
    def _pen_for_index(index):
        return pg.mkPen(pg.intColor(index), width=2)

    def _make_click_handler(self, line_series):
        def handler():
            print(f"Clicked on {line_series.name()}")

        return handler

    def _make_drag_handler(self, vline):
        def handler():
            time_offset_s = vline.pos().x()
            timestamp_s = time_offset_s + self.start_time_s
            self._suspend_auto_scroll = True
            if self.time_slider:
                self.time_slider.set_time(timestamp_s)

        return handler

    def _handle_ctrl_jump(self, view_box: pg.ViewBox, view_point: QtCore.QPointF):
        relative_time_s = view_point.x()
        self._suspend_auto_scroll = True
        if self.time_slider:
            timestamp_s = self.start_time_s + relative_time_s
            self.time_slider.set_time(timestamp_s)
        else:
            self._update_vlines(relative_time_s)

    def _on_time_slider_changed(self, timestamp_s):
        # Disable updates to prevent excessive repainting
        self.plot_widget.setUpdatesEnabled(False)
        try:
            time_offset_s = timestamp_s - self.start_time_s
            self._update_vlines(time_offset_s)
        finally:
            self.plot_widget.setUpdatesEnabled(True)

    def _update_vlines(self, time_offset_s):
        if not self._plots:
            return

        # This logic examines the axis x range and the total x extent of the data.
        # We implement some fancy auto scrolling logic to keep the playhead in a reasonable
        # location and auto scroll the plots when necessary.
        min_time, max_time = self.time_slider.get_time_range()
        min_time -= self.start_time_s
        max_time -= self.start_time_s
        current_vline_pos = self._plot_entries[self._x_link_source].vline.pos().x()
        direction = np.sign(time_offset_s - current_vline_pos)
        view_box = self._x_link_source.getViewBox()
        x_min, x_max = view_box.viewRange()[0]
        width = x_max - x_min
        fraction = (current_vline_pos - x_min) / width

        if direction > 0:
            if x_max >= max_time:
                self.auto_scroll = False
            else:
                if x_min <= min_time and fraction < 0.5:
                    self.auto_scroll = False
                else:
                    self.auto_scroll = True
        else:
            if x_min <= min_time:
                self.auto_scroll = False
            else:
                if x_max >= max_time and fraction > 0.5:
                    self.auto_scroll = False
                else:
                    self.auto_scroll = True

        if not self._suspend_auto_scroll and (time_offset_s < x_min or time_offset_s > x_max):
            self._x_link_source.setXRange(time_offset_s - width / 2, time_offset_s + width / 2, padding=0)

        pre_positions = {}

        # Note, the rest of the logic here computes info and updates each plot item.
        # But the plot items have linked X axes so it really only needs to be done for one.
        if self.auto_scroll and not self._suspend_auto_scroll:
            for plot_item in self._plots:
                entry = self._plot_entries.get(plot_item)
                if entry is None or entry.vline is None:
                    continue
                view_box = plot_item.getViewBox()
                x_min, x_max = view_box.viewRange()[0]
                width = x_max - x_min
                if width <= 0:
                    continue
                relative = entry.vline.pos().x()
                fraction = (relative - x_min) / width
                pre_positions[plot_item] = (fraction, width)

        for plot_item in self._plots:
            entry = self._plot_entries.get(plot_item)
            if entry is None or entry.vline is None:
                continue
            entry.vline.setPos(time_offset_s)
            if self.auto_scroll and not self._suspend_auto_scroll and plot_item in pre_positions:
                fraction, width = pre_positions[plot_item]
                self._scroll_to_timestamp(plot_item, time_offset_s, fraction, width)
        self._suspend_auto_scroll = False

    @staticmethod
    def _scroll_to_timestamp(plot_item, relative_time, fraction=None, width=None):
        view_box = plot_item.getViewBox()
        current_range = view_box.viewRange()
        x_min, x_max = current_range[0]
        if width is None:
            width = x_max - x_min
        if width <= 0:
            return
        if fraction is None:
            fraction = (relative_time - x_min) / width
            fraction = max(0.0, min(1.0, fraction))
        new_x_min = relative_time - fraction * width
        view_box.setXRange(new_x_min, new_x_min + width, padding=0)


class PlotInteractionViewBox(pg.ViewBox):
    """Custom ViewBox implementing tailored interaction modes."""

    def __init__(
        self,
        plot_widget: "PlotWidget",
    ):
        super().__init__(enableMenu=True)
        self._plot_widget = plot_widget
        self._plot_item: pg.PlotItem | None = None

        self.setMouseMode(self.PanMode)
        self._previous_mouse_mode = None
        self._right_drag_mode = None
        self._right_drag_start = None
        self._right_last_pos = None

    def setPlotItem(self, plot_item):
        self._plot_item = plot_item
        self._customize_context_menu(plot_item.getMenu())

    def raiseContextMenu(self, ev):
        menu = self._plot_item.getMenu()

        # Clean up previous series actions
        if hasattr(self, "_context_menu_series_actions"):
            for action in self._context_menu_series_actions:
                menu.removeAction(action)
        self._context_menu_series_actions = []

        # Identify clicked series
        series = self._get_clicked_series(ev)
        if series:
            # Add separator
            sep = menu.addSeparator()
            self._context_menu_series_actions.append(sep)

            # Series Name Label (disabled action)
            name = series.name() or "Unnamed Series"
            label_action = menu.addAction(f"Series: {name}")
            label_action.setEnabled(False)
            self._context_menu_series_actions.append(label_action)

            # Style Submenu
            style_menu = menu.addMenu("Display Style")
            self._context_menu_series_actions.append(style_menu.menuAction())

            # Style Options
            def set_style(s, mode):
                self._set_series_style(s, mode)

            a_line = style_menu.addAction("Line")
            a_line.triggered.connect(lambda: set_style(series, "line"))

            a_points = style_menu.addAction("Points")
            a_points.triggered.connect(lambda: set_style(series, "points"))

            a_both = style_menu.addAction("Line + Points")
            a_both.triggered.connect(lambda: set_style(series, "both"))

        menu.popup(ev.screenPos().toPoint())

    def _get_clicked_series(self, ev) -> pg.PlotDataItem | None:
        pos = ev.scenePos()
        if self.scene() is None:
            return None

        for item in self.scene().items(pos):
            if isinstance(item, pg.PlotDataItem):
                return item
            # Handle cases where we hit the curve or scatter item directly
            if isinstance(item, (pg.PlotCurveItem, pg.ScatterPlotItem)):
                parent = item.parentItem()
                if isinstance(parent, pg.PlotDataItem):
                    return parent
        return None

    def _set_series_style(self, series: pg.PlotDataItem, style: str):
        # Attempt to recover the base color from current settings
        # Preference: current pen -> current symbol pen -> default blue
        color = "b"
        current_pen = series.opts.get("pen")
        if current_pen is not None:
            color = current_pen.color() if hasattr(current_pen, "color") else pg.mkPen(current_pen).color()
        else:
            current_symbol_pen = series.opts.get("symbolPen")
            if current_symbol_pen is not None:
                color = (
                    current_symbol_pen.color()
                    if hasattr(current_symbol_pen, "color")
                    else pg.mkPen(current_symbol_pen).color()
                )

        pen = pg.mkPen(color, width=2)
        brush = pg.mkBrush(color)

        if style == "line":
            series.setPen(pen)
            series.setSymbol(None)
        elif style == "points":
            series.setPen(None)
            series.setSymbol("o")
            series.setSymbolPen(pen)
            series.setSymbolBrush(brush)
            series.setSymbolSize(2)
        elif style == "both":
            series.setPen(pen)
            series.setSymbol("o")
            series.setSymbolPen(pen)
            series.setSymbolBrush(brush)
            series.setSymbolSize(4)

    def _customize_context_menu(self, menu):
        # Helper to recursively find and hide
        for action in menu.actions():
            text = action.text()
            if text in ["Transforms", "Downsample", "Average", "Alpha", "Points", "Export..."]:
                action.setVisible(False)

        # Legend Toggle
        legend_action_text = "Show Legend"
        legend_action = None
        for action in menu.actions():
            if action.text() == legend_action_text:
                legend_action = action
                break

        if not legend_action:
            menu.addSeparator()
            legend_action = menu.addAction(legend_action_text)
            legend_action.setCheckable(True)
            legend_action.setChecked(True)  # Assume visible by default or check actual state
            if self._plot_item and self._plot_item.legend:
                legend_action.setChecked(self._plot_item.legend.isVisible())
            legend_action.triggered.connect(self._toggle_legend)

        # Horizontal Lines
        add_hline_text = "Add Horizontal Line..."
        menu.addSeparator()
        menu.addAction(add_hline_text, self._on_add_hline)

        clear_hline_text = "Clear Horizontal Lines"
        menu.addAction(clear_hline_text, self._on_clear_hlines)

        menu.addSeparator()
        menu.addAction("Set Title...", self._on_set_title)
        menu.addAction("Set Y Label...", self._on_set_ylabel)
        menu.addAction("Set Y Units...", self._on_set_yunits)

    def _on_set_title(self):
        if self._plot_item:
            text, ok = QtWidgets.QInputDialog.getText(
                None, "Set Plot Title", "Title:", text=self._plot_item.titleLabel.text
            )
            if ok:
                # self._plot_item.setTitle(text)
                # avoid setting empty string because it will hide the dock title bar
                self._plot_widget._plot_docks[self._plot_item].setTitle(text or " ")

    def _on_set_ylabel(self):
        if self._plot_item:
            axis = self._plot_item.getAxis("left")
            text, ok = QtWidgets.QInputDialog.getText(None, "Set Y Label", "Label:", text=axis.labelText)
            if ok:
                axis.setLabel(text=text, units=axis.labelUnits)

    def _on_set_yunits(self):
        if self._plot_item:
            axis = self._plot_item.getAxis("left")
            text, ok = QtWidgets.QInputDialog.getText(None, "Set Y Units", "Units:", text=axis.labelUnits)
            if ok:
                axis.setLabel(text=axis.labelText, units=text)

    def _toggle_legend(self, checked):
        if self._plot_item.legend:
            self._plot_item.legend.setVisible(checked)

    def _on_add_hline(self):
        self._plot_widget.add_horizontal_line_dialog(self._plot_item)

    def _on_clear_hlines(self):
        self._plot_widget.clear_horizontal_lines(self._plot_item)

    def mousePressEvent(self, ev):
        if (
            ev.button() == QtCore.Qt.MouseButton.LeftButton
            and ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._plot_widget._handle_ctrl_jump(self, self.mapSceneToView(ev.scenePos()))
            # After jump, fall through to allow the default pan/drag behavior
            ev.accept()
            super().mousePressEvent(ev)
            return

        super().mousePressEvent(ev)

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.LeftButton:
            if ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                # Manually compute Y range from children bounds
                bounds = self.childrenBounds()
                if bounds is not None:
                    y_bounds = bounds[1]
                    if y_bounds is not None and y_bounds[0] is not None and y_bounds[1] is not None:
                        self.setYRange(y_bounds[0], y_bounds[1], padding=0.05)

                self.enableAutoRange(pg.ViewBox.YAxis, True)
                self.enableAutoRange(pg.ViewBox.XAxis, False)
            elif ev.double():
                self.enableAutoRange(pg.ViewBox.XYAxes, True)
                self.autoRange()
            else:
                # Single click logic
                series = self._get_clicked_series(ev)
                if series and self._plot_widget.object_model:
                    # Find series item
                    entry = self._plot_widget._plot_entries.get(self._plot_item)
                    if entry and series in entry.series_items:
                        self._plot_widget.object_model.setActiveObject(entry.series_items[series])
                        ev.accept()
                        return

                # If not series or not found, delegate to default (which might select plot)
                # But _on_plot_clicked is not automatically called by pg.ViewBox click.
                # We should call it manually if we want clicking plot bg to select plot.
                if self._plot_item:
                    self._plot_widget._on_plot_clicked(self._plot_item)

            ev.accept()
            return

        super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev, axis=None):
        button = ev.button()
        modifiers = ev.modifiers()

        if button == QtCore.Qt.MouseButton.LeftButton:
            if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                ev.ignore()
                return

            if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                self._handle_rect_zoom_drag(ev, axis)
                return

            self.setMouseMode(self.PanMode)
            super().mouseDragEvent(ev, axis)
            return

        if button == QtCore.Qt.MouseButton.MiddleButton:
            super().mouseDragEvent(ev, axis)
            return

        if button == QtCore.Qt.MouseButton.RightButton:
            self._handle_axis_scale_drag(ev)
            return

        super().mouseDragEvent(ev, axis)

    def _handle_rect_zoom_drag(self, ev, axis):
        if ev.isStart():
            self._previous_mouse_mode = self.state["mouseMode"]
            self.setMouseMode(self.RectMode)

        super().mouseDragEvent(ev, axis)

        if ev.isFinish() and self._previous_mouse_mode is not None:
            self.setMouseMode(self._previous_mouse_mode)
            self._previous_mouse_mode = None

    def _handle_axis_scale_drag(self, ev):
        ev.accept()
        pos = ev.pos()

        if ev.isStart():
            self._right_drag_mode = None
            self._right_drag_start = pos
            self._right_last_pos = pos
            self._right_start_center = self.mapSceneToView(ev.scenePos())
            return

        if self._right_drag_mode is None:
            delta = pos - self._right_drag_start
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._right_drag_mode = "x" if abs(delta.x()) >= abs(delta.y()) else "y"

        if self._right_drag_mode is None:
            return

        delta = pos - self._right_last_pos
        self._right_last_pos = pos

        if self._right_drag_mode == "x":
            self._scale_axis(delta.x(), axis="x", scene_pos=ev.scenePos())
        else:
            self._scale_axis(-delta.y(), axis="y", scene_pos=ev.scenePos())

        if ev.isFinish():
            self._right_drag_mode = None
            self._right_drag_start = None
            self._right_last_pos = None
            self._right_start_center = None

    def _scale_axis(self, delta_pixels, axis: str, scene_pos):
        if delta_pixels == 0:
            return

        # Use an exponential scale factor for smooth zooming similar to ViewBox defaults.
        scale_factor = 1 - (delta_pixels * 0.01)
        scale_factor = max(0.1, min(10.0, scale_factor))
        center = self._right_start_center or self.mapSceneToView(scene_pos)

        if axis == "x":
            self.scaleBy((scale_factor, 1.0), center=center)
        else:
            self.scaleBy((1.0, scale_factor), center=center)


def updateStylePatched(self):
    r = "3px"
    if self.dim:
        fg = "#404040"
        bg = "#d0d0d0"
        border = "#d0d0d0"
    else:
        fg = "#fff"
        bg = "#808080"
        border = "#808080"

    if self.orientation == "vertical":
        self.vStyle = """DockLabel {
            background-color : %s;
            color : %s;
            border-top-right-radius: 0px;
            border-top-left-radius: %s;
            border-bottom-right-radius: 0px;
            border-bottom-left-radius: %s;
            border-width: 0px;
            border-right: 2px solid %s;
            padding-top: 3px;
            padding-bottom: 3px;
            font-size: 14px;
        }""" % (bg, fg, r, r, border)
        self.setStyleSheet(self.vStyle)
    else:
        self.hStyle = """DockLabel {
            background-color : %s;
            color : %s;
            border-top-right-radius: %s;
            border-top-left-radius: %s;
            border-bottom-right-radius: 0px;
            border-bottom-left-radius: 0px;
            border-width: 0px;
            border-bottom: 2px solid %s;
            padding-left: 13px;
            padding-right: 13px;
            font-size: 14px
        }""" % (bg, fg, r, r, border)
        self.setStyleSheet(self.hStyle)
