"""Tests for timercallback module."""

import sys
import time
import pytest
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer
from director.timercallback import TimerCallback


def test_timer_callback_construction(qapp):
    """Test that TimerCallback can be constructed."""
    callback = TimerCallback(targetFps=30)
    assert callback is not None
    assert callback.targetFps == 30


def test_timer_callback_with_function(qapp):
    """Test TimerCallback with a callback function."""
    call_count = [0]

    def callback_func():
        call_count[0] += 1
        return True

    timer = TimerCallback(targetFps=10, callback=callback_func)
    timer.start()

    # Process events for a short time
    qapp.processEvents()
    time.sleep(0.2)  # Wait a bit
    qapp.processEvents()

    # Should have been called at least once
    assert call_count[0] > 0

    timer.stop()


def test_timer_callback_start_stop(qapp):
    """Test starting and stopping timer."""
    timer = TimerCallback(targetFps=30)

    assert not timer.isActive()
    timer.start()
    assert timer.isActive()
    timer.stop()
    assert not timer.isActive()


def test_timer_callback_single_shot(qapp):
    """Test single-shot timer functionality."""
    call_count = [0]

    def callback_func():
        call_count[0] += 1

    timer = TimerCallback(callback=callback_func)
    timer.singleShot(0.1)

    # Process events
    time.sleep(0.2)
    qapp.processEvents()

    # Should have been called once
    assert call_count[0] == 1


def test_timer_callback_tick_returns_false(qapp):
    """Test that returning False stops the timer."""
    call_count = [0]

    def callback_func():
        call_count[0] += 1
        if call_count[0] >= 2:
            return False  # Stop after 2 calls
        return True

    timer = TimerCallback(targetFps=60, callback=callback_func)
    timer.start()

    # Process events multiple times to ensure timer events are processed
    # With scheduled timer mode, we need to give it time to execute
    for _ in range(10):
        time.sleep(0.05)
        qapp.processEvents()
        if not timer.isActive():
            break

    # Should have stopped automatically after returning False
    assert not timer.isActive(), "Timer should have stopped when callback returned False"
    assert call_count[0] >= 2, "Callback should have been called at least twice"
