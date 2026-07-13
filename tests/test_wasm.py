"""Tests for the director.wasm scene serialization framework and demo server.

These stay render-free: WasmScene serializes with vtkObjectManager without ever
calling Render(), so no GPU/GL context is needed and the tests run headless.
"""

import json
import threading
from unittest import mock

import pytest
import vtk

from director.wasm import PoseSource, WasmScene, flat16_from_vtk_matrix


def _cone_polydata() -> vtk.vtkPolyData:
    cone = vtk.vtkConeSource()
    cone.SetResolution(16)
    cone.Update()
    polydata = vtk.vtkPolyData()
    polydata.DeepCopy(cone.GetOutput())
    return polydata


def _build_test_scene() -> WasmScene:
    scene = WasmScene()
    folder = scene.add_folder("Shapes")
    scene.add_object("cone", _cone_polydata(), color=(1.0, 0.5, 0.0), parent=folder.key)
    scene.finalize()
    return scene


class TestWasmScene:
    def test_finalize_captures_object_ids(self):
        scene = _build_test_scene()
        assert scene.is_finalized
        assert scene.render_window_id > 0
        assert scene.renderer_id > 0
        assert scene.interactor_id > 0

        metadata = scene.scene_metadata()
        assert [node["kind"] for node in metadata] == ["folder", "object"]

        cone_meta = metadata[1]
        assert cone_meta["parent"] == "Shapes"
        assert cone_meta["actor_id"] > 0
        assert cone_meta["matrix_id"] > 0
        assert cone_meta["property_id"] > 0

    def test_duplicate_names_get_unique_keys(self):
        scene = WasmScene()
        first = scene.add_object("cone", _cone_polydata())
        second = scene.add_object("cone", _cone_polydata())
        assert first.key == "cone"
        assert second.key == "cone_2"

    def test_add_after_finalize_raises(self):
        scene = _build_test_scene()
        with pytest.raises(RuntimeError, match="finalized"):
            scene.add_object("late", _cone_polydata())

    def test_get_actor_escape_hatch(self):
        """Direct vtkActor edits during the build phase serialize with the scene."""
        scene = WasmScene()
        obj = scene.add_object("cone", _cone_polydata())
        scene.get_actor("cone").PickableOff()
        with pytest.raises(KeyError, match="unknown"):
            scene.get_actor("unknown")
        scene.finalize()

        state = json.loads(scene.get_state(obj.actor_id))
        assert state["Pickable"] == 0

    def test_get_actor_after_finalize_raises(self):
        """Post-finalize actor edits would never reach the client, so refuse them."""
        scene = _build_test_scene()
        with pytest.raises(RuntimeError, match="finalized"):
            scene.get_actor("cone")

    def test_strips_are_decomposed_to_triangles(self):
        """vtkTubeFilter emits triangle strips, which the vtk-wasm client
        garbles into stray triangles; add_object must feed the mapper plain
        triangles instead."""
        line = vtk.vtkLineSource()
        line.SetPoint1(0.0, 0.0, 0.0)
        line.SetPoint2(0.0, 0.0, 1.0)
        tube = vtk.vtkTubeFilter()
        tube.SetInputConnection(line.GetOutputPort())
        tube.SetRadius(0.05)
        tube.Update()
        assert tube.GetOutput().GetNumberOfStrips() > 0  # premise of the test

        scene = WasmScene()
        scene.add_object("tube", tube.GetOutput())
        mapper_input = scene.get_actor("tube").GetMapper().GetInput()
        assert mapper_input.GetNumberOfStrips() == 0
        assert mapper_input.GetNumberOfPolys() > 0

    def test_scene_version_stable_across_rebuilds(self):
        """Identical scenes must version identically even though VTK MTimes (a
        process-global counter) differ between the two builds -- otherwise the
        browser cache would never get a hit."""
        assert _build_test_scene().scene_version() == _build_test_scene().scene_version()

    def test_scene_version_changes_on_property_edit(self):
        """A property-only edit must bust the version: the browser caches full
        states keyed by it, so a same-version change would replay the old
        state from cache (this really happened with PickableOff)."""
        edited = WasmScene()
        folder = edited.add_folder("Shapes")
        edited.add_object("cone", _cone_polydata(), color=(1.0, 0.5, 0.0), parent=folder.key)
        edited.get_actor("cone").PickableOff()
        edited.finalize()
        assert edited.scene_version() != _build_test_scene().scene_version()

    def test_serialization_protocol_round_trip(self):
        scene = _build_test_scene()
        assert scene.scene_version()

        status = scene.get_status(scene.render_window_id)
        assert status["cameras"]
        assert status["hashes"]

        # Every dependency id must have fetchable JSON state.
        some_id = status["ids"][0][0]
        state = json.loads(scene.get_state(some_id))
        assert state

        blob = scene.get_blob(status["hashes"][0])
        assert isinstance(blob, bytes) and blob

    def test_initial_matrix_applied(self):
        scene = WasmScene()
        matrix = [1.0, 0, 0, 5.0, 0, 1.0, 0, 6.0, 0, 0, 1.0, 7.0, 0, 0, 0, 1.0]
        obj = scene.add_object("cone", _cone_polydata(), matrix=matrix)
        scene.finalize()

        state = json.loads(scene.get_state(obj.matrix_id))
        assert state["Data"] == matrix

    def test_flat16_round_trip(self):
        vtk_matrix = vtk.vtkMatrix4x4()
        vtk_matrix.SetElement(0, 3, 1.5)
        vtk_matrix.SetElement(2, 3, -2.0)
        flat = flat16_from_vtk_matrix(vtk_matrix)
        assert flat[3] == 1.5
        assert flat[11] == -2.0
        assert len(flat) == 16


