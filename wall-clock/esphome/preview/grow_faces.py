#!/usr/bin/env python3
"""Preview the grow-clock faces exactly as the firmware lambdas draw them.

    python3 grow_faces.py            # writes grow-faces.png beside this file
    GROW_PREVIEW_FONT=/path/Roboto.ttf python3 grow_faces.py

Every number here is copied from mini-round-clock-with-display.yaml and must
be kept in step with it BY HAND. The YAML is the source of truth; this is a
way to look at a layout before flashing, not a second implementation.

This file holds the still faces: the palette, the eye primitive and the
resting pose of each state. grow_anim.py adds the animator on top.

Rows: the "eyes" face (Deskimon-style glowing eyes on black), "eyes on
colour" (same eyes, dark on the state colour), "sun and moon", and the bar
panel. Columns: sleep, almost, awake, bedtime. Nap draws as sleep.
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esphome_canvas import BLACK, Canvas, Color, Font, TextAlign, dim  # noqa: E402

STATES = ["sleep", "almost", "awake", "bedtime"]
FRAC = 0.6          # of the night still to go: 5 of 8 stars lit
STAR_COUNT = 8      # grow_star_count
STAR_SHAPE = "stars"  # grow_star_shape: "dots" or "stars"
# Mirrors the firmware's "Grow clock flat art (test)" switch: the moon and the
# star row drawn with axis-aligned rectangles only, to test whether the flicker
# follows the EDGE STRUCTURE rather than the position or the size.
FLAT = False
# BLOCK is the proposed *fix* if the flat-art test confirms the hypothesis,
# as opposed to FLAT which is the *instrument*.
#
# I over-stated the constraint in my own notes: I said a crescent built from
# stacked bars "will not do, that reintroduces the row-to-row change". That is
# too strict. A circle changes its run-length at EVERY row -- about 32 of them
# for the moon. A shape made of three stacked bars changes at TWO boundaries.
# The hypothesis is about fine, repeated row-to-row structure, not about any
# change anywhere, so a chunky pixel-art shape is a real improvement and does
# not have to look like a fallback.
BLOCK = False
MIN_TO = 12         # grow_min_to, for the countdown
CLOCK = "6:45"
TWELVE_HOUR = True          # mirrors fmt_24h off
MERIDIEM = "am"
SLEEP_COLOUR = "blue"
WAKE_COLOUR = "yellow"

# eye geometry, (EX, EY, EW, EH, ER, BAR): centre offset, centre line, width,
# height, corner radius, closed-bar height
SCALE = 1.0                 # mirrors number.grow_clock_size / 100, clamped 0.70..1.20
# The night sky's dials, mirroring the firmware one for one.
NIGHT_STARS  = 12           # number.grow_clock_night_sky_stars      0..60
NIGHT_SEED   = 0x9E3779B9   # button.grow_clock_new_night_sky changes this
NIGHT_BRIGHT = 1.00         # number.grow_clock_night_sky_brightness 0.10..1.00
NIGHT_SIZE   = 2            # number.grow_clock_night_sky_star_size  1..4
NIGHT_AT_BED = True         # switch.grow_clock_night_sky_at_bedtime
# A message typed in Home Assistant. It takes the star row's place while it is
# set -- there is no other free band under the animation box, and a message
# someone typed on purpose outranks an ambient row of stars.
MESSAGE = "back to bed, mate"   # text.<clock>_message
AN_L, AN_R, AN_T, AN_B = 180 - 124, 180 + 124, 60, 240   # the animation box

def _scaled_eyes(sc):
    return (round(60*sc), 180 - round(34*sc), round(80*sc),
            round(112*sc), round(28*sc), round(16*sc))

ROUND_EYES = _scaled_eyes(SCALE)
BAR_EYES = (40, 56, 48, 72, 18, 10)


# --- colours: one table, mirrored in both panel lambdas -----------------------
def palette(st: int, glow: bool, sc: str = SLEEP_COLOUR, wc: str = WAKE_COLOUR):
    """(field, ink) for a state. glow=True is the Deskimon look: black field,
    eyes in the state colour. glow=False is the state colour as the field with
    dark eyes on it."""
    if glow:
        if st in (0, 4):
            ink = (Color(255, 40, 30) if sc == "red" else Color(170, 60, 255) if sc == "purple"
                   else Color(50, 50, 60) if sc == "off" else Color(40, 100, 255))
        elif st == 1:
            ink = Color(255, 150, 30)
        elif st == 2:
            ink = (Color(60, 230, 80) if wc == "green" else Color(240, 240, 240) if wc == "white"
                   else Color(255, 210, 40))
        else:
            ink = Color(255, 120, 50)
        return BLACK, ink
    if st in (0, 4):
        field = (Color(90, 10, 10) if sc == "red" else Color(50, 10, 80) if sc == "purple"
                 else Color(0, 0, 0) if sc == "off" else Color(10, 18, 80))
        ink = Color(225, 228, 240)
    elif st == 1:
        field, ink = Color(200, 120, 20), Color(40, 24, 4)
    elif st == 2:
        field = (Color(40, 180, 60) if wc == "green" else Color(220, 220, 220) if wc == "white"
                 else Color(240, 200, 40))
        ink = Color(40, 32, 8)
    else:
        field, ink = Color(140, 60, 20), Color(240, 225, 200)
    return field, ink


def base_pose(st):
    """(lid, smile, droop) the face rests at between clips. lid is the share
    of the eye covered from the top; 1 is closed. smile is the bite from
    below that turns an eye into a happy arch."""
    if st in (0, 4):
        return 1.0, 0.0, 0.0
    if st == 1:
        return 0.45, 0.0, 0.0
    if st == 2:
        return 0.0, 0.35, 0.0
    return 0.55, 0.0, 1.0


# --- the eye primitives, same shapes as the C++ helpers ----------------------
def rrect(it: Canvas, x, y, w, h, r, c):
    """Rounded rectangle from two rectangles and four circles: the only way
    to get one out of ESPHome's Display without a bitmap."""
    it.filled_rectangle(x + r, y, w - 2 * r, h, c)
    it.filled_rectangle(x, y + r, w, h - 2 * r, c)
    it.filled_circle(x + r, y + r, r, c)
    it.filled_circle(x + w - 1 - r, y + r, r, c)
    it.filled_circle(x + r, y + h - 1 - r, r, c)
    it.filled_circle(x + w - 1 - r, y + h - 1 - r, r, c)


