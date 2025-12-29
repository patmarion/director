Overview
========

Introduction
------------

Director is a robotics interface and visualization framework built with Python, VTK, and Qt.
It provides a Python-centric environment for developing interactive 3D applications, with
a focus on robotics visualization and control.

Key Features
------------

*   **Interactive 3D Visualization**: Built on VTK for high-performance rendering.
*   **Python Scripting**: Full access to the object model and visualization pipeline via Python.
*   **Qt Integration**: Seamlessly embeds 3D views in Qt applications.
*   **Extensible Object Model**: Property-based system for managing scene objects.

Core Dependencies
-----------------

*   **VTK** (Visualization Toolkit): The backend for all 3D rendering and data processing.
*   **Qt** (via QtPy): The GUI framework. Supports PySide6, PySide2, PyQt6, and PyQt5.
*   **Python/Numpy**: The core language and numerical processing library.

Installation
------------

The quickest way to install is with pip from the GitHub main branch:

.. code-block:: bash

    pip install "director[extras,pyside] @ git+https://github.com/patmarion/director.git"

Then run the basic builtin application with:

.. code-block:: bash

    python -m director.main

Note that the above command installs Director with additional dependencies requested.
If you install vanilla Director you will get the full library but with a minimal set of
dependencies. You must also install at least one Qt bindings library: PySide or PyQt.
To get all additional dependencies plus a bindings library you can install ``[extras,pyside]``
or ``[extras,pyqt]``. The extras option will install opencv, mujoco, qtconsole, and
pyqtgraph, for example.


Development with uv
~~~~~~~~~~~~~~~~~~~

You can git clone the Director repo and then use ``uv`` to work locally.

.. code-block:: bash

    git clone https://github.com/patmarion/director.git
    cd director
    uv sync --extra dev
    uv run python -m director.main


Examples
--------

Minimal App
~~~~~~~~~~~

A minimal example of running an application with a 3D view:

.. literalinclude:: ../src/director/examples/main_window.py
   :language: python

Visualizing PolyData
~~~~~~~~~~~~~~~~~~~~

Loading and displaying a VTK file:

.. code-block:: python

    from director import ioUtils
    from director import visualization as vis

    polyData = ioUtils.readPolyData("my_mesh.vtp")
    vis.showPolyData(polyData, "mesh")

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :hidden:

   self
   examples
   tutorial
   generated/api
