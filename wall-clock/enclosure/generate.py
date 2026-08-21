#!/usr/bin/env python3
"""Generate the Glowforge SVG and validate the enclosure geometry.

    python3 generate.py            # writes face.svg, checks geometry
    python3 generate.py --preview  # also renders preview.png (needs cairosvg)

The SVG is real-world scale: 1 SVG user unit = 1 mm, with mm on width/height,
so Glowforge imports it at the right size without scaling. Colours map to
operations (Glowforge groups by colour, you assign the operation in the UI):

    #FF0000  red    -> CUT
    #0000FF  blue   -> SCORE   (alignment marks, optional)
    #000000  black  -> ENGRAVE (filled shapes)

NO TEXT ELEMENTS. Glowforge does not embed fonts, so an SVG <text> node
renders with whatever the browser substitutes, or not at all. Every mark here
is geometry. If you want numerals, add them in a vector editor and convert
text to paths BEFORE uploading.
"""
import math
import sys
import xml.etree.ElementTree as ET

import params as p

CUT, SCORE, ENGRAVE = "#FF0000", "#0000FF", "#000000"


def polar(r, deg):
    """Clock convention: 0 deg = 12 o'clock, increasing clockwise."""
    a = math.radians(deg - 90.0)
    return r * math.cos(a), r * math.sin(a)


def arc_path(r_out, r_in, a0, a1, half_w):
    """One aperture segment between two spokes.

    half_w is the spoke half-width in mm. Converting it to an angle per radius
    (rather than using one fixed angle) is what makes the spoke a constant
    width instead of a wedge.
    """
    da_o = math.degrees(math.asin(half_w / r_out))
    da_i = math.degrees(math.asin(half_w / r_in))
    s_o, e_o = a0 + da_o, a1 - da_o
    s_i, e_i = a0 + da_i, a1 - da_i
    large = 1 if (e_o - s_o) > 180 else 0
    x1, y1 = polar(r_out, s_o)
    x2, y2 = polar(r_out, e_o)
    x3, y3 = polar(r_in, e_i)
    x4, y4 = polar(r_in, s_i)
    return (f"M {x1:.4f} {y1:.4f} "
            f"A {r_out:.4f} {r_out:.4f} 0 {large} 1 {x2:.4f} {y2:.4f} "
            f"L {x3:.4f} {y3:.4f} "
            f"A {r_in:.4f} {r_in:.4f} 0 {large} 0 {x4:.4f} {y4:.4f} Z")


def tick(deg, r0, r1, w):
    """Radial tick as a closed quad, centred on `deg`, `w` wide."""
    pts = []
    for r, sign in ((r0, +1), (r1, +1), (r1, -1), (r0, -1)):
        d = math.degrees(math.asin((w / 2) / r)) * sign
        pts.append(polar(r, deg + d))
    # reorder so the quad doesn't self-cross
    a, b, c, d = pts[0], pts[1], pts[2], pts[3]
    return ("M {:.4f} {:.4f} L {:.4f} {:.4f} L {:.4f} {:.4f} L {:.4f} {:.4f} Z"
            .format(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]))


def build():
    size = p.FACE_OD + 10.0          # 5mm margin so nothing touches the edge
    c = size / 2.0
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": f"{size}mm", "height": f"{size}mm",
        "viewBox": f"0 0 {size} {size}",
        "version": "1.1",
    })
    ET.SubElement(svg, "title").text = "Wall clock face - 3mm plywood"
    g = ET.SubElement(svg, "g", {"transform": f"translate({c},{c})"})

    def path(d, stroke=None, fill="none", layer=""):
        attrs = {"d": d, "fill": fill}
        if stroke:
            attrs["stroke"] = stroke
            attrs["stroke-width"] = "0.1"
        if layer:
            attrs["data-layer"] = layer
        ET.SubElement(g, "path", attrs)

    def circle(r, stroke, layer):
        ET.SubElement(g, "circle", {
            "cx": "0", "cy": "0", "r": f"{r:.4f}",
            "fill": "none", "stroke": stroke, "stroke-width": "0.1",
            "data-layer": layer,
        })

    # --- ENGRAVE: hour ticks (drawn first so cuts sit on top visually) ------
    for h in range(12):
        major = (h % 3 == 0)
        w = p.TICK_MAJOR_W if major else p.TICK_MINOR_W
        ln = p.TICK_MAJOR_L if major else p.TICK_MINOR_L
        r1 = p.TICK_OUTER_R
        path(tick(h * 30.0, r1 - ln, r1, w), fill=ENGRAVE, layer="engrave-ticks")

    # --- CUT: window apertures, split by spokes ----------------------------
    # Spokes sit at 45/135/225/315 so they never cover an hour tick.
    step = 360.0 / p.FACE_SPOKES
    for k in range(p.FACE_SPOKES):
        a0 = 45.0 + k * step
        path(arc_path(p.WINDOW_OD / 2, p.WINDOW_ID / 2, a0, a0 + step,
                      p.FACE_SPOKE_W / 2),
             stroke=CUT, layer="cut-window")

    # --- CUT: face fixings -------------------------------------------------
    # On the spoke azimuths, in the solid outer band, so they land between
    # hour ticks rather than on one.
    hole_r = (p.SCREW_M + 0.2) / 2
    for k in range(p.SCREW_POSTS):
        x, y = polar(p.SCREW_POST_R, 45.0 + k * (360.0 / p.SCREW_POSTS))
        ET.SubElement(g, "circle", {
            "cx": f"{x:.4f}", "cy": f"{y:.4f}", "r": f"{hole_r:.4f}",
            "fill": "none", "stroke": CUT, "stroke-width": "0.1",
            "data-layer": "cut-fixings",
        })

    # --- CUT: outline (last, so the part stays supported until the end) ----
    circle(p.FACE_OD / 2, CUT, "cut-outline")

    return svg, size


