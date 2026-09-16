#!/usr/bin/env python3
"""CHECK 11 -- the laser-cut plywood face for the 60.

Measured off the FILE that lands on disk and the MESHES it has to live with,
never off the generator's intent. The generator and this file share params.py
and nothing else: if make_face_svg.py draws a tick in the wrong frame, or flips
a sign, or writes a cut where an engrave belongs, the numbers here come from
re-reading the XML and put the clock's own parts against it.

The one that matters most is section 3. A part that goes inside another one
gets a boolean against it -- that lesson cost 1134 mm3 of plinth sitting inside
a clock last week -- so the disc is built as a solid at its seated height and
intersected with the real base.
"""
import sys, math, os
import numpy as np, trimesh
from lxml import etree
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import csg
from csg import to_manifold, cyl, tube, box_lwh
import build_v2 as BV
from params import *

B = BV.BODY60
LASER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laser')
FAIL = []


def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c:
        FAIL.append(msg)


# ---------------------------------------------------------------- read the SVG
def load(name):
    """Every shape in the file, in millimetres, in MATHS coordinates (y up),
    with the group transform applied and the document centre at the origin."""
    t = etree.parse(os.path.join(LASER, name))
    root = t.getroot()
    w = float(root.get('width').replace('mm', ''))
    h = float(root.get('height').replace('mm', ''))
    vb = [float(v) for v in root.get('viewBox').split()]
    # user units must BE millimetres, or nothing downstream means anything
    assert abs(vb[2] - w) < 1e-6 and abs(vb[3] - h) < 1e-6, \
        f'{name}: viewBox {vb[2]}x{vb[3]} is not the {w}x{h} mm document'
    g = root.find('{http://www.w3.org/2000/svg}g')
    tx, ty = [float(v) for v in g.get('transform')[10:-1].split(',')]
    # The group translate puts the PART frame at the document centre, so the
    # coordinates inside it are already the part's own. Subtracting the
    # translate as well -- which is what this did first -- moves every tick
    # 117 mm sideways and then reports the part as broken. Assert the relation
    # instead of correcting for it twice.
    assert abs(tx - w/2) < 1e-6 and abs(ty - h/2) < 1e-6, \
        f'{name}: the group is translated to {tx},{ty}, not the {w/2},{h/2} centre'
    out = []
    for el in g:
        tag = etree.QName(el).localname
        layer = el.get('data-layer', '')
        fill = el.get('fill', 'none')
        stroke = el.get('stroke')
        if tag == 'circle':
            r = float(el.get('r'))
            pts = [(r*math.cos(a), r*math.sin(a))
                   for a in np.linspace(0, 2*math.pi, 361)[:-1]]
        elif tag == 'path':
            d = el.get('d').replace('M ', '').replace(' Z', '')
            pts = [(float(p.split(',')[0]), -float(p.split(',')[1]))
                   for p in d.split(' L ')]      # y flipped back to maths up
        else:
            continue
        out.append(dict(layer=layer, fill=fill, stroke=stroke, tag=tag,
                        pts=pts, poly=Polygon(pts)))
    return out, w, h


print('=' * 72)
print('CHECK 11: the 3 mm plywood face for the 60-LED clock')

shapes, DW, DH = load('face-60-wood.svg')
ticks = [s for s in shapes if s['layer'] == 'engrave-ticks']
outl = [s for s in shapes if s['layer'] == 'cut-outline']
scr = [s for s in shapes if s['layer'] == 'cut-screen']

print('\n1. The file says what it is')
ck(abs(DW - DH) < 1e-6, 'the document is square', f'{DW:.2f} x {DH:.2f} mm')
ck(len(outl) == 1 and len(scr) == 1, 'one outline and one screen bore',
   f'{len(outl)} outline, {len(scr)} screen')
ck(len(ticks) == B.n, f'{B.n} tick lines', f'{len(ticks)} found')
# the operation is carried by the attributes, and a laser reads the attributes
ck(all(t['fill'] == '#000000' and t['stroke'] is None for t in ticks),
   'every tick is FILLED and unstroked, so it rasters and does not cut')
ck(all(s['fill'] == 'none' and s['stroke'] == '#FF0000' for s in outl + scr),
   'outline and screen bore are STROKED and unfilled, so they cut')
