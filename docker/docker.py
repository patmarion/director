#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IMAGE_NAME = "director-env"
DEFAULT_TAG = "latest"
VOLUME_PREFIX = "director-storage"
DEFAULT_CONTAINER_PREFIX = "director"


@dataclass(frozen=True)
class ImageRef:
    name: str
    tag: str

    @property
    def full(self) -> str:
        return f"{self.name}:{self.tag}"


def _repo_root() -> Path:
    # This file lives in <repo>/docker/docker.py
    return Path(__file__).resolve().parent.parent


def _docker_dir() -> Path:
    return _repo_root() / "docker"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=check, text=True)


def _run_no_raise(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=False, text=True)


def _capture(cmd: list[str], *, check: bool = True) -> str:
    print(f"+ {shlex.join(cmd)}", flush=True)
    cp = subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE)
    return cp.stdout


def _is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _sanitize_volume_suffix(raw: str) -> str:
    # Docker volume names allow: [a-zA-Z0-9][a-zA-Z0-9_.-]
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw)
    safe = safe.lstrip("-._")
    return safe or "user"


def _volume_name(*, map_user: bool) -> str:
    if map_user:
        suffix = _sanitize_volume_suffix(_host_user())
    else:
        suffix = "root"
    return f"{VOLUME_PREFIX}-{suffix}"


