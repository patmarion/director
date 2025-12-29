# Director

A robotics interface and visualization framework built with Python, VTK, and Qt.

## Overview

Director is a Python-centric environment for developing interactive 3D applications,
with a focus on robotics visualization and control. Key features include:

- **VTK** for 3D visualization and high-performance rendering
- **QtPy** for Qt abstraction layer (supporting PySide6/PySide2/PyQt6/PyQt5)
- **Numpy** for numerical computing and array math

## Installation

### Installation with pip

You can install Director from GitHub with pip:

```bash
pip install "director[extras,pyside] @ git+https://github.com/patmarion/director.git"
```

The optional dependencies are specified inside the square brackets. You must choose a Qt bindings
library: `pyside` or `pyqt`. The `extras` group installs additional common dependencies to provide
a fully featured application experience.

Next, launch the main application with:

```bash
python -m director.main
```

You can browse and launch more examples with:

```bash
python -m director.examples
```

### System Dependencies (Linux)

While most application functionality is provided by Qt and managed by installing the
Python bindings PySide or PyQt, there may be certain system libraries required to provide
additional capabilities, particularly related to X11 on Linux. To ensure you aren't
missing certain requirements, start with an apt install:

```bash
sudo apt-get install libxcb-cursor0
```

### Development with uv

If you want to run Director locally from source code, you can manage the project dependencies
with the `uv` tool. If you need to install uv, you can install it from the official source
with their install script:

```bash
# See https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With `uv` installed, use `uv sync` to install dependencies:

```bash
uv sync --extra dev
```

The `dev` extra will install a full set of dependencies for a fully featured Director application.
Next, launch the main application with:

```bash
uv run python -m director.main
```

Browse and run examples with:

```bash
uv run python -m director.examples
```

Using `uv sync` will create a virtual environment as an initial step. You can also
directly create the virtual environment:

```bash
# Create a virtual environment (in `.venv` by default)
uv venv  # optionally, request a specific python version: --python 3.10.19

# Install dependencies
uv sync --extra dev

# Activate the environment
source .venv/bin/activate

# Run main application
python -m director.main
```

Running `uv sync` without additional arguments will install a core set of dependencies, which is
intentionally defined as a minimal set so that downstream users can choose which Qt bindings library
they want to use in their project. That means the minimal set does not specify PySide or PyQt, and
Director will fail to launch without at least one installed. Some examples:

```bash
uv sync --extra pyside  # install minimal deps + pyside
uv sync --extra pyqt    # install minimal deps + pyqt
uv sync --extra dev     # installs pyside, plus opencv, mujoco, qtconsole, pyqtgraph, and docs & test deps
```

## Running Tests

To run the test suite:

```bash
uv run pytest

# or, source the virtual environment to run directly
source .venv/bin/activate
pytest
```

Or run with verbose output:

```bash
uv run pytest -v
```

## Documentation

To build the documentation (including API docs):

```bash
uv run ./manage_docs.py build
```

To view the generated documentation in your browser:

```bash
uv run ./manage_docs.py view
```

To clean build artifacts:

```bash
uv run ./manage_docs.py clean
```

## Project Structure

```
director/
├── pyproject.toml          # Project configuration and dependencies
├── README.md               # This file
├── src/
│   └── director/
│       ├── <source files>
│       └── examples/
│           └── <example files>
├── tests/
│   └── <test files>
└── docs/
    └── <documentation files>
```

## Version History

### Director 2.0 (Current)

The current version of Director is a pure Python implementation using QtPy as the Qt bindings
abstraction layer. Dependencies are managed with standard Python tools like uv and pip.

### Director 1.0

The original Director was a C++ library with a CMake build system. It used the PythonQt C++
library (not to be confused with PyQt) for Qt bindings. While functional, maintaining the C++
build system and upgrading dependencies became burdensome. Director 2.0 is a rewrite
in pure Python, requiring only minor API adjustments from the original PythonQt bindings.
