#!/usr/bin/env python3
"""The four changes Sam asked for after test-fitting. Did they land?"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, trimesh
import csg
from csg import box_lwh, cyl, tube, wedge, to_manifold, to_trimesh
from params import *

FAIL=[]
def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c: FAIL.append(msg)

def load(f):
    m = trimesh.load(f, process=False); m.merge_vertices(); return m

BASE = to_manifold(load('mini-round-clock-base-v2.stl'))
DIFF = to_manifold(load('mini-round-clock-diffuser-v3.stl'))
Dt   = load('mini-round-clock-diffuser-v3.stl')

def solid_at(man, x, y, z, e=0.02):
    return (man ^ box_lwh(x-e, x+e, y-e, y+e, z-e, z+e)).volume() > 1e-9

def column_top(man, x, y, e=0.05):
    """Exact top of the material in a thin column — no probe tolerance."""
    col = man ^ box_lwh(x-e, x+e, y-e, y+e, -50.0, 50.0)
    if col.volume() < 1e-9: return None
    return to_trimesh(col).bounds[1][2]

def bisect(f, lo, hi, n=40):
    flo = f(lo)
    if flo == f(hi): return None
    for _ in range(n):
        m = (lo+hi)/2
        if f(m) == flo: lo = m
        else: hi = m
    return (lo+hi)/2

# ---------------------------------------------------------------- 1. tab slot
print('1. The tab slot, now cut for the 30.55 mm tab Sam measured')
TAB_HW, TAB_R = DISP_TAB_W/2, math.hypot(DISP_TAB_W/2, DISP_OVERALL - DISP_PCB_D/2)
print(f'         tab {DISP_TAB_W} wide, corners reach r = {TAB_R:.2f}')
for z, lbl in [(8.8, 'tab bottom'), (9.4, 'tab middle'), (10.0, 'tab top')]:
    for r in (33.0, 37.0, 40.0):
        hw = bisect(lambda y: solid_at(BASE, math.sqrt(max(r*r-y*y, 0)), y, z), 0.0, 30.0)
        print(f'         z={z:4.1f} r={r:4.0f}  slot half-width {hw:6.2f}' if hw
              else f'         z={z:4.1f} r={r:4.0f}  open')
        if hw: ck(abs(hw - TAB_SLOT_HW) < 0.25, f'  slot is {2*TAB_SLOT_HW:.2f} wide at z={z}, r={r}',
                  f'{2*hw:.2f} mm')

# the tab itself must pass
TAB_REACH = DISP_OVERALL - DISP_PCB_D/2          # 37.0 along the midline
tab = box_lwh(R_DISP_POCKET, TAB_REACH, -TAB_HW, TAB_HW, Z_SEAT, Z_SEAT + DISP_TAB_T)
ck((BASE ^ tab).volume() < 1e-6, 'the tab clears the slot', f'{(BASE ^ tab).volume():.5f} mm3')
# and it must NOT be able to rotate far
rot = math.degrees(math.asin(min(1.0, TAB_SLOT_HW / TAB_R))) - \
      math.degrees(math.asin(min(1.0, TAB_HW / TAB_R)))
ck(rot < 1.0, 'rotation is taken out of it', f'+/-{rot:.2f} deg (was +/-25.9)')
ck(27.5 * math.radians(rot) < 0.4, 'screen edge can move less than 0.4 mm',
   f'{27.5*math.radians(rot):.3f} mm')

print('\n2. The new walls do not foul anything else')
board = box_lwh(BOARD_X0, BOARD_X1, -BOARD_W/2, BOARD_W/2,
                Z_BACK - 0.80, Z_BACK - 0.80 + BOARD_T + BOARD_TALL)
ck((BASE ^ board).volume() < 1e-6, 'clear of the S3 board', f'{(BASE ^ board).volume():.5f} mm3')
module = cyl(DISP_PCB_D/2, Z_SEAT, Z_SEAT + 4.0, 128)
ck((BASE ^ module).volume() < 1e-3, 'clear of the display module', f'{(BASE ^ module).volume():.5f} mm3')
ring = tube(RING_ID/2, RING_OD/2, Z_RING_FLOOR, Z_RING_FLOOR + PCB_T + LED_H, 128) \
       if 'RING_ID' in dir() else tube(35.5, 46.0, Z_RING_FLOOR, Z_RING_FLOOR + 3.2, 128)
# 1e-3, not 1e-6: the walls stop exactly at the ring pocket floor, so the
# test cylinder's base plane is coincident with theirs and the faceting of
# two independently generated circles leaves ~5e-5 mm3 behind. That is
# arithmetic, not plastic.
ck((BASE ^ ring).volume() < 1e-3, 'clear of the LED ring', f'{(BASE ^ ring).volume():.5f} mm3')
# ...and they put the ring's floor back at 12 o'clock, everywhere the tab is
# not. Measured outboard of the slot, since the middle has to stay open.
floor = wedge(36.0, 42.0, Z_RING_FLOOR - 1.0, Z_RING_FLOOR, -TAB_HALF_DEG, TAB_HALF_DEG) \
        - box_lwh(0.0, 60.0, -18.0, 18.0, Z_RING_FLOOR - 2.0, Z_RING_FLOOR + 1.0)
got = (BASE ^ floor).volume() / floor.volume()
ck(got > 0.90, 'ring pocket floor restored either side of the tab',
   f'{100*got:.0f}% of that sector is solid (it was 0)')

print('\n3. The diffuser is a press fit')
r_out = np.hypot(Dt.vertices[:,0], Dt.vertices[:,1]).max()
ck(abs(r_out - DIFF_OUTER_NEW) < 0.02, 'outer radius grown', f'{r_out:.4f} (was {DIFF_OUTER:.3f})')
ck(r_out > R_RING_O, 'it now interferes with the ring pocket wall',
   f'{r_out - R_RING_O:+.4f} mm radial, {2*(r_out - R_RING_O):+.4f} on diameter')
ck(r_out - R_RING_O < 0.15, 'but not so much it cannot be pressed in',
   f'{2*(r_out - R_RING_O):.3f} mm diametral interference')
ck(abs(Dt.bounds[1][2] - (DIFF_COLLAR_H + COLLAR_EXTEND)) < 1e-3,
   'overall height is still set by the collar', f'{Dt.bounds[1][2]:.2f} mm')

print('\n4. One layer over the LEDs, and the cell walls survived it')
a_gap = DIFF_BAFFLE_A0 + 360.0/DIFF_BAFFLE_N/2          # midway between two walls
# sampled inside the LINE -- outside it the face is deliberately 2.0 mm now,
# which section 5b checks
for r in (DIFF_LINE_RI + 0.3, DIFF_LINE_R, DIFF_LINE_RO - 0.3):
    x, y = r*math.cos(math.radians(a_gap)), r*math.sin(math.radians(a_gap))
    t = column_top(DIFF, x, y)
    ck(t is not None and abs(t - DIFF_MEM_T) < 0.02,
       f'membrane is one layer at r={r:.0f}, between walls',
       f'{t:.3f} mm (was 0.800)' if t else 'n/a')
for r in (40.0, 42.0, 44.0):
    x, y = r*math.cos(math.radians(DIFF_BAFFLE_A0)), r*math.sin(math.radians(DIFF_BAFFLE_A0))
    t = column_top(DIFF, x, y, e=0.02)
    ck(t is not None and t > 3.0, f'the cell wall at r={r:.0f} still reaches full height',
       f'{t:.2f} mm' if t else 'n/a')
walls = 0
for i in range(DIFF_BAFFLE_N):
    a = DIFF_BAFFLE_A0 + i*(360.0/DIFF_BAFFLE_N)
    x, y = 42*math.cos(math.radians(a)), 42*math.sin(math.radians(a))
    if solid_at(DIFF, x, y, 2.0): walls += 1
ck(walls == DIFF_BAFFLE_N, 'all 24 cell walls survived the thinning', f'{walls} of {DIFF_BAFFLE_N}')

print('\n5b. The lit band is now a line')
a_gap = DIFF_BAFFLE_A0 + 360.0/DIFF_BAFFLE_N/2
def thick_at(r):
    x, y = r*math.cos(math.radians(a_gap)), r*math.sin(math.radians(a_gap))
    return column_top(DIFF, x, y)
# inside the line: one layer.  outside it: opaque.
for r in (DIFF_LINE_RI + 0.3, DIFF_LINE_R, DIFF_LINE_RO - 0.3):
    t = thick_at(r)
    ck(t is not None and abs(t - DIFF_MEM_T) < 0.02, f'r={r:.2f} is one layer (inside the line)',
       f'{t:.3f} mm' if t else 'n/a')
for r in (DIFF_MEM_RI + 0.2, DIFF_LINE_RI - 0.3, DIFF_LINE_RO + 0.3, DIFF_MEM_RO - 0.3):
    t = thick_at(r)
    ck(t is not None and t >= DIFF_OPAQUE_T - 0.02, f'r={r:.2f} is {DIFF_OPAQUE_T} mm (outside the line)',
       f'{t:.3f} mm' if t else 'n/a')
# the line has to sit on the LEDs, not beside them
ck(abs((DIFF_LINE_RI + DIFF_LINE_RO)/2 - DIFF_LINE_R) < 1e-9,
   'the line is centred on the LED circle', f'r = {DIFF_LINE_R:.2f}')
led_i, led_o = DIFF_LINE_R - 2.5, DIFF_LINE_R + 2.5      # a 5050 is 5 mm
ck(led_i < DIFF_LINE_RI and DIFF_LINE_RO < led_o,
   'and narrower than the 5 mm LED, so it acts as an aperture',
   f'line {DIFF_LINE_W:.2f} inside LED {led_o-led_i:.2f}')
# no step where the inner band meets the skirt
ck(abs(DIFF_OPAQUE_T - 2.0) < 1e-9,
   'inner band is flush with the skirt, so the face is one shelf', f'both {DIFF_OPAQUE_T:.2f} mm')
seg = 2*math.pi*DIFF_LINE_R/DIFF_BAFFLE_N - 0.95
print(f'         one lit LED now shows {DIFF_LINE_W:.2f} x {seg:.2f} mm  '
      f'({seg/DIFF_LINE_W:.1f}:1), was {DIFF_MEM_RO-DIFF_MEM_RI:.2f} x {seg:.2f} '
      f'({seg/(DIFF_MEM_RO-DIFF_MEM_RI):.1f}:1)')
print(f'         the walls leave {100*seg/(2*math.pi*DIFF_LINE_R/DIFF_BAFFLE_N):.0f}% of the '
      f'circle lit, so adjacent LEDs read as one line')

print('\n5. The collar reaches further in')
h = column_top(DIFF, 29.0, 0.0)
ck(h is not None and abs(h - (DIFF_COLLAR_H + COLLAR_EXTEND)) < 0.05,
   'collar height', f'{h:.2f} mm (was {DIFF_COLLAR_H:.2f})')
reach = Z_RECESS - (DIFF_COLLAR_H + COLLAR_EXTEND)
print(f'         it now reaches base z = {reach:.2f}; the seat is at {Z_SEAT:.2f}')
print(f'         -> it clamps a module whose rim is {reach - Z_SEAT:.2f} mm thick.')
print(f'            Sam reports the screen is LOOSE with the 8.20 collar, which')
print(f'            reached z = {Z_RECESS - DIFF_COLLAR_H:.2f} -- so the rim is under'
      f' {Z_RECESS - DIFF_COLLAR_H - Z_SEAT:.2f} mm.')
print(f'            Measure it (call it t) and set COLLAR_EXTEND = '
      f'{Z_RECESS - DIFF_COLLAR_H - Z_SEAT:.2f} - t for an exact clamp.')
ck(COLLAR_EXT_RI > DISP_ACTIVE_D/2, 'the collar stays off the glass',
   f'inner r {COLLAR_EXT_RI:.2f} vs active area r {DISP_ACTIVE_D/2:.2f}')
ck(COLLAR_EXT_RO < R_DISP_POCKET, 'and inside the display pocket',
   f'outer r {COLLAR_EXT_RO:.2f} vs pocket {R_DISP_POCKET:.4f}')

print()
if FAIL:
    print(f'CHECK 4: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('CHECK 4: all four changes verified on the built parts')
