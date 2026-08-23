#!/usr/bin/env python3
"""Round clock enclosure — 24-LED ring + 360x360 round display in the centre.

    python3 build.py            # writes *.stl + face.svg, validates geometry
    python3 build.py --preview  # also renders face.png

Everything derives from the four measured numbers at the top. Change them,
re-run, re-slice. Nothing downstream is hardcoded.
"""
import math
import sys
import xml.etree.ElementTree as ET

import mesh

# =============================================================================
# MEASURED — the Mokungi 24-LED WS2812B ring
# =============================================================================
RING_OD, RING_ID = 92.0, 71.0      # confirmed by Sam
PCB_T, LED_H = 1.6, 1.6
NUM_LEDS = 24

# =============================================================================
# THE DISPLAY — GC9B72 360x360 round module
# =============================================================================
# From the photos: a round PCB with a RECTANGULAR TAB carrying a 10-pin header
# (TE SDO BL CS DC RST SDA SCL VCC GND). The tab is why the module is not a
# circle, and it is the whole reason for the notch below.
#
# !! ALL FIVE OF THESE ARE ESTIMATES FROM PHOTOS. MEASURE BEFORE PRINTING. !!
DISP_PCB_D = 60.0       # diameter of the ROUND part of the blue PCB
DISP_ACTIVE_D = 53.0    # black screen area -> sets the plywood aperture
DISP_T = 4.0            # glass to back of PCB, at the RIM (not the connectors)
DISP_TAB_REACH = 36.0   # centre of module -> outer edge of the tab
DISP_TAB_W = 24.0       # width of the tab
DISP_TAB_ANGLE = 0.0    # clock position the tab points. 0 = 12 o'clock.
                        # Pick whatever keeps it clear of the ring's connector.
DISP_TAB_T = 1.6        # thickness of the tab.
# 1.6 assumes you DESOLDER the 10-pin header and solder wires flat to the pads.
# Do that. Left on, the header adds ~9 mm behind the tab, which forces the whole
# module 9+ mm back into a well you cannot read. Same goes for the ring's 4-pin
# header. Two connectors removed is the difference between a clean build and a
# shadowed one.

# --- fits ---------------------------------------------------------------------
CLEAR = 0.75                       # radial slop around the LED PCB
DISP_CLEAR = 0.6                   # radial slop around the display module
FACE_T = 3.0                       # plywood — measure your sheet
RIM = 7.625                        # body material outside the ring

# --- derived radii ------------------------------------------------------------
R_CH_O = (RING_OD + CLEAR) / 2     # 46.375  ring pocket outer
R_CH_I = (RING_ID - CLEAR) / 2     # 35.125  ring pocket inner
R_BODY = R_CH_O + RIM              # 54.000  -> 108 mm OD
R_FACE = R_BODY - 2.0              # 52.000  -> 104 mm face, 2 mm proud lip
R_DP = (DISP_PCB_D + DISP_CLEAR) / 2          # display pocket wall
R_SEAT = R_DP - 2.5                           # 2.5 mm shelf the module rests on
R_TAB = DISP_TAB_REACH + DISP_CLEAR           # how far the notch must reach
TAB_WIN = 2 * math.degrees(math.asin(min(0.99, (DISP_TAB_W / 2) / max(R_DP, 1))))

# --- depths, front-referenced -------------------------------------------------
Z_FACE = FACE_T                    # 3.0   plywood occupies 0..3
DIFF_H, DIFF_TOP = 6.0, 0.8
# THE DECIDING NUMBER: does the tab stay inside the ring's inner wall?
#   tab reach <= R_CH_I  -> shallow seat, screen sits just behind the plywood
#   tab reach >  R_CH_I  -> the tab must pass BEHIND the ring, so the whole
#                           module drops back and the screen sits in a well
# Worked out here rather than left to you, because getting it wrong means a
# printed part the display physically cannot go into.
Z_SEAT_SHALLOW = Z_FACE + DISP_T
Z_DIFF_B = Z_FACE + DIFF_H         # 9.0   LED tops meet the diffuser here
Z_PCB_F = Z_DIFF_B + LED_H         # 10.6
Z_PCB_B = Z_PCB_F + PCB_T          # 12.2  ring pocket floor
Z_BACK = 22.0                      # body back face (bay for the S3 behind)

