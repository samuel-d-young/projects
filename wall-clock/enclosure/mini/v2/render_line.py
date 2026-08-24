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

N     = CELL_N
PITCH = 360.0 / N
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


def face(ax, mode, title, sub):
    ax.set_facecolor('#14161a')
    ax.add_patch(Circle((0,0), RING_OD/2 + 0.5, fc=FACE, ec='none', zorder=1))
    ax.add_patch(Circle((0,0), RING_ID/2 - 0.5, fc='#14161a', ec='none', zorder=2))

    for i in range(N):
        a = CELL_WALL_A0 + (i + 0.5) * PITCH
        lit = i in LIT
        col, alpha = LIT.get(i, ('#ddd8ca', 0.30))
        halo = [(2.6,.13), (1.5,.22), (0.6,.38), (0.0,1.0)] if lit else [(0.0, alpha)]
        for k, (gr, ga) in enumerate(halo):
            if mode == 'arc':
                arc_patch(ax, i, DIFF_LINE_RI, DIFF_LINE_RO, col,
                          ga*(alpha if lit else 1.0), 3+k, gr)
            else:
                tick_patch(ax, a, TICK_RI, TICK_RO, TICK_W, col,
                           ga*(alpha if lit else 1.0), 3+k, gr)

    # the hours, debossed on the diffuser itself (v5) or engraved in plywood (v4)
    for h in range(12):
        a = 90.0 - h*30.0
        key = int(round(a)) % 360
        if mode == 'tick' and key in NUMERALS:
            ax.text(NUM_R*math.cos(math.radians(a)), NUM_R*math.sin(math.radians(a)),
                    NUMERALS[key], ha='center', va='center', fontsize=8.5,
                    color=INK, zorder=6, family='DejaVu Sans', weight='bold')
            continue
        ri, ro = ((MARK_RI_MAJ, MARK_RO_MAJ) if h % 3 == 0 else (MARK_RI, MARK_RO)) \
                 if mode == 'tick' else (RING_ID/2 - 6.6, RING_ID/2 - 3.0)
        lw = (MARK_W_MAJ if h % 3 == 0 else MARK_W) * 1.6 if mode == 'tick' else \
             (2.4 if h % 3 == 0 else 1.4)
        r_ = math.radians(a)
        ax.plot([ri*math.cos(r_), ro*math.cos(r_)], [ri*math.sin(r_), ro*math.sin(r_)],
                color=INK, lw=lw, zorder=6, solid_capstyle='round')

    ax.add_patch(Circle((0,0), DISP_ACTIVE_D/2, fc='#0b0d10', ec='#2a2e35', lw=1.0, zorder=7))
    ax.text(0, 3.5, '10:09', ha='center', va='center', fontsize=17,
            color='#dfe3ea', zorder=8, family='DejaVu Sans')
    ax.text(0, -6.0, '24°  clear', ha='center', va='center', fontsize=7.5,
            color='#7d838d', zorder=8)
    ax.set_xlim(-52, 52); ax.set_ylim(-52, 52); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12, color='#1c1c1c', pad=8)
    ax.text(0, -58, sub, ha='center', fontsize=9.5, color='#555')


fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.4))
seg = 2*math.pi*DIFF_LINE_R/N - 0.95
face(axes[0], 'arc', f'v4 — {DIFF_LINE_W:.2f} mm arc, hours in the plywood',
     f'lit LED reads {DIFF_LINE_W:.2f} x {seg:.2f} mm, lying ALONG the circle')
face(axes[1], 'tick', f'v5 — {TICK_W:.2f} x {TICK_RO-TICK_RI:.2f} mm radial tick',
     f'lit LED reads {TICK_W:.2f} x {TICK_RO-TICK_RI:.2f} mm, pointing AT the centre')
fig.patch.set_facecolor('#f7f7f5')
fig.suptitle('The lit face: aperture turned 90 degrees, and the hours moved onto '
             'the diffuser', fontsize=13.5)
fig.text(0.5, 0.015, 'Drawn from params.py — cell pitch, tick size and every hour '
         'marking are the geometry being printed. The glow is an impression.',
         ha='center', fontsize=8.5, color='#777')
fig.tight_layout()
fig.savefig('render_line.png', dpi=110, bbox_inches='tight')
print('wrote render_line.png')
