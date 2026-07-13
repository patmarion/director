"""Metadata describing scene tree nodes for the vtk-wasm client.

The client builds its object tree (folders + selectable items) and properties
panels purely from this metadata, so it stays application-agnostic.  Renderable
objects also carry the serialization ids the client needs to drive the object
directly on the WASM side.
"""

from dataclasses import dataclass


@dataclass
class SceneNode:
    """A non-renderable grouping node (folder) in the scene tree."""

    key: str
    name: str
    parent: str | None = None
    kind: str = "folder"

    def to_metadata(self) -> dict:
        return {"key": self.key, "name": self.name, "kind": self.kind, "parent": self.parent}


@dataclass
class SceneObject:
    """A renderable object plus the WASM ids the client uses to manipulate it.

    ``matrix_id`` is the id of the actor's ``UserMatrix`` (a ``vtkMatrix4x4``
    whose serialized ``Data`` field is a row-major 4x4).  The client updates
    poses through that matrix. ``property_id`` targets the ``vtkProperty`` for
    color and opacity edits; ``actor_id`` targets the actor for visibility.
    """

    key: str
    name: str
    parent: str | None
    object_type: str
    color: tuple[float, float, float]
    opacity: float
    # Populated by WasmScene.finalize().
    actor_id: int = 0
    matrix_id: int = 0
    property_id: int = 0
    kind: str = "object"

    def to_metadata(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "kind": self.kind,
            "parent": self.parent,
            "object_type": self.object_type,
            "color": list(self.color),
            "opacity": self.opacity,
            "actor_id": self.actor_id,
            "matrix_id": self.matrix_id,
            "property_id": self.property_id,
        }