def draw_eye(it, cx, cy, geom, lid, smile, hs, droop, outer_left, ink, field):
    """One eye. Lids and the smile are painted over an open eye in the field
    colour, which only works because nothing is drawn behind the eyes."""
    _, _, EW, EH, ER, BAR = geom
    h = int(EH * hs)
    w = EW
    r = min(ER, h // 2 - 1)
    if lid >= 0.9:
        rrect(it, cx - w // 2, cy - BAR // 2, w, BAR, BAR // 2, ink)
        return
    rrect(it, cx - w // 2, cy - h // 2, w, h, r, ink)
    x0, top = cx - w // 2 - 1, cy - h // 2 - 1
    if lid > 0.02:
        L = int(h * lid)
        it.filled_rectangle(x0, top, w + 2, L + 1, field)
        if droop > 0:
            # the outer corner droops: tired, not sad
            d = max(4, int(EH / 8 * droop))
            if outer_left:
                it.filled_triangle(x0, top + L, x0 + w + 2, top + L, x0, top + L + d, field)
            else:
                it.filled_triangle(x0, top + L, x0 + w + 2, top + L, x0 + w + 2, top + L + d, field)
    if smile > 0.02:
        # a field-coloured circle bites up from below, leaving a happy arch
        Rb = int(w * 0.9)
        it.filled_circle(cx, cy + h // 2 + Rb - int(smile * h * 0.78), Rb, field)


def star(it, x, y, r, c, pointy):
    if BLOCK:                       # a sparkle from two crossed bars
        it.filled_rectangle(x - 2, y - r, 5, 2 * r + 1, c)
        it.filled_rectangle(x - r, y - 2, 2 * r + 1, 5, c)
        return
    if FLAT:
        it.filled_rectangle(x - r, y - r, 2 * r + 1, 2 * r + 1, c)
        return
    """A four-point sparkle from four triangles, or a dot."""
    if pointy:
        a, b = r, max(2, r // 3)
        it.filled_triangle(x, y - a, x - b, y, x + b, y, c)
        it.filled_triangle(x, y + a, x - b, y, x + b, y, c)
        it.filled_triangle(x - a, y, x, y - b, x, y + b, c)
        it.filled_triangle(x + a, y, x, y - b, x, y + b, c)
    else:
        it.filled_circle(x, y, r * 2 // 3, c)


def sky(it, cx, sy, st, ink, field, r=16):
    """Moon at night and bedtime, sun by day, half a sun when it is almost
    morning. Sits above the eyes, outside the animation box."""
    k = r / 16.0
    if st in (0, 4, 3):
        if BLOCK:
            # Step the REAL crescent into a few horizontal bands rather than
            # hand-picking bars: outer disc radius R, bite disc radius Rb offset
            # right and up, exactly as the round version. N bands means the
            # run-length changes N-1 times instead of a circle's ~2R, which is
            # the whole point -- and stepping the true shape keeps it reading as
            # a moon where hand-drawn bars read as the letter C.
            R, Rb, bx, by, N = int(r * 1.25), int(r * 0.95), int(r * 0.55), -int(r * 0.28), 7
            for i in range(N):
                y0 = -R + (2 * R * i) // N
                y1 = -R + (2 * R * (i + 1)) // N
                ym = (y0 + y1) / 2.0                       # sample at band centre
                if abs(ym) >= R:
                    continue
                xl = -math.sqrt(R * R - ym * ym)
                xr = math.sqrt(R * R - ym * ym)
                d = Rb * Rb - (ym - by) ** 2
                if d > 0:                                   # the bite cuts this band
                    xr = min(xr, bx - math.sqrt(d))
                if xr - xl < 2:
                    continue
                it.filled_rectangle(cx + int(xl), sy + y0, int(xr - xl), y1 - y0, ink)
        elif FLAT:
            # plain square, no bite: uniform width down every row (see firmware)
            it.filled_rectangle(cx - r, sy - r, 2 * r, 2 * r, ink)
        else:
            it.filled_circle(cx, sy, r, ink)
            it.filled_circle(cx + int(7 * k), sy - int(4 * k), int(13 * k), field)
    else:
        if FLAT:
            it.filled_rectangle(cx - int(11 * k), sy - int(11 * k), 2 * int(11 * k), 2 * int(11 * k), ink)
        else:
            it.filled_circle(cx, sy, int(11 * k), ink)
        for i in range(8):
            a = i * math.pi / 4
            it.line(cx + round(15 * k * math.cos(a)), sy + round(15 * k * math.sin(a)),
                    cx + round(22 * k * math.cos(a)), sy + round(22 * k * math.sin(a)), ink)
        if st == 1:
            it.filled_rectangle(cx - int(26 * k), sy + 2, int(52 * k), int(24 * k), field)


def draw_eyes_resting(it, cx, st, geom, ink, field):
    EX, EY = geom[0], geom[1]
    lid, smile, droop = base_pose(st)
    draw_eye(it, cx - EX, EY, geom, lid, smile, 1.0, droop, True, ink, field)
    draw_eye(it, cx + EX, EY, geom, lid, smile, 1.0, droop, False, ink, field)


# --- the round panel, 360 x 360 ------------------------------------------------
def draw_round(st: int, face: str, sound=False) -> Canvas:
    it = Canvas(360, 360, round_=True)
    CX = CY = 180
    glow = face in ("eyes", "eyes and sky")
    field, ink = palette(st, glow)
    it.fill(field)
    font_med, font_t48, font_small = Font(32), Font(48), Font(22)

    if face in ("eyes", "eyes and sky", "eyes on colour"):
        # Two eyes, about half the panel wide, a little above centre so the
        # stars and the time fit underneath inside the circle.
        # The night sky goes FIRST, exactly as the firmware does it, so the
        # eyes and the z's paint over anything behind them.
        if (st in (0, 4) or (st == 3 and NIGHT_AT_BED)) and NIGHT_STARS:
            rr = NIGHT_SEED | 1
            def nxt():
                nonlocal rr
                rr = (rr*1664525 + 1013904223) & 0xFFFFFFFF
                return (rr >> 16) & 0x7FFF
            for i in range(NIGHT_STARS):
                nx = AN_L + 8 + nxt() % (AN_R - AN_L - 16)
                ny = AN_T + 8 + nxt() % (AN_B - AN_T - 16)
                phase = nxt() % 628
                r = 1 + nxt() % NIGHT_SIZE
                tw = 0.675 + 0.325*math.sin(phase/100.0)
                c = dim(ink, tw*NIGHT_BRIGHT)
                it.filled_rectangle(nx - r, ny, 2*r + 1, 1, c)
                it.filled_rectangle(nx, ny - r, 1, 2*r + 1, c)
        draw_eyes_resting(it, CX, st, ROUND_EYES, ink, field)
        if st in (0, 4):
            for i in range(3):
                ph = i / 3.0
                it.print(CX + 70 + int(14 * ph), CY - 74 - int(24 * ph), font_med,
                         dim(ink, 1 - ph * 0.9), TextAlign.CENTER, "z")
        if sound:
            it.print(CX, CY + 40, font_med, ink, TextAlign.CENTER, "shh")
        if face == "eyes and sky":
            sky(it, CX, CY - 144, st, ink, field)
    elif face == "sun and moon":
        if st in (0, 4, 3):
            it.filled_circle(CX, CY - 10, 70, ink)
            it.filled_circle(CX + 28, CY - 24, 62, field)
            for sx, sy in [(-120, -60), (-95, 70), (105, -80), (125, 20), (60, -125)]:
                it.filled_circle(CX + sx, CY + sy, 5, ink)
        else:
            it.filled_circle(CX, CY - 10, 60, ink)
            for i in range(12):
                a = i * math.pi / 6
                it.line(CX + round(78 * math.cos(a)), CY - 10 + round(78 * math.sin(a)),
                        CX + round(105 * math.cos(a)), CY - 10 + round(105 * math.sin(a)), ink)
        if sound:
            it.print(CX, CY + 100, font_med, ink, TextAlign.CENTER, "shh")

    # Stars until morning, a row under the eyes; the countdown in their place
    # when it is almost morning or almost bed.
    # The message takes the star row's place, and on the sun-and-moon face the
    # top instead -- the disc reaches CY + 95 there. Mirrors the firmware, which
    # also lets it take that face's countdown spot.
    sunmoon = face == "sun and moon"
    if MESSAGE:
        my = CY - 150 if sunmoon else CY + 72
        # The chord at that height, same measurement the firmware makes: the
        # panel is a circle, so there is 330 px at CY + 72 and only 199 at
        # CY - 150, and a fixed threshold printed "ack to bed, mat" there.
        room = 2*int(math.sqrt(max(0.0, 180.0**2 - (my - CY)**2))) - 12
        wide = lambda f, t: it.text_width(f, t)
        f = font_med if wide(font_med, MESSAGE) <= room else font_small
        out = MESSAGE
        while len(out) > 1 and wide(f, out + "...") > room:
            out = out[:-1]
        if len(out) < len(MESSAGE):
            out += "..."
        it.print(CX, my, f, ink, TextAlign.CENTER, out)
    # The star row: only when there is no message, exactly as the firmware.
    if not MESSAGE and st in (0, 4):
        NS = max(3, min(12, STAR_COUNT))
        pitch = min(28, 220 // max(1, NS - 1))
        lit = min(NS, math.ceil(FRAC * NS))
        for i in range(NS):
            star(it, CX - (NS - 1) * pitch // 2 + i * pitch, CY + 72, 9,
                 ink if i < lit else dim(ink, 0.18), STAR_SHAPE == "stars")
    if st in (1, 3) and not (sunmoon and MESSAGE):
        it.print(CX, CY - 150 if sunmoon else CY + 40, font_med, ink,
                 TextAlign.CENTER, f"{MIN_TO} min")

    # The time, digital, along the bottom. Mirrors the firmware exactly: in
    # 12-hour the PAIR is centred, not the digits, and the baselines are
    # aligned rather than the boxes.
    if TWELVE_HOUR:
        def metrics(f, t):
            a, d = f.font.getmetrics()
            return int(round(f.font.getlength(t))), a + d, a
        tw, th, tb = metrics(font_t48, CLOCK)
        aw, ah, ab = metrics(font_small, MERIDIEM)
        GAP = 7
        top = CY + 120 - th // 2
        left = CX - (tw + GAP + aw) // 2
        it.print(left, top, font_t48, ink, TextAlign.TOP_LEFT, CLOCK)
        it.print(left + tw + GAP, top + tb - ab, font_small, ink,
                 TextAlign.TOP_LEFT, MERIDIEM)
    else:
        it.print(CX, CY + 120, font_t48, ink, TextAlign.CENTER, CLOCK)
    return it


# --- the bar panel, 320 x 170 --------------------------------------------------
def draw_bar(st: int, face: str, sound=False) -> Canvas:
    it = Canvas(320, 170)
    W, H = 320, 170
    FX = W // 2
    glow = face in ("eyes", "eyes and sky")
    field, ink = palette(st, glow)
    it.fill(field)
    font_med, font_small = Font(32), Font(22)

    if face in ("eyes", "eyes and sky", "eyes on colour"):
        draw_eyes_resting(it, FX, st, BAR_EYES, ink, field)
        if st in (0, 4):
            for i in range(3):
                ph = i / 3.0
                it.print(FX + 62 + int(10 * ph), 24 - int(16 * ph), font_med,
                         dim(ink, 1 - ph * 0.9), TextAlign.CENTER, "z")
        if face == "eyes and sky":
            sky(it, 30, 24, st, ink, field, r=11)
    elif face == "sun and moon":
        if st in (0, 4, 3):
            it.filled_circle(FX, 70, 46, ink)
            it.filled_circle(FX + 18, 60, 40, field)
        else:
            it.filled_circle(FX, 70, 40, ink)
            for i in range(12):
                a = i * math.pi / 6
                it.line(FX + round(52 * math.cos(a)), 70 + round(52 * math.sin(a)),
                        FX + round(68 * math.cos(a)), 70 + round(68 * math.sin(a)), ink)
    if sound:
        it.print(W - 12, 10, font_med, ink, TextAlign.TOP_RIGHT, "shh")
    if st in (0, 4):
        NS = max(3, min(12, STAR_COUNT))
        pitch = min(20, 160 // max(1, NS - 1))
        lit = min(NS, math.ceil(FRAC * NS))
        for i in range(NS):
            star(it, FX - (NS - 1) * pitch // 2 + i * pitch, 120, 6,
                 ink if i < lit else dim(ink, 0.18), STAR_SHAPE == "stars")
    elif st in (1, 3):
        if face == "sun and moon":
            it.print(12, 10, font_small, ink, TextAlign.TOP_LEFT, f"{MIN_TO} min")
        else:
            it.print(FX, 120, font_small, ink, TextAlign.CENTER, f"{MIN_TO} min")
    if TWELVE_HOUR:                       # same rule as the round panel
        def metrics(f, t):
            a, d = f.font.getmetrics()
            return int(round(f.font.getlength(t))), a + d, a
        tw, th, tb = metrics(font_med, CLOCK)
        aw, ah, ab = metrics(font_small, MERIDIEM)
        GAP = 5
        top = 148 - th // 2
        left = FX - (tw + GAP + aw) // 2
        it.print(left, top, font_med, ink, TextAlign.TOP_LEFT, CLOCK)
        it.print(left + tw + GAP, top + tb - ab, font_small, ink,
                 TextAlign.TOP_LEFT, MERIDIEM)
    else:
        it.print(FX, 148, font_med, ink, TextAlign.CENTER, CLOCK)
    return it


def sheet(out: str):
    rows = [
        ("eyes and sky  (the default: Deskimon eyes, a sun or moon, the stars)", lambda st: draw_round(st, "eyes and sky")),
        ("eyes", lambda st: draw_round(st, "eyes")),
        ("eyes on colour", lambda st: draw_round(st, "eyes on colour")),
        ("sun and moon", lambda st: draw_round(st, "sun and moon")),
        ("bar panel, eyes and sky", lambda st: draw_bar(st, "eyes and sky")),
    ]
    cell, pad, label_h = 360, 16, 34
    W = pad + 4 * (cell + pad)
    H = pad + sum(label_h + (360 if "bar" not in name else 170) + pad for name, _ in rows)
    im = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(im)
    label = Font(22).font
    small = Font(18).font
    y = pad
    for name, fn in rows:
        d.text((pad, y), name, font=label, fill=(30, 30, 30))
        y += label_h
        for i, st_name in enumerate(STATES):
            st = STATES.index(st_name)
            c = fn(st)
            x = pad + i * (cell + pad)
            im.paste(c.image(), (x, y))
            d.text((x + 6, y + 4), st_name, font=small, fill=(160, 160, 160) if "bar" in name else (110, 110, 110))
        y += (360 if "bar" not in name else 170) + pad
    im.save(out)
    return out


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grow-faces.png")
    print(sheet(out))
