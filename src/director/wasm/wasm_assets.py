"""Download and cache the VTK WASM runtime matching the server's VTK version.

The client WASM runtime and the server ``vtkObjectManager`` must serialize in
the same format, so the WASM tarball version must match the Python VTK version.
Reading the version at runtime keeps this correct across venv upgrades without
any pinned constant to maintain.
"""

import io
import logging
import tarfile
from pathlib import Path

import httpx
from vtkmodules.vtkCommonCore import vtkVersion

log = logging.getLogger(__name__)

VTK_VERSION = vtkVersion().GetVTKVersion()
_WASM_TARBALL_URL = (
    "https://gitlab.kitware.com/api/v4/projects/13/packages/generic/"
    f"vtk-wasm32-emscripten/{VTK_VERSION}/"
    f"vtk-{VTK_VERSION}-wasm32-emscripten.tar.gz"
)
DEFAULT_WASM_CACHE_ROOT = Path.home() / ".cache" / "vtk-wasm"
WASM_CACHE_DIR = DEFAULT_WASM_CACHE_ROOT / VTK_VERSION


def ensure_wasm_files(cache_root: Path | None = None) -> Path:
    """Download and extract VTK WASM files to a per-version cache directory.

    ``cache_root`` overrides where the cache lives (a ``{VTK_VERSION}``
    subdirectory is always appended, since the runtime must match the server's
    VTK version); the default follows the XDG cache convention.

    The @kitware/vtk-wasm npm package's tarball extraction only recognizes the
    new file naming (vtkWebAssembly.mjs), but VTK < 9.5.20250531 ships with the
    old naming (vtkWasmSceneManager.mjs). Serving the extracted files from a
    directory URL lets the client-side loader's legacy fallback find them.
    """
    cache_dir = (cache_root or DEFAULT_WASM_CACHE_ROOT) / VTK_VERSION
    marker = cache_dir / ".extracted"
    if marker.exists():
        return cache_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Downloading VTK WASM tarball: {_WASM_TARBALL_URL}")
    resp = httpx.get(_WASM_TARBALL_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()

    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tf:
        tf.extractall(cache_dir, filter="data")

    marker.touch()
    files = [f.name for f in cache_dir.iterdir()]
    log.info(f"Extracted VTK WASM files to {cache_dir}: {files}")
    return cache_dir
