"""System Monitor: CPU, RAM, GPU, disk, temperatures, battery, processes, startup apps, slowdown check."""
import glob
import math
import os
import shutil
import signal
import time
from collections import deque

import common as C
from common import GLib, Gtk
from page import Page

HZ = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")


# ---------------------------------------------------------------------------- readers
def cpu_times():
    with open("/proc/stat") as fh:
        v = [int(x) for x in fh.readline().split()[1:]]
    idle = v[3] + (v[4] if len(v) > 4 else 0)
    return sum(v), idle


def net_bytes():
    rx = tx = 0
    try:
        for line in open("/proc/net/dev").readlines()[2:]:
            name, data = line.split(":", 1)
            if name.strip() == "lo":
                continue
            f = data.split()
            rx += int(f[0])
            tx += int(f[8])
    except (OSError, ValueError, IndexError):
        pass
    return rx, tx


def disk_bytes():
    rd = wr = 0
    try:
        for line in open("/proc/diskstats"):
            f = line.split()
            if len(f) > 9 and (f[2].startswith(("sd", "vd", "nvme", "mmcblk")) and not f[2][-1].isdigit()
                               or f[2].startswith("nvme") and "p" not in f[2][4:]):
                rd += int(f[5]) * 512
                wr += int(f[9]) * 512
    except (OSError, ValueError):
        pass
    return rd, wr


def temperatures():
    temps = []
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            name = open(os.path.join(hw, "name")).read().strip()
        except OSError:
            name = "sensor"
        for t in glob.glob(os.path.join(hw, "temp*_input")):
            try:
                val = int(open(t).read()) / 1000
                lab_file = t.replace("_input", "_label")
                lab = open(lab_file).read().strip() if os.path.exists(lab_file) else name
                if 0 < val < 150:
                    temps.append((f"{name}: {lab}" if lab != name else name, val))
            except (OSError, ValueError):
                pass
    if not temps:
        for z in glob.glob("/sys/class/thermal/thermal_zone*"):
            try:
                temps.append((open(os.path.join(z, "type")).read().strip(), int(open(os.path.join(z, "temp")).read()) / 1000))
            except (OSError, ValueError):
                pass
    return temps


def batteries():
    out = []
    for b in glob.glob("/sys/class/power_supply/BAT*"):
        def rd(name, d=None):
            try:
                return open(os.path.join(b, name)).read().strip()
            except OSError:
                return d
        full = rd("energy_full") or rd("charge_full")
        design = rd("energy_full_design") or rd("charge_full_design")
        health = round(100 * int(full) / int(design)) if full and design and int(design) else None
        out.append({"name": os.path.basename(b), "capacity": rd("capacity", "?"), "status": rd("status", "?"),
                    "health": health, "cycles": rd("cycle_count")})
    return out


def gpu_info():
    name = next((l.split(": ", 1)[-1] for l in C.sh("lspci").splitlines() if "VGA" in l or "3D" in l), "unknown")
    busy = None
    for f in glob.glob("/sys/class/drm/card*/device/gpu_busy_percent"):
        try:
            busy = int(open(f).read())
        except (OSError, ValueError):
            pass
    return name, busy


def processes():
    """[(pid, name, user_uid, cpu_ticks, rss_bytes, state)]"""
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as fh:
                raw = fh.read()
            name = raw[raw.index("(") + 1:raw.rindex(")")]
            f = raw[raw.rindex(")") + 2:].split()
            ticks = int(f[11]) + int(f[12])
            rss = int(f[21]) * PAGE
            uid = os.stat(f"/proc/{d}").st_uid
            out.append((int(d), name, uid, ticks, rss, f[0]))
        except (OSError, ValueError, IndexError):
            pass
    return out


# ---------------------------------------------------------------------------- startup apps (also used by Desktop)
def autostart_entries():
    entries = {}
    dirs = ["/etc/xdg/autostart", os.path.expanduser("~/.config/autostart")]
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.desktop")):
            data = {}
            try:
                for line in open(f, errors="replace"):
                    if "=" in line and not line.startswith("#"):
                        k, v = line.rstrip("\n").split("=", 1)
                        data.setdefault(k, v)
            except OSError:
                continue
            base = os.path.basename(f)
            prev = entries.get(base, {})
            prev.update(data)
            prev["_file"] = base
            entries[base] = prev
    out = []
    for base, e in sorted(entries.items()):
        if e.get("NoDisplay") == "true" and base.startswith("claudius-"):
            continue  # Claudius' own plumbing
        only = e.get("OnlyShowIn", "")
        if only and "XFCE" not in only:
            continue
        if "XFCE" in e.get("NotShowIn", ""):
            continue
        out.append((base, e.get("Name", base), e.get("Comment", ""), e.get("Hidden", "false") != "true"))
    return out


