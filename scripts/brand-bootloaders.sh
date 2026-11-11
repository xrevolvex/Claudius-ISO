#!/usr/bin/env bash
# Copy live-build's boot menu templates (ISOLINUX for BIOS, GRUB for UEFI)
# into config/bootloaders and give them the Claudius look and labels.
#   brand-bootloaders.sh <branding/png dir> <live-build config dir>
set -euo pipefail
PNG="$1"
CFG="$2"
SRC=/usr/share/live/build/bootloaders
DST="$CFG/bootloaders"
mkdir -p "$DST"

for d in syslinux_common isolinux grub-pc; do
    if [ -d "$SRC/$d" ]; then
        cp -a "$SRC/$d" "$DST/"
    fi
done

echo "--- bootloader templates in use:"
find "$DST" -type f | sort

# ---- splash images ---------------------------------------------------------
make_svg_wrapper() {  # embed a PNG in an SVG for templates that render splash.svg.in
    local png="$1" w="$2" h="$3"
    printf '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="%s" height="%s"><image width="%s" height="%s" xlink:href="data:image/png;base64,%s"/></svg>\n' \
        "$w" "$h" "$w" "$h" "$(base64 -w0 "$png")"
}
for d in syslinux_common isolinux; do
    [ -d "$DST/$d" ] || continue
    cp "$PNG/splash-640x480.png" "$DST/$d/splash.png"
    if [ -f "$DST/$d/splash.svg.in" ]; then
        make_svg_wrapper "$PNG/splash-640x480.png" 640 480 > "$DST/$d/splash.svg.in"
    fi
done
if [ -d "$DST/grub-pc" ]; then
    cp "$PNG/splash-1024x768.png" "$DST/grub-pc/splash.png"
    find "$DST/grub-pc" -name 'splash.png' -exec cp "$PNG/splash-1024x768.png" {} \;
    if [ -f "$DST/grub-pc/splash.svg.in" ]; then
        make_svg_wrapper "$PNG/splash-1024x768.png" 1024 768 > "$DST/grub-pc/splash.svg.in"
    fi
fi

# ---- menu labels -------------------------------------------------------------
find "$DST" -type f \( -name '*.cfg' -o -name '*.cfg.in' -o -name '*.txt' \) -print0 |
    xargs -0 -r sed -i \
        -e 's/Live system/Start Claudius/g' \
        -e 's/Debian GNU\/Linux/Claudius/g' \
        -e 's/Debian Live/Claudius/g'

# ---- extra entry: copy the whole system into RAM (fastest with 4 GB or more) --
TORAM_LABEL='Start Claudius in RAM (fastest, needs 4 GB+)'
for f in $(grep -rl '@APPEND_LIVE@' "$DST" 2>/dev/null); do
    # ISOLINUX:  label live-@FLAVOUR@ ... append @APPEND_LIVE@
    TORAM_LABEL="$TORAM_LABEL" perl -0pi -e '
        if (/(^label live-\@FLAVOUR\@\n(?:[ \t]+[^\n]*\n)+)/m && !/toram/) {
            my $b = $1; my $t = $b;
            $t =~ s/label live-\@FLAVOUR\@/label live-\@FLAVOUR\@-toram/;
            $t =~ s/menu label [^\n]*/menu label ^$ENV{TORAM_LABEL}/;
            $t =~ s/^[ \t]*menu default\n//m;
            $t =~ s/\@APPEND_LIVE\@/\@APPEND_LIVE\@ toram/;
            s/\Q$b\E/$b\n$t/;
        }' "$f"
    # GRUB:  menuentry "..." { linux ... @APPEND_LIVE@ ... }
    TORAM_LABEL="$TORAM_LABEL" perl -0pi -e '
        if (/(menuentry "[^"]*\(\@FLAVOUR\@\)"[^\n]*\{\n.*?\n\}\n)/s && !/toram/) {
            my $b = $1; my $t = $b;
            $t =~ s/menuentry "[^"]*"/menuentry "$ENV{TORAM_LABEL}"/;
            $t =~ s/--hotkey=\S+//;
            $t =~ s/\@APPEND_LIVE\@/\@APPEND_LIVE\@ toram/;
            s/\Q$b\E/$b$t/;
        }' "$f"
done

# ---- shorter timeouts so VMs boot by themselves ---------------------------------
for f in "$DST"/isolinux/isolinux.cfg "$DST"/syslinux_common/*.cfg; do
    [ -f "$f" ] && sed -i 's/^timeout .*/timeout 50/I' "$f"
done
if [ -d "$DST/grub-pc" ]; then
    if grep -rqs 'set timeout=' "$DST/grub-pc"; then
        grep -rl 'set timeout=' "$DST/grub-pc" | xargs sed -i 's/set timeout=.*/set timeout=5/'
    else
        printf '\nset timeout=5\n' >> "$DST/grub-pc/config.cfg"
    fi
fi

echo "--- branded menu entries:"
grep -rh -E 'menu label|menuentry' "$DST" 2>/dev/null | head -20 || true
echo "--- isolinux.cfg:"; cat "$DST/isolinux/isolinux.cfg" 2>/dev/null || true
echo "--- grub config.cfg/theme:"; cat "$DST/grub-pc/config.cfg" "$DST/grub-pc/theme.cfg" 2>/dev/null || true
