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
# THE DISPLAY — !! MEASURE YOURS, these are typical 1.85" values !!
# =============================================================================
# A 1.85" round panel is ~47 mm active. Module outline and thickness vary by
# vendor, and thickness especially depends on the FPC connector and whether a
# touch controller is fitted. Put calipers on it before printing the body.
DISP_MODULE_D = 48.0               # module outline diameter  (unverified)
DISP_ACTIVE_D = 47.0               # glass active area -> face aperture
DISP_T = 5.0                       # module thickness incl. components (unverified)

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
R_DP = (DISP_MODULE_D + DISP_CLEAR) / 2       # display pocket radius
R_DL = R_DP - 2.0                             # ledge the display rests on

# --- depths, front-referenced -------------------------------------------------
Z_FACE = FACE_T                    # 3.0   plywood occupies 0..3
DIFF_H, DIFF_TOP = 6.0, 0.8
Z_DISP_B = Z_FACE + DISP_T         # 8.0   back of the display pocket
Z_DIFF_B = Z_FACE + DIFF_H         # 9.0   LED tops meet the diffuser here
Z_PCB_F = Z_DIFF_B + LED_H         # 10.6
Z_PCB_B = Z_PCB_F + PCB_T          # 12.2  ring pocket floor
Z_BACK = 22.0                      # body back face (bay for the S3 behind)

# --- diffuser -----------------------------------------------------------------
R_D_O, R_D_I = RING_OD / 2, RING_ID / 2
DIFF_WALL, SKIRT = 1.0, 1.2

# --- face ---------------------------------------------------------------------
W_OD, W_ID = RING_OD + 1.0, RING_ID - 1.0     # window over the ring
APERTURE_D = DISP_ACTIVE_D + 1.0              # window over the display
SPOKES, SPOKE_W = 4, 5.0
TICK_R = W_ID / 2 - 2.0                       # ticks run inward from here
TICK_MIN_L, TICK_MAJ_L = 4.0, 7.0
TICK_MIN_W, TICK_MAJ_W = 1.8, 3.0

CUT, ENGRAVE = "#FF0000", "#000000"


def build_body():
    """One revolve. Ring pocket outboard, display pocket inboard, bay behind.

    Traced counter-clockwise in (r, z) so the interior stays on the left and
    the revolved mesh comes out wound outward.
    """
    return mesh.revolve([
        (R_BODY, 0.0),        # front face of the retaining lip
        (R_BODY, Z_BACK),     # down the outside
        (R_DL,   Z_BACK),     # across the back, inward to the S3 bay opening
        (R_DL,   Z_DISP_B),   # up the bay wall
        (R_DP,   Z_DISP_B),   # the ledge the display sits on
        (R_DP,   Z_FACE),     # display pocket wall
        (R_CH_I, Z_FACE),     # web between display pocket and ring pocket
        (R_CH_I, Z_PCB_B),    # ring pocket inner wall
        (R_CH_O, Z_PCB_B),    # ring pocket floor — the PCB rests here
        (R_CH_O, Z_FACE),     # ring pocket outer wall
        (R_FACE, Z_FACE),     # face recess floor
        (R_FACE, 0.0),        # inside of the retaining lip
    ], seg=200)


def build_diffuser():
    tris = mesh.revolve([
        (R_D_I, 0.0), (R_D_O, 0.0),
        (R_D_O, DIFF_H), (R_D_O - SKIRT, DIFF_H),
        (R_D_O - SKIRT, DIFF_TOP),
        (R_D_I + SKIRT, DIFF_TOP),
        (R_D_I + SKIRT, DIFF_H), (R_D_I, DIFF_H),
    ], seg=200)
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
    r_out = R_DL - 0.15
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
          f"pitch {math.pi*(RING_OD+RING_ID)/2/NUM_LEDS:.2f} mm\n")
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
    want(DISP_MODULE_D < RING_ID - 6,
         f"display {DISP_MODULE_D} mm fits the {RING_ID} mm centre "
         f"({(RING_ID-DISP_MODULE_D)/2:.1f} mm each side)")
    want(R_DP < R_CH_I - 3, "display pocket clears the ring pocket wall")
    want(R_DL > 8, f"S3 bay opening {R_DL*2:.0f} mm across")
    want(TICK_R - TICK_MAJ_L > APERTURE_D / 2 + 1,
         f"ticks (in to r={TICK_R-TICK_MAJ_L:.1f}) clear the "
         f"{APERTURE_D:.0f} mm aperture (r={APERTURE_D/2:.1f})")
    want(TICK_R < W_ID / 2, "ticks sit inside the ring window")
    cell = math.pi * (R_D_O + R_D_I) / NUM_LEDS - DIFF_WALL
    want(cell > 3.0, f"diffuser cell {cell:.2f} mm wide")
    want(Z_DISP_B <= Z_PCB_B, "display sits no deeper than the ring PCB")
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
