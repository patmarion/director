"""Tests for consoleapp module."""

import pytest
import sys
from qtpy.QtWidgets import QApplication
from director import consoleapp
from director.timercallback import TimerCallback


def test_consoleapp_get_testing_args_default(qapp):
    """Test getting testing args with defaults."""
    # Reset cached args
    consoleapp.ConsoleApp._testingArgs = None
    
    # Mock sys.argv for testing
    original_argv = sys.argv[:]
    try:
        sys.argv = ['test_program']
        args = consoleapp.ConsoleApp.getTestingArgs()
        
        assert hasattr(args, 'testing')
        assert hasattr(args, 'data_dir')
        assert hasattr(args, 'output_dir')
        assert hasattr(args, 'interactive')
        assert args.testing == False
        assert args.interactive == False
    finally:
        sys.argv = original_argv


def test_consoleapp_get_testing_args_with_flags(qapp):
    """Test getting testing args with flags set."""
    consoleapp.ConsoleApp._testingArgs = None
    
    original_argv = sys.argv[:]
    try:
        sys.argv = ['test_program', '--testing', '--interactive']
        args = consoleapp.ConsoleApp.getTestingArgs()
        
        assert args.testing == True
        assert args.interactive == True
    finally:
        sys.argv = original_argv


def test_consoleapp_get_testing_enabled(qapp):
    """Test getTestingEnabled method."""
    consoleapp.ConsoleApp._testingArgs = None
    
    original_argv = sys.argv[:]
    try:
        sys.argv = ['test_program', '--testing']
        enabled = consoleapp.ConsoleApp.getTestingEnabled()
        assert enabled == True
        
        sys.argv = ['test_program']
        consoleapp.ConsoleApp._testingArgs = None
        enabled = consoleapp.ConsoleApp.getTestingEnabled()
        assert enabled == False
    finally:
        sys.argv = original_argv


def test_consoleapp_get_testing_interactive_enabled(qapp):
    """Test getTestingInteractiveEnabled method."""
    consoleapp.ConsoleApp._testingArgs = None
    
    original_argv = sys.argv[:]
    try:
        sys.argv = ['test_program', '--interactive']
        enabled = consoleapp.ConsoleApp.getTestingInteractiveEnabled()
        assert enabled == True
        
        sys.argv = ['test_program']
        consoleapp.ConsoleApp._testingArgs = None
        enabled = consoleapp.ConsoleApp.getTestingInteractiveEnabled()
        assert enabled == False
    finally:
        sys.argv = original_argv


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


# def test_consoleapp_quit_timer(qapp):
#     """Test quit timer functionality."""
#     consoleapp.ConsoleApp._quitTimer = None
    
#     consoleapp.ConsoleApp.startQuitTimer(0.01)
    
#     timer = consoleapp.ConsoleApp.getQuitTimer()
#     assert timer is not None
#     assert isinstance(timer, TimerCallback)


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

