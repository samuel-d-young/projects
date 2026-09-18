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
# THE HOLE IS SIZED BY WHAT PASSES THROUGH IT. This used to assert the
# opposite -- that the bore was INSIDE the 55 mm active area, so the face would
# cover the panel edge -- and that assertion passed happily on a face whose
# middle hole was 5.9 mm too small to go over the 59.9 mm screen collar. It was
# checking a preference against a part that could not be assembled.
ck(2*r_scr >= PLY_CENTRE_OD + 2*PLY_CENTRE_CLR - 0.01,
   f'the middle hole clears the {PLY_CENTRE_OD:.1f} mm housing that has to pass '
   f'through it',
   f'{2*r_scr:.2f} bore over a {PLY_CENTRE_OD:.1f} housing: '
   f'{r_scr - PLY_CENTRE_OD/2:.2f} radial')
ck(2*r_scr - PLY_KERF > PLY_CENTRE_OD,
   'and still clears once the kerf has taken its half',
   f'{2*r_scr - PLY_KERF:.2f} vs {PLY_CENTRE_OD:.1f}')
ck(2*r_scr < DISP_ACTIVE_D,
   'and it still FRAMES the panel, which is what Sam wanted kept',
   f'{2*r_scr:.2f} bore inside a {DISP_ACTIVE_D:.1f} active area: '
   f'{(DISP_ACTIVE_D - 2*r_scr)/2:.2f} mm of wood over the panel edge')

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
# What matters is how WIDE the seat is, not whether the collar is completely
# hidden. The old test demanded the collar's inner edge sit outboard of the
# hole, which is a statement about looks; once the hole grew to clear the
# housing a 0.3 mm ring of collar shows through it and the wood still has 4.5 mm
# of annular seat to land on.
seat_w = min(c_ro, r_out) - max(c_ri, r_scr)
ck(seat_w > 2.0, 'the wood lands on a real width of collar, not an edge',
   f'collar r {c_ri:.2f}..{c_ro:.2f}, wood from {r_scr:.2f}: '
   f'{seat_w:.2f} mm of seat')
ck(c_ro < r_out, 'and the collar is inboard of the disc, so nothing overhangs',
   f'collar out to {c_ro:.2f}, disc to {r_out:.2f}')

print('\n3b. Against the part DIRECTLY BEHIND IT, which section 3 never did')
# Sam, 2026-09-17, after cutting a face: "That laser cut svg didn't fit the
# middle part at all. I wasted material."
#
# Section 3 booleans the disc against the BASE and stops there. It proved the
# wood lands on the collar and clears the bore -- and never once put it against
# the diffuser, which is the part occupying the very space the wood wants.
#
# The plain diffuser tops out at 21.93 and the wood wants 19.00 to 22.00: they
# overlap by about 105 CUBIC CENTIMETRES. With a plain diffuser in the clock the
# face cannot go in at all. That is not a tolerance, it is the whole part, and
# seven checks measured this face without asking the question.
#
# The same lesson as the plinth that sat inside the clock: a part that goes
# inside another one gets a boolean against it. I applied it to the base and
# not to the thing immediately behind the base.
wood_solid = (cyl(r_out, seat, seat + PLY_T, 256)
              - cyl(r_scr, seat - 1.0, seat + PLY_T + 1.0, 256))
for nm, want_clear in (('mini-round-clock-diffuser-60-cells.stl', True),
                       ('mini-round-clock-diffuser-60-plain.stl', False),
                       ('mini-round-clock-diffuser-60.stl', False)):
    pth = csg.part(nm)
    if not os.path.exists(pth):
        continue
    d = trimesh.load(pth, process=False)
    d.merge_vertices()
    d.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
    d.apply_translation([0, 0, DIFF_SEAT_Z])
    v = (to_manifold(d) ^ wood_solid).volume()
    if want_clear:
        ck(v < 1.0, f'{nm} is the one that lets the wood in',
           f'{v:.2f} mm3 of clash, tops out at z={d.bounds[1][2]:.2f}')
    else:
        ck(v > 1000.0,
           f'{nm} does NOT -- and the check records that rather than assuming it',
           f'{v/1000:.1f} cm3 of clash, tops out at z={d.bounds[1][2]:.2f}')

