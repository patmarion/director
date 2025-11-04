"""Pytest configuration and shared fixtures for Director tests."""

import sys
import pytest
from qtpy.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create a single QApplication instance for all tests.
    
    This fixture is session-scoped, meaning it will be created once
    for the entire test session and reused across all test files.
    """
    app = QApplication.instance()
    do_quit = False
    if app is None:
        do_quit = True
        app = QApplication(sys.argv)
    
    yield app
    
    # Cleanup: quit the application at the end of the test session
    # Note: We don't call quit() if we reused an existing instance,
    # as that might interfere with other code
    # if do_quit:
    #     print("Quitting application")
    #     app.quit()

