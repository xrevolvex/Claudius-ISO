"""Shared helpers for the Claudius apps (Center, Quick Settings, Launcher, Welcome)."""
import json
import os
import shlex
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

HELPER = "/usr/lib/claudius/claudius-helper"
CONFIG_DIR = os.path.expanduser("~/.config/claudius")
APPEARANCE_FILE = os.path.join(CONFIG_DIR, "appearance.json")
WALLPAPERS = "/usr/share/claudius/wallpapers"
IS_LIVE = os.path.isdir("/run/live/medium")

# accent name -> (hex colour, Yaru theme base name)
ACCENTS = {
    "orange": ("#ff9447", "Yaru"),
    "blue": ("#4c8dff", "Yaru-blue"),
    "green": ("#3ecf8e", "Yaru-viridian"),
    "teal": ("#2ec4c9", "Yaru-prussiangreen"),
    "purple": ("#a77bff", "Yaru-purple"),
    "pink": ("#ff6fb5", "Yaru-magenta"),
    "red": ("#ff5f6d", "Yaru-red"),
}
DEFAULT_APPEARANCE = {"style": "claudius", "mode": "dark", "accent": "orange", "wallpaper": "auto"}


# ---------------------------------------------------------------------------- small utilities
def read_kv(path):
    data = {}
    try:
        with open(path) as fh:
            for line in fh:
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    data[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return data


def meminfo():
    """/proc/meminfo as {key: kB}."""
    out = {}
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, v = line.split(":", 1)
                out[k] = int(v.split()[0])
    except (OSError, ValueError):
        pass
    return out


def sh(cmd, timeout=20):
    """Run a command, return its stdout ('' on any failure)."""
    try:
        args = cmd if isinstance(cmd, list) else shlex.split(cmd)
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def have(cmd):
    return any(os.access(os.path.join(p, cmd), os.X_OK) for p in os.environ.get("PATH", "/usr/bin").split(":"))


def launch(cmd):
    try:
        subprocess.Popen(cmd if isinstance(cmd, list) else shlex.split(cmd), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def apt_installed(pkg):
    out = sh(["dpkg-query", "-W", "-f=${Status}", pkg])
    return "install ok installed" in out


def flatpak_installed_ids():
    if not have("flatpak"):
        return set()
    return set(sh(["flatpak", "list", "--app", "--columns=application"]).split())


def xfconf(channel, prop, value=None, kind="string"):
    if value is None:
        return sh(["xfconf-query", "-c", channel, "-p", prop]).strip()
    if isinstance(value, bool):
        kind, value = "bool", "true" if value else "false"
    sh(["xfconf-query", "-c", channel, "-p", prop, "-n", "-t", kind, "-s", str(value)])
    return None


def run_async(argv, on_line=None, on_done=None):
    """Run argv in a thread, streaming output lines to on_line(str) and calling on_done(rc) on the GTK thread."""
    def worker():
        rc = 1
        try:
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc.stdout:
                if on_line:
                    GLib.idle_add(on_line, line.rstrip("\n"))
            rc = proc.wait()
        except OSError as err:
            if on_line:
                GLib.idle_add(on_line, str(err))
        if on_done:
            GLib.idle_add(on_done, rc)
    threading.Thread(target=worker, daemon=True).start()


def helper(args, on_line=None, on_done=None):
    """Run a privileged action through pkexec + claudius-helper."""
    run_async(["pkexec", HELPER, *args], on_line, on_done)


# ---------------------------------------------------------------------------- appearance
def load_appearance():
    cfg = dict(DEFAULT_APPEARANCE)
    try:
        with open(APPEARANCE_FILE) as fh:
            cfg.update(json.load(fh))
    except (OSError, ValueError):
        pass
    if cfg.get("accent") not in ACCENTS:
        cfg["accent"] = "orange"
    return cfg


def accent_hex(cfg=None):
    return ACCENTS[(cfg or load_appearance())["accent"]][0]


def theme_exists(name):
    return any(os.path.isdir(os.path.join(d, name)) for d in
               ("/usr/share/themes", os.path.expanduser("~/.themes"), os.path.expanduser("~/.local/share/themes")))


def icons_exist(name):
    return any(os.path.isdir(os.path.join(d, name)) for d in
               ("/usr/share/icons", os.path.expanduser("~/.icons"), os.path.expanduser("~/.local/share/icons")))


def wallpaper_for(cfg):
    if cfg.get("wallpaper") not in (None, "", "auto"):
        return cfg["wallpaper"]
    name = f"claudius-{cfg['accent']}{'-light' if cfg['mode'] == 'light' else ''}.png"
    path = os.path.join(WALLPAPERS, name)
    return path if os.path.exists(path) else os.path.join(WALLPAPERS, "claudius-default.png")


def set_wallpaper(path):
    props = [p for p in sh(["xfconf-query", "-c", "xfce4-desktop", "-l"]).split() if p.endswith("/last-image")]
    if not props:
        mons = [l.split()[0] for l in sh(["xrandr", "--query"]).splitlines() if " connected" in l]
        props = [f"/backdrop/screen0/monitor{m}/workspace{w}/last-image" for m in mons or ["0"] for w in range(4)]
    ours = path.startswith(WALLPAPERS)
    light = path.endswith("-light.png")
    rgb = ("0.933", "0.945", "0.973") if light else ("0.0706", "0.0941", "0.1882")
    for p in props:
        base = p[: -len("/last-image")]
        xfconf("xfce4-desktop", p, path)
        # Claudius wallpapers are flat: fit them on a matching colour so nothing is cropped
        xfconf("xfce4-desktop", base + "/image-style", 4 if ours else 5, "int")
        xfconf("xfce4-desktop", base + "/color-style", 0, "int")
        sh(["xfconf-query", "-c", "xfce4-desktop", "-p", base + "/rgba1", "-r"])
        sh(["xfconf-query", "-c", "xfce4-desktop", "-p", base + "/rgba1", "-n",
            "-t", "double", "-s", rgb[0], "-t", "double", "-s", rgb[1], "-t", "double", "-s", rgb[2], "-t", "double", "-s", "1"])


def apply_appearance(cfg):
    dark = cfg["mode"] == "dark"
    if cfg["style"] == "yaru":
        base = ACCENTS[cfg["accent"]][1]
        gtk = f"{base}-dark" if dark else base
        if not theme_exists(gtk):
            gtk = "Yaru-dark" if dark else "Yaru"
        icons = gtk if icons_exist(gtk) else ("Yaru-dark" if dark else "Yaru")
        if not theme_exists(gtk):
            gtk, icons = ("Arc-Dark", "Papirus-Dark") if dark else ("Arc", "Papirus")
    else:
        gtk, icons = ("Arc-Dark", "Papirus-Dark") if dark else ("Arc-Lighter", "Papirus-Light")
        if not theme_exists(gtk):
            gtk = "Arc"
        if not icons_exist(icons):
            icons = "Papirus"
    xfconf("xsettings", "/Net/ThemeName", gtk)
    xfconf("xsettings", "/Net/IconThemeName", icons)
    wm = "Arc-Dark" if dark else "Arc"
    if theme_exists(os.path.join(gtk, "xfwm4")):
        wm = gtk
    xfconf("xfwm4", "/general/theme", wm)
    xfconf("xfce4-panel", "/panels/dark-mode", dark)
    set_wallpaper(wallpaper_for(cfg))
    xfconf("xfce4-terminal", "/color-cursor", accent_hex(cfg))
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(APPEARANCE_FILE, "w") as fh:
        json.dump(cfg, fh, indent=2)


# ---------------------------------------------------------------------------- styling
def css(accent=None):
    a = accent or accent_hex()
    return f"""
    .claudius-window {{ background-color: #0f1428; }}
    .sidebar-list {{ background-color: #0b0f20; }}
    .sidebar-list row {{ padding: 10px 14px; border-radius: 10px; margin: 2px 8px; color: #c8cde0; }}
    .sidebar-list row:selected {{ background-color: alpha({a}, 0.18); color: #ffffff; }}
    .sidebar-list row:selected label {{ color: #ffffff; }}
    .page {{ padding: 28px 34px; }}
    .h1 {{ font-size: 24px; font-weight: 800; color: #ffffff; }}
    .h2 {{ font-size: 15px; font-weight: 700; color: #ffffff; }}
    .dim {{ color: #8f98bd; }}
    .card {{ background-color: #161c36; border: 1px solid #242d57; border-radius: 14px; padding: 16px; }}
    .card-title {{ font-weight: 700; color: #ffffff; }}
    .chip {{ background-color: alpha({a}, 0.16); color: {a}; border-radius: 99px; padding: 3px 10px;
             font-size: 11px; font-weight: 700; }}
    .accent-btn, button.suggested-action {{ background-image: none; background-color: {a}; color: #14100a;
             border: none; border-radius: 10px; padding: 6px 16px; font-weight: 800; box-shadow: none; text-shadow: none; }}
    .accent-btn label, button.suggested-action label {{ color: #14100a; }}
    .flat-btn {{ background-image: none; background-color: #1d2546; color: #e6e9f2; border: 1px solid #2a3462;
                 border-radius: 10px; padding: 6px 14px; box-shadow: none; text-shadow: none; }}
    .flat-btn:hover {{ background-color: #253061; }}
    .swatch {{ border-radius: 99px; min-width: 34px; min-height: 34px; padding: 0; border: 3px solid transparent;
               background-image: none; box-shadow: none; }}
    .swatch.active {{ border-color: #ffffff; }}
    .ok {{ color: #6ee7a8; font-weight: 700; }}
    .warn {{ color: #ffcc66; font-weight: 700; }}
    .bad {{ color: #ff7b7b; font-weight: 700; }}
    textview.log, textview.log text {{ background-color: #0a0e1c; color: #c8cde0; font-family: monospace; font-size: 11px; }}
    """


def install_css(accent=None):
    provider = Gtk.CssProvider()
    provider.load_from_data(css(accent).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return provider


def label(text, cls=None, xalign=0, wrap=False, markup=False, selectable=False):
    lab = Gtk.Label(xalign=xalign)
    if markup:
        lab.set_markup(text)
    else:
        lab.set_text(text)
    lab.set_line_wrap(wrap)
    lab.set_selectable(selectable)
    if cls:
        for c in cls.split():
            lab.get_style_context().add_class(c)
    return lab


def button(text, cb=None, cls="flat-btn", icon=None):
    b = Gtk.Button(label=text)
    if icon:
        b.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        b.set_always_show_image(True)
    for c in cls.split():
        b.get_style_context().add_class(c)
    if cb:
        b.connect("clicked", lambda *_: cb())
    return b


def card(*children, spacing=8, orientation=Gtk.Orientation.VERTICAL):
    box = Gtk.Box(orientation=orientation, spacing=spacing)
    box.get_style_context().add_class("card")
    for c in children:
        box.pack_start(c, False, False, 0)
    return box


def styled(widget, *classes):
    for c in classes:
        widget.get_style_context().add_class(c)
    return widget
