#!/usr/bin/env python3
"""Build the v2 rear end onto Sam's edited base.

    python3 build_v2.py

Writes:
    mini-round-clock-base-v2.stl        Sam's base + the deck + the S3 bay
    mini-round-clock-rearhousing.stl    battery box, wall hanger, cable exit
    mini-round-clock-diffuser-fix.stl   optional: Sam's diffuser, collar shortened

Nothing here guesses at Sam's geometry — every number it keys off was probed
from the uploaded STL and lives in params.py.
"""
import sys, math
import numpy as np, trimesh
sys.path.insert(0, '.')
import csg
from csg import (box_lwh, cyl, cone, tube, wedge, prism, prism_taper,
                 rounded_rect, rot_rect, text_prism, to_manifold, to_trimesh)
from params import *
from manifold3d import Manifold

SEG = 144          # matches the segment count of Sam's own outer wall

# =============================================================================
def load_sams_base(path='base_in.stl'):
    """The uploaded base, recentred, with the boolean residue dropped.

    The export contains a second shell of 605 mm^3 lying in the display-tab
    window (r 35.06-40.90, +/-41.9 deg, z 11.80-15.75). Its faces are coincident
    with the main body's cut surface and it arrived as a +2832/-2227 shell pair,
    which is what a CAD boolean leaves behind when it fails to merge. It is not
    a feature: it fills the slot the display tab has to pass through. Dropped.
    """
    m = trimesh.load(path, process=False)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    main = parts[0]
    b = main.bounds
    main = main.copy()
    main.apply_translation([-(b[0][0]+b[1][0])/2, -(b[0][1]+b[1][1])/2, 0])
    dropped = sum(abs(p.volume) for p in parts[1:])
    print(f'  loaded {path}: main shell {main.volume:.1f} mm^3, dropped {dropped:.1f} mm^3 of residue')
    return to_manifold(main)

# =============================================================================
def build_deck():
    """An annular floor under Sam's base.

    v6 emptied this out. It used to carry the S3 in a window with ledges, a
    beam and a screwed-on keeper; the board lives in the rear housing now, so
    all the deck has to do is close the back, carry the four screw pilots and
    give the housing something to mate against. Everything inside r = 44 is
    open, which is every cable path at once: the display's ribbon coming down
    the tab slot at 12 o'clock, the ring's leads at 6 o'clock, and the run down
    to the board.

    An annulus, printed flat: no window, no ledge, no overhang anywhere.
    """
    # DECK_INSET is 0.00 -- matching Sam's own 144-gon outer wall exactly is
    # clean once finalise() heals the float32 round trip, and it avoids a 0.3 mm
    # overhanging ledge running right round the part at z=0.
    return tube(DECK_RI, R_BODY - DECK_INSET, Z_DECK, Z_BACK, SEG)


def seat_drop(mm):
    """Lower the display seat, so the diffuser's collar stops fouling the module.

    Cut up to the top of the display pocket rather than stopping at the old seat
    plane: stopping there would leave a 0.3 mm down-facing ledge ringing the
    pocket, which is a needless overhang for no gain.
    """
    if mm <= 0:
        return None
    return cyl(R_DISP_POCKET, Z_SEAT - mm, Z_RECESS + 0.5, SEG)


def tab_slot_keep():
    """The volume the display tab has to pass through: a straight slot up to
    just above the tab, then a 45-degree lead-in on the top inner edge."""
    hw, R = TAB_SLOT_HW, TAB_WALL_RO + 5.0
    keep = box_lwh(0.0, R, -hw, hw, Z_BACK - 1.0, TAB_CHAMF_Z)
    keep += prism_taper([(0.0, -hw), (R, -hw), (R, hw), (0.0, hw)],
                        TAB_CHAMF_Z, TAB_WALL_TOP + 0.001,
                        1.0, (hw + (TAB_WALL_TOP - TAB_CHAMF_Z)) / hw)
    return keep


