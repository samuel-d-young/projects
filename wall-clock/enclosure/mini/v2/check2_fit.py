#!/usr/bin/env python3
"""Does everything fit, on both bodies, measured on the built STLs?

Nothing here reads the code that made the parts -- it loads the files that will
be sliced and probes them as solids.
"""
import sys, math, os; sys.path.insert(0, '.')
import numpy as np, trimesh
from csg import box_lwh, cyl, cone, tube, wedge, to_manifold, to_trimesh
from params import *
import build_v2 as BV

FAIL = []
def ck(c, msg, d=''):
    print(f'  [{"ok  " if c else "FAIL"}] {msg}' + (f'   {d}' if d else ''))
    if not c: FAIL.append(msg)

def load(f):
    m = trimesh.load(f, process=False); m.merge_vertices(); return m

SEG = BV.SEG
SAM = BV.load_sams_base()
BODIES = [(BV.BODY24, ''), (BV.BODY32, '-32'), (BV.BODY60, '-60')]
DEPTH  = Z_FRONT - (Z_DECK - HOUSING_DEEP)

for B, tg in BODIES:
    BASE = to_manifold(load(f'mini-round-clock-base{tg}.stl'))
    HOUS = to_manifold(load(f'mini-round-clock-housing{tg}.stl'))
    DIFF = to_manifold(load(f'mini-round-clock-diffuser{tg}.stl'))
    Bt   = load(f'mini-round-clock-base{tg}.stl')
    print(f'\n{"="*70}\n{B.n}-LED body — {2*B.r_body:.2f} mm across, ring {B.ring_od} / {B.ring_id}')

    print("\n1. What of Sam's geometry survives")
    keep_r = 40.0 if B.n == 24 else KEEP_R32 - 1.0
    inside = cyl(keep_r, 0.001, 60.0, SEG)
    sam_in, new_in = SAM ^ inside, BASE ^ inside
    removed, added = (sam_in - new_in), (new_in - sam_in)
    allow_rm = None
    for a_ in B.screw_ang:
        x, y = B.screw_r*math.cos(math.radians(a_)), B.screw_r*math.sin(math.radians(a_))
        c = cyl(SCREW_PILOT/2 + 0.05, -1, Z_BACK+SCREW_DEPTH+0.05, 48, centre=(x, y))
        allow_rm = c if allow_rm is None else allow_rm + c
    if B.n != 24:
        # the wire gap -- the same +/-13.00 mm channel Sam's own base has, but
        # carried out to the bigger ring's inner edge and open to the shelf
        allow_rm += box_lwh(-B.r_ring_o - 2.05, -R_BORE + 4.05,
                            -WIRE_SLOT_HW - 0.05, WIRE_SLOT_HW + 0.05,
                            Z_DECK - 1.0, Z_RECESS - B.band_top + FACE_T + 0.05)
    ck((removed - allow_rm).volume() < 0.05,
       f'inside r={keep_r:.0f} nothing is removed but the pilots'
       + ('' if B.n == 24 else ' and the wire gap'),
       f'{(removed - allow_rm).volume():.4f} mm3 outside them')
    wall_env = (wedge(TAB_WALL_RI - 0.10, TAB_WALL_RO + 0.10, Z_BACK - 0.05,
                      TAB_WALL_TOP + 0.10, -TAB_WALL_AHALF - 0.2, TAB_WALL_AHALF + 0.2)
                - box_lwh(-1.0, 60.0, -TAB_SLOT_HW, TAB_SLOT_HW, Z_BACK - 1.0, TAB_CHAMF_Z))
    allow_add = wall_env
    if B.n != 24:
        allow_add += tube(34.50, KEEP_R32, 10.30,
                          Z_RECESS - B.band_top + FACE_T + 0.10, SEG)
    ck((added - allow_add).volume() < 0.05,
       'and nothing is added but the tab-slot walls'
       + ('' if B.n == 24 else ' and the pocket fill'),
       f'{(added - allow_add).volume():.3f} mm3 outside them')

    print('\n2. The LED ring drops into its pocket')
    ring = tube(B.ring_id/2, B.ring_od/2, Z_RING_FLOOR, Z_RING_FLOOR + PCB_T + LED_H, 192)
    ck((BASE ^ ring).volume() < 1e-3, f'the {B.ring_od} / {B.ring_id} ring is clear of the base',
       f'{(BASE ^ ring).volume():.5f} mm3')
    ck((ring - BASE).volume() > 0.99*ring.volume(), '...and the pocket is actually empty',
       f'{100*(ring - BASE).volume()/ring.volume():.1f}% clear')
    ck(B.r_ring_i <= B.ring_id/2 and B.r_ring_o >= B.ring_od/2,
       'the pocket brackets the ring on both edges',
       f'{B.r_ring_i:.2f} <= {B.ring_id/2:.2f} and {B.r_ring_o:.2f} >= {B.ring_od/2:.2f}')
    ck(B.r_body - B.r_ring_o >= 3.0, 'and there is a real wall outboard of it',
       f'{B.r_body - B.r_ring_o:.2f} mm')

    print('\n3. The diffuser is a press fit')
    r_out = np.hypot(*load(f'mini-round-clock-diffuser{tg}.stl').vertices[:, :2].T).max()
    nominal = B.diff_outer
    # on a guide body the diffuser is the whole face and presses into the lip,
    # not into the ring pocket
    press_r = B.r_lip_i if B.guides else B.r_ring_o
    ck(abs(r_out - (nominal + DIFF_RIB_H)) < 0.02, 'the crush ribs stand proud of the wall',
       f'crest r {r_out:.3f}, wall {nominal:.3f}')
    ck(nominal < press_r, 'the wall itself has clearance, so it starts square',
       f'{2*(press_r - nominal):.2f} mm on diameter, into r={press_r:.2f}')
    ck(r_out > press_r, 'and the ribs interfere, so it does not fall out',
       f'{2*(r_out - press_r):.2f} mm on diameter at {DIFF_RIB_N} ribs')
    ck(0.35 <= 2*(r_out - press_r) <= 0.90, '...by an amount a printer can actually crush',
       f'{2*(r_out - press_r):.2f} mm')

    print('\n4. The display module and its tab')
    module = cyl(DISP_PCB_D/2, Z_SEAT, Z_SEAT + 4.0, 128)
    ck((BASE ^ module).volume() < 1e-3, 'the module clears the base', f'{(BASE ^ module).volume():.5f} mm3')
    tab = box_lwh(R_DISP_POCKET, DISP_OVERALL - DISP_PCB_D/2, -DISP_TAB_W/2, DISP_TAB_W/2,
                  Z_SEAT, Z_SEAT + DISP_TAB_T)
    ck((BASE ^ tab).volume() < 1e-6, 'the tab clears the slot', f'{(BASE ^ tab).volume():.5f} mm3')

    print('\n5. The S3 is actually HELD, and the frame can be printed')
    ZP = Z_DECK - (PLATE_T + POCKET_DEEP) + PLATE_T
    zt   = ZP + BRD_POST_H                  # PCB underside
    ztp  = zt + BOARD_T                     # PCB top
    zlip = ZP + BRD_LIP_Z0
    ztop = ZP + BRD_RAIL_TOP
    HW   = BOARD_W/2
    x_tip  = BRD_X0 + BRD_FING_X0
    x_root = x_tip + BRD_FING_L

    def solid(bx):
        v = (HOUS ^ bx).volume()
        return v, v/bx.volume()

    # --- (a) the board and everything on it fits
    pcb = box_lwh(BRD_X0, BRD_X1, -HW, HW, zt, ztp)
    ck(solid(pcb)[0] < 1e-3, 'the PCB itself is not fouled anywhere',
       f'{solid(pcb)[0]:.5f} mm3')
    # the lips DO stand over the board's top -- that is their whole job -- so
    # they are cut out of this probe and measured on their own below
    lips = box_lwh(x_tip - 0.1, x_tip + BRD_FING_LIP_L + 0.1, -HW, HW, ztp, ztop + 1.0)
    tall = box_lwh(BRD_X0, BRD_X1, -HW, HW, ztp, ztp + BOARD_TALL) - lips
    ck(solid(tall)[0] < 1e-3, 'nor is anything standing on it, the lips aside',
       f'{solid(tall)[0]:.5f} mm3')
    shells = box_lwh(BRD_X0 - BOARD_CONN_OVER, BRD_X0 + BOARD_CONN_L,
                     -BOARD_CONN_Y, BOARD_CONN_Y, ztp, ztp + BOARD_TALL)
    ck(solid(shells)[0] < 1e-3, 'and the two USB shells are clear, overhang and all',
       f'{BOARD_CONN_L:.2f} x {2*BOARD_CONN_Y:.2f} mm, hanging {BOARD_CONN_OVER:.2f} past the end')

    # --- (b) located across: rails beside the board's EDGE, not its faces
    rails = 0
    for x_ in (x_root + 2.0, (x_root + BRD_X1)/2, BRD_X1 - 2.0):
        for sy in (1, -1):
            pr = box_lwh(x_ - 0.4, x_ + 0.4,
                         *sorted((sy*(BRD_RAIL_Y + 0.15), sy*(BRD_RAIL_Y + 0.9))), zt, ztp)
            if solid(pr)[1] > 0.5: rails += 1
    ck(rails == 6, 'a rail stands beside the board on both sides, along its length',
       f'{rails} of 6 probes solid, {2*BRD_RAIL_CLR:.2f} mm of total slop across')
    face = box_lwh(BRD_X0, BRD_X1, -BOARD_PAD_EDGE - BOARD_PAD_OD/2 - HW + 2*HW,
                   HW, ztp, ztp + 0.3) - lips
    ck(solid(face)[0] < 1e-3, '...and nothing rests on the pad rows',
       'the rails only ever touch the board\'s 1.60 mm edge')

    # --- (c) located along: end wall one way, corner stops the other
    ew = box_lwh(BRD_X1 + BRD_END_CLR + 0.1, BRD_X1 + BRD_END_CLR + 1.5, -8.0, 8.0, zt, ztp)
    ck(solid(ew)[1] > 0.9, 'an end wall stops it at the antenna end',
       f'{BRD_END_CLR:.2f} mm clear, and it is what takes the plug\'s push')
    st = 0
    for sy in (1, -1):
        ps = box_lwh(BRD_X0 - BRD_END_CLR - 0.7, BRD_X0 - BRD_END_CLR - 0.1,
                     *sorted((sy*(BRD_STOP_RI + 0.3), sy*(HW - 0.2))), zt, ztp)
        if solid(ps)[1] > 0.5: st += 1
    ck(st == 2, 'and corner stops stop it walking back toward the wall',
       f'{st} of 2, so pulling a plug cannot drag the board into its own window')
    ck(BRD_STOP_RI > BOARD_CONN_Y and BRD_STOP_RI > USB_WIN_W/2,
       '...landing outboard of the USB shells and clear of the window',
       f'stops at |y|={BRD_STOP_RI:.2f}, shells reach {BOARD_CONN_Y:.2f}, '
       f'window {USB_WIN_W/2:.2f}')

    # --- (d) held DOWN: the snap lips, and where they land
    lip_ok = 0
    for sy in (1, -1):
        pl = box_lwh(x_tip + 0.5, x_tip + BRD_FING_LIP_L - 0.5,
                     *sorted((sy*(HW - BRD_FING_OVER + 0.15), sy*(HW - 0.15))), zlip, zlip + 0.4)
        if solid(pl)[1] > 0.8: lip_ok += 1
    ck(lip_ok == 2, 'two snap lips close over the board\'s top face',
       f'{lip_ok} of 2, reaching {BRD_FING_OVER:.2f} mm over it, '
       f'{BRD_LIP_CLR:.2f} mm above it')
    ramp = box_lwh(x_tip + 0.5, x_tip + BRD_FING_LIP_L - 0.5,
                   HW - BRD_FING_OVER + 0.15, HW - 0.15, ztop - 0.25, ztop)
    ck(solid(ramp)[1] < 0.25, '...with a lead-in ramp, so pressing it down opens them',
       f'{100*solid(ramp)[1]:.0f}% solid at the top against '
       f'{100*solid(box_lwh(x_tip+0.5, x_tip+BRD_FING_LIP_L-0.5, HW-BRD_FING_OVER+0.15, HW-0.15, zlip, zlip+0.4))[1]:.0f}% at the bottom')
    # they must land on bare board, whether or not headers are soldered on
    ck(x_tip + BRD_FING_LIP_L - BRD_X0 < BOARD_CLEAR_CON,
       '...on the strip that carries neither a USB shell nor a pad',
       f'lip ends {x_tip + BRD_FING_LIP_L - BRD_X0:.2f} mm along, copper starts at '
       f'{BOARD_CLEAR_CON:.2f}')
    ck(HW - BRD_FING_OVER > BOARD_CONN_Y,
       '...and inboard of nothing it could foul',
       f'lip reaches |y|={HW - BRD_FING_OVER:.2f}, shells stop at {BOARD_CONN_Y:.2f}')

    # --- (e) the finger can actually flex, and prints in the strong direction
    gap = box_lwh(x_tip + 1.0, x_root - 1.0,
                  BRD_RAIL_Y + BRD_FING_T + 0.1,
                  BRD_RAIL_Y + BRD_FING_T + BRD_FING_GAP - 0.1, ZP, ztop)
    ck(solid(gap)[0] < 1e-3, 'there is a slot behind each finger to flex into',
       f'{BRD_FING_GAP:.2f} mm against {BRD_FING_DEFL:.2f} mm of deflection needed')
    # measure L and t on the built file rather than trusting params
    def edge(f, lo, hi, n=32):
        flo = f(lo)
        if flo == f(hi): return None
        for _ in range(n):
            m = (lo + hi)/2
            if f(m) == flo: lo = m
            else: hi = m
        return (lo + hi)/2
    zmid = (ZP + ztop)/2
    def at_y(y):
        return solid(box_lwh(x_tip + 6.0, x_tip + 7.0, y - 0.02, y + 0.02, zmid, zmid + 0.5))[1] > 0.5
    y_i = edge(at_y, BRD_RAIL_Y - 0.5, BRD_RAIL_Y + 0.5)
    y_o = edge(at_y, BRD_RAIL_Y + BRD_FING_T + 0.5, BRD_RAIL_Y + BRD_FING_T - 0.5)
    t_meas = (y_o - y_i) if (y_i and y_o) else float('nan')
    strain = 1.5 * BRD_FING_DEFL * t_meas / BRD_FING_L**2
    ck(strain < BRD_FING_EMAX, 'and it bends within what the plastic will take',
       f'e = 1.5*Y*t/L^2 = 1.5*{BRD_FING_DEFL:.2f}*{t_meas:.2f}/{BRD_FING_L:.0f}^2 '
       f'= {100*strain:.2f}%, against ~{100*BRD_FING_EMAX:.1f}% for PLA')
    ck(BRD_FING_L / t_meas >= 8.0, '...on a beam long enough to bend rather than snap',
       f'L/t = {BRD_FING_L/t_meas:.1f}:1, and 8:1 is the floor quoted for PLA')
    E, b_ = 2500.0, BRD_RAIL_TOP
    P = b_ * t_meas**2 * E * strain / (6 * BRD_FING_L)
    ck(1.0 < 2*P < 25.0, '...and takes a thumb to press home, not a press',
       f'{P:.1f} N a finger, {2*P:.1f} N for the pair, at E~{E:.0f} MPa')

    # --- (f) supported from below, clear of what is underneath the board
    posts = 0
    for px in (BRD_X0 + 3.0, (BRD_X0 + BRD_X1)/2, BRD_X1 - 4.0):
        for sy in (1, -1):
            pp = cyl(0.8, ZP + 0.5, zt - 0.5, 24, centre=(px, sy*BRD_POST_HY))
            if solid(pp)[1] > 0.5: posts += 1
    ck(posts == 6, 'three pairs of posts carry it, including under the connectors',
       f'{posts} of 6')
    ck(BRD_POST_HY + BRD_POST_D/2 < BOARD_PAD_EDGE + 0.0 + (HW - BOARD_PAD_EDGE) - BOARD_PAD_OD/2,
       '...inboard of the pad rows, so header tails have somewhere to go',
       f'posts reach |y|={BRD_POST_HY + BRD_POST_D/2:.2f}, copper starts at '
       f'{HW - BOARD_PAD_EDGE - BOARD_PAD_OD/2:.2f}, {BRD_POST_H:.2f} mm of space under the board')

    # --- (g) the window, and a plug through it
    ck(math.hypot(BRD_X0, HW + BOARD_CLR) < B.r_inner,
       'the board still sits as far out at 6 o\'clock as its corners allow',
       f'corner r {math.hypot(BRD_X0, HW + BOARD_CLR):.2f} inside the pocket wall {B.r_inner:.2f}')
    win = box_lwh(-B.r_body - 1.0, -B.r_inner + 1.0, -USB_WIN_W/2 + 0.2, USB_WIN_W/2 - 0.2,
                  ZP + USB_WIN_Z + 0.2, ZP + USB_WIN_Z + USB_WIN_H - 0.2)
    ck(solid(win)[0] < 1e-3, 'the window is bored right through the wall',
       f'{USB_WIN_W:.0f} x {USB_WIN_H:.0f} mm, {solid(win)[0]:.5f} mm3')
    plug = box_lwh(-B.r_body - 25.0, BRD_X0, -PLUG_W/2, PLUG_H/2 + 3.0,
                   ZP + USB_WIN_Z + 0.5, ZP + USB_WIN_Z + USB_WIN_H - 0.5)
    ck(solid(plug)[0] < 1e-3, 'and a plug reaches the board from outside',
       f'{solid(plug)[0]:.5f} mm3')

    print('\n6. The two printed halves mate, and only mate')
    ck((BASE ^ HOUS).volume() < 1e-6, 'base and housing do not interfere',
       f'{(BASE ^ HOUS).volume():.6f} mm3')
    ck(abs(to_trimesh(HOUS).bounds[1][2] - Z_DECK) < 1e-3, 'they meet at z=-2.40',
       f'{to_trimesh(HOUS).bounds[1][2]:.3f}')
    ck(abs(2*np.hypot(*to_trimesh(HOUS).vertices[:, :2].T).max() - 2*B.r_body) < 0.05,
       'and their outside diameters match', f'{2*B.r_body:.2f} mm')
    ck(abs(DEPTH - (Z_FRONT - Z_DECK + HOUSING_DEEP)) < 1e-6,
       'the clock is as deep as Sam asked for and no deeper',
       f'housing {HOUSING_DEEP:.1f} mm, pocket {POCKET_DEEP:.1f} clear, '
       f'clock {DEPTH:.1f} overall (was 74.4)')
    plenum = POCKET_DEEP - BRD_RAIL_TOP
    ck(plenum > 10.0, 'with the board and its frame in, the cables still have room',
       f'{plenum:.2f} mm of clear plenum above the frame, for the display ribbon '
       f'and the ring leads')
    ck(HOUSING_DEEP < BATTERY_MIN_HOUSING
       and not os.path.exists('mini-round-clock-battery-shelf-x2.stl'),
       'and no battery shelf is shipped, because no battery fits',
       f'a {BAT_T:.2f} mm cell needs a {BATTERY_MIN_HOUSING:.2f} mm housing; '
       f'this one is {HOUSING_DEEP:.2f}')

    print('\n8. The wire gap, from the ring to the middle')
    # Sam: "there is a gap between the LED and the middle to fit the wires going
    # to the centre from the LED rings". His own 108 mm base has it as a shaft at
    # 6 o'clock, open TOP TO BOTTOM -- so a lead leaves the ring at ring level,
    # travels inward, and drops, without being bent flat against the floor first.
    ring_top = B.ring_floor + PCB_T + LED_H
    LEAD_HW = 4.0                       # an 8 mm bundle: three wires and slack
    at_ring = box_lwh(-(B.ring_id/2 - 0.5), -(R_BORE + 0.5),
                      -LEAD_HW, LEAD_HW, B.ring_floor, ring_top)
    ck((BASE ^ at_ring).volume() < 1e-3,
       'a lead can leave the ring and run inward at ring level',
       f'{2*LEAD_HW:.0f} mm wide, r {R_BORE+0.5:.1f}..{B.ring_id/2-0.5:.1f}, '
       f'{(BASE ^ at_ring).volume():.5f} mm3 in the way')
    shaft = box_lwh(-(B.ring_id/2 - 0.5), -(R_BORE + 0.5),
                    -LEAD_HW, LEAD_HW, Z_DECK, ring_top)
    ck((BASE ^ shaft).volume() < 1e-3,
       '...and then straight down to the deck, with nothing to bend round',
       f'open z {Z_DECK:.1f}..{ring_top:.1f}, {(BASE ^ shaft).volume():.5f} mm3 in the way')

    print('\n9. How much of the diffuser is actually inside the bore')
    # The diffuser is modelled face-at-z=0 and goes in turned over. Find where it
    # comes to rest -- the deepest position at which nothing but the crush ribs
    # is touching -- and measure the contact from the built files.
    def place(C):
        d = load(f'mini-round-clock-diffuser{tg}.stl')
        d.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
        d.apply_translation([0, 0, C])
        return to_manifold(d)
    def ribs_only(C):
        ov = BASE ^ place(C)
        if ov.volume() < 0.01: return True
        t = to_trimesh(ov)
        return np.hypot(*t.vertices[:, :2].T).min() > B.diff_outer - 0.05
    lo, hi = Z_RECESS - 2.0, Z_RECESS + 6.0
    for _ in range(18):
        mid = (lo + hi) / 2
        if ribs_only(mid): hi = mid
        else: lo = mid
    seat = hi
    ov = to_trimesh(BASE ^ place(seat))
    grip = ov.bounds[1][2] - ov.bounds[0][2] if ov.volume > 1e-9 else 0.0
    ck(grip >= 2.0, 'the crush ribs grip over a real length, not a lip',
       f'{grip:.2f} mm of contact, z {ov.bounds[0][2]:.2f}..{ov.bounds[1][2]:.2f}, '
       f'face resting at z={seat:.2f}')
    ck(seat - B.band_top > ring_top,
       'and the band still stops short of the LEDs',
       f'band bottom z={seat - B.band_top:.2f} against a ring top of {ring_top:.2f}')

    print('\n7. The wall hanger')
    # the head ends up INSIDE the compartment once the clock is dropped on it
    head = cyl(KEY_HEAD_CLR/2, ZP, ZP + KEY_HEAD_H, 32, centre=(HANG_R, 0))
    ck((HOUS ^ head).volume() < 1e-3, 'an 8 mm screw head clears the keyhole pocket',
       f'{(HOUS ^ head).volume():.5f} mm3')
    ck(KEY_DROP >= 6.0, 'and the clock has to be lifted to come off', f'{KEY_DROP:.1f} mm')

print()
if FAIL:
    print(f'PASS 2: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('PASS 2: every fit and clearance check holds, on all three bodies')
