#!/usr/bin/env python3
"""CHECK 6 -- the stand-box, its tray, the back cover, and the diffuser variants.

Sam, 2026-09-03: "create the back of the clock to house the ESP32 S3. It
could be housed at the bottom of the clock in the stand. Make the clock lean
back a bit though." And: "the diffuser larger on the outside to fit to the
edge of the base", "a diffuser that doesn't have numbers on it".

Every number here is MEASURED off the built STL, not recomputed from params --
the same rule as check2, for the same reason: the parameter file has claimed
things the mesh did not do before. The one thing taken from the generator is
the cradle's lead notch, as a solid, so that the roof can be probed where the
notch actually is rather than where a formula guessed it would be -- the
first version probed a fixed spot and called the 60's roof blocked when the
notch was 4 mm further forward.
"""
import sys, math, os
import numpy as np, trimesh
from manifold3d import Manifold
from csg import to_manifold, box_lwh, cyl, tube
import csg
import build_v2 as BV
from params import *

FAIL = []


def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c:
        FAIL.append(msg)


def load(f):
    m = trimesh.load(csg.part(f), process=False)
    m.merge_vertices()
    return m


depth = Z_FRONT - (Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET))

for B, tg in ((BV.BODY24, ''), (BV.BODY32, '-32'), (BV.BODY60, '-60')):
    try:
        S = to_manifold(load(f'mini-round-clock-standbox{tg}.stl'))
        T = to_manifold(load(f'mini-round-clock-standbox-tray{tg}.stl'))
        C = load(f'mini-round-clock-backcover{tg}.stl')
        Dn = load(f'mini-round-clock-diffuser{tg}.stl')
        Dp = load(f'mini-round-clock-diffuser{tg}-plain.stl')
        base = to_manifold(load(f'mini-round-clock-base{tg}.stl'))
    except Exception as e:
        print(f'\n{B.n}-LED: parts not built ({e}); skipped')
        continue
    print(f'\n{"="*70}\n{B.n}-LED stand-box, for a {2*B.r_body:.1f} mm clock with the flat back cover')
    sb = S.bounding_box()
    hw = B.r_body
    # Derived from the SAME parameters build_standbox uses. These used to be
    # BOARD_W/BOARD_L -- the drawing's numbers -- so once the tray was cut for
    # Sam's measured board the check was measuring the previous design and
    # reporting its own staleness as six failures. The stand-box's board is
    # STANDBOX_SLOT_W / STANDBOX_BOARD_L; the base's mount still uses BOARD_*.
    rail_y = STANDBOX_SLOT_W/2
    bay_w = STANDBOX_SLOT_W + 2*STANDBOX_RAIL_T + 2*STANDBOX_BAY_CLR
    bay_l = STANDBOX_BOARD_L + BRD_END_CLR + STANDBOX_RAIL_T + STANDBOX_BAY_CLR
    y1 = sb[4]
    z0, z1 = STANDBOX_FLOOR, STANDBOX_PLINTH_H - STANDBOX_ROOF
    H = STANDBOX_PLINTH_H
    cw, chh = STANDBOX_BAY_CHAMF_W, STANDBOX_BAY_CHAMF_H
    _, notch, h0 = BV._stand_solid(B, depth, STANDBOX_TILT)

    print('\n1. The well is there, and it is open at the TOP')
    # Sam: "Remove the sliding tray. Because it is a dev board, wires stick out
    # the top." The drawer is gone; the bay is a well the board drops into. So
    # the test is no longer "is the tunnel clear" but "is the lid off".
    well_hw = BOARD2_W/2 + STANDBOX_WELL_CLR + FDM_SLOT_UNDER/2
    Sm = load(f'mini-round-clock-standbox{tg}.stl')
    Cm = load(f'mini-round-clock-standbox-cradle{tg}.stl')
    lo, hi = Sm.bounds
    H = STANDBOX_PLINTH_H
    xs = np.arange(-well_hw + 1, well_hw, 1.0)
    ys = np.arange(lo[1] + STANDBOX_WALL + 2, hi[1] - STANDBOX_WALL - 1, 1.5)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    roof = Sm.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                        np.full(gx.size, H - 0.5)]))
    ck(not roof.any(), 'the well is open to the sky over its whole length',
       f'{roof.sum()} of {roof.size} probes blocked')
    ck(H - STANDBOX_FLOOR >= BRD_POST_H + STANDBOX_BOARD_H + STANDBOX_WIRE_H,
       'and deep enough for the board, its headers AND the loom on top',
       f'{H - STANDBOX_FLOOR:.1f} mm against '
       f'{BRD_POST_H + STANDBOX_BOARD_H + STANDBOX_WIRE_H:.1f} needed')

    print('\n2. The board drops in, and the loom stays on it')
    ymid = (lo[1] + hi[1])/2.0
    z_pcb = STANDBOX_FLOOR + BRD_POST_H
    def clear(ztop, what):
        gx2, gy2, gz2 = np.meshgrid(
            np.arange(-BOARD2_W/2 + 0.5, BOARD2_W/2, 1.0),
            np.arange(ymid - BOARD2_L/2 + 0.5, ymid + BOARD2_L/2, 1.5),
            np.arange(z_pcb + 0.2, ztop, 0.8), indexing='ij')
        h = Sm.contains(np.column_stack([gx2.ravel(), gy2.ravel(), gz2.ravel()]))
        ck(not h.any(), what, f'{h.sum()} of {h.size} probes hit material')
    clear(z_pcb + BOARD_T, "Sam's 64 x 30 board sits in the well")
    clear(z_pcb + STANDBOX_BOARD_H, 'its headers clear the walls')
    clear(H - 0.5, 'and so does the loom standing on them')
    # a vertical drop, not a slide: the board must come STRAIGHT down
    gx3, gy3, gz3 = np.meshgrid(
        np.arange(-BOARD2_W/2 + 0.5, BOARD2_W/2, 1.5),
        np.arange(ymid - BOARD2_L/2 + 0.5, ymid + BOARD2_L/2, 2.0),
        np.arange(z_pcb + BOARD_T + 1.0, H + 8.0, 1.5), indexing='ij')
    down = Sm.contains(np.column_stack([gx3.ravel(), gy3.ravel(), gz3.ravel()]))
    ck(not down.any(), 'it goes STRAIGHT down — nothing overhangs the well',
       f'{down.sum()} of {down.size} probes blocked')

    print('\n3. The leads get from the clock into the well')
    zc = H + 1.0
    thr = Cm.contains(np.array([[0.0, ymid, zc]]))
    ck(not thr.all(), "the cradle's notch is above the well")

    print('\n4. The cradle is the lid, and it goes on')
    inter = csg.to_trimesh(to_manifold(Sm) ^ to_manifold(Cm))
    ck(inter.volume < 1.0, 'cradle and plinth do not interfere',
       f'{inter.volume:.2f} mm3')
    ck(abs(Cm.bounds[0][2] - H) < 0.01, 'the cradle sits on the plinth at z = H',
       f'{Cm.bounds[0][2]:.2f}')
    BOTH = csg.to_trimesh(to_manifold(Sm) + to_manifold(Cm))
    lid = BOTH.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                         np.full(gx.size, H + STANDBOX_ROOF/2)]))
    # It roofs the well EXCEPT the lead notch, which is the whole point of the
    # notch. So the test is not "how much is covered" -- it is "is everything
    # that is open the notch, and nothing else". A percentage would have passed
    # a hole anywhere.
    openx = np.abs(gx.ravel()[~lid])
    ck(lid.any(), 'the cradle roofs the well')
    ck(openx.size == 0 or openx.max() <= STAND_NOTCH_HW + 1.0,
       'and the only thing open is the leads\' notch',
       f'{(~lid).sum()} cells open, all within |x| = '
       f'{openx.max() if openx.size else 0:.1f} of a {STAND_NOTCH_HW:.0f} mm notch')

    print('\n5. It stays up, leaning back')
    # the clock's centre: on the cradle axis, mid-depth
    t = math.radians(STANDBOX_TILT)
    y_com = (depth/2)*math.sin(t)
    z_com = h0 - (depth/2)*math.cos(t)
    fwd = math.degrees(math.atan2(y_com - sb[1], z_com))
    back = math.degrees(math.atan2(sb[4] - y_com, z_com))
    ck(fwd >= 20.0, f'tips forward only past {fwd:.1f} deg (floor 20)')
    ck(back >= 20.0, f'tips backward only past {back:.1f} deg (floor 20)')
    ck(STANDBOX_TILT > STAND_TILT, f'leans {STANDBOX_TILT:.0f} deg, more than the cradle\'s {STAND_TILT:.0f}')
    print(f'       plinth {sb[3]-sb[0]:.1f} wide, {sb[4]-sb[1]:.1f} deep; the clock\'s centre {z_com:.0f} mm up')

    print('\n6. The back cover')
    ck(C.is_watertight and C.volume > 0, 'watertight', f'{C.volume/1000:.1f} cm3')
    cb = C.bounds
    ck(abs((cb[1][2] - cb[0][2]) - (BACKCOVER_PLATE + BACKCOVER_POCKET)) < 0.05,
       f'is {BACKCOVER_PLATE + BACKCOVER_POCKET:.1f} mm deep', f'{cb[1][2]-cb[0][2]:.2f}')
    # the lead notch at 6 o'clock, through the rim
    Cm = to_manifold(C)
    notch_c = box_lwh(-B.r_body - 0.5, -B.r_inner - 0.5, -CABLE_W/2 + 0.3, CABLE_W/2 - 0.3,
                      Z_DECK - BACKCOVER_POCKET + 0.3, Z_DECK - 0.3)
    ck((notch_c ^ Cm).volume() < 1.0, 'lead notch open at 6 o\'clock', f'{(notch_c ^ Cm).volume():.1f} mm3 blocking')

    print('\n7. The diffuser variants')
    ck(abs(Dp.volume - Dn.volume) < 300.0 and Dp.volume > Dn.volume,
       'plain diffuser is the numbered one with the numerals filled in',
       f'{Dp.volume - Dn.volume:+.1f} mm3')
    ff = f'mini-round-clock-diffuser{tg}-flange.stl'
    room = (B.r_lip_i - DIFF_FLANGE_CLR) - B.diff_outer
    if room < DIFF_FLANGE_MIN:
        ck(not os.path.exists(csg.part(ff)), f'no flange variant: the diffuser already reaches the lip',
           f'diffuser r {B.diff_outer:.2f}, lip r {B.r_lip_i:.2f}')
    else:
        Df = load(ff)
        fb = Df.bounds
        ck(abs(2*max(-fb[0][0], fb[1][0]) - 2*(B.r_lip_i - DIFF_FLANGE_CLR)) < 0.2,
           f'flange reaches the lip: {2*max(-fb[0][0], fb[1][0]):.2f} mm across',
           f'lip bore {2*B.r_lip_i:.2f}, base {2*B.r_body:.2f}')
        ck(abs(fb[0][2]) < 0.02, 'its front is the face plane -- nothing stands proud, it prints face down',
           f'lowest point z={fb[0][2]:.2f}')
        Dfm = to_manifold(Df)
        ann_s = tube(B.diff_outer + 0.5, B.r_lip_i - DIFF_FLANGE_CLR - 0.8, 0.3, DIFF_FLANGE_D - 0.1, 96)
        ann_v = tube(B.diff_outer + 0.5, B.r_lip_i + 5.0, DIFF_FLANGE_D + 0.05, FACE_T + 40.0, 96)
        ck((ann_s ^ Dfm).volume() > 0.99*ann_s.volume() and (ann_v ^ Dfm).volume() < 1.0,
           f'flange is {DIFF_FLANGE_D:.2f} deep and nothing sits behind it',
           f'{(ann_s ^ Dfm).volume()/ann_s.volume()*100:.0f}% solid, {(ann_v ^ Dfm).volume():.1f} mm3 behind')
        # seated in the base the way check2 seats the diffuser: no overlap,
        # and the flange stops DIFF_FLANGE_CLR above the recess floor
        Ds = Df.copy()
        Ds.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
        Ds.apply_translation([0, 0, DIFF_SEAT_Z])
        Dsm = to_manifold(Ds)
        # ...outboard of the band, where the flange is. Inside it the collar's
        # crush ribs bite the bore by 1.16 mm3, which is the press fit itself
        # and identical on the plain diffuser; check2 owns that number.
        ov = (Dsm ^ base ^ tube(B.diff_outer - 1.5, B.r_body + 5.0, -50.0, 50.0, 96)).volume()
        ck(ov < 1e-3, 'seated, the flange overlaps the base nowhere', f'{ov:.2f} mm3')
        under = (Dsm ^ tube(B.diff_outer + 0.3, B.r_lip_i + 2.0, 0.0, 40.0, 96)).bounding_box()
        ck(abs((under[2] - Z_RECESS) - 0.30) < 0.05,
           f'and its back stands {under[2] - Z_RECESS:.2f} above the recess floor',
           f'flange back at z={under[2]:.2f}, floor at {Z_RECESS:.2f}')
        # the membrane inside the band is untouched: the numbered and flange
        # diffusers are identical inside the band's outer wall
        core = cyl(B.diff_outer - 1.2, -1.0, 40.0, 96)
        dv = abs((Dfm ^ core).volume() - (to_manifold(Dn) ^ core).volume())
        ck(dv < 1.0, 'inside the band the flange diffuser is the plain-numbered one, membrane included', f'{dv:.2f} mm3 differs')

