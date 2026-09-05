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
# tier : which firmware is on it, because they do not expose the same entities.
#        "full"  = mini-round-clock-with-display.yaml -- 17 switches, 13 selects,
#                  23 numbers. Gets every card.
#        "basic" = mini-round-clock.yaml / test-clock-d1mini.yaml /
#                  wall-clock.yaml -- Display, Mode, Brightness, Night
#                  brightness, and a Backlight on the ones that have a panel.
#                  Handing these the full card set is what produces a screen of
#                  "Entity not found": the entities are not missing, they were
#                  never compiled in.
# THE NAMES ARE SAM'S CHILDREN'S, and the slugs are not. A slug is the ESPHome
# entity prefix and changing it means a reflash; a label is free text and is
# what the picker shows. So the devices stay mini_round_clock_3 and _4 -- which
# is also what keeps every generated card working -- and only the labels moved.
# They match the device names in Home Assistant, renamed there with name_by_user
# on 2026-09-05, which likewise does not disturb entity ids.
#
# THREE, not four. Sam, 2026-09-05: "There are not 2 screens there are 3." The
# two dead entries (Mini Round Clock, Mini Round Clock 2 -- boards that have not
# answered since 2026-08-31) were deleted from Home Assistant, and the D1 mini
# test clock has never existed as a device. What is left is two flashed clocks
# and one Sam has yet to flash.
CLOCKS = [
    # 24 LED. COM11, 192.168.1.69, ac:27:6e:a3:3b:ac.
    {"slug": "mini_round_clock_3", "label": "Zac's Clock", "tier": "full",
     "backlight": True},
    # 32 LED. COM10, 192.168.1.68, ac:27:6e:a3:de:6c -- the rewired Flight Deck.
    {"slug": "mini_round_clock_4", "label": "Jake's Clock", "tier": "full",
     "backlight": True},
    # NOT FLASHED YET. Sam, 2026-09-05: "Their is a third clock that I will
    # flash at a later stage." It costs nothing to list: every card is gated on
    # binary_sensor.mini_round_clock_status, so until the board is on the
    # network the picker offers it and the "not connected" notice is all that
    # renders. The slug is the bare prefix because deleting the two dead config
    # entries freed it -- flash the third board with `-s device_name
    # mini-round-clock` and it lands here with no further edits.
    # Rename the label when it has a name.
    {"slug": "mini_round_clock", "label": "Third Clock", "tier": "full",
     "backlight": True},
]

PICKER = "input_select.wall_clock_target"

# How many columns the Settings view is laid out in, and how tall a card is
# reckoned to be when balancing them. The height is an estimate on purpose:
# what matters is the ORDER cards go into columns, and a row count gets that
# right without pretending to know the rendered pixel height of a slider on
# whatever phone is being used.
MAX_COLS = 3


