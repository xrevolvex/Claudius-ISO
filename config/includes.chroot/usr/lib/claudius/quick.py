#!/usr/bin/env python3
"""Claudius Quick Settings: a Windows-style panel above the taskbar.

    claudius-quick                 toggles, sliders and notifications
    claudius-quick --notifications open with the notification centre in front
"""
import configparser
import glob
import os
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, "/usr/lib/claudius/center")
import common as C  # noqa: E402
from common import Gdk, GLib, Gtk  # noqa: E402

STATE = os.path.join(C.CONFIG_DIR, "quick.json")
PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claudius-quick.pid")


# ---------------------------------------------------------------------------- system state
def nm(*args):
    return C.sh(["nmcli", *args]).strip()


def wifi_device():
    return any(l.split(":")[1:2] == ["wifi"] for l in nm("-t", "-f", "DEVICE,TYPE", "device").splitlines())


def wifi_on():
    return nm("radio", "wifi") == "enabled"


def vpn_connections():
    out = []
    for l in nm("-t", "-f", "NAME,TYPE,DEVICE", "connection", "show").splitlines():
        parts = l.rsplit(":", 2)
        if len(parts) == 3 and ("vpn" in parts[1] or "wireguard" in parts[1]):
            out.append((parts[0], bool(parts[2])))
    return out


def bluetooth_present():
    return bool(glob.glob("/sys/class/bluetooth/hci*"))


def bluetooth_on():
    out = C.sh(["rfkill", "list", "bluetooth"])
    return "Soft blocked: no" in out


def volume():
    out = C.sh(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    try:
        return int(out.split("/")[1].strip().rstrip("%"))
    except (IndexError, ValueError):
        return 50


def muted():
    return "yes" in C.sh(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])


def backlight():
    """Return (current %, kind) where kind is 'hw', 'sw' or None."""
    if C.have("brightnessctl") and glob.glob("/sys/class/backlight/*"):
        out = C.sh(["brightnessctl", "-m"]).split(",")
        try:
            return int(out[3].rstrip("%")), "hw"
        except (IndexError, ValueError):
            pass
    out = C.sh(["xrandr", "--verbose", "--current"])
    for line in out.splitlines():
        if "Brightness:" in line:
            try:
                return int(float(line.split(":")[1]) * 100), "sw"
            except ValueError:
                pass
    return 100, "sw" if out else None


def set_brightness(pct, kind):
    if kind == "hw":
        C.sh(["brightnessctl", "set", f"{pct}%"])
    else:
        outs = [l.split()[0] for l in C.sh(["xrandr", "--query"]).splitlines() if " connected" in l]
        for o in outs:
            C.sh(["xrandr", "--output", o, "--brightness", f"{max(pct, 20) / 100:.2f}"])


def flag(name):
    return os.path.exists(os.path.join(C.CONFIG_DIR, name))


def set_flag(name, on):
    p = os.path.join(C.CONFIG_DIR, name)
    os.makedirs(C.CONFIG_DIR, exist_ok=True)
    if on:
        open(p, "w").close()
    elif os.path.exists(p):
        os.remove(p)


# ---------------------------------------------------------------------------- notification history
def notification_log():
    """Read xfce4-notifyd's log, whichever format this version uses. Returns [(time, app, summary, body)]."""
    base = os.path.expanduser("~/.cache/xfce4/notifyd")
    items = []
    for db in glob.glob(os.path.join(base, "*.sqlite")) + glob.glob(os.path.join(base, "*.db")):
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            for (table,) in con.execute("select name from sqlite_master where type='table'"):
                cols = [r[1] for r in con.execute(f"pragma table_info('{table}')")]
                pick = lambda *names: next((c for c in cols if c.lower() in names), None)  # noqa: E731
                s, b, a, t = pick("summary"), pick("body"), pick("app_name", "appname", "app"), pick("timestamp", "time")
                if s:
                    q = f"select {t or 'rowid'}, {a or 'null'}, {s}, {b or 'null'} from '{table}' order by rowid desc limit 30"
                    items += [(str(r[0]), r[1] or "", r[2] or "", r[3] or "") for r in con.execute(q)]
            con.close()
        except sqlite3.Error:
            pass
    keyfile = os.path.join(base, "log")
    if os.path.exists(keyfile):
        cp = configparser.RawConfigParser(strict=False)
        try:
            cp.read(keyfile)
            for sec in reversed(cp.sections()[-30:]):
                items.append((sec, cp.get(sec, "app_name", fallback=""), cp.get(sec, "summary", fallback=""),
                              cp.get(sec, "body", fallback="")))
        except configparser.Error:
            pass
    return items