def _ensure_volume_exists(name: str) -> None:
    cp = subprocess.run(["docker", "volume", "inspect", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode == 0:
        return
    _run(["docker", "volume", "create", name])


def _image_exists_locally(image_full: str) -> bool:
    cp = subprocess.run(
        ["docker", "image", "inspect", image_full],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return cp.returncode == 0


def _require_local_image(image_full: str) -> None:
    if _image_exists_locally(image_full):
        return
    raise SystemExit(
        "\n".join(
            [
                f"Image not found locally: {image_full}",
                f"Run: {shlex.quote(sys.argv[0])} build",
            ]
        )
    )


def _volume_exists(name: str) -> bool:
    cp = subprocess.run(["docker", "volume", "inspect", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cp.returncode == 0


def _containers_using_volume(volume_name: str) -> list[str]:
    out = _capture(["docker", "ps", "-a", "--filter", f"volume={volume_name}", "--format", "{{.ID}} {{.Names}}"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def _clean_volume(volume_name: str) -> None:
    if not _volume_exists(volume_name):
        _run(["docker", "volume", "create", volume_name])
        return

    cp = subprocess.run(["docker", "volume", "rm", volume_name], text=True)
    if cp.returncode == 0:
        _run(["docker", "volume", "create", volume_name])
        return

    holders = _containers_using_volume(volume_name)
    if holders:
        msg_lines = [
            f"Cannot remove volume {volume_name!r}; it is still used by container(s):",
            *[f"  - {h}" for h in holders],
            "",
            "Tip: run `./docker.py stop` (or remove those containers) and try again.",
        ]
        raise SystemExit("\n".join(msg_lines))

    raise SystemExit(f"Failed to remove volume {volume_name!r}.")


def _host_user() -> str:
    import getpass

    # getpass.getuser() handles non-TTY environments better than os.getlogin().
    return getpass.getuser()


def _host_uid() -> int:
    return os.getuid()


def _host_gid() -> int:
    return os.getgid()


def _xauthority_path() -> Path:
    xauth = os.environ.get("XAUTHORITY")
    if xauth:
        return Path(xauth).expanduser()
    return Path.home() / ".Xauthority"


def _host_group_gid(group_name: str) -> int | None:
    import grp

    try:
        return grp.getgrnam(group_name).gr_gid
    except KeyError:
        return None


def _gl_env(gl_mode: str) -> dict[str, str]:
    if gl_mode == "dri":
        return {}
    if gl_mode == "software":
        return {
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe",
        }
    if gl_mode == "indirect":
        return {"LIBGL_ALWAYS_INDIRECT": "1"}
    raise ValueError(f"Unknown gl mode: {gl_mode}")


def _dri_device_args() -> list[str]:
    dri_dir = Path("/dev/dri")
    if not dri_dir.is_dir():
        return []
    args: list[str] = []
    for child in sorted(dri_dir.iterdir()):
        try:
            mode = child.stat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISCHR(mode):
            args += ["--device", str(child)]
    return args


def _map_groups_env_for_dri() -> str:
    # We pass pairs like: "render:992,video:44"
    pairs: list[str] = []
    for name in ("render", "video"):
        gid = _host_group_gid(name)
        if gid is not None:
            pairs.append(f"{name}:{gid}")
    return ",".join(pairs)


def _bootstrap_script_path(*, work_dir: str) -> str:
    # We mount the repo root at work_dir (default: /workdir), so this path exists in the container.
    return f"{work_dir}/docker/user_bootstrap.sh"


def _container_name(*, name_arg: str | None, map_user: bool) -> str:
    if name_arg:
        return name_arg
    suffix = _sanitize_volume_suffix(_host_user()) if map_user else "root"
    return f"{DEFAULT_CONTAINER_PREFIX}-{suffix}"


def _container_exists(name: str) -> bool:
    cp = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"],
        text=True,
        stdout=subprocess.PIPE,
    )
    return name in cp.stdout.splitlines()


def _container_running(name: str) -> bool:
    cp = subprocess.run(
        ["docker", "ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"],
        text=True,
        stdout=subprocess.PIPE,
    )
    return name in cp.stdout.splitlines()


def _container_start(name: str) -> None:
    _run(["docker", "start", name])


def _container_stop(name: str) -> None:
    _run(["docker", "stop", name])


def _container_rm(name: str) -> None:
    _run(["docker", "rm", name])


def _container_inspect(name: str) -> dict:
    out = _capture(["docker", "inspect", name])
    data = json.loads(out)
    if not data:
        raise SystemExit(f"docker inspect returned no data for container: {name}")
    return data[0]


@dataclass(frozen=True)
class DesiredContainerConfig:
    image_full: str
    work_dir: str
    binds: tuple[str, ...]
    devices: tuple[str, ...]


def _desired_config(
    *,
    image: ImageRef,
    vol_name: str,
    container_home: str,
    work_dir: str,
    enable_x11: bool,
    xauth: Path | None,
    gl_mode: str,
) -> DesiredContainerConfig:
    binds = [
        f"{vol_name}:{container_home}",
        f"{str(_repo_root())}:{work_dir}",
    ]
    if enable_x11:
        binds.append("/tmp/.X11-unix:/tmp/.X11-unix:rw")
        if xauth is not None:
            binds.append(f"{str(xauth)}:{str(xauth)}:ro")

    devices: list[str] = []
    if gl_mode == "dri":
        devices = [arg for arg in _dri_device_args()[1::2]]  # every --device <path>

    return DesiredContainerConfig(
        image_full=image.full,
        work_dir=work_dir,
        binds=tuple(sorted(binds)),
        devices=tuple(sorted(devices)),
    )


def _existing_config(name: str) -> DesiredContainerConfig:
    info = _container_inspect(name)
    image_full = info.get("Config", {}).get("Image", "")
    work_dir = info.get("Config", {}).get("WorkingDir", "")
    binds = tuple(sorted(info.get("HostConfig", {}).get("Binds", []) or []))
    devices = info.get("HostConfig", {}).get("Devices", []) or []
    device_paths = tuple(sorted([d.get("PathOnHost", "") for d in devices if d.get("PathOnHost")]))
    return DesiredContainerConfig(image_full=image_full, work_dir=work_dir, binds=binds, devices=device_paths)


def _needs_recreate(name: str, desired: DesiredContainerConfig) -> bool:
    existing = _existing_config(name)
    return existing != desired


def cmd_build(args: argparse.Namespace) -> None:
    image = ImageRef(name=args.image_name, tag=args.tag)
    _run(["docker", "build", "-t", image.full, str(_docker_dir())])


def cmd_run(args: argparse.Namespace) -> None:
    image = ImageRef(name=args.image_name, tag=args.tag)

    map_user = not args.root
    enable_x11 = not args.headless
    gl_mode = args.gl
    persist = args.session
    clean_volume = args.clean_volume

    work_dir = args.work_dir
    if not work_dir.startswith("/"):
        raise SystemExit("--work-dir must be an absolute path inside the container (e.g. /workdir)")

    host_user = _host_user()
    host_uid = _host_uid()
    host_gid = _host_gid()

    container_home = f"/home/{host_user}" if map_user else "/root"
    uv_project_env = f"{container_home}/venv"

    vol_name = _volume_name(map_user=map_user)
    if clean_volume and persist:
        print("Warning: --clean-volume ignored when using --session (would disrupt an existing session).")

    if clean_volume and not persist:
        _clean_volume(vol_name)
    else:
        _ensure_volume_exists(vol_name)

    container_name = _container_name(name_arg=args.name, map_user=map_user) if persist else ""
    bootstrap_path = _bootstrap_script_path(work_dir=work_dir)

    base_run_args: list[str] = ["docker", "run"]

    base_run_args += ["--volume", f"{vol_name}:{container_home}"]
    base_run_args += ["--volume", f"{str(_repo_root())}:{work_dir}"]
    base_run_args += ["--workdir", work_dir]

    env = {
        "HOME": container_home,
        "UV_PROJECT_ENVIRONMENT": uv_project_env,
        "QT_X11_NO_MITSHM": "1",
        **_gl_env(gl_mode),
    }

    xauth: Path | None = None
    if enable_x11:
        display = os.environ.get("DISPLAY")
        if not display:
            raise SystemExit("--headless was not set, but DISPLAY is not set on the host")

        xauth = _xauthority_path()
        if not xauth.is_file():
            raise SystemExit(f"X11 requested but Xauthority file not found at: {xauth}")

        env["DISPLAY"] = display
        env["XAUTHORITY"] = str(xauth)
        base_run_args += ["--volume", "/tmp/.X11-unix:/tmp/.X11-unix:rw"]
        base_run_args += ["--volume", f"{str(xauth)}:{str(xauth)}:ro"]

    if gl_mode == "dri":
        base_run_args += _dri_device_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        command = ["bash"]

    if map_user:
        env |= {
            "HOST_UID": str(host_uid),
            "HOST_GID": str(host_gid),
            "HOST_USER": host_user,
            "HOST_HOME": container_home,
            "EXTRA_GROUPS": _map_groups_env_for_dri() if gl_mode == "dri" else "",
        }

    # Always set env on container creation / ephemeral run.
    for k, v in env.items():
        base_run_args += ["--env", f"{k}={v}"]

    if persist:
        desired = _desired_config(
            image=image,
            vol_name=vol_name,
            container_home=container_home,
            work_dir=work_dir,
            enable_x11=enable_x11,
            xauth=xauth,
            gl_mode=gl_mode,
        )

        if not _container_exists(container_name):
            _require_local_image(image.full)
            create_args = ["docker", "run", "--detach", "--name", container_name, "--restart", "unless-stopped"]
            create_args += base_run_args[2:]  # drop initial ["docker","run"]

            if map_user:
                create_cmd = create_args + [image.full, "bash", bootstrap_path, "sleep", "infinity"]
            else:
                create_cmd = create_args + [image.full, "sleep", "infinity"]

            _run(create_cmd)
        else:
            if _needs_recreate(container_name, desired):
                _require_local_image(image.full)
                if _container_running(container_name):
                    _container_stop(container_name)
                _container_rm(container_name)

                create_args = ["docker", "run", "--detach", "--name", container_name, "--restart", "unless-stopped"]
                create_args += base_run_args[2:]

                if map_user:
                    create_cmd = create_args + [image.full, "bash", bootstrap_path, "sleep", "infinity"]
                else:
                    create_cmd = create_args + [image.full, "sleep", "infinity"]
                _run(create_cmd)

        if not _container_running(container_name):
            _container_start(container_name)

        exec_args = ["docker", "exec"]
        exec_args += ["-it"] if _is_tty() else ["-i"]
        exec_args += ["--workdir", work_dir]
        if map_user:
            # Exec as root and run the bootstrap each time; it is idempotent and avoids races.
            for k, v in env.items():
                exec_args += ["--env", f"{k}={v}"]
            cp = _run_no_raise(exec_args + [container_name, "bash", bootstrap_path] + command)
        else:
            cp = _run_no_raise(exec_args + ["--env", "HOME=/root", container_name] + command)

        if cp.returncode != 0:
            print(f"Docker container exited with code: {cp.returncode}", file=sys.stderr)
            raise SystemExit(cp.returncode)
        return

    # Ephemeral run that exits when the command exits.
    _require_local_image(image.full)
    run_args = ["docker", "run", "--rm", "--init"]
    run_args += ["-it"] if _is_tty() else ["-i"]
    run_args += base_run_args[2:]  # drop initial ["docker","run"]

    if map_user:
        cp = _run_no_raise(run_args + [image.full, "bash", bootstrap_path] + command)
    else:
        cp = _run_no_raise(run_args + [image.full] + command)

    if cp.returncode != 0:
        print(f"Docker container exited with code: {cp.returncode}", file=sys.stderr)
        raise SystemExit(cp.returncode)


def cmd_remove_volumes(_: argparse.Namespace) -> None:
    out = _capture(["docker", "volume", "ls", "--format", "{{.Name}}"])
    names = [line.strip() for line in out.splitlines() if line.strip()]
    to_delete = [n for n in names if n.startswith(f"{VOLUME_PREFIX}-")]

    if not to_delete:
        print(f"No volumes found matching: {VOLUME_PREFIX}-*")
        return

    print("Deleting volumes:")
    for v in to_delete:
        print(f"  - {v}")

    _run(["docker", "volume", "rm", *to_delete])


def cmd_stop(args: argparse.Namespace) -> None:
    image = ImageRef(name=args.image_name, tag=args.tag)
    out = _capture(
        ["docker", "ps", "-a", "--filter", f"ancestor={image.full}", "--format", "{{.ID}} {{.Names}} {{.Status}}"]
    )
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if not lines:
        print(f"No containers found for image: {image.full}")
        return

    container_ids: list[str] = []
    running_ids: list[str] = []
    print("Stopping/removing containers:")
    for line in lines:
        container_id = line.split(" ", 1)[0]
        container_ids.append(container_id)
        # docker status string starts with "Up" for running containers.
        if " Up " in f" {line} ":
            running_ids.append(container_id)
        print(f"  - {line}")

    if running_ids:
        _run(["docker", "stop", *running_ids])
    _run(["docker", "rm", *container_ids])

    # Best-effort: remove the image too (helps ensure nothing is held indirectly).
    subprocess.run(["docker", "image", "rm", image.full], text=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Build the docker image")
    p_build.add_argument("--image-name", default=DEFAULT_IMAGE_NAME)
    p_build.add_argument("--tag", default=DEFAULT_TAG)
    p_build.set_defaults(func=cmd_build)

    p_run = sub.add_parser("run", help="Run the docker container")
    p_run.add_argument("--image-name", default=DEFAULT_IMAGE_NAME)
    p_run.add_argument("--tag", default=DEFAULT_TAG)
    p_run.add_argument("--work-dir", default="/workdir", help="Container workdir/mount point (absolute path)")

    p_run.add_argument("--root", action="store_true", help="Run as root (do not map user)")
    p_run.add_argument("--headless", action="store_true", help="Do not forward X11")
    p_run.add_argument(
        "--session",
        action="store_true",
        help="Reuse a named, persistent container session (default: ephemeral --rm container).",
    )
    p_run.add_argument(
        "--clean-volume",
        action="store_true",
        help="Delete and recreate the volume before running (ignored with --session).",
    )
    p_run.add_argument(
        "--name",
        help="Session container name to use/reuse (default: director-<user>|director-root). Only applies with --session.",
    )
    p_run.add_argument(
        "--gl",
        choices=["dri", "software", "indirect"],
        default="dri",
        help="OpenGL mode: dri (default), software, or indirect",
    )
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="Command to run (default: bash)")
    p_run.set_defaults(func=cmd_run)

    p_rm = sub.add_parser("remove-volumes", help="Remove docker volumes used by this project")
    p_rm.set_defaults(func=cmd_remove_volumes)

    p_stop = sub.add_parser("stop", help="Stop running containers for a given image:tag")
    p_stop.add_argument("--image-name", default=DEFAULT_IMAGE_NAME)
    p_stop.add_argument("--tag", default=DEFAULT_TAG)
    p_stop.set_defaults(func=cmd_stop)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