def card_rows(c):
    if c.get("type") == "entities":
        return 1 + len(c.get("entities", []))
    if c.get("type") == "markdown":
        return max(3, len(c.get("content", "")) // 90)
    return 2


def vis(label, slug=None):
    """Show a card only while the picker is on this clock AND the clock is there.

    The second condition is what stops this dashboard filling with yellow
    "Entity not found" boxes. A clock that has never been flashed, or that is
    off the network, has no entities for these cards to bind to -- and an
    entities card renders one error row per missing entity, which looks like
    twenty faults instead of one absent device.

    `binary_sensor.<slug>_status` comes from `platform: status` in the clock's
    firmware. It is NOT created automatically -- an earlier version of this
    docstring said the ESPHome integration makes one for every adopted device,
    and that is wrong (ESPHome docs, checked 2026-09-03: the status binary
    sensor is opt-in). It matters because the failure is silent: the condition
    on a missing entity is false, so a firmware without it renders this whole
    view BLANK rather than filling it with "Entity not found" rows. Any clock
    added to CLOCKS must be running firmware that declares it. The status line
    at the top of the view is NOT gated this way, so there is always something
    on screen saying why the rest is missing.
    """
    c = [{"condition": "state", "entity": PICKER, "state": label}]
    if slug:
        c.append({"condition": "state",
                  "entity": "binary_sensor.%s_status" % slug, "state": "on"})
    return c


def row(entity, name):
    return {"entity": entity, "name": name}


def section(label):
    return {"type": "section", "label": label}


def absent_card(slug, label):
    """Shown INSTEAD of a clock's controls when that clock is not there.

    Gating the controls on `binary_sensor.<slug>_status` stops a page full of
    yellow "Entity not found" rows, which is what Sam asked for -- but on its
    own it replaces them with nothing at all, and a clock that silently
    vanishes from its own picker is its own kind of wrong. The bench session
    raised exactly this when it declined to paste the gated view over the live
    one: clocks 1 and 2 would disappear rather than read as unavailable.

    So each clock gets this, on the opposite condition. `state_not` is true
    both when the sensor exists and is off (flashed, off the network) and when
    the entity does not exist at all (never flashed) -- a missing entity has
    no state, and no state is not "on". That second case is the one that
    matters for clocks 1 and 2 today, and it is the case I can least verify
    from here, so if it turns out that a missing entity renders nothing, this
    card is no worse than the blank it replaces.
    """
    return {
        "type": "markdown",
        "visibility": [
            {"condition": "state", "entity": PICKER, "state": label},
            {"condition": "state", "entity": "binary_sensor.%s_status" % slug,
             "state_not": "on"},
        ],
        "content": (
            "### %s is not connected\n\n"
            "Its controls are hidden because the device is not on the network, "
            "so every one of them would read *Entity not found*.\n\n"
            "If it is powered and on wifi, it needs flashing with firmware that "
            "declares the status sensor (`binary_sensor: platform: status`) "
            "before this page can tell it apart from a clock that is simply "
            "absent." % label
        ),
    }


def basic_cards(slug, label, backlight):
    """Everything a `basic` firmware actually exposes, and nothing it does not.

    mini-round-clock.yaml, test-clock-d1mini.yaml and wall-clock.yaml compile
    four controls between them. Listing more would not "reveal" anything -- the
    entity does not exist on the device, and the card says so in yellow.
    """
    e = lambda domain, suffix: "%s.%s_%s" % (domain, slug, suffix)
    v = vis(label, slug)
    ents = [row(e("switch", "display"), "Display"),
            row(e("select", "mode"), "Mode"),
            section("Brightness"),
            row(e("number", "brightness"), "Day brightness"),
            row(e("number", "night_brightness"), "Night brightness")]
    if backlight:
        ents.insert(2, row(e("light", "backlight"), "Backlight"))
    return [
        {"type": "entities", "title": "%s" % label, "show_header_toggle": False,
         "state_color": True, "visibility": v, "entities": ents},
        {"type": "markdown", "visibility": v,
         "content": (
             "This clock runs the **basic** firmware, which compiles these four "
             "controls and no more. The face, colour, timer and status cards "
             "belong to `mini-round-clock-with-display.yaml`; flashing that "
             "firmware onto this device is what makes them appear."
         )},
    ]


def clock_cards(slug, label):
    e = lambda domain, suffix: "%s.%s_%s" % (domain, slug, suffix)
    v = vis(label, slug)

    ring = {
        "type": "entities", "title": "%s — Ring" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("number", "ring_led_count"), "LED count"),
            row(e("number", "twelve_o_clock_offset"), "Twelve o'clock offset"),
            row(e("select", "mode"), "Mode"),
            row(e("switch", "ring_leds"), "Ring LEDs on"),
            # The ring's current budget in mA. On a PC USB port keep it near
            # 350; on a proper 5 V 2 A supply it can go to 1500 and never bite.
            row(e("number", "ring_current_limit"), "Current limit"),
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

    # ---- Grow clock ------------------------------------------------------
    # One switch turns the whole clock into a child's sleep-training clock;
    # everything else here only matters while it is on. Times are hour +
    # minute pairs because a slider is easier on a phone than a time string.
    # SPLIT INTO THREE, and the reason is layout rather than taste. As one
    # card this was 56 rows -- longer than everything else on the page put
    # together -- and in a sections view one enormous card forces a single
    # tall column with the rest of the width left empty. That empty width is
    # the gap Sam is looking at. Three cards of comparable height let the
    # grid put them side by side. The split is along the seams the card
    # already had: when it happens, what it looks like, how bright it is.
    grow = {
        "type": "entities", "title": "%s — Grow clock: times" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("switch", "grow_clock"), "Grow clock on"),
            row(e("sensor", "grow_clock_state"), "Right now it is"),
            section("Wake up"),
            row(e("number", "grow_clock_wake_hour"), "Hour"),
            row(e("number", "grow_clock_wake_minute"), "Minute"),
            row(e("number", "grow_clock_almost_time_minutes"), "\"Almost time\" before wake"),
            section("Weekends"),
            row(e("switch", "grow_clock_weekend_times"), "Different times at weekends"),
            row(e("number", "grow_clock_weekend_wake_hour"), "Weekend hour"),
            row(e("number", "grow_clock_weekend_wake_minute"), "Weekend minute"),
            section("Bedtime"),
            row(e("number", "grow_clock_bed_hour"), "Hour"),
            row(e("number", "grow_clock_bed_minute"), "Minute"),
            row(e("number", "grow_clock_bedtime_warning_minutes"), "Warning before bed"),
            section("Right now"),
            row(e("button", "grow_clock_wake_now"), "Wake now"),
            row(e("button", "grow_clock_sleep_now"), "Sleep now"),
            row(e("button", "grow_clock_start_nap"), "Start a nap"),
            row(e("number", "grow_clock_nap_minutes"), "Nap length"),
            row(e("button", "grow_clock_cancel_nap"), "Cancel the nap"),
            row(e("button", "grow_clock_five_more_minutes"), "Five more minutes"),
            row(e("number", "grow_clock_snooze_minutes"), "...which is how many"),
            row(e("button", "grow_clock_back_to_schedule"), "Back to the schedule"),
            row(e("switch", "grow_clock_holiday"), "Holiday: weekend times every day"),
            row(e("switch", "grow_clock_clock_by_day"), "Ordinary clock by day"),
            row(e("number", "grow_clock_wake_hold_minutes"), "...this long after wake"),
            row(e("sensor", "grow_clock_minutes_to_wake"), "Minutes to wake"),
        ],
    }
    grow_look = {
        "type": "entities", "title": "%s — Grow clock: look" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("select", "grow_clock_sleep_colour"), "Sleep colour"),
            row(e("select", "grow_clock_almost_colour"), "\"Almost time\" colour"),
            row(e("select", "grow_clock_wake_colour"), "Wake colour"),
            row(e("select", "grow_clock_bedtime_colour"), "Bedtime colour"),
            row(e("select", "grow_clock_face"), "Face"),
            # One dial for the whole face. 100% is the size it has always
            # been; the range stops at 120 because above that the eyes run
            # past the edge of the fixed window the anti-flicker fix draws in.
            row(e("number", "grow_clock_size"), "Size of everything"),
            row(e("switch", "grow_clock_stars"), "Stars until morning"),
            row(e("number", "grow_clock_star_count"), "How many stars"),
            row(e("select", "grow_clock_star_shape"), "Star shape"),
            # Scattered, gently twinkling stars behind the face at sleep time.
            # Separate from the star row above, which counts down the night.
            row(e("switch", "grow_clock_night_sky"), "Twinkling night sky"),
            row(e("number", "grow_clock_night_sky_stars"), "How many in the sky"),
            row(e("switch", "grow_clock_animate"), "Animate the eyes"),
            # The dial that settles the flicker on this panel: how often
            # the face may be redrawn. Sat next to the switch it belongs to.
            row(e("number", "grow_clock_animation_interval"), "Animation interval"),
            # A/B for the repaint fix: off (default) repaints the panel when
            # the picture changes; on restores the old 1 Hz full repaint.
            # The decisive one: stops ALL writes to the panel. If it still
            # flickers with this on, nothing the firmware draws is the cause.
            # OFF (default) = every repaint is a full frame, the arrangement
            # the first working build had. ON restores the partial redraw.
            # Draws the moon and star row with straight edges only. If the
            # flicker follows the SHAPE, it is the panel's inversion/VCOM.
            # The proposed fix if the flat-art test confirms: pixel-art
            # crescent and crossed-bar sparkles. Default off.
            row(e("switch", "grow_clock_blocky_art"), "Blocky art"),
            row(e("switch", "grow_clock_flat_art_test"), "Flat art (test)"),
            row(e("switch", "grow_clock_partial_redraw_test"), "Partial redraw (test)"),
            row(e("switch", "screen_freeze_test"), "Screen freeze (test)"),
            row(e("switch", "grow_clock_repaint_every_second"), "Repaint every second (test)"),
            row(e("switch", "grow_clock_freeze_the_eyes_test"), "Freeze the eyes (test)"),
            row(e("sensor", "grow_clock_frame_time"), "Frame time"),
            # Which build is actually on the clock. Read this BEFORE reporting
            # a symptom — several flicker reports were made against firmware
            # that predated the fix being discussed.
            row(e("sensor", "firmware_built"), "Firmware built"),
            # Reboots into WiFi + OTA only and waits ten minutes for an image.
            # Use it before an OTA you are unsure of, or to rescue a clock
            # whose firmware is running but wedged. Not a restart button.
            row(e("button", "restart_into_safe_mode"), "Restart into safe mode"),
            row(e("switch", "grow_clock_show_time"), "Show the time"),
            row(e("switch", "grow_clock_show_countdown"), "Show the minutes to go"),
            row(e("select", "grow_clock_wake_effect"), "Wake-up effect on the ring"),
            row(e("number", "grow_clock_wake_effect_minutes"), "Wake-up effect for"),
            row(e("select", "grow_clock_expression"), "Force an expression (demo)"),
        ],
    }
    grow_bright = {
        "type": "entities", "title": "%s — Grow clock: brightness and sound" % label,
        "show_header_toggle": False, "state_color": True, "visibility": v,
        "entities": [
            row(e("switch", "grow_clock_dim_at_night"), "Dim at night"),
            row(e("number", "grow_clock_ring_night_brightness"), "Ring at night"),
            row(e("number", "grow_clock_ring_day_brightness"), "Ring by day"),
            row(e("number", "grow_clock_screen_night_brightness"), "Screen at night"),
            row(e("number", "grow_clock_screen_day_brightness"), "Screen by day"),
            row(e("number", "grow_clock_sunrise_fade_minutes"), "Sunrise fade"),
            section("Sound"),
            row(e("switch", "grow_clock_respond_to_sound"), "Respond to sound"),
            row(e("number", "grow_clock_sound_response_seconds"), "Respond for"),
            row(e("sensor", "grow_clock_sound_events"), "Sound events since boot"),
            row("input_boolean.wall_clock_grow_sound", "Test: pretend a sound"),
        ],
    }

    grow_note = {
        "type": "markdown", "visibility": v,
        "content": (
            "**How the grow clock reads.** Sleep colour with stars that go out one by "
            "one through the night; amber and a half-awake face for *almost time*; "
            "the wake colour and a smile when it is fine to get up; a yawn in the "
            "warning before bed. The eyes are Deskimon-style and move on their own — "
            "looks, blinks, smiles, yawns when it is late; *Animate the eyes* off "
            "leaves them still. While it is on, this clock shows nothing else — no "
            "hands, timers or status.\n\n"
            "**Sound.** The clock has no microphone. *Test: pretend a sound* is the "
            "same helper anything in Home Assistant can pulse — a Voice PE hearing "
            "its wake word, a baby monitor, a noise sensor. See "
            "`packages/wall_clock_grow.yaml` for a ready-made example. During sleep "
            "it brightens in the **sleep** colour and says *shh*; it never shows the "
            "wake colour for a noise, because that would reward calling out.\n\n"
            "**Overrides** last until the schedule next changes on its own, so "
            "*Wake now* at 6:40 lets go by itself at bedtime."
        ),
    }

    return [ring, ring_note, colour_note, colour, screen, grow, grow_look,
            grow_bright, grow_note, alert, alert_note, bright]


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
        cards.append(absent_card(c["slug"], c["label"]))
        if c.get("tier") == "basic":
            cards += basic_cards(c["slug"], c["label"], c.get("backlight", False))
        else:
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
    if "--view" in sys.argv:
        # A paste-ready Settings view for the dashboard's raw configuration
        # editor: the cards above wrapped in the view header, as YAML.
        import yaml
        out = sys.argv[sys.argv.index("--view") + 1]
        # SECTIONS, not masonry. Sam's dashboard was rebuilt on Home
        # Assistant's sections layout, and a masonry view pasted over it
        # reverts that -- the bench session spotted that and refused to paste,
        # which was the right call. `--masonry` still emits the old shape.
        if "--masonry" in sys.argv:
            view = [{"title": "Settings", "path": "settings",
                     "icon": "mdi:tune-variant", "cards": cards}]
        else:
            # GROUPED, one section per clock rather than one per card.
            # Sam: "condense the wall clock settings page so that there are no
            # gaps." A sections view lays each section out as its own column,
            # so a section per card gives a page of short ragged columns with
            # whitespace between them. Grouping every card belonging to one
            # clock into a single section lets the grid pack them, and it also
            # lets the picker-and-status condition be carried ONCE on the
            # section instead of repeated on each card inside it.
            #
            # Each clock gets two sections on opposite conditions -- its
            # controls, and the "not connected" notice -- so exactly one of
            # them ever renders and neither leaves a hole.
            #
            # "And move the text boxes to the bottom of the page": the
            # explanatory markdown goes last. The absent-clock notice is
            # markdown too but stays with its clock, because it is not an
            # explainer -- it is what stands in for the controls that are
            # hidden, and at the bottom of the page it would be describing
            # something the reader is no longer looking at.
            # NO GAPS MEANS BALANCING WHAT IS ON SCREEN, NOT WHAT IS IN THE
            # FILE. A sections view lays each section out as a column and packs
            # them left to right; a short column leaves the space under it
            # empty. The previous arrangement emitted a 17-row header section
            # next to 49-row control sections, so the top of the page was one
            # narrow strip with two thirds of the width blank -- which is the
            # gap Sam is pointing at.
            #
            # Only ONE clock is ever selected, so the page that actually renders
            # is: the header, that clock's cards, and the shared timers.
            # Everything else is hidden and collapses. So balance those, and
            # balance them in two rows that each fill the width:
            #
            #   row 1   header + picker + shared timers, over MAX_COLS sections
            #   row 2   the selected clock's controls and prose, over MAX_COLS
            #
            # PROSE SITS AT THE FOOT OF ITS COLUMN, which is what "text boxes at
            # the bottom" means on a grid: putting every explainer below every
            # control would give three short columns of text under three tall
            # ones, and reintroduce the gap from the other end.
            # The two markdown cards that are NOT prose: the heading that
            # names the clock being edited, and the online/offline status line.
            # A filter that only asked "is it markdown" swept both to the foot
            # of the page, which put the title and the liveness indicator below
            # three screens of sliders. Sam asked for the TEXT BOXES at the
            # bottom -- the ones that explain things, not the ones that say what
            # you are looking at and whether it is switched on.
            head = [c for c in cards
                    if c.get("type") == "markdown" and "visibility" not in c
                    and ("{{ states(" in c.get("content", "")
                         or "binary_sensor." in c.get("content", ""))]
            picker = [c for c in cards
                      if c.get("type") == "entities" and "visibility" not in c
                      and not c.get("title")]
            buttons = [c for c in cards if c.get("type") == "horizontal-stack"]
            top = head[:1] + buttons + head[1:] + picker
            secs = []
            def grid(cs, vis=None):
                g = {"type": "grid", "cards": cs}
                if vis:
                    g["visibility"] = vis
                return g
            def strip(c):
                c = dict(c)
                c.pop("visibility", None)
                return c
            def spread(items, vis=None, tail_items=()):
                """Longest first into the shortest column, then the prose under
                whatever column ended up shortest, so the text lands low."""
                cols = [[] for _ in range(MAX_COLS)]
                hs = [0] * MAX_COLS
                for x in sorted(items, key=card_rows, reverse=True):
                    i = hs.index(min(hs))
                    cols[i].append(strip(x)); hs[i] += card_rows(x)
                for x in sorted(tail_items, key=card_rows, reverse=True):
                    i = hs.index(min(hs))
                    cols[i].append(strip(x)); hs[i] += card_rows(x)
                for col in cols:
                    if col:
                        secs.append(grid(col, vis))

            # ---- row 1: the always-visible header, and the shared timers
            shared = [c for c in cards
                      if c.get("type") == "entities" and c.get("title") == "Timers (shared)"]
            notes = [c for c in cards
                     if c.get("type") == "markdown" and "visibility" not in c
                     and c not in head]
            # The heading and the buttons stay together and stay first: they are
            # what tells you which clock you are editing and how to change it.
            spread(top[:2], None, top[2:] + shared + notes)

            # ---- row 2: the selected clock
            for c in CLOCKS:
                mine = [x for x in cards
                        if any(cond.get("state") == c["label"]
                               for cond in x.get("visibility", []))]
                ctrl = [x for x in mine
                        if not any(cond.get("state_not") for cond in x["visibility"])]
                away = [x for x in mine
                        if any(cond.get("state_not") for cond in x["visibility"])]
                body  = [x for x in ctrl if x.get("type") != "markdown"]
                prose = [x for x in ctrl if x.get("type") == "markdown"]
                if body or prose:
                    spread(body, ctrl[0]["visibility"], prose)
                if away:
                    secs.append(grid([strip(x) for x in away], away[0]["visibility"]))

            view = [{"title": "Settings", "path": "settings",
                     "icon": "mdi:tune-variant", "type": "sections",
                     "max_columns": 3, "sections": secs}]
        head = ("# Paste into the dashboard's Raw configuration editor, replacing the existing\n"
                "# Settings view in the `views:` list. This is a SECTIONS view, matching the\n"
                "# layout the dashboard already uses; pass --masonry for the older shape.\n#\n"
                "# Generated by homeassistant/dashboards/build_clock_dashboard.py --view -- do\n"
                "# not hand-edit; edit CLOCKS in that script and re-run it.\n")
        io.open(out, "w", encoding="utf-8", newline="\n").write(
            head + yaml.safe_dump(view, sort_keys=False, allow_unicode=True, width=1000))
        print("view: %s" % out)
    print("clocks: %d   cards: %d" % (len(CLOCKS), len(cards)))
    for c in CLOCKS:
        print("  %-22s -> %s" % (c["label"], c["slug"]))