def check():
    """Assert the parts actually fit each other and the machines."""
    fails = []

    def want(ok, msg):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    print("Geometry checks:")
    want(p.CHANNEL_OD > p.RING_OD and p.CHANNEL_ID < p.RING_ID,
         f"ring {p.RING_OD}/{p.RING_ID} drops into channel "
         f"{p.CHANNEL_OD}/{p.CHANNEL_ID}")
    want(p.WINDOW_OD > p.DIFF_OD - 1 and p.WINDOW_ID < p.DIFF_ID + 1,
         f"face window {p.WINDOW_ID}-{p.WINDOW_OD} exposes diffuser "
         f"{p.DIFF_ID}-{p.DIFF_OD}")
    want(p.WINDOW_OD < p.BODY_OD - 2 * p.BODY_WALL,
         "window clears the body wall")
    head_r = 2.75   # M3 pan head is ~5.5mm across
    want(p.SCREW_POST_R + head_r + 2.0 < p.FACE_OD / 2,
         f"M3 heads at r={p.SCREW_POST_R} clear the {p.FACE_OD:.0f}mm face edge "
         f"by {p.FACE_OD / 2 - p.SCREW_POST_R - head_r:.1f}mm")
    want(p.SCREW_POST_R * 2 > p.WINDOW_OD,
         "fixings sit outside the window, in solid material")
    want(p.TICK_OUTER_R < p.WINDOW_ID / 2,
         f"hour ticks (to r={p.TICK_OUTER_R:.0f}) sit on the centre disc, "
         f"clear of the window at r={p.WINDOW_ID / 2:.0f}")
    want(p.TICK_OUTER_R - p.TICK_MAJOR_L > 20,
         "hour ticks stop short of the middle")

    cell = p.LED_PITCH - p.DIFF_WALL
    want(cell > 3.0, f"diffuser cell {cell:.2f}mm wide at {p.LED_PITCH:.2f}mm pitch")
    want(p.DIFF_TOP_T < 1.2, f"diffuser top {p.DIFF_TOP_T}mm thin enough to glow")

    print("Machine limits:")
    want(p.BODY_OD <= p.BED_XY,
         f"body {p.BODY_OD}mm on {p.BED_XY}mm bed ({p.BED_XY - p.BODY_OD:.0f}mm spare)")
    want(p.DIFF_OD <= p.BED_XY, f"diffuser {p.DIFF_OD}mm on {p.BED_XY}mm bed")
    want(p.FACE_OD + 10 <= p.LASER_XY,
         f"face sheet {p.FACE_OD + 10:.0f}mm on {p.LASER_XY}mm Aura "
         f"({p.LASER_XY - p.FACE_OD - 10:.0f}mm spare)")
    return fails


def write_scad_params():
    """Emit params.scad so OpenSCAD and the SVG share one source of truth.

    Never hand-edit params.scad — edit params.py and re-run this.
    """
    keys = [k for k in dir(p) if k.isupper()]
    lines = ["// GENERATED by generate.py from params.py — DO NOT EDIT BY HAND.",
             "// Edit params.py and re-run:  python3 generate.py", ""]
    for k in sorted(keys):
        v = getattr(p, k)
        if isinstance(v, (int, float)):
            lines.append(f"{k} = {v};")
    lines += ["", "$fn = 180;   // curve smoothness; drop to 64 while iterating"]
    open("params.scad", "w").write("\n".join(lines) + "\n")
    print(f"Wrote params.scad — {len([l for l in lines if '=' in l])} values")


def main():
    svg, size = build()
    write_scad_params()
    out = "face.svg"
    ET.ElementTree(svg).write(out, encoding="unicode", xml_declaration=True)
    n = len(svg[1])
    print(f"Wrote {out} — {size:.0f} x {size:.0f} mm, {n} shapes\n")

    fails = check()

    if "--preview" in sys.argv:
        try:
            import cairosvg
            cairosvg.svg2png(url=out, write_to="preview.png",
                             output_width=900, output_height=900,
                             background_color="#f5efe3")
            print("\nWrote preview.png")
        except ImportError:
            print("\n(cairosvg not installed; skipping preview)")

    if fails:
        print(f"\n{len(fails)} GEOMETRY CHECK(S) FAILED")
        return 1
    print("\nAll geometry checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
