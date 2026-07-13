"""Serve a static browser scene with primitive shapes and editable properties.

Run:
    uv run python -m director.examples.wasm_shapes
then open http://127.0.0.1:8000 in a browser.
"""

import argparse
from pathlib import Path

import vtk

from director import transformUtils
from director.debugVis import DebugData
from director.wasm import WasmScene, create_wasm_app, flat16_from_vtk_matrix, run_wasm_app

_ASSETS_DIR = Path(__file__).parent / "wasm_demo_assets" / "shapes"


def _translation(x: float, y: float, z: float) -> list[float]:
    frame = transformUtils.frameFromPositionAndRPY([x, y, z], [0.0, 0.0, 0.0])
    return flat16_from_vtk_matrix(frame.GetMatrix())


def _polydata(build) -> vtk.vtkPolyData:
    """Build one shape into its own polydata (color=None skips DebugData's
    per-vertex color array; the actor's vtkProperty drives color instead so the
    properties panel can edit it)."""
    data = DebugData()
    build(data)
    return data.getPolyData()


def build_shapes_scene() -> WasmScene:
    scene = WasmScene(
        camera_position=(6.0, 5.0, 4.0),
        camera_focal_point=(0.0, 0.0, 0.5),
        camera_view_up=(0.0, 0.0, 1.0),
        # Terrain style keeps Z up while orbiting, which suits a Z-up scene
        # sitting on a ground plane (the other demos keep the trackball
        # default). The style serializes with the scene like everything else.
        interactor_style=vtk.vtkInteractorStyleTerrain(),
    )

    primitives = scene.add_folder("Primitives")
    scene.add_object(
        "sphere",
        _polydata(lambda d: d.addSphere(center=(0, 0, 0.5), radius=0.5, color=None)),
        color=(0.30, 0.55, 0.95),
        parent=primitives.key,
        object_type="sphere",
        matrix=_translation(-2.4, 0.0, 0.0),
    )
    scene.add_object(
        "cube",
        _polydata(lambda d: d.addCube(dimensions=(0.8, 0.8, 0.8), center=(0, 0, 0.4), color=None)),
        color=(0.92, 0.45, 0.20),
        parent=primitives.key,
        object_type="cube",
        matrix=_translation(-0.8, 0.0, 0.0),
    )
    scene.add_object(
        "capsule",
        _polydata(lambda d: d.addCapsule(center=(0, 0, 0.6), axis=(0, 0, 1), length=0.8, radius=0.3, color=None)),
        color=(0.35, 0.80, 0.45),
        parent=primitives.key,
        object_type="capsule",
        matrix=_translation(0.8, 0.0, 0.0),
    )
    scene.add_object(
        "cone",
        _polydata(lambda d: d.addCone(origin=(0, 0, 0), normal=(0, 0, 1), radius=0.45, height=1.0, color=None)),
        color=(0.85, 0.75, 0.25),
        parent=primitives.key,
        object_type="cone",
        matrix=_translation(2.4, 0.0, 0.0),
    )

    environment = scene.add_folder("Environment")
    scene.add_object(
        "ground",
        _polydata(lambda d: d.addPlane(origin=(0, 0, 0), normal=(0, 0, 1), width=7.0, height=4.0, color=None)),
        color=(0.45, 0.48, 0.55),
        # Half-transparent so shapes read against the gradient background and
        # the panel's Alpha slider has a non-default starting value.
        opacity=0.5,
        parent=environment.key,
        object_type="plane",
    )

    scene.finalize()
    return scene


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a static shapes scene to a vtk-wasm browser viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_wasm_app(
        build_shapes_scene(),
        static_dir=_ASSETS_DIR,
        title="director.wasm shapes demo",
    )
    print(f"Shapes demo running -- open http://{args.host}:{args.port} in a browser")
    run_wasm_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
