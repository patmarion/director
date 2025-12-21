"""Value slider widget with play/pause controls."""

from director import callbacks
from director.flags import Flags
from director.timercallback import TimerCallback
from director import qtutils
import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets

import time
import numpy as np


class ValueSlider(object):
    """Slider widget with double spin box and play/pause button."""

    events = Flags("VALUE_CHANGED")

    def __init__(self, minValue=0.0, maxValue=1.0, resolution=1000):
        """Initialize ValueSlider.

        Args:
            minValue: Minimum value
            maxValue: Maximum value
            resolution: Slider resolution (number of steps)
        """
        self._value = 0.0
        self.spinbox = QtWidgets.QDoubleSpinBox()
        self.spinbox.setSuffix("s")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.playButton = QtWidgets.QPushButton()
        self.playButton.setFlat(True)
        style = QtWidgets.QApplication.style()
        self._play_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)
        self._pause_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPause)
        self._updatePlayButtonIcon(is_playing=False)
        self.speedComboBox = QtWidgets.QComboBox()
        self._setupSpeedComboBox()
        self.setValueRange(minValue, maxValue)
        self.setResolution(resolution)
        self.slider.valueChanged.connect(self._onSliderValueChanged)
        self.spinbox.valueChanged.connect(self._onSpinboxValueChanged)
        self.playButton.clicked.connect(self.togglePlayPause)
        self.speedComboBox.currentTextChanged.connect(self._onSpeedComboBoxChanged)
        self.widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.playButton)
        layout.addWidget(self.spinbox)
        layout.addWidget(self.slider)
        layout.addWidget(self.speedComboBox)

        self.animationPrevTime = 0.0
        self.animationRate = 1.0
        self.animationRateTarget = 1.0
        self.animationRateAlpha = 1.0
        self.animationTimer = TimerCallback(callback=self._tick, targetFps=60)
        self.useRealTime = True

        self.callbacks = callbacks.CallbackRegistry(self.events._fields)

        # Event filter for direct slider clicking
        self.eventFilter = SliderEventFilter(self)
        self.slider.installEventFilter(self.eventFilter)

    def _tick(self):
        """Timer callback for animation."""
        if self.useRealTime:
            tnow = time.time()
            dt = tnow - self.animationPrevTime
            self.animationPrevTime = tnow
        else:
            dt = 1.0 / self.animationTimer.targetFps

        self.animationRate = (
            1.0 - self.animationRateAlpha
        ) * self.animationRate + self.animationRateAlpha * self.animationRateTarget

        valueChange = dt * self.animationRate
        value = self.getValue() + valueChange
        if value > self.maxValue:
            self.setValue(self.maxValue)
            self.pause()
            return False
        self.setValue(value)
        return True

    def setAnimationRate(self, animationRate, rateAlpha=1.0):
        """Set animation playback rate.

        Args:
            animationRate: Rate of change per second
            rateAlpha: Smoothing factor (0-1)
        """
        self.animationRateTarget = animationRate
        self.animationRateAlpha = rateAlpha

    def play(self):
        """Start animation playback."""
        self._updatePlayButtonIcon(is_playing=True)
        self.animationPrevTime = time.time()
        self.animationTimer.start()

    def pause(self):
        """Pause animation playback."""
        self._updatePlayButtonIcon(is_playing=False)
        self.animationTimer.stop()

    def togglePlayPause(self):
        """Handle play/pause button click."""
        if self.animationTimer.isActive():
            self.pause()
        else:
            if self.slider.value() >= self.slider.maximum():
                self.setValue(self.minValue)
            self.play()

    def setResolution(self, resolution):
        """Set slider resolution.

        Args:
            resolution: Maximum slider value (number of steps)
        """
        with qtutils.BlockSignals(self.slider):
            self.slider.setMaximum(resolution)
        self._syncSlider()

    def setValueRange(self, minValue, maxValue):
        """Set the value range.

        Args:
            minValue: Minimum value
            maxValue: Maximum value
        """
        newValue = np.clip(self._value, minValue, maxValue)
        changed = newValue != self._value
        self.minValue = minValue
        self.maxValue = maxValue
        self._value = newValue
        with qtutils.BlockSignals(self.spinbox):
            self.spinbox.setMinimum(minValue)
            self.spinbox.setMaximum(maxValue)
        self._syncSpinBox()
        self._syncSlider()
        if changed:
            self._notifyValueChanged()

    def getValue(self):
        """Get current value."""
        return self._value

    def setValue(self, value):
        """Set current value.

        Args:
            value: Value to set (will be clipped to range)
        """
        self._value = np.clip(value, self.minValue, self.maxValue)
        self._syncSlider()
        self._syncSpinBox()
        self._notifyValueChanged()

    def connectValueChanged(self, callback):
        """Connect callback to value changed event.

        Args:
            callback: Function to call when value changes

        Returns:
            Callback ID for disconnection
        """
        return self.callbacks.connect(self.events.VALUE_CHANGED, callback)

    def _notifyValueChanged(self):
        """Notify listeners of value change."""
        self.callbacks.process(self.events.VALUE_CHANGED, self._value)

    def _syncSlider(self):
        """Sync slider position to current value."""
        with qtutils.BlockSignals(self.slider):
            slider_value = int(
                self.slider.maximum() * (self._value - self.minValue) / float(self.maxValue - self.minValue)
            )
            self.slider.setValue(slider_value)

    def _syncSpinBox(self):
        """Sync spin box value to current value."""
        with qtutils.BlockSignals(self.spinbox):
            self.spinbox.setValue(self._value)

    def _onSpinboxValueChanged(self, spinboxValue):
        """Handle spin box value change."""
        self._value = spinboxValue
        self._syncSlider()
        self._notifyValueChanged()

    def _onSliderValueChanged(self, sliderValue):
        """Handle slider value change."""
        self._value = self.minValue + (self.maxValue - self.minValue) * (sliderValue / float(self.slider.maximum()))
        self._syncSpinBox()
        self._notifyValueChanged()

    def _setupSpeedComboBox(self):
        """Setup speed combobox with predefined speed options."""
        speed_options = ["10x", "8x", "6x", "5x", "4x", "3x", "2x", "1x", "0.5x", "0.25x", "0.1x"]
        self.speedComboBox.addItems(speed_options)
        # Add separator after predefined speeds
        self.speedComboBox.insertSeparator(len(speed_options))
        # Add "Enter custom value" after separator
        self.speedComboBox.addItem("Enter custom value")
        # Set default to 1x
        self.speedComboBox.setCurrentText("1x")

    def _onSpeedComboBoxChanged(self, text):
        """Handle speed combobox selection change."""
        if text == "Enter custom value":
            # Open input dialog for custom value
            value, ok = QtWidgets.QInputDialog.getDouble(
                self.widget,
                "Custom Playback Speed",
                "Enter playback speed:",
                1.0,  # value
                0.01,  # min
                100.0,  # max
                2,  # decimals
            )
            if ok:
                # Format the custom value
                custom_text = f"{value}x"
                # Check if this custom value already exists
                existing_index = self.speedComboBox.findText(custom_text)
                if existing_index >= 0:
                    # If it exists, just select it
                    with qtutils.BlockSignals(self.speedComboBox):
                        self.speedComboBox.setCurrentText(custom_text)
                else:
                    # Find the index of "Enter custom value" (after separator)
                    enter_custom_index = self.speedComboBox.findText("Enter custom value")
                    # Insert the custom value after the separator, before "Enter custom value"
                    with qtutils.BlockSignals(self.speedComboBox):
                        self.speedComboBox.insertItem(enter_custom_index, custom_text)
                        self.speedComboBox.setCurrentText(custom_text)
                # Set the animation rate
                self.setAnimationRate(value)
        else:
            # Parse the speed value from text (e.g., "2x" -> 2.0, "0.5x" -> 0.5)
            try:
                speed_value = float(text.rstrip("x"))
                self.setAnimationRate(speed_value)
            except ValueError:
                # If parsing fails, default to 1x
                self.setAnimationRate(1.0)

    def _updatePlayButtonIcon(self, is_playing: bool):
        """Update play button to show play/pause icon."""
        icon = self._pause_icon if is_playing else self._play_icon
        tooltip = "Pause" if is_playing else "Play"
        self.playButton.setIcon(icon)
        self.playButton.setToolTip(tooltip)


class SliderEventFilter(QtCore.QObject):
    """Event filter for direct slider clicking."""

    def __init__(self, valueSlider):
        """Initialize event filter.

        Args:
            valueSlider: ValueSlider instance
        """
        super().__init__()
        self.valueSlider = valueSlider

    def eventFilter(self, obj, event):
        """Filter mouse events for direct slider clicking.

        Args:
            obj: Object receiving the event
            event: QEvent

        Returns:
            True if event was handled, False otherwise
        """
        if not obj.isEnabled():
            return False
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                # Get mouse position
                pos = event.pos()
                x = pos.x()
                val = QtWidgets.QStyle.sliderValueFromPosition(obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        elif event.type() == QtCore.QEvent.Type.MouseMove:
            if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                # Get mouse position
                pos = event.pos()
                x = pos.x()
                val = QtWidgets.QStyle.sliderValueFromPosition(obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        return False
