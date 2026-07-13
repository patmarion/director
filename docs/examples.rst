Examples
========

(This page is a placeholder for future examples)

*   Running the application
*   Loading data
*   Creating custom visuals

VTK WASM browser demos
----------------------

The ``director.wasm`` module renders VTK scenes in the browser with VTK
compiled to WebAssembly.  The scene is authored in Python, serialized once with
``vtkObjectManager``, imported by the ``@kitware/vtk-wasm`` RemoteSession, and
then driven with lightweight per-object pose frames over a WebSocket -- the
geometry never crosses the wire again.  The backend is FastAPI and the frontend
is a folder of plain ES modules and CSS served statically (no npm, no build
step).

Run a demo and open http://127.0.0.1:8000 in a browser:

.. code-block:: bash

   uv run python -m director.examples.wasm_cone          # animated full-page viewer
   uv run python -m director.examples.wasm_shapes        # static scene, object tree + properties, terrain camera
   uv run python -m director.examples.wasm_picking       # hover highlight + click/right-click object picking
   uv run python -m director.examples.wasm_iframe_embed  # viewer embedded in a host page (iframe)

The iframe demo places the viewer as one element of a normal page (half-width
card with a fixed aspect ratio) and drives it from host-page controls outside
the iframe: resizing the card (the viewer's ResizeObserver follows), reloading
the iframe, and changing the renderer background by posting a message that the
embedded page translates into ``viewer.setBackground(bottom, top)`` -- a direct
WASM ``set()`` on the renderer using the ``renderer_id`` from ``/api/info``.

To build a new viewer: construct a :class:`director.wasm.WasmScene`
(``add_folder`` / ``add_object`` / ``finalize``), optionally implement a
:class:`director.wasm.PoseSource` whose ``pose_frame()`` returns
``{object_key: [16 row-major floats]}``, and serve both with
:func:`director.wasm.create_wasm_app`.  The object tree, properties panel,
IndexedDB geometry caching, and pose streaming come for free from the shared
frontend library in ``director/wasm/viewer_assets``.

The floating panels are hidden by default so embedding pages get a clean 3D
view.  Right-click the viewer to toggle the scene panel (object tree +
properties) and the debug info panel (status, cache stats, pose rate, and a
text console).  ``createViewer`` accepts ``panels: {scene, debug}`` for the
initial visibility and ``contextMenu: false`` to disable the menu entirely.

Right-clicking an object also hardware-picks it (a ``vtkPropPicker`` running
inside the WASM runtime, like Director's ``showRightClickMenu``): the menu
shows the object's name and a Select action that highlights it in the scene
panel.  Host pages get the same pick through ``viewer.pickAtEvent(event)``;
the ``wasm_picking`` demo builds hover highlighting and click-to-select on
top of it, mirroring ``director.examples.draw_shapes``.  The demo's ground
plane stays clickable but is skipped by the hover glow (a host-page choice --
a highlight on the full-view plane is distracting).  To remove an object from
picking entirely, the way Director ignores its grid, use the ``vtkActor``
escape hatch during the build phase (``scene.get_actor(key).PickableOff()``)
or toggle it live from the client with ``SceneSession.setPickable``.

