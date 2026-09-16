#!/usr/bin/env python3
"""The laser-cut plywood face for the 60-LED clock, and the coupon that tells
you how deep to engrave it.

Sam, 2026-09-16: "Make a file that I can laser cut wood for the front of the
60LED clock. With lines for the LED's to shine through. Those areas won't be
cut all the way through, but be recessed from the laser so light shines
through."

WHAT THIS REPLACES. On the 60 the white printed diffuser carries a 0.20 mm
membrane over each tick and a 6 mm cell wall between them: the membrane glows,
the wall is opaque. The plywood does the same job the same way round -- opaque
everywhere, thinned to about half a millimetre on the sixty lines -- except
that plywood is opaque to start with, so the cell walls are not needed to stop
light crossing between ticks. The wood IS the mask.

THE SEAT WAS ALREADY THERE. Measured on the built base-60 mesh: the front face
is at z = 22.00, the front bore is r = 116.50, and the screen collar's top face
is at z = 18.99 in a ring from r 30.65 to 35.10. That collar is the seat, it is
3.01 mm down, and a 3 mm sheet lands flush. `Z_RECESS` in params.py has said
"plywood face recess floor" since the first version of the file.

MIRRORING. The lines are engraved from the BACK, so the natural question is
whether the file has to be flipped. It does not, and that is a property worth
keeping rather than a coincidence: every feature here is symmetric about the
12-6 axis, so the drawing and its mirror image are the same drawing. The plain
face is 60-fold symmetric as well, which means any of the sixty rotations seats
it correctly. Do not add an asymmetric mark to this file without also deciding
which side it is drawn from.

Run:  python3 make_face_svg.py          -> laser/*.svg and laser/*.png
"""
import math, os, sys
sys.path.insert(0, '.')
from params import *
import build_v2 as BV

B = BV.BODY60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laser')

CUT   = '#FF0000'      # stroke only: cut through
ENG   = '#000000'      # filled: raster engrave
SCORE = '#0000FF'      # stroke only: score, marks only


# ---------------------------------------------------------------- geometry
def stadium(r0, r1, w, ang_deg, seg=16):
    """A radial slot with half-round ends, as an explicit polygon.

    Explicit, and not an SVG arc, on purpose: `A` takes a large-arc and a sweep
    flag whose sense depends on which way the y axis runs, and this file flips y
    on the way out. A polygon cannot be got subtly wrong -- and check11 measures
    the polygon that lands in the file, not the intent behind it.
    """
    h = w/2.0
    pts = [(r0, -h), (r1, -h)]
    for i in range(1, seg):                      # outer cap, -y round to +y
        a = -math.pi/2 + math.pi*i/seg
        pts.append((r1 + h*math.cos(a), h*math.sin(a)))
    pts.append((r1, h))
    pts.append((r0, h))
    for i in range(1, seg):                      # inner cap, +y round to -y
        a = math.pi/2 + math.pi*i/seg
        pts.append((r0 + h*math.cos(a), h*math.sin(a)))
    t = math.radians(ang_deg)
    c, s = math.cos(t), math.sin(t)
    return [(x*c - y*s, x*s + y*c) for (x, y) in pts]


def poly(pts, fill=None, stroke=None, layer=''):
    d = 'M ' + ' L '.join(f'{x:.4f},{-y:.4f}' for x, y in pts) + ' Z'   # y flipped
    a = f' fill="{fill}"' if fill else ' fill="none"'
    a += f' stroke="{stroke}" stroke-width="0.1"' if stroke else ''
    return f'<path d="{d}"{a} data-layer="{layer}" />'


def circle(r, fill=None, stroke=None, layer=''):
    a = f' fill="{fill}"' if fill else ' fill="none"'
    a += f' stroke="{stroke}" stroke-width="0.1"' if stroke else ''
    return f'<circle cx="0" cy="0" r="{r:.4f}"{a} data-layer="{layer}" />'


