#!/usr/bin/env python3
"""PASS 10 — the dock. Sam: "I hate the stand. Start again. I want it enclosed."

A clean sheet, so a clean set of tests. The rule this file works to, learned
three times over on the part it replaces: TEST THE JOURNEY, NOT THE SHAPE, and
give every part that goes INSIDE another one a boolean against it.
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
T = trimesh.load(csg.part(f'mini-round-clock-dock{TAG}.stl'))
C = trimesh.load(csg.part(f'mini-round-clock-dock{TAG}-cap.stl'))
F = BV._dock_frame(B)
hw, y_f, y_b = F['hw'], F['y_f'], F['y_b']
seat_z = DOCK_H - DOCK_BED

print(f'dock{TAG}: {T.extents[0]:.0f} x {T.extents[1]:.0f} x {DOCK_H:.0f} mm overall — '
      f'tray {T.volume/1000:.1f} cm3, cap {C.volume/1000:.1f} cm3 solid '
      f'(a slab: the slicer hollows it)')

for nm, m in (('tray', T), ('cap', C)):
    ck(m.is_watertight and m.body_count == 1, f'{nm} is one watertight solid',
       f'{m.body_count} bodies')

# ---- 1. the two halves go together --------------------------------------
ov = csg.to_trimesh(csg.to_manifold(T) ^ csg.to_manifold(C))
ck(ov.volume < 1.0, 'cap and tray do not interfere', f'{ov.volume:.2f} mm3')
ck(abs(C.bounds[0][2] - DOCK_CAP_Z) < 0.01,
   'the cap sits on the ledge at the top of the tray',
   f'cap underside z {C.bounds[0][2]:.2f}')
ck(T.bounds[1][2] > C.bounds[0][2] + 1.0,
   "and drops into the tray's rim rather than balancing on the wall tops",
   f'rim tops out at z {T.bounds[1][2]:.1f}, cap starts at {C.bounds[0][2]:.1f}')
BOTH = csg.to_manifold(T) + csg.to_manifold(C)
both = csg.to_trimesh(BOTH)

# ---- 2. IT IS ENCLOSED. The whole point. --------------------------------
# Fire a ray in from outside at cavity height on all four sides and count how
# many get in. Only two ways in are allowed: the USB tunnel and the wire drop.
zc = DOCK_FLOOR + 6.0
ys = np.arange(y_f + 4, y_b - 3, 1.0)
xs = np.arange(-hw + 4, hw - 3, 1.0)
def wall_open(pts):
    return (~both.contains(pts)).sum()
left  = wall_open(np.column_stack([np.full_like(ys, -hw + 1.2), ys, np.full_like(ys, zc)]))
right = wall_open(np.column_stack([np.full_like(ys,  hw - 1.2), ys, np.full_like(ys, zc)]))
frontw= wall_open(np.column_stack([xs, np.full_like(xs, y_f + 1.2), np.full_like(xs, zc)]))
backw = wall_open(np.column_stack([xs, np.full_like(xs, y_b - 1.2), np.full_like(xs, zc)]))
ck(right == 0 and frontw == 0 and backw == 0,
   'three of the four walls are solid — only the USB side is open',
   f'front {frontw}, back {backw}, right {right} open cells')
ck(0 < left <= DOCK_USB_W + 3,
   'and the left wall is open only where the USB tunnel is',
   f'{left} cells of a {2*(hw-4):.0f} mm run')
# the floor, and the top away from the seat
gx, gy = np.meshgrid(np.arange(-hw + 4, hw - 3, 2.0), np.arange(y_f + 4, y_b - 3, 2.0),
                     indexing='ij')
floor = (~both.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                         np.full(gx.size, 1.2)]))).sum()
ck(floor == 0, 'the floor is solid — nothing open underneath at all', f'{floor} cells')
# and nothing at all pierces the bottom face, not even a countersink
und = (~both.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                       np.full(gx.size, 0.25)]))).sum()
ck(und == 0, '...and no screw head breaks it either', f'{und} cells')

# ---- 3. the clock sits in it and nothing touches ------------------------
clock = F['xf'](cyl(B.r_body, F['Zb'], F['Zf'], 192))
for nm, part in (('tray', csg.to_manifold(T)), ('cap', csg.to_manifold(C))):
    v = csg.to_trimesh(part ^ clock).volume
    ck(v < 1.0, f'the clock does not touch the {nm}', f'{v:.2f} mm3')
ck(abs(DOCK_BED - (DOCK_H - seat_z)) < 1e-9,
   f'the clock beds {DOCK_BED:.0f} mm into the seat')

# ---- 4. the wires get from the seat to the tray -------------------------
zs = np.arange(DOCK_FLOOR + 8.0, seat_z + 6.0, 0.5)
drop = both.contains(np.column_stack([np.zeros_like(zs), np.full_like(zs, -14.0), zs]))
ck(not drop.any(), 'the wire drop runs from the seat into the tray',
   f'{drop.sum()} of {drop.size} probes blocked')
ck(2*DOCK_DROP_HW >= 12.0, 'and it is wide enough for a loom',
   f'{2*DOCK_DROP_HW:.0f} mm')
# it runs the WHOLE seat, so it does not matter which way round the clock goes
span = F['back'](DOCK_H) - 2.0 - (F['front'](DOCK_H) + 2.0)
ck(span > 28.0, 'the drop runs the full length of the seat, whichever way the '
   'clock is turned', f'{span:.1f} mm')

# ---- 5. the board, and the bar that holds it ----------------------------
by = DOCK_BOARD_Y
def fits(y2, ztop, what):
    gx, gy, gz = np.meshgrid(np.arange(-BOARD2_L/2 + 0.5, BOARD2_L/2, 1.5),
                             np.arange(by - BOARD2_W/2 + 0.4, y2, 1.0),
                             np.arange(DOCK_FLOOR + 0.2, ztop, 0.6), indexing='ij')
    h = T.contains(np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()]))
    ck(not h.any(), what, f'{h.sum()} of {h.size} probes hit material')
fits(by + BOARD2_W/2, DOCK_FLOOR + BOARD_T, "Sam's 64 x 30 board fits the bay")
fits(by + BOARD2_W/2, DOCK_FLOOR + BOARD_T + BOARD_TALL,
     'and so do its 3.20 mm of components')
CL = trimesh.load(csg.part('mini-round-clock-backstand-clamp.stl'))
_lz0 = BACKSTAND_FOOT_T + BACKSTAND_POST_H + BOARD_T
_top = _lz0 + BOARD_TALL + BACKSTAND_CLAMP_LIFT
_y0  = BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W/2.0
_fl  = np.eye(4); _fl[1, 1] = -1.0; _fl[2, 2] = -1.0
CL.apply_translation([0.0, -_y0, -(_top + BACKSTAND_CLAMP_T)])
CL.apply_transform(_fl)
CL.apply_translation([0.0, by, DOCK_FLOOR - BACKSTAND_FOOT_T])
ck(csg.to_trimesh(csg.to_manifold(T) ^ csg.to_manifold(CL)).volume < 1.0,
   'the existing hold-down bar drops straight in',
   f'{csg.to_trimesh(csg.to_manifold(T) ^ csg.to_manifold(CL)).volume:.2f} mm3')
ck(CL.bounds[1][2] < DOCK_CAP_Z, 'and it clears the cap',
   f'bar tops out at z {CL.bounds[1][2]:.1f}, cap underside {DOCK_CAP_Z:.1f}')

# ---- 6. a USB-C plug reaches the board ----------------------------------
px = np.arange(-hw - 3, -BOARD2_L/2 + 1.5, 0.5)
py = np.arange(by - 5.5, by + 5.6, 0.5)
pz = np.arange(DOCK_FLOOR + 1.0, DOCK_FLOOR + 7.5, 0.5)
gx, gy, gz = np.meshgrid(px, py, pz, indexing='ij')
plug = both.contains(np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()]))
ck(not plug.any(), 'a USB-C plug reaches the board from outside',
   f'{plug.sum()} of {plug.size} probes blocked')

# ---- 7. it does not fall over -------------------------------------------
RHO = 1.24e-3      # PLA, g/mm3
m_clock = 0.0
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-housing{TAG}.stl',
           f'mini-round-clock-backcover{TAG}.stl', f'mini-round-clock-diffuser{TAG}.stl'):
    m_clock += trimesh.load(csg.part(fn)).volume*RHO
m_clock += 40.0                                    # ring, screen, wiring
cl = csg.to_trimesh(clock)
m_dock = (T.volume + C.volume*0.35)*RHO            # 35%: the cap is a slab the
                                                   # slicer fills sparsely
com = (cl.center_mass*m_clock + both.center_mass*m_dock)/(m_clock + m_dock)
lo, hi = both.bounds
for nm, lever, h in (('forwards', com[1] - lo[1], com[2]),
                     ('backwards', hi[1] - com[1], com[2]),
                     ('sideways', hi[0] - com[0], com[2])):
    ang = math.degrees(math.atan2(lever, h))
    ck(ang >= 20.0, f'tips {nm} at {ang:.1f} deg', f'needs 20')
print(f'  masses: clock {m_clock:.0f} g, dock {m_dock:.0f} g; '
      f'combined centre of mass at y {com[1]:.1f}, z {com[2]:.1f}')

# ---- 8. it prints ------------------------------------------------------
ck(abs(T.bounds[0][2]) < 1e-6, 'the tray sits on z = 0', f'{T.bounds[0][2]:.4f}')
ck(C.bounds[1][2] - C.bounds[0][2] <= DOCK_H - DOCK_CAP_Z + 3.01,
   'the cap is no taller than its own slab plus the spigot',
   f'{C.bounds[1][2] - C.bounds[0][2]:.2f} mm')
# the seat is a VALLEY, open upward, so a vertical ray from above it must reach
# the seat floor without passing through cap
sx = np.arange(-30, 31, 3.0)
above = C.contains(np.column_stack([sx, np.full_like(sx, -14.0),
                                    np.full_like(sx, DOCK_H + 0.5)]))
ck(not above.any(), 'the seat is open to the sky — nothing to bridge or support',
   f'{above.sum()} of {above.size} probes blocked')

print(('  ALL PASS' if not FAIL else f'  {len(FAIL)} FAILURE(S): ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
