#!/usr/bin/env python3
"""CHECK 12 -- the white press-fit plugs for a CUT-THROUGH plywood face.

Measured off the STLs that land on disk and the meshes they have to live with.
The generator and this file share params.py and nothing else.

Section 3 is the one that matters, for the same reason it was in check 11: a
part that goes inside another one gets a BOOLEAN against it, in the assembly's
own transform. Here that is the flange against the seated cell ring and against
a fitted perspex guide -- 0.40 mm of flange in a gap measured at 0.43.
"""
import os, sys, math
import numpy as np, trimesh
import csg
from csg import to_manifold, to_trimesh, box_lwh
import build_v2 as BV
from params import *

B = BV.BODY60
FAIL = []


def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c:
        FAIL.append(msg)


def bodies(name):
    t = trimesh.load(csg.part(name), process=False)
    t.merge_vertices()
    return t.split(only_watertight=False)


def body_w(b):
    """The width of the part that goes INTO the slot.

    Not b.extents[0]: the bounding box is the FLANGE, which is 5.60 on every
    plug by design, so measuring it said all sixty were identical and that the
    hours plate had no wide ones -- a checker reading the one dimension the
    part deliberately holds constant. The body lives above the flange's top
    face at z=0, so measure it there."""
    # A real SECTION, not a vertex filter: the body is a straight prism, so it
    # has no vertices anywhere between its bottom and its top and filtering by
    # z returned an empty array.
    sec = b.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
    v = np.asarray(sec.vertices)
    return float(v[:, 0].max() - v[:, 0].min())


SLOT_LEN = (B.tick_ro - B.tick_ri) + PLY_TICK_W      # 32.30 as drawn
HOLE_LEN = SLOT_LEN + PLUG_KERF                      # 32.50 once cut
HOLE_W = PLY_TICK_W + PLUG_KERF                      # 2.00
HOLE_HR_W = PLY_HOUR_W + PLUG_KERF                   # 3.00
R_MID = (B.tick_ri - PLY_TICK_W / 2 + B.tick_ro + PLY_TICK_W / 2) / 2.0
BACK = 22.00 - PLY_T                                 # 19.00, the wood's back

print('CHECK 12 -- press-fit plugs for a cut-through face')
print(f'  slot as drawn {SLOT_LEN:.2f} x {PLY_TICK_W:.2f}; '
      f'once cut {HOLE_LEN:.2f} x {HOLE_W:.2f}; wood back z={BACK:.2f}')

# ---------------------------------------------------------- 1. the plain plate
print('\n1. The plain plate -- sixty identical plugs')
pl = bodies('mini-round-clock-face-60-plugs.stl')
ck(len(pl) == B.n, 'one plug per LED, and they are separate pieces',
   f'{len(pl)} bodies')
ws = sorted(round(body_w(b), 2) for b in pl)
ck(set(ws) == {round(PLUG_W, 2)}, 'every one the same width',
   f'widths {sorted(set(ws))}')
hs = sorted(round(float(b.extents[2]), 2) for b in pl)
ck(set(hs) == {round(PLUG_T + PLUG_FLANGE_T, 2)},
   'body plus flange, and nothing taller', f'heights {sorted(set(hs))}')
ck(all(b.is_watertight for b in pl), 'each one closes')

# ------------------------------------------------- 2. it is WIDER than the hole
print('\n2. It is a press fit, which means it does not fit')
ck(PLUG_W > HOLE_W, 'the plug is wider than the hole the laser leaves',
   f'{PLUG_W:.2f} into {HOLE_W:.2f} = {PLUG_W - HOLE_W:.2f} interference')
ck(PLUG_FLANGE_LEN - 2 * PLUG_END_INSET < HOLE_LEN,
   'and it is NOT tight on length as well -- tight on both goes in crooked',
   f'body {PLUG_FLANGE_LEN - 2*PLUG_END_INSET:.2f} in a {HOLE_LEN:.2f} hole')
ck(PLUG_FLANGE_W > HOLE_W,
   'the flange cannot pass through the slot, so it cannot be pushed too far',
   f'flange {PLUG_FLANGE_W:.2f} vs hole {HOLE_W:.2f}')

# --------------------------------------------- 3. seated, against the real parts
print('\n3. Seated behind the wood, against the parts it has to share with')
p = pl[0].copy()
c = p.bounds.mean(axis=0)
p.apply_translation([-c[0], -c[1], 0.0])          # recentre in XY, keep its z
p.apply_translation([0.0, R_MID, BACK])           # seat at 12 o'clock
pm = to_manifold(p)
ck(abs(p.bounds[1][2] - 22.00) < 1e-6,
   'the body finishes flush with the face of the clock',
   f'plug tops out at z={p.bounds[1][2]:.3f}, the wood face is 22.000')
ck(abs(p.bounds[0][2] - (BACK - PLUG_FLANGE_T)) < 1e-6,
   'and the flange stands exactly its own thickness behind the wood',
   f'z={p.bounds[0][2]:.3f}')

cells = trimesh.load(csg.part('mini-round-clock-diffuser-60-cells.stl'),
                     process=False)
