#!/usr/bin/env python3
"""PASS 7 — the back-stand.

Everything here is measured off the EXPORTED MESH, not recomputed from the
parameters. check6 was written the other way round and gave 21 failures, 6 of
them false, because it re-derived the tray from its own copy of the design and
then disagreed with the design. A checker that recomputes the part is not
checking the part.
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
B   = {'-32': BV.BODY32, '-60': BV.BODY60, '': BV.BODY24}[TAG]
FN  = f'mini-round-clock-backstand{TAG}.stl'
m   = trimesh.load(FN)
lo, hi = m.bounds

print(f'{FN}: {hi[0]-lo[0]:.2f} x {hi[1]-lo[1]:.2f} x {hi[2]-lo[2]:.2f} mm, '
      f'{m.volume/1000:.1f} cm3')

# ---- 1. one solid, sitting on the bed --------------------------------------
ck(m.is_watertight, 'watertight')
ck(m.body_count == 1, 'one solid', f'{m.body_count}')
ck(abs(lo[2]) < 1e-6, 'sits on z = 0', f'{lo[2]:.4f}')
sb   = trimesh.load(f'mini-round-clock-standbox{TAG}.stl')
tray = trimesh.load(f'mini-round-clock-standbox-tray{TAG}.stl')
was  = sb.volume + tray.volume
ck(m.volume < 0.40 * was, 'less than 40% of the stand-box it replaces',
   f'{m.volume/1000:.1f} vs {was/1000:.1f} cm3, in one part not two')

# ---- 2. the clock ----------------------------------------------------------
# The clock as a solid, in the same desk frame the part was built in. Built
# here from the SAME transform the part used, because that is the interface
# being checked -- but at ZERO clearance, so any contact at all is a failure.
th = math.radians(BACKSTAND_TILT)
ct, st_ = math.cos(th), math.sin(th)
Zb = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)
Zf = Z_FRONT
z0 = BACKSTAND_SIT + B.r_body*ct - Zb*st_
y0 = B.r_body*st_ + Zb*ct
tt   = math.tan(th)
back = lambda z: y0 + tt*(z - z0) - Zb/ct     # the clock's back face, vs height
clock = (cyl(B.r_body, Zb, Zf, 192)
         .rotate([90.0 - BACKSTAND_TILT, 0.0, 0.0]).translate([0.0, y0, z0]))
part  = csg.to_manifold(m)
hit   = csg.to_trimesh(part ^ clock)
ck(hit.volume < 1.0, 'the clock does not touch the stand anywhere',
   f'overlap {hit.volume:.3f} mm3')

cl = csg.to_trimesh(clock)
ck(abs(cl.bounds[0][2] - BACKSTAND_SIT) < 0.02, 'the clock sits at the design height',
   f'lowest point z = {cl.bounds[0][2]:.2f}')

# how deep the clock beds into the foot: the trench floor is at SIT, the foot's
# top face at FOOT_T, and the clock has to be held by more than a lip
bed = BACKSTAND_FOOT_T - cl.bounds[0][2]
ck(bed >= 3.0, 'the clock beds at least 3 mm into the foot', f'{bed:.2f} mm')

# and the buttresses have to reach up the clock's back, not just poke it
ck(hi[2] >= 0.30 * (cl.bounds[1][2] - cl.bounds[0][2]),
   'the back support reaches at least 30% of the clock height',
   f'{hi[2]:.1f} of {cl.bounds[1][2]-cl.bounds[0][2]:.1f} mm')

# ---- 3. the board slot, measured -------------------------------------------
# Sweep a ray across the bay at the height of the board's edge and read the
# free span in y off the mesh.
zprobe = BACKSTAND_FOOT_T + BACKSTAND_POST_H + BOARD_T/2.0
# x = 20, NOT x = 0: the cable gate takes the middle out of the front rail, so
# a probe down the centreline reads the gate, not the slot.
XPROBE = BACKSTAND_CABLE_HW + 11.0
ys = np.arange(0.0, hi[1], 0.02)
inside = m.contains(np.column_stack([np.full_like(ys, XPROBE), ys, np.full_like(ys, zprobe)]))
free, runs, cur = [], [], None
for y, ins in zip(ys, inside):
    if not ins:
        cur = y if cur is None else cur
    elif cur is not None:
        runs.append((cur, y)); cur = None
if cur is not None: runs.append((cur, ys[-1]))
runs = [r for r in runs if r[1] - r[0] > 5.0]
# The run that matters is the one the board goes in. There is a second open run
# in front of the front rail -- that is the trench and the cable channel, not a
# fault -- so pick by position, not by count.
mid = BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W/2.0
bay = [r for r in runs if r[0] < mid < r[1]]
ck(len(bay) == 1, 'the bay is one open channel at board height',
   f'{[f"{a:.2f}..{b:.2f}" for a, b in runs]}')
if bay:
    runs = bay
    w = runs[0][1] - runs[0][0]
    ck(abs(w - BACKSTAND_SLOT_W) < 0.10, 'the slot is the width it was asked for',
       f'{w:.2f} vs {BACKSTAND_SLOT_W:.2f}')
    ck(w - BOARD2_W >= 0.20, "and it clears Sam's board",
       f'{w - BOARD2_W:.2f} mm total, {(w-BOARD2_W)/2:.2f} a side')
    ck(w - BOARD2_W - FDM_SLOT_UNDER >= 0.10,
       'and still clears it if the print loses the worst case',
       f'{w - BOARD2_W - FDM_SLOT_UNDER:.2f} mm total')

# ---- 4. the board fits along its length, and can be lifted out -------------
xs = np.arange(-hi[0]-1.0, hi[0]+1.0, 0.05)
ymid = BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W/2.0
ins = m.contains(np.column_stack([xs, np.full_like(xs, ymid), np.full_like(xs, zprobe)]))
clear = xs[~ins]
ck(clear.max() - clear.min() >= BOARD2_L + 1.0,
   'the bay is longer than the board', f'{clear.max()-clear.min():.2f} vs {BOARD2_L:.2f}')

# nothing over the board except the retaining lip: probe the whole board
# footprint just above its top face
gx, gy = np.meshgrid(np.arange(-BOARD2_L/2+0.5, BOARD2_L/2, 1.0),
                     np.arange(BACKSTAND_BAY_Y0+0.5, BACKSTAND_BAY_Y0+BACKSTAND_SLOT_W, 0.5))
ztop = BACKSTAND_FOOT_T + BACKSTAND_POST_H + BOARD2_H + 0.5
over = m.contains(np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, ztop)]))
ck(not over.any(), 'nothing closes over the board -- the leads come off the top',
   f'{over.sum()} of {over.size} probes blocked')

# the lip, and only the lip, over the PCB's top face
zlip = BACKSTAND_FOOT_T + BACKSTAND_POST_H + BOARD_T + BACKSTAND_LIP_GAP + BACKSTAND_LIP_T/2
lipy = np.arange(BACKSTAND_BAY_Y0, BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W, 0.05)
# and x = 12 for the lip: inside its +/-18 span, outside the cable gate's +/-9
XLIP = 12.0
lip_in = m.contains(np.column_stack([np.full_like(lipy, XLIP), lipy, np.full_like(lipy, zlip)]))
reach = (lipy[lip_in].max() - lipy[lip_in].min()) if lip_in.any() else 0.0
ck(lip_in.any(), 'there is a lip holding the board down')
ck(reach <= 2.50, 'and it is a ledge, not a bridge (check3 allows 2.50)',
   f'{reach:.2f} mm')

# ---- 5. the cable route ----------------------------------------------------
# a continuous open path at the foot's top, from under the clock back to the bay
# The trench at this height is a LENS, not the full 34 mm the clock is thick:
# the rim is a curve and it is only a few mm above its lowest point here. So the
# test is connectivity, not "everything from the clock's front edge is open" --
# one unbroken open run has to contain both a point inside the trench and a
# point inside the bay.
zc = BACKSTAND_FOOT_T - BACKSTAND_CABLE_D/2.0
cy = np.arange(-40.0, BACKSTAND_BAY_Y0 + 6.0, 0.10)
blocked = m.contains(np.column_stack([np.zeros_like(cy), cy, np.full_like(cy, zc)]))
open_runs, cur = [], None
for y, b in zip(cy, blocked):
    if not b: cur = y if cur is None else cur
    elif cur is not None: open_runs.append((cur, y)); cur = None
if cur is not None: open_runs.append((cur, cy[-1]))
trench_y = back(zc) - 1.0                    # just inside the trench
gate_y   = BACKSTAND_BAY_Y0 - 1.0            # inside the gate, at the front rail
joined = [r for r in open_runs if r[0] <= trench_y and r[1] >= gate_y]
ck(bool(joined), 'the trench and the cable gate are one unbroken run',
   f'runs {[f"{a:.1f}..{b:.1f}" for a, b in open_runs if b - a > 1.0]}, '
   f'need {trench_y:.1f} to {gate_y:.1f}')
# and the gate has to open UPWARDS into the bay, over the front rail
# the front rail's height is derived in the builder now, so derive it here too
RAIL_H = BACKSTAND_POST_H + BOARD_T + BACKSTAND_RAIL_OVER
zs = np.arange(zc, BACKSTAND_FOOT_T + RAIL_H + 0.5, 0.10)
up = m.contains(np.column_stack([np.zeros_like(zs), np.full_like(zs, gate_y), zs]))
ck(not up.any(), 'and the gate opens upward into the bay, clear of the front rail',
   f'{up.sum()} of {up.size} probes blocked')

# and out through the buttress, for the USB-C
wx = np.arange(hi[0] - 20.0, hi[0] + 1.0, 0.05)
wz = BACKSTAND_FOOT_T + BACKSTAND_POST_H + 3.0
wy = (BACKSTAND_WIN_Y0 + BACKSTAND_WIN_Y1)/2.0
wins = m.contains(np.column_stack([wx, np.full_like(wx, wy), np.full_like(wx, wz)]))
ck(not wins.any(), 'the window goes right through the buttress, for the USB-C',
   f'{wins.sum()} of {wins.size} probes blocked')
ck(hi[0] - BOARD2_L/2 >= 2.0, 'the buttresses stand outboard of the board',
   f'{hi[0]:.1f} half-width vs {BOARD2_L/2:.1f}')

# ---- 6. it does not fall over ----------------------------------------------
# Real masses: PLA at 1.24 g/cm3 for the printed parts, plus the ring, the
# panel and the board.
RHO = 1.24e-3            # g/mm3
clock_parts = [f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
               f'mini-round-clock-diffuser{TAG}.stl']
mv = sum(trimesh.load(f).volume for f in clock_parts)
m_clock = mv*RHO + 45.0                  # + ring, panel, screws, leads
m_stand = m.volume*RHO
m_board = 12.0
c_clock = np.array([0.0, (cl.bounds[0][1]+cl.bounds[1][1])/2, (cl.bounds[0][2]+cl.bounds[1][2])/2])
c_stand = m.center_mass
c_board = np.array([0.0, BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W/2,
                    BACKSTAND_FOOT_T + BACKSTAND_POST_H + BOARD2_H/2])
M = m_clock + m_stand + m_board
com = (m_clock*c_clock + m_stand*c_stand + m_board*c_board) / M
print(f'  masses: clock {m_clock:.0f} g, stand {m_stand:.0f} g, board {m_board:.0f} g; '
      f'com y {com[1]:.2f}, z {com[2]:.2f}')

foot = m.slice_plane([0, 0, 0.25], [0, 0, 1])
fp = foot.vertices[:, :2] if len(foot.vertices) else np.zeros((1, 2))
y_front, y_back, x_side = fp[:, 1].min(), fp[:, 1].max(), abs(fp[:, 0]).max()
for name, lever in (('forwards', com[1] - y_front), ('backwards', y_back - com[1]),
                    ('sideways', x_side - abs(com[0]))):
    ang = math.degrees(math.atan2(lever, com[2]))
    ck(ang >= 20.0, f'tips {name} at 20 degrees or more', f'{ang:.1f} deg')

# ---- 7. it is not bulkier than what it replaces -----------------------------
ck(hi[0]-lo[0] < sb.bounds[1][0] - sb.bounds[0][0], 'narrower than the stand-box',
   f'{hi[0]-lo[0]:.1f} vs {sb.bounds[1][0]-sb.bounds[0][0]:.1f} mm wide')
# The point of the rebuild was bulk, and bulk is not height on its own: the 60
# is a 240 mm clock and its back support has to be tall. What must hold on every
# body is that the stand is smaller in every direction than the clock it carries.
d = 2*B.r_body
ck(max(hi - lo) < d, 'smaller in every direction than the clock it holds',
   f'{hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} inside a {d:.0f} mm disc')

print(('  ALL PASS' if not FAIL else f'  {len(FAIL)} FAILURE(S): ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
