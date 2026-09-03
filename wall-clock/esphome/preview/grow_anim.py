#!/usr/bin/env python3
"""The grow-clock eye animator, mirrored from the firmware so it can be watched
before it is flashed.

    python3 grow_anim.py             # grow-anim-<state>.gif for each state, plus
                                     # grow-anim-strip.png and a variety report

The engine here and the C++ in mini-round-clock-with-display.yaml (the
"grow eye animator" interval and the two panel lambdas) are the SAME design
with the same constants, clip table, weights, envelopes and random generator
(a 32-bit LCG, so a seed reproduces a sequence on both). The YAML is what
runs; if the two disagree, the panel is right and this file is wrong.

Frame period is 100 ms, the firmware's animation interval.
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esphome_canvas import BLACK, Canvas, Color, Font, TextAlign, dim  # noqa: E402
from grow_faces import BAR_EYES, ROUND_EYES, base_pose, draw_eye, palette  # noqa: E402

FRAME_MS = 100

# --- clip ids: one table, both implementations ------------------------------
BLINK, DBLINK, LOOK, LOOK_AROUND, SMILE, WINK, BOUNCE, WIDE, SQUINT, ROLL, \
    WIGGLE, YAWN, SLOW_BLINK, PEEK, DRIFT, NOD, TWITCH, DANCE = range(1, 19)
NAMES = {BLINK: "blink", DBLINK: "double blink", LOOK: "look", LOOK_AROUND: "look around",
         SMILE: "smile", WINK: "wink", BOUNCE: "bounce", WIDE: "wide eyes", SQUINT: "squint",
         ROLL: "eye roll", WIGGLE: "wiggle", YAWN: "yawn", SLOW_BLINK: "slow blink",
         PEEK: "peek", DRIFT: "drift", NOD: "nod off", TWITCH: "twitch", DANCE: "happy dance"}

# duration range per clip, ms
DUR = {BLINK: (360, 360), DBLINK: (800, 800), LOOK: (1500, 3500), LOOK_AROUND: (4000, 6000),
       SMILE: (2000, 4000), WINK: (700, 700), BOUNCE: (900, 900), WIDE: (1200, 1200),
       SQUINT: (1500, 2500), ROLL: (1600, 1600), WIGGLE: (900, 900), YAWN: (3000, 3000),
       SLOW_BLINK: (1200, 1200), PEEK: (1800, 1800), DRIFT: (4000, 6000), NOD: (2400, 2400),
       TWITCH: (400, 400), DANCE: (2400, 2400)}

# (clip, weight) per state, weights sum to 100; and the idle gap range after a clip
TABLE = {
    2: ([(LOOK, 22), (LOOK_AROUND, 14), (BLINK, 14), (DBLINK, 5), (SMILE, 16), (WINK, 4),
         (BOUNCE, 6), (WIDE, 3), (SQUINT, 4), (ROLL, 3), (WIGGLE, 4), (DANCE, 5)], (1500, 5000)),
    1: ([(SLOW_BLINK, 22), (BLINK, 10), (LOOK, 15), (YAWN, 15), (PEEK, 12), (DRIFT, 14),
         (SQUINT, 6), (SMILE, 6)], (2000, 6000)),
    3: ([(YAWN, 26), (SLOW_BLINK, 20), (NOD, 16), (DRIFT, 14), (LOOK, 10), (BLINK, 9),
         (SQUINT, 5)], (2000, 7000)),
    0: ([(TWITCH, 100)], (12000, 30000)),
}
TABLE[4] = TABLE[0]

GAZE_X, GAZE_Y = 20, 12          # px at round scale




def ease(u):
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    return u * u * (3 - 2 * u)


def tri(u):
    return u * 2 if u < 0.5 else 2 - u * 2


def hold(u, a, b):
    """Rise over [0,a], hold, fall over [b,1]."""
    if u < a:
        return ease(u / a)
    if u < b:
        return 1.0
    return ease((1 - u) / (1 - b))


class Animator:
    """State the firmware keeps in globals, and the per-frame step."""

    def __init__(self, seed=12345):
        self.seed = seed & 0xFFFFFFFF
        self.clip = 0
        self.t0 = 0
        self.dur = 1
        self.next_at = 0
        self.p = [0, 0, 0, 0]
        self.gx = self.gy = 0.0
        self.st_last = -1
        # outputs
        self.lidl = self.lidr = 0.0
        self.smile = 0.0
        self.hs = 1.0
        self.mouth = 0.0
        self.zph = 0.0
        self.log = []          # (ms, clip, params) for the variety report

    # 32-bit LCG (Numerical Recipes), top 24 bits used
    def rnd(self):
        self.seed = (self.seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.seed >> 8) & 0xFFFFFF

    def rr(self, lo, hi):
        return lo + self.rnd() % (hi - lo + 1)

    def pick(self, st, ms):
        clips, gap = TABLE[st]
        r = self.rr(0, 99)
        acc = 0
        c = clips[-1][0]
        for cid, w in clips:
            acc += w
            if r < acc:
                c = cid
                break
        lo, hi = DUR[c]
        self.clip, self.t0, self.dur = c, ms, self.rr(lo, hi)
        # parameters: gaze targets, small for the sleepy states
        k = 1.0 if st == 2 else 0.6
        self.p = [int(self.rr(-GAZE_X, GAZE_X) * k), int(self.rr(-GAZE_Y, GAZE_Y) * k),
                  int(self.rr(-GAZE_X, GAZE_X) * k), int(self.rr(-GAZE_Y, GAZE_Y) * k)]
        self.next_at = ms + self.dur + self.rr(gap[0], gap[1])
        self.log.append((ms, c, self.dur, tuple(self.p)))

    def step(self, st, ms, animate=True):
        base_lid, base_smile, _ = base_pose(st)
        if st != self.st_last:
            # a state change cancels the clip and rests the eyes
            self.clip, self.next_at = 0, ms + 1500
            self.st_last = st
        if animate and ms >= self.next_at:
            self.pick(st, ms)

        c = self.clip
        u = (ms - self.t0) / self.dur if c else 1.0
        if u >= 1.0:
            c, u = 0, 1.0
            self.clip = 0

        lidl = lidr = base_lid
        smile = base_smile
        hs = 1.0
        mouth = 0.0
        tx = ty = 0.0
        direct = None
        p = self.p

        if c == BLINK:
            lidl = lidr = max(base_lid, tri(u))
        elif c == DBLINK:
            lidl = lidr = max(base_lid, tri((u * 2) % 1.0))
        elif c == LOOK:
            tx, ty = p[0], p[1]
        elif c == LOOK_AROUND:
            tx, ty = (p[0], p[1]) if u < 0.45 else (p[2], p[3]) if u < 0.9 else (0, 0)
        elif c == SMILE:
            smile = max(base_smile, hold(u, 0.2, 0.75))
        elif c == WINK:
            lidr = max(base_lid, hold(u, 0.25, 0.65))
            smile = max(base_smile, 0.6 * hold(u, 0.25, 0.65))
        elif c == BOUNCE:
            hs = 1 + 0.16 * math.sin(2 * math.pi * u) * (1 - u)
        elif c == WIDE:
            lidl = lidr = 0.0
            hs = 1 + 0.15 * hold(u, 0.2, 0.7)
            ty = -3 * hold(u, 0.2, 0.7)
        elif c == SQUINT:
            lidl = lidr = max(base_lid, 0.45 * hold(u, 0.25, 0.75))
            tx, ty = p[0], -6
        elif c == ROLL:
            direct = (14 * math.cos(2 * math.pi * u), 9 * math.sin(2 * math.pi * u))
        elif c == WIGGLE:
            direct = (10 * math.sin(4 * math.pi * u) * (1 - u), 0)
        elif c == YAWN:
            e = hold(u, 0.3, 0.8)
            lidl = lidr = max(base_lid, e)
            mouth = hold(u, 0.35, 0.7)
            ty = 4 * mouth
        elif c == SLOW_BLINK:
            lidl = lidr = max(base_lid, tri(u))
        elif c == PEEK:
            e = hold(u, 0.3, 0.7)
            lidl = lidr = base_lid * (1 - e)
            ty = -3 * e
        elif c == DRIFT:
            lidl = lidr = min(0.95, base_lid + 0.25 * math.sin(math.pi * u))
        elif c == NOD:
            if u < 0.55:
                e = ease(u / 0.55)
                lidl = lidr = base_lid + (0.95 - base_lid) * e
                ty = 10 * e
            elif u < 0.7:
                lidl = lidr = 0.15
                ty = -4
            else:
                e = 1 - ease((u - 0.7) / 0.3)
                lidl = lidr = base_lid + (0.15 - base_lid) * e
        elif c == TWITCH:
            direct = (3 * math.sin(4 * math.pi * u) * (1 - u), 0)
        elif c == DANCE:
            smile = 1.0
            hs = 1 + 0.14 * math.sin(4 * math.pi * u) * (1 - 0.5 * u)
            direct = (10 * math.sin(2 * math.pi * u), 0)

        if direct is not None:
            self.gx, self.gy = direct
        else:
            self.gx += (tx - self.gx) * 0.4
            self.gy += (ty - self.gy) * 0.4

        self.lidl, self.lidr, self.smile, self.hs, self.mouth = lidl, lidr, smile, hs, mouth
        self.zph = (ms % 3000) / 3000.0
        return self


# --- drawing one frame from the outputs -----------------------------------------


def draw_frame_round(a: Animator, st, face="eyes", clock="6:45", sound=False, partial=False):
    it = Canvas(360, 360, round_=True)
    CX = CY = 180
    field, ink = palette(st, face == "eyes")
    EX, EY, EW, EH, ER, BAR = ROUND_EYES
    _, _, droop = base_pose(st)
    font_med, font_t48 = Font(32), Font(48)
    if partial:
        it.fill(Color(30, 30, 30))          # what a partial frame does NOT repaint
        it.filled_rectangle(CX - 124, 60, 248, 184, field)
    else:
        it.fill(field)
    gx, gy = int(round(a.gx)), int(round(a.gy))
    draw_eye(it, CX - EX + gx, EY + gy, ROUND_EYES, a.lidl, a.smile, a.hs, droop, True, ink, field)
    draw_eye(it, CX + EX + gx, EY + gy, ROUND_EYES, a.lidr, a.smile, a.hs, droop, False, ink, field)
    if a.mouth > 0.05:
        r = 4 + int(12 * a.mouth)
        it.filled_circle(CX + gx, EY + EH // 2 + 20 + gy, r, ink)
        if r > 6:
            it.filled_circle(CX + gx, EY + EH // 2 + 20 + gy, r - 5, field)
    if st in (0, 4):
        for i in range(3):
            ph = (a.zph + i / 3.0) % 1.0
            it.print(CX + 70 + int(14 * ph), CY - 74 - int(24 * ph), font_med,
                     dim(ink, 1 - ph * 0.9), TextAlign.CENTER, "z")
    if sound:
        it.print(CX, CY + 40, font_med, ink, TextAlign.CENTER, "shh")
    if not partial:
        if st in (0, 4):
            NS, lit = 8, 5
            for i in range(NS):
                it.filled_circle(CX - (NS - 1) * 14 + i * 28, CY + 72, 6, ink if i < lit else dim(ink, 0.18))
        it.print(CX, CY + 120, font_t48, ink, TextAlign.CENTER, clock)
    return it


def gif(st, seconds=40, seed=777, out=None, face="eyes"):
    a = Animator(seed)
    frames = []
    for f in range(int(seconds * 1000 / FRAME_MS)):
        ms = 1000 + f * FRAME_MS
        a.step(st, ms)
        if f % 2 == 0:                       # gif at 5 fps keeps the file small
            frames.append(draw_frame_round(a, st, face).image())
    out = out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              f"grow-anim-{['sleep','almost','awake','bedtime','nap'][st]}.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS * 2, loop=0,
                   optimize=False)
    return out, a


def variety(st, minutes=20, seed=4242):
    """How much distinct content a stretch of the programme holds."""
    a = Animator(seed)
    ms = 1000
    end = ms + minutes * 60000
    while ms < end:
        a.step(st, ms)
        ms += FRAME_MS
    clips = a.log
    distinct = {(c, d, p) for _, c, d, p in clips}
    kinds = {c for _, c, _, _ in clips}
    total = sum(d for _, _, d, _ in clips) / 1000.0
    return len(clips), len(distinct), sorted(NAMES[k] for k in kinds), total


def strip(out):
    """One row per clip: eight frames across its duration, awake palette."""
    rows = []
    for cid in range(1, 19):
        st = 2 if cid in (BLINK, DBLINK, LOOK, LOOK_AROUND, SMILE, WINK, BOUNCE, WIDE, SQUINT, ROLL,
                          WIGGLE, DANCE) else 3 if cid in (YAWN, NOD) else 1 if cid in (SLOW_BLINK, PEEK, DRIFT) else 0
        a = Animator(99)
        a.st_last = st
        a.step(st, 0)
        a.clip, a.t0, a.dur = cid, 0, DUR[cid][1]
        a.p = [14, -6, -12, 8]
        a.next_at = 10 ** 9
        imgs = []
        for k in range(8):
            ms = int(a.dur * k / 7.0)
            # replay from 0 so the gaze smoothing is honest
            b = Animator(99); b.st_last = st; b.clip, b.t0, b.dur, b.p, b.next_at = cid, 0, a.dur, a.p, 10 ** 9
            t = 0
            while t <= ms:
                b.step(st, t); t += FRAME_MS
            imgs.append(draw_frame_round(b, st).image().resize((180, 180), Image.LANCZOS))
        rows.append((NAMES[cid], imgs))
    cell, pad, lab = 180, 8, 26
    W = 150 + 8 * (cell + pad)
    H = pad + len(rows) * (cell + pad)
    im = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(im)
    f = Font(18).font
    for i, (name, imgs) in enumerate(rows):
        y = pad + i * (cell + pad)
        d.text((8, y + cell // 2 - 10), name, font=f, fill=(30, 30, 30))
        for k, img in enumerate(imgs):
            im.paste(img, (150 + k * (cell + pad), y))
    im.save(out)
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for st in (2, 1, 3, 0):
        out, _ = gif(st)
        print(out)
    print(strip(os.path.join(here, "grow-anim-strip.png")))
    for st, name in ((2, "awake"), (1, "almost"), (3, "bedtime"), (0, "sleep")):
        n, distinct, kinds, total = variety(st)
        print(f"{name:8s} 20 min: {n} clips, {distinct} distinct, {total:.0f} s of clip time, "
              f"kinds: {', '.join(kinds)}")
