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
    # DOWN TO Z_DECK, not Z_BACK. The walls used to start on top of the deck, so
    # any deck opening wider than the slot undercut them -- and the cable gap
    # Sam asked for is exactly that. Taking them to the part's own bottom plane
    # means they carry themselves: the deck can be opened to the full slot width
    # between them, the walls stand on the build plate rather than on a plate
    # with a hole in it, and there is no coincident face where the two meet.
    solid = wedge(TAB_WALL_RI, TAB_WALL_RO, Z_DECK, TAB_WALL_TOP,
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
                   1.6 mm EDGE, never a face -- so pads, solder fillets and
                   header strips are all irrelevant to them. They are a GUIDE,
                   not a fit: 0.40 mm a side, sized so the worst printed slot
                   still clears the widest board it claims to take.
      end wall     at the antenna end. Takes the USB plug's insertion load,
                   which is the only real force this thing ever sees.
      snap fingers two, at the connector end, clamping the board down onto its
                   posts. Their lips land in the clear strips at |y| 10.54 to
                   12.70, over the last 7.15 mm of board that carries neither
                   the USB shells nor the pad rows -- so they work with or
                   without headers soldered on. The lip's inner face is an
                   absolute |y|, because what limits it is the USB-C shell at
                   |y| = 10.81, not the board's edge.
      posts        three pairs, at |y| = 6.50: between the USB shells' end tabs
                   at the connector end, mid-board, and under the antenna end.

      clamp        a separate bar, screwed down over the antenna end. v9
                   argued that a board held at one end cannot lift at the
                   other; that was wrong -- the lips have BRD_LIP_CLR of slack
                   over a 4.00 mm base, and on a 63 mm board that is a 15:1
                   lever and 3.1 mm of lift. v13 answered it with a moulded
                   hood and got it wrong twice. A screwed bar goes on AFTER the
                   board, so it overhangs nothing, needs no assembly move, and
                   does not care how long the board is.

    WHY v9 DID NOT FIT, which is the actual repair here. The rails were drawn
    0.10 mm a side clear of the board and the end wall 0.30 mm clear of its
    end. Both read as clearances and neither is one: an FDM slot comes off the
    plate up to FDM_SLOT_UNDER narrower than drawn, so a 25.60 slot prints
    25.20 to 25.50 around a 25.40 board, and the board is WIDER than the hole
    it has to enter. It is the collar mistake again -- a nominal clearance that
    the printer eats -- so the cure is the collar's cure: size it off the worst
    printed case, and let check2 assert that rather than trusting the drawing.

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

    # --- the antenna end is SCREWED down, not hooded.
    # Sam: "add a way to screw it down to fasten it." Two bosses, both of them
    # beyond the longest board this bay takes, carrying a separate bar that
    # presses the board's last few millimetres between the pad rows. The bar
    # goes on after the board, so nothing here overhangs, nothing has to be slid
    # under anything, and the length of the board stops mattering -- which is
    # what killed the moulded hood twice over.
    CW, CS = BRD_CLAMP_W, BRD_CLAMP_SEAT
    for sy in (1, -1):
        add(cyl(BRD_CLAMP_BOSS/2, z0, z0 + CS, 32,
                centre=(BRD_CLAMP_SX, sy*BRD_CLAMP_SY)))
    # the bar has to sit flat on those, so nothing in its footprint may stand
    # proud of the seat: the end wall gets cut down to it across the bar's width
    s = s - box_lwh(BRD_X0 + BRD_CLAMP_PAD0 - 2.0, BRD_CLAMP_SX + 8.0,
                    -CW - 0.20, CW + 0.20, z0 + CS, z_top + 2.0)

    # --- snap fingers
    for sy in (1, -1):
        y_in, y_out = sy*RY, sy*(RY + BRD_FING_T)
        add(box_lwh(x_tip, x_root, *sorted((y_in, y_out)), z0, z_top))
        # The lip, and its lead-in ramp, as the hull of two thin slices: at the
        # bottom it reaches BRD_FING_OVER over the board, at the top it is back
        # flush with the rail, so pressing the board down wedges the finger out.
        # Built buried BRD_FING_BURY into the finger rather than butted against
        # its face -- a coincident face here does not survive float32.
        y_lip = sy*BRD_FING_YI          # absolute: set by the USB shell, not the edge
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
        add(box_lwh(-RI + 0.5, BRD_X0,
                    *sorted((sy*BRD_STOP_RI, sy*(RY + RT))), z0, z_lip))

    # --- posts under it
    # the far pair sits directly under the hood's low edge, so the hood
    # presses the board onto a post rather than onto a span of nothing
    for px in (BRD_X0 + 3.0, (BRD_X0 + BRD_X1)/2, BRD_X0 + BRD_CLAMP_PAD0 + 1.5):
        for py in (BRD_POST_HY, -BRD_POST_HY):
            add(cyl(BRD_POST_D/2, z0, zt, 32, centre=(px, py)))

    # --- the window the board's own connector looks out through
    win = box_lwh(-RB - 2.0, -RI + 2.0, -USB_WIN_W/2, USB_WIN_W/2,
                  z0 + USB_WIN_Z, z0 + USB_WIN_Z + USB_WIN_H)
    for sy in (1, -1):
        win += cyl(SCREW_PILOT/2, z0 + CS - BRD_CLAMP_DEEP, z0 + CS + 0.10, 24,
                   centre=(BRD_CLAMP_SX, sy*BRD_CLAMP_SY))
    return s, win


def build_rear_housing(pocket_d, r_body=None, r_inner=None, with_board=True,
                       vent_ang=None, screw_ang=None, screw_r=None, plate_t=None):
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
    PT = PLATE_T if plate_t is None else plate_t
    Z1 = Z_DECK                              # -2.40, mates to the base's deck
    Z0 = Z1 - (PT + pocket_d)                # rear face, against the wall
    Z_POCKET = Z0 + PT                       # floor of the pocket

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
             + cyl(SCREW_HEAD/2, Z0 - 1.0, Z0 + min(3.20, PT - 0.60), 40, centre=(x, y)))
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
def numeral_box(num_h):
    """Half-extents of the widest numeral, in the frame the dial places it in.

    THE NUMERALS ARE UPRIGHT. They are not rotated to face outward -- a clock
    face reads upright, which is what Sam asked for and what the Echo does --
    and that is exactly why a band computed as num_r +/- num_h/2 is wrong. An
    upright glyph at 10 o'clock has its CORNER pointing at the middle of the
    dial, not its edge, and the corner reaches further in than the edge does.

    Returns (hx, hy): hx is the half-extent along the model's x, hy along y.
    text_prism places these with mirror=True, which swaps the glyph's own axes,
    so the glyph's HEIGHT lands on x and its WIDTH on y.
    """
    from csg import text_polys
    import numpy as _np
    w = 0.0
    for t in NUMERALS.values():
        pts = _np.concatenate(text_polys(t, num_h, family=NUM_FONT,
                                         weight=NUM_WEIGHT, fontfile=NUM_FONT_FILE))
        w = max(w, pts[:, 0].max() - pts[:, 0].min())
    return num_h / 2.0, w / 2.0


def numeral_reach(num_r, num_h):
    """The true innermost and outermost radius the twelve numerals reach.

    The box is axis-aligned (upright) and centred at radius num_r, so how close
    it comes to the middle depends on WHERE on the dial it sits. Straight up at
    12 the inner edge is the closest point; at 10 it is a corner, and that is
    0.5-1.5 mm further in on a small dial. This measures all twelve.
    """
    hx, hy = numeral_box(num_h)
    lo, hi = 1e9, 0.0
    for h in range(1, 13):
        a = math.radians(30.0 * (h % 12))
        cx, cy = abs(num_r * math.cos(a)), abs(num_r * math.sin(a))
        dx, dy = max(0.0, cx - hx), max(0.0, cy - hy)
        lo = min(lo, math.hypot(dx, dy))
        hi = max(hi, math.hypot(cx + hx, cy + hy))
    return lo, hi


