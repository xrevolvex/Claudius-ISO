"""Personalize: Appearance, Desktop experience, Display, Performance."""
import glob
import json
import os

import common as C
from common import Gdk, GLib, Gtk
from page import Page

SHORTCUTS_FILE = os.path.join(C.CONFIG_DIR, "shortcuts.json")
# action id -> (description, command, default accelerator)
CLAUDIUS_SHORTCUTS = {
    "launcher": ("Launcher (search apps, files, settings)", "claudius-launcher", "Super_L"),
    "grid": ("App grid", "claudius-launcher --grid", "<Super>a"),
    "quick": ("Quick Settings", "claudius-quick", "<Super>s"),
    "notifications": ("Notification centre", "claudius-quick --notifications", "<Super>n"),
    "capture": ("Capture: screenshot a region (annotate)", "claudius-capture --region", "Print"),
    "capture-full": ("Capture: whole screen", "claudius-capture --full", "<Shift>Print"),
    "capture-window": ("Capture: active window", "claudius-capture --window", "<Alt>Print"),
    "record": ("Start / stop screen recording", "claudius-capture --record-toggle", "<Super><Shift>r"),
    "terminal": ("Terminal", "xfce4-terminal", "<Primary><Alt>t"),
    "files": ("Files", "thunar", "<Super>e"),
    "browser": ("Web browser", "firefox-esr", "<Super>b"),
    "center": ("Claudius Center", "claudius-center", "<Super>i"),
    "monitor": ("System Monitor", "claudius-center --page monitor", "<Primary><Shift>Escape"),
}


def load_shortcuts():
    cur = {k: v[2] for k, v in CLAUDIUS_SHORTCUTS.items()}
    try:
        with open(SHORTCUTS_FILE) as fh:
            cur.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return cur


