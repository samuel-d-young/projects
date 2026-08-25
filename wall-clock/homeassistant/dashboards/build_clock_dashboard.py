#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_clock_dashboard.py — generate the Wall Clock "Settings" view.

WHY THIS IS GENERATED RATHER THAN HAND-EDITED
---------------------------------------------
Every control on a clock is an ESPHome entity, and ESPHome derives entity ids
from the device name. So a second clock does not share entities with the first
— `mini_round_clock_hour_hue` and `kitchen_clock_hour_hue` are different
entities, and no Home Assistant card can abstract over that natively.

That leaves one honest option: one set of cards per clock, each shown only when
that clock is picked. Written by hand it is N copies of ~60 rows to keep in
sync, and it will drift the first time a control is added. Generated, adding a
clock is one line in CLOCKS below.

The picker is `input_select.wall_clock_target`, defined in
packages/wall_clock_ui.yaml. Card-level `visibility` does the switching, which
is core Home Assistant — no HACS card needed.

USAGE
-----
    python build_clock_dashboard.py            # writes wall-clock-settings-cards.json
    python build_clock_dashboard.py --names    # just print the picker options

Then install with jq (see the wall-clock BUILD-LOG for the exact command).
"""

import json, io, sys

# -----------------------------------------------------------------------------
# THE CLOCKS
# -----------------------------------------------------------------------------
# slug  : the ESPHome entity prefix — device `name:` with hyphens as underscores.
#         `name: mini-round-clock` -> entities `*.mini_round_clock_*`.
# label : what you see in the picker. Free text; rename freely, it is only a
#         label. Changing `slug` means renaming the device in ESPHome and
#         reflashing, because it is the entity id.
CLOCKS = [
    {"slug": "mini_round_clock", "label": "Mini Round Clock"},
    # {"slug": "kitchen_clock",  "label": "Kitchen"},
]

PICKER = "input_select.wall_clock_target"


def vis(label):
    """Show a card only while the picker is on this clock."""
    return [{"condition": "state", "entity": PICKER, "state": label}]


def row(entity, name):
    return {"entity": entity, "name": name}


def section(label):
    return {"type": "section", "label": label}


def clock_cards(slug, label):
    e = lambda domain, suffix: "%s.%s_%s" % (domain, slug, suffix)
    v = vis(label)

    ring = {
        "type": "entities", "title": "%s — Ring" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("number", "ring_led_count"), "LED count"),
            row(e("number", "twelve_o_clock_offset"), "Twelve o'clock offset"),
            row(e("select", "mode"), "Mode"),
            section("Hands"),
            row(e("select", "second_hand_style"), "Second hand"),
            row(e("switch", "second_hand"), "Show second hand"),
            section("Markers"),
            row(e("select", "hour_markers"), "Markers"),
            row(e("number", "hour_marker_brightness"), "Marker brightness"),
            section("Timer + status"),
            row(e("select", "timer_countdown_style"), "Countdown style"),
            row(e("select", "timer_arc_direction"), "Arc direction"),
            row(e("switch", "show_extra_timer_pips"), "Extra timer pips"),
            row(e("switch", "show_status_hints"), "Status hints"),
            row(e("number", "status_pixel_brightness"), "Status brightness"),
        ],
    }

    colour_note = {
        "type": "markdown", "visibility": v,
        "content": (
            "### %s — Colour\n"
            "The presets **default, warm, cool, mono** ignore the sliders below. "
            "Set **Theme** to **custom** first, then they apply immediately, no reflash.\n\n"
            "*Intensity* is the ring's brightness for that element, not the screen's — "
            "the screen reuses the same hue at its own brightness, because a bare LED "
            "and a backlit panel don't want the same value.\n\n"
            "Status **pips** follow the timer arc at 62%% and have no separate control. "
            "**mono** pins every saturation to zero and is the accessible palette."
        ) % label,
    }

    ents = [row(e("select", "colour_theme"), "Theme")]
    for pfx, lbl in (("hour", "Hour hand"), ("minute", "Minute hand"),
                     ("second", "Second hand"), ("timer", "Timer arc")):
        ents += [section(lbl),
                 row(e("number", "%s_hue" % pfx), "Hue"),
                 row(e("number", "%s_saturation" % pfx), "Saturation"),
                 row(e("number", "%s_intensity" % pfx), "Intensity")]
    colour = {"type": "entities", "title": "%s — Colour" % label,
              "show_header_toggle": False, "state_color": True,
              "visibility": v, "entities": ents}

    screen = {
        "type": "entities", "title": "%s — Screen" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("switch", "display"), "Screen on"),
            row(e("select", "face"), "Face"),
            row(e("switch", "24_hour_time"), "24 hour time"),
            row(e("select", "digital_time_size"), "Digital time size"),
            section("On an analogue face"),
            row(e("select", "digital_time_on_analog"), "Digital time"),
            section("While a timer runs"),
            row(e("select", "screen_during_a_timer"), "Screen shows"),
            section("Subtitle lines"),
            row(e("switch", "show_date"), "Date"),
            row(e("switch", "show_day_of_week"), "Day of week"),
            row(e("switch", "show_weather"), "Weather"),
            section("Background"),
            row(e("number", "weather_tint_strength"), "Weather tint"),
        ],
    }

    alert = {
        "type": "entities", "title": "%s — Alert" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("select", "alert_pattern"), "Pattern"),
            row(e("number", "alert_hue"), "Hue"),
        ],
    }

    bright = {
        "type": "entities", "title": "%s — Brightness" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("light", "backlight"), "Backlight"),
            row(e("number", "brightness"), "Day brightness"),
            section("Night"),
            row(e("switch", "auto_dim_at_night"), "Auto dim"),
            row(e("number", "night_brightness"), "Night brightness"),
            row(e("number", "night_starts"), "Night starts"),
            row(e("number", "night_ends"), "Night ends"),
            row(e("switch", "blank_screen_at_night"), "Blank screen at night"),
        ],
    }

    return [ring, colour_note, colour, screen, alert, bright]


def build():
    cards = [
        {
            "type": "markdown",
            "content": (
                "### Which clock\n"
                "Pick a clock and every card below switches to it. The picker is "
                "`input_select.wall_clock_target`.\n\n"
                "Adding another clock: give it a different `name:` in ESPHome (that "
                "sets its entity prefix, hostname and OTA target), add it to `CLOCKS` "
                "in `build_clock_dashboard.py`, and to the options of the input_select."
            ),
        },
        {
            "type": "entities", "show_header_toggle": False,
            "entities": [row(PICKER, "Customising")],
        },
        # Timers are Home Assistant's, not any one clock's — the pool is shared,
        # so this card is deliberately outside the per-clock switching.
        {
            "type": "entities", "title": "Timers (shared)",
            "show_header_toggle": False, "state_color": True,
            "entities": [
                row("sensor.wall_clock_timer_slots", "Slots in use"),
            ] + [row("timer.wall_clock_%d" % i, "Timer %d" % i) for i in range(1, 6)],
        },
    ]
    for c in CLOCKS:
        cards += clock_cards(c["slug"], c["label"])
    return cards


if __name__ == "__main__":
    if "--names" in sys.argv:
        for c in CLOCKS:
            print(c["label"])
        raise SystemExit(0)
    cards = build()
    io.open("wall-clock-settings-cards.json", "w", encoding="utf-8",
            newline="\n").write(json.dumps(cards, indent=2))
    print("clocks: %d   cards: %d" % (len(CLOCKS), len(cards)))
    for c in CLOCKS:
        print("  %-22s -> %s" % (c["label"], c["slug"]))
