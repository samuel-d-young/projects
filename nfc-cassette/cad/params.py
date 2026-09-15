"""nfc-cassette - every dimension in one place, with its provenance.

Same rule as robot/luma: no number appears in a part file. A part asks for
`D["bay_l"]` and gets a value that `derive()` computed from parameters that
verify.py has swept. Provenance tags:

    datasheet   read off a published dimension. Trust it.
    derived     computed here. Cannot be wrong on its own.
    choice      a free design decision; any value in [lo, hi] must print.
    assumed     NOT VERIFIED. Measure before trusting; gauges.py prints a coupon.

Coordinates for the player: +X to the right, +Y toward the back, +Z up, origin
at the centre of the base's footprint on the table. The cassette bay is offset
toward the back to leave a strip along the front for the LED and the cosmetic
buttons. Millimetres.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    name: str
    nominal: float
    lo: float
    hi: float
    source: str  # datasheet | derived | choice | assumed
    note: str = ""


_P: list[Param] = [
    # ---- the cassette shell: a real compact cassette, so it feels right in the hand
    Param("cassette_l", 100.4, 100.0, 100.8, "datasheet", "IEC 60094-7 compact cassette shell"),
    Param("cassette_w", 63.8, 63.5, 64.0, "datasheet"),
    Param("cassette_h", 12.0, 11.8, 12.2, "datasheet"),
    Param("cassette_corner_r", 2.0, 1.5, 3.0, "choice", "vertical corner radius of the shell"),
    Param("shell_wall", 1.8, 1.6, 2.4, "choice"),
    Param("shell_floor", 1.6, 1.2, 2.0, "choice", "tray floor; the card sits on it"),
    Param("lid_t", 1.6, 1.2, 2.0, "choice", "the lid is a flat plate glued into the tray"),
    Param("lid_seat", 0.9, 0.8, 1.2, "choice", "rebate width the lid drops into"),
    Param("lid_clr", 0.15, 0.1, 0.3, "choice", "lid to rebate, per side"),
    Param("label_recess", 0.5, 0.4, 0.6, "choice", "sticker sits below the surface"),
    Param("rib_h", 1.0, 0.8, 1.2, "choice", "ribs that frame the card"),
    # ---- the NFC card inside the cassette
    Param("card_l", 85.60, 85.47, 85.72, "datasheet", "ISO/IEC 7810 ID-1"),
    Param("card_w", 53.98, 53.92, 54.03, "datasheet"),
    Param("card_t", 0.76, 0.68, 0.84, "datasheet"),
    Param("card_clr", 0.4, 0.2, 0.8, "choice", "card to rib frame, per side"),
    # ---- PN532 V3 module (Elechouse layout)
    Param("pn532_l", 42.7, 42.5, 43.0, "datasheet", "Elechouse PN532 NFC Module V3 drawing"),
    Param("pn532_w", 40.4, 40.2, 40.7, "datasheet"),
    Param("pn532_t", 1.6, 1.5, 1.7, "assumed", "standard FR4; gauge: measure with calipers"),
    Param("pn532_comp_h", 4.5, 4.0, 5.5, "assumed", "tallest part on the component side is the DIP switch"),
    Param("pin_below", 3.0, 2.5, 3.5, "assumed", "straight header, pins soldered pointing away from the antenna"),
    Param("dupont_h", 14.0, 13.5, 14.5, "datasheet", "2.54 mm Dupont housing length"),
    Param("pcb_clr", 0.3, 0.2, 0.6, "choice", "module to its locating lips, per side"),
    # ---- Wemos D1 mini
    Param("d1_l", 34.2, 34.0, 34.5, "datasheet", "Wemos D1 mini"),
    Param("d1_w", 25.6, 25.4, 25.8, "datasheet"),
    Param("d1_t", 1.0, 0.9, 1.2, "datasheet"),
    Param("d1_standoff", 3.0, 2.5, 4.0, "choice", "board underside above the base floor"),
    Param("d1_top_h", 14.0, 3.0, 14.5, "choice", "headroom above the board: 14 for Dupont on headers, 3 for soldered wires"),
    Param("usb_w", 13.0, 12.0, 14.0, "assumed", "micro-USB plug boot"),
    Param("usb_h", 8.0, 7.0, 9.0, "assumed"),
    # ---- extras
    Param("buzzer_d", 12.0, 11.8, 12.5, "datasheet", "common 12 mm passive buzzer"),
    Param("led_d", 5.0, 4.9, 5.2, "datasheet", "5 mm LED"),
    Param("led_clr", 0.2, 0.1, 0.3, "choice"),
    # ---- the player body
    Param("wall", 2.4, 2.0, 3.0, "choice", "6 perimeters at 0.4"),
    Param("floor", 2.4, 2.0, 3.0, "choice"),
    Param("bay_floor", 1.6, 1.2, 2.0, "choice", "between the module and the cassette; thin on purpose"),
    Param("bay_depth", 7.0, 6.0, 8.5, "choice", "the tape stands proud by cassette_h - bay_depth; 7 leaves 5 mm to grab (Samuel, 2026-09-15: not all the way in)"),
    Param("bay_clr", 0.4, 0.3, 0.8, "choice", "cassette to bay, per side"),
    Param("side_margin", 8.0, 7.0, 10.0, "choice", "slab beyond the bay, left and right"),
    Param("front_strip", 14.0, 12.0, 18.0, "choice", "slab in front of the bay"),
    Param("back_margin", 11.0, 9.0, 13.0, "choice", "slab behind the bay; the back screws live here"),
    Param("corner_r", 4.0, 3.0, 6.0, "choice", "outer vertical corners of the body"),
    Param("notch_d", 22.0, 20.0, 26.0, "choice", "finger notch at each end of the bay"),
    Param("notch_depth", 5.0, 4.0, 6.0, "choice", "how far the notch bites into the slab"),
    Param("screw_hole", 3.4, 3.2, 3.6, "datasheet", "M3 clearance"),
    Param("screw_pilot", 2.6, 2.5, 2.8, "datasheet", "M3 self-tapping into PLA"),
    Param("screw_head_d", 6.2, 6.0, 7.0, "datasheet", "M3 pan head + a little"),
    Param("screw_head_h", 2.5, 2.2, 3.0, "datasheet"),
    Param("screw_len", 16.0, 12.0, 20.0, "choice", "M3 x 16 pan head (24 in the LUMA box); the slab is thin now the bay is shallow"),
    Param("thread_min", 6.0, 5.0, 8.0, "choice", "thread engagement in the post, minimum"),
    Param("post_d", 7.0, 6.5, 8.0, "choice", "screw post in the base"),
    Param("post_inset", 5.5, 5.0, 7.0, "choice", "screw centre from the outer edge"),
    Param("lip_t", 1.2, 1.0, 1.6, "choice", "locating lips around the PCBs"),
    Param("ledge", 2.5, 2.0, 3.0, "choice", "how much of a PCB corner rests on its post"),
    Param("cavity_clr", 1.0, 0.5, 2.0, "choice", "air below the lowest thing in the cavity"),
]
PARAMS: dict[str, Param] = {p.name: p for p in _P}


def nominal() -> dict[str, float]:
    return {k: p.nominal for k, p in PARAMS.items()}


def derive(v: dict[str, float]) -> dict[str, float]:
    """Every derived number, computed once. Parts read D; verify.py checks D."""
    D = dict(v)
    # cassette
    D["tray_h"] = v["cassette_h"] - v["lid_t"]
    D["tray_inner_l"] = v["cassette_l"] - 2 * v["shell_wall"]
    D["tray_inner_w"] = v["cassette_w"] - 2 * v["shell_wall"]
    D["tray_inner_r"] = max(v["cassette_corner_r"] - v["shell_wall"], 0.6)
    D["lid_l"] = D["tray_inner_l"] + 2 * v["lid_seat"] - 2 * v["lid_clr"]
    D["lid_w"] = D["tray_inner_w"] + 2 * v["lid_seat"] - 2 * v["lid_clr"]
    D["seat_l"] = D["tray_inner_l"] + 2 * v["lid_seat"]
    D["seat_w"] = D["tray_inner_w"] + 2 * v["lid_seat"]
    D["card_pocket_l"] = v["card_l"] + 2 * v["card_clr"]
    D["card_pocket_w"] = v["card_w"] + 2 * v["card_clr"]
    D["card_top_z"] = v["shell_floor"] + v["card_t"]            # in tray coordinates
    D["lid_bottom_z"] = D["tray_h"] - v["lid_t"]                # where the lid's underside sits
    # player footprint
    D["bay_l"] = v["cassette_l"] + 2 * v["bay_clr"]
    D["bay_w"] = v["cassette_w"] + 2 * v["bay_clr"]
    D["bay_r"] = v["cassette_corner_r"] + v["bay_clr"]
    # the finger notch bites `notch_depth` into the side margin and must leave
    # the wall plus a 1.2 mm skin - so the margin grows with the wall if it must
    D["side_margin"] = max(v["side_margin"], v["wall"] + v["notch_depth"] + 1.2)
    D["L"] = D["bay_l"] + 2 * D["side_margin"]
    D["W"] = D["bay_w"] + v["front_strip"] + v["back_margin"]
    D["bay_cy"] = (v["front_strip"] - v["back_margin"]) / 2.0
    D["bay_front_y"] = D["bay_cy"] - D["bay_w"] / 2.0
    D["bay_back_y"] = D["bay_cy"] + D["bay_w"] / 2.0
    # the vertical stack, from the table up
    D["pn532_below"] = max(v["pn532_comp_h"], v["pin_below"] + v["dupont_h"])
    D["pcb_bottom_z"] = v["floor"] + v["cavity_clr"] + D["pn532_below"]
    D["pcb_top_z"] = D["pcb_bottom_z"] + v["pn532_t"]
    D["base_h"] = D["pcb_top_z"]                                 # the slab sits on the module
    D["slab_t"] = v["bay_floor"] + v["bay_depth"]
    D["H"] = D["base_h"] + D["slab_t"]
    D["bay_floor_z"] = D["H"] - v["bay_depth"]
    D["cavity_h"] = D["base_h"] - v["floor"]
    D["cavity_l"] = D["L"] - 2 * v["wall"]
    D["cavity_w"] = D["W"] - 2 * v["wall"]
    D["cavity_r"] = max(v["corner_r"] - v["wall"], 0.6)
    # module placement: under the card, shifted 8 mm left so the D1 mini clears
    # the back-right screw post. The card is 85.6 long, the module 42.7, so
    # the antenna is still entirely under the card. Header edge toward -X,
    # Dupont tails hang straight down off it.
    D["pn532_cx"], D["pn532_cy"] = -8.0, D["bay_cy"]
    D["antenna_to_card"] = v["pn532_t"] + v["bay_floor"] + v["shell_floor"]
    # D1 mini: to the right of the module, long side along Y, USB toward the back wall
    D["d1_cx"] = (D["pn532_cx"] + v["pn532_l"] / 2 + v["pcb_clr"] + v["lip_t"] + 2.0
                  + v["lip_t"] + v["pcb_clr"] + v["d1_w"] / 2)
    D["d1_cy"] = D["cavity_w"] / 2 - 3.0 - v["d1_l"] / 2       # 3 mm short of the back wall for the plug
    D["d1_board_z"] = v["floor"] + v["d1_standoff"]
    D["d1_top_z"] = D["d1_board_z"] + v["d1_t"] + v["d1_top_h"]
    D["usb_cz"] = D["d1_board_z"] + v["d1_t"] / 2 + 1.5           # plug centre a little above the board
    # buzzer: against the left wall, clear of the module's lips
    D["buzzer_cx"] = -(D["cavity_l"] / 2 - v["buzzer_d"] / 2 - 2.0)
    D["buzzer_cy"] = -12.0
    D["buzzer_hole_z"] = v["floor"] + 5.0
    # front face furniture: LED left, five cosmetic transport buttons to its right
    D["led_cx"] = -36.0
    D["led_cz"] = D["base_h"] / 2 + 2.0
    D["buttons_cz"] = D["base_h"] / 2 + 2.0
    D["buttons_x0"] = -10.0
    D["buttons_pitch"] = 12.0
    # screws: head sits in a counterbore, the shank passes the rest of the slab,
    # the thread bites the post; the pilot is drilled 2 mm deeper than needed
    D["screw_x"] = D["L"] / 2 - v["post_inset"]
    D["screw_y"] = D["W"] / 2 - v["post_inset"]
    D["screw_in_post"] = v["screw_len"] - (D["slab_t"] - v["screw_head_h"])
    D["pilot_depth"] = D["screw_in_post"] + 2.0
    D["proud"] = v["cassette_h"] - v["bay_depth"]
    D["notch_cx"] = D["bay_l"] / 2 + v["notch_d"] / 2 - v["notch_depth"]
    return D
