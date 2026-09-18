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
from cassette import build_lid, build_tray  # noqa: E402
from player import build_base, build_top  # noqa: E402
from player_slot import build_body as build_slot_body, build_lid as build_slot_lid, build_knob, build_diffuser  # noqa: E402


def invariants(v: dict, D: dict) -> list[str]:
    bad = []

    def chk(cond: bool, msg: str):
        if not cond:
            bad.append(msg)

    # cassette
    chk(D["card_pocket_l"] < D["tray_inner_l"] - 2 * 1.6, "card frame does not fit inside the tray")
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
    chk(D["s_d1_rib_gap"] >= 0.5, "slot: D1 mini too close to the module's side rib; widen s_side_margin")
    chk(D["y_d1_1"] + v["cavity_clr"] <= D["s_W"] / 2 - v["wall"] + 1e-6, "slot: D1 mini through the back wall")
    chk(D["s_d1_top_z"] <= D["s_roof_z"] - 0.5, "slot: Dupont on the D1 mini hits the roof")
    chk(D["s_usb_cz"] + v["usb_h"] / 2 < D["s_plate_bot_z"], "slot: USB cutout runs into the slot floor plate")
    chk(D["y_tail1"] + v["cavity_clr"] <= D["s_W"] / 2 - v["wall"] + 1e-6, "slot: module tails through the back wall")
    # zip-tie hold-down: the strap has to stand up behind the board, the groove
    # must not eat the lid, and both stations must miss the corner lips
    chk(D["s_tie_rise_gap"] >= v["tie_t"] + 0.3, "slot: no room for the zip tie to rise behind the D1 mini")
    chk(D["s_lid_t"] - D["s_tie_groove_d"] >= 1.2, "slot: the zip-tie groove leaves too little lid under it")
    chk(v["s_tie_span"] / 2 + D["s_tie_slot_l"] / 2 <= D["s_tie_lip_free"], "slot: a zip-tie slot lands on the D1 mini's corner lips")
    chk(D["s_tie_y_back"] + D["s_tie_slot_w"] / 2 <= D["s_lid_w"] / 2 - 0.8, "slot: the zip-tie slot runs off the back edge of the lid")
    chk(D["s_tie_y_back"] + D["s_tie_slot_w"] / 2 - D["y_d1_1"] >= v["tie_t"], "slot: too little of the back zip-tie slot is clear of the board for the strap to stand up")
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
        chk(abs(x - D["s_d1_cx"]) > v["d1_l"] / 2 + r + v["lip_t"] or abs(y - D["s_d1_cy"]) > v["d1_w"] / 2 + r + v["lip_t"], "slot: a screw post hits the D1 mini")
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
    feet = [("D1 mini's mount", D["s_d1_cx"], D["s_d1_cy"], v["d1_l"] / 2 + mount, v["d1_w"] / 2 + mount),
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
    return bad


def build_all(D: dict):
    return {"cassette_tray": build_tray(D), "cassette_lid": build_lid(D),
            "player_base": build_base(D), "player_top": build_top(D),
            "slot_body": build_slot_body(D), "slot_lid": build_slot_lid(D),
            "vu_diffuser": build_diffuser(D),
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
    emit(parts["cassette_lid"], "cassette_lid", "dimples up")
    emit(parts["player_base"], "player_base", "open side up", note="electronics drop in from above")
    emit(parts["player_top"], "player_top", "bay side up", note="4 x M3 x 16 pan head from the top")
    emit(parts["slot_body"], "slot_body", "upside down, top face on the bed", note="slot floor bridges 13 mm")
    emit(parts["slot_lid"], "slot_lid", "outside face down",
         note=f"4 x M3 x {D['screw_len']:.0f} pan head from below; the lid recesses into the body; "
              f"2 small zip ties ({D['s_tie_slot_l']:.1f} x {D['s_tie_slot_w']:.1f} mm slots) hold the D1 mini down, "
              f"return run in the groove on the outside face")
    emit(parts["vu_diffuser"], "vu_diffuser", "smooth face down, grooves up",
         note="WHITE PLA; glue into the dial's dish inside the bezel")
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
    sweep = ["wall", "bay_clr", "pcb_clr", "pn532_comp_h", "d1_top_h", "card_clr", "s_mount_gap"]
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
