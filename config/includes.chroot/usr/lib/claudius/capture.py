#!/usr/bin/env python3
"""Claudius Capture: screenshots (Flameshot) and screen recording (FFmpeg).

    claudius-capture                 the Capture window
    claudius-capture --region        select an area, then annotate (arrows, blur, text), copy or save   [Print]
    claudius-capture --full          whole screen, saved and copied                                      [Shift+Print]
    claudius-capture --window        the active window                                                    [Alt+Print]
    claudius-capture --record-toggle start or stop a full-screen recording                               [Super+Shift+R]
"""
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, "/usr/lib/claudius/center")
import common as C  # noqa: E402
from common import Gdk, GLib, Gtk  # noqa: E402

PICS = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
VIDS = os.path.join(os.path.expanduser("~"), "Videos", "Recordings")
PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claudius-recording.pid")
CONF = os.path.join(C.CONFIG_DIR, "capture.json")


def notify(title, body, icon="camera-photo"):
    C.launch(["notify-send", "-a", "Claudius Capture", "-i", icon, title, body])


def screenshot(mode, delay=0):
    os.makedirs(PICS, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H-%M-%S")
    if mode == "region" and C.have("flameshot"):
        C.launch(["flameshot", "gui", "-p", PICS] + (["-d", str(delay * 1000)] if delay else []))
    elif mode == "full" and C.have("flameshot"):
        C.launch(["flameshot", "full", "-c", "-p", PICS] + (["-d", str(delay * 1000)] if delay else []))
        notify("Screenshot saved", f"Copied to the clipboard and saved in {PICS}")
    else:  # window, or Flameshot missing
        flag = {"region": "-r", "full": "-f", "window": "-w"}[mode]
        C.launch(["xfce4-screenshooter", flag, "-d", str(delay), "-s", os.path.join(PICS, f"Screenshot {stamp}.png")])


# ---------------------------------------------------------------------------- recording
def recording_pid():
    try:
        pid = int(open(PIDFILE).read())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def screen_geometry():
    s = Gdk.Screen.get_default()
    return 0, 0, s.get_width() // 2 * 2, s.get_height() // 2 * 2


def select_region():
    if not C.have("slop"):
        return None
    out = C.sh(["slop", "-f", "%x %y %w %h", "-b", "3", "-c", "1,0.58,0.28,1"], timeout=120).split()
    if len(out) != 4:
        return None
    x, y, w, h = (int(v) for v in out)
    return x, y, max(2, w // 2 * 2), max(2, h // 2 * 2)


class Recorder(Gtk.Window):
    """A small floating 'Stop' bar shown while FFmpeg records."""

    def __init__(self, geom, audio=True, gif=False, fps=30):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        os.makedirs(VIDS, exist_ok=True)
        self.out = os.path.join(VIDS, f"Recording {time.strftime('%Y-%m-%d %H-%M-%S')}.mp4")
        self.gif = gif
        x, y, w, h = geom
        disp = os.environ.get("DISPLAY", ":0")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-framerate", str(fps), "-video_size", f"{w}x{h}",
               "-draw_mouse", "1", "-i", f"{disp}+{x},{y}"]
        if audio:
            cmd += ["-f", "pulse", "-i", "default"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
        if audio:
            cmd += ["-c:a", "aac", "-b:a", "128k"]
        cmd += ["-movflags", "+faststart", self.out]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with open(PIDFILE, "w") as fh:
            fh.write(str(os.getpid()))
        self.t0 = time.monotonic()

        box = Gtk.Box(spacing=10, margin=8)
        C.styled(box, "card")
        self.dot = C.label("●", "bad")
        box.pack_start(self.dot, False, False, 0)
        self.time = C.label("00:00", "h2")
        box.pack_start(self.time, False, False, 0)
        box.pack_start(C.button("Stop", self.stop, "accent-btn"), False, False, 0)
        self.add(box)
        self.show_all()
        scr = Gdk.Screen.get_default()
        self.move(scr.get_width() - 230, 16)
        GLib.timeout_add(500, self.tick)
        signal.signal(signal.SIGUSR1, lambda *_: GLib.idle_add(self.stop))

    def tick(self):
        if self.proc.poll() is not None:
            self.finish()
            return False
        s = int(time.monotonic() - self.t0)
        self.time.set_text(f"{s // 60:02d}:{s % 60:02d}")
        self.dot.set_opacity(1.0 if s % 2 == 0 else 0.35)
        return True

    def stop(self, *_):
        if self.proc.poll() is None:
            try:
                self.proc.stdin.write(b"q")
                self.proc.stdin.flush()
            except OSError:
                self.proc.send_signal(signal.SIGINT)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.finish()
        return False

    def finish(self):
        try:
            os.remove(PIDFILE)
        except OSError:
            pass
        self.hide()
        result = self.out
        if self.gif and os.path.exists(self.out):
            gif = self.out[:-4] + ".gif"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", self.out, "-vf",
                            "fps=15,scale='min(960,iw)':-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", gif])
            if os.path.exists(gif):
                result = gif
        notify("Recording saved", result, "media-record")
        C.launch(["xdg-open", os.path.dirname(result)])
        Gtk.main_quit()