print('\n3c. Nothing in the middle reaches the wood any more')
# Sam cut a face and it would not go on: "The hole in the middle was too small
# for the 3D printed housing." The hole was 54.0 and the screen collar 59.9.
#
# Two ways out: open the hole to clear the collar, or cut the collar down to
# pass under the wood. Sam chose the second -- "keep the 54mm frame, do the
# diffuser variant" -- so this is the check that the choice actually holds.
# It is a boolean against the parts, not a comparison of parameters, because
# the parameter comparison is what was wrong in the first place.
wood_vol = (cyl(r_out, 19.00, 22.00, 256)
            - cyl(r_scr, 18.0, 23.0, 256))
stack = None
for nm in ('mini-round-clock-diffuser-60-cells.stl',
           'mini-round-clock-screen-collar-60.stl'):
    m = trimesh.load(csg.part(nm), process=False)
    m.merge_vertices()
    m.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
    m.apply_translation([0, 0, DIFF_SEAT_Z])
    ck(m.bounds[1][2] <= 19.00 + 1e-6,
       f'{nm.replace("mini-round-clock-", "")} stops below the wood',
       f'tops out at z={m.bounds[1][2]:.2f}, wood back face is 19.00')
    stack = to_manifold(m) if stack is None else stack + to_manifold(m)
clash = (stack ^ wood_vol).volume()
ck(clash < 1.0, 'so the whole stack clears the wood -- booleaned, not argued',
   f'{clash:.3f} mm3')

# and the collar has to still DO something: sit in the base bore, round the
# screen, without standing in front of a pixel or leaning on the glass
col = trimesh.load(csg.part('mini-round-clock-screen-collar-60.stl'),
                   process=False)
col.merge_vertices()
col.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
col.apply_translation([0, 0, DIFF_SEAT_Z])
crr = np.hypot(col.vertices[:, 0], col.vertices[:, 1])
ck(crr.min() * 2 > DISP_ACTIVE_D - 0.01,
   'the collar never stands in front of a pixel',
   f'bore {2*crr.min():.2f} vs a {DISP_ACTIVE_D:.1f} active area')
ck(crr.min() > r_scr,
   'and the wood caps it, so it cannot come forward',
   f'collar bore r {crr.min():.2f} vs hole r {r_scr:.2f}: '
   f'{crr.min() - r_scr:.2f} mm of overhang')
ck(col.bounds[0][2] > Z_SEAT + DISP_T,
   'and it stops clear of the panel rather than resting on the glass',
   f'collar bottom z={col.bounds[0][2]:.2f}, panel front {Z_SEAT + DISP_T:.2f}')
base_c = trimesh.load(csg.part('mini-round-clock-base-60.stl'), process=False)
base_c.merge_vertices()
bv = (to_manifold(base_c) ^ to_manifold(col)).volume()
ck(bv < 1.0, 'and it drops into the base bore without fouling it',
   f'{bv:.3f} mm3')

print('\n3d. The OPEN-CENTRE pair -- 61.2 mm, over the housing instead of under it')
# Sam, 2026-09-18: "the updated SVG file with the larger circle in the middle."
# The other answer to the same clash: rather than cutting the housing down to
# pass under the wood, make the hole big enough to pass over it. Two things have
# to hold, and the second is the one that could quietly fail -- a hole grown far
# enough walks off its own seat and the face drops through.
for nm in ('face-60-wood-cut-open.svg', 'face-60-wood-cut-open-hours.svg'):
    sh, _, _ = load(nm)
    sc = [x for x in sh if x['layer'] == 'cut-screen']
    ck(len(sc) == 1, f'{nm}: one centre cut', f'{len(sc)}')
    rb = max(math.hypot(*p) for p in sc[0]['pts'])
    ck(2*rb - PLY_KERF > PLY_HOUSING_OD,
       f'   clears the {PLY_HOUSING_OD:.1f} mm housing, kerf included',
       f'{2*rb:.2f} bore, {2*rb - PLY_KERF - PLY_HOUSING_OD:+.2f} mm to spare')
    tk = [x for x in sh if x['layer'] == 'cut-ticks']
    ck(len(tk) == B.n, '   still sixty lines, still cuts', f'{len(tk)}')
    ck(rb < min(math.hypot(*p) for t in tk for p in t['pts']),
       '   and the bore does not eat into the innermost line',
       f'bore {rb:.2f}, nearest tick {min(math.hypot(*p) for t in tk for p in t["pts"]):.2f}')
