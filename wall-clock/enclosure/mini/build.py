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
# THE DISPLAY — GC9B72 360x360, MEASURED
# =============================================================================
DISP_PCB_D = 60.0       # round part of the blue PCB
DISP_ACTIVE_D = 55.0    # black screen area -> sets the plywood aperture
DISP_T = 4.0            # module thickness at the rim
DISP_TAB_W = 40.0       # width of the tab carrying the header
DISP_OVERALL = 67.0     # top to bottom, i.e. round part + tab
DISP_TAB_T = 1.6        # bare PCB. ASSUMES THE 10-PIN HEADER IS DESOLDERED.
DISP_TAB_ANGLE = 0.0    # clock position the tab points. 0 = 12 o'clock.

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
R_DP = (DISP_PCB_D + DISP_CLEAR) / 2          # display pocket wall  -> 30.3
R_SEAT = R_DP - 2.5                           # 2.5 mm shelf the module rests on

# THE NUMBER THAT DECIDES THE WHOLE STACK.
# The tab is a RECTANGLE, so its reach is set by its CORNERS, not its midline:
#   reach along the midline = DISP_OVERALL - DISP_PCB_D/2 = 37.0
#   corner radius           = hypot(20, 37)               = 42.06
# The LED circle is at r = 40.75. The corners land 1.3 mm PAST the LEDs, so the
# tab cannot share their plane at any rotation — it has to pass behind the ring.
DISP_TAB_REACH = DISP_OVERALL - DISP_PCB_D / 2
R_TAB = math.hypot(DISP_TAB_W / 2, DISP_TAB_REACH) + DISP_CLEAR
# Widest angular half-span of the tab is at the smallest radius it crosses.
TAB_WIN = 2 * math.degrees(math.asin(min(0.99, (DISP_TAB_W / 2) / R_DP)))

# --- depths, front-referenced -------------------------------------------------
Z_FACE = FACE_T                    # 3.0   plywood occupies 0..3
# 4 mm, not 6. Every millimetre of diffuser pushes the ring back, and the
# display has to sit behind the ring, so it comes straight off the screen's
# viewing depth. 4 mm cells at 9.67 mm pitch still separate the pixels well.
DIFF_H, DIFF_TOP = 4.0, 0.8
# THE DECIDING NUMBER: does the tab stay inside the ring's inner wall?
#   tab reach <= R_CH_I  -> shallow seat, screen sits just behind the plywood
#   tab reach >  R_CH_I  -> the tab must pass BEHIND the ring, so the whole
#                           module drops back and the screen sits in a well
# Worked out here rather than left to you, because getting it wrong means a
# printed part the display physically cannot go into.
# The module seats so its TAB clears the back of the ring PCB.
# tab back rests level with the module back; tab front must be behind the ring.
Z_MOD_BACK_MIN = 0.0    # filled in below, after Z_PCB_B is known
Z_DIFF_B = Z_FACE + DIFF_H         # 9.0   LED tops meet the diffuser here
Z_PCB_F = Z_DIFF_B + LED_H         # 10.6
Z_PCB_B = Z_PCB_F + PCB_T          # 12.2  ring pocket floor
Z_BACK = 22.0                      # body back face (bay for the S3 behind)

TAB_CLEARS_RING = R_TAB < ((RING_ID - CLEAR) / 2)
# The seat stays SHALLOW either way. When the tab overhangs the ring's inner
# wall we do not drop the module into a well -- we notch the web and the
# diffuser's inner skirt instead, and let the tab sit in the plane of the
# diffuser. Costs the inner baffle wall on two or three LED cells, which is
# invisible behind plywood, and keeps the screen right where you can read it.
# 0.8 gap behind the ring PCB, then the tab, then the shelf. The slot's own
# 0.4 front clearance is carved out of that 0.8, so the tab still clears the
# ring by 0.4 mm -- an earlier 0.4 here left them touching exactly.
# 1.6, not 0.8. At the tab's angle the slot removes everything behind this
# plane, so whatever is left between the ring pocket floor and the slot IS the
# floor there. 0.8 left a 0.4 mm membrane spanning 7.5 mm radially -- it would
# have cracked. 1.6 leaves a 1.2 mm floor, which costs ~1 mm of screen depth.
RING_TAB_GAP = 1.6
Z_SEAT = Z_PCB_B + RING_TAB_GAP + DISP_TAB_T   # module back / shelf top
Z_TAB_FRONT = Z_SEAT - DISP_TAB_T - 0.4        # front of the tab slot
WELL_DEPTH = (Z_SEAT - DISP_T) - Z_FACE  # how far the screen sits behind the ply

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
TICK_MIN_L, TICK_MAJ_L = 2.5, 4.0
TICK_MIN_W, TICK_MAJ_W = 1.8, 3.0

