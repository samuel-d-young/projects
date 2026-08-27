#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_legend.py - the legend collar that says what each lit pixel means.

WHAT THIS IS
------------
A flat ring that the clock body drops into, carrying printed labels for the
AMBIENT pixels. The hands are self-explanatory; the status pixels are not --
a single amber dot at 3 o'clock means nothing until someone tells you it is
the garage. This is that telling, on the object rather than in a document.

Laser cut it (SVG, two layers) or 3D print it (SCAD -> STL). Both come out of
the same numbers here, so they cannot disagree.

WHY IT SITS OUTSIDE THE BODY, NOT ON THE FACE
---------------------------------------------
On the 32 the LED ring is 111.85 OD inside a body of 119.85 OD. That leaves
4 mm of face between the two -- not enough for a word, let alone a legend. So
the collar goes around the OUTSIDE of the body: its bore clears the body, and
the whole band is free for text.

WHERE THE POSITIONS COME FROM
-----------------------------
Read out of the ring lambda in mini-round-clock-with-display.yaml rather than
assumed. The ambient pixels are placed with P(fraction):

    P(0.00)  12 o'clock   bin night     green = waste, yellow = recycling
    P(0.25)   3 o'clock   garage open   amber
    P(0.75)   9 o'clock   driveway      blinking red
    P(0.50)   6 o'clock   HA dropped    dim red
    P(0.5 + (w-1.5)/N)    who is home   four dots straddling 6 o'clock

The presence dots land on LEDs 15/16/17/18 of 32 -- Sam, Laura, Amanda, Zac,
left to right. Note that on any ring size the HA-dropped tint shares 6 o'clock
with the second presence dot; that is the firmware's arrangement, and the
legend says "who's home" there because that is what is lit far more often.

USAGE
-----
    python build_legend.py                 # every variant, every size
    python build_legend.py --size 32       # just the 32-LED collar
    python build_legend.py --list          # what it can make
"""

import argparse
import io
import math
import os

# -----------------------------------------------------------------------------
# SIZES - body radius is what the bore has to clear
# -----------------------------------------------------------------------------
# r_body: outer radius of the clock body, from enclosure/mini/v2/params.py
#         (R_BODY, R_BODY32) and enclosure/params.py (the 60 build).
# n:      LEDs on that ring, which sets where the tick marks go.
SIZES = {
    "24": {"n": 24, "r_body": 53.9926, "band": 22.0, "label": "24-LED"},
    "32": {"n": 32, "r_body": 59.9250, "band": 26.0, "label": "32-LED"},
    "60": {"n": 60, "r_body": 120.000, "band": 34.0, "label": "60-LED"},
}

#: Printed clearance between the body and the collar's bore. 0.4 is a print
#: fit; a laser kerf is usually smaller, but the same number cuts fine and a
#: collar that is slightly loose is far better than one that will not go on.
BORE_CLEAR = 0.40

#: Laser conventions. Most cutters key off colour: pure red = cut through,
#: black = engrave. Kept as constants so a different cutter is one edit.
CUT_COLOUR = "#ff0000"
CUT_WIDTH = 0.1
ENGRAVE_COLOUR = "#000000"


# -----------------------------------------------------------------------------
# THE LEGENDS
# -----------------------------------------------------------------------------
# Each entry: (fraction round the dial, label, swatch colour, sub-label or None)
# Fractions match P() in the firmware. 0.0 is 12 o'clock, increasing clockwise.
STATUS = [
    (0.00, "BIN NIGHT", "#00961e", "green waste / yellow recycling"),
    (0.25, "GARAGE OPEN", "#964600", None),
    (0.50, "WHO'S HOME", "#002859", "Sam  Laura  Amanda  Zac"),
    (0.75, "DRIVEWAY", "#c80000", "blinking = someone there"),
]

HANDS = [
    (0.00, "HOUR", "#ff7b1e", "the short one, orange"),
    (0.25, "MINUTE", "#3c8cff", "blue"),
    (0.50, "SECOND", "#9a9a9a", "grey, off by default"),
    (0.75, "TIMER", "#00b4a0", "teal arc, drains to zero"),
]

PRESENCE = [
    (0.4531, "SAM", "#002859", None),
    (0.4844, "LAURA", "#5a0046", None),
    (0.5156, "AMANDA", "#004628", None),
    (0.5469, "ZAC", "#463200", None),
]

VARIANTS = {
    "status": {
        "title": "Ambient status",
        "items": STATUS,
        "note": "What the coloured dots mean. Hands are hour/minute/second.",
    },
    "hands": {
        "title": "Hands and timer",
        "items": HANDS,
        "note": "For a clock used mostly as a timer.",
    },
    "presence": {
        "title": "Who is home",
        "items": PRESENCE,
        "note": "The four dots either side of 6 o'clock, in order.",
    },
    "hours": {"title": "Hour numerals", "items": None, "note": "1-12, no status."},
    "blank": {"title": "Blank", "items": None, "note": "Ticks only - label it yourself."},
}


# -----------------------------------------------------------------------------
# geometry helpers
# -----------------------------------------------------------------------------
def polar(cx, cy, r, frac):
    """Point at `frac` of the way round, 0 = 12 o'clock, clockwise."""
    a = frac * 2.0 * math.pi - math.pi / 2.0
    return cx + r * math.cos(a), cy + r * math.sin(a)


