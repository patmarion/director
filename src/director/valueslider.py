"""Value slider widget with play/pause controls."""

import time

import numpy as np
import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets

from director import callbacks, qtutils
from director.flags import Flags
from director.qtutils import EventFilterDelegate
from director.timercallback import TimerCallback


class ValueSlider:
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
        self._sliderEventFilter = EventFilterDelegate(self._handleSliderEvent)
        self.slider.installEventFilter(self._sliderEventFilter)

        # For optional keyboard shortcuts and mouse scrubber
        self.shortcuts = []
        self.mouseScrubber = None

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

    def stepBackward(self):
        """Step slider backward by single step."""
        self.slider.setValue(self.slider.value() - self.slider.singleStep())

    def stepForward(self):
        """Step slider forward by single step."""
        self.slider.setValue(self.slider.value() + self.slider.singleStep())

    def jumpBackward(self):
        """Jump slider backward by page step."""
        self.slider.setValue(self.slider.value() - self.slider.pageStep())

    def jumpForward(self):
        """Jump slider forward by page step."""
        self.slider.setValue(self.slider.value() + self.slider.pageStep())

    def togglePlayForward(self):
        """Toggle forward playback."""
        isPlayingForward = self.animationTimer.isActive() and self.animationRateTarget > 0
        self.setAnimationRate(np.abs(self.animationRateTarget))
        if isPlayingForward:
            self.pause()
        else:
            self.play()

    def togglePlayReverse(self):
        """Toggle reverse playback."""
        isPlayingReverse = self.animationTimer.isActive() and self.animationRateTarget < 0
        self.setAnimationRate(-1 * np.abs(self.animationRateTarget))
        if isPlayingReverse:
            self.pause()
        else:
            self.play()

    def setResolution(self, resolution):
        """Set slider resolution.

        Args:
            resolution: Maximum slider value (number of steps)
        """
        resolution = min(resolution, 32767)
        with qtutils.BlockSignals(self.slider):
            self.slider.setMaximum(resolution)
        self._syncSlider()

    def setValueRange(self, minValue, maxValue, newValue=None, notifyChange=True):
        """Set the value range.

        Args:
            minValue: Minimum value
            maxValue: Maximum value
            newValue: Optional new value to set (defaults to current value clipped to range)
            notifyChange: Whether to notify listeners if value changed (default True)
        """
        newValue = self._value if newValue is None else newValue
        newValue = np.clip(newValue, minValue, maxValue)
        changed = newValue != self._value
        self.minValue = minValue
        self.maxValue = maxValue
        self._value = newValue
        with qtutils.BlockSignals(self.spinbox):
            self.spinbox.setMinimum(minValue)
            self.spinbox.setMaximum(maxValue)
        self._syncSpinBox()
        self._syncSlider()
        if changed and notifyChange:
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

    def initMouseScrubber(self, widget):
        """Initialize mouse scrubber for alt+drag scrubbing.

        Args:
            widget: Widget to install the mouse scrubber on
        """
        self.mouseScrubber = MouseScrubber(widget, self.slider)

    def initKeyboardShortcuts(self, widget):
        """Initialize keyboard shortcuts for playback control.

        Args:
            widget: Widget to install shortcuts on

        Shortcuts:
            [: Step backward
            ]: Step forward
            shift+[: Jump backward
            shift+]: Jump forward
            space: Toggle forward playback
            shift+space: Toggle reverse playback
        """
        import qtpy.QtGui as QtGui

        commands = {
            "[": self.stepBackward,
            "]": self.stepForward,
            "shift+[": self.jumpBackward,
            "shift+]": self.jumpForward,
            " ": self.togglePlayForward,
            "shift+ ": self.togglePlayReverse,
        }
        self.shortcuts = []
        for keySequence, func in commands.items():
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(keySequence), widget)
            shortcut.activated.connect(func)
            self.shortcuts.append(shortcut)

    def _handleSliderEvent(self, obj, event):
        """Handle mouse events for direct slider clicking.

        Args:
            obj: Slider receiving the event
            event: QEvent

        Returns:
            True if event was handled, False otherwise
        """
        if not obj.isEnabled():
            return False
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                x = event.pos().x()
                val = QtWidgets.QStyle.sliderValueFromPosition(obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        elif event.type() == QtCore.QEvent.Type.MouseMove:
            if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                x = event.pos().x()
                val = QtWidgets.QStyle.sliderValueFromPosition(obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        return False


class MouseScrubber:
    """Event filter for mouse scrubbing with Alt+drag or '.' key held."""

    def __init__(self, widget, slider):
        """Initialize MouseScrubber.

        Args:
            widget: Widget to install the event filter on
            slider: QSlider to control
        """
        self.slider = slider
        self.keyState = {}
        self.movePos = None
        self.factor = 3.0
        self.enabled = True
        self._eventFilter = EventFilterDelegate(self._handleEvent)
        widget.installEventFilter(self._eventFilter)

    def _handleEvent(self, obj, event):
        """Handle events for mouse scrubbing.

        Args:
            obj: Object receiving the event
            event: QEvent

        Returns:
            False (never consumes events, just observes)
        """
        if not self.enabled:
            return False
        if event.type() == QtCore.QEvent.Type.HoverMove:
            if self.movePos is None:
                self.movePos = event.pos()
            if self.keyState.get(".") or event.modifiers() == QtCore.Qt.KeyboardModifier.AltModifier:
                delta = event.pos() - self.movePos
                delta = delta.x()
                self.slider.setValue(self.slider.value() + int(delta * self.slider.singleStep() * self.factor))
            self.movePos = event.pos()
            return False
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if not event.isAutoRepeat():
                self.keyState[event.text()] = True
        elif event.type() == QtCore.QEvent.Type.KeyRelease:
            if not event.isAutoRepeat():
                self.keyState[event.text()] = False
        return False
