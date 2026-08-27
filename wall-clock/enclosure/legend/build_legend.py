#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_legend.py - the legend collar that says what each lit pixel means.

WHAT THIS IS
------------
A flat ring the clock body drops into, carrying a printed name for each LED.
The hands are self-explanatory; the ambient pixels are not -- a single amber
dot at 3 o'clock means nothing until something tells you it is the garage.
This is that telling, on the object rather than in a document.

Laser cut it (SVG, two layers) or 3D print it (SCAD -> STL). Both come out of
the same numbers, so they cannot disagree.

EVERY LABEL IS UPRIGHT
----------------------
Text is horizontal, never curved and never rotated, so the whole collar reads
from across the room without tilting your head. Curved text looks better in a
render and is worse on a wall: half of it ends up upside down.

Upright labels sitting on one circle collide near 12 and 6, where neighbours
sit side by side. So they ALTERNATE between two radii -- odd positions on an
inner ring, even on an outer one -- which about doubles how many fit before
anything touches. `--check` reports the tightest gap on the sheet.

WHERE THE POSITIONS COME FROM
-----------------------------
Read out of the ring lambda in mini-round-clock-with-display.yaml, not assumed:

    P(0.00)  LED 0    bin night     green = waste, yellow = recycling
    P(0.25)  LED n/4  garage open   amber
    P(0.75)  LED 3n/4 driveway      blinking red
    P(0.50)  LED n/2  HA dropped    dim red
    P(0.5 + (w-1.5)/n)              who is home, four dots straddling 6

On the 32 the presence dots land on LEDs 15/16/17/18 - Sam, Laura, Amanda,
Zac, left to right.

NAMING A PIXEL DOES NOT LIGHT IT
--------------------------------
The `full` variant names every LED, because that is what was asked for, but
only the pixels listed above are driven by the firmware today. The rest are
SUGGESTIONS - edit SLOT_NAMES below to whatever you want, and add a matching
status pixel in the ring lambda to make one actually light. A collar that
names a light that never comes on is a collar that lies.

USAGE
-----
    python build_legend.py                 # every variant, every size
    python build_legend.py --size 32       # just the 32-LED collar
    python build_legend.py --check         # report tightest label spacing
    python build_legend.py --list
