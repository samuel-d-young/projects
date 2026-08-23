#!/usr/bin/env python3
"""Generate the mini (24-LED) test clock enclosure: STLs + Glowforge SVG.

    python3 build.py            # writes *.stl and mini-face.svg, validates
    python3 build.py --preview  # also renders mini-face.png

!! MEASURE THE RING FIRST !!
RING_OD/RING_ID below are the standard 24-LED WS2812B ring dimensions (the
Adafruit NeoPixel Ring 24 is 66.0 / 51.0 mm and the generic Mokungi-style
clones follow it). NOT confirmed against a Mokungi datasheet. Put calipers on
yours and correct these two numbers before printing — everything else follows.
"""
import math
import sys
import xml.etree.ElementTree as ET

import mesh

# --- the ring -----------------------------------------------------------------
RING_OD, RING_ID = 66.0, 51.0     # <-- MEASURE AND CORRECT
PCB_T, LED_H = 1.6, 1.6
NUM_LEDS = 24

# --- fits ---------------------------------------------------------------------
CLEAR = 0.75                      # total radial slop around the PCB
FACE_T = 3.0                      # plywood thickness — measure your sheet

# --- derived radii ------------------------------------------------------------
R_CH_O = (RING_OD + CLEAR) / 2     # 33.375  pocket outer
R_CH_I = (RING_ID - CLEAR) / 2     # 25.125  pocket inner
R_BODY = R_CH_O + 6.625            # 40.0    body outer  -> 80 mm OD
R_FACE = 38.0                      # face disc radius -> 76 mm, sits in a recess
R_LIP = R_BODY                     # 2 mm proud lip retains the face

# --- depths, front-referenced -------------------------------------------------
Z_FACE = FACE_T                    # 3.0   face occupies 0..3
DIFF_H, DIFF_TOP = 6.0, 0.8
Z_DIFF_BACK = Z_FACE + DIFF_H      # 9.0   LED tops meet the diffuser here
Z_PCB_F = Z_DIFF_BACK + LED_H      # 10.6
Z_PCB_B = Z_PCB_F + PCB_T          # 12.2  pocket floor
Z_BACK = 19.0                      # body back face

# --- diffuser radii -----------------------------------------------------------
R_D_O, R_D_I = RING_OD / 2, RING_ID / 2          # 33.0, 25.5
DIFF_WALL = 1.0
SKIRT = 1.2


def build_body():
    """Dish holding the ring, with a recess the plywood face drops into.

    Centre is open all the way through: the ring's wires route inward and the
    back cover plugs in behind. No screws — see README for why the mini uses a
    friction fit where the 60-LED build uses posts.
    """
    prof = [
        (R_BODY,  0.0),        # front outer edge of the retaining lip
        (R_BODY,  Z_BACK),     # down the outside
        (R_CH_I,  Z_BACK),     # across the back to the central opening
        (R_CH_I,  Z_PCB_B),    # up the central opening to the pocket floor
        (R_CH_O,  Z_PCB_B),    # across the pocket floor (the ring rests here)
        (R_CH_O,  Z_FACE),     # up the pocket wall to the face recess
        (R_FACE,  Z_FACE),     # out across the face recess floor
        (R_FACE,  0.0),        # up the inside of the retaining lip
    ]
    return mesh.revolve(prof, seg=180)


def build_diffuser():
    """24-cell light guide. Top annulus + two skirts + radial baffles."""
    prof = [
        (R_D_I, 0.0), (R_D_O, 0.0),                    # the glowing face
        (R_D_O, DIFF_H), (R_D_O - SKIRT, DIFF_H),      # outer skirt
        (R_D_O - SKIRT, DIFF_TOP),
        (R_D_I + SKIRT, DIFF_TOP),
        (R_D_I + SKIRT, DIFF_H), (R_D_I, DIFF_H),      # inner skirt
    ]
    tris = mesh.revolve(prof, seg=180)
    # One baffle per pixel boundary, offset half a cell so each wall sits
    # BETWEEN two LEDs rather than on top of one.
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
    """Cup that plugs into the body's central opening and hides the D1 mini.

    16 mm central hole so a USB cable reaches the board without removing it.
    """
    r_out = R_CH_I - 0.15          # slip fit into the body's central opening
    return mesh.revolve([
        (8.0, 0.0), (r_out, 0.0), (r_out, 8.0),
        (r_out - 2.0, 8.0), (r_out - 2.0, 2.0), (8.0, 2.0),
    ], seg=180)


