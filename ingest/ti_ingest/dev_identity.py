"""Choose the ingest uid and the host Compose command.

The container's ``uname`` is always Linux, including on a Mac. Docker
Desktop's kernel release contains ``linuxkit``. A native Linux daemon
(Omarchy) does not. File ownership is read from the landing-zone mount,
because ``sudo docker compose`` runs as root and would hide the laptop
user's id.

``RAW_DATA_DIR`` is a path inside the container. Compose mounts the
clone's ``./data/raw`` at ``/data/raw``. A tilde or a ``/Users`` or
``/home`` path is the laptop path, and that folder is not the mount.
"""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass

# Migrate does not mount the landing zone. It keeps the account created
# in the image. Ingest replaces these numbers with the mount owner.
IMAGE_UID = 1000
IMAGE_GID = 1000
APP_USER = "app"
LINUXKIT_MARK = "linuxkit"


class ContainerPathError(ValueError):
    """``RAW_DATA_DIR`` is not a path inside the container."""


class RootOwnedLandingZone(RuntimeError):
    """The landing zone is owned by root on a native Linux daemon.

    sudo starts Docker. It does not change who owns ``data/raw``. The
    ingest process must not create root-owned files there.
    """


class UnsupportedHost(RuntimeError):
    """``uname -s`` is neither Darwin nor Linux."""

    def __init__(self, sysname: str) -> None:
        self.sysname = sysname
        super().__init__(
            f"uname {sysname!r} is not a TI dev machine. "
            "Darwin uses Docker Desktop. Linux uses sudo docker compose."
        )


@dataclass(frozen=True)
class ProcessIdentity:
    """Who the ingest or migrate process should run as.

    ``host`` is ``linux``, ``docker-desktop``, or ``image-default``.
    ``image-default`` means there is no landing-zone mount (migrate).
    """

    uid: int
    gid: int
    host: str


def is_docker_desktop(kernel_release: str) -> bool:
    """True when this container is Docker Desktop's LinuxKit VM.

    That VM is how Docker Desktop runs Linux containers on macOS.
    The string is the kernel release (``os.uname().release``), not the
    host's ``uname -s``.
    """
    return LINUXKIT_MARK in kernel_release.lower()


def compose_argv(sysname: str) -> list[str]:
    """The docker compose command for this host, without a subcommand.

    macOS uses Docker Desktop, so the socket does not need sudo.
    On Omarchy the socket is root-owned, so the command is sudo.
    This does not change group membership.
    """
    if sysname == "Darwin":
        return ["docker", "compose"]
    if sysname == "Linux":
        return ["sudo", "docker", "compose"]
    raise UnsupportedHost(sysname)


def container_data_dir(raw: str) -> str:
    """Return ``raw`` when it is an absolute path inside the container."""
    if raw == "" or raw != raw.strip() or "~" in raw or raw.startswith("$"):
        raise ContainerPathError(
            "RAW_DATA_DIR must be the container path /data/raw. "
            "A blank, a tilde, or a shell variable is a laptop path, "
            "and that folder is not mounted in the container."
        )
    if not raw.startswith("/"):
        raise ContainerPathError(
            "RAW_DATA_DIR must be an absolute path inside the container. "
            f"Use /data/raw. Got {raw!r}."
        )
    if raw in {"/home", "/Users"} or raw.startswith(("/home/", "/Users/")):
        raise ContainerPathError(
            "RAW_DATA_DIR is the path inside the container. "
            f"{raw!r} is a laptop home directory. Use /data/raw, "
            "where Compose mounts the clone's data/raw."
        )
    return raw


def choose_identity(
    *,
    mount_uid: int,
    mount_gid: int,
    kernel_release: str,
) -> ProcessIdentity:
    """Pick the process ids from the landing-zone owner.

    A non-zero owner is used on both machines. That is Howard's uid
    (often 501 on a Mac, often 1000 on Linux). Docker Desktop sometimes
    reports the mount as 0:0; the Desktop file server still creates host
    files as the Mac user, so the process stays root only in that case.
    A 0:0 mount on native Linux is refused.
    """
    if mount_uid < 0 or mount_gid < 0:
        raise ValueError("uid and gid must be >= 0")
    desktop = is_docker_desktop(kernel_release)
    if mount_uid != 0:
        host = "docker-desktop" if desktop else "linux"
        return ProcessIdentity(mount_uid, mount_gid, host)
    if desktop:
        return ProcessIdentity(0, 0, "docker-desktop")
    raise RootOwnedLandingZone(
        "The landing zone is owned by uid 0. On this Linux daemon the "
        "ingest process would create root-owned files. data/raw should "
        "be owned by the user who cloned the repo. Starting Docker with "
        "sudo does not change that owner. RAW_DATA_DIR stays /data/raw."
    )


def identity_for_landing_zone(
    raw: str | None,
    *,
    mount_uid: int | None,
    mount_gid: int | None,
    kernel_release: str,
    is_dir: bool,
    mode: int | None,
) -> ProcessIdentity:
    """Decide the process identity from env and a stat of the mount.

    ``raw is None`` is the migrate container: it has no landing zone.
    """
    if raw is None:
        return ProcessIdentity(IMAGE_UID, IMAGE_GID, "image-default")
    container_data_dir(raw)
    if not is_dir:
        raise ContainerPathError(
            f"{raw} is not a directory inside the container. "
            "Compose mounts ./data/raw at /data/raw. Keep data/raw/.gitkeep "
            "so the clone contains that directory."
        )
    if mount_uid is None or mount_gid is None or mode is None:
        raise ContainerPathError(f"{raw} has no owner. It is not a usable mount.")
    identity = choose_identity(
        mount_uid=mount_uid,
        mount_gid=mount_gid,
        kernel_release=kernel_release,
    )
    if not (stat.S_IMODE(mode) & stat.S_IWUSR):
        raise ContainerPathError(
            f"{raw} is not writable by its owner (mode {stat.S_IMODE(mode):o})."
        )
    return identity


def drop_privileges(uid: int, gid: int) -> None:
    """Become ``uid``:``gid``. No-op when this process already is.

    The entrypoint starts as root so it can call ``setuid``. A non-root
    process cannot switch users. Staying root is only for the Docker
    Desktop 0:0 case, where ``uid`` is 0.
    """
    if os.geteuid() == uid and os.getegid() == gid:
        return
    if os.geteuid() != 0:
        raise SystemExit(
            f"cannot switch to uid {uid}: the entrypoint is uid {os.geteuid()}"
        )
    if uid == 0:
        return
    _align_app_account(uid, gid)
    os.initgroups(APP_USER, gid)
    os.setgid(gid)
    os.setuid(uid)
    if os.geteuid() != uid:
        raise SystemExit(f"still uid {os.geteuid()} after setuid({uid})")


def _align_app_account(uid: int, gid: int) -> None:
    """Point the image's ``app`` account at the host ids.

    Python's ``getpass.getuser`` looks up the uid in ``/etc/passwd``.
    A numeric ``setuid`` with no passwd row raises KeyError later.
    """
    import grp

    try:
        grp.getgrgid(gid)
    except KeyError:
        _run(["groupadd", "--gid", str(gid), "hostgrp"])
    _run(
        [
            "usermod",
            "--uid",
            str(uid),
            "--gid",
            str(gid),
            "--non-unique",
            APP_USER,
        ]
    )


def _run(argv: list[str]) -> None:
    result = subprocess.run(argv, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"{' '.join(argv)} failed ({result.returncode}): {detail}")