def tab_slot_walls():
    """Narrow the display-tab slot to the tab Sam actually measured.

    His base cuts the slot as an angular wedge sized for a 40 mm tab. The real
    tab is 30.55 mm, so at r=35 the slot is 46.6 mm wide against a 30.55 mm tab
    and the module can rotate +/-25.9 degrees. That is the "doesn't stay
    upright".

    Two walls either side bring it to 31.15 mm. They run from the deck up to the
    ring pocket floor, which also puts back the floor the tab window had removed,
    so the ring is supported at 12 o'clock again. Above them the slot flares back
    out, so the tab still finds its way in.

    They sit at |y| >= 15.575 and the S3 board is |y| <= 12.70, so the two never
    meet.
    """
    solid = wedge(TAB_WALL_RI, TAB_WALL_RO, Z_BACK, TAB_WALL_TOP,
                  -TAB_WALL_AHALF, TAB_WALL_AHALF)
    # The volume the tab needs: a straight slot up to just above the tab, then a
    # 45-degree lead-in chamfer on the top inner edge so a slightly rotated tab
    # still finds its way down. The chamfer has to finish BY the ring pocket
    # floor -- an earlier version carried it 2.2 mm above, straight into the
    # 445 mm3 of space the LED ring occupies, and the checker caught it.
    return solid - tab_slot_keep()


def screw_pilots():
    """Pilot holes for the rear-housing screws.

    Subtracted from the ASSEMBLED base, not from the deck alone: the deck is
    only 2.4 mm thick, so boring it there left the screw to self-tap 8 mm of
    solid PLA off a 2.4 mm guide, which splits the boss as often as it holds.
    """
    holes = None
    for a in SCREW_ANG:
        x, y = SCREW_R*math.cos(math.radians(a)), SCREW_R*math.sin(math.radians(a))
        c = cyl(SCREW_PILOT/2, Z_DECK - 1.0, Z_BACK + SCREW_DEPTH, 32, centre=(x, y))
        holes = c if holes is None else holes + c
    return holes
# =============================================================================
def board_mount(z_floor, RB=None, RI=None):
    """Posts, hooks and the window that hold the S3 in the housing pocket.

    Returns (solid, void). The void is the USB window through the outer wall.

    Sam: "move the board more towards the edge so that the power can be
    connected easily." So the board is as far out at 6 o'clock as its own
    corners allow -- at |y| = 13.15 the pocket wall is at x = -49.27, and the
    board's end sits at -48.50. Its own connector then looks straight out
    through the wall; there is no breakout board any more.
    """
    RB = R_BODY if RB is None else RB
    RI = R_INNER if RI is None else RI
    zt = z_floor + BRD_POST_H                     # PCB underside
    s = None

    def add(m):
        nonlocal s
        s = m if s is None else s + m

    # four posts under the board, inboard of the pad rows
    for px in (BRD_X0 + 5.0, BRD_X1 - 5.0):
        for py in (BRD_POST_HY, -BRD_POST_HY):
            add(cyl(BRD_POST_D/2, z_floor, zt, 32, centre=(px, py)))

    # +x end: two posts and a hook 0.20 mm over the bare end of the board
    zl = zt + BRD_HOOK_LO
    for py in (BRD_HOOK_HY, -BRD_HOOK_HY):
        add(cyl(BRD_POST_D/2, z_floor, zl + BRD_HOOK_T, 32,
                centre=(BRD_X1 + 3.50, py)))
    add(box_lwh(BRD_X1 - BRD_HOOK_OVER, BRD_X1 + 3.50 + BRD_POST_D/2,
                -BRD_HOOK_HY - BRD_POST_D/2, BRD_HOOK_HY + BRD_POST_D/2,
                zl, zl + BRD_HOOK_T))

    # -x end: two posts standing clear of the wall, with arms reaching in over
    # the board's long edges ABOVE everything on it
    zh = zt + BRD_HOOK_HI
    for sy in (1, -1):
        add(cyl(BRD_HOOK_PD/2, z_floor, zh + BRD_HOOK_T, 32,
                centre=(BRD_HOOK_PX, sy * BRD_HOOK_PY)))
        add(box_lwh(BRD_HOOK_PX - BRD_HOOK_PD/2, BRD_HOOK_PX + BRD_HOOK_PD/2,
                    min(sy*BRD_HOOK_IY, sy*BRD_HOOK_PY), max(sy*BRD_HOOK_IY, sy*BRD_HOOK_PY),
                    zh, zh + BRD_HOOK_T))

    # the window the power lead comes in through. 22 x 6 because which
    # connector the board carries is still not a settled fact -- Espressif's
    # v1.1 guide says Micro-USB, the boards sold as DevKitC-1 have two Type-C.
    win = box_lwh(-RB - 2.0, -RI + 2.0, -USB_WIN_W/2, USB_WIN_W/2,
                  z_floor + USB_WIN_Z, z_floor + USB_WIN_Z + USB_WIN_H)
    return s, win


