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
import build_v2 as BV
from params import *

FAIL = []


def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c:
        FAIL.append(msg)


def load(f):
    m = trimesh.load(f, process=False)
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
    bay_w = BOARD_W + 2*(BRD_RAIL_CLR + STANDBOX_RAIL_T) + 2*STANDBOX_BAY_CLR
    bay_l = BOARD_L + BRD_END_CLR + STANDBOX_RAIL_T + STANDBOX_BAY_CLR
    y1 = sb[4]
    z0, z1 = STANDBOX_FLOOR, STANDBOX_PLINTH_H - STANDBOX_ROOF
    H = STANDBOX_PLINTH_H
    cw, chh = STANDBOX_BAY_CHAMF_W, STANDBOX_BAY_CHAMF_H
    _, notch, h0 = BV._stand_solid(B, depth, STANDBOX_TILT)

    print('\n1. The bay is there, the right size, and open at the back')
    # the tray's length of bay from the back face: full width up to the
    # chamfers, and the narrower flat up to the roof -- all void
    lo = box_lwh(-bay_w/2 + 0.3, bay_w/2 - 0.3, y1 - bay_l + 0.3, y1 + 0.5, z0 + 0.3, z1 - chh - 0.3)
    hi = box_lwh(-bay_w/2 + cw + 0.3, bay_w/2 - cw - 0.3, y1 - bay_l + 0.3, y1 + 0.5, z1 - chh, z1 - 0.3)
    left = (lo ^ S).volume() + (hi ^ S).volume()
    ck(left < 1.0, f'bay {bay_w:.1f} x {bay_l:.1f} x {z1-z0:.1f} mm is clear', f'{left:.1f} mm3 of solid in it')
    ck(z1 - z0 >= BRD_POST_H + BOARD_T + 14.0,
       'bay is tall enough for the board and the leads on top of it',
       f'{z1-z0:.1f} clear, needs {BRD_POST_H + BOARD_T + 14.0:.1f}')
    # the roof is bridged: measure the flat ceiling's width at the roof plane
    roof = box_lwh(-bay_w/2 - 1.0, bay_w/2 + 1.0, y1 - bay_l + 5.0, y1 - bay_l + 6.0, z1 - 0.2, z1 - 0.05)
    void = roof - (roof ^ S)
    vb = void.bounding_box()
    ck(vb[3] - vb[0] <= 25.0, f'the bay roof\'s flat span is {vb[3]-vb[0]:.1f} mm (check3 allows 25)')
    # ...and the chamfers under it are steeper than 45 deg
    ck(chh / cw > 1.0, f'chamfers are {math.degrees(math.atan2(chh, cw)):.1f} deg from the horizontal')

    print('\n2. The tray fits the bay, and the board fits the tray')
    tb = T.bounding_box()
    ck(abs((tb[3] - tb[0]) - (bay_w + 2*STANDBOX_LID_LIP)) < 0.2,
       'tray is the bay plus the lid lips wide', f'{tb[3]-tb[0]:.2f} mm')
    ck(abs(tb[2]) < 0.02 and abs(tb[5] - (H - z0)) < 0.05,
       'it sits flat: nothing below the floor plane, the lid reaches the roof',
       f'z {tb[2]:.2f} .. {tb[5]:.2f}, roof at {H - z0:.2f}')
    # the tray proper (without the lid) must be narrower than the bay by the
    # worst FDM slot loss, and the board must fit between the rails the same way
    body = T ^ box_lwh(-100, 100, 0.5, 200, -10, 100)     # everything past the lid
    bb = body.bounding_box()
    ck(bay_w - (bb[3] - bb[0]) >= 2*FDM_SLOT_UNDER,
       'tray clears the bay even when the bay prints narrow',
       f'{bay_w - (bb[3]-bb[0]):.2f} mm total, needs {2*FDM_SLOT_UNDER:.2f}')
    # the board's own envelope, on the pads, is clear of everything
    slot = box_lwh(-BOARD_W/2 - 0.2, BOARD_W/2 + 0.2, 5.0, BOARD_L - 5.0,
                   STANDBOX_TRAY_T + BRD_POST_H + 0.3, STANDBOX_TRAY_T + BRD_POST_H + BOARD_T - 0.3)
    ck((slot ^ T).volume() < 1.0, 'the board slot between the rails is clear of the pads',
       f'{(slot ^ T).volume():.1f} mm3 in the way')
    rails = box_lwh(-BRD_RAIL_Y - STANDBOX_RAIL_T + 0.3, BRD_RAIL_Y + STANDBOX_RAIL_T - 0.3,
                    10, BOARD_L - 10, STANDBOX_TRAY_T + 0.5, STANDBOX_TRAY_T + STANDBOX_RAIL_H - 0.5) - \
            box_lwh(-BRD_RAIL_Y - 0.3, BRD_RAIL_Y + 0.3, 0, 200, -10, 100)
    ck((rails ^ T).volume() > 0.8 * rails.volume(), 'both rails are there', f'{(rails ^ T).volume()/rails.volume()*100:.0f}% present')
    # the hooks over the far corners, and nothing between them
    tray_l = BOARD_L + BRD_END_CLR + STANDBOX_RAIL_T
    hy0, hy1 = tray_l - STANDBOX_RAIL_T - STANDBOX_BAR_W + 0.3, tray_l - STANDBOX_RAIL_T - 0.3
    hz0, hz1 = STANDBOX_TRAY_T + BRD_LIP_Z0 + 0.3, STANDBOX_TRAY_T + BRD_RAIL_TOP - 0.3
    hooks = box_lwh(-BRD_RAIL_Y + 0.3, -BRD_RAIL_Y + STANDBOX_HOOK_W - 0.3, hy0, hy1, hz0, hz1) + \
            box_lwh(BRD_RAIL_Y - STANDBOX_HOOK_W + 0.3, BRD_RAIL_Y - 0.3, hy0, hy1, hz0, hz1)
    gap = box_lwh(-BRD_RAIL_Y + STANDBOX_HOOK_W + 0.3, BRD_RAIL_Y - STANDBOX_HOOK_W - 0.3, hy0, hy1, hz0, hz1)
    ck((hooks ^ T).volume() > 0.9 * hooks.volume() and (gap ^ T).volume() < 1.0,
       f'two {STANDBOX_HOOK_W:.0f} mm hooks over the far corners, open between them',
       f'{(hooks ^ T).volume()/hooks.volume()*100:.0f}% hook, {(gap ^ T).volume():.1f} mm3 between')
    # USB window in the lid, at the connector height
    z_usb = STANDBOX_TRAY_T + BRD_POST_H + BOARD_T + BOARD_TALL/2
    win = box_lwh(-USB_WIN_W/2 + 0.3, USB_WIN_W/2 - 0.3, -STANDBOX_LID_T - 0.5, 0.5,
                  z_usb - USB_WIN_H/2 + 0.3, z_usb + USB_WIN_H/2 - 0.3)
    ck((win ^ T).volume() < 1.0, f'USB-C window {USB_WIN_W:.0f} x {USB_WIN_H:.0f} open in the lid', f'{(win ^ T).volume():.1f} mm3 blocking')

    print('\n3. The leads can get from the clock into the bay')
    # the cradle's own notch, from 3 mm inside the bay up through the roof
    # and 6 mm into the cradle: all of it void, and there is enough of it
    p = notch ^ box_lwh(-200, 200, -200, 200, z1 - 3.0, H + 6.0)
    pb = p.bounding_box()
    blocked = (p ^ S).volume()
    ck(blocked < 1.0 and p.volume() > 200.0,
       f'the notch runs through the roof into the bay, at y {pb[1]:.0f}..{pb[4]:.0f}',
       f'{blocked:.1f} mm3 in the way, {p.volume():.0f} mm3 of notch')

    print('\n4. The lid screws have something to bite')
    zs = (z0 + z1)/2
    for sx in (-1, 1):
        xs = sx*(bay_w/2 + 4.5)
        # the pilot is drilled STANDBOX_WALL + STANDBOX_BOSS_L - 1 deep from
        # the back face (it starts 1 mm inside the pillar's front); probe it
        # 0.3 short of that, and the 5 mm of material around it
        pd = STANDBOX_WALL + STANDBOX_BOSS_L - 1.0
        pilot = cyl(STANDBOX_SCREW_PILOT/2 - 0.2, 0.0, pd - 0.3, 24,
                    centre=(xs, 0.0)).rotate([-90.0, 0.0, 0.0]) \
                    .translate([0.0, y1 - pd + 0.3, zs])
        meat = (box_lwh(xs - 2.5, xs + 2.5, y1 - pd + 0.3, y1 - 0.3, zs - 2.5, zs + 2.5)
                - cyl(STANDBOX_SCREW_PILOT/2 + 0.2, -1.0, 30.0, 24, centre=(xs, 0.0))
                      .rotate([-90.0, 0.0, 0.0]).translate([0.0, y1 - 20.0, zs]))
        ck((pilot ^ S).volume() < 0.5 and (meat ^ S).volume() > 0.97*meat.volume(),
           f'pilot at x={xs:+.1f}: {pd:.1f} mm deep with solid all round',
           f'{(pilot ^ S).volume():.1f} mm3 in the hole, {(meat ^ S).volume()/meat.volume()*100:.0f}% solid around it')

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
        ck(not os.path.exists(ff), f'no flange variant: the diffuser already reaches the lip',
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
print('CHECK 6: the S3 lives in the stand, the clock leans back, the covers and diffusers fit')
