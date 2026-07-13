"""Minimal director.wasm demo: an animated cone rendered in the browser.

This is the "hello world" of the vtk-wasm viewer pattern:

1. Build a VTK scene in Python with :class:`director.wasm.WasmScene` and
   serialize it exactly once (``finalize``).
2. Serve it with the reusable FastAPI app from :func:`director.wasm.create_wasm_app`,
   which also serves the frontend viewer library and this demo's static page.
3. Stream tiny per-object pose frames (16 floats each) over a WebSocket; the
   browser applies them to the resident WASM objects directly -- the geometry
   never crosses the wire again after the one-time import.

Run:
    uv run python -m director.examples.wasm_cone
then open http://127.0.0.1:8000 in a browser.
"""

import argparse
import math
import threading
import time
from pathlib import Path

from director import transformUtils
from director.debugVis import DebugData
from director.wasm import (
    PoseSource,
    SceneObject,
    WasmScene,
    create_wasm_app,
    flat16_from_vtk_matrix,
    run_wasm_app,
)

_ASSETS_DIR = Path(__file__).parent / "wasm_demo_assets" / "cone"

# Synthetic animation: how fast the cone spins (deg/s) and bobs (m).
_SPIN_DEG_PER_SEC = 60.0
_BOB_AMPLITUDE_M = 0.25
_BOB_RATE_RAD_PER_SEC = 2.0
_POSE_RATE_HZ = 30.0


def build_cone_scene() -> tuple[WasmScene, SceneObject]:
    """A cone lying along +X (so spinning about Z is visible) above a ground plane."""
    scene = WasmScene(
        camera_position=(4.0, 4.0, 3.0),
        camera_focal_point=(0.0, 0.0, 0.0),
        camera_view_up=(0.0, 0.0, 1.0),
    )

    cone_data = DebugData()
    cone_data.addCone(origin=(0.0, 0.0, 0.5), normal=(1.0, 0.0, 0.0), radius=0.4, height=1.2, color=None)
    cone = scene.add_object("cone", cone_data.getPolyData(), color=(0.92, 0.45, 0.20))

    ground_data = DebugData()
    ground_data.addPlane(origin=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), width=4.0, height=4.0, color=None)
    scene.add_object("ground", ground_data.getPolyData(), color=(0.45, 0.48, 0.55), object_type="plane")

    scene.finalize()
    return scene, cone


class SpinningConePoseSource(PoseSource):
    """Synthetic animation: the cone spins about Z and bobs vertically.

    Poses are a pure function of wall-clock time, so ``pose_frame`` is computed
    lazily on demand; a separate ticker (see :func:`start_animation_ticker`)
    just bumps ``seq`` at the streaming rate to wake the WebSocket handler.
    """

    def __init__(self, cone_key: str) -> None:
        super().__init__()
        self._cone_key = cone_key
        self._start_time = time.monotonic()

    def pose_frame(self) -> dict[str, list[float]]:
        elapsed_s = time.monotonic() - self._start_time
        yaw_deg = (elapsed_s * _SPIN_DEG_PER_SEC) % 360.0
        bob_m = _BOB_AMPLITUDE_M * math.sin(elapsed_s * _BOB_RATE_RAD_PER_SEC)
        frame = transformUtils.frameFromPositionAndRPY([0.0, 0.0, bob_m], [0.0, 0.0, yaw_deg])
        return {self._cone_key: flat16_from_vtk_matrix(frame.GetMatrix())}


def start_animation_ticker(pose_source: PoseSource, rate_hz: float = _POSE_RATE_HZ) -> threading.Thread:
    """Wake pose-stream waiters at a fixed rate.

    In a real application ``notify()`` would be called from wherever poses
    actually change (kinematics callback, sim step, ...).  Here poses are a
    function of time, so a simple daemon ticker stands in for that event.
    """

    def tick() -> None:
        period_s = 1.0 / rate_hz
        while True:
            pose_source.notify()
            time.sleep(period_s)

    thread = threading.Thread(target=tick, daemon=True, name="wasm-pose-ticker")
    thread.start()
    return thread


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve an animated cone to a vtk-wasm browser viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    scene, cone = build_cone_scene()
    pose_source = SpinningConePoseSource(cone.key)
    start_animation_ticker(pose_source)

    app = create_wasm_app(
        scene,
        pose_source=pose_source,
        static_dir=_ASSETS_DIR,
        title="director.wasm cone demo",
    )
    print(f"Cone demo running -- open http://{args.host}:{args.port} in a browser")
    run_wasm_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