def build_rear_housing(pocket_d, r_body=None, r_inner=None, with_board=True,
                       vent_ang=None, screw_ang=None, screw_r=None):
    """Electronics box + battery pocket + wall hanger. Prints rear-plate-down.

    v6 moved the S3 in here. pocket_d is the clear depth; at 46.50 that is
    8.80 mm of board on its posts, 24.89 of battery above it if one goes in,
    and still 11.31 mm left for the cables coming off the display and the ring
    -- which is what Sam said the old 15.00 and 27.50 mm pockets did not have.
    """
    RB = R_BODY if r_body is None else r_body
    RI = R_INNER if r_inner is None else r_inner
    VA = [50, 75, 100, 260, 285, 310] if vent_ang is None else vent_ang
    SA = SCREW_ANG if screw_ang is None else screw_ang
    SR = SCREW_R if screw_r is None else screw_r
    Z1 = Z_DECK                              # -2.40, mates to the base's deck
    Z0 = Z1 - (PLATE_T + pocket_d)           # rear face, against the wall
    Z_POCKET = Z0 + PLATE_T                  # floor of the pocket

    body = cyl(RB, Z0, Z1, SEG)
    body -= cyl(RI, Z_POCKET, Z1 + 1.0, SEG)

    # No stiffening ribs behind the hanger. An earlier version had them and the
    # checker caught that they ate into the battery footprint. The plate is
    # 3.5 mm and the screw shank bears on 4.6 x 3.5 mm of it, so at a 400 g
    # clock that is about 0.25 MPa against PLA's ~50 MPa yield.

    # --- keyhole. Cut as ONE solid: three overlapping pieces subtracted
    #     separately leave coincident faces that break the mesh in float32.
    kx, kd = HANG_R, KEY_DROP
    zt = Z_POCKET + 1.0
    key = (cyl(KEY_ENTRY_D/2, Z0 - 1.0, zt, 48, centre=(kx - kd, 0))
           + box_lwh(kx - kd, kx, -KEY_SLOT_W/2, KEY_SLOT_W/2, Z0 - 1.0, zt)
           + cyl(KEY_SLOT_W/2, Z0 - 1.0, zt, 32, centre=(kx, 0)))
    body -= key

    # --- screw pillars up to the deck
    pillars, holes = None, None
    for a in SA:
        x, y = SR*math.cos(math.radians(a)), SR*math.sin(math.radians(a))
        p = cyl(3.60, Z0, Z1, 40, centre=(x, y))
        h = (cyl(SCREW_CLEAR/2, Z0 - 1.0, Z1 + 1.0, 32, centre=(x, y))
             + cyl(SCREW_HEAD/2, Z0 - 1.0, Z0 + 3.20, 40, centre=(x, y)))
        pillars = p if pillars is None else pillars + p
        holes = h if holes is None else holes + h
    body += pillars
    body -= holes

    # --- the board, and the window its own connector looks out through
    if with_board:
        mount, win = board_mount(Z_POCKET, RB, RI)
        body += mount
        body -= win

    # --- mains lead exit at 6 o'clock, above the USB window
    z_cab = Z_POCKET + USB_WIN_Z + USB_WIN_H + 3.0
    body -= box_lwh(-RB - 2.0, -RI + 2.0, -CABLE_W/2, CABLE_W/2,
                    z_cab, z_cab + CABLE_H)

    # --- ventilation. A lithium cell in a closed PLA box wants a path for warm
    #     air: slots low and high so it convects when the clock is on a wall.
    vents = None
    for a in VA:
        for k in range(VENT_ROWS + 2):
            z = Z_POCKET + 3.0 + k*(VENT_W + 2.4)
            if z + VENT_W > Z1 - 2.0: continue
            v = wedge(RI - 2.0, RB + 2.0, z, z + VENT_W,
                      a - VENT_L/2, a + VENT_L/2)
            vents = v if vents is None else vents + v
    if vents is not None:
        body -= vents
    return body


