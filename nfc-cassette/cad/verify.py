"""One gate: build every part at nominal and export it, check the invariants,
then sweep the parameter corners and rebuild without exporting.

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\verify.py          # nominal + corner sweep
    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\verify.py --quick  # nominal only

The invariants are the things a print would get wrong silently: a card that
does not fit its cassette, a cassette that does not fit its bay, a module
that cannot drop between its lips, a Dupont tail with nowhere to go.
"""
from __future__ import annotations

import itertools
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import params  # noqa: E402
from _lib import emit, write_manifest  # noqa: E402
from cartridge import build_back as build_cart_back, build_shell as build_cart_shell  # noqa: E402
from cassette import build_lid, build_tray  # noqa: E402
from player import build_base, build_top  # noqa: E402
from player_slot import build_body as build_slot_body, build_lid as build_slot_lid, build_knob, build_diffuser  # noqa: E402
from player_tap import (build_body as build_tap_body, build_fascia as build_tap_fascia,  # noqa: E402
                        build_lid as build_tap_lid, build_mark_arc)


def invariants(v: dict, D: dict) -> list[str]:
    bad = []

    def chk(cond: bool, msg: str):
        if not cond:
            bad.append(msg)

    # cassette
    chk(D["card_pocket_l"] < D["tray_inner_l"] - 2 * 1.6, "card frame does not fit inside the tray")
    # the sticker recess: it has to leave lid behind it and stay on the lid
    chk(D["lid_t"] - v["cass_sticker_t"] >= 0.9, "cassette: the sticker recess leaves too little lid behind it")
    chk(D["cass_sticker_l"] < D["lid_l"] and D["cass_sticker_w"] < D["lid_w"], "cassette: the sticker recess runs off the lid")
    chk(D["card_top_z"] + 0.2 <= D["lid_bottom_z"], "card touches the lid")
    chk(0.2 <= v["card_clr"] <= 0.8, "card clearance out of range")
    chk(D["lid_l"] < D["seat_l"] and D["lid_w"] < D["seat_w"], "lid does not fit its seat")
    chk(D["lid_l"] > D["tray_inner_l"] + 0.6, "lid falls through the tray opening")
    # bay
    chk(0.3 <= v["bay_clr"] <= 0.8, "bay clearance out of range")
    chk(D["proud"] >= 4.0, "the tape must stand at least 4 mm proud so it can be lifted out")
    chk(v["bay_depth"] >= 5.0, "less than 5 mm of bay and the tape can tip out")
    chk(D["screw_in_post"] >= v["thread_min"], "not enough thread in the post; longer screws")
    chk(D["pilot_depth"] < D["base_h"] - v["floor"] - 1.0, "pilot hole reaches the floor")
    chk(D["slab_t"] - v["screw_head_h"] >= 3.0, "slab too thin under the screw head")
    chk(v["notch_depth"] + v["wall"] + 1.0 <= D["side_margin"], "finger notch breaks through the side wall")
    # screws clear of the bay and inside the strips
    chk(D["screw_y"] - v["screw_head_d"] / 2 > D["bay_back_y"] + 0.8, "back screws hit the bay")
    chk(-D["screw_y"] + v["screw_head_d"] / 2 < D["bay_front_y"] - 0.8, "front screws hit the bay")
    chk(D["screw_x"] + v["post_d"] / 2 < D["L"] / 2, "screw post outside the body")
    # module
    chk(D["cavity_h"] >= D["pn532_below"] + v["pn532_t"] + v["cavity_clr"] - 1e-6, "module stack taller than the cavity")
    chk(v["pn532_l"] + 2 * (v["pcb_clr"] + v["lip_t"]) < D["cavity_l"], "module lips wider than the cavity")
    chk(D["pn532_cy"] + v["pn532_w"] / 2 + v["pcb_clr"] + v["lip_t"] < D["cavity_w"] / 2, "module lips hit the back wall")
    chk(D["antenna_to_card"] <= 12.0, "antenna too far from the card for a PN532")
    # D1 mini beside the module, USB plug reaches the back wall opening
    chk(D["d1_cx"] + v["d1_w"] / 2 + v["pcb_clr"] + v["lip_t"] < D["cavity_l"] / 2, "D1 mini lips hit the right wall")
    chk(D["d1_cx"] - v["d1_w"] / 2 - v["pcb_clr"] - v["lip_t"] > D["pn532_cx"] + v["pn532_l"] / 2 + v["pcb_clr"] + v["lip_t"], "D1 mini overlaps the module lips")
    chk(D["d1_top_z"] <= D["base_h"] - 0.5, "Dupont on the D1 mini hits the slab")
    chk(D["d1_cy"] + v["d1_l"] / 2 < D["cavity_w"] / 2, "D1 mini through the back wall")
    chk(D["usb_cz"] - v["usb_h"] / 2 > v["floor"] - 0.01, "USB cutout below the floor")
    chk(D["usb_cz"] + v["usb_h"] / 2 < D["base_h"], "USB cutout above the wall")
    # screws vs the D1 mini and the module corner posts (all four screw posts are in the corners)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * D["screw_x"], sy * D["screw_y"]
            chk(abs(x - D["d1_cx"]) > v["d1_w"] / 2 + v["post_d"] / 2 + v["lip_t"] or abs(y - D["d1_cy"]) > v["d1_l"] / 2 + v["post_d"] / 2 + v["lip_t"], "a screw post hits the D1 mini")
            chk(abs(x - D["pn532_cx"]) > v["pn532_l"] / 2 + v["post_d"] / 2 + v["lip_t"] or abs(y - D["pn532_cy"]) > v["pn532_w"] / 2 + v["post_d"] / 2 + v["lip_t"], "a screw post hits the module")
    # buzzer and LED
    chk(D["buzzer_cx"] - v["buzzer_d"] / 2 - 1.5 > -D["cavity_l"] / 2, "buzzer ring through the left wall")
    chk(D["buzzer_cx"] + v["buzzer_d"] / 2 + 1.5 < D["pn532_cx"] - v["pn532_l"] / 2 - v["pcb_clr"] - v["lip_t"], "buzzer ring under the module")
    chk(D["led_cz"] + v["led_d"] / 2 < D["base_h"] - 1.0, "LED hole breaks the top edge of the base")
    chk(D["led_cx"] + v["led_d"] / 2 + 3.0 < D["buttons_x0"] - 4.5, "LED too close to the first button")
    chk(D["led_cx"] - v["led_d"] / 2 > D["buzzer_cx"] + v["buzzer_d"] / 2 + 1.5, "LED legs land in the buzzer")
    chk(D["buttons_x0"] + 4 * D["buttons_pitch"] + 4.5 < D["L"] / 2 - v["corner_r"], "buttons run into the corner radius")

    # ---- vertical-slot player ----
    chk(D["s_proud"] >= 20.0, "slot: less than 20 mm of tape stands proud; hard to grab")
    chk(v["s_slot_depth"] >= 25.0, "slot: less than 25 mm of tape in the slot; it will wobble")
    chk(D["s_antenna_to_card"] <= 12.0, "slot: antenna too far from the card")
    chk(D["s_buzzer_top_z"] + 0.5 < D["s_roof_z"], "slot: buzzer hits the roof")
    chk(D["s_buzzer_cx"] - v["buzzer_d"] / 2 - 1.5 > D["s_rail_x"] + v["s_keeper"] / 2, "slot: buzzer ring overlaps the module's side rib")
    chk(D["s_buzzer_cx"] + v["buzzer_d"] / 2 + 1.5 < D["s_cavity_l"] / 2, "slot: buzzer ring through the right wall")
    chk(D["s_buzzer_cy"] - v["buzzer_d"] / 2 - 1.5 > D["y_pcb0"], "slot: buzzer ring in front of the module wall")
    chk(D["s_plate_bot_z"] > D["s_led_cz"] + v["led_d"] / 2 + 1.0, "slot: LED hole runs into the slot floor plate")
    chk(D["s_pcb_top_z"] + v["cavity_clr"] <= D["s_roof_z"] + 1e-6, "slot: module taller than the cavity")
    chk(v["s_lip_engage"] < v["s_edge_free"], "slot: a lip reaches past the PCB's component-free edge strip")
    chk(D["s_lip_top_z0"] < D["s_pcb_top_z"] - 0.5, "slot: top lip does not reach over the PCB's top edge")
    chk(D["s_lip_bot_z1"] > D["s_pcb_bot_z"] + 0.5, "slot: bottom lip does not reach over the PCB's bottom edge")
    corner_inner = v["pn532_l"] / 2 - 2.0 - v["s_corner_zone"]     # where the corner zones start
    chk(v["s_lip_top_w"] / 2 < corner_inner, "slot: top lip reaches into a corner zone (holes, headers)")
    chk(v["s_lip_bot_w"] / 2 < corner_inner, "slot: bottom lip reaches into a corner zone (I2C header, DIP switch)")
    chk(v["s_slot_r"] < D["s_slot_w"] / 2 - 0.3, "slot: plan corner radius too big for the slot width")
    chk(v["s_slot_r"] <= 1.2, "slot: plan corner radius would pinch the tape's square edges")
    for (x, y) in D["s_posts"]:
        chk((x - D["s_led_cx"]) ** 2 + (y + D["s_W"] / 2 - v["wall"] - 4.3) ** 2 > (v["post_d"] / 2 + v["led_d"] / 2 + 0.5) ** 2 or abs(x - D["s_led_cx"]) > v["post_d"] / 2 + v["led_d"] / 2 + 0.5,
            "slot: the LED body runs into a screw post")
    # the detent has to bite, but not so hard the tape needs a shove
    chk(0.05 <= D["s_click_bite"] <= 0.35, "slot: the detent's bite is outside 0.05-0.35 mm; it either misses the tape or fights it")
    chk(v["s_click_len"] < D["s_slot_l"] - 10.0, "slot: the detent ridge is nearly as long as the slot")
    chk(D["s_click_z"] + v["s_click_r"] < D["s_H"], "slot: the detent ridge runs out of the top of the body")
    chk(D["s_click_z"] - v["s_click_r"] > D["s_plate_top_z"], "slot: the detent ridge digs into the slot floor")
    chk(D["s_brd_tail_gap"] >= 0.0, "slot: the ESP32 runs into the module's Dupont tails")
    chk(D["s_brd_end_gap"] >= v["s_mount_gap"], "slot: the ESP32's end blocks hit the cavity wall")
    chk(D["s_brd_top_edge_z"] + v["cavity_clr"] <= D["s_roof_z"], "slot: the ESP32 stands into the roof")
    chk(D["y_brd_1"] + v["cavity_clr"] <= D["s_W"] / 2 - v["wall"] + 1e-6, "slot: the ESP32 goes through the back wall")
    chk(D["s_brd_top_z"] <= D["s_roof_z"] - 0.5, "slot: Dupont on the ESP32 hits the roof")
    # the USB window is high now, at the standing board's mid-height, so what
    # keeps it out of the slot block is being BEHIND it, not below it
    chk(D["s_brd_cy"] - v["esp_usb_w"] / 2 > D["y_pcb0"], "slot: the USB window opens into the slot block")
    chk(D["y_tail1"] + v["cavity_clr"] <= D["s_W"] / 2 - v["wall"] + 1e-6, "slot: module tails through the back wall")
    # zip-tie hold-down: the strap has to stand up behind the board, the groove
    # must not eat the lid, and both stations must miss the corner lips
    chk(D["s_tie_rise_gap"] >= v["tie_t"] + 0.3, "slot: no room for the zip tie to rise behind the D1 mini")
    chk(D["s_lid_t"] - D["s_tie_groove_d"] >= 1.2, "slot: the zip-tie groove leaves too little lid under it")
    chk(D["s_tie_span"] / 2 + D["s_tie_slot_l"] / 2 <= D["s_tie_lip_free"], "slot: a zip-tie slot lands on the D1 mini's corner lips")
    chk(D["s_tie_y_back"] + D["s_tie_slot_w"] / 2 <= D["s_lid_w"] / 2 - 0.8, "slot: the zip-tie slot runs off the back edge of the lid")
    chk(D["s_tie_y_back"] + D["s_tie_slot_w"] / 2 - D["y_brd_1"] >= v["tie_t"], "slot: too little of the back zip-tie slot is clear of the board for the strap to stand up")
    chk(D["s_tie_y_front"] - D["s_tie_slot_w"] / 2 > D["y_pcb0"] - 1e-6 or D["s_tie_y_front"] + D["s_tie_slot_w"] / 2 < D["y_pcb0"], "slot: the front zip-tie slot straddles the slot block's wall")
    for (x, y) in D["s_posts"]:
        for tx in D["s_tie_x"]:
            chk(abs(x - tx) > v["screw_head_d"] / 2 + D["s_tie_slot_l"] / 2 + 0.5
                or y > D["s_tie_y_back"] + v["screw_head_d"] / 2
                or y < D["s_tie_y_front"] - v["screw_head_d"] / 2, "slot: the zip-tie groove runs into a screw head recess")
    # posts clear of the slot ends, the D1 mini, the tails and the buzzer
    for (x, y) in D["s_posts"]:
        r = v["post_d"] / 2
        chk(abs(x) - r > D["s_slot_l"] / 2 + v["s_end_wall"] or y - r > D["y_pcb0"], "slot: a screw post lands in the slot block")
        chk(abs(x - D["s_brd_cx"]) > D["s_brd_mount_l"] / 2 + r or abs(y - D["s_brd_cy"]) > D["s_brd_mount_w"] / 2 + r, "slot: a screw post hits the ESP32's mount")
        chk(abs(x) > v["pn532_l"] / 2 + r or y - r > D["y_tail1"], "slot: a screw post lands in the module tails")
        chk((x - D["s_buzzer_cx"]) ** 2 + (y - D["s_buzzer_cy"]) ** 2 > (r + v["buzzer_d"] / 2 + 1.5) ** 2, "slot: a screw post hits the buzzer")
        chk(abs(x) + r <= D["s_cavity_l"] / 2 + v["wall"] and abs(y) + r <= D["s_cavity_w"] / 2 + v["wall"], "slot: a screw post outside the body")
    # ---- the recessed bottom lid, and everything that stands on it
    # (Samuel, 2026-09-18: the lid fouled the back wall by 0.5 mm and sat flush
    # against the left one, so it could not drop in; nothing checked for it)
    chk(D["s_lid_t"] - v["screw_head_h"] >= v["s_lid_under_head"] - 1e-6,
        "slot: the screw counterbore leaves no material under the head")
    chk(D["s_lid_ledge"] >= 0.8, "slot: the lid's outer rim is too thin to print")
    chk(v["wall"] - D["s_lid_ledge"] >= 0.8 - 1e-6, "slot: no seat left for the lid to stop against")
    chk(D["s_lid_l"] < D["s_pocket_l"] and D["s_lid_w"] < D["s_pocket_w"], "slot: the lid does not fit its pocket")
    chk(D["s_pocket_l"] > D["s_cavity_l"] and D["s_pocket_w"] > D["s_cavity_w"], "slot: the lid pocket is not wider than the cavity, so there is no seat")
    chk(D["s_usb_cz"] - v["usb_h"] / 2 > D["s_lid_t"] + 0.5, "slot: the USB cutout notches the lid skirt")
    chk(D["s_led_cz"] - v["led_d"] / 2 > D["s_lid_t"] + 0.5, "slot: the LED hole notches the lid skirt")
    # Nothing standing on the lid may touch a cavity wall: the lid goes in
    # straight down, so a zero-gap fit is an interference fit. Measure against
    # the ROUNDED cavity, not the flat wall - the first version of this check
    # used the flat wall and a mount corner still fouled the fillet.
    A, B, R = D["s_cavity_l"] / 2, D["s_cavity_w"] / 2, D["s_cavity_r"]

    def clear(x: float, y: float) -> float:
        """Distance from a point to the rounded cavity wall; negative is outside."""
        dx, dy = abs(x) - (A - R), abs(y) - (B - R)
        if dx > 0 and dy > 0:
            return R - (dx * dx + dy * dy) ** 0.5
        return min(A - abs(x), B - abs(y))

    mount = v["pcb_clr"] + v["lip_t"]
    # s_brd_mount_l already carries the lips; adding `mount` here counted them
    # twice and reported a mount 0.6 too big for a cavity that in fact fits it
    feet = [("the ESP32's mount", D["s_brd_cx"], D["s_brd_cy"], D["s_brd_mount_l"] / 2, D["s_brd_mount_w"] / 2),
            ("buzzer ring", D["s_buzzer_cx"], D["s_buzzer_cy"], v["buzzer_d"] / 2 + 1.5, v["buzzer_d"] / 2 + 1.5),
            ("module shelf", 0.0, (D["y_pcb0"] + D["y_pcb1"]) / 2, 15.0, (v["pn532_t"] + v["pcb_clr"]) / 2),
            ("ring posts", D["k_vu_c"][0] + D["s_ring_post_dx"], (D["s_ring_y0"] + D["s_ring_y1"]) / 2, 2.5,
             (D["s_ring_y1"] - D["s_ring_y0"]) / 2 + 0.2),
            ("ring posts", D["k_vu_c"][0] - D["s_ring_post_dx"], (D["s_ring_y0"] + D["s_ring_y1"]) / 2, 2.5,
             (D["s_ring_y1"] - D["s_ring_y0"]) / 2 + 0.2)]
    for what, cx, cy, hx, hy in feet:
        # located by the straight walls...
        chk(min(A - (abs(cx) + hx), B - (abs(cy) + hy)) >= v["s_mount_gap"] - 1e-6,
            f"slot: the {what} is not {v['s_mount_gap']} mm clear of the cavity wall; the lid is not located")
        # ...and it still has to physically pass the filleted corners
        for sx in (-1, 1):
            for sy in (-1, 1):
                chk(clear(cx + sx * hx, cy + sy * hy) >= 0.25,
                    f"slot: a corner of the {what} fouls the cavity; the lid will not drop in")
    # the screw heads have to land on the lid, which is smaller than the body
    for (x, y) in D["s_posts"]:
        chk(abs(x) + v["screw_head_d"] / 2 + 1.0 < D["s_lid_l"] / 2
            and abs(y) + v["screw_head_d"] / 2 + 1.0 < D["s_lid_w"] / 2,
            "slot: a screw counterbore runs off the edge of the lid")
    chk(D["s_screw_in_post"] >= v["thread_min"], "slot: not enough thread in the posts")
    chk(D["s_pilot_depth"] < D["s_roof_z"] - D["s_lid_t"] - 1.0, "slot: pilot hole reaches the roof")
    chk(D["s_buttons_x0"] + 4 * D["s_buttons_pitch"] + 4.5 < D["s_L"] / 2 - v["corner_r"], "slot: buttons run into the corner radius")
    chk(D["s_led_cx"] - v["led_d"] / 2 > -D["s_L"] / 2 + v["corner_r"], "slot: LED in the corner radius")
    # cosmetics stay on the face: nothing dents deeper than half the wall, nothing
    # runs into the LED hole or off the edge
    # the cutters are centred on the face, so the depth into the wall is k_dimple / k_recess
    chk(v["k_dimple"] < v["wall"] / 2 + 0.01 and v["k_recess"] < v["wall"] / 2 + 0.01, "slot: a cosmetic recess goes too deep into the wall")
    for (cx, cz), d in ((D["k_knob_big_c"], v["k_knob_big_d"]), (D["k_knob_small_c"], v["k_knob_small_d"])):
        chk(abs(cx) + d / 2 + 1.5 < D["s_L"] / 2 - v["corner_r"] and cz + d / 2 + 1.5 < D["s_H"], "slot: a knob recess runs off the face")
        chk((cx - D["s_led_cx"]) ** 2 + (cz - D["s_led_cz"]) ** 2 > (d / 2 + v["led_d"] / 2 + 1.5) ** 2, "slot: a knob recess hits the LED hole")
    chk(abs(D["k_knob_big_c"][0] - D["k_knob_small_c"][0]) > (v["k_knob_big_d"] + v["k_knob_small_d"]) / 2 + 2.0, "slot: the two knobs overlap")
    chk(D["s_buttons_x0"] - v["k_key_w"] / 2 > D["s_led_cx"] + v["led_d"] / 2 + 1.0, "slot: first key covers the LED")
    chk(D["s_buttons_x0"] + 4 * D["s_buttons_pitch"] + v["k_key_w"] / 2 < D["k_vu_c"][0] - D["k_vu_bezel_od"] / 2 - 2.0, "slot: keys run into the dial")
    chk(D["s_buttons_cz"] + v["k_key_h"] / 2 < D["k_counter_c"][1] - D["k_counter_h"] / 2 - 2.0, "slot: keys run into the counter window")
    # ---- the VU dial and the ring behind it
    vx, vz = D["k_vu_c"]
    bo = D["k_vu_bezel_od"] / 2
    chk(vx + bo < D["s_L"] / 2 - v["corner_r"] and vx - bo > D["s_buttons_x0"], "slot: the dial runs off the face")
    chk(vz + bo < D["s_H"] - 1.0 and vz - bo > D["s_lid_t"] + 1.0, "slot: the dial runs off the top or into the lid skirt")
    chk(v["k_vu_r1"] < bo - v["k_vu_bezel_w"] - 0.8, "slot: the wedge slots run under the bezel")
    chk(v["k_vu_r0"] > v["k_vu_centre_d"] / 2 + 1.5, "slot: the wedges meet the centre hole")
    chk(D["k_rec_c"][0] + 2.0 + 2.0 < vx - bo, "slot: the REC lamp runs into the dial's bezel")
    # the wedges have to straddle the LEDs, or the pixels light the wall
    # the wedge has to overlap the LED generously; it does not have to swallow it
    # whole, and demanding that made the dial too big for the face
    led_half = 2.5      # a WS2812B 5050 is 5 mm square
    chk(v["k_vu_r0"] <= v["s_ring_led_c"] / 2 - 1.0, "slot: wedge slots start outside the LED circle")
    chk(v["k_vu_r1"] >= v["s_ring_led_c"] / 2 + 1.0, "slot: wedge slots end short of the LED circle")
    # ...with enough angular slack that the ring does not have to be clocked exactly
    led_deg = 2 * math.degrees(math.asin(min(1.0, led_half / (v["s_ring_led_c"] / 2))))
    chk(360.0 / 8 - v["k_vu_gap_deg"] >= led_deg + 8.0, "slot: no rotational slack - the wedge is barely wider than the LED")
    chk(vz - v["s_ring_od"] / 2 > D["s_lid_t"] + 0.5, "slot: the ring sits in the lid skirt")
    chk(vz + v["s_ring_od"] / 2 + v["s_ring_clr"] + 3.0 < D["s_roof_z"], "slot: the ring hits the roof")
    chk(D["s_ring_rib_x"] + v["s_ring_rib"] / 2 < D["s_cavity_l"] / 2, "slot: the ring's ribs run through the side wall")
    chk(D["s_ring_y1"] <= D["y_slot0"] - 0.5 + 1e-6, "slot: the ring fouls the slot block; the slot has not moved back far enough")
    chk(D["s_ring_y0"] > -D["s_W"] / 2 + v["wall"] + 1e-6, "slot: the ring is inside the front wall")
    chk(D["s_ring_post_top"] > D["s_lid_t"] + 1.0, "slot: the ring's posts are too short to print")
    # the ring is 32 mm of disc in the front-right corner, where a screw post lives
    for (x, y) in D["s_posts"]:
        chk(abs(x - D["s_ring_cx"]) > v["s_ring_od"] / 2 + v["s_ring_clr"] + v["post_d"] / 2
            or y - v["post_d"] / 2 > D["s_ring_y1"] + 0.5,
            "slot: the VU ring runs into a screw post")
    # the VU diffuser: sunk below the bezel rim, material left at the grooves,
    # and each groove inside its web at the radius where the web is narrowest
    chk(D["k_vu_diff_r"] < D["k_vu_bezel_od"] / 2 - v["k_vu_bezel_w"] - 1e-6, "slot: the diffuser does not fit its dish")
    chk(D["k_vu_diff_proud"] <= v["k_vu_bezel_proud"] - 0.2 + 1e-9, "slot: the diffuser stands proud of the bezel rim")
    chk(not D["k_vu_diff_grooved"] or D["k_vu_diff_t_eff"] - D["k_vu_diff_groove_d_eff"] >= 0.4 - 1e-9, "slot: the diffuser's light-break groove leaves too little material")
    chk(not D["k_vu_diff_grooved"] or D["k_vu_diff_groove_w0"] >= v["k_vu_diff_groove_min"], "slot: a diffuser groove is narrower than a nozzle at k_vu_r0")
    chk(not D["k_vu_diff_grooved"] or D["k_vu_diff_groove_half"] < math.radians(v["k_vu_gap_deg"]) / 2, "slot: a diffuser groove opens into a wedge")
    chk(D["k_vu_diff_groove_r1"] <= D["k_vu_diff_r"] - 0.2, "slot: a diffuser groove runs off the edge of the disc")
    chk(D["k_vu_diff_groove_r0"] > 0.5, "slot: a diffuser groove reaches the centre of the disc")
    # ---- the tap player ----
    chk(D["t_pad_l"] <= D["s_L"] - 2 * v["wall"] - 1e-6, "tap: the pad cuts through the end walls")
    chk(D["t_pad_w"] <= D["s_W"] - 2 * v["wall"] - 1e-6, "tap: the pad cuts through the front or back wall")
    chk(D["t_antenna_to_tag"] <= 12.0, "tap: the antenna is too far from a tapped tag")
    chk(D["t_pn_board_z"] > D["s_brd_top_z"] + 1.0, "tap: the module hangs into the ESP32's headroom")
    chk(D["t_pn_air"] >= v["t_pn_air"] - 1e-9, "tap: the module's components touch the top wall")
    chk(v["pn532_l"] <= D["t_pad_l"] and v["pn532_w"] <= D["t_pad_w"], "tap: the module is bigger than the pad it sits under")
    # the tag lands over the coil, not merely near it. Nothing checked this:
    # t_antenna_to_tag measures the gap and says nothing about the offset.
    chk(abs(D["t_pad_cx"] - D["t_pn_cx"]) + v["tag_d"] / 2 <= v["pn532_l"] / 2 + 1e-6
        and abs(D["t_pad_cy"] - D["t_pn_cy"]) + v["tag_d"] / 2 <= v["pn532_w"] / 2 + 1e-6,
        "tap: a tapped tag does not land inside the module's footprint")
    chk(abs(D["t_pad_cx"]) + D["t_pad_l"] / 2 <= D["s_L"] / 2 - v["wall"] + 1e-6
        and abs(D["t_pad_cy"]) + D["t_pad_w"] / 2 <= D["s_W"] / 2 - v["wall"] + 1e-6,
        "tap: the pad has moved off the top of the body")
    # ---- the cartridge, which had no invariants at all ----
    chk(D["cart_pocket_d"] + 2 * v["cart_tag_ring_t"]
        <= min(D["cart_inner_l"], D["cart_inner_w"]) - 2.0,
        "cartridge: the tag's locating ring does not fit the cavity")
    chk(v["tag_t"] + 0.6 <= D["cart_cavity_h"] + 1e-9, "cartridge: the tag is thicker than the cavity")
    chk(D["cart_tag_ring_h"] <= D["cart_cavity_h"] - 0.4 + 1e-9, "cartridge: the locating ring is taller than the cavity")
    chk(not D["cart_pressed"] or D["cart_tag_press_h"] >= 0.8,
        "cartridge: the back plate's spigot is too short to print")
    chk(D["cart_tag_ring_h"] >= 0.6, "cartridge: the locating ring is too short to locate anything")
    chk(D["cart_sticker_t"] >= 0.15, "cartridge: the label recess has been squeezed to nothing")
    chk(D["cart_sticker_l"] <= v["cart_l"] - 2 * v["cart_corner_r"] + 1e-9
        and D["cart_sticker_w"] <= v["cart_w"] - 2 * v["cart_corner_r"] + 1e-9,
        "cartridge: the label recess runs into the corner radius")
    chk(v["cart_wall"] - D["cart_sticker_t"] >= 0.9 - 1e-9, "cartridge: the label recess leaves too little shell behind it")
    chk(v["cart_seat"] > v["cart_back_clr"] + 0.2, "cartridge: the back plate's rebate is smaller than its own clearance")
    chk(D["cart_break"] > 0.0, "cartridge: the edge break has gone negative")
    chk(v["cart_bevel"] < min(v["cart_l"], v["cart_w"]) / 2, "cartridge: the bevel has eaten half the cartridge")
    # the mark is an instruction - tap HERE - so it has to stay on the surface
    # the cartridge actually lands on, in both directions
    _r_in, _r_out = D["t_mark_r"][-1]
    _half = (D["t_mark_a1"] - D["t_mark_a0"]) / 2
    _wide = _half >= math.pi / 2
    _mx1 = D["t_pn_cx"] + _r_out
    _mx0 = D["t_pn_cx"] + (-_r_out if _wide else _r_in * math.cos(_half))
    _my = _r_out * (1.0 if _wide else math.sin(_half))
    chk(_mx1 <= D["t_pad_l"] / 2 + 1e-6 and _mx0 >= -D["t_pad_l"] / 2 - 1e-6
        and _my <= D["t_pad_w"] / 2 + 1e-6,
        "tap: the contactless mark runs off the pad it is telling you to tap")
    # the module goes in through the front opening, so the opening is its
    # ceiling, not the roof. It fitted under the roof and could not be got in.
    chk(D["t_pn_comp_z"] <= D["t_ap_z1"] - v["t_pn_slide_clr"] + 1e-9,
        "tap: the module stands above the opening it has to slide through")
    chk(v["pn532_l"] + 2 * v["t_pn_clr"] + 2 * v["t_pn_rail_t"] <= D["t_ap_l"],
        "tap: the module and its rails are wider than the opening")
    # ---- the fascia, and how it gets in and out ----
    # Everything here is scar tissue. Two earlier versions of this face seated
    # perfectly and could not be assembled - once because the flange was wider
    # than the cavity it had to retreat into, once because the dial left no
    # frame at the top to hook on to. Neither showed up until the fit check
    # tried to move it.
    chk(D["t_face_band"] >= v["t_face_band_min"] - 1e-9,
        "tap: no frame left above the opening for the fascia to bear on")
    chk(D["t_face_dial_top"] <= D["t_ap_z1"] - v["t_face_clr"] + 1e-9,
        "tap: the fascia's own edge cuts through the top of the dial")
    chk(D["t_face_dial_bot"] >= D["s_lid_t"] + 1e-9, "tap: the dial runs into the lid")
    chk(D["t_face_z0"] >= D["s_lid_t"] - 1e-9,
        "tap: the fascia's flange hangs below the lid that is meant to hold it up")
    chk(abs(D["t_face_z1"] - D["t_roof_z"]) < 1e-9,
        "tap: the fascia's flange does not reach the roof, so nothing stops it sliding up")
    chk(v["t_face_inset"] - D["t_face_ledge"] >= 0.8 - 1e-9,
        "tap: too little body left outside the channel to hold the fascia sideways")
    chk(v["wall"] - D["t_face_rebate"] >= 0.8 - 1e-9,
        "tap: the channel leaves the front wall thinner than two perimeters")
    chk(D["t_face_chamfer"] > 0.0, "tap: the fascia's lead-in chamfer has gone negative")
    chk(D["t_face_chamfer"] <= D["t_face_rebate"] - 0.3 + 1e-9
        and D["t_face_chamfer"] <= D["t_face_ledge"] - 0.4 + 1e-9,
        "tap: the fascia's chamfer eats the flange it is chamfering")
    chk(D["k_vu_c"][0] + D["k_vu_bezel_od"] / 2 <= D["t_ap_l"] / 2 - v["t_face_clr"],
        "tap: the dial runs off the end of the fascia")
    return bad


