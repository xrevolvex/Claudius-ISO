#!/usr/bin/env python3
"""Claudius Launcher: search apps, files and settings, calculate, run commands.

    claudius-launcher          Spotlight-style search (Super)
    claudius-launcher --grid   full-screen app grid (Super+A)

Tips:  =2*21  calculate   >htop  run in a terminal   ?query  search the web
       Ctrl+P pin or unpin an app   Ctrl+1..9 open a pinned app
"""
import ast
import json
import math
import operator
import os
import subprocess
import sys
import threading

sys.path.insert(0, "/usr/lib/claudius/center")
import common as C  # noqa: E402
from common import Gdk, GLib, Gtk  # noqa: E402
import gi  # noqa: E402

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

CONF = os.path.join(C.CONFIG_DIR, "launcher.json")
PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claudius-launcher.pid")
DEFAULT_PINS = ["firefox-esr.desktop", "thunar.desktop", "xfce4-terminal.desktop", "libreoffice-writer.desktop",
                "org.thonny.Thonny.desktop", "claudius-center.desktop"]
CENTER_PAGES = [  # (title, keywords, page)
    ("Appearance", "theme accent dark light wallpaper colour color", "appearance"),
    ("Desktop layout", "layout dock taskbar windows macos ubuntu workspaces tiling shortcuts startup", "desktop"),
    ("Display and refresh rate", "screen resolution hz 144 refresh monitor", "display"),
    ("Performance profile", "ram memory speed profile zram fast", "performance"),
    ("Update Center", "update upgrade security restart history", "updates"),
    ("App Center", "install apps store software", "apps"),
    ("Packs", "developer gaming steam docker vm remote desktop power", "packs"),
    ("Security Center", "firewall security encryption permissions ports", "security"),
    ("Restore & Backup", "backup restore snapshot timeshift", "backup"),
    ("System Monitor", "task manager processes cpu ram temperature battery slow kill", "monitor"),
    ("Drivers", "drivers guest additions virtualbox firmware gpu", "drivers"),
]

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg,
       ast.UAdd: operator.pos}
FUNCS = {k: getattr(math, k) for k in ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil")}
FUNCS.update(abs=abs, round=round, pi=math.pi, e=math.e)


def calc(expr):
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", ".")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            if isinstance(n.op, ast.Pow) and abs(ev(n.right)) > 1000:
                raise ValueError
            return OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name) and n.id in FUNCS and not callable(FUNCS[n.id]):
            return FUNCS[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and len(n.args) == 1:
            return FUNCS[n.func.id](ev(n.args[0]))
        raise ValueError
    try:
        v = ev(ast.parse(expr, mode="eval"))
        if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
            v = int(v)
        return f"{v:,.10g}".replace(",", " ") if isinstance(v, float) else f"{v:,}".replace(",", " ")
    except Exception:  # noqa: BLE001
        return None


def load_conf():
    try:
        with open(CONF) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"pins": DEFAULT_PINS}


def save_conf(conf):
    os.makedirs(C.CONFIG_DIR, exist_ok=True)
    with open(CONF, "w") as fh:
        json.dump(conf, fh, indent=2)


def all_apps():
    apps = [a for a in Gio.AppInfo.get_all() if a.should_show()]
    return sorted(apps, key=lambda a: a.get_display_name().lower())


def score(app, q):
    name = app.get_display_name().lower()
    if name.startswith(q):
        return 100
    if q in name:
        return 80
    words = name.split()
    if "".join(w[0] for w in words if w).startswith(q):
        return 70
    extra = " ".join(filter(None, [app.get_description() or "", app.get_executable() or "",
                                   " ".join(app.get_keywords() if hasattr(app, "get_keywords") and app.get_keywords() else [])])).lower()
    return 40 if q in extra else 0


def find_files(q, limit=12):
    if C.have("plocate") and os.path.exists("/var/lib/plocate/plocate.db"):
        out = C.sh(["plocate", "-i", "-l", "40", "--basename", q], timeout=3).splitlines()
        home = os.path.expanduser("~")
        out = [p for p in out if p.startswith(home) and "/." not in p[len(home):]]
        if out:
            return out[:limit]
    res = []
    home = os.path.expanduser("~")
    for root, dirs, files in os.walk(home):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "snap")]
        if root.count(os.sep) - home.count(os.sep) > 5:
            dirs[:] = []
        for f in files + dirs:
            if q in f.lower():
                res.append(os.path.join(root, f))
                if len(res) >= limit:
                    return res
    return res


class Result:
    def __init__(self, title, sub, icon, action, app_id=None):
        self.title, self.sub, self.icon, self.action, self.app_id = title, sub, icon, action, app_id


def gicon_image(icon, size):
    if isinstance(icon, str):
        img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
    elif icon is not None:
        img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)
    else:
        img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
    img.set_pixel_size(size)
    return img