def build_shelf(bat_w, r_inner=None):
    """One battery shelf. Print TWO, one either side.

    v6 changed what this part is. It used to be a side shim that stopped the
    battery sliding in y, standing on the pocket floor. The board is on that
    floor now, so the shelf has to hold the battery clear of it as well: it is
    BRD_POST_H + BOARD_T + BOARD_TALL + 1.50 tall, and the battery rests on top
    of the pair rather than on the board.

    Its outer edge IS the pocket circle, so it meets the straight ends at a
    steep angle and nothing anywhere is thinner than SHIM_WALL.
    """
    RI = R_INNER if r_inner is None else r_inner
    h = BRD_POST_H + BOARD_T + BOARD_TALL + 1.50           # 10.30
    h = BRD_POST_H + BOARD_T + BOARD_TALL + BRD_HOOK_T + 1.60    # 12.00
    r_out = RI - 0.35
    y0 = bat_w/2 + SHIM_CLR
    hx = SHIM_HALF_X
    body = box_lwh(-hx, hx, y0, r_out + 5.0, 0.0, h) ^ cyl(r_out, -1.0, h + 1.0, SEG)

    # lighten it: three holes, each kept SHIM_WALL clear of every edge
    y_mid = (y0 + math.sqrt(max(r_out**2 - hx**2, 0.0))) / 2.0
    for cx in (-hx/2, 0.0, hx/2):
        body -= prism([(x + cx, y + y_mid)
                       for x, y in rounded_rect(hx/2 - SHIM_WALL, 9.0, 2.0)], -1.0, h + 1.0)
    return body


def load_sams_diffuser():
    m = trimesh.load('diffuser_in.stl', process=False)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    d = parts[0].copy()
    b = d.bounds
    d.apply_translation([-(b[0][0]+b[1][0])/2, -(b[0][1]+b[1][1])/2, 0])
    return to_manifold(d)