class _FixedPoseSource(PoseSource):
    def pose_frame(self) -> dict[str, list[float]]:
        return {"cone": [float(i) for i in range(16)]}


class TestPoseSource:
    def test_notify_wakes_waiter(self):
        source = _FixedPoseSource()
        results = []

        def wait() -> None:
            results.append(source.wait_for_update(last_seen_seq=0, timeout_s=5.0))

        waiter = threading.Thread(target=wait)
        waiter.start()
        source.notify()
        waiter.join(timeout=5.0)
        assert results == [(1, True)]

    def test_timeout_without_update(self):
        source = _FixedPoseSource()
        assert source.wait_for_update(last_seen_seq=0, timeout_s=0.01) == (0, False)

    def test_stop_unblocks_waiters(self):
        source = _FixedPoseSource()
        source.stop()
        assert source.wait_for_update(last_seen_seq=0, timeout_s=5.0) == (0, False)


class TestWasmApp:
    @pytest.fixture(scope="class")
    def client(self, tmp_path_factory):
        fastapi = pytest.importorskip("fastapi")  # noqa: F841 -- wasm extra may be absent
        from fastapi.testclient import TestClient

        from director.wasm import create_wasm_app

        # Serve an empty directory instead of downloading the real WASM runtime
        # tarball; these tests exercise the protocol, not the WASM assets.
        fake_wasm_dir = tmp_path_factory.mktemp("wasm-files")
        with mock.patch("director.wasm.server.ensure_wasm_files", return_value=fake_wasm_dir):
            scene = _build_test_scene()
            app = create_wasm_app(scene, pose_source=_FixedPoseSource())
        with TestClient(app) as test_client:
            yield test_client

    def test_info_endpoint(self, client):
        info = client.get("/api/info").json()
        assert info["render_window_id"] > 0
        assert info["renderer_id"] > 0
        assert info["interactor_id"] > 0
        assert info["wasm_url"] == "/vtk-wasm-files"
        assert info["scene_version"]
        assert len(info["objects"]) == 2

    def test_viewer_assets_are_never_stale(self, client):
        """Demo servers share ports, so viewer files must revalidate every load."""
        resp = client.get("/vtk-viewer/viewer.js")
        assert resp.status_code == 200
        assert resp.headers["cache-control"] == "no-cache"

    def test_state_and_blob_endpoints(self, client):
        info = client.get("/api/info").json()
        status = client.get(f"/api/status/{info['render_window_id']}").json()
        assert status["hashes"]

        state_resp = client.get(f"/api/state/{info['render_window_id']}")
        assert state_resp.status_code == 200
        assert state_resp.json()

        blob_resp = client.get(f"/api/blob/{status['hashes'][0]}")
        assert blob_resp.status_code == 200
        assert blob_resp.content

    def test_pose_websocket_sends_initial_frame(self, client):
        with client.websocket_connect("/ws/poses") as websocket:
            frame = websocket.receive_json()
        assert frame["poses"]["cone"] == [float(i) for i in range(16)]

    def test_unfinalized_scene_rejected(self):
        pytest.importorskip("fastapi")
        from director.wasm import create_wasm_app

        with pytest.raises(RuntimeError, match="finalize"):
            create_wasm_app(WasmScene())
