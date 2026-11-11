# Building Claudius

There are three ways to build the ISO. All of them produce `out/claudius-1.0-amd64.iso`.

## A. On GitHub (no Linux machine needed)

Fork the repository and push any change to `main`, or open **Actions → Build Claudius ISO → Run workflow**. About 40 minutes later the ISO, its checksum and boot-test screenshots appear under **Releases**.

## B. With Docker (any Linux, or WSL2 on Windows)

```bash
git clone https://github.com/xrevolvex/Claudius-ISO.git
cd Claudius-ISO
./scripts/build-in-docker.sh
```

This needs about 15 GB of free disk space and an internet connection. The container must be `--privileged` (the script does that), because live-build mounts filesystems.

## C. Natively on Debian 13

```bash
sudo ./build.sh
```

## Customising

| Want to... | Edit |
|---|---|
| Add or remove apps | `config/package-lists/claudius.list.chroot` |
| Change the name, version or codename | `claudius.conf` |
| Change default settings (panel, theme, terminal) | `config/includes.chroot/etc/xdg/...` |
| Change what runs at build time | `config/hooks/normal/9000-claudius-system.hook.chroot` |
| Change the performance profiles | `config/includes.chroot/usr/bin/claudius-tune` |
| Change the artwork | edit `branding/generate.py`, then `python3 branding/generate.py` (needs Playwright) |

Packages that don't exist in Debian are skipped with a warning instead of failing the build (`scripts/check-packages.sh`).

## Testing without VirtualBox

```bash
sudo apt install qemu-system-x86 ovmf
./tests/boot-test.sh out/claudius-1.0-amd64.iso out/screenshots
```
