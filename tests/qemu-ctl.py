#!/usr/bin/env python3
"""Drive a QEMU VM through its monitor socket (used by boot-test.sh).

    qemu-ctl.py SOCKET key ctrl-alt-t
    qemu-ctl.py SOCKET type "claudius ram\n"
    qemu-ctl.py SOCKET shot out/01-login.png
"""
import socket
import sys
import time

SPECIAL = {
    " ": "spc", "\n": "ret", "\t": "tab", "-": "minus", "_": "shift-minus", ".": "dot",
    ",": "comma", "/": "slash", "&": "shift-7", ":": "shift-semicolon", ";": "semicolon",
    "=": "equal", "+": "shift-equal", "|": "shift-backslash", ">": "shift-dot",
    "<": "shift-comma", "~": "shift-grave_accent", "'": "apostrophe", '"': "shift-apostrophe",
    "*": "shift-8", "(": "shift-9", ")": "shift-0", "!": "shift-1", "@": "shift-2",
    "#": "shift-3", "$": "shift-4", "%": "shift-5",
}


def keys(text):
    for ch in text:
        if ch.isalpha():
            yield f"shift-{ch.lower()}" if ch.isupper() else ch
        elif ch.isdigit():
            yield ch
        elif ch in SPECIAL:
            yield SPECIAL[ch]


def main():
    path, cmd, arg = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(path)
    time.sleep(0.2)

    def drain():
        try:
            while s.recv(65536):
                pass
        except (socket.timeout, BlockingIOError):
            pass

    def send(line, pause=0.09):
        s.sendall((line + "\n").encode())
        time.sleep(pause)

    s.settimeout(0.2)
    drain()
    if cmd == "key":
        send(f"sendkey {arg}")
    elif cmd == "type":
        for k in keys(arg.encode().decode("unicode_escape")):
            send(f"sendkey {k}")
    elif cmd == "shot":
        send(f"screendump {arg} -f png", pause=2.0)
    elif cmd == "quit":
        send("quit")
    drain()
    s.close()


if __name__ == "__main__":
    main()
