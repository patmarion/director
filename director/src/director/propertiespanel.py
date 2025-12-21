"""PropertiesPanel - Python implementation of property editing panel."""

from qtpy.QtWidgets import (
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QSlider,
    QColorDialog,
    QComboBox,
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPainter


class PropertyEditor(QWidget):
    """Base class for property editors."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(parent)
        self.propertySet = propertySet
        self.propertyName = propertyName
        self._updating = False  # Flag to prevent recursive updates

    def getValue(self):
        """Get current value from PropertySet."""
        return self.propertySet.getProperty(self.propertyName)

    def setValue(self, value):
        """Set value in PropertySet (if not currently updating)."""
        if not self._updating:
            self._updating = True
            try:
                self.propertySet.setProperty(self.propertyName, value)
            finally:
                self._updating = False

    def updateFromPropertySet(self):
        """Update editor widget from PropertySet value."""
        self._updating = True
        try:
            self._updateWidget(self.getValue())
        finally:
            self._updating = False

    def _updateWidget(self, value):
        """Override in subclasses to update the widget."""
        pass


class BoolEditor(PropertyEditor):
    """Checkbox editor for boolean properties."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(propertySet, propertyName, parent)
        self.checkbox = QCheckBox(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)

        self.checkbox.toggled.connect(self._onToggled)
        self.updateFromPropertySet()

    def _updateWidget(self, value):
        """Update checkbox state, blocking signals to prevent recursive updates."""
        # Block signals while updating to prevent triggering _onStateChanged
        self.checkbox.blockSignals(True)
        try:
            self.checkbox.setChecked(bool(value))
        finally:
            self.checkbox.blockSignals(False)

    def _onToggled(self, checked):
        """Handle checkbox state change."""
        if not self._updating:
            self.setValue(checked)


class EnumEditor(PropertyEditor):
    """Combo box editor for enum properties (integer with enumNames attribute)."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(propertySet, propertyName, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        attributes = propertySet._attributes.get(propertyName)
        enum_names = attributes.enumNames if attributes and attributes.enumNames else []

        self.comboBox = QComboBox(self)
        self.comboBox.addItems(enum_names)
        self.comboBox.currentIndexChanged.connect(self._onIndexChanged)

        layout.addWidget(self.comboBox)

        self.updateFromPropertySet()

    def _updateWidget(self, value):
        """Update combo box from property value (value is integer index)."""
        index = int(value) if isinstance(value, (int, float)) else 0
        # Clamp index to valid range
        max_index = self.comboBox.count() - 1
        index = max(0, min(index, max_index))
        self.comboBox.setCurrentIndex(index)

    def _onIndexChanged(self, index):
        """Handle combo box selection change."""
        if not self._updating:
            # Set the integer index as the property value
            self.setValue(index)


class IntEditor(PropertyEditor):
    """Spin box editor for integer properties (with optional slider)."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(propertySet, propertyName, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        attributes = propertySet._attributes.get(propertyName)
        if attributes:
            min_val = int(attributes.minimum)
            max_val = int(attributes.maximum)
            step = int(attributes.singleStep)
        else:
            min_val = -2147483647
            max_val = 2147483647
            step = 1

        self.spinbox = QSpinBox(self)
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setSingleStep(step)

        # Add slider if range is reasonable
        show_slider = (max_val - min_val) <= 1000 and (max_val - min_val) > 1
        if show_slider:
            self.slider = QSlider(Qt.Horizontal, self)
            self.slider.setMinimum(min_val)
            self.slider.setMaximum(max_val)
            self.slider.setSingleStep(step)
            layout.addWidget(self.slider, 1)
            self.slider.valueChanged.connect(self._onSliderChanged)
            self.spinbox.valueChanged.connect(self._onSpinBoxChanged)

        layout.addWidget(self.spinbox)

        self.spinbox.valueChanged.connect(self._onSpinBoxChanged)
        self.updateFromPropertySet()

    def _updateWidget(self, value):
        val = int(value)
        self.spinbox.setValue(val)
        if hasattr(self, "slider"):
            self.slider.setValue(val)

    def _onSpinBoxChanged(self, value):
        if not self._updating:
            self.setValue(value)
            if hasattr(self, "slider"):
                self._updating = True
                try:
                    self.slider.setValue(value)
                finally:
                    self._updating = False

    def _onSliderChanged(self, value):
        if not self._updating:
            self.setValue(value)
            self._updating = True
            try:
                self.spinbox.setValue(value)
            finally:
                self._updating = False


class FloatEditor(PropertyEditor):
    """Double spin box editor for float properties (with optional slider)."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(propertySet, propertyName, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        attributes = propertySet._attributes.get(propertyName)
        if attributes:
            min_val = float(attributes.minimum)
            max_val = float(attributes.maximum)
            step = float(attributes.singleStep)
            decimals = int(attributes.decimals)
        else:
            min_val = -1e9
            max_val = 1e9
            step = 1.0
            decimals = 5

        self.spinbox = QDoubleSpinBox(self)
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setSingleStep(step)
        self.spinbox.setDecimals(decimals)

        # Add slider if range is reasonable (normalize to 0-1000)
        show_slider = (max_val - min_val) <= 1000.0 and (max_val - min_val) > 0.01
        if show_slider:
            self.slider = QSlider(Qt.Horizontal, self)
            slider_max = 1000
            self.slider.setMinimum(0)
            self.slider.setMaximum(slider_max)
            layout.addWidget(self.slider, 1)
            self.slider.valueChanged.connect(self._onSliderChanged)
            self.spinbox.valueChanged.connect(self._onSpinBoxChanged)
            self._min_val = min_val
            self._max_val = max_val
            self._slider_max = slider_max

        layout.addWidget(self.spinbox)

        self.spinbox.valueChanged.connect(self._onSpinBoxChanged)
        self.updateFromPropertySet()

    def _updateWidget(self, value):
        val = float(value)
        self.spinbox.setValue(val)
        if hasattr(self, "slider"):
            # Convert value to slider range
            normalized = (val - self._min_val) / (self._max_val - self._min_val)
            slider_val = int(normalized * self._slider_max)
            self._updating = True
            try:
                self.slider.setValue(slider_val)
            finally:
                self._updating = False

    def _onSpinBoxChanged(self, value):
        if not self._updating:
            self.setValue(value)
            if hasattr(self, "slider"):
                # Convert value to slider range
                normalized = (value - self._min_val) / (self._max_val - self._min_val)
                slider_val = int(normalized * self._slider_max)
                self._updating = True
                try:
                    self.slider.setValue(slider_val)
                finally:
                    self._updating = False

    def _onSliderChanged(self, value):
        if not self._updating:
            # Convert slider value back to property range
            normalized = value / self._slider_max
            prop_value = self._min_val + normalized * (self._max_val - self._min_val)
            self.setValue(prop_value)
            self._updating = True
            try:
                self.spinbox.setValue(prop_value)
            finally:
                self._updating = False


class StringEditor(PropertyEditor):
    """Line edit editor for string properties."""

    def __init__(self, propertySet, propertyName, parent=None):
        super().__init__(propertySet, propertyName, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lineEdit = QLineEdit(self)
        layout.addWidget(self.lineEdit)

        self.lineEdit.editingFinished.connect(self._onEditingFinished)
        self.updateFromPropertySet()

    def _updateWidget(self, value):
        self.lineEdit.setText(str(value))

    def _onEditingFinished(self):
        if not self._updating:
            self.setValue(self.lineEdit.text())


class ColorSquare(QWidget):
    """Small widget that displays a color square."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
        self.setMinimumSize(20, 20)
        self.setMaximumSize(20, 20)

    def setColor(self, color):
        """Set the color (expects [r, g, b] in 0-1 range)."""
        self.color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)
        painter.setPen(Qt.black)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)


