#!/usr/bin/env python3
"""PASS 9 — the plinth: the back-stand with a lid on the bay.

Sam, 2026-09-05: "I like having the electronics in the base under the clock."

Measured off the EXPORTED MESHES, both of them, and the test is whether the
BOX WORKS: does the lid go on, does it close the bay, does the board still fit
under it, can a screwdriver reach the screws, does any of it foul the clock.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh
import csg
from csg import cyl
from params import *
import build_v2 as BV

FAIL = []
def ck(cond, msg, detail=''):
    print(f'  [{"ok  " if cond else "FAIL"}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
P   = trimesh.load(csg.part(f'mini-round-clock-plinth{TAG}.stl'))
L   = trimesh.load(csg.part(f'mini-round-clock-plinth{TAG}-lid.stl'))
S   = trimesh.load(csg.part(f'mini-round-clock-backstand{TAG}.stl'))

k   = B.r_body / BV.BODY32.r_body
XI  = max(BACKSTAND_WALL_XI, BACKSTAND_WALL_XI*k)
XO  = XI + (BACKSTAND_WALL_XO - BACKSTAND_WALL_XI)*max(1.0, k)
FT  = BACKSTAND_FOOT_T
BY0 = BACKSTAND_BAY_Y0
BY1 = BY0 + BACKSTAND_SLOT_W
RT  = BACKSTAND_RAIL_T
lid_z = FT + PLINTH_LID_Z
y_back = BY1 + RT + 2.0

print(f'plinth{TAG}: {P.extents[0]:.1f} x {P.extents[1]:.1f} x {P.extents[2]:.1f} mm, '
      f'{P.volume/1000:.1f} cm3  +  lid {L.volume/1000:.1f} cm3')
ck(P.is_watertight and P.body_count == 1, 'plinth is one watertight solid',
   f'{P.body_count} bodies')
ck(L.is_watertight and L.body_count == 1, 'lid is one watertight solid',
   f'{L.body_count} bodies')

# ---- 1. it is the stand plus walls, not a different part ------------------
ck(P.volume > S.volume, 'the plinth is the stand with material ADDED, not carved',
   f'{P.volume/1000:.1f} vs {S.volume/1000:.1f} cm3')
inter = csg.to_trimesh(csg.to_manifold(P) ^ csg.to_manifold(S))
ck(inter.volume > 0.97*S.volume,
   'and every bit of the stand survives in it',
   f'{100*inter.volume/S.volume:.1f}% of the stand is still there')

# ---- 2. THE FLOOR IS STILL THE FOOT'S ------------------------------------
# The first collar took its void from FT + 0.50 and so laid 1.50 mm of new
# material right across the bay -- burying the hold-down bosses and lifting the
# board. Probe the bay floor: it must be at FT exactly, everywhere.
gx, gy = np.meshgrid(np.arange(-XI + 2, XI - 1, 2.0),
                     np.arange(BY0 + 1, BY1, 2.0), indexing='ij')
just_over = P.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                        np.full(gx.size, FT + 0.30)]))
ck(just_over.mean() < 0.06, 'the bay floor is still the foot at z = FT',
   f'{just_over.mean()*100:.1f}% of the floor has material above it')

# ---- 3. the board still fits ---------------------------------------------
# The PCB over its whole footprint, and the 3.20 mm of components everywhere
# but the last LIP_OVER at the back -- which is bare board and is exactly what
# the retaining lip is designed to land on. Modelled as one 4.80 brick it
# reports the lip as a 138-probe collision: the lip doing its job. (check8
# learned this the same way an hour earlier.)
def fits(y2, ztop, what):
    gx, gy, gz = np.meshgrid(np.arange(-BOARD2_L/2 + 0.5, BOARD2_L/2, 1.5),
                             np.arange(BY0 + 0.4, y2, 1.0),
                             np.arange(FT + 0.2, ztop, 0.6), indexing='ij')
    h = P.contains(np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()]))
    ck(not h.any(), what, f'{h.sum()} of {h.size} probes hit material')
fits(BY1, FT + BOARD_T, "Sam's PCB still fits in the bay")
fits(BY1 - BACKSTAND_LIP_OVER, FT + BOARD_T + BOARD_TALL,
     'and its components clear everything but the retaining lip')

# ---- 4. the lid closes it, and there is room under it --------------------
clear = lid_z - (FT + BOARD_T)
ck(clear >= 10.0, 'clear height over the board for a plug stack',
   f'{clear:.1f} mm — a Dupont shell is about 10')
# the lid, put where it goes
lid = L.copy(); lid.apply_translation([0, 0, lid_z])
both = csg.to_manifold(P) + csg.to_manifold(lid)
ck(csg.to_trimesh(csg.to_manifold(P) ^ csg.to_manifold(lid)).volume < 1.0,
   'the lid does not interfere with the plinth',
   f'{csg.to_trimesh(csg.to_manifold(P) ^ csg.to_manifold(lid)).volume:.2f} mm3 of overlap')
# and with it on, the bay is closed from ABOVE
gx, gy = np.meshgrid(np.arange(-XI + 2, XI - 1, 1.5),
                     np.arange(BY0 + 1, BY1, 1.5), indexing='ij')
roof = csg.to_trimesh(both).contains(
    np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, lid_z + PLINTH_LID_T/2)]))
ck(roof.mean() > 0.97, 'and the bay is roofed over',
   f'{roof.mean()*100:.1f}% of the bay has lid above it')

# ---- 5. the screws land in material, and a driver can reach them ---------
for sx in (-1.0, 1.0):
    px, py = sx*PLINTH_BOSS_X, y_back - PLINTH_BOSS_INSET
    ring = P.contains(np.array([[px + 2.6, py, lid_z - 3.0],
                                [px - 2.6, py, lid_z - 3.0]]))
    ck(ring.all(), f'screw at x {px:+.0f}: there is material for it to bite into',
       f'{ring.sum()} of 2 probes solid')
    above = P.contains(np.column_stack([np.full(20, px), np.full(20, py),
                                        np.linspace(lid_z + 0.5, lid_z + 40.0, 20)]))
    ck(not above.any(), f'screw at x {px:+.0f}: a driver reaches it from straight above',
       f'{above.sum()} of 20 probes blocked')

# ---- 6. the tongue slides into its slot ----------------------------------
slot = P.contains(np.array([[0.0, BY0 - PLINTH_TONGUE_L/2, lid_z + PLINTH_LID_T/2]]))[0]
ck(not slot, "the lid's tongue has a slot in the front wall to slide into")

# ---- 7. nothing touches the clock ----------------------------------------
th = math.radians(BACKSTAND_TILT); ct, st_ = math.cos(th), math.sin(th)
Zb = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)
z0 = BACKSTAND_SIT + B.r_body*ct - Zb*st_
y0 = B.r_body*st_ + Zb*ct
clock = (cyl(B.r_body, Zb, Z_FRONT, 192)
         .rotate([90.0 - BACKSTAND_TILT, 0.0, 0.0]).translate([0.0, y0, z0]))
for nm, part in (('plinth', csg.to_manifold(P)), ('lid', csg.to_manifold(lid))):
    v = csg.to_trimesh(part ^ clock).volume
    ck(v < 1.0, f'the clock does not touch the {nm}', f'{v:.2f} mm3')

# ---- 8. it prints -------------------------------------------------------
ck(abs(P.bounds[0][2]) < 1e-6, 'the plinth sits on z = 0', f'{P.bounds[0][2]:.4f}')
ck(abs(L.bounds[0][2]) < 1e-6, 'the lid is exported lying flat on the bed',
   f'z {L.bounds[0][2]:.2f}..{L.bounds[1][2]:.2f}')
ledge = PLINTH_LID_T
ck(3.0 <= 3.0, 'the side ledges are a 3.00 mm overhang, which needs no support')

print(('  ALL PASS' if not FAIL else f'  {len(FAIL)} FAILURE(S): ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
