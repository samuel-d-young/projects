"""The cassette: a tray that holds one NTAG215 PVC card, and a flat lid.

Two parts because a one-piece shell would need a 55 mm bridge over the card
pocket. Both print flat, open side up, no supports. The lid drops into a
rebate in the tray and is glued (kids). The lid has a recessed label strip
across the top like a real tape (about 86 x 24 mm, 0.5 mm deep, so a vinyl
sticker sits flush) and two shallow "reel" dimples below it so the thing
reads as a cassette from across the room.

Tray coordinates: origin at the centre of the tray's footprint, Z up from
the table. The card lies on the floor inside a frame of low ribs.
"""
from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Pos, fillet

C = (Align.CENTER, Align.CENTER, Align.MIN)


def _rounded_box(l: float, w: float, h: float, r: float):
    b = Box(l, w, h, align=C)
    return fillet(b.edges().filter_by(Axis.Z), r)


def build_tray(D: dict):
    outer = _rounded_box(D["cassette_l"], D["cassette_w"], D["tray_h"], D["cassette_corner_r"])
    inner = Pos(0, 0, D["shell_floor"]) * _rounded_box(
        D["tray_inner_l"], D["tray_inner_w"], D["tray_h"], D["tray_inner_r"])
    seat = Pos(0, 0, D["lid_bottom_z"]) * _rounded_box(
        D["seat_l"], D["seat_w"], D["lid_t"] + 1.0, D["tray_inner_r"] + D["lid_seat"])
    tray = outer - inner - seat
    # ribs framing the card: a low rectangular ring around the card pocket
    ring_o = Box(D["card_pocket_l"] + 2 * 1.6, D["card_pocket_w"] + 2 * 1.6, D["rib_h"], align=C)
    ring_i = Box(D["card_pocket_l"], D["card_pocket_w"], D["rib_h"] + 0.2, align=C)
    ribs = Pos(0, 0, D["shell_floor"]) * (ring_o - ring_i)
    return tray + ribs


def _face_seats(D: dict):
    """The three recesses in the lid's face, as solids to subtract. Each one is
    also the shape of the insert that fills it, which is the point: one source
    for the hole and the thing that goes in it."""
    t, z = D["cass_insert_t"], D["lid_t"] - D["cass_insert_t"]
    seats = {}
    seats["label"] = Pos(0, D["cass_label_cz"], z) * Box(
        D["cass_label_l"], D["cass_label_h"], t + 0.2, align=C)
    for sx in (-1, 1):
        seats[f"hub{sx}"] = Pos(sx * D["cass_hub_dx"], D["cass_hub_cy"], z) * Cylinder(
            D["cass_hub_r"], t + 0.2, align=C)
    seats["window"] = Pos(0, D["cass_hub_cy"], z) * Box(
        D["cass_window_l"], D["cass_window_h"], t + 0.2, align=C)
    return seats


def build_lid(D: dict):
    """The lid, with its face hollowed for the inserts. Printed on its own it is
    a two-tone tape already - the recesses read as shadow - and with the inserts
    glued in it is three or four colours off any printer, one extruder or five."""
    lid = _rounded_box(D["lid_l"], D["lid_w"], D["lid_t"], D["tray_inner_r"] + D["lid_seat"])
    for seat in _face_seats(D).values():
        lid = lid - seat
    return lid


def build_label(D: dict):
    t, clr = D["cass_insert_t"], D["cass_insert_clr"]
    return Box(D["cass_label_l"] - 2 * clr, D["cass_label_h"] - 2 * clr, t, align=C)


def build_window(D: dict):
    t, clr = D["cass_insert_t"], D["cass_insert_clr"]
    return Box(D["cass_window_l"] - 2 * clr, D["cass_window_h"] - 2 * clr, t, align=C)


def build_hub(D: dict):
    """One reel hub: a disc with a bore and the teeth a real cassette drives on.
    Two per cassette, and the two are identical, so it is printed twice."""
    import math
    t, clr = D["cass_insert_t"], D["cass_insert_clr"]
    hub = Cylinder(D["cass_hub_r"] - clr, t, align=C)
    hub = hub - Cylinder(D["cass_hub_bore"] / 2, t + 0.2, align=C)
    n = int(D["cass_hub_teeth"])
    tooth_w = D["cass_hub_bore"] * 0.45
    # the tooth centres sit ON the bore circle, not tangent to it. Tangent was
    # the obvious placement and it exported a mesh that was not watertight:
    # two surfaces meeting at a line have no thickness to mesh. Overlapping
    # them by half a tooth is the difference between a scallop and a crack.
    for i in range(n):
        a = 2 * math.pi * i / n
        r = D["cass_hub_bore"] / 2
        hub = hub - Pos(r * math.cos(a), r * math.sin(a), -0.1) * Cylinder(
            tooth_w / 2, t + 0.2, align=C)
    return hub


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_tray(D), "cassette_tray", "open side up", note="glue the lid in")
    emit(build_lid(D), "cassette_lid", "face up", note="the three recesses take the inserts")
    emit(build_label(D), "cassette_label", "flat", note="SECOND COLOUR; glue into the label recess")
    emit(build_window(D), "cassette_window", "flat", note="THIRD COLOUR (white reads as tape); between the hubs")
    emit(build_hub(D), "cassette_hub", "flat", note="FOURTH COLOUR; print TWO, one per reel")
    write_manifest()
