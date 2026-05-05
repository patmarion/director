"""Externally connectable Jupyter kernel hosted inside Director."""

import json
import os
import queue
import sys
import threading
from pathlib import Path

from qtpy import QtCore
from qtpy.QtWidgets import QApplication

try:
    from ipykernel.kernelapp import IPKernelApp

    JUPYTER_KERNEL_AVAILABLE = True
except ImportError:
    JUPYTER_KERNEL_AVAILABLE = False


class DirectorJupyterKernel:
    """Externally connectable Jupyter kernel hosted inside the Director process."""

    def __init__(self, namespace=None, connection_file=None):
        if not JUPYTER_KERNEL_AVAILABLE:
            raise RuntimeError("Jupyter kernel not available. Please install ipykernel.")

        # Suppress warning about frozen modules interferring with breakpoints.
        os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

        self._argv = ["--log-level=CRITICAL"]
        if connection_file:
            self._argv.extend(["-f", connection_file])
        self._initial_namespace = dict(namespace or {})
        self._ready_event = threading.Event()
        self._started_event = threading.Event()
        self._startup_error = None
        self._main_thread_executor = MainThreadExecutor()
        self.kernel_app = None
        self._kernel = None
        self._thread = threading.Thread(
            target=self._run_kernel,
            name="DirectorJupyterKernel",
            daemon=True,
        )
        self._thread.start()
        self._wait_until_ready()
        self.connect_quit_handler()

    @property
    def connection_file(self):
        """Absolute path to the connection file for external Jupyter clients."""
        return self.kernel_app.abs_connection_file

    def _run_kernel(self):
        try:
            self.kernel_app = IPKernelApp.instance()
            self.kernel_app.init_signal = _skip_signal_initialization
            self.kernel_app.initialize(self._argv)
            self._kernel = self.kernel_app.kernel
            self._install_main_thread_execution()
            self._add_connection_file_metadata()

            if self._initial_namespace:
                self.kernel_app.shell.push(self._initial_namespace)

            print(
                f"Director Jupyter kernel connection file: {self.kernel_app.abs_connection_file}",
                file=sys.__stdout__,
            )
            self._ready_event.set()
            self._started_event.set()
            self.kernel_app.start()
        except Exception as error:
            self._startup_error = error
            self._ready_event.set()
        finally:
            if self.kernel_app:
                self.kernel_app.cleanup_connection_file()

    def _wait_until_ready(self):
        self._ready_event.wait()
        if self._startup_error:
            raise RuntimeError("Failed to start Director Jupyter kernel.") from self._startup_error

    def _add_connection_file_metadata(self):
        """Tag the connection file so browser frontends can present a readable kernel name."""
        connection_path = Path(self.connection_file)
        connection_info = json.loads(connection_path.read_text())
        connection_info["kernel_name"] = "director"
        connection_path.write_text(json.dumps(connection_info, indent=2) + "\n")

    def _install_main_thread_execution(self):
        shell = self.kernel_app.shell
        if not hasattr(shell, "run_cell"):
            return

        original_run_cell = shell.run_cell

        def run_cell_on_main_thread(*args, **kwargs):
            parent_header = getattr(shell, "parent_header", None)

            def run_cell_with_parent():
                if parent_header:
                    shell.set_parent(parent_header)
                return original_run_cell(*args, **kwargs)

            return self._main_thread_executor.call(run_cell_with_parent)

        shell.run_cell = run_cell_on_main_thread

    def push_variables(self, variables):
        """Add variables to the Jupyter kernel namespace."""
        self._wait_until_ready()
        self.kernel_app.shell.push(variables)

    def start(self):
        """The kernel starts in a background thread during initialization."""
        self._wait_until_ready()
        self._started_event.wait()

    def shutdown(self):
        """Stop the kernel event loop and clean up the connection file."""
        self._wait_until_ready()
        io_loop = getattr(self.kernel_app, "io_loop", None)
        if io_loop is not None:
            io_loop.add_callback(io_loop.stop)
        self._thread.join(timeout=5.0)

    def connect_quit_handler(self):
        """Connect to QApplication's aboutToQuit signal to automatically shutdown on quit."""
        QApplication.instance().aboutToQuit.connect(self.shutdown)


def _skip_signal_initialization():
    """ipykernel signal handlers can only be installed from the main thread."""


class MainThreadExecutor(QtCore.QObject):
    """Run Python callables on the Qt main thread and return results to callers."""

    def __init__(self):
        super().__init__()
        self._main_thread = threading.current_thread()
        self._requests = queue.Queue()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1)
        self._timer.timeout.connect(self._process_requests)
        self._timer.start()

    def call(self, function, *args, **kwargs):
        if threading.current_thread() is self._main_thread:
            return function(*args, **kwargs)

        request = _MainThreadRequest(function=function, args=args, kwargs=kwargs)
        self._requests.put(request)
        request.done.wait()

        if request.error:
            raise request.error
        return request.result

    def _process_requests(self):
        while True:
            try:
                request = self._requests.get_nowait()
            except queue.Empty:
                return

            try:
                request.result = request.function(*request.args, **request.kwargs)
            except BaseException as error:
                request.error = error
            finally:
                request.done.set()


class _MainThreadRequest:
    def __init__(self, function, args, kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.done = threading.Event()
        self.result = None
        self.error = None