"""

import argparse
import io
import math
import os

# -----------------------------------------------------------------------------
# SIZES
# -----------------------------------------------------------------------------
# r_body: outer radius of the clock body, from enclosure/mini/v2/params.py
#         (R_BODY, R_BODY32) and enclosure/params.py (the 60 build).
# band:   radial depth of the collar. The `full` variant overrides this,
#         because 32 names need two text rings and a wider band to hold them.
SIZES = {
    "24": {"n": 24, "r_body": 53.9926, "band": 22.0, "band_full": 30.0, "label": "24-LED"},
    "32": {"n": 32, "r_body": 59.9250, "band": 26.0, "band_full": 34.0, "label": "32-LED"},
    "60": {"n": 60, "r_body": 120.000, "band": 34.0, "band_full": 40.0, "label": "60-LED"},
}

BORE_CLEAR = 0.40          # print fit between body and bore
CUT_COLOUR = "#ff0000"     # laser convention: pure red cuts through
CUT_WIDTH = 0.1
ENGRAVE_COLOUR = "#000000"


# -----------------------------------------------------------------------------
# NAMES
# -----------------------------------------------------------------------------
# Keyed by LED index on a 32-LED ring. The five marked REAL are what the
# firmware actually drives; everything else is a suggestion for a slot you
# could wire up. Rename freely - nothing downstream reads these.
#: ONLY what the firmware actually drives. Nothing here is invented: every
#: entry was read out of the ring lambda, and if a pixel is not listed the
#: firmware does not light it for any reason today.
#:
#: Unnamed pixels are NOT left off the collar -- they get their LED index
#: engraved instead, which is a fact rather than a guess and is exactly what
#: you need to add one later: pick a number, add a status pixel at P(i/n) in
#: the ring lambda, and write the name on this line.
SLOT_NAMES_32 = {
    0:  "BIN NIGHT",   # P(0.00) - binary_sensor.wall_clock_bin_night
    8:  "GARAGE",      # P(0.25) - binary_sensor.wall_clock_garage_open
    15: "SAM",         # presence - binary_sensor.wall_clock_home_sam
    16: "LAURA",       # presence - and where the HA-dropped tint lands
    17: "AMANDA",      # presence - binary_sensor.wall_clock_home_amanda
    18: "ZAC",         # presence - binary_sensor.wall_clock_home_zac
    24: "DRIVEWAY",    # P(0.75) - binary_sensor.wall_clock_driveway_unknown
}

# The four-label sets. (fraction round the dial, label, lit colour, sub-label)
STATUS = [
    (0.00, "BIN NIGHT", "#00961e", "green / yellow"),
    (0.25, "GARAGE OPEN", "#964600", None),
    (0.50, "WHO'S HOME", "#002859", "Sam Laura Amanda Zac"),
    (0.75, "DRIVEWAY", "#c80000", "blinking"),
]
HANDS = [
    (0.00, "HOUR", "#ff7b1e", "orange"),
    (0.25, "MINUTE", "#3c8cff", "blue"),
    (0.50, "SECOND", "#9a9a9a", "grey"),
    (0.75, "TIMER", "#00b4a0", "teal arc"),
]
PRESENCE = [
    (0.4531, "SAM", "#002859", None),
    (0.4844, "LAURA", "#5a0046", None),
    (0.5156, "AMANDA", "#004628", None),
    (0.5469, "ZAC", "#463200", None),
]

VARIANTS = {
    "full":     {"title": "Every pixel named", "items": None,
                 "note": "One name per LED. Edit SLOT_NAMES_32."},
    "status":   {"title": "Ambient status", "items": STATUS,
                 "note": "Only the pixels the firmware drives today."},
    "hands":    {"title": "Hands and timer", "items": HANDS,
                 "note": "For a clock used mostly as a timer."},
    "presence": {"title": "Who is home", "items": PRESENCE,
                 "note": "The four dots either side of 6 o'clock."},
    "hours":    {"title": "Hour numerals", "items": None, "note": "1-12."},
    "blank":    {"title": "Blank", "items": None, "note": "Ticks only."},
}


# -----------------------------------------------------------------------------
def polar_svg(cx, cy, r, frac):
    """SVG point at `frac` round the dial. 0 = 12 o'clock, clockwise, y down."""
    a = frac * 2.0 * math.pi - math.pi / 2.0
    return cx + r * math.cos(a), cy + r * math.sin(a)


def polar_scad(r, frac):
    """OpenSCAD point, same convention but y up."""
    a = frac * 2.0 * math.pi
    return r * math.sin(a), r * math.cos(a)


def slots_for(size_key):
    """The (frac, text, named) list for the `full` variant at this ring size.

    A pixel the firmware drives gets its name; every other pixel gets its LED
    index. SLOT_NAMES_32 is written against the 32, so on another ring size
    the four cardinals are recomputed from the fractions rather than scaled --
    BIN NIGHT belongs at 12 o'clock on any ring, not at LED 0 of a 24 that
    happens to round there.
    """
    n = SIZES[size_key]["n"]

    # P() rounds with C's lroundf, which goes half AWAY FROM ZERO. Python's
    # round() is banker's and goes to even -- with that, 15.5 and 16.5 both
    # land on 16, LAURA and AMANDA collide and one silently overwrites the
    # other. Match the firmware, not the language.
    def lround(x):
        return int(math.floor(x + 0.5))

    cardinal = {0.00: "BIN NIGHT", 0.25: "GARAGE", 0.75: "DRIVEWAY"}
    # The presence dots are placed by P(0.5 + (w-1.5)/n), which lands on the
    # four pixels straddling 6 o'clock whatever n is.
    presence = {}
    for w, who in enumerate(("SAM", "LAURA", "AMANDA", "ZAC")):
        presence[lround((0.5 + (w - 1.5) / n) * n) % n] = who

    out = []
    for i in range(n):
        frac = i / float(n)
        name = None
        for cf, cn in cardinal.items():
            if lround(cf * n) % n == i:
                name = cn
        if i in presence:
            name = presence[i]
        out.append((frac, name if name else str(i), name is not None))
    return out


def est_width(text, fs):
    """Rough advance width. 0.62 em per char suits DejaVu Sans caps closely
    enough to catch a collision before it reaches the laser."""
    return len(text) * fs * 0.62


