"""FastAPI app factory for serving a WasmScene to the browser.

This reusable backend serves a Director vtk-wasm viewer. It provides the
``vtkObjectManager`` serialization endpoints used by ``@kitware/vtk-wasm``
(``info`` / ``status`` / ``state`` / ``blob``), an optional pose-streaming
WebSocket, and static mounts:

- ``/vtk-viewer``     - the reusable frontend library (plain ES modules + CSS,
  no build step) shipped inside the ``director`` package.
- ``/vtk-viewer/wasm-runtime/{VTK_VERSION}`` - the VTK WASM runtime, downloaded
  lazily on first request to match the server's VTK version so client/server
  serialization formats agree. Clients never hardcode this URL; they read
  ``wasm_url`` from the info endpoint.
- ``/``               - the demo's own static assets (``index.html``, ...).

Applications embedding a viewer in their own FastAPI app should call
:func:`mount_viewer_assets` instead of duplicating this layout.

The browser imports and caches the scene over HTTP, then applies pose updates
in the WASM runtime.
"""

import asyncio
import contextlib
import logging
import tarfile
import threading
from collections.abc import AsyncIterator
from pathlib import Path

import anyio.to_thread
import httpx
import uvicorn
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from director.wasm.pose_source import PoseSource
from director.wasm.wasm_assets import DEFAULT_WASM_CACHE_ROOT, VTK_VERSION, ensure_wasm_files
from director.wasm.wasm_scene import WasmScene

log = logging.getLogger(__name__)

VIEWER_ASSETS_DIR = Path(__file__).parent / "viewer_assets"

# How long a WebSocket waiter blocks before re-checking for client disconnect.
_POSE_WAIT_TIMEOUT_S = 2.0


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that forces revalidation on every request.

    ``no-cache`` requires browsers to revalidate the viewer library and demo
    pages. This prevents a page cached from one demo from being reused by
    another demo on the same port.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


class WasmRuntimeStaticFiles(StaticFiles):
    """Serve the VTK WASM runtime, downloading it lazily on first request.

    Deferring ``ensure_wasm_files`` to the first request keeps app startup
    fast and network-tolerant: if the Kitware download fails, only the runtime
    URL returns 503 (the browser viewer reports a load failure) while the rest
    of the app keeps working, and the next request simply retries.

    Responses are marked immutable: the runtime is served under a URL
    containing the VTK version, so a VTK upgrade moves clients to a new URL
    and the old cached bytes can be kept forever without revalidation.
    """

    def __init__(self, cache_root: Path | None = None) -> None:
        cache_dir = (cache_root or DEFAULT_WASM_CACHE_ROOT) / VTK_VERSION
        # Starlette requires the directory to exist to serve from it; the
        # files inside arrive with the lazy download on first request.
        cache_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(directory=cache_dir)
        self._cache_root = cache_root
        self._download_lock = threading.Lock()
        self._runtime_ready = False

    def _ensure_runtime_downloaded(self) -> None:
        with self._download_lock:
            if not self._runtime_ready:
                ensure_wasm_files(cache_root=self._cache_root)
                self._runtime_ready = True

    async def get_response(self, path, scope):
        if not self._runtime_ready:
            try:
                await anyio.to_thread.run_sync(self._ensure_runtime_downloaded)
            except (httpx.HTTPError, tarfile.TarError, OSError) as exc:
                log.error(f"VTK WASM runtime unavailable (download failed): {exc}")
                return PlainTextResponse(
                    "VTK WASM runtime unavailable: download from Kitware failed",
                    status_code=503,
                )
        return await super().get_response(path, scope)

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def mount_viewer_assets(app: FastAPI, *, prefix: str = "/vtk-viewer", wasm_cache_root: Path | None = None) -> str:
    """Mount the viewer frontend library and the version-matched WASM runtime.

    Returns the runtime URL that the app's info endpoint must expose as
    ``wasm_url`` so the client loader can find it. Keeping both mounts behind
    one helper lets embedding apps (e.g. Flight Deck) serve everything under a
    single ``{prefix}`` reverse-proxy location while preserving the split
    caching policy: the runtime is immutable per VTK version, the viewer
    library must always revalidate.

    The runtime download from Kitware happens lazily on the first request, so
    mounting never blocks startup or raises on network failure.
    """
    wasm_url = f"{prefix}/wasm-runtime/{VTK_VERSION}"
    # The nested mount must be registered before the broader prefix mount;
    # Starlette matches mounts in registration order.
    app.mount(wasm_url, WasmRuntimeStaticFiles(cache_root=wasm_cache_root), name="vtk-wasm-runtime")
    app.mount(prefix, NoCacheStaticFiles(directory=VIEWER_ASSETS_DIR), name="vtk-viewer")
    return wasm_url