# and the engraves come first in the document, while the disc is still attached
order = [s['layer'] for s in shapes]
ck(order.index('cut-outline') > max(i for i, l in enumerate(order)
                                    if l == 'engrave-ticks'),
   'the engraving is written before the cut, so the disc is still in the sheet')

print('\n2. It is the right size for the clock it goes in')
r_out = max(math.hypot(*p) for p in outl[0]['pts'])
r_scr = max(math.hypot(*p) for p in scr[0]['pts'])
gap = B.r_lip_i - r_out
ck(0.20 <= gap <= 0.60, 'the disc clears the base bore without being loose',
   f'{2*r_out:.2f} mm disc in a {2*B.r_lip_i:.2f} bore: {gap:.2f} radial')
ck(gap - PLY_KERF/2 > 0.10, 'and still clears once the kerf has taken its half',
   f'{gap - PLY_KERF/2:.2f} mm at a {PLY_KERF:.2f} kerf')
ck(2*r_scr < DISP_ACTIVE_D, 'the screen bore is inside the active area, so the '
   'face covers the panel edge',
   f'{2*r_scr:.2f} bore in a {DISP_ACTIVE_D:.1f} active area')

print('\n3. Seated in the base — booleaned, not reasoned about')
base = trimesh.load(csg.part('mini-round-clock-base-60.stl'), process=False)
base.merge_vertices()
# where the collar's top face actually is, measured, not taken from Z_RECESS
zs = np.arange(14.0, 22.0, 0.01)
col = base.contains(np.column_stack([np.full(zs.size, 32.5), np.zeros(zs.size), zs]))
seat = zs[col].max()
def disc_at(z0):
    return (cyl(r_out, z0, z0 + PLY_T, 256)
            - cyl(r_scr, z0 - 1.0, z0 + PLY_T + 1.0, 256))
# Two questions, not one. Seated a hair PROUD of the collar, does anything at
# all stand in the way? And seated ON it, is the collar the only thing it
# touches? A single "overlap < tolerance" test cannot tell a part that rests on
# its seat from a part that is buried 0.2 mm into a boss it never noticed.
clear = (to_manifold(base) ^ disc_at(seat + 0.02)).volume()
ck(clear < 0.01, 'lifted two hundredths off its seat, nothing is in the way',
   f'{clear:.3f} mm3')
touch = to_manifold(base) ^ disc_at(seat)
tv = touch.volume()
tb = csg.to_trimesh(touch) if tv > 1e-6 else None
tr = (np.hypot(tb.vertices[:, 0], tb.vertices[:, 1]) if tb is not None else np.array([0.0]))
ck(tv > 0.5, 'and set down, it really does land on the collar rather than float',
   f'{tv:.2f} mm3 of contact film')
ck(tb is None or (tr.min() > 29.0 and tr.max() < 36.0 and
                  tb.bounds[1][2] - seat < 0.05),
   'and the collar is the ONLY thing it lands on',
   f'contact at r {tr.min():.2f}..{tr.max():.2f}, '
   f'{(tb.bounds[1][2] - seat) if tb is not None else 0:.3f} mm thick')
ck(abs((seat + PLY_T) - Z_FRONT) < 0.25,
   'and its front lands flush with the clock face',
   f'top at z={seat + PLY_T:.2f}, the base front is {Z_FRONT:.2f}')
# it has to LAND on something: the collar ring must be under the wood
rr = np.arange(20.0, 45.0, 0.05)
c2 = base.contains(np.column_stack([rr, np.zeros(rr.size), np.full(rr.size, seat - 0.05)]))
c_ri, c_ro = rr[c2].min(), rr[c2].max()
ck(c_ri > r_scr and c_ro < r_out,
   'the screen collar is a full ring under the wood, not a step it misses',
   f'collar r {c_ri:.2f}..{c_ro:.2f}, wood spans {r_scr:.2f}..{r_out:.2f}')

print('\n4. The lines sit where the light comes out')
# The printed diffuser is the authority: its pockets are the places the design
# lets light reach the face. Every tick's centreline is sampled against it.
dif = trimesh.load(csg.part('mini-round-clock-diffuser-60-plain.stl'), process=False)
dif.merge_vertices()
mids, blocked = [], 0
probe_r = [82.0, 90.0, 100.0, 108.0]
for t in ticks:
    c = t['poly'].centroid
    a = math.degrees(math.atan2(c.y, c.x)) % 360.0
    mids.append(a)
    for r in probe_r:
        p = np.array([[r*math.cos(math.radians(a)), r*math.sin(math.radians(a)), 1.0]])
        if dif.contains(p)[0]:
            blocked += 1
