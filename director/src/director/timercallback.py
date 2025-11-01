"""Timer callback utility for periodic execution."""

import time
from qtpy import QtCore


class TimerCallback(object):
    """Timer callback class for periodic execution at a target FPS."""

    def __init__(self, targetFps=30, callback=None):
        '''
        Construct TimerCallback. The targetFps defines frames per second, the
        frequency for the ticks() callback method.
        '''
        self.targetFps = targetFps
        self.timer = QtCore.QTimer()
        self.enableScheduledTimer()

        self.singleShotTimer = QtCore.QTimer()
        self.singleShotTimer.setSingleShot(True)
        self.callback = callback

    def start(self):
        '''
        Start the timer.
        '''
        if not self.timer.isActive():
            self.timer.timeout.connect(self._timerEvent)

        self.startTime = time.time()
        self.lastTickTime = self.startTime

        if self.useScheduledTimer:
            self.timer.start(0)
        else:
            self.timer.start(int(1000.0 / self.targetFps))

    def stop(self):
        '''
        Stop the timer.
        '''
        self.timer.stop()
        try:
            self.timer.timeout.disconnect(self._timerEvent)
        except TypeError:
            pass  # Already disconnected
        self.singleShotTimer.stop()
        try:
            self.singleShotTimer.timeout.disconnect(self._singleShotTimerEvent)
        except TypeError:
            pass  # Already disconnected

    def tick(self):
        '''
        Timer event callback method. Subclasses can override this method.
        '''
        if self.callback:
            return self.callback()

    def isActive(self):
        '''
        Return whether or not the timer is active.
        '''
        return self.timer.isActive()

    def enableScheduledTimer(self):
        """Enable scheduled timer mode."""
        self.useScheduledTimer = True
        self.timer.setSingleShot(True)

    def disableScheduledTimer(self):
        """Disable scheduled timer mode."""
        self.useScheduledTimer = False
        self.timer.setSingleShot(False)

    def singleShot(self, timeoutInSeconds):
        """Schedule a single-shot timer event."""
        if not self.singleShotTimer.isActive():
            self.singleShotTimer.timeout.connect(self._singleShotTimerEvent)
        self.singleShotTimer.start(int(timeoutInSeconds * 1000))

    def _singleShotTimerEvent(self):
        """Handle single-shot timer event."""
        self.tick()
        try:
            self.singleShotTimer.timeout.disconnect(self._singleShotTimerEvent)
        except TypeError:
            pass  # Already disconnected

    def _schedule(self, elapsedTimeInSeconds):
        '''
        This method is given an elapsed time since the start of the last
        call to ticks(). It schedules a timer event to achieve the targetFps.
        '''
        fpsDelayMilliseconds = int(1000.0 / self.targetFps)
        elapsedMilliseconds = int(elapsedTimeInSeconds*1000.0)
        waitMilliseconds = fpsDelayMilliseconds - elapsedMilliseconds
        self.timer.start(waitMilliseconds if waitMilliseconds > 0 else 1)

    def _timerEvent(self):
        '''
        Internal timer callback method. Calls tick() and measures elapsed time.
        '''
        startTime = time.time()
        self.elapsed = startTime - self.lastTickTime

        try:
            result = self.tick()
        except Exception:
            self.stop()
            raise

        if result is not False:
            self.lastTickTime = startTime
            if self.useScheduledTimer:
                self._schedule(time.time() - startTime)
        else:
            self.stop()

