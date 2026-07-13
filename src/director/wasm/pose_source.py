"""Abstract source of per-frame object poses for a streamed vtk-wasm scene.

A :class:`PoseSource` decouples *where poses come from* (robot kinematics, a
sim, a synthetic animation, ...) from *how they're delivered* (the WebSocket
handler).  The ``seq`` / :meth:`wait_for_update` machinery lets the handler
block until new poses are available instead of polling, and :meth:`stop`
unblocks waiters on shutdown.  Pose frames map a scene-object key to a
row-major 4x4 (16 floats), matching ``SceneObject.matrix_id``'s ``Data`` field
on the WASM side.
"""

import abc
import threading


class PoseSource(abc.ABC):
    """Produces pose frames and notifies waiters when new poses arrive."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._seq = 0
        self._stopped = False

    @abc.abstractmethod
    def pose_frame(self) -> dict[str, list[float]]:
        """Return ``{object_key: [16 row-major floats]}`` for the current poses."""

    @property
    def seq(self) -> int:
        return self._seq

    def notify(self) -> None:
        """Bump the sequence and wake any :meth:`wait_for_update` waiters.

        Call this whenever the underlying poses change (e.g. from a 30 Hz
        animation or kinematics callback).  Cheap and safe to call from a
        background thread.
        """
        with self._cond:
            self._seq += 1
            self._cond.notify_all()

    def wait_for_update(self, last_seen_seq: int, timeout_s: float) -> tuple[int, bool]:
        """Block until a new pose update arrives or the timeout expires.

        Returns ``(current_seq, has_update)``.  ``has_update`` is False when the
        timeout expired without new data or the source has been stopped.
        """
        with self._cond:
            if not self._stopped and last_seen_seq >= self._seq:
                self._cond.wait(timeout=timeout_s)
            if self._stopped or last_seen_seq >= self._seq:
                return self._seq, False
            return self._seq, True

    def stop(self) -> None:
        """Unblock all waiters so WebSocket handlers can shut down cleanly."""
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
