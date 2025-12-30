# Director

A robotics interface and visualization framework built with Python, VTK, and Qt.

## Overview

Director is a Python-centric environment for developing interactive 3D applications,
with a focus on robotics data visualization.

Key dependencies:

- **VTK** for 3D visualization and high-performance rendering
- **QtPy** for Qt abstraction layer (supporting PySide6/PySide2/PyQt6/PyQt5)
- **Numpy** for numerical computing and matrix math

## Quick Start

Install Director from GitHub with pip:

```bash
pip install "director[pyside,extras] @ git+https://github.com/patmarion/director.git"
```

The optional dependencies are specified inside the square brackets. You must choose a Qt bindings
library: `pyside` or `pyqt`. The `extras` group installs additional common dependencies to provide
a full featured set of application components.

Launch the main application:

```bash
python -m director.main
```

Browse and launch more examples:

```bash
python -m director.examples
```

> [!NOTE]
> On Linux, if you encounter display or X11-related errors, see [System Dependencies](#system-dependencies-linux) below.

## Development Setup

If you want to run Director locally from source code you can manage the project dependencies
with the `uv` tool. If you need to install uv you can install it from the official source
with their install script:

```bash
# See https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With `uv` installed, use `uv sync` to install dependencies:

```bash
uv sync --extra dev
```

The `dev` extra will install a full set of dependencies to run all available application components.
Launch the main application with:

```bash
uv run python -m director.main
```

Browse and run examples with:

```bash
uv run python -m director.examples
```

Using `uv` will create a virtual environment as an initial step. You can also
explicitly initialize the virtual environment:

```bash
# Create a virtual environment (in `.venv` by default)
uv venv  # optionally, request a specific python version: --python 3.10.19

# Install dependencies
uv sync --extra dev

# Activate the environment
source .venv/bin/activate

# Run main application without `uv run`
python -m director.main
```

Running `uv sync` without additional arguments will install a core set of dependencies which is
intentionally defined as a minimal set so that downstream users can choose which Qt bindings library
they want to use in their project. That means the minimal set does not specify PySide or PyQt and
Director will fail to launch without at least one installed. So typically you must pass one
or more `--extra <name>` args to uv sync. For example:

```bash
uv sync --extra pyside  # install minimal deps + pyside
uv sync --extra pyqt    # install minimal deps + pyqt
uv sync --extra dev     # installs pyside, plus opencv, mujoco, qtconsole, pyqtgraph, and docs & test deps
uv sync --extra pyside --extra qtconsole --extra pyqtgraph  # just a few selected extras
```

## System Dependencies (Linux)

On Linux, certain system libraries may be required for Qt functionality, particularly
related to X11. If you encounter display-related errors, install the following:

```bash
sudo apt-get install libxcb-cursor0
```

## Running Tests

To run the test suite:

```bash
uv run pytest

# or, source the virtual environment to run pytest directly
source .venv/bin/activate
pytest
```

Or run with verbose output:

```bash
uv run pytest -v
```

## CI Testing

[![Build status](https://badge.buildkite.com/cdfb045f914125717c09beafac6fcbb1931f43ef622afb726c.svg?branch=main)](https://buildkite.com/pat-marion/director)

This project uses [Buildkite](https://buildkite.com/pat-marion/director) for continuous integration.
The pipeline configuration is defined in [`buildkite/pipeline.yml`](buildkite/pipeline.yml).

## Documentation

Documentation is generated with Sphinx via [`docs/manage_docs.py`](docs/manage_docs.py).
For convenience, bash wrapper scripts are provided:

Build the documentation:

```bash
docs/build.sh
```

View the documentation in your browser:

```bash
docs/view.sh
```

Clean build artifacts:

```bash
docs/clean.sh
```

## Project Structure

```
director/
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Locked dependency versions
├── README.md               # This file
├── LICENSE.txt             # BSD-3-Clause license
├── src/
│   └── director/
│       ├── <source files>
│       └── examples/
│           └── <example files>
├── tests/
│   └── <test files>
├── docs/
│   └── <documentation files>
└── buildkite/
    └── pipeline.yml        # CI pipeline configuration
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
