#!/usr/bin/env python3
"""CHECK 13 -- the cabinet: the clock in the top bay, the drawer under it.

    python cabinet.py && python check13_cabinet.py [tag]

Everything is measured on the files cabinet.py wrote (cabinet/world/*.stl, the
parts in the world frame) and the clock parts build_v2.py wrote (stl/), never
on the parameters that made them. Where a thing has to MOVE to be assembled or
used, the check moves it, in steps, against the real mesh: the clock in over
its lip, the board in along its rails, the hatch into its rebate, every drawer
all the way out.
"""
import os, sys, math, re
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csg
from csg import to_manifold, box_lwh, cyl
from params import *
from cabinet import (Frame, world_dir, boss_points, boss_axis, side_instances,
                     hatch_outline, retainer_sites, xz_prism, circle,
                     CLOCK_Z_FRONT, CLOCK_Z_BACK, HERE)

FAILS = []


def ck(ok, what, detail=''):
    print(f'  [{"ok" if ok else "FAIL"}] {what}' + (f'  ({detail})' if detail else ''))
    if not ok:
        FAILS.append(what)


def W(fn):
    t = trimesh.load(os.path.join(world_dir(), fn), process=False)
    t.merge_vertices()
    return t


def moved(man, dx=0.0, dy=0.0, dz=0.0):
    return man.translate([dx, dy, dz])


def vol(a, b):
    return (a ^ b).volume()


def _pin_xz(F):
    """Where the keyed retainer's pin sits: the back cover's keyhole, at 12."""
    return (0.0, F.z_clock + HANG_R - KEY_DROP)


