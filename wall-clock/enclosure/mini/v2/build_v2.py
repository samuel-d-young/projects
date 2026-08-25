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
from manifold3d import Manifold, JoinType

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
    """A frame that actually holds the S3, and prints with no support anywhere.

    Returns (solid, void). The void is the USB window through the outer wall.

    The board has NO mounting holes -- Espressif's v1.1 dimension drawing shows
    two 22-pin rows and nothing else -- so it has to be captured mechanically.
    What was here before was a tray: four posts under the middle of the board,
    nothing locating it across, and the -x retainer 3.40 mm clear of the board's
    top face. It rattled in every direction.

    WHAT HOLDS IT NOW
      rails        two walls at |y| = BRD_RAIL_Y, touching only the board's
                   1.6 mm EDGE. They locate it across to 0.10 mm a side and
                   never touch a face, so pads, solder fillets and header
                   strips are all irrelevant to them.
      end wall     at the antenna end. Takes the USB plug's insertion load,
                   which is the only real force this thing ever sees.
      snap fingers two, at the connector end, clamping the board down onto its
                   posts. Their lips land in the clear strips at |y| 10.54 to
                   12.70, over the last 7.15 mm of board that carries neither
                   the USB shells nor the pad rows -- so they work with or
                   without headers soldered on.
      posts        three pairs, at |y| = 6.50: between the USB shells' end tabs
                   at the connector end, mid-board, and under the antenna end.

    The antenna end gets no clamp and should not have one: it has 0.55 mm of
    clear board and the WROOM module sits on it. It does not need one either --
    a 1.6 mm FR4 board is rigid over 62.74 mm, so an end held top, bottom and
    sideways cannot let the far end lift.

    PRINT ORIENTATION, which is the other half of the question. The housing
    prints rear-plate-down, so this whole frame grows upward off the pocket
    floor and every wall in it is vertical. The fingers are part of that: each
    is a wall with a slot behind it, so its long axis AND its flexing direction
    are both in the XY plane -- the strong orientation. A finger standing up in
    z would put the bending stress straight across the layer bonds, which is
    exactly where printed snap fits break. The only overhangs in the part are
    the two lips, each a 0.90 mm ledge, and each lip's upper face is a 63 degree
    lead-in ramp rather than a flat roof, so there is nothing to bridge.
    """
    RB = R_BODY if RB is None else RB
    RI = R_INNER if RI is None else RI
    z0 = z_floor
    zt = z0 + BRD_POST_H                        # PCB underside
    z_lip = z0 + BRD_LIP_Z0                     # underside of the snap lips
    z_top = z0 + BRD_RAIL_TOP
    s = None

    def add(m):
        nonlocal s
        s = m if s is None else s + m

    RY, RT = BRD_RAIL_Y, BRD_RAIL_T
    x_end = BRD_X1 + BRD_END_CLR                # inner face of the end wall
    x_tip = BRD_X0 + BRD_FING_X0                # finger tip
    x_root = x_tip + BRD_FING_L                 # where it joins the rail

    # --- rails, from the finger root to the end wall
    for sy in (1, -1):
        add(box_lwh(x_root, x_end + RT,
                    *sorted((sy*RY, sy*(RY + RT))), z0, z_top))

    # --- end wall: the plug's load path, and the +x stop
    add(box_lwh(x_end, x_end + RT, -(RY + RT), RY + RT, z0, z_top))

    # --- snap fingers
    for sy in (1, -1):
        y_in, y_out = sy*RY, sy*(RY + BRD_FING_T)
        add(box_lwh(x_tip, x_root, *sorted((y_in, y_out)), z0, z_top))
        # The lip, and its lead-in ramp, as the hull of two thin slices: at the
        # bottom it reaches BRD_FING_OVER over the board, at the top it is back
        # flush with the rail, so pressing the board down wedges the finger out.
        # Built buried BRD_FING_BURY into the finger rather than butted against
        # its face -- a coincident face here does not survive float32.
        y_lip = sy*(BOARD_W/2 - BRD_FING_OVER)
        y_bury = sy*(RY + BRD_FING_BURY)
        lo = box_lwh(x_tip, x_tip + BRD_FING_LIP_L,
                     *sorted((y_lip, y_bury)), z_lip, z_lip + 0.01)
        hi = box_lwh(x_tip, x_tip + BRD_FING_LIP_L,
                     *sorted((sy*(RY - 0.01), y_bury)), z_top - 0.01, z_top)
        add((lo + hi).hull())

    # --- corner stops at the connector end, so the board cannot walk toward the
    #     wall when a plug is pulled out. They butt the board's END FACE, in the
    #     strips outboard of the USB shells, and stop short of the window.
    for sy in (1, -1):
        # started at -RI + 0.5, not -RI - 1.0: at |y| = 14.80 the outer wall is
        # only at x = -51.92, and running the stop out to -RI - 1.0 pushed 0.07
        # mm of it through the outside of the clock. Starting inboard still
        # buries it 0.8-1.7 mm into the wall, which is what fuses it on.
        add(box_lwh(-RI + 0.5, BRD_X0 - BRD_END_CLR,
                    *sorted((sy*BRD_STOP_RI, sy*(RY + RT))), z0, z_lip))

    # --- posts under it
    for px in (BRD_X0 + 3.0, (BRD_X0 + BRD_X1)/2, BRD_X1 - 4.0):
        for py in (BRD_POST_HY, -BRD_POST_HY):
            add(cyl(BRD_POST_D/2, z0, zt, 32, centre=(px, py)))

    # --- the window the board's own connector looks out through
    win = box_lwh(-RB - 2.0, -RI + 2.0, -USB_WIN_W/2, USB_WIN_W/2,
                  z0 + USB_WIN_Z, z0 + USB_WIN_Z + USB_WIN_H)
    return s, win


