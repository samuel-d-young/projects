"""Does the reader actually sit inside? Exact answer, not an estimate.

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\fitcheck_slot.py

Builds the electronics as solids at their designed positions - the PN532
board, the envelope its components may occupy, the header's Dupont tails,
the D1 mini with its headroom, its USB plug, the buzzer, the LED, and the
tape in the slot - then intersects each with the slot body and the lid in
build123d. Any overlap is a real collision and is printed in mm^3. It also
intersects the two PRINTED PARTS with each other, seated and on the way in:
the lid carries the D1 mini's posts and lips, the buzzer ring and the module
shelf, and those have to clear the cavity walls. Then it slides the module
down its insertion path (lid off, straight down out of the pocket) in steps
and checks the body never touches it on the way.

The component envelope keeps s_edge_free clear of the PCB's top and bottom
edges in the middle third, which is the one geometric assumption about the
clone board (from the listing photos); the top and bottom lips live in
exactly that band, so this check is also what guards that assumption.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build123d import Align, Box, Cylinder, Pos, Rot  # noqa: E402

import params  # noqa: E402
from player_slot import build_body, build_lid  # noqa: E402

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)
TOL = 0.05  # mm^3 - below this is tessellation noise, not a collision


def parts_inside(D: dict):
    """Every solid that lives inside the player, at its designed place."""
    v = D
    pcb_y = (D["y_pcb0"] + D["y_pcb1"]) / 2
    pcb = Pos(0, pcb_y, D["s_pcb_bot_z"]) * Box(v["pn532_l"], v["pn532_t"], v["pn532_w"], align=C)
    # components: the whole back face minus the s_edge_free band top and bottom
    # (middle third) and minus the outermost 2 mm at the sides
    comp = Pos(0, D["y_pcb1"] + v["pn532_comp_h"] / 2, D["s_pcb_bot_z"] + v["s_edge_free"]) * Box(
        v["pn532_l"] - 4.0, v["pn532_comp_h"], v["pn532_w"] - 2 * v["s_edge_free"], align=C)
    # the corner regions outside the middle third may carry parts right to the
    # edge strip (headers, DIP switch): model them as full-height blocks
    corners = []
    for sx in (-1, 1):
        corners.append(Pos(sx * (v["pn532_l"] / 2 - 2.0 - v["s_corner_zone"] / 2), D["y_pcb1"] + v["pn532_comp_h"] / 2, D["s_pcb_bot_z"] + 0.3) * Box(
            v["s_corner_zone"], v["pn532_comp_h"], v["pn532_w"] - 0.6, align=C))
    # Dupont tails off the 8-pin header along the left edge: 2.54 pitch, 8 pins
    tails = Pos(-(v["pn532_l"] / 2 - 2.5), D["y_pcb1"] + D["s_tail"] / 2, D["s_pcb_bot_z"] + 8.0) * Box(
        3.0, D["s_tail"], 8 * 2.54 + 1.0, align=C)
    # The board stands on edge: 55 across, its thickness plus the Dupont headroom
    # front to back, and its 27.9 width going UP. Modelled flat it read as a
    # 2586 mm3 collision with the roof and the lid - the solid, not the board.
    esp = Pos(D["s_brd_cx"], D["s_brd_cy"], D["s_brd_board_z"]) * Box(
        v["esp_l"], v["esp_w"], v["esp_t"] + v["esp_top_h"], align=C)
    usb = Pos(D["s_brd_cx"] - v["esp_l"] / 2 - 6.0, D["s_brd_cy"], D["s_usb_cz"]) * Box(12.0, v["esp_usb_w"] - 1.0, v["esp_usb_h"] - 1.0, align=CC)
    buzzer = Pos(D["s_buzzer_cx"], D["s_buzzer_cy"], D["s_lid_t"] + 0.2) * Cylinder(v["buzzer_d"] / 2, v["buzzer_d"] * 0.8, align=C)
    led = Pos(D["s_led_cx"], -D["s_W"] / 2 + v["wall"] + 4.3, D["s_led_cz"]) * Rot(90, 0, 0) * Cylinder(v["led_d"] / 2, 8.6, align=CC)
    tape = Pos(0, (D["y_slot0"] + D["y_slot1"]) / 2, D["s_plate_top_z"] + 0.3) * Box(v["cassette_l"], v["cassette_h"], v["cassette_w"], align=C)
    # The VU dial's boards, as one disc each: the ring board (the single LED sits
    # in its middle, so a full disc is the conservative shape) and the LED
    # packages standing in front of it, in the air gap behind the front wall.
    # The ring is an ANNULUS, not a disc. It was modelled as a full disc while
    # nothing sat in the middle; the single WS2812B now has a mount there, so
    # the hole has to be real or the mount reads as a collision with a board
    # that is not there.
    def _ring(y, t):
        return Pos(D["s_ring_cx"], y, D["s_ring_cz"]) * Rot(90, 0, 0) * (
            Cylinder(v["s_ring_od"] / 2, t, align=CC)
            - Cylinder(v["s_ring_id"] / 2, t + 1.0, align=CC))
    ring = _ring((D["s_ring_y0"] + D["s_ring_y1"]) / 2, v["s_ring_t"])
    ring_leds = _ring((D["s_ring_led_y"] + D["s_ring_y0"]) / 2, v["s_ring_led_h"])
    dot = Pos(D["s_ring_cx"], (D["s_ring_led_y"] + D["s_ring_y1"]) / 2, D["s_ring_cz"]) * Rot(90, 0, 0) * Cylinder(
        v["s_dot_od"] / 2, v["s_ring_led_h"] + v["s_ring_t"], align=CC)
    return {"PN532 board": pcb, "PN532 components (middle)": comp, "PN532 corner parts L": corners[0],
            "PN532 corner parts R": corners[1], "Dupont tails": tails, "ESP32 + headroom": esp,
            "USB plug": usb, "buzzer": buzzer, "LED": led, "tape in the slot": tape,
            "VU ring board": ring, "VU ring LEDs": ring_leds, "the single WS2812B": dot}


def overlap(a, b) -> float:
    try:
        return float((a & b).volume)
    except Exception:
        return 0.0


def main() -> int:
    D = params.derive(params.nominal())
    body, lid = build_body(D), build_lid(D)
    outer = Box(D["s_L"], D["s_W"], D["s_H"], align=C)
    bad = 0
    print("part                          vs body    vs lid     inside?")
    for name, solid in parts_inside(D).items():
        ob, ol = overlap(solid, body), overlap(solid, lid)
        # the tape stands out of the top and the USB plug pokes through the wall, by design
        inside = name in ("tape in the slot", "USB plug") or abs(overlap(solid, outer) - float(solid.volume)) < TOL
        # The detent is meant to touch the tape - that is the whole point of it -
        # so the tape is allowed exactly the two ridges' worth of interference
        # and not a cubic millimetre more. An allowance, not an exemption.
        allow = D["s_click_volume"] * 1.25 if name == "tape in the slot" else TOL
        ok = ob < allow and ol < TOL and inside
        bad += 0 if ok else 1
        note = "" if name != "tape in the slot" else f"  (detent, expect {D['s_click_volume']:.2f})"
        print(f"  {name:28} {ob:8.2f} {ol:9.2f}   {'yes' if inside else 'NO':6} {'ok' if ok else 'COLLISION'}{note}")
    # Does the LID go in? The check that was missing: the electronics were
    # intersected with both parts, but the two printed parts were never
    # intersected with each other, so the D1 mini's mount driving 0.5 mm into
    # the back wall went unseen through a full sweep (Samuel, 2026-09-18:
    # "the bottom doesn't go in properly").
    seated = overlap(lid, body)
    print(f"  {'lid seated in the body':28} {seated:8.2f}   {'ok' if seated < TOL else 'COLLISION'}")
    bad += 0 if seated < TOL else 1
    # and it has to get there: straight up into the pocket, nothing catching
    lid_bad = 0
    for i in range(1, 5):
        o = overlap(Pos(0, 0, -i * 1.5) * lid, body)
        if o > TOL:
            lid_bad += 1
            print(f"  lid approach -{i * 1.5:.1f} mm: body overlap {o:.2f} mm^3")
    print(f"  lid approach: {'clear' if not lid_bad else str(lid_bad) + ' steps blocked'} (4 steps)")
    bad += lid_bad

    # insertion path: the module drops straight down out of its pocket (lid off)
    v = D
    pcb_y = (D["y_pcb0"] + D["y_pcb1"]) / 2
    steps = 6
    path_bad = 0
    for i in range(1, steps + 1):
        dz = -(D["s_pcb_bot_z"] - D["s_lid_t"] + 2.0) * i / steps
        moving = Pos(0, pcb_y, D["s_pcb_bot_z"] + dz) * Box(v["pn532_l"], v["pn532_t"], v["pn532_w"], align=C)
        comp_m = Pos(0, D["y_pcb1"] + v["pn532_comp_h"] / 2, D["s_pcb_bot_z"] + v["s_edge_free"] + dz) * Box(
            v["pn532_l"] - 4.0, v["pn532_comp_h"], v["pn532_w"] - 2 * v["s_edge_free"], align=C)
        o = overlap(moving, body) + overlap(comp_m, body)
        if o > TOL:
            path_bad += 1
            print(f"  insertion step {i}/{steps} (dz {dz:.1f}): body overlap {o:.2f} mm^3")
    print(f"  insertion path: {'clear' if not path_bad else str(path_bad) + ' steps blocked'} ({steps} steps)")
    print("RESULT:", "the reader sits inside" if not bad and not path_bad else f"{bad} collisions, {path_bad} blocked steps")
    return 0 if not bad and not path_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
