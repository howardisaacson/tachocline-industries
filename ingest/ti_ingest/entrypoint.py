"""Container entrypoint for the migrate and ingest image.

Starts as root, chooses a uid, then ``exec``s the real command so signals
go to that process. Ingest sets ``RAW_DATA_DIR``. Migrate does not, and
keeps the image's ``app`` user.

https://docs.python.org/3/library/os.html#os.setuid
"""

from __future__ import annotations

import os
import sys

from ti_ingest.dev_identity import (
    ContainerPathError,
    RootOwnedLandingZone,
    container_data_dir,
    drop_privileges,
    identity_for_landing_zone,
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("entrypoint needs the command to run")
    raw = os.environ.get("RAW_DATA_DIR")
    mount_uid = None
    mount_gid = None
    mode = None
    is_dir = False
    if raw is not None:
        try:
            # Validate the shape before stat, so a laptop path fails
            # even when a same-named directory happens to exist.
            path = container_data_dir(raw)
        except ContainerPathError as exc:
            raise SystemExit(str(exc)) from exc
        is_dir = os.path.isdir(path)
        if is_dir:
            st = os.stat(path)
            mount_uid = st.st_uid
            mount_gid = st.st_gid
            mode = st.st_mode
    try:
        identity = identity_for_landing_zone(
            raw,
            mount_uid=mount_uid,
            mount_gid=mount_gid,
            kernel_release=os.uname().release,
            is_dir=is_dir,
            mode=mode,
        )
    except (ContainerPathError, RootOwnedLandingZone) as exc:
        raise SystemExit(str(exc)) from exc
    sys.stderr.write(
        f"dev identity host={identity.host} uid={identity.uid} gid={identity.gid}\n"
    )
    drop_privileges(identity.uid, identity.gid)
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
