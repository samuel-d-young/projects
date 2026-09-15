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
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import params  # noqa: E402
from _lib import emit, write_manifest  # noqa: E402
from cassette import build_lid, build_tray  # noqa: E402
from player import build_base, build_top  # noqa: E402


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
    return bad


def build_all(D: dict):
    return {"cassette_tray": build_tray(D), "cassette_lid": build_lid(D),
            "player_base": build_base(D), "player_top": build_top(D)}


def valid(part) -> bool:
    """build123d made is_valid a property in 0.9; older releases had a method."""
    v = part.is_valid
    return bool(v() if callable(v) else v)


def main() -> int:
    quick = "--quick" in sys.argv
    v = params.nominal()
    D = params.derive(v)
    print(f"player {D['L']:.1f} x {D['W']:.1f} x {D['H']:.1f} mm, cassette {v['cassette_l']} x {v['cassette_w']} x {v['cassette_h']}, "
          f"antenna to card {D['antenna_to_card']:.1f} mm, cavity {D['cavity_h']:.1f} mm")
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
    emit(parts["player_top"], "player_top", "bay side up", note="4 x M3 x 10 pan head from the top")
    write_manifest()
    print(f"  nominal built and exported in {time.time() - t0:.0f} s")
    if quick:
        return 0

    # corner sweep over the parameters that actually move the geometry
    sweep = ["wall", "bay_clr", "pcb_clr", "pn532_comp_h", "d1_top_h", "card_clr", "cassette_corner_r"]
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
