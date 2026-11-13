# 0029. Match the ingest user to the host inside one Compose file

- **Status:** Proposed
- **Date:** 2026-11-13
- **Deciders:** Howard Isaacson

## Context
Howard develops on a Mac (Docker Desktop, Apple Silicon or Intel, no sudo) and on Omarchy Linux (the Docker daemon is started with sudo). [ADR 0002](0002-build-locally-first-with-docker-compose.md) says one `docker compose up` starts the stack. [ADR 0014](0014-when-to-use-more-than-one-docker-container.md) says the database data lives in a named volume. The landing zone is the exception: `ingest` bind-mounts `./data/raw` at `/data/raw` and writes the raw files there ([ADR 0004](0004-python-scheduled-pollers-with-raw-landing-zone.md)).

The image used to `useradd` uid 1000 and run as that user. That matches a common Linux account and misses a Mac account (often uid 501). When the mount enforces the host uid, the poller cannot create files. Putting a host path or a tilde in `RAW_DATA_DIR` does not fix it: that variable is read inside the container, and Compose only mounts `/data/raw`.

A container cannot see Darwin. `uname` inside it is always Linux. Docker Desktop's VM kernel release contains `linuxkit`. Omarchy's kernel does not. `sudo docker compose` runs as root, so the client uid is not the laptop user. The mount's owner still is.

Cloud hosting, including AWS, stays deferred ([ADR 0011](0011-cloud-deployment-target-deferred-with-criteria.md)). This ADR is only the local dev stack.

## Options considered
### A. Keep uid 1000 in the image
- Pros: one line; works when the laptop user happens to be 1000.
- Cons: fails when the user is not 1000; Howard would edit the uid by hand on one of the machines.
### B. A second Compose file per OS
- Pros: each file can hard-code a `user:` and a `platform:`.
- Cons: two files to remember; the default command diverges; easy to start the wrong one.
### C. An env var Howard sets to his uid
- Pros: explicit.
- Cons: another value to edit per machine. `sudo` on Omarchy does not pass his uid unless he remembers extra flags.
### D. One Compose file; the entrypoint reads the mount owner
- Pros: `docker compose up` on the Mac and `sudo docker compose up` on Omarchy need no uid, path, or architecture edit. The same file is the default on both.
- Cons: the entrypoint starts as root so it can `setuid`. Someone has to understand LinuxKit versus a native kernel.

## Decision
Use option D.

- One `docker-compose.yml`. No `platform:` key and no `user:` on `ingest`.
- `ingest` and `migrate` share an entrypoint. It starts as root, then replaces itself with the real command.
- When `RAW_DATA_DIR` is set, the process uid and gid are the owner of that directory. A non-zero owner is used on both machines.
- When the kernel release contains `linuxkit` and the mount looks like root, the process stays root. That is Docker Desktop's VirtioFS mapping: the Desktop file server creates the host files as the Mac user.
- When the kernel is not LinuxKit and the mount is root, the container exits. Writing as root on Omarchy would leave root-owned files. sudo does not change who owns `data/raw`. The clone keeps `data/raw/.gitkeep` so the directory exists and belongs to the user who cloned.
- When `RAW_DATA_DIR` is unset (the migrate service), the process is the image user `app` (uid 1000). Migrate does not write the landing zone.
- `RAW_DATA_DIR` must be an absolute container path. A tilde, a relative path, or a path under `/Users` or `/home` is rejected.
- `api` has no writable host mount, so it keeps uid 1000. Grafana and Postgres write named volumes (`grafana_data`, `pgdata`), not a checkout folder.
- The Mac command is `docker compose`. The Omarchy command is `sudo docker compose`. That difference is stated in the README quick start. `scripts/dev-compose` runs the matching one. This does not add the user to a Docker group and does not switch the daemon to rootless.
- Pulled images must publish `linux/amd64` and `linux/arm64`, so Apple Silicon, Intel, and Omarchy each run a native image. Checked 2026-11-13: `timescale/timescaledb:2.31.0-pg17-oss`, `grafana/grafana:13.2.4`, `python:3.12-slim-bookworm`, `node:22.23.4-alpine`, and `nginx:1.27-alpine` all do. Our own images are built on the machine that runs them. They are not published as a multi-arch manifest.

## Consequences
- Easier: a clean clone starts on either laptop without editing ids, paths, or tags.
- Harder: the first thing the ingest image does is choose a uid. A future Docker Desktop that drops the `linuxkit` kernel string would treat a 0:0 mount as the Linux error. The fix is that one string match.
- Database files stay in the named volumes `pgdata` and `grafana_data`.
- This does not deploy the stack. AWS is still a later decision.

## How to explain this in an interview
"The container is Linux even on my Mac, so I don't ask `uname` for Darwin. Docker Desktop's kernel says `linuxkit`. The poller writes a bind-mounted data directory, so it setuids to that directory's owner instead of a hardcoded 1000. On Omarchy I start Docker with sudo, which would look like root, but the mount is still owned by my user. I kept one Compose file and I didn't pin amd64, because the base images publish both architectures."

## Learn more
- Docker docs, [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- Docker docs, [Multi-platform images](https://docs.docker.com/build/building/multi-platform/)
- Docker docs, [Change your Docker Desktop settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/) (file sharing runs as the Desktop user)
- Python docs, [`os.setuid`](https://docs.python.org/3/library/os.html#os.setuid)
- LinuxKit, [project page](https://github.com/linuxkit/linuxkit) (the kernel Docker Desktop's VM boots)
