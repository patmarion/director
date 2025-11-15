"""Utilities for frame property synchronization and FrameItem helpers."""

from __future__ import annotations

import itertools
import time
import weakref
from contextlib import contextmanager
from typing import Optional

import numpy as np
from qtpy import QtGui

from director import objectmodel as om
from director import transformUtils
from director import vtkAll as vtk


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
            om.PropertyAttributes(decimals=3, singleStep=0.01),
        )
        self._ensure_property(
            self.RPY_PROPERTY,
            rpy_deg,
            om.PropertyAttributes(decimals=2, singleStep=1.0),
        )

        self._frame_callback = self.frame.connectFrameModified(self._on_frame_modified)
        self._properties_callback = self._properties.connectPropertyChanged(
            self._on_property_changed
        )

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
        position = self._as_float_list(
            self._properties.getProperty(self.POSITION_PROPERTY)
        )
        rpy_deg = self._as_float_list(self._properties.getProperty(self.RPY_PROPERTY))
        new_transform = transformUtils.frameFromPositionAndRPY(position, rpy_deg)
        self.frame.copyFrame(new_transform)
        return new_transform

    def _record_transform_change(self, new_transform, description):
        new_copy = transformUtils.copyFrame(new_transform)

        if self._undo_stack and not self._is_suspended():
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


class FrameSync:
    """Keep multiple FrameItems in sync by mirroring transforms."""

    class FrameData:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def __init__(self):
        self.frames = {}
        self._block_callbacks = False
        self._ids = itertools.count()

    def addFrame(self, frame, ignoreIncoming=False):
        if frame is None or self._findFrameId(frame) is not None:
            return

        frame_id = next(self._ids)
        callback_id = frame.connectFrameModified(self._on_frame_modified)
        self.frames[frame_id] = FrameSync.FrameData(
            ref=weakref.ref(frame),
            baseTransform=self._compute_base_transform(frame),
            callbackId=callback_id,
            ignoreIncoming=ignoreIncoming,
        )

    def removeFrame(self, frame):
        frame_id = self._findFrameId(frame)
        if frame_id is None:
            raise KeyError(frame)
        frame.disconnectFrameModified(self.frames[frame_id].callbackId)
        del self.frames[frame_id]

    def _compute_base_transform(self, frame):
        current_delta = None
        for frame_id, frame_data in list(self.frames.items()):
            ref_frame = frame_data.ref()
            if ref_frame is None:
                del self.frames[frame_id]
                continue
            if ref_frame is frame:
                continue
            current_delta = transformUtils.copyFrame(
                frame_data.baseTransform.GetLinearInverse()
            )
            current_delta.Concatenate(transformUtils.copyFrame(ref_frame.transform))
            break

        t = transformUtils.copyFrame(frame.transform)
        t.PostMultiply()
        if current_delta:
            t.Concatenate(current_delta.GetLinearInverse())
        return t

    def _findFrameId(self, frame):
        for frame_id, frame_data in list(self.frames.items()):
            ref_frame = frame_data.ref()
            if ref_frame is None:
                del self.frames[frame_id]
                continue
            if ref_frame is frame:
                return frame_id
        return None

    def _move_frame(self, frame_id, modified_frame_id):
        frame_data = self.frames[frame_id]
        modified_data = self.frames[modified_frame_id]

        transform = vtk.vtkTransform()
        transform.PostMultiply()
        transform.Concatenate(frame_data.baseTransform)
        transform.Concatenate(modified_data.baseTransform.GetLinearInverse())
        transform.Concatenate(modified_data.ref().transform)
        frame_data.ref().copyFrame(transform)

    def _on_frame_modified(self, frame):
        if self._block_callbacks:
            return

        modified_frame_id = self._findFrameId(frame)
        if modified_frame_id is None:
            return

        if self.frames[modified_frame_id].ignoreIncoming:
            self.frames[modified_frame_id].baseTransform = self._compute_base_transform(
                frame
            )
            return

        self._block_callbacks = True
        for frame_id, frame_data in list(self.frames.items()):
            if frame_data.ref() is None:
                del self.frames[frame_id]
                continue
            if frame_id != modified_frame_id:
                self._move_frame(frame_id, modified_frame_id)
        self._block_callbacks = False


