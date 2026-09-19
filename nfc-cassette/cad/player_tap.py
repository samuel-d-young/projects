"""The tap player: same face, no slot. Cartridges are tapped on the top.

What changed and why it is a different part rather than an edit. The slot
player's whole middle is built around a 13 mm vertical slot: a solid block from
the floor plate to the roof, the plate itself, the detent, and a PN532 standing
UPRIGHT behind the slot so its antenna faces the card edge-on. Tapping needs
none of that and wants the opposite - the module lying FLAT, antenna up, as
close under the top surface as the wall allows.

The body stays about the same size anyway, which is the surprise. The slot was
never what set it: the face has to carry a 38 mm dial, which is what makes the
body ~48 tall, and the ESP32 plus the face's furniture is what makes it ~127
long. Take the slot out and the box barely moves. What moves is the inside.

The light matters more here than it did. A slot gave a detent, a thunk, and a
tape standing proud; tapping gives none of those, so the dial going amber and
then white is the only way to know anything happened. That is why the dial
stays on the FRONT, where it is visible across a room, rather than under the
hand that is doing the tapping.

Body coordinates, as for the slot player: origin at the centre of the
footprint, Z up from the table, -Y is the face.
"""
from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Pos, Rot, chamfer

import math

from player_slot import (_front_cosmetics, _posts_and_lips, _rounded_box, _sector,
                         break_outer_edges)

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)


def _mark_arcs(D: dict):
    """The contactless mark's arcs, innermost first."""
    return D["t_mark_r"]


def build_fascia(D: dict):
    """The front face, as its own part.

    It carries everything that reads as the machine - the dial and its wedges,
    the transport keys, the knob recesses, the counter window, the REC lamp and
    the LED hole - and none of the structure. Printed face down it is the one
    surface nobody has to apologise for, and swapping it changes the whole look
    without touching a screw on the outside.

    Two steps, and which way it goes in is the whole design. The plate fills
    the opening flush with the front; the flange behind it is wider all round
    and rides in a channel cut into the inside of the front wall. The channel
    is closed on the left, the right and the roof and open at the BOTTOM, so
    the face slides up into it from underneath and the lid, screwed on after,
    is what holds it there. Four screws to change a face, and nothing on the
    outside to see.

    The step between plate and flange is chamfered, which does two jobs: it is
    the lead-in that finds the channel, and printing face down it turns a
    1.5 mm unsupported ledge into a 45 degree wall.
    """
    W, wall = D["s_W"], D["wall"]
    clr, reb = D["t_face_clr"], D["t_face_rebate"]
    y0 = -W / 2
    pz0, pz1 = D["t_ap_z0"], D["t_ap_z1"] - clr
    plate = Pos(0, y0 + (wall - reb) / 2, (pz0 + pz1) / 2) * Box(
        D["t_ap_l"] - 2 * clr, wall - reb, pz1 - pz0, align=CC)
    fz0, fz1 = D["t_face_z0"], D["t_face_z1"] - clr
    flange = Pos(0, y0 + wall - reb / 2, (fz0 + fz1) / 2) * Box(
        D["t_face_l"] - 2 * clr, reb, fz1 - fz0, align=CC)
    flange = chamfer(flange.edges().group_by(Axis.Y)[0], D["t_face_chamfer"])
    face = plate + flange
    face = face - Pos(D["s_led_cx"], y0, D["s_led_cz"]) * Rot(90, 0, 0) * Cylinder(
        (D["led_d"] + 2 * D["led_clr"]) / 2, wall * 3, align=CC)
    return _front_cosmetics(face, D)


def build_mark_arc(D: dict, i: int):
    """One arc of the contactless mark, as an insert for its recess."""
    a0, a1 = D["t_mark_r"][i]
    clr = D["t_mark_clr"]
    da = clr / max(a1, 1e-6)
    return _sector(a0 + clr, a1 - clr, D["t_mark_a0"] + da, D["t_mark_a1"] - da,
                   D["t_mark_t"])


