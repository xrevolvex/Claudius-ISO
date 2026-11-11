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


# --------------------------------------------------------------------------
# Flat backgrounds (no gradients or glows)
# --------------------------------------------------------------------------
BG = "#121830"        # flat navy
ORANGE = "#ff9447"    # flat logo orange

# Where the C sits on the 1920x1080 wallpaper: centred, a little below centre
WALL_BOX = 256                     # the 512-unit emblem box drawn at 256 px (scale 0.5)
WALL_CX, WALL_CY = 960, 1080 * 0.57


def flat_bg(w, h, color=None):
    return f'<rect width="{w}" height="{h}" fill="{color or BG}"/>'


def version_tag(w, h, ref=1080, text="#ffffff", accent=None):
    """'1.0' with a smaller 'xrevolvex' underneath, bottom-right corner."""
    accent = accent or ORANGE
    s = h / ref
    x, y = w - 64 * s, h - 78 * s
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="end" font-family="Inter Display, Inter, sans-serif" '
            f'font-weight="600" font-size="{34*s:.1f}" fill="{text}" fill-opacity="0.88">1.0</text>'
            f'<text x="{x:.1f}" y="{y + 28*s:.1f}" text-anchor="end" font-family="Inter, sans-serif" '
            f'font-weight="500" font-size="{17*s:.1f}" letter-spacing="{1.5*s:.1f}" fill="{accent}">xrevolvex</text>')


def placed_emblem(cx, cy, box_px, fill=ORANGE):
    sc = box_px / 512
    return f'<g transform="translate({cx - 256*sc:.2f},{cy - 256*sc:.2f}) scale({sc:.5f})">{emblem(grad=fill)}</g>'


def wallpaper_svg(w=1920, h=1080, accent=None, light=False):
    s = h / 1080
    accent = accent or ORANGE
    bg, text = ("#eef1f8", "#1a2242") if light else (BG, "#ffffff")
    return svg(w, h, flat_bg(w, h, bg) + placed_emblem(WALL_CX * s, WALL_CY * s, WALL_BOX * s, accent)
               + version_tag(w, h, text=text, accent=accent))


# Wallpaper pack: one flat wallpaper per accent colour, dark and light (matches common.ACCENTS)
ACCENT_COLORS = {"orange": "#ff9447", "blue": "#4c8dff", "green": "#3ecf8e", "teal": "#2ec4c9",
                 "purple": "#a77bff", "pink": "#ff6fb5", "red": "#ff5f6d"}


def login_svg(w=1920, h=1080):
    """Background for the fallback login screen: flat, with the version tag."""
    return svg(w, h, flat_bg(w, h) + version_tag(w, h))


def splash_svg(w, h):
    """Boot menu background (ISOLINUX / GRUB): logo on top, menu below."""
    logo_px = h * 0.30
    top = h * 0.06
    g = placed_emblem(w / 2, top + logo_px / 2, logo_px)
    y = top + logo_px + h * 0.07
    t = (f'<text x="{w/2}" y="{y:.1f}" text-anchor="middle" font-family="Inter Display, Inter, sans-serif" '
         f'font-weight="600" font-size="{h*0.062:.1f}" letter-spacing="{h*0.02:.1f}" fill="#ffffff">CLAUDIUS</text>')
    return svg(w, h, flat_bg(w, h) + g + t + version_tag(w, h, ref=1080 * 0.62))


def version_tag_svg():
    """Standalone '1.0 / xrevolvex' tag (transparent) for the boot animation."""
    return svg(200, 76, f'<text x="196" y="36" text-anchor="end" font-family="Inter Display, Inter, sans-serif" '
                        f'font-weight="600" font-size="34" fill="#ffffff" fill-opacity="0.88">1.0</text>'
                        f'<text x="196" y="64" text-anchor="end" font-family="Inter, sans-serif" font-weight="500" '
                        f'font-size="17" letter-spacing="1.5" fill="{ORANGE}">xrevolvex</text>')


def welcome_svg(w=800, h=300):
    """Header image for the installer's welcome page."""
    g = placed_emblem(w * 0.2, h * 0.5, h * 0.72)
    t = (f'<text x="{w*0.40}" y="{h*0.5:.1f}" font-family="Inter Display, Inter, sans-serif" font-weight="600" '
         f'font-size="{h*0.2:.1f}" letter-spacing="{h*0.03:.1f}" fill="#ffffff">CLAUDIUS</text>'
         f'<text x="{w*0.40}" y="{h*0.66:.1f}" font-family="Inter, sans-serif" font-size="{h*0.075:.1f}" '
         f'fill="{ORANGE}">Light. Fast. Yours.</text>')
    return svg(w, h, flat_bg(w, h) + g + t)


