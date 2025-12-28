"""Launcher for browsing and running Director examples."""

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


from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence, QShortcut
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

        subprocess.Popen([sys.executable, str(path)])


def main():
    app = QApplication([])
    launcher = ExampleLauncher()
    launcher.show()
    app.exec_()


if __name__ == "__main__":
    main()