def numeral_r_for_inner(limit, num_h):
    """The smallest num_r whose innermost numeral corner still clears `limit`.

    Bisected rather than solved: the closest point can be an edge or a corner
    depending on the angle, so the expression changes form partway and a closed
    solution would have to case-split on something that is cheaper to search.
    numeral_reach's inner value rises monotonically with num_r, which is all a
    bisection needs.
    """
    lo, hi = limit, limit + 60.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if numeral_reach(mid, num_h)[0] < limit:
            lo = mid
        else:
            hi = mid
    return hi


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
        # The tick is as long as this body's own cell allows, centred on the
        # LED, leaving TICK_CELL_MARGIN of rib standing at each end. Set after
        # the ribs below, because it depends on them -- see the note further
        # down where it is actually computed.
        # the hours keep their exact offsets inboard of the ticks
        # Set below, once the tick is known -- the marks sit inboard of it.
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
            self.tick_bound = 'the light guides'
        elif n == CELL_N:
            self.rib_i_ri, self.rib_i_ro = RIB_I_RI, RIB_I_RO
            self.wall_ri = CELL_WALL_RI
        else:
            self.rib_i_ri, self.rib_i_ro = r_ring_i + 0.15, r_ring_i + 1.35
            self.wall_ri = self.rib_i_ri + 0.40
        # --- the tick, as long as THIS body's cell allows -------------------
        # Sam: "there is more of a line for the LEDs to shine through."
        # Centred on the LED and stopping TICK_CELL_MARGIN short of the ribs at
        # each end, so it is the longest mark this body can carry without
        # cutting the walls that stop light leaking between LEDs. The tighter
        # side binds, because the tick stays centred.
        if not guides:
            # ONE aperture length on every flat body: APER_L, the 5050 die.
            # Sam: "make sure each of the plain diffusers have the same size
            # LED hole ... they are not even at the moment." They were not,
            # because each body used to take the longest tick it could carry
            # and the two are bound by different things. Now the mark is fixed
            # and the FACE gives way to it, in this order:
            #
            #   1. the cell has to physically hold it, leaving
            #      TICK_CELL_MARGIN of rib standing at each end. This is an
            #      assert, not a min(): a body too small for a 5 mm mark is a
            #      body this rule does not fit, and it should say so rather
            #      than quietly go back to per-body lengths.
            #   2. it stays CENTRED ON THE LED. Centring it on the cell instead
            #      buys 0.10 mm of rib on the 32's tight side and costs the one
            #      thing the mark is for: check4 asserts the tick is centred on
            #      the emitter, and it is right to -- a 5.00 mm slot over a 5.00
            #      mm die is only exactly as long as the lit thing if the two
            #      share a centre. The tenth is not worth it; 0.40 of standing
            #      rib is enough, and the assert below proves it on both sides
            #      separately rather than on the span.
            #   3. the numerals are then solved DOWN from their nominal height
            #      until they clear it -- see below.
            half = APER_L / 2.0
            room_i = self.led_r - half - self.rib_i_ro
            room_o = self.rib_o_ri - (self.led_r + half)
            assert min(room_i, room_o) >= TICK_CELL_MARGIN - 1e-9, (
                f'{tag or "24"}: a {APER_L:.2f} mm mark centred on the LED leaves '
                f'{room_i:.2f} / {room_o:.2f} mm of rib, and the floor is '
                f'{TICK_CELL_MARGIN:.2f}')
            self.tick_ri = self.led_r - half
            self.tick_ro = self.led_r + half
            self.tick_bound = 'the 5050 die'
            # THE NUMERALS GIVE WAY, not the mark. Each is placed as far in as
            # the screen window allows (numeral_r_for_inner), and if its outer
            # corner still reaches within NUM_MARGIN of the tick, it is set
            # smaller and placed again. Bisected on height: both reaches are
            # monotonic in it. NUM_H_MIN is where a stem stops being two clean
            # beads, and it is an assert rather than a clamp -- a face that
            # cannot carry legible numerals under a 5 mm mark is a fact to
            # report, not to round away.
            limit = self.tick_ri - NUM_MARGIN
            def _fits(h):
                r = numeral_r_for_inner(DIFF_BORE_RI + NUM_BORE_CLR, h)
                return numeral_reach(r, h)[1] <= limit, r
            ok, r = _fits(self.num_h)
            if not ok:
                lo_h, hi_h = NUM_H_MIN, self.num_h
                assert _fits(lo_h)[0], (
                    f'{tag or "24"}: even {NUM_H_MIN:.2f} mm numerals reach the '
                    f'aperture; the face cannot carry a {APER_L:.2f} mm mark')
                for _ in range(40):
                    m = (lo_h + hi_h) / 2.0
                    if _fits(m)[0]: lo_h = m
                    else:           hi_h = m
                self.num_h = round(lo_h, 3)
                r = _fits(self.num_h)[1]
            self.num_r = r
            # the minute marks fall in behind the tick, as before
            self.mark_ro_maj = self.tick_ri - TICK_MARK_GAP
            self.mark_ro     = self.mark_ro_maj - MARK_MAJ_EXT
            self.mark_ri     = self.mark_ro - MARK_LEN
            self.mark_ri_maj = self.mark_ri - MARK_MAJ_EXT
            self.num_fixed   = True

        # --- where the numerals go, on every body, by one rule
        # Their OUTER edge sits NUM_MARGIN inboard of the aperture's inner edge,
        # so they read as a ring of hours just inside the dots -- the Echo's
        # layout -- and they can never break into a 0.20 mm aperture membrane.
        # Inboard of the MARKS, not of the tick -- the marks are now the
        # innermost thing on the dial and the numerals have to clear them.
        # On a guide body the numerals were never solved above, so place them
        # the old way and then push them in far enough that no CORNER breaks the
        # window -- the 60 has 30 mm of slack there, but the rule is the rule.
        if not getattr(self, 'num_fixed', False):
            self.num_r = self.mark_ri_maj - NUM_MARGIN - self.num_h / 2
            self.num_r = max(self.num_r,
                             numeral_r_for_inner(DIFF_BORE_RI + NUM_BORE_CLR,
                                                 self.num_h))
        self.num_reach = numeral_reach(self.num_r, self.num_h)

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


def build_board_clamp():
    """The bar that screws the S3 down. Prints flat, top face on the plate.

    Sam: "add a way to screw it down to fasten it."

    It presses the last few millimetres of the board BETWEEN the pad rows, at
    |y| <= BRD_CLAMP_Y, and both screws land BEYOND the board's end -- so no
    part of it crosses a pad row at any height, and headers can be fitted
    either way up or left off entirely.

    Its underside has three planes:
      seat   BRD_CLAMP_T from the top face. Rests on the two bosses and on the
             end wall, both cut to BRD_CLAMP_SEAT.
      pad    0.10 shallower, over the board. The board's top face is 0.10 mm
             ABOVE the seat, so tightening the screws lands the bar on the
             BOARD rather than bottoming it on its own bosses -- a real clamp.
             0.10 mm of flex in a 3.00 mm bar is a few newtons; it cannot crack
             FR4, and it takes up any board thickness from 1.50 to 1.70.
      relief BRD_CLAMP_RLF shallower, everywhere short of the pad, so the bar
             cannot come down on the WROOM module however far back it ends.

    Printed TOP FACE DOWN. That way the first layer is the full outline and the
    three planes are all pockets opening upward: no overhang, no support, and
    nothing that needs a brim.
    """
    X0 = BRD_X0 + BRD_CLAMP_PAD0 - 1.50
    X1 = BRD_CLAMP_SX + BRD_CLAMP_BOSS/2 + 1.50
    W, T = BRD_CLAMP_W, BRD_CLAMP_T
    g = box_lwh(X0, X1, -W, W, 0.0, T)
    # relief, everywhere before the pad starts
    g -= box_lwh(X0 - 1.0, BRD_X0 + BRD_CLAMP_PAD0, -W - 1.0, W + 1.0,
                 T - BRD_CLAMP_RLF, T + 1.0)
    # the pad, 0.10 shallower than the seat, out to the longest board it takes
    g -= box_lwh(BRD_X0 + BRD_CLAMP_PAD0, BRD_X0 + BOARD_L_MAX, -W - 1.0, W + 1.0,
                 T - 0.10, T + 1.0)
    for sy in (1, -1):
        g -= cyl(SCREW_CLEAR/2, -0.10, T + 0.10, 32,
                 centre=(BRD_CLAMP_SX, sy*BRD_CLAMP_SY))
    # which way up, debossed where it cannot be lost
    g -= text_prism('THIS SIDE UP', 3.20, ((X0 + X1)/2, 0.0), -0.10, 0.50,
                    family=NUM_FONT, weight=NUM_WEIGHT, fontfile=NUM_FONT_FILE)
    return g.translate([-(X0 + X1)/2, 0.0, 0.0])


def build_board_fit_gauge():
    """Does SAM'S board fit? Four channels, 0.40 mm apart, and he tells us which.

    Sam, 2026-09-03: "before going ahead, give me some test prints to make sure
    it will fit the ESP32. The width of the board is 32mm, and the length is
    64mm."

    32.00 is 3.81 mm wider than the board every mount in this file was derived
    from, and the stand-box's tray was built for that narrower one: its rails
    stand at |x| 13.10 and a 32 mm board is 16.00 to the edge. So the tray as
    shipped does not take his board, and no amount of arithmetic here settles
    what does -- a printed slot is not its nominal width, and this printer's
    number for that is unknown. Hence four slots rather than one guess. It is
    the same method as the collar gauge, which is the one thing in this project
    that ended a run of wrong fits.

    Each channel is BOARD2_GAUGE_LEN long -- a SECTION, not the whole 64 -- so
    the print is minutes, and the board is checked on width, which is the axis
    that has gone wrong. The number beside each channel is the slot's nominal
    width in millimetres. The rails are the stand-box's own height, so a board
    that sits down between them here sits down between them there.

    Read it: drop the board in each, from 32.40 upward. The one it enters
    without force, and cannot rattle sideways in, is the answer. Tell me that
    number.
    """
    T   = 3.00                      # base plate
    RH  = STANDBOX_RAIL_H           # rail height, as the tray's
    RT  = STANDBOX_RAIL_T           # rail thickness, as the tray's
    LN  = BOARD2_GAUGE_LEN
    PAD = 8.00                      # bare plate at the labelled end
    gap = 6.00                      # between channels, for the numbers
    xs, x = [], 0.0
    for w in BOARD2_GAUGE_SLOTS:
        xs.append((x, w))
        x += w + 2*RT + gap
    W_total = x - gap
    g = box_lwh(-4.0, W_total + 4.0, -PAD, LN + 4.0, 0.0, T)
    for x0, w in xs:
        # two rails making a slot w wide, open at the top and at both ends --
        # an open channel, because his board has wires standing off the top of
        # it and nothing may close over them
        g += box_lwh(x0, x0 + RT, 0.0, LN, T - 0.01, T + RH)
        g += box_lwh(x0 + RT + w, x0 + 2*RT + w, 0.0, LN, T - 0.01, T + RH)
        # the number, debossed in the plate below the channel
        g -= text_prism(f'{w:.1f}', 5.0, (x0 + RT + w/2, -PAD/2 - 0.5),
                        T - 0.60, T + 0.10)
    return g