def build_body(D: dict):
    """The shell, the tap pad, and the module's cradle under it."""
    L, W, H, wall = D["s_L"], D["s_W"], D["s_H"], D["wall"]
    floor = D["s_lid_t"]
    body = Pos(0, 0, floor) * _rounded_box(L, W, H - floor, D["corner_r"])
    cavity = Pos(0, 0, floor - 0.01) * _rounded_box(
        D["s_cavity_l"], D["s_cavity_w"], D["t_roof_z"] - floor + 0.01, D["s_cavity_r"])
    body = body - cavity
    # the skirt: the outer wall carries on down past the lid, as before
    skirt = _rounded_box(L, W, floor, D["corner_r"]) - Pos(0, 0, -0.01) * _rounded_box(
        D["s_pocket_l"], D["s_pocket_w"], floor + 0.02, D["s_pocket_r"])
    body = body + skirt

    # ---- the contactless mark, recessed into the top. No dish: a dish says
    # "put it in" and these are tapped. The mark is centred on the module, so
    # the symbol is literally over the antenna rather than near it, and each
    # arc is a recess that takes its own insert - one colour each, or paint
    # them if the printer can.
    for a0, a1 in _mark_arcs(D):
        body = body - Pos(D["t_pn_cx"], D["t_pn_cy"], H - D["t_mark_t"]) * _sector(
            a0, a1, D["t_mark_a0"], D["t_mark_a1"], D["t_mark_t"] * 2 + 0.2)

    # ---- the front opening, and the channel the fascia slides up into. The
    # body keeps t_face_inset of itself each side as a frame, and t_face_band
    # above the opening - that thin strip is the whole of what stops the face
    # tipping out at the top, which is why params sizes it from the dial and
    # the sweep guards it. Both cuts run down to z = 0: the channel has to be
    # open at the bottom or the face can never be got in or out.
    reb = D["t_face_rebate"]
    body = body - Pos(0, -W / 2, D["t_ap_cz"]) * Box(
        D["t_ap_l"], wall * 3, D["t_ap_h"], align=CC)
    body = body - Pos(0, -W / 2 + wall - reb / 2 + 0.1, D["t_face_z1"] / 2) * Box(
        D["t_face_l"], reb + 0.2, D["t_face_z1"], align=CC)

    # ---- the module, FLAT and antenna up, on two rails it SLIDES IN ON.
    # It cannot be posted up from the lid: the ESP32 is under it and there is
    # nowhere to put the posts. It cannot be lowered onto posts either - that
    # is how the first version did it, and the fit check pointed out that the
    # only way in would have been through a closed roof. So it slides in
    # through the front opening, sits on two ledges, and the fascia closes the
    # door behind it. Gravity does the rest: the ledges are under the board.
    hx = D["pn532_l"] / 2 + D["t_pn_clr"]
    y_back = D["t_pn_cy"] + D["pn532_w"] / 2 + D["t_pn_clr"]
    y_front = D["t_inner_y0"]
    z0 = D["t_pn_board_z"] - D["t_pn_rail_t"]
    for sx in (-1, 1):
        # the upright of the rail, from under the board up to the roof
        body = body + Pos(D["t_pn_cx"] + sx * (hx + D["t_pn_rail_t"] / 2), (y_front + y_back) / 2, z0) * Box(
            D["t_pn_rail_t"], y_back - y_front, D["t_roof_z"] - z0, align=C)
        # and the ledge it sits on, reaching in over the board's edge strip
        body = body + Pos(D["t_pn_cx"] + sx * (hx - D["t_pn_ledge"] / 2), (y_front + y_back) / 2, z0) * Box(
            D["t_pn_ledge"], y_back - y_front, D["t_pn_rail_t"], align=C)
        # ...and a second ledge over the top, which turns two rails into a
        # slot. Without it the board rests on the ledges and has 1.95 mm of
        # daylight to the roof, and that daylight IS the read distance: the
        # same tap reads differently depending on how the board happened to
        # settle. The upper ledge reaches in less than the lower one so it
        # stays on the board's edge margin and off the antenna coil.
        body = body + Pos(D["t_pn_cx"] + sx * (hx - D["t_pn_top_ledge"] / 2), (y_front + y_back) / 2,
                          D["t_pn_slot_z1"]) * Box(
            D["t_pn_top_ledge"], y_back - y_front, D["t_pn_rail_t"], align=C)
    # a stop at the back so it cannot be pushed past the mark
    body = body + Pos(D["t_pn_cx"], y_back + D["t_pn_rail_t"] / 2, z0) * Box(
        2 * (hx + D["t_pn_rail_t"]), D["t_pn_rail_t"], D["t_roof_z"] - z0, align=C)

    # ---- the VU ring's cradle on the front wall, unchanged from the slot
    # player: two vertical ribs, a stop across the top, posts on the lid.
    cx, cz = D["k_vu_c"]
    ry = -W / 2 + wall + D["t_ring_dy"] + D["s_ring_depth"] / 2
    rx = D["s_ring_rib_x"]
    for sx in (-1, 1):
        body = body + Pos(cx + sx * rx, ry, cz) * Box(
            D["s_ring_rib"], D["s_ring_depth"], D["s_ring_od"] + 8.0, align=CC)
    body = body + Pos(cx, ry, cz + D["s_ring_od"] / 2 + D["s_ring_clr"] + 1.0) * Box(
        2 * rx, D["s_ring_depth"], 2.0, align=CC)
    # and a stop behind it. The ribs and the lid posts locate the ring in X and
    # Z and leave it 64 mm of cavity to fall back into - it was held by nothing
    # but the fascia in front of it. These catch its back face, so the ring is
    # trapped between the stop and the face and cannot rock.
    ry_back = -W / 2 + wall + D["t_ring_dy"] + D["s_ring_depth"]
    for sx in (-1, 1):
        body = body + Pos(cx + sx * (rx - D["s_ring_stop"] / 2), ry_back + 1.0, cz) * Box(
            D["s_ring_stop"], 2.0, D["s_ring_stop_h"], align=CC)

    # ---- screw posts from the roof down to the lid
    for (x, y) in D["t_posts"]:
        body = body + Pos(x, y, floor) * Cylinder(
            D["post_d"] / 2, D["t_roof_z"] - floor + 0.5, align=C)
        body = body - Pos(x, y, floor - 0.1) * Cylinder(
            D["screw_pilot"] / 2, D["s_pilot_depth"] + 0.1, align=C)

    # ---- openings: USB out the left wall, the front LED through the face
    body = body - Pos(-L / 2, D["s_brd_cy"], D["s_usb_cz"]) * Box(
        wall * 3, D["esp_usb_w"], D["esp_usb_h"], align=CC)
    for dy in (-3.0, 0.0, 3.0):
        body = body - Pos(L / 2, D["s_buzzer_cy"] + dy, 6.0) * Rot(0, 90, 0) * Cylinder(
            1.0, wall * 3, align=CC)
    # break the outline top and bottom, last, so it catches every edge the
    # features above have left on it
    return break_outer_edges(body, L, W, D["corner_r"], D["edge_break"], 0.0, H)


