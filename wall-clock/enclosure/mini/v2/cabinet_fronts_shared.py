#!/usr/bin/env python3
"""cabinet_fronts_shared.py - the wood fronts TILED so every internal edge is cut once.

    python cabinet_fronts_shared.py            # every body
    python cabinet_fronts_shared.py --only -32

cabinet.py's own `-fronts.svg` lays the pieces out as they sit on the box, so
the grain runs on from one front into the next. Every piece carries its own
closed outline, so the laser walks the boundary between two neighbours twice.

This file gives up the grain and butts the pieces instead. Two straight edges
that touch are ONE cut serving both - and they do not have to be the same
length, they only have to overlap. All six fronts tile:

        +--------+-------+----------+
        |        |  L1   |   R1     |    the side block, 2 x 2
        |  face  +-------+----------+
        |        |  L0   |   R0     |
        +--------+-------+----------+
        |       drawer front        |    full width, under everything
        +---------------------------+

Every line in that diagram is cut once. The outer boundary is the only closed
path left.

What this costs, both deliberate:

  - Butted corners go square. They were 0.3 mm fillets and they sit behind a
    0.80 mm reveal, so they are not visible. The radii that DO matter - the
    top row's r_in - reveal, which follows the sleeve's corner, and the drawer
    front's two bottom corners - are placed on the outside of the nest, where
    they survive. That is why the top row is the top of the block and the
    drawer front is the bottom of the sheet.
  - A shared cut takes its kerf out of both neighbours, so each piece finishes
    PLY_KERF/2 = 0.10 mm short on a shared edge. Against a 0.80 mm reveal that
    is nothing. It is why the outer boundary is still grown by a half-kerf
    while the shared lines are drawn on the true edge.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cabinet as C
from params import CAB_REVEAL, PLY_KERF, PLY_T

HERE = os.path.dirname(os.path.abspath(__file__))
K = PLY_KERF / 2
MARGIN = 5.0
SQ = 0.0          # a butted corner is square


def layout(F):
    """Every piece placed so it touches its neighbours. Returns
    (polys, holes, circles, w, h) in sheet coords with y UP."""
    r_top = F.r_in - CAB_REVEAL          # the radius that follows the sleeve
    fpo = C.face_panel_outline(F)
    fx0 = min(x for x, _ in fpo)
    fz0 = min(z for _, z in fpo)
    fw = max(x for x, _ in fpo) - fx0
    fh = max(z for _, z in fpo) - fz0
    dfo = C.drawer_front_outline(F)
    dx0 = min(x for x, _ in dfo)
    dz0 = min(z for _, z in dfo)
    dw = max(x for x, _ in dfo) - dx0
    dh = max(z for _, z in dfo) - dz0
    sw = (F.w_in / 2 - CAB_REVEAL) - (F.x_part_o + CAB_REVEAL)
    rows = [(z0 + CAB_REVEAL, z1 - CAB_REVEAL) for z0, z1 in F.side_z]
    h0 = rows[0][1] - rows[0][0]
    h1 = rows[1][1] - rows[1][0]

    up_w = fw + 2 * sw
    span = max(dw, up_w)
    w = MARGIN + span + MARGIN
    h = MARGIN + dh + max(fh, h0 + h1) + MARGIN
    x_d = MARGIN + (span - dw) / 2
    x_u = MARGIN + (span - up_w) / 2
    y_d = MARGIN
    y_u = MARGIN + dh

    polys, holes, circles = [], [], []
    # drawer front: the two big bottom radii face the sheet edge, top is butted
    polys.append(C.rrect_r(x_d, x_d + dw, y_d, y_d + dh, SQ, SQ, r_top, r_top))
    for sx in (1, -1):
        holes.append((x_d + dw / 2 + sx * F.pull_x, y_d + F.z_pull - dz0))
    # A corner keeps its radius only where BOTH its edges are on the outside of
    # the nest. The side columns go either side of the face panel - as they do
    # on the cabinet - so each column's sleeve radius lands on a sheet edge.
    x_face = x_u + sw
    polys.append(C.rrect_r(x_face, x_face + fw, y_u, y_u + fh, SQ, SQ, SQ, SQ))
    circles.append(C.circle(F.aper_r, x_face + fw / 2, y_u + F.z_clock - fz0, 360))
    for sx in (-1, 1):
        x0 = x_u if sx < 0 else x_face + fw
        for row in (0, 1):
            y0 = y_u + (0 if row == 0 else h0)
            hh = h0 if row == 0 else h1
            tr = tl = bl = br = SQ
            if row == 1:
                if sx < 0:
                    tl = r_top          # outer top-left of the sheet
                else:
                    tr = r_top          # outer top-right of the sheet
            polys.append(C.rrect_r(x0, x0 + sw, y0, y0 + hh, tr, tl, bl, br))
            inst = next(i for i in C.side_instances(F)
                        if i['sx'] == sx and i['row'] == row)
            for s2 in (1, -1):
                x_world = abs(sx * F.x_side_c + s2 * F.side_pull_x)
                xl = x_world - (F.x_part_o + CAB_REVEAL)
                if sx < 0:
                    xl = sw - xl
                holes.append((x0 + xl, y0 + inst['z_pull'] - rows[row][0]))
    return polys, holes, circles, w, h


def write_svg(F, path):
    from shapely.geometry import Polygon
    from shapely.ops import linemerge, unary_union
    polys, holes, circles, w, h = layout(F)
    shp = [Polygon(p).buffer(0) for p in polys]
    joined = unary_union(shp)
    if joined.geom_type != "Polygon":
        raise SystemExit("pieces did not tile into one body: " + joined.geom_type)
    # every edge the pieces share: all their boundaries, less the outer one.
    # linemerge then joins the segments end to end, so the laser pierces once
    # per run of shared edge rather than once per piece that touches it.
    inner = unary_union([p.boundary for p in shp])
    inner = inner.difference(joined.boundary.buffer(1e-6))
    if not inner.is_empty:
        inner = linemerge(inner)

    def tr(pts):
        return [(x, h - y) for x, y in pts]

    def d_of(pts, closed=True):
        body = " L ".join("%.3f %.3f" % (x, y) for x, y in pts)
        return "M " + body + (" Z" if closed else "")

    paths = []
    for hx, hy in holes:
        paths.append(d_of(tr(C._offset(C.circle(C.SCREW_CLEAR / 2 + 0.1, hx, hy, 48), -K))))
    for c in circles:
        paths.append(d_of(tr(C._offset(c, -K))))
    n_lines = 0
    for ls in getattr(inner, "geoms", [inner]):
        if ls.is_empty or ls.geom_type != "LineString":
            continue
        pts = list(ls.coords)
        if len(pts) < 2:
            continue
        paths.append(d_of(tr(pts), closed=False))
        n_lines += 1
    outer = Polygon(joined.exterior).buffer(K, join_style=1, resolution=16)
    paths.append(d_of(tr(list(outer.exterior.coords)[:-1])))

    head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
            'viewBox="0 0 %.2f %.2f">' % (w, h, w, h))
    note = ("<!-- mini-round-clock cabinet%s fronts, TILED for shared cuts: %.2f mm ply, "
            "kerf %.2f. Red = cut. One outer outline plus the internal lines; every "
            "internal line is cut ONCE and frees the piece on both sides of it. "
            "Holes first, lines next, outline last. -->" % (F.tag, PLY_T, PLY_KERF))
    out = [head, note]
    out += ['<path d="%s" fill="none" stroke="#FF0000" stroke-width="0.1"/>' % d for d in paths]
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return len(polys), n_lines, w, h


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="cabinet wood fronts, tiled for shared cuts")
    ap.add_argument("--only", default=None, help='"" or -32')
    a = ap.parse_args()
    for tag in ([a.only] if a.only is not None else list(C.BODIES)):
        F = C.Frame(tag)
        if not F.sides:
            print("%s: no side drawers" % (tag or "24"))
            continue
        p = os.path.join(HERE, "cabinet",
                         "mini-round-clock-cabinet%s-fronts-shared.svg" % tag)
        n, lines, w, h = write_svg(F, p)
        print("%4s: %s  %.1f x %.1f mm, %d pieces from 1 outline + %d shared lines"
              % (tag or "24", os.path.basename(p), w, h, n, lines))