cells.merge_vertices()
cells.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
cells.apply_translation([0, 0, DIFF_SEAT_Z])
ov = (pm ^ to_manifold(cells)).volume()
ck(ov < 0.5, 'the flange does not foul the cell ring behind it',
   f'{ov:.3f} mm3')

guide = box_lwh(GUIDE_RI, GUIDE_RO, -GUIDE_W / 2, GUIDE_W / 2,
                15.50, 15.50 + GUIDE_T)
gv = (pm ^ guide).volume()
ck(gv < 0.5, 'nor a fitted 3 mm perspex guide, which tops out at 18.50',
   f'{gv:.3f} mm3')

# the flange has to stay inside the pocket, and the pocket is not centred
fl = p.slice_plane([0, 0, BACK - 0.01], [0, 0, -1])
rr = np.hypot(fl.vertices[:, 0], fl.vertices[:, 1])
ck(rr.min() > 79.0 and rr.max() < 113.5,
   'and the flange stays inside a pocket that runs r 79.0 to 113.5',
   f'flange spans r {rr.min():.2f} .. {rr.max():.2f}')

# ------------------------------------------------------- 4. it fills the slot
print('\n4. It fills the slot it is plugging')
hole = to_manifold(trimesh.creation.extrude_polygon(
    __import__('make_plugs').stadium_poly(HOLE_LEN, HOLE_W), PLY_T))
ht = to_trimesh(hole)
ht.apply_translation([0.0, R_MID, BACK])
hole = to_manifold(ht)
filled = (pm ^ hole).volume() / hole.volume()
ck(filled > 0.93, 'the plug fills the hole it is pushed into',
   f'{100*filled:.1f}% of the slot volume is plug')

# ------------------------------------------------------- 5. the hours variant
print('\n5. The hours plate -- twelve wide ones')
hp = bodies('mini-round-clock-face-60-plugs-hours.stl')
ck(len(hp) == B.n, 'sixty again', f'{len(hp)} bodies')
hw = [round(body_w(b), 2) for b in hp]
ck(hw.count(round(PLUG_HOUR_W, 2)) == 12,
   'twelve of them are the wide ones', f'{hw.count(round(PLUG_HOUR_W,2))} wide')
ck(hw.count(round(PLUG_W, 2)) == 48, 'and forty-eight are not',
   f'{hw.count(round(PLUG_W,2))} narrow')
ck(PLUG_HOUR_W > HOLE_HR_W, 'the wide one is a press fit in the wide slot too',
   f'{PLUG_HOUR_W:.2f} into {HOLE_HR_W:.2f}')

# ---------------------------------------------------------- 6. the fit test
print('\n6. The fit test, because the interference cannot be computed')
ft = bodies('mini-round-clock-face-60-plug-fit-test.stl')
ck(len(ft) == 6, 'six of them', f'{len(ft)} bodies')
fw = sorted(round(body_w(b), 2) for b in ft)
ck(len(set(fw)) == 6, 'every one a different width', f'{fw}')
ck(abs(fw[0] - 1.95) < 0.02 and abs(fw[-1] - 2.20) < 0.02,
   'spanning slack to tight around the nominal hole',
   f'{fw[0]:.2f} .. {fw[-1]:.2f} on a {HOLE_W:.2f} hole')
ck(all(abs((fw[i+1] - fw[i]) - 0.05) < 0.02 for i in range(5)),
   'in even steps, so the answer interpolates')
# the numbers have to be SHAPES -- the coupon's digits came out zero-width and
# a test that only counted segments passed them
tall = [round(float(b.extents[2]), 2) for b in ft]
ck(set(tall) == {round(PLUG_T + PLUG_TEST_FLANGE_T + PLUG_TEST_MARK_H, 2)},
   'each carries its number, standing off the flange', f'heights {sorted(set(tall))}')
# Everything BELOW the flange's back face is the numeral. Capped, so it closes
# and its volume means something -- the first version took the convex hull of a
# flat section, which is a zero-thickness solid whose volume is noise. Third
# time in this file that the checker measured the wrong thing; the part was
# right every time. Threshold 0.5: a '1' is two segments and measures 0.80,
# a zero-width glyph measures nothing, and 0.8 was a knife-edge threshold that
# would flip on any change to the digit height.
marks = []
for b in ft:
    m = b.slice_plane([0, 0, b.bounds[0][2] + PLUG_TEST_MARK_H],
                      [0, 0, -1], cap=True)
    marks.append(float(abs(m.volume)) if len(m.vertices) else 0.0)
ck(all(v > 0.5 for v in marks), 'and every number has real substance to it',
   f'smallest {min(marks):.2f} mm3, largest {max(marks):.2f}')
thin = PLUG_TEST_MARK_SIZE * 0.16
ck(thin >= 0.45, 'and its thinnest stroke is wider than one extrusion',
   f'{thin:.2f} mm at a 0.40 nozzle')

print()
if FAIL:
    print(f'CHECK 12: {len(FAIL)} FAILURES')
    for f in FAIL:
        print('   ' + f)
    sys.exit(1)
print('CHECK 12: the plugs press into the cut slots, finish flush, '
      'and clear the cells and the guides behind')