def set_autostart(base, enabled):
    d = os.path.expanduser("~/.config/autostart")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, base)
    src = path if os.path.exists(path) else os.path.join("/etc/xdg/autostart", base)
    lines = []
    try:
        lines = [l for l in open(src, errors="replace") if not l.startswith("Hidden=")]
    except OSError:
        lines = ["[Desktop Entry]\n", "Type=Application\n", f"Name={base}\n"]
    lines.append(f"Hidden={'false' if enabled else 'true'}\n")
    with open(path, "w") as fh:
        fh.writelines(lines)


def startup_rows():
    rows = []
    for base, name, comment, enabled in autostart_entries():
        box = Gtk.Box(spacing=14)
        C.styled(box, "card")
        t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        t.pack_start(C.label(name, "card-title"), False, False, 0)
        if comment:
            t.pack_start(C.label(comment, "dim", wrap=True), False, False, 0)
        box.pack_start(t, True, True, 0)
        sw = Gtk.Switch(active=enabled, valign=Gtk.Align.CENTER)
        sw.connect("state-set", lambda _s, st, b=base: set_autostart(b, st) or False)
        box.pack_end(sw, False, False, 0)
        rows.append(box)
    return rows


# ---------------------------------------------------------------------------- graph widget
class Graph(Gtk.DrawingArea):
    def __init__(self, title, color, maximum=100.0, unit="%", series=1):
        super().__init__()
        self.set_size_request(240, 110)
        self.title, self.color, self.maximum, self.unit = title, color, maximum, unit
        self.data = [deque([0.0] * 60, maxlen=60) for _ in range(series)]
        self.text = ""
        self.connect("draw", self.on_draw)

    def push(self, *vals, text=""):
        for d, v in zip(self.data, vals):
            d.append(v)
        self.text = text
        self.queue_draw()

    def on_draw(self, _w, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cr.set_source_rgb(0.086, 0.11, 0.21)
        r = 12
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()
        top = max([self.maximum] + [max(d) for d in self.data]) if self.unit != "%" else 100.0
        colors = [self.color, (0.65, 0.48, 1.0)]
        for i, d in enumerate(self.data):
            cr.set_source_rgba(*colors[i % 2], 0.95)
            cr.set_line_width(2)
            for j, v in enumerate(d):
                x = 10 + (w - 20) * j / (len(d) - 1)
                y = h - 10 - (h - 44) * (v / top if top else 0)
                (cr.move_to if j == 0 else cr.line_to)(x, y)
            cr.stroke()
        cr.set_source_rgb(1, 1, 1)
        cr.select_font_face("Cantarell", 0, 1)
        cr.set_font_size(13)
        cr.move_to(12, 20)
        cr.show_text(self.title)
        cr.set_source_rgba(0.78, 0.8, 0.88, 1)
        cr.select_font_face("Cantarell", 0, 0)
        cr.move_to(12, 36)
        cr.show_text(self.text)
        return False


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------------------------------------------------------------------------- the page
class MonitorPage(Page):
    title = "System Monitor"
    subtitle = "Live view of your computer. Select a process and click End if it stops responding."

    def build(self):
        acc = C.accent_hex()
        rgb = tuple(int(acc[i:i + 2], 16) / 255 for i in (1, 3, 5))
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        self.g_cpu = Graph("CPU", rgb)
        self.g_ram = Graph("Memory", rgb)
        self.g_net = Graph("Network (down / up)", rgb, maximum=1024 * 64, unit="B/s", series=2)
        self.g_disk = Graph("Disk (read / write)", rgb, maximum=1024 * 256, unit="B/s", series=2)
        for i, g in enumerate((self.g_cpu, self.g_ram, self.g_net, self.g_disk)):
            grid.attach(g, i % 2, i // 2, 1, 1)
        self.put(grid)

        self.facts = Gtk.Grid(column_spacing=24, row_spacing=6)
        self.put(C.card(self.facts))

        self.section("What's slowing my PC down?")
        self.advice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.put(self.advice)

        self.section("Processes", "Sorted by CPU use. CPU % is per core (200 % means two full cores).")
        bar = Gtk.Box(spacing=8)
        self.mine_only = Gtk.CheckButton(label="Only my apps", active=True)
        bar.pack_start(self.mine_only, False, False, 0)
        bar.pack_end(C.button("Force quit", lambda: self.kill(signal.SIGKILL)), False, False, 0)
        bar.pack_end(C.button("End process", lambda: self.kill(signal.SIGTERM), "accent-btn"), False, False, 0)
        self.put(bar)
        self.store = Gtk.ListStore(int, str, float, str, str, float)  # pid, name, cpu, mem text, state, mem bytes
        self.tree = Gtk.TreeView(model=self.store)
        for i, (title, col) in enumerate((("Process", 1), ("CPU %", 2), ("Memory", 3), ("PID", 0), ("State", 4))):
            cell = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, cell, text=col)
            column.set_sort_column_id(5 if col == 3 else col)
            column.set_expand(i == 0)
            self.tree.append_column(column)
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(-1, 300)
        sw.add(self.tree)
        self.put(sw)
        self.kill_status = C.label("", "dim")
        self.put(self.kill_status)

        self.section("Startup apps", "Turn off what you don't need right after logging in.")
        for w in startup_rows():
            self.put(w)

        self.prev_cpu = cpu_times()
        self.prev_net = net_bytes()
        self.prev_disk = disk_bytes()
        self.prev_proc = {}
        self.prev_t = time.monotonic()
        self.busy_hist = {}
        self.tick = 0
        self.timer = None

    def on_show(self):
        if self.timer is None:
            self.update()
            self.timer = GLib.timeout_add(1000, self.update)
        return False

    def update(self):
        if not self.get_mapped():
            self.timer = None
            return False
        now = time.monotonic()
        dt = max(0.2, now - self.prev_t)
        tot, idle = cpu_times()
        ptot, pidle = self.prev_cpu
        cpu = 100 * (1 - (idle - pidle) / max(1, tot - ptot))
        self.prev_cpu = (tot, idle)
        mem = C.meminfo()
        used = mem.get("MemTotal", 1) - mem.get("MemAvailable", 0)
        ram = 100 * used / max(1, mem.get("MemTotal", 1))
        rx, tx = net_bytes()
        rd, wr = disk_bytes()
        drx, dtx = (rx - self.prev_net[0]) / dt, (tx - self.prev_net[1]) / dt
        drd, dwr = (rd - self.prev_disk[0]) / dt, (wr - self.prev_disk[1]) / dt
        self.prev_net, self.prev_disk = (rx, tx), (rd, wr)
        self.g_cpu.push(cpu, text=f"{cpu:.0f} % of {os.cpu_count()} cores")
        self.g_ram.push(ram, text=f"{human(used * 1024)} of {human(mem.get('MemTotal', 0) * 1024)}")
        self.g_net.push(drx, dtx, text=f"↓ {human(drx)}/s   ↑ {human(dtx)}/s")
        self.g_disk.push(drd, dwr, text=f"read {human(drd)}/s   write {human(dwr)}/s")

        procs = processes()
        rows = []
        cores = os.cpu_count() or 1
        for pid, name, uid, ticks, rss, state in procs:
            p = self.prev_proc.get(pid)
            pcpu = 100 * (ticks - p) / HZ / dt if p is not None else 0.0
            rows.append((pid, name, uid, pcpu, rss, state))
        self.prev_proc = {r[0]: r[3] for r in procs}
        self.prev_t = now
        mine = self.mine_only.get_active()
        uid = os.getuid()
        rows.sort(key=lambda r: (-r[3], -r[4]))
        sel = self.selected_pid()
        self.store.clear()
        states = {"R": "running", "S": "sleeping", "D": "waiting for disk", "Z": "zombie", "T": "stopped", "I": "idle"}
        for pid, name, puid, pcpu, rss, state in rows[:120]:
            if mine and puid != uid:
                continue
            it = self.store.append([pid, name, round(pcpu, 1), human(rss), states.get(state, state), float(rss)])
            if pid == sel:
                self.tree.get_selection().select_iter(it)

        # remember who keeps the CPU busy
        for pid, name, _u, pcpu, _r, _s in rows[:5]:
            h = self.busy_hist.setdefault(name, deque(maxlen=10))
            h.append(pcpu)
        self.tick += 1
        if self.tick % 3 == 1:
            self.update_facts(cpu, ram, mem)
            self.update_advice(cpu, ram, mem, rows, cores)
        return True

    def update_facts(self, cpu, ram, mem):
        for c in self.facts.get_children():
            self.facts.remove(c)
        gname, gbusy = gpu_info()
        du = shutil.disk_usage("/")
        facts = [("Graphics", gname + (f" · {gbusy} % busy" if gbusy is not None else ""))]
        facts.append(("Disk (/)", f"{human(du.used)} used of {human(du.total)} ({100 * du.used / du.total:.0f} %)"))
        swap_used = mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)
        facts.append(("Swap (zram)", f"{human(swap_used * 1024)} of {human(mem.get('SwapTotal', 0) * 1024)}"))
        temps = temperatures()
        facts.append(("Temperatures", ", ".join(f"{n} {v:.0f} °C" for n, v in temps[:4]) if temps
                      else "not reported (normal in a virtual machine)"))
        bats = batteries()
        for b in bats:
            h = f", health {b['health']} %" if b["health"] is not None else ""
            cyc = f", {b['cycles']} cycles" if b.get("cycles") not in (None, "0") else ""
            facts.append((f"Battery {b['name']}", f"{b['capacity']} % ({b['status']}){h}{cyc}"))
        if not bats:
            facts.append(("Battery", "none (desktop or virtual machine)"))
        up = float(open("/proc/uptime").read().split()[0])
        facts.append(("Up for", f"{int(up // 3600)} h {int(up % 3600 // 60)} min"))
        for i, (k, v) in enumerate(facts):
            self.facts.attach(C.label(k, "dim"), 0, i, 1, 1)
            self.facts.attach(C.label(v, wrap=True), 1, i, 1, 1)
        self.facts.show_all()

    def update_advice(self, cpu, ram, mem, rows, cores):
        tips = []
        hogs = [(n, sum(h) / len(h)) for n, h in self.busy_hist.items() if len(h) >= 3 and sum(h) / len(h) > 60]
        for n, avg in sorted(hogs, key=lambda x: -x[1])[:2]:
            tips.append(("warn", f"“{n}” keeps the CPU busy (about {avg:.0f} %). If it's stuck, select it below and click End."))
        if ram > 85:
            big = max(rows, key=lambda r: r[4]) if rows else None
            tips.append(("bad", f"Memory is almost full ({ram:.0f} %)." + (f" The biggest user is “{big[1]}” ({human(big[4])})." if big else "")
                         + " Close apps or tabs you don't need."))
        swap_used = mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)
        if swap_used > 0.5 * max(1, mem.get("SwapTotal", 1)):
            tips.append(("warn", "A lot of memory is being compressed into swap. More RAM for the VM would make things faster."))
        du = shutil.disk_usage("/")
        if du.used / du.total > 0.9:
            tips.append(("bad", "Your disk is more than 90 % full. Run 'claudius clean' or remove apps you don't use."))
        hot = [(n, v) for n, v in temperatures() if v > 85]
        if hot:
            tips.append(("bad", f"{hot[0][0]} is hot ({hot[0][1]:.0f} °C). Check the fans and air vents."))
        n_start = sum(1 for e in autostart_entries() if e[3])
        if n_start > 10:
            tips.append(("warn", f"{n_start} apps start at login. Turning some off (below) makes start-up faster."))
        if not tips:
            tips.append(("ok", "Nothing is slowing your computer down right now."))
        for c in self.advice.get_children():
            self.advice.remove(c)
        for cls, text in tips:
            box = Gtk.Box(spacing=12)
            box.pack_start(C.label({"ok": "✔", "warn": "!", "bad": "✖"}[cls], cls), False, False, 0)
            box.pack_start(C.label(text, wrap=True), True, True, 0)
            self.advice.pack_start(C.card(box, orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        self.advice.show_all()

    def selected_pid(self):
        model, it = self.tree.get_selection().get_selected()
        return model[it][0] if it else None

    def kill(self, sig):
        pid = self.selected_pid()
        if pid is None:
            self.kill_status.set_text("Select a process first.")
            return
        try:
            os.kill(pid, sig)
            self.kill_status.set_text(f"Sent {'end' if sig == signal.SIGTERM else 'force quit'} to process {pid}.")
        except PermissionError:
            self.kill_status.set_text("That process belongs to the system. Use 'sudo kill' in a terminal if you're sure.")
        except ProcessLookupError:
            self.kill_status.set_text("That process has already ended.")
