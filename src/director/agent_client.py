"""CLI for AI agents to interact with an existing Director Jupyter kernel."""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jupyter_client import BlockingKernelClient


@dataclass
class ExecutionResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    display_data: list[dict[str, object]] = field(default_factory=list)
    error: dict[str, object] | None = None


def main(argv=None):
    parser = _make_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        code = _get_code(args)
        result = execute_code(
            code=code,
            connection_file=args.connection_file,
            timeout=args.timeout,
            store_history=not args.no_history,
        )
        _print_result(result)
        return 0 if result.status == "ok" else 1

    if args.command == "screenshot":
        result = execute_code(
            code=_screenshot_code(args.output, args.render),
            connection_file=args.connection_file,
            timeout=args.timeout,
            store_history=not args.no_history,
        )
        _print_result(result)
        return 0 if result.status == "ok" else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def execute_code(code, connection_file=None, timeout=30.0, store_history=True):
    """Execute Python code in an existing Director Jupyter kernel."""
    client = BlockingKernelClient(connection_file=_resolve_connection_file(connection_file))
    client.load_connection_file()
    client.start_channels()

    stdout_parts = []
    stderr_parts = []
    display_data = []
    error = None

    try:
        client.wait_for_ready(timeout=timeout)
        reply = client.execute_interactive(
            code,
            timeout=timeout,
            store_history=store_history,
            output_hook=lambda msg: _handle_output(msg, stdout_parts, stderr_parts, display_data),
        )
    finally:
        client.stop_channels()

    content = reply["content"]
    if content["status"] == "error":
        error = {
            "ename": content.get("ename"),
            "evalue": content.get("evalue"),
            "traceback": content.get("traceback", []),
        }

    return ExecutionResult(
        status=content["status"],
        stdout="".join(stdout_parts),
        stderr="".join(stderr_parts),
        display_data=display_data,
        error=error,
    )


def _make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.set_defaults(command=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="execute Python code in Director")
    _add_common_args(run_parser)
    code_group = run_parser.add_mutually_exclusive_group()
    code_group.add_argument("--code", help="Python code to execute")
    code_group.add_argument("--file", type=Path, help="Python file to execute")

    screenshot_parser = subparsers.add_parser("screenshot", help="capture the active Director view")
    _add_common_args(screenshot_parser)
    screenshot_parser.add_argument("--output", default="/tmp/director-view.png", help="output PNG path")
    screenshot_parser.add_argument("--no-render", action="store_false", dest="render", help="skip forceRender")
    screenshot_parser.set_defaults(render=True)

    return parser


def _add_common_args(parser):
    parser.add_argument(
        "--connection-file",
        default=os.environ.get("DIRECTOR_KERNEL_CONNECTION_FILE"),
        help="Director Jupyter kernel connection file",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="execution timeout in seconds")
    parser.add_argument("--no-history", action="store_true", help="do not store code in kernel history")


def _get_code(args):
    if args.code is not None:
        return args.code
    if args.file is not None:
        return args.file.read_text()
    return sys.stdin.read()


def _resolve_connection_file(connection_file):
    if connection_file is None:
        return str(_find_director_connection_file())

    path = Path(connection_file).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Director kernel connection file does not exist: {path}")
    return str(path)


def _find_director_connection_file(runtime_dir=None):
    runtime_path = Path(runtime_dir or _jupyter_runtime_dir()).expanduser()
    if not runtime_path.exists():
        raise FileNotFoundError(f"Jupyter runtime directory does not exist: {runtime_path}")

    for path in sorted(runtime_path.glob("kernel-*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            connection_info = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if connection_info.get("kernel_name") == "director":
            return path

    raise FileNotFoundError(f"No Director kernel connection file found in {runtime_path}")


def _jupyter_runtime_dir():
    if "JUPYTER_RUNTIME_DIR" in os.environ:
        return os.environ["JUPYTER_RUNTIME_DIR"]
    return Path.home() / ".local" / "share" / "jupyter" / "runtime"


def _handle_output(msg, stdout_parts, stderr_parts, display_data):
    msg_type = msg["header"]["msg_type"]
    content = msg["content"]
    if msg_type == "stream":
        if content["name"] == "stderr":
            stderr_parts.append(content["text"])
        else:
            stdout_parts.append(content["text"])
    elif msg_type in {"display_data", "execute_result"}:
        data = content.get("data", {})
        display_data.append(
            {
                "mime_types": sorted(data.keys()),
                "metadata": content.get("metadata", {}),
            }
        )
        if "text/plain" in data:
            stdout_parts.append(f"{data['text/plain']}\n")
    elif msg_type == "error":
        stderr_parts.append("\n".join(content.get("traceback", [])))
        stderr_parts.append("\n")


def _screenshot_code(output, render):
    return "\n".join(
        [
            "import json",
            "from pathlib import Path",
            "from director import ioUtils",
            "from director import vtkNumpy as vnp",
            "from director.screen_recorder import capture_screenshot",
            "from director.script_context import fields",
            f"output_path = Path({output!r}).expanduser()",
            "output_path.parent.mkdir(parents=True, exist_ok=True)",
            f"render = {render!r}",
            "if render:",
            "    fields.view.forceRender()",
            "image = capture_screenshot(fields.view)",
            "ioUtils.writeImage(vnp.numpyToImageData(image), str(output_path))",
            "print(json.dumps({'path': str(output_path), 'shape': list(image.shape), 'dtype': str(image.dtype)}))",
        ]
    )


def _print_result(result):
    print(
        json.dumps(
            {
                "status": result.status,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "display_data": result.display_data,
                "error": result.error,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
