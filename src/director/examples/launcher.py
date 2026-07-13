"""Launcher for browsing and running Director examples."""

import re
import subprocess
import sys
from pathlib import Path

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer

    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


from qtpy.QtCore import QProcess, Qt, QTimer, QUrl
from qtpy.QtGui import QDesktopServices, QKeySequence, QShortcut
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# First http URL a server demo prints on startup (both the demo's own
# "open http://..." message and uvicorn's "Uvicorn running on http://..." match).
_SERVER_URL_PATTERN = re.compile(r"https?://[\w.\-]+:\d+")

# Only the head of the output is scanned for a URL; well-behaved demos print it
# right away and this keeps the scan buffer bounded for chatty servers.
_URL_SCAN_LIMIT_CHARS = 16384

_STOP_KILL_GRACE_MS = 3000


def _is_server_example(path: Path) -> bool:
    """Server demos (wasm_*) keep running after their browser tab closes, unlike
    Qt examples which quit with their window, so they get explicit launcher
    controls (open browser / stop) instead of a fire-and-forget Popen."""
    return path.stem.startswith("wasm_")


def _browsable_url(url: str) -> str:
    """0.0.0.0 binds all interfaces but is not itself a browsable host."""
    return url.replace("//0.0.0.0:", "//127.0.0.1:")


class RunningServerRow(QWidget):
    """One row in the launcher's running-servers panel.

    Watches the demo's merged stdout/stderr for the served URL; once detected
    the browser is opened automatically (so a wasm demo "shows a window" the
    way Qt examples do) and an Open-browser button allows reopening the tab.
    Stop terminates the backend gracefully (uvicorn shuts down on SIGTERM) with
    a kill fallback.
    """

    def __init__(self, name: str, process: QProcess, on_finished):
        super().__init__()
        self.process = process
        self.url: str | None = None
        self.stop_requested = False
        self._scan_buffer = ""
        self._on_finished = on_finished

        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.setInterval(_STOP_KILL_GRACE_MS)
        self._kill_timer.timeout.connect(self._kill_if_still_running)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(name)
        self.status_label = QLabel("starting…")
        self.status_label.setStyleSheet("color: #888;")

        self.open_button = QPushButton("Open browser")
        self.open_button.setVisible(False)
        self.open_button.clicked.connect(self.open_browser)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)

        layout.addWidget(name_label)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.open_button)
        layout.addWidget(self.stop_button)

        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._handle_finished)

    def is_running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def open_browser(self):
        if self.url:
            QDesktopServices.openUrl(QUrl(self.url))

    def stop(self):
        self.stop_requested = True
        self.status_label.setText("stopping…")
        self.stop_button.setEnabled(False)
        self.process.terminate()
        self._kill_timer.start()

    def _kill_if_still_running(self):
        if self.is_running():
            self.process.kill()

    def _read_output(self):
        # Always drain so QProcess's buffer stays bounded; only scan for the
        # URL until it has been found.
        chunk = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if self.url is not None:
            return
        self._scan_buffer = (self._scan_buffer + chunk)[-_URL_SCAN_LIMIT_CHARS:]
        match = _SERVER_URL_PATTERN.search(self._scan_buffer)
        if match:
            self.url = _browsable_url(match.group(0))
            self._scan_buffer = ""
            self.status_label.setText(self.url)
            self.open_button.setVisible(True)
            self.open_browser()

    def _handle_finished(self, exit_code, _exit_status):
        clean = self.stop_requested or exit_code == 0
        self._on_finished(self, clean, exit_code)


class ExampleLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Director Examples")
        self.resize(1000, 700)

        # Find examples directory (same as this file)
        self.examples_dir = Path(__file__).parent
        self.example_files: dict[str, Path] = {}

        # Build UI
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side: list of examples
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.list_widget)

        # Right side: code viewer + run button
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.code_browser = QTextBrowser()
        self.code_browser.setOpenLinks(False)
        right_layout.addWidget(self.code_browser, 1)

        if not HAS_PYGMENTS:
            warning_label = QLabel("Code syntax highlighting disabled, please install pygments")
            warning_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
            right_layout.addWidget(warning_label)

        self.run_button = QPushButton("Run Example")
        self.run_button.clicked.connect(self._on_run_clicked)
        self.run_button.setEnabled(False)
        right_layout.addWidget(self.run_button)

        # Running-servers panel: only server demos (wasm_*) appear here, since
        # Qt examples quit with their own window and need no controls.
        self.servers_panel = QWidget()
        servers_layout = QVBoxLayout(self.servers_panel)
        servers_layout.setContentsMargins(0, 6, 0, 0)
        servers_title = QLabel("Running demo servers")
        servers_title.setStyleSheet("font-weight: bold;")
        servers_layout.addWidget(servers_title)
        self.server_rows_layout = QVBoxLayout()
        servers_layout.addLayout(self.server_rows_layout)
        self.servers_panel.setVisible(False)
        self.server_rows: list[RunningServerRow] = []
        right_layout.addWidget(self.servers_panel)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 750])

        # Populate examples list
        self._load_examples()

        # Initialize pygments formatter if available
        self.formatter = None
        if HAS_PYGMENTS:
            self.formatter = HtmlFormatter(style="monokai", noclasses=True)

        # Keyboard shortcuts
        QShortcut(QKeySequence.StandardKey.Quit, self, self.close)

    def _load_examples(self):
        """Load all Python files from the examples directory."""
        for path in sorted(self.examples_dir.glob("*.py")):
            # Skip launcher itself and __init__
            if path.name in ("launcher.py", "__init__.py", "__main__.py"):
                continue
            name = path.stem.replace("_", " ").title()
            self.example_files[name] = path
            self.list_widget.addItem(name)

    def _on_selection_changed(self, row: int):
        """Display the selected example's source code with syntax highlighting."""
        if row < 0:
            self.code_browser.clear()
            self.run_button.setEnabled(False)
            return

        name = self.list_widget.item(row).text()
        path = self.example_files.get(name)
        if not path or not path.exists():
            self.code_browser.setPlainText("File not found.")
            self.run_button.setEnabled(False)
            return

        code = path.read_text()

        if self.formatter:
            highlighted = highlight(code, PythonLexer(), self.formatter)
            # Wrap in HTML with dark background to match monokai
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        background-color: #272822;
                        margin: 8px;
                        font-family: 'Consolas', 'Monaco', 'Menlo', monospace;
                        font-size: 13px;
                    }}
                    pre {{
                        margin: 0;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }}
                </style>
            </head>
            <body>
                {highlighted}
            </body>
            </html>
            """
            self.code_browser.setHtml(html)
        else:
            self.code_browser.setPlainText(code)
        self.run_button.setEnabled(True)

    def _on_run_clicked(self):
        """Launch the selected example as a subprocess."""
        row = self.list_widget.currentRow()
        if row < 0:
            return

        name = self.list_widget.item(row).text()
        path = self.example_files.get(name)
        if not path or not path.exists():
            return

        if _is_server_example(path):
            self._launch_server_example(name, path)
        else:
            subprocess.Popen([sys.executable, str(path)])

    def _launch_server_example(self, name: str, path: Path):
        """Launch a server demo under QProcess so the launcher can detect its
        URL, open the browser, and offer a Stop control."""
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setProgram(sys.executable)
        process.setArguments([str(path)])

        server_row = RunningServerRow(name, process, on_finished=self._on_server_finished)
        self.server_rows.append(server_row)
        self.server_rows_layout.addWidget(server_row)
        self.servers_panel.setVisible(True)
        process.start()

    def _on_server_finished(self, server_row: RunningServerRow, clean: bool, exit_code: int):
        if clean:
            self._remove_server_row(server_row)
            return
        # Keep failed rows visible (e.g. port already in use) so the exit is
        # not silent; the Stop button becomes a Dismiss.
        server_row.status_label.setText(f"exited (code {exit_code})")
        server_row.open_button.setVisible(False)
        server_row.stop_button.setText("Dismiss")
        server_row.stop_button.setEnabled(True)
        server_row.stop_button.clicked.disconnect()
        server_row.stop_button.clicked.connect(lambda: self._remove_server_row(server_row))

    def _remove_server_row(self, server_row: RunningServerRow):
        if server_row in self.server_rows:
            self.server_rows.remove(server_row)
        self.server_rows_layout.removeWidget(server_row)
        server_row.process.deleteLater()
        server_row.deleteLater()
        self.servers_panel.setVisible(bool(self.server_rows))

    def closeEvent(self, event):
        # Unlike Qt examples, server demos would otherwise be orphaned with
        # their port still bound when the launcher closes.
        for server_row in self.server_rows:
            if server_row.is_running():
                server_row.stop_requested = True
                server_row.process.terminate()
        event.accept()


def main():
    app = QApplication([])
    launcher = ExampleLauncher()
    launcher.show()
    app.exec_()


if __name__ == "__main__":
    main()
