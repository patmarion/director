"""A VTK scene serialized once for the ``@kitware/vtk-wasm`` RemoteSession.

``WasmScene`` is the reusable core of the viewer framework.  It owns a VTK
render pipeline (renderer + offscreen render window + interactor) and a
``vtkObjectManager``, and exposes a small build API plus the serialization
protocol the client needs.

Lifecycle:
  1. Build phase: ``add_folder`` / ``add_object`` populate the scene.
  2. ``finalize`` serializes everything exactly once and captures the WASM ids.
  3. Read-only phase: ``get_state`` / ``get_blob`` / ``get_status`` serve the
     import; the scene never re-serializes.  Live motion is applied entirely on
     the client by setting each object's ``UserMatrix`` ``Data`` directly (see
     :class:`SceneObject`), which is the performance unlock over a
     "re-serialize on every pose" approach.
"""

import hashlib
import logging
import re
import threading
from collections.abc import Sequence

import vtk
from vtkmodules.vtkSerializationManager import vtkObjectManager

from director.wasm.scene_object import SceneNode, SceneObject

log = logging.getLogger(__name__)

# Default dark gradient background, matched to the frontend panels.
_BACKGROUND = (38 / 255, 42 / 255, 54 / 255)
_BACKGROUND2 = (62 / 255, 68 / 255, 84 / 255)

Vec3 = tuple[float, float, float]

# Matches "MTime": <n> fields (at any nesting depth) in serialized state JSON;
# see _compute_scene_version for why they must not participate in the version.
_MTIME_FIELD = re.compile(r'"MTime"\s*:\s*\d+')