def build_lid(D: dict):
    """The bottom plate: the same recessed lid, carrying the ESP32 and the
    ring's two posts. The module is not on the lid any more - it hangs under the
    top - so the lid is emptier than the slot player's."""
    floor = D["s_lid_t"]
    lid = _rounded_box(D["s_lid_l"], D["s_lid_w"], floor, D["s_lid_r"])
    for (x, y) in D["t_posts"]:
        lid = lid - Pos(x, y, -0.1) * Cylinder(D["screw_hole"] / 2, floor + 0.2, align=C)
        lid = lid - Pos(x, y, -0.1) * Cylinder(
            D["screw_head_d"] / 2, D["screw_head_h"] + 0.1, align=C)
    for p in _posts_and_lips(D["s_brd_cx"], D["s_brd_cy"], D["esp_l"], D["esp_w"], D,
                             top_z=D["s_brd_board_z"],
                             lip_top_z=D["s_brd_board_z"] + D["esp_t"] + 3.0, z0=floor):
        lid = lid + p
    # the zip-tie stations, as on the slot player
    sl, sw = D["s_tie_slot_l"], D["s_tie_slot_w"]
    yf, yb = D["s_tie_y_front"], D["s_tie_y_back"]
    for x in D["s_tie_x"]:
        for y in (yf, yb):
            lid = lid - Pos(x, y, -0.1) * Box(sl, sw, floor + 0.2, align=C)
        lid = lid - Pos(x, (yf + yb) / 2, -0.1) * Box(
            sl, yb - yf, D["s_tie_groove_d"] + 0.1, align=C)
    # the two posts the ring stands on
    cx, cz = D["k_vu_c"]
    py0, py1 = D["s_ring_y0"] - 0.2, D["s_ring_y1"] + 0.2
    for sx in (-1, 1):
        lid = lid + Pos(cx + sx * D["s_ring_post_dx"], (py0 + py1) / 2, floor) * Box(
            D["s_ring_post_w"], py1 - py0, D["s_ring_post_top"] - floor, align=C)
    # buzzer locating ring
    lid = lid + Pos(D["s_buzzer_cx"], D["s_buzzer_cy"], floor) * (
        Cylinder(D["buzzer_d"] / 2 + 0.3 + 1.2, 3.0, align=C)
        - Cylinder(D["buzzer_d"] / 2 + 0.3, 3.2, align=C))
    return break_outer_edges(lid, D["s_lid_l"], D["s_lid_w"], D["s_lid_r"],
                             D["edge_break"], 0.0, floor)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_body(D), "tap_body", "upside down, top face on the bed",
         note="tap pad on the top; PN532 flat under it, antenna up")
    emit(build_fascia(D), "tap_fascia", "face down",
         note="the front face; print in whatever colours you like and swap at will")
    for i in range(len(D["t_mark_r"])):
        emit(build_mark_arc(D, i), f"tap_mark_{i + 1}", "flat",
             note="arc %d of the contactless mark; glue into its recess" % (i + 1))
    emit(build_lid(D), "tap_lid", "outside face down",
         note=f"4 x M3 x {D['screw_len']:.0f} pan head from below; ESP32 and the ring's posts")
    write_manifest()
