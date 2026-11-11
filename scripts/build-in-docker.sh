#!/usr/bin/env bash
# Build Claudius inside a Debian 13 container, for hosts that aren't Debian
# (Ubuntu, Fedora, Arch, WSL2, macOS with Docker Desktop...).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec docker run --rm --privileged \
    -v "$ROOT":/claudius \
    -w /claudius \
    -e GITHUB_RUN_NUMBER="${GITHUB_RUN_NUMBER:-local}" \
    debian:trixie \
    bash -c "apt-get update -qq && apt-get install -y -qq rsync >/dev/null && ./build.sh"