# =============================================================================
class Body:
    """One clock size. Everything that differs between the 24- and the 32-LED
    build is here, and every derived number keeps the relationship the 24-LED
    version was verified with -- the hour marks sit the same distance inboard of
    the ticks, the outer rib is the same width, and so on.
    """
    def __init__(self, tag, n, ring_od, ring_id, r_body, r_ring_i, r_ring_o,
                 r_lip_i, deck_ri, screw_r, screw_ang, vent_ang):
        self.tag, self.n = tag, n
        self.ring_od, self.ring_id = ring_od, ring_id
        self.r_body, self.r_lip_i = r_body, r_lip_i
        self.r_ring_i, self.r_ring_o = r_ring_i, r_ring_o
        self.deck_ri, self.screw_r = deck_ri, screw_r
        self.screw_ang, self.vent_ang = screw_ang, vent_ang
        self.r_inner = r_body - WALL_T
        self.pitch = 360.0 / n
        self.led_r = (ring_od + ring_id) / 4
        # --- diffuser band
        self.diff_outer = r_ring_o + DIFF_FIT
        self.rib_o_ri = self.diff_outer - (DIFF_OUTER_NEW - RIB_O_RI)   # same rib width
        self.tick_ri = self.led_r - (TICK_RO - TICK_RI) / 2
        self.tick_ro = self.led_r + (TICK_RO - TICK_RI) / 2
        # the hours keep their exact offsets inboard of the ticks
        self.mark_ri = self.tick_ri - (TICK_RI - MARK_RI)
        self.mark_ro = self.tick_ri - (TICK_RI - MARK_RO)
        self.mark_ri_maj = self.tick_ri - (TICK_RI - MARK_RI_MAJ)
        self.mark_ro_maj = self.tick_ri - (TICK_RI - MARK_RO_MAJ)
        self.num_r = self.tick_ri - (TICK_RI - NUM_R)
        self.wall_a0 = CELL_WALL_A0 if n == CELL_N else self.pitch / 2
        # the cells sit in the ring pocket. On the 24 body that is Sam's own
        # inner rib at 35.50; on the 32 the pocket has moved out, so they move
        # with it -- everything inboard of the pocket is face, and only face.
        if n == CELL_N:
            self.rib_i_ri, self.rib_i_ro = RIB_I_RI, RIB_I_RO
            self.wall_ri = CELL_WALL_RI
        else:
            self.rib_i_ri, self.rib_i_ro = r_ring_i + 0.15, r_ring_i + 1.35
            self.wall_ri = self.rib_i_ri + 0.40

BODY24 = Body('', 24, RING_OD, RING_ID, R_BODY, R_RING_I, R_RING_O, R_LIP_I,
              DECK_RI, SCREW_R, SCREW_ANG, [50, 75, 100, 260, 285, 310])
BODY32 = Body('-32', RING32_N, RING32_OD, RING32_ID, R_BODY32, R_RING_I32,
              R_RING_O32, R_LIP_I32, DECK_RI, 44.00, [60, 120, 240, 300],
              [80, 105, 255, 280])


