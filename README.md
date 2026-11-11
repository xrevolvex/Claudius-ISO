<p align="center">
  <img src="branding/png/icon-128.png" width="96" alt="Claudius logo">
</p>

<h1 align="center">Claudius</h1>
<p align="center"><b>Light. Fast. Yours.</b><br>
A Debian-based Linux desktop that tunes itself to the machine it runs on, from a 2 GB virtual machine up to 8 GB and beyond.</p>

<p align="center">
  <a href="../../releases/latest"><b>Download the ISO</b></a> ·
  <a href="docs/VIRTUALBOX.md">Run it in VirtualBox</a> ·
  <a href="docs/BUILDING.md">Build it yourself</a>
</p>

---

## What you get

| | |
|---|---|
| **Desktop** | XFCE with a Windows-style taskbar, a start menu (press <kbd>Super</kbd>), a live CPU/RAM meter and a dark Arc theme with Papirus icons |
| **Login** | A branded login screen (LightDM). The live session's login is `claudius` / `claudius` |
| **Web** | Firefox ESR with a fast, private Claudius start page, telemetry off |
| **Office and media** | LibreOffice Writer, Calc and Impress, VLC, a PDF viewer, an image viewer, a text and code editor (Mousepad, Geany) |
| **Files** | Thunar file manager, archive support (zip, 7z, tar), USB drives, Trash |
| **Terminal** | xfce4-terminal with a Claudius colour scheme, a custom prompt, a system card at startup, and the `claudius` helper command |
| **Python** | Python 3 with pip, venv, pipx, tkinter, numpy, requests, IPython, IDLE and the **Thonny** IDE. Double-click a `.py` file to open it, right-click → **Run with Python** to run it, example scripts in `~/Python` |
| **Ubuntu-style** | Switch to a **top bar + left dock** layout with the **Yaru** theme (`claudius layout ubuntu`), **ufw firewall** on by default, **automatic security updates**, **command-not-found** suggestions, **Software & Updates**, **GNOME Disks**, coloured `apt` with a progress bar, and **Flatpak + Flathub** |
| **Apps** | The whole Debian archive: `claudius install <app>`, Synaptic, or Flathub apps with `claudius flatpak <id>` |
| **Installer** | Calamares. Click **Install Claudius** on the desktop to install it to disk (BIOS or UEFI) |
| **Welcome** | A welcome app with one-click shortcuts and tips |

## Python, ready to go

```bash
python3 ~/Python/hello.py          # or just double-click it
claudius newpy ~/Projects          # new project folder with its own .venv
pipx install httpie                # command-line tools from PyPI, isolated
```

Thonny opens `.py` files by default (press <kbd>F5</kbd> to run). Geany, IDLE and IPython are there too. In the file manager, right-click a script → **Run with Python**, or right-click a folder → **New Python project here**.

## Built for speed

At every boot, `claudius-tune` checks how much RAM and CPU the machine has and picks a profile:

| Profile | RAM | What changes |
|---|---|---|
| **lite** | under 3 GB | large compressed swap in RAM (zram, 75 %), 2 browser processes, no window effects |
| **balanced** | 3 to 6 GB | zram 50 %, 4 browser processes |
| **performance** | 6 GB and up | zram 25 %, 8 browser processes, a 512 MB browser memory cache, window effects on, and Firefox/LibreOffice preloaded into RAM so they open instantly |

Also included: no Bluetooth, printing or modem services, no boot splash daemon, I/O scheduling tuned for virtual disks, journald capped in size, and a **"Start Claudius in RAM"** boot entry that copies the whole system into memory (4 GB+). On an 8 GB VM that makes every app launch close to instant.

Check what it picked: open a terminal and run `claudius ram`. Change it with `claudius profile performance` (or `lite`, `balanced`, `auto`).

## Quick start (VirtualBox)

1. Download `claudius-1.0-amd64.iso` from [Releases](../../releases/latest).
2. Create a VM: **Type** Linux, **Version** Debian (64-bit), **8 GB RAM**, **2+ CPUs**, **25 GB disk**, Graphics **VMSVGA** with 128 MB video memory.
3. Attach the ISO and start the VM. Log in with `claudius` / `claudius`.

Step-by-step instructions with every setting: **[docs/VIRTUALBOX.md](docs/VIRTUALBOX.md)**

## The `claudius` command

```
claudius info             system summary
claudius ram              memory use, top apps and the active profile
claudius profile [name]   show or set: auto, lite, balanced, performance
claudius update           update everything
claudius install <app>    install apps (e.g. claudius install gimp)
claudius remove <app>     remove apps
claudius search <word>    search the catalogue
claudius clean            free disk space
claudius python <file>    run a Python script (no file: interactive Python)
claudius newpy [folder]   new Python project with its own virtual environment
claudius layout [name]    classic (Windows-like) or ubuntu (top bar + dock)
claudius flatpak <app>    install from Flathub, e.g. org.gimp.GIMP
claudius firewall [on|off]
claudius guest-additions  install VirtualBox Guest Additions in one go
claudius tips             keyboard shortcuts
```

## How it's built

Claudius is a set of [live-build](https://live-team.pages.debian.net/live-manual/) configuration files on top of Debian 13 "trixie". Nothing is downloaded from anywhere but the official Debian archive.

```
build.sh                    the build script (runs live-build)
claudius.conf               name, version, codename
config/package-lists/       which packages go in
config/hooks/               setup scripts that run inside the image
config/includes.chroot/     files copied into the OS (settings, apps, scripts)
branding/                   artwork: SVG sources and a generator script
scripts/                    helpers: Docker build, boot-menu branding, package check
tests/boot-test.sh          boots the ISO in QEMU and takes screenshots
.github/workflows/          GitHub Actions: build, test and release on every push
```

Every push to `main` builds the ISO on GitHub Actions and boots it in QEMU (BIOS with 8 GB, UEFI with 2 GB). It logs in, opens a terminal and Firefox, screenshots each step, and publishes the ISO and screenshots as a release.

## License

The build system and Claudius's own programs are licensed under the **GNU GPL v3** ([LICENSE](LICENSE)). The artwork in `branding/` is licensed under **CC BY-SA 4.0**. The ISO contains Debian packages under their own free licenses. Claudius is an independent project and is not affiliated with Debian.