# --------------------------------------------------------------------------
# Boot animation frames: the C draws itself, the dot drops in, then it breathes
# --------------------------------------------------------------------------
ANIM_BOX = 220          # px, frame size (the 512-unit emblem box)
DRAW_FRAMES = 48        # stroke tracing
DOT_FRAMES = 16         # dot drops in
PULSE_FRAMES = 64       # looping breathe


def _ease(t):
    return 1 - (1 - t) ** 3


def anim_frame_svg(i):
    r = 176; sw = r * 0.30; cr = r * 0.70; ccy = 256 + r * 0.14
    a0, a1 = math.radians(48), math.radians(312)
    x0, y0 = 256 + cr * math.cos(a0), ccy + cr * math.sin(a0)
    x1, y1 = 256 + cr * math.cos(a1), ccy + cr * math.sin(a1)
    length = cr * math.radians(264)
    dot_r = sw * 0.42
    dot_cy = ccy - cr - sw / 2 - dot_r - sw * 0.45
    if i < DRAW_FRAMES:
        drawn, dot_t, op = _ease((i + 1) / DRAW_FRAMES), 0.0, 1.0
    elif i < DRAW_FRAMES + DOT_FRAMES:
        drawn, dot_t, op = 1.0, _ease((i - DRAW_FRAMES + 1) / DOT_FRAMES), 1.0
    else:
        k = (i - DRAW_FRAMES - DOT_FRAMES) / PULSE_FRAMES
        drawn, dot_t, op = 1.0, 1.0, 0.62 + 0.38 * (0.5 + 0.5 * math.cos(2 * math.pi * k))
    body = (f'<path d="M{x1:.2f},{y1:.2f} A{cr:.2f},{cr:.2f} 0 1 0 {x0:.2f},{y0:.2f}" fill="none" '
            f'stroke="{ORANGE}" stroke-width="{sw:.1f}" stroke-linecap="round" '
            f'stroke-dasharray="{length:.2f} {length:.2f}" stroke-dashoffset="{length * (1 - drawn):.2f}"/>')
    if dot_t > 0:
        body += (f'<circle cx="256" cy="{dot_cy - 60 * (1 - dot_t):.2f}" r="{dot_r * (0.4 + 0.6 * dot_t):.2f}" '
                 f'fill="{ORANGE}" fill-opacity="{dot_t:.3f}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
            f'<g opacity="{op:.3f}">{body}</g></svg>')


def main():
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    sources = {
        "claudius-logo.svg": logo_svg(),
        "claudius-icon.svg": icon_svg(),
        "wallpaper.svg": wallpaper_svg(),
        "login.svg": login_svg(),
        "splash-640x480.svg": splash_svg(640, 480),
        "splash-1024x768.svg": splash_svg(1024, 768),
        "version-tag.svg": version_tag_svg(),
        "installer-welcome.svg": welcome_svg(),
    }
    for acc, col in ACCENT_COLORS.items():
        sources[f"wall-{acc}.svg"] = wallpaper_svg(accent=col)
        sources[f"wall-{acc}-light.svg"] = wallpaper_svg(accent=col, light=True)
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
        ("version-tag.svg", "version-tag.png", 200, 76),
    ]
    for size in (16, 22, 24, 32, 48, 64, 128, 256):
        jobs.append(("claudius-icon.svg", f"icon-{size}.png", size, size))
    (PNG_DIR / "wallpapers").mkdir(parents=True, exist_ok=True)
    for acc in ACCENT_COLORS:
        for suffix in ("", "-light"):
            jobs.append((f"wall-{acc}{suffix}.svg", f"wallpapers/claudius-{acc}{suffix}.png", 1920, 1080))
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
        # boot animation frames
        anim = PNG_DIR / "anim"
        anim.mkdir(exist_ok=True)
        page.set_viewport_size({"width": ANIM_BOX, "height": ANIM_BOX})
        total = DRAW_FRAMES + DOT_FRAMES + PULSE_FRAMES
        for i in range(total):
            content = anim_frame_svg(i).replace('width="512" height="512"', f'width="{ANIM_BOX}" height="{ANIM_BOX}"', 1)
            page.set_content(f'<html><body style="margin:0;background:transparent">{content}</body></html>')
            page.screenshot(path=str(anim / f"frame-{i:03d}.png"), omit_background=True,
                            clip={"x": 0, "y": 0, "width": ANIM_BOX, "height": ANIM_BOX})
        b.close()
    print(f"rendered {len(jobs)} PNGs and {total} animation frames to {PNG_DIR}")

    # geometry shared with the greeter and the session splash (they draw the C live)
    import json
    (PNG_DIR / "geometry.json").write_text(json.dumps({
        "background": BG, "orange": ORANGE,
        "wallpaper": {"width": 1920, "height": 1080, "cx": WALL_CX, "cy": WALL_CY, "box": WALL_BOX},
        "anim": {"box": ANIM_BOX, "draw": DRAW_FRAMES, "dot": DOT_FRAMES, "pulse": PULSE_FRAMES},
    }, indent=2))


if __name__ == "__main__":
    main()
