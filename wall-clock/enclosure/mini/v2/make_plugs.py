#!/usr/bin/env python3
"""White press-fit plugs for a plywood face whose sixty lines are CUT THROUGH.

Sam, 2026-09-17: "I will be cutting out the 60 lines instead of engraving.
Create a 3d printed file that can be pushed into the 60 cut lines from the back.
I want them to be individual pieces that are a press fit."

THE SHAPE. Each plug is a stadium prism -- the slot's own section -- with a
wider, thinner FLANGE behind it. Pushed in from the back, the body fills the
3 mm of ply and finishes flush at the front; the flange stops against the
wood's back face so it cannot go through, and gives you something to push on
that is not the 2 mm sliver itself.

WHY THE FLANGE IS ONLY 0.40 THICK, AND ONLY WIDER AT THE SIDES. Both numbers
are measured off the seated cell ring, not chosen:

    pocket behind each tick     6.65 mm wide, 3.25 deep (z 15.68 .. 18.93)
    wood's back face            z 19.00
    a fitted 3 mm guide         tops out at 18.50, leaving 0.43

so 0.40 thick clears the guide if the guides are in and obviously clears if
they are not -- one part, either build. And it does not overhang the ENDS
because the slot already reaches r 79.1 while the guide channel starts at
79.0. There is room at the sides and none at the ends.

WHAT IS NOT KNOWN. PLUG_FIT, the interference. The hole is the drawn line plus
the laser's kerf, and the plug is the hole plus however much a press fit wants
on Sam's printer. None of that is computable from here -- so
face-60-plug-fit-test.stl carries six widths with the number embossed on each,
the same answer the depth coupon gave for the engrave depth.
"""
import os, sys, math
import numpy as np, trimesh
from shapely.geometry import LineString
import csg
from csg import to_manifold, to_trimesh
import build_v2 as BV
from params import *
from make_face_svg import digit

B = BV.BODY60
SEG_ENDS = 24          # facets around each rounded end


def stadium_poly(length, width, seg=SEG_ENDS):
    """A stadium of OVERALL length x width, centred on the origin, long axis y."""
    r = width / 2.0
    straight = length - width
    if straight < 0:
        raise ValueError(f'length {length} shorter than width {width}')
    return LineString([(0.0, -straight / 2.0),
                       (0.0, straight / 2.0)]).buffer(r, resolution=seg // 4)


def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0)
    m.apply_translation([0.0, 0.0, z0])
    return to_manifold(m)


def plug(width, length, body_t=None, flange_t=None, mark=None,
         flange_len=None):
    """One plug, z=0 at the wood's BACK face: body up, flange down."""
    body_t = PLUG_T if body_t is None else body_t
    flange_t = PLUG_FLANGE_T if flange_t is None else flange_t
    # The body is sunk INTO the flange rather than butted onto it. Two solids
    # that meet exactly on a plane is the one thing float32 does not survive.
    flange_len = PLUG_FLANGE_LEN if flange_len is None else flange_len
    m = prism(stadium_poly(length, width), -PLUG_BODY_SINK, body_t)
    m += prism(stadium_poly(flange_len, PLUG_FLANGE_W), -flange_t, 0.0)
    if mark is not None:
        # the index, standing off the back of a TEST flange so you can read
        # which one went in. Seven-segment, the same glyphs as the coupon --
        # no font, nothing for a slicer to substitute.
        for g in digit(mark, 0.0, 0.0, PLUG_TEST_MARK_SIZE):
            gp = trimesh.creation.extrude_polygon(
                LineString(g + [g[0]]).convex_hull, PLUG_TEST_MARK_H)
            gp.apply_translation([0.0, 0.0, -flange_t - PLUG_TEST_MARK_H])
            m += to_manifold(gp)
    return m


def lay_out(items, cols, pitch_x, pitch_y):
    """Separate bodies on a print plate. No sprue: Sam asked for individual
    pieces, and a sprue on a 2 mm part breaks the part when you cut it."""
    out = None
    for i, m in enumerate(items):
        c, r = i % cols, i // cols
        t = to_trimesh(m)
        t.apply_translation([(c - (cols - 1) / 2.0) * pitch_x,
                             (r * pitch_y), 0.0])
        out = to_manifold(t) if out is None else out + to_manifold(t)
    return out


def main():
    slot_len = (B.tick_ro - B.tick_ri) + PLY_TICK_W          # 32.30 drawn
    hole_len = slot_len + PLUG_KERF                          # 32.50 cut
    body_len = PLUG_FLANGE_LEN - 2 * PLUG_END_INSET          # 31.60
    print(f'  slot drawn {slot_len:.2f} long -> hole {hole_len:.2f} after kerf')
    print(f'  flange {PLUG_FLANGE_LEN:.2f} long (pocket allows 32.20), '
          f'body {body_len:.2f} strictly inside it')
    print(f'  minute plug {PLUG_W:.2f} wide, hour plug {PLUG_HOUR_W:.2f}, '
          f'body {PLUG_T:.2f} tall, flange {PLUG_FLANGE_W:.2f} x '
          f'{PLUG_FLANGE_T:.2f}')

    jobs = []
    # 1. the plain face: sixty identical plugs
    jobs.append(('mini-round-clock-face-60-plugs',
                 [plug(PLUG_W, body_len) for _ in range(B.n)], 10))
    # 2. the hours face: forty-eight narrow, twelve wide
    hrs = [plug(PLUG_HOUR_W if i % 5 == 0 else PLUG_W, body_len)
           for i in range(B.n)]
    jobs.append(('mini-round-clock-face-60-plugs-hours', hrs, 10))
    # 3. the fit test: six widths, numbered, on a flange you can hold
    test = []
    for i in range(6):
        w = PLY_TICK_W + PLUG_KERF + (i - 1) * 0.05      # 1.95 .. 2.20
        test.append(plug(w, body_len, flange_t=PLUG_TEST_FLANGE_T, mark=i + 1))
        print(f'    test {i+1}: {w:.2f} wide '
              f'({w - (PLY_TICK_W + PLUG_KERF):+.2f} on a {PLY_TICK_W + PLUG_KERF:.2f} hole)')
    jobs.append(('mini-round-clock-face-60-plug-fit-test', test, 6))

    for name, items, cols in jobs:
        man = lay_out(items, cols, PLUG_FLANGE_W + 2.0, body_len + 3.0)
        t = csg.finalise(man, name, strict=False)
        t.export(csg.part_out(name + '.stl'))
        t.export(csg.part_out(name + '.3mf'))
        print(f'  wrote {name + ".stl":48s} {len(items)} bodies, '
              f'{t.volume/1000:.2f} cm3')


if __name__ == '__main__':
    main()
