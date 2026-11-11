"""Base class for Claudius Center pages."""
import common as C
from common import Gtk


class Page(Gtk.ScrolledWindow):
    title = ""
    subtitle = ""

    def __init__(self, center):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.center = center
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        C.styled(self.box, "page")
        Gtk.ScrolledWindow.add(self, self.box)
        if self.title:
            self.box.pack_start(C.label(self.title, "h1"), False, False, 0)
        if self.subtitle:
            self.box.pack_start(C.label(self.subtitle, "dim", wrap=True), False, False, 0)
        self.build()

    def build(self):
        pass

    # helpers -----------------------------------------------------------------
    def section(self, title, hint=None):
        self.box.pack_start(C.label(title, "h2"), False, False, 6)
        if hint:
            self.box.pack_start(C.label(hint, "dim", wrap=True), False, False, 0)

    def put(self, widget, expand=False):
        self.box.pack_start(widget, expand, expand, 0)
        return widget

    def row(self, title, desc, control):
        """A settings row: title + description on the left, a control on the right."""
        r = Gtk.Box(spacing=16)
        C.styled(r, "card")
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        texts.pack_start(C.label(title, "card-title"), False, False, 0)
        if desc:
            texts.pack_start(C.label(desc, "dim", wrap=True), False, False, 0)
        r.pack_start(texts, True, True, 0)
        control.set_valign(Gtk.Align.CENTER)
        r.pack_end(control, False, False, 0)
        self.put(r)
        return r

    def switch(self, title, desc, active, on_toggle):
        sw = Gtk.Switch(active=active)
        sw.connect("state-set", lambda _s, state: on_toggle(state) or False)
        self.row(title, desc, sw)
        return sw

    def log_view(self):
        exp = Gtk.Expander(label="Details")
        tv = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        C.styled(tv, "log")
        tv.set_size_request(-1, 160)
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(-1, 180)
        sw.add(tv)
        exp.add(sw)
        self.put(exp)

        def append(line):
            buf = tv.get_buffer()
            buf.insert(buf.get_end_iter(), line + "\n")
            tv.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)
        return exp, append
