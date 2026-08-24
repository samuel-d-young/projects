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
    """Full-disc floor under Sam's base, with a window the S3 pushes up into.

    The board is caught by a ledge at its two SHORT ends only. The DevKitC-1
    carries its pad/pin rows down both long edges, 1.27 mm in from the edge, so
    a ledge there would foul any soldered header; the ends are bare.

    Printed deck-side-down the ledge is material that simply stops -- not an
    overhang -- so the whole part needs no support.
    """
    # 0.30 inset: Sam's outer wall is a 144-gon at r=54.00 and a second
    # independently-generated cylinder at the same radius leaves 1e-5 slivers
    # that collapse into zero-area faces when the STL is written in float32.
    deck = cyl(R_BODY - DECK_INSET, Z_DECK, Z_BACK, SEG)

    c  = BOARD_CLR
    x0, x1 = BOARD_X0 - c, BOARD_X1 + c
    y1 = BOARD_W/2 + c
    Z_LEDGE = Z_BACK - 0.80          # board underside rests here

    # Cut the window straight through, then put the two end ledges BACK.
    # Subtracting a stepped (T-shaped) void instead leaves a surface that is
    # self-touching once the mesh is quantised to float32 for the STL -- the
    # two lobes share their full-width side walls. Same solid, clean mesh.
    # The window runs PAST the board at +x, so the keeper's riser has somewhere
    # to come up through (see build_keeper).
    deck -= box_lwh(x0, WINDOW_X1_EXT, -y1, y1, Z_DECK - 1.0, Z_BACK + 1.0)
    # ...and the ledges are bars under the board's two ends, anchored into the
    # deck at both y ends. 1.50 mm, not 3.00: see LEDGE_END in params.py -- a
    # 3 mm ledge at each end narrows the opening so far that the board cannot be
    # tilted in at all, which is the bug this fixes.
    deck += box_lwh(x0, x0 + LEDGE_END, -y1, y1, Z_DECK, Z_LEDGE)
    deck += box_lwh(BOARD_X1 - LEDGE_END, BOARD_X1, -y1, y1, Z_DECK, Z_LEDGE)

    # wire port for the battery lead, moved clear of the USB-C bay
    deck -= box_lwh(*WIRE_PORT[:2], *WIRE_PORT[2:], Z_DECK - 1.0, Z_BACK + 1.0)

    # two corner posts at the +x end, to stop the board sliding in y. The -x
    # pair are gone: the beam's pillars stand in that space now.
    posts = None
    for sy in (1, -1):
        p = cyl(1.60, Z_BACK, Z_BACK + POST_H, 24,
                centre=(BOARD_X1 - 3.0, sy * (y1 + 1.4)))
        posts = p if posts is None else posts + p
    deck += posts

    return deck


def board_beam():
    """A beam across the board's USB end, so it cannot lift into the clock.

    The ledges stop the board falling out the back; nothing stopped it floating
    4.60 mm forward. This beam sits at z 4.20, which is 0.20 mm above the
    tallest thing the board carries -- so it never touches the board in normal
    use and cannot foul a connector or a soldered header, whatever the board's
    exact layout.

    Its pillars stand at x = -20.00 rather than over the board's end at -24.00
    for a measured reason: Sam's rear bore is r = 27.78, so at x = -24 the bore
    is only open to |y| < 13.99 and the deck window already reaches 13.15 --
    0.84 mm of landing. At x = -20 the bore is open to |y| < 19.30 and the
    pillars get a 3 mm footprint on solid deck.
    """
    y1 = BOARD_W/2 + BOARD_CLR
    x0, x1 = -20.0 - BEAM_PILLAR_W/2, -20.0 + BEAM_PILLAR_W/2
    yo = BEAM_PILLAR_Y + BEAM_PILLAR_W/2
    b = box_lwh(x0, x1, y1 + 0.85, yo, Z_BACK, BEAM_Z1)
    b += box_lwh(x0, x1, -yo, -(y1 + 0.85), Z_BACK, BEAM_Z1)
    b += box_lwh(x0, x1, -yo, yo, BEAM_Z0, BEAM_Z1)
    return b