ck(blocked == 0, 'every tick lies over a lit pocket of the printed diffuser',
   f'{blocked} of {len(ticks)*len(probe_r)} samples hit a cell wall')
mids = np.array(sorted(mids))
step = np.diff(np.append(mids, mids[0] + 360.0))
ck(np.allclose(step, 360.0/B.n, atol=0.02), f'evenly spaced at {360.0/B.n:.0f} degrees',
   f'{step.min():.3f} to {step.max():.3f}')
ck(np.min(np.abs(mids - 90.0)) < 0.02, 'with one line at 12 o\'clock',
   f'nearest is {mids[np.argmin(np.abs(mids - 90.0))]:.3f} deg')

print('\n5. The wood that is left')
rings = unary_union([t['poly'] for t in ticks])
ck(rings.bounds[1] > -r_out and rings.bounds[3] < r_out, 'ticks stay inside the disc')
land_out = r_out - max(math.hypot(*p) for t in ticks for p in t['pts'])
land_in = min(math.hypot(*p) for t in ticks for p in t['pts']) - r_scr
ck(land_out >= 3.0, 'a rim of solid wood outside the ticks',
   f'{land_out:.2f} mm to the edge')
ck(land_in >= 20.0, 'and a wide field inside them',
   f'{land_in:.2f} mm to the screen bore')
def slot_wh(poly):
    """The width and length of a slot, off its own minimum rotated rectangle --
    not area/length, which counts the round ends and reads 0.08 mm wide."""
    xy = np.array(poly.minimum_rotated_rectangle.exterior.coords)
    e = np.hypot(*(xy[1:] - xy[:-1]).T)[:2]
    return min(e), max(e)
w = [slot_wh(t['poly'])[0] for t in ticks]
L = [slot_wh(t['poly'])[1] for t in ticks]
ck(abs(np.mean(w) - PLY_TICK_W) < 0.03, f'each line is {PLY_TICK_W:.2f} mm wide',
   f'{np.mean(w):.3f} mm, spread {max(w)-min(w):.4f}')
ck(abs(np.mean(L) - ((B.tick_ro - B.tick_ri) + PLY_TICK_W)) < 0.03,
   f'and runs r {B.tick_ri:.1f} to {B.tick_ro:.1f} with round ends',
   f'{np.mean(L):.2f} mm long')
lit = rings.area
ck(lit > 2000.0, 'and there is enough of it to read across a room',
   f'{lit:.0f} mm2 of glowing line, {100*lit/(math.pi*r_out**2):.1f}% of the face')

print('\n6. Engraved from the back, and it does not matter which way round')
# Mirror the union about x = 0 and about y = 0 and ask whether anything moved.
# If nothing does, the file cannot be put on the sheet the wrong way round --
# which is the whole reason there is no orientation mark on it.
from shapely import affinity
for name, m in (('left to right', affinity.scale(rings, -1, 1, origin=(0, 0))),
                ('top to bottom', affinity.scale(rings, 1, -1, origin=(0, 0)))):
    d = rings.symmetric_difference(m).area
    ck(d < 1.0, f'mirrored {name}, the drawing is unchanged', f'{d:.4f} mm2 differs')

print('\n7. The hours variant')
sh2, _, _ = load('face-60-wood-hours.svg')
t2 = [s for s in sh2 if s['layer'] == 'engrave-ticks']
ck(len(t2) == B.n, f'{B.n} lines')
w2 = sorted(slot_wh(s['poly'])[0] for s in t2)
wide = [x for x in w2 if x > (PLY_TICK_W + PLY_HOUR_W)/2]
ck(len(wide) == 12, 'twelve of them are the wide ones', f'{len(wide)} wide')
r2 = unary_union([s['poly'] for s in t2])
ck(r2.symmetric_difference(affinity.scale(r2, -1, 1, origin=(0, 0))).area < 1.0,
   'and it is still symmetric, so it also cannot go on the wrong way round')
# the wide ones must be the HOURS: 30 degrees apart, one at 12
ha = sorted(math.degrees(math.atan2(s['poly'].centroid.y, s['poly'].centroid.x)) % 360
            for s in t2 if slot_wh(s['poly'])[0] > (PLY_TICK_W + PLY_HOUR_W)/2)