def build_board_gauge():
    """The S3 frame on its own, so the fit can be settled before 69 g of housing.

    Sam has now had a mount that "doesn't fit at all", and the numbers the
    sellers publish for a board called "ESP32-S3-DevKitC-1 N16R8" disagree with
    each other by more than a centimetre. Espressif's own v1.1 dimension
    drawing says 62.865 x 25.400 x 1.60 and this frame is built around that,
    with room either side -- but no figure argued here settles what is in Sam's
    hand. A print does.

    So: exactly the geometry board_mount() puts in the housing, on a 3 mm plate
    instead of inside a clock. Same rails, same snap fingers, same corner
    stops, same hood, same posts. About 12 g and twenty minutes. If the board
    clicks into this, it clicks into the housing; if it does not, the plate
    carries a scale off the connector end so the length can be read straight
    off it, and BOARD_L is the one number to change.
    """
    RY, RT = BRD_RAIL_Y, BRD_RAIL_T
    x_end  = BRD_X1 + BRD_END_CLR
    x0, x1 = BRD_X0 - 7.0, x_end + RT + 2.0
    y1     = RY + RT + 7.0    # wide enough that the label is on bare plate
    t      = 2.5
    # +0.02, not 0.0: the frame's own base plane is z = 0, and two coplanar
    # faces meeting across a union is what float32 turns into a bad edge. Two
    # hundredths of a millimetre of burial costs nothing and settles it.
    plate  = box_lwh(x0, x1, -y1, y1, -t, 0.02)
    # board_mount starts its corner stops at -RI + 0.5, meaning to bury them in
    # the housing's pocket wall. Here RI is chosen so they start 1.00 mm inside
    # this plate's own end instead -- buried, not butted.
    frame, void = board_mount(0.0, RB=60.0, RI=55.0)
    frame -= void            # so the gauge carries the clamp's pilot holes too
    # board_mount hangs its corner stops off the housing's pocket wall; here
    # there is no wall, so they are backed by a rib of the plate's own instead
    frame += box_lwh(BRD_X0 - 4.0, BRD_X0, -y1, y1, 0.0, BRD_LIP_Z0)
    g = plate + frame
    # a scale along the plate's edge: a notch every 5 mm from the connector
    # end, and a deeper one at each end of the range the frame claims to take
    for d in range(5, int(BOARD_L_MAX) + 1, 5):
        g -= box_lwh(BRD_X0 + d - 0.25, BRD_X0 + d + 0.25,
                     -y1 - 1.0, -y1 + 2.0, -0.60, 0.10)
    for d in (BOARD_L_MIN, BOARD_L, BOARD_L_MAX):
        g -= box_lwh(BRD_X0 + d - 0.35, BRD_X0 + d + 0.35,
                     -y1 - 1.0, -y1 + 4.5, -0.60, 0.10)
    # and the two numbers that matter, debossed where they cannot be lost
    g -= text_prism(f'{BOARD_L:.1f}x{BOARD_W:.1f}', 4.0,
                    ((BRD_X0 + x_end)/2, y1 - 3.5), -0.60, 0.10,
                    family=NUM_FONT, weight=NUM_WEIGHT, fontfile=NUM_FONT_FILE)
    return g.translate([-(x0 + x1)/2, 0.0, t])


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
def build_diffuser(B, bar=False, numerals_on=True, flange=False):
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
    elif COLLAR_EXTEND < 0:
        # v17: the collar is now SHORTER than Sam's own, so there is nothing to
        # extend -- it has to be TRIMMED. Missing this is what let the built
        # part sit 0.87 mm longer than params said: the branch above simply did
        # nothing when COLLAR_EXTEND went negative, so his 8.20 collar survived
        # untouched while every derived number claimed 4.43. check2 caught it by
        # measuring the built mesh rather than recomputing from params, which is
        # the entire reason it does that.
        # cyl, NOT tube(0.0, ...): a tube with a zero inner radius comes back
        # as an EMPTY solid, so the first version of this subtracted nothing at
        # all and the trim silently did not happen.
        d -= cyl(COLLAR_EXT_RO + 2.0, FACE_T + COLLAR_LEN,
                 DIFF_COLLAR_H + 2.0, SEG)

    # --- 1c. turn the collar down -------------------------------------------
    # Sam's collar is 30.108 in a 30.19 bore: 0.164 mm on diameter, which is not
    # clearance on a printed part. At COLLAR_OD there is 0.58, and the six ribs
    # added below are the only thing that touches. Done HERE, before the ribs
    # exist -- doing it at the end took the ribs off with it.
    # Cut from just above the face, and stopping short of the band at 34.50, so
    # it can only ever see the collar.
    d -= tube(COLLAR_OD, 34.00, FACE_T + 0.001,
              max(DIFF_COLLAR_H, FACE_T + COLLAR_LEN) + 1.0, SEG)

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
    # COLLAR_RIB_N crush ribs on the main collar, standing COLLAR_RIB_H proud of
    # measured bore. Buried COLLAR_RIB_BURY into the collar rather than butted
    # onto its face -- a rib sitting exactly on the surface it grows from comes
    # away as its own shell in float32.
    r_crest = R_DISP_BORE + COLLAR_RIB_H
    r_in = COLLAR_OD - COLLAR_RIB_BURY
    # On a -bar base the bore wall is missing over two 57 deg ears at +/-x,
    # where the module overhangs it. Measured on the built part, the standard
    # six ribs put 30 deg and 330 deg straight into the +x ear -- 4% of each rib
    # had anything to bite on -- which leaves the grip entirely on the -x side
    # and shoves the collar sideways. Four ribs on the diagonals clear both ears
    # by 31 deg and are symmetric about both axes, which is what a press fit
    # needs. Same interference, same rib width, same lead-in: only the count and
    # the phase change.
    ribs = COLLAR_RIB_BAR_N if bar else COLLAR_RIB_N
    phase = COLLAR_RIB_BAR_PHASE if bar else 0.5
    for k in range(ribs):
        a = 360.0 / ribs * (k + phase)
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
    # ...unless this is the plain one. Sam: "a diffuser that doesn't have
    # numbers on it." Same part in every other respect, so the numerals inlay
    # simply has nowhere to go and is not emitted for it.
    if numerals_on:
        d -= numerals(B, -0.10, NUM_DEPTH)

    # --- 5. the flange, out to the base's lip --------------------------------
    # The face's front plane carries on outward, over the trough between the
    # band and the lip, as one disc: an annulus from 1.00 mm inside the band's
    # outer wall (buried in it) to DIFF_FLANGE_CLR short of the lip, from the
    # face plane back to DIFF_FLANGE_D -- which is neither FACE_T nor the
    # FACE_T - 0.05 of the inner fill, so its back lands on no other plane.
    # Its front IS the face plane, the way every other tube on this face is,
    # so face down it prints as the same first layer. It fills the front
    # chamfer 2b cut at the band's edge, and gets its own on the new outer
    # edge. The membrane over the LEDs is untouched: the flange starts
    # outboard of the band's outer wall.
    if flange:
        ro = B.r_lip_i - DIFF_FLANGE_CLR
        assert ro - B.diff_outer >= DIFF_FLANGE_MIN, (
            f'{B.n}-LED: the diffuser already reaches the lip; no flange to add')
        d += tube(B.diff_outer - 1.00, ro, 0.0, DIFF_FLANGE_D, SEG)
        d -= (cyl(ro + 2.0, -0.10, DIFF_FLANGE_CHAMF, SEG)
              - cone(ro - DIFF_FLANGE_CHAMF - 0.10, ro, -0.10, DIFF_FLANGE_CHAMF, SEG))

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

    # Z_DECK, not Z_BACK. The big bodies used to sit their annulus on top of a
    # full-width deck, which meant two stacked floor plates. The annulus now
    # reaches the bottom plane itself and carries the only floor -- see the
    # DECK_RO_BIG note in params, and the 69 mm bridge that the first version
    # of this change produced.
    ann = tube(KEEP_R32 - 1.00, B.r_body, Z_DECK, Z_FRONT, SEG)
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
    # The floor is HOLLOW_FLOOR thick measured from the part's own bottom plane,
    # which is Z_DECK now, not Z_BACK. Leaving this as an absolute would have
    # given a 4.40 mm floor -- the thing this change exists to stop.
    z_floor = Z_DECK + HOLLOW_FLOOR
    inner = tube(KEEP_R32 + 1.0, B.r_ring_i - HOLLOW_WALL, z_floor,
                 shelf_in - 2.50, SEG)
    outer = tube(B.r_ring_o + HOLLOW_WALL, B.r_lip_i - HOLLOW_WALL, z_floor,
                 GUIDE_SHELF - 2.50, SEG)
    void = inner + outer
    # one circumferential rib in each cavity, so no ceiling spans more than
    # ~14 mm when the part is printed deck-face-down
    keep = (tube((KEEP_R32 + B.r_ring_i)/2 - HOLLOW_RIB_W/2,
                 (KEEP_R32 + B.r_ring_i)/2 + HOLLOW_RIB_W/2,
                 z_floor - 1.0, Z_FRONT + 1.0, SEG)
            + tube((B.r_ring_o + B.r_lip_i)/2 - HOLLOW_RIB_W/2,
                   (B.r_ring_o + B.r_lip_i)/2 + HOLLOW_RIB_W/2,
                   z_floor - 1.0, Z_FRONT + 1.0, SEG))
    for k in range(HOLLOW_RIBS):
        a = 360.0/HOLLOW_RIBS * (k + 0.5)
        rm = (KEEP_R32 + B.r_lip_i) / 2
        r = prism(rot_rect(rm*math.cos(math.radians(a)), rm*math.sin(math.radians(a)),
                           B.r_lip_i - KEEP_R32, HOLLOW_RIB_W, a),
                  z_floor - 1.0, Z_FRONT + 1.0)
        keep = keep + r
    for a in B.screw_ang:
        x, y = B.screw_r*math.cos(math.radians(a)), B.screw_r*math.sin(math.radians(a))
        keep += cyl(5.50, z_floor - 1.0, Z_FRONT + 1.0, 32, centre=(x, y))
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
    # OUTER RADIUS DEPENDS ON THE BODY. On the 24 the deck is the only thing
    # closing the back, so it runs the full annulus. On the 32 and 60 the base
    # is rebuilt outboard of KEEP_R32 and brings its own floor, so out there the
    # deck was a second plate stacked on the first -- 93 cm^3 of pure double-up
    # on the 60. See DECK_RO_BIG in params for why that is the cut worth making.
    ro = (B.r_body - DECK_INSET) if B.n == 24 else DECK_RO_BIG
    d = tube(B.deck_ri, ro, Z_DECK, Z_BACK, SEG)
    # THE CABLE GAP. Sam: "the gap at the bottom... doesn't allow for the
    # cables. Make the gap at the bottom gap wider to fit the cables that come
    # down under the ESP 32." Was +/-10.00; now +/-20.00.
    #
    # The old comment here said cutting it wider left the tab-slot walls
    # standing over a void. That was true when it was cut across the walls'
    # whole radial run -- so it is not cut there any more. The walls stand at
    # r 31.00..43.50, and this opening now stops at TAB_CABLE_RO, short of them,
    # leaving a continuous land under every part of the wall that touches the
    # deck. check3's island sweep is what proves it rather than this comment.
    # ...but NOT as one rectangle, because 40 mm undercuts the tab-slot walls.
    # They stand at r 31.00..43.50 and |y| >= 15.575, and cutting +/-20 through
    # that band leaves them standing on nothing over |y| 15.575..20.00. The
    # assembled part then reads 6 mm^3 of SELF-OVERLAP -- trimesh 104126.04
    # against manifold3d 104120.01 -- which is the coincident-face signature,
    # and those walls are the whole reason the display stopped tilting.
    #
    # THE ACTUAL PINCH, which is what Sam is feeling: the slot the tab passes
    # through is 31.15 mm wide, and the hole in the deck under it was 20.00.
    # The deck was NARROWER than the slot above it, so the ribbon met a step on
    # its way out. That is the thing to fix, and it is free.
    #
    # So the opening is stepped, and it is as wide as it can be at every radius:
    #   r 30.0..31.0   40.00 mm   (inboard of the walls -- mostly bore anyway)
    #   r 31.0..44.0   32.35 mm   through the wall band: the full slot width,
    #                             so nothing is pinched and every wall keeps a
    #                             continuous land under it
    #   r 44.0..44.5   40.00 mm   (outboard of the walls)
    # ONE stepped prism, not three butted boxes. Three boxes meeting on shared
    # planes at x0 and x1 is exactly the coincident-face case this file keeps
    # relearning: it built, and then finalise() could not get a clean float32
    # mesh out of it in six rounds -- watertight=False, one bad edge. Extruding
    # a single closed outline has no internal faces to disagree about.
    hw   = DECK_CABLE_W / 2
    slot = TAB_SLOT_HW + 0.60             # 0.60 clear of the slot the tab uses,
                                          # which the walls now carry themselves
    x0, x1 = TAB_WALL_RI - 0.50, TAB_WALL_RO + 0.50
    outline = [(20.0, hw), (x0, hw), (x0, slot), (x1, slot), (x1, hw),
               (TAB_CABLE_RO, hw), (TAB_CABLE_RO, -hw), (x1, -hw),
               (x1, -slot), (x0, -slot), (x0, -hw), (20.0, -hw)]
    d -= prism(outline, Z_DECK - 1.0, Z_BACK + 1.0)
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