def apply_shortcuts(cur, old=None):
    base = "/commands/custom/"
    for k, accel in (old or {}).items():
        if accel and accel != cur.get(k):
            C.sh(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-p", base + accel, "-r"])
    for k, accel in cur.items():
        if accel:
            C.xfconf("xfce4-keyboard-shortcuts", base + accel, CLAUDIUS_SHORTCUTS[k][1])
    os.makedirs(C.CONFIG_DIR, exist_ok=True)
    with open(SHORTCUTS_FILE, "w") as fh:
        json.dump(cur, fh, indent=2)


# ============================================================================ Appearance
class AppearancePage(Page):
    title = "Appearance"
    subtitle = "Accent colour, light or dark, theme style and wallpaper. Changes apply instantly."

    def build(self):
        self.cfg = C.load_appearance()

        self.section("Mode")
        modes = Gtk.Box(spacing=10)
        self.mode_btns = {}
        for m, text in (("dark", "Dark"), ("light", "Light")):
            b = Gtk.ToggleButton(label=text, active=self.cfg["mode"] == m)
            C.styled(b, "flat-btn")
            b.connect("toggled", self.on_mode, m)
            modes.pack_start(b, False, False, 0)
            self.mode_btns[m] = b
        self.put(modes)

        self.section("Accent colour", "Used by the wallpaper, Claudius apps, the terminal and (with the Yaru style) every app.")
        sw = Gtk.Box(spacing=12)
        self.swatches = {}
        for name, (hexc, _y) in C.ACCENTS.items():
            b = Gtk.Button()
            C.styled(b, "swatch")
            prov = Gtk.CssProvider()
            prov.load_from_data(f"button {{ background-color: {hexc}; }}".encode())
            b.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
            b.set_tooltip_text(name.capitalize())
            b.connect("clicked", self.on_accent, name)
            sw.pack_start(b, False, False, 0)
            self.swatches[name] = b
        self.put(sw)

        self.section("Style")
        styles = Gtk.Box(spacing=10)
        self.style_btns = {}
        for st, text in (("claudius", "Claudius (Arc + Papirus icons)"), ("yaru", "Yaru (Ubuntu style, follows the accent)")):
            b = Gtk.ToggleButton(label=text, active=self.cfg["style"] == st)
            C.styled(b, "flat-btn")
            b.connect("toggled", self.on_style, st)
            styles.pack_start(b, False, False, 0)
            self.style_btns[st] = b
        self.put(styles)

        self.section("Wallpaper")
        flow = Gtk.FlowBox(max_children_per_line=5, selection_mode=Gtk.SelectionMode.NONE,
                           column_spacing=10, row_spacing=10)
        auto = Gtk.Button(label="Match accent")
        C.styled(auto, "flat-btn")
        auto.set_size_request(192, 108)
        auto.connect("clicked", lambda *_: self.set_wall("auto"))
        flow.add(auto)
        for path in sorted(glob.glob(os.path.join(C.WALLPAPERS, "claudius-*.png"))):
            if path.endswith(("-default-2560.png", "-login.png")):
                continue
            try:
                from gi.repository import GdkPixbuf
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 192, 108, False)
            except Exception:  # noqa: BLE001
                continue
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.add(Gtk.Image.new_from_pixbuf(pb))
            b.set_tooltip_text(os.path.basename(path))
            b.connect("clicked", lambda _b, p=path: self.set_wall(p))
            flow.add(b)
        pick = Gtk.Button(label="Choose a picture…")
        C.styled(pick, "flat-btn")
        pick.set_size_request(192, 108)
        pick.connect("clicked", self.pick_wall)
        flow.add(pick)
        self.put(flow)
        self.refresh_swatches()

    def refresh_swatches(self):
        for name, b in self.swatches.items():
            ctx = b.get_style_context()
            (ctx.add_class if name == self.cfg["accent"] else ctx.remove_class)("active")

    def apply(self):
        C.apply_appearance(self.cfg)
        C.install_css(C.accent_hex(self.cfg))
        self.refresh_swatches()

    def on_mode(self, btn, mode):
        if btn.get_active():
            self.cfg["mode"] = mode
            for m, b in self.mode_btns.items():
                if m != mode:
                    b.set_active(False)
            self.apply()

    def on_style(self, btn, st):
        if btn.get_active():
            self.cfg["style"] = st
            for s, b in self.style_btns.items():
                if s != st:
                    b.set_active(False)
            self.apply()

    def on_accent(self, _b, name):
        self.cfg["accent"] = name
        self.apply()

    def set_wall(self, path):
        self.cfg["wallpaper"] = path
        self.apply()

    def pick_wall(self, *_):
        dlg = Gtk.FileChooserDialog(title="Choose a wallpaper", parent=self.center, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Use", Gtk.ResponseType.OK)
        f = Gtk.FileFilter()
        f.set_name("Pictures")
        f.add_mime_type("image/*")
        dlg.add_filter(f)
        if dlg.run() == Gtk.ResponseType.OK:
            self.set_wall(dlg.get_filename())
        dlg.destroy()


# ============================================================================ Desktop experience
class DesktopPage(Page):
    title = "Desktop"
    subtitle = "Layouts inspired by Windows, macOS and Ubuntu, plus taskbar, dock, workspaces, tiling, animations, shortcuts and startup apps."

    def build(self):
        self.section("Layout", "Switch any time. Nothing is reinstalled.")
        layouts = Gtk.Box(spacing=12, homogeneous=True)
        for lid, title, desc in (("classic", "Windows", "Taskbar at the bottom with a start menu"),
                                 ("macos", "macOS", "Top menu bar and a zooming dock at the bottom"),
                                 ("ubuntu", "Ubuntu", "Top bar and a dock on the left")):
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.add(C.card(C.label(title, "card-title"), C.label(desc, "dim", wrap=True)))
            b.connect("clicked", lambda _b, l=lid: C.launch(["claudius-layout", l]))
            layouts.pack_start(b, True, True, 0)
        self.put(layouts)

        self.section("Taskbar")
        pos = Gtk.ComboBoxText()
        for pid, text in (("p=10;x=0;y=0", "Bottom"), ("p=6;x=0;y=0", "Top")):
            pos.append(pid, text)
        pos.set_active_id(C.xfconf("xfce4-panel", "/panels/panel-1/position") or "p=10;x=0;y=0")
        pos.connect("changed", lambda c: C.xfconf("xfce4-panel", "/panels/panel-1/position", c.get_active_id()))
        self.row("Position", "Where the main panel sits (Windows layout).", pos)
        size = Gtk.SpinButton.new_with_range(24, 64, 2)
        size.set_value(int(C.xfconf("xfce4-panel", "/panels/panel-1/size") or 42))
        size.connect("value-changed", lambda s: C.xfconf("xfce4-panel", "/panels/panel-1/size", int(s.get_value()), "uint"))
        self.row("Height", "Taskbar thickness in pixels.", size)

        self.section("Dock (macOS layout)")
        zoom = Gtk.Switch(active=C.sh(["gsettings", "get", PLANK, "zoom-enabled"]).strip() != "false")
        zoom.connect("state-set", lambda _s, st: plank_set("zoom-enabled", "true" if st else "false") or False)
        self.row("Zoom icons", "Icons grow as the mouse passes over them.", zoom)
        isz = Gtk.SpinButton.new_with_range(32, 96, 4)
        isz.set_value(int((C.sh(["gsettings", "get", PLANK, "icon-size"]).strip() or "48").split()[-1]))
        isz.connect("value-changed", lambda s: plank_set("icon-size", str(int(s.get_value()))))
        self.row("Icon size", "", isz)
        self.row("App grid", "All apps in a full-screen grid (Super+A).",
                 C.button("Open", lambda: C.launch(["claudius-launcher", "--grid"])))

        self.section("Workspaces and windows")
        ws = Gtk.SpinButton.new_with_range(1, 9, 1)
        ws.set_value(int(C.xfconf("xfwm4", "/general/workspace_count") or 2))
        ws.connect("value-changed", lambda s: C.xfconf("xfwm4", "/general/workspace_count", int(s.get_value()), "int"))
        self.row("Virtual desktops", "Switch with Ctrl+Alt+Left/Right.", ws)
        self.switch("Snap windows to screen edges", "Drag a window to an edge to tile it to half the screen.",
                    C.xfconf("xfwm4", "/general/tile_on_move") != "false",
                    lambda st: C.xfconf("xfwm4", "/general/tile_on_move", st))
        self.switch("Keyboard tiling", "Super+Arrow keys tile the active window.", True, self.keyboard_tiling)

        self.section("Animations")
        self.switch("Window effects", "Shadows and smooth window drawing (the compositor). Turn off on very slow machines.",
                    C.xfconf("xfwm4", "/general/use_compositing") == "true",
                    lambda st: C.xfconf("xfwm4", "/general/use_compositing", st))
        flag = os.path.join(C.CONFIG_DIR, "no-splash")
        self.switch("Login-to-desktop animation", "The C glides into the wallpaper while the desktop starts.",
                    not os.path.exists(flag), lambda st: toggle_flag(flag, not st))

        self.section("Keyboard shortcuts", "Click Change, then press the new key combination. Esc cancels, Backspace removes it.")
        self.shortcuts = load_shortcuts()
        self.sc_labels = {}
        for k, (desc, _cmd, _d) in CLAUDIUS_SHORTCUTS.items():
            box = Gtk.Box(spacing=8)
            lab = C.label(self.pretty(self.shortcuts.get(k)), "chip")
            self.sc_labels[k] = lab
            box.pack_start(lab, False, False, 0)
            box.pack_start(C.button("Change", lambda key=k: self.capture(key)), False, False, 0)
            self.row(desc, None, box)

        self.section("Startup apps", "Apps that start when you log in. Fewer means a faster start and more free RAM.")
        from pages_monitor import startup_rows
        for w in startup_rows():
            self.put(w)

    @staticmethod
    def pretty(accel):
        if not accel:
            return "none"
        key, mods = Gtk.accelerator_parse(accel)
        return Gtk.accelerator_get_label(key, mods) if key else accel

    def capture(self, k):
        dlg = Gtk.Dialog(title="New shortcut", transient_for=self.center, modal=True)
        dlg.get_content_area().add(C.label(f"Press the new keys for:\n{CLAUDIUS_SHORTCUTS[k][0]}", wrap=True))
        dlg.set_default_size(360, 120)
        result = {}

        def on_key(_w, ev):
            if ev.keyval == Gdk.KEY_Escape:
                dlg.response(Gtk.ResponseType.CANCEL)
            elif ev.keyval == Gdk.KEY_BackSpace:
                result["accel"] = ""
                dlg.response(Gtk.ResponseType.OK)
            elif ev.keyval not in (Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                                   Gdk.KEY_Alt_L, Gdk.KEY_Alt_R):
                mods = ev.state & Gtk.accelerator_get_default_mod_mask()
                result["accel"] = Gtk.accelerator_name(ev.keyval, mods)
                dlg.response(Gtk.ResponseType.OK)
            return True
        dlg.connect("key-press-event", on_key)
        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK and "accel" in result:
            old = dict(self.shortcuts)
            self.shortcuts[k] = result["accel"]
            apply_shortcuts(self.shortcuts, old)
            self.sc_labels[k].set_text(self.pretty(result["accel"]))
        dlg.destroy()

    @staticmethod
    def keyboard_tiling(on):
        keys = {"<Super>Left": "tile_left_key", "<Super>Right": "tile_right_key",
                "<Super>Up": "maximize_window_key", "<Super>Down": "hide_window_key"}
        for accel, action in keys.items():
            p = f"/xfwm4/custom/{accel}"
            if on:
                C.xfconf("xfce4-keyboard-shortcuts", p, action)
            else:
                C.sh(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-p", p, "-r"])


PLANK = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"


def plank_set(key, value):
    C.sh(["gsettings", "set", PLANK, key, value])


def toggle_flag(path, present):
    if present:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
    elif os.path.exists(path):
        os.remove(path)


# ============================================================================ Display
class DisplayPage(Page):
    title = "Display"
    subtitle = "Resolution and refresh rate. Claudius picks the highest refresh rate your screen offers, and 144 Hz in virtual machines."

    def build(self):
        d = C.read_kv("/run/claudius/display")
        self.info = C.label(f"Now: {d.get('MODE', '?')} at {d.get('REFRESH', '?')} Hz on {d.get('OUTPUT', '?')} "
                            f"({'virtual machine: ' + d['VIRT'] if d.get('VIRT', 'none') != 'none' else 'physical screen'})",
                            "h2")
        self.put(self.info)
        combo = Gtk.ComboBoxText()
        for r in ("auto", "60", "75", "90", "120", "144", "165", "240"):
            combo.append(r, "Automatic (recommended)" if r == "auto" else f"{r} Hz")
        try:
            combo.set_active_id(open("/etc/claudius/refresh").read().strip())
        except OSError:
            combo.set_active_id("auto")
        combo.connect("changed", self.on_rate)
        self.row("Refresh rate", "Higher is smoother. In VirtualBox, turn on 3D acceleration for the best result.", combo)
        self.row("Resolution, scaling and monitors", "Arrange screens and choose a resolution.",
                 C.button("Open display settings", lambda: C.launch("xfce4-display-settings")))
        self.row("Night light", "Warmer colours in the evening. Quick Settings has the switch.",
                 C.button("Quick Settings", lambda: C.launch("claudius-quick")))
        gl = C.sh(["glxinfo", "-B"], timeout=8)
        renderer = next((l.split(":", 1)[1].strip() for l in gl.splitlines() if "OpenGL renderer" in l), "unknown")
        soft = "llvmpipe" in renderer.lower() or "softpipe" in renderer.lower()
        self.row("Graphics acceleration", f"Renderer: {renderer}",
                 C.label("Software only (enable 3D in VirtualBox)" if soft else "Hardware accelerated",
                         "warn" if soft else "ok"))

    def on_rate(self, combo):
        rate = combo.get_active_id()

        def done(rc):
            if rc == 0:
                C.sh(["/usr/bin/claudius-display-setup"])
                d = C.read_kv("/run/claudius/display")
                mode = C.sh(["xrandr", "--query"])
                cur = next((l.split()[0] for l in mode.splitlines() if "*" in l), d.get("MODE", "?"))
                self.info.set_text(f"Now: {cur} (setting: {rate}). Fully applied at next login.")
        C.helper(["refresh", rate], on_done=done)


# ============================================================================ Performance
class PerformancePage(Page):
    title = "Performance"
    subtitle = "Claudius tunes memory, swap, the browser and window effects for your RAM at every start."

    def build(self):
        t = C.read_kv("/run/claudius/tune")
        self.put(C.label(f"Active now: {t.get('PROFILE', '?')} · {t.get('MEM_MB', '?')} MB RAM · {t.get('CPUS', '?')} CPUs · "
                         f"zram {t.get('ZRAM_PERCENT', '?')} % · {t.get('FIREFOX_PROCESSES', '?')} Firefox processes", "h2"))
        try:
            want = open("/etc/claudius/profile").read().strip()
        except OSError:
            want = "auto"
        group = None
        for pid, title, desc in (
                ("auto", "Automatic (recommended)", "Pick the best profile for the RAM at every start."),
                ("lite", "Lite", "Under 3 GB: big compressed swap, 2 browser processes, no effects."),
                ("balanced", "Balanced", "3 to 6 GB: moderate settings."),
                ("performance", "Performance", "6 GB and up: more browser processes and caches, effects on, apps preloaded.")):
            rb = Gtk.RadioButton.new_with_label_from_widget(group, title)
            group = group or rb
            rb.set_active(pid == want)
            rb.connect("toggled", self.on_profile, pid)
            self.row(title, desc, rb)
        self.status = C.label("", "dim")
        self.put(self.status)

    def on_profile(self, rb, pid):
        if not rb.get_active():
            return
        self.status.set_text("Applying…")
        C.helper(["profile", pid], on_done=lambda rc: self.status.set_text(
            "Saved. Browser and window-effect changes apply at next login." if rc == 0 else "Not changed."))
