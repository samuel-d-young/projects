#!/usr/bin/env python3
"""CHECK 6 -- the stand-box, the back cover, and the diffuser variants.

Sam, 2026-09-08: "Make the base look much nicer, and the bottom can be fully
open, with a spot for ziptie down the ESP32 with the USB cable out he back."

That permission -- the bottom CAN be open -- turned the stand back into ONE
part, so most of what this file used to test (a tray that slides, a cradle lid
that drops on four pins, a floor that must not have holes in it) is gone with
the parts it tested. What replaces it is the same discipline: every number is
MEASURED off the built STL, not recomputed from params, because the parameter
file has claimed things the mesh did not do before.

The two faults this file caught on the day it was rewritten are worth keeping
in mind, because neither was visible in a render:

  * the shelf ran unbroken from the board's edge out to the wall, so the cable
    tie Sam asked for had nowhere to pass. A tie can loop under a shelf only
    where there is a hole to get under it through.
  * the shelves were 22 mm apart and the board is 30 mm wide, so it could only
    be got in by rolling it 43 degrees inside 22 mm of headroom, one-handed,
    with a soldered loom hanging off it.

Both are the same class of mistake: a part that is the right shape and cannot
be assembled. So the tests here are journeys -- the board's way in, the tie's
way round, the USB lead's way out -- and not shapes.
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


def runs(vals, mask):
    """The contiguous runs of True in mask, as (first, last) pairs of vals."""
    out, prev = [], False
    for v, c in zip(vals, mask):
        if c and not prev:
            out.append([v, v])
        elif c:
            out[-1][1] = v
        prev = c
    return [tuple(r) for r in out]


def solid_run(m, axis, vals, at):
    """Where along `axis` the mesh is solid, with the other two coords fixed."""
    pts = np.tile(np.asarray(at, float), (len(vals), 1))
    pts[:, axis] = vals
    return runs(vals, m.contains(pts))


depth = Z_FRONT - (Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET))

for B, tg in ((BV.BODY24, ''), (BV.BODY32, '-32'), (BV.BODY60, '-60')):
    try:
        Sm = load(f'mini-round-clock-standbox{tg}.stl')
        S = to_manifold(Sm)
        C = load(f'mini-round-clock-backcover{tg}.stl')
        Dn = load(f'mini-round-clock-diffuser{tg}.stl')
        Dp = load(f'mini-round-clock-diffuser{tg}-plain.stl')
        base = to_manifold(load(f'mini-round-clock-base{tg}.stl'))
    except Exception as e:
        print(f'\n{B.n}-LED: parts not built ({e}); skipped')
        continue
    print(f'\n{"="*70}\n{B.n}-LED stand-box, one part, open underneath, for a {2*B.r_body:.1f} mm clock')
    lo, hi = Sm.bounds
    sb = [lo[0], lo[1], lo[2], hi[0], hi[1], hi[2]]
    H = STANDBOX_PLINTH_H
    cradle_m, notch, h0 = BV._stand_solid(B, depth, STANDBOX_TILT)
    cradle = csg.to_trimesh(cradle_m); cradle.merge_vertices()

    # ---- MEASURE the cavity, the shelves and the board's seat --------------
    ymid = (lo[1] + hi[1])/2.0
    xs = np.arange(lo[0] - 1.0, hi[0] + 1.0, 0.25)
    ys = np.arange(lo[1] + 0.25, hi[1], 0.25)
    zs = np.arange(0.25, H + 0.25, 0.25)
    # cavity: the open run about x = 0 at a height below the shelves
    z_low = STANDBOX_SHELF_Z/2.0
    solid_x = runs(xs, ~Sm.contains(np.column_stack(
        [xs, np.full(xs.size, ymid), np.full(xs.size, z_low)])))
    cav_x = [r for r in solid_x if r[0] <= 0.0 <= r[1]]
    chw = min(-cav_x[0][0], cav_x[0][1]) if cav_x else 0.0
    open_y = [r for r in runs(ys, ~Sm.contains(
        np.column_stack([np.zeros(ys.size), ys, np.full(ys.size, z_low)])))
        if r[1] - r[0] > 20.0]
    cy0, cy1 = open_y[0]
    # The board sits at the BACK of the cavity, which on the 60 is 99.5 mm deep
    # for a 64 mm board -- so everything about the board is measured at the
    # BOARD's mid-length and not the plinth's. Reading the shelf at the plinth's
    # midpoint found no shelf on the 60 and reported the part as broken.
    by1, by0 = cy1 - 1.0, cy1 - 1.0 - BOARD2_L
    bymid = (by0 + by1)/2.0
    # the shelf, read at mid-board where no tie window cuts it
    sh = solid_run(Sm, 2, zs, (chw - 1.0, bymid, 0.0))
    sh = [r for r in sh if r[1] < H - 8.0]
    ck(len(sh) == 1, 'there is one shelf on each side, and it is a shelf and not a wall',
       f'solid runs in z at x={chw-1:.1f}: {sh}')
    z_seat = sh[0][1] + 0.25 if sh else STANDBOX_SHELF_Z + STANDBOX_SHELF_T
    # its inner edge, at the shelf's own mid-height
    sx = solid_run(Sm, 0, xs, (0.0, bymid, (sh[0][0] + sh[0][1])/2.0)) if sh else []
    shelf_xi = min(abs(r[0]) for r in sx if r[0] > 0.0) if sx else 0.0
    # The ceiling. NOT straight up the middle: the leads' notch is at x = 0 and a
    # column there runs clean out of the top of the part, which read the ceiling
    # as 34 and let three tests pass that should not have. Take the LOWEST first
    # solid over a fan of columns clear of the notch, which is what a board
    # standing in the cavity would actually meet.
    czs = np.arange(STANDBOX_SHELF_Z + STANDBOX_SHELF_T + 1.0, H + 0.5, 0.5)
    cys = np.arange(cy0 + 3.0, cy1 - 2.0, 4.0)

    def ceiling(xlist):
        xa = np.array([x for x in xlist if abs(x) > STAND_NOTCH_HW + 1.0])
        G = np.array(np.meshgrid(xa, cys, czs, indexing='ij')).reshape(3, -1).T
        hit = Sm.contains(G).reshape(-1, len(czs))
        z = [czs[h.argmax()] for h in hit if h.any()]
        return min(z) if z else H
    # the flat middle, and the board's own edge, where the chamfer bites and
    # where the loom's connectors actually stand
    ceil = ceiling(np.arange(-STANDBOX_CAV_HW + STANDBOX_BAY_CHAMF_W + 1.0,
                             STANDBOX_CAV_HW - STANDBOX_BAY_CHAMF_W, 2.0))
    ceil_edge = ceiling([-BOARD2_W/2.0, BOARD2_W/2.0])
    print(f'       cavity {2*chw:.1f} wide x {cy1-cy0:.1f} deep, ceiling z={ceil:.1f} flat '
          f'({ceil_edge:.1f} at the board\'s edge); shelves {2*shelf_xi:.1f} apart, '
          f'top at z={z_seat:.1f}')

    print('\n1. The bottom is open, which is the thing that made it one part')
    gx, gy = np.meshgrid(np.arange(-chw + 1.5, chw - 1.0, 1.0),
                         np.arange(cy0 + 1.5, cy1 - 1.0, 1.5), indexing='ij')
    floor = Sm.contains(np.column_stack([gx.ravel(), gy.ravel(),
                                         np.full(gx.size, 0.30)]))
    ck(not floor.any(), 'nothing at all across the cavity mouth',
       f'{floor.sum()} of {floor.size} probes hit material, '
       f'{2*chw*(cy1-cy0)/100:.1f} cm2 open')
    # and open all the way up to the shelves, so a hand and a board can get in
    gz = np.arange(0.30, STANDBOX_SHELF_Z - 0.3, 1.0)
    g3 = np.array(np.meshgrid(np.arange(-chw + 1.5, chw - 1.0, 1.5),
                              np.arange(cy0 + 1.5, cy1 - 1.0, 2.0), gz,
                              indexing='ij')).reshape(3, -1).T
    ck(not Sm.contains(g3).any(), 'and clear right up to the shelves',
       f'{Sm.contains(g3).sum()} of {len(g3)} probes')

    print('\n2. The board gets in — tilted, from underneath')
    # 30 mm of board cannot pass flat between shelves that are less than 30
    # apart, so it goes in rolled. The angle is not a preference, it is
    # acos(gap / width) corrected for the board's own thickness, and it is what
    # Sam has to do with his hands, so it is measured and it is reported.
    half, t2 = BOARD2_W/2.0, BOARD_T/2.0
    gap_h = shelf_xi - 0.40           # 0.4 of knuckle room per side
    th = None
    for d in np.arange(0.0, 60.0, 0.5):
        r = math.radians(d)
        if half*math.cos(r) + t2*math.sin(r) <= gap_h:
            th = d
            break
    ck(th is not None, 'there is a roll angle at which the board passes the shelves')
    if th is not None:
        swept = 2*(half*math.sin(math.radians(th)) + t2*math.cos(math.radians(th)))
        head = ceil - z_seat
        ck(th <= 32.0, f'and it is {th:.0f} deg, not a contortion (ceiling 32)',
           f'{2*shelf_xi:.1f} mm gap for a {BOARD2_W:.0f} mm board')
        ck(swept <= head, f'rolled that far it sweeps {swept:.1f} mm into {head:.1f} of headroom')
        # now prove it with the actual mesh: the rolled board, lifted through
        # the shelves in half-millimetre steps, must never touch anything
        brd = box_lwh(-half, half, by0, by1, -t2, t2).rotate([0.0, 0.0, 0.0])
        rolled = box_lwh(-half, half, by0, by1, -t2, t2)
        rolled = rolled.rotate([0.0, th + 2.0, 0.0])
        worst, worst_z = 0.0, None
        for z in np.arange(STANDBOX_SHELF_Z - 3.0, z_seat + swept/2.0 + 0.5, 0.5):
            v = (S ^ rolled.translate([0.0, 0.0, float(z)])).volume()
            if v > worst:
                worst, worst_z = v, z
        ck(worst < 1.0, 'and the mesh agrees: it lifts through without touching',
           f'worst {worst:.2f} mm3' + (f' at z={worst_z:.1f}' if worst_z else ''))
        # then it rolls flat at the top, clear of the ceiling and the chamfers
        top = z_seat + swept/2.0 + 0.5
        worst = max((S ^ box_lwh(-half, half, by0, by1, -t2, t2)
                     .rotate([0.0, float(a), 0.0]).translate([0.0, 0.0, top])).volume()
                    for a in np.arange(0.0, th + 2.5, 2.5))
        ck(worst < 1.0, 'and rolls flat once it is above them', f'worst {worst:.2f} mm3')

    print('\n3. Seated, the board and everything standing on it clear the walls')
    # Each thing is probed over the width IT occupies. Probing all of them over
    # the full 30 mm was what turned a 3 mm shortfall at the board's edges into
    # a pass: the chamfer takes its headroom exactly where the headers are.
    def clear(hx, ztop, what, dz=0.8):
        g = np.array(np.meshgrid(
            np.arange(-hx + 0.5, hx, 1.0),
            np.arange(by0 + 0.5, by1, 1.5),
            np.arange(z_seat + 0.2, ztop, dz), indexing='ij')).reshape(3, -1).T
        h = Sm.contains(g)
        ck(not h.any(), what, f'{h.sum()} of {h.size} probes hit material')
    hdr = chw - STANDBOX_BAY_CHAMF_W      # where the flat ceiling runs out to
    need = BOARD_T + STANDBOX_BOARD_H + STANDBOX_WIRE_H
    clear(half, z_seat + BOARD_T, "Sam's 64 x 30 board lies on the shelves")
    clear(hdr, z_seat + BOARD_T + STANDBOX_BOARD_H,
          f'its headers and their Dupont housings clear the walls out to |x| {hdr:.0f}')
    clear(hdr - 2.0, z_seat + need, 'and so does the loom standing on them')
    ck(ceil - z_seat >= need, 'the headroom is the sum of what has to live in it',
       f'{ceil - z_seat:.1f} mm against {need:.1f} needed')
    ck(ceil_edge - z_seat >= BOARD_T + 2.0,
       'and the board\'s own edge is under a ceiling, not a chamfer',
       f'{ceil_edge - z_seat:.1f} mm at |x| = {half:.0f}')
    ck(half - shelf_xi >= 1.0, 'the board actually lands on the shelves',
       f'{half - shelf_xi:.1f} mm of ledge under each edge')
    # and what hangs BELOW it. With the bottom open the board's solder tails
    # have the whole desk under them, but "the whole desk" is only 4.5 mm on a
    # shelf this low, and the tie's loop is in there with them.
    # BRD_POST_H is the repo's existing allowance for header tails under the
    # PCB -- it is what the old design stood the board off its floor by. With
    # the bottom open there is no floor, but there is a desk.
    ck(z_seat - BRD_POST_H >= 1.0,
       'the board\'s solder tails clear the desk',
       f'{z_seat - BRD_POST_H:.1f} mm under the {BRD_POST_H:.1f} mm tail allowance')
    ck(z_seat - STANDBOX_SHELF_T - 1.2 >= 0.5,
       'and the tie\'s loop passes under the shelf without touching the desk',
       f'{z_seat - STANDBOX_SHELF_T:.1f} mm of air under the shelf, tie is ~1.2 thick')

    print('\n4. Each cable tie can be threaded — over the board, through the shelf, under it')
    # Sam asked for "a spot for ziptie down the ESP32". A spot is not a groove:
    # it is a closed path. This walks the path.
    ties = (by0 + STANDBOX_TIE_INSET, by1 - STANDBOX_TIE_INSET)
    x_win = (STANDBOX_TIE_WIN_XI + chw)/2.0
    for i, ty in enumerate(ties, 1):
        blocked = []
        # (a) down through the shelf, outboard of the board's edge, both sides
        for sgn in (-1.0, 1.0):
            col = np.column_stack([np.full(24, sgn*x_win), np.full(24, ty),
                                   np.linspace(STANDBOX_SHELF_Z - 1.0,
                                               STANDBOX_SHELF_Z + STANDBOX_SHELF_T + 1.0, 24)])
            if Sm.contains(col).any():
                blocked.append(f'window at x={sgn*x_win:+.1f}')
        # (b) across the open bottom, under the shelves, from one to the other
        under = np.column_stack([np.linspace(-x_win, x_win, 60),
                                 np.full(60, ty),
                                 np.full(60, STANDBOX_SHELF_Z - 1.5)])
        if Sm.contains(under).any():
            blocked.append('the crossing under the shelves')
        # (c) and back over the board, in a groove so it cannot walk
        over = np.column_stack([np.linspace(-x_win, x_win, 60), np.full(60, ty),
                                np.full(60, z_seat - STANDBOX_TIE_GROOVE_D/2.0)])
        if Sm.contains(over).any():
            blocked.append('the groove across the shelf tops')
        ck(not blocked, f'tie {i}, {STANDBOX_TIE_INSET:.0f} mm in from the board\'s '
           f'{"front" if i == 1 else "back"} end, has a way round',
           'blocked: ' + ', '.join(blocked) if blocked else 'window, crossing and groove all clear')
    # the groove must be a groove and not a cut: shelf either side of it
    beside = Sm.contains(np.column_stack(
        [np.full(2, chw - 1.0), np.array([ties[0] + 4.0, ties[1] - 4.0]),
         np.full(2, z_seat - 0.5)]))
    ck(beside.all(), 'and it is a groove, not a gap: shelf on both sides of each tie')

    print('\n5. USB-C leaves through the back')
    z_usb = z_seat + BOARD_T + BOARD_TALL/2.0
    out = np.column_stack([np.zeros(40), np.linspace(by1 - 2.0, hi[1] + 2.0, 40),
                           np.full(40, z_usb)])
    ck(not Sm.contains(out).any(), 'a straight run from the board\'s end to open air',
       f'on the board\'s axis at z={z_usb:.1f}')
    wall = solid_run(Sm, 1, np.arange(cy1 - 2.0, hi[1] + 2.0, 0.25),
                     (USB_WIN_W/2.0 + 2.0, 0.0, z_usb))
    ck(bool(wall), 'and the wall it goes through is still there beside the window',
       f'solid in y at x={USB_WIN_W/2.0+2.0:.1f}: {[(round(a,1), round(b,1)) for a, b in wall]}')

    print('\n6. The clock goes in the seat that was cut for it')
    # THE TEST THAT WAS NEVER HERE. Every earlier version of this file treated
    # the clock as something the stand held, and measured the stand alone: the
    # well, the tray, the tipping angle, the covers. None of them ever put the
    # clock in the stand and looked, and the whole time the plinth's roof was
    # sitting inside the clock -- 491 mm3 on the 24, 1134 on the 60 -- because
    # _stand_solid cuts the seat out of the CRADLE and the stand-box then
    # unioned a plinth into it and filled the seat back in.
    #
    # A part that goes inside another one gets a boolean against it.
    a = math.radians(90.0 - STANDBOX_TILT)
    M = np.array([[1, 0, 0, 0],
                  [0, math.cos(a), -math.sin(a), 0.0],
                  [0, math.sin(a),  math.cos(a), h0],
                  [0, 0, 0, 1]])
    clock = None
    for fn in (f'mini-round-clock-base{tg}.stl', f'mini-round-clock-backcover{tg}.stl'):
        cm = load(fn)
        cm.apply_translation([0.0, 0.0, -Z_FRONT])
        cm.apply_transform(M)
        clock = to_manifold(cm) if clock is None else clock + to_manifold(cm)
    hit = (S ^ clock)
    ck(hit.volume() < 5.0, 'the clock seats in the stand without touching it',
       f'{hit.volume():.1f} mm3' + ('' if hit.volume() < 5.0 else
        f'  {csg.to_trimesh(hit).bounds[0][2]:.1f}..{csg.to_trimesh(hit).bounds[1][2]:.1f} in z'))
    cl = csg.to_trimesh(clock)
    ck(cl.bounds[0][2] > 0.5, 'and it clears the desk',
       f'lowest point z={cl.bounds[0][2]:.2f}')
    ck(cl.bounds[0][2] - ceil >= 1.5,
       'with real material between its underside and the board\'s cavity',
       f'{cl.bounds[0][2] - ceil:.2f} mm of roof')
    # and the leads can get from the clock down into the cavity, on the notch's
    # own axis -- taken from the notch SOLID, not from a formula, because the
    # notch has been 4 mm from where a formula put it before
    nb = csg.to_trimesh(notch).bounds
    ny = (nb[0][1] + nb[1][1])/2.0
    path = np.column_stack([np.zeros(50), np.full(50, ny),
                            np.linspace(ceil - 0.5, cl.bounds[0][2] + 2.0, 50)])
    ck(not Sm.contains(path).any(),
       'the leads drop straight from the clock into the cavity',
       f'through the notch at y={ny:.1f}')

    print('\n7. It stands up, leaning back')
    t = math.radians(STANDBOX_TILT)
    y_com = (depth/2)*math.sin(t)
    z_com = h0 - (depth/2)*math.cos(t)
    fwd = math.degrees(math.atan2(y_com - sb[1], z_com))
    back = math.degrees(math.atan2(sb[4] - y_com, z_com))
    ck(fwd >= 20.0, f'tips forward only past {fwd:.1f} deg (floor 20)')
    ck(back >= 20.0, f'tips backward only past {back:.1f} deg (floor 20)')
    ck(STANDBOX_TILT > STAND_TILT, f'leans {STANDBOX_TILT:.0f} deg, more than the cradle\'s {STAND_TILT:.0f}')
    print(f'       plinth {sb[3]-sb[0]:.1f} wide, {sb[4]-sb[1]:.1f} deep; the clock\'s centre {z_com:.0f} mm up')

    print('\n8. It looks like something')
    # Sam: "Make the base look much nicer." Three moves, and a render will show
    # them but not prove them, so they are measured: a radius on the vertical
    # corners, a chamfer round the top edge, and a reveal at the foot.
    def half_at(z, y):
        r = solid_run(Sm, 0, xs, (0.0, y, z))
        return max((max(abs(a), abs(b)) for a, b in r), default=0.0)
    # ...at a y where the plinth's own top edge is exposed. The cradle laps 3 mm
    # down over the plinth and is only 0.4 mm narrower, so measuring the top
    # edge under the cradle reads the cradle and calls a 2.5 mm chamfer 0.4 --
    # which is exactly what it did on the 60, whose cradle reaches the front.
    y_front = None
    for y in np.arange(lo[1] + STANDBOX_CORNER_R + 2.0, hi[1] - STANDBOX_CORNER_R, 2.0):
        w = max(abs(a) for a, b in solid_run(Sm, 0, xs, (0.0, float(y), H/2.0))
                for a in (a, b))
        if not cradle.contains(np.array([[w - 0.6, float(y), H - 0.4]])).any():
            y_front = float(y)
            break
    ck(y_front is not None, 'the plinth\'s top edge is exposed somewhere at all')
    if y_front is None:
        y_front = lo[1] + STANDBOX_CORNER_R + 4.0
    w_mid = half_at(H/2.0, y_front)
    ck(not Sm.contains(np.array([[w_mid - 0.5, lo[1] + 0.5, H/2.0]])).all(),
       f'the vertical corners are radiused, not square',
       f'nothing at the corner of a {2*w_mid:.1f} x {sb[4]-sb[1]:.1f} box')
    # NOT by probing a point a radius in from the corner: with the wings
    # hollowed that point is inside a void, and the test failed on a part whose
    # corners are perfectly round. Measure the OUTLINE instead -- how far the
    # skin has pulled in at a known distance from the end -- which is what a
    # radius actually is. For a circle of radius R, at d from the tangent line
    # the inset is R - sqrt(R^2 - (R-d)^2).
    d = 0.5
    R = STANDBOX_CORNER_R
    exp = R - math.sqrt(max(0.0, R*R - (R - d)**2))
    w_end = half_at(H/2.0, lo[1] + d)
    w_run = half_at(H/2.0, lo[1] + R)
    ck(abs((w_mid - w_end) - exp) < 0.8,
       f'and the radius measures about {R:.1f}',
       f'the skin is {w_mid - w_end:.2f} mm in at {d:.1f} from the end, '
       f'{exp:.2f} expected')
    ck(abs(w_mid - w_run) < 0.25,
       'and it has run out by a radius from the end, not carried on curving',
       f'{w_mid - w_run:.2f} mm in at {R:.1f} from the end')
    w_top = half_at(H - 0.4, y_front)
    ck(w_mid - w_top >= STANDBOX_CHAMF - 0.9,
       f'the top edge is chamfered, {w_mid - w_top:.1f} mm in at 0.4 below the top '
       f'(measured at y={y_front:.0f}, clear of the cradle)',
       f'{2*w_mid:.1f} wide at mid-height, {2*w_top:.1f} at the top')
    w_foot = half_at(0.6, y_front)
    ck(abs((w_mid - w_foot) - STANDBOX_REVEAL_D) < 0.35,
       f'and the foot steps in {w_mid - w_foot:.2f} mm, so the plinth reads as floating',
       f'reveal {STANDBOX_REVEAL_H:.1f} mm tall')
    ck(abs(half_at(STANDBOX_REVEAL_H + 0.6, y_front) - w_mid) < 0.05,
       'the reveal stops where it should, and the body is full width above it')

    print('\n9. The back cover')
    ck(C.is_watertight and C.volume > 0, 'watertight', f'{C.volume/1000:.1f} cm3')
    cb = C.bounds
    ck(abs((cb[1][2] - cb[0][2]) - (BACKCOVER_PLATE + BACKCOVER_POCKET)) < 0.05,
       f'is {BACKCOVER_PLATE + BACKCOVER_POCKET:.1f} mm deep', f'{cb[1][2]-cb[0][2]:.2f}')
    # the lead notch at 6 o'clock, through the rim
    Cm = to_manifold(C)
    notch_c = box_lwh(-B.r_body - 0.5, -B.r_inner - 0.5, -CABLE_W/2 + 0.3, CABLE_W/2 - 0.3,
                      Z_DECK - BACKCOVER_POCKET + 0.3, Z_DECK - 0.3)
    ck((notch_c ^ Cm).volume() < 1.0, 'lead notch open at 6 o\'clock', f'{(notch_c ^ Cm).volume():.1f} mm3 blocking')

    print('\n10. The diffuser variants')
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
print('CHECK 6: the S3 lives in the stand on two shelves, two ties hold it, '
      'USB-C is out the back and the bottom is open')