class WasmScene:
    """Builds a VTK scene and serializes it once for the vtk-wasm client."""

    def __init__(
        self,
        *,
        size: tuple[int, int] = (800, 600),
        camera_position: Vec3 = (10.0, 10.0, 10.0),
        camera_focal_point: Vec3 = (0.0, 0.0, 0.0),
        camera_view_up: Vec3 = (0.0, 0.0, 1.0),
        interactor_style: vtk.vtkInteractorStyle | None = None,
    ) -> None:
        self.object_manager = vtkObjectManager()
        self.object_manager.Initialize()
        self._lock = threading.Lock()

        self._renderer = vtk.vtkRenderer()
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground(*_BACKGROUND)
        self._renderer.SetBackground2(*_BACKGROUND2)

        light_kit = vtk.vtkLightKit()
        light_kit.SetKeyLightWarmth(0.5)
        light_kit.SetFillLightWarmth(0.5)
        light_kit.AddLightsToRenderer(self._renderer)

        self._render_window = vtk.vtkRenderWindow()
        self._render_window.SetOffScreenRendering(True)
        self._render_window.SetSize(*size)
        self._render_window.AddRenderer(self._renderer)

        self._interactor = vtk.vtkRenderWindowInteractor()
        self._interactor.SetRenderWindow(self._render_window)
        self._interactor.SetInteractorStyle(interactor_style or vtk.vtkInteractorStyleTrackballCamera())

        self._camera_position = camera_position
        self._camera_focal_point = camera_focal_point
        self._camera_view_up = camera_view_up

        # Ordered tree nodes (folders + objects) plus the live VTK handles we
        # need at finalize() to read back their serialization ids.
        self._nodes: list[SceneNode | SceneObject] = []
        self._keys: set[str] = set()
        self._handles: dict[str, tuple[vtk.vtkActor, vtk.vtkMatrix4x4]] = {}

        self._finalized = False
        self.render_window_id = 0
        # Lets clients drive renderer-level properties (e.g. the gradient
        # background) with direct WASM set() calls, like per-object edits.
        self.renderer_id = 0
        # Lets clients reach the interactor's default prop picker via WASM
        # invoke() calls for hardware picking (hover/click/context menu).
        self.interactor_id = 0
        self._scene_version = ""

    # ── Build API ─────────────────────────────────────────────────────

    def add_folder(self, name: str, parent: str | None = None) -> SceneNode:
        """Add a grouping node (no geometry) to the client object tree."""
        self._assert_building()
        node = SceneNode(key=self._unique_key(name), name=name, parent=parent)
        self._nodes.append(node)
        return node

    def add_object(
        self,
        name: str,
        polydata: vtk.vtkPolyData,
        *,
        color: Vec3 = (0.8, 0.8, 0.8),
        opacity: float = 1.0,
        parent: str | None = None,
        object_type: str = "mesh",
        matrix: Sequence[float] | None = None,
    ) -> SceneObject:
        """Add a renderable object built from ``polydata``.

        ``matrix`` is an optional initial pose as 16 row-major floats so the
        first imported frame is already correctly placed.  The actor is driven
        per-frame via its ``UserMatrix`` (see :class:`SceneObject`).
        """
        self._assert_building()
        key = self._unique_key(name)

        # The vtk-wasm client mis-renders triangle strips (tube/stripper
        # output): strip connectivity gets garbled into stray triangles while
        # desktop OpenGL draws the same polydata fine. Decompose strips into
        # plain triangles so any polydata renders as it does on desktop. Only
        # strip-bearing inputs are touched -- triangulating everything would
        # e.g. add diagonals to quad meshes in "Surface with edges" mode.
        if polydata.GetNumberOfStrips() > 0:
            triangle_filter = vtk.vtkTriangleFilter()
            triangle_filter.SetInputData(polydata)
            triangle_filter.Update()
            polydata = triangle_filter.GetOutput()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        # The mapper's default lookup table serializes its color table even
        # when unused, and before Build() that table is uninitialized memory --
        # which made identical scenes hash to different scene_versions and
        # defeated the browser cache. Building it makes the state deterministic.
        mapper.GetLookupTable().Build()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(opacity)

        # Drive pose through a vtkMatrix4x4 we own so it gets a stable id we can
        # target each frame with set(matrix_id, {"Data": [...]}).
        user_matrix = vtk.vtkMatrix4x4()
        if matrix is not None:
            _apply_matrix(user_matrix, matrix)
        actor.SetUserMatrix(user_matrix)

        self._renderer.AddActor(actor)

        obj = SceneObject(
            key=key,
            name=name,
            parent=parent,
            object_type=object_type,
            color=tuple(color),
            opacity=opacity,
        )
        self._nodes.append(obj)
        self._handles[key] = (actor, user_matrix)
        return obj

    def get_actor(self, key: str) -> vtk.vtkActor:
        """Escape hatch to an object's underlying ``vtkActor`` during the build phase.

        The build API intentionally covers only the common fields (color,
        opacity, pose); anything beyond that -- e.g. ``PickableOff()`` for
        background geometry, or lighting tweaks on ``GetProperty()`` -- can be
        set directly on the actor and will serialize with the scene, as long
        as it happens before :meth:`finalize` captures the states.  The scene
        never re-serializes after finalize, so a late edit would silently
        never reach the client; that is why this raises instead.  (Runtime
        changes belong on the client, via direct WASM ``set()`` calls on the
        actor id, e.g. ``SceneSession.setPickable``.)
        """
        if self._finalized:
            raise RuntimeError("WasmScene is finalized; actor edits would no longer be serialized")
        if key not in self._handles:
            raise KeyError(f"No object with key {key!r}")
        actor, _ = self._handles[key]
        return actor

    def finalize(self) -> None:
        """Frame the camera, serialize once, and capture all WASM ids."""
        if self._finalized:
            return

        camera = self._renderer.GetActiveCamera()
        camera.SetPosition(*self._camera_position)
        camera.SetFocalPoint(*self._camera_focal_point)
        camera.SetViewUp(*self._camera_view_up)
        self._renderer.ResetCamera()

        self.object_manager.RegisterObject(self._render_window)
        self.object_manager.UpdateStatesFromObjects()
        self.render_window_id = self.object_manager.GetId(self._render_window)
        self.renderer_id = self.object_manager.GetId(self._renderer)
        self.interactor_id = self.object_manager.GetId(self._interactor)

        for node in self._nodes:
            if isinstance(node, SceneObject):
                actor, user_matrix = self._handles[node.key]
                node.actor_id = self.object_manager.GetId(actor)
                node.matrix_id = self.object_manager.GetId(user_matrix)
                node.property_id = self.object_manager.GetId(actor.GetProperty())

        self._scene_version = self._compute_scene_version()
        self._finalized = True

        object_count = sum(1 for n in self._nodes if isinstance(n, SceneObject))
        log.info(
            f"WasmScene finalized: rw_id={self.render_window_id}, {object_count} objects, version={self._scene_version}"
        )

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    # ── Serialization protocol (called by HTTP/WS routes) ─────────────

    def get_state(self, obj_id: int) -> str:
        with self._lock:
            return self.object_manager.GetState(obj_id)

    def get_blob(self, hash_str: str) -> bytes:
        with self._lock:
            return bytes(memoryview(self.object_manager.GetBlob(hash_str)))

    def get_status(self, obj_id: int) -> dict:
        """Dependency graph the RemoteSession needs to import the scene.

        Read-only: nothing is ignored or force-pushed.  Camera/interactor ids
        are reported so the client knows which objects they are.
        """
        with self._lock:
            all_ids = list(self.object_manager.GetAllDependencies(obj_id))
            hashes = list(self.object_manager.GetBlobHashes(all_ids))

            ids_mtime = []
            for vid in all_ids:
                vtk_obj = self.object_manager.GetObjectAtId(vid)
                mtime = int(vtk_obj.GetMTime()) if vtk_obj is not None else 0
                ids_mtime.append([vid, mtime])

            cameras: list[int] = []
            root = self.object_manager.GetObjectAtId(obj_id)
            if root is not None and root.IsA("vtkRenderWindow"):
                renderers = root.GetRenderers()
                renderers.InitTraversal()
                for _ in range(renderers.GetNumberOfItems()):
                    renderer = renderers.GetNextItem()
                    cameras.append(self.object_manager.GetId(renderer.GetActiveCamera()))

            return {
                "ids": ids_mtime,
                "hashes": hashes,
                "ignore_ids": [],
                "cameras": cameras,
                "force_push": [],
                "interactor": self.object_manager.GetId(self._interactor),
            }

    def scene_metadata(self) -> list[dict]:
        """Flat list of tree nodes (folders + objects) for the client.

        The client reconstructs the hierarchy from each node's ``parent`` key.
        """
        return [node.to_metadata() for node in self._nodes]

    def scene_version(self) -> str:
        """Stable signature of the serialized graph (for client cache busting)."""
        return self._scene_version

    # ── Internal helpers ──────────────────────────────────────────────

    def _assert_building(self) -> None:
        if self._finalized:
            raise RuntimeError("WasmScene is finalized; cannot add more nodes")

    def _unique_key(self, name: str) -> str:
        base = name or "object"
        key = base
        suffix = 2
        while key in self._keys:
            key = f"{base}_{suffix}"
            suffix += 1
        self._keys.add(key)
        return key

    def _compute_scene_version(self) -> str:
        """Signature over the serialized states and blob hashes of the full graph.

        The browser caches every state and blob keyed by this value, so it must
        change whenever *anything* serialized changes -- not just the object
        graph or geometry.  Hashing only ids/classes/blob hashes once caused a
        real stale-cache bug: a property-only edit (``PickableOff`` on an
        actor) produced the same version, and returning browsers replayed the
        old actor state from IndexedDB.  Hashing the full state JSON closes
        that hole.

        ``MTime`` values are stripped first: VTK's modification counter is a
        process-global sequence, so identical scenes serialize with different
        MTimes on every run and would otherwise defeat the cache entirely.
        """
        all_ids = list(self.object_manager.GetAllDependencies(self.render_window_id))
        parts = []
        for vid in sorted(all_ids):
            state = _MTIME_FIELD.sub("", self.object_manager.GetState(vid))
            parts.append(f"{vid}:{state}")
        hashes = sorted(self.object_manager.GetBlobHashes(all_ids))
        signature = ";".join(parts) + "|" + ";".join(hashes)
        return hashlib.sha1(signature.encode()).hexdigest()[:12]


def flat16_from_vtk_matrix(vtk_matrix: vtk.vtkMatrix4x4) -> list[float]:
    """Flatten a vtkMatrix4x4 into the 16 row-major floats the pose wire format
    (and ``vtkMatrix4x4``'s serialized ``Data`` field) uses."""
    return [vtk_matrix.GetElement(row, col) for row in range(4) for col in range(4)]


def _apply_matrix(vtk_matrix: vtk.vtkMatrix4x4, flat16: Sequence[float]) -> None:
    """Write 16 row-major floats into a vtkMatrix4x4."""
    for i in range(16):
        vtk_matrix.SetElement(i // 4, i % 4, float(flat16[i]))