TAB_CLEARS_RING = (DISP_TAB_REACH + DISP_CLEAR) < ((RING_ID - CLEAR) / 2)
# The seat stays SHALLOW either way. When the tab overhangs the ring's inner
# wall we do not drop the module into a well -- we notch the web and the
# diffuser's inner skirt instead, and let the tab sit in the plane of the
# diffuser. Costs the inner baffle wall on two or three LED cells, which is
# invisible behind plywood, and keeps the screen right where you can read it.
Z_SEAT = Z_SEAT_SHALLOW
WELL_DEPTH = Z_SEAT - DISP_T - Z_FACE

# --- diffuser -----------------------------------------------------------------
R_D_O, R_D_I = RING_OD / 2, RING_ID / 2
DIFF_WALL, SKIRT = 1.0, 1.2

# --- face ---------------------------------------------------------------------
W_OD, W_ID = RING_OD + 1.0, RING_ID - 1.0     # window over the ring
APERTURE_D = DISP_ACTIVE_D - 1.0              # window over the display,
# 1 mm INSIDE the active area on purpose: the plywood then hides the tab and
# the PCB's ragged edge, and all you see is a perfect circle of screen.
SPOKES, SPOKE_W = 4, 5.0
TICK_R = W_ID / 2 - 2.0                       # ticks run inward from here
TICK_MIN_L, TICK_MAJ_L = 3.0, 5.0
TICK_MIN_W, TICK_MAJ_W = 1.8, 3.0

CUT, ENGRAVE = "#FF0000", "#000000"


def build_body():
    """Ring pocket outboard, display pocket inboard, S3 bay behind.

    THE NOTCH: the display's tab sticks out past the round PCB, so a plain
    circular pocket cannot take it. At the tab's clock position the pocket wall
    and the seating shelf are both pushed out to the tab's reach, which deletes
    the shelf locally and lets the tab (and the header soldered to its back)
    drop straight through into the bay. Everywhere else the shelf is intact and
    carries the module.

    Done with an angle-modulated revolve rather than a boolean, because there
    is no CSG here — see mesh.revolve_mod.
    """
    def mod(tag, deg):
        if tag is None:
            return 0.0
        d = ((deg - DISP_TAB_ANGLE + 180.0) % 360.0) - 180.0
        if abs(d) > TAB_WIN / 2:
            return 0.0
        return {'wall': R_TAB - R_DP,
                'seat': R_TAB - R_SEAT,
                'web': max(0.0, R_TAB - R_CH_I)}.get(tag, 0.0)

    profile = [
        (R_BODY,  0.0,      None),     # front face of the retaining lip
        (R_BODY,  Z_BACK,   None),     # down the outside
        (R_SEAT,  Z_BACK,   'seat'),   # across the back to the bay opening
        (R_SEAT,  Z_SEAT,   'seat'),   # up the bay wall  -- notched at the tab
        (R_DP,    Z_SEAT,   'wall'),   # the seating shelf -- vanishes at the tab
        (R_DP,    Z_FACE,   'wall'),   # display pocket wall -- widens at the tab
        (R_CH_I,  Z_FACE,   'web'),    # web between display and ring pockets --
        (R_CH_I,  Z_PCB_B,  'web'),    #   opened at the tab angle if it overhangs
        (R_CH_O,  Z_PCB_B,  None),     # ring pocket floor
        (R_CH_O,  Z_FACE,   None),     # ring pocket outer wall
        (R_FACE,  Z_FACE,   None),     # face recess floor
        (R_FACE,  0.0,      None),     # inside of the retaining lip
    ]
    return mesh.revolve_mod(profile, seg=240, mod=mod)


