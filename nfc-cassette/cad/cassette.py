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


def build_lid(D: dict):
    lid = _rounded_box(D["lid_l"], D["lid_w"], D["lid_t"], D["tray_inner_r"] + D["lid_seat"])
    # label strip across the top third, like a real tape's label
    label = Pos(0, D["lid_w"] / 2 - 4.0 - 12.0, D["lid_t"] - D["label_recess"]) * Box(
        D["lid_l"] - 12.0, 24.0, D["label_recess"] + 0.2, align=C)
    lid = lid - label
    # two reel dimples
    for x in (-21.0, 21.0):
        lid = lid - Pos(x, -D["lid_w"] / 2 + 15.0, D["lid_t"] - D["label_recess"]) * Cylinder(
            8.0, D["label_recess"] + 0.2, align=C)
    return lid


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_tray(D), "cassette_tray", "open side up", note="glue the lid in")
    emit(build_lid(D), "cassette_lid", "dimples up")
    write_manifest()
