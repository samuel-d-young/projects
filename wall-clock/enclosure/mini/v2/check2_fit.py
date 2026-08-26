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
import csg

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
    # B.ring_floor, not the global: the 60's pocket floor is 12.48, not 11.80,
    # and probing at the wrong height is how a pocket looks empty when it is not
    ring = tube(B.ring_id/2, B.ring_od/2, B.ring_floor, B.ring_floor + PCB_T + LED_H, 192)
    ck((BASE ^ ring).volume() < 1e-3, f'the {B.ring_od} / {B.ring_id} ring is clear of the base',
       f'{(BASE ^ ring).volume():.5f} mm3')
    ck((ring - BASE).volume() > 0.99*ring.volume(), '...and the pocket is actually empty',
       f'{100*(ring - BASE).volume()/ring.volume():.1f}% clear')
    ck(B.r_ring_i <= B.ring_id/2 and B.r_ring_o >= B.ring_od/2,
       'the pocket brackets the ring on both edges',
       f'{B.r_ring_i:.2f} <= {B.ring_id/2:.2f} and {B.r_ring_o:.2f} >= {B.ring_od/2:.2f}')
    ck(B.r_body - B.r_ring_o >= 3.0, 'and there is a real wall outboard of it',
       f'{B.r_body - B.r_ring_o:.2f} mm')

    print('\n3. The press fit is on the INSIDE, and the outside grips nothing')
    Dt = load(f'mini-round-clock-diffuser{tg}.stl')
    r_out = np.hypot(*Dt.vertices[:, :2].T).max()
    press_r = B.r_lip_i if B.guides else B.r_ring_o
    ck(r_out < press_r, 'the outer wall drops into its pocket with clearance',
       f'{2*(press_r - r_out):.2f} mm on diameter, into r={press_r:.2f}')
    ck(0.20 <= 2*(press_r - r_out) <= 1.00,
       '...enough to clear a printer\'s error, not enough to rattle',
       f'{2*(press_r - r_out):.2f} mm')
    # and the collar carries it instead
    crest = R_DISP_BORE + COLLAR_RIB_H
    zc = (COLLAR_RIB_Z0 + COLLAR_RIB_Z1) / 2
    # in the annulus between the collar's OD and the crest, so it can only read
    # solid if a rib is really there
    probe = sum(1 for k in range(COLLAR_RIB_N)
                if (lambda w: (DIFF ^ w).volume() > 0.5*w.volume())(
                    wedge(DIFF_COLLAR_RO + 0.06, crest - 0.02, zc - 0.3, zc + 0.3,
                          360.0/COLLAR_RIB_N*(k + 0.5) - 1.0,
                          360.0/COLLAR_RIB_N*(k + 0.5) + 1.0)))
    ck(probe == COLLAR_RIB_N, f'all {COLLAR_RIB_N} collar ribs stand proud of the bore',
       f'{probe} of {COLLAR_RIB_N}, crest r={crest:.3f} against a bore of {R_DISP_BORE:.2f}')
    ck(DIFF_COLLAR_RO < R_DISP_BORE,
       'the collar itself has clearance, so it starts square',
       f'{2*(R_DISP_BORE - DIFF_COLLAR_RO):.2f} mm on diameter')
    ck(0.0 < 2*COLLAR_RIB_H <= 0.50, 'and the ribs interfere, but only just',
       f'{2*COLLAR_RIB_H:.2f} mm on diameter over {COLLAR_RIB_N} x {COLLAR_RIB_W:.2f} mm')
    # THE invariant, and the one that was missing while this was being tuned
    # three times: the wall behind the ribs must have so much more clearance than
    # the ribs have interference that the wall can never become the fit itself.
    # That is the failure a rib-height knob cannot tune away.
    wall_clr = 2*(R_DISP_BORE - COLLAR_OD)
    ck(wall_clr >= 0.80 and wall_clr >= 4 * 2*COLLAR_RIB_H,
       '...on a wall that has far more clearance than they have interference',
       f'wall {wall_clr:.2f} mm clear on diameter against {2*COLLAR_RIB_H:.2f} of '
       f'interference, {wall_clr/max(2*COLLAR_RIB_H,1e-9):.0f}x -- the ribs stand '
       f'{R_DISP_BORE + COLLAR_RIB_H - COLLAR_OD:.2f} mm proud and can crush most '
       f'of that before anything else touches')
    ck(os.path.exists('mini-round-clock-collar-gauges.stl')
       and min(GAUGE_HS) <= COLLAR_RIB_H <= max(GAUGE_HS),
       '...and a printed gauge brackets the figure being shipped',
       f'gauges at {", ".join(f"{h:.2f}" for h in GAUGE_HS)}, '
       f'shipping {COLLAR_RIB_H:.2f}')
    ck(COLLAR_RIB_Z1 - COLLAR_RIB_Z0 >= 3.0, '...over a real length of bore',
       f'{COLLAR_RIB_Z1 - COLLAR_RIB_Z0:.2f} mm of engagement')
    # the ribs have to be tapered at the end that enters the bore FIRST, and the
    # collar goes in tip first, so that is the HIGH z end
    lead = np.hypot(*Dt.vertices[np.abs(Dt.vertices[:, 2] - COLLAR_RIB_Z1) < 1e-3][:, :2].T)
    ck(len(lead) == 0 or lead.max() < crest - 0.1,
       '...and tapered at the end that meets the bore first',
       f'r={lead.max():.3f} at z={COLLAR_RIB_Z1:.2f} against a {crest:.3f} crest'
       if len(lead) else 'nothing at full crest there')

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
    x_end  = BRD_X1 + BRD_END_CLR

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
    # v14: no exemption for the antenna end any more. The hood is gone and the
    # clamp is a separate part, so nothing moulded into the housing stands over
    # the board except the two snap lips.
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
                     *sorted((sy*(BRD_FING_YI + 0.15), sy*(HW - 0.15))), zlip, zlip + 0.4)
        if solid(pl)[1] > 0.8: lip_ok += 1
    ck(lip_ok == 2, 'two snap lips close over the board\'s top face',
       f'{lip_ok} of 2, reaching {BRD_FING_OVER:.2f} mm over it, '
       f'{BRD_LIP_CLR:.2f} mm above it')
    ramp = box_lwh(x_tip + 0.5, x_tip + BRD_FING_LIP_L - 0.5,
                   BRD_FING_YI + 0.15, HW - 0.15, ztop - 0.25, ztop)
    ck(solid(ramp)[1] < 0.25, '...with a lead-in ramp, so pressing it down opens them',
       f'{100*solid(ramp)[1]:.0f}% solid at the top against '
       f'{100*solid(box_lwh(x_tip+0.5, x_tip+BRD_FING_LIP_L-0.5, HW-BRD_FING_OVER+0.15, HW-0.15, zlip, zlip+0.4))[1]:.0f}% at the bottom')
    # they must land on bare board, whether or not headers are soldered on
    ck(x_tip + BRD_FING_LIP_L - BRD_X0 < BOARD_CLEAR_CON,
       '...on the strip that carries neither a USB shell nor a pad',
       f'lip ends {x_tip + BRD_FING_LIP_L - BRD_X0:.2f} mm along, copper starts at '
       f'{BOARD_CLEAR_CON:.2f}')
    ck(BRD_FING_YI > BOARD_CONN_Y + BRD_SHIFT_Y + 0.20,
       '...and inboard of nothing it could foul, board sitting as far over as it can',
       f'lip reaches |y|={BRD_FING_YI:.2f}, a shell shifted {BRD_SHIFT_Y:.2f} '
       f'reaches {BOARD_CONN_Y + BRD_SHIFT_Y:.2f}')
    ck(HW - BRD_SHIFT_Y - BRD_FING_YI > 0.50,
       '...and still catches the board with it shifted the other way',
       f'{HW - BRD_SHIFT_Y - BRD_FING_YI:.2f} mm of board edge under the lip, worst case')

    # --- (d2) the antenna end is SCREWED down
    CS = BRD_CLAMP_SEAT
    bosses = 0
    for sy in (1, -1):
        pb = box_lwh(BRD_CLAMP_SX - 1.2, BRD_CLAMP_SX + 1.2,
                     *sorted((sy*(BRD_CLAMP_SY + 1.2), sy*(BRD_CLAMP_SY + 2.4))),
                     ZP + CS - 1.5, ZP + CS - 0.2)
        if solid(pb)[1] > 0.8: bosses += 1
    ck(bosses == 2, 'two screw bosses carry a clamp over the antenna end',
       f'{bosses} of 2, {BRD_CLAMP_BOSS:.2f} mm across, seat {CS:.2f} above the pocket floor')
    drilled = 0
    for sy in (1, -1):
        ph = cyl(SCREW_PILOT/2 - 0.15, ZP + CS - BRD_CLAMP_DEEP + 0.3, ZP + CS - 0.3,
                 24, centre=(BRD_CLAMP_SX, sy*BRD_CLAMP_SY))
        if solid(ph)[0] < 1e-3: drilled += 1
    ck(drilled == 2, '...each drilled for an M3 self-tapper, and not through the back',
       f'{drilled} of 2: {SCREW_PILOT:.2f} mm pilot, {BRD_CLAMP_DEEP:.2f} deep into '
       f'{CS + PLATE_T:.2f} mm of material')
    seat = box_lwh(BRD_X0 + BRD_CLAMP_PAD0, BRD_CLAMP_SX + BRD_CLAMP_BOSS/2,
                   -BRD_CLAMP_W, BRD_CLAMP_W, ZP + CS + 0.15, ZP + BRD_RAIL_TOP + 1.0)
    ck(solid(seat)[0] < 1e-3, '...and the bar has a clear plane to sit on',
       'nothing in its footprint stands above the seat, end wall included')
    ck(BRD_CLAMP_SX - BRD_CLAMP_BOSS/2 > BRD_X0 + BOARD_L_MAX,
       '...with both screws BEYOND the longest board, never over a pad row',
       f'boss starts {BRD_CLAMP_SX - BRD_CLAMP_BOSS/2 - BRD_X0:.2f} mm along, '
       f'the longest board ends at {BOARD_L_MAX:.2f}')
    ck(BRD_CLAMP_Y + BRD_SHIFT_Y < BOARD_CLEAR_ANT_Y,
       '...and its pad presses between the pad rows, so headers do not matter',
       f'pad |y|={BRD_CLAMP_Y:.2f}, copper starts at {BOARD_CLEAR_ANT_Y:.2f} and the '
       f'board can sit {BRD_SHIFT_Y:.2f} over')
    ck(BRD_CLAMP_PAD0 > BOARD_MOD_END + 1.0,
       '...behind the WROOM module, on bare board',
       f'pad starts {BRD_CLAMP_PAD0:.2f} mm along, module ends at {BOARD_MOD_END:.2f}')
    ck(BOARD_L_MIN > BRD_CLAMP_PAD0 + 0.50,
       '...and the shortest board the bay takes still reaches it',
       f'{BOARD_L_MIN - BRD_CLAMP_PAD0:.2f} mm of pad at L={BOARD_L_MIN:.2f}, '
       f'{BOARD_L - BRD_CLAMP_PAD0:.2f} at {BOARD_L:.2f}')
    ck(BRD_CLAMP_SEAT < BRD_POST_H + BOARD_T,
       '...and it lands on the BOARD, not on its own bosses',
       f'seat {BRD_CLAMP_SEAT:.2f} against a board top at '
       f'{BRD_POST_H + BOARD_T:.2f} -- {BRD_POST_H + BOARD_T - BRD_CLAMP_SEAT:.2f} mm of grip')

    # --- (d2b) the clamp bar, PUT BACK IN THE HOUSING.
    # It is built and printed lying on its top face, so nothing had ever
    # measured it against the thing it bolts to. Load the STL, turn it over,
    # drop it on its bosses, and check the assembly rather than the drawing.
    if os.path.exists('mini-round-clock-board-clamp.stl'):
        cm = trimesh.load('mini-round-clock-board-clamp.stl', process=False)
        cm.merge_vertices()
        X0c = BRD_X0 + BRD_CLAMP_PAD0 - 1.50
        X1c = BRD_CLAMP_SX + BRD_CLAMP_BOSS/2 + 1.50
        T = np.eye(4)
        T[2, 2] = -1.0                                   # printed upside down
        T[2, 3] = ZP + BRD_CLAMP_SEAT + BRD_CLAMP_T
        T[0, 3] = (X0c + X1c)/2                          # build() centred it in x
        # trimesh already fixes the winding for a negative-determinant
        # transform; inverting again here turned the bar inside out and made
        # every boolean below meaningless (it read -1.7 mm3 of overlap)
        cm.apply_transform(T)
        assert cm.volume > 0, 'clamp bar came through the transform inside out'
        CL = csg.to_manifold(cm)
        ck(abs(cm.bounds[0][2] - (ZP + BRD_CLAMP_SEAT)) < 1e-3,
           'the clamp bar, turned over, lands exactly on its bosses',
           f'its lowest plane is z={cm.bounds[0][2]:.3f}, the seat is '
           f'{ZP + BRD_CLAMP_SEAT:.3f}')
        ck((CL ^ HOUS).volume() < 1e-3,
           '...without fouling the housing anywhere',
           f'{(CL ^ HOUS).volume():.5f} mm3 of overlap with the part it bolts to')
        pcb_top = box_lwh(BRD_X0, BRD_X1, -HW, HW, ztp - 0.02, ztp + 0.02)
        ck((CL ^ pcb_top).volume() > 1.0,
           '...and its pad does land on the board',
           f'{(CL ^ pcb_top).volume():.1f} mm3 of pad over the PCB\'s top face')
        rows = box_lwh(BRD_X0, BRD_X1,
                       BOARD_CLEAR_ANT_Y - BRD_SHIFT_Y, HW, ztp, ztp + 20.0)
        rows += box_lwh(BRD_X0, BRD_X1,
                        -HW, -(BOARD_CLEAR_ANT_Y - BRD_SHIFT_Y), ztp, ztp + 20.0)
        ck((CL ^ rows).volume() < 1e-3,
           '...and never crosses a pad row, at any height',
           'so headers can point either way, or be left off')
        mod = box_lwh(BRD_X0, BRD_X0 + BOARD_MOD_END, -HW, HW,
                      ztp, ztp + BOARD_TALL)
        ck((CL ^ mod).volume() < 1e-3,
           '...and cannot come down on the WROOM module',
           f'relieved {BRD_CLAMP_RLF:.2f} mm short of the pad, which starts '
           f'{BRD_CLAMP_PAD0:.2f} mm along')
        for sy in (1, -1):
            sh = cyl(SCREW_CLEAR/2 - 0.2, ZP + BRD_CLAMP_SEAT - 0.1,
                     ZP + BRD_CLAMP_SEAT + BRD_CLAMP_T + 0.1, 24,
                     centre=(BRD_CLAMP_SX, sy*BRD_CLAMP_SY))
            if (CL ^ sh).volume() > 1e-3: FAIL.append('clamp screw hole blocked')
        ck('clamp screw hole blocked' not in FAIL,
           '...with both screw holes clear, over their pilots',
           f'{SCREW_CLEAR:.2f} mm clearance for an M3, into a {SCREW_PILOT:.2f} pilot')

    # --- (d3) THE ONE THAT v9 FAILED. Every clearance here is checked against
    # what the printer will actually leave, not against what was drawn. A slot
    # loses FDM_SLOT_UNDER across; if the nominal clearance is smaller than
    # that, it is not a clearance, it is an interference fit with a nice label.
    slot_w = 2*BRD_RAIL_Y - FDM_SLOT_UNDER
    ck(slot_w - BOARD_W_MAX >= 0.10,
       'the WORST printed rail slot still clears the widest board it claims to take',
       f'{2*BRD_RAIL_Y:.2f} drawn -> {slot_w:.2f} printed, against {BOARD_W_MAX:.2f} '
       f'of board: {slot_w - BOARD_W_MAX:+.2f}')
    slot_l = BOARD_L + BRD_END_CLR - FDM_SLOT_UNDER
    ck(slot_l - BOARD_L_MAX >= 0.10,
       '...and the worst printed bay still swallows the longest',
       f'{BOARD_L + BRD_END_CLR:.2f} drawn -> {slot_l:.2f} printed, against '
       f'{BOARD_L_MAX:.2f} of board: {slot_l - BOARD_L_MAX:+.2f}')
    ck(2*BRD_RAIL_CLR > FDM_SLOT_UNDER,
       '...so the rails are a guide and not a press fit',
       f'{2*BRD_RAIL_CLR:.2f} mm of drawn slop against {FDM_SLOT_UNDER:.2f} of shrink')

    # --- (d4) every ledge in the frame hangs off ONE edge, so its reach is the
    # whole overhang, not half a span. check3 catches a ledge that stands on
    # nothing; this one keeps the ones that do stand on something short enough
    # to print. 2.50 is the ceiling -- the snap lips ask 1.60 and the hood 2.00.
    LEDGE_MAX = 2.50
    ck(BRD_FING_OVER <= LEDGE_MAX,
       'no ledge in the frame reaches further than a nozzle will carry it',
       f'the snap lips at {BRD_FING_OVER:.2f} are the only ones left, against a '
       f'{LEDGE_MAX:.2f} ceiling -- the hood that needed 2.00 is a screwed bar now')

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

    print('\n9. Where the diffuser comes to rest, and what it clears there')
    # v8 got this wrong and Sam felt it. It measured the seat by pushing the
    # diffuser into the BARE base -- no LED ring, no display module -- so the
    # crush ribs were the only thing stopping it, and it concluded the band
    # needed to be 2 mm taller. At the real seat that drove the band 2.00 mm
    # into the LED ring. So the seat is now asserted against the base's own
    # geometry, and the ring clearance is measured there.
    seat = DIFF_SEAT_Z
    Dp = load(f'mini-round-clock-diffuser{tg}.stl')
    Dp.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
    Dp.apply_translation([0, 0, seat])
    DP = to_manifold(Dp)
    ring = tube(B.ring_id/2, B.ring_od/2, B.ring_floor, B.ring_floor + PCB_T + LED_H, 192)
    ck((DP ^ ring).volume() < 1e-3,
       'at its seat the diffuser is nowhere near the LED ring',
       f'{(DP ^ ring).volume():.4f} mm3; band underside z='
       f'{seat - B.band_top:.2f}, ring top z={B.ring_floor + PCB_T + LED_H:.2f}, '
       f'clear by {seat - B.band_top - (B.ring_floor + PCB_T + LED_H):.2f} mm')
    gap = seat - B.band_top - (B.ring_floor + PCB_T + LED_H)
    if B.guides:
        # On a guide body the band is SUPPOSED to come down to the shelf -- that
        # is what traps the perspex -- so the LED tops are level with it by
        # construction. The relief is what keeps it off the LEDs themselves.
        ck(abs(gap) < 0.01, 'the band lands on the guide shelf, as it must',
           f'{gap:+.3f} mm, and the strips are trapped between it and the shelf')
        ck(GUIDE_LED_CLR >= 0.30, '...with the band relieved over the LEDs',
           f'{GUIDE_LED_CLR:.2f} mm of relief across r '
           f'{B.rib_i_ri:.2f}..{B.r_ring_o:.2f}')
    else:
        ck(gap >= 1.0, '...with room for a printer to be wrong about it',
           f'{gap:.2f} mm of margin')
    # the land it actually rests on
    land = tube(R_DISP_BORE + 0.2, 35.0, DIFF_WALL_CREST - 0.4, DIFF_WALL_CREST - 0.1, 192)
    ck((BASE ^ land).volume() > 0.8*land.volume(),
       'and it rests on a real land, not on a lip',
       f'annular land r {R_DISP_BORE + 0.2:.2f}..35.00 with its top at z='
       f'{DIFF_WALL_CREST:.2f}')
    ck((DP ^ BASE).volume() < 200.0,
       'the only thing it touches in the base is that land and the bore',
       f'{(DP ^ BASE).volume():.1f} mm3, which is the collar ribs crushing')
    # The two ceilings. Both of these were frozen constants once and both drifted
    # silently when something upstream of them moved, so they are asserted now.
    ck(DIFF_SEAT_Z <= Z_FRONT + 0.001,
       'the face fits inside the front recess rather than standing proud',
       f'face top z={DIFF_SEAT_Z:.2f} against a front face at {Z_FRONT:.2f}; '
       f'FACE_T {FACE_T:.2f} of a possible {Z_FRONT - DIFF_WALL_CREST:.2f}')
    ck(abs((DIFF_SEAT_Z - FACE_T) - DIFF_WALL_CREST) < 1e-9,
       '...and its underside is exactly on the land, by construction',
       f'{DIFF_SEAT_Z - FACE_T:.2f} = {DIFF_WALL_CREST:.2f}')
    # v14: this used to compare the tip against Z_SEAT + DISP_TAB_T -- the top of
    # the module's bare TAB, 2.40 mm below the surface the collar actually lands
    # on. It passed while the collar was 1.77 mm inside the screen. The ceiling
    # is the module's FRONT FACE, and it is measured on the built diffuser now
    # rather than recomputed from the same parameters the part was built from.
    tip = DP.bounding_box()[2]
    face = Z_SEAT + DISP_T
    ck(tip >= face - 1e-6,
       'the collar stops short of the screen instead of pushing it forward',
       f'tip z={tip:.2f}, the module\'s front face at {face:.2f} '
       f'(seat {Z_SEAT:.2f} + {DISP_T:.2f} of module) -- {tip - face:+.2f} mm')
    ck(tip - face <= 1.00 + 1e-9,
       '...but close enough to still hold it in',
       f'{tip - face:.2f} mm of float left to the module, against a 1.00 ceiling')

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