def create_wasm_app(
    scene: WasmScene,
    *,
    pose_source: PoseSource | None = None,
    static_dir: Path | None = None,
    title: str = "director.wasm demo",
) -> FastAPI:
    """Build a FastAPI app serving ``scene`` and, optionally, live poses.

    The scene must be finalized before the server starts. A static scene
    (``pose_source=None``) has no ``/ws/poses`` endpoint; the frontend viewer
    skips pose streaming when no WebSocket URL is configured.
    """
    if not scene.is_finalized:
        raise RuntimeError("WasmScene must be finalized before serving; call scene.finalize()")

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        # Unblock wait_for_update waiters so open WebSockets close cleanly.
        if pose_source is not None:
            pose_source.stop()

    app = FastAPI(title=title, lifespan=lifespan)

    wasm_url = mount_viewer_assets(app)

    @app.get("/api/info")
    def wasm_info() -> dict:
        """Everything the client needs to import + drive the scene.

        ``scene_version`` namespaces the browser geometry cache; ``objects`` is
        the flat tree metadata (folders + objects with their WASM ids) the
        client uses for the object tree, properties panel, and pose application.
        """
        return {
            "render_window_id": scene.render_window_id,
            "renderer_id": scene.renderer_id,
            "interactor_id": scene.interactor_id,
            "wasm_url": wasm_url,
            "scene_version": scene.scene_version(),
            "objects": scene.scene_metadata(),
        }

    @app.get("/api/status/{obj_id}")
    def wasm_status(obj_id: int) -> dict:
        """Dependency IDs, blob hashes, and camera info for a VTK object."""
        return scene.get_status(obj_id)

    @app.get("/api/state/{obj_id}")
    def wasm_state(obj_id: int) -> Response:
        """Serialized JSON state for a VTK object."""
        return Response(content=scene.get_state(obj_id), media_type="application/json")

    @app.get("/api/blob/{hash_str}")
    def wasm_blob(hash_str: str) -> Response:
        """Binary blob data (vertex arrays, etc.)."""
        return Response(content=scene.get_blob(hash_str), media_type="application/octet-stream")

    if pose_source is not None:
        _add_pose_websocket(app, pose_source)

    # Demo pages must always revalidate (demos share ports, and stale HTML
    # from another demo breaks the viewer). The viewer library + WASM runtime
    # mounts are registered by mount_viewer_assets above.
    if static_dir is not None:
        app.mount("/", NoCacheStaticFiles(directory=static_dir, html=True), name="demo-static")

    return app


def _add_pose_websocket(app: FastAPI, pose_source: PoseSource) -> None:
    @app.websocket("/ws/poses")
    async def pose_stream(websocket: WebSocket) -> None:
        """Stream lightweight per-object pose frames as poses change.

        The scene is imported once over HTTP; thereafter only ``{seq, poses}``
        is pushed here (``poses`` maps object key -> 16 row-major floats).  The
        client applies each pose to the object's ``UserMatrix`` directly on the
        WASM side, so no VTK state is re-serialized per frame.
        """
        await websocket.accept()
        last_seen_seq = pose_source.seq

        # Send an initial frame so the client is correctly posed immediately,
        # even if nothing has moved since import.
        await websocket.send_json({"seq": last_seen_seq, "poses": pose_source.pose_frame()})

        # Detect client disconnect promptly without blocking the send cadence.
        receive_task: asyncio.Task = asyncio.create_task(websocket.receive())

        try:
            while True:
                update_task: asyncio.Task = asyncio.create_task(
                    asyncio.to_thread(pose_source.wait_for_update, last_seen_seq, _POSE_WAIT_TIMEOUT_S)
                )

                done, _ = await asyncio.wait(
                    [update_task, receive_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if receive_task in done:
                    update_task.cancel()
                    return

                new_seq, has_update = update_task.result()
                if not has_update:
                    continue
                last_seen_seq = new_seq
                await websocket.send_json({"seq": new_seq, "poses": pose_source.pose_frame()})
        except (WebSocketDisconnect, asyncio.CancelledError):
            return
        finally:
            receive_task.cancel()


def run_wasm_app(app: FastAPI, *, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the app with uvicorn (blocks until interrupted)."""
    log.info(f"Serving {app.title} at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
