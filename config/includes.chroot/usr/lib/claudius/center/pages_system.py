"""Update Center, Security Center, Restore & Backup, Drivers."""
import datetime
import glob
import os
import re
import subprocess
import threading

import common as C
from common import GLib, Gtk
from page import Page


def in_thread(fn, then):
    """Run fn() in a thread and pass its result to then() on the GTK thread."""
    threading.Thread(target=lambda: GLib.idle_add(then, fn()), daemon=True).start()


def reboot_required():
    return os.path.exists("/run/reboot-required") or newer_kernel_installed()


def newer_kernel_installed():
    running = os.uname().release
    kernels = sorted(os.path.basename(p)[len("vmlinuz-"):] for p in glob.glob("/boot/vmlinuz-*"))
    return bool(kernels) and kernels[-1] != running and not C.IS_LIVE


def auto_updates_on():
    try:
        return '"1"' in open("/etc/apt/apt.conf.d/20auto-upgrades").read().split("Unattended-Upgrade")[1]
    except (OSError, IndexError):
        return False


def apt_history(limit=40):
    entries, cur = [], {}
    for path in sorted(glob.glob("/var/log/apt/history.log*")):
        if path.endswith(".gz"):
            continue
        try:
            for line in open(path, errors="replace"):
                if line.startswith("Start-Date:"):
                    cur = {"date": line.split(":", 1)[1].strip()}
                elif line.startswith(("Install:", "Upgrade:", "Remove:", "Purge:")):
                    kind, pk = line.split(":", 1)
                    names = re.findall(r"([a-z0-9][a-z0-9+.-]+):[a-z0-9]+ \(", pk)
                    cur.setdefault("changes", []).append((kind, names))
                elif line.startswith("End-Date:") and cur:
                    entries.append(cur)
                    cur = {}
        except OSError:
            pass
    return list(reversed(entries))[:limit]


