"""Tests for the Director agent client CLI helpers."""

import json
import os
from argparse import Namespace

import pytest

from director import agent_client


def test_get_code_prefers_inline_code(tmp_path):
    code_file = tmp_path / "code.py"
    code_file.write_text("print('from file')")

    args = Namespace(code="print('inline')", file=code_file)

    assert agent_client._get_code(args) == "print('inline')"


def test_get_code_reads_file(tmp_path):
    code_file = tmp_path / "code.py"
    code_file.write_text("print('from file')")

    args = Namespace(code=None, file=code_file)

    assert agent_client._get_code(args) == "print('from file')"


def test_resolve_connection_file_requires_existing_file(tmp_path):
    connection_file = tmp_path / "kernel.json"
    connection_file.write_text("{}")

    assert agent_client._resolve_connection_file(str(connection_file)) == str(connection_file)

    with pytest.raises(FileNotFoundError):
        agent_client._resolve_connection_file(str(tmp_path / "missing.json"))


def test_resolve_connection_file_finds_newest_director_kernel(tmp_path):
    older_connection_file = tmp_path / "kernel-older.json"
    older_connection_file.write_text(json.dumps({"kernel_name": "director"}))
    newer_non_director_file = tmp_path / "kernel-newer-non-director.json"
    newer_non_director_file.write_text(json.dumps({"kernel_name": "python3"}))
    newest_connection_file = tmp_path / "kernel-newest.json"
    newest_connection_file.write_text(json.dumps({"kernel_name": "director"}))

    os.utime(older_connection_file, (1, 1))
    os.utime(newer_non_director_file, (2, 2))
    os.utime(newest_connection_file, (3, 3))

    assert agent_client._find_director_connection_file(tmp_path) == newest_connection_file


def test_handle_output_collects_streams_and_display_metadata():
    stdout_parts = []
    stderr_parts = []
    display_data = []

    agent_client._handle_output(
        {
            "header": {"msg_type": "stream"},
            "content": {"name": "stdout", "text": "hello\n"},
        },
        stdout_parts,
        stderr_parts,
        display_data,
    )
    agent_client._handle_output(
        {
            "header": {"msg_type": "display_data"},
            "content": {
                "data": {"image/png": "...", "text/plain": "<Image>"},
                "metadata": {"image/png": {"width": 100}},
            },
        },
        stdout_parts,
        stderr_parts,
        display_data,
    )

    assert stdout_parts == ["hello\n", "<Image>\n"]
    assert stderr_parts == []
    assert display_data == [
        {
            "mime_types": ["image/png", "text/plain"],
            "metadata": {"image/png": {"width": 100}},
        }
    ]


def test_screenshot_code_uses_director_screenshot_helpers():
    code = agent_client._screenshot_code("/tmp/director-view.png", render=True)

    assert "from director.screen_recorder import capture_screenshot" in code
    assert "from director import ioUtils" in code
    assert "ioUtils.writeImage" in code
    assert "Path('/tmp/director-view.png')" in code
    assert "render = True" in code
