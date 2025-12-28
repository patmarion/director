"""Utilities for frame property synchronization and FrameItem helpers."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional

import numpy as np
from qtpy import QtGui

from director import transformUtils
from director.propertyset import PropertyAttributes


class FramePropertyCommand(QtGui.QUndoCommand):
    """Undo command that stores before/after transforms for a frame."""

    COMMAND_ID = 4201
    MERGE_WINDOW_SEC = 0.25

    def __init__(
        self,
        frame,
        frame_properties: "FrameProperties",
        before_transform,
        after_transform,
        description: str,
    ):
        super().__init__(description)
        self.frame = frame
        self._frame_properties = frame_properties
        self._before = transformUtils.copyFrame(before_transform)
        self._after = transformUtils.copyFrame(after_transform)
        self._timestamp = time.monotonic()

    def id(self):
        return self.COMMAND_ID

    def undo(self):
        with self._frame_properties.suspend_updates():
            self.frame.copyFrame(self._before)

    def redo(self):
        with self._frame_properties.suspend_updates():
            self.frame.copyFrame(self._after)

    def mergeWith(self, other):
        if not isinstance(other, FramePropertyCommand):
            return False
        if other.frame is not self.frame:
            return False
        if self.text() != other.text():
            return False
        if other._timestamp - self._timestamp > self.MERGE_WINDOW_SEC:
            return False
        self._after = transformUtils.copyFrame(other._after)
        self._timestamp = other._timestamp
        self.setText(other.text())
        return True


class FrameProperties:
    """Bidirectional sync between a FrameItem and editable properties."""

    POSITION_PROPERTY = "Position"
    RPY_PROPERTY = "RPY (deg)"

    def __init__(self, frame, undo_stack: Optional[QtGui.QUndoStack] = None):
        self.frame = frame
        self._undo_stack = undo_stack
        self._properties = frame.properties
        self._block_signals = False
        self._suspend_depth = 0
        self._last_frame_transform = transformUtils.copyFrame(frame.transform)

        position, rpy_deg = self._get_frame_values()
        self._ensure_property(
            self.POSITION_PROPERTY,
            position,
            PropertyAttributes(decimals=3, singleStep=0.01),
        )
        self._ensure_property(
            self.RPY_PROPERTY,
            rpy_deg,
            PropertyAttributes(decimals=2, singleStep=1.0),
        )

        self._frame_callback = self.frame.connectFrameModified(self._on_frame_modified)
        self._properties_callback = self._properties.connectPropertyChanged(self._on_property_changed)

    def set_undo_stack(self, undo_stack: QtGui.QUndoStack):
        self._undo_stack = undo_stack

    def _ensure_property(self, name, value, attributes):
        if self._properties.hasProperty(name):
            self._properties.setProperty(name, value)
        else:
            self._properties.addProperty(name, value, attributes=attributes)

    def _get_frame_values(self):
        position = list(self.frame.transform.GetPosition())
        rpy_rad = transformUtils.rollPitchYawFromTransform(self.frame.transform)
        rpy_deg = np.degrees(rpy_rad).tolist()
        return position, rpy_deg

    def _on_frame_modified(self, _frame):
        if self._block_signals or self._is_suspended():
            return
        position, rpy_deg = self._get_frame_values()
        self._block_signals = True
        try:
            self._properties.setProperty(self.POSITION_PROPERTY, position)
            self._properties.setProperty(self.RPY_PROPERTY, rpy_deg)
        finally:
            self._block_signals = False
        self._record_transform_change(self.frame.transform, "Transform frame")

    def _on_property_changed(self, _property_set, property_name):
        if property_name not in (self.POSITION_PROPERTY, self.RPY_PROPERTY):
            return
        if self._block_signals:
            return
        self._block_signals = True
        try:
            new_transform = self._apply_properties_to_frame()
        finally:
            self._block_signals = False
        if new_transform is not None:
            self._record_transform_change(new_transform, f"Update {property_name}")

    def _apply_properties_to_frame(self):
        position = self._as_float_list(self._properties.getProperty(self.POSITION_PROPERTY))
        rpy_deg = self._as_float_list(self._properties.getProperty(self.RPY_PROPERTY))
        new_transform = transformUtils.frameFromPositionAndRPY(position, rpy_deg)
        self.frame.copyFrame(new_transform)
        return new_transform

    def _record_transform_change(self, new_transform, description):
        new_copy = transformUtils.copyFrame(new_transform)

        if self._undo_stack is not None and not self._is_suspended():
            command = FramePropertyCommand(
                self.frame,
                self,
                self._last_frame_transform,
                new_copy,
                description,
            )
            self._undo_stack.push(command)
        self._last_frame_transform = new_copy

    def _is_suspended(self):
        return self._suspend_depth > 0

    @contextmanager
    def suspend_updates(self):
        self._suspend_depth += 1
        try:
            yield
        finally:
            self._suspend_depth -= 1

    @staticmethod
    def _as_float_list(values):
        return [float(v) for v in values]
