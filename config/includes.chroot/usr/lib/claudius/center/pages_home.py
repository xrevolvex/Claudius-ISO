"""Home and About pages."""
import os
import platform

import common as C
from common import Gtk
from page import Page

RELEASE = C.read_kv("/etc/claudius-release")


def upgradable_count():
    out = C.sh(["apt", "list", "--upgradable"], timeout=30)
    return sum(1 for l in out.splitlines() if "/" in l and "[upgradable" in l)


class HomePage(Page):
    title = "Welcome back"

    def build(self):
        tune = C.read_kv("/run/claudius/tune")
        disp = C.read_kv("/run/claudius/display")
        chips = Gtk.Box(spacing=8)
        for text in (f"Claudius {RELEASE.get('CLAUDIUS_VERSION', '1.0')} {RELEASE.get('CLAUDIUS_CODENAME', '')}",
                     f"{tune.get('PROFILE', 'auto').capitalize()} profile",
                     f"{int(tune.get('MEM_MB', '0') or 0) // 1024 or '<1'} GB RAM",
                     f"{disp.get('REFRESH', '?')} Hz",
                     "Live session" if C.IS_LIVE else "Installed"):
            chips.pack_start(C.styled(Gtk.Label(label=text), "chip"), False, False, 0)
        self.put(chips)

        self.status = C.label("Checking your system…", "dim")
        self.put(self.status)

        grid = Gtk.Grid(column_spacing=14, row_spacing=14, column_homogeneous=True)
        tiles = [
            ("system-software-update", "Update Center", "Updates, history and restarts", "updates"),
            ("system-software-install", "App Center", "Install apps in one click", "apps"),
            ("preferences-desktop-theme", "Appearance", "Accent colour, dark mode, wallpaper", "appearance"),
            ("preferences-desktop", "Desktop", "Windows, macOS or Ubuntu layout", "desktop"),
            ("security-high", "Security Center", "Firewall, encryption, recommendations", "security"),
            ("document-revert", "Restore & Backup", "Snapshots and personal backups", "backup"),
            ("org.xfce.taskmanager", "System Monitor", "What's slowing my PC down?", "monitor"),
            ("package-x-generic", "Packs", "Developer, gaming, VMs, remote desktop", "packs"),
        ]
        for i, (icon, title, desc, pid) in enumerate(tiles):
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
            img.set_pixel_size(40)
            img.set_halign(Gtk.Align.START)
            box.pack_start(img, False, False, 0)
            box.pack_start(C.label(title, "card-title"), False, False, 0)
            box.pack_start(C.label(desc, "dim", wrap=True), False, False, 0)
            b.add(C.card(box))
            b.connect("clicked", lambda _b, p=pid: self.center.open_page(p))
            grid.attach(b, i % 4, i // 4, 1, 1)
        self.put(grid)

        tools = Gtk.Box(spacing=10)
        for text, cmd in (("Quick Settings", "claudius-quick"), ("Launcher", "claudius-launcher"),
                          ("Capture", "claudius-capture"), ("Setup checklist", "claudius-setup")):
            tools.pack_start(C.button(text, lambda c=cmd: C.launch(c)), False, False, 0)
        self.section("Claudius tools")
        self.put(tools)

    def on_show(self):
        def work():
            n = upgradable_count()
            reboot = os.path.exists("/run/reboot-required") or os.path.exists("/var/run/reboot-required")
            parts = [f"{n} update{'s' if n != 1 else ''} available" if n else "Your software is up to date"]
            if reboot:
                parts.append("a restart is needed to finish updating")
            C.GLib.idle_add(self.status.set_text, " · ".join(parts))
        import threading
        threading.Thread(target=work, daemon=True).start()
        return False


class AboutPage(Page):
    title = "About Claudius"

    def build(self):
        top = Gtk.Box(spacing=20)
        logo = Gtk.Image.new_from_icon_name("claudius", Gtk.IconSize.DIALOG)
        logo.set_pixel_size(96)
        top.pack_start(logo, False, False, 0)
        t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        t.pack_start(C.label(f"Claudius {RELEASE.get('CLAUDIUS_VERSION', '1.0')}", "h1"), False, False, 0)
        t.pack_start(C.label(f"“{RELEASE.get('CLAUDIUS_CODENAME', '')}” · made by xrevolvex", "dim"), False, False, 0)
        top.pack_start(t, False, False, 0)
        self.put(top)

        mem = C.meminfo()
        cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "?")
        gpu = next((l.split(":", 2)[-1].strip() for l in C.sh("lspci").splitlines() if "VGA" in l or "3D" in l), "?")
        rows = [
            ("Based on", f"Debian {open('/etc/debian_version').read().strip() if os.path.exists('/etc/debian_version') else '13'}"),
            ("Kernel", platform.release()),
            ("Desktop", "XFCE"),
            ("Processor", f"{cpu} ({os.cpu_count()} cores)"),
            ("Memory", f"{mem.get('MemTotal', 0) // 1024} MB"),
            ("Graphics", gpu),
            ("Machine", C.sh("systemd-detect-virt").strip() or "physical"),
            ("Built", f"{RELEASE.get('CLAUDIUS_BUILD_DATE', '?')} (build {RELEASE.get('CLAUDIUS_BUILD_ID', '?')})"),
        ]
        grid = Gtk.Grid(column_spacing=24, row_spacing=8)
        for i, (k, v) in enumerate(rows):
            grid.attach(C.label(k, "dim"), 0, i, 1, 1)
            grid.attach(C.label(v, selectable=True, wrap=True), 1, i, 1, 1)
        self.put(C.card(grid))

        links = Gtk.Box(spacing=10)
        url = RELEASE.get("CLAUDIUS_URL", "https://github.com/xrevolvex/Claudius-ISO")
        links.pack_start(C.button("Project on GitHub", lambda: C.launch(["xdg-open", url])), False, False, 0)
        links.pack_start(C.button("Report a problem", lambda: C.launch(["xdg-open", url + "/issues"])), False, False, 0)
        links.pack_start(C.button("Roadmap", lambda: C.launch(["xdg-open", url + "/blob/main/ROADMAP.md"])), False, False, 0)
        self.put(links)
        self.put(C.label("Claudius is free software under the GNU GPL v3. Artwork: CC BY-SA 4.0. "
                         "It is built on Debian and thousands of open-source projects.", "dim", wrap=True))
