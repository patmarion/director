"""Tests for consoleapp module."""

from director import consoleapp


def test_consoleapp_register_startup_callback(qapp):
    """Test registering startup callbacks."""
    callback_called = [False]

    def test_callback():
        callback_called[0] = True

    # Clear any existing callbacks
    consoleapp.ConsoleApp._startupCallbacks = {}

    consoleapp.ConsoleApp.registerStartupCallback(test_callback, priority=1)

    # Check callback was registered
    assert 1 in consoleapp.ConsoleApp._startupCallbacks
    assert test_callback in consoleapp.ConsoleApp._startupCallbacks[1]

    # Test priority ordering
    callback2_called = [False]

    def test_callback2():
        callback2_called[0] = True

    consoleapp.ConsoleApp.registerStartupCallback(test_callback2, priority=0)
    assert 0 in consoleapp.ConsoleApp._startupCallbacks
    assert test_callback2 in consoleapp.ConsoleApp._startupCallbacks[0]


def test_consoleapp_process_events(qapp):
    """Test processEvents method."""
    # Should not raise
    consoleapp.ConsoleApp.processEvents()


def test_consoleapp_application_instance(qapp):
    """Test applicationInstance method."""
    instance = consoleapp.ConsoleApp.applicationInstance()
    assert instance is not None
    assert instance == qapp


def test_consoleapp_init(qapp):
    """Test ConsoleApp initialization."""
    app = consoleapp.ConsoleApp()

    assert app.objectModelWidget is None
    # Check that object model was initialized
    from director import objectmodel as om

    assert om.isInitialized()


def test_consoleapp_exit_code(qapp):
    """Test exit code handling."""
    assert consoleapp.ConsoleApp._exitCode == 0

    consoleapp.ConsoleApp._exitCode = 1
    assert consoleapp.ConsoleApp._exitCode == 1

    # Reset for other tests
    consoleapp.ConsoleApp._exitCode = 0
