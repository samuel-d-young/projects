"""The Game Boy cartridge: a shell that carries one 25 mm NTAG215 disc, and a
back plate glued into it.

Why this format exists at all: the compact cassette is 100.4 x 63.8 and holds
an ID-1 card in a rib frame. A Game Boy cartridge is 57 x 65, and an ID-1 card
(85.60 x 53.98) does not fit inside it in any orientation. That is fine - only
the tag's serial number is ever used, so the tag's shape is free - but it means
this shell is built around a disc, not a card, and the two are not the same
part with different numbers.

The bevelled corner is the whole silhouette. Without it a Game Boy cartridge is
a rounded rectangle and reads as nothing; with it, it is unmistakable across a
room. It is also what tells a child which way up the thing goes, which matters
more here than it did on the cassette: these are TAPPED, not inserted, so
nothing mechanical stops them going on upside down.

Both parts print flat, open side up, no supports.

Shell coordinates: origin at the centre of the footprint, Z up from the table,
the label on +Z and the open back on... also +Z, because it prints open side up
and the label is a recess in the closed face beneath.
"""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, Cylinder, Plane, Polygon, Pos, chamfer,
                       extrude, fillet)

C = (Align.CENTER, Align.CENTER, Align.MIN)


def _bevelled(l: float, w: float, h: float, r: float, bevel: float, flip: bool = False):
    """The cartridge outline: a rounded rectangle with the top-left corner cut
    off at 45 degrees. Built as a polygon then filleted, because a chamfer on a
    filleted box has to be told which corner it is and a polygon just is.

    flip mirrors the cut corner across Y, for a part that is printed one way up
    and installed the other. See build_back.
    """
    hl, hw = l / 2, w / 2
    pts = [(-hl, -hw), (hl, -hw), (hl, hw), (-hl + bevel, hw), (-hl, hw - bevel)]
    if flip:
        # mirror in Y, then REVERSE, because mirroring alone reverses the
        # winding and extrude follows the face normal: the plate came out
        # below the sketch plane while the spigot stayed above it, and the
        # part was two disconnected solids with a gap between them. It
        # exported clean - two closed shells are still watertight, and the
        # volume still agreed - which is why _lib now counts bodies.
        pts = [(x, -y) for x, y in pts][::-1]
    body = extrude(Plane.XY * Polygon(*pts, align=None), h)
    return fillet(body.edges().filter_by(Axis.Z), r)


def _break_edges(solid, c: float):
    """Break the outline's top and bottom edges.

    The players get this by subtracting a tapered ring, because chamfer() could
    not survive the junctions on the tap body. Here it can: the cartridge is
    one clean bevelled prism, so the edges can just be picked and chamfered.
    Picking is by the bounding box - an edge is on the outline if it reaches
    the extreme in X or Y - which leaves the label recess and the tag pocket
    sharp, as they should be.
    """
    for z in (solid.bounding_box().min.Z, solid.bounding_box().max.Z):
        bb = solid.bounding_box()
        keep = []
        for e in solid.edges():
            eb = e.bounding_box()
            if not (abs(eb.min.Z - z) < 1e-6 and abs(eb.max.Z - z) < 1e-6):
                continue
            if (abs(eb.min.X - bb.min.X) < 0.02 or abs(eb.max.X - bb.max.X) < 0.02
                    or abs(eb.min.Y - bb.min.Y) < 0.02 or abs(eb.max.Y - bb.max.Y) < 0.02):
                keep.append(e)
        if keep:
            solid = chamfer(keep, c)
    return solid


def build_shell(D: dict):
    """The front of the cartridge: the bevelled shell, hollow behind, with the
    tag's pocket in the floor and a recess in the face for a printed label."""
    shell = _bevelled(D["cart_l"], D["cart_w"], D["cart_h"],
                      D["cart_corner_r"], D["cart_bevel"])
    # hollow it from the back, leaving cart_wall all round and under the face
    inner = _bevelled(D["cart_inner_l"], D["cart_inner_w"],
                      D["cart_cavity_h"] + D["cart_lid_t"] + 0.1,
                      max(D["cart_corner_r"] - D["cart_wall"], 0.5),
                      D["cart_bevel"])
    shell = shell - Pos(0, 0, D["cart_wall"]) * inner
    # ...and a rebate the back plate drops into, so it closes flush instead of
    # falling through a hole its own size
    seat = _bevelled(D["cart_inner_l"] + 2 * D["cart_seat"],
                     D["cart_inner_w"] + 2 * D["cart_seat"],
                     D["cart_lid_t"] + 0.2,
                     max(D["cart_corner_r"] - D["cart_wall"] + D["cart_seat"], 0.5),
                     D["cart_bevel"])
    shell = shell - Pos(0, 0, D["cart_h"] - D["cart_lid_t"]) * seat
    # The tag is located by a RING, not by a pocket. It was a pocket, and the
    # pocket did nothing: it was cut at exactly the z the cavity floor already
    # starts at, so it removed material that was already gone and left a 25 mm
    # disc loose in a 54 x 62 box. Cutting it any lower is not the fix either -
    # the floor is only cart_wall thick and the tag is most of that. Adding a
    # ring costs no floor and locates the disc properly.
    shell = shell + Pos(0, 0, D["cart_wall"]) * (
        Cylinder(D["cart_pocket_d"] / 2 + D["cart_tag_ring_t"],
                 D["cart_tag_ring_h"], align=C)
        - Cylinder(D["cart_pocket_d"] / 2, D["cart_tag_ring_h"] + 0.2, align=C))
    # the label recess, in the face, below the bevel
    st = Pos(0, -D["cart_bevel"] * 0.25, -0.1) * _bevelled(
        D["cart_sticker_l"], D["cart_sticker_w"], D["cart_sticker_t"] + 0.1,
        D["cart_sticker_r"], 0.5)
    return _break_edges(shell - st, D["cart_break"])


def build_back(D: dict):
    """The plate that closes the shell. Glued, like the cassette's lid.

    Built in its PRINT orientation, spigot up, which is not how it installs -
    it goes in rotated 180 degrees about X so the spigot reaches down onto the
    tag. That rotation also swings the bevelled corner across to the other
    side, so the outline here is mirrored to land the right way round once it
    is turned over. It did not matter while the plate was a flat prism,
    symmetrical top to bottom; the spigot is what made it handed, and a handed
    part that fits its seat only in the orientation it cannot be used in is a
    part that will be printed, tried, and thrown away.
    """
    back = _bevelled(D["cart_inner_l"] + 2 * D["cart_seat"] - 2 * D["cart_back_clr"],
                     D["cart_inner_w"] + 2 * D["cart_seat"] - 2 * D["cart_back_clr"],
                     D["cart_lid_t"],
                     max(D["cart_corner_r"] - D["cart_wall"] + D["cart_seat"] - D["cart_back_clr"], 0.4),
                     D["cart_bevel"], flip=True)
    # a spigot that holds the tag down on the floor. The ring stops the disc
    # sliding; without this it can still float most of the cavity's height,
    # and height is read distance.
    if D["cart_pressed"]:
        back = back + Pos(0, 0, D["cart_lid_t"]) * Cylinder(
            D["cart_pocket_d"] / 2 - 0.4, D["cart_tag_press_h"], align=C)
    return _break_edges(back, D["cart_break"])


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_shell(D), "cart_shell", "face down, open side up",
         note="the pocket takes a 25 mm NTAG215 disc; label recess in the face")
    emit(build_back(D), "cart_back", "flat, spigot UP",
         note="installs turned over - spigot down onto the tag; the outline is mirrored to suit")
    write_manifest()