# =============================================================================
def build_diffuser(B):
    """Sam's diffuser, with everything he has asked for since first test-fitting.

    1. PRESS FIT, and this time a real one. v3 grew the wall to a 0.10 mm
       interference on diameter and Sam still reports it loose -- 0.10 mm is
       inside a printer's own tolerance. v6 gives the wall 0.10 mm of CLEARANCE
       so it starts square, and puts the interference on eight crush ribs that
       deform as it goes home: 0.60 mm on diameter over 8 x 1.60 mm.
    2. ONE LAYER over the LEDs, in a RADIAL TICK -- "the line needs to be
       perpendicular to the screen, like the lines are."
    3. THE HOURS, debossed on the face.
    4. COLLAR + COLLAR_EXTEND, to reach further in and hold the screen.

    The band that carries all of this is rebuilt rather than patched. Sam's mesh
    is kept only inside BAND_CUT_R, where it is perfect; outboard of that it
    carries 183 non-manifold edges and every union through them made it worse.
    """
    # --- 1. Sam's collar and inner face, which are defect-free ---------------
    d = load_sams_diffuser() ^ cyl(BAND_CUT_R, -1.0, 12.0, SEG)

    # --- 2. the band, rebuilt clean -----------------------------------------
    d += tube(BAND_FACE_RI, B.diff_outer, 0.0, FACE_T, SEG)
    d += tube(B.rib_i_ri, B.rib_i_ro, 0.0, BAND_TOP, SEG)
    d += tube(B.rib_o_ri, B.diff_outer, 0.0, BAND_TOP, SEG)
    rm = (B.wall_ri + B.rib_o_ri + 0.60) / 2
    ln = (B.rib_o_ri + 0.60) - B.wall_ri
    for k in range(B.n):
        a = B.wall_a0 + k * B.pitch
        cx, cy = rm * math.cos(math.radians(a)), rm * math.sin(math.radians(a))
        d += prism(rot_rect(cx, cy, ln, CELL_WALL_T, a), 0.0, BAND_TOP)

    # --- 2b. crush ribs on the outside --------------------------------------
    # tangential blocks standing DIFF_RIB_H proud, with a lead-in so the
    # diffuser starts square in the pocket before anything has to deform
    for k in range(DIFF_RIB_N):
        a = 360.0 / DIFF_RIB_N * (k + 0.5)
        # buried 1.00 mm into the wall: a rib whose inner face sits exactly on
        # the wall's outer surface separates from it in float32
        rr = B.diff_outer + DIFF_RIB_H / 2 - 0.50
        cx, cy = rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a))
        d += prism(rot_rect(cx, cy, DIFF_RIB_H + 1.0, DIFF_RIB_W, a), 0.0, BAND_TOP)
    # one conical cut takes a lead-in off the ribs AND off the wall itself, so
    # the diffuser starts square in the pocket before anything has to deform
    d -= (cyl(B.diff_outer + DIFF_RIB_H + 2.0, -0.10, DIFF_RIB_LEAD, SEG)
          - cone(B.diff_outer - 0.30, B.diff_outer + DIFF_RIB_H,
                 -0.10, DIFF_RIB_LEAD, SEG))

    # --- 3. one radial tick per cell, thinned to a single layer --------------
    ticks = None
    for i in range(B.n):
        a = B.wall_a0 + (i + 0.5) * B.pitch
        cx = (B.tick_ri + B.tick_ro) / 2 * math.cos(math.radians(a))
        cy = (B.tick_ri + B.tick_ro) / 2 * math.sin(math.radians(a))
        t = prism(rot_rect(cx, cy, B.tick_ro - B.tick_ri, TICK_W, a, TICK_END_R),
                  DIFF_MEM_T, BAND_TOP + 0.60)
        ticks = t if ticks is None else ticks + t
    d -= ticks

    # --- 4. the hours, written on the face ----------------------------------
    marks = None
    for h in range(12):
        a = 90.0 - h * 30.0                       # 12 at the top, clockwise
        major = (h % 3 == 0)
        ri, ro = ((B.mark_ri_maj, B.mark_ro_maj) if major else (B.mark_ri, B.mark_ro))
        w = MARK_W_MAJ if major else MARK_W
        key = int(round(a)) % 360
        if key in NUMERALS:
            cx = B.num_r * math.cos(math.radians(a))
            cy = B.num_r * math.sin(math.radians(a))
            m = text_prism(NUMERALS[key], NUM_H, (cx, cy), -0.10, NUM_DEPTH)
        else:
            cx = (ri + ro) / 2 * math.cos(math.radians(a))
            cy = (ri + ro) / 2 * math.sin(math.radians(a))
            m = prism(rot_rect(cx, cy, ro - ri, w, a, w / 2 * 0.9), -0.10, MARK_DEPTH)
        marks = m if marks is None else marks + m
    d -= marks

    # --- 5. a taller collar --------------------------------------------------
    if COLLAR_EXTEND > 0:
        d += tube(COLLAR_EXT_RI, COLLAR_EXT_RO,
                  DIFF_COLLAR_H - 1.0, DIFF_COLLAR_H + COLLAR_EXTEND, SEG)
    return d