def check_spacing(size_key):
    """Smallest gap between neighbouring `full` labels, in mm.

    Positive means clear. Labels alternate radius, so only same-ring
    neighbours -- two steps apart -- can actually touch.
    """
    S = SIZES[size_key]
    r_in = S["r_body"] + BORE_CLEAR
    r_out = r_in + S["band_full"]
    fs = full_font(S)
    r_a, r_b = r_out - fs * 1.5, r_out - fs * 3.6
    worst = 1e9
    items = slots_for(size_key)
    for i, (frac, name, _) in enumerate(items):
        j = (i + 2) % len(items)
        other = items[j]
        r = r_a if i % 2 == 0 else r_b
        x0, y0 = polar_svg(0, 0, r, frac)
        x1, y1 = polar_svg(0, 0, r, other[0])
        centres = math.hypot(x1 - x0, y1 - y0)
        gap = centres - (est_width(name, fs) + est_width(other[1], fs)) / 2.0
        worst = min(worst, gap)
    return worst, fs


def full_font(S):
    """Font size for the `full` variant: as large as the tightest pair allows."""
    return max(2.2, min(3.6, S["band_full"] * 0.105))


def fit_radius(r, frac, w, h, r_in, r_out, margin=1.2):
    """Pull a label inward until its whole box sits inside the band.

    An UPRIGHT label is horizontal, so at 3 and 9 o'clock its width points
    radially and a word placed on the nominal radius hangs straight over the
    cut line -- which on a laser means the end of the word is simply not
    there. At 12 and 6 the same width is tangential and costs nothing. So the
    correction has to be per-label, from its real box, not a fixed inset.
    """
    for _ in range(4):
        x, y = polar_svg(0.0, 0.0, r, frac)
        corners = [(x + sx * w / 2.0, y + sy * h / 2.0)
                   for sx in (-1, 1) for sy in (-1, 1)]
        rmax = max(math.hypot(a, b) for a, b in corners)
        rmin = min(math.hypot(a, b) for a, b in corners)
        over = rmax - (r_out - margin)
        under = (r_in + margin) - rmin
        if over <= 0 and under <= 0:
            break
        if over > 0:
            r -= over
        elif under > 0:
            r += under
    return r


