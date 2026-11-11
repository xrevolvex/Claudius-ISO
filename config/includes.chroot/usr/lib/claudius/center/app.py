#!/usr/bin/env python3
"""Claudius Center: settings and system tools in one window.

    claudius-center [--page NAME]
    pages: home appearance desktop display performance updates apps packs
           security backup drivers monitor about
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common as C  # noqa: E402
from common import Gtk, GLib  # noqa: E402

PAGES = [
    # id, title, icon, module, class
    ("home", "Home", "go-home", "pages_home", "HomePage"),
    (None, "Personalize", None, None, None),
    ("appearance", "Appearance", "preferences-desktop-theme", "pages_look", "AppearancePage"),
    ("desktop", "Desktop", "preferences-desktop", "pages_look", "DesktopPage"),
    ("display", "Display", "preferences-desktop-display", "pages_look", "DisplayPage"),
    ("performance", "Performance", "utilities-system-monitor", "pages_look", "PerformancePage"),
    (None, "Software", None, None, None),
    ("updates", "Update Center", "system-software-update", "pages_system", "UpdatesPage"),
    ("apps", "App Center", "system-software-install", "pages_apps", "AppsPage"),
    ("packs", "Packs", "package-x-generic", "pages_apps", "PacksPage"),
    (None, "Protect", None, None, None),
    ("security", "Security Center", "security-high", "pages_system", "SecurityPage"),
    ("backup", "Restore & Backup", "document-revert", "pages_system", "BackupPage"),
    (None, "System", None, None, None),
    ("monitor", "System Monitor", "org.xfce.taskmanager", "pages_monitor", "MonitorPage"),
    ("drivers", "Drivers", "preferences-system", "pages_system", "DriversPage"),
    ("about", "About", "help-about", "pages_home", "AboutPage"),
]


class Center(Gtk.Window):
    def __init__(self, start="home"):
        super().__init__(title="Claudius Center")
        self.set_icon_name("claudius")
        self.set_default_size(1100, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        C.styled(self, "claudius-window")
        self.pages = {}

        paned = Gtk.Box()
        self.add(paned)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        C.styled(side, "sidebar-list")
        side.set_size_request(230, -1)
        head = Gtk.Box(spacing=10, margin=18)
        logo = Gtk.Image.new_from_icon_name("claudius", Gtk.IconSize.DND)
        logo.set_pixel_size(36)
        head.pack_start(logo, False, False, 0)
        head.pack_start(C.label("Claudius Center", "h2"), False, False, 0)
        side.pack_start(head, False, False, 0)

        self.listbox = Gtk.ListBox()
        C.styled(self.listbox, "sidebar-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.rows = {}
        for pid, title, icon, _m, _c in PAGES:
            row = Gtk.ListBoxRow()
            if pid is None:
                row.set_selectable(False)
                row.set_activatable(False)
                row.add(C.label(title.upper(), "dim", xalign=0))
            else:
                box = Gtk.Box(spacing=12)
                box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
                box.pack_start(C.label(title), False, False, 0)
                row.add(box)
                row.page_id = pid
                self.rows[pid] = row
            self.listbox.add(row)
        self.listbox.connect("row-selected", self.on_row)
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sw.add(self.listbox)
        side.pack_start(sw, True, True, 0)
        paned.pack_start(side, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=160)
        paned.pack_start(self.stack, True, True, 0)
        self.show_all()
        self.open_page(start if start in self.rows else "home")

    def on_row(self, _lb, row):
        if row is not None and hasattr(row, "page_id"):
            self.show_page(row.page_id)

    def open_page(self, pid):
        self.listbox.select_row(self.rows[pid])

    def show_page(self, pid):
        if pid not in self.pages:
            entry = next(p for p in PAGES if p[0] == pid)
            try:
                mod = __import__(entry[3])
                page = getattr(mod, entry[4])(self)
            except Exception as err:  # noqa: BLE001  a broken page must not take the app down
                import traceback
                traceback.print_exc()
                page = Gtk.Label(label=f"This page could not be loaded:\n{err}")
            self.pages[pid] = page
            self.stack.add_named(page, pid)
            page.show_all()
        self.stack.set_visible_child_name(pid)
        page = self.pages[pid]
        if hasattr(page, "on_show"):
            GLib.idle_add(page.on_show)


def main():
    start = "home"
    if "--page" in sys.argv:
        i = sys.argv.index("--page")
        if i + 1 < len(sys.argv):
            start = sys.argv[i + 1]
    C.install_css()
    win = Center(start)
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