def run(tag):
    F = Frame(tag)
    pre = f'mini-round-clock-cabinet{tag}'
    print(f'\n=== cabinet{tag or " (24)"}: {F.W:.1f} x {F.H:.1f} x {F.D:.1f} mm ===')

    # ------------------------------------------------------------------ 1
    print('\n1. The parts are closed solids, and each fits the bed as printed')
    meshes = {}
    printed = ['sleeve', 'hatch', 'drawer', 'pull']
    plys = ['face-ply', 'drawer-ply']
    insts = side_instances(F) if F.sides else []
    if F.sides:
        printed += [i['drawer'].lstrip('-') for i in insts]
        printed += [i['pull'].lstrip('-') for i in insts]
        plys += [i['ply'].lstrip('-') for i in insts]
    for k in printed + plys:
        t = W(f'{pre}-{k}.stl')
        ck(t.is_watertight and t.body_count == 1, f'{k}: one closed body',
           f'watertight={t.is_watertight}, bodies={t.body_count}')
        meshes[k] = t
    S, B, D, P = (to_manifold(meshes[k]) for k in ('sleeve', 'hatch', 'drawer', 'pull'))
    FP, DP = to_manifold(meshes['face-ply']), to_manifold(meshes['drawer-ply'])
    M_ = {k: to_manifold(meshes[k]) for k in printed + plys}
    # the parts with a file of their own in stl/: every side pull is the same
    # print, so only the first is written, under the name the print sheet uses
    on_disk = {}
    for j, k in enumerate(printed):
        if insts and k == insts[0]['pull'].lstrip('-'):
            on_disk[k] = 'pull-side'
        elif k not in [i['pull'].lstrip('-') for i in insts[1:]]:
            on_disk[k] = k
    for k, nm in on_disk.items():
        t = trimesh.load(csg.part(f'{pre}-{nm}.stl'), process=False)
        ext = t.bounds[1] - t.bounds[0]
        ck(max(ext[0], ext[1]) <= CAB_BED and ext[2] <= CAB_BED,
           f'{nm} as printed fits a {CAB_BED:.0f} bed', f'{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f}')
    mass = sum(meshes[k].volume for k in printed) / 1000.0
    print(f'       printed solid volume {mass:.0f} cm3, about {mass * 1.27:.0f} g of PETG')

    # ------------------------------------------------------------------ 2
    print('\n2. Nothing in the box occupies the same space as anything else')
    pairs = [('sleeve', S, 'hatch', B), ('sleeve', S, 'drawer', D), ('sleeve', S, 'face ply', FP),
             ('sleeve', S, 'drawer ply', DP), ('hatch', B, 'drawer', D), ('drawer', D, 'drawer ply', DP),
             ('drawer ply', DP, 'pull', P), ('drawer', D, 'pull', P), ('face ply', FP, 'drawer ply', DP)]
    for i in insts:
        nm = f'{i["side"]}{i["row"] + 1}'
        DS, SP_, PU = (M_[i[k].lstrip('-')] for k in ('drawer', 'ply', 'pull'))
        pairs += [('sleeve', S, f'side drawer {nm}', DS), ('hatch', B, f'side drawer {nm}', DS),
                  ('sleeve', S, f'side ply {nm}', SP_), ('sleeve', S, f'side pull {nm}', PU),
                  ('face ply', FP, f'side ply {nm}', SP_),
                  (f'side drawer {nm}', DS, f'side ply {nm}', SP_),
                  (f'side ply {nm}', SP_, f'side pull {nm}', PU),
                  ('drawer', D, f'side drawer {nm}', DS), ('drawer ply', DP, f'side ply {nm}', SP_)]
    for i, j in [(a, b) for k, a in enumerate(insts) for b in insts[k + 1:]]:
        pairs.append((f'side drawer {i["side"]}{i["row"] + 1}', M_[i['drawer'].lstrip('-')],
                      f'side drawer {j["side"]}{j["row"] + 1}', M_[j['drawer'].lstrip('-')]))
        pairs.append((f'side ply {i["side"]}{i["row"] + 1}', M_[i['ply'].lstrip('-')],
                      f'side ply {j["side"]}{j["row"] + 1}', M_[j['ply'].lstrip('-')]))
    for an, a, bn, b in pairs:
        v = vol(a, b)
        ck(v < 1e-3, f'{an} / {bn}: no overlap', f'{v:.3f} mm3')

    # ------------------------------------------------------------------ 3
    print('\n3. The clock: real base, back cover and flange diffuser, where the box puts them')
    M = F.clock_matrix()
    def clock_part(fn, pre_m=None):
        t = trimesh.load(csg.part(fn), process=False); t.merge_vertices()
        if pre_m is not None:
            t.apply_transform(pre_m)
        t.apply_transform(M)
        return t
    seat = np.diag([1.0, -1.0, -1.0, 1.0]); seat[2, 3] = DIFF_SEAT_Z
    base_t = clock_part(f'mini-round-clock-base{tag}.stl')
    cover_t = clock_part(f'mini-round-clock-backcover{tag}.stl')
    diff_t = clock_part(f'mini-round-clock-diffuser{tag}-flange.stl', seat)
    # Sam's base carries inherited bad edges, so interference is measured
    # against the body's own envelope -- a solid cylinder the size of the base,
    # front face to back cover -- which is what the saddle has to clear anyway.
    env = cyl(F.r_body, CLOCK_Z_BACK, CLOCK_Z_FRONT, 288)
    env = csg.to_manifold(csg.to_trimesh(env))
    Mm = M[:3, :].tolist()
    ENV = env.transform(np.array(Mm))
    ext = base_t.bounds[1] - base_t.bounds[0]
    ck(abs(ext[0] - 2 * F.r_body) < 0.2 and abs(ext[2] - 2 * F.r_body) < 0.2,
       'the placed base is the body the envelope stands for', f'{ext[0]:.2f} x {ext[2]:.2f}')
    ck(abs(base_t.bounds[1][2] - (F.z_clock + F.r_body)) < 0.1 and abs(base_t.bounds[0][0] + F.r_body) < 0.1,
       '...and it is upright and centred', f'top z {base_t.bounds[1][2]:.2f}')
    for nm, other in (('sleeve', S), ('hatch', B), ('face ply', FP), ('drawer', D)):
        v = vol(ENV, other)
        ck(v < 1e-3, f'clock / {nm}: no overlap', f'{v:.3f} mm3')
    # it cannot lift, shift or drop: the bore holds it on every side
    for nm, dx, dz in (('up', 0, 1), ('down', 0, -1), ('sideways', 1, 0)):
        play = 0.0
        lo, hi = 0.0, 3.0
        for _ in range(22):
            m = (lo + hi) / 2
            if vol(ENV.translate([dx * m, 0, dz * m]), S) < 1e-4: lo = m
            else: hi = m
        ck(lo <= CAB_SOCKET_CLR + 0.05, f'in the socket it can move {lo:.2f} mm {nm} and no further',
           f'bore clearance {CAB_SOCKET_CLR:.2f}')
    front = min(base_t.bounds[0][1], diff_t.bounds[0][1], cover_t.bounds[0][1])
    ck(abs(front - F.y_shoulder1) < 1e-3, "its front face lands on the shoulder, not on the wood",
       f'clock front y={front:.2f}, shoulder back y={F.y_shoulder1:.2f}')
    ck(front >= F.y_ply1 + CAB_AIR - 1e-3, '...and the wood carries nothing',
       f'{front - F.y_ply1:.2f} mm of air behind the panel')
    v = vol(ENV.translate([0, -0.3, 0]), S)
    ck(v > 1e-3, 'pushed forward it is stopped by the shoulder', f'{v:.2f} mm3 at -0.30')

    # the face you see
    dv = diff_t.vertices
    r_diff = np.hypot(dv[:, 0], dv[:, 2] - F.z_clock).max()
    ck(r_diff <= F.aper_r - 0.2, 'the whole diffuser, flange included, is inside the aperture',
       f'diffuser r {r_diff:.2f}, aperture r {F.aper_r:.2f}')
    ck(F.aper_r <= F.r_body - 1.0, 'and the wood still lands on the base, hiding its rim',
       f'aperture r {F.aper_r:.2f}, body r {F.r_body:.2f}')
    # the shoulder is behind the wood's own edge, so it shadows nothing
    sh = box_lwh(-F.aper_r + 0.2, F.aper_r - 0.2, F.y_shoulder0 - 0.1, F.y_shoulder1 + 0.1,
                 F.z_clock - F.aper_r + 0.2, F.z_clock + F.aper_r - 0.2)
    inner = sh ^ xz_prism(circle(F.aper_r - 0.2, 0.0, F.z_clock, 288), F.y_shoulder0, F.y_shoulder1)
    ck(vol(inner, S) < 1e-3, 'and the shoulder stays outside the aperture, shadowing nothing')
    probe = (csg.tube(F.aper_r - 0.15, F.aper_r - 0.05, -1.0, 1.0, 288)
             .rotate([90, 0, 0]).translate([0, 0, F.z_clock]))
    probe = csg.to_manifold(csg.to_trimesh(probe)).translate([0, F.y_ply0 + PLY_T / 2, 0])
    ck(vol(probe, FP) < 1e-3, 'the aperture as cut is concentric with the clock in its socket')

    # ------------------------------------------------------------------ 4
    print('\n4. It slides in through the hatch, and three retainers hold it there')
    y_out = F.D + 5.0 - F.y_clock_f
    worst = max(vol(ENV.translate([0, y_out * (1 - k / 60.0), 0.0]), S) for k in range(61))
    ck(worst < 1e-3, 'straight in along its own axis, from outside the box to the shoulder',
       f'worst {worst:.3f} mm3 over 61 steps')
    op = (F.cw - 2 * CAB_HATCH_LEDGE, F.h_clock - 2 * CAB_HATCH_LEDGE)
    ck(min(op) >= 2 * F.r_body + 1.0, 'the hatch opening passes it',
       f'opening {op[0]:.1f} x {op[1]:.1f}, clock {2 * F.r_body:.1f}')

    RET = {}
    for site in retainer_sites(F):
        nm = f'retainer-{site["ang"]:.0f}'
        t = W(f'{pre}-{nm}.stl')
        ck(t.is_watertight and t.body_count == 1, f'{nm}: one closed body')
        RET[site['ang']] = (to_manifold(t), site)
    for a, (R_, site) in RET.items():
        nm = ('keyed ' if site['key'] else '') + f'retainer at {a:.0f} deg'
        ck(vol(R_, S) < 1e-3, f'{nm}: clear of the sleeve', f'{vol(R_, S):.3f} mm3')
        # it sits CAB_RET_GAP clear of the clock -- the foam tape closes that.
        # The keyed one's pin is inside the keyhole, which the solid envelope
        # does not have, so that one is measured against the real back cover
        # further down instead.
        bar_only = R_ - xz_prism(circle(CAB_RET_PIN_D / 2 + 0.5, *_pin_xz(F), 48),
                                 F.y_ret0 - 9.0, F.y_ret0) if site['key'] else R_
        ck(vol(bar_only, ENV) < 1e-3, f'{nm}: clear of the clock as printed')
        ck(vol(R_.translate([0, -(CAB_RET_GAP + 0.1), 0]), ENV) > 1e-3,
           f'{nm}: and only {CAB_RET_GAP:.2f} mm clear of it, which the foam tape takes up')
        # the screw: through the bar, into the boss's pilot, solid all round
        bx, bz = site['xz']
        # the screw goes in from the BACK: through the bar, on into the post
        pin = cyl(1.1, -(F.y_ret1 + CAB_BOSS_L - 0.5), -(F.y_ret0 + 0.1), 32).rotate([90, 0, 0]).translate([bx, 0, bz])
        ck(vol(pin, S) < 1e-3 and vol(pin, R_) < 1e-3, f'{nm}: its screw runs clear into the pilot')
        ring = (box_lwh(bx - 2.4, bx + 2.4, F.y_ret1 + 1.0, F.y_ret1 + CAB_BOSS_L - 0.5,
                        bz - 2.4, bz + 2.4)
                - box_lwh(bx - 1.4, bx + 1.4, 0, F.D + 5, bz - 1.4, bz + 1.4))
        frac = vol(ring, S) / ring.volume()
        ck(frac > 0.90, f'{nm}: solid plastic round that pilot', f'{frac * 100:.0f}%')
    # with the retainers on, the clock cannot come back out
    back = None
    for a, (R_, site) in RET.items():
        back = R_ if back is None else back + R_
    ck(vol(ENV.translate([0, 0.4, 0]), back) > 1e-3,
       'with all three on, it cannot slide back out: 0.40 and it is into them',
       f'{vol(ENV.translate([0, 0.4, 0]), back):.2f} mm3')

    # THE ROTATION LOCK: the keyed retainer's pin in the back cover's keyhole.
    # Measured on the real back cover mesh, rotated about the clock's own axis.
    key_R = next(R_ for a, (R_, s) in RET.items() if s['key'])
    cover_m = to_manifold(cover_t)
    ck(vol(cover_m, key_R) < 1e-3, 'the pin drops into the keyhole with the dial upright',
       f'{vol(cover_m, key_R):.3f} mm3')
    def spun(deg):
        ax = M[:3, 1]                      # the clock's own axis, in world
        Rm = trimesh.transformations.rotation_matrix(
            math.radians(deg), ax, [0.0, F.y_clock_f, F.z_clock])
        t = cover_t.copy(); t.apply_transform(Rm)
        return to_manifold(t)
    hits = [d for d in (1.0, 1.5, 2.0, 3.0) if vol(spun(d), key_R) > 1e-3
            and vol(spun(-d), key_R) > 1e-3]
    ck(bool(hits), f'and it stops the dial turning: {min(hits) if hits else "-"} degrees either '
                   f'way is already into the pin')

    # the leads: out of the notch at 6 o'clock, through the socket's slot, and back
    lane = box_lwh(-CABLE_W / 2 + 0.5, CABLE_W / 2 - 0.5, F.y_notch0 + 0.2, F.y_clock_b - 0.2,
                   F.z_clock - F.r_sock - 0.5, F.z_clock - F.r_bore - 0.2)
    ck(vol(lane, S) < 1e-3, f"the socket is slotted at 6 o'clock, so the {CABLE_W:.0f} mm notch "
                            f"opens into the bay")
    lane2 = box_lwh(-CABLE_W / 2, CABLE_W / 2, F.y_clock_b + 0.2, F.y_bstop0,
                    F.z_cf + 0.1, F.z_cf + 3.5)
    ck(vol(lane2, S) < 1e-3, 'and a lane runs on along the floor to the board')


    # ------------------------------------------------------------------ 5
    print('\n5. The face panel')
    fb = meshes['face-ply'].bounds
    ck(abs(fb[0][1] - CAB_RECESS) < 1e-3, 'its face sits CAB_RECESS behind the sleeve front',
       f'y={fb[0][1]:.2f}')
    v = vol(FP.translate([0, 0.1, 0]), S)
    ck(v > 1e-3, 'pushed, it lands on the stop tabs', f'{v:.2f} mm3 at +0.10')
    # with side drawers the panel's sides are the partitions, not the sleeve
    gaps = [fb[0][0] + F.cw / 2, F.cw / 2 - fb[1][0], fb[0][2] - F.z_cf, F.z_ct - fb[1][2]]
    ck(all(abs(g - CAB_REVEAL) < 0.02 for g in gaps), 'reveal to the sleeve on all four sides',
       ' / '.join(f'{g:.2f}' for g in gaps))

    # ------------------------------------------------------------------ 6
    print('\n6. The drawer')
    DR = D + DP + P
    db = meshes['drawer-ply'].bounds
    ck(abs(db[0][1] - fb[0][1]) < 1e-3, 'its front is in the same plane as the face panel',
       f'{db[0][1]:.2f} / {fb[0][1]:.2f}')
    v = vol(D.translate([0, 0.1, 0]), S)
    ck(v > 1e-3, "closed, it stops on the sleeve's own back wall", f'{v:.2f} mm3 at +0.10')
    ck(vol(D.translate([0, 0.1, 0]), B) < 1e-3, '...and never touches the hatch')
    worst, travel = 0.0, F.D
    for k in range(0, 81):
        worst = max(worst, vol(DR.translate([0, -travel * k / 80.0, 0]), S))
    ck(worst < 1e-3, 'it slides all the way out touching nothing but the floor', f'{worst:.3f} mm3')
    v = vol(D.translate([0, 0, -0.05]), S)
    ck(v > 1e-3, 'it is carried by the floor', f'{v:.2f} mm3 at -0.05')
    def play(dx, dz):
        lo, hi = 0.0, 3.0
        for _ in range(24):
            m = (lo + hi) / 2
            if vol(D.translate([dx * m, 0, dz * m]), S) < 1e-4: lo = m
            else: hi = m
        return lo
    side, up = play(1, 0), play(0, 1)
    ck(side >= CAB_DR_SIDE_CLR - 0.02, f'it can move {side:.2f} sideways before it touches, corners included')
    ck(up >= CAB_DR_TOP_CLR - 0.02, f'and lift {up:.2f} before it touches the divider')
    inner = (F.w_in - 2 * CAB_DR_SIDE_CLR - 2 * CAB_DR_WALL,
             F.y_wall - F.y_ply1 - CAB_DR_FRONT_T - CAB_DR_WALL,
             CAB_DRAWER_H - CAB_DR_TOP_CLR - CAB_DR_FLOOR)
    print(f'       inside the drawer: {inner[0]:.0f} wide x {inner[1]:.0f} deep x {inner[2]:.0f} high')
    # the pull's screws: through drawer front, ply, into the legs, all on one axis
    for sx in (1, -1):
        x = sx * F.pull_x
        def ypin(r, y0, y1, x=x):
            return cyl(r, -y1, -y0, 32).rotate([90, 0, 0]).translate([x, 0, F.z_pull])
        rod = ypin(1.5, F.y_ply0 + 0.01, F.y_ply1 + CAB_DR_FRONT_T - 0.01)
        ck(vol(rod, D) < 1e-3 and vol(rod, DP) < 1e-3, f'pull screw at x={x:+.1f}: clear through ply and drawer front')
        bite = ypin(1.0, F.y_ply0 - CAB_PULL_PILOT + 0.2, F.y_ply0 - 0.2)
        ck(vol(bite, P) < 1e-3, f'...and into a {CAB_PULL_PILOT:.0f} mm pilot in the leg')
        shell = (box_lwh(x - 3.2, x + 3.2, F.y_ply0 - CAB_PULL_PILOT, F.y_ply0 - 0.2,
                         F.z_pull - 3.2, F.z_pull + 3.2)
                 - box_lwh(x - 1.4, x + 1.4, F.y_ply0 - 20, F.y_ply0 + 1, F.z_pull - 1.4, F.z_pull + 1.4))
        frac = vol(shell, P) / shell.volume()
        ck(frac > 0.97, '...with solid plastic all round the pilot', f'{frac * 100:.0f}%')
    print(f'       screws: M3 x 12 self-tapping ({CAB_DR_FRONT_T:.1f} front + {PLY_T:.1f} ply + '
          f'{12 - CAB_DR_FRONT_T - PLY_T:.1f} into the leg of {CAB_PULL_PILOT:.0f})')

    # ------------------------------------------------------------------ 6b
    if F.sides:
        print('\n6b. The side drawers: {} rows each side of the clock'.format(F.side_rows))
        depth_in = F.y_wall - F.y_ply1 - CAB_DR_FRONT_T - CAB_DR_WALL
        print(f'       {2 * F.side_rows} drawers, each {F.side_w - 2 * CAB_DR_SIDE_CLR - 2 * CAB_DR_WALL:.0f} '
              f'wide x {depth_in:.0f} deep x {F.side_row_h - CAB_DR_TOP_CLR - CAB_DR_FLOOR:.0f} high inside')
        # the partitions, and the shelf between the rows, are solid
        for sx in (1, -1):
            slab = box_lwh(min(sx * (F.x_part_i + 0.2), sx * (F.x_part_o - 0.2)),
                           max(sx * (F.x_part_i + 0.2), sx * (F.x_part_o - 0.2)),
                           F.y_ply1 + 2.0, F.y_hatch0 - 2.0,
                           F.z_cf + 2.0, F.z_ct - 2.0)
            frac = vol(slab, S) / slab.volume()
            ck(frac > 0.97, f'the partition on the {"right" if sx > 0 else "left"} is solid '
                            f'floor to ceiling, front to back', f'{frac * 100:.0f}%')
        for row in range(F.side_rows - 1):
            z = F.side_z[row][1]
            for sx in (1, -1):
                shelf = box_lwh(min(sx * (F.x_part_o + 0.4), sx * (F.w_in / 2 - 0.4)),
                                max(sx * (F.x_part_o + 0.4), sx * (F.w_in / 2 - 0.4)),
                                F.y_ply1 + 2.0, F.y_wall - 2.0,
                                z + 0.2, z + CAB_SIDE_SHELF - 0.2)
                frac = vol(shelf, S) / shelf.volume()
                ck(frac > 0.97, f'the shelf over row {row + 1} on the '
                                f'{"right" if sx > 0 else "left"} is solid', f'{frac * 100:.0f}%')
        for i in insts:
            nm = f'{"right" if i["sx"] > 0 else "left"} row {i["row"] + 1}'
            DS, SPP, PU = (M_[i[k].lstrip('-')] for k in ('drawer', 'ply', 'pull'))
            sb = meshes[i['ply'].lstrip('-')].bounds
            ck(abs(sb[0][1] - CAB_RECESS) < 1e-3,
               f'{nm}: its front is in the same plane as every other front', f'y={sb[0][1]:.2f}')
            if i['sx'] > 0:
                inner_g, outer_g = sb[0][0] - F.x_part_o, F.w_in / 2 - sb[1][0]
            else:
                inner_g, outer_g = -F.x_part_o - sb[1][0], sb[0][0] + F.w_in / 2
            gaps = [inner_g, outer_g, sb[0][2] - i['z0'], i['z1'] - sb[1][2]]
            ck(all(abs(g - CAB_REVEAL) < 0.02 for g in gaps),
               f'{nm}: the same {CAB_REVEAL:.1f} reveal all four sides',
               ' / '.join(f'{g:.2f}' for g in gaps))
            v = vol(DS.translate([0, 0.1, 0]), S)
            ck(v > 1e-3, f'{nm}: closed, it stops on the back wall', f'{v:.2f} mm3 at +0.10')
            ck(vol(DS.translate([0, 0.1, 0]), S) > 1e-3, f"{nm}: on the sleeve's own back wall")
            SD = DS + SPP + PU
            worst = max(vol(SD.translate([0, -F.D * k / 60.0, 0]), S) for k in range(61))
            ck(worst < 1e-3, f'{nm}: it slides all the way out touching nothing but its floor',
               f'{worst:.3f} mm3')
            ck(vol(DS.translate([0, 0, -0.05]), S) > 1e-3,
               f'{nm}: it is carried by the floor under it')
            def play(dx, dz, D_=DS):
                lo, hi = 0.0, 3.0
                for _ in range(24):
                    m = (lo + hi) / 2
                    if vol(D_.translate([dx * m, 0, dz * m]), S) < 1e-4: lo = m
                    else: hi = m
                return lo
            sp, upp = min(play(1, 0), play(-1, 0)), play(0, 1)
            ck(sp >= CAB_DR_SIDE_CLR - 0.02 and upp >= CAB_DR_TOP_CLR - 0.02,
               f'{nm}: {sp:.2f} of sideways play and {upp:.2f} up')
            for s2 in (1, -1):
                x = i['sx'] * F.x_side_c + s2 * F.side_pull_x
                def ypin(r, y0, y1, x=x, zp=i['z_pull']):
                    return cyl(r, -y1, -y0, 32).rotate([90, 0, 0]).translate([x, 0, zp])
                rod = ypin(1.5, F.y_ply0 + 0.01, F.y_ply1 + CAB_DR_FRONT_T - 0.01)
                bite = ypin(1.0, F.y_ply0 - CAB_PULL_PILOT + 0.2, F.y_ply0 - 0.2)
                ck(vol(rod, DS) < 1e-3 and vol(rod, SPP) < 1e-3 and vol(bite, PU) < 1e-3,
                   f'{nm}: pull screw at x={x:+.1f} runs clear into its leg')


    # ------------------------------------------------------------------ 7
    print('\n7. The ESP32-S3: in along its rails from the back, USB-C out through the panel')
    zb = F.z_cf + CAB_TAPE
    pcb = box_lwh(-BOARD2_W / 2, BOARD2_W / 2, F.y_board0, F.y_board1, zb, zb + BOARD_T)
    parts_top = box_lwh(-BOARD2_W / 2 + 1.5, BOARD2_W / 2 - 1.5, F.y_board0, F.y_board1,
                        zb + BOARD_T - 0.01, zb + BOARD2_H)
    board = pcb + parts_top
    for nm, other in (('sleeve', S), ('hatch', B)):
        ck(vol(board, other) < 1e-3, f'board ({BOARD2_L:.0f} x {BOARD2_W:.0f} x {BOARD2_H:.0f}) / {nm}: no overlap')
    worst = max(vol(board.translate([0, (F.D + 2 - F.y_board0) * k / 40.0, 0]), S) for k in range(41))
    ck(worst < 1e-3, 'it slides in from behind the box along the rails', f'{worst:.3f} mm3')
    ck(vol(pcb.translate([0.45, 0, 0]), S) > 1e-3 and vol(pcb.translate([-0.45, 0, 0]), S) > 1e-3,
       f'the rails locate it across ({HOUSING_S3_SLOT_W - BOARD2_W:.2f} total play)')
    ck(vol(pcb.translate([0, -(CAB_STOP_GAP + 0.1), 0]), S) > 1e-3, 'the end stop locates it forward')
    ck(vol(board.translate([0, HOUSING_S3_USB_GAP + 0.1, 0]), B) > 1e-3,
       f'the hatch locates it rearward ({HOUSING_S3_USB_GAP:.2f} of play)')
    zc = zb + BOARD_T + 1.6
    plug = box_lwh(-12.35 / 2, 12.35 / 2, F.y_board1 + 0.3, F.D + 20, zc - 6.5 / 2, zc + 6.5 / 2)
    ck(vol(plug, B) < 1e-3 and vol(plug, S) < 1e-3,
       'a full-size USB-C overmould (12.35 x 6.50) reaches the socket through the window')

    # ------------------------------------------------------------------ 8
    print('\n8. The back: closed over every drawer, one recessed hatch over the clock')
    # the drawer bays are closed by the sleeve itself
    bays = [('the bottom drawer', -F.w_in / 2 + 6, F.w_in / 2 - 6, F.z_dr0 + 4, F.z_dr1 - 4)]
    for i in insts:
        bays.append((f'side bay {i["side"]}{i["row"] + 1}',
                     min(i['sx'] * (F.x_part_o + 4), i['sx'] * (F.w_in / 2 - 4)),
                     max(i['sx'] * (F.x_part_o + 4), i['sx'] * (F.w_in / 2 - 4)),
                     i['z0'] + 4, i['z1'] - 4))
    for nm, x0, x1, z0, z1 in bays:
        wall = box_lwh(x0, x1, F.y_wall + 0.2, F.D - 0.2, z0, z1)
        frac = vol(wall, S) / wall.volume()
        ck(frac > 0.98, f'{nm} is closed by the sleeve, not by a panel', f'{frac * 100:.0f}% solid')
    # ...and the clock bay is not: the hatch opening goes right through
    # what has to be open at the back is the clock's own way in: its bore,
    # which the socket's pads define. The rest of the bay's cross-section is
    # where those pads and their fins live.
    thru = xz_prism(circle(F.r_bore - 0.1, 0.0, F.z_clock, 288), F.y_hatch0 - 0.2, F.D + 0.2)
    ck(vol(thru, S) < 1e-3, 'the clock bay is open at the back, the full width of the bore')

    hb = meshes['hatch'].bounds
    ck(abs(hb[1][1] - (F.D - CAB_HATCH_INSET)) < 1e-3,
       f'the hatch is recessed {CAB_HATCH_INSET:.1f} mm into the back face',
       f'hatch back y={hb[1][1]:.2f}, sleeve back y={F.D:.2f}')
    ck(abs(meshes['sleeve'].bounds[1][1] - F.D) < 1e-3, '...which is a flat face all round it')
    seat_at = next((0.05 * k for k in range(1, 40)
                    if vol(B.translate([0, -0.05 * k, 0]), S) > 1e-3), None)
    ck(vol(B.translate([0, 0.2, 0]), S) < 1e-3 and seat_at is not None and seat_at < 0.8,
       "it wedges into the rebate's taper rather than falling through it",
       f'it bites {seat_at:.2f} mm in, so it lands {CAB_HATCH_INSET - seat_at:.2f} deep')
    worst = max(vol(B.translate([0, 40.0 * (1 - k / 40.0), 0]), S) for k in range(41))
    ck(worst < 1e-3, 'it goes straight in from behind, nothing to lift or hook', f'{worst:.3f} mm3')
    for (bx, bz, t0, t1) in boss_axis(F):
        hole = box_lwh(bx - 1.0, bx + 1.0, F.y_hatch0 - 0.1, F.y_hatch1 + 0.1, bz - 1.0, bz + 1.0)
        ck(vol(hole, B) < 1e-3, f'hatch hole at ({bx:+.1f}, {bz:.1f}) is open')
        pilot = box_lwh(bx - 0.8, bx + 0.8, t0 + 1.2, t1 - 0.1, bz - 0.8, bz + 0.8)
        ring = (box_lwh(bx - 2.4, bx + 2.4, t0 + 1.2, t1 - 0.1, bz - 2.4, bz + 2.4)
                - box_lwh(bx - 1.4, bx + 1.4, 0, F.D + 5, bz - 1.4, bz + 1.4))
        frac = vol(ring, S) / ring.volume()
        ck(vol(pilot, S) < 1e-3 and frac > 0.97,
           f'...into a {t1 - t0:.0f} mm pilot on the same axis, solid all round', f'{frac * 100:.0f}%')
        run_ = box_lwh(bx - 1.4, bx + 1.4, F.y_hatch1 - 0.1, t0, bz - 1.4, bz + 1.4)
        ck(vol(run_, S) < 1e-3 and vol(run_, B) < 1e-3,
           f'...and the screw reaches it: {F.y_hatch1 - t0:.0f} mm from the hatch face, so M3 x '
           f'{int(math.ceil((F.y_hatch1 - t0 + 6) / 5.0) * 5)}')
    # the clock has to fit through the hatch opening on its way in
    op = (F.cw - 2 * CAB_HATCH_LEDGE, F.h_clock - 2 * CAB_HATCH_LEDGE)
    ck(op[0] >= 2 * F.r_body + 1.0 and op[1] >= 2 * F.r_body + 1.0,
       'and the clock passes through that opening flat',
       f'opening {op[0]:.1f} x {op[1]:.1f}, clock {2 * F.r_body:.1f}')


    # ------------------------------------------------------------------ 9
    print('\n9. Printing: no overhang flatter than 45 degrees wider than 5.0 mm, as printed')
    for k, nm in on_disk.items():
        t = trimesh.load(csg.part(f'{pre}-{nm}.stl'), process=False)
        t.merge_vertices()
        n = t.face_normals
        zmin = t.vertices[t.faces][:, :, 2].min(axis=1)
        over = np.nonzero((n[:, 2] < -0.72) & (zmin > 0.05))[0]
        # width of each connected patch = its projected area over its length,
        # so a long thin strip on a diagonal is measured as the strip it is
        worst_w, worst_at, area = 0.0, None, t.area_faces[over].sum()
        if len(over):
            sub = t.submesh([over], append=True)
            for comp in sub.split(only_watertight=False):
                ext = comp.bounds[1] - comp.bounds[0]
                proj = (comp.area_faces * np.abs(comp.face_normals[:, 2])).sum()
                w = proj / max(ext[0], ext[1], 1e-6)
                if w > worst_w:
                    worst_w, worst_at = w, comp.bounds.mean(axis=0)
        where = '' if worst_at is None else f' at print xyz {worst_at[0]:.0f},{worst_at[1]:.0f},{worst_at[2]:.0f}'
        # 5.0 for the sleeve, 3.5 for everything else: its widest patches are the
        # rear ends of the socket's fins where they meet the hatch's seat -- each
        # under 200 mm2, 4.4 mm off the bed, hanging off the bay wall beside them
        lim = 5.0 if nm.endswith('sleeve') else 3.5
        ck(worst_w <= lim + 1e-6, f'{nm}: overhangs {area:.0f} mm2 in all, the widest patch '
                                  f'{worst_w:.2f} mm across{where}')

    # ------------------------------------------------------------------ 10
    print('\n10. The Glowforge file: one joined sheet, every front still bounded')
    from cabinet import joined_fronts
    from shapely.geometry import Polygon, LineString, MultiLineString
    from shapely.ops import unary_union
    boundary, lines, holes, saved, placed = joined_fronts(F)
    svg = open(os.path.join(HERE, 'cabinet', f'{pre}-fronts.svg'), encoding='utf-8').read()
    closed = re.findall(r'd="M ([^"]+) Z"', svg)
    opened = re.findall(r'd="M ((?:(?!Z")[^"])+)"', svg)
    def pts(d):
        return np.array([[float(v) for v in p.split()] for p in d.split(' L ')])
    ck(len(closed) == 1 + len(holes),
       f'one outline and {len(holes)} holes, closed paths, and nothing else closed',
       f'{len(closed)} closed')
    ck(len(opened) == len(lines), f'{len(lines)} lines across the sheet, cut once each',
       f'{len(opened)} open paths')
    print(f'       {saved:.0f} mm less cut than the same fronts as separate outlines')

    # every front, where the sheet puts it, is still bounded by cut on all sides
    cut = unary_union([LineString(list(p) + [p[0]]) for p in
                       [ [tuple(q) for q in pts(d)] for d in closed ]]
                      + [LineString([tuple(q) for q in pts(d)]) for d in opened])
    # the sheet's own frame: x right, y down from the top left
    xs = [p[0] for p in boundary]; zs = [p[1] for p in boundary]
    x0, z1 = min(xs) - 5.0, max(zs) + 5.0
    from shapely.geometry import Point
    for nm, o, hs in placed:
        ring = [(x - x0, z1 - z) for x, z in o]
        ring.append(ring[0])
        # every vertex, and every 2 mm along every edge, has to sit ON a cut
        # line. Hausdorff will not do it: the cut runs on past each part, so
        # the far half of the measure is always the neighbour's line.
        probe = []
        for a_, b_ in zip(ring, ring[1:]):
            probe.append(a_)
            n = max(1, int(math.dist(a_, b_) / 2.0))
            for t_ in range(1, n):
                probe.append((a_[0] + (b_[0] - a_[0]) * t_ / n,
                              a_[1] + (b_[1] - a_[1]) * t_ / n))
        gap = max(cut.distance(Point(p_)) for p_ in probe)
        # 0.35 covers the 0.30 corner radii: where two fronts share a corner the
        # cut runs straight past it, so that part comes out with a square corner
        # instead of a rounded one
        ck(gap < 0.35, f'{nm}: every millimetre of its outline is on a cut line',
           f'worst {gap:.3f} mm over {len(probe)} points')
    # the window and the pull holes are the parts they were before
    k = PLY_KERF
    circ = [pts(d) for d in closed
            if abs((pts(d)[:, 0].max() - pts(d)[:, 0].min())
                   - (pts(d)[:, 1].max() - pts(d)[:, 1].min())) < 0.05]
    big = max(circ, key=lambda p: p[:, 0].max() - p[:, 0].min())
    ck(abs((big[:, 0].max() - big[:, 0].min()) - (2 * F.aper_r - k)) < 0.05,
       'the window is the clock aperture less kerf',
       f'{big[:, 0].max() - big[:, 0].min():.2f}')
    small = [p for p in circ if p[:, 0].max() - p[:, 0].min() < 10]
    want_holes = 2 + 4 * F.side_rows if F.sides else 2
    ck(len(small) == want_holes, f'{want_holes} pull holes', f'{len(small)} found')
    ck('stroke="#FF0000"' in svg and '<text' not in svg, 'red cut lines only, no text')


if __name__ == '__main__':
    tags = sys.argv[1:] if len(sys.argv) > 1 else ['', '-32']
    for tg in tags:
        run('' if tg in ('24', '""') else tg)
    print()
    if FAILS:
        print(f'check13: {len(FAILS)} FAILED')
        for f in FAILS:
            print('   -', f)
        sys.exit(1)
    print('check13: all passed')
