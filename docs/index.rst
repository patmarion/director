Overview
========

Introduction
------------

Director is a robotics interface and visualization framework built on top of VTK and Qt. It provides a python-centric environment for developing interactive 3D applications, with a focus on robotics visualization and control.

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

Examples
--------

Console App
~~~~~~~~~~~

A minimal example of running a standalone console application with a 3D view:

.. literalinclude:: ../src/director/examples/simple.py
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

