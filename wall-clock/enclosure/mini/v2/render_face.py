#!/usr/bin/env python3
"""What the plywood face is, and what it looks like lit.

The middle panel is the point of the whole exercise and the only one that
answers the question Sam actually asked, which is whether sixty thin lines in
wood read as a clock.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle
from params import *
import build_v2 as BV
from make_face_svg import stadium

B = BV.BODY60
R = B.r_lip_i - PLY_CLR

fig, ax = plt.subplots(1, 3, figsize=(15.0, 5.6), dpi=150)

# ---- 1. the file, as the laser reads it --------------------------------------
a0 = ax[0]
a0.add_patch(Circle((0, 0), R, fc='white', ec='#FF0000', lw=1.0))
a0.add_patch(Circle((0, 0), PLY_BORE_R, fc='#f4f4f4', ec='#FF0000', lw=1.0))
for k in range(B.n):
    a0.add_patch(MPoly(stadium(B.tick_ri, B.tick_ro, PLY_TICK_W,
                               90.0 - k*360.0/B.n), fc='black', ec='none'))
a0.set_title('the file — black engraves, red cuts', fontsize=9)

# ---- 2. lit, on the wall ------------------------------------------------------
a1 = ax[1]
a1.set_facecolor('#15130f')
a1.add_patch(Circle((0, 0), B.r_body, fc='#2a2622', ec='none'))
a1.add_patch(Circle((0, 0), R, fc='#b98a4e', ec='#8a6334', lw=1.2))
# a plausible 10:09, and the whole minute ring low and warm
hr, mn = 10, 9
for k in range(B.n):
    ang = 90.0 - k*360.0/B.n
    lit, col = 0.16, '#ffd9a0'
    if k == mn:                       col, lit = '#ffffff', 1.0
    elif k == (hr % 12)*5:            col, lit = '#ffc14d', 0.95
    elif k % 5 == 0:                  lit = 0.34
    p = MPoly(stadium(B.tick_ri, B.tick_ro, PLY_TICK_W, ang),
              fc=col, ec='none', alpha=lit)
    a1.add_patch(p)
    if lit > 0.9:                     # a little bloom through the veneer
        a1.add_patch(MPoly(stadium(B.tick_ri, B.tick_ro, PLY_TICK_W + 2.6, ang),
                           fc=col, ec='none', alpha=0.16))
a1.add_patch(Circle((0, 0), PLY_BORE_R, fc='#0b0b0c', ec='none'))
a1.text(0, 2, f'{hr}:{mn:02d}', ha='center', va='center',
        color='#e8e8ea', fontsize=15, family='monospace')
a1.set_title('lit — 0.5 mm of veneer left on each line', fontsize=9)

# ---- 3. the coupon ------------------------------------------------------------
a2 = ax[2]
from make_face_svg import digit, PLY_HOUR_W
n, pitch = 5, 13.0
W = pitch*(n + 1) + 10.0
tick_len = B.tick_ro - B.tick_ri
H = tick_len + 22.0
cols = ['#FF00FF', '#00A0A0', '#804000', '#008000', '#606060']
a2.add_patch(MPoly([(-W/2, -H/2), (W/2, -H/2), (W/2, H/2), (-W/2, H/2)],
                   fc='#efe6d6', ec='#FF0000', lw=1.0))
for i in range(n + 1):
    x = -W/2 + 5.0 + pitch*i + pitch/2
    if i:
        for dx, w in ((-2.6, PLY_TICK_W), (2.6, PLY_HOUR_W)):
            a2.add_patch(MPoly([(x + dx + px, 3.0 + py)
                                for px, py in stadium(-tick_len/2, tick_len/2, w, 90.0)],
                               fc=cols[(i - 1) % len(cols)], ec='none'))
    for g in digit(i, x, -H/2 + 7.0, 7.0):
        a2.add_patch(MPoly(g, fc='black', ec='none'))
a2.set_title(f'depth coupon — {W:.0f} x {H:.1f} mm, 0 is left bare', fontsize=9)

for a, lim in ((a0, R + 4), (a1, B.r_body + 3), (a2, 48)):
    a.set_xlim(-lim, lim); a.set_ylim(-lim*0.62 if a is a2 else -lim, lim*0.62 if a is a2 else lim)
    a.set_aspect('equal'); a.axis('off')
fig.suptitle(f'60-LED clock — laser-cut {PLY_T:.0f} mm plywood face, '
             f'{2*R:.1f} mm across, {B.n} lines {PLY_TICK_W:.1f} mm wide '
             f'from r {B.tick_ri:.0f} to {B.tick_ro:.0f}. Engraved from the back; '
             f'the drawing is symmetric so it cannot go on the wrong way round.',
             fontsize=10)
fig.tight_layout()
fig.savefig('render_face-60.png', facecolor='white')
print('wrote render_face-60.png')