def build_rear_housing(pocket_d, r_body=None, r_inner=None, with_board=True,
                       vent_ang=None, screw_ang=None, screw_r=None):
    """Electronics box + battery pocket + wall hanger. Prints rear-plate-down.

    v6 moved the S3 in here; v9 halves the depth. pocket_d is the clear depth;
    at 21.50 that is 7.40 mm of board and its frame, and 14.10 mm of clear
    plenum above it for the display ribbon and the ring leads. A battery no
    longer fits -- see BATTERY_MIN_HOUSING in params.
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
                 r_lip_i, deck_ri, screw_r, screw_ang, vent_ang, guides=False):
        self.tag, self.n = tag, n
        self.ring_od, self.ring_id = ring_od, ring_id
        self.r_body, self.r_lip_i = r_body, r_lip_i
        self.r_ring_i, self.r_ring_o = r_ring_i, r_ring_o
        self.deck_ri, self.screw_r = deck_ri, screw_r
        self.screw_ang, self.vent_ang = screw_ang, vent_ang
        self.guides  = guides
        # the numerals sit just inboard of the LED apertures, which is where the
        # Echo has them. num_r is set at the END of __init__, once tick_ri is
        # known -- it differs on a guide body -- see NUM_MARGIN in params.
        self.num_h = NUM_H_60 if guides else (NUM_H_24 if n == CELL_N else NUM_H_32)
        self.ring_floor = Z_RING_FLOOR60 if guides else Z_RING_FLOOR
        self.band_top   = BAND_TOP60 if guides else BAND_TOP
        self.r_inner = r_body - WALL_T
        self.pitch = 360.0 / n
        self.led_r = (ring_od + ring_id) / 4
        # --- diffuser band
        # on a guide body the diffuser is the whole face, out to the lip, not
        # just an insert in the ring pocket -- so that is what it presses into
        self.diff_outer = (r_lip_i if guides else r_ring_o) + DIFF_FIT
        self.rib_o_ri = self.diff_outer - (DIFF_OUTER_NEW - RIB_O_RI)   # same rib width
        self.tick_ri = self.led_r - (TICK_RO - TICK_RI) / 2
        self.tick_ro = self.led_r + (TICK_RO - TICK_RI) / 2
        # the hours keep their exact offsets inboard of the ticks
        self.mark_ri = self.tick_ri - (TICK_RI - MARK_RI)
        self.mark_ro = self.tick_ri - (TICK_RI - MARK_RO)
        self.mark_ri_maj = self.tick_ri - (TICK_RI - MARK_RI_MAJ)
        self.mark_ro_maj = self.tick_ri - (TICK_RI - MARK_RO_MAJ)
        self.wall_a0 = CELL_WALL_A0 if n == CELL_N else self.pitch / 2
        # the cells sit in the ring pocket. On the 24 body that is Sam's own
        # inner rib at 35.50; on the 32 the pocket has moved out, so they move
        # with it -- everything inboard of the pocket is face, and only face.
        if guides:
            self.rib_i_ri, self.rib_i_ro = r_ring_i + 0.15, r_ring_i + 1.35
            self.wall_ri = self.rib_i_ri
            self.tick_ri, self.tick_ro = APER_RI, APER_RO
            self.mark_ri, self.mark_ro = MARK60_RI, MARK60_RO
            self.mark_ri_maj, self.mark_ro_maj = MARK60_RI_MAJ, MARK60_RO_MAJ
        elif n == CELL_N:
            self.rib_i_ri, self.rib_i_ro = RIB_I_RI, RIB_I_RO
            self.wall_ri = CELL_WALL_RI
        else:
            self.rib_i_ri, self.rib_i_ro = r_ring_i + 0.15, r_ring_i + 1.35
            self.wall_ri = self.rib_i_ri + 0.40
        # --- where the numerals go, on every body, by one rule
        # Their OUTER edge sits NUM_MARGIN inboard of the aperture's inner edge,
        # so they read as a ring of hours just inside the dots -- the Echo's
        # layout -- and they can never break into a 0.20 mm aperture membrane.
        self.num_r = self.tick_ri - NUM_MARGIN - self.num_h / 2

BODY24 = Body('', 24, RING_OD, RING_ID, R_BODY, R_RING_I, R_RING_O, R_LIP_I,
              DECK_RI, SCREW_R, SCREW_ANG, [50, 75, 100, 260, 285, 310])
BODY32 = Body('-32', RING32_N, RING32_OD, RING32_ID, R_BODY32, R_RING_I32,
              R_RING_O32, R_LIP_I32, DECK_RI, 44.00, [60, 120, 240, 300],
              [80, 105, 255, 280])
BODY60 = Body('-60', RING60_N, RING60_OD, RING60_ID, R_BODY60, R_RING_I60,
              R_RING_O60, R_LIP_I60, DECK_RI, SCREW_R60, [45, 135, 225, 315],
              [80, 105, 255, 280], guides=True)


def taper_slot(a_deg, r0, r1, w0, w1, z0, z1):
    """A radial slot that widens as it goes out -- the aperture over a light
    guide, paid out to match the light falling off along the strip."""
    a = math.radians(a_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(r0, -w0/2), (r1, -w1/2), (r1, w1/2), (r0, w0/2)]
    return prism([(u*ca - v*sa, u*sa + v*ca) for u, v in pts], z0, z1)


def build_light_guides(B):
    """The 60 light guides, printed, as one part.

    This is the alternative to cutting 60 strips of perspex. Print it in CLEAR
    or NATURAL PETG -- white PLA is opaque and would do nothing. A printed guide
    is a worse pipe than acrylic (the layer lines scatter) and a better lamp for
    exactly the same reason: it glows along its length instead of dumping the
    light out of the far end.

    The strips are joined by a 1.40 mm ring at the outer end so it drops in as
    one piece. Cut perspex instead if you have it -- 60 off 6.00 x 3.00 x 30.00,
    and see the README for how, because the Aura cannot cut clear acrylic.
    """
    g = tube(GUIDE_RO, GUIDE_RO + 1.40, 0.0, GUIDE_T, SEG)
    rm = (GUIDE_RI + GUIDE_RO) / 2
    for k in range(B.n):
        a = 360.0/B.n * k
        cx, cy = rm*math.cos(math.radians(a)), rm*math.sin(math.radians(a))
        g += prism(rot_rect(cx, cy, GUIDE_RO - GUIDE_RI + 1.0, GUIDE_W, a),
                   0.0, GUIDE_T)
    return g


def numerals(B, z0, z1):
    """All twelve, upright, inboard of the ring. One call makes both the pockets
    in the diffuser and the solids that fill them, so they cannot drift apart.

    The face is Liberation Sans Bold, not Amazon Ember -- Ember is Amazon's own
    proprietary brand typeface and is not installable here. Point NUM_FONT_FILE
    at a .ttf if you have something closer.
    """
    out = None
    for h in range(1, 13):
        # In the DIFFUSER's own frame, looking at its face from outside (from
        # -z, because the part is installed turned over), +x reads as up and +y
        # reads as right. So the hours run 12 at +x, 3 at +y, 6 at -x, 9 at -y:
        # a = 30*h anticlockwise from +x, which is clockwise on the finished
        # clock. Once it is flipped into the base, 12 lands on the base's +x --
        # the keyhole end -- which is the top of the clock on the wall.
        a = 30.0 * (h % 12)
        cx = B.num_r * math.cos(math.radians(a))
        cy = B.num_r * math.sin(math.radians(a))
        m = text_prism(NUMERALS[h], B.num_h, (cx, cy), z0, z1, mirror=True,
                       family=NUM_FONT, weight=NUM_WEIGHT, fontfile=NUM_FONT_FILE)
        out = m if out is None else out + m
    return out


def build_collar_gauges():
    """Three short rings of the collar, at three rib heights, side by side.

    Sam has now called the collar fit too tight three times running, which says
    his printer's error on a 30 mm bore and a 30 mm boss is bigger than the
    numbers being argued over. No amount of choosing a figure here settles that
    -- only a print does. This is that print: five minutes, and whichever ring
    goes into the base's screen bore with a firm push is the number to put in
    COLLAR_RIB_H.

    Each ring is the real collar section -- same OD, same wall, same rib width,
    same lead-in -- just 8 mm of it, with its rib height in hundredths of a
    millimetre debossed on the top face.
    """
    out = None
    for i, h in enumerate(GAUGE_HS):
        cx = (i - (len(GAUGE_HS) - 1) / 2.0) * GAUGE_PITCH
        crest = R_DISP_BORE + h
        g = tube(DIFF_COLLAR_RI, COLLAR_OD, 0.0, GAUGE_H, SEG)
        # every ring gets ribs, including the 0.00 one -- there the crest is
        # exactly the bore size, which is the datum that says whether the
        # printer is running over or under before any interference is asked for
        r_in = COLLAR_OD - COLLAR_RIB_BURY
        for k in range(COLLAR_RIB_N):
            a = 360.0 / COLLAR_RIB_N * (k + 0.5)
            rm = (crest + r_in) / 2
            g += prism(rot_rect(rm*math.cos(math.radians(a)),
                                rm*math.sin(math.radians(a)),
                                crest - r_in, COLLAR_RIB_W, a), 0.0, GAUGE_H - 1.5)
        # lead-in on the end that goes into the bore, same as the real collar
        g -= (cyl(crest + 2.0, GAUGE_H - COLLAR_RIB_LEAD, GAUGE_H + 0.10, SEG)
              - cone(crest + 0.40, COLLAR_OD - 0.30,
                     GAUGE_H - COLLAR_RIB_LEAD, GAUGE_H + 0.10, SEG))
        # its number, debossed in the top face
        g -= text_prism(f'{int(round(h*100)):d}', GAUGE_NUM_H,
                        (0.0, (DIFF_COLLAR_RI + COLLAR_OD) / 2),
                        GAUGE_H - NUM_DEPTH, GAUGE_H + 0.10,
                        family=NUM_FONT, weight=NUM_WEIGHT, fontfile=NUM_FONT_FILE)
        g = g.translate([cx, 0.0, 0.0])
        out = g if out is None else out + g
    return out


def build_numerals(B):
    """The numerals as their OWN part, 0.50 mm thick, exactly filling the pockets
    debossed into the diffuser. Load the diffuser in Bambu Studio, then
    right-click -> Add part -> Load this, and assign it filament 2. Same
    coordinates, so it lands in register.

    This is a multi-shell STL by nature -- twelve numerals, and the two-digit
    ones are two shells each. That is correct, not a defect.
    """
    return numerals(B, 0.0, NUM_INLAY_T)


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

    # --- 1b. thicken HIS face too -------------------------------------------
    # Raising FACE_T only thickens the band this file rebuilds, from r=34.50
    # out. Inside that it is Sam's mesh and it stays 2.00 mm, which would leave
    # a step and a thin ring you can still see the screen's surround through.
    # Fill it out to the same FACE_T, from the window's edge to the band.
    # Radii chosen so neither wall lands ON one of his surfaces: the inner one
    # is 0.07 inside the window edge so it is buried in his face rather than
    # coincident with its bore, and the outer one stops 0.20 short of the band
    # this file adds at 34.50, so it is buried in that. Two curved surfaces at
    # the same nominal radius but different tessellations is how you get
    # NotManifold.
    # ...and 0.05 short of FACE_T at the back, so that where it overlaps the
    # band this file adds it is not ALSO landing on that band's own top plane.
    # Overlapping into a coplanar face is the one thing float32 does not survive;
    # the 0.05 step is on the hidden side of the face.
    d += tube(DIFF_BORE_RI + 0.07, BAND_FACE_RI + 0.30, 0.0, FACE_T - 0.05, SEG)

    # --- 1b2. the taller collar ----------------------------------------------
    # Added BEFORE the turn-down below, so the same cut sizes the collar and its
    # extension and they come out as one flush cylinder.
    if COLLAR_EXTEND > 0:
        d += tube(COLLAR_EXT_RI, COLLAR_EXT_RO,
                  DIFF_COLLAR_H - 1.0, DIFF_COLLAR_H + COLLAR_EXTEND, SEG)

    # --- 1c. turn the collar down -------------------------------------------
    # Sam's collar is 30.108 in a 30.19 bore: 0.164 mm on diameter, which is not
    # clearance on a printed part. At COLLAR_OD there is 0.58, and the six ribs
    # added below are the only thing that touches. Done HERE, before the ribs
    # exist -- doing it at the end took the ribs off with it.
    # Cut from just above the face, and stopping short of the band at 34.50, so
    # it can only ever see the collar.
    d -= tube(COLLAR_OD, 34.00, FACE_T + 0.001,
              DIFF_COLLAR_H + COLLAR_EXTEND + 1.0, SEG)

    # --- 2. the band, rebuilt clean -----------------------------------------
    d += tube(BAND_FACE_RI, B.diff_outer, 0.0, FACE_T, SEG)
    if B.guides:
        # A solid band, then a channel cut out of it per LED. The channel is
        # open downward, so the LED under its inner end fires straight into the
        # strip; the strip is trapped between this face above and the base's
        # guide shelf below, and needs nothing to hold it.
        d += tube(B.rib_i_ri, B.diff_outer, 0.0, B.band_top, SEG)
        ch = None
        rm = (GUIDE_CH_RI + GUIDE_CH_RO) / 2
        for k in range(B.n):
            a = 360.0/B.n * k
            cx, cy = rm*math.cos(math.radians(a)), rm*math.sin(math.radians(a))
            c = prism(rot_rect(cx, cy, GUIDE_CH_RO - GUIDE_CH_RI,
                               GUIDE_W + 2*GUIDE_CLR, a), FACE_T, B.band_top + 0.6)
            ch = c if ch is None else ch + c
        d -= ch
        # the aperture: one layer of face left, widening as it goes out
        ap = None
        for k in range(B.n):
            a = 360.0/B.n * k
            s_ = taper_slot(a, APER_RI, APER_RO, APER_W_IN, APER_W_OUT,
                            DIFF_MEM_T, FACE_T + 0.60)
            ap = s_ if ap is None else ap + s_
        d -= ap
        # relief over the LED ring itself: the band lands on the guide shelf,
        # which is outboard at r >= r_ring_o, and must not come down on the LEDs
        d -= tube(B.rib_i_ri - 1.0, B.r_ring_o, B.band_top - GUIDE_LED_CLR,
                  B.band_top + 1.0, SEG)
    if not B.guides:
        d += tube(B.rib_i_ri, B.rib_i_ro, 0.0, B.band_top, SEG)
        d += tube(B.rib_o_ri, B.diff_outer, 0.0, B.band_top, SEG)
    if not B.guides:
        rm = (B.wall_ri + B.rib_o_ri + 0.60) / 2
        ln = (B.rib_o_ri + 0.60) - B.wall_ri
        for k in range(B.n):
            a = B.wall_a0 + k * B.pitch
            cx, cy = rm * math.cos(math.radians(a)), rm * math.sin(math.radians(a))
            d += prism(rot_rect(cx, cy, ln, CELL_WALL_T, a), 0.0, B.band_top)

    # --- 2b. the outer wall grips NOTHING -----------------------------------
    # Sam: "I want the press fit to be on the inside where the screen is not the
    # outside." The eight outer crush ribs are gone; the wall drops into the ring
    # pocket with DIFF_FIT of clearance and does nothing but keep light in.
    # A chamfer at each end: one where it enters the pocket, one on the visible
    # rim so a squashed first layer cannot leave a lip standing proud.
    d -= (cyl(B.diff_outer + 2.0, B.band_top - DIFF_CHAMF, B.band_top + 0.10, SEG)
          - cone(B.diff_outer, B.diff_outer - DIFF_CHAMF,
                 B.band_top - DIFF_CHAMF, B.band_top + 0.10, SEG))
    d -= (cyl(B.diff_outer + 2.0, -0.10, DIFF_CHAMF, SEG)
          - cone(B.diff_outer - DIFF_CHAMF - 0.10, B.diff_outer, -0.10, DIFF_CHAMF, SEG))

    # --- 2c. THE PRESS FIT, on the collar, inside, where the screen is -------
    # Six crush ribs on the main collar, standing COLLAR_RIB_H proud of the
    # measured bore. Buried COLLAR_RIB_BURY into the collar rather than butted
    # onto its face -- a rib sitting exactly on the surface it grows from comes
    # away as its own shell in float32.
    r_crest = R_DISP_BORE + COLLAR_RIB_H
    r_in = COLLAR_OD - COLLAR_RIB_BURY
    for k in range(COLLAR_RIB_N):
        a = 360.0 / COLLAR_RIB_N * (k + 0.5)
        rm = (r_crest + r_in) / 2
        cx, cy = rm * math.cos(math.radians(a)), rm * math.sin(math.radians(a))
        d += prism(rot_rect(cx, cy, r_crest - r_in, COLLAR_RIB_W, a),
                   COLLAR_RIB_Z0, COLLAR_RIB_Z1)
    # The lead-in goes on the end that meets the bore first. The collar enters
    # tip first, and the tip is the HIGH z end of this part, so the taper is at
    # COLLAR_RIB_Z1 -- not at Z0, which is the trailing end.
    d -= (cyl(r_crest + 2.0, COLLAR_RIB_Z1 - COLLAR_RIB_LEAD,
              COLLAR_RIB_Z1 + 0.10, SEG)
          - cone(r_crest + 0.40, COLLAR_OD - 0.30,
                 COLLAR_RIB_Z1 - COLLAR_RIB_LEAD, COLLAR_RIB_Z1 + 0.10, SEG))
    # ^ the cone starts 0.40 OUTSIDE the crest, not on it. Starting it exactly at
    # r_crest makes its surface tangent to each rib's crest along one line, and
    # in float32 that leaves a sliver at every rib -- 6 bad edges, all at
    # r=30.29, z=6.00. Offset, it crosses the crest cleanly partway up.

    # --- 3. one radial tick per cell, thinned to a single layer --------------
    ticks = None
    for i in ([] if B.guides else range(B.n)):
        a = B.wall_a0 + (i + 0.5) * B.pitch
        cx = (B.tick_ri + B.tick_ro) / 2 * math.cos(math.radians(a))
        cy = (B.tick_ri + B.tick_ro) / 2 * math.sin(math.radians(a))
        # A 3.00 mm face would otherwise leave each dot at the bottom of a
        # 2.80 mm deep, 2.00 mm wide slot -- visible head-on and nowhere else.
        # So the hole opens out behind the membrane: 2.00 x 4.00 at the front,
        # APER_FLARE wider on every side by the time it reaches the cell.
        lo = prism(rot_rect(cx, cy, B.tick_ro - B.tick_ri, TICK_W, a, TICK_END_R),
                   DIFF_MEM_T, DIFF_MEM_T + 0.01)
        hi = prism(rot_rect(cx, cy, B.tick_ro - B.tick_ri + 2*APER_FLARE,
                            TICK_W + 2*APER_FLARE, a, TICK_END_R),
                   B.band_top + 0.59, B.band_top + 0.60)
        t = (lo + hi).hull()
        ticks = t if ticks is None else ticks + t
    if ticks is not None:
        d -= ticks

    # --- 4. all twelve hours, written on the face ---------------------------
    d -= numerals(B, -0.10, NUM_DEPTH)

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
    # up to the SHELF THIS BODY USES, not a hardcoded 17.00. On the 60-LED body
    # the diffuser is 5.35 thick rather than 4.00, so its face lands at 15.65 --
    # a fill to 17.00 collided with it by 1.35 mm, and left a shelf across the
    # wire gap at 6 o'clock as well.
    shelf = DIFF_SEAT_Z - B.band_top - DIFF_SEAT_CLR
    keep += (tube(34.60, KEEP_R32 - 0.50, 10.40, shelf, SEG) - tab_slot_keep())

    ann = tube(KEEP_R32 - 1.00, B.r_body, Z_BACK, Z_FRONT, SEG)
    ann -= tube(B.r_ring_i, B.r_ring_o, B.ring_floor, Z_FRONT + 1.0, SEG)
    # inboard of the pocket the diffuser's face sits on a shelf...
    ann -= tube(KEEP_R32 - 2.0, B.r_ring_i, shelf, Z_FRONT + 1.0, SEG)
    # ...and the plywood face still drops into a 3 mm recess at 19.00
    ann -= tube(KEEP_R32 - 2.0, B.r_lip_i, Z_RECESS, Z_FRONT + 1.0, SEG)
    if B.guides:
        # outboard of the ring the guides need their own shelf to rest on, at
        # the height of the LED tops -- so the strip's underside is level with
        # what is feeding it
        ann -= tube(B.r_ring_o, B.r_lip_i, GUIDE_SHELF, Z_FRONT + 1.0, SEG)
        ann -= hollow(B)
    return keep + ann


def hollow(B):
    """The void that keeps a 240 mm annulus from being a kilogram of PLA.

    Everything between the floor plate and whatever is above it goes, except
    the two walls either side of the ring pocket, the outer wall, four screw
    bosses and twelve radial ribs.
    """
    # Both voids stop 2.50 mm short of what sits on top of them: inboard that is
    # the shelf the diffuser's face lands on, outboard it is the shelf the light
    # guides rest on. Hollowing straight through would have left the guides
    # bridging between ribs.
    shelf_in = Z_RECESS - B.band_top + FACE_T
    inner = tube(KEEP_R32 + 1.0, B.r_ring_i - HOLLOW_WALL, HOLLOW_FLOOR,
                 shelf_in - 2.50, SEG)
    outer = tube(B.r_ring_o + HOLLOW_WALL, B.r_lip_i - HOLLOW_WALL, HOLLOW_FLOOR,
                 GUIDE_SHELF - 2.50, SEG)
    void = inner + outer
    # one circumferential rib in each cavity, so no ceiling spans more than
    # ~14 mm when the part is printed deck-face-down
    keep = (tube((KEEP_R32 + B.r_ring_i)/2 - HOLLOW_RIB_W/2,
                 (KEEP_R32 + B.r_ring_i)/2 + HOLLOW_RIB_W/2,
                 HOLLOW_FLOOR - 1.0, Z_FRONT + 1.0, SEG)
            + tube((B.r_ring_o + B.r_lip_i)/2 - HOLLOW_RIB_W/2,
                   (B.r_ring_o + B.r_lip_i)/2 + HOLLOW_RIB_W/2,
                   HOLLOW_FLOOR - 1.0, Z_FRONT + 1.0, SEG))
    for k in range(HOLLOW_RIBS):
        a = 360.0/HOLLOW_RIBS * (k + 0.5)
        rm = (KEEP_R32 + B.r_lip_i) / 2
        r = prism(rot_rect(rm*math.cos(math.radians(a)), rm*math.sin(math.radians(a)),
                           B.r_lip_i - KEEP_R32, HOLLOW_RIB_W, a),
                  HOLLOW_FLOOR - 1.0, Z_FRONT + 1.0)
        keep = keep + r
    for a in B.screw_ang:
        x, y = B.screw_r*math.cos(math.radians(a)), B.screw_r*math.sin(math.radians(a))
        keep += cyl(5.50, HOLLOW_FLOOR - 1.0, Z_FRONT + 1.0, 32, centre=(x, y))
    # ...and a vent through each shelf, so no cavity is sealed. A sealed void is
    # a second surface shell -- the topology check counts it as a second body,
    # and a slicer cannot drain it either.
    shelf_in = Z_RECESS - B.band_top + FACE_T
    vents = None
    for k in range(HOLLOW_RIBS):
        a = 360.0/HOLLOW_RIBS * k
        # two per gap, one either side of the circumferential rib -- it splits
        # each cavity in half and each half needs its own way out
        mid_i = (KEEP_R32 + B.r_ring_i)/2
        mid_o = (B.r_ring_o + B.r_lip_i)/2
        for rr, z0, z1 in ((mid_i - 7.0, shelf_in - 3.0, Z_FRONT),
                           (mid_i + 7.0, shelf_in - 3.0, Z_FRONT),
                           (mid_o - 7.0, GUIDE_SHELF - 3.0, Z_FRONT),
                           (mid_o + 7.0, GUIDE_SHELF - 3.0, Z_FRONT)):
            v = cyl(3.0, z0, z1, 24,
                    centre=(rr*math.cos(math.radians(a)), rr*math.sin(math.radians(a))))
            vents = v if vents is None else vents + v
    return (void - keep) + vents


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
        d -= box_lwh(-(B.r_ring_o - 2.0), -R_BORE + 4.0,
                     -WIRE_SLOT_HW - 0.40, WIRE_SLOT_HW + 0.40,
                     Z_DECK - 1.0, Z_BACK + 1.0)
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
        # THE WIRE GAP. Sam: "there is a gap between the LED and the middle to
        # fit the wires going to the centre from the LED rings ... update all the
        # sizes for this." On his own 108 mm base that gap is his wire slot at 6
        # o'clock, and it is open TOP TO BOTTOM from the bore right out into the
        # ring pocket -- so a lead can leave the ring at ring level and travel
        # inward without dropping first.
        #
        # The bigger bodies only had a shallow channel under the pocket floor,
        # which meant a duck-under. This is the same gap his base has: the same
        # +/-13.00 mm half width, from the bore out past the ring's inner edge,
        # and open all the way up to the shelf the diffuser's face lands on.
        shelf = DIFF_SEAT_Z - B.band_top - DIFF_SEAT_CLR
        out -= box_lwh(-(B.r_ring_o - 2.0), -R_BORE + 4.0,
                       -WIRE_SLOT_HW, WIRE_SLOT_HW, Z_DECK - 1.0, shelf)
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

    # A 240 mm clock puts its centre of mass 155 mm up. On the footprint the
    # cradle alone gives, that tips at 11 degrees -- so the big bodies get a low
    # plinth behind the stop wall, sized to bring the measured angle back over 20.
    #
    # TAIL_TARGET is a DESIGN angle, not the measured one: the real centre of
    # mass sits further back than the crude depth/2 estimate used here, so the
    # measured result lands several degrees below it. 27 was tuned when the
    # clock leaned 8 degrees. Leaning it back further moves the CoM toward the
    # heels, and at 10 degrees that same 27 produced exactly 20.0 measured on
    # the 240 mm body -- a hair under the floor. 30 restores the margin by
    # lengthening the plinth rather than by giving back the lean.
    TAIL_TARGET = 30.0
    h_com = STAND_LIFT + B.r_body*math.cos(math.radians(t))
    com_back = depth/2 * math.cos(math.radians(t))
    tail = max(0.0, com_back + h_com*math.tan(math.radians(TAIL_TARGET))
                    - (depth*math.cos(math.radians(t)) + STAND_STOP_T))

    # And a toe at the front, for tipping the other way. Tilted back and stood on
    # the desk, the stand's front-most point works out at exactly
    #     foot_front = -(h_com*tan(t) + toe/cos(t))
    # so the toe that buys a given forward margin is closed form rather than
    # tuned. On the 108 and 120 mm bodies it comes out negative -- they are
    # already stable forwards -- and those get no toe.
    toe = max(0.0, math.cos(math.radians(t)) *
              (h_com*math.tan(math.radians(STAND_TOE_TARGET))
               - h_com*math.tan(math.radians(t)) - com_back))

    prof = [( x_out, y_top), ( hw, y_top - STAND_FLARE), ( hw, Y_LOW),
            (-hw, Y_LOW), (-hw, y_top - STAND_FLARE), (-x_out, y_top)]
    s = prism(prof, -(depth + STAND_STOP_T), toe)
    if tail > 0.5:
        s += (prism(prof, -(depth + STAND_STOP_T + tail), -(depth + STAND_STOP_T))
              - box_lwh(-hw - 1, hw + 1, -(B.r_body + 6.0), 1.0,
                        -(depth + STAND_STOP_T + tail) - 1.0, -(depth + STAND_STOP_T) + 0.001))
    s -= cyl(R, -depth - 0.001, toe + 5.0, SEG)                 # the cradle
    s -= cyl(STAND_STOP_RI, -(depth + STAND_STOP_T) - 1.0, -depth, SEG)  # stop wall
    # An arch through it, front to back. It halves the filament, it is the
    # cable route, and its ceiling is a cylinder concentric with the cradle --
    # convex downward, so it needs no support.
    crown = -(R + STAND_SHELL)
    arch = [(-STAND_ARCH_HW, Y_LOW), (STAND_ARCH_HW, Y_LOW),
            (STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0)),
            (10.0, crown), (-10.0, crown),
            (-STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0))]
    s -= prism(arch, -(depth + STAND_STOP_T) - 1.0, toe + 5.0)
    # its roof has to clear the stop wall's inner circle, or a shallow shelf is
    # left across it at the back
    s -= box_lwh(-STAND_NOTCH_HW, STAND_NOTCH_HW, Y_LOW - 1.0, -(STAND_STOP_RI - 6.0),
                 -(depth + STAND_STOP_T) - 1.0, -(depth - STAND_NOTCH_BACK))

    # tilt it back and stand it on the desk
    h0 = STAND_LIFT + B.r_body * math.cos(math.radians(t))
    s = s.rotate([90.0 - t, 0.0, 0.0]).translate([0.0, 0.0, h0])
    s = s ^ box_lwh(-200, 200, -200, 200, 0.0, 400.0)
    # --- a real flat foot.
    # Trimming a tilted solid with the desk plane leaves a knife edge wherever a
    # face happens to meet that plane at a shallow angle. Replace everything
    # below STAND_FOOT with a straight extrusion of the section at STAND_FOOT,
    # so every edge on the footprint is vertical and has full thickness.
    # Done as ONE subtraction rather than cut-and-re-union: butting a separately
    # built foot onto the body at z = STAND_FOOT leaves two coincident faces,
    # and in float32 those come apart into two shells.
    # The section is pulled in STAND_FOOT_OFF first. Extruded at its exact size
    # its wall would be tangent to the stand's own surface all along z =
    # STAND_FOOT, and a boolean against a tangency is what NotManifold means.
    # Shrunk, the wall is strictly inside the solid it is cutting.
    sec = s.slice(STAND_FOOT).offset(-STAND_FOOT_OFF, JoinType.Miter, 2.0)
    keep = Manifold.extrude(sec, STAND_FOOT + 1.0).translate([0.0, 0.0, -1.0])
    return s - (box_lwh(-200, 200, -200, 200, -1.0, STAND_FOOT) - keep)


# =============================================================================
if __name__ == '__main__':
    print(summary())
    print('building...')
    sam = load_sams_base()
    parts = []
    for B in (BODY24, BODY32, BODY60):
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
            (build_numerals(B),              f'mini-round-clock-numerals{tg}',  False),
        ]
    # The battery shelves only mean anything if a battery fits, and at
    # HOUSING_DEEP = 25.00 one does not. Emitting the part anyway would put a
    # file in the folder that cannot be used, so it is skipped and said out loud.
    if HOUSING_DEEP >= BATTERY_MIN_HOUSING:
        parts.append((build_shelf(BAT_W), 'mini-round-clock-battery-shelf-x2', True))
    else:
        print(f'  battery shelves SKIPPED: a {BAT_T:.2f} mm cell needs a '
              f'{BATTERY_MIN_HOUSING:.2f} mm housing and this one is '
              f'{HOUSING_DEEP:.2f}. No internal battery in this build.')
    parts.append((build_light_guides(BODY60), 'mini-round-clock-light-guides-60', True))
    parts.append((build_collar_gauges(), 'mini-round-clock-collar-gauges', False))
    for man, fn, strict in parts:
        t = csg.finalise(man, fn, strict=strict)
        t.export(fn + '.stl')
        t.export(fn + '.3mf')
    print('done')
