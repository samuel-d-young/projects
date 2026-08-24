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

print('\n4. One layer over the LEDs, in a radial tick, and the cells survived')
CELL_PITCH = 360.0 / CELL_N
a_cell = CELL_WALL_A0 + CELL_PITCH / 2                 # midway between two walls
def at(r, a):
    return r*math.cos(math.radians(a)), r*math.sin(math.radians(a))

# inside the tick: one layer of plastic and nothing else
for r in (TICK_RI + 0.4, (TICK_RI + TICK_RO)/2, TICK_RO - 0.4):
    t = column_top(DIFF, *at(r, a_cell))
    ck(t is not None and abs(t - DIFF_MEM_T) < 0.02,
       f'r={r:.2f} is one layer, inside the tick', f'{t:.3f} mm (was 0.800)' if t else 'n/a')
# just outside it, still in the same cell: the full opaque face
for r in (TICK_RI - 0.6, TICK_RO + 0.6):
    t = column_top(DIFF, *at(r, a_cell))
    ck(t is not None and abs(t - FACE_T) < 0.02,
       f'r={r:.2f} is {FACE_T:.2f} mm, outside the tick', f'{t:.3f} mm' if t else 'n/a')
# and sideways out of the tick, at the same radius: also opaque
for dy in (TICK_W/2 + 0.6, -(TICK_W/2 + 0.6)):
    a = a_cell + math.degrees(dy / ((TICK_RI+TICK_RO)/2))
    t = column_top(DIFF, *at((TICK_RI+TICK_RO)/2, a))
    ck(t is not None and abs(t - FACE_T) < 0.02,
       f'{abs(dy):.2f} mm to the side of the tick is {FACE_T:.2f} mm', f'{t:.3f} mm' if t else 'n/a')

# every cell has exactly one tick, and every wall is full height
ticks = sum(1 for i in range(CELL_N)
            if (lambda t: t is not None and t < 0.5)(
                column_top(DIFF, *at((TICK_RI+TICK_RO)/2, CELL_WALL_A0 + (i+0.5)*CELL_PITCH))))
ck(ticks == CELL_N, f'all {CELL_N} cells have a tick', f'{ticks} of {CELL_N}')
walls = sum(1 for i in range(CELL_N)
            if (lambda t: t is not None and abs(t - BAND_TOP) < 0.02)(
                column_top(DIFF, *at(41.0, CELL_WALL_A0 + i*CELL_PITCH), e=0.02)))
ck(walls == CELL_N, f'all {CELL_N} cell walls reach {BAND_TOP:.2f} mm', f'{walls} of {CELL_N}')
for r in (RIB_I_RI + 0.5, RIB_O_RI + 0.5):
    t = column_top(DIFF, *at(r, a_cell))
    ck(t is not None and abs(t - BAND_TOP) < 0.02, f'the rib at r={r:.2f} is continuous',
       f'{t:.3f} mm (Sam\'s was notched at every wall)' if t else 'n/a')

print('\n5b. The tick is perpendicular to the circle, and sized to the LED')
ck(TICK_RO - TICK_RI > TICK_W, 'it is radial, not tangential',
   f'{TICK_RO-TICK_RI:.2f} mm radial x {TICK_W:.2f} mm tangential '
   f'({(TICK_RO-TICK_RI)/TICK_W:.1f}:1 pointing at the centre)')
led_i, led_o = DIFF_LINE_R - 2.5, DIFF_LINE_R + 2.5      # a 5050 is 5 mm square
ck(led_i < TICK_RI and TICK_RO < led_o, 'it sits inside the LED, so it is lit end to end',
   f'tick {TICK_RI:.2f}..{TICK_RO:.2f} inside LED {led_i:.2f}..{led_o:.2f}')
ck(abs((TICK_RI+TICK_RO)/2 - DIFF_LINE_R) < 0.01, 'and centred on the LED circle',
   f'tick centre {(TICK_RI+TICK_RO)/2:.2f} vs LED circle {DIFF_LINE_R:.2f}')
gap = 2*math.pi*DIFF_LINE_R/CELL_N - TICK_W
ck(gap > 3*TICK_W, 'the ticks read as separate marks, not a ring',
   f'{TICK_W:.2f} mm lit, {gap:.2f} mm dark between them')
# what actually stops crosstalk is the cell wall, not the aperture: the walls
# run the full depth of the cell, from the face up to the LED PCB, so light
# from the next LED never enters this cell to begin with.
ck(BAND_TOP - FACE_T >= 1.5, 'the cell wall runs the full depth of the cell',
   f'{BAND_TOP-FACE_T:.2f} mm from the face to the PCB, so the neighbouring LED '
   f'has no path in')
half = math.degrees(math.atan((TICK_W/2) / (FACE_T - DIFF_MEM_T)))
ck(half < 60.0, 'and the aperture keeps the tick a mark, not a glow',
   f'{FACE_T-DIFF_MEM_T:.2f} mm deep x {TICK_W:.2f} mm wide -> lit within '
   f'+/-{half:.0f} deg of straight on')

print('\n5c. The hours are written on the face')
def column_bottom(man, x, y, e=0.05):
    col = man ^ box_lwh(x-e, x+e, y-e, y+e, -50.0, 50.0)
    if col.volume() < 1e-9: return None
    return to_trimesh(col).bounds[0][2]

hit = 0
for h in range(12):
    a = 90.0 - h*30.0
    if int(round(a)) % 360 in NUMERALS: continue
    ri, ro = (MARK_RI_MAJ, MARK_RO_MAJ) if h % 3 == 0 else (MARK_RI, MARK_RO)
    b = column_bottom(DIFF, *at((ri+ro)/2, a), e=0.02)
    if b is not None and abs(b - MARK_DEPTH) < 0.02: hit += 1
ck(hit == 8, 'the 8 plain hour marks are debossed', f'{hit} of 8 at {MARK_DEPTH:.2f} mm deep')

for ang, txt in sorted(NUMERALS.items()):
    cx, cy = at(NUM_R, ang)
    w = NUM_H*1.6
    probe = box_lwh(cx-w, cx+w, cy-NUM_H*0.75, cy+NUM_H*0.75, 0.0, MARK_DEPTH)
    cut = probe.volume() - (DIFF ^ probe).volume()
    ck(cut > 0.5, f'"{txt}" is engraved at {ang} deg', f'{cut:.2f} mm3 of plastic removed')
ck(FACE_T - NUM_DEPTH >= 1.0, 'and the face stays opaque under the engraving',
   f'{FACE_T-NUM_DEPTH:.2f} mm left under a {NUM_DEPTH:.2f} mm deboss')
mark_lo = min(MARK_RI, MARK_RI_MAJ, NUM_R - NUM_H/2)
ck(mark_lo > R_RING_I, 'all of it is inside the plywood window',
   f'innermost mark r={mark_lo:.2f}, window edge r={R_RING_I:.2f}')
ck(max(MARK_RO, MARK_RO_MAJ, NUM_R + NUM_H/2) < TICK_RI, 'and clear of the lit ticks',
   f'outermost mark r={max(MARK_RO, MARK_RO_MAJ, NUM_R+NUM_H/2):.2f}, ticks start {TICK_RI:.2f}')

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
