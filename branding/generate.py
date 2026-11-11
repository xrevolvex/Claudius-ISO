#!/usr/bin/env python3
"""
Claudius artwork generator.

Writes every SVG source in branding/svg/. Then, if Playwright and Chromium are
installed, renders them to the PNGs that the OS ships (wallpapers, login
background, boot splashes, icons, installer images).

    python3 branding/generate.py          # SVG + PNG
    python3 branding/generate.py --svg    # SVG only

All artwork is original and released under CC BY-SA 4.0 (see branding/LICENSE).
"""
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SVG_DIR = HERE / "svg"
PNG_DIR = HERE / "png"

# Palette
NAVY_0 = "#0a0e1c"
NAVY_1 = "#141b33"
NAVY_2 = "#22305c"
AMBER = "#ffb547"
CORAL = "#ff7a45"
VIOLET = "#7c5cff"


# --------------------------------------------------------------------------
# The emblem: a bold open "C" with a dot above it
# --------------------------------------------------------------------------
def emblem(cx=256, cy=256, r=176, grad="url(#gold)", **_):
    """The Claudius mark: a bold open "C" with a dot above it."""
    out = []
    sw = r * 0.30                 # stroke width of the C
    cr = r * 0.70                 # radius of the C
    ccy = cy + r * 0.14           # shift the C down a little to make room for the dot
    a0, a1 = math.radians(48), math.radians(312)
    x0, y0 = cx + cr * math.cos(a0), ccy + cr * math.sin(a0)
    x1, y1 = cx + cr * math.cos(a1), ccy + cr * math.sin(a1)
    out.append(
        f'<path d="M{x1:.2f},{y1:.2f} A{cr:.2f},{cr:.2f} 0 1 0 {x0:.2f},{y0:.2f}" '
        f'fill="none" stroke="{grad}" stroke-width="{sw:.1f}" stroke-linecap="round"/>')
    # the dot above the C
    dot_r = sw * 0.42
    out.append(f'<circle cx="{cx}" cy="{ccy - cr - sw/2 - dot_r - sw*0.45:.1f}" r="{dot_r:.1f}" fill="{grad}"/>')
    return "\n".join(out)


GOLD_DEF = f'''<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{CORAL}"/></linearGradient>'''


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs>{GOLD_DEF}{defs}</defs>{body}</svg>')


def logo_svg():
    return svg(512, 512, emblem())


def icon_svg():
    bg = (f'<defs><radialGradient id="ibg" cx="0.3" cy="0.25" r="0.9">'
          f'<stop offset="0" stop-color="{NAVY_2}"/><stop offset="1" stop-color="{NAVY_0}"/></radialGradient></defs>'
          f'<rect x="16" y="16" width="480" height="480" rx="112" fill="url(#ibg)"/>')
    return svg(512, 512, bg + emblem(256, 262, 160))


def background_layers(w, h, variant="desktop"):
    """Shared gradient and glow background used by wallpaper, login and splash."""
    defs = f'''
<radialGradient id="bg" cx="0.28" cy="0.22" r="1.05">
  <stop offset="0" stop-color="{NAVY_2}"/><stop offset="0.55" stop-color="{NAVY_1}"/>
  <stop offset="1" stop-color="{NAVY_0}"/></radialGradient>
<radialGradient id="glowA" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="{CORAL}" stop-opacity="0.55"/><stop offset="1" stop-color="{CORAL}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowB" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="{VIOLET}" stop-opacity="0.45"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowC" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="{AMBER}" stop-opacity="0.35"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{AMBER}" stop-opacity="0.9"/><stop offset="1" stop-color="{CORAL}" stop-opacity="0.2"/></linearGradient>
<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{w/40:.0f}"/></filter>
'''
    s = w / 1920
    body = [f'<rect width="{w}" height="{h}" fill="url(#bg)"/>']
    body.append(f'<g filter="url(#blur)">'
                f'<ellipse cx="{1500*s}" cy="{820*s}" rx="{620*s}" ry="{420*s}" fill="url(#glowA)"/>'
                f'<ellipse cx="{380*s}" cy="{980*s}" rx="{640*s}" ry="{380*s}" fill="url(#glowB)"/>'
                f'<ellipse cx="{1180*s}" cy="{180*s}" rx="{520*s}" ry="{260*s}" fill="url(#glowC)"/></g>')
    # orbit rings
    ocx, ocy = (1430 * s, 560 * s) if variant == "desktop" else (w / 2, h / 2)
    for i, (rr, op) in enumerate(((330, 0.22), (450, 0.13), (590, 0.07), (760, 0.04))):
        body.append(f'<circle cx="{ocx:.1f}" cy="{ocy:.1f}" r="{rr*s:.1f}" fill="none" '
                    f'stroke="url(#ring)" stroke-opacity="{op}" stroke-width="{2.2*s:.2f}"/>')
    # faint dot field
    dots = []
    import random
    rnd = random.Random(7)
    for _ in range(int(140 * (w * h) / (1920 * 1080))):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(0.6, 1.8)*s:.2f}" '
                    f'fill="#ffffff" fill-opacity="{rnd.uniform(0.05, 0.35):.2f}"/>')
    body.append("".join(dots))
    return defs, "".join(body), (ocx, ocy)


