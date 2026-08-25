#!/usr/bin/env python3
"""Does everything fit, on both bodies, measured on the built STLs?

Nothing here reads the code that made the parts -- it loads the files that will
be sliced and probes them as solids.
"""
import sys, math; sys.path.insert(0, '.')
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

    print('\n5. The S3 in the housing, and its own connector out through the wall')
    ZP = Z_DECK - (PLATE_T + POCKET_DEEP) + PLATE_T
    zt = ZP + BRD_POST_H
    pcb  = box_lwh(BRD_X0, BRD_X1, -BOARD_W/2, BOARD_W/2, zt, zt + BOARD_T)
    # the +x hook deliberately closes 0.20 mm over the last BRD_HOOK_OVER mm of
    # the board, which is bare PCB (the two 22-pin rows are 53.34 mm on a 62.74
    # board, leaving 4.70 mm clear at each end), so that strip is excluded here
    tall = box_lwh(BRD_X0, BRD_X1 - BRD_HOOK_OVER, -BOARD_W/2, BOARD_W/2,
                   zt + BOARD_T, zt + BOARD_T + BOARD_TALL)
    ck((HOUS ^ pcb).volume() < 1e-3, 'the PCB does not intersect the housing',
       f'{(HOUS ^ pcb).volume():.5f} mm3')
    ck((HOUS ^ tall).volume() < 1e-3, 'nor does anything on top of it',
       f'{(HOUS ^ tall).volume():.5f} mm3')
    ck(math.hypot(BRD_X0, BOARD_W/2 + BOARD_CLR) < B.r_inner,
       'the board sits as far out at 6 o\'clock as its corners allow',
       f'corner r {math.hypot(BRD_X0, BOARD_W/2 + BOARD_CLR):.2f} inside the pocket wall {B.r_inner:.2f}')
    # posts really under it, hooks really over it
    for px in (BRD_X0 + 5.0, BRD_X1 - 5.0):
        probe = cyl(1.0, ZP + 0.5, zt - 0.5, 24, centre=(px, BRD_POST_HY))
        ck((HOUS ^ probe).volume() > 0.5*probe.volume(), f'a post stands under x={px:+.1f}',
           f'{100*(HOUS ^ probe).volume()/probe.volume():.0f}% solid')
    hk = box_lwh(BRD_X1 - 1.0, BRD_X1, -4.0, 4.0, zt + BRD_HOOK_LO, zt + BRD_HOOK_LO + BRD_HOOK_T)
    ck((HOUS ^ hk).volume() > 0.5*hk.volume(), 'a hook closes over the +x end',
       f'{1000*(zt + BRD_HOOK_LO - (zt + BOARD_T)):.0f} um of float there')
    hk2 = box_lwh(BRD_HOOK_PX - 1.0, BRD_HOOK_PX + 1.0, BRD_HOOK_IY, BRD_HOOK_IY + 1.0,
                  zt + BRD_HOOK_HI, zt + BRD_HOOK_HI + BRD_HOOK_T)
    ck((HOUS ^ hk2).volume() > 0.5*hk2.volume(), 'and an arm closes over the -x end',
       f'above everything on the board, so it cannot foul a connector')
    # the window, and a plug through it
    win = box_lwh(-B.r_body - 1.0, -B.r_inner + 1.0, -USB_WIN_W/2 + 0.2, USB_WIN_W/2 - 0.2,
                  ZP + USB_WIN_Z + 0.2, ZP + USB_WIN_Z + USB_WIN_H - 0.2)
    ck((HOUS ^ win).volume() < 1e-3, 'the window is bored right through the wall',
       f'{USB_WIN_W:.0f} x {USB_WIN_H:.0f} mm, {(HOUS ^ win).volume():.5f} mm3')
    plug = box_lwh(-B.r_body - 25.0, BRD_X0, -PLUG_W/2, PLUG_H/2 + 3.0,
                   ZP + USB_WIN_Z + 0.5, ZP + USB_WIN_Z + USB_WIN_H - 0.5)
    ck((HOUS ^ plug).volume() < 1e-3, 'and a plug reaches the board from outside',
       f'{(HOUS ^ plug).volume():.5f} mm3')

    print('\n6. The two printed halves mate, and only mate')
    ck((BASE ^ HOUS).volume() < 1e-6, 'base and housing do not interfere',
       f'{(BASE ^ HOUS).volume():.6f} mm3')
    ck(abs(to_trimesh(HOUS).bounds[1][2] - Z_DECK) < 1e-3, 'they meet at z=-2.40',
       f'{to_trimesh(HOUS).bounds[1][2]:.3f}')
    ck(abs(2*np.hypot(*to_trimesh(HOUS).vertices[:, :2].T).max() - 2*B.r_body) < 0.05,
       'and their outside diameters match', f'{2*B.r_body:.2f} mm')
    ck(DEPTH >= 50.0, 'the clock is deep enough for the cables Sam asked for',
       f'housing {HOUSING_DEEP:.1f} mm, pocket {POCKET_DEEP:.1f} clear, clock {DEPTH:.1f} overall')
    left = POCKET_DEEP - (BRD_POST_H + BOARD_T + BOARD_TALL) - BAT_T - 1.5
    ck(left > 8.0, 'with the board and a battery in, there is still cable room',
       f'{left:.2f} mm above the battery')

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
