#!/usr/bin/env python3
"""
Claudius Greeter: the login screen.

Timeline
  0.00 s  the C draws itself in the middle of the screen, the dot drops in
  1.00 s  the C glides up and shrinks a little
  1.30 s  the login card fades in and slides up into place
login     the card fades out, the C glides back to the centre and breathes
          while the desktop starts (claudius-splash then takes over)

All animation is driven by GTK's frame clock, so it runs at the display's
refresh rate (60, 75, 120, 144 Hz...).
"""
import math
import os
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("LightDM", "1")
from gi.repository import Gdk, GLib, Gtk, LightDM  # noqa: E402
import cairo  # noqa: E402

BG = (0x12 / 255, 0x18 / 255, 0x30 / 255)
ORANGE = (1.0, 0x94 / 255, 0x47 / 255)
ANIM_BOX = 220
SMALL_BOX = 150
TAG = "/usr/share/claudius/logo/version-tag.png"
AVATAR = "/usr/share/claudius/logo/claudius-avatar.png"
IS_LIVE = os.path.isdir("/run/live/medium")

CSS = b"""
#card { background-color: #1a2244; border-radius: 18px; padding: 26px 30px; border: 1px solid #263063; }
#name { color: #ffffff; font-size: 19px; font-weight: 700; }
#hint { color: #8f98bd; font-size: 11px; }
#error { color: #ff7b7b; font-size: 12px; font-weight: 700; }
#clock { color: #e6e9f2; font-size: 15px; }
entry { background-color: #0f1530; color: #ffffff; border: 1px solid #2c3770; border-radius: 10px;
        padding: 9px 12px; font-size: 14px; caret-color: #ff9447; box-shadow: none; }
entry:focus { border-color: #ff9447; }
button.login { background-image: none; background-color: #ff9447; color: #1a1206; border: none;
               border-radius: 10px; padding: 8px 18px; font-weight: 800; box-shadow: none; text-shadow: none; }
button.login:hover { background-color: #ffa862; }
button.login label { color: #1a1206; }
button.power { background-image: none; background-color: transparent; border: none; color: #c8cde0;
               box-shadow: none; text-shadow: none; padding: 6px 10px; border-radius: 8px; }
button.power:hover { background-color: rgba(255,255,255,0.08); }
button.power label { color: #c8cde0; }
combobox button { background-image: none; background-color: #0f1530; color: #ffffff; border: 1px solid #2c3770;
                  border-radius: 10px; box-shadow: none; }
"""


def log(msg):
    print(f"claudius-greeter: {msg}", file=sys.stderr, flush=True)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def draw_c(cr, cx, cy, box, progress=1.0, dot=1.0, alpha=1.0):
    """Draw the Claudius mark. box = size in px of the 512-unit emblem box."""
    k = box / 512.0
    sw, rad = 52.8 * k, 123.2 * k
    ccy = cy + 24.64 * k
    cr.set_source_rgba(*ORANGE, alpha)
    if progress > 0:
        cr.set_line_width(sw)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        start = math.radians(312)
        cr.new_path()
        cr.arc_negative(cx, ccy, rad, start, start - math.radians(264) * progress)
        cr.stroke()
    if dot > 0:
        dot_r = 22.18 * k * (0.4 + 0.6 * dot)
        dy = cy + (85.1 - 256) * k - 60 * k * (1 - dot)
        cr.set_source_rgba(*ORANGE, alpha * dot)
        cr.arc(cx, dy, dot_r, 0, 2 * math.pi)
        cr.fill()