def usbc_bay():
    """Rails, shelf and lips that hold the USB-C breakout, and its wall pocket.

    Returns (solid, void). The void is cut from the assembled base first -- it
    opens a pocket through the wall at 6 o'clock and the channel the plug comes
    in through -- then the solid is added back inside it.

    The breakout slides in along -x until its PCB edge butts the channel's
    shoulder. That shoulder is what makes this safe to pull on: the channel is
    13.00 mm wide and the PCB is 14.20, so pulling the plug cannot drag the
    breakout out through the wall.
    """
    hy = USBC_PCB_W/2 + USBC_CLR                     # 7.40
    x0, x1 = USBC_FACE_X, USBC_BAY_X1

    void = box_lwh(USBC_FACE_X, WIRE_SLOT_END + 1.0, -USBC_RAIL_HY, USBC_RAIL_HY,
                   Z_BACK, USBC_RAIL_H)              # pocket through the wall
    void += box_lwh(-R_BODY - 2.0, USBC_FACE_X, -PLUG_CH_W/2, PLUG_CH_W/2,
                    PLUG_CH_Z0, PLUG_CH_Z0 + PLUG_CH_H)      # the plug channel

    solid = box_lwh(x0, x1,  hy, USBC_RAIL_HY, Z_BACK, USBC_RAIL_H)
    solid += box_lwh(x0, x1, -USBC_RAIL_HY, -hy, Z_BACK, USBC_RAIL_H)
    solid += box_lwh(x0, x1, -USBC_SHELF_HY, USBC_SHELF_HY, Z_BACK, USBC_Z)
    solid += box_lwh(x0, x1,  USBC_LIP_HY, hy, USBC_LIP_Z0, USBC_LIP_Z1)
    solid += box_lwh(x0, x1, -hy, -USBC_LIP_HY, USBC_LIP_Z0, USBC_LIP_Z1)
    return solid, void


def keeper_pilots():
    """Two M3 pilots for the keeper. r = 44.02 -- outside the tab window
    (42.66) and outside the tab-slot walls (43.50), so they bite solid base."""
    holes = None
    for sy in (1, -1):
        c = cyl(KEEP_SCREW_PIL/2, Z_DECK - 1.0, Z_BACK + KEEP_SCREW_DEP, 32,
                centre=(KEEP_SCREW_X, sy * KEEP_SCREW_Y))
        holes = c if holes is None else holes + c
    return holes


def build_keeper():
    """The part that goes on after the board: a plate, a riser, a tongue.

    Print it plate-down. The tongue's 2.30 mm overhang is the only unsupported
    face on it.
    """
    hy = KEEP_TONGUE_HY
    z0 = Z_DECK - KEEP_PLATE_T
    xr0 = BOARD_X1 + 0.30
    # the plate is clipped to a circle so its corners cannot reach the housing's
    # pocket wall, and so the screws keep 1.8 mm of material all round them
    k = (box_lwh(xr0, KEEP_PLATE_X1, -KEEP_PLATE_HY, KEEP_PLATE_HY, z0, Z_DECK)
         ^ cyl(KEEP_PLATE_R, z0 - 1.0, Z_DECK + 1.0, SEG))      # plate
    k += box_lwh(xr0, WINDOW_X1_EXT - 0.50, -hy, hy, z0, KEEP_TONGUE_Z1)   # riser
    k += box_lwh(KEEP_TONGUE_X1 - KEEP_TONGUE_L, xr0, -hy, hy,
                 KEEP_TONGUE_Z0, KEEP_TONGUE_Z1)                # tongue
    for sy in (1, -1):
        k -= cyl(KEEP_SCREW_D/2, z0 - 1.0, Z_DECK + 1.0, 32,
                 centre=(KEEP_SCREW_X, sy * KEEP_SCREW_Y))
    return k


