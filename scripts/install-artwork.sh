#!/usr/bin/env bash
# Copy the rendered Claudius artwork into the chroot overlay.
#   install-artwork.sh <branding/png dir> <config/includes.chroot dir>
set -euo pipefail
PNG="$1"
DEST="$2"
SVG="$(dirname "$PNG")/svg"

install -d "$DEST/usr/share/claudius/wallpapers" "$DEST/usr/share/claudius/logo" \
           "$DEST/usr/share/backgrounds/claudius" "$DEST/usr/share/pixmaps"

install -m644 "$PNG/claudius-wallpaper-1920x1080.png" "$DEST/usr/share/claudius/wallpapers/claudius-default.png"
install -m644 "$PNG/claudius-wallpaper-2560x1440.png" "$DEST/usr/share/claudius/wallpapers/claudius-default-2560.png"
install -m644 "$PNG/claudius-login-1920x1080.png"     "$DEST/usr/share/claudius/wallpapers/claudius-login.png"
ln -sf /usr/share/claudius/wallpapers/claudius-default.png "$DEST/usr/share/backgrounds/claudius/default.png"
# accent wallpaper pack (Claudius Center > Appearance)
for f in "$PNG"/wallpapers/claudius-*.png; do
    [ -f "$f" ] && install -m644 "$f" "$DEST/usr/share/claudius/wallpapers/$(basename "$f")"
done

install -m644 "$PNG/claudius-logo-256.png"   "$DEST/usr/share/claudius/logo/claudius-logo.png"
install -m644 "$PNG/claudius-avatar-96.png"  "$DEST/usr/share/claudius/logo/claudius-avatar.png"
install -m644 "$PNG/installer-welcome.png"   "$DEST/usr/share/claudius/logo/installer-welcome.png"
install -m644 "$SVG/claudius-logo.svg"       "$DEST/usr/share/claudius/logo/claudius-logo.svg"
install -m644 "$SVG/claudius-icon.svg"       "$DEST/usr/share/claudius/logo/claudius-icon.svg"
install -m644 "$PNG/icon-256.png"            "$DEST/usr/share/pixmaps/claudius.png"

# hicolor icon theme: "claudius" is used by the menu button, the welcome app and the installer
for s in 16 22 24 32 48 64 128 256; do
    install -d "$DEST/usr/share/icons/hicolor/${s}x${s}/apps"
    install -m644 "$PNG/icon-$s.png" "$DEST/usr/share/icons/hicolor/${s}x${s}/apps/claudius.png"
    install -m644 "$PNG/icon-$s.png" "$DEST/usr/share/icons/hicolor/${s}x${s}/apps/claudius-install.png"
done
install -d "$DEST/usr/share/icons/hicolor/scalable/apps"
install -m644 "$SVG/claudius-icon.svg" "$DEST/usr/share/icons/hicolor/scalable/apps/claudius.svg"

# Boot animation (Plymouth): frame-0.png ... frame-127.png, plus the version tag
T="$DEST/usr/share/plymouth/themes/claudius"
install -d "$T"
i=0
for f in $(ls "$PNG"/anim/frame-*.png | sort); do
    install -m644 "$f" "$T/frame-$i.png"; i=$((i + 1))
done
install -m644 "$PNG/version-tag.png" "$T/version-tag.png"
install -m644 "$PNG/version-tag.png" "$DEST/usr/share/claudius/logo/version-tag.png"
# Geometry shared by the login screen and the desktop splash
install -m644 "$PNG/geometry.json" "$DEST/usr/share/claudius/geometry.json"
echo "boot animation: $i frames"

# Installer (Calamares) branding images
B="$DEST/etc/calamares/branding/claudius"
install -d "$B"
install -m644 "$PNG/icon-128.png"          "$B/logo.png"
install -m644 "$PNG/icon-64.png"           "$B/icon.png"
install -m644 "$PNG/installer-welcome.png" "$B/welcome.png"

# GRUB background for the installed system
install -d "$DEST/usr/share/claudius/boot"
install -m644 "$PNG/splash-1024x768.png" "$DEST/usr/share/claudius/boot/grub-background.png"

echo "artwork installed"
