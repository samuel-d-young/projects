#!/usr/bin/env python3
"""PASS 8 — the deep rear housing, the one that encloses the ESP32.

Measured off the EXPORTED MESH. The back-stand failed because every check
modelled the clock as a plain cylinder and nothing looked at what comes OUT of
it; the lesson taken here is to test the JOURNEY -- board in, plug in, wires
through, board out -- rather than the shape.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh
import csg
from params import *
import build_v2 as BV

FAIL = []
def ck(cond, msg, detail=''):
    print(f'  [{"ok  " if cond else "FAIL"}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
m   = trimesh.load(csg.part(f'mini-round-clock-housing{TAG}-deep.stl'))
lo, hi = m.bounds
PT  = HOUSING_S3_PLATE
z0  = Z_DECK - (PT + HOUSING_S3_POCKET) + PT
hw  = HOUSING_S3_SLOT_W/2.0
y_wall = -math.sqrt(B.r_inner**2 - hw**2)
y_usb  = y_wall + HOUSING_S3_USB_GAP
y_far  = y_usb + BOARD2_L
lz0 = z0 + HOUSING_S3_POST_H + BOARD_T

print(f'housing{TAG}-deep: {hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f} mm, '
      f'{m.volume/1000:.1f} cm3 — the whole clock is {Z_FRONT - lo[2]:.1f} mm deep')

ck(m.is_watertight, 'watertight')
ck(m.body_count == 1, 'one solid', f'{m.body_count}')

# ---- 1. the board goes in -------------------------------------------------
# Sam's board, as a solid, where the design says it sits.
# TWO probes, because the board is not a brick. The PCB is 1.60 mm over its
# whole footprint; the 3.20 mm of USB shell and module stand off it everywhere
# EXCEPT the last LIP_OVER at the far end, which is bare board and is exactly
# what the lip is designed to land on. A single 4.80 mm brick reported the lip
# as a 216-probe collision -- the lip doing its job.
bx = np.arange(-BOARD2_W/2 + 0.3, BOARD2_W/2, 0.75)
def clear(y1, y2, ztop, what):
    by_ = np.arange(y_usb + 0.3, y2, 0.75)
    bz_ = np.arange(z0 + HOUSING_S3_POST_H + 0.2, ztop, 0.6)
    gx, gy, gz = np.meshgrid(bx, by_, bz_, indexing='ij')
    h = m.contains(np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()]))
    ck(not h.any(), what, f'{h.sum()} of {h.size} probes hit material')
clear(y_usb, y_far, z0 + HOUSING_S3_POST_H + BOARD_T,
      "Sam's 64 x 30 PCB fits where the mount puts it")
clear(y_usb, y_far - HOUSING_S3_LIP_OVER,
      z0 + HOUSING_S3_POST_H + BOARD_T + BOARD_TALL,
      'and its 3.20 mm of components clear everything but the lip')

# and the slot is the width it claims, measured across the rails
zp = z0 + HOUSING_S3_POST_H + BOARD_T/2.0
xs = np.arange(-40, 40, 0.02)
ymid = (y_usb + y_far)/2.0
ins = m.contains(np.column_stack([xs, np.full_like(xs, ymid), np.full_like(xs, zp)]))
runs, cur = [], None
for x, v in zip(xs, ins):
    if not v and cur is None: cur = x
    elif v and cur is not None: runs.append((cur, x)); cur = None
if cur is not None: runs.append((cur, xs[-1]))
slot = [r for r in runs if r[0] < 0 < r[1]]
w = (slot[0][1] - slot[0][0]) if slot else 0.0
ck(abs(w - HOUSING_S3_SLOT_W) < 0.10, 'the slot is the width it was asked for',
   f'{w:.2f} vs {HOUSING_S3_SLOT_W:.2f}')
ck(w - BOARD2_W - FDM_SLOT_UNDER >= 0.10,
   "and still clears Sam's board if the print loses the worst case",
   f'{w - BOARD2_W - FDM_SLOT_UNDER:.2f} mm total')

# ---- 2. it can be lifted straight out -------------------------------------
gx2, gy2 = np.meshgrid(np.arange(-BOARD2_W/2 + 1, BOARD2_W/2, 1.0),
                       np.arange(y_usb + 1, y_far - HOUSING_S3_LIP_OVER - 1, 1.0),
                       indexing='ij')
ztop = z0 + HOUSING_S3_POST_H + BOARD2_H
over = m.contains(np.column_stack([gx2.ravel(), gy2.ravel(), np.full(gx2.size, ztop)]))
ck(not over.any(), 'nothing closes over the board — the loom comes off its top',
   f'{over.sum()} of {over.size} probes blocked')

# there IS a lip at the far end, and it is a ledge not a bridge
zl = lz0 + HOUSING_S3_LIP_GAP + HOUSING_S3_LIP_T/2.0
ly = np.arange(y_far - 6.0, y_far + 0.5, 0.05)
lin = m.contains(np.column_stack([np.zeros_like(ly), ly, np.full_like(ly, zl)]))
reach = (ly[lin].max() - ly[lin].min()) if lin.any() else 0.0
ck(lin.any(), 'there is a lip holding the far end down')
ck(reach <= 2.50, 'and it is a ledge, not a bridge (check3 allows 2.50)',
   f'{reach:.2f} mm')

# ---- 3. THE PLUG. This is the one the old mount got wrong ------------------
# A USB-C plug is about 12 x 6.5 over the overmould. Sweep that section from
# outside the body all the way to the board's end: if any of it is blocked, the
# cable cannot be plugged in and the clock is a brick.
px = np.arange(-5.5, 5.6, 0.5)
pz = np.arange(z0 + HOUSING_S3_POST_H + 0.4, z0 + HOUSING_S3_POST_H + 6.6, 0.5)
py = np.arange(-B.r_body - 2.0, y_usb + 1.0, 0.5)
gx3, gy3, gz3 = np.meshgrid(px, py, pz, indexing='ij')
plug = m.contains(np.column_stack([gx3.ravel(), gy3.ravel(), gz3.ravel()]))
ck(not plug.any(), 'a USB-C plug reaches the board from outside the clock',
   f'{plug.sum()} of {plug.size} probes blocked')
ck(HOUSING_S3_USB_GAP <= 3.0, 'and the reach is short enough to be a plug, not a tunnel',
   f'{HOUSING_S3_USB_GAP:.2f} mm from the wall to the board')

# ---- 4. the plenum the screen's tail lives in -----------------------------
plenum = Z_DECK - lz0
ck(plenum >= HOUSING_S3_PLENUM_MIN, 'clear plenum over the board for the loom',
   f'{plenum:.1f} mm')
# and the wires can actually get from the base's port to the board: the port is
# at +x, r 34..48, so probe a corridor from there across to the board
cx = np.arange(30.0, 46.0, 1.0)
cy = np.arange(-8.0, 8.0, 1.0)
cz = np.arange(lz0 + 1.0, Z_DECK - 1.0, 1.0)
g4 = np.meshgrid(cx, cy, cz, indexing='ij')
corr = m.contains(np.column_stack([g4[0].ravel(), g4[1].ravel(), g4[2].ravel()]))
ck(corr.mean() < 0.02, "the base's wire port opens into clear space inside",
   f'{corr.mean()*100:.1f}% of the corridor blocked')

# ---- 5. the cable ties, and the recess that makes them usable -------------
for ty in HOUSING_S3_TIE_Y:
    yy = y_usb + BOARD2_L/2.0 + ty
    zs = np.arange(z0 - PT + 0.1, z0 + 0.4, 0.1)
    for sx in (-1.0, 1.0):
        col = m.contains(np.column_stack([np.full_like(zs, sx*HOUSING_S3_TIE_X),
                                          np.full_like(zs, yy), zs]))
        ck(not col.any(), f'tie at y {ty:+.0f}, x {sx*HOUSING_S3_TIE_X:+.0f}: slot open through the plate',
           f'{col.sum()} of {col.size} blocked')
    xr = np.linspace(-HOUSING_S3_TIE_X, HOUSING_S3_TIE_X, 41)
    for zq in (z0 - PT + 0.05, z0 - PT + 1.0):
        rel = m.contains(np.column_stack([xr, np.full_like(xr, yy), np.full_like(xr, zq)]))
        ck(not rel.any(), f'tie at y {ty:+.0f}: the relief runs clear at z {zq - (z0 - PT):.2f} above the face',
           f'{rel.sum()} of {rel.size} blocked')
    mid = m.contains(np.column_stack([xr, np.full_like(xr, yy),
                                      np.full_like(xr, z0 - PT + HOUSING_S3_TIE_RELIEF + 0.6)]))
    ck(mid.mean() > 0.75, f'tie at y {ty:+.0f}: solid plate over the relief to pull against',
       f'{mid.mean()*100:.0f}% of the run')

# ---- 6. it still hangs on a wall, and the board is not in the way ---------
key = m.contains(np.array([[HANG_R - KEY_DROP/2.0, 0.0, lo[2] + 0.3]]))[0]
ck(not key, 'the keyhole is still open in the rear plate')
ck(abs(HANG_R - KEY_DROP) - 4.5 > BOARD2_W/2 + HOUSING_S3_RAIL_T,
   'and the board clears it', f'keyhole reaches x {HANG_R - KEY_DROP - 4.5:.1f}, '
   f'board+rails reach {BOARD2_W/2 + HOUSING_S3_RAIL_T:.1f}')

# ---- 6b. the USB window is a window, not half the wall --------------------
# The first build put a vent 10 degrees from it and the two merged into one
# 24 mm hole where 13 was drawn. Manifold, clean, and wrong -- which is why the
# opening is measured here rather than assumed from the parameter.
zq = z0 + HOUSING_S3_POST_H + HOUSING_S3_USB_H/2.0
rw = (B.r_inner + B.r_body)/2.0
ang = np.arange(0, 360, 0.25)
wall = m.contains(np.column_stack([rw*np.cos(np.radians(ang)), rw*np.sin(np.radians(ang)),
                                   np.full_like(ang, zq)]))
gaps, cur = [], None
for a_, v in zip(ang, wall):
    if not v and cur is None: cur = a_
    elif v and cur is not None: gaps.append((cur, a_)); cur = None
if cur is not None: gaps.append((cur, ang[-1]))
arc = lambda g: (g[1] - g[0])*math.pi*rw/180.0
usb = [g for g in gaps if g[0] <= 270.0 <= g[1]]
w_usb = arc(usb[0]) if usb else 0.0
ck(bool(usb), 'there is an opening at the USB window')
ck(w_usb < HOUSING_S3_USB_W + 4.0,
   'and it has not merged with a vent', f'{w_usb:.1f} mm of arc against a '
   f'{HOUSING_S3_USB_W:.0f} mm window')
ck(len(gaps) >= len(B.vent_ang), 'every vent is still its own opening',
   f'{len(gaps)} openings for {len(B.vent_ang)} vents plus the USB window')

# ---- 7. print orientation: it goes plate-down with nothing to support -----
zq = lo[2] + 0.2
g5x, g5y = np.meshgrid(np.arange(-B.r_body, B.r_body, 1.0),
                       np.arange(-B.r_body, B.r_body, 1.0), indexing='ij')
first = m.contains(np.column_stack([g5x.ravel(), g5y.ravel(), np.full(g5x.size, zq)]))
ck(first.sum() > 200, 'a real first layer on the rear plate', f'{first.sum()} cells')

print(('  ALL PASS' if not FAIL else f'  {len(FAIL)} FAILURE(S): ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
