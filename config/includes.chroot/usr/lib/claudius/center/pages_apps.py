"""App Center and Packs."""
import json
import os

import common as C
from common import Gtk
from page import Page

CATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")


def load_catalog():
    try:
        with open(CATALOG) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"categories": [], "apps": [], "packs": []}


def is_installed(app, flat_ids):
    if app.get("apt"):
        return C.apt_installed(app["apt"])
    return app.get("flatpak") in flat_ids


def install_args(app):
    return ["apt-install", app["apt"]] if app.get("apt") else ["flatpak-install", app["flatpak"]]


def remove_args(app):
    return ["apt-remove", app["apt"]] if app.get("apt") else ["flatpak-remove", app["flatpak"]]


class AppCard(Gtk.Box):
    def __init__(self, page, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        C.styled(self, "card")
        self.set_size_request(250, -1)
        self.page, self.app = page, app
        head = Gtk.Box(spacing=12)
        img = Gtk.Image.new_from_icon_name(app.get("icon", "application-x-executable"), Gtk.IconSize.DIALOG)
        img.set_pixel_size(48)
        head.pack_start(img, False, False, 0)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER)
        names.pack_start(C.label(app["name"], "card-title"), False, False, 0)
        src = "Debian" if app.get("apt") else "Flathub"
        names.pack_start(C.label(f"{app.get('category', '')} · {src}", "dim"), False, False, 0)
        head.pack_start(names, True, True, 0)
        self.pack_start(head, False, False, 0)
        self.pack_start(C.label(app.get("summary", ""), "dim", wrap=True), False, False, 0)
        self.actions = Gtk.Box(spacing=8)
        self.pack_start(self.actions, False, False, 0)
        self.spinner = Gtk.Spinner()

    def update(self, installed):
        for c in self.actions.get_children():
            self.actions.remove(c)
        if installed:
            self.actions.pack_start(C.button("Open", self.open_app, "accent-btn"), False, False, 0)
            self.actions.pack_start(C.button("Remove", lambda: self.run(remove_args(self.app), False)), False, False, 0)
        else:
            self.actions.pack_start(C.button("Install", lambda: self.run(install_args(self.app), True), "accent-btn"),
                                    False, False, 0)
        self.actions.show_all()

    def open_app(self):
        if self.app.get("flatpak"):
            C.launch(["flatpak", "run", self.app["flatpak"]])
        else:
            C.launch(["gtk-launch", self.app.get("icon", self.app["apt"])])

    def run(self, args, installing):
        for c in self.actions.get_children():
            self.actions.remove(c)
        self.actions.pack_start(self.spinner, False, False, 0)
        self.actions.pack_start(C.label("Installing…" if installing else "Removing…", "dim"), False, False, 0)
        self.actions.show_all()
        self.spinner.start()

        def done(rc):
            self.spinner.stop()
            ok = rc == 0
            self.update(installing if ok else not installing)
            if not ok:
                self.actions.pack_start(C.label("failed", "bad"), False, False, 0)
                self.actions.show_all()
        C.helper(args, self.page.log, done)


class AppsPage(Page):
    title = "App Center"
    subtitle = "Hand-picked apps. Debian apps are updated with the system, Flathub apps run in a sandbox."

    def build(self):
        self.catalog = load_catalog()
        bar = Gtk.Box(spacing=10)
        self.search = Gtk.SearchEntry(placeholder_text="Search apps")
        self.search.connect("search-changed", lambda *_: self.filter())
        bar.pack_start(self.search, True, True, 0)
        self.cat = Gtk.ComboBoxText()
        self.cat.append("all", "All categories")
        for c in self.catalog["categories"]:
            self.cat.append(c, c)
        self.cat.set_active_id("all")
        self.cat.connect("changed", lambda *_: self.filter())
        bar.pack_start(self.cat, False, False, 0)
        self.put(bar)
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=12, row_spacing=12,
                                max_children_per_line=4, homogeneous=True)
        self.put(self.flow)
        self.cards = []
        for app in self.catalog["apps"]:
            card = AppCard(self, app)
            self.cards.append(card)
            self.flow.add(card)
        self.exp, self.log = self.log_view()
        self.put(C.label("More apps: Synaptic (all of Debian) or flathub.org.", "dim"))
        self.put(C.button("Open Synaptic", lambda: C.launch(["synaptic-pkexec"])))

    def on_show(self):
        flat = C.flatpak_installed_ids()
        for card in self.cards:
            card.update(is_installed(card.app, flat))
        self.filter()
        return False

    def filter(self):
        q = self.search.get_text().lower().strip()
        cat = self.cat.get_active_id()
        for card in self.cards:
            a = card.app
            show = (cat in (None, "all") or a.get("category") == cat) and \
                (not q or q in a["name"].lower() or q in a.get("summary", "").lower())
            card.get_parent().set_visible(show)


class PacksPage(Page):
    title = "Packs"
    subtitle = "Everything for one job, installed in one click."

    def build(self):
        self.catalog = load_catalog()
        flat = C.flatpak_installed_ids()
        for pack in self.catalog["packs"]:
            have = all(C.apt_installed(p) for p in pack["apt"]) and all(f in flat for f in pack["flatpak"])
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            head = Gtk.Box(spacing=12)
            img = Gtk.Image.new_from_icon_name(pack["icon"], Gtk.IconSize.DIALOG)
            img.set_pixel_size(48)
            head.pack_start(img, False, False, 0)
            t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            t.pack_start(C.label(pack["name"], "h2"), False, False, 0)
            t.pack_start(C.label(pack["summary"], "dim", wrap=True), False, False, 0)
            head.pack_start(t, True, True, 0)
            status = C.label("Installed ✔", "ok") if have else C.button("Install pack", lambda p=pack: self.install(p), "accent-btn")
            head.pack_end(status, False, False, 0)
            box.pack_start(head, False, False, 0)
            contents = ", ".join(pack["apt"] + [f.split(".")[-1] + " (Flathub)" for f in pack["flatpak"]])
            box.pack_start(C.label(f"Includes: {contents}", "dim", wrap=True), False, False, 0)
            if pack.get("xrdp"):
                sw = Gtk.Switch(active=C.sh(["systemctl", "is-active", "xrdp"]).strip() == "active")
                sw.connect("state-set", lambda _s, st: C.helper(["xrdp", "on" if st else "off"], self.log) or False)
                row = Gtk.Box(spacing=10)
                row.pack_start(C.label("Let other computers connect to this one (RDP server, port 3389)"), True, True, 0)
                row.pack_end(sw, False, False, 0)
                box.pack_start(row, False, False, 0)
            self.put(C.card(box))
        self.status = C.label("", "dim")
        self.put(self.status)
        self.exp, self.log = self.log_view()

    def install(self, pack):
        self.status.set_text(f"Installing the {pack['name']} pack… (this can take a while)")
        self.exp.set_expanded(True)

        def flat_step(rc):
            if rc == 0 and pack["flatpak"]:
                C.helper(["flatpak-install", *pack["flatpak"]], self.log, finish)
            else:
                finish(rc)

        def finish(rc):
            self.status.set_text(f"{pack['name']} pack installed ✔" if rc == 0 else "Something went wrong: see Details")
        if pack["apt"]:
            C.helper(["apt-install", *pack["apt"]], self.log, flat_step)
        else:
            flat_step(0)
