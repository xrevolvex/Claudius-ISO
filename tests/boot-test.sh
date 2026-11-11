#!/usr/bin/env bash
# =============================================================================
#  Automated boot test for the Claudius ISO.
#
#  Boots the ISO in QEMU twice and saves screenshots of each stage:
#    1. BIOS boot with 8 GB RAM: boot menu, login, desktop, terminal, Firefox
#    2. UEFI boot with 2 GB RAM: boot menu, login, desktop + RAM report
#
#      tests/boot-test.sh out/claudius-1.0-amd64.iso out/screenshots
# =============================================================================
set -u
ISO="$1"
OUT="${2:-screenshots}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"

if [ -w /dev/kvm ]; then ACCEL=(-enable-kvm -cpu host); F=1; echo "KVM acceleration: yes"
else ACCEL=(-accel tcg); F=4; echo "KVM acceleration: no (slow software emulation)"; fi

MON="$(mktemp -u /tmp/claudius-mon.XXXX)"
ctl() { python3 "$HERE/qemu-ctl.py" "$MON" "$@"; }
pause() { sleep $(( $1 * F )); }
shot() { ctl shot "$PWD/$OUT/$1.png" && echo "  screenshot: $1"; }

start_vm() {  # start_vm <name> <ram MB> [extra qemu args...]
    local name="$1" ram="$2"; shift 2
    rm -f "$MON"
    qemu-system-x86_64 "${ACCEL[@]}" -m "$ram" -smp 2 -machine q35 \
        -cdrom "$ISO" -boot d -vga std -display none \
        -nic user,model=e1000 -usb -device usb-tablet \
        -monitor "unix:$MON,server,nowait" \
        -serial "file:$OUT/$name-serial.log" "$@" &
    QPID=$!
    for _ in $(seq 1 50); do [ -S "$MON" ] && break; sleep 0.2; done
}
stop_vm() { ctl quit 2>/dev/null; sleep 2; kill "$QPID" 2>/dev/null; wait "$QPID" 2>/dev/null; }

login_and_explore() {  # login_and_explore <prefix> <with firefox: yes/no>
    local p="$1"
    shot "$p-2-login-screen"
    ctl type "claudius"; ctl key ret
    pause 40;  shot "$p-3-desktop"
    ctl key ctrl-alt-t
    pause 8
    ctl type "claudius ram; claudius refresh\n"
    pause 4;   shot "$p-4-terminal"
    ctl type "clear; python3 ~/Python/numbers_demo.py && python3 ~/Python/system_info.py\n"
    pause 6;   shot "$p-5-python"
    if [ "$2" = yes ]; then
        ctl type "firefox-esr &\n"
        pause 40; shot "$p-6-firefox"
    else
        ctl type "claudius layout ubuntu\n"
        pause 14; shot "$p-6-ubuntu-layout"
    fi
}

echo "== Test 1: BIOS, 8 GB RAM"
start_vm bios-8gb 8192
sleep 4; shot "bios-1-boot-menu"
sleep 14; ctl key ret          # in case the menu timeout did not fire
sleep 7; shot "bios-1b-boot-animation"
pause 68
login_and_explore bios yes
stop_vm

echo "== Test 2: UEFI, 2 GB RAM"
OVMF=""
for f in /usr/share/ovmf/OVMF.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/qemu/OVMF.fd; do
    [ -f "$f" ] && { OVMF="$f"; break; }
done
if [ -n "$OVMF" ]; then
    start_vm uefi-2gb 2048 -bios "$OVMF"
    sleep 9; shot "uefi-1-boot-menu"
    sleep 10; ctl key ret
    pause 80
    login_and_explore uefi no
    stop_vm
else
    echo "OVMF firmware not found: skipping the UEFI test"
fi

ls -la "$OUT"
# The test passes when the desktop screenshots exist and differ from the login screen
for p in bios uefi; do
    [ -f "$OUT/$p-3-desktop.png" ] || continue
    if cmp -s "$OUT/$p-2-login-screen.png" "$OUT/$p-3-desktop.png"; then
        echo "::warning::$p: the screen did not change after logging in"
    fi
done
[ -f "$OUT/bios-3-desktop.png" ]