# --- Glowforge face -----------------------------------------------------------
CUT, ENGRAVE = "#FF0000", "#000000"
W_OD, W_ID = 67.0, 50.0            # window shows the diffuser
SPOKES, SPOKE_W = 4, 5.0
TICK_R = W_ID / 2 - 2.0            # ticks run inward from just inside the window
TICK_MIN_L, TICK_MAJ_L = 3.5, 6.0
TICK_MIN_W, TICK_MAJ_W = 1.6, 2.8


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
    ET.SubElement(svg, "title").text = "Mini test clock face - 3mm plywood"
    g = ET.SubElement(svg, "g", {"transform": f"translate({c},{c})"})
    for h in range(12):
        major = h % 3 == 0
        ln = TICK_MAJ_L if major else TICK_MIN_L
        w = TICK_MAJ_W if major else TICK_MIN_W
        ET.SubElement(g, "path", {"d": tick(h * 30.0, TICK_R - ln, TICK_R, w),
                                  "fill": ENGRAVE, "data-layer": "engrave-ticks"})
    step = 360.0 / SPOKES
    for k in range(SPOKES):
        a0 = 45.0 + k * step
        ET.SubElement(g, "path", {
            "d": arc_path(W_OD / 2, W_ID / 2, a0, a0 + step, SPOKE_W / 2),
            "fill": "none", "stroke": CUT, "stroke-width": "0.1",
            "data-layer": "cut-window"})
    ET.SubElement(g, "circle", {"cx": "0", "cy": "0", "r": f"{R_FACE:.4f}",
                                "fill": "none", "stroke": CUT,
                                "stroke-width": "0.1", "data-layer": "cut-outline"})
    return svg, size


def main():
    parts = [("mini-body.stl", build_body(), "body"),
             ("mini-diffuser.stl", build_diffuser(), "diffuser"),
             ("mini-backcover.stl", build_backcover(), "back cover")]
    print("STL parts:")
    fails = []
    for fn, tris, name in parts:
        n = mesh.write_stl(fn, tris, name)
        v = mesh.signed_volume(tris)
        (x0, x1), (y0, y1), (z0, z1) = mesh.bounds(tris)
        ok = v > 0
        if not ok:
            fails.append(fn)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {fn:<22} {n:>6} tris  "
              f"vol {v/1000:7.2f} cm3  bbox {x1-x0:5.1f} x {y1-y0:5.1f} x {z1-z0:5.1f} mm")

    svg, size = build_face_svg()
    ET.ElementTree(svg).write("mini-face.svg", encoding="unicode", xml_declaration=True)
    print(f"\nLaser: mini-face.svg  {size:.0f} x {size:.0f} mm")

    print("\nFit checks:")
    def want(ok, msg):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)
    want(R_CH_O * 2 > RING_OD and R_CH_I * 2 < RING_ID,
         f"ring {RING_OD}/{RING_ID} drops into pocket {R_CH_O*2:.2f}/{R_CH_I*2:.2f}")
    want(W_OD / 2 > R_D_O - 1 and W_ID / 2 < R_D_I + 1,
         f"face window {W_ID}-{W_OD} exposes diffuser {R_D_I*2}-{R_D_O*2}")
    want(R_FACE < R_BODY, f"face {R_FACE*2:.0f}mm sits inside the {R_BODY*2:.0f}mm body lip")
    want(TICK_R < W_ID / 2, "ticks sit on the centre disc, clear of the window")
    want(TICK_R - TICK_MAJ_L > 8, "ticks stop short of the middle")
    cell = math.pi * (R_D_O + R_D_I) / NUM_LEDS - DIFF_WALL
    want(cell > 3.0, f"diffuser cell {cell:.2f} mm wide")
    want(R_BODY * 2 <= 256 and size <= 305, "fits the P1S bed and the Aura")

    if "--preview" in sys.argv:
        try:
            import cairosvg
            cairosvg.svg2png(url="mini-face.svg", write_to="mini-face.png",
                             output_width=700, output_height=700,
                             background_color="#f5efe3")
            print("\nWrote mini-face.png")
        except ImportError:
            print("\n(cairosvg missing, no preview)")

    print(f"\n{'FAILURES: ' + str(fails) if fails else 'All checks passed.'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