def seat_drop(mm):
    """Lower the display seat, so the diffuser's collar stops fouling the module.

    Cut up to the top of the display pocket rather than stopping at the old seat
    plane: stopping there would leave a 0.3 mm down-facing ledge ringing the
    pocket, which is a needless overhang for no gain.
    """
    if mm <= 0:
        return None
    return cyl(R_DISP_POCKET, Z_SEAT - mm, Z_RECESS + 0.5, SEG)


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
    hw, R = TAB_SLOT_HW, TAB_WALL_RO + 5.0
    keep = box_lwh(0.0, R, -hw, hw, Z_BACK - 1.0, TAB_CHAMF_Z)
    keep += prism_taper([(0.0, -hw), (R, -hw), (R, hw), (0.0, hw)],
                        TAB_CHAMF_Z, TAB_WALL_TOP + 0.001,
                        1.0, (hw + (TAB_WALL_TOP - TAB_CHAMF_Z)) / hw)
    return solid - keep


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
def build_rear_housing(pocket_d):
    """Battery box + wall hanger + cable exit. Prints rear-plate-down.

    pocket_d is the clear depth for the battery. It is the ONLY thing that
    changes between the two variants, because it is the only thing the battery
    choice actually drives.
    """
    Z1 = Z_DECK                              # -2.40, mates to the base's deck
    Z0 = Z1 - (PLATE_T + pocket_d)           # rear face, against the wall
    Z_POCKET = Z0 + PLATE_T                  # floor of the battery pocket

    body = cyl(R_BODY, Z0, Z1, SEG)
    body -= cyl(R_INNER, Z_POCKET, Z1 + 1.0, SEG)

    # No stiffening ribs behind the hanger. An earlier version had them and the
    # checker caught that they ate into the battery footprint. They were not
    # needed: the plate is 3.5 mm and the screw shank bears on 4.6 x 3.5 mm of
    # it, so at a 400 g clock the bearing stress is about 0.25 MPa against PLA's
    # ~50 MPa yield. The plate is already two orders of magnitude oversized.

    # --- keyhole. Cut as ONE solid: three overlapping pieces subtracted
    #     separately leave coincident faces that break the mesh in float32.
    kx, kd = HANG_R, KEY_DROP
    zt = Z_POCKET + 1.0
    key = (cyl(KEY_ENTRY_D/2, Z0 - 1.0, zt, 48, centre=(kx - kd, 0))
           + box_lwh(kx - kd, kx, -KEY_SLOT_W/2, KEY_SLOT_W/2, Z0 - 1.0, zt)
           + cyl(KEY_SLOT_W/2, Z0 - 1.0, zt, 32, centre=(kx, 0)))
    body -= key

    # The screw head ends up INSIDE the compartment once the clock is dropped
    # onto it -- that is what holds the clock up. Nothing to cut for it, the
    # pocket is already open there; but the battery has to stay clear of that
    # zone, which is why the pocket is offset (see BAT_CX).

    # --- screw pillars up to the deck
    pillars, holes = None, None
    for a in SCREW_ANG:
        x, y = SCREW_R*math.cos(math.radians(a)), SCREW_R*math.sin(math.radians(a))
        p = cyl(3.60, Z0, Z1, 40, centre=(x, y))
        h = (cyl(SCREW_CLEAR/2, Z0 - 1.0, Z1 + 1.0, 32, centre=(x, y))
             + cyl(SCREW_HEAD/2, Z0 - 1.0, Z0 + 3.20, 40, centre=(x, y)))
        pillars = p if pillars is None else pillars + p
        holes = h if holes is None else holes + h
    body += pillars
    body -= holes

    # --- cable exit at 6 o'clock, through the outer wall
    body -= box_lwh(-R_BODY - 2.0, -R_INNER + 2.0, -CABLE_W/2, CABLE_W/2,
                    Z_POCKET + 1.5, Z_POCKET + 1.5 + CABLE_H)

    # --- ventilation. A lithium cell in a closed PLA box wants a path for warm
    #     air: slots low and high so it convects when the clock is on a wall.
    vents = None
    for a in [50, 75, 100, 260, 285, 310]:
        for k in range(VENT_ROWS):
            z = Z_POCKET + 3.0 + k*(VENT_W + 2.4)
            if z + VENT_W > Z1 - 2.0: continue
            v = wedge(R_INNER - 2.0, R_BODY + 2.0, z, z + VENT_W,
                      a - VENT_L/2, a + VENT_L/2)
            vents = v if vents is None else vents + v
    if vents is not None:
        body -= vents
    return body


