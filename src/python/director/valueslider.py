from director import callbacks
from director.flags import Flags
from director.timercallback import TimerCallback
from director import qtutils
import PythonQt
from PythonQt import QtCore, QtGui

import time
import numpy as np


class ValueSlider(object):

    events = Flags('VALUE_CHANGED')

    def __init__(self, minValue=0.0, maxValue=1.0, resolution=1000):
        self._value = 0.0
        self.spinbox = QtGui.QDoubleSpinBox()
        self.spinbox.setSuffix('s')
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.playButton = QtGui.QPushButton('Play')
        self.setValueRange(minValue, maxValue)
        self.setResolution(resolution)
        self.slider.connect('valueChanged(int)', self._onSliderValueChanged)
        self.spinbox.connect('valueChanged(double)', self._onSpinboxValueChanged)
        self.playButton.connect('clicked()', self._onPlayClicked)
        self.widget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout(self.widget)
        layout.addWidget(self.playButton)
        layout.addWidget(self.spinbox)
        layout.addWidget(self.slider)

        self.shortcuts = []
        self.mouseScrubber = None
        self.callbacks = callbacks.CallbackRegistry(self.events._fields)
        self.animationPrevTime = 0.0
        self.animationRate = 1.0
        self.animationRateTarget = 1.0
        self.animationRateAlpha = 1.0
        self.animationTimer = TimerCallback(callback=self._tick, targetFps=60)
        self.useRealTime = True
        self.eventFilter = PythonQt.dd.ddPythonEventFilter()
        self.eventFilter.connect('handleEvent(QObject*, QEvent*)', self._filterEvent)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.MouseButtonPress)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.MouseMove)
        self.slider.installEventFilter(self.eventFilter)

    def _tick(self):
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

    def setAnimationRate(self, animationRate, rateAlpha=1.0):
        self.animationRateTarget = animationRate
        self.animationRateAlpha = rateAlpha

    def play(self):
        self.playButton.setText('Pause')
        self.animationPrevTime = time.time()
        self.animationTimer.start()

    def pause(self):
        self.playButton.setText('Play')
        self.animationTimer.stop()

    def stepBackward(self):
        self.slider.setValue(self.slider.value - self.slider.singleStep)

    def stepForward(self):
        self.slider.setValue(self.slider.value + self.slider.singleStep)

    def jumpBackward(self):
        self.slider.setValue(self.slider.value - self.slider.pageStep)

    def jumpForward(self):
        self.slider.setValue(self.slider.value + self.slider.pageStep)

    def togglePlayForward(self):
        isPlayingForward = self.animationTimer.isActive() and self.animationRateTarget > 0
        self.setAnimationRate(np.abs(self.animationRateTarget))
        if isPlayingForward:
            self.pause()
        else:
            self.play()
        
    def togglePlayReverse(self):
        isPlayingReverse = self.animationTimer.isActive() and self.animationRateTarget < 0
        self.setAnimationRate(-1 * np.abs(self.animationRateTarget))
        if isPlayingReverse:
            self.pause()
        else:
            self.play()

    def _onPlayClicked(self):
        if self.animationTimer.isActive():
            self.pause()
        else:
            self.play()

    def _filterEvent(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            val = QtGui.QStyle.sliderValueFromPosition(obj.minimum, obj.maximum, event.x(), obj.width)
            self.eventFilter.setEventHandlerResult(True)
            obj.setValue(val)
        elif event.type() == QtCore.QEvent.MouseMove:
            val = QtGui.QStyle.sliderValueFromPosition(obj.minimum, obj.maximum, event.x(), obj.width)
            self.eventFilter.setEventHandlerResult(True)
            obj.setValue(val)

    def setResolution(self, resolution):
        with qtutils.BlockSignals(self.slider):
            self.slider.maximum = resolution
        self._syncSlider()

    def setValueRange(self, minValue, maxValue, newValue=None, notifyChange=True):
        newValue = self._value if newValue is None else newValue
        newValue = np.clip(newValue, minValue, maxValue)
        changed = newValue != self._value
        self.minValue = minValue
        self.maxValue = maxValue
        self._value = newValue
        with qtutils.BlockSignals(self.spinbox):
            self.spinbox.minimum = minValue
            self.spinbox.maximum = maxValue
        self._syncSpinBox()
        self._syncSlider()
        if changed and notifyChange:
            self._notifyValueChanged()

    def getValue(self):
        return self._value

    def setValue(self, value):
        self._value = np.clip(value, self.minValue, self.maxValue)
        self._syncSlider()
        self._syncSpinBox()
        self._notifyValueChanged()

    def connectValueChanged(self, callback):
        return self.callbacks.connect(self.events.VALUE_CHANGED, callback)

    def _notifyValueChanged(self):
        self.callbacks.process(self.events.VALUE_CHANGED, self._value)

    def _syncSlider(self):
        with qtutils.BlockSignals(self.slider):
            self.slider.value = self.slider.maximum * (self._value - self.minValue) / float(self.maxValue - self.minValue)

    def _syncSpinBox(self):
        with qtutils.BlockSignals(self.spinbox):
            self.spinbox.value = self._value

    def _onSpinboxValueChanged(self, spinboxValue):
        self._value = spinboxValue
        self._syncSlider()
        self._notifyValueChanged()

    def _onSliderValueChanged(self, sliderValue):
        self._value = (self.minValue + (self.maxValue - self.minValue) * (sliderValue / float(self.slider.maximum)))
        self._syncSpinBox()
        self._notifyValueChanged()

    def initMouseScrubber(self, widget):
        self.mouseScrubber = MouseScrubber(widget, self)

    def initKeyboardShortcuts(self, widget):
        commands = {
            '[': self.stepBackward,
            ']': self.stepForward,
            'shift+[': self.jumpBackward,
            'shift+]': self.jumpForward,
            ' ': self.togglePlayForward,
            'shift+ ': self.togglePlayReverse
        }
        self.shortcuts = []
        for keySequence, func in commands.items():
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(keySequence), widget)
            shortcut.connect('activated()', func)
            self.shortcuts.append(shortcut)


class MouseScrubber:

    def __init__(self, widget, slider):
        self.slider = slider
        self.keyState = {}
        self.movePos = None
        self.factor = 3.0
        self.enabled = True
        self.eventFilter = PythonQt.dd.ddPythonEventFilter()
        self.eventFilter.connect('handleEvent(QObject*, QEvent*)', self.filterEvent)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.KeyPress)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.KeyRelease)
        self.eventFilter.addFilteredEventType(QtCore.QEvent.HoverMove)
        widget.installEventFilter(self.eventFilter)

    def filterEvent(self, obj, event):
        if not self.enabled:
            return
        if event.type() == QtCore.QEvent.HoverMove:
            if self.movePos is None:
                self.movePos = event.pos()
            if self.keyState.get('.') or event.modifiers() == QtCore.Qt.AltModifier:
                delta = event.pos() - self.movePos
                delta = delta.x()
                self.slider.setValue(self.slider.value + (delta * self.slider.singleStep * self.factor))
            self.movePos = event.pos()
            return
        if event.isAutoRepeat():
            return
        if event.type() == QtCore.QEvent.KeyPress:
            self.keyState[event.text()] = True
        elif event.type() == QtCore.QEvent.KeyRelease:
            self.keyState[event.text()] = False