# =============================================================================
def build_base(B, sam):
    """Sam's base for the 24-LED body; his base with a new outer ring for the 32.

    The 32-LED ring is 111.85 mm across and the body is 107.99, so the body has
    to grow. Everything inside r = 46 is Sam's and is kept exactly: the bore,
    the display pocket and seat, the display-tab window, his wire slot. Only the
    outer ring -- his ring pocket, outer wall and face recess -- is replaced.
    """
    if B.n == 24:
        return sam
    keep = sam ^ cyl(KEEP_R32, -1.0, 40.0, SEG)
    # Fill his old ring pocket up to 17.00, which becomes the shelf the new
    # diffuser's face lands on. It starts at 10.40 -- inside solid material, not
    # butted onto the pocket floor -- and the display tab's slot is cut back out
    # of it, or the tab could not be got in.
    keep += (tube(34.60, KEEP_R32 - 0.50, 10.40, 17.00, SEG) - tab_slot_keep())

    ann = tube(KEEP_R32 - 1.00, B.r_body, Z_BACK, Z_FRONT, SEG)
    ann -= tube(B.r_ring_i, B.r_ring_o, Z_RING_FLOOR, Z_FRONT + 1.0, SEG)
    # inboard of the new pocket the face sits on the same 17.00 shelf...
    ann -= tube(KEEP_R32 - 2.0, B.r_ring_i, 17.00, Z_FRONT + 1.0, SEG)
    # ...and the plywood face still drops into a 3 mm recess at 19.00
    ann -= tube(KEEP_R32 - 2.0, B.r_lip_i, Z_RECESS, Z_FRONT + 1.0, SEG)
    return keep + ann


def build_deck_for(B):
    # DECK_RI is 30, not 44: at 44 the deck stopped short of Sam's own underside
    # and left a 16 mm annular bridge to print into thin air. At 30 it follows
    # his bore, and the only openings are the ones he already has -- the tab
    # slot at 12 o'clock and the wire slot at 6.
    d = tube(B.deck_ri, B.r_body - DECK_INSET, Z_DECK, Z_BACK, SEG)
    # +/-10, not the full slot width: the tab itself never comes below z=8.60,
    # so this only has to pass the display's ribbon -- and cutting it wider left
    # the tab-slot walls standing over a void, which cost 2 mm3 of self-overlap
    d -= box_lwh(20.0, TAB_WALL_RO + 1.0, -10.0, 10.0, Z_DECK - 1.0, Z_BACK + 1.0)
    # +0.40: cutting the deck at exactly Sam's own slot half-width leaves two
    # coincident planes, and the float32 round trip turns those into a 2 mm3
    # disagreement between two ways of measuring the same solid
    d -= box_lwh(WIRE_SLOT_END - 1.0, -20.0,
                 -WIRE_SLOT_HW - 0.40, WIRE_SLOT_HW + 0.40, Z_DECK - 1.0, Z_BACK + 1.0)
    if B.n != 24:
        d -= box_lwh(-B.r_ring_o + 1.0, WIRE_SLOT_END + 3.0,
                     -WIRE32_HW, WIRE32_HW, Z_DECK - 1.0, Z_BACK + 1.0)
    return d


def screw_pilots_for(B):
    holes = None
    for a in B.screw_ang:
        x, y = B.screw_r*math.cos(math.radians(a)), B.screw_r*math.sin(math.radians(a))
        c = cyl(SCREW_PILOT/2, Z_DECK - 1.0, Z_BACK + SCREW_DEPTH, 32, centre=(x, y))
        holes = c if holes is None else holes + c
    return holes


def assemble_base(B, sam):
    out = build_base(B, sam) + build_deck_for(B) + tab_slot_walls()
    out = out - screw_pilots_for(B)
    if B.n != 24:
        # the ring's leads need a way down from the new pocket to the housing
        out -= box_lwh(-B.r_ring_o + 1.0, WIRE_SLOT_END + 3.0, -WIRE32_HW, WIRE32_HW,
                       Z_DECK - 1.0, Z_RING_FLOOR)
    drop = seat_drop(SEAT_DROP)
    if drop is not None:
        out = out - drop
        print(f'  display seat dropped {SEAT_DROP:.2f} mm '
              f'(now z={Z_SEAT - SEAT_DROP:.2f}) -- diffuser needs no reprint')
    return out