class ColorArrayEditor(PropertyEditor):
    """Color editor as an expandable array-like structure with Red/Green/Blue components."""

    def __init__(self, propertySet, propertyName, treeItem, parent=None):
        # Use the tree widget as parent if available
        if parent is None and treeItem.treeWidget() is not None:
            parent = treeItem.treeWidget()
        super().__init__(propertySet, propertyName, parent)
        self.treeItem = treeItem
        self.childEditors = {}

        # Create widget for main row: color square + picker button
        self._createMainRowWidget()

        self._updateColorChildren()
        self._updateMainRowWidget()
        # Color should be collapsed by default
        self.treeItem.setExpanded(False)

    def _createMainRowWidget(self):
        """Create the widget for the main row (color square + picker button)."""
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        value = self.getValue()
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            self.colorSquare = ColorSquare(value, main_widget)
        else:
            self.colorSquare = ColorSquare([1.0, 1.0, 1.0], main_widget)
        layout.addWidget(self.colorSquare)

        self.pickerButton = QPushButton("Pick Color...", main_widget)
        self.pickerButton.clicked.connect(self._onPickColor)
        layout.addWidget(self.pickerButton)
        layout.addStretch()

        # Set the widget in the tree
        tree_widget = self.treeItem.treeWidget()
        if tree_widget:
            tree_widget.setItemWidget(self.treeItem, 1, main_widget)

    def _updateMainRowWidget(self):
        """Update the main row widget (color square) from property value."""
        value = self.getValue()
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            if hasattr(self, "colorSquare"):
                self.colorSquare.setColor(value)

    def _updateColorChildren(self):
        """Create or update child items for Red, Green, Blue components."""
        value = self.getValue()
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            return

        # Component names and indices
        components = [("Red", 0), ("Green", 1), ("Blue", 2)]

        # Remove extra children if any
        while self.treeItem.childCount() > len(components):
            child = self.treeItem.takeChild(self.treeItem.childCount() - 1)
            if child.text(0) in self.childEditors:
                del self.childEditors[child.text(0)]

        # Create or update component editors
        for comp_name, index in components:
            child_item = None

            # Find existing child
            for j in range(self.treeItem.childCount()):
                if self.treeItem.child(j).text(0) == comp_name:
                    child_item = self.treeItem.child(j)
                    break

            if child_item is None:
                child_item = QTreeWidgetItem(self.treeItem, [comp_name, ""])
                child_item.setFlags(child_item.flags() & ~Qt.ItemIsSelectable)
                self.treeItem.addChild(child_item)

            # Create editor for this component if needed
            if comp_name not in self.childEditors:
                # Pass the float value (0.0-1.0) - editor will convert to int (0-255) for display
                editor = ColorComponentEditor(
                    self.propertySet, self.propertyName, index, value[index] if index < len(value) else 0.0
                )
                if editor:
                    tree_widget = self.treeItem.treeWidget()
                    if tree_widget:
                        tree_widget.setItemWidget(child_item, 1, editor)
                        self.childEditors[comp_name] = editor

        # Update existing editors
        for comp_name, index in components:
            if comp_name in self.childEditors:
                self.childEditors[comp_name].updateFromPropertySet()

    def _onPickColor(self):
        """Open color picker dialog."""
        value = self.getValue()
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            current_color = QColor(int(value[0] * 255), int(value[1] * 255), int(value[2] * 255))
        else:
            current_color = QColor(255, 255, 255)

        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            new_value = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
            self.setValue(new_value)

    def updateFromPropertySet(self):
        """Update color editor when property changes."""
        self._updateColorChildren()
        self._updateMainRowWidget()


