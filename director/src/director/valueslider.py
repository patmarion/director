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

    events = Flags('VALUE_CHANGED')

    def __init__(self, minValue=0.0, maxValue=1.0, resolution=1000):
        """Initialize ValueSlider.
        
        Args:
            minValue: Minimum value
            maxValue: Maximum value
            resolution: Slider resolution (number of steps)
        """
        self._value = 0.0
        self.spinbox = QtWidgets.QDoubleSpinBox()
        self.spinbox.setSuffix('s')
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.playButton = QtWidgets.QPushButton('Play')
        self.setValueRange(minValue, maxValue)
        self.setResolution(resolution)
        self.slider.valueChanged.connect(self._onSliderValueChanged)
        self.spinbox.valueChanged.connect(self._onSpinboxValueChanged)
        self.playButton.clicked.connect(self._onPlayClicked)
        self.widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.playButton)
        layout.addWidget(self.spinbox)
        layout.addWidget(self.slider)

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
            dt = (1.0 / self.animationTimer.targetFps)

        self.animationRate = (1.0 - self.animationRateAlpha)*self.animationRate + self.animationRateAlpha*self.animationRateTarget

        valueChange = dt * self.animationRate
        value = self.getValue() + valueChange
        if value > self.maxValue:
            self.setValue(self.maxValue)
            self.playButton.setText('Play')
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
        self.playButton.setText('Pause')
        self.animationPrevTime = time.time()
        self.animationTimer.start()

    def pause(self):
        """Pause animation playback."""
        self.playButton.setText('Play')
        self.animationTimer.stop()

    def _onPlayClicked(self):
        """Handle play/pause button click."""
        if self.animationTimer.isActive():
            self.pause()
        else:
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
            slider_value = int(self.slider.maximum() * (self._value - self.minValue) / float(self.maxValue - self.minValue))
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
        self._value = (self.minValue + (self.maxValue - self.minValue) * (sliderValue / float(self.slider.maximum())))
        self._syncSpinBox()
        self._notifyValueChanged()


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
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                # Get mouse position
                pos = event.pos()
                x = pos.x()
                val = QtWidgets.QStyle.sliderValueFromPosition(
                    obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        elif event.type() == QtCore.QEvent.Type.MouseMove:
            if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                # Get mouse position
                pos = event.pos()
                x = pos.x()
                val = QtWidgets.QStyle.sliderValueFromPosition(
                    obj.minimum(), obj.maximum(), x, obj.width())
                obj.setValue(val)
                return True
        return False

