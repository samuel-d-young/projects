#!/usr/bin/env python3
"""The desk stand. Does the clock actually sit in it, and can it be plugged in?

    "build a stand for the clock to go in so that it can sit on a desk too. But
     the stand is another print that the clock sits in."
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh
from csg import box_lwh, cyl, tube, wedge, to_manifold, to_trimesh
from params import *
import build_v2 as BV

FAIL = []
def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c: FAIL.append(msg)

def load(f):
    m = trimesh.load(f, process=False); m.merge_vertices(); return m

SEG   = BV.SEG
DEPTH = Z_FRONT - (Z_DECK - HOUSING_DEEP)
T     = STAND_TILT

def placed(man, B, up=0.0, along=0.0):
    """Take a solid built in the stand's own frame -- clock axis along +Z, front
    face at Z=0, +Y up in the clock's plane -- into desk coordinates. `up` lifts
    it out of the cradle, `along` slides it forward (+) or back (-)."""
    h0 = STAND_LIFT + B.r_body*math.cos(math.radians(T))
    return man.translate([0.0, up, along]).rotate([90.0 - T, 0.0, 0.0]) \
              .translate([0.0, 0.0, h0])

for B, tg in [(BV.BODY24, ''), (BV.BODY32, '-32')]:
    S  = to_manifold(load(f'mini-round-clock-deskstand{tg}.stl'))
    St = load(f'mini-round-clock-deskstand{tg}.stl')
    print(f'\n{"="*70}\n{B.n}-LED stand — for a {2*B.r_body:.2f} x {DEPTH:.1f} mm clock')

    print('\n1. The clock sits in it')
    clock = placed(cyl(B.r_body, -DEPTH, 0.0, 192), B)
    ck((S ^ clock).volume() < 1e-3, 'the clock does not interfere with the cradle',
       f'{(S ^ clock).volume():.5f} mm3')
    seat = placed(cyl(B.r_body + STAND_CLR + 0.02, -DEPTH, 0.0, 192), B)
    ck((S ^ seat).volume() > 100.0, '...but it is a cradle, not a slot it rattles in',
       f'{STAND_CLR:.2f} mm radial clearance')
    # the stop wall is behind the clock, and really stops it
    pushed = placed(cyl(B.r_body, -DEPTH, 0.0, 192), B, along=-3.0)
    ck((S ^ pushed).volume() > 50.0, 'a stop wall closes behind it',
       f'push it 3 mm back and it fouls {(S ^ pushed).volume():.0f} mm3 of stop wall')

    print('\n2. ...and can be lowered straight in')
    worst = 0.0
    for d in (0.0, 2.0, 5.0, 10.0, 20.0, 40.0):
        v = (S ^ placed(cyl(B.r_body, -DEPTH, 0.0, 96), B, up=d)).volume()
        worst = max(worst, v)
    ck(worst < 1e-3, 'nothing is in the way on the way down',
       f'worst interference {worst:.5f} mm3 over a 40 mm lift')
    y_top = -(B.r_body + STAND_CLR)*math.cos(math.radians(STAND_WRAP))
    ck(abs(y_top) < B.r_body, 'the cradle stops short of the clock\'s widest point',
       f'walls end {(B.r_body - abs(y_top)):.1f} mm up a {2*B.r_body:.0f} mm disc, '
       f'so it lifts straight out')

    print('\n3. The USB plug clears the desk')
    ZP = Z_DECK - (PLATE_T + POCKET_DEEP) + PLATE_T
    z_win = ZP + USB_WIN_Z + USB_WIN_H/2                 # centre of the window
    back  = Z_FRONT - z_win                              # how far behind the front face
    # a straight plug: 20 mm of overmold, socket ~1 mm inside the rim
    reach = 20.0 - 1.0
    # 6 o'clock on the clock is -Y in the stand's build frame (+Y is "up in the
    # clock's own plane"), and the clock's tangential direction is X.
    p = placed(box_lwh(-PLUG_W/2, PLUG_W/2, -(B.r_body + reach), -(B.r_body - 2.0),
                       -back - PLUG_H/2, -back + PLUG_H/2), B)
    ck((S ^ p).volume() < 1e-3, 'the stand is cut away where the plug comes out',
       f'{(S ^ p).volume():.5f} mm3')
    zt = to_trimesh(p).bounds[0][2]
    ck(zt > 3.0, 'and the plug clears the desk itself',
       f'tip {zt:.1f} mm above it, {back:.0f} mm back from the face')
    # the lead can get out of the back
    lead = placed(box_lwh(-6.0, 6.0, -(B.r_body + 24.0), -(B.r_body - 2.0),
                          -DEPTH - STAND_STOP_T - 1.0, -back), B)
    ck((S ^ lead).volume() < 1e-3, 'and the lead runs out through the back of the stand',
       f'{(S ^ lead).volume():.5f} mm3')

    print('\n4. It does not foul anything on the clock')
    lo, hi = 180.0 - STAND_WRAP, 180.0 + STAND_WRAP
    ck(all(not (lo < a < hi) for a in B.vent_ang),
       'the cradle misses every vent', f'cradle {lo:.0f}-{hi:.0f} deg, vents {B.vent_ang}')
    ck(not (lo < 0.0 < hi), 'and the wall keyhole at 12 o\'clock stays clear')
    covered = [a for a in B.screw_ang if lo < a < hi]
    print(f'         housing screws at {covered} deg sit behind the stop wall -- '
          f'recessed, so nothing binds, but take the clock out to reach them')

    print('\n5. It stays up')
    b = St.bounds
    foot = (b[0][1], b[1][1])
    # clock CoM: ~480 g, roughly central in depth; stand ~ its own volume
    com_back = DEPTH/2 * math.cos(math.radians(T))
    ck(foot[0] < 0.0 and foot[1] > com_back + 15.0,
       'the footprint straddles the clock\'s centre of mass',
       f'footprint {foot[0]:.0f}..{foot[1]:.0f} mm, CoM about {com_back:.0f} mm back')
    h_com = STAND_LIFT + B.r_body*math.cos(math.radians(T))
    tip_b = math.degrees(math.atan2(foot[1] - com_back, h_com))
    tip_f = math.degrees(math.atan2(com_back - foot[0], h_com))
    ck(min(tip_b, tip_f) > 20.0, 'and it would have to be tipped a long way to go over',
       f'{tip_b:.0f} deg backwards, {tip_f:.0f} deg forwards')
    ck(b[1][0] - b[0][0] >= 2*B.r_body - 0.1, 'it is as wide as the clock',
       f'{b[1][0]-b[0][0]:.1f} mm')
    print(f'         stands {b[1][2]:.0f} mm tall, {2*B.r_body:.0f} x {foot[1]-foot[0]:.0f} mm '
          f'on the desk; the clock leans back {T:.0f} deg')

print()
if FAIL:
    print(f'CHECK 5: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('CHECK 5: the clock sits in the stand and can be plugged in on a desk')