# ============================================================================ Update Center
class UpdatesPage(Page):
    title = "Update Center"
    subtitle = "System and security updates from Debian, app updates from Flathub, history and restarts, in one place."

    def build(self):
        self.banner = C.label("", "warn", wrap=True)
        self.put(self.banner)
        top = Gtk.Box(spacing=10)
        self.check_btn = C.button("Check for updates", self.check, "flat-btn", "view-refresh")
        self.install_btn = C.button("Install all updates", self.install, "accent-btn")
        self.install_btn.set_sensitive(False)
        top.pack_start(self.check_btn, False, False, 0)
        top.pack_start(self.install_btn, False, False, 0)
        self.spinner = Gtk.Spinner()
        top.pack_start(self.spinner, False, False, 0)
        self.state = C.label("", "dim")
        top.pack_start(self.state, False, False, 0)
        self.put(top)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.put(C.card(self.list))
        self.exp, self.log = self.log_view()

        self.section("Restart")
        rbox = Gtk.Box(spacing=8)
        self.time = Gtk.Entry(text="03:00", width_chars=6)
        rbox.pack_start(self.time, False, False, 0)
        rbox.pack_start(C.button("Schedule", lambda: C.helper(["schedule-restart", self.time.get_text()],
                                                              self.log, lambda rc: self.state.set_text(
                                                                  f"Restart scheduled for {self.time.get_text()}" if rc == 0 else "Could not schedule"))),
                        False, False, 0)
        rbox.pack_start(C.button("Restart now", lambda: C.helper(["schedule-restart", "now"])), False, False, 0)
        rbox.pack_start(C.button("Cancel scheduled", lambda: C.helper(["cancel-restart"], self.log)), False, False, 0)
        self.row("Restart to finish updating", "Kernel and core updates take effect after a restart.", rbox)

        self.section("Settings")
        self.switch("Automatic security updates", "Install important security fixes in the background every day.",
                    auto_updates_on(), lambda st: C.helper(["auto-updates", "on" if st else "off"]))
        ar = Gtk.Box(spacing=8)
        self.ar_time = Gtk.Entry(text="03:30", width_chars=6)
        ar.pack_start(self.ar_time, False, False, 0)
        ar.pack_start(C.button("Turn on", lambda: C.helper(["auto-reboot", self.ar_time.get_text()])), False, False, 0)
        ar.pack_start(C.button("Turn off", lambda: C.helper(["auto-reboot", "off"])), False, False, 0)
        self.row("Automatic restart", "If an automatic update needs a restart, do it at this time (only when needed).", ar)
        self.switch("Snapshot before updating", "Take a Timeshift system snapshot before installing updates, so you can roll back.",
                    os.path.exists("/etc/claudius/snapshot-before-updates"),
                    lambda st: C.helper(["snapshot-before-updates", "on" if st else "off"]))
        self.row("Repair", "If an update was interrupted or failed, this finishes it and fixes broken packages.",
                 C.button("Repair updates", lambda: self.run_action(["repair"], "Repairing…")))

        self.section("History")
        self.history = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.put(C.card(self.history))

    def on_show(self):
        self.banner.set_text("A restart is needed to finish installing updates." if reboot_required() else "")
        for child in self.history.get_children():
            self.history.remove(child)
        hist = apt_history()
        if not hist:
            self.history.add(C.label("No updates have been installed yet.", "dim"))
        for e in hist:
            parts = [f"{k.lower()} {len(n)}" for k, n in e.get("changes", [])]
            names = ", ".join(sum((n for _k, n in e.get("changes", [])), [])[:6])
            self.history.add(C.label(f"{e['date']}   ·   {', '.join(parts)}   ·   {names}", wrap=True))
        self.history.show_all()
        self.list_updates()
        return False

    def list_updates(self):
        def work():
            apt = [l for l in C.sh(["apt", "list", "--upgradable"], timeout=40).splitlines() if "[upgradable" in l]
            flat = []
            if C.have("flatpak"):
                flat = [l for l in C.sh(["flatpak", "remote-ls", "--updates", "--columns=name,application"],
                                        timeout=40).splitlines() if l.strip()]
            return apt, flat

        def show(res):
            apt, flat = res
            for child in self.list.get_children():
                self.list.remove(child)
            sec = [l for l in apt if "-security" in l]
            for l in apt[:200]:
                name = l.split("/")[0]
                ver = l.split()[1] if len(l.split()) > 1 else ""
                tag = "  [security]" if "-security" in l else ""
                self.list.add(C.label(f"{name}  →  {ver}{tag}", "warn" if tag else None))
            for l in flat:
                self.list.add(C.label(f"{l}  (app from Flathub)"))
            n = len(apt) + len(flat)
            self.state.set_text(f"{n} update{'s' if n != 1 else ''} ({len(sec)} security)" if n else "Everything is up to date")
            if not n:
                self.list.add(C.label("✔  Everything is up to date", "ok"))
            self.install_btn.set_sensitive(n > 0)
            self.list.show_all()
        in_thread(work, show)

    def run_action(self, args, msg, then=None):
        self.spinner.start()
        self.state.set_text(msg)
        self.exp.set_expanded(True)

        def done(rc):
            self.spinner.stop()
            self.state.set_text("Done" if rc == 0 else "Something went wrong: see Details")
            self.on_show()
            if then:
                then(rc)
        C.helper(args, self.log, done)

    def check(self):
        self.run_action(["apt-update"], "Checking…")

    def install(self):
        self.run_action(["apt-upgrade-safe"], "Installing updates… (you can keep working)")


