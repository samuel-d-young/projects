#!/usr/bin/env python3
"""PASS 2 of 3 — fits and clearances. Does the hardware physically go in?"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, trimesh
import csg
from csg import box_lwh, cyl, wedge, to_manifold, to_trimesh
from params import *
from params import max_battery, fits
from build_v2 import load_sams_base

FAIL=[]
def ck(cond, msg, detail=''):
    print(f'  [{"ok  " if cond else "FAIL"}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

def load(f):
    m = trimesh.load(f, process=False); m.merge_vertices(); return m

BASE = load('mini-round-clock-base-v2.stl')
HB   = load('mini-round-clock-rearhousing-battery.stl')
HS   = load('mini-round-clock-rearhousing-slim.stl')
CR   = load('mini-round-clock-battery-shim-x2.stl')
mBASE, mHB, mHS, mCR = map(to_manifold, (BASE, HB, HS, CR))

BIG = 200.0
def half(z0, z1):
    return box_lwh(-BIG, BIG, -BIG, BIG, z0, z1)

print("\n1. Sam's geometry above z = 0 is untouched except where it must be")
sam = load_sams_base()
up = half(0.001, 60.0)
samU, newU = sam ^ up, mBASE ^ up
removed = (samU - newU)
added   = (newU - samU)
print(f'         removed {removed.volume():8.2f} mm3   added {added.volume():8.2f} mm3')

# everything removed must be inside the four screw pilots
pilots = None
for a_ in SCREW_ANG:
    x, y = SCREW_R*math.cos(math.radians(a_)), SCREW_R*math.sin(math.radians(a_))
    c = cyl(SCREW_PILOT/2 + 0.05, -1, Z_BACK+SCREW_DEPTH+0.05, 48, centre=(x,y))
    pilots = c if pilots is None else pilots + c
ck((removed - pilots).volume() < 0.05,
   'the only material removed above z=0 is the four screw pilots',
   f'{(removed - pilots).volume():.4f} mm3 outside them')

# everything added must be inside the four board-locating posts, or inside the
# tab-slot walls. Not a blanket allowance: the walls have to be where they are
# supposed to be, which is outboard of the tab, inside the tab window, and
# stopping at the ring pocket floor.
c2 = BOARD_CLR
allowed = None
for sx, sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
    px = (BOARD_X1 + c2 - 3.0) if sx > 0 else (BOARD_X0 - c2 + 3.0)
    py = sy * (BOARD_W/2 + c2 + 1.4)
    c = cyl(1.60 + 0.05, -1, Z_BACK + POST_H + 0.05, 40, centre=(px, py))
    allowed = c if allowed is None else allowed + c
# the walls' own construction envelope. They deliberately over-reach past the
# tab window, both radially and angularly, into material that is already solid,
# so the union has something to merge with instead of butting onto a face.
wall_env = (wedge(TAB_WALL_RI - 0.10, TAB_WALL_RO + 0.10,
                  Z_BACK - 0.05, TAB_WALL_TOP + 0.10,
                  -TAB_WALL_AHALF - 0.2, TAB_WALL_AHALF + 0.2)
            - box_lwh(-1.0, 60.0, -TAB_SLOT_HW, TAB_SLOT_HW,
                      Z_BACK - 1.0, TAB_CHAMF_Z))
allowed = allowed + wall_env
stray = (added - allowed).volume()
ck(stray < 0.05,
   'material added above z=0 is only the board posts and the tab-slot walls',
   f'{stray:.3f} mm3 outside either')
walls_v = (added - (added - wall_env)).volume()
ck(walls_v > 2000, 'the tab-slot walls are actually there', f'{walls_v:.0f} mm3')

print('\n2. The S3 board goes in and is caught by the end ledges')
BX0, BX1, BY = BOARD_X0, BOARD_X1, BOARD_W/2
Z_LEDGE = Z_BACK - 0.80
board = box_lwh(BX0, BX1, -BY, BY, Z_LEDGE, Z_LEDGE + BOARD_T)
ck((mBASE ^ board).volume() < 1e-6, 'PCB does not intersect the base', f'{(mBASE ^ board).volume():.4f} mm3')
tall = box_lwh(BX0, BX1, -BY, BY, Z_LEDGE + BOARD_T, Z_LEDGE + BOARD_T + BOARD_TALL)
ck((mBASE ^ tall).volume() < 1e-6, 'components on top clear the base too', f'{(mBASE ^ tall).volume():.4f} mm3')
# ledge really is under the board at both ends
for nm, x in [('-x end (USB-C)', BX0 + 1.0), ('+x end', BX1 - 1.0)]:
    probe = box_lwh(x-0.5, x+0.5, -BY+0.5, BY-0.5, Z_DECK+0.1, Z_LEDGE-0.05)
    v = (mBASE ^ probe).volume()
    ck(v > 0.1, f'ledge present under the {nm}', f'{v:.3f} mm3')
# and NOT under the long sides, where the pin rows are
mid = box_lwh(0.0, 4.0, -BY+0.2, BY-0.2, Z_DECK+0.1, Z_LEDGE-0.05)
ck((mBASE ^ mid).volume() < 1e-6, 'no ledge under the long sides (clears pin rows)')
gap = BOARD_CLR
ck(abs(gap-0.45) < 1e-9, 'clearance per side', f'{gap:.2f} mm')

print('\n3. The board clears everything Sam already has in there')
top = Z_LEDGE + BOARD_T + BOARD_TALL
ck(top < Z_SEAT, 'board top is below the display seat', f'{top:.2f} < {Z_SEAT:.2f}  ({Z_SEAT-top:.2f} mm)')
TAB_Z0 = Z_SEAT                       # tab is the module's own PCB, at its back
ck(top < TAB_Z0, 'board top is below the display tab', f'{top:.2f} < {TAB_Z0:.2f}  ({TAB_Z0-top:.2f} mm)')
ck(top < Z_RING_FLOOR, 'board top is below the ring pocket floor', f'{top:.2f} < {Z_RING_FLOOR:.2f}')
for nm, x, y in [('-x corner', BOARD_X0, BOARD_W/2), ('+x corner', BOARD_X1, BOARD_W/2)]:
    r = math.hypot(x, y)
    lim = R_BORE if x < 0 else R_TAB
    ck(r < lim, f'{nm} inside the {"bore" if x<0 else "tab window"}', f'r={r:.2f} < {lim:.2f}')

print('\n4. The two parts mate, and only mate')
for nm, m in [('battery', mHB), ('slim', mHS)]:
    v = (mBASE ^ m).volume()
    ck(v < 1e-6, f'base and the {nm} housing do not interfere', f'{v:.6f} mm3')
    tb = to_trimesh(m).bounds
    ck(abs(tb[1][2] - Z_DECK) < 1e-3, f'{nm} housing front face meets the deck at z={Z_DECK}', f'{tb[1][2]:.3f}')
    ck(abs(tb[1][0] - R_BODY) < 0.05, f'{nm} housing OD matches the base', f'{2*tb[1][0]:.2f} vs {2*R_BODY:.2f} mm')

print('\n5. Screws line up and have material to bite into')
for a_ in SCREW_ANG:
    x, y = SCREW_R*math.cos(math.radians(a_)), SCREW_R*math.sin(math.radians(a_))
    # an actual M3 shank is 3.0 mm; test with 3.05 so we are not comparing
    # two coincident surfaces
    shank = cyl(3.05/2, Z_DECK-40, Z_DECK, 32, centre=(x,y))
    ck((mHB ^ shank).volume() < 1e-6, f'{a_:5.0f} deg: an M3 shank passes through the housing',
       f'{(mHB ^ shank).volume():.5f} mm3')
    # the pilot is deliberately UNDERSIZE so the screw taps it: check it is bored,
    # not that it is empty at full diameter
    core = cyl(SCREW_PILOT/2 - 0.15, Z_DECK, Z_BACK+SCREW_DEPTH-0.2, 32, centre=(x,y))
    ck((mBASE ^ core).volume() < 1e-6, f'{a_:5.0f} deg: pilot is bored in the base',
       f'{(mBASE ^ core).volume():.5f} mm3')
    # is there PLA around the pilot to thread into?
    ring = (cyl(SCREW_PILOT/2+1.6, Z_DECK, Z_BACK+SCREW_DEPTH, 40, centre=(x,y))
            - cyl(SCREW_PILOT/2, Z_DECK-1, Z_BACK+SCREW_DEPTH+1, 40, centre=(x,y)))
    v = (mBASE ^ ring).volume(); full = ring.volume()
    ck(v/full > 0.85, f'{a_:5.0f} deg: solid material around the pilot', f'{100*v/full:.1f}% of the collar')

print('\n6. The wall hanger')
head = cyl(8.0/2, -60, 60, 48, centre=(HANG_R-KEY_DROP, 0))
ck((mHB ^ head).volume() < 1e-6, 'an 8.0 mm screw head passes the entry hole')
shank = cyl(4.0/2, -60, 60, 32, centre=(HANG_R, 0))
ck((mHB ^ shank).volume() < 1e-6, 'a 4.0 mm shank sits in the slot')
head_at_slot = cyl(8.0/2, Z_REAR-1, Z_REAR+PLATE_T-0.2, 48, centre=(HANG_R, 0))
v = (mHB ^ head_at_slot).volume()
ck(v > 20.0, 'the head is CAPTURED at the top of the slot (that is what holds it up)', f'{v:.1f} mm3 of overlap')
# The real criterion is not "drop >= head diameter". It is that the shank,
# once dropped, cannot get back through the entry hole without lifting the
# clock -- and how far it must be lifted.
min_drop = (KEY_ENTRY_D + KEY_SLOT_W)/2
ck(KEY_DROP > min_drop, 'drop exceeds the geometric minimum',
   f'{KEY_DROP:.2f} > {min_drop:.2f} mm')
lift = KEY_DROP - (KEY_ENTRY_D - 8.0)/2      # head must re-centre on the entry hole
ck(lift >= 5.0, 'clock must be lifted this far to come off the screw', f'{lift:.2f} mm')

print('\n7. Battery pocket and cradle')
Z0b = Z_DECK - (PLATE_T + POCKET_BATTERY)
ZF  = Z0b + PLATE_T                      # pocket floor
# lifted 0.01 off the floor: the battery rests ON it, and testing two
# coincident planes just measures floating point
bat = box_lwh(BAT_CX-BAT_L/2, BAT_CX+BAT_L/2, -BAT_W/2, BAT_W/2, ZF+0.01, ZF+BAT_T)
ck((mHB ^ bat).volume() < 1e-6, f'the {BAT_L}x{BAT_W}x{BAT_T} battery fits the pocket',
   f'{(mHB ^ bat).volume():.4f} mm3')
batL = bat.translate([0, 0, -ZF - 0.01])
for sy, lbl in ((+1, '+y'), (-1, '-y')):
    shp = mCR if sy > 0 else mCR.mirror([0.0, 1.0, 0.0])
    ck((shp ^ batL).volume() < 1e-6, f'shim on the {lbl} side clears the battery',
       f'{(shp ^ batL).volume():.4f} mm3')
    # and stays inside the pocket
    sv = to_trimesh(shp).vertices
    ck(np.hypot(sv[:,0], sv[:,1]).max() <= R_INNER, f'shim on the {lbl} side fits the pocket',
       f'max r = {np.hypot(sv[:,0],sv[:,1]).max():.2f}')
# the wall screw's head sweeps this zone as the clock drops onto it
headzone = box_lwh(HANG_R-KEY_DROP-4.5, HANG_R+4.5, -4.5, 4.5, ZF-1.0, ZF+3.2)
ck((bat ^ headzone).volume() < 1e-6, 'the battery clears the hanging screw head',
   f'{(bat ^ headzone).volume():.3f} mm3')
ck((mCR ^ headzone).volume() < 1e-6, 'the shim clears it too',
   f'{(mCR ^ headzone).volume():.3f} mm3')
# and the cradle stays inside the pocket wall
cb = to_trimesh(mCR).vertices
ck(np.hypot(cb[:,0], cb[:,1]).max() <= R_INNER + 1e-6, 'shim stays inside the pocket wall',
   f'max r = {np.hypot(cb[:,0],cb[:,1]).max():.3f} vs {R_INNER:.3f}')
ck(math.hypot(BAT_L, BAT_W) < 2*R_INNER, 'battery diagonal fits the interior circle',
   f'{math.hypot(BAT_L,BAT_W):.1f} < {2*R_INNER:.1f} mm')
for sx in (-1,1):
    for sy in (-1,1):
        r = math.hypot(BAT_CX + sx*BAT_L/2, sy*BAT_W/2)
        ck(r < R_INNER, f'battery corner ({sx:+d},{sy:+d}) inside the wall', f'r={r:.2f} < {R_INNER:.2f}')
ck(POCKET_BATTERY - BAT_T >= 1.4, 'air above the battery', f'{POCKET_BATTERY-BAT_T:.2f} mm')

# what this pocket will actually take, and how the real candidates score.
# Sharp-cornered is the conservative reading; every retail bank is radiused,
# and 2 mm of corner radius is worth ~0.7 mm of length here.
print('\n   maximum battery, by width:')
print(f'      {"width":>6s}  {"sharp":>7s}  {"r=2mm":>7s}   (x {POCKET_BATTERY-1.4:.1f} mm thick)')
for W in (36, 38, 40, 45, 50, 55, 60):
    print(f'      {W:6.1f}  {max_battery(W, 0.0):7.1f}  {max_battery(W, 2.0):7.1f}')
print('\n   the candidates that were verified:')
CANDIDATES = [
    ('Anker Nano A1653          A$49  Scorptec',      76.96, 36.83, 24.89),
    ('Baseus Compact Type-C 5K  A$46  baseus.com.au', 80.00, 40.20, 25.60),
    ('UGREEN PB503              no AU stock',         79.00, 38.00, 26.00),
    ('Anker PowerCore 10000',                         92.00, 60.00, 22.00),
    ('Anker Nano A1259 10000    wrong part',         103.90, 52.30, 25.90),
]
for name, L, W, T in CANDIDATES:
    ok, why = fits(L, W, T)
    print(f'      {"FITS" if ok else "no  "}  {name:44s} {L:5.1f}x{W:4.1f}x{T:4.1f}  {why}')
ck(fits(BAT_L, BAT_W, BAT_T)[0], 'the battery the shim is cut for fits',
   fits(BAT_L, BAT_W, BAT_T)[1])

print('\n8. Room for the battery\'s own connectors')
# A 77 mm bank in a 102 mm circle leaves ~25 mm split between its two ends, and
# the -x end is spoken for. Which way round the battery goes in is therefore not
# a free choice, and it is the kind of thing that ruins an evening at the bench.
def wall_x(y): return math.sqrt(max(R_INNER**2 - y**2, 0.0))
end_neg = wall_x(0) - (BAT_L/2 - BAT_CX)
end_pos = wall_x(0) - (BAT_CX + BAT_L/2)
print(f'         -x (6 o\'clock) end: {end_neg:5.2f} mm     +x (12 o\'clock) end: {end_pos:5.2f} mm')
ck(end_neg < 12.0, 'the 6 o\'clock end has NO room for a plug (so the ports must face 12)',
   f'{end_neg:.2f} mm')
# off the screw head's centreline, at y = 6..18, how much is there?
PLUG_RA = 15.0                      # a slim right-angle USB-C plug, mating face to cable
worst = min(wall_x(y) - (BAT_CX + BAT_L/2) for y in (6.0, 12.0, 18.0))
ck(worst >= PLUG_RA, f'a {PLUG_RA:.0f} mm right-angle plug fits at 12 o\'clock, off centre',
   f'{worst:.2f} mm at y = 6..18')
side = min(math.sqrt(max(R_INNER**2 - x**2, 0.0)) - BAT_W/2 for x in (-30, -15, 0, 15))
ck(side >= 12.0, 'room beside the battery to route the mains lead up to it',
   f'{side:.2f} mm each side')
ck(POCKET_BATTERY - BAT_T >= 1.4, 'air above the battery', f'{POCKET_BATTERY-BAT_T:.2f} mm')

print('\n9. Cable exit takes a USB-C plug')
plug = box_lwh(-70, -R_INNER+3.0, -9.0/2, 9.0/2, ZF+2.0, ZF+2.0+4.5)
ck((mHB ^ plug).volume() < 1e-6, 'a 9.0 x 4.5 mm USB-C plug body passes the exit',
   f'{(mHB ^ plug).volume():.4f} mm3')

print('\n10. Will the hanger hold it?')
PLA_RHO, PETG_RHO = 1.24e-3, 1.27e-3          # g/mm3
parts_g = {
    'base':          to_trimesh(mBASE).volume * PLA_RHO,
    'rear housing':  to_trimesh(mHB).volume * PETG_RHO,
    'shims x2':      2 * to_trimesh(mCR).volume * PLA_RHO,
}
fitted_g = {'battery (Anker A1653)': 100.0, 'display module': 25.0,
            'LED ring': 12.0, 'S3 devkit': 9.0, 'plywood face': 16.0,
            'wiring + screws': 15.0}
total = sum(parts_g.values()) + sum(fitted_g.values())
for k, v in {**parts_g, **fitted_g}.items():
    print(f'         {k:24s} {v:6.1f} g')
print(f'         {"TOTAL":24s} {total:6.1f} g')
W = total * 9.81e-3                            # newtons
# the shank bears on the slot walls through the plate's thickness
bearing = KEY_SLOT_W * PLATE_T
sigma = W / bearing
ck(sigma < 5.0, 'bearing stress on the keyhole slot is nowhere near PLA yield',
   f'{sigma:.3f} MPa on {bearing:.1f} mm2, against ~50 MPa')
# and the plate must not tear out between the slot and the outer wall
lig = R_INNER - (HANG_R + KEY_SLOT_W/2)
ck(lig >= 1.5, 'ligament between the slot and the outer wall', f'{lig:.2f} mm')
shear = W / (2 * lig * PLATE_T)
ck(shear < 5.0, 'shear on that ligament', f'{shear:.3f} MPa')
ck(total < 600, 'total hanging mass is sane for one wall screw', f'{total:.0f} g')

print('\n11. Overall stack')
tb = to_trimesh(mBASE).bounds; hb = to_trimesh(mHB).bounds; hs = to_trimesh(mHS).bounds
ck(True, 'clock depth, battery variant', f'{tb[1][2]-hb[0][2]:.2f} mm')
ck(True, 'clock depth, slim variant', f'{tb[1][2]-hs[0][2]:.2f} mm')
ck(tb[1][2]-hb[0][2] < 60.0, 'battery variant stays under 60 mm deep')

print()
if FAIL:
    print(f'PASS 2: {len(FAIL)} FAILURES'); [print('   -',f) for f in FAIL]; sys.exit(1)
print('PASS 2: every fit and clearance check holds')