def build_diffuser():
    """Top face + two skirts + 24 baffles, with the inner skirt notched away at
    the display tab's angle so the tab can sit in the diffuser's plane."""
    overhang = max(0.0, R_TAB - R_D_I)

    def mod(tag, deg):
        if tag != 'skirt' or overhang <= 0:
            return 0.0
        d = ((deg - DISP_TAB_ANGLE + 180.0) % 360.0) - 180.0
        return overhang if abs(d) <= TAB_WIN / 2 else 0.0

    tris = mesh.revolve_mod([
        (R_D_I, 0.0, None), (R_D_O, 0.0, None),       # the glowing face stays whole
        (R_D_O, DIFF_H, None), (R_D_O - SKIRT, DIFF_H, None),
        (R_D_O - SKIRT, DIFF_TOP, None),
        (R_D_I + SKIRT, DIFF_TOP, 'skirt'),
        (R_D_I + SKIRT, DIFF_H, 'skirt'),
        (R_D_I, DIFF_H, 'skirt'),
    ], seg=240, mod=mod)
    step = 360.0 / NUM_LEDS
    rmid = (R_D_O + R_D_I) / 2
    for i in range(NUM_LEDS):
        a = math.radians(i * step + step / 2)
        tris += mesh.box(rmid * math.cos(a), rmid * math.sin(a),
                         DIFF_TOP + (DIFF_H - DIFF_TOP) / 2,
                         R_D_O - R_D_I, DIFF_WALL, DIFF_H - DIFF_TOP,
                         math.degrees(a))
    return tris


def build_backcover():
    """Closes the S3 bay. 20 mm hole so the USB-C lead reaches the board."""
    r_out = R_SEAT - 0.15
    return mesh.revolve([
        (10.0, 0.0), (r_out, 0.0), (r_out, 9.0),
        (r_out - 2.0, 9.0), (r_out - 2.0, 2.0), (10.0, 2.0),
    ], seg=200)


# --- Glowforge face -----------------------------------------------------------
def polar(r, deg):
    a = math.radians(deg - 90.0)
    return r * math.cos(a), r * math.sin(a)


def arc_path(ro, ri, a0, a1, hw):
    do, di = math.degrees(math.asin(hw / ro)), math.degrees(math.asin(hw / ri))
    x1, y1 = polar(ro, a0 + do)
    x2, y2 = polar(ro, a1 - do)
    x3, y3 = polar(ri, a1 - di)
    x4, y4 = polar(ri, a0 + di)
    lg = 1 if (a1 - a0) > 180 else 0
    return (f"M {x1:.4f} {y1:.4f} A {ro:.4f} {ro:.4f} 0 {lg} 1 {x2:.4f} {y2:.4f} "
            f"L {x3:.4f} {y3:.4f} A {ri:.4f} {ri:.4f} 0 {lg} 0 {x4:.4f} {y4:.4f} Z")


def tick(deg, r0, r1, w):
    pts = []
    for r, sgn in ((r0, +1), (r1, +1), (r1, -1), (r0, -1)):
        pts.append(polar(r, deg + math.degrees(math.asin((w / 2) / r)) * sgn))
    return ("M {:.4f} {:.4f} L {:.4f} {:.4f} L {:.4f} {:.4f} L {:.4f} {:.4f} Z"
            .format(*[c for p in pts for c in p]))


def build_face_svg():
    size = R_FACE * 2 + 8
    c = size / 2
    svg = ET.Element("svg", {"xmlns": "http://www.w3.org/2000/svg",
                             "width": f"{size}mm", "height": f"{size}mm",
                             "viewBox": f"0 0 {size} {size}", "version": "1.1"})
    ET.SubElement(svg, "title").text = "Round clock face - 3mm plywood"
    g = ET.SubElement(svg, "g", {"transform": f"translate({c},{c})"})
    # ENGRAVE: hour ticks, on the band between the display and the ring
    for h in range(12):
        major = h % 3 == 0
        ln = TICK_MAJ_L if major else TICK_MIN_L
        w = TICK_MAJ_W if major else TICK_MIN_W
        ET.SubElement(g, "path", {"d": tick(h * 30.0, TICK_R - ln, TICK_R, w),
                                  "fill": ENGRAVE, "data-layer": "engrave-ticks"})
    # CUT: display aperture
    ET.SubElement(g, "circle", {"cx": "0", "cy": "0", "r": f"{APERTURE_D/2:.4f}",
                                "fill": "none", "stroke": CUT, "stroke-width": "0.1",
                                "data-layer": "cut-aperture"})
    # CUT: ring window, split by spokes
    step = 360.0 / SPOKES
    for k in range(SPOKES):
        a0 = 45.0 + k * step
        ET.SubElement(g, "path", {
            "d": arc_path(W_OD / 2, W_ID / 2, a0, a0 + step, SPOKE_W / 2),
            "fill": "none", "stroke": CUT, "stroke-width": "0.1",
            "data-layer": "cut-window"})
    # CUT: outline last
    ET.SubElement(g, "circle", {"cx": "0", "cy": "0", "r": f"{R_FACE:.4f}",
                                "fill": "none", "stroke": CUT, "stroke-width": "0.1",
                                "data-layer": "cut-outline"})
    return svg, size


