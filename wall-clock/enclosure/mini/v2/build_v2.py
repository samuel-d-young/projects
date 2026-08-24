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
from csg import box_lwh, cyl, cone, tube, wedge, prism, rounded_rect, to_manifold, to_trimesh
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
    deck -= box_lwh(x0, x1, -y1, y1, Z_DECK - 1.0, Z_BACK + 1.0)
    deck += box_lwh(x0, x0 + LEDGE_END, -y1, y1, Z_DECK, Z_LEDGE)
    deck += box_lwh(x1 - LEDGE_END, x1, -y1, y1, Z_DECK, Z_LEDGE)

    # wire port beside the S3's USB-C end, for the battery lead
    deck -= box_lwh(-30.0, -26.0, -8.0, 8.0, Z_DECK - 1.0, Z_BACK + 1.0)

    # four corner posts above the deck so the board cannot tip or slide
    posts = None
    for sx, sy in [(1,1), (1,-1), (-1,1), (-1,-1)]:
        px = (x1 - 3.0) if sx > 0 else (x0 + 3.0)
        py = sy * (y1 + 1.4)
        p = cyl(1.60, Z_BACK, Z_BACK + POST_H, 24, centre=(px, py))
        posts = p if posts is None else posts + p
    deck += posts

    return deck


def seat_drop(mm):
    """Lower the display seat, so the diffuser's collar stops fouling the module.

    Cut up to the top of the display pocket rather than stopping at the old seat
    plane: stopping there would leave a 0.3 mm down-facing ledge ringing the
    pocket, which is a needless overhang for no gain.
    """
    if mm <= 0:
        return None
    return cyl(R_DISP_POCKET, Z_SEAT - mm, Z_RECESS + 0.5, SEG)


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
def build_diffuser_fix(shorten):
    """Sam's diffuser with the screen-retainer collar shortened by `shorten` mm."""
    m = trimesh.load('diffuser_in.stl', process=False)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    d = parts[0].copy()
    b = d.bounds
    d.apply_translation([-(b[0][0]+b[1][0])/2, -(b[0][1]+b[1][1])/2, 0])
    man = to_manifold(d)
    top = d.bounds[1][2]
    return man - cyl(34.0, top - shorten, top + 5.0, SEG)

# =============================================================================
def assemble_base(base, deck):
    out = base + deck - screw_pilots()
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
        # derived from Sam's diffuser, which itself carries 387 non-manifold
        # edges at the baffle junctions; the trim halves that to 183 but cannot
        # invent topology that was never in the source. Not held to strict.
        (build_diffuser_fix(COLLAR_TRIM),  'mini-round-clock-diffuser-fix', False),
    ]
    for man, fn, strict in parts:
        t = csg.finalise(man, fn, strict=strict)
        t.export(fn + '.stl')
        t.export(fn + '.3mf')
    print('done')