# =============================================================================
def build_stand(B, depth):
    """A desk cradle the clock drops into. Sam: "the stand is another print that
    the clock sits in."

    Built with the clock's axis along +Z and "up in the clock's own plane" along
    +Y, then tilted back STAND_TILT and dropped onto the desk plane, so the
    cradle is a true coaxial cylinder and the clock contacts it along an arc
    rather than at points.

    STAND_LIFT is the number that matters and it is not a style choice: the USB
    plug stands about 13 mm out of the rim at 6 o'clock, which is exactly where
    a cradle wants to hold the clock. The clock therefore sits 26 mm off the
    desk, and a slot runs right through the stand at 6 o'clock for the plug and
    its lead.
    """
    t = STAND_TILT
    R = B.r_body + STAND_CLR
    y_top = -R * math.cos(math.radians(STAND_WRAP))
    x_top =  R * math.sin(math.radians(STAND_WRAP))
    x_out = math.sqrt((R + STAND_WALL)**2 - y_top**2)
    hw = B.r_body                      # the stand is exactly as wide as the clock
    Y_LOW = -160.0

    prof = [( x_out, y_top), ( hw, y_top - STAND_FLARE), ( hw, Y_LOW),
            (-hw, Y_LOW), (-hw, y_top - STAND_FLARE), (-x_out, y_top)]
    s = prism(prof, -(depth + STAND_STOP_T), 0.0)
    s -= cyl(R, -depth - 0.001, 5.0, SEG)                       # the cradle
    s -= cyl(STAND_STOP_RI, -(depth + STAND_STOP_T) - 1.0, -depth, SEG)  # stop wall
    # An arch through it, front to back. It halves the filament, it is the
    # cable route, and its ceiling is a cylinder concentric with the cradle --
    # convex downward, so it needs no support.
    crown = -(R + STAND_SHELL)
    arch = [(-STAND_ARCH_HW, Y_LOW), (STAND_ARCH_HW, Y_LOW),
            (STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0)),
            (10.0, crown), (-10.0, crown),
            (-STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0))]
    s -= prism(arch, -(depth + STAND_STOP_T) - 1.0, 5.0)
    # its roof has to clear the stop wall's inner circle, or a shallow shelf is
    # left across it at the back
    s -= box_lwh(-STAND_NOTCH_HW, STAND_NOTCH_HW, Y_LOW - 1.0, -(STAND_STOP_RI - 6.0),
                 -(depth + STAND_STOP_T) - 1.0, -(depth - STAND_NOTCH_BACK))

    # tilt it back and stand it on the desk
    h0 = STAND_LIFT + B.r_body * math.cos(math.radians(t))
    s = s.rotate([90.0 - t, 0.0, 0.0]).translate([0.0, 0.0, h0])
    return s ^ box_lwh(-200, 200, -200, 200, 0.0, 400.0)


# =============================================================================
if __name__ == '__main__':
    print(summary())
    print('building...')
    sam = load_sams_base()
    parts = []
    for B in (BODY24, BODY32):
        tg = B.tag
        parts += [
            (assemble_base(B, sam),          f'mini-round-clock-base{tg}',      True),
            (build_rear_housing(POCKET_DEEP, B.r_body, B.r_inner,
                                vent_ang=B.vent_ang, screw_ang=B.screw_ang,
                                screw_r=B.screw_r),
                                             f'mini-round-clock-housing{tg}',   True),
            (build_diffuser(B),              f'mini-round-clock-diffuser{tg}',  True),
            (build_stand(B, Z_FRONT - (Z_DECK - HOUSING_DEEP)),
                                             f'mini-round-clock-deskstand{tg}', True),
        ]
    parts.append((build_shelf(BAT_W), 'mini-round-clock-battery-shelf-x2', True))
    for man, fn, strict in parts:
        t = csg.finalise(man, fn, strict=strict)
        t.export(fn + '.stl')
        t.export(fn + '.3mf')
    print('done')