class ColorComponentEditor(PropertyEditor):
    """Editor for a single color component (Red, Green, or Blue).

    Displays as integer 0-255, but stores as float 0.0-1.0 in PropertySet.
    """

    def __init__(self, propertySet, propertyName, index, initial_value, parent=None):
        super().__init__(propertySet, f"{propertyName}[{index}]", parent)
        self.colorPropertyName = propertyName
        self.index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create an integer spin box for the component (0-255 for display)
        self.spinBox = QSpinBox(self)
        self.spinBox.setMinimum(0)
        self.spinBox.setMaximum(255)
        self.spinBox.setSingleStep(1)
        self.spinBox.valueChanged.connect(self._onChanged)
        layout.addWidget(self.spinBox)

        self.updateFromPropertySet()

    def getValue(self):
        """Get value from color array at our index (returns float 0.0-1.0)."""
        array_value = self.propertySet.getProperty(self.colorPropertyName)
        if isinstance(array_value, (list, tuple)) and self.index < len(array_value):
            return array_value[self.index]
        return 0.0

    def setValue(self, value):
        """Set value in color array at our index.

        Args:
            value: Can be float (0.0-1.0) or int (0-255). Will be converted to float 0.0-1.0.
        """
        array_value = list(self.propertySet.getProperty(self.colorPropertyName))
        if self.index < len(array_value):
            # Convert to float 0.0-1.0 if needed
            if isinstance(value, int) and value >= 0 and value <= 255:
                # Assume it's a 0-255 integer value
                float_value = value / 255.0
            else:
                # Already a float 0.0-1.0 or needs conversion
                float_value = float(value)
                if float_value > 1.0:
                    # If > 1.0, assume it's 0-255 range
                    float_value = float_value / 255.0
                float_value = max(0.0, min(1.0, float_value))  # Clamp to 0.0-1.0

            array_value[self.index] = float_value
            self.propertySet.setProperty(self.colorPropertyName, array_value)

    def _updateWidget(self, value):
        """Update editor widget from value (value is float 0.0-1.0, display as int 0-255)."""
        # Convert float 0.0-1.0 to int 0-255 for display
        if isinstance(value, (int, float)):
            int_value = int(round(float(value) * 255.0))
            int_value = max(0, min(255, int_value))  # Clamp to 0-255
        else:
            int_value = 0
        self.spinBox.setValue(int_value)

    def _onChanged(self):
        """Handle spinbox value change (spinbox shows 0-255, convert to 0.0-1.0 for storage)."""
        if not self._updating:
            # Spinbox value is 0-255, convert to 0.0-1.0 float for storage
            int_value = self.spinBox.value()
            float_value = int_value / 255.0
            self.setValue(float_value)