def build_shim(bat_w, pocket_d):
    """One side shim. Print TWO and put one either side of the battery.

    An earlier version was a full frame clipped to the pocket circle. The
    checker found it: where the frame's corner ran nearly tangent to the
    circle, the clip left slivers down to 0.03 mm. This shape cannot do that --
    its outer edge IS the circle, and it meets the straight ends at a steep
    angle, so nothing anywhere is thinner than SHIM_WALL.
    """
    h = min(SHIM_H, pocket_d - 2.0)
    r_out = R_INNER - 0.35
    y0 = bat_w/2 + SHIM_CLR
    hx = SHIM_HALF_X
    body = box_lwh(-hx, hx, y0, r_out + 5.0, 0.0, h) ^ cyl(r_out, -1.0, h + 1.0, SEG)

    # lighten it: three holes, each kept SHIM_WALL clear of every edge
    y_mid = (y0 + math.sqrt(max(r_out**2 - hx**2, 0.0))) / 2.0
    for cx in (-hx/2, 0.0, hx/2):
        body -= prism([(x + cx, y + y_mid)
                       for x, y in rounded_rect(hx/2 - SHIM_WALL, 9.0, 2.0)], -1.0, h + 1.0)
    return body


# =============================================================================
def load_sams_diffuser():
    m = trimesh.load('diffuser_in.stl', process=False)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    d = parts[0].copy()
    b = d.bounds
    d.apply_translation([-(b[0][0]+b[1][0])/2, -(b[0][1]+b[1][1])/2, 0])
    return to_manifold(d)


def build_diffuser_v3():
    """Sam's diffuser, with everything he asked for after test-fitting it.

    1. PRESS FIT. It was 46.000 in a 46.3516 pocket -- 0.70 mm of slop on
       diameter. Grown to 46.4016 for a light interference.
    2. ONE LAYER over the LEDs. Each cell's aperture is a 0.20 mm skin, which
       at 0.20 mm layers is a single bottom layer. It prints face DOWN, so that
       layer goes straight onto the plate -- no bridging.
    3. RADIAL TICKS, not an arc. "The line needs to be perpendicular to the
       screen, like the lines are." A tick pointing at the centre reads as a
       mark on a clock face; an arc lying along the circle reads as a blob.
       2.00 mm of white PLA either side of it stays opaque, so light comes out
       of the tick and nowhere else -- the Echo look.
    4. THE HOURS, debossed on the face inboard of the ticks.
    5. COLLAR + COLLAR_EXTEND, to reach further in and hold the screen.

    The band that carries all of this is rebuilt rather than patched -- see the
    v5b block in params.py. Sam's mesh is kept only inside BAND_CUT_R, where it
    is perfect; outboard of that it carries 183 non-manifold edges and every
    union through them made the result worse.
    """
    # --- 1. Sam's collar and inner face, which are defect-free ---------------
    d = load_sams_diffuser() ^ cyl(BAND_CUT_R, -1.0, 12.0, SEG)

    # --- 2. the band, rebuilt clean -----------------------------------------
    # the face: 2.00 mm everywhere, out to the press-fit diameter. It starts
    # 0.50 mm inside the cut so the seam is buried in solid material.
    d += tube(BAND_FACE_RI, DIFF_OUTER_NEW, 0.0, FACE_T, SEG)
    # the two annular ribs -- continuous now, where Sam's were notched at each
    # wall. The outer one is also the press fit.
    d += tube(RIB_I_RI, RIB_I_RO, 0.0, BAND_TOP, SEG)
    d += tube(RIB_O_RI, DIFF_OUTER_NEW, 0.0, BAND_TOP, SEG)
    # 24 cell walls, one per LED, ends buried 0.4/0.6 mm into the ribs
    rm = (CELL_WALL_RI + CELL_WALL_RO) / 2
    for k in range(CELL_N):
        a = CELL_WALL_A0 + k * (360.0 / CELL_N)
        cx, cy = rm * math.cos(math.radians(a)), rm * math.sin(math.radians(a))
        d += prism(rot_rect(cx, cy, CELL_WALL_RO - CELL_WALL_RI, CELL_WALL_T, a),
                   0.0, BAND_TOP)

    # --- 3. one radial tick per cell, thinned to a single layer --------------
    ticks = None
    for i in range(CELL_N):
        # cells sit BETWEEN the walls, which are at CELL_WALL_A0 + k*pitch
        a = CELL_WALL_A0 + (i + 0.5) * (360.0 / CELL_N)
        cx = (TICK_RI + TICK_RO) / 2 * math.cos(math.radians(a))
        cy = (TICK_RI + TICK_RO) / 2 * math.sin(math.radians(a))
        t = prism(rot_rect(cx, cy, TICK_RO - TICK_RI, TICK_W, a, TICK_END_R),
                  DIFF_MEM_T, BAND_TOP + 0.60)
        ticks = t if ticks is None else ticks + t
    d -= ticks

    # --- 4. the hours, written on the face ----------------------------------
    marks = None
    for h in range(12):
        a = 90.0 - h * 30.0                       # 12 at the top, clockwise
        major = (h % 3 == 0)
        ri, ro = (MARK_RI_MAJ, MARK_RO_MAJ) if major else (MARK_RI, MARK_RO)
        w = MARK_W_MAJ if major else MARK_W
        key = int(round(a)) % 360
        if key in NUMERALS:
            cx = NUM_R * math.cos(math.radians(a))
            cy = NUM_R * math.sin(math.radians(a))
            # upright, not rotated with the dial -- it is read from across a room
            m = text_prism(NUMERALS[key], NUM_H, (cx, cy), -0.10, NUM_DEPTH)
        else:
            cx = (ri + ro) / 2 * math.cos(math.radians(a))
            cy = (ri + ro) / 2 * math.sin(math.radians(a))
            m = prism(rot_rect(cx, cy, ro - ri, w, a, w / 2 * 0.9), -0.10, MARK_DEPTH)
        marks = m if marks is None else marks + m
    d -= marks

    # --- 5. a taller collar --------------------------------------------------
    if COLLAR_EXTEND > 0:
        # start 1 mm DOWN inside the collar rather than butting onto its top
        # face: two coincident faces there survive the float32 round trip as a
        # self-intersection. The overlap is entirely inside existing material.
        d += tube(COLLAR_EXT_RI, COLLAR_EXT_RO,
                  DIFF_COLLAR_H - 1.0, DIFF_COLLAR_H + COLLAR_EXTEND, SEG)
    return d

