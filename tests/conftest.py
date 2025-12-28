"""Pytest configuration and shared fixtures for Director tests."""

import faulthandler
import gc

import pytest
from qtpy.QtWidgets import QApplication


def install_fault_handler(timeout=20.0):
    """Install a fault handler that dumps tracebacks to the console."""
    faulthandler.dump_traceback_later(timeout=timeout, repeat=True)


@pytest.fixture(scope="session")
def qapp():
    """Create a single QApplication instance for all tests.

    This fixture is session-scoped, meaning it will be created once
    for the entire test session and reused across all test files.
    """
    app = QApplication.instance()
    assert not app, "QApplication instance already exists"
    app = QApplication([])
    yield app

    # Close remaining windows
    for window in app.topLevelWidgets():
        try:
            window.close()
        except Exception:
            pass

    # Run garbage collection and quit the application
    gc.collect()
    app.quit()
    del app
    gc.collect()
