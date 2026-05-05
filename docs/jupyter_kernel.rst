Jupyter Kernel
==============

Director can host an externally connectable Jupyter kernel inside the live Qt
application process. Code executed through that kernel runs in the same process
as the 3D view, object model, and application state, so it can inspect and
modify the running Director session.

Starting Director With a Kernel
-------------------------------

Start Director with the Jupyter kernel enabled:

.. code-block:: bash

    python -m director.main --jupyter-kernel

Director prints the generated connection file path on startup. You can also
choose the connection file path explicitly:

.. code-block:: bash

    python -m director.main --jupyter-kernel --jupyter-connection-file /tmp/director-kernel.json

The kernel namespace includes the same application symbols pushed to the Python
console, including ``fields``, ``view``, ``om``, ``vis``, ``quit``, and
``exit``.

Connecting a Console Client
---------------------------

External Jupyter clients can attach to the connection file:

.. code-block:: bash

    jupyter console --existing /tmp/director-kernel.json
    jupyter qtconsole --existing /tmp/director-kernel.json

For browser frontends such as Notebook 7 or JupyterLab, start the server with
external kernel discovery enabled for the directory containing the connection
file:

.. code-block:: bash

    jupyter lab --ServerApp.allow_external_kernels=True --ServerApp.external_connection_dir=/tmp
    jupyter notebook --ServerApp.allow_external_kernels=True --ServerApp.external_connection_dir=/tmp

In Cursor or VS Code with the Jupyter extension, use the kernel picker to
connect to an existing kernel and select the Director connection file.

Installing a Kernel Spec
------------------------

You can install a Jupyter kernel spec that launches Director directly when a
client selects the kernel. For example, this file registers a ``Custom Director
Kernel``:

.. code-block:: bash

    cat ~/.local/share/jupyter/kernels/director/kernel.json

.. code-block:: json

    {
      "argv": [
        "python",
        "-m",
        "director.main",
        "--jupyter-kernel",
        "--jupyter-connection-file",
        "{connection_file}"
      ],
      "display_name": "Custom Director Kernel",
      "language": "python",
      "env": {
        "MY_ENV_VAR": "value"
      }
    }

Using the Kernel From AI Coding Agents
--------------------------------------

AI coding agents can use the hosted kernel as a live automation channel into
Director. The ``director.agent_client`` module provides a small command line
client that executes code in the running kernel and returns structured JSON:

.. code-block:: bash

    python -m director.agent_client run --code "print(fields.view.camera().GetPosition())"

When ``--connection-file`` is omitted, the client checks
``DIRECTOR_KERNEL_CONNECTION_FILE`` first and then scans
``~/.local/share/jupyter/runtime/kernel-*.json`` from newest to oldest for a
connection file tagged with ``"kernel_name": "director"``.

The screenshot helper is implemented by running ordinary Director code in the
kernel:

.. code-block:: bash

    python -m director.agent_client screenshot --output /tmp/director-view.png

Equivalent Python code can be run directly from any connected Jupyter client:

.. code-block:: python

    from director.screen_recorder import capture_screenshot
    from director import ioUtils
    from director import vtkNumpy as vnp
    from director.script_context import fields

    image = capture_screenshot(fields.view)
    ioUtils.writeImage(vnp.numpyToImageData(image), "/tmp/director-view.png")