# ...and it still lands on the base's collar. Booleaned at the seated height.
disc_open = (cyl(r_out, seat, seat + PLY_T, 256)
             - cyl(PLY_BORE_OPEN_R, seat - 1.0, seat + PLY_T + 1.0, 256))
t_open = to_manifold(base) ^ disc_open
ck(t_open.volume() > 0.5, 'the open-centre disc still lands on the collar',
   f'{t_open.volume():.2f} mm3 of contact film')
tro = np.hypot(csg.to_trimesh(t_open).vertices[:, 0],
               csg.to_trimesh(t_open).vertices[:, 1])
ck(tro.max() - tro.min() > 2.0,
   'on a real width of it, not an edge -- a bigger hole walks off its seat',
   f'seat r {tro.min():.2f}..{tro.max():.2f} = {tro.max()-tro.min():.2f} mm')
ck((to_manifold(base) ^ (cyl(r_out, seat + 0.02, seat + 0.02 + PLY_T, 256)
    - cyl(PLY_BORE_OPEN_R, seat - 1.0, seat + PLY_T + 1.0, 256))).volume() < 0.01,
   'and lifted clear, nothing is in its way either')

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

print('\n8b. The CUT-THROUGH pair, for the printed-plug build')
for nm, nwide in (('face-60-wood-cut.svg', 0), ('face-60-wood-cut-hours.svg', 12)):
    sh, _, _ = load(nm)
    tk = [x for x in sh if x['layer'] == 'cut-ticks']
    ck(len(tk) == B.n, f'{nm}: sixty lines, and they are CUTS not engraves',
       f'{len(tk)} cut-ticks')
    ck(all(x['fill'] in (None, 'none') for x in tk),
       '   none of them filled, or the laser rasters instead of cutting')
    ck(not [x for x in sh if str(x['layer']).startswith('engrave')],
       '   and nothing is left engraved')
    if nwide:
        w = [round(slot_wh(x['poly'])[0], 2) for x in tk]
        ck(w.count(round(PLY_HOUR_W, 2)) == nwide,
           f'   twelve widened to {PLY_HOUR_W:.2f}', f'{w.count(round(PLY_HOUR_W,2))}')
    # ORDER: every tick before the screen bore, and the outline dead last. A
    # disc with sixty through-slots in it is far more fragile than the engraved
    # one, and a piece that comes free early takes the gantry with it.
    order = [x['layer'] for x in sh]
    ck(order[-1] == 'cut-outline', '   the outline is the last cut in the file',
       f'last op is {order[-1]}')
    ck(max(i for i, l in enumerate(order) if l == 'cut-ticks')
       < order.index('cut-screen'),
       '   and every line is cut while the disc is still attached')

print('\n8c. The slot test -- the other half of the plug experiment')
sl, _, _ = load('face-60-slot-test.svg')
slots = [x for x in sl if x['layer'] == 'cut-slots']
ck(len(slots) == 6, 'six slots, one per test plug', f'{len(slots)}')
sw = sorted(round(slot_wh(x['poly'])[0], 2) for x in slots)
ck(set(sw) == {round(PLY_TICK_W, 2)},
   f'drawn at the SAME {PLY_TICK_W:.2f} as the face, so the kerf is the same kerf',
   f'widths {sorted(set(sw))}')
sl_len = sorted(round(slot_wh(x['poly'])[1], 1) for x in slots)
want_l = round((B.tick_ro - B.tick_ri) + PLY_TICK_W, 1)
ck(all(abs(v - want_l) < 1.1 for v in sl_len),
   'and at the real length, so a plug is tested over its whole run',
   f'lengths {sorted(set(sl_len))}')
ck(all(x['fill'] in (None, 'none') for x in slots),
   'they are cuts, not engraves')
lab = [x for x in sl if x['layer'] == 'engrave-labels']
ck(len(lab) > 0 and min(x['poly'].area for x in lab) > 0.5,
   'the numbers are engraved and every segment has area',
   f'{len(lab)} segments, smallest {min(x["poly"].area for x in lab):.2f} mm2')
order = [x['layer'] for x in sl]
ck(order[-1] == 'cut-outline', 'the outline is cut last',
   f'last op is {order[-1]}')
ck(max(i for i, l in enumerate(order) if l == 'engrave-labels')
   < min(i for i, l in enumerate(order) if l == 'cut-slots'),
   'and the numbers are engraved while the sheet is still whole')

