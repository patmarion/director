# Director 2.0

A robotics interface and visualization framework with Python, VTK, and Qt.

## Overview

Director 2.0 is a port and refactor of Director using:
- **VTK** for 3D visualization
- **QtPy** for Qt abstraction layer (supporting PySide6/PySide2)
- **PySide6** as the Qt backend

The previous version of Director was a core c++ library with a cmake build system
and used the more niche PythonQt c++ library (not to be confused with PyQt) as the
main Qt binding system.  It was a burden to maintain the build system and upgrade
the c++ dependencies.  This new version is pure python and dependencies are more
simply managed with uv/pip.  The Qt bindings are now provided by QtPy which is
an abstraction supporting either PySide or PyQt.  The port requires minor rewrites
to most modules to update certain API differences from PythonQt.

## Installation

### System Dependencies (Linux)

While most application functionality is provided by Qt and managed by installing the
python bindings PySide or PyQt, there may be certain system libraries required to provide
additional capabilities, in particular related to X11 on Linux.  To ensure you aren't
missing certain requirements please start with an apt install:

```bash
sudo apt-get install libxcb-cursor0
```

### Python Dependencies

The most basic starting point is:

```bash
uv run python -m director.hello_world
```

Or you can install just the package dependencies:
```bash
# Sync dependencies from pyproject.toml
uv sync

# or use a specific python version
uv sync --python 3.10.19
```

Using uv sync will create a virtual environment as an initial step.  You can also
directly create the virtual environment:

```bash
# Create a virtual environment (in `.venv` by default)
uv venv

# Install dependencies
uv sync

# Activate the environment
source .venv/bin/activate

# Run hello world
python -m director.hello_world
```

Besides runtime dependencies you may want to install additional development and test
dependencies:

```bash
uv sync --all-extras
```

The `uv run` command automatically uses the virtual environment and ensures all dependencies
are available.

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

## Project Structure

```
director/
├── pyproject.toml          # Project configuration and dependencies
├── README.md               # This file
├── src/
│   └── director/
│       ├── __init__.py     # Package initialization
│       └── <source files>
├── examples/
│   └── <example files>
├── tests/
    ├── __init__.py
    └── <test files>
```