# =============================================================================
def assemble_base(base, deck):
    bay_solid, bay_void = usbc_bay()
    out = base + deck + tab_slot_walls()
    out = out - screw_pilots() - keeper_pilots() - bay_void
    out = out + bay_solid + board_beam()
    drop = seat_drop(SEAT_DROP)
    if drop is not None:
        out = out - drop
        print(f'  display seat dropped {SEAT_DROP:.2f} mm '
              f'(now z={Z_SEAT - SEAT_DROP:.2f}) -- diffuser needs no reprint')
    return out


if __name__ == '__main__':
    print(summary())
    print('building...')
    base = load_sams_base()
    deck = build_deck()
    parts = [
        (assemble_base(base, deck),            'mini-round-clock-base-v2',           True),
        (build_rear_housing(POCKET_SLIM),      'mini-round-clock-rearhousing-slim',  True),
        (build_rear_housing(POCKET_BATTERY),   'mini-round-clock-rearhousing-battery', True),
        (build_shim(BAT_W, POCKET_BATTERY),    'mini-round-clock-battery-shim-x2',   True),
        (build_keeper(),                       'mini-round-clock-board-keeper',      True),
        # Sam's diffuser carries 183 non-manifold edges, all of them in the LED
        # band. v5b rebuilds that band instead of unioning through it, so this
        # one IS held to strict: watertight, one body, like every other part.
        (build_diffuser_v3(),              'mini-round-clock-diffuser-v3',  True),
    ]
    for man, fn, strict in parts:
        t = csg.finalise(man, fn, strict=strict)
        t.export(fn + '.stl')
        t.export(fn + '.3mf')
    print('done')
