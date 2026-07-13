"""director.wasm demo: embedding the 3D viewer in an iframe on a larger page.

The scene and pose stream are the ones from :mod:`director.examples.wasm_cone`;
only the static assets differ.  ``index.html`` is a dashboard-style page whose
3D panel is an ``<iframe>`` pointing at ``viewer.html`` (the same kind of
full-page viewer the other demos use).

The iframe is deliberate, not a workaround for this demo: VTK WASM takes over
its canvas and sizes it to the parent container, which fights the layout of a
surrounding component tree (e.g. the parent height collapses after VTK
initializes inside a flex/React layout).  Giving the viewer its own document
(with ``body { height: 100vh }``) keeps canvas sizing stable, and the host page
just places the iframe like any other element.

Run:
    uv run python -m director.examples.wasm_iframe_embed
then open http://127.0.0.1:8000 in a browser.
"""

import argparse
from pathlib import Path

from director.examples.wasm_cone import (
    SpinningConePoseSource,
    build_cone_scene,
    start_animation_ticker,
)
from director.wasm import create_wasm_app, run_wasm_app

_ASSETS_DIR = Path(__file__).parent / "wasm_demo_assets" / "iframe_embed"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a page embedding the vtk-wasm viewer in an iframe")
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
        title="director.wasm iframe embed demo",
    )
    print(f"Iframe embed demo running -- open http://{args.host}:{args.port} in a browser")
    run_wasm_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
