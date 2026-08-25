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

import build_v2 as BV

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
BODIES = [(BV.BODY24, ''), (BV.BODY32, '-32')]

print('1. The tab slot, cut for the 30.55 mm tab Sam measured')
TAB_HW, TAB_R = DISP_TAB_W/2, math.hypot(DISP_TAB_W/2, DISP_OVERALL - DISP_PCB_D/2)
rot = math.degrees(math.asin(min(1.0, TAB_SLOT_HW / TAB_R))) - \
      math.degrees(math.asin(min(1.0, TAB_HW / TAB_R)))
ck(rot < 1.0, 'rotation is taken out of it', f'+/-{rot:.2f} deg (was +/-25.9)')
ck(27.5 * math.radians(rot) < 0.4, 'screen edge can move less than 0.4 mm',
   f'{27.5*math.radians(rot):.3f} mm')

for B, tg in BODIES:
    DIFF = to_manifold(load(f'mini-round-clock-diffuser{tg}.stl'))
    Dt   = load(f'mini-round-clock-diffuser{tg}.stl')
    print(f'\n{"="*70}\n{B.n}-LED diffuser')

    def at(r, a):
        return r*math.cos(math.radians(a)), r*math.sin(math.radians(a))
    a_cell = B.wall_a0 + B.pitch/2

    print('\n2. One layer over the LEDs, in a radial tick')
    for r in (B.tick_ri + 0.4, (B.tick_ri + B.tick_ro)/2, B.tick_ro - 0.4):
        t = column_top(DIFF, *at(r, a_cell))
        ck(t is not None and abs(t - DIFF_MEM_T) < 0.02,
           f'r={r:.2f} is one layer, inside the tick', f'{t:.3f} mm' if t else 'n/a')
    for r in (B.tick_ri - 0.6, B.tick_ro + 0.6):
        t = column_top(DIFF, *at(r, a_cell))
        ck(t is not None and abs(t - FACE_T) < 0.02,
           f'r={r:.2f} is {FACE_T:.2f} mm, outside the tick', f'{t:.3f} mm' if t else 'n/a')
    ticks = sum(1 for i in range(B.n)
                if (lambda t: t is not None and t < 0.5)(
                    column_top(DIFF, *at((B.tick_ri+B.tick_ro)/2, B.wall_a0 + (i+0.5)*B.pitch))))
    ck(ticks == B.n, f'all {B.n} cells have a tick', f'{ticks} of {B.n}')
    walls = sum(1 for i in range(B.n)
                if (lambda t: t is not None and abs(t - BAND_TOP) < 0.02)(
                    column_top(DIFF, *at((B.wall_ri + B.rib_o_ri)/2,
                                         B.wall_a0 + i*B.pitch), e=0.02)))
    ck(walls == B.n, f'all {B.n} cell walls reach {BAND_TOP:.2f} mm', f'{walls} of {B.n}')
    for r in (B.rib_i_ri + 0.5, B.rib_o_ri + 0.5):
        t = column_top(DIFF, *at(r, a_cell))
        ck(t is not None and abs(t - BAND_TOP) < 0.02, f'the rib at r={r:.2f} is continuous',
           f'{t:.3f} mm' if t else 'n/a')
    ck(BAND_TOP - FACE_T >= 1.5, 'the cell wall runs the full depth of the cell',
       f'{BAND_TOP-FACE_T:.2f} mm from the face to the PCB')

    print('\n3. The tick is perpendicular to the circle, and sized to the LED')
    ck(B.tick_ro - B.tick_ri > TICK_W, 'it is radial, not tangential',
       f'{B.tick_ro-B.tick_ri:.2f} radial x {TICK_W:.2f} tangential')
    led_i, led_o = B.led_r - 2.5, B.led_r + 2.5
    ck(led_i < B.tick_ri and B.tick_ro < led_o, 'it sits inside the LED',
       f'tick {B.tick_ri:.2f}..{B.tick_ro:.2f} inside LED {led_i:.2f}..{led_o:.2f}')
    ck(abs((B.tick_ri+B.tick_ro)/2 - B.led_r) < 0.01, 'and centred on the LED circle',
       f'{B.led_r:.2f}')
    gap = 2*math.pi*B.led_r/B.n - TICK_W
    ck(gap > 2*TICK_W, 'the ticks read as separate marks, not a ring',
       f'{TICK_W:.2f} mm lit, {gap:.2f} mm dark between them')

    print('\n4. The hours are written on the face')
    def column_bottom(man, x, y, e=0.05):
        col = man ^ box_lwh(x-e, x+e, y-e, y+e, -50.0, 50.0)
        if col.volume() < 1e-9: return None
        return to_trimesh(col).bounds[0][2]
    hit = 0
    for h in range(12):
        a = 90.0 - h*30.0
        if int(round(a)) % 360 in NUMERALS: continue
        ri, ro = (B.mark_ri_maj, B.mark_ro_maj) if h % 3 == 0 else (B.mark_ri, B.mark_ro)
        b_ = column_bottom(DIFF, *at((ri+ro)/2, a), e=0.02)
        if b_ is not None and abs(b_ - MARK_DEPTH) < 0.02: hit += 1
    ck(hit == 8, 'the 8 plain hour marks are debossed', f'{hit} of 8, {MARK_DEPTH:.2f} mm deep')
    for ang, txt in sorted(NUMERALS.items()):
        cx, cy = at(B.num_r, ang)
        w = NUM_H*1.6
        probe = box_lwh(cx-w, cx+w, cy-NUM_H*0.75, cy+NUM_H*0.75, 0.0, MARK_DEPTH)
        cut = probe.volume() - (DIFF ^ probe).volume()
        ck(cut > 0.5, f'"{txt}" is engraved at {ang} deg', f'{cut:.2f} mm3 removed')
    ck(FACE_T - NUM_DEPTH >= 1.0, 'and the face stays opaque under the engraving',
       f'{FACE_T-NUM_DEPTH:.2f} mm left')
    ck(max(B.mark_ro, B.mark_ro_maj, B.num_r + NUM_H/2) < B.tick_ri,
       'the hours stay clear of the lit ticks',
       f'outermost {max(B.mark_ro, B.mark_ro_maj, B.num_r+NUM_H/2):.2f}, ticks start {B.tick_ri:.2f}')

    print('\n5. Crush ribs, and the collar')
    r_out = np.hypot(Dt.vertices[:,0], Dt.vertices[:,1]).max()
    n_rib = 0
    for k in range(DIFF_RIB_N):
        a = 360.0/DIFF_RIB_N*(k+0.5)
        p = box_lwh(-0.4, 0.4, -0.4, 0.4, BAND_TOP-1.0, BAND_TOP-0.5)
        px, py = at(B.diff_outer + DIFF_RIB_H/2, a)
        if (DIFF ^ box_lwh(px-0.4, px+0.4, py-0.4, py+0.4,
                           BAND_TOP-1.0, BAND_TOP-0.5)).volume() > 1e-6: n_rib += 1
    ck(n_rib == DIFF_RIB_N, f'all {DIFF_RIB_N} crush ribs are there', f'{n_rib} of {DIFF_RIB_N}')
    lead = np.hypot(*Dt.vertices[np.abs(Dt.vertices[:,2]) < 1e-3][:, :2].T).max()
    ck(lead < r_out - 0.2, 'and they are chamfered at the entry face',
       f'{lead:.2f} at z=0 against a {r_out:.2f} crest')
    h = column_top(DIFF, 29.0, 0.0)
    ck(h is not None and abs(h - (DIFF_COLLAR_H + COLLAR_EXTEND)) < 0.05,
       'the collar still reaches 10.20 mm', f'{h:.2f} mm')

print()
if FAIL:
    print(f'CHECK 4: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('CHECK 4: the diffuser checks out on both bodies')
