"""The vertical-slot player: the tape stands in a slot in the top, label to the
front, and comes out of the top. Samuel, 2026-09-15: "the cassette can go in
but also be taken out of the top rather than put into the side."

Two printed parts:
    slot_body   the shell, printed UPSIDE DOWN (top face on the bed): the
                slot is an open channel from the bed, the module pocket and
                the cavity open upward, the screw posts grow from the bed.
                The slot floor is a 13 mm bridge, nothing else overhangs.
    slot_lid    the bottom plate, printed outside face down: counterbores
                open at the bed, the D1 mini posts, buzzer ring and the
                module shelf stand up from it.

Inside: the PN532 stands vertically with its flat back against the wall
behind the slot (the antenna coil reads through its own PCB), held by two
side ribs, two keeper ribs hanging from the roof, and a shelf on the lid.
Everything on the module's component side - the DIP switch, the header,
the Dupont tails - faces the back. The D1 mini lies on the lid to the left,
USB out through the left wall. The buzzer sits under the slot floor on the
right with three sound holes through the front wall. LED and five cosmetic
transport buttons on the front face, below the slot.
"""
from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Pos, Rot, fillet

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)


def _rounded_box(l: float, w: float, h: float, r: float):
    b = Box(l, w, h, align=C)
    return fillet(b.edges().filter_by(Axis.Z), r)


def _posts_and_lips(cx, cy, pl, pw, D, top_z, lip_top_z, z0):
    """Corner posts under a PCB's corners plus L-shaped lips outside them (see player.py)."""
    parts = []
    post = D["ledge"] + D["pcb_clr"] + D["lip_t"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            py = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            parts.append(Pos(px, py, z0) * Box(post, post, top_z - z0, align=C))
            lx = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            ly = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            parts.append(Pos(lx, py, z0) * Box(D["lip_t"], post, lip_top_z - z0, align=C))
            parts.append(Pos(px, ly, z0) * Box(post, D["lip_t"], lip_top_z - z0, align=C))
    return parts


def build_body(D: dict):
    L, W, H, floor, wall = D["s_L"], D["s_W"], D["s_H"], D["floor"], D["wall"]
    body = Pos(0, 0, floor) * _rounded_box(L, W, H - floor, D["corner_r"])
    cavity = Pos(0, 0, floor - 0.01) * _rounded_box(D["s_cavity_l"], D["s_cavity_w"],
                                                     D["s_roof_z"] - floor + 0.01, D["s_cavity_r"])
    body = body - cavity

    # the slot block: solid from the slot-floor plate up to the roof, spanning the
    # slot plus an end wall each side and the module wall behind; then the slot itself
    blk_l = D["s_slot_l"] + 2 * D["s_end_wall"]
    blk_y0, blk_y1 = D["y_slot0"] - 0.5, D["y_pcb0"]           # overlaps the front wall a touch
    blk = Pos(0, (blk_y0 + blk_y1) / 2, D["s_plate_bot_z"]) * Box(blk_l, blk_y1 - blk_y0, D["s_roof_z"] - D["s_plate_bot_z"] + 0.5, align=C)
    body = body + blk
    slot = Pos(0, (D["y_slot0"] + D["y_slot1"]) / 2, D["s_plate_top_z"]) * _rounded_box(
        D["s_slot_l"], D["s_slot_w"], H - D["s_plate_top_z"] + 1.0, min(D["cassette_corner_r"] + D["s_slot_clr"], D["s_slot_w"] / 2 - 0.5))
    body = body - slot

    # module pocket: two full-height side ribs and two keepers hanging from the roof
    rib_len = D["s_rail_y1"] - D["s_rail_y0"]
    for sx in (-1, 1):
        body = body + Pos(sx * D["s_rail_x"], (D["s_rail_y0"] + D["s_rail_y1"]) / 2, floor) * Box(
            D["s_keeper"], rib_len, D["s_roof_z"] - floor + 0.5, align=C)
        body = body + Pos(sx * D["s_keeper_x"], D["s_keeper_y"], D["s_roof_z"] - 8.0) * Box(
            4.0, D["s_keeper"], 8.5, align=C)

    # screw posts from the roof down to the lid, pilot-drilled from below
    for (x, y) in D["s_posts"]:
        body = body + Pos(x, y, floor) * Cylinder(D["post_d"] / 2, D["s_roof_z"] - floor + 0.5, align=C)
        body = body - Pos(x, y, floor - 0.1) * Cylinder(D["screw_pilot"] / 2, D["s_pilot_depth"] + 0.1, align=C)

    # openings: USB through the left wall, LED and buzzer holes through the front wall
    body = body - Pos(-L / 2, D["s_d1_cy"], D["s_usb_cz"]) * Box(wall * 3, D["usb_w"], D["usb_h"], align=CC)
    body = body - Pos(D["s_led_cx"], -W / 2, D["s_led_cz"]) * Rot(90, 0, 0) * Cylinder(
        (D["led_d"] + 2 * D["led_clr"]) / 2, wall * 3, align=CC)
    for dy in (-3.0, 0.0, 3.0):
        body = body - Pos(L / 2, D["s_buzzer_cy"] + dy, 6.0) * Rot(0, 90, 0) * Cylinder(1.0, wall * 3, align=CC)

    # cosmetic transport buttons
    for i in range(5):
        x = D["s_buttons_x0"] + i * D["s_buttons_pitch"]
        body = body + Pos(x, -W / 2 - 0.6, D["s_buttons_cz"]) * Box(9.0, 1.8, 6.0, align=CC)
    return body


def build_lid(D: dict):
    L, W, floor = D["s_L"], D["s_W"], D["floor"]
    lid = _rounded_box(L, W, floor, D["corner_r"])
    for (x, y) in D["s_posts"]:
        lid = lid - Pos(x, y, -0.1) * Cylinder(D["screw_hole"] / 2, floor + 0.2, align=C)
        lid = lid - Pos(x, y, -0.1) * Cylinder(D["screw_head_d"] / 2, D["screw_head_h"] + 0.1, align=C)
    # shelf the PCB's bottom edge rests on, between the module wall and the keepers
    lid = lid + Pos(0, (D["y_pcb0"] + D["y_pcb1"]) / 2, floor) * Box(30.0, D["pn532_t"] + D["pcb_clr"], D["s_shelf_h"], align=C)
    # D1 mini posts + lips
    for p in _posts_and_lips(D["s_d1_cx"], D["s_d1_cy"], D["d1_l"], D["d1_w"], D,
                             top_z=D["s_d1_board_z"], lip_top_z=D["s_d1_board_z"] + D["d1_t"] + 3.0, z0=floor):
        lid = lid + p
    # buzzer locating ring
    lid = lid + Pos(D["s_buzzer_cx"], D["s_buzzer_cy"], floor) * (
        Cylinder(D["buzzer_d"] / 2 + 0.3 + 1.2, 3.0, align=C) - Cylinder(D["buzzer_d"] / 2 + 0.3, 3.2, align=C))
    return lid


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_body(D), "slot_body", "upside down, top face on the bed", note="slot floor bridges 13 mm")
    emit(build_lid(D), "slot_lid", "outside face down", note="4 x M3 x 10 pan head from below")
    write_manifest()