CSS_EXTRA = """
.launcher { background-color: #121830; border: 1px solid #2a3462; border-radius: 18px; }
.launcher entry { background-color: transparent; border: none; box-shadow: none; color: #ffffff; font-size: 22px; padding: 10px 6px; }
.launcher list, .launcher row { background-color: transparent; }
.launcher row { border-radius: 10px; padding: 6px 8px; }
.launcher row:selected { background-color: alpha(@accent, 0.22); }
.grid-win { background-color: rgba(10, 14, 28, 0.97); }
.grid-app { background-image: none; background-color: transparent; border: none; box-shadow: none; border-radius: 14px; padding: 10px; }
.grid-app:hover { background-color: alpha(@accent, 0.18); }
.grid-app label { color: #e6e9f2; }
"""


class Launcher(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_default_size(680, -1)
        self.conf = load_conf()
        self.apps = all_apps()
        self.by_id = {a.get_id(): a for a in self.apps}
        self.file_gen = 0
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=14)
        C.styled(box, "launcher")
        self.add(box)
        top = Gtk.Box(spacing=10)
        logo = Gtk.Image.new_from_icon_name("system-search", Gtk.IconSize.DND)
        top.pack_start(logo, False, False, 6)
        self.entry = Gtk.Entry(placeholder_text="Search apps, files, settings…   (= calculate, > command, ? web)")
        self.entry.connect("changed", lambda *_: self.search())
        self.entry.connect("activate", lambda *_: self.activate())
        top.pack_start(self.entry, True, True, 0)
        box.pack_start(top, False, False, 0)
        self.list = Gtk.ListBox()
        self.list.connect("row-activated", lambda _l, row: self.run(row.result))
        box.pack_start(self.list, False, False, 0)
        self.hint = C.label("Ctrl+P pin · Ctrl+1–9 open a pin · Esc close", "dim")
        box.pack_start(self.hint, False, False, 0)
        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", lambda *_: GLib.timeout_add(150, self.maybe_close))
        self.search()
        self.show_all()
        screen = Gdk.Screen.get_default()
        self.move((screen.get_width() - 680) // 2, int(screen.get_height() * 0.18))
        self.present()
        self.entry.grab_focus()

    def maybe_close(self):
        if not self.is_active():
            self.destroy()
        return False

    # ------------------------------------------------------------------ results
    def app_result(self, a):
        return Result(a.get_display_name(), a.get_description() or "", a.get_icon(), lambda: a.launch([], None), a.get_id())

    def search(self):
        q = self.entry.get_text().strip()
        ql = q.lower()
        results = []
        if not q:
            for pid in self.conf.get("pins", []):
                if pid in self.by_id:
                    r = self.app_result(self.by_id[pid])
                    r.sub = "Pinned"
                    results.append(r)
        elif q.startswith(">"):
            cmd = q[1:].strip()
            results.append(Result(f"Run: {cmd}", "in a terminal", "utilities-terminal",
                                  lambda: C.launch(["xfce4-terminal", "--hold", "-x", "bash", "-lc", cmd])))
        elif q.startswith("?"):
            results.append(self.web(q[1:].strip()))
        else:
            val = calc(q.lstrip("="))
            if val is not None and (q.startswith("=") or any(ch in q for ch in "+-*/^%()")):
                results.append(Result(f"= {val}", "Enter copies the result", "accessories-calculator",
                                      lambda v=val: self.copy(v.replace(" ", ""))))
            scored = sorted(((score(a, ql), a) for a in self.apps), key=lambda x: -x[0])
            results += [self.app_result(a) for s, a in scored if s > 0][:6]
            for title, kw, page in CENTER_PAGES:
                if ql in title.lower() or any(w.startswith(ql) for w in kw.split()):
                    results.append(Result(title, "Claudius Center", "preferences-system",
                                          lambda p=page: C.launch(["claudius-center", "--page", p])))
            results = results[:9]
            results.append(self.web(q))
            if len(ql) >= 3:
                self.find_files_async(ql)
        self.show_results(results)

    def web(self, q):
        url = "https://duckduckgo.com/?q=" + GLib.uri_escape_string(q, None, True)
        return Result(f"Search the web for “{q}”", "DuckDuckGo", "web-browser", lambda: C.launch(["xdg-open", url]))

    def find_files_async(self, q):
        self.file_gen += 1
        gen = self.file_gen

        def work():
            files = find_files(q)
            GLib.idle_add(self.add_files, gen, files)
        threading.Thread(target=work, daemon=True).start()

    def add_files(self, gen, files):
        if gen != self.file_gen:
            return False
        for path in files[:6]:
            ctype = Gio.content_type_guess(path, None)[0]
            icon = Gio.content_type_get_icon(ctype) if ctype else "text-x-generic"
            self.add_row(Result(os.path.basename(path), path.replace(os.path.expanduser("~"), "~", 1), icon,
                                lambda p=path: C.launch(["xdg-open", p])))
        self.list.show_all()
        return False

    def show_results(self, results):
        for c in self.list.get_children():
            self.list.remove(c)
        for r in results:
            self.add_row(r)
        self.list.show_all()
        first = self.list.get_row_at_index(0)
        if first:
            self.list.select_row(first)

    def add_row(self, r):
        row = Gtk.ListBoxRow()
        row.result = r
        box = Gtk.Box(spacing=12)
        box.pack_start(gicon_image(r.icon, 32), False, False, 0)
        t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        t.pack_start(C.label(r.title, "card-title"), False, False, 0)
        if r.sub:
            t.pack_start(C.label(r.sub[:90], "dim"), False, False, 0)
        box.pack_start(t, True, True, 0)
        row.add(box)
        self.list.add(row)

    # ------------------------------------------------------------------ actions
    def copy(self, text):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).store()

    def run(self, r):
        try:
            r.action()
        except Exception as err:  # noqa: BLE001
            print(err, file=sys.stderr)
        GLib.timeout_add(120, self.destroy)

    def activate(self):
        row = self.list.get_selected_row()
        if row:
            self.run(row.result)

    def on_key(self, _w, ev):
        ctrl = ev.state & Gdk.ModifierType.CONTROL_MASK
        if ev.keyval == Gdk.KEY_Escape:
            self.destroy()
        elif ev.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            row = self.list.get_selected_row()
            i = (row.get_index() if row else -1) + (1 if ev.keyval == Gdk.KEY_Down else -1)
            nxt = self.list.get_row_at_index(max(0, i))
            if nxt:
                self.list.select_row(nxt)
            return True
        elif ctrl and ev.keyval in (Gdk.KEY_p, Gdk.KEY_P):
            row = self.list.get_selected_row()
            if row and row.result.app_id:
                pins = self.conf.setdefault("pins", [])
                (pins.remove if row.result.app_id in pins else pins.append)(row.result.app_id)
                save_conf(self.conf)
                self.hint.set_text("Pinned" if row.result.app_id in pins else "Unpinned")
                self.search()
            return True
        elif ctrl and Gdk.KEY_1 <= ev.keyval <= Gdk.KEY_9:
            pins = [p for p in self.conf.get("pins", []) if p in self.by_id]
            i = ev.keyval - Gdk.KEY_1
            if i < len(pins):
                self.run(self.app_result(self.by_id[pins[i]]))
            return True
        return False


