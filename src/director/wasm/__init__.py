"""Reusable VTK-to-WASM scene framework for browser-based Director viewers.

These building blocks are intentionally free of any application specifics so
they can back any 3D viewer: build a VTK scene in Python, serialize it once
with ``vtkObjectManager`` for the ``@kitware/vtk-wasm`` RemoteSession protocol,
and stream lightweight per-object pose frames that the client applies with
direct WASM ``set`` calls (no per-frame re-serialization).

The matching frontend library (plain ES modules, no build step) lives in
``director/wasm/viewer_assets`` and is served by :func:`create_wasm_app`.
See ``director.examples.wasm_cone`` for a minimal end-to-end demo.

Public API:
  - :class:`WasmScene`        - build + serialize a scene once; serve states/blobs.
  - :class:`SceneObject` / :class:`SceneNode` - object/folder metadata for the client tree.
  - :class:`PoseSource`       - abstract source of per-frame poses (seq + wait_for_update).
  - :func:`flat16_from_vtk_matrix` - flatten a vtkMatrix4x4 into the pose wire format.
  - :func:`ensure_wasm_files` - download/cache the matching VTK WASM runtime.
  - :func:`create_wasm_app`   - FastAPI app serving the scene protocol + static frontend.
  - :func:`mount_viewer_assets` - mount the viewer library + WASM runtime onto an
    existing FastAPI app; returns the ``wasm_url`` for the app's info endpoint.
  - :func:`run_wasm_app`      - run the app with uvicorn.
  - :class:`NoCacheStaticFiles` - StaticFiles that always revalidates, for apps
    serving their own mutable viewer pages.
"""

from director.wasm.pose_source import PoseSource
from director.wasm.scene_object import SceneNode, SceneObject
from director.wasm.server import (
    VIEWER_ASSETS_DIR,
    NoCacheStaticFiles,
    create_wasm_app,
    mount_viewer_assets,
    run_wasm_app,
)
from director.wasm.wasm_assets import VTK_VERSION, WASM_CACHE_DIR, ensure_wasm_files
from director.wasm.wasm_scene import WasmScene, flat16_from_vtk_matrix

__all__ = [
    "VIEWER_ASSETS_DIR",
    "VTK_VERSION",
    "WASM_CACHE_DIR",
    "NoCacheStaticFiles",
    "PoseSource",
    "SceneNode",
    "SceneObject",
    "WasmScene",
    "create_wasm_app",
    "ensure_wasm_files",
    "flat16_from_vtk_matrix",
    "mount_viewer_assets",
    "run_wasm_app",
]
