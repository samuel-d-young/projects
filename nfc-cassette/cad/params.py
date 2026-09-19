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

import math
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
    # ---- the cassette's face: one shallow recess for a printed sticker
    # (Samuel, 2026-09-19: "keep the front of the cassette simple because I'll
    # print off the front design"). The moulded label strip, tape window and
    # reel hubs are gone - artwork does all of that better and costs nothing.
    Param("cass_sticker_t", 0.30, 0.20, 0.60, "choice", "depth of the sticker recess. Paper label stock is 0.10-0.20 and vinyl 0.15-0.25, so 0.30 leaves the artwork a touch below flush where the edges cannot be picked at"),
    Param("cass_sticker_margin", 2.0, 1.0, 4.0, "choice", "lid left proud around the sticker, per side. Enough to drop the artwork in square by eye"),
    Param("label_recess", 0.5, 0.4, 0.6, "choice", "sticker sits below the surface"),
    Param("rib_h", 1.0, 0.8, 1.2, "choice", "ribs that frame the card"),
    # ---- the NFC card inside the cassette
    Param("card_l", 85.60, 85.47, 85.72, "datasheet", "ISO/IEC 7810 ID-1"),
    Param("card_w", 53.98, 53.92, 54.03, "datasheet"),
    Param("card_t", 0.76, 0.68, 0.84, "datasheet"),
    Param("card_clr", 0.4, 0.2, 0.8, "choice", "card to rib frame, per side"),
    # ---- PN532 V3 module (Elechouse layout)
    # 2026-09-18: measured off Samuel's own board from a perspective-corrected photo
    # (calibrated on the 2.54 mm header pitch): 42.6 x 40.3, so the drawing holds.
    # The 42.7 edges are the ones the 8-pin and 10-pin headers run alongside; the
    # 4-pin runs alongside a 40.4 edge. The top/bottom lips press on the 42.7 edges.
    Param("pn532_l", 42.7, 42.5, 43.0, "datasheet", "Elechouse V3 drawing; photo-measured 42.6 (2026-09-18)"),
    Param("pn532_w", 40.4, 40.2, 40.7, "datasheet", "photo-measured 40.3 (2026-09-18)"),
    Param("pn532_t", 1.6, 1.5, 1.7, "assumed", "standard FR4; gauge: measure with calipers"),
    Param("pn532_comp_h", 4.5, 4.0, 5.5, "assumed", "tallest part on the component side is the DIP switch - CONFIRMED to be the tallest by photo (2026-09-18); its HEIGHT is still unmeasured"),
    Param("pin_below", 3.0, 2.5, 3.5, "assumed", "straight header, pins soldered pointing away from the antenna. The photos show BOTH headers unpopulated: this is Samuel's soldering choice, not the board's. It drives s_tail (17 mm) and so the body's whole depth - right-angle headers or wires straight to the pads would save ~14 mm"),
    Param("dupont_h", 14.0, 13.5, 14.5, "datasheet", "2.54 mm Dupont housing length"),
    Param("pcb_clr", 0.3, 0.2, 0.6, "choice", "module to its locating lips, per side"),
    # ---- Wemos D1 mini
    Param("d1_l", 34.2, 34.0, 34.5, "datasheet", "Wemos D1 mini"),
    Param("d1_w", 25.6, 25.4, 25.8, "datasheet"),
    Param("d1_t", 1.0, 0.9, 1.2, "datasheet"),
    Param("d1_standoff", 3.0, 2.5, 4.0, "choice", "board underside above the base floor"),
    # ---- the ESP32-WROOM-32 DevKit, which is the board that actually works.
    # Two D1 minis never answered esptool on any cable; the ESP32 did first try
    # (2026-09-19), so the slot player houses this now. It is 20.8 mm longer
    # than a D1 mini and that lands straight on the body: 127.9 -> 169.5.
    Param("esp_l", 55.0, 54.0, 56.5, "assumed", "ESP32 DevKit board length, 38-pin. WANTS CALIPERS: the 30-pin and 38-pin boards differ, and clones vary along this axis more than any other"),
    Param("esp_w", 27.9, 25.4, 28.5, "assumed", "and its width, across the two header rows"),
    Param("esp_t", 1.6, 1.4, 1.8, "assumed", "PCB thickness"),
    Param("esp_standoff", 3.0, 2.5, 4.0, "choice", "board underside above the lid"),
    Param("esp_top_h", 14.0, 3.0, 14.5, "choice", "headroom above the board: 14 for Dupont on the headers, 3 for soldered wires"),
    Param("esp_usb_w", 13.0, 12.0, 14.5, "assumed", "micro-USB plug boot on the DevKit"),
    Param("esp_usb_h", 8.0, 7.0, 9.5, "assumed"),
    Param("esp_slot_clr", 0.40, 0.30, 0.60, "choice", "the board's edge slot, over esp_t"),
    Param("esp_slot_h", 6.00, 4.00, 9.00, "choice", "how far the slot walls stand off the lid: enough to hold a 27.9 mm board upright, short enough to print as a fin"),
    Param("esp_end_block", 2.40, 1.60, 3.20, "choice", "the blocks past each end of the board, which is what a cable being pushed in actually pushes against"),
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
    # ---- the vertical-slot player ("toaster"): the tape stands in a slot in the top
    Param("s_slot_clr", 0.5, 0.3, 0.8, "choice", "tape to slot, per side, both directions"),
    Param("s_slot_depth", 33.0, 28.0, 38.0, "choice", "how much of the tape's 63.8 height is inside; the rest stands proud"),
    Param("s_slot_floor", 2.0, 1.6, 2.6, "choice", "plate the tape stands on"),
    Param("s_module_wall", 1.6, 1.2, 2.0, "choice", "between the slot and the module's flat back"),
    Param("s_roof", 2.4, 2.0, 3.0, "choice", "top face over the module zone"),
    Param("s_side_margin", 13.0, 12.0, 15.0, "choice", "beyond the slot ends; the D1 mini lives on the left behind the module wall"),
    Param("s_keeper", 1.5, 1.2, 2.0, "choice", "thickness of the ribs that hold the PCB against the module wall"),
    Param("s_shelf_h", 1.0, 0.8, 1.5, "choice", "rib on the lid the PCB's bottom edge rests on"),
    Param("s_lip_engage", 1.5, 1.2, 1.8, "choice", "how far the top and bottom lips reach over the PCB's edge strips"),
    Param("s_edge_free", 2.0, 1.8, 2.5, "assumed", "component-free band along the PCB's top and bottom edges, middle third. 2026-09-18, measured on Samuel's board: those are the edges the 8-pin and 10-pin headers run alongside, at 6.3 and 9.5 mm from the edge (hole centres, +-0.5). A 2.54 header body reaches no closer than ~5.1 mm, so a 1.5 mm lip has ~3.6 mm to spare. Still assumed for SMD HEIGHT, measured in plan"),
    Param("s_lip_top_w", 16.0, 12.0, 18.0, "choice", "width of the top lip, centred - clear of the corner zones (holes, headers, DIP switch)"),
    Param("s_lip_bot_w", 16.0, 10.0, 18.0, "choice", "width of the bottom lip, centred - between the I2C header and the DIP switch"),
    Param("s_corner_zone", 10.0, 8.0, 12.0, "assumed", "band inside each side edge (after a 2 mm margin) where the headers, holes and DIP switch may sit right up to the top/bottom edges. The DIP switch is the feature that sets this; it sits in a corner on the photos, inside the 10 mm, but it has not been measured"),
    Param("s_slot_r", 0.8, 0.5, 1.2, "choice", "plan-view corner radius of the slot; the tape's thickness edges are square, so keep this small or it pinches"),
    # ---- the detent (Samuel, 2026-09-19: "make the bottom of the cassette area
    # click or a bump or something so that you know when it goes in"). A ridge
    # on each long wall of the slot, just above where the tape's bottom edge
    # comes to rest: the edge rides over it and drops the last few mm, so the
    # tape announces itself before the LED does. It has to EXCEED s_slot_clr to
    # touch at all - at 0.50 clearance a 0.45 bump never meets the tape.
    Param("s_click_r", 0.65, 0.55, 0.80, "choice", "how far the detent ridge stands into the slot. The interference over s_slot_clr is what you feel, and it is taken out of the cassette's shell, which is hollow and flexes - not out of the player, which does not"),
    Param("s_click_len", 20.0, 12.0, 30.0, "choice", "ridge length along the slot, centred"),
    Param("s_click_up", 3.0, 2.0, 5.0, "choice", "the ridge sits this far above the tape's seated bottom edge, so the click lands just before home"),
    Param("s_end_wall", 2.0, 1.6, 2.6, "choice", "slot block beyond each end of the slot"),
    # ---- the bottom lid: recessed into the body, not butted against it (Samuel,
    # 2026-09-18: "the bottom doesn't go in properly... move the mount, it hits the edge")
    Param("s_mount_gap", 0.6, 0.4, 1.0, "choice", "gap between anything standing on the lid and the cavity wall; the lid drops in vertically, so a zero-gap fit does not assemble"),
    Param("s_lid_ledge", 1.2, 0.8, 1.6, "choice", "width of the body's outer rim that continues down past the recessed lid"),
    Param("s_lid_clr", 0.25, 0.15, 0.4, "choice", "lid to its pocket in the body, per side"),
    Param("s_lid_under_head", 1.2, 1.0, 2.0, "choice", "lid material left under the screw head; sets the lid's thickness"),
    # ---- zip-tie hold-down for the D1 mini (Samuel, 2026-09-18: "hold down the
    # d1 mini too, and so the board is fastened when plugging in the cable").
    # The strap rises in the 2.1 mm gap between the board's back edge and the
    # cavity wall, crosses the board and drops through a second slot in front of
    # it; the return run sits in a groove in the lid's OUTSIDE face so the player
    # still stands flat. Measure a strap before printing: these are off a bag of
    # "100 mm x 2.5 mm" ties and the bags lie.
    Param("tie_w", 2.5, 2.0, 3.0, "assumed", "zip-tie strap width; sets the slot's length along X"),
    Param("tie_t", 1.2, 0.9, 1.3, "assumed", "zip-tie strap thickness; sets the slot's width and the groove's depth. The ceiling is real: the strap stands up in pcb_clr + lip_t + s_mount_gap behind the board, which is 1.8 mm at the tightest corner of the sweep, so a medium (3.6 x 1.6) tie does not fit - small ties only"),
    Param("tie_clr", 0.4, 0.3, 0.6, "choice", "clearance around the strap in its slot and groove"),
    Param("s_tie_span_frac", 0.62, 0.45, 0.75, "choice", "distance between the two straps, as a fraction of the board's length. A fraction because the board changed once already: 19 mm was two thirds of a D1 mini and barely a third of an ESP32, which put both straps in the middle where they do least against a cable being pushed in"),
    # ---- front-face cosmetics (Samuel, 2026-09-16: "fake buttons and knobs")
    Param("k_key_w", 10.0, 8.0, 12.0, "choice", "transport key width"),
    Param("k_key_h", 9.0, 7.0, 11.0, "choice", "transport key height on the face"),
    Param("k_key_proud", 3.0, 2.0, 4.0, "choice", "how far a key stands off the face"),
    Param("k_knob_big_d", 16.0, 12.0, 20.0, "choice", "volume knob, printed flat and glued into its recess"),
    Param("k_knob_small_d", 11.0, 9.0, 14.0, "choice", "tuning knob"),
    Param("k_knob_h", 6.0, 4.0, 8.0, "choice", "knob height"),
    Param("k_recess", 0.6, 0.4, 0.8, "choice", "locating recess in the face for a glued knob"),
    Param("k_dimple", 0.8, 0.6, 1.0, "choice", "depth of the counter window and the REC lamp"),
    # ---- the VU dial: a WS2812B 8-LED ring behind eight wedge slots, one per
    # pixel, with the single WS2812B showing through the middle. Samuel,
    # 2026-09-18: "put the rings behind the grate on the right hand side" and
    # move the slot back to make room. It replaces the dimpled speaker grille.
    Param("s_ring_od", 32.0, 31.0, 34.0, "assumed", "WS2812B 8-LED ring board diameter; photo-measured ~32, wants calipers"),
    Param("s_ring_led_c", 25.5, 24.5, 26.5, "assumed", "diameter of the circle the eight LEDs sit on; photo-measured 25.5"),
    Param("s_ring_id", 19.0, 16.0, 21.0, "assumed", "the ring board's centre hole. The 5050 packages reach in to r 10.25, so the hole cannot exceed 20.5 - and the single WS2812B lives in it, which is why this is modelled at last"),
    Param("s_ring_t", 1.6, 1.4, 1.8, "assumed", "ring PCB thickness; standard FR4"),
    Param("s_ring_led_h", 1.6, 1.2, 2.0, "assumed", "WS2812B 5050 package height above the board"),
    Param("s_dot_od", 10.0, 8.0, 12.0, "assumed", "the single WS2812B board's diameter"),
    Param("s_dot_ledge", 2.0, 1.5, 3.0, "choice", "the ledge the single WS2812B stands on, and how far its fins run past it"),
    Param("s_ring_air", 0.6, 0.4, 1.0, "choice", "air between the LED tops and the inside of the front wall"),
    Param("s_ring_clr", 0.4, 0.3, 0.8, "choice", "ring to its cradle, per side"),
    Param("s_ring_rib", 2.0, 1.6, 2.6, "choice", "the vertical ribs that hold the ring; vertical so they print on a vertical face"),
    Param("s_ring_post_w", 5.0, 4.0, 6.0, "choice", "width of each post the ring stands on"),
    Param("k_vu_bezel_w", 2.5, 2.0, 3.5, "choice", "width of the raised bezel ring"),
    Param("k_vu_bezel_proud", 1.0, 0.6, 1.4, "choice", "how far the bezel stands off the face - kept shallow, like the counter frame, because a tall boss on a vertical face is a half-cylinder overhang"),
    Param("k_vu_r0", 8.5, 7.0, 10.0, "choice", "inner radius of the wedge slots"),
    Param("k_vu_r1", 15.0, 13.5, 15.5, "choice", "outer radius of the wedge slots; has to overlap the LED circle generously, not swallow it"),
    Param("k_vu_gap_deg", 9.0, 7.0, 14.0, "choice", "web between wedges, degrees"),
    Param("k_vu_centre_d", 3.5, 2.5, 4.5, "choice", "hole the single LED shows through"),
    # ---- the diffuser (Samuel, 2026-09-18: "a diffuser for where the LED rings
    # will be... printed in white PLA"). A disc that glues into the dial's dish,
    # like the knobs glue into their recesses. It does NOT plug the wedge slots:
    # the 2.4 mm slot behind it collimates, and a plug would only carry light
    # sideways. Segmentation is kept by grooves on the back, one per web.
    Param("k_vu_diff_t", 1.2, 0.8, 1.6, "choice", "diffuser disc thickness. White PLA: 1.2 is six layers at 0.2 - enough to scatter the 5050 dies, thin enough to stay bright"),
    Param("k_vu_diff_clr", 0.3, 0.2, 0.5, "choice", "diffuser to the wall of its dish, per side"),
    Param("k_vu_diff_groove_d", 0.6, 0.3, 0.9, "choice", "depth of the light-break groove on the back face, one per web between wedges"),
    Param("k_vu_diff_groove_margin", 0.45, 0.40, 0.60, "choice", "web left either side of a groove, in mm, measured at k_vu_r0 where the web is narrowest. In mm and not degrees because the web narrows with radius and the inner end is what pinches"),
    Param("k_vu_diff_groove_min", 0.40, 0.35, 0.60, "choice", "narrowest groove worth cutting - one nozzle width. Below this the disc comes out plain and the wall's webs do the segmenting on their own"),
    Param("k_vu_diff_over", 1.0, 0.5, 2.0, "choice", "how far a groove runs past the wedges at each end, radially"),
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
    # the face's furniture, derived so it follows the lid rather than sitting in
    # the part file as loose numbers    # the sticker: what to print, and where it sits
    D["cass_sticker_l"] = D["lid_l"] - 2 * v["cass_sticker_margin"]
    D["cass_sticker_w"] = D["lid_w"] - 2 * v["cass_sticker_margin"]
    D["cass_sticker_r"] = max(D["tray_inner_r"] + D["lid_seat"] - v["cass_sticker_margin"], 0.5)
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

    # ------------------------------------------------------------------
    # Vertical-slot player. Distances `f_*` are measured from the front
    # outer face toward the back; y = f - s_W/2. The tape stands on its long
    # edge, label to the front, card side to the back, where the module's
    # flat back presses against the wall behind the slot. Components, header
    # and Dupont tails all face the back. The D1 mini lies flat on the lid
    # to the LEFT of the module, USB out of the left wall. The buzzer sits
    # under the slot floor at the right. Bottom lid, four M3 screws up into
    # posts hanging from the roof.
    # ------------------------------------------------------------------
    D["s_slot_l"] = v["cassette_l"] + 2 * v["s_slot_clr"]
    D["s_slot_w"] = v["cassette_h"] + 2 * v["s_slot_clr"]
    # the body is as long as the slot plus its margins, OR as long as the D1 mini
    # beside the module pocket needs (wall, lip, clearance, board, clearance, lip,
    # a 0.5 mm gap, then the module's side rib), whichever is more - so a thicker
    # wall grows the body instead of squeezing the board against the rib
    # The board stands UPRIGHT BEHIND the module, not flat beside it. Beside it,
    # a 55 mm ESP32 had to clear the module's half-width as well as its own
    # length, and that drove s_L to 169.5 - a body 41.6 mm longer than the slot
    # needs, to house one board. Behind the module it may overlap it in X, so
    # all it asks of the length is its own 55 plus the walls, and the slot gets
    # the body back at 127.9 (Samuel, 2026-09-19: "keep the width at 127.9").
    brd_needs = 2 * (v["wall"] + v["s_mount_gap"] + v["lip_t"] + v["pcb_clr"]) + v["esp_l"]
    D["s_L"] = max(D["s_slot_l"] + 2 * v["s_side_margin"], brd_needs)
    # the lid carries the screws, so it is as thick as a counterbored head needs,
    # never the shared `floor`: a 2.4 mm plate with a 2.5 mm head recess is a hole
    D["s_lid_t"] = max(v["floor"], v["screw_head_h"] + v["s_lid_under_head"])
    # the lid drops into a pocket in the bottom of the body and finishes flush with
    # it; the ledge is the rim of wall that continues down past it, and the step
    # from pocket to cavity is the seat the lid stops against
    D["s_lid_ledge"] = min(v["s_lid_ledge"], v["wall"] - 0.8)
    D["s_tail"] = max(v["pn532_comp_h"], v["pin_below"] + v["dupont_h"])
    # The ring lives between the front wall and the slot block, so the slot -
    # and everything behind it - moves back by the ring's stack plus the 0.5 mm
    # the block overlaps the front wall by. The body gets deeper; nothing else
    # about the face changes.
    D["s_ring_depth"] = v["s_ring_air"] + v["s_ring_led_h"] + v["s_ring_t"] + v["s_ring_clr"]
    D["f_slot0"] = v["wall"] + D["s_ring_depth"] + 0.5
    D["f_slot1"] = D["f_slot0"] + D["s_slot_w"]
    D["f_pcb0"] = D["f_slot1"] + v["s_module_wall"]
    D["f_pcb1"] = D["f_pcb0"] + v["pn532_t"]
    D["f_tail1"] = D["f_pcb1"] + D["s_tail"]
    # Behind the tails, lying flat. Standing it on edge was 12 mm shallower and
    # wrong: the DevKit's header rows run along its two LONG edges, so on edge
    # one whole row points down into whatever holds it. Flat, the board keeps
    # the posts-and-lips mount that already works and the pins face up.
    D["f_brd_0"] = D["f_tail1"] + v["cavity_clr"]
    D["f_brd_1"] = D["f_brd_0"] + v["esp_w"]
    # the back wall clears whichever is deeper: the module's tails plus air, or the
    # D1 mini's lips plus the gap the lid needs to drop past them
    D["f_back_inner"] = max(D["f_tail1"] + v["cavity_clr"],
                            D["f_brd_1"] + v["pcb_clr"] + v["lip_t"] + v["s_mount_gap"])
    D["s_W"] = D["f_back_inner"] + v["wall"]
    yof = -D["s_W"] / 2.0
    for k in ("f_slot0", "f_slot1", "f_pcb0", "f_pcb1", "f_tail1", "f_brd_0", "f_brd_1", "f_back_inner"):
        D["y" + k[1:]] = D[k] + yof              # y_slot0, y_slot1, y_pcb0 ...
    D["s_H"] = D["s_lid_t"] + v["s_shelf_h"] + v["pn532_w"] + v["cavity_clr"] + v["s_roof"]
    D["s_plate_top_z"] = D["s_H"] - v["s_slot_depth"]
    D["s_plate_bot_z"] = D["s_plate_top_z"] - v["s_slot_floor"]
    D["s_roof_z"] = D["s_H"] - v["s_roof"]        # underside of the roof
    D["s_proud"] = v["cassette_w"] - v["s_slot_depth"]
    D["s_cavity_l"] = D["s_L"] - 2 * v["wall"]
    D["s_cavity_w"] = D["s_W"] - 2 * v["wall"]
    # The cavity's inner fillet is what pinches a lid mount whose corner reaches
    # the wall: a square corner cannot sit in a round one. Keep the fillet no
    # bigger than the gap the mounts already stand off by, and the corners stop
    # being the binding constraint (the wall just gets thicker at the corners).
    D["s_cavity_r"] = min(max(v["corner_r"] - v["wall"], 0.6), max(v["s_mount_gap"], 0.6))
    # the ring, measured back from the inside of the front wall
    D["s_ring_led_y"] = -D["s_W"] / 2 + v["wall"] + v["s_ring_air"]   # LED tops
    D["s_ring_y0"] = D["s_ring_led_y"] + v["s_ring_led_h"]            # board, front face
    D["s_ring_y1"] = D["s_ring_y0"] + v["s_ring_t"]                   # board, back face
    D["s_pcb_bot_z"] = D["s_lid_t"] + v["s_shelf_h"]
    D["s_pcb_top_z"] = D["s_pcb_bot_z"] + v["pn532_w"]
    D["s_rail_x"] = v["pn532_l"] / 2 + v["pcb_clr"] + v["s_keeper"] / 2   # side rib centre
    D["s_rail_y0"] = D["y_slot1"]
    D["s_rail_y1"] = D["y_pcb1"] + v["pcb_clr"] + v["s_keeper"]
    # the lips sit BEHIND the PCB plane, in the band just clear of its back face,
    # and reach over the top / bottom edge strips only - never over a component
    D["s_lip_y"] = D["y_pcb1"] + v["pcb_clr"] + v["s_keeper"] / 2
    D["s_lip_top_z0"] = D["s_roof_z"] - v["cavity_clr"] - v["s_lip_engage"]     # bottom of the top lip
    D["s_lip_bot_z1"] = D["s_lid_t"] + v["s_shelf_h"] + v["s_lip_engage"]          # top of the bottom lip
    D["s_click_z"] = D["s_plate_top_z"] + 0.3 + v["s_click_up"]
    D["s_click_bite"] = v["s_click_r"] - v["s_slot_clr"]      # what the tape actually feels
    # how much of the tape the two ridges displace: a circular segment of depth
    # s_click_bite on each, twice. The fit check expects exactly this much
    # overlap and nothing more - the detent is the ONE place the player is
    # meant to touch the tape, so it is measured, not excused.
    _d, _r = D["s_click_bite"], v["s_click_r"]
    _seg = _r ** 2 * math.acos((_r - _d) / _r) - (_r - _d) * math.sqrt(max(2 * _r * _d - _d ** 2, 0.0))
    D["s_click_volume"] = 2 * _seg * v["s_click_len"]
    D["s_antenna_to_card"] = v["s_module_wall"] + v["pn532_t"] + v["shell_floor"] + v["s_slot_clr"] + v["pcb_clr"]
    # D1 mini: long side along X, against the left wall (USB out through it); the
    # gap to the module's side rib is what the sweep checks
    # Hard against the left wall, not centred. Centred, the board's USB socket
    # sat 22 mm inside the wall its cutout is in - the hole was there and the
    # plug could not reach it (Samuel, 2026-09-19: "move the location of the
    # Node MCU to the edge so that it can be plugged in easier"). Behind the
    # module it can sit anywhere across the width, so it sits where the cable
    # can get to it.
    D["s_brd_cx"] = -(D["s_cavity_l"] / 2 - v["s_mount_gap"] - v["pcb_clr"] - v["lip_t"] - v["esp_l"] / 2)
    D["s_brd_cy"] = (D["y_brd_0"] + D["y_brd_1"]) / 2
    # Beside the module, the number that mattered was the gap to its side rib.
    # Behind it, the board may sit over those ribs in X and what matters instead
    # is that it clears the tails in Y and stays inside the cavity in X.
    D["s_brd_tail_gap"] = D["y_brd_0"] - D["y_tail1"]
    D["s_brd_end_gap"] = D["s_cavity_l"] / 2 - (v["esp_l"] / 2 + v["esp_end_block"])
    D["s_brd_board_z"] = D["s_lid_t"] + v["esp_standoff"]
    D["s_brd_top_edge_z"] = D["s_brd_board_z"] + v["esp_t"]
    mount = v["pcb_clr"] + v["lip_t"]
    D["s_brd_mount_l"] = v["esp_l"] + 2 * mount
    D["s_brd_mount_w"] = v["esp_w"] + 2 * mount
    D["s_brd_top_z"] = D["s_brd_board_z"] + v["esp_t"] + v["esp_top_h"]
    D["s_usb_cz"] = D["s_brd_board_z"] + v["esp_t"] / 2 + 1.5
    # buzzer on the lid in the back zone, right of the module; sound holes through the right wall
    D["s_buzzer_cx"] = 40.0
    D["s_buzzer_cy"] = (D["y_pcb0"] + D["y_back_inner"]) / 2
    D["s_buzzer_top_z"] = D["s_lid_t"] + 3.0 + v["buzzer_d"] * 0.8     # ring 3 tall, buzzer ~9.6 tall
    # front face furniture. Through-holes (LED) stay below the slot floor plate;
    # the cosmetics only add material or dent the 2.4 mm wall by k_dimple, so
    # they may sit anywhere on the face.
    D["s_led_cx"], D["s_led_cz"] = -49.5, 8.0        # as far left as the front-left screw post allows
    # ...which is set by the WORST sweep corner, not nominal: a thick wall grows
    # s_L through brd_needs but pulls the post inward faster, and at wall 3.0 with
    # the tightest clearances -51.0 left 0.05 mm between the LED body and the post
    D["s_buttons_x0"], D["s_buttons_pitch"], D["s_buttons_cz"] = -39.5, v["k_key_w"] + 2.0, 9.0
    D["k_knob_big_c"] = (-48.0, 30.0)            # volume, top-left
    D["k_knob_small_c"] = (-30.0, 30.0)          # tuning, next to it
    D["k_counter_c"], D["k_counter_w"], D["k_counter_h"] = (-8.0, 30.0), 22.0, 8.0   # tape counter window
    # the dial, right of centre: far enough in that the bezel clears the corner radius
    D["k_vu_c"] = (36.5, 25.0)
    D["k_vu_bezel_od"] = 2 * v["k_vu_r1"] + 2 * 1.5 + 2 * v["k_vu_bezel_w"]
    # the diffuser: a disc in the dish, standing k_vu_diff_t - k_dimple off the
    # face and so still sunk below the bezel rim. The grooves follow the webs, so
    # they are annular sectors, not straight slots: at r0 the web is only
    # radians(gap) * r0 wide and a straight slot would open into a wedge.
    D["k_vu_diff_r"] = D["k_vu_bezel_od"] / 2 - v["k_vu_bezel_w"] - v["k_vu_diff_clr"]
    # The disc drops into the dial's dish, which is k_dimple deep, and must never
    # stand above the bezel rim - so the bezel, not the wish, sets the thickness.
    # Clamping here rather than deepening the dish keeps the BODY untouched: the
    # diffuser is a new part, not a change to the player.
    D["k_vu_diff_t_eff"] = min(v["k_vu_diff_t"], v["k_dimple"] + v["k_vu_bezel_proud"] - 0.2)
    D["k_vu_diff_proud"] = D["k_vu_diff_t_eff"] - v["k_dimple"]
    D["k_vu_diff_groove_d_eff"] = min(v["k_vu_diff_groove_d"], D["k_vu_diff_t_eff"] - 0.4)
    D["k_vu_diff_web"] = v["k_vu_r1"] * math.radians(v["k_vu_gap_deg"])      # web arc at the outer radius
    # the groove is whatever is left of the web after a margin each side, measured
    # at k_vu_r0 where the web pinches. If that leaves less than a nozzle, the
    # disc comes out plain rather than carrying a groove the slicer would drop.
    D["k_vu_diff_web0"] = math.radians(v["k_vu_gap_deg"]) * v["k_vu_r0"]
    D["k_vu_diff_groove_w0"] = D["k_vu_diff_web0"] - 2 * v["k_vu_diff_groove_margin"]
    D["k_vu_diff_grooved"] = (D["k_vu_diff_groove_w0"] >= v["k_vu_diff_groove_min"]
                              and D["k_vu_diff_groove_d_eff"] >= 0.2)
    D["k_vu_diff_groove_half"] = (D["k_vu_diff_groove_w0"] / 2) / v["k_vu_r0"] if D["k_vu_diff_grooved"] else 0.0
    D["k_vu_diff_groove_r0"] = max(v["k_vu_r0"] - v["k_vu_diff_over"], 1.0)
    D["k_vu_diff_groove_r1"] = min(v["k_vu_r1"] + v["k_vu_diff_over"], D["k_vu_diff_r"] - 0.4)
    # the tightest place on a groove: the web is narrowest at the inner radius
    D["s_ring_cx"], D["s_ring_cz"] = D["k_vu_c"]
    # anything standing in the ring's hole stays inside this radius
    D["s_dot_fin_r"] = v["s_ring_id"] / 2 - v["s_ring_clr"]
    # the lid's two posts sit under the rim, off to each side; their tops follow
    # the circle, or they would hold the board 2 mm below where it belongs
    D["s_ring_post_dx"] = v["s_ring_od"] * 0.26
    # measured at the post's INNER edge: across the post's width the rim is
    # lowest nearest the middle of the disc, so that edge is what sets the top.
    # (The centre gives a top 1.2 mm too high, the outer edge 3.1 mm too high;
    # both drive a corner of the post through the board.)
    _pe = D["s_ring_post_dx"] - v["s_ring_post_w"] / 2
    D["s_ring_post_top"] = D["s_ring_cz"] - ((v["s_ring_od"] / 2) ** 2 - _pe ** 2) ** 0.5
    D["s_ring_rib_x"] = v["s_ring_od"] / 2 + v["s_ring_clr"] + v["s_ring_rib"] / 2
    D["k_rec_c"] = (12.0, 30.0)                  # "REC" lamp recess
    # screw posts: front-left, front-right, back-right, back-middle (x = 0 sits between
    # the module tails and the back wall, which the D1 mini's depth makes deep enough)
    px = D["s_L"] / 2 - v["wall"] - v["post_d"] / 2 - 0.5
    py = D["s_W"] / 2 - v["wall"] - v["post_d"] / 2 - 0.5
    # The fourth post used to sit at the middle of the back, which was empty
    # while the board lay beside the module. The board is across the back now,
    # so the post moves out past its mount rather than standing through it.
    D["s_post4_x"] = D["s_brd_cx"] + D["s_brd_mount_l"] / 2 + v["post_d"] / 2 + 1.0
    D["s_posts"] = [(-px, -py), (px, -py), (px, py), (D["s_post4_x"], py)]
    D["s_pocket_l"] = D["s_L"] - 2 * D["s_lid_ledge"]
    D["s_pocket_w"] = D["s_W"] - 2 * D["s_lid_ledge"]
    D["s_pocket_r"] = max(v["corner_r"] - D["s_lid_ledge"], 0.6)
    D["s_lid_l"] = D["s_pocket_l"] - 2 * v["s_lid_clr"]
    D["s_lid_w"] = D["s_pocket_w"] - 2 * v["s_lid_clr"]
    D["s_lid_r"] = max(D["s_pocket_r"] - v["s_lid_clr"], 0.4)
    # two zip-tie stations across the board, inboard of the corner lips. The slot
    # is tie_w long (X) and tie_t wide (Y), both plus clearance; the back slot is
    # centred in the gap between the board's edge and the cavity wall, the front
    # one just outside the lip line where there is room to spare.
    D["s_tie_slot_l"] = v["tie_w"] + 2 * v["tie_clr"]
    D["s_tie_slot_w"] = v["tie_t"] + 2 * v["tie_clr"]
    D["s_tie_groove_d"] = v["tie_t"] + v["tie_clr"]
    D["s_tie_span"] = v["s_tie_span_frac"] * v["esp_l"]
    D["s_tie_x"] = [D["s_brd_cx"] - D["s_tie_span"] / 2, D["s_brd_cx"] + D["s_tie_span"] / 2]
    D["s_tie_y_front"] = (D["y_brd_0"] - v["pcb_clr"] - v["lip_t"] - 0.4 - D["s_tie_slot_w"] / 2)
    # centred in the rise gap, but pulled inboard if that would crowd the lid's
    # own edge; the slot may overhang the board, there is d1_standoff under it
    D["s_tie_y_back"] = min((D["y_brd_1"] + D["s_cavity_w"] / 2) / 2,
                            D["s_lid_w"] / 2 - 1.0 - D["s_tie_slot_w"] / 2)
    D["s_tie_rise_gap"] = D["s_cavity_w"] / 2 - D["y_brd_1"]          # room for the strap to stand up
    D["s_tie_lip_free"] = v["esp_l"] / 2 + v["pcb_clr"] + v["lip_t"] - (v["ledge"] + v["pcb_clr"] + v["lip_t"])
    D["s_screw_in_post"] = v["screw_len"] - (D["s_lid_t"] - v["screw_head_h"])
    D["s_pilot_depth"] = D["s_screw_in_post"] + 2.0
    return D