# ============================================================================ Security Center
class SecurityPage(Page):
    title = "Security Center"
    subtitle = "The important things at a glance, with plain-language recommendations."

    def build(self):
        self.recs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.put(self.recs)

        self.section("Firewall", "Blocks connections from other computers. Apps on this PC can still reach the internet.")
        fw = Gtk.Box(spacing=8)
        fw.pack_start(C.button("Turn on", lambda: C.helper(["firewall", "on"], None, lambda rc: self.on_show())), False, False, 0)
        fw.pack_start(C.button("Turn off", lambda: C.helper(["firewall", "off"], None, lambda rc: self.on_show())), False, False, 0)
        self.fw_state = C.label("", "dim")
        fw.pack_start(self.fw_state, False, False, 0)
        self.row("Firewall", "Recommended: on.", fw)
        rule = Gtk.Box(spacing=8)
        self.port = Gtk.Entry(placeholder_text="e.g. 22/tcp", width_chars=10)
        rule.pack_start(self.port, False, False, 0)
        for act in ("allow", "deny"):
            rule.pack_start(C.button(act.capitalize(), lambda a=act: C.helper(["ufw-rule", a, self.port.get_text().strip()],
                                                                              None, lambda rc: self.load_rules())), False, False, 0)
        self.row("Add a rule", "Open (allow) or block (deny) a port for incoming connections.", rule)
        self.rules = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.put(C.card(C.label("Rules (click Load to see them, needs your password)", "dim"), self.rules,
                        C.button("Load rules", self.load_rules)))
        self.row("Advanced firewall", "Profiles, logging and app rules.", C.button("Open Gufw", lambda: C.launch(["gufw"])))

        self.section("App permissions", "What each Flathub app may access. Debian apps are trusted system software.")
        self.perms = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.put(self.perms)

        self.section("Disk encryption")
        self.enc = C.label("", wrap=True)
        self.put(C.card(self.enc))

    def on_show(self):
        def work():
            fw = C.sh(["systemctl", "is-active", "ufw"]).strip() == "active" and os.path.exists("/etc/ufw/ufw.conf") \
                and "ENABLED=yes" in open("/etc/ufw/ufw.conf").read()
            ups = [l for l in C.sh(["apt", "list", "--upgradable"], timeout=30).splitlines() if "[upgradable" in l]
            sec = [l for l in ups if "-security" in l]
            try:
                last = datetime.datetime.fromtimestamp(os.path.getmtime("/var/log/apt/history.log"))
                days = (datetime.datetime.now() - last).days
            except OSError:
                days = None
            lsblk = C.sh(["lsblk", "-rno", "NAME,TYPE,MOUNTPOINT"])
            encrypted = any(l.split()[1] == "crypt" for l in lsblk.splitlines() if len(l.split()) >= 2)
            ports = [l.split()[4] for l in C.sh(["ss", "-Htuln"]).splitlines()
                     if len(l.split()) > 4 and not l.split()[4].startswith(("127.", "[::1]", "::1"))]
            return fw, ups, sec, days, encrypted, ports

        def show(r):
            fw, ups, sec, days, encrypted, ports = r
            for c in self.recs.get_children():
                self.recs.remove(c)
            recs = []
            recs.append(("ok" if fw else "bad", "Firewall is on" if fw else "Turn on the firewall to block incoming connections"))
            recs.append(("ok" if C.IS_LIVE or auto_updates_on() else "warn",
                         "Automatic security updates are on" if auto_updates_on() else "Turn on automatic security updates (Update Center)"))
            if sec:
                recs.append(("bad", f"{len(sec)} security update{'s' if len(sec) != 1 else ''} waiting: install them in the Update Center"))
            elif ups:
                recs.append(("warn", f"{len(ups)} updates available"))
            else:
                recs.append(("ok", "Your software is up to date"))
            if days is not None and days > 30:
                recs.append(("warn", f"Software was last updated {days} days ago"))
            if C.IS_LIVE:
                recs.append(("warn", "You are running the live ISO: install Claudius to keep your files and updates"))
            elif not encrypted:
                recs.append(("warn", "Your disk is not encrypted. Anyone with the disk can read your files. "
                                     "Choose 'Encrypt system' when installing to protect it"))
            else:
                recs.append(("ok", "Your disk is encrypted"))
            if ports:
                recs.append(("warn" if not fw else "ok", f"Listening for network connections on: {', '.join(sorted(set(ports))[:6])}"))
            for cls, text in recs:
                icon = {"ok": "✔", "warn": "!", "bad": "✖"}[cls]
                box = Gtk.Box(spacing=12)
                box.pack_start(C.label(icon, cls), False, False, 0)
                box.pack_start(C.label(text, wrap=True), True, True, 0)
                self.recs.pack_start(C.card(box, orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
            self.recs.show_all()
            self.fw_state.set_text("on" if fw else "off")
            self.fw_state.get_style_context().add_class("ok" if fw else "bad")
            self.enc.set_text("Encrypted with LUKS: your files are protected if the disk is lost or stolen." if encrypted else
                              "Not encrypted. Encryption can only be turned on while installing: in the installer, "
                              "choose Erase disk, then tick 'Encrypt system'.")
            self.load_perms()
        in_thread(work, show)
        return False

    def load_rules(self):
        lines = []

        def done(_rc):
            for c in self.rules.get_children():
                self.rules.remove(c)
            for l in lines:
                m = re.match(r"\[\s*(\d+)\]\s+(.*)", l)
                if m:
                    box = Gtk.Box(spacing=10)
                    box.pack_start(C.label(m.group(2)), True, True, 0)
                    box.pack_end(C.button("Delete", lambda n=m.group(1): C.helper(["ufw-rule", "delete", n], None,
                                                                                   lambda rc: self.load_rules())), False, False, 0)
                    self.rules.add(box)
                elif l.startswith(("Status", "Default")):
                    self.rules.add(C.label(l, "dim"))
            self.rules.show_all()
        C.helper(["ufw-status"], lines.append, done)

    def load_perms(self):
        for c in self.perms.get_children():
            self.perms.remove(c)
        apps = sorted(C.flatpak_installed_ids())
        if not apps:
            self.perms.pack_start(C.label("No Flathub apps installed yet.", "dim"), False, False, 0)
        for app in apps:
            info = C.sh(["flatpak", "info", "--show-permissions", app])
            box = Gtk.Box(spacing=14)
            box.pack_start(C.label(app, "card-title"), True, True, 0)
            for perm, flag_on, flag_off, text in (("network", "--share=network", "--unshare=network", "Internet"),
                                                  ("home", "--filesystem=home", "--nofilesystem=home", "Home folder"),
                                                  ("devices", "--device=all", "--nodevice=all", "Devices"),
                                                  ("pulseaudio", "--socket=pulseaudio", "--nosocket=pulseaudio", "Sound")):
                sw = Gtk.Switch(active=perm in info)
                sw.connect("state-set", lambda _s, st, a=app, on=flag_on, off=flag_off:
                           C.sh(["flatpak", "override", "--user", on if st else off, a]) and False)
                b = Gtk.Box(spacing=4)
                b.pack_start(C.label(text, "dim"), False, False, 0)
                b.pack_start(sw, False, False, 0)
                box.pack_start(b, False, False, 0)
            self.perms.pack_start(C.card(box, orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        self.perms.show_all()


# ============================================================================ Restore & Backup
class BackupPage(Page):
    title = "Restore & Backup"
    subtitle = "Two different safety nets. Use both."

    def build(self):
        # --- system snapshots
        self.section("System snapshots", "A snapshot saves Claudius itself (programs and settings, not your personal files) "
                                         "so you can undo a bad update or setting change. Kept on this disk.")
        ts = C.have("timeshift")
        if not ts:
            self.row("Timeshift is not installed", "Timeshift takes and restores system snapshots.",
                     C.button("Install Timeshift", lambda: C.helper(["apt-install", "timeshift"], self.log,
                                                                    lambda rc: self.status.set_text("Installed: reopen this page" if rc == 0 else "Install failed")),
                              "accent-btn"))
        else:
            box = Gtk.Box(spacing=8)
            box.pack_start(C.button("Create snapshot now", self.snapshot, "accent-btn"), False, False, 0)
            box.pack_start(C.button("Show snapshots", self.list_snaps), False, False, 0)
            box.pack_start(C.button("Restore…", lambda: C.launch(["timeshift-launcher"])), False, False, 0)
            self.row("Snapshots", "Restore opens Timeshift: pick a snapshot and restart into it.", box)
            self.switch("Snapshot before every update", "The Update Center takes a snapshot first.",
                        os.path.exists("/etc/claudius/snapshot-before-updates"),
                        lambda st: C.helper(["snapshot-before-updates", "on" if st else "off"]))
        self.snaps = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.put(self.snaps)

        # --- personal backups
        self.section("Personal file backup", "Copies your home folder (documents, pictures, settings) to a USB drive, another "
                                              "disk or a network folder. This is what protects your files if the disk fails.")
        self.dest = Gtk.FileChooserButton(title="Choose a backup destination", action=Gtk.FileChooserAction.SELECT_FOLDER)
        media = sorted(glob.glob(f"/media/{os.environ.get('USER', '')}/*"))
        if media:
            self.dest.set_current_folder(media[0])
        self.row("Back up to", "A folder on a USB drive or another disk is best.", self.dest)
        box = Gtk.Box(spacing=8)
        box.pack_start(C.button("Back up now", self.backup, "accent-btn"), False, False, 0)
        box.pack_start(C.button("Restore files from backup", self.restore), False, False, 0)
        self.row("Home folder", "Skips caches and Trash. Only changed files are copied after the first time.", box)
        self.status = C.label("", "dim")
        self.put(self.status)
        self.exp, self.log = self.log_view()

        self.section("Recover from a failed update")
        self.put(C.label("1. Open the Update Center and click 'Repair updates'.\n"
                         "2. Still broken? Restore the snapshot taken before the update (above).\n"
                         "3. Can't reach the desktop? Boot the Claudius ISO, open Timeshift and restore from there.",
                         wrap=True))

    def snapshot(self):
        self.status.set_text("Creating a snapshot… (the first one takes a few minutes)")
        self.exp.set_expanded(True)
        C.helper(["snapshot-create", "Claudius Center"], self.log,
                 lambda rc: self.status.set_text("Snapshot created" if rc == 0 else "Snapshot failed: see Details"))

    def list_snaps(self):
        lines = []

        def done(_rc):
            for c in self.snaps.get_children():
                self.snaps.remove(c)
            rows = [l for l in lines if re.match(r"^\d+\s+>", l)]
            for l in rows or ["No snapshots yet."]:
                self.snaps.add(C.label(l, "dim"))
            self.snaps.show_all()
        C.helper(["snapshot-list"], lines.append, done)

    def backup_dir(self):
        d = self.dest.get_filename()
        return os.path.join(d, f"claudius-home-backup-{os.environ.get('USER', 'user')}") if d else None

    def backup(self):
        target = self.backup_dir()
        if not target:
            self.status.set_text("Choose where to back up first.")
            return
        os.makedirs(target, exist_ok=True)
        self.status.set_text(f"Backing up to {target}…")
        self.exp.set_expanded(True)
        C.run_async(["rsync", "-a", "--delete", "--info=progress2", "--exclude=.cache/", "--exclude=.local/share/Trash/",
                     "--exclude=Downloads/*.iso", os.path.expanduser("~") + "/", target + "/"],
                    self.log, lambda rc: self.status.set_text(
                        f"Backup finished ({datetime.datetime.now():%Y-%m-%d %H:%M})" if rc == 0 else "Backup failed: see Details"))

    def restore(self):
        src = self.backup_dir()
        if not src or not os.path.isdir(src):
            self.status.set_text("No backup found in the chosen folder.")
            return
        dlg = Gtk.MessageDialog(transient_for=self.center, modal=True, message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text="Restore your files from the backup?")
        dlg.format_secondary_text("Files in the backup are copied back into your home folder. Newer files you have now are kept.")
        ok = dlg.run() == Gtk.ResponseType.OK
        dlg.destroy()
        if ok:
            self.exp.set_expanded(True)
            C.run_async(["rsync", "-a", "--update", "--info=progress2", src + "/", os.path.expanduser("~") + "/"],
                        self.log, lambda rc: self.status.set_text("Files restored" if rc == 0 else "Restore failed"))


# ============================================================================ Drivers
class DriversPage(Page):
    title = "Drivers"
    subtitle = "Extra software that makes your hardware, or your virtual machine, work at its best."

    def build(self):
        virt = C.sh(["systemd-detect-virt"]).strip() or "none"
        self.status = C.label("", "dim")
        self.exp, self.log = None, None
        cpu = open("/proc/cpuinfo").read()
        items = []
        if virt == "oracle":
            running = C.sh(["pgrep", "-x", "VBoxService"]).strip() != ""
            items.append(("VirtualBox Guest Additions",
                          "Auto-resize the screen with the window, shared clipboard, drag and drop and shared folders. "
                          "First choose Devices → Insert Guest Additions CD image in the VirtualBox menu.",
                          running, ["vbox-additions"]))
        elif virt == "vmware":
            items.append(("VMware Tools", "Screen resizing, clipboard and shared folders.",
                          C.apt_installed("open-vm-tools-desktop"), ["apt-install", "open-vm-tools-desktop"]))
        elif virt in ("kvm", "qemu"):
            items.append(("QEMU / KVM guest tools", "Clipboard sharing and automatic screen size (SPICE), host integration.",
                          C.apt_installed("spice-vdagent"), ["apt-install", "spice-vdagent", "qemu-guest-agent"]))
        if "GenuineIntel" in cpu:
            items.append(("Intel CPU microcode", "Security and stability fixes for your processor.",
                          C.apt_installed("intel-microcode"), ["apt-install", "intel-microcode"]))
        if "AuthenticAMD" in cpu:
            items.append(("AMD CPU microcode", "Security and stability fixes for your processor.",
                          C.apt_installed("amd64-microcode"), ["apt-install", "amd64-microcode"]))
        if virt == "none":
            items.append(("Extra firmware", "Wi-Fi, Bluetooth and graphics firmware for more hardware.",
                          C.apt_installed("firmware-misc-nonfree"),
                          ["apt-install", "firmware-misc-nonfree", "firmware-realtek", "firmware-iwlwifi", "firmware-amd-graphics"]))
        self.put(C.label(f"Machine: {'physical computer' if virt == 'none' else 'virtual machine (' + virt + ')'}", "h2"))
        for title, desc, installed, action in items:
            ctl = C.label("Installed ✔", "ok") if installed else C.button("Install", lambda a=action: self.install(a), "accent-btn")
            self.row(title, desc, ctl)
        if not items:
            self.put(C.label("Nothing extra is needed for this machine. ✔", "ok"))
        gpu = [l.split(": ", 1)[-1] for l in C.sh("lspci").splitlines() if "VGA" in l or "3D" in l]
        self.row("Graphics", ", ".join(gpu) or "unknown", C.button("Display settings", lambda: self.center.open_page("display")))
        self.put(self.status)
        self.exp, self.log = self.log_view()

    def install(self, action):
        self.status.set_text("Installing… (this can take a few minutes)")
        self.exp.set_expanded(True)
        C.helper(action, self.log, lambda rc: self.status.set_text(
            "Done. Restart to use the new driver." if rc == 0 else "Something went wrong: see Details"))
