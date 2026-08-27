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
            row(e("switch", "ring_leds"), "Ring LEDs on"),
            section("Hands"),
            row(e("select", "second_hand_style"), "Second hand"),
            row(e("switch", "ring_second_hand"), "Show second hand"),
            section("Markers"),
            row(e("select", "ring_hour_markers"), "Markers"),
            row(e("number", "hour_marker_brightness"), "Marker brightness"),
            section("Timer + status"),
            row(e("select", "timer_countdown_style"), "Countdown style"),
            row(e("select", "timer_arc_direction"), "Arc direction"),
            row(e("switch", "show_extra_timer_pips"), "Extra timer pips"),
            row(e("switch", "show_status_hints"), "Status hints"),
            row(e("number", "status_pixel_brightness"), "Status brightness"),
            # One switch per ambient pixel. The master above still turns the
            # whole group off; these decide which of the four you keep.
            row(e("switch", "status_bin_night"), " Bin night (12 o'clock)"),
            row(e("switch", "status_garage_open"), " Garage open (3 o'clock)"),
            row(e("switch", "status_driveway"), " Driveway (9 o'clock)"),
            row(e("switch", "status_who_is_home"), " Who is home (6 o'clock)"),
        ],
    }

    # Sam asked, in as many words: "what else is showing on the LED ring. The
    # hours, minutes, seconds and what else?" This is the whole answer, on the
    # page where the switches are, rather than in a document he has to find.
    ring_note = {
        "type": "markdown", "visibility": v,
        "content": (
            "### %s — everything the ring can light\n"
            "| what | where | colour | switch |\n|---|---|---|---|\n"
            "| Hour hand | the hour | orange | always on |\n"
            "| Minute hand | the minute | blue | always on |\n"
            "| Second hand | the second | grey | *Show second hand* |\n"
            "| Hour markers | all twelve | dim blue-white | *Markers* |\n"
            "| Timer arc | from 12 | teal | only while a timer runs |\n"
            "| Timer pips | where each one finishes | dim teal | *Extra timer pips* |\n"
            "| Bin night | 12 o'clock | breathing green, yellow for recycling | *Bin night* |\n"
            "| Garage open | 3 o'clock | amber | *Garage open* |\n"
            "| Driveway | 9 o'clock | blinking red | *Driveway* |\n"
            "| Who is home | either side of 6 | Sam **blue**, Laura magenta, "
            "Amanda green, Zac amber | *Who is home* |\n"
            "| Home Assistant dropped | 6 o'clock | dim red | automatic |\n\n"
            "**A single blue dot just left of 6 o'clock is Sam's presence pixel.** "
            "The twelve hour markers are faintly blue too, but they are dim and "
            "there are twelve of them, so one blue dot is the presence one."
        ) % label,
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
            row(e("switch", "display"), "Everything on (master)"),
            row(e("switch", "screen_on"), "Screen on"),
            row(e("select", "screen"), "Which panel"),
            row(e("select", "face"), "Face"),
            row(e("select", "screen_hour_markers"), "Hour markers"),
            row(e("switch", "screen_second_hand"), "Second hand"),
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
            row(e("number", "alert_shows_for"), "Clock shows it for"),
            section("The alarm itself"),
            row("input_button.wall_clock_timer_dismiss", "Dismiss the alarm"),
            row("input_number.wall_clock_alert_repeat_seconds", "Re-announce every"),
            row("input_number.wall_clock_alert_repeat_max", "Repeats (0 = until cancelled)"),
        ],
    }

    alert_note = {
        "type": "markdown", "visibility": v,
        "content": (
            "The **alarm** sounds until it is cancelled — the dismiss button "
            "above, saying *stop the timer*, or starting another one.\n\n"
            "**Clock shows it for** is only how long the ring and the screen keep "
            "flashing if nothing cancels it. A cancel clears them instantly either "
            "way. Set it to 0 and the lights last exactly as long as the sound."
        ),
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

    return [ring, ring_note, colour_note, colour, screen, alert, alert_note, bright]


def build():
    cards = [
        # WHICH CLOCK YOU ARE EDITING, made obvious rather than inferred.
        # This used to be a markdown paragraph over a dropdown row, which told
        # you the picker's entity id but not which clock was live, and took
        # three taps to change. Now: the name in a heading, one button per
        # clock, and the device's own status underneath so you can see you are
        # editing something that is actually on the network.
        {
            "type": "markdown",
            "content": (
                "# {{ states('input_select.wall_clock_target') }}\n"
                "Everything below is this clock. Tap another button to switch."
            ),
        },
        {
            "type": "horizontal-stack",
            "cards": [
                {
                    "type": "button",
                    "name": c["label"],
                    "icon": "mdi:clock-outline",
                    "show_state": False,
                    "tap_action": {
                        "action": "perform-action",
                        "perform_action": "input_select.select_option",
                        "target": {"entity_id": PICKER},
                        "data": {"option": c["label"]},
                    },
                }
                for c in CLOCKS
            ],
        },
        # The status line degrades rather than erroring: a device that has never
        # been adopted has no *_status entity at all, and a dashboard that shows
        # "unknown" is more use than one that shows a red error card.
        {
            "type": "markdown",
            "content": "".join(
                "{%% set s = 'binary_sensor.%s_status' %%}"
                "{%% if is_state('%s', '%s') %%}"
                "**%s** &mdash; "
                "{%% if is_state(s, 'on') %%}online"
                "{%% elif is_state(s, 'off') %%}**offline** (changes will not reach it)"
                "{%% else %%}status unknown &mdash; not adopted yet?{%% endif %%}"
                "{%% endif %%}" % (c["slug"], PICKER, c["label"], c["label"])
                for c in CLOCKS
            ),
        },
        {
            "type": "entities", "show_header_toggle": False,
            "entities": [row(PICKER, "Customising")],
        },
        {
            "type": "markdown",
            "content": (
                "Adding another clock: give it a different `name:` in ESPHome (that "
                "sets its entity prefix, hostname and OTA target), add it to `CLOCKS` "
                "in `build_clock_dashboard.py`, and to the options of the input_select."
            ),
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