def clear_notifications():
    base = os.path.expanduser("~/.cache/xfce4/notifyd")
    for db in glob.glob(os.path.join(base, "*.sqlite")) + glob.glob(os.path.join(base, "*.db")):
        try:
            con = sqlite3.connect(db)
            for (table,) in con.execute("select name from sqlite_master where type='table'").fetchall():
                con.execute(f"delete from '{table}'")
            con.commit()
            con.close()
        except sqlite3.Error:
            pass
    if os.path.exists(os.path.join(base, "log")):
        open(os.path.join(base, "log"), "w").close()


# ---------------------------------------------------------------------------- UI
CSS_EXTRA = """
window.popup-win { background-color: #121830; }
.quick { background-color: #121830; border: 1px solid #263063; border-radius: 16px; }
.tile { background-image: none; background-color: #1b2347; color: #e6e9f2; border: none; border-radius: 12px;
        padding: 10px; min-height: 64px; box-shadow: none; text-shadow: none; }
.tile label { color: #e6e9f2; }
.tile.on { background-color: @accent; }
.tile.on label { color: #14100a; }
.tile:disabled { opacity: 0.45; }
.notif { background-color: #182044; border-radius: 10px; padding: 10px; }
"""


class Tile(Gtk.Button):
    def __init__(self, icon, text, on_click, state=False, sensitive=True, sub=""):
        super().__init__()
        C.styled(self, "tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        img.set_halign(Gtk.Align.START)
        box.pack_start(img, False, False, 0)
        box.pack_start(C.label(text), False, False, 0)
        self.sub = C.label(sub, "dim")
        box.pack_start(self.sub, False, False, 0)
        self.add(box)
        self.set_state(state)
        self.set_sensitive(sensitive)
        self.connect("clicked", lambda *_: on_click(self))

    def set_state(self, on, sub=None):
        self.on = on
        (self.get_style_context().add_class if on else self.get_style_context().remove_class)("on")
        if sub is not None:
            self.sub.set_text(sub)


class Quick(Gtk.Window):
    def __init__(self, notifications_first=False):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        C.styled(self, "popup-win")
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_default_size(400, -1)
        self.connect("key-press-event", lambda _w, e: e.keyval == Gdk.KEY_Escape and self.destroy())
        self.connect("focus-out-event", lambda *_: GLib.timeout_add(150, self.maybe_close))
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
        C.styled(outer, "quick")
        frame = Gtk.Box(margin=0)
        frame.pack_start(outer, True, True, 0)
        self.add(frame)

        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        cfg = C.load_appearance()
        vpns = vpn_connections()
        has_wifi = wifi_device()
        bt = bluetooth_present()
        profile = (open("/etc/claudius/profile").read().strip() if os.path.exists("/etc/claudius/profile") else "auto")
        dnd = C.xfconf("xfce4-notifyd", "/do-not-disturb") == "true"
        tiles = [
            Tile("network-wireless", "Wi-Fi", self.t_wifi, has_wifi and wifi_on(), has_wifi, "" if has_wifi else "no adapter"),
            Tile("bluetooth", "Bluetooth", self.t_bt, bt and bluetooth_on(), bt, "" if bt else "no adapter"),
            Tile("airplane-mode", "Airplane", self.t_air, nm("radio", "all").count("disabled") >= 1 and has_wifi and not wifi_on()),
            Tile("night-light", "Night light", self.t_night, flag("nightlight")),
            Tile("battery-low", "Battery saver", self.t_saver, profile == "lite"),
            Tile("weather-clear-night", "Dark mode", self.t_dark, cfg["mode"] == "dark"),
            Tile("network-vpn", "VPN", self.t_vpn, any(a for _n, a in vpns), True, vpns[0][0] if vpns else "add…"),
            Tile("notification-disabled", "Do not disturb", self.t_dnd, dnd),
            Tile("camera-photo", "Capture", lambda *_: (C.launch("claudius-capture"), self.destroy())),
        ]
        for i, t in enumerate(tiles):
            grid.attach(t, i % 3, i // 3, 1, 1)
        outer.pack_start(grid, False, False, 0)

        # sliders
        vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 150, 1)
        vol.set_value(volume())
        vol.set_draw_value(False)
        vol.connect("value-changed", lambda s: C.sh(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(s.get_value())}%"]))
        mute = Gtk.Button.new_from_icon_name("audio-volume-muted" if muted() else "audio-volume-high", Gtk.IconSize.BUTTON)
        mute.set_relief(Gtk.ReliefStyle.NONE)
        mute.connect("clicked", lambda *_: C.sh(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]))
        row = Gtk.Box(spacing=8)
        row.pack_start(mute, False, False, 0)
        row.pack_start(vol, True, True, 0)
        outer.pack_start(row, False, False, 0)
        pct, kind = backlight()
        bri = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 100, 1)
        bri.set_value(pct)
        bri.set_draw_value(False)
        bri.connect("value-changed", lambda s: set_brightness(int(s.get_value()), kind))
        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Image.new_from_icon_name("display-brightness", Gtk.IconSize.BUTTON), False, False, 6)
        row.pack_start(bri, True, True, 0)
        outer.pack_start(row, False, False, 0)

        # notification centre
        head = Gtk.Box(spacing=8)
        head.pack_start(C.label("Notifications", "h2"), True, True, 0)
        head.pack_end(C.button("Clear all", self.clear), False, False, 0)
        outer.pack_start(head, False, False, 0)
        self.notes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sw.set_size_request(-1, 220 if notifications_first else 150)
        sw.add(self.notes)
        outer.pack_start(sw, False, False, 0)
        self.fill_notes()

        # footer
        foot = Gtk.Box(spacing=6)
        user = os.environ.get("USER", "")
        foot.pack_start(C.label(f"{user}  ·  {time.strftime('%a %d %b  %H:%M')}", "dim"), True, True, 0)
        for icon, tip, cmd in (("preferences-system", "Settings", ["claudius-center"]),
                               ("system-lock-screen", "Lock", ["xflock4"]),
                               ("system-shutdown", "Power", ["xfce4-session-logout"])):
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            b.set_tooltip_text(tip)
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.connect("clicked", lambda _b, c=cmd: (C.launch(c), self.destroy()))
            foot.pack_end(b, False, False, 0)
        outer.pack_start(foot, False, False, 0)
        self.show_all()
        self.place()

    def place(self):
        screen = Gdk.Screen.get_default()
        _w, h = self.get_size()
        self.move(screen.get_width() - 400 - 12, max(12, screen.get_height() - h - 56))

    def maybe_close(self):
        if not self.is_active():
            self.destroy()
        return False

    def fill_notes(self):
        for c in self.notes.get_children():
            self.notes.remove(c)
        items = notification_log()
        if not items:
            self.notes.pack_start(C.label("No new notifications", "dim"), False, False, 0)
        for _t, app, summary, body in items[:30]:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            C.styled(box, "notif")
            box.pack_start(C.label(summary, "card-title", wrap=True), False, False, 0)
            if body:
                box.pack_start(C.label(body[:200], "dim", wrap=True), False, False, 0)
            if app:
                box.pack_start(C.label(app, "dim"), False, False, 0)
            self.notes.pack_start(box, False, False, 0)
        self.notes.show_all()

    def clear(self):
        clear_notifications()
        self.fill_notes()

    # ------------------------------------------------------------------ tile actions
    def t_wifi(self, t):
        C.sh(["nmcli", "radio", "wifi", "off" if t.on else "on"])
        t.set_state(wifi_on())

    def t_bt(self, t):
        C.helper(["rfkill", "bluetooth", "off" if t.on else "on"], on_done=lambda rc: t.set_state(bluetooth_on()))

    def t_air(self, t):
        turn_off = not t.on
        C.sh(["nmcli", "radio", "all", "off" if turn_off else "on"])
        if bluetooth_present():
            C.helper(["rfkill", "all", "off" if turn_off else "on"])
        t.set_state(turn_off)

    def t_night(self, t):
        if t.on:
            C.sh(["redshift", "-x"])
        else:
            C.sh(["redshift", "-P", "-O", "4200"])
        set_flag("nightlight", not t.on)
        t.set_state(not t.on)

    def t_saver(self, t):
        new = "auto" if t.on else "lite"
        if C.have("powerprofilesctl"):
            C.sh(["powerprofilesctl", "set", "balanced" if t.on else "power-saver"])
        C.helper(["profile", new], on_done=lambda rc: t.set_state(new == "lite" if rc == 0 else t.on))

    def t_dark(self, t):
        cfg = C.load_appearance()
        cfg["mode"] = "light" if t.on else "dark"
        C.apply_appearance(cfg)
        t.set_state(cfg["mode"] == "dark")

    def t_vpn(self, t):
        vpns = vpn_connections()
        if not vpns:
            C.launch("nm-connection-editor")
            self.destroy()
            return
        name, active = vpns[0]
        C.run_async(["nmcli", "connection", "down" if active else "up", name],
                    on_done=lambda rc: t.set_state(any(a for _n, a in vpn_connections())))

    def t_dnd(self, t):
        C.xfconf("xfce4-notifyd", "/do-not-disturb", not t.on)
        t.set_state(not t.on)


def main():
    # toggle: a second press closes the open panel
    try:
        pid = int(open(PIDFILE).read())
        os.kill(pid, 15)
        os.remove(PIDFILE)
        return
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    prov = C.install_css()
    extra = Gtk.CssProvider()
    extra.load_from_data((f"@define-color accent {C.accent_hex()};" + CSS_EXTRA).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), extra, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
    win = Quick("--notifications" in sys.argv)
    win.connect("destroy", Gtk.main_quit)
    try:
        Gtk.main()
    finally:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass
    del prov


if __name__ == "__main__":
    main()