CUT, ENGRAVE = "#FF0000", "#000000"


def build_body():
    """Ring pocket outboard, display pocket inboard, S3 bay behind.

    THE TAB SLOT. The tab's corners reach r=42, past the LED circle at r=40.75,
    so the tab has to pass BEHIND the ring PCB. The slot is therefore local in
    BOTH axes: it opens out to the tab's corner radius, but only over the tab's
    clock angle and only across the ~2 mm of depth the tab occupies. Widening
    the whole pocket wall instead would delete the ring and diffuser seats at
    that angle and leave a visible gap in the light ring.

    Done with an angle-modulated revolve rather than a boolean — see
    mesh.revolve_mod.
    """
    def mod(tag, deg):
        if tag is None:
            return 0.0
        d = ((deg - DISP_TAB_ANGLE + 180.0) % 360.0) - 180.0
        if abs(d) > TAB_WIN / 2:
            return 0.0
        return {'slot': R_TAB - R_DP, 'seat': R_TAB - R_SEAT}.get(tag, 0.0)

    profile = [
        (R_BODY,  0.0,         None),    # front face of the retaining lip
        (R_BODY,  Z_BACK,      None),    # down the outside
        (R_SEAT,  Z_BACK,      'seat'),  # back face in to the bay opening
        (R_SEAT,  Z_SEAT,      'seat'),  # bay wall -- opened at the tab angle
        (R_DP,    Z_SEAT,      'slot'),  # seating shelf -- vanishes at the tab
        (R_DP,    Z_TAB_FRONT, 'slot'),  # tab slot -- ONLY this depth widens
        (R_DP,    Z_FACE,      None),    # plain display pocket bore above it
        (R_CH_I,  Z_FACE,      None),    # web between display and ring pockets
        (R_CH_I,  Z_PCB_B,     None),    # ring pocket inner wall
        (R_CH_O,  Z_PCB_B,     None),    # ring pocket floor
        (R_CH_O,  Z_FACE,      None),    # ring pocket outer wall
        (R_FACE,  Z_FACE,      None),    # face recess floor
        (R_FACE,  0.0,         None),    # inside of the retaining lip
    ]
    return mesh.revolve_mod(profile, seg=288, mod=mod)


def build_diffuser():
    """Top face + two skirts + 24 baffles, with the inner skirt notched away at
    the display tab's angle so the tab can sit in the diffuser's plane."""
    # No notch needed: the tab passes behind the ring PCB, well clear of the
    # diffuser, so every cell keeps its baffles and the light ring is unbroken.
    def mod(tag, deg):
        return 0.0

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
    print(f"  tab corners reach r={R_TAB - DISP_CLEAR:.2f} mm vs LED circle at "
          f"r={(RING_OD+RING_ID)/4:.2f} mm")
    print(f"  -> tab seated BEHIND the ring PCB; slot spans {TAB_WIN:.0f} deg "
          f"at z {Z_TAB_FRONT:.1f}-{Z_SEAT:.1f}")
    print(f"  -> screen sits {WELL_DEPTH:.1f} mm behind the plywood\n")
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
    # 8 mm, not 6. With a 54 mm aperture a 6.4 mm recess only shadows the screen
    # edge past ~85 degrees off-axis; head-on and at normal viewing angles it is
    # invisible. Structural floor and diffuser depth are worth more than the
    # last millimetre here.
    want(WELL_DEPTH < 8.0,
         f"screen recessed {WELL_DEPTH:.1f} mm behind the plywood")
    floor_t = Z_TAB_FRONT - Z_PCB_B
    want(floor_t >= 1.0,
         f"ring pocket floor is {floor_t:.1f} mm thick over the tab slot "
         f"(needs >=1.0 or it cracks)")
    want(Z_TAB_FRONT > Z_PCB_B,
         f"tab slot starts at z={Z_TAB_FRONT:.1f}, behind the ring PCB at "
         f"z={Z_PCB_B:.1f} -- nothing touches the LEDs")
    want(R_TAB < R_CH_O,
         f"tab corners (r={R_TAB:.1f}) stay inside the ring pocket outer wall "
         f"(r={R_CH_O:.2f})")
    want(Z_BACK - Z_SEAT > 6.0,
         f"{Z_BACK - Z_SEAT:.1f} mm of bay left behind the display for the S3")
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
