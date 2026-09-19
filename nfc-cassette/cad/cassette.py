"""The cassette: a tray that holds one NTAG215 PVC card, and a flat lid.

Two parts because a one-piece shell would need a 55 mm bridge over the card
pocket. Both print flat, open side up, no supports. The lid drops into a
rebate in the tray and is glued (kids). The lid has a recessed label strip
across its face for a printed sticker, which is where all the detail lives:
artwork per film costs nothing, a moulded hub does not.

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
    """The lid: a flat plate with one shallow recess for a printed sticker.

    It carried a moulded label strip, a tape window and two reel hubs. Artwork
    does all three better and costs nothing per cassette, so the face is plain
    and the recess is there to locate the sticker and to keep its edges below
    the surface where they cannot be picked at."""
    lid = _rounded_box(D["lid_l"], D["lid_w"], D["lid_t"], D["tray_inner_r"] + D["lid_seat"])
    sticker = Pos(0, 0, D["lid_t"] - D["cass_sticker_t"]) * _rounded_box(
        D["cass_sticker_l"], D["cass_sticker_w"], D["cass_sticker_t"] + 0.2, D["cass_sticker_r"])
    return lid - sticker


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_tray(D), "cassette_tray", "open side up", note="glue the lid in")
    emit(build_lid(D), "cassette_lid", "face up",
         note="the recess takes a printed sticker; see BUILD-LOG for the artwork size")
    write_manifest()