class ArrayEditor(PropertyEditor):
    """Editor for array properties - creates expandable item with child editors."""

    def __init__(self, propertySet, propertyName, treeItem, parent=None, expanded_by_default=False):
        # Array editor doesn't create a widget, but PropertyEditor expects one
        # Use the tree widget as parent if available
        if parent is None and treeItem.treeWidget() is not None:
            parent = treeItem.treeWidget()
        super().__init__(propertySet, propertyName, parent)
        # Array editor doesn't create a widget for itself
        # Instead, it manages child items in the tree
        self.treeItem = treeItem
        self.childEditors = {}
        self.summaryWidget = None
        self._updateArrayChildren()
        self._ensureSummaryWidget()
        # Update main row text and set expansion state
        self._updateMainRowText()
        if expanded_by_default:
            self.treeItem.setExpanded(True)

    def _updateArrayChildren(self):
        """Create or update child items for array elements."""
        value = self.getValue()
        if not isinstance(value, (list, tuple)):
            return

        # Remove extra children
        while self.treeItem.childCount() > len(value):
            child = self.treeItem.takeChild(self.treeItem.childCount() - 1)
            if child.text(0) in self.childEditors:
                del self.childEditors[child.text(0)]

        # Add or update children
        for i, elem_value in enumerate(value):
            child_name = f"[{i}]"
            child_item = None

            # Find existing child
            for j in range(self.treeItem.childCount()):
                if self.treeItem.child(j).text(0) == child_name:
                    child_item = self.treeItem.child(j)
                    break

            if child_item is None:
                child_item = QTreeWidgetItem(self.treeItem, [child_name, ""])
                child_item.setFlags(child_item.flags() & ~Qt.ItemIsSelectable)
                self.treeItem.addChild(child_item)

            # Create appropriate editor for this element
            if child_name not in self.childEditors:
                editor = self._createElementEditor(i, elem_value)
                if editor:
                    tree_widget = self.treeItem.treeWidget()
                    if tree_widget:
                        tree_widget.setItemWidget(child_item, 1, editor)
                        self.childEditors[child_name] = editor

        # Update existing editors
        for i, elem_value in enumerate(value):
            child_name = f"[{i}]"
            if child_name in self.childEditors:
                self.childEditors[child_name].updateFromPropertySet()

    def _ensureSummaryWidget(self):
        if self.summaryWidget or self.treeItem.treeWidget() is None:
            return
        line_edit = QLineEdit(self.treeItem.treeWidget())
        line_edit.setReadOnly(True)
        line_edit.setFrame(False)
        line_edit.setFocusPolicy(Qt.ClickFocus)
        self.treeItem.treeWidget().setItemWidget(self.treeItem, 1, line_edit)
        self.summaryWidget = line_edit

    def _createElementEditor(self, index, value):
        """Create an editor widget for an array element."""
        # Create a fake property name for this element
        element_prop_name = f"{self.propertyName}[{index}]"

        # Determine type from value
        if isinstance(value, bool):
            # We need to handle array elements differently
            # For now, create a simple editor that updates the array
            return ArrayElementEditor(self.propertySet, self.propertyName, index, value)
        elif isinstance(value, int):
            return ArrayElementEditor(self.propertySet, self.propertyName, index, value)
        elif isinstance(value, float):
            return ArrayElementEditor(self.propertySet, self.propertyName, index, value)
        elif isinstance(value, str):
            return ArrayElementEditor(self.propertySet, self.propertyName, index, value)
        else:
            return ArrayElementEditor(self.propertySet, self.propertyName, index, value)

    def _updateMainRowText(self):
        """Update the main row text with array representation."""
        value = self.getValue()
        if isinstance(value, (list, tuple)):
            str_values = [self._format_component(v) for v in value]
            array_str = "[" + ", ".join(str_values) + "]"
            self._ensureSummaryWidget()
            if self.summaryWidget:
                self.summaryWidget.setText(array_str)
            else:
                self.treeItem.setText(1, array_str)

    @staticmethod
    def _format_component(value):
        if isinstance(value, float):
            formatted = f"{value:.6f}".rstrip("0").rstrip(".")
            if formatted in ("", "-", "-0"):
                formatted = "0"
            if formatted == "-":
                formatted = "0"
            if formatted == "-0":
                formatted = "0"
            if formatted.startswith("-0.") and formatted != "-0":
                formatted = "-" + formatted[1:]
            return formatted
        return str(value)

    def updateFromPropertySet(self):
        """Update array editor when property changes."""
        self._updateArrayChildren()
        self._updateMainRowText()