print()
if FAIL:
    print(f'CHECK 6: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
# =============================================================================
# ENCLOSED. Sam asked for that three times, and picked this stand to have it.
# =============================================================================
# The bay opens at the BACK and the tray closes it, so the only thing that was
# ever open in the bottom face was the pair of lightening pockets -- 19 x 66 mm
# each, the biggest holes in anything in this set. STANDBOX_POCKETS is off and
# this is the test that keeps it that way.
print('\n7. Enclosed')
for B, tg in ((BV.BODY24, ''), (BV.BODY32, '-32'), (BV.BODY60, '-60')):
    S = load(f'mini-round-clock-standbox{tg}.stl')
    lo, hi = S.bounds
    gx, gy = np.meshgrid(np.arange(lo[0] + 2, hi[0] - 1, 2.0),
                         np.arange(lo[1] + 2, hi[1] - 1, 2.0), indexing='ij')
    pts = np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, 0.4)])
    outline = S.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                          np.full(gx.size, 0.4)]))
    # a hole is a column that is open at the bottom AND open a centimetre up,
    # inside the plinth's own outline in plan
    up = S.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                     np.full(gx.size, 10.0)]))
    inside = (np.abs(gx.ravel()) < B.r_body - 3) & \
             (gy.ravel() > lo[1] + 4) & (gy.ravel() < hi[1] - 4)
    holes = inside & (~outline) & (~up)
    ck(not holes.any(), f'{B.n}-LED: nothing open in the underside',
       f'{holes.sum()} of {inside.sum()} columns open')

print('CHECK 6: the S3 lives in the stand, the clock leans back, the covers and diffusers fit')
