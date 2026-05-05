"""Tests for Director-hosted Jupyter kernel support."""

import argparse
import json
import threading
import time
from argparse import Namespace

from director import argutils, consoleapp, jupyter_kernel, mainwindowapp, python_console
from director.fieldcontainer import FieldContainer


def test_standard_args_include_jupyter_kernel_options():
    parser = argparse.ArgumentParser()
    argutils.add_standard_args(parser)

    args = parser.parse_args(
        [
            "--jupyter-kernel",
            "--jupyter-connection-file",
            "/tmp/director-kernel.json",
        ]
    )

    assert args.jupyter_kernel is True
    assert args.jupyter_connection_file == "/tmp/director-kernel.json"


def test_director_jupyter_kernel_initializes_connection_file(monkeypatch, qapp, tmp_path):
    connection_file = tmp_path / "director-kernel.json"
    fake_app = _FakeKernelApp()

    class FakeIPKernelApp:
        @staticmethod
        def instance():
            return fake_app

    monkeypatch.setattr(jupyter_kernel, "JUPYTER_KERNEL_AVAILABLE", True)
    monkeypatch.setattr(jupyter_kernel, "IPKernelApp", FakeIPKernelApp)

    kernel = jupyter_kernel.DirectorJupyterKernel(
        namespace={"initial_value": 1},
        connection_file=str(connection_file),
    )

    assert fake_app.initialize_argv == ["--log-level=CRITICAL", "-f", str(connection_file)]
    assert json.loads(connection_file.read_text())["kernel_name"] == "director"
    assert fake_app.shell.pushed_variables == [{"initial_value": 1}]

    kernel.push_variables({"next_value": 2})
    kernel.start()
    kernel._thread.join(timeout=1.0)
    kernel.shutdown()

    assert fake_app.shell.pushed_variables[-1] == {"next_value": 2}
    assert fake_app.started is True
    assert fake_app.io_loop.stop_requested is True
    assert fake_app.cleaned_connection_file is True


def test_mainwindow_pushes_application_fields_to_jupyter_kernel(monkeypatch):
    fake_kernel_instances = []

    class FakeDirectorJupyterKernel:
        def __init__(self, connection_file=None):
            self.connection_file = connection_file
            self.pushed_variables = []
            fake_kernel_instances.append(self)

        def push_variables(self, variables):
            self.pushed_variables.append(dict(variables))

    class FakeApp:
        def quit(self):
            pass

        def exit(self):
            pass

    monkeypatch.setattr(python_console, "QTCONSOLE_AVAILABLE", False)
    monkeypatch.setattr(jupyter_kernel, "DirectorJupyterKernel", FakeDirectorJupyterKernel)
    monkeypatch.setattr(consoleapp.ConsoleApp, "getTestingEnabled", staticmethod(lambda: True))

    factory = mainwindowapp.MainWindowAppFactory()
    fields = FieldContainer(
        globalsDict={"existing_name": "existing-value"},
        command_line_args=Namespace(
            jupyter_kernel=True,
            jupyter_connection_file="/tmp/director-kernel.json",
        ),
    )

    console_fields = factory.initPythonConsole(fields)
    kernel_fields = factory.initJupyterKernel(
        FieldContainer(
            command_line_args=fields.command_line_args,
            register_application_fields=console_fields.register_application_fields,
        )
    )

    assert console_fields.pythonConsoleWidget is None
    assert kernel_fields.jupyter_kernel is fake_kernel_instances[0]
    assert kernel_fields.jupyter_kernel.connection_file == "/tmp/director-kernel.json"

    application_fields = FieldContainer(
        globalsDict={"existing_name": "existing-value"},
        app=FakeApp(),
        view="view-object",
        jupyter_kernel=kernel_fields.jupyter_kernel,
    )
    kernel_fields.register_application_fields(application_fields)

    pushed_variables = kernel_fields.jupyter_kernel.pushed_variables[-1]
    assert pushed_variables["existing_name"] == "existing-value"
    assert pushed_variables["fields"] is application_fields
    assert pushed_variables["view"] == "view-object"
    assert pushed_variables["quit"] == application_fields.app.quit
    assert pushed_variables["exit"] == application_fields.app.exit
    assert "jupyter_kernel" not in pushed_variables
    assert pushed_variables["fields"].jupyter_kernel is kernel_fields.jupyter_kernel


def test_mainwindow_start_keeps_qt_event_loop_in_charge(monkeypatch, qapp):
    class FakeJupyterKernel:
        def start(self):
            raise AssertionError("Jupyter kernel should not replace the Qt app loop")

    monkeypatch.setattr(consoleapp.ConsoleApp, "getTestingEnabled", staticmethod(lambda: True))
    monkeypatch.setattr(consoleapp.ConsoleApp, "start", staticmethod(lambda: "qt-loop-started"))

    app = mainwindowapp.MainWindowApp()
    app.jupyter_kernel = FakeJupyterKernel()

    assert app.start() == "qt-loop-started"


def test_main_thread_executor_runs_worker_requests_on_qt_thread(qapp):
    executor = jupyter_kernel.MainThreadExecutor()
    main_thread = threading.current_thread()
    worker_result = {}
    worker_done = threading.Event()

    def worker():
        try:
            worker_result["thread"] = executor.call(threading.current_thread)
        finally:
            worker_done.set()

    thread = threading.Thread(target=worker)
    thread.start()

    deadline = time.time() + 2.0
    while not worker_done.is_set() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.001)

    thread.join(timeout=1.0)

    assert worker_done.is_set()
    assert worker_result["thread"] is main_thread


class _FakeShell:
    def __init__(self):
        self.pushed_variables = []

    def push(self, variables):
        self.pushed_variables.append(dict(variables))


class _FakeIoLoop:
    def __init__(self):
        self.stop_requested = False

    def add_callback(self, callback):
        callback()

    def stop(self):
        self.stop_requested = True


class _FakeKernelApp:
    def __init__(self):
        self.abs_connection_file = None
        self.cleaned_connection_file = False
        self.initialize_argv = None
        self.io_loop = _FakeIoLoop()
        self.kernel = object()
        self.shell = _FakeShell()
        self.started = False

    def initialize(self, argv):
        self.initialize_argv = argv
        connection_file = argv[argv.index("-f") + 1]
        self.abs_connection_file = connection_file
        with open(connection_file, "w") as file:
            json.dump({"ip": "127.0.0.1"}, file)

    def start(self):
        self.started = True

    def cleanup_connection_file(self):
        self.cleaned_connection_file = True