class ArrayElementEditor(PropertyEditor):
    """Editor for a single array element."""

    def __init__(self, propertySet, propertyName, index, initial_value, parent=None):
        # Create a synthetic property name
        super().__init__(propertySet, f"{propertyName}[{index}]", parent)
        self.arrayPropertyName = propertyName
        self.index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create appropriate editor based on value type
        if isinstance(initial_value, bool):
            self.editor = QCheckBox(self)
            self.editor.toggled.connect(self._onChanged)
            layout.addWidget(self.editor)
        elif isinstance(initial_value, int):
            self.editor = QSpinBox(self)
            attributes = propertySet._attributes.get(propertyName)
            if attributes:
                self.editor.setMinimum(int(attributes.minimum))
                self.editor.setMaximum(int(attributes.maximum))
                self.editor.setSingleStep(int(attributes.singleStep))
            self.editor.valueChanged.connect(self._onChanged)
            layout.addWidget(self.editor)
        elif isinstance(initial_value, float):
            self.editor = QDoubleSpinBox(self)
            attributes = propertySet._attributes.get(propertyName)
            if attributes:
                self.editor.setMinimum(float(attributes.minimum))
                self.editor.setMaximum(float(attributes.maximum))
                self.editor.setSingleStep(float(attributes.singleStep))
                self.editor.setDecimals(int(attributes.decimals))
            else:
                self.editor.setDecimals(5)
            self.editor.valueChanged.connect(self._onChanged)
            layout.addWidget(self.editor)
        elif isinstance(initial_value, str):
            self.editor = QLineEdit(self)
            self.editor.editingFinished.connect(self._onChanged)
            layout.addWidget(self.editor)
        else:
            # Fallback: line edit
            self.editor = QLineEdit(self)
            self.editor.editingFinished.connect(self._onChanged)
            layout.addWidget(self.editor)

        self.updateFromPropertySet()

    def getValue(self):
        """Get value from array at our index."""
        array_value = self.propertySet.getProperty(self.arrayPropertyName)
        if isinstance(array_value, (list, tuple)) and self.index < len(array_value):
            return array_value[self.index]
        return None

    def setValue(self, value):
        """Set value in array at our index."""
        array_value = list(self.propertySet.getProperty(self.arrayPropertyName))
        if self.index < len(array_value):
            array_value[self.index] = value
            self.propertySet.setProperty(self.arrayPropertyName, array_value)

    def _updateWidget(self, value):
        """Update editor widget from value."""
        if isinstance(self.editor, QCheckBox):
            # Block signals to prevent triggering _onChanged during update
            self.editor.blockSignals(True)
            try:
                self.editor.setChecked(bool(value))
            finally:
                self.editor.blockSignals(False)
        elif isinstance(self.editor, (QSpinBox, QDoubleSpinBox)):
            self.editor.setValue(float(value) if isinstance(value, (int, float)) else 0)
        elif isinstance(self.editor, QLineEdit):
            self.editor.setText(str(value))

    def _onChanged(self):
        """Handle editor value change."""
        if self._updating:
            return

        if isinstance(self.editor, QCheckBox):
            value = self.editor.isChecked()
        elif isinstance(self.editor, (QSpinBox, QDoubleSpinBox)):
            value = self.editor.value()
        elif isinstance(self.editor, QLineEdit):
            value = self.editor.text()
        else:
            return

        self.setValue(value)