def document(body, w, h, title):
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.4f} {h:.4f}">'
            f'<title>{title}</title>'
            f'<g transform="translate({w/2:.4f},{h/2:.4f})">' + ''.join(body) +
            '</g></svg>\n')


# ---------------------------------------------------------------- the face
def face(hours=False):
    r_out = B.r_lip_i - PLY_CLR
    parts = []
    # ENGRAVE FIRST. Glowforge runs steps in the order it finds them and the
    # disc must still be attached to the sheet while it is being engraved: cut
    # the outline first and the piece lifts, shifts, or catches the gantry.
    for k in range(B.n):
        a = 90.0 - k*(360.0/B.n)          # k = 0 at 12 o'clock, clockwise
        w = PLY_HOUR_W if (hours and k % 5 == 0) else PLY_TICK_W
        parts.append(poly(stadium(B.tick_ri, B.tick_ro, w, a),
                          fill=ENG, layer='engrave-ticks'))
    parts.append(circle(PLY_BORE_R, stroke=CUT, layer='cut-screen'))
    parts.append(circle(r_out,      stroke=CUT, layer='cut-outline'))
    d = 2*r_out + 2.0
    return document(parts, d, d,
                    f'60-LED clock face - {PLY_T:.0f} mm plywood - '
                    f'{"hours emphasised" if hours else "plain"}')


# ---------------------------------------------------------------- the coupon
def coupon(n=6):
    """Six real ticks at six settings, each its own colour so the laser can be
    given a different number of passes for each. Cut it, hold it over a lit LED
    in a dark room, and the one that glows without going translucent at the
    edges is the setting for the face.

    There is no way to compute this. It depends on the sheet, the glue line, the
    laser and the lens, so it is measured on the bench and written down.
    """
    W, H = 110.0, 46.0
    pitch = W/(n + 1)
    cols = ['#000000', '#FF00FF', '#00A0A0', '#804000', '#008000', '#606060']
    parts = []
    for i in range(n):
        x = -W/2 + pitch*(i + 1)
        pts = [(x + px, py) for (px, py) in stadium(-12.5, 12.5, PLY_TICK_W, 90.0)]
        parts.append(poly(pts, fill=cols[i % len(cols)], layer=f'engrave-test-{i+1}'))
    # the orientation notch: pass 1 is the end with the notch
    notch = [(-W/2, -3.0), (-W/2 + 4.0, 0.0), (-W/2, 3.0)]
    body = [(-W/2, -H/2), (W/2, -H/2), (W/2, H/2), (-W/2, H/2)]
    parts.append(poly(notch, stroke=CUT, layer='cut-notch'))
    parts.append(poly(body,  stroke=CUT, layer='cut-outline'))
    return document(parts, W + 2.0, H + 2.0,
                    f'Engrave depth coupon - {n} settings - notched end is #1')


def main():
    os.makedirs(OUT, exist_ok=True)
    files = {'face-60-wood.svg':       face(hours=False),
             'face-60-wood-hours.svg': face(hours=True),
             'face-60-depth-test.svg': coupon()}
    for name, svg in files.items():
        with open(os.path.join(OUT, name), 'w') as f:
            f.write(svg)
        print(f'  wrote laser/{name:26s} {len(svg):6d} bytes')
    r_out = B.r_lip_i - PLY_CLR
    print(f'\n  disc      {2*r_out:.2f} mm across, into a {2*B.r_lip_i:.2f} bore')
    print(f'  screen    {2*PLY_BORE_R:.2f} mm bore, active area is {DISP_ACTIVE_D:.1f}')
    print(f'  ticks     {B.n} x {PLY_TICK_W:.2f} wide, r {B.tick_ri:.1f} to {B.tick_ro:.1f}, '
          f'every {360.0/B.n:.0f} deg from 12 o\'clock')
    print(f'  thickness {PLY_T:.2f} nominal; the seat is {Z_FRONT - Z_RECESS:.2f} below the face')


if __name__ == '__main__':
    main()