class Greeter(Gtk.Window):
    def __init__(self, greeter):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.greeter = greeter
        self.t0 = None
        self.phase = "intro"          # intro -> ready -> leaving
        self.leave_t = None
        self.shake_t = None
        self.prompted = False
        self.pending = None
        self.awaiting = False      # a password was sent and we wait for LightDM's answer
        self.last_pw = None
        self.retried = False
        self.user = None
        self.users = {}
        self._t = 0.0
        self._t_abs = 0.0
        self.tag = None
        try:
            self.tag = cairo.ImageSurface.create_from_png(TAG)
        except Exception:  # noqa: BLE001
            pass

        screen = Gdk.Screen.get_default()
        self.W, self.H = screen.get_width(), screen.get_height()
        self.set_default_size(self.W, self.H)
        self.move(0, 0)
        self.set_decorated(False)
        self.set_app_paintable(True)

        overlay = Gtk.Overlay()
        self.add(overlay)
        self.canvas = Gtk.DrawingArea()
        self.canvas.connect("draw", self.on_draw)
        overlay.add(self.canvas)

        # ---- clock (top centre)
        self.clock = Gtk.Label(name="clock", halign=Gtk.Align.CENTER, valign=Gtk.Align.START, margin_top=22)
        overlay.add_overlay(self.clock)
        self.update_clock()
        GLib.timeout_add_seconds(1, self.update_clock)

        # ---- login card
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, name="card",
                            halign=Gtk.Align.CENTER, valign=Gtk.Align.START)
        self.card.set_size_request(360, -1)
        top = Gtk.Box(spacing=14)
        try:
            avatar = Gtk.Image.new_from_file(AVATAR)
        except Exception:  # noqa: BLE001
            avatar = Gtk.Image.new_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        top.pack_start(avatar, False, False, 0)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        self.name = Gtk.Label(name="name", xalign=0)
        self.users_combo = Gtk.ComboBoxText()
        self.username_entry = Gtk.Entry(placeholder_text="Username")
        names.pack_start(self.name, False, False, 0)
        names.pack_start(self.users_combo, False, False, 0)
        names.pack_start(self.username_entry, False, False, 0)
        top.pack_start(names, True, True, 0)
        self.card.pack_start(top, False, False, 0)

        self.password = Gtk.Entry(placeholder_text="Password", visibility=False)
        self.password.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password.connect("activate", self.on_login)
        row = Gtk.Box(spacing=10)
        row.pack_start(self.password, True, True, 0)
        login = Gtk.Button(label="Log in")
        login.get_style_context().add_class("login")
        login.connect("clicked", self.on_login)
        row.pack_start(login, False, False, 0)
        self.card.pack_start(row, False, False, 0)
        self.error = Gtk.Label(name="error", xalign=0)
        self.card.pack_start(self.error, False, False, 0)
        if IS_LIVE:
            self.card.pack_start(Gtk.Label(label="Live session password: claudius", name="hint", xalign=0),
                                 False, False, 0)
        self.card.set_opacity(0)
        overlay.add_overlay(self.card)

        # ---- power buttons (bottom left)
        power = Gtk.Box(spacing=4, halign=Gtk.Align.START, valign=Gtk.Align.END, margin_start=24, margin_bottom=22)
        for label, can, action in (("Restart", LightDM.get_can_restart, LightDM.restart),
                                   ("Shut down", LightDM.get_can_shutdown, LightDM.shutdown)):
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("power")
            b.set_sensitive(bool(can()))
            b.connect("clicked", lambda _b, a=action: a())
            power.pack_start(b, False, False, 0)
        overlay.add_overlay(power)
        self.power = power
        power.set_opacity(0)

        self.canvas.add_tick_callback(self.on_tick)

    # ------------------------------------------------------------------ users
    def load_users(self):
        users = [u for u in LightDM.UserList.get_instance().get_users()]
        self.users = {u.get_name(): u for u in users}
        hint = self.greeter.get_select_user_hint()
        self.username_entry.set_no_show_all(True)
        self.users_combo.set_no_show_all(True)
        if not users:
            self.username_entry.show()
            self.name.set_text("Welcome")
            self.username_entry.connect("activate", lambda *_: self.password.grab_focus())
            return
        if len(users) > 1:
            for u in users:
                self.users_combo.append(u.get_name(), u.get_display_name())
            self.users_combo.show()
            self.users_combo.connect("changed", lambda c: self.select_user(c.get_active_id()))
        first = hint if hint in self.users else users[0].get_name()
        if len(users) > 1:
            self.users_combo.set_active_id(first)
        self.select_user(first)

    def select_user(self, name):
        if not name:
            return
        self.user = name
        u = self.users.get(name)
        self.name.set_text(u.get_display_name() if u else name)
        if self.greeter.get_in_authentication():
            self.greeter.cancel_authentication()
        self.prompted = False
        self.greeter.authenticate(name)

    # ------------------------------------------------------------------ auth
    def on_prompt(self, _greeter, text, _type):
        log(f"prompt: {text!r}")
        self.prompted = True
        if self.pending is not None:
            pw, self.pending = self.pending, None
            self.prompted = False
            self.greeter.respond(pw)

    def on_message(self, _greeter, text, _type):
        self.error.set_text(text)

    def on_login(self, *_):
        if self.phase == "leaving":
            return
        if self.user is None:
            name = self.username_entry.get_text().strip()
            if not name:
                return
            self.user = name
            self.prompted = False
            self.greeter.authenticate(name)
        pw = self.password.get_text()
        self.error.set_text("")
        self.last_pw, self.awaiting, self.retried = pw, True, False
        log(f"login: prompted={self.prompted}")
        if self.prompted:
            self.prompted = False
            self.greeter.respond(pw)
        else:
            self.pending = pw
        GLib.timeout_add(5000, self.check_stuck)

    def check_stuck(self):
        """LightDM never answered (a lost prompt): start the conversation again and resend once."""
        if self.awaiting and self.phase != "leaving" and not self.retried and self.user:
            log("no answer from LightDM: retrying authentication")
            self.retried = True
            if self.greeter.get_in_authentication():
                self.greeter.cancel_authentication()
            self.prompted = False
            self.pending = self.last_pw
            self.greeter.authenticate(self.user)
            GLib.timeout_add(6000, self.check_stuck)
        elif self.awaiting and self.retried and self.phase != "leaving":
            self.awaiting = False
            self.error.set_text("The login service is not answering. Try again.")
        return False

    def on_auth_complete(self, greeter):
        log(f"authentication complete: ok={greeter.get_is_authenticated()}")
        self.awaiting = False
        if greeter.get_is_authenticated():
            self.phase = "leaving"
            self.leave_t = self.now()
            GLib.timeout_add(900, self.start_session)
        else:
            self.error.set_text("Wrong password, try again.")
            self.password.set_text("")
            self.shake_t = self.now()
            name = self.user
            if not self.users:
                self.user = None      # typed username: ask again
            elif name:
                GLib.idle_add(self.reauthenticate, name)
            self.password.grab_focus()

    def reauthenticate(self, name):
        self.prompted = False
        self.greeter.authenticate(name)
        return False

    def start_session(self):
        u = self.users.get(self.user)
        session = (u.get_session() if u else None) or self.greeter.get_default_session_hint() or "xfce"
        try:
            self.greeter.start_session_sync(session)
        except GLib.Error as err:
            try:
                self.greeter.start_session_sync(None)
            except GLib.Error:
                self.phase = "ready"
                self.card.set_opacity(1)
                self.error.set_text(f"Could not start the desktop: {err.message}")
        return False

    # ------------------------------------------------------------------ animation
    def now(self):
        clock = self.canvas.get_frame_clock()
        return clock.get_frame_time() / 1e6 if clock else time.monotonic()

    def update_clock(self):
        self.clock.set_text(time.strftime("%A %d %B   %H:%M"))
        return True

    def logo_state(self, t):
        """Return (cx, cy, box, progress, dot, alpha) for the C at time t."""
        cx, cy_mid, cy_top = self.W / 2, self.H / 2, self.H * 0.30
        if self.phase == "leaving":
            k = ease_in_out((t - self.leave_t) / 0.55)
            cy = cy_top + (cy_mid - cy_top) * k
            box = SMALL_BOX + (ANIM_BOX - SMALL_BOX) * k
            breathe = 0.62 + 0.38 * (0.5 + 0.5 * math.cos(2 * math.pi * max(0, t - self.leave_t - 0.55) / 1.3))
            return cx, cy, box, 1, 1, breathe if k >= 1 else 1
        progress = ease_out(t / 0.75)
        dot = ease_out((t - 0.72) / 0.28)
        k = ease_in_out((t - 1.0) / 0.7)
        cy = cy_mid + (cy_top - cy_mid) * k
        box = ANIM_BOX + (SMALL_BOX - ANIM_BOX) * k
        return cx, cy, box, progress, dot, 1

    def on_tick(self, _widget, clock):
        t_abs = clock.get_frame_time() / 1e6
        if self.t0 is None:
            self.t0 = t_abs
        t = t_abs - self.t0
        # card position and opacity
        card_y = self.H * 0.30 + SMALL_BOX * 0.62
        if self.phase == "leaving":
            lt = t_abs - self.leave_t
            self.card.set_opacity(max(0.0, 1 - lt / 0.25))
            self.power.set_opacity(max(0.0, 1 - lt / 0.25))
        else:
            a = ease_out((t - 1.3) / 0.7)
            self.card.set_opacity(a)
            self.power.set_opacity(a)
            self.card.set_margin_top(int(card_y + 24 * (1 - a)))
            if a > 0 and self.phase == "intro":
                self.phase = "ready"
                self.password.grab_focus()
        # shake on a wrong password
        if self.shake_t is not None:
            st = t_abs - self.shake_t
            if st < 0.45:
                off = int(14 * math.sin(st * 40) * (1 - st / 0.45))
                self.card.set_margin_start(max(0, off) * 2)
                self.card.set_margin_end(max(0, -off) * 2)
            else:
                self.card.set_margin_start(0)
                self.card.set_margin_end(0)
                self.shake_t = None
        self._t = t
        self._t_abs = t_abs
        self.canvas.queue_draw()
        return True

    def on_draw(self, _widget, cr):
        cr.set_source_rgb(*BG)
        cr.paint()
        if self.phase == "leaving":
            cx, cy, box, p, d, a = self.logo_state(self._t_abs)
        else:
            cx, cy, box, p, d, a = self.logo_state(self._t)
        draw_c(cr, cx, cy, box, p, d, a)
        if self.phase == "leaving" and self._t_abs - self.leave_t > 0.4:
            cr.set_source_rgba(0.78, 0.8, 0.88, min(1.0, (self._t_abs - self.leave_t - 0.4) / 0.4))
            cr.select_font_face("Cantarell", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(15)
            msg = "Starting your desktop…"
            ext = cr.text_extents(msg)
            cr.move_to(self.W / 2 - ext.width / 2, self.H / 2 + ANIM_BOX * 0.62)
            cr.show_text(msg)
        if self.tag is not None:
            cr.set_source_surface(self.tag, self.W - self.tag.get_width() - 44, self.H - self.tag.get_height() - 40)
            cr.paint()
        return False


def main():
    try:
        greeter, win = setup()
    except Exception:  # noqa: BLE001  anything before LightDM is contacted: let the launcher fall back
        import traceback
        traceback.print_exc()
        sys.exit(3)
    greeter.connect_to_daemon_sync()
    win.load_users()
    win.show_all()
    win.password.grab_focus()
    win.get_window().set_cursor(win.cursor)
    win.get_window().focus(Gdk.CURRENT_TIME)
    Gtk.main()


def setup():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-theme-name", "Arc-Dark")
    settings.set_property("gtk-font-name", "Cantarell 11")

    greeter = LightDM.Greeter()
    win = Greeter(greeter)
    greeter.connect("show-prompt", win.on_prompt)
    greeter.connect("show-message", win.on_message)
    greeter.connect("authentication-complete", win.on_auth_complete)

    root = Gdk.get_default_root_window()
    cursor = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.LEFT_PTR)
    root.set_cursor(cursor)

    win.cursor = cursor
    return greeter, win


if __name__ == "__main__":
    main()
