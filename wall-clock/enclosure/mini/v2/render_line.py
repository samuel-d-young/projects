#!/usr/bin/env python3
"""What the lit face looks like: the old wide band against the new line.

Drawn straight from params, so it is the geometry being printed, not an
impression of it.
"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from params import *

BAFFLE_W = 0.95                       # measured on Sam's diffuser, at r=42
N        = DIFF_BAFFLE_N
PITCH    = 360.0 / N

# a plausible face: hour, minute, second, in the palette the firmware uses
LIT = {2: ('#ff5a14', 1.00),          # hour hand, amber
       9: ('#1e78ff', 1.00),          # minute hand, blue
      17: ('#9a9a9a', 0.85)}          # second dot, grey

def face(ax, r_in, r_out, title, sub):
    ax.set_facecolor('#14161a')
    # the plywood window, and the diffuser face you see through it
    ax.add_patch(Circle((0,0), RING_OD/2 + 0.5, fc='#e8e4d9', ec='none', zorder=1))
    ax.add_patch(Circle((0,0), RING_ID/2 - 0.5, fc='#14161a', ec='none', zorder=2))
    for i in range(N):
        # cell i is centred between two walls; walls sit at DIFF_BAFFLE_A0 + k*PITCH
        a0 = DIFF_BAFFLE_A0 + i*PITCH + math.degrees(BAFFLE_W/2/DIFF_LINE_R)
        a1 = DIFF_BAFFLE_A0 + (i+1)*PITCH - math.degrees(BAFFLE_W/2/DIFF_LINE_R)
        if i in LIT:
            col, alpha = LIT[i]
            for k, (gr, ga) in enumerate([(2.6, .13), (1.5, .22), (0.6, .38), (0.0, 1.0)]):
                ax.add_patch(Wedge((0,0), r_out+gr, a0-gr*2, a1+gr*2,
                                   width=(r_out-r_in)+2*gr, fc=col,
                                   alpha=ga*alpha, ec='none', zorder=3+k))
        else:
            # unlit, a cell is the same white PLA as everything round it. Barely
            # a tone difference -- which is the whole Echo look: a plain white
            # face, and light only where an LED is actually on.
            ax.add_patch(Wedge((0,0), r_out, a0, a1, width=r_out-r_in,
                               fc='#ddd8ca', alpha=.30, ec='none', zorder=3))
    # hour ticks, engraved in the plywood
    for h in range(12):
        a = math.radians(90 - h*30)
        rr = RING_ID/2 - 3.0
        L = 3.6 if h % 3 == 0 else 2.2
        ax.plot([rr*math.cos(a), (rr-L)*math.cos(a)], [rr*math.sin(a), (rr-L)*math.sin(a)],
                color='#8d8778', lw=2.4 if h % 3 == 0 else 1.4, zorder=6,
                solid_capstyle='round')
    ax.add_patch(Circle((0,0), DISP_ACTIVE_D/2, fc='#0b0d10', ec='#2a2e35', lw=1.0, zorder=7))
    ax.text(0, 3.5, '10:09', ha='center', va='center', fontsize=17,
            color='#dfe3ea', zorder=8, family='DejaVu Sans')
    ax.text(0, -6.0, '24°  clear', ha='center', va='center', fontsize=7.5,
            color='#7d838d', zorder=8)
    ax.set_xlim(-52, 52); ax.set_ylim(-52, 52); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12, color='#1c1c1c', pad=8)
    ax.text(0, -58, sub, ha='center', fontsize=9.5, color='#555')

fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.4))
face(axes[0], DIFF_MEM_RI, DIFF_MEM_RO, 'BEFORE — 5.90 mm band',
     f'each lit LED is {DIFF_MEM_RO-DIFF_MEM_RI:.2f} x 9.72 mm — 1.6:1, a blob')
face(axes[1], DIFF_LINE_RI, DIFF_LINE_RO, f'AFTER — {DIFF_LINE_W:.2f} mm line',
     f'each lit LED is {DIFF_LINE_W:.2f} x 9.72 mm — 3.9:1, a dash on a ring')
fig.patch.set_facecolor('#f7f7f5')
fig.suptitle('The lit face: aperture narrowed to a line, Echo-style', fontsize=13.5)
fig.text(0.5, 0.015, 'Drawn from params.py — cell pitch, wall width and aperture '
         'are the geometry being printed. The glow is an impression.',
         ha='center', fontsize=8.5, color='#777')
fig.tight_layout()
fig.savefig('render_line.png', dpi=110, bbox_inches='tight')
print('wrote render_line.png')
