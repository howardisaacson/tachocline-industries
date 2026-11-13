"""Host identity for the local Compose stack (ADR 0029)."""

from __future__ import annotations

import os
import stat

import pytest

from ti_ingest.dev_identity import (
    IMAGE_GID,
    IMAGE_UID,
    ContainerPathError,
    ProcessIdentity,
    RootOwnedLandingZone,
    UnsupportedHost,
    choose_identity,
    compose_argv,
    container_data_dir,
    drop_privileges,
    identity_for_landing_zone,
    is_docker_desktop,
)

LINUX = "6.12.113-arch1-1"
LINUXKIT = "6.10.14-linuxkit"
DIR = stat.S_IFDIR | 0o755


def test_compose_command_is_sudo_only_on_linux() -> None:
    assert compose_argv("Darwin") == ["docker", "compose"]
    assert compose_argv("Linux") == ["sudo", "docker", "compose"]
    with pytest.raises(UnsupportedHost):
        compose_argv("Omarchy")


def test_linuxkit_marks_docker_desktop() -> None:
    assert is_docker_desktop(LINUXKIT)
    assert is_docker_desktop("6.12.0-LINUXKIT")
    assert not is_docker_desktop(LINUX)


def test_non_root_mount_owner_is_used_on_both_hosts() -> None:
    mac = choose_identity(mount_uid=501, mount_gid=20, kernel_release=LINUXKIT)
    linux = choose_identity(mount_uid=1000, mount_gid=1000, kernel_release=LINUX)
    other = choose_identity(mount_uid=1001, mount_gid=1001, kernel_release=LINUX)
    assert mac == ProcessIdentity(501, 20, "docker-desktop")
    assert linux == ProcessIdentity(1000, 1000, "linux")
    assert other == ProcessIdentity(1001, 1001, "linux")


def test_root_mount_on_linux_is_refused() -> None:
    with pytest.raises(RootOwnedLandingZone):
        choose_identity(mount_uid=0, mount_gid=0, kernel_release=LINUX)


def test_root_mount_on_docker_desktop_stays_root() -> None:
    assert choose_identity(
        mount_uid=0, mount_gid=0, kernel_release=LINUXKIT
    ) == ProcessIdentity(0, 0, "docker-desktop")


def test_container_path_accepts_the_mount_and_rejects_laptop_paths() -> None:
    assert container_data_dir("/data/raw") == "/data/raw"
    for raw in (
        "~/data/raw",
        "data/raw",
        "/Users/howard/data/raw",
        "/home/howard/Projects/tachocline-industries/data/raw",
        "$HOME/data/raw",
        " /data/raw",
        "",
    ):
        with pytest.raises(ContainerPathError):
            container_data_dir(raw)


def test_migrate_keeps_the_image_user_when_raw_dir_is_unset() -> None:
    assert identity_for_landing_zone(
        None,
        mount_uid=None,
        mount_gid=None,
        kernel_release=LINUX,
        is_dir=False,
        mode=None,
    ) == ProcessIdentity(IMAGE_UID, IMAGE_GID, "image-default")


def test_missing_or_read_only_landing_zone_is_an_error() -> None:
    with pytest.raises(ContainerPathError):
        identity_for_landing_zone(
            "/data/raw",
            mount_uid=None,
            mount_gid=None,
            kernel_release=LINUX,
            is_dir=False,
            mode=None,
        )
    with pytest.raises(ContainerPathError):
        identity_for_landing_zone(
            "/data/raw",
            mount_uid=1000,
            mount_gid=1000,
            kernel_release=LINUX,
            is_dir=True,
            mode=stat.S_IFDIR | 0o555,
        )


def test_landing_zone_identity_matches_the_directory_owner() -> None:
    assert identity_for_landing_zone(
        "/data/raw",
        mount_uid=501,
        mount_gid=20,
        kernel_release=LINUXKIT,
        is_dir=True,
        mode=DIR,
    ) == ProcessIdentity(501, 20, "docker-desktop")


def test_drop_privileges_is_a_noop_for_the_current_user() -> None:
    drop_privileges(os.geteuid(), os.getegid())


def test_drop_privileges_refuses_a_switch_when_not_root() -> None:
    if os.geteuid() == 0:
        pytest.skip("root can switch; this lock is for an unprivileged runner")
    with pytest.raises(SystemExit):
        drop_privileges(os.geteuid() + 1, os.getegid())
