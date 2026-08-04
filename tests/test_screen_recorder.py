"""Tests for screen_recorder capture, codec presets, and transparent background recording."""

import shutil
import subprocess

import numpy as np
import pytest
import vtk

from director import screen_recorder
from director.ffmpeg_writer import FFMpegWriter
from director.screen_recorder import (
    CODEC_PRESETS,
    ScreenRecorder,
    capture_screenshot,
    capture_screenshot_rgba,
)
from director.vtk_widget import VTKWidget

requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _preset(name):
    (preset,) = [preset for preset in CODEC_PRESETS if preset.name == name]
    return preset


def _make_widget_with_cone(qapp):
    widget = VTKWidget()
    widget.resize(320, 240)
    cone = vtk.vtkConeSource()
    cone.SetResolution(32)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(cone.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    widget.renderer().AddActor(actor)
    widget.resetCamera()
    widget.show()
    qapp.processEvents()
    widget.forceRender()
    return widget


def test_capture_screenshot_shapes(qapp):
    """RGB capture returns 3 channels, RGBA capture returns 4."""
    widget = _make_widget_with_cone(qapp)

    rgb = capture_screenshot(widget)
    assert rgb.ndim == 3 and rgb.shape[2] == 3
    assert rgb.dtype == np.uint8

    rgba = capture_screenshot_rgba(widget)
    assert rgba.ndim == 3 and rgba.shape[2] == 4
    assert rgba.dtype == np.uint8
    assert rgba.shape[:2] == rgb.shape[:2]


def test_capture_screenshot_rgba_transparent_background(qapp):
    """With BackgroundAlpha=0 the capture separates geometry from background."""
    widget = _make_widget_with_cone(qapp)
    renderer = widget.renderer()
    renderer.GradientBackgroundOff()
    renderer.SetBackground(0.0, 0.0, 0.0)
    renderer.SetBackgroundAlpha(0.0)
    widget.forceRender()

    alpha = capture_screenshot_rgba(widget)[:, :, 3]
    total = alpha.size
    assert np.sum(alpha == 0) > 0.3 * total, "expected a mostly transparent background"
    assert np.sum(alpha == 255) > 0.005 * total, "expected opaque geometry pixels"


TRANSPARENT_PRESET_NAMES = [preset.name for preset in CODEC_PRESETS if preset.transparent_background]


@requires_ffmpeg
@pytest.mark.parametrize("preset_name", TRANSPARENT_PRESET_NAMES)
def test_transparent_preset_alpha_roundtrip(tmp_path, preset_name):
    """RGBA frames encode with alpha, unpremultiplied to straight alpha on the way in."""
    preset = _preset(preset_name)
    width, height = 64, 48
    filename = tmp_path / f"alpha.{preset.file_extension}"

    # Premultiplied test content: transparent background, opaque square, and a
    # half-coverage region (rgb = 0.5 * color) as produced by MSAA edges.
    frame = np.zeros((height, width, 4), dtype=np.uint8)
    frame[8:40, 32:56] = [230, 100, 40, 255]
    frame[16:32, 4:24] = [115, 50, 20, 128]

    with FFMpegWriter(
        filename=str(filename), width=width, height=height, framerate=30.0, **preset.writer_kwargs
    ) as writer:
        for _ in range(3):
            writer.write_frame(frame)

    decode_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(filename),
        "-frames:v",
        "1",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-",
    ]
    raw = subprocess.run(decode_cmd, capture_output=True, check=True).stdout
    decoded = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)

    color_tolerance = 12
    assert decoded[0, 0, 3] == 0, "background alpha not preserved"
    opaque = decoded[24, 44]
    assert opaque[3] == 255 and abs(int(opaque[0]) - 230) <= color_tolerance
    edge = decoded[24, 12]
    assert abs(int(edge[3]) - 128) <= 6, "fractional alpha not preserved"
    # unpremultiply should recover the straight color from the premultiplied rgb.
    assert abs(int(edge[0]) - 230) <= color_tolerance, f"straight color not recovered: {edge}"


@requires_ffmpeg
def test_ffmpeg_writer_rejects_wrong_channel_count(tmp_path):
    with FFMpegWriter(filename=str(tmp_path / "out.mp4"), width=32, height=32) as writer:
        with pytest.raises(ValueError, match="does not match expected"):
            writer.write_frame(np.zeros((32, 32, 4), dtype=np.uint8))


def test_ffmpeg_writer_rejects_unknown_input_pix_fmt(tmp_path):
    with pytest.raises(ValueError, match="Unsupported pix_fmt_input"):
        FFMpegWriter(filename=str(tmp_path / "out.mp4"), width=32, height=32, pix_fmt_input="yuv420p")


class _FakeWriter:
    """Stands in for FFMpegWriter so recording tests skip the ffmpeg process."""

    def __init__(self, filename, width, height, framerate, **kwargs):
        self.filename = filename
        self.kwargs = kwargs
        self.frames = []

    def write_frame(self, frame):
        self.frames.append(frame)

    def close(self):
        pass


def test_codec_preset_menu_defaults_and_selection(qapp):
    """The default preset is checked; selecting another flips the exclusive group."""
    recorder = ScreenRecorder(main_window=None, view=None)
    default_preset = CODEC_PRESETS[0]
    assert recorder.codec_preset is default_preset
    assert recorder.codec_preset_actions[default_preset.name].isChecked()

    prores = _preset("transparent_prores4444_mov")
    recorder._set_codec_preset(prores)
    assert recorder.codec_preset is prores
    assert recorder.codec_preset_actions[prores.name].isChecked()
    assert not recorder.codec_preset_actions[default_preset.name].isChecked()


def test_transparent_recording_switches_and_restores_background(qapp, monkeypatch):
    """A transparent preset records RGBA to .mov and restores the renderer on stop."""
    widget = _make_widget_with_cone(qapp)
    renderer = widget.renderer()
    original_gradient = renderer.GetGradientBackground()
    original_background = renderer.GetBackground()
    original_alpha = renderer.GetBackgroundAlpha()

    monkeypatch.setattr(screen_recorder, "FFMpegWriter", _FakeWriter)
    recorder = ScreenRecorder(main_window=None, view=widget)
    monkeypatch.setattr(recorder, "_show_completion_dialog", lambda: None)
    recorder._set_capture_mode("playback")
    recorder._set_codec_preset(_preset("transparent_prores4444_mov"))

    recorder._start_recording()
    assert recorder.is_recording
    assert recorder.current_filename.endswith(".mov")
    assert recorder.writer.kwargs["pix_fmt_input"] == "rgba"
    assert renderer.GetBackgroundAlpha() == 0.0
    assert not renderer.GetGradientBackground()

    recorder.on_capture()
    assert len(recorder.writer.frames) == 1
    assert recorder.writer.frames[0].shape[2] == 4

    recorder._stop_recording()
    assert not recorder.is_recording
    assert renderer.GetGradientBackground() == original_gradient
    assert renderer.GetBackground() == original_background
    assert renderer.GetBackgroundAlpha() == original_alpha


def test_default_recording_still_writes_rgb_mp4(qapp, monkeypatch):
    widget = _make_widget_with_cone(qapp)
    monkeypatch.setattr(screen_recorder, "FFMpegWriter", _FakeWriter)
    recorder = ScreenRecorder(main_window=None, view=widget)
    monkeypatch.setattr(recorder, "_show_completion_dialog", lambda: None)
    recorder._set_capture_mode("playback")

    recorder._start_recording()
    assert recorder.current_filename.endswith(".mp4")
    recorder.on_capture()
    assert recorder.writer.frames[0].shape[2] == 3
    recorder._stop_recording()