def main():
    fails = []

    def want(ok, msg):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    print(f"Ring {RING_OD} / {RING_ID} mm, {NUM_LEDS} LEDs, "
          f"pitch {math.pi*(RING_OD+RING_ID)/2/NUM_LEDS:.2f} mm")
    print(f"Display: round PCB {DISP_PCB_D} mm, active {DISP_ACTIVE_D} mm, "
          f"tab reaches r={DISP_TAB_REACH} mm at {DISP_TAB_ANGLE:.0f} deg")
    if TAB_CLEARS_RING:
        print(f"  -> tab stays inside the ring. Notch in the body only.\n")
    else:
        print(f"  -> tab overhangs the ring's inner wall by "
              f"{R_TAB - (RING_ID-CLEAR)/2:.1f} mm, so the diffuser's inner skirt is")
        print(f"     notched too. Screen stays {WELL_DEPTH:.1f} mm behind the plywood.\n")
    print("STL parts:")
    for fn, tris, nm in (("body.stl", build_body(), "body"),
                         ("diffuser.stl", build_diffuser(), "diffuser"),
                         ("backcover.stl", build_backcover(), "backcover")):
        n = mesh.write_stl(fn, tris, nm)
        v = mesh.signed_volume(tris)
        (x0, x1), _, (z0, z1) = mesh.bounds(tris)
        ok = v > 0
        if not ok:
            fails.append(fn)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {fn:<16} {n:>6} tris  "
              f"vol {v/1000:7.2f} cm3  {x1-x0:6.1f} dia x {z1-z0:5.1f} deep")

    svg, size = build_face_svg()
    ET.ElementTree(svg).write("face.svg", encoding="unicode", xml_declaration=True)
    print(f"\nLaser: face.svg  {size:.0f} x {size:.0f} mm\n")

    print("Fit checks:")
    want(R_CH_O * 2 > RING_OD and R_CH_I * 2 < RING_ID,
         f"ring drops into pocket {R_CH_O*2:.2f} / {R_CH_I*2:.2f}")
    want(DISP_PCB_D < RING_ID - 4,
         f"round PCB {DISP_PCB_D} mm fits the {RING_ID} mm centre "
         f"({(RING_ID-DISP_PCB_D)/2:.1f} mm each side)")
    want(R_DP < R_CH_I - 2, "display pocket clears the ring pocket wall")
    want(WELL_DEPTH < 6.0,
         f"screen recessed only {WELL_DEPTH:.1f} mm behind the plywood")
    want(DISP_TAB_T < DIFF_H - DIFF_TOP - 0.5,
         f"tab {DISP_TAB_T} mm thick fits the {DIFF_H-DIFF_TOP:.1f} mm notch "
         f"(desolder the header, or this fails)")
    want(R_SEAT > 10, f"S3 bay opening {R_SEAT*2:.0f} mm across")
    want(TAB_WIN < 120, f"tab notch spans {TAB_WIN:.0f} deg of the shelf")
    want(TICK_R - TICK_MAJ_L > APERTURE_D / 2 + 1,
         f"ticks (in to r={TICK_R-TICK_MAJ_L:.1f}) clear the "
         f"{APERTURE_D:.0f} mm aperture (r={APERTURE_D/2:.1f})")
    want(TICK_R < W_ID / 2, "ticks sit inside the ring window")
    cell = math.pi * (R_D_O + R_D_I) / NUM_LEDS - DIFF_WALL
    want(cell > 3.0, f"diffuser cell {cell:.2f} mm wide")
    want(Z_SEAT < Z_BACK - 2, "display seat leaves room for the S3 bay behind it")
    want(R_BODY * 2 <= 256, f"body {R_BODY*2:.0f} mm on the 256 mm bed")
    want(size <= 305, f"face sheet {size:.0f} mm on the 305 mm Aura")

    if "--preview" in sys.argv:
        try:
            import cairosvg
            cairosvg.svg2png(url="face.svg", write_to="face.png",
                             output_width=800, output_height=800,
                             background_color="#f5efe3")
            print("\nWrote face.png")
        except ImportError:
            pass

    print(f"\n{'FAILURES: ' + str(fails) if fails else 'All checks passed.'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