def bar_pocket():
    """The cut that lets the 1.9" bar module take the round one's place.

    Measured before it was designed: the module's whole swept volume, from its
    seat to the front recess, clashes with only 193.9 mm3 of the built base.
    That is because the two places it overhangs the round bore are the two
    places the base is ALREADY open -- the display-tab slot at 12 o'clock and
    the wire slot at 6 o'clock. The module pokes past r 30.19 only in two ears
    at +/-x, 4.52 mm deep and 29 mm wide, and those slots have between them
    already taken out all but a fifth of both.

    So this is not a redesigned middle. It is a rectangular relief cut through
    what little is left, plus the 1.10 mm the seat has to drop.

    Nothing else moves. Z_SEAT_BAR is derived so the module's FRONT FACE lands
    exactly where the round module's does, which means the diffuser, its collar,
    the land at 19.03 and the whole vertical stack are untouched -- and the
    diffuser does not even need reprinting, because its central hole is r 27.92
    against the bar's 24.18 of active half-diagonal.
    """
    hl, hw = BAR_L/2 + BAR_CLR, BAR_W/2 + BAR_CLR
    # from just under the seat up through the front recess, so the module drops
    # straight in from the front rather than having to be tilted through a bore
    # it is 1.62 mm too long for
    cut = box_lwh(-hl, hl, -hw, hw, Z_SEAT_BAR - 0.60, Z_RECESS + 0.50)

    # ...and something for it to land on. Measured on the first build: the cut
    # alone left the seat 0.0% solid -- the wire slot at 6 o'clock already goes
    # right through under the bore, so the module had nothing under it at all
    # and would have dropped straight into the housing.
    #
    # Two rails along its long edges, from the deck up to the seat. They sit at
    # |y| 12.90..14.90, which is outboard of the wire slot's own half width of
    # 13.00, so the slot stays open for the ring leads. 1.60 mm of the module's
    # 29 mm width rests on each -- and the diffuser's collar tip, 0.40 mm above
    # its top face, is what stops it lifting back out.
    rails = None
    for sy in (1, -1):
        r = box_lwh(-BAR_L/2 - 1.0, BAR_L/2 + 1.0,
                    *sorted((sy*(BAR_W/2 + BAR_CLR), sy*(BAR_W/2 - 1.60))),
                    Z_DECK, Z_SEAT_BAR)
        rails = r if rails is None else rails + r
    return cut, rails


def assemble_base(B, sam, bar=False):
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
    if bar:
        cut, rails = bar_pocket()
        out = (out - cut) + rails
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


def build_backcover(B):
    """A flat back for a clock whose S3 lives in the stand-box.

    The 25 mm housing carried the board; this carries nothing but the plate
    the clock hangs from and a shallow pocket for the leads to turn the corner
    in. Same screw pillars and keyhole as the housing, so the base does not
    know the difference, and the lead exit is a notch in the rim at 6 o'clock
    the full depth of the pocket.
    """
    RB, RI = B.r_body, B.r_inner
    PT, PD = BACKCOVER_PLATE, BACKCOVER_POCKET
    Z1 = Z_DECK
    Z0 = Z1 - (PT + PD)
    ZP = Z0 + PT
    body = cyl(RB, Z0, Z1, SEG) - cyl(RI, ZP, Z1 + 1.0, SEG)
    # keyhole, one solid
    kx, kd = HANG_R, KEY_DROP
    zt = ZP + 1.0
    key = (cyl(KEY_ENTRY_D/2, Z0 - 1.0, zt, 48, centre=(kx - kd, 0))
           + box_lwh(kx - kd, kx, -KEY_SLOT_W/2, KEY_SLOT_W/2, Z0 - 1.0, zt)
           + cyl(KEY_SLOT_W/2, Z0 - 1.0, zt, 32, centre=(kx, 0)))
    body -= key
    # screw pillars up to the deck, same places as the housing
    pillars, holes = None, None
    for a in B.screw_ang:
        x, y = B.screw_r*math.cos(math.radians(a)), B.screw_r*math.sin(math.radians(a))
        p = cyl(3.60, Z0, Z1, 40, centre=(x, y))
        h = (cyl(SCREW_CLEAR/2, Z0 - 1.0, Z1 + 1.0, 32, centre=(x, y))
             + cyl(SCREW_HEAD/2, Z0 - 1.0, Z0 + min(3.20, PT - 0.60), 40, centre=(x, y)))
        pillars = p if pillars is None else pillars + p
        holes = h if holes is None else holes + h
    body += pillars
    body -= holes
    # the leads leave at 6 o'clock: a notch through the rim, pocket-deep
    body -= box_lwh(-RB - 2.0, -RI + 2.0, -CABLE_W/2, CABLE_W/2, ZP, Z1 + 1.0)
    return body


