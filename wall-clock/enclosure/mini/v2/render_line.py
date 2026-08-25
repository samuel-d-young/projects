#!/usr/bin/env python3
"""What the lit face looks like: the arc that was, against the radial tick.

    "the line needs to be perpendicular to the screen, like the lines are.
     I want the LED's to look more like the echo wall clock led's."

Drawn straight from params, so the pitch, the tick and the hour markings are
the geometry being printed. Only the glow is an impression.
"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, FancyBboxPatch
from matplotlib.transforms import Affine2D
from params import *
import build_v2 as BV
LIT   = {2: ('#ff5a14', 1.00),        # hour hand, amber
         9: ('#1e78ff', 1.00),        # minute hand, blue
        17: ('#9a9a9a', 0.85)}        # second dot, grey
FACE  = '#e8e4d9'
INK   = '#8d8778'


def tick_patch(ax, a_deg, ri, ro, w, col, alpha, zorder, grow=0.0):
    """A radial capsule centred on the a_deg ray."""
    L, W = (ro - ri) + 2*grow, w + 2*grow
    p = FancyBboxPatch((-L/2, -W/2), L, W, boxstyle=f'round,pad=0,rounding_size={W/2}',
                       fc=col, ec='none', alpha=alpha, zorder=zorder)
    rm = (ri + ro) / 2
    p.set_transform(Affine2D().rotate_deg(a_deg).translate(
        rm*math.cos(math.radians(a_deg)), rm*math.sin(math.radians(a_deg))) + ax.transData)
    ax.add_patch(p)


def arc_patch(ax, i, ri, ro, col, alpha, zorder, grow=0.0):
    a0 = CELL_WALL_A0 + i*PITCH + math.degrees(0.95/2/DIFF_LINE_R)
    a1 = CELL_WALL_A0 + (i+1)*PITCH - math.degrees(0.95/2/DIFF_LINE_R)
    ax.add_patch(Wedge((0,0), ro+grow, a0-grow*2, a1+grow*2, width=(ro-ri)+2*grow,
                       fc=col, alpha=alpha, ec='none', zorder=zorder))


def face(ax, B, title, sub):
    N, PITCH = B.n, B.pitch
    ax.set_facecolor('#14161a')
    ax.add_patch(Circle((0,0), B.ring_od/2 + 0.5, fc=FACE, ec='none', zorder=1))
    ax.add_patch(Circle((0,0), B.ring_id/2 - 0.5, fc='#14161a', ec='none', zorder=2))
    lit = {2: LIT[2], int(N*9/24): LIT[9], int(N*17/24): LIT[17]}
    for i in range(N):
        a = B.wall_a0 + (i + 0.5) * PITCH
        on = i in lit
        col, alpha = lit.get(i, ('#ddd8ca', 0.30))
        halo = [(2.6,.13), (1.5,.22), (0.6,.38), (0.0,1.0)] if on else [(0.0, alpha)]
        for k, (gr, ga) in enumerate(halo):
            tick_patch(ax, a, B.tick_ri, B.tick_ro, TICK_W, col,
                       ga*(alpha if on else 1.0), 3+k, gr)
    # All twelve now, and no plain marks. Drawn in the VIEWER's frame: on the
    # clock +x is up and -y is right, so the whole face is the model turned 90
    # degrees, and hour h -- at model angle -30h -- lands at 90 - 30h here.
    for h in range(1, 13):
        a = 90.0 - (h % 12)*30.0
        ax.text(B.num_r*math.cos(math.radians(a)), B.num_r*math.sin(math.radians(a)),
                NUMERALS[h], ha='center', va='center',
                fontsize=8.5*(B.num_h/NUM_H_24),
                color=INK, zorder=6, family='DejaVu Sans', weight='bold')
    ax.add_patch(Circle((0,0), DISP_ACTIVE_D/2, fc='#0b0d10', ec='#2a2e35', lw=1.0, zorder=7))
    ax.text(0, 3.5, '10:09', ha='center', va='center', fontsize=17,
            color='#dfe3ea', zorder=8, family='DejaVu Sans')
    ax.text(0, -6.0, '24\u00b0  clear', ha='center', va='center', fontsize=7.5,
            color='#7d838d', zorder=8)
    L = 64
    ax.set_xlim(-L, L); ax.set_ylim(-L, L); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12, color='#1c1c1c', pad=8)
    ax.text(0, -L-6, sub, ha='center', fontsize=9.5, color='#555')


fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.4))
for ax, B in zip(axes, (BV.BODY24, BV.BODY32)):
    gap = 2*math.pi*B.led_r/B.n - TICK_W
    face(ax, B, f'{B.n} LEDs \u2014 body {2*B.r_body:.0f} mm',
         f'ring {B.ring_od:g} / {B.ring_id:g}, tick {TICK_W:.2f} x '
         f'{B.tick_ro-B.tick_ri:.2f} mm, {gap:.2f} mm dark between')
fig.patch.set_facecolor('#f7f7f5')
fig.suptitle('The lit face: radial ticks on the LED circle, hours debossed on the '
             'diffuser', fontsize=13.5)
fig.text(0.5, 0.015, 'Drawn from params.py \u2014 cell pitch, tick size and every hour '
         'marking are the geometry being printed. The glow is an impression.',
         ha='center', fontsize=8.5, color='#777')
fig.tight_layout()
fig.savefig('render_line.png', dpi=110, bbox_inches='tight')
print('wrote render_line.png')
