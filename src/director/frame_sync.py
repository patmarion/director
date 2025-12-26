import itertools
import weakref

from director import transformUtils
from director import vtkAll as vtk


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
            current_delta = transformUtils.copyFrame(frame_data.baseTransform.GetLinearInverse())
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
            self.frames[modified_frame_id].baseTransform = self._compute_base_transform(frame)
            return

        self._block_callbacks = True
        for frame_id, frame_data in list(self.frames.items()):
            if frame_data.ref() is None:
                del self.frames[frame_id]
                continue
            if frame_id != modified_frame_id:
                self._move_frame(frame_id, modified_frame_id)
        self._block_callbacks = False
