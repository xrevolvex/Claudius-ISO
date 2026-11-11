# Claudius roadmap

Status: ✅ done · 🚧 in progress · ⏳ planned. All Claudius tools are small Python + GTK apps that build on
reliable existing Linux tools (apt, unattended-upgrades, ufw, Timeshift, NetworkManager, PipeWire,
Flameshot, FFmpeg, xfwm4, Plank) instead of reinventing them.

| | App | What it does | Built on |
|---|---|---|---|
| 🚧 | **Claudius Center** | One window for every setting and tool below | GTK 3 |
| 🚧 | **System Monitor** | CPU, RAM, GPU, disk, temperatures, battery health, processes (end unresponsive ones), startup apps, and a "what's slowing my PC down" check | /proc, /sys |
| 🚧 | **Quick Settings** | Wi-Fi, Bluetooth, volume, brightness, night light, battery saver, dark mode, VPN, airplane mode, do-not-disturb and a notification centre | nmcli, rfkill, pactl, xrandr/brightnessctl, redshift, xfce4-notifyd |
| 🚧 | **Update Center** | OS and security updates, app (Flatpak) updates, history, restart-required notices, automatic updates, scheduled restarts, repair after failed updates | apt, unattended-upgrades, flatpak, systemd timers |
| 🚧 | **Restore & Backup** | *System snapshots* (before updates, roll back) kept clearly separate from *personal file backups* | Timeshift, rsync |
| 🚧 | **Security Center** | Firewall manager (rules), app permissions (Flatpak), disk-encryption status, automatic security updates, outdated-software warnings, plain-language recommendations | ufw, flatpak override, lsblk |
| 🚧 | **Welcome & Setup** | First-boot wizard after install: language, keyboard, Wi-Fi, updates, privacy, theme, drivers, essential apps, with a checklist | localectl, nmcli, helper |
| 🚧 | **Launcher** | Super: apps, files, settings, calculator, commands, pinned favourites. Super+A: app grid. Configurable shortcuts | Gio, plocate |
| 🚧 | **Capture** | Region, window or full-screen screenshots with arrows, blur, text and copy to clipboard. Screen recording to MP4 (optional GIF) | Flameshot, FFmpeg, slop |
| 🚧 | **Desktop Experience** | Windows, macOS (Plank dock with zoom) and Ubuntu layouts, taskbar, dock, app grid, virtual desktops, window tiling, animation controls, startup apps | xfce4-panel, Plank, xfwm4 |
| 🚧 | **App Center** | Curated catalogue, one-click install from Debian or Flathub | apt, flatpak |
| 🚧 | **Driver Manager** | VirtualBox/VMware/QEMU guest tools, CPU microcode, firmware, GPU and 3D status | systemd-detect-virt, lspci |
| 🚧 | **Packs** | Developer, gaming, virtual machines, remote desktop, power management | apt, flatpak |
| 🚧 | **Themes** | Accent colours (Yaru accents), dark/light, flat wallpaper pack, notification theme | Yaru, Arc, Papirus |

## Already shipped in 1.0
✅ Live + installer ISO (BIOS/UEFI) · ✅ adaptive RAM profiles · ✅ boot to RAM · ✅ animated boot and login ·
✅ refresh-rate detection (144 Hz) · ✅ Python tooling · ✅ Ubuntu-style layout · ✅ firewall on · ✅ CI build + boot test