def _stand_solid(B, depth, tilt):
    """build_stand's body, parameterised on the tilt, returned in the DESK
    frame with its flat foot. Kept separate so the stand-box can reuse it."""
    t = tilt
    R = B.r_body + STAND_CLR
    y_top = -R * math.cos(math.radians(STAND_WRAP))
    x_out = math.sqrt((R + STAND_WALL)**2 - y_top**2)
    hw = B.r_body
    Y_LOW = -160.0
    h_com = STAND_LIFT + B.r_body*math.cos(math.radians(t))
    com_back = depth/2 * math.cos(math.radians(t))
    toe = max(0.0, math.cos(math.radians(t)) *
              (h_com*math.tan(math.radians(STAND_TOE_TARGET))
               - h_com*math.tan(math.radians(t)) - com_back))
    prof = [( x_out, y_top), ( hw, y_top - STAND_FLARE), ( hw, Y_LOW),
            (-hw, Y_LOW), (-hw, y_top - STAND_FLARE), (-x_out, y_top)]
    s = prism(prof, -(depth + STAND_STOP_T), toe)
    s -= cyl(R, -depth - 0.001, toe + 5.0, SEG)
    s -= cyl(STAND_STOP_RI, -(depth + STAND_STOP_T) - 1.0, -depth, SEG)
    crown = -(R + STAND_SHELL)
    arch = [(-STAND_ARCH_HW, Y_LOW), (STAND_ARCH_HW, Y_LOW),
            (STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0)),
            (10.0, crown), (-10.0, crown),
            (-STAND_ARCH_HW, crown - (STAND_ARCH_HW - 10.0))]
    s -= prism(arch, -(depth + STAND_STOP_T) - 1.0, toe + 5.0)
    notch = box_lwh(-STAND_NOTCH_HW, STAND_NOTCH_HW, Y_LOW - 1.0, -(STAND_STOP_RI - 6.0),
                    -(depth + STAND_STOP_T) - 1.0, -(depth - STAND_NOTCH_BACK))
    s -= notch
    h0 = STAND_LIFT + B.r_body * math.cos(math.radians(t))
    xf = lambda m: m.rotate([90.0 - t, 0.0, 0.0]).translate([0.0, 0.0, h0])
    s = xf(s) ^ box_lwh(-200, 200, -200, 200, 0.0, 400.0)
    sec = s.slice(STAND_FOOT).offset(-STAND_FOOT_OFF, JoinType.Miter, 2.0)
    keep = Manifold.extrude(sec, STAND_FOOT + 1.0).translate([0.0, 0.0, -1.0])
    s = s - (box_lwh(-200, 200, -200, 200, -1.0, STAND_FOOT) - keep)
    return s, xf(notch), h0


def _teardrop(r, z0, z1, seg=24):
    """A hole for printing sideways: a cylinder along z with a point on its
    local -y side (which rotate([-90, 0, 0]) turns into +z, up). The point is
    a pentagon: a box 0.02 wider than the circle's 45-degree chord, from
    inside the circle down to the chord's height, then two edges to an apex
    at 2c + 0.05 -- 47 degrees from the horizontal, so every facet of the
    circle above the chord is inside them. A triangle with its base 0.05
    INSIDE the circle was tried first: its edges were secants that re-entered
    the circle, and the 240 and 255 degree facets were left outside them
    (10.5 mm2 of 22-37 degree faces, check3)."""
    c = r*math.cos(math.radians(45.0)) + 0.02
    apex = 2.0*c + 0.05
    return cyl(r, z0, z1, seg) + prism([(-c, 0.2), (-c, -c), (0.0, -apex), (c, -c), (c, 0.2)], z0, z1)


