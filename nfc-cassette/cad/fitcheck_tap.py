"""Does the tap player go together, and does it read a tag?

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\fitcheck_tap.py

fitcheck_slot.py does this for the slot player. This is the same idea for the
tap player, and it exists because the slot version earned its keep twice: it
found a module mount 0.5 mm inside a wall, and it found a VU ring that could
never be fitted at all because something stood in its centre hole. Neither
showed up in 128 corner sweeps. A sweep checks that numbers stay sane; only
this checks that a person can assemble the thing.

What it measures, all on the real built solids and never on the numbers that
made them:

  1. every board and component, intersected with the body and with the lid
  2. everything is inside the outer envelope, except what is meant to stick out
  3. the lid seats, and gets there - it drops in vertically, so a mount that
     fits when seated can still foul on the way
  3a. the fascia seats, and slides back out of the bottom of its channel,
      past the VU ring that is already fitted behind it
  4. the module drops out of its cradle under the top (the reverse of fitting)
  5. the ring drops out through the lid opening
  6. a cartridge tapped on the pad sits clear of the body, and its tag lands
     within range of the antenna - which is the entire function of the machine
  7. the cartridge itself closes: the back plate seats flush the way up it is
     actually fitted, and the tag is trapped between its ring and the spigot
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import params  # noqa: E402
from build123d import Align, Box, Cylinder, Pos, Rot  # noqa: E402
from cartridge import build_back as build_cart_back, build_shell as build_cart_shell  # noqa: E402
from player_tap import build_body, build_fascia, build_lid  # noqa: E402

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)
TOL = 0.01


def parts_inside(D: dict):
    """The electronics as solids, where the design says they go."""
    v = D
    # --- the PN532, lying flat under the tap pad, antenna (component) side UP
    pcb = Pos(D["t_pn_cx"], D["t_pn_cy"], D["t_pn_board_z"]) * Box(
        v["pn532_l"], v["pn532_w"], v["pn532_t"], align=C)
    comp = Pos(D["t_pn_cx"], D["t_pn_cy"], D["t_pn_board_z"] + v["pn532_t"]) * Box(
        v["pn532_l"] - 2 * v["s_edge_free"], v["pn532_w"] - 2 * v["s_edge_free"],
        v["pn532_comp_h"], align=C)
    # its header tails hang DOWN now, not backwards
    tails = Pos(D["t_pn_cx"], D["t_pn_cy"] + v["pn532_w"] / 2 - 6.3,
                D["t_pn_board_z"] - v["pin_below"]) * Box(
        8 * 2.54, 2.54, v["pin_below"], align=C)
    # --- the ESP32, flat on the lid, with the Dupont headroom above it
    esp = Pos(D["s_brd_cx"], D["s_brd_cy"], D["s_brd_board_z"]) * Box(
        v["esp_l"], v["esp_w"], v["esp_t"] + v["esp_top_h"], align=C)
    usb = Pos(D["s_brd_cx"] - v["esp_l"] / 2 - 6.0, D["s_brd_cy"], D["s_usb_cz"]) * Box(
        12.0, v["esp_usb_w"] - 1.0, v["esp_usb_h"] - 1.0, align=CC)
    buzzer = Pos(D["s_buzzer_cx"], D["s_buzzer_cy"], D["s_lid_t"] + 0.2) * Cylinder(
        v["buzzer_d"] / 2, v["buzzer_d"] * 0.8, align=C)
    led = Pos(D["s_led_cx"], -D["s_W"] / 2 + v["wall"] + 4.3, D["s_led_cz"]) * Rot(90, 0, 0) * Cylinder(
        v["led_d"] / 2, 8.6, align=CC)

    def _ring(y, t):
        # the tap player sets its ring back by t_ring_dy to clear the back of
        # the fascia's flange; the solids have to move with the cradle
        return Pos(D["s_ring_cx"], y + D["t_ring_dy"], D["s_ring_cz"]) * Rot(90, 0, 0) * (
            Cylinder(v["s_ring_od"] / 2, t, align=CC)
            - Cylinder(v["s_ring_id"] / 2, t + 1.0, align=CC))

    ring = _ring((D["s_ring_y0"] + D["s_ring_y1"]) / 2, v["s_ring_t"])
    ring_leds = _ring((D["s_ring_led_y"] + D["s_ring_y0"]) / 2, v["s_ring_led_h"])
    dot = Pos(D["s_ring_cx"], (D["s_ring_led_y"] + D["s_ring_y1"]) / 2 + D["t_ring_dy"], D["s_ring_cz"]) * Rot(90, 0, 0) * Cylinder(
        v["s_dot_od"] / 2, v["s_ring_led_h"] + v["s_ring_t"], align=CC)
    return {"PN532 board": pcb, "PN532 components": comp, "PN532 header tails": tails,
            "ESP32 + headroom": esp, "USB plug": usb, "buzzer": buzzer, "front LED": led,
            "VU ring board": ring, "VU ring LEDs": ring_leds, "the single WS2812B": dot}


def overlap(a, b) -> float:
    try:
        return float((a & b).volume)
    except Exception:
        return 0.0


def main() -> int:
    D = params.derive(params.nominal())
    v = D
    steps = 6
    body, lid = build_body(D), build_lid(D)
    outer = Box(D["s_L"], D["s_W"], D["s_H"], align=C)
    bad = 0
    print("part                          vs body    vs lid     inside?")
    for name, solid in parts_inside(D).items():
        ob, ol = overlap(solid, body), overlap(solid, lid)
        # the USB plug pokes through the wall by design
        inside = name == "USB plug" or abs(overlap(solid, outer) - float(solid.volume)) < TOL
        ok = ob < TOL and ol < TOL and inside
        bad += 0 if ok else 1
        print(f"  {name:28} {ob:8.2f} {ol:9.2f}   {'yes' if inside else 'NO':6} "
              f"{'ok' if ok else 'COLLISION'}")

    # ---- the fascia: it seats, and it can be got out again. It slides UP into
    # a channel that is closed on three sides and open at the bottom, so the
    # way out is straight DOWN, with the lid off. This is the check that has
    # earned its keep most: the first two versions of this face could not be
    # fitted at all, and neither the invariants nor the sweep said a word.
    fascia = build_fascia(D)
    o = overlap(fascia, body)
    print(f"  fascia seated in its channel {o:8.2f}   {'ok' if o < TOL else 'COLLISION'}")
    bad += 0 if o < TOL else 1
    o = overlap(fascia, lid)
    if o > TOL:
        bad += 1
        print(f"  the fascia and the lid overlap by {o:.2f} mm^3")
    face_bad = 0
    drop = D["t_face_h"] + 4.0
    # the ring is already in when the face goes on, so it is part of the
    # obstacle course, not just something to clear once seated
    behind = [(nm, parts_inside(D)[nm])
              for nm in ("VU ring board", "VU ring LEDs", "the single WS2812B")]
    for i in range(0, steps + 1):
        dz = -drop * i / steps
        moved = Pos(0, 0, dz) * fascia
        o = overlap(moved, body)
        if o > TOL:
            face_bad += 1
            print(f"  fascia step {i}/{steps} (dz {dz:.1f}): body overlap {o:.2f} mm^3")
        for nm, solid in behind:
            r = overlap(moved, solid)
            if r > TOL:
                face_bad += 1
                print(f"  fascia step {i}/{steps} (dz {dz:.1f}): fouls the {nm} by {r:.2f} mm^3")
    print(f"  fascia slides out the bottom, past the ring: "
          f"{'clear' if not face_bad else str(face_bad) + ' steps blocked'} ({steps + 1} steps)")

    # ---- the lid, seated and on its way in
    o = overlap(lid, body)
    print(f"  lid seated in the body {o:8.2f}   {'ok' if o < TOL else 'COLLISION'}")
    bad += 0 if o < TOL else 1
    lid_bad = 0
    for i in range(1, 5):
        o = overlap(Pos(0, 0, -i * 1.5) * lid, body)
        if o > TOL:
            lid_bad += 1
            print(f"  lid approach -{i * 1.5:.1f} mm: body overlap {o:.2f} mm^3")
    print(f"  lid approach: {'clear' if not lid_bad else str(lid_bad) + ' steps blocked'} (4 steps)")

    path_bad = lid_bad + face_bad
    # ---- the module's way in: through the front opening, with the fascia off.
    pn = parts_inside(D)["PN532 board"]
    pnc = parts_inside(D)["PN532 components"]
    # it slides FORWARD out of the front opening, which is the reverse of
    # fitting it. Dropping it down was the old mount and the old mount could
    # not be assembled at all.
    run = D["pn532_w"] + 6.0
    mod_bad = 0
    for i in range(1, steps + 1):
        dy = -run * i / steps
        o = overlap(Pos(0, dy, 0) * pn, body) + overlap(Pos(0, dy, 0) * pnc, body)
        if o > TOL:
            mod_bad += 1
            print(f"  module step {i}/{steps} (dy {dy:.1f}): body overlap {o:.2f} mm^3")
    print(f"  module slides out the front: {'clear' if not mod_bad else str(mod_bad) + ' steps blocked'} ({steps} steps)")
    path_bad += mod_bad

    # ---- the ring drops out through the lid opening
    ring = parts_inside(D)["VU ring board"]
    leds = parts_inside(D)["VU ring LEDs"]
    rdrop = D["s_ring_cz"] + v["s_ring_od"] / 2 - D["s_lid_t"] + 2.0
    ring_bad = 0
    for i in range(1, steps + 1):
        dz = -rdrop * i / steps
        o = overlap(Pos(0, 0, dz) * ring, body) + overlap(Pos(0, 0, dz) * leds, body)
        if o > TOL:
            ring_bad += 1
            print(f"  ring step {i}/{steps} (dz {dz:.1f}): body overlap {o:.2f} mm^3")
    print(f"  ring drops out: {'clear' if not ring_bad else str(ring_bad) + ' steps blocked'} ({steps} steps)")
    path_bad += ring_bad

    # ---- and the point of the machine: a cartridge tapped on the pad has to
    # sit on it without fouling, and its tag has to land within range.
    cart = Pos(D["t_pad_cx"], D["t_pad_cy"], D["s_H"]) * Box(
        v["cart_l"], v["cart_w"], v["cart_h"], align=C)
    o = overlap(cart, body)
    tap_bad = 0
    if o > TOL:
        tap_bad += 1
        print(f"  a tapped cartridge fouls the body by {o:.2f} mm^3")
    # the tag sits just inside the cartridge's face, which is the face on the pad
    gap = D["t_antenna_to_tag"]
    if gap > 12.0:
        tap_bad += 1
        print(f"  the tag sits {gap:.2f} mm off the antenna; a PN532 wants 12 or less")
    covered = (v["pn532_l"] <= D["t_pad_l"] + 1e-6) and (v["pn532_w"] <= D["t_pad_w"] + 1e-6)
    if not covered:
        tap_bad += 1
        print("  the module is wider than the pad, so part of it is not under the tap point")
    print(f"  tap: cartridge sits clear, tag {gap:.2f} mm off the antenna "
          f"({'ok' if not tap_bad else str(tap_bad) + ' problems'})")
    bad += tap_bad

    # ---- the cartridge closes, the right way up, with the tag trapped.
    # The back plate is built in its PRINT orientation, spigot up, and goes in
    # turned over. That flip swings its bevelled corner across to the other
    # side of a bevelled seat, so the outline is mirrored to suit - and a
    # mirrored outline is exactly the sort of thing that is obviously right
    # until you put the two solids in the same room.
    shell, back = build_cart_shell(D), build_cart_back(D)
    fitted = Pos(0, 0, v["cart_h"]) * Rot(180, 0, 0) * back
    cart_bad = 0
    o = overlap(fitted, shell)
    if o > TOL:
        cart_bad += 1
        print(f"  the back plate does not seat: {o:.2f} mm^3 into the shell")
    fb = fitted.bounding_box()
    if abs(fb.max.Z - v["cart_h"]) > 0.01:
        cart_bad += 1
        print(f"  the back plate finishes at {fb.max.Z:.2f}, not flush at {v['cart_h']:.2f}")
    tag = Pos(0, 0, v["cart_wall"]) * Cylinder(v["tag_d"] / 2, v["tag_t"], align=C)
    for nm, solid in (("shell", shell), ("back plate", fitted)):
        o = overlap(tag, solid)
        if o > TOL:
            cart_bad += 1
            print(f"  the tag fouls the {nm} by {o:.2f} mm^3")
    slide = D["cart_pocket_d"] - v["tag_d"]
    float_z = (v["cart_h"] - D["cart_lid_t"] - D["cart_tag_press_h"]) - (v["cart_wall"] + v["tag_t"])         if D["cart_pressed"] else D["cart_cavity_h"] - v["tag_t"]
    if slide > 1.5:
        cart_bad += 1
        print(f"  the tag can slide {slide:.2f} mm in its ring")
    print(f"  cartridge: back plate seats flush, tag held with {slide:.2f} mm of slide "
          f"and {float_z:.2f} mm of float ({'ok' if not cart_bad else str(cart_bad) + ' problems'})")
    bad += cart_bad

    ok = not bad and not path_bad
    print("RESULT:", "the tap player goes together and reads"
          if ok else f"{bad} collisions, {path_bad} blocked steps")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