def build_all(D: dict):
    return {"cassette_tray": build_tray(D), "cassette_lid": build_lid(D),
            "player_base": build_base(D), "player_top": build_top(D),
            "slot_body": build_slot_body(D), "slot_lid": build_slot_lid(D),
            "vu_diffuser": build_diffuser(D),
            "tap_body": build_tap_body(D), "tap_fascia": build_tap_fascia(D),
            "tap_lid": build_tap_lid(D),
            **{f"tap_mark_{i + 1}": build_mark_arc(D, i) for i in range(len(D["t_mark_r"]))},
            "cart_shell": build_cart_shell(D), "cart_back": build_cart_back(D),
            "knob_big": build_knob(D, D["k_knob_big_d"]), "knob_small": build_knob(D, D["k_knob_small_d"])}


def valid(part) -> bool:
    """build123d made is_valid a property in 0.9; older releases had a method."""
    v = part.is_valid
    return bool(v() if callable(v) else v)


def main() -> int:
    quick = "--quick" in sys.argv
    v = params.nominal()
    D = params.derive(v)
    print(f"flat player {D['L']:.1f} x {D['W']:.1f} x {D['H']:.1f} mm, cassette {v['cassette_l']} x {v['cassette_w']} x {v['cassette_h']}, "
          f"antenna to card {D['antenna_to_card']:.1f} mm, cavity {D['cavity_h']:.1f} mm")
    print(f"slot player {D['s_L']:.1f} x {D['s_W']:.1f} x {D['s_H']:.1f} mm, tape stands {D['s_proud']:.1f} mm proud, "
          f"antenna to card {D['s_antenna_to_card']:.1f} mm")
    bad = invariants(v, D)
    if bad:
        print("NOMINAL INVARIANTS FAILED:\n  " + "\n  ".join(bad))
        return 1
    t0 = time.time()
    parts = build_all(D)
    for name, part in parts.items():
        if not valid(part):
            print(f"  INVALID solid: {name}")
            return 1
    emit(parts["cassette_tray"], "cassette_tray", "open side up", note="glue the lid in")
    emit(parts["cassette_lid"], "cassette_lid", "face up", note="the three recesses take the inserts")
    emit(parts["player_base"], "player_base", "open side up", note="electronics drop in from above")
    emit(parts["player_top"], "player_top", "bay side up", note="4 x M3 x 16 pan head from the top")
    emit(parts["slot_body"], "slot_body", "upside down, top face on the bed", note="slot floor bridges 13 mm")
    emit(parts["slot_lid"], "slot_lid", "outside face down",
         note=f"4 x M3 x {D['screw_len']:.0f} pan head from below; the lid recesses into the body; "
              f"2 small zip ties ({D['s_tie_slot_l']:.1f} x {D['s_tie_slot_w']:.1f} mm slots) hold the D1 mini down, "
              f"return run in the groove on the outside face")
    emit(parts["vu_diffuser"], "vu_diffuser", "smooth face down, grooves up",
         note="WHITE PLA; glue into the dial's dish inside the bezel")
    emit(parts["tap_body"], "tap_body", "upside down, top face on the bed",
         note="tap pad on the top; PN532 flat under it, antenna up")
    emit(parts["tap_fascia"], "tap_fascia", "face down",
         note="the swappable face; slides UP into the body, the lid holds it there")
    emit(parts["tap_lid"], "tap_lid", "outside face down",
         note="4 x M3 pan head from below; ESP32, ring posts, buzzer, zip ties")
    for i in range(len(D["t_mark_r"])):
        emit(parts[f"tap_mark_{i + 1}"], f"tap_mark_{i + 1}", "flat",
             note=f"arc {i + 1} of the contactless mark; glue into its recess on the top")
    emit(parts["cart_shell"], "cart_shell", "face down, open side up",
         note="pocket takes a 25 mm NTAG215 disc; label recess in the face")
    emit(parts["cart_back"], "cart_back", "flat, spigot UP",
         note="installs turned over - spigot down onto the tag; the outline is mirrored to suit")
    emit(parts["knob_big"], "knob_big", "flat, base down", note="glue into the left recess")
    emit(parts["knob_small"], "knob_small", "flat, base down", note="glue into the right recess")
    write_manifest()
    print(f"  nominal built and exported in {time.time() - t0:.0f} s")
    if quick:
        return 0

    # corner sweep over the parameters that actually move the geometry
    # cassette_corner_r is deliberately NOT swept (Samuel, 2026-09-18): adding
    # s_mount_gap had doubled this to 256 corners. It reaches three places -
    # the cassette tray's outer radius, tray_inner_r (tray + lid) and bay_r
    # (the flat player's bay) - and all three belong to parts that have not
    # moved since they were first swept. It touches nothing in the slot
    # player, whose slot has its own s_slot_r. Put it back before changing
    # the cassette shell or the flat bay.
    # First, sweeps that build nothing. The geometry sweep can only afford a
    # handful of parameters because every corner rebuilds eighteen solids; the
    # invariants cost microseconds, so they get their own passes over
    # everything the tap player's face, its mounts and the cartridge depend on.
    #
    # In GROUPS, and exhaustive within each one, rather than all of them at
    # once: twenty-eight parameters together is 2**28 corners, which is not a
    # stronger check than two exhaustive passes so much as one that never
    # finishes. Each group holds the parameters that actually reach each
    # other; the rest sit at nominal.
    #
    # This is where every range fault in this design has been caught. Each of
    # them satisfied nominal perfectly and broke somewhere in here.
    groups = {
        "face and mounts": [
            "t_face_ledge", "t_face_rebate", "t_face_clr", "t_face_band_min",
            "t_face_dial_bot_pad", "t_face_chamfer", "t_pn_slide_clr",
            "t_pn_slot_clr", "t_pn_top_ledge", "k_vu_r1", "k_vu_bezel_w",
            "t_face_inset", "edge_break", "wall", "t_mark_r0", "t_mark_pitch",
            "t_mark_w", "t_mark_half_deg"],
        "cartridge": [
            "cart_wall", "cart_lid_t", "cart_tag_ring_t", "cart_tag_press_clr",
            "tag_d", "tag_t", "tag_clr", "cart_h", "cart_l", "cart_w",
            "cart_sticker_margin", "cart_seat", "cart_corner_r", "cart_bevel"],
    }
    t0 = time.time()
    fails = 0
    for label, names in groups.items():
        g_fail = 0
        for corner in itertools.product(*[(params.PARAMS[k].lo, params.PARAMS[k].hi)
                                          for k in names]):
            vv = dict(v)
            vv.update(dict(zip(names, corner)))
            bad = invariants(vv, params.derive(vv))
            if bad:
                g_fail += 1
                if g_fail <= 3:
                    print(f"  {label} corner {dict(zip(names, corner))}: " + "; ".join(bad))
        print(f"  {label}: {2 ** len(names)} corners, {g_fail} failures")
        fails += g_fail
    print(f"  invariant groups: {fails} failures, {time.time() - t0:.0f} s")
    if fails:
        return 1

    # tag_t is in here for one reason: it is what decides whether the back
    # plate gets its hold-down spigot, and a conditional feature that is only
    # ever built at nominal is a feature nobody has checked.
    sweep = ["wall", "bay_clr", "pcb_clr", "pn532_comp_h", "esp_top_h", "card_clr",
             "s_mount_gap", "t_face_ledge", "esp_l", "tag_t"]
    fails = 0
    n = 0
    t0 = time.time()
    for corner in itertools.product(*[(params.PARAMS[k].lo, params.PARAMS[k].hi) for k in sweep]):
        vv = dict(v)
        vv.update(dict(zip(sweep, corner)))
        DD = params.derive(vv)
        n += 1
        bad = invariants(vv, DD)
        if bad:
            fails += 1
            print(f"  corner {dict(zip(sweep, corner))}: " + "; ".join(bad))
            continue
        try:
            for name, part in build_all(DD).items():
                if not valid(part) or part.volume <= 0:
                    fails += 1
                    print(f"  corner {dict(zip(sweep, corner))}: {name} invalid")
        except Exception as e:  # a boolean that fails is a real finding, not noise
            fails += 1
            print(f"  corner {dict(zip(sweep, corner))}: build error {e}")
    print(f"  sweep: {n} corners, {fails} failures, {time.time() - t0:.0f} s")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