def start_recording(region=False, audio=True, gif=False):
    geom = select_region() if region else screen_geometry()
    if geom is None:
        return False
    fps = 60 if C.read_kv("/run/claudius/tune").get("PROFILE") == "performance" else 30
    Recorder(geom, audio=audio, gif=gif, fps=fps)
    return True


# ---------------------------------------------------------------------------- main window
class CaptureWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Claudius Capture")
        self.set_icon_name("camera-photo")
        self.set_resizable(False)
        C.styled(self, "claudius-window")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20)
        self.add(box)
        box.pack_start(C.label("Screenshot", "h2"), False, False, 0)
        row = Gtk.Box(spacing=8, homogeneous=True)
        for text, mode, icon in (("Region", "region", "edit-select-all"), ("Window", "window", "window-new"),
                                 ("Full screen", "full", "video-display")):
            row.pack_start(C.button(text, lambda m=mode: self.shot(m), "flat-btn", icon), True, True, 0)
        box.pack_start(row, False, False, 0)
        d = Gtk.Box(spacing=8)
        d.pack_start(C.label("Delay", "dim"), False, False, 0)
        self.delay = Gtk.SpinButton.new_with_range(0, 10, 1)
        d.pack_start(self.delay, False, False, 0)
        d.pack_start(C.label("seconds  ·  Region mode has arrows, blur, text and copy", "dim"), False, False, 0)
        box.pack_start(d, False, False, 0)

        box.pack_start(C.label("Screen recording", "h2"), False, False, 6)
        row = Gtk.Box(spacing=8, homogeneous=True)
        row.pack_start(C.button("Record screen", lambda: self.record(False), "accent-btn", "media-record"), True, True, 0)
        row.pack_start(C.button("Record region", lambda: self.record(True), "flat-btn", "edit-select-all"), True, True, 0)
        box.pack_start(row, False, False, 0)
        opts = Gtk.Box(spacing=14)
        self.audio = Gtk.CheckButton(label="Record sound", active=True)
        self.gif = Gtk.CheckButton(label="Also save as GIF", active=False)
        opts.pack_start(self.audio, False, False, 0)
        opts.pack_start(self.gif, False, False, 0)
        box.pack_start(opts, False, False, 0)
        box.pack_start(C.label("Print: region  ·  Shift+Print: screen  ·  Alt+Print: window  ·  Super+Shift+R: record",
                               "dim"), False, False, 0)
        links = Gtk.Box(spacing=8)
        links.pack_start(C.button("Screenshots folder", lambda: self.open_dir(PICS)), False, False, 0)
        links.pack_start(C.button("Recordings folder", lambda: self.open_dir(VIDS)), False, False, 0)
        box.pack_start(links, False, False, 0)
        self.show_all()

    def open_dir(self, d):
        os.makedirs(d, exist_ok=True)
        C.launch(["xdg-open", d])

    def shot(self, mode):
        delay = int(self.delay.get_value())
        self.hide()
        GLib.timeout_add(350, lambda: (screenshot(mode, delay), Gtk.main_quit()) and False)

    def record(self, region):
        audio, gif = self.audio.get_active(), self.gif.get_active()
        self.hide()

        def go():
            if not start_recording(region, audio, gif):
                Gtk.main_quit()
            return False
        GLib.timeout_add(300, go)


def main():
    args = sys.argv[1:]
    if "--region" in args:
        return screenshot("region")
    if "--full" in args:
        return screenshot("full")
    if "--window" in args:
        return screenshot("window")
    C.install_css()
    if "--record-toggle" in args:
        pid = recording_pid()
        if pid:
            os.kill(pid, signal.SIGUSR1)
            return None
        if not start_recording():
            return None
    else:
        win = CaptureWindow()
        win.connect("delete-event", lambda *_: Gtk.main_quit())
    Gtk.main()
    return None


if __name__ == "__main__":
    main()