hs = np.diff(np.append(ha, ha[0] + 360.0))
ck(np.allclose(hs, 30.0, atol=0.02) and min(abs(np.array(ha) - 90.0)) < 0.02,
   'every 30 degrees, one of them at 12 o\'clock')

print('\n8. The cell ring that has to go behind it')
# The wood is opaque, so it does not need cell walls to keep light off the face.
# It needs them for the other thing they do: stopping LED n from lighting tick
# n+1. Without them one lit LED glows through three lines and the hands stop
# being hands. diffuser-60-cells is the plain diffuser with the front PLY_T
# sliced off, and it has to seat where the old one did and still hold a guide.
cells = trimesh.load(csg.part('mini-round-clock-diffuser-60-cells.stl'), process=False)
cells.merge_vertices()
cells.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))     # the seating transform
cells.apply_translation([0, 0, DIFF_SEAT_Z])               # check6 uses the same one
cm = to_manifold(cells)
ck(cells.body_count == 1, 'it is one ring, not a ring and an orphaned collar',
   f'{cells.body_count} bodies, {cells.volume/1000:.1f} cm3')
ov = (to_manifold(base) ^ cm).volume()
ck(ov < 5.0, 'it still seats in the base', f'{ov:.2f} mm3')
top = cells.bounds[1][2]
ck(0.0 <= seat - top <= 0.30, 'and its top comes up to meet the wood',
   f'ring tops out at z={top:.2f}, the wood sits at {seat:.2f}: {seat-top:.2f} mm apart')
# a light guide has to drop into a cell and be held by it
g = box_lwh(GUIDE_RI, GUIDE_RO, -GUIDE_W/2, GUIDE_W/2, 15.50, 15.50 + GUIDE_T)
ck((cm ^ g).volume() < 1.0, 'a 6 x 3 mm guide drops into a cell without fouling it',
   f'{(cm ^ g).volume():.2f} mm3')
wide = box_lwh(GUIDE_RI, GUIDE_RO, -GUIDE_W/2 - 1.2, GUIDE_W/2 + 1.2,
               15.50, 15.50 + GUIDE_T)
ck((cm ^ wide).volume() > 20.0, 'and the cell walls are there to stop it wandering',
   f'{(cm ^ wide).volume():.1f} mm3 of wall within 1.2 mm either side')
# the separation itself: is there wall between one tick and the next, all the
# way along? probe the mid-angle between ticks over the tick's radial span
half = 360.0/B.n/2.0
rr = np.arange(B.tick_ri + 1.0, B.tick_ro, 1.0)
zz = np.arange(16.0, 18.8, 0.4)
R, Z = np.meshgrid(rr, zz)
a = math.radians(half)
pts = np.column_stack([(R*math.cos(a)).ravel(), (R*math.sin(a)).ravel(), Z.ravel()])
solid = cells.contains(pts)
ck(solid.mean() > 0.90, 'there is wall between every tick and the next one',
   f'{100*solid.mean():.0f}% of the gap between two ticks is solid')

print('\n9. The depth coupon')
cp, cw, chh = load('face-60-depth-test.svg')
patches = [s for s in cp if s['layer'].startswith('engrave-test-')]
ck(len(patches) >= 4, 'several test patches', f'{len(patches)}')
cols = [s['fill'] for s in patches]
ck(len(set(cols)) == len(cols),
   'each in its own colour, so each can be given its own number of passes',
   f'{len(set(cols))} colours for {len(patches)} patches')
pw = [slot_wh(s['poly'])[0] for s in patches]
ck(all(abs(x - PLY_TICK_W) < 0.03 for x in pw),
   f'and each is a real {PLY_TICK_W:.2f} mm tick, not a square swatch',
   f'{min(pw):.2f} to {max(pw):.2f} mm')
ck(any(s['layer'] == 'cut-notch' for s in cp),
   'with a notch so you can tell which end is setting 1')
ck(max(cw, chh) < 300.0, 'and it fits a small bed', f'{cw:.0f} x {chh:.0f} mm')

print()
if FAIL:
    print(f'CHECK 11: {len(FAIL)} FAILURES')
    [print('   -', f) for f in FAIL]
    sys.exit(1)
print('CHECK 11: the face fits the bore, lands on the collar, and its sixty '
      'lines sit over sixty lit pockets')
