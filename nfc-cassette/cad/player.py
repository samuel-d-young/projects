"""The player: a base that carries the electronics and a top slab with the
cassette bay. Four M3 screws from the top, in the strips front and back of
the bay, hold the two together.

The stack, table up (all from params.derive):
    floor
    cavity: Dupont tails hanging off the PN532's header, the D1 mini
    PN532 module, component side DOWN, held between four corner posts and
        the slab's underside - no pegs, no screws, nothing depends on the
        module's hole positions
    bay floor (thin: it is the only thing between antenna and card)
    the cassette, sitting in the bay, standing 2 mm proud for grip

Both parts print flat with the open/recessed side up. No supports.
"""
from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Pos, Rot, fillet

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)


def _rounded_box(l: float, w: float, h: float, r: float):
    b = Box(l, w, h, align=C)
    return fillet(b.edges().filter_by(Axis.Z), r)


def _hole_y(x: float, z: float, d: float, length: float):
    """A cylinder along Y, centred at (x, ?, z): for cutting through front/back walls."""
    return Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(d / 2, length, align=CC)


def _hole_x(y: float, z: float, d: float, length: float):
    return Pos(0, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, length, align=CC)


def _corner_posts(cx: float, cy: float, pl: float, pw: float, D: dict, top_z: float, lip_top_z: float):
    """Four posts under a PCB's corners plus an L-shaped lip outside each corner.

    The PCB (pl x pw, centred at cx, cy) rests on the posts with `ledge` mm of
    each corner supported; the lips stop it sliding. Drop-in from above.
    """
    parts = []
    post = D["ledge"] + D["pcb_clr"] + D["lip_t"]           # post square, corner sits on it
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            py = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            parts.append(Pos(px, py, D["floor"]) * Box(post, post, top_z - D["floor"], align=C))
            # lips: one along X at the outer Y face, one along Y at the outer X face
            lx = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            ly = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            parts.append(Pos(lx, cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] - post / 2), D["floor"])
                         * Box(D["lip_t"], post, lip_top_z - D["floor"], align=C))
            parts.append(Pos(cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] - post / 2), ly, D["floor"])
                         * Box(post, D["lip_t"], lip_top_z - D["floor"], align=C))
    return parts


def build_base(D: dict):
    base = _rounded_box(D["L"], D["W"], D["base_h"], D["corner_r"])
    cavity = Pos(0, 0, D["floor"]) * _rounded_box(D["cavity_l"], D["cavity_w"], D["base_h"], D["cavity_r"])
    base = base - cavity

    # screw posts in the four corners, pilot-drilled from the top
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * D["screw_x"], sy * D["screw_y"]
            base = base + Pos(x, y, D["floor"] - 0.01) * Cylinder(D["post_d"] / 2, D["base_h"] - D["floor"] + 0.01, align=C)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * D["screw_x"], sy * D["screw_y"]
            base = base - Pos(x, y, D["base_h"] - D["pilot_depth"]) * Cylinder(D["screw_pilot"] / 2, D["pilot_depth"] + 0.1, align=C)

    # PN532 module: corner posts up to the PCB underside, lips up to the slab
    for p in _corner_posts(D["pn532_cx"], D["pn532_cy"], D["pn532_l"], D["pn532_w"], D,
                           top_z=D["pcb_bottom_z"], lip_top_z=D["base_h"]):
        base = base + p
    # D1 mini: standoffs to the board underside, lips a few mm up its edge
    for p in _corner_posts(D["d1_cx"], D["d1_cy"], D["d1_w"], D["d1_l"], D,
                           top_z=D["d1_board_z"], lip_top_z=D["d1_board_z"] + D["d1_t"] + 3.0):
        base = base + p
    # buzzer locating ring on the floor
    ring = Pos(D["buzzer_cx"], D["buzzer_cy"], D["floor"]) * (
        Cylinder(D["buzzer_d"] / 2 + 0.3 + 1.2, 3.0, align=C) - Cylinder(D["buzzer_d"] / 2 + 0.3, 3.2, align=C))
    base = base + ring

    # openings: USB in the back wall, LED in the front wall, buzzer sound hole in the left wall
    base = base - Pos(D["d1_cx"], D["W"] / 2, D["usb_cz"]) * Box(D["usb_w"], D["wall"] * 3, D["usb_h"], align=CC)
    base = base - Pos(D["led_cx"], -D["W"] / 2, D["led_cz"]) * Rot(90, 0, 0) * Cylinder(
        (D["led_d"] + 2 * D["led_clr"]) / 2, D["wall"] * 3, align=CC)
    base = base - Pos(-D["L"] / 2, D["buzzer_cy"], D["buzzer_hole_z"]) * Rot(0, 90, 0) * Cylinder(
        2.0, D["wall"] * 3, align=CC)

    # cosmetic transport buttons on the front face
    for i in range(5):
        x = D["buttons_x0"] + i * D["buttons_pitch"]
        base = base + Pos(x, -D["W"] / 2 - 0.6, D["buttons_cz"]) * Box(9.0, 1.2 + 0.6, 6.0, align=CC)
    return base


def build_top(D: dict):
    top = Pos(0, 0, D["base_h"]) * _rounded_box(D["L"], D["W"], D["slab_t"], D["corner_r"])
    bay = Pos(0, D["bay_cy"], D["bay_floor_z"]) * _rounded_box(D["bay_l"], D["bay_w"], D["bay_depth"] + 1.0, D["bay_r"])
    top = top - bay
    # finger notches at both ends of the bay
    for sx in (-1, 1):
        top = top - Pos(sx * D["notch_cx"], D["bay_cy"], D["bay_floor_z"]) * Cylinder(
            D["notch_d"] / 2, D["bay_depth"] + 1.0, align=C)
    # screw holes with counterbores, from the top
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * D["screw_x"], sy * D["screw_y"]
            top = top - Pos(x, y, D["base_h"] - 0.1) * Cylinder(D["screw_hole"] / 2, D["slab_t"] + 0.2, align=C)
            top = top - Pos(x, y, D["H"] - D["screw_head_h"]) * Cylinder(D["screw_head_d"] / 2, D["screw_head_h"] + 0.1, align=C)
    return top


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_base(D), "player_base", "open side up", note="electronics drop in from above")
    emit(build_top(D), "player_top", "bay side up", note="4 x M3 x 10 from the top")
    write_manifest()
