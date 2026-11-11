#!/usr/bin/env python3
"""Claudius Setup: first-boot wizard with a checklist.

Starts by itself at the first login after installing (not in the live session).
Open it again any time from the menu: "Set up Claudius".
"""
import json
import os
import sys
import threading

sys.path.insert(0, "/usr/lib/claudius/center")
import common as C  # noqa: E402
from common import GLib, Gtk  # noqa: E402

STATE = os.path.join(C.CONFIG_DIR, "setup.json")
LOCALES = [("en_US.UTF-8", "English (United States)"), ("en_GB.UTF-8", "English (United Kingdom)"),
           ("hu_HU.UTF-8", "Magyar"), ("de_DE.UTF-8", "Deutsch"), ("fr_FR.UTF-8", "Français"),
           ("es_ES.UTF-8", "Español"), ("it_IT.UTF-8", "Italiano"), ("pt_BR.UTF-8", "Português (Brasil)"),
           ("pl_PL.UTF-8", "Polski"), ("ro_RO.UTF-8", "Română"), ("nl_NL.UTF-8", "Nederlands"),
           ("tr_TR.UTF-8", "Türkçe"), ("ru_RU.UTF-8", "Русский"), ("ja_JP.UTF-8", "日本語"), ("zh_CN.UTF-8", "中文（简体）")]
LAYOUTS = [("us", "English (US)"), ("gb", "English (UK)"), ("hu", "Hungarian"), ("de", "German"), ("fr", "French"),
           ("es", "Spanish"), ("it", "Italian"), ("br", "Portuguese (Brazil)"), ("pl", "Polish"), ("ro", "Romanian"),
           ("nl", "Dutch"), ("tr", "Turkish"), ("ru", "Russian"), ("jp", "Japanese"), ("cn", "Chinese")]
STEPS = [("welcome", "Welcome"), ("language", "Language & keyboard"), ("network", "Wi-Fi & network"),
         ("updates", "Updates"), ("privacy", "Privacy"), ("look", "Look & layout"), ("drivers", "Drivers"),
         ("apps", "Essential apps"), ("done", "All set")]


def load_state():
    try:
        with open(STATE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"done": [], "finished": False}


def save_state(st):
    os.makedirs(C.CONFIG_DIR, exist_ok=True)
    with open(STATE, "w") as fh:
        json.dump(st, fh, indent=2)