def upright(frac):
    """True when a label at this dial position needs its baseline reversed.

    Text on a clockwise arc reads correctly across the top and stands on its
    head across the bottom -- which is exactly where "WHO'S HOME" sits. Any
    label in the bottom half gets an anticlockwise baseline instead, so it
    reads left-to-right to someone standing in front of the clock.
    """
    f = frac % 1.0
    return 0.25 < f < 0.75


def arc_path(cx, cy, r, f0, f1, flip=False):
    """An SVG baseline arc from f0 to f1.

    flip runs it the other way round, which puts the text on the outside of
    the curve and the right way up for the bottom half of the dial.
    """
    if flip:
        f0, f1 = f1, f0
        sweep = 0
    else:
        sweep = 1
    x0, y0 = polar(cx, cy, r, f0)
    x1, y1 = polar(cx, cy, r, f1)
    large = 1 if abs(f1 - f0) % 1.0 > 0.5 else 0
    return "M %.3f %.3f A %.3f %.3f 0 %d %d %.3f %.3f" % (
        x0, y0, r, r, large, sweep, x1, y1)


# -----------------------------------------------------------------------------
# SVG
# -----------------------------------------------------------------------------
def build_svg(size_key, variant_key):
    S = SIZES[size_key]
    V = VARIANTS[variant_key]
    n = S["n"]

    r_in = S["r_body"] + BORE_CLEAR
    r_out = r_in + S["band"]
    pad = 4.0
    span = 2 * (r_out + pad)
    cx = cy = r_out + pad

    # Text sits on two arcs: the label out near the rim, a sub-label inboard.
    r_label = r_in + S["band"] * 0.62
    r_sub = r_in + S["band"] * 0.30
    r_tick_o = r_out - 1.5
    r_tick_i = r_out - 4.5
    r_swatch = r_in + S["band"] * 0.86

    fs_label = max(3.2, S["band"] * 0.185)
    fs_sub = max(2.4, S["band"] * 0.115)
    fs_title = max(2.8, S["band"] * 0.13)

    o = io.StringIO()
    o.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    o.write('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
            'width="%.3fmm" height="%.3fmm" viewBox="0 0 %.3f %.3f">\n'
            % (span, span, span, span))
    o.write("  <!-- %s legend collar, %s variant.\n"
            "       bore %.2f dia (body %.2f + %.2f clearance), outside %.2f dia.\n"
            "       RED = cut through, BLACK = engrave. -->\n"
            % (S["label"], variant_key, r_in * 2, S["r_body"] * 2,
               BORE_CLEAR, r_out * 2))

    # ---- defs: the text baselines ----
    o.write("  <defs>\n")
    if V["items"]:
        for i, (frac, _lab, _col, sub) in enumerate(V["items"]):
            half = 0.115 if len(V["items"]) <= 4 else 0.035
            fl = upright(frac)
            # A flipped baseline hangs its text inward instead of outward, so
            # the radius is nudged by the cap height to land in the same band.
            rl = r_label + (fs_label if fl else 0.0)
            rs = r_sub + (fs_sub if fl else 0.0)
            o.write('    <path id="lab%d" fill="none" d="%s"/>\n'
                    % (i, arc_path(cx, cy, rl, frac - half, frac + half, fl)))
            if sub:
                # The sub-label sits on a smaller circle, so the same angular
                # span buys less arc. Scale it by the radius ratio, or a long
                # sub-label runs out of baseline and overlaps itself.
                hs = half * (rl / rs)
                o.write('    <path id="sub%d" fill="none" d="%s"/>\n'
                        % (i, arc_path(cx, cy, rs, frac - hs, frac + hs, fl)))
    # The title sits low-left, on a flipped baseline so it reads normally.
    o.write('    <path id="title" fill="none" d="%s"/>\n'
            % arc_path(cx, cy, r_sub + fs_title, 0.60, 0.90, True))
    o.write("  </defs>\n\n")

    # ---- CUT layer ----
    o.write('  <g id="CUT" inkscape:label="CUT" inkscape:groupmode="layer" '
            'fill="none" stroke="%s" stroke-width="%.2f">\n'
            % (CUT_COLOUR, CUT_WIDTH))
    o.write('    <circle cx="%.3f" cy="%.3f" r="%.3f"/>\n' % (cx, cy, r_out))
    o.write('    <circle cx="%.3f" cy="%.3f" r="%.3f"/>\n' % (cx, cy, r_in))
    o.write("  </g>\n\n")

    # ---- ENGRAVE layer ----
    o.write('  <g id="ENGRAVE" inkscape:label="ENGRAVE" '
            'inkscape:groupmode="layer" fill="%s" stroke="none" '
            'font-family="DejaVu Sans, Helvetica, Arial, sans-serif">\n'
            % ENGRAVE_COLOUR)

    # LED ticks: one per pixel, so the collar lines up with the ring and you
    # can count round to a dot rather than guessing which one is lit.
    for i in range(n):
        f = i / float(n)
        x0, y0 = polar(cx, cy, r_tick_i, f)
        x1, y1 = polar(cx, cy, r_tick_o, f)
        major = (i % (n // 12) == 0) if n % 12 == 0 else (i % 4 == 0)
        o.write('    <line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                'stroke="%s" stroke-width="%.2f"/>\n'
                % (x0, y0, x1, y1, ENGRAVE_COLOUR, 0.6 if major else 0.25))

    if variant_key == "hours":
        for h in range(1, 13):
            x, y = polar(cx, cy, r_label, h / 12.0)
            o.write('    <text x="%.3f" y="%.3f" font-size="%.2f" '
                    'text-anchor="middle" dominant-baseline="central" '
                    'font-weight="600">%d</text>\n' % (x, y, fs_label * 1.3, h))

    elif V["items"]:
        for i, (frac, lab, col, sub) in enumerate(V["items"]):
            # Swatch: an outlined dot on the LED's own radial line. Outlined,
            # not filled, so a laser engraves a ring rather than a blob -- and
            # so it can be filled with paint or a coloured insert afterwards.
            sx, sy = polar(cx, cy, r_swatch, frac)
            o.write('    <circle cx="%.3f" cy="%.3f" r="%.2f" fill="none" '
                    'stroke="%s" stroke-width="0.35"/>\n'
                    % (sx, sy, max(1.0, S["band"] * 0.055), ENGRAVE_COLOUR))
            o.write('    <!-- lit colour here is %s -->\n' % col)
            o.write('    <text font-size="%.2f" font-weight="700" '
                    'letter-spacing="%.2f"><textPath xlink:href="#lab%d" '
                    'startOffset="50%%" text-anchor="middle">%s</textPath></text>\n'
                    % (fs_label, fs_label * 0.06, i, lab))
            if sub:
                o.write('    <text font-size="%.2f"><textPath '
                        'xlink:href="#sub%d" startOffset="50%%" '
                        'text-anchor="middle">%s</textPath></text>\n'
                        % (fs_sub, i, _esc(sub)))

    if variant_key != "blank":
        o.write('    <text font-size="%.2f" fill="%s" opacity="0.75">'
                '<textPath xlink:href="#title" startOffset="50%%" '
                'text-anchor="middle">%s</textPath></text>\n'
                % (fs_title, ENGRAVE_COLOUR, _esc(V["title"])))

    o.write("  </g>\n</svg>\n")
    return o.getvalue()


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace("'", "&apos;"))


# -----------------------------------------------------------------------------
# OpenSCAD
# -----------------------------------------------------------------------------
def build_scad(size_key, variant_key):
    S = SIZES[size_key]
    V = VARIANTS[variant_key]
    n = S["n"]
    r_in = S["r_body"] + BORE_CLEAR
    r_out = r_in + S["band"]
    r_label = r_in + S["band"] * 0.62
    r_sub = r_in + S["band"] * 0.30
    r_swatch = r_in + S["band"] * 0.86
    fs_label = max(3.2, S["band"] * 0.185)
    fs_sub = max(2.4, S["band"] * 0.115)

    o = io.StringIO()
    o.write("// %s legend collar - %s\n" % (S["label"], V["title"]))
    o.write("// Generated by build_legend.py. Edit that, not this.\n")
    o.write("//\n")
    o.write("// Text is RAISED by TEXT_H above the plate, so it reads without\n")
    o.write("// paint. For a two-colour print, pause at PLATE_H and swap\n")
    o.write("// filament -- the text starts exactly at that height.\n")
    o.write("//\n")
    o.write("// Bore is body dia %.2f + %.2f clearance.\n"
            % (S["r_body"] * 2, BORE_CLEAR))
    o.write("$fn = 160;\n")
    o.write("PLATE_H = 2.4;   // collar thickness\n")
    o.write("TEXT_H  = 0.6;   // raised text, 3 layers at 0.2\n")
    o.write("TICK_H  = 0.4;\n")
    o.write("R_IN = %.4f;\nR_OUT = %.4f;\n\n" % (r_in, r_out))

    o.write("module plate() {\n")
    o.write("  difference() {\n")
    o.write("    cylinder(h = PLATE_H, r = R_OUT);\n")
    o.write("    translate([0, 0, -1]) cylinder(h = PLATE_H + 2, r = R_IN);\n")
    o.write("  }\n}\n\n")

    # curved_text places a label centred on a dial fraction, tangential.
    o.write("// A label centred on `frac` of the dial, lying tangentially.\n")
    o.write("// 0 = 12 o'clock, increasing clockwise, matching P() in the\n")
    o.write("// firmware -- so a label lands on the pixel it describes.\n")
    o.write("// `flip` turns a bottom-half label the right way up: without it\n")
    o.write("// everything from 3 to 9 o'clock stands on its head.\n")
    o.write("module label(frac, r, size, txt, bold = true, flip = false) {\n")
    o.write("  a = frac * 360;\n")
    o.write("  rotate([0, 0, -a + (flip ? 180 : 0)])\n")
    o.write("    translate([0, flip ? -r : r, PLATE_H])\n")
    o.write("      linear_extrude(height = TEXT_H)\n")
    o.write("        text(txt, size = size, halign = \"center\",\n")
    o.write("             valign = \"center\", font = bold ?\n")
    o.write("             \"DejaVu Sans:style=Bold\" : \"DejaVu Sans\");\n")
    o.write("}\n\n")

    o.write("module ticks() {\n")
    o.write("  for (i = [0 : %d]) {\n" % (n - 1))
    o.write("    a = i * %.6f;\n" % (360.0 / n))
    o.write("    major = (i %% %d) == 0;\n" % max(1, n // 12))
    o.write("    rotate([0, 0, -a])\n")
    o.write("      translate([-(major ? 0.5 : 0.2), R_OUT - 4.5, PLATE_H])\n")
    o.write("        cube([major ? 1.0 : 0.4, 3.0, TICK_H]);\n")
    o.write("  }\n}\n\n")

    o.write("module legend() {\n  plate();\n  ticks();\n")
    if variant_key == "hours":
        for h in range(1, 13):
            o.write('  label(%.6f, %.3f, %.2f, "%d");\n'
                    % (h / 12.0, r_label, fs_label * 1.3, h))
    elif V["items"]:
        for frac, lab, col, sub in V["items"]:
            fl = "true" if upright(frac) else "false"
            o.write('  // lit colour: %s\n' % col)
            o.write('  label(%.6f, %.3f, %.2f, "%s", true, %s);\n'
                    % (frac, r_label, fs_label, lab, fl))
            if sub:
                o.write('  label(%.6f, %.3f, %.2f, "%s", false, %s);\n'
                        % (frac, r_sub, fs_sub, sub, fl))
            o.write("  rotate([0, 0, %.4f]) translate([0, %.3f, PLATE_H])\n"
                    "    cylinder(h = TEXT_H, r = %.2f);\n"
                    % (-frac * 360, r_swatch, max(1.0, S["band"] * 0.055)))
    o.write("}\n\nlegend();\n")
    return o.getvalue()


# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", choices=sorted(SIZES), action="append",
                    help="ring size; repeatable. Default: all.")
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append",
                    help="legend variant; repeatable. Default: all.")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        print("sizes:")
        for k, v in sorted(SIZES.items()):
            print("  %-4s %-8s body %.2f dia -> collar %.2f dia"
                  % (k, v["label"], v["r_body"] * 2,
                     (v["r_body"] + BORE_CLEAR + v["band"]) * 2))
        print("variants:")
        for k, v in sorted(VARIANTS.items()):
            print("  %-9s %-18s %s" % (k, v["title"], v["note"]))
        return

    sizes = a.size or sorted(SIZES)
    variants = a.variant or sorted(VARIANTS)
    made = 0
    for s in sizes:
        for v in variants:
            for ext, fn in (("svg", build_svg), ("scad", build_scad)):
                path = os.path.join(a.out, "legend-%s-%s.%s" % (s, v, ext))
                io.open(path, "w", encoding="utf-8", newline="\n").write(fn(s, v))
                made += 1
        S = SIZES[s]
        print("%-4s collar %.2f dia, bore %.2f dia, %d ticks"
              % (s, (S["r_body"] + BORE_CLEAR + S["band"]) * 2,
                 (S["r_body"] + BORE_CLEAR) * 2, S["n"]))
    print("%d files in %s" % (made, a.out))


if __name__ == "__main__":
    main()
