"""Screen recorder widget for capturing video using FFMpegWriter."""

import os
import sys
import subprocess
import datetime
from pathlib import Path
import qtpy.QtWidgets as QtWidgets
import qtpy.QtCore as QtCore
import qtpy.QtGui as QtGui

from director.ffmpeg_writer import FFMpegWriter
from director.timercallback import TimerCallback
from director import vtkNumpy as vnp
from director import vtkAll as vtk


def capture_screenshot(view):
    """Capture a screenshot from the view and return as numpy array.

    Args:
        view: VTKWidget instance to capture from

    Returns:
        numpy array of shape (height, width, 3) with uint8 RGB data
    """
    # view.forceRender()

    grabber = vtk.vtkWindowToImageFilter()
    grabber.SetInput(view.renderWindow())
    grabber.SetInputBufferTypeToRGB()
    grabber.ReadFrontBufferOff()
    grabber.SetShouldRerender(False)
    grabber.Update()

    vtk_image = grabber.GetOutput()
    numpy_image = vnp.getNumpyImageFromVtk(vtk_image)
    return numpy_image


class ScreenRecorder:
    """Manages screen recording with FFMpegWriter and provides a toolbar widget."""

    def __init__(self, main_window, view):
        """
        Initialize screen recorder.

        Args:
            main_window: QMainWindow instance
            view: VTKWidget instance to record from
            framerate: Frame rate in fps (default: 60.0)
        """
        self.main_window = main_window
        self.view = view
        self.framerate = 30.0

        self.writer = None
        self.is_recording = False
        self.recording_width = None
        self.recording_height = None
        self.locked_by_recorder = False

        # Value slider connection
        self.value_slider = None
        self.original_use_real_time = None
        self.original_timer_fps = None
        self.value_changed_callback_id = None

        # Create record button
        self.record_button = QtWidgets.QPushButton()
        self.record_button.setCheckable(True)
        self.record_button.setIcon(self._get_record_icon())
        self.record_button.toggled.connect(self._on_record_toggled)
        self.record_button.setToolTip("Start/Stop screen recording")

        # Enable context menu on record button
        self.record_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.record_button.customContextMenuRequested.connect(self._show_context_menu)

        # Store filename for dialog
        self.current_filename = None

        self.capture_timer = TimerCallback(targetFps=self.framerate, callback=self._on_capture_timer)

        # Initialize context menu
        self._setup_context_menu()

    def _get_record_icon(self):
        """Get icon for record button (red circle)."""
        # Create a simple red circle icon
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))  # Red
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 0, 0), 1))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _setup_context_menu(self):
        """Set up the right-click context menu for the record button."""
        self.context_menu = QtWidgets.QMenu(self.record_button)

        # Framerate submenu
        framerate_menu = self.context_menu.addMenu("Framerate")
        self.framerate_group = QtGui.QActionGroup(framerate_menu)
        self.framerate_group.setExclusive(True)

        # 30 fps option
        self.fps30_action = QtWidgets.QAction("30 fps", framerate_menu)
        self.fps30_action.setCheckable(True)
        self.fps30_action.setChecked(self.framerate == 30.0)
        self.fps30_action.triggered.connect(lambda: self._set_framerate(30.0))
        self.framerate_group.addAction(self.fps30_action)
        framerate_menu.addAction(self.fps30_action)

        # 60 fps option
        self.fps60_action = QtWidgets.QAction("60 fps", framerate_menu)
        self.fps60_action.setCheckable(True)
        self.fps60_action.setChecked(self.framerate == 60.0)
        self.fps60_action.triggered.connect(lambda: self._set_framerate(60.0))
        self.framerate_group.addAction(self.fps60_action)
        framerate_menu.addAction(self.fps60_action)

        # View size submenu
        view_size_menu = self.context_menu.addMenu("View size")
        view_size_group = QtGui.QActionGroup(view_size_menu)
        view_size_group.setExclusive(True)

        # 1024x768 option
        size1024_action = QtWidgets.QAction("1024 x 768", view_size_menu)
        size1024_action.setCheckable(True)
        size1024_action.triggered.connect(lambda: self._set_view_size(1024, 768))
        view_size_group.addAction(size1024_action)
        view_size_menu.addAction(size1024_action)

        # 1920x1080 option
        size1920_action = QtWidgets.QAction("1920 x 1080", view_size_menu)
        size1920_action.setCheckable(True)
        size1920_action.triggered.connect(lambda: self._set_view_size(1920, 1080))
        view_size_group.addAction(size1920_action)
        view_size_menu.addAction(size1920_action)

        # Unconstrained option
        unconstrained_action = QtWidgets.QAction("Unconstrained", view_size_menu)
        unconstrained_action.setCheckable(True)
        unconstrained_action.setChecked(True)  # Default to unconstrained
        unconstrained_action.triggered.connect(self._set_view_size_unconstrained)
        view_size_group.addAction(unconstrained_action)
        view_size_menu.addAction(unconstrained_action)

        # Capture mode submenu
        capture_mode_menu = self.context_menu.addMenu("Capture Mode")
        self.capture_mode_group = QtGui.QActionGroup(capture_mode_menu)
        self.capture_mode_group.setExclusive(True)

        # On timer option
        self.timer_action = QtWidgets.QAction("On Timer", capture_mode_menu)
        self.timer_action.setCheckable(True)
        self.timer_action.setChecked(True)  # Default to timer
        self.timer_action.triggered.connect(lambda: self._set_capture_mode("timer"))
        self.capture_mode_group.addAction(self.timer_action)
        capture_mode_menu.addAction(self.timer_action)

        # On playback option
        self.playback_action = QtWidgets.QAction("On Playback", capture_mode_menu)
        self.playback_action.setCheckable(True)
        self.playback_action.triggered.connect(lambda: self._set_capture_mode("playback"))
        self.capture_mode_group.addAction(self.playback_action)
        capture_mode_menu.addAction(self.playback_action)

        self.capture_mode = "timer"

    def _set_capture_mode(self, mode: str):
        """Set the capture mode ('timer' or 'playback')."""
        self.capture_mode = mode

        # Update checked state
        if mode == "timer":
            self.timer_action.setChecked(True)
        elif mode == "playback":
            self.playback_action.setChecked(True)

    def _show_context_menu(self, position):
        """Show the context menu at the given position."""
        self.context_menu.exec_(self.record_button.mapToGlobal(position))

    def _set_framerate(self, fps: float):
        """Set the recording framerate.

        Args:
            fps: Frame rate in frames per second
        """
        self.framerate = fps

        # Update checked state
        if fps == 30.0:
            self.fps30_action.setChecked(True)
        elif fps == 60.0:
            self.fps60_action.setChecked(True)

    def _set_view_size(self, width: int, height: int):
        """Set the view to a fixed size.

        Args:
            width: View width in pixels
            height: View height in pixels
        """
        self.view.setFixedSize(width, height)

    def _set_view_size_unconstrained(self):
        """Set the view size to unconstrained (allow resizing)."""
        qtwidget_max_view_size = 16777215
        self.view.setFixedSize(qtwidget_max_view_size, qtwidget_max_view_size)

    def _on_record_toggled(self, checked: bool):
        """Handle record button toggle."""
        if checked:
            self._start_recording()
        else:
            self._stop_recording()

    def _round_to_even(self, value: int) -> int:
        """Round value to nearest even number (required for some video codecs)."""
        return (value // 2) * 2

    def _lock_view_size(self):
        """Lock the view to its current size."""
        width = self.view.width()
        height = self.view.height()

        # Round to even numbers for ffmpeg compatibility
        width = self._round_to_even(width)
        height = self._round_to_even(height)

        self.view.setFixedSize(width, height)
        return width, height

    def _unlock_view_size(self):
        """Unlock the view size to allow resizing."""
        qtwidget_max_view_size = 16777215
        self.view.setFixedSize(qtwidget_max_view_size, qtwidget_max_view_size)

    def _disable_slider_realtime(self):
        """Disable real-time mode on value slider if connected."""
        if self.value_slider is not None:
            self.original_use_real_time = self.value_slider.useRealTime
            self.original_timer_fps = self.value_slider.animationTimer.targetFps
            self.value_slider.useRealTime = False
            self.value_slider.animationTimer.targetFps = self.framerate

    def _restore_slider_realtime(self):
        """Restore real-time mode on value slider if it was changed."""
        if self.value_slider is not None and self.original_use_real_time is not None:
            self.value_slider.useRealTime = self.original_use_real_time
            self.value_slider.animationTimer.targetFps = self.original_timer_fps
            self.original_use_real_time = None
            self.original_timer_fps = None
            self.value_slider.pause()

    def _start_recording(self):
        """Start a new recording."""
        if self.is_recording:
            return

        # Check if view is already locked
        is_view_locked = self.view.minimumSize() == self.view.maximumSize()

        if not is_view_locked:
            # Lock the view size
            width, height = self._lock_view_size()
            self.locked_by_recorder = True
        else:
            # Use current dimensions (ensure even for ffmpeg)
            width = self._round_to_even(self.view.width())
            height = self._round_to_even(self.view.height())
            self.locked_by_recorder = False

        self.recording_width = width
        self.recording_height = height

        # Generate filename with datetime
        videos_dir = Path.home() / "Videos"
        videos_dir.mkdir(exist_ok=True)

        datetime_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = videos_dir / f"{datetime_str}_director_video.mp4"
        self.current_filename = str(filename)

        try:
            # Create FFMpegWriter
            self.writer = FFMpegWriter(
                filename=self.current_filename, width=width, height=height, framerate=self.framerate
            )
        except Exception as e:
            # If creation failed, cleanup
            if self.locked_by_recorder:
                self._unlock_view_size()
            self.locked_by_recorder = False

            # Show error dialog
            error_dialog = QtWidgets.QMessageBox(self.main_window)
            error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
            error_dialog.setWindowTitle("Recording Error")
            error_dialog.setText(f"Failed to start recording:\n{str(e)}")
            error_dialog.exec()

            # Reset button state
            self.record_button.setChecked(False)
            return

        # If we got here, writer started successfully
        self.is_recording = True
        self.record_button.setToolTip(f"Recording to: {self.current_filename}")

        # Disable context menu during recording
        self.record_button.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        # Disable real-time mode on value slider if connected
        self._disable_slider_realtime()

        if self.capture_mode == "timer":
            self.capture_timer.targetFps = self.framerate
            self.capture_timer.start()

    def _stop_recording(self):
        """Stop the current recording."""
        if not self.is_recording or self.writer is None:
            return

        # Stop timer immediately
        self.capture_timer.stop()

        # Close the writer
        try:
            self.writer.close()
        except Exception as e:
            error_dialog = QtWidgets.QMessageBox(self.main_window)
            error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
            error_dialog.setWindowTitle("Recording Error")
            error_dialog.setText(f"Error closing video file:\n{str(e)}")
            error_dialog.exec()

        self.writer = None
        self.is_recording = False

        # Unlock view size if we locked it
        if self.locked_by_recorder:
            self._unlock_view_size()
        self.locked_by_recorder = False

        # Restore real-time mode on value slider if connected
        self._restore_slider_realtime()

        # Reset button tooltip
        self.record_button.setToolTip("Start/Stop screen recording")

        # Re-enable context menu
        self.record_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Show completion dialog with filename (if it exists)
        if self.current_filename:
            self._show_completion_dialog()

        self.current_filename = None
        self.recording_width = None
        self.recording_height = None

    def _show_completion_dialog(self):
        """Show dialog with recording filename.

        Args:
            filename: Path to the saved video file
        """
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle("Recording Complete")
        dialog.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Label
        label = QtWidgets.QLabel("Recording saved to:")
        layout.addWidget(label)

        # Label with selectable filename
        filename_label = QtWidgets.QLabel(self.current_filename)
        filename_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(filename_label)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        # Open folder button
        open_folder_btn = QtWidgets.QPushButton("Open Folder")
        open_folder_btn.clicked.connect(lambda: self._open_folder())
        button_layout.addWidget(open_folder_btn)

        # Copy path button
        copy_btn = QtWidgets.QPushButton("Copy Path")
        copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.current_filename))
        button_layout.addWidget(copy_btn)

        # Rename button
        rename_btn = QtWidgets.QPushButton("Rename")
        rename_btn.clicked.connect(lambda: self._rename_file(dialog, filename_label, self.current_filename))
        button_layout.addWidget(rename_btn)

        button_layout.addStretch()

        # OK button
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _rename_file(self, dialog, label, current_filename: str):
        """Rename the video file to a new location/name.

        Args:
            dialog: The completion dialog
            text_edit: The QLineEdit showing the filename
            current_filename: Current path to the video file
        """
        # Get directory and base filename
        file_path = Path(current_filename)
        directory = str(file_path.parent)
        base_name = file_path.name

        # Open file dialog to choose new name/location
        new_filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self.main_window, "Rename Video File", str(file_path), "MP4 Files (*.mp4);;All Files (*)"
        )

        if not new_filename:
            # User cancelled
            return

        try:
            # Rename/move the file
            import shutil

            shutil.move(current_filename, new_filename)

            # Update the label to show new filename
            label.setText(new_filename)

            # Update stored filename for potential future use
            self.current_filename = new_filename
        except Exception as e:
            # Show error dialog
            error_dialog = QtWidgets.QMessageBox(dialog)
            error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
            error_dialog.setWindowTitle("Rename Error")
            error_dialog.setText(f"Failed to rename file:\n{str(e)}")
            error_dialog.exec()

    def _open_folder(self):
        """Open the Videos folder in the system file manager."""
        videos_dir = Path.home() / "Videos"
        if videos_dir.exists():
            if sys.platform == "darwin":
                subprocess.run(["open", str(videos_dir)])
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(videos_dir)])
            elif sys.platform == "win32":
                os.startfile(str(videos_dir))

    def get_widget(self):
        """Get the record button widget for adding to toolbar."""
        return self.record_button

    def connect_to_value_slider(self, slider):
        """Connect to a ValueSlider to capture frames on value changes.

        Args:
            slider: ValueSlider instance
        """
        self.value_slider = slider
        self.value_changed_callback_id = slider.connectValueChanged(self._on_time_slider)

        # Automatically switch to playback mode and 60fps when connected to slider
        self._set_capture_mode("playback")
        self._set_framerate(60.0)

    def _on_capture_timer(self):
        if self.capture_mode == "timer":
            self.on_capture()

    def _on_time_slider(self, time_s: float):
        if self.capture_mode == "playback":
            self.on_capture()

    def on_capture(self):
        """Callback for value slider changes - captures and writes frame."""
        if not self.is_recording:
            return

        try:
            # Capture screenshot
            frame = capture_screenshot(self.view)
            # Write frame
            self.write_frame(frame)
        except Exception as e:
            # Stop recording on error
            self.record_button.setChecked(False)
            error_dialog = QtWidgets.QMessageBox(self.main_window)
            error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
            error_dialog.setWindowTitle("Recording Error")
            error_dialog.setText(f"Error capturing frame:\n{str(e)}")
            error_dialog.exec()

    def write_frame(self, frame):
        """
        Write a frame to the current recording (if recording).

        Args:
            frame: numpy array of shape (height, width, 3) with uint8 RGB data
        """
        if self.is_recording and self.writer is not None:
            try:
                self.writer.write_frame(frame)
            except Exception as e:
                # Stop recording on error
                self.record_button.setChecked(False)
                error_dialog = QtWidgets.QMessageBox(self.main_window)
                error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
                error_dialog.setWindowTitle("Recording Error")
                error_dialog.setText(f"Error writing frame:\n{str(e)}")
                error_dialog.exec()