def build_standbox(B, depth):
    """The stand with the S3 in it. Sam: "housed at the bottom of the clock in
    the stand. Make the clock lean back a bit though."

    The cradle is _stand_solid at STANDBOX_TILT, for a clock wearing the flat
    back cover. Under and behind it, in the desk frame so everything in it is
    level, a plinth: a box the width of the clock, with a BAY for the board
    tray opening at the back, a lightening pocket open at the bottom either
    side of it (roof bridged, ribbed past STANDBOX_CELL_MAX), and the cradle's
    own 6 o'clock notch re-cut through the plinth's roof so the leads drop
    straight from the clock into the bay. The notch is the SAME solid the
    cradle was cut with, put through the same transform -- so the two cuts
    cannot disagree.

    How deep the plinth runs is set by tipping, both ways: the toe in front by
    the forward angle, the back edge by the backward one, each to
    STANDBOX_TIP_TARGET with the clock's centre where the cover puts it.
    STANDBOX_PLINTH_D is the floor, not the answer -- on the 60 the centre is
    137 mm up and the plinth runs 56 mm behind the cradle axis.

    Returns (stand, tray). The tray carries the board and IS the lid: a floor
    with pads and rails, a hook over each far corner, and an end plate with
    the USB-C window that closes the bay and screws to the back face.
    """
    t = STANDBOX_TILT
    s, notch, h0 = _stand_solid(B, depth, t)
    bb = s.bounding_box()
    tip = math.tan(math.radians(STANDBOX_TIP_TARGET))
    y_com = (depth/2)*math.sin(math.radians(t))
    z_com = h0 - (depth/2)*math.cos(math.radians(t))
    # The plinth's front face sits PROUD of the cradle's front-most point,
    # never on it: on the 32 body, whose cradle needs no toe, the cradle's
    # tilted front face meets a flush vertical face along the foot's front
    # edge -- a line tangency, and in float32 that is exactly a NotManifold.
    toe = max(0.5, z_com*tip + bb[1] - y_com)
    y0 = bb[1] - toe
    y1 = max(y0 + STANDBOX_PLINTH_D + max(0.0, toe - 4.0), y_com + z_com*tip + 0.5)
    hw = B.r_body
    H = STANDBOX_PLINTH_H

    # --- the bay, sized off the tray ----------------------------------------
    # SAM'S board, not the drawing's. The rails used to be BOARD_W/2 +
    # BRD_RAIL_CLR apart, i.e. 28.99, against a board that measures 29.00 --
    # a negative fit that no print tuning could rescue. STANDBOX_SLOT_W is the
    # channel between the rails and it is the one number to turn if the fit is
    # wrong; the base's own board mount is untouched and keeps BOARD_W/BOARD_L.
    rail_y = STANDBOX_SLOT_W/2
    tray_w = STANDBOX_SLOT_W + 2*STANDBOX_RAIL_T                    # 34.20
    tray_l = STANDBOX_BOARD_L + BRD_END_CLR + STANDBOX_RAIL_T       # 67.50
    bay_w = tray_w + 2*STANDBOX_BAY_CLR
    bay_l = tray_l + STANDBOX_BAY_CLR
    bay_z0 = STANDBOX_FLOOR
    bay_z1 = H - STANDBOX_ROOF
    # Headroom, stated as what it actually has to hold rather than a bare 14:
    # the tray's own floor, the pads that lift the PCB clear of its header
    # tails, Sam's 14 mm over the PCB with the headers on, and air above that
    # for the leads, because he said they stick out of the top.
    need = STANDBOX_TRAY_T + BRD_POST_H + STANDBOX_BOARD_H + STANDBOX_WIRE_H
    assert bay_z1 - bay_z0 >= need, \
        f'bay {bay_z1 - bay_z0:.2f} too low: needs {need:.2f} for board + leads'
    assert bay_w + 2*STANDBOX_WALL <= 2*hw, 'bay wider than the clock'
    # The bay opens at the back and runs forward at least the tray's length,
    # and further -- to 2 mm past the front of the cradle's notch -- when the
    # notch lands ahead of that. On the 60 the plinth is pushed back for
    # stability while the notch stays under the clock, and a bay that stopped
    # short would leave the leads a dead-end trench in the roof. A longer bay
    # is a longer tunnel, not a wider bridge.
    nb = (notch ^ box_lwh(-300, 300, -300, 300, bay_z1 - 1.0, H + 1.0)).bounding_box()
    bay_y0 = min(y1 - bay_l, nb[1] - 2.0)
    assert bay_y0 - y0 >= STANDBOX_WALL, 'bay runs into the plinth\'s front wall'

    # 0.4 mm WIDER than the cradle each side, not flush with it: the cradle's
    # side faces are the planes x = +-hw, and a box with its sides on those
    # same planes unions into coplanar faces that come apart in float32 --
    # the 32 and the 60 both failed finalise on exactly that. Proud, the
    # cradle's sides are buried. Built from z = -1 and cut at the desk plane
    # at the very end, with everything else, so the bottom is one face.
    plinth = box_lwh(-hw - 0.4, hw + 0.4, y0, y1, -1.0, H)
    # The bay: its section in x-z is a box with the two top corners chamfered
    # (STANDBOX_BAY_CHAMF_W in, _H up: 54.5 deg, steeper than check3's 45),
    # so the flat ceiling is bay_w - 2*CHAMF_W = 23.8 mm and not a 34 mm
    # bridge. Drawn in x-y, extruded along z, stood up about x.
    cw, chh = STANDBOX_BAY_CHAMF_W, STANDBOX_BAY_CHAMF_H
    sec = [(-bay_w/2, bay_z0), (bay_w/2, bay_z0), (bay_w/2, bay_z1 - chh),
           (bay_w/2 - cw, bay_z1), (-bay_w/2 + cw, bay_z1), (-bay_w/2, bay_z1 - chh)]
    bay = prism(sec, 0.0, (y1 + 1.0) - bay_y0).rotate([90.0, 0.0, 0.0]) \
              .translate([0.0, y1 + 1.0, 0.0])
    # The bay and the lightening pockets are cut from the ASSEMBLED solid,
    # not from the plinth alone: the cradle's stop wall runs down into the
    # plinth's roof and 3 mm past it, and cut from the plinth alone that
    # lower lip was left hanging inside the bay (1.2 cm3 of it, check6) and
    # as a fin in each pocket with nothing under it to print on.
    # Pockets either side of the bay, open at the bottom, roof bridged, split
    # into cells no wider than STANDBOX_CELL_MAX -- and stopping short of the
    # cradle's legs at |x| = STAND_ARCH_HW, which stay solid to the desk.
    pockets = None
    xi = bay_w/2 + STANDBOX_WALL
    xo = min(hw - STANDBOX_WALL, STAND_ARCH_HW - 1.0)
    span = xo - xi
    if span >= 8.0:
        ncell = max(1, int(math.ceil(span / STANDBOX_CELL_MAX)))
        cwid = (span - (ncell - 1)*STANDBOX_RIB_T) / ncell
        for sign in (-1, 1):
            for k in range(ncell):
                a = xi + k*(cwid + STANDBOX_RIB_T)
                b = a + cwid
                c = box_lwh(a if sign > 0 else -b, b if sign > 0 else -a,
                            y0 + STANDBOX_WALL, y1 - STANDBOX_WALL, -1.0, bay_z1)
                pockets = c if pockets is None else pockets + c

    stand = s + plinth
    stand -= bay
    if pockets is not None:
        stand -= pockets
    # M2 pilots for the lid, in the back face either side of the bay. The
    # back wall is 3 mm, which is one turn of an M2; so each pilot gets a
    # PILLAR behind the wall, in the back corner of the pocket, from the desk
    # to the roof -- added AFTER the pocket is cut, or the pocket takes it
    # away again (which is what happened to the first version's bosses).
    # Buried 1 mm into the back wall, the side wall and the roof, and it
    # stands on the desk, so it prints as a post and not as a cantilever.
    zs = (bay_z0 + bay_z1)/2
    for sx in (-1, 1):
        xs = sx*(bay_w/2 + 4.5)
        stand += box_lwh(xs - STANDBOX_BOSS_R, xs + STANDBOX_BOSS_R,
                         y1 - STANDBOX_WALL - STANDBOX_BOSS_L, y1 - 2.0,
                         -1.0, bay_z1 + 1.0)
        # ...and the pilot runs 1 mm PAST the back face, so its end cap never
        # lands on that face
        stand -= _teardrop(STANDBOX_SCREW_PILOT/2, 0.0, STANDBOX_WALL + STANDBOX_BOSS_L) \
                 .rotate([-90.0, 0.0, 0.0]).translate([xs, y1 - STANDBOX_WALL - STANDBOX_BOSS_L + 1.0, zs])
    # the notch, through the roof and into the bay: the leads' way down.
    # Only down to just under the roof, not through the bay floor.
    stand -= notch ^ box_lwh(-200, 200, -200, 200, bay_z1 - 1.0, 400.0)
    stand = stand ^ box_lwh(-300, 300, -300, 300, 0.0, 400.0)

    # --- the tray, printed flat, in its own frame: floor on z = 0, board
    #     along +y with the connector end at y = 0 where the lid is ----------
    T = STANDBOX_TRAY_T
    tray = box_lwh(-tray_w/2, tray_w/2, 0.0, tray_l, 0.0, T)
    # rails, touching only the board's edge
    for sx in (-1, 1):
        tray += box_lwh(sx*rail_y if sx > 0 else -(rail_y + STANDBOX_RAIL_T),
                        rail_y + STANDBOX_RAIL_T if sx > 0 else -rail_y,
                        0.0, tray_l, T - 0.01, T + STANDBOX_RAIL_H)
    # end stop at the antenna end
    tray += box_lwh(-tray_w/2, tray_w/2, tray_l - STANDBOX_RAIL_T, tray_l,
                    T - 0.01, T + BRD_RAIL_TOP)
    # a hook over each far corner of the board, from the rail STANDBOX_HOOK_W
    # inward, the board slides under them. Not one bar across: that is a 26 mm
    # flat ceiling between the rails, over check3's 25.
    for sx in (-1, 1):
        x_in = rail_y - STANDBOX_HOOK_W
        tray += box_lwh(x_in if sx > 0 else -(rail_y + STANDBOX_RAIL_T),
                        rail_y + STANDBOX_RAIL_T if sx > 0 else -x_in,
                        tray_l - STANDBOX_RAIL_T - STANDBOX_BAR_W, tray_l - STANDBOX_RAIL_T + 0.01,
                        T + BRD_LIP_Z0, T + BRD_RAIL_TOP)
    # four pads under the board, between the pad rows
    for yy in (10.0, STANDBOX_BOARD_L - 8.0):
        for sx in (-1, 1):
            tray += cyl(BRD_POST_D/2, T - 0.01, T + BRD_POST_H, 32,
                        centre=(sx*BRD_POST_HY, yy))
    # the lid: the tray's end plate at y = 0, covering the bay's opening and
    # the roof above it, out to STANDBOX_LID_LIP past the bay each side. Its
    # bottom edge is the tray's floor plane -- the plinth's own 2 mm floor
    # shows under it -- so the whole part sits flat on the bed. The first
    # version ran 2 mm below the floor, which would have printed on air.
    lid_w = bay_w + 2*STANDBOX_LID_LIP
    lid = box_lwh(-lid_w/2, lid_w/2, -STANDBOX_LID_T, 0.01, 0.0, H - bay_z0)
    # USB-C window, centred on the connectors' height above the tray floor
    z_usb = T + BRD_POST_H + BOARD_T + BOARD_TALL/2
    lid -= box_lwh(-USB_WIN_W/2, USB_WIN_W/2, -STANDBOX_LID_T - 1.0, 1.0,
                   z_usb - USB_WIN_H/2, z_usb + USB_WIN_H/2)
    # screw clearance, matching the pilots
    for sx in (-1, 1):
        lid -= _teardrop(STANDBOX_SCREW_CLEAR/2, -STANDBOX_LID_T - 1.0, 1.0) \
               .rotate([-90.0, 0.0, 0.0]).translate([sx*(bay_w/2 + 4.5), 0.0, zs - bay_z0])
    tray += lid
    return stand, tray


def _wall_yz(prof, x0, x1):
    """A plate of constant thickness in x, whose SIDE PROFILE is prof, a list of
    (y, z) in the desk frame. prism extrudes a cross-section along z, and
    rotate([0, 90, 0]) maps local (X, Y, Z) to world (Z, Y, -X) -- verified,
    not assumed -- so the profile goes in as (-z, y) and the extrusion axis
    comes out as x. Winding is fixed inside prism()."""
    return prism([(-z, y) for (y, z) in prof], x0, x1).rotate([0.0, 90.0, 0.0])