# -----------------------------------------------------------------------------
# SVG
# -----------------------------------------------------------------------------
def build_svg(size_key, variant_key):
    S = SIZES[size_key]
    V = VARIANTS[variant_key]
    n = S["n"]
    full = variant_key == "full"

    band = S["band_full"] if full else S["band"]
    r_in = S["r_body"] + BORE_CLEAR
    r_out = r_in + band
    pad = 4.0
    span = 2 * (r_out + pad)
    cx = cy = r_out + pad

    fs = full_font(S) if full else max(3.2, band * 0.185)
    fs_sub = max(2.4, band * 0.115)
    fs_title = max(2.8, band * 0.13)
    r_tick_o = r_out - 1.2
    r_tick_i = r_out - 3.6

    o = io.StringIO()
    o.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    o.write('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            'width="%.3fmm" height="%.3fmm" viewBox="0 0 %.3f %.3f">\n'
            % (span, span, span, span))
    o.write("  <!-- %s legend collar, %s variant. All labels upright.\n"
            "       bore %.2f dia (body %.2f + %.2f), outside %.2f dia.\n"
            "       RED = cut through, BLACK = engrave. -->\n"
            % (S["label"], variant_key, r_in * 2, S["r_body"] * 2,
               BORE_CLEAR, r_out * 2))

    # ---- CUT ----
    o.write('  <g id="CUT" inkscape:label="CUT" inkscape:groupmode="layer" '
            'fill="none" stroke="%s" stroke-width="%.2f">\n'
            % (CUT_COLOUR, CUT_WIDTH))
    o.write('    <circle cx="%.3f" cy="%.3f" r="%.3f"/>\n' % (cx, cy, r_out))
    o.write('    <circle cx="%.3f" cy="%.3f" r="%.3f"/>\n' % (cx, cy, r_in))
    o.write("  </g>\n\n")

    # ---- ENGRAVE ----
    o.write('  <g id="ENGRAVE" inkscape:label="ENGRAVE" '
            'inkscape:groupmode="layer" fill="%s" stroke="none" '
            'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" '
            'text-anchor="middle" dominant-baseline="central">\n' % ENGRAVE_COLOUR)

    for i in range(n):
        f = i / float(n)
        x0, y0 = polar_svg(cx, cy, r_tick_i, f)
        x1, y1 = polar_svg(cx, cy, r_tick_o, f)
        major = (i % max(1, n // 12) == 0)
        o.write('    <line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                'stroke="%s" stroke-width="%.2f"/>\n'
                % (x0, y0, x1, y1, ENGRAVE_COLOUR, 0.55 if major else 0.25))

    if full:
        # Two text rings, alternating, so neighbours never sit side by side.
        r_a = r_out - fs * 1.5
        r_b = r_out - fs * 3.6
        for i, (frac, name, real) in enumerate(slots_for(size_key)):
            r = fit_radius(r_a if i % 2 == 0 else r_b, frac,
                           est_width(name, fs), fs, r_in, r_out)
            x, y = polar_svg(cx, cy, r, frac)
            # A driven pixel is bold, a suggestion is light, so you can see at
            # a glance which names mean something. No marker dot: at this text
            # size it lands on top of the word it is meant to mark.
            o.write('    <text x="%.3f" y="%.3f" font-size="%.2f"%s>%s</text>\n'
                    % (x, y, fs,
                       ' font-weight="700"' if real else ' opacity="0.7"',
                       _esc(name)))

    elif variant_key == "hours":
        for h in range(1, 13):
            r = fit_radius(r_in + band * 0.55, h / 12.0,
                           est_width(str(h), fs * 1.3), fs * 1.3, r_in, r_out)
            x, y = polar_svg(cx, cy, r, h / 12.0)
            o.write('    <text x="%.3f" y="%.3f" font-size="%.2f" '
                    'font-weight="600">%d</text>\n' % (x, y, fs * 1.3, h))

    elif V["items"]:
        for frac, lab, col, sub in V["items"]:
            r = fit_radius(r_in + band * 0.62, frac,
                           est_width(lab, fs), fs, r_in, r_out)
            x, y = polar_svg(cx, cy, r, frac)
            o.write('    <!-- lit colour %s -->\n' % col)
            o.write('    <text x="%.3f" y="%.3f" font-size="%.2f" '
                    'font-weight="700">%s</text>\n' % (x, y, fs, _esc(lab)))
            if sub:
                rs = fit_radius(r - fs * 1.6, frac,
                                est_width(sub, fs_sub), fs_sub, r_in, r_out)
                xs, ys = polar_svg(cx, cy, rs, frac)
                o.write('    <text x="%.3f" y="%.3f" font-size="%.2f">%s</text>\n'
                        % (xs, ys, fs_sub, _esc(sub)))

    if variant_key != "blank":
        o.write('    <text x="%.3f" y="%.3f" font-size="%.2f" opacity="0.6">'
                '%s</text>\n' % (cx, cy - r_in - band * 0.14, fs_title,
                                 _esc(V["title"])))

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
    full = variant_key == "full"
    band = S["band_full"] if full else S["band"]
    r_in = S["r_body"] + BORE_CLEAR
    r_out = r_in + band
    fs = full_font(S) if full else max(3.2, band * 0.185)
    fs_sub = max(2.4, band * 0.115)

    o = io.StringIO()
    o.write("// %s legend collar - %s\n" % (S["label"], V["title"]))
    o.write("// Generated by build_legend.py. Edit that, not this.\n//\n")
    o.write("// Every label is UPRIGHT - no rotation - so the collar reads\n")
    o.write("// from across the room whichever pixel you are looking at.\n//\n")
    o.write("// Text is RAISED by TEXT_H. For a two-colour print, pause at\n")
    o.write("// PLATE_H and swap filament: the text starts exactly there.\n//\n")
    o.write("// Bore is body dia %.2f + %.2f clearance.\n"
            % (S["r_body"] * 2, BORE_CLEAR))
    o.write("$fn = 160;\n")
    o.write("PLATE_H = 2.4;\nTEXT_H = 0.6;\nTICK_H = 0.4;\n")
    o.write("R_IN = %.4f;\nR_OUT = %.4f;\n\n" % (r_in, r_out))

    o.write("module plate() {\n  difference() {\n")
    o.write("    cylinder(h = PLATE_H, r = R_OUT);\n")
    o.write("    translate([0, 0, -1]) cylinder(h = PLATE_H + 2, r = R_IN);\n")
    o.write("  }\n}\n\n")

    o.write("// Upright: translate only, never rotate.\n")
    o.write("module lab(x, y, size, txt, bold = true) {\n")
    o.write("  translate([x, y, PLATE_H])\n")
    o.write("    linear_extrude(height = TEXT_H)\n")
    o.write("      text(txt, size = size, halign = \"center\",\n")
    o.write("           valign = \"center\", font = bold ?\n")
    o.write("           \"DejaVu Sans:style=Bold\" : \"DejaVu Sans\");\n}\n\n")

    o.write("module ticks() {\n  for (i = [0 : %d]) {\n" % (n - 1))
    o.write("    a = i * %.6f;\n" % (360.0 / n))
    o.write("    major = (i %% %d) == 0;\n" % max(1, n // 12))
    o.write("    rotate([0, 0, -a])\n")
    o.write("      translate([-(major ? 0.45 : 0.18), R_OUT - 3.6, PLATE_H])\n")
    o.write("        cube([major ? 0.9 : 0.36, 2.4, TICK_H]);\n")
    o.write("  }\n}\n\n")

    o.write("module legend() {\n  plate();\n  ticks();\n")
    if full:
        r_a, r_b = r_out - fs * 1.5, r_out - fs * 3.6
        for i, (frac, name, real) in enumerate(slots_for(size_key)):
            r = fit_radius(r_a if i % 2 == 0 else r_b, frac,
                           est_width(name, fs), fs, r_in, r_out)
            x, y = polar_scad(r, frac)
            o.write('  lab(%.3f, %.3f, %.2f, "%s", %s);%s\n'
                    % (x, y, fs, name, "true" if real else "false",
                       "   // driven by the firmware" if real else ""))
    elif variant_key == "hours":
        for h in range(1, 13):
            r = fit_radius(r_in + band * 0.55, h / 12.0,
                           est_width(str(h), fs * 1.3), fs * 1.3, r_in, r_out)
            x, y = polar_scad(r, h / 12.0)
            o.write('  lab(%.3f, %.3f, %.2f, "%d");\n' % (x, y, fs * 1.3, h))
    elif V["items"]:
        for frac, lab_, col, sub in V["items"]:
            r = fit_radius(r_in + band * 0.62, frac,
                           est_width(lab_, fs), fs, r_in, r_out)
            x, y = polar_scad(r, frac)
            o.write('  // lit colour %s\n' % col)
            o.write('  lab(%.3f, %.3f, %.2f, "%s");\n' % (x, y, fs, lab_))
            if sub:
                rs = fit_radius(r - fs * 1.6, frac,
                                est_width(sub, fs_sub), fs_sub, r_in, r_out)
                xs, ys = polar_scad(rs, frac)
                o.write('  lab(%.3f, %.3f, %.2f, "%s", false);\n'
                        % (xs, ys, fs_sub, sub))
    o.write("}\n\nlegend();\n")
    return o.getvalue()


# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", choices=sorted(SIZES), action="append")
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="report the tightest label gap on the full variant")
    a = ap.parse_args()

    if a.list:
        print("sizes:")
        for k, v in sorted(SIZES.items()):
            print("  %-4s %-8s body %.2f dia -> collar %.2f dia (full: %.2f)"
                  % (k, v["label"], v["r_body"] * 2,
                     (v["r_body"] + BORE_CLEAR + v["band"]) * 2,
                     (v["r_body"] + BORE_CLEAR + v["band_full"]) * 2))
        print("variants:")
        for k, v in sorted(VARIANTS.items()):
            print("  %-9s %-20s %s" % (k, v["title"], v["note"]))
        return

    if a.check:
        for k in sorted(SIZES):
            gap, fs = check_spacing(k)
            n = SIZES[k]["n"]
            verdict = "OK" if gap > 0.8 else ("TIGHT" if gap > 0 else "OVERLAP")
            print("%-4s %2d labels at %.2f mm -> tightest gap %+.2f mm  %s"
                  % (k, n, fs, gap, verdict))
        return

    sizes = a.size or sorted(SIZES)
    variants = a.variant or sorted(VARIANTS)
    made = 0
    for s in sizes:
        for v in variants:
            for ext, fn in (("svg", build_svg), ("scad", build_scad)):
                p = os.path.join(a.out, "legend-%s-%s.%s" % (s, v, ext))
                io.open(p, "w", encoding="utf-8", newline="\n").write(fn(s, v))
                made += 1
        gap, fs = check_spacing(s)
        print("%-4s full: %d names, %.2f mm text, tightest gap %+.2f mm"
              % (s, SIZES[s]["n"], fs, gap))
    print("%d files in %s" % (made, a.out))


if __name__ == "__main__":
    main()