class Setup(Gtk.Window):
    def __init__(self):
        super().__init__(title="Set up Claudius")
        self.set_icon_name("claudius")
        self.set_default_size(980, 640)
        self.set_position(Gtk.WindowPosition.CENTER)
        C.styled(self, "claudius-window")
        self.state = load_state()
        main = Gtk.Box()
        self.add(main)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin=18)
        C.styled(side, "sidebar-list")
        side.set_size_request(250, -1)
        side.pack_start(C.label("Setup checklist", "h2"), False, False, 8)
        self.checks = {}
        for sid, title in STEPS:
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            row = Gtk.Box(spacing=10)
            mark = C.label("", "ok")
            row.pack_start(mark, False, False, 0)
            row.pack_start(C.label(title), False, False, 0)
            b.add(row)
            b.connect("clicked", lambda _b, s=sid: self.go(s))
            side.pack_start(b, False, False, 0)
            self.checks[sid] = mark
        main.pack_start(side, False, False, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, transition_duration=220)
        right.pack_start(self.stack, True, True, 0)
        nav = Gtk.Box(spacing=10, margin=18)
        self.back = C.button("Back", lambda: self.step(-1))
        self.skip = C.button("Skip", lambda: self.step(1))
        self.next = C.button("Next", lambda: self.complete_and_next(), "accent-btn")
        nav.pack_start(self.back, False, False, 0)
        nav.pack_end(self.next, False, False, 0)
        nav.pack_end(self.skip, False, False, 0)
        right.pack_start(nav, False, False, 0)
        main.pack_start(right, True, True, 0)

        for sid, _t in STEPS:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            C.styled(page, "page")
            getattr(self, f"page_{sid}")(page)
            sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
            sw.add(page)
            self.stack.add_named(sw, sid)
        self.refresh_checks()
        self.show_all()
        self.go("welcome")

    # ------------------------------------------------------------------ navigation
    def current(self):
        return self.stack.get_visible_child_name()

    def index(self):
        return [s for s, _t in STEPS].index(self.current())

    def go(self, sid):
        self.stack.set_visible_child_name(sid)
        i = [s for s, _t in STEPS].index(sid)
        self.back.set_sensitive(i > 0)
        self.skip.set_visible(sid not in ("welcome", "done"))
        self.next.set_label("Finish" if sid == "done" else "Next")

    def step(self, d):
        i = max(0, min(len(STEPS) - 1, self.index() + d))
        self.go(STEPS[i][0])

    def mark(self, sid):
        if sid not in self.state["done"]:
            self.state["done"].append(sid)
        save_state(self.state)
        self.refresh_checks()

    def refresh_checks(self):
        for sid, lab in self.checks.items():
            lab.set_text("✔" if sid in self.state["done"] else "○")

    def complete_and_next(self):
        sid = self.current()
        if sid == "done":
            self.state["finished"] = True
            save_state(self.state)
            self.destroy()
            return
        self.mark(sid)
        self.step(1)

    @staticmethod
    def h(page, title, text):
        page.pack_start(C.label(title, "h1"), False, False, 0)
        page.pack_start(C.label(text, "dim", wrap=True), False, False, 0)

    # ------------------------------------------------------------------ pages
    def page_welcome(self, p):
        logo = Gtk.Image.new_from_icon_name("claudius", Gtk.IconSize.DIALOG)
        logo.set_pixel_size(112)
        logo.set_halign(Gtk.Align.START)
        p.pack_start(logo, False, False, 0)
        self.h(p, "Welcome to Claudius", "Let's get your computer ready. Every step can be skipped and changed later in "
                                         "Claudius Center. No terminal needed.")

    def page_language(self, p):
        self.h(p, "Language & keyboard", "The system language applies after you log out and back in. The keyboard changes now.")
        self.loc = Gtk.ComboBoxText()
        for code, name in LOCALES:
            self.loc.append(code, name)
        self.loc.set_active_id(os.environ.get("LANG", "en_US.UTF-8").replace(".utf8", ".UTF-8"))
        if self.loc.get_active_id() is None:
            self.loc.set_active_id("en_US.UTF-8")
        p.pack_start(C.label("Language", "card-title"), False, False, 0)
        p.pack_start(self.loc, False, False, 0)
        self.kb = Gtk.ComboBoxText()
        for code, name in LAYOUTS:
            self.kb.append(code, name)
        self.kb.set_active_id("us")
        p.pack_start(C.label("Keyboard layout", "card-title"), False, False, 0)
        p.pack_start(self.kb, False, False, 0)
        self.lang_status = C.label("", "dim")
        p.pack_start(C.button("Apply", self.apply_language, "accent-btn"), False, False, 0)
        p.pack_start(self.lang_status, False, False, 0)

    def apply_language(self):
        kb, loc = self.kb.get_active_id(), self.loc.get_active_id()
        C.sh(["setxkbmap", kb])
        C.xfconf("keyboard-layout", "/Default/XkbDisable", False)
        C.xfconf("keyboard-layout", "/Default/XkbLayout", kb)
        self.lang_status.set_text("Applying…")
        C.helper(["set-keymap", kb], on_done=lambda rc: C.helper(
            ["set-locale", loc], on_done=lambda rc2: (self.lang_status.set_text(
                "Done. The language applies at next login." if rc2 == 0 else "Keyboard set; the language could not be changed."),
                self.mark("language"))))

    def page_network(self, p):
        self.h(p, "Wi-Fi & network", "Connect to the internet for updates and apps.")
        self.net_status = C.label("", "h2")
        p.pack_start(self.net_status, False, False, 0)
        self.wifi_list = Gtk.ListBox()
        p.pack_start(self.wifi_list, False, False, 0)
        row = Gtk.Box(spacing=8)
        self.wifi_pw = Gtk.Entry(placeholder_text="Wi-Fi password", visibility=False)
        row.pack_start(self.wifi_pw, True, True, 0)
        row.pack_start(C.button("Connect", self.connect_wifi, "accent-btn"), False, False, 0)
        row.pack_start(C.button("Rescan", self.scan_wifi), False, False, 0)
        p.pack_start(row, False, False, 0)
        p.pack_start(C.button("Advanced network settings", lambda: C.launch("nm-connection-editor")), False, False, 0)
        GLib.idle_add(self.scan_wifi)

    def scan_wifi(self):
        st = C.sh(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"])
        connected = [l.split(":")[2] for l in st.splitlines() if l.split(":")[1:2] == ["connected"]]
        self.net_status.set_text(f"✔ Connected ({', '.join(connected)})" if connected else "Not connected")
        for c in self.wifi_list.get_children():
            self.wifi_list.remove(c)
        nets = C.sh(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "auto"], timeout=20)
        seen = set()
        for l in nets.splitlines():
            parts = l.rsplit(":", 2)
            if len(parts) == 3 and parts[0] and parts[0] not in seen:
                seen.add(parts[0])
                row = Gtk.ListBoxRow()
                row.ssid = parts[0]
                row.add(C.label(f"{parts[0]}   ·   {parts[1]} %   {'🔒' if parts[2] else ''}"))
                self.wifi_list.add(row)
        if not seen:
            self.wifi_list.add(C.label("No Wi-Fi networks found (a VM uses a wired connection).", "dim"))
        self.wifi_list.show_all()
        if connected:
            self.mark("network")
        return False

    def connect_wifi(self):
        row = self.wifi_list.get_selected_row()
        if not row or not hasattr(row, "ssid"):
            return
        cmd = ["nmcli", "device", "wifi", "connect", row.ssid]
        if self.wifi_pw.get_text():
            cmd += ["password", self.wifi_pw.get_text()]
        self.net_status.set_text(f"Connecting to {row.ssid}…")
        C.run_async(cmd, on_done=lambda rc: self.scan_wifi())

    def page_updates(self, p):
        self.h(p, "Updates", "Claudius can install security fixes by itself in the background.")
        from pages_system import auto_updates_on
        sw = Gtk.Switch(active=auto_updates_on(), halign=Gtk.Align.START)
        sw.connect("state-set", lambda _s, st: C.helper(["auto-updates", "on" if st else "off"]) or False)
        p.pack_start(C.label("Automatic security updates (recommended)", "card-title"), False, False, 0)
        p.pack_start(sw, False, False, 0)
        p.pack_start(C.button("Check for updates now", lambda: C.launch(["claudius-center", "--page", "updates"])), False, False, 0)

    def page_privacy(self, p):
        self.h(p, "Privacy", "Claudius collects nothing. Firefox telemetry and studies are already off.")
        gtk_ini = os.path.expanduser("~/.config/gtk-3.0/settings.ini")

        def set_recent(on):
            os.makedirs(os.path.dirname(gtk_ini), exist_ok=True)
            lines = [l for l in (open(gtk_ini).readlines() if os.path.exists(gtk_ini) else []) if not l.startswith("gtk-recent-files")]
            if not any(l.strip() == "[Settings]" for l in lines):
                lines.insert(0, "[Settings]\n")
            lines.append(f"gtk-recent-files-enabled={'true' if on else 'false'}\n")
            open(gtk_ini, "w").writelines(lines)
            if not on:
                try:
                    os.remove(os.path.expanduser("~/.local/share/recently-used.xbel"))
                except OSError:
                    pass
        for title, desc, active, cb in (
                ("Remember recently used files", "Shows recent files in apps. Turn off to keep no history.", True, set_recent),
                ("Firewall", "Block incoming connections (recommended).", True,
                 lambda st: C.helper(["firewall", "on" if st else "off"]))):
            box = Gtk.Box(spacing=14)
            t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            t.pack_start(C.label(title, "card-title"), False, False, 0)
            t.pack_start(C.label(desc, "dim", wrap=True), False, False, 0)
            box.pack_start(t, True, True, 0)
            sw = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
            sw.connect("state-set", lambda _s, st, f=cb: f(st) or False)
            box.pack_end(sw, False, False, 0)
            p.pack_start(C.card(box, orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        p.pack_start(C.label("✔ Firefox: telemetry, studies and sponsored content are off. Search uses DuckDuckGo.", "ok", wrap=True),
                     False, False, 0)

    def page_look(self, p):
        self.h(p, "Look & layout", "Pick a colour and a layout. Everything else lives in Claudius Center → Appearance.")
        cfg = C.load_appearance()
        sw = Gtk.Box(spacing=12)
        for name, (hexc, _y) in C.ACCENTS.items():
            b = Gtk.Button()
            C.styled(b, "swatch")
            prov = Gtk.CssProvider()
            prov.load_from_data(f"button {{ background-color: {hexc}; }}".encode())
            b.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
            b.set_tooltip_text(name.capitalize())
            b.connect("clicked", lambda _b, n=name: self.set_accent(n))
            sw.pack_start(b, False, False, 0)
        p.pack_start(sw, False, False, 0)
        modes = Gtk.Box(spacing=8)
        for m in ("dark", "light"):
            modes.pack_start(C.button(m.capitalize(), lambda mm=m: self.set_mode(mm)), False, False, 0)
        p.pack_start(modes, False, False, 0)
        lay = Gtk.Box(spacing=8)
        for lid, text in (("classic", "Windows"), ("macos", "macOS"), ("ubuntu", "Ubuntu")):
            lay.pack_start(C.button(text, lambda l=lid: C.launch(["claudius-layout", l])), False, False, 0)
        p.pack_start(C.label("Layout", "card-title"), False, False, 0)
        p.pack_start(lay, False, False, 0)
        _ = cfg

    def set_accent(self, n):
        cfg = C.load_appearance()
        cfg["accent"] = n
        C.apply_appearance(cfg)
        C.install_css(C.accent_hex(cfg))

    def set_mode(self, m):
        cfg = C.load_appearance()
        cfg["mode"] = m
        C.apply_appearance(cfg)

    def page_drivers(self, p):
        self.h(p, "Drivers", "Claudius checks what extra software your hardware or virtual machine needs.")
        virt = C.sh(["systemd-detect-virt"]).strip() or "none"
        msg = {"oracle": "VirtualBox detected. Guest Additions add auto-resize and a shared clipboard.",
               "vmware": "VMware detected. VMware Tools add auto-resize and a shared clipboard.",
               "kvm": "KVM/QEMU detected. SPICE tools add clipboard sharing.",
               "qemu": "QEMU detected. SPICE tools add clipboard sharing.",
               "none": "Physical computer: Claudius can add CPU microcode and extra firmware."}.get(virt, f"Machine: {virt}")
        p.pack_start(C.label(msg, wrap=True), False, False, 0)
        p.pack_start(C.button("Open Driver Manager", lambda: C.launch(["claudius-center", "--page", "drivers"]), "accent-btn"),
                     False, False, 0)

    def page_apps(self, p):
        self.h(p, "Essential apps", "Tick what you'd like. Already installed apps are not shown.")
        sys.path.insert(0, "/usr/lib/claudius/center")
        from pages_apps import is_installed, load_catalog
        flat = C.flatpak_installed_ids()
        self.app_checks = []
        grid = Gtk.Grid(column_spacing=24, row_spacing=8)
        cat = load_catalog()
        wanted = [a for a in cat["apps"] if a.get("essential") or a["name"] in ("Spotify", "Discord", "Steam", "Inkscape", "Telegram")]
        n = 0
        for a in wanted:
            if is_installed(a, flat):
                continue
            cb = Gtk.CheckButton(label=f"{a['name']}: {a['summary']}")
            cb.app = a
            grid.attach(cb, n % 2, n // 2, 1, 1)
            self.app_checks.append(cb)
            n += 1
        if not n:
            grid.attach(C.label("All the essentials are already installed. ✔", "ok"), 0, 0, 1, 1)
        p.pack_start(grid, False, False, 0)
        self.app_status = C.label("", "dim")
        p.pack_start(C.button("Install selected", self.install_apps, "accent-btn"), False, False, 0)
        p.pack_start(self.app_status, False, False, 0)

    def install_apps(self):
        chosen = [cb.app for cb in self.app_checks if cb.get_active()]
        apt = [a["apt"] for a in chosen if a.get("apt")]
        flat = [a["flatpak"] for a in chosen if a.get("flatpak")]
        if not chosen:
            return
        self.app_status.set_text(f"Installing {len(chosen)} app(s)… you can keep going.")

        def after_apt(rc):
            if flat:
                C.helper(["flatpak-install", *flat], on_done=finish)
            else:
                finish(rc)

        def finish(rc):
            self.app_status.set_text("Installed ✔" if rc == 0 else "Some apps could not be installed (check the internet connection).")
            if rc == 0:
                self.mark("apps")
        if apt:
            C.helper(["apt-install", *apt], on_done=after_apt)
        else:
            after_apt(0)

    def page_done(self, p):
        self.h(p, "You're all set", "Claudius is ready. Things you skipped are unticked on the left: come back any time from "
                                    "the menu (Set up Claudius) or Claudius Center.")
        tips = ("Super opens the Launcher. Super+A shows all apps.\n"
                "Super+S opens Quick Settings. Print takes a screenshot.\n"
                "Claudius Center (Super+I) has every setting and tool.")
        p.pack_start(C.card(C.label(tips, wrap=True)), False, False, 0)


def main():
    if "--first-login" in sys.argv:
        if C.IS_LIVE or load_state().get("finished"):
            return
    C.install_css()
    win = Setup()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