class Grid(Gtk.Window):
    """Full-screen app grid."""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        C.styled(self, "grid-win")
        screen = Gdk.Screen.get_default()
        self.set_default_size(screen.get_width(), screen.get_height())
        self.move(0, 0)
        self.fullscreen()
        self.connect("key-press-event", lambda _w, e: e.keyval == Gdk.KEY_Escape and self.destroy())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin=40)
        self.add(box)
        self.entry = Gtk.SearchEntry(placeholder_text="Type to search", halign=Gtk.Align.CENTER, width_chars=40)
        self.entry.connect("search-changed", lambda *_: self.flow.invalidate_filter())
        box.pack_start(self.entry, False, False, 0)
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=8, min_children_per_line=4,
                                column_spacing=16, row_spacing=16, homogeneous=True)
        self.flow.set_filter_func(self.filter)
        for a in all_apps():
            b = Gtk.Button()
            C.styled(b, "grid-app")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            v.pack_start(gicon_image(a.get_icon(), 64), False, False, 0)
            lab = Gtk.Label(label=a.get_display_name(), max_width_chars=14, ellipsize=3, justify=Gtk.Justification.CENTER)
            v.pack_start(lab, False, False, 0)
            b.add(v)
            b.app = a
            b.connect("clicked", lambda btn: (btn.app.launch([], None), self.destroy()))
            self.flow.add(b)
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sw.add(self.flow)
        box.pack_start(sw, True, True, 0)
        box.pack_start(C.label("Esc closes", "dim", xalign=0.5), False, False, 0)
        self.connect("button-press-event", lambda *_: None)
        self.show_all()
        self.entry.grab_focus()

    def filter(self, child):
        q = self.entry.get_text().lower().strip()
        return not q or q in child.get_child().app.get_display_name().lower()


def main():
    try:  # pressing the shortcut again closes it
        pid = int(open(PIDFILE).read())
        os.kill(pid, 15)
        os.remove(PIDFILE)
        return
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    C.install_css()
    extra = Gtk.CssProvider()
    extra.load_from_data((f"@define-color accent {C.accent_hex()};" + CSS_EXTRA).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), extra, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
    win = Grid() if "--grid" in sys.argv else Launcher()
    win.connect("destroy", Gtk.main_quit)
    try:
        Gtk.main()
    finally:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