print('\n9. The depth coupon')
cp, cw, chh = load('face-60-depth-test.svg')
patches = [s for s in cp if s['layer'].startswith('engrave-test-')]
labels = [s for s in cp if s['layer'] == 'engrave-labels']
ck(len(patches) >= 8, 'a pair of ticks at each setting', f'{len(patches)} patches')
cols = {s['fill'] for s in patches}
ck(len(cols) == len(patches)//2,
   'each setting in its own colour, so each can be given its own passes',
   f'{len(cols)} colours over {len(patches)} patches')
pw = sorted(round(slot_wh(s['poly'])[0], 2) for s in patches)
ck(set(pw) == {round(PLY_TICK_W, 2), round(PLY_HOUR_W, 2)},
   f'and each pair is a real {PLY_TICK_W:.2f} and {PLY_HOUR_W:.2f} mm line, not a swatch',
   f'widths {sorted(set(pw))}')
pl = {round(slot_wh(s['poly'])[1], 1) for s in patches}
want = round((B.tick_ro - B.tick_ri) + PLY_TICK_W, 1)
ck(all(abs(v - want) < 1.1 for v in pl),
   f'at the real {B.tick_ro - B.tick_ri:.1f} mm length, so the glow can be judged along it',
   f'lengths {sorted(pl)}')
ck(len(labels) > 0 and all(s['fill'] == '#000000' for s in labels),
   'the numerals are engraved in their own colour, at one constant depth',
   f'{len(labels)} segments')
# ...and they have to be SHAPES. The first version drew the three horizontal
# bars as zero-width rectangles and this test did not exist, so a coupon whose
# numerals were unreadable passed. A segment with no area is not a numeral.
seg_a = [s['poly'].area for s in labels]
ck(min(seg_a) > 0.5, 'and every segment of them has real area',
   f'smallest segment {min(seg_a):.2f} mm2, largest {max(seg_a):.2f}')
# the bare reference: one column with a numeral and no tick
def columns(shapes, gap=5.0):
    """Group shapes into columns by x. A seven-segment digit is SEVEN shapes
    at slightly different x, so counting distinct centroids counts segments and
    reports fifteen columns for six digits."""
    xs = sorted(sh['poly'].centroid.x for sh in shapes)
    cols, run = [], [xs[0]]
    for x in xs[1:]:
        if x - run[-1] <= gap:
            run.append(x)
        else:
            cols.append(run)
            run = [x]
    cols.append(run)
    return [sum(c)/len(c) for c in cols]
# 6.5 mm for the ticks. The two widths of one setting sit 5.2 apart and belong
# to the same column; the nearest ticks of ADJACENT settings are 13 - 5.2 = 7.8
# apart. So the gap has to fall between those two, and 8.0 merged the lot into
# one column and reported a coupon with a single setting on it.
xs_t = columns(patches, 6.5)
xs_l = columns(labels, 5.0)
bare = [x for x in xs_l if all(abs(x - t) > 5.0 for t in xs_t)]
ck(len(xs_l) == len(xs_t) + 1, 'a numeral under every setting, and one more',
   f'{len(xs_l)} numerals, {len(xs_t)} tick columns')
ck(len(bare) == 1, 'and that one is left bare, as the unlit reference',
   f'{len(bare)} bare column(s) of {len(xs_l)}')
# The size that matters is the CUT rectangle -- the bit of ply Sam ends up
# holding -- not the document, which carries a millimetre of margin all round.
# Reporting the document read 90 x 54 against a part that is 88 x 52.5, and a
# check whose number disagrees with the drawing's own caption is a check nobody
# trusts twice.
cut = [s for s in cp if s['layer'] == 'cut-outline']
ck(len(cut) == 1, 'one cut outline, so it comes off the bed as one piece',
   f'{len(cut)} cut path(s)')
x0, y0, x1, y1 = cut[0]['poly'].bounds
kw, kh = x1 - x0, y1 - y0
ck(max(kw, kh) < 120.0, 'the coupon is small', f'{kw:.1f} x {kh:.1f} mm cut')
ck(kw < cw and kh < chh,
   'and the cut sits inside the sheet with margin, not on its edge',
   f'cut {kw:.1f} x {kh:.1f} in a {cw:.1f} x {chh:.1f} document')

print()
if FAIL:
    print(f'CHECK 11: {len(FAIL)} FAILURES')
    [print('   -', f) for f in FAIL]
    sys.exit(1)
print('CHECK 11: the face fits the bore, lands on the collar, and its sixty '
      'lines sit over sixty lit pockets')
