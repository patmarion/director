import numpy as np

from director.valueslider import ValueSlider
from director import callbacks
from director.propertyset import PropertySet
from director.timercallback import TimerCallback
import qtpy.QtGui as QtGui
import qtpy.QtWidgets as QtWidgets



class TimestampSlider:
    """Wrapper around ValueSlider for timestamp playback with absolute timestamp callbacks."""
    
    def __init__(self, min_timestamp: float = 0.0, max_timestamp: float = 1.0, step_frequency: int = 100):
        """
        Initialize timestamp slider.
        
        Args:
            min_timestamp: Minimum absolute timestamp in seconds
            max_timestamp: Maximum absolute timestamp in seconds
            step_frequency: Determines how many ticks per second will be emitted by the slider.
        """
        self.min_timestamp = min_timestamp
        self.max_timestamp = max_timestamp
        duration_s = max_timestamp - min_timestamp
        
        # Create callback registry for on_time_changed
        self.callbacks = callbacks.CallbackRegistry(['on_time_changed'])
        
        # Create ValueSlider from 0 to duration
        self.slider = ValueSlider(minValue=0.0, maxValue=duration_s, resolution=duration_s * step_frequency)

        # Connect slider value changed to convert to absolute timestamp
        def on_time_value_changed(relative_timestamp_s):
            """Convert relative timestamp to absolute and call callbacks."""
            absolute_timestamp_s = relative_timestamp_s + self.min_timestamp
            self.callbacks.process('on_time_changed', absolute_timestamp_s)
        
        self.slider.connectValueChanged(on_time_value_changed)
        
        # PropertySet for keyboard shortcut increment sizes
        self.properties = PropertySet()
        self.properties.addProperty('Arrow Key Increment (s)', 1.0)
        self.properties.addProperty('Shift+Arrow Increment (s)', 0.1)
        self.properties.addProperty('Ctrl+Arrow Increment (s)', 0.01)
        self.properties.addProperty('Ctrl+Shift+Arrow Increment (s)', 10.0)

        self.timer = TimerCallback(callback=self._on_timer_tick)
        self._skip_increment = None
        
        # Store shortcuts for cleanup if needed
        self._shortcuts = []
    
    def set_time_range(self, min_timestamp: float, max_timestamp: float, step_frequency: int = 100):
        """
        Set the time range of the slider.
        
        Args:
            min_timestamp: Minimum absolute timestamp in seconds
            max_timestamp: Maximum absolute timestamp in seconds
            step_frequency: Determines how many ticks per second will be emitted by the slider.
        """
        self.min_timestamp = min_timestamp
        self.max_timestamp = max_timestamp
        duration_s = max_timestamp - min_timestamp
        self.slider.setValueRange(0.0, duration_s)
        self.slider.setResolution(duration_s * step_frequency)

    def _on_timer_tick(self):
        if self._skip_increment:
            current_time = self.get_time()
            new_time = max(self.min_timestamp, min(self.max_timestamp, current_time + self._skip_increment))
            self.set_time(new_time)
            self._skip_increment = None

    def add_to_toolbar(self, app, toolbar_name: str):
        """
        Add the slider to a toolbar.
        
        Args:
            toolbar_name: Name of the toolbar
        """
        toolBar = app.addToolBar(toolbar_name)
        toolBar.addWidget(self.slider.widget)
    
    def connect_on_time_changed(self, callback):
        """
        Connect a callback to be called when the timestamp changes.
        
        Args:
            callback: Function that takes absolute_timestamp_s as argument
            
        Returns:
            Callback ID for disconnection
        """
        return self.callbacks.connect('on_time_changed', callback)
    
    def disconnect_on_time_changed(self, callback_id):
        """
        Disconnect a callback.
        
        Args:
            callback_id: Callback ID returned from connect_on_time_changed
        """
        self.callbacks.disconnect(callback_id)
    
    def get_time(self) -> float:
        """
        Get the current absolute timestamp (in seconds) selected by the slider.
        
        Returns:
            Absolute timestamp in seconds.
        """
        relative_timestamp_s = self.slider.getValue()
        absolute_timestamp_s = relative_timestamp_s + self.min_timestamp
        return absolute_timestamp_s

    def set_time(self, absolute_timestamp_s: float):
        """
        Set the slider to a specific absolute timestamp.
        
        Args:
            absolute_timestamp_s: Absolute timestamp in seconds
        """
        relative_timestamp_s = absolute_timestamp_s - self.min_timestamp
        self.slider.setValue(relative_timestamp_s)

    def set_time_from_start(self, relative_timestamp_s: float):
        """
        Set the slider position using a relative timestamp (seconds since start).
        
        Args:
            relative_timestamp_s: Timestamp in seconds from the start (relative to min_timestamp)
        """
        self.slider.setValue(relative_timestamp_s)

    def get_time_from_start(self) -> float:
        """
        Get the current slider value as a relative timestamp (seconds since start).
        
        Returns:
            Relative timestamp in seconds from the start (min_timestamp)
        """
        return self.slider.getValue()
    
    def _toggle_play_pause(self):
        """Toggle play/pause state."""
        if self.slider.animationTimer.isActive():
            self.slider.pause()
        else:
            self.slider.play()
    
    def _skip_forward(self, increment_s: float):
        """Skip time forward by the specified increment."""
        current_time = self.get_time()
        new_time = min(self.max_timestamp, current_time + increment_s)
        self.set_time(new_time)
    
    def _skip_backward(self, increment_s: float):
        """Skip time backward by the specified increment."""
        current_time = self.get_time()
        new_time = max(self.min_timestamp, current_time - increment_s)
        self.set_time(new_time)
    
    def add_keyboard_shortcuts(self, main_window: QtWidgets.QMainWindow):
        """
        Add keyboard shortcuts to the main window.
        
        Args:
            main_window: QMainWindow instance to add shortcuts to
        """
        # Space bar: toggle play/pause
        space_shortcut = QtGui.QShortcut(QtGui.QKeySequence('Space'), main_window)
        space_shortcut.activated.connect(self._toggle_play_pause)

        def on_skip(increment_s: float):
            # schedule the skip with a single shot timer to prevent keyboard events
            # from stacking up in the qt event buffer
            self._skip_increment = increment_s
            self.timer.start()
        
        # Use arrow keys to skip forward and backward.
        # This dict maps keyboard modifiers to increment property names.
        skip_shortcuts = {
            '': 'Arrow Key Increment (s)',
            'Shift+': 'Shift+Arrow Increment (s)',
            'Ctrl+': 'Ctrl+Arrow Increment (s)',
            'Ctrl+Shift+': 'Ctrl+Shift+Arrow Increment (s)',
        }
        
        # Add keyboard shortcuts for the left and right arrow keys with control and shift modifiers.
        # The left arrow key multiplies increment by -1 to skip backward.
        for modifier, property_name in skip_shortcuts.items():
            for direction, sign in [('Left', -1), ('Right', 1)]:
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(f'{modifier}{direction}'), main_window)
                increment = sign * self.properties.getProperty(property_name)
                shortcut.activated.connect(lambda inc=increment: on_skip(inc))
