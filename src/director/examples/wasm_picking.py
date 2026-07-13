"""director.wasm demo: object picking (hover highlight, click select, menu).

The browser analog of :mod:`director.examples.draw_shapes`: a static scene of
DebugData geometry where the object under the cursor is found with a real VTK
hardware pick executed inside the WASM runtime (``vtkPropPicker`` via WASM
``invoke`` calls -- see ``SceneSession.pick``).  The demo page wires three
interactions on top of ``viewer.pickAtEvent``:

- hover: the picked object glows (ambient bump, like draw_shapes) and its name
  is shown in the header;
- left click (with a drag tolerance): the object is selected in the scene panel;
- right click: the built-in context menu shows the picked object's name and a
  Select action, like Director's showRightClickMenu.

Run:
    uv run python -m director.examples.wasm_picking
then open http://127.0.0.1:8000 in a browser.
"""

import argparse
from pathlib import Path

import numpy as np
import vtk

from director import transformUtils
from director.debugVis import DebugData
from director.wasm import WasmScene, create_wasm_app, flat16_from_vtk_matrix, run_wasm_app

_ASSETS_DIR = Path(__file__).parent / "wasm_demo_assets" / "picking"


def _translation(x: float, y: float, z: float) -> list[float]:
    frame = transformUtils.frameFromPositionAndRPY([x, y, z], [0.0, 0.0, 0.0])
    return flat16_from_vtk_matrix(frame.GetMatrix())


def _polydata(build) -> vtk.vtkPolyData:
    """Build one shape into its own polydata (color=None skips DebugData's
    per-vertex color array so the actor's vtkProperty drives color; that also
    keeps the hover highlight's ambient bump visually uniform)."""
    data = DebugData()
    build(data)
    return data.getPolyData()


def _helix_points(number_of_points: int = 400) -> np.ndarray:
    theta = np.linspace(0, np.pi * 8, number_of_points)
    points = np.vstack((theta, np.cos(theta), np.sin(theta))).T.copy()
    points /= np.max(points)
    return points


def build_picking_scene() -> WasmScene:
    scene = WasmScene(
        camera_position=(7.0, 6.0, 5.0),
        camera_focal_point=(0.0, 0.0, 0.5),
        camera_view_up=(0.0, 0.0, 1.0),
        interactor_style=vtk.vtkInteractorStyleTerrain(),
    )

    curves = scene.add_folder("Curves")
    scene.add_object(
        "helix",
        _polydata(lambda d: d.addPolyLine(_helix_points(), radius=0.04, color=None)),
        color=(0.35, 0.80, 0.85),
        parent=curves.key,
        object_type="polyline",
        matrix=_translation(-2.2, -1.0, 0.6),
    )
    scene.add_object(
        "arrow",
        _polydata(lambda d: d.addArrow((0, 0, 0), (0, 0, 1.2), tubeRadius=0.04, headRadius=0.12, color=None)),
        color=(0.90, 0.35, 0.35),
        parent=curves.key,
        object_type="arrow",
        matrix=_translation(-0.9, -1.2, 0.0),
    )

    solids = scene.add_folder("Solids")
    scene.add_object(
        "ellipsoid",
        _polydata(lambda d: d.addEllipsoid((0, 0, 0.35), radii=(0.55, 0.35, 0.35), color=None)),
        color=(0.85, 0.65, 0.25),
        parent=solids.key,
        object_type="ellipsoid",
        matrix=_translation(0.6, -1.1, 0.0),
    )
    scene.add_object(
        "capsule",
        _polydata(lambda d: d.addCapsule(center=(0, 0, 0.55), axis=(0, 0, 1), length=0.7, radius=0.28, color=None)),
        color=(0.35, 0.80, 0.45),
        parent=solids.key,
        object_type="capsule",
        matrix=_translation(2.0, -1.0, 0.0),
    )
    scene.add_object(
        "cube",
        _polydata(lambda d: d.addCube(dimensions=(0.7, 0.7, 0.7), center=(0, 0, 0.35), color=None)),
        color=(0.92, 0.45, 0.20),
        parent=solids.key,
        object_type="cube",
        matrix=_translation(-1.4, 1.0, 0.0),
    )
    scene.add_object(
        "sphere",
        _polydata(lambda d: d.addSphere(center=(0, 0, 0.45), radius=0.45, color=None)),
        color=(0.30, 0.55, 0.95),
        parent=solids.key,
        object_type="sphere",
        matrix=_translation(0.2, 1.2, 0.0),
    )
    scene.add_object(
        "cone",
        _polydata(lambda d: d.addCone(origin=(0, 0, 0), normal=(0, 0, 1), radius=0.4, height=0.9, color=None)),
        color=(0.85, 0.75, 0.25),
        parent=solids.key,
        object_type="cone",
        matrix=_translation(1.8, 1.1, 0.0),
    )

    environment = scene.add_folder("Environment")
    scene.add_object(
        "ground",
        _polydata(lambda d: d.addPlane(origin=(0, 0, 0), normal=(0, 0, 1), width=7.0, height=5.0, color=None)),
        color=(0.45, 0.48, 0.55),
        opacity=0.5,
        parent=environment.key,
        object_type="plane",
    )
    # The ground stays pickable so click-select and the right-click menu work
    # on it; only the hover highlight skips it (see HOVER_SKIP in the demo
    # page) because a glow on the full-view plane is distracting. To remove an
    # object from picking entirely, use the vtkActor escape hatch instead:
    # scene.get_actor("ground").PickableOff() before finalize, or toggle it
    # live from the client with SceneSession.setPickable.

    scene.finalize()
    return scene


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve an object-picking vtk-wasm demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_wasm_app(
        build_picking_scene(),
        static_dir=_ASSETS_DIR,
        title="director.wasm picking demo",
    )
    print(f"Picking demo running -- open http://{args.host}:{args.port} in a browser")
    run_wasm_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
