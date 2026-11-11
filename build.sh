#!/usr/bin/env bash
# =============================================================================
#  Claudius ISO builder
#
#  Builds a bootable hybrid ISO (BIOS and UEFI) with Debian's live-build.
#  Run it as root on Debian 13 (trixie), or use the Docker wrapper:
#
#      sudo ./build.sh                 # on a Debian 13 machine
#      ./scripts/build-in-docker.sh    # anywhere Docker runs
#
#  The ISO is written to ./out/
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=claudius.conf
. "$ROOT/claudius.conf"

WORK="${WORK:-$ROOT/work}"
OUT="${OUT:-$ROOT/out}"
ISO_NAME="claudius-${CLAUDIUS_VERSION}-amd64.iso"

log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "build.sh must run as root (try: sudo ./build.sh)"; exit 1; }

# -----------------------------------------------------------------------------
log "Installing build dependencies"
# -----------------------------------------------------------------------------
if [ "${SKIP_DEPS:-0}" != "1" ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        live-build debootstrap squashfs-tools xorriso \
        grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed shim-signed mtools dosfstools \
        syslinux syslinux-common isolinux librsvg2-bin \
        rsync ca-certificates cpio zstd xz-utils
fi

# -----------------------------------------------------------------------------
log "Preparing a clean work directory: $WORK"
# -----------------------------------------------------------------------------
if [ -d "$WORK" ]; then (cd "$WORK" && lb clean --purge >/dev/null 2>&1 || true); fi
rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"
cd "$WORK"

BOOT_APPEND="boot=live components quiet splash noeject \
username=${CLAUDIUS_LIVE_USER} hostname=claudius \
live-config.noautologin locales=en_US.UTF-8 keyboard-layouts=us"

log "Configuring live-build"
lb config \
    --mode debian \
    --system live \
    --distribution "$CLAUDIUS_DEBIAN_SUITE" \
    --archive-areas "main contrib non-free-firmware" \
    --mirror-bootstrap "http://deb.debian.org/debian/" \
    --mirror-binary "http://deb.debian.org/debian/" \
    --mirror-binary-security "http://security.debian.org/debian-security/" \
    --security true \
    --updates true \
    --linux-flavours amd64 \
    --apt-recommends true \
    --debian-installer none \
    --binary-images iso-hybrid \
    --uefi-secure-boot disable \
    --memtest none \
    --firmware-binary false \
    --firmware-chroot false \
    --chroot-squashfs-compression-type xz \
    --iso-application "$CLAUDIUS_NAME" \
    --iso-publisher "Claudius Project; $CLAUDIUS_URL" \
    --iso-volume "CLAUDIUS_${CLAUDIUS_VERSION//./_}" \
    --image-name "claudius-${CLAUDIUS_VERSION}-amd64" \
    --bootappend-live "$BOOT_APPEND"

# -----------------------------------------------------------------------------
log "Adding the Claudius configuration overlay"
# -----------------------------------------------------------------------------
rsync -a "$ROOT/config/" "$WORK/config/"

# Release file read by hooks and tools inside the OS
mkdir -p config/includes.chroot/etc
cat > config/includes.chroot/etc/claudius-release <<EOF
CLAUDIUS_NAME="$CLAUDIUS_NAME"
CLAUDIUS_VERSION="$CLAUDIUS_VERSION"
CLAUDIUS_CODENAME="$CLAUDIUS_CODENAME"
CLAUDIUS_URL="$CLAUDIUS_URL"
CLAUDIUS_BUILD_DATE="$(date -u +%Y-%m-%d)"
CLAUDIUS_BUILD_ID="${GITHUB_RUN_NUMBER:-local}"
EOF

# Artwork: copy the rendered PNGs into the OS image
"$ROOT/scripts/install-artwork.sh" "$ROOT/branding/png" "$WORK/config/includes.chroot"

# Boot menus: copy live-build's templates and brand them
"$ROOT/scripts/brand-bootloaders.sh" "$ROOT/branding/png" "$WORK/config"

# Drop packages that don't exist in this Debian release, so one typo can't kill a build
"$ROOT/scripts/check-packages.sh" "$CLAUDIUS_DEBIAN_SUITE" config/package-lists/*.list.chroot

# -----------------------------------------------------------------------------
log "Building (this takes a while)"
# -----------------------------------------------------------------------------
lb build 2>&1 | tee "$OUT/build.log"

ISO_SRC="$(ls -1 "$WORK"/*.iso 2>/dev/null | head -n1 || true)"
if [ -z "$ISO_SRC" ]; then
    echo "Build failed: no ISO produced. See $OUT/build.log"
    exit 1
fi

mv "$ISO_SRC" "$OUT/$ISO_NAME"
(cd "$OUT" && sha256sum "$ISO_NAME" > "$ISO_NAME.sha256")
[ -f "$WORK/chroot.packages.live" ] && cp "$WORK/chroot.packages.live" "$OUT/packages.txt" || true

log "Done: $OUT/$ISO_NAME ($(du -h "$OUT/$ISO_NAME" | cut -f1))"
