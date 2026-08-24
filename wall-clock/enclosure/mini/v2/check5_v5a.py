#!/usr/bin/env python3
"""v5a: is the S3 actually held, and can a USB-C plug reach it from outside?

Two things Sam asked for after v5:
    "make sure that the ESP32 S3 is held in properly and that the USB connector
     can be connected externally from the outside of the wall. I may or may not
     use a USB battery or USB power supply."

Everything here is measured on the built STLs, not on the code that made them.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh
from csg import box_lwh, cyl, tube, wedge, prism, rot_rect, to_manifold, to_trimesh
from params import *

FAIL = []
def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c: FAIL.append(msg)

def load(f):
    m = trimesh.load(f, process=False); m.merge_vertices(); return m

BASE = to_manifold(load('mini-round-clock-base-v2.stl'))
KEEP = to_manifold(load('mini-round-clock-board-keeper.stl'))
HB   = to_manifold(load('mini-round-clock-rearhousing-battery.stl'))
HS   = to_manifold(load('mini-round-clock-rearhousing-slim.stl'))

Z_LEDGE = Z_BACK - 0.80
BY      = BOARD_W / 2
def board_solid(z0=Z_LEDGE, t=BOARD_T):
    return box_lwh(BOARD_X0, BOARD_X1, -BY, BY, z0, z0 + t)

def solid_at(man, x, y, z, e=0.05):
    return (man ^ box_lwh(x-e, x+e, y-e, y+e, z-e, z+e)).volume() > 1e-9


# =============================================================================
print('1. The board cannot lift into the clock any more')
top = Z_LEDGE + BOARD_T + BOARD_TALL                      # 4.00
ck(abs(BEAM_Z0 - 4.20) < 1e-9 and BEAM_Z0 > top,
   'the beam sits above everything the board carries',
   f'beam at z {BEAM_Z0:.2f}, board tops out at {top:.2f}')
ck(BEAM_Z0 - top <= 0.25, 'so the float is gone', f'{BEAM_Z0 - top:.2f} mm (was {Z_SEAT - top:.2f})')
# it is really there, over the board, and it really is a beam and not a lump
ck(solid_at(BASE, -20.0, 0.0, (BEAM_Z0+BEAM_Z1)/2), 'the beam spans the board on the axis')
for y in (-12.0, 12.0):
    ck(solid_at(BASE, -20.0, y, (BEAM_Z0+BEAM_Z1)/2), f'...and at y={y:+.0f}')
ck(not solid_at(BASE, -20.0, 0.0, BEAM_Z0 - 0.30), 'nothing below it', 'the board slides under')
ck(BEAM_Z1 < Z_SEAT, 'and it stays clear of the display seat',
   f'beam top {BEAM_Z1:.2f} < seat {Z_SEAT:.2f}')
# its pillars land on solid deck, inside the bore
for sy in (1, -1):
    x, y = -20.0, sy * BEAM_PILLAR_Y
    ck(math.hypot(x, y) < R_BORE, f'pillar at y={y:+.1f} is inside the bore',
       f'r = {math.hypot(x, y):.2f} < {R_BORE:.2f}')
    ck(abs(y) > BOARD_W/2 + BOARD_CLR, '...and outside the deck window',
       f'|y| {abs(y):.2f} > {BOARD_W/2 + BOARD_CLR:.2f}')

print('\n2. ...and it can still be got in, tilted, +x end up')
gap = (BOARD_X1 - LEDGE_END) - (BOARD_X0 - BOARD_CLR + LEDGE_END)
th = None
for d in np.arange(0.0, 40.0, 0.05):
    r = math.radians(d)
    if BOARD_L*math.cos(r) + BOARD_T*math.sin(r) <= gap:
        th = d; break
ck(th is not None, 'there IS a tilt that clears both ledges',
   f'{th:.1f} deg through a {gap:.2f} mm gap' if th else f'gap {gap:.2f} mm is too small')

# Now prove it on the actual mesh. The board does not simply rotate in place:
# it goes in tilted, flattens with its ends outside the two ledges, and is then
# slid -x by about a millimetre onto them -- which is what the 3.26 mm of window
# past the board's +x end is for. So the test is a small motion search: at every
# angle from the tilt-in down to flat, is there ANY position (dx, dz) the board
# can be in without touching the base? If the feasible set is non-empty at every
# angle and the steps are half a degree, the board can be walked in.
cx, cz = (BOARD_X0 + BOARD_X1)/2, Z_LEDGE + BOARD_T/2
def pose(d, dx, dz):
    r = -math.radians(d)                      # negative about y = +x end UP
    M = np.array([[ math.cos(r), 0, math.sin(r), cx - cx*math.cos(r) - cz*math.sin(r) + dx],
                  [ 0, 1, 0, 0],
                  [-math.sin(r), 0, math.cos(r), cz + cx*math.sin(r) - cz*math.cos(r) + dz],
                  [ 0, 0, 0, 1]])
    b = to_trimesh(board_solid(Z_LEDGE, BOARD_T + BOARD_TALL))
    b.apply_transform(M)
    return to_manifold(b)

angles = np.arange(0.0, (th or 0) + 3.01, 0.5)
feasible, stuck = {}, None
for d in angles:
    hit = None
    for dx in (0.0, 0.6, 1.2, 1.8, 2.4, 3.0):
        for dz in (0.0, -0.5, -1.5, -3.0, -5.0, -8.0, -12.0):
            if (BASE ^ pose(d, dx, dz)).volume() < 1e-6:
                hit = (dx, dz); break
        if hit: break
    feasible[round(float(d), 2)] = hit
    if hit is None and stuck is None: stuck = d
ck(stuck is None, f'a clear pose exists at every angle from 0 to {(th or 0)+3:.1f} deg',
   f'{len(angles)} poses, e.g. flat needs dx={feasible[0.0][0]:.1f}, tilted needs '
   f'dx={feasible[round(float(angles[-1]),2)][0]:.1f} mm'
   if stuck is None else f'no pose at {stuck:.1f} deg')
ck(feasible.get(0.0) == (0.0, 0.0), 'and the seated pose itself is exactly clear',
   f'dx={feasible[0.0][0]:.1f}, dz={feasible[0.0][1]:.1f}')
print('         the path, in half-degree steps (tilt, then how far the board sits low):')
_tr = [(d, feasible[round(float(d),2)]) for d in angles[::4]]
print('        ' + '  '.join(f'{d:.0f}d:{v[1]:+.1f}' for d, v in _tr if v))
slide = max((v[0] for v in feasible.values() if v), default=0.0)
ck(WINDOW_X1_EXT - BOARD_X1 > slide, 'the window is long enough for the final slide',
   f'{slide:.1f} mm of slide into {WINDOW_X1_EXT - BOARD_X1:.2f} mm of window')

rise = BOARD_L/2 * math.sin(math.radians(th or 0))
ck(Z_RING_FLOOR - (Z_LEDGE + rise) > 1.0, 'and there is headroom over the +x end',
   f'needs z {Z_LEDGE + rise:.2f}, tab window is open to {Z_RING_FLOOR:.2f} '
   f'({Z_RING_FLOOR - Z_LEDGE - rise:.2f} mm spare)')
ck(Z_SEAT - (Z_LEDGE + rise) < 1.0, 'which is why it goes in +x end up, not -x',
   f'the bore only opens to {Z_SEAT:.2f}, and it needs {Z_LEDGE + rise:.2f}')

print('\n3. The keeper takes out the last degree of freedom')
ck((BASE ^ KEEP).volume() < 1e-6, 'the keeper does not fight the base',
   f'{(BASE ^ KEEP).volume():.5f} mm3')
for nm, h in (('battery', HB), ('slim', HS)):
    ck((h ^ KEEP).volume() < 1e-6, f'...nor the {nm} housing', f'{(h ^ KEEP).volume():.5f} mm3')
ck((board_solid() ^ KEEP).volume() < 1e-6, '...nor the board itself',
   f'{(board_solid() ^ KEEP).volume():.5f} mm3')
# the tongue really does overhang the board
tng = box_lwh(KEEP_TONGUE_X1 - KEEP_TONGUE_L, KEEP_TONGUE_X1, -KEEP_TONGUE_HY,
              KEEP_TONGUE_HY, KEEP_TONGUE_Z0, KEEP_TONGUE_Z1)
ck((KEEP ^ tng).volume() > 0.9 * tng.volume(), 'the tongue covers the board\'s +x end',
   f'{KEEP_TONGUE_L:.2f} x {2*KEEP_TONGUE_HY:.1f} mm of it')
ck(abs(KEEP_TONGUE_Z0 - (Z_LEDGE + BOARD_T)) - 0.20 < 1e-9,
   'with 0.20 mm of float under it',
   f'tongue at {KEEP_TONGUE_Z0:.2f}, board top at {Z_LEDGE + BOARD_T:.2f}')
ck(KEEP_TONGUE_HY < BY - 3.0,
   'and it stays inboard of the pad rows',
   f'+/-{KEEP_TONGUE_HY:.1f} against a board edge at +/-{BY:.1f}; the two 22-pin '
   f'rows leave {(BOARD_L - 21*2.54)/2:.2f} mm clear at each end')
# the screws line up, and the pilot is in solid base rather than in the deck alone
for sy in (1, -1):
    x, y = KEEP_SCREW_X, sy*KEEP_SCREW_Y
    hole = cyl(KEEP_SCREW_PIL/2 - 0.10, Z_BACK + 0.5, Z_BACK + KEEP_SCREW_DEP - 0.5, 32,
               centre=(x, y))
    ck((BASE ^ hole).volume() < 1e-6, f'pilot at y={y:+.1f} is bored through',
       f'r = {math.hypot(x,y):.2f}')
ck(math.hypot(KEEP_SCREW_X, KEEP_SCREW_Y) > R_RING_O,
   'and it is outboard of the ring pocket, so it never breaks into it',
   f'r = {math.hypot(KEEP_SCREW_X, KEEP_SCREW_Y):.2f} > {R_RING_O:.2f}')

print('\n4. The USB-C inlet: the breakout fits its bay')
pcb = box_lwh(USBC_FACE_X, USBC_FACE_X + USBC_PCB_L, -USBC_PCB_W/2, USBC_PCB_W/2,
              USBC_Z, USBC_Z + 1.60)
conn = box_lwh(USBC_FACE_X, USBC_FACE_X + 8.0, -4.47, 4.47, USBC_Z + 1.60, USBC_Z + USBC_PCB_H)
# 1e-3, not 1e-6: the PCB rests ON the shelf, so its underside and the shelf's
# top face are the same plane by design, and two independently faceted surfaces
# there leave a few microns behind. That is arithmetic, not plastic.
ck((BASE ^ pcb).volume() < 1e-3, 'the 20.4 x 14.2 PCB drops in', f'{(BASE ^ pcb).volume():.6f} mm3')
ck((BASE ^ conn).volume() < 1e-6, 'the connector body clears everything',
   f'{(BASE ^ conn).volume():.5f} mm3')
ck((board_solid() ^ box_lwh(USBC_FACE_X, USBC_BAY_X1, -USBC_RAIL_HY, USBC_RAIL_HY,
                            Z_BACK, USBC_RAIL_H)).volume() < 1e-6,
   'the bay does not run into the S3 board',
   f'{USBC_BAY_X1 - (BOARD_X0 - BOARD_CLR):+.2f} mm of gap')
# lips: over the PCB, clear of the connector
ck(USBC_LIP_HY < USBC_PCB_W/2, 'the lips overlap the PCB',
   f'{USBC_PCB_W/2 - USBC_LIP_HY:.2f} mm each side')
ck(USBC_LIP_HY > 8.94/2, '...and clear the 8.94 mm connector shell',
   f'{USBC_LIP_HY - 8.94/2:.2f} mm each side')
ck(USBC_LIP_Z0 > USBC_Z + 1.60, '...and sit above the PCB, not on it',
   f'lip at {USBC_LIP_Z0:.2f}, PCB top at {USBC_Z + 1.60:.2f}')
ck(USBC_LIP_Z1 - USBC_LIP_Z0 >= 1.20, '...and are thick enough to print',
   f'{USBC_LIP_Z1 - USBC_LIP_Z0:.2f} mm')
for sy in (1, -1):
    ck(solid_at(BASE, -35.0, sy*(USBC_LIP_HY + 0.6), (USBC_LIP_Z0+USBC_LIP_Z1)/2, e=0.15),
       f'the lip at y={sy*(USBC_LIP_HY+0.6):+.2f} is really there')

print('\n5. ...and a plug reaches it from outside the wall')
plug = box_lwh(-R_BODY - 25.0, USBC_FACE_X, -PLUG_W/2, PLUG_W/2,
               USBC_PORT_Z - PLUG_H/2, USBC_PORT_Z + PLUG_H/2)
ck((BASE ^ plug).volume() < 1e-6, 'a full-size USB-C overmold comes straight in',
   f'{PLUG_W:.2f} x {PLUG_H:.2f} mm (the USB-IF maximum), {(BASE ^ plug).volume():.5f} mm3')
ck(PLUG_CH_W < USBC_PCB_W, 'the channel is narrower than the breakout PCB',
   f'{PLUG_CH_W:.2f} < {USBC_PCB_W:.2f} -- pulling the plug cannot drag it out, '
   f'the PCB butts a {(USBC_PCB_W - PLUG_CH_W)/2:.2f} mm shoulder each side')
ck(PLUG_CH_Z0 >= Z_BACK, 'the channel stays out of the deck',
   f'floor at z {PLUG_CH_Z0:.2f}, deck top at {Z_BACK:.2f}')
ck(PLUG_CH_Z0 + PLUG_CH_H < Z_RING_FLOOR, '...and out of the LED ring pocket',
   f'roof at z {PLUG_CH_Z0 + PLUG_CH_H:.2f} < {Z_RING_FLOOR:.2f}')
recess = R_BODY + USBC_FACE_X                    # how far in the socket sits
ck(6.0 < recess < 9.0, 'the socket sits a plug-shell\'s depth inside the rim',
   f'{recess:.2f} mm')
ck(20.0 - recess > 8.0, 'so the overmold stands proud and can be gripped',
   f'~{20.0 - recess:.1f} mm out of the clock on a 20 mm overmold')
# nothing else got holed
band = tube(R_RING_I, R_RING_O, Z_RING_FLOOR, Z_RING_FLOOR + PCB_T + LED_H, 128)
ck((band - BASE).volume() > 0.99 * band.volume(),
   'the ring pocket is still empty where the ring goes',
   f'{100*(band - BASE).volume()/band.volume():.1f}% clear')

print('\n6. Power: what the inlet is wired to')
print(f'         Adafruit ADA4090, 20.4 x 14.2 x 5.0 mm, two 5.1 kohm CC resistors.')
print(f'         A$5.40 inc GST at Core Electronics. NOT ORDERED.')
print(f'         VBUS/GND -> the board\'s 5V and GND pins, per README section 2.')
print(f'         The CC resistors are not optional: without them a USB-C charger')
print(f'         or power bank never turns 5 V on at all.')

print()
if FAIL:
    print(f'CHECK 5: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('CHECK 5: the board is held, and the plug reaches it from outside')