def build_backstand(B):
    """The stand that is not a box. Sam, 2026-09-04: "give make a better base
    that isn't as bulky... The base needs to be open to fit the cables, and the
    base can go behind the clock housing with an angle."

    The clock comes down onto the desk and beds BACKSTAND_SIT into a trench in
    the foot. The trench is not modelled: the whole clock is subtracted from the
    blank as one cylinder, so the trench walls ARE the clock's own front and
    back faces at BACKSTAND_CLR, and the part cannot foul the clock anywhere.

    Two buttresses behind it take the lean. Between them is nothing at all --
    that is the cable route and the board bay, an open channel with no lid, no
    tray and no screws. Every overhang is 45 degrees or steeper and the part
    prints flat on its foot with no support.
    """
    th  = math.radians(BACKSTAND_TILT)
    ct, st_, tt = math.cos(th), math.sin(th), math.tan(th)
    R   = B.r_body
    Zb  = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)   # the clock's back face
    Zf  = Z_FRONT                                          # and its front face
    C   = BACKSTAND_CLR
    FT  = BACKSTAND_FOOT_T

    # Put the clock's lowest point at (y = 0, z = BACKSTAND_SIT). Rotating the
    # clock frame by 90 - tilt about x sends its +z axis to (0, -cos, +sin) --
    # forwards and up -- so the lowest point of the disc is the BACK face's
    # bottom rim, which is what a thing leaning backwards rests on.
    z0 = BACKSTAND_SIT + R*ct - Zb*st_
    y0 = R*st_ + Zb*ct
    xf = lambda m: m.rotate([90.0 - BACKSTAND_TILT, 0.0, 0.0]).translate([0.0, y0, z0])
    clock = xf(cyl(R + C, Zb - C, Zf + C, SEG))

    # Where the clock's two faces sit, as a function of height. Both are planes:
    # eliminating the in-plane coordinate from the rotation gives
    #   y = y0 + tan(tilt)*(z - z0) - q/cos(tilt)
    # with q the face's own z in the clock frame.
    back  = lambda z: y0 + tt*(z - z0) - Zb/ct
    front = lambda z: y0 + tt*(z - z0) - Zf/ct
    # The same two planes, moved out by the clearance ALONG THE CLOCK'S AXIS --
    # C/cos(tilt) in y, not C. Anything built to these is outside the clock at
    # every height, so the clock subtraction never touches it and there is no
    # feather where the rim crosses it. Only the FOOT is shaped by the clock
    # itself, because the trench has to follow the rim: that is the seat.
    backc  = lambda z: back(z) + C/ct
    frontc = lambda z: front(z) - C/ct

    # THE FOOTPRINT SCALES WITH THE CLOCK, the board bay does not. The numbers
    # in params are the 32's, so k is 1 there and nothing moves. On the 60 the
    # clock is 240 mm across and 290 g heavier: check7 measured an 86 mm foot
    # tipping backwards at 17.5 degrees under it, which is how this got written.
    # The floors keep the 24 -- which is SMALLER than the 32 -- from pulling the
    # buttresses in over a board that does not shrink with it.
    k   = B.r_body / BODY32.r_body
    XI  = max(BACKSTAND_WALL_XI, BACKSTAND_WALL_XI*k)
    XO  = XI + (BACKSTAND_WALL_XO - BACKSTAND_WALL_XI)*max(1.0, k)
    SH  = BACKSTAND_SPINE_H*k
    KH  = BACKSTAND_KERB_H*max(1.0, k)
    BY1_ = BACKSTAND_BAY_Y0 + BACKSTAND_SLOT_W
    Y0 = front(FT) - BACKSTAND_LIP          # the foot's front edge
    Y1 = max(BY1_ + BACKSTAND_RAIL_T + 2.0, BACKSTAND_BACK*k)   # and its back
    HW = max(XO + 2.5, BACKSTAND_HW*k)

    # ---- the foot ----------------------------------------------------------
    fillet = BACKSTAND_FILLET
    foot_pts = [(-HW, Y0), (HW, Y0), (HW, Y1 - fillet)]
    for i in range(1, 8):
        a = math.radians(90.0*i/8.0)
        foot_pts.append((HW - fillet + fillet*math.cos(a), Y1 - fillet + fillet*math.sin(a)))
    foot_pts.append((-HW + fillet, Y1))
    for i in range(1, 8):
        a = math.radians(90.0 + 90.0*i/8.0)
        foot_pts.append((-HW + fillet + fillet*math.cos(a), Y1 - fillet + fillet*math.sin(a)))
    s = prism(foot_pts, 0.0, FT)

    # ---- the front lip, which is the trench's front wall --------------------
    # It runs up past where the clock's front face crosses it; subtracting the
    # clock leaves its inner face parallel to that face, at the clearance.
    # FROM z = 0, not from the foot's top and not buried a millimetre into it.
    # Both were tried and both are the same mistake in different clothes. The
    # kerb shares the foot's FRONT face at Y0 and both its side faces at HW, so
    # it has to share the bottom one too and be a straight extension of the
    # prism there -- otherwise the boolean leaves a T-junction along the front
    # bottom edge, and the float32 round trip turns that into five non-manifold
    # edges on every body. (Meeting exactly at z = FT was worse still: on the 60
    # the kerb exported as a second body floating above the plate.)
    # ...and INSET half a millimetre on the front, so it shares no vertical face
    # or edge with the foot. Sharing the front face exactly left two edges with
    # four faces on them, which float32 cannot represent.
    #
    # NARROWER THAN THE FOOT, and that is not cosmetic. The clock is a leaning
    # DISC: at the kerb's top its rim has curved in to a half width of
    # sqrt(R^2 - p^2), and a kerb wider than that has its top plane grazed
    # tangentially by the rim, which feathers out to nothing. check3 measured
    # 0.09 mm of it. So the kerb stops well inside the rim and the clock's front
    # face cuts it cleanly right across.
    KW = min(HW - 0.5, 20.0*max(1.0, k))
    s += _wall_yz([(Y0 + 0.5, 0.0), (frontc(0.0), 0.0),
                   (frontc(KH), KH), (Y0 + 0.5, KH)], -KW, KW)

    # ---- the two buttresses ------------------------------------------------
    # Front edge: the clock's back face, so the disc beds against the whole
    # height of it. Back edge: a straight rake from the foot's back corner to
    # SPINE_T behind the clock at the top -- 33 degrees off vertical, so the
    # overhang is 57 degrees from horizontal and needs no support.
    prof = [(backc(FT - 1.0), FT - 1.0),
            (backc(SH), SH),
            (backc(SH) + BACKSTAND_SPINE_T*max(1.0, k), SH),
            # Y1 - FILLET, not Y1: the foot's back corners are radiused, so a
            # buttress that runs all the way to the back edge overhangs the
            # fillet at its outer corner. On the 24 that left a 1.12 mm sliver
            # and check3 found it.
            (Y1 - BACKSTAND_FILLET, FT - 1.0)]
    for sgn in (-1.0, 1.0):
        xi, xo = sorted((sgn*XI, sgn*XO))
        s += _wall_yz(prof, xi, xo)

    # ---- the board bay: two rails, and a lip on the back one ---------------
    SW  = BACKSTAND_SLOT_W
    BY0 = BACKSTAND_BAY_Y0
    BY1 = BY0 + SW
    RT = BACKSTAND_RAIL_T
    # DERIVED, not the old flat 6.00. The front rail's job is to locate the
    # PCB's edge and clear its top face by a fraction; with the board 4 mm lower
    # than it used to be, a 6 mm rail is a wall beside a 1.6 mm board.
    RH = BACKSTAND_POST_H + BOARD_T + BACKSTAND_RAIL_OVER
    BL = BACKSTAND_BOARD_L
    # The rails run all the way out to the buttresses and TIE THEM TOGETHER.
    # Two 2.50 mm ribs across the foot cost nothing and stop the pair splaying
    # under a 290 g clock leaning on them; the board only needs to reach 32.
    # THE FRONT RAIL TIES THE BUTTRESSES TOGETHER, the back one does not. At
    # y 7.5..10 the front rail is deep inside the buttress at every height, so
    # it welds into it cleanly; the back rail at y 40.6..43.1 runs past the
    # buttress's raked back edge and leaves 0.1 mm slivers where it pokes out.
    # One tie is enough -- it is a rib across the foot, and the foot is what
    # actually stops the pair splaying.
    rx_f = XO - 0.50         # buried in the wall, not flush with its face:
                             # a coincident face here cost the 60 six rounds
                             # of float32 cleanup and then failed outright
    rx_b = BL/2.0 + 1.50     # clear of the buttress altogether
    rx   = max(rx_f, rx_b)   # for the cuts and the probes below
    lz0 = FT + BACKSTAND_POST_H + BOARD_T   # the board's top face
    rh_back = (lz0 + BACKSTAND_LIP_GAP + BACKSTAND_LIP_T) - FT
    s += box_lwh(-rx_f, rx_f, BY0 - RT, BY0, FT - 1.0, FT + RH)        # low,
    s += box_lwh(-rx_b, rx_b, BY1, BY1 + RT, FT - 1.0, FT + rh_back)   # carries
    # NO POSTS UNDER THE PCB. There were four 6 mm pads lifting it
    # BACKSTAND_POST_H off the floor so header tails had somewhere to be; Sam,
    # 2026-09-05: "remove the 4 small cylinders on the ESP32 mount area." So the
    # board lies flat on the bay floor and POST_H is 0.
    #
    # It is still a parameter and everything below is still derived from it --
    # the rail height, the lip, the cut over the board. Put a number back in it
    # and the whole bay lifts by that much, correctly. What it will NOT do on
    # its own is give the tails somewhere to go: for that the posts have to come
    # back, or the rails need an inward ledge at POST_H.
    # The back rail's lip: slide the board's back edge under it, then drop the
    # front edge in over the low front rail. Nothing screws down and nothing
    # closes over the board. The lip's underside is a flat ceiling 1.50 mm wide
    # -- a LEDGE, not a bridge, and check3 allows 2.50.
    lo = BACKSTAND_LIP_OVER
    s += box_lwh(-18.0, 18.0, BY1 - lo, BY1,
                 lz0 + BACKSTAND_LIP_GAP, FT + rh_back)

    # ---- and now take everything away --------------------------------------
    s -= clock
    # the board slot itself, and the air over it: the leads come off the top of
    # a dev board, so nothing may close over it
    # NOT rx. The rails run THROUGH the buttresses; this cut must stop at their
    # inner face or it takes the top off both of them -- which is exactly what
    # it did the first time rx was widened, and check3 is what found it.
    cx = XI + 0.50
    # FT + 0.50, not FT + POST_H. With the posts gone POST_H is 0 and this cut
    # would land exactly on the foot's top face -- the coincident-plane case
    # that cost this part two rebuilds already. Half a millimetre up is still
    # under the board and cannot be coincident with anything.
    #
    # The second cut, which used to clear the space under the lip, is gone:
    # between the foot's top and the lip there is nothing to remove, and a
    # boolean that removes nothing is only a chance to go wrong.
    s -= box_lwh(-cx, cx, BY0, BY1 - lo, FT + 0.50, FT + 200.0)
    # the window through each buttress, a pentagon with a 45 degree gable
    wy0, wy1 = BACKSTAND_WIN_Y0, BACKSTAND_WIN_Y1
    wh, wa = FT + BACKSTAND_WIN_H, FT + BACKSTAND_WIN_APEX
    win = [(wy0, FT - 1.0), (wy1, FT - 1.0), (wy1, wh),
           ((wy0 + wy1)/2.0, wa), (wy0, wh)]
    # The buttress's back edge RAKES FORWARD, so the wall behind the window is
    # thinnest at the window's tallest back point, not at its base. At y1 = 36
    # that left 0.98 mm and check3 found it on two bodies.
    rake = lambda z: (Y1 - BACKSTAND_FILLET) + (backc(SH) + BACKSTAND_SPINE_T*max(1.0, k)
                                                - (Y1 - BACKSTAND_FILLET)) * (z - (FT - 1.0)) / (SH - (FT - 1.0))
    for wy, wz in ((wy1, FT - 1.0), (wy1, wh), ((wy0 + wy1)/2.0, wa)):
        assert rake(wz) - wy >= 1.5, (
            f'back-stand: {rake(wz) - wy:.2f} mm of buttress behind the window at '
            f'y={wy:.1f}, z={wz:.1f}; move BACKSTAND_WIN_Y1 forward')
    # ONE PER BUTTRESS. Cut across the full width and it goes through the board
    # bay's rails and the retaining lip as well, which is exactly what the first
    # version did.
    for sgn in (-1.0, 1.0):
        xi, xo = sorted((sgn*(XI - 1.0), sgn*(XO + 1.0)))
        s -= _wall_yz(win, xi, xo)
    # The cable gate: a channel out of the foot's top from inside the trench to
    # inside the bay, and it takes the middle out of the front rail on the way
    # so the leads reach the board without climbing anything. The rail's two
    # outer sections still hold the board's front edge and still tie the
    # buttresses together.
    #
    # It starts BEHIND the clock and ends INSIDE the bay on purpose. Ending it
    # on a face that already exists -- the foot's top, the rail's top, the bay's
    # front -- is what a boolean cannot do reliably: the first version stopped
    # 0.001 mm above the foot and that sliver collapsed in the float32 round
    # trip, taking the 24's manifold with it. Overlap what you cut into.
    s -= box_lwh(-BACKSTAND_CABLE_HW, BACKSTAND_CABLE_HW,
                 back(FT) - 2.0, BY0 + 2.0,
                 FT - BACKSTAND_CABLE_D, FT + RH + 1.0)
    # and anything that ended up under the desk
    s -= box_lwh(-500, 500, -500, 500, -500.0, 0.0)
    return s