class PropertiesPanel(QWidget):
    """Panel for editing PropertySet properties."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.propertySet = None
        self.connections = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Property", "Value"])
        self.tree.header().setStretchLastSection(True)
        self.tree.setColumnWidth(0, 200)
        # Disable all selection - no row or cell highlighting needed
        self.tree.setSelectionMode(QTreeWidget.NoSelection)
        # Disable focus to prevent any selection-like highlighting
        self.tree.setFocusPolicy(Qt.NoFocus)
        # self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)

        # Map property names to tree items
        self.propertyToItem = {}
        self.itemToProperty = {}
        self.itemToEditor = {}

    def clear(self):
        """Clear the panel and disconnect from PropertySet."""
        # Disconnect callbacks
        for connection in self.connections:
            if self.propertySet:
                self.propertySet.callbacks.disconnect(connection)
        self.connections = []

        # Clear tree
        self.tree.clear()
        self.propertyToItem.clear()
        self.itemToProperty.clear()
        self.itemToEditor.clear()

        self.propertySet = None

    def hide_header(self, hide: bool = True):
        """Hide or show the tree header."""
        self.tree.header().setVisible(not hide)

    def connectProperties(self, propertySet):
        """Connect to a PropertySet and populate the panel."""
        self.clear()
        self.propertySet = propertySet

        # Connect callbacks
        self.connections.append(propertySet.connectPropertyChanged(self._onPropertyChanged))
        self.connections.append(propertySet.connectPropertyAdded(self._onPropertyAdded))
        self.connections.append(propertySet.connectPropertyRemoved(self._onPropertyRemoved))
        self.connections.append(propertySet.connectPropertyAttributeChanged(self._onPropertyAttributeChanged))

        # Populate from existing properties
        for propName in propertySet.propertyNames():
            self._addProperty(propName)

    def _addProperty(self, propertyName):
        """Add a property to the tree (handles nested paths)."""
        # Split property path (e.g., "nest1/prop1" -> ["nest1", "prop1"])
        path_parts = propertyName.split("/")

        # Navigate/create parent items
        parent_item = self.tree.invisibleRootItem()
        for part in path_parts[:-1]:
            # Look for existing parent item
            found = False
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == part and child.text(1) == "":  # Empty value means it's a folder
                    parent_item = child
                    found = True
                    break

            if not found:
                # Create new parent item
                parent_item = QTreeWidgetItem(parent_item, [part, ""])
                parent_item.setFlags(parent_item.flags() & ~Qt.ItemIsSelectable)
                parent_item.setExpanded(True)

        # Create item for the actual property
        leaf_name = path_parts[-1]
        item = QTreeWidgetItem(parent_item, [leaf_name, ""])
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        parent_item.addChild(item)

        # Store mappings
        self.propertyToItem[propertyName] = item
        self.itemToProperty[item] = propertyName

        # Create appropriate editor
        value = self.propertySet.getProperty(propertyName)
        attributes = self.propertySet._attributes.get(propertyName)

        editor = self._createEditor(propertyName, value, attributes)

        # Special handling for arrays (but not colors - colors are handled separately)
        is_array = isinstance(value, (list, tuple)) and len(value) > 0
        is_color = "color" in propertyName.lower() and isinstance(value, (list, tuple)) and len(value) == 3

        if is_array and not is_color:
            # Array editor doesn't create a widget for itself, it manages children
            # Expand if list has 6 or fewer elements
            expanded_by_default = len(value) <= 6
            array_editor = ArrayEditor(self.propertySet, propertyName, item, expanded_by_default=expanded_by_default)
            self.itemToEditor[item] = array_editor
        elif is_color:
            # Color should be expandable like arrays
            color_editor = ColorArrayEditor(self.propertySet, propertyName, item)
            self.itemToEditor[item] = color_editor
        elif editor:
            self.tree.setItemWidget(item, 1, editor)
            self.itemToEditor[item] = editor

        parent_item.setExpanded(True)

        item.setHidden(bool(attributes.hidden))

    def _createEditor(self, propertyName, value, attributes):
        """Create an appropriate editor widget for a property."""
        if isinstance(value, bool):
            return BoolEditor(self.propertySet, propertyName)
        elif isinstance(value, int):
            # Check if this is an enum property (has enumNames attribute)
            if attributes and attributes.enumNames:
                return EnumEditor(self.propertySet, propertyName)
            else:
                return IntEditor(self.propertySet, propertyName)
        elif isinstance(value, float):
            return FloatEditor(self.propertySet, propertyName)
        elif isinstance(value, str):
            return StringEditor(self.propertySet, propertyName)
        elif isinstance(value, (list, tuple)):
            # Arrays and colors are handled specially in _addProperty
            return None
        else:
            # Fallback: string editor
            return StringEditor(self.propertySet, propertyName)

    def _removeProperty(self, propertyName):
        """Remove a property from the tree."""
        if propertyName in self.propertyToItem:
            item = self.propertyToItem[propertyName]
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

            # Clean up mappings
            del self.propertyToItem[propertyName]
            if item in self.itemToProperty:
                del self.itemToProperty[item]
            if item in self.itemToEditor:
                del self.itemToEditor[item]

    def _onPropertyChanged(self, propertySet, propertyName):
        """Handle property value change."""
        if propertyName in self.propertyToItem:
            item = self.propertyToItem[propertyName]
            if item in self.itemToEditor:
                editor = self.itemToEditor[item]
                if isinstance(editor, (ArrayEditor, ColorArrayEditor)):
                    # Array/Color editors need special handling to update children
                    editor.updateFromPropertySet()
                else:
                    editor.updateFromPropertySet()

    def _onPropertyAdded(self, propertySet, propertyName):
        """Handle property added."""
        self._addProperty(propertyName)

    def _onPropertyRemoved(self, propertySet, propertyName):
        """Handle property removed."""
        self._removeProperty(propertyName)

    def _onPropertyAttributeChanged(self, propertySet, propertyName, attributeName):
        """Handle property attribute change, including hidden and readOnly."""
        if propertyName in self.propertyToItem:
            item = self.propertyToItem[propertyName]
            editor = self.itemToEditor.get(item)

            # Handle 'hidden' attribute: show/hide the row
            if attributeName == "hidden":
                attributes = propertySet._attributes.get(propertyName)
                if attributes and hasattr(item, "setHidden"):  # Qt API: QTreeWidgetItem.setHidden(bool)
                    item.setHidden(bool(attributes.hidden))

            # Handle 'readOnly' attribute: set editor enabled/disabled or swap for label
            elif attributeName == "readOnly":
                attributes = propertySet._attributes.get(propertyName)
                read_only = attributes.readOnly if attributes else False
                if item in self.itemToEditor:
                    editor = self.itemToEditor[item]
                    if hasattr(editor, "setEnabled"):
                        # Try disabling/enabling the editor widget itself
                        try:
                            editor.setEnabled(not read_only)
                        except Exception:
                            pass
                    elif read_only:
                        # Fallback: replace with a label showing value
                        from qtpy.QtWidgets import QLabel

                        value = propertySet.getProperty(propertyName)
                        label = QLabel(str(value), self.tree)
                        self.tree.setItemWidget(item, 1, label)
                        self.itemToEditor[item] = label
                    else:
                        # If not readOnly and previously swapped with a label, try to restore editor
                        self._onPropertyChanged(propertySet, propertyName)
                return

            elif attributeName == "enumNames":
                if isinstance(editor, EnumEditor):
                    # For enum properties, if enumNames changed, recreate the editor
                    # Recreate the editor with new enum values
                    value = propertySet.getProperty(propertyName)
                    attributes = propertySet._attributes.get(propertyName)

                    # Remove old editor
                    self.tree.setItemWidget(item, 1, None)
                    del self.itemToEditor[item]

                    # Create new editor
                    new_editor = EnumEditor(self.propertySet, propertyName)
                    self.tree.setItemWidget(item, 1, new_editor)
                    self.itemToEditor[item] = new_editor
            elif hasattr(editor, "updateFromPropertySet"):
                # For other attributes, just update the existing editor
                editor.updateFromPropertySet()