def wallpaper_svg(w=1920, h=1080):
    defs, body, (ocx, ocy) = background_layers(w, h, "desktop")
    s = w / 1920
    # the emblem sits inside the inner orbit, faint
    g = (f'<g opacity="0.92" transform="translate({ocx - 256*s*0.62:.1f},{ocy - 256*s*0.62:.1f}) '
         f'scale({s*0.62:.4f})">{emblem()}</g>')
    return svg(w, h, body + g, defs)


def login_svg(w=1920, h=1080):
    defs, body, _ = background_layers(w, h, "login")
    s = w / 1920
    g = (f'<g opacity="0.10" transform="translate({w/2 - 256*s*1.9:.1f},{h/2 - 256*s*1.9:.1f}) '
         f'scale({s*1.9:.4f})">{emblem()}</g>')
    title = (f'<text x="{w/2}" y="{120*s}" text-anchor="middle" font-family="Inter Display, Inter, sans-serif" '
             f'font-weight="300" font-size="{40*s:.0f}" letter-spacing="{18*s:.0f}" fill="#ffffff" '
             f'fill-opacity="0.85">CLAUDIUS</text>')
    return svg(w, h, body + g + title, defs)


def splash_svg(w, h, subtitle):
    defs, body, _ = background_layers(w, h, "login")
    logo_px = h * 0.34
    sc = logo_px / 512
    g = f'<g transform="translate({w/2 - 256*sc:.1f},{h*0.05:.1f}) scale({sc:.4f})">{emblem()}</g>'
    y = h * 0.05 + logo_px + h * 0.075
    t = (f'<text x="{w/2}" y="{y:.1f}" text-anchor="middle" font-family="Inter Display, Inter, sans-serif" '
         f'font-weight="600" font-size="{h*0.062:.1f}" letter-spacing="{h*0.02:.1f}" fill="#ffffff">CLAUDIUS</text>'
         f'<text x="{w/2}" y="{y + h*0.05:.1f}" text-anchor="middle" font-family="Inter, sans-serif" '
         f'font-size="{h*0.03:.1f}" letter-spacing="{h*0.006:.1f}" fill="{AMBER}">{subtitle}</text>')
    return svg(w, h, body + g + t, defs)


def welcome_svg(w=800, h=300):
    """Header image for the installer's welcome page."""
    defs, body, _ = background_layers(w, h, "login")
    sc = (h * 0.7) / 512
    g = f'<g transform="translate({w*0.08:.1f},{h*0.15:.1f}) scale({sc:.4f})">{emblem()}</g>'
    t = (f'<text x="{w*0.42}" y="{h*0.5:.1f}" font-family="Inter Display, Inter, sans-serif" font-weight="600" '
         f'font-size="{h*0.2:.1f}" letter-spacing="{h*0.03:.1f}" fill="#ffffff">CLAUDIUS</text>'
         f'<text x="{w*0.42}" y="{h*0.66:.1f}" font-family="Inter, sans-serif" font-size="{h*0.075:.1f}" '
         f'fill="{AMBER}">Light. Fast. Yours.</text>')
    return svg(w, h, body + g + t, defs)


def main():
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    sources = {
        "claudius-logo.svg": logo_svg(),
        "claudius-icon.svg": icon_svg(),
        "wallpaper.svg": wallpaper_svg(),
        "login.svg": login_svg(),
        "splash-640x480.svg": splash_svg(640, 480, "1.0  ·  LAUREL"),
        "splash-1024x768.svg": splash_svg(1024, 768, "1.0  ·  LAUREL"),
        "installer-welcome.svg": welcome_svg(),
    }
    for name, content in sources.items():
        (SVG_DIR / name).write_text(content)
    print(f"wrote {len(sources)} SVGs to {SVG_DIR}")
    if "--svg" in sys.argv:
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed: skipping PNG rendering")
        return

    PNG_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [  # (svg, png, width, height)
        ("wallpaper.svg", "claudius-wallpaper-1920x1080.png", 1920, 1080),
        ("wallpaper.svg", "claudius-wallpaper-2560x1440.png", 2560, 1440),
        ("login.svg", "claudius-login-1920x1080.png", 1920, 1080),
        ("splash-640x480.svg", "splash-640x480.png", 640, 480),
        ("splash-1024x768.svg", "splash-1024x768.png", 1024, 768),
        ("installer-welcome.svg", "installer-welcome.png", 800, 300),
        ("claudius-logo.svg", "claudius-logo-256.png", 256, 256),
        ("claudius-icon.svg", "claudius-avatar-96.png", 96, 96),
    ]
    for size in (16, 22, 24, 32, 48, 64, 128, 256):
        jobs.append(("claudius-icon.svg", f"icon-{size}.png", size, size))
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for src, dst, w, h in jobs:
            page.set_viewport_size({"width": w, "height": h})
            content = (SVG_DIR / src).read_text()
            content = content.replace(f'width="', f'data-w="', 1).replace(f'height="', f'data-h="', 1)
            html = (f'<html><body style="margin:0;background:transparent">'
                    f'<div style="width:{w}px;height:{h}px">{content.replace("<svg ", f"<svg width=\"{w}\" height=\"{h}\" preserveAspectRatio=\"xMidYMid slice\" ", 1)}</div></body></html>')
            page.set_content(html)
            page.wait_for_timeout(50)
            page.screenshot(path=str(PNG_DIR / dst), omit_background=True,
                            clip={"x": 0, "y": 0, "width": w, "height": h})
        b.close()
    print(f"rendered {len(jobs)} PNGs to {PNG_DIR}")


if __name__ == "__main__":
    main()