def make_body(n, ring_od, ring_id, tag=None):
    """A clock of another size: give it the LED count and the ring's outer and
    inner diameter, measured, and every other radius follows the rules the 32
    was derived by. Sam: "Add more options to change the size of the clock."
    No preset for a ring nobody has measured -- the numbers come from the
    part in your hand.
    """
    r_ring_i = ring_id/2 - 0.50
    r_ring_o = ring_od/2 + 0.50
    r_body   = r_ring_o + 3.50
    r_lip_i  = r_body - 2.00
    screw_r  = r_ring_i - 3.50
    assert r_ring_i > DIFF_BORE_RI + 6.0, (
        f'a {ring_id} mm ring does not clear the {2*DIFF_BORE_RI:.1f} mm screen window')
    return Body(tag if tag is not None else f'-{n}', n, ring_od, ring_id, r_body,
                r_ring_i, r_ring_o, r_lip_i, DECK_RI, screw_r,
                [60, 120, 240, 300], [80, 105, 255, 280])


def parts_for(B, sam, full=True):
    """Everything one body needs. full=False skips the bar variants."""
    tg = B.tag
    cover_depth = Z_FRONT - (Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET))
    standbox, tray = build_standbox(B, cover_depth)
    parts = [
        (assemble_base(B, sam),          f'mini-round-clock-base{tg}',      True),
        (build_rear_housing(
             POCKET_DEEP if B.n == 24 else HOUSING_DEEP_BIG - PLATE_T_BIG,
             B.r_body, B.r_inner,
             vent_ang=B.vent_ang, screw_ang=B.screw_ang, screw_r=B.screw_r,
             plate_t=None if B.n == 24 else PLATE_T_BIG),
                                         f'mini-round-clock-housing{tg}',   True),
        (build_backcover(B),             f'mini-round-clock-backcover{tg}', True),
        (build_diffuser(B),              f'mini-round-clock-diffuser{tg}',  True),
        (build_diffuser(B, numerals_on=False),
                                         f'mini-round-clock-diffuser{tg}-plain', True),
        (build_stand(B, Z_FRONT - (Z_DECK - HOUSING_DEEP)),
                                         f'mini-round-clock-deskstand{tg}', True),
        (standbox,                       f'mini-round-clock-standbox{tg}',  True),
        (tray,                           f'mini-round-clock-standbox-tray{tg}', True),
        (build_backstand(B),             f'mini-round-clock-backstand{tg}', True),
        (build_numerals(B),              f'mini-round-clock-numerals{tg}',  False),
    ]
    # the flange only where there is a trough to fill: the 60's diffuser
    # already runs out to its lip
    if (B.r_lip_i - DIFF_FLANGE_CLR) - B.diff_outer >= DIFF_FLANGE_MIN:
        parts += [
            (build_diffuser(B, flange=True), f'mini-round-clock-diffuser{tg}-flange', True),
            (build_diffuser(B, numerals_on=False, flange=True),
                                             f'mini-round-clock-diffuser{tg}-flange-plain', True),
        ]
    else:
        print(f'  diffuser{tg}-flange SKIPPED: the diffuser reaches r {B.diff_outer:.2f} and '
              f'the lip is at {B.r_lip_i:.2f}; there is no trough to fill')
    if full and B.n != 24 and B.n in (32, 60):
        parts += [
            (assemble_base(B, sam, bar=True),
             f'mini-round-clock-base{tg}-bar', True),
            (build_diffuser(B, bar=True),
             f'mini-round-clock-diffuser{tg}-bar', True),
            (build_diffuser(B, bar=True, numerals_on=False),
             f'mini-round-clock-diffuser{tg}-bar-plain', True),
        ]
    return parts


# =============================================================================
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='mini-round-clock parts')
    ap.add_argument('--custom', nargs=3, type=float, metavar=('N', 'RING_OD', 'RING_ID'),
                    help='build one body of another size: LED count, ring outer '
                         'and inner diameter in mm, measured off the ring')
    ap.add_argument('--tag', default=None, help='file suffix for a custom body, e.g. -45')
    ap.add_argument('--only', default=None, help='build only this body tag ("", -32, -60)')
    args = ap.parse_args()
    print(summary())
    print('building...')
    sam = load_sams_base()
    parts = []
    if args.custom:
        n, od, idm = int(args.custom[0]), args.custom[1], args.custom[2]
        B = make_body(n, od, idm, args.tag)
        print(f'  custom body: {n} LEDs, ring {od} / {idm}, body {2*B.r_body:.2f} mm, '
              f'tag "{B.tag}"')
        parts += parts_for(B, sam, full=False)
    else:
        for B in (BODY24, BODY32, BODY60):
            if args.only is not None and B.tag != args.only:
                continue
            # -bar: the same base with the rectangular relief for the 1.9"
            # ST7789. Only the 32 and 60 get one. On the 108 mm body the
            # module's corners reach r 34.22 against a ring pocket that starts
            # at 35.11, which would leave 0.89 mm of wall -- see BUILD-LOG.
            parts += parts_for(B, sam)
    # The battery shelves only mean anything if a battery fits, and at
    # HOUSING_DEEP = 25.00 one does not. Emitting the part anyway would put a
    # file in the folder that cannot be used, so it is skipped and said out loud.
    if HOUSING_DEEP >= BATTERY_MIN_HOUSING:
        parts.append((build_shelf(BAT_W), 'mini-round-clock-battery-shelf-x2', True))
    else:
        print(f'  battery shelves SKIPPED: a {BAT_T:.2f} mm cell needs a '
              f'{BATTERY_MIN_HOUSING:.2f} mm housing and this one is '
              f'{HOUSING_DEEP:.2f}. No internal battery in this build.')
    if not args.custom and args.only in (None, '-60'):
        parts.append((build_light_guides(BODY60), 'mini-round-clock-light-guides-60', True))
    if not args.custom and args.only is None:
        parts.append((build_collar_gauges(), 'mini-round-clock-collar-gauges', False))
        parts.append((build_board_clamp(), 'mini-round-clock-board-clamp', True))
        parts.append((build_board_gauge(), 'mini-round-clock-board-gauge', True))
    for man, fn, strict in parts:
        t = csg.finalise(man, fn, strict=strict)
        t.export(fn + '.stl')
        t.export(fn + '.3mf')
    print('done')
