#!/usr/bin/env python3
"""The rear end, v5a: what holds the S3 down and where the USB-C plug goes in.

Two views, both drawn from params.py:
  left   looking at the back of the clock, deck towards you
  right  a section on the 6 o'clock axis, with a plug going in
"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrow
from params import *

BOARD = '#2c6e49'; PLASTIC = '#cfd3d8'; EDGE = '#5a6069'
HOLD  = '#c1440e'; USB = '#1e5fa8'

def rect(ax, x0, x1, y0, y1, **kw):
    ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, **kw))

# ---------------------------------------------------------------- rear view
fig, (a, b) = plt.subplots(2, 1, figsize=(13.0, 13.4),
                           gridspec_kw={'height_ratios': [2.7, 1.0]})
a.add_patch(Circle((0,0), R_BODY, fc='#eef0f2', ec=EDGE, lw=1.2))
a.add_patch(Circle((0,0), R_INNER, fc='none', ec='#c9ced4', lw=0.8, ls=':'))
y1 = BOARD_W/2 + BOARD_CLR
rect(a, BOARD_X0 - BOARD_CLR, WINDOW_X1_EXT, -y1, y1, fc='#ffffff', ec=EDGE, lw=0.9)
rect(a, BOARD_X0, BOARD_X1, -BOARD_W/2, BOARD_W/2, fc=BOARD, ec='#1b4332', lw=0.9, alpha=.85)
a.text((BOARD_X0+BOARD_X1)/2, 0, 'ESP32-S3  62.74 x 25.40', ha='center', va='center',
       fontsize=8, color='white')
# ledges
for x0, x1 in ((BOARD_X0 - BOARD_CLR, BOARD_X0 - BOARD_CLR + LEDGE_END),
               (BOARD_X1 - LEDGE_END, BOARD_X1)):
    rect(a, x0, x1, -y1, y1, fc=PLASTIC, ec=EDGE, lw=0.8, hatch='///')
a.annotate(f'ledges, {LEDGE_END:.2f} mm\n(3.00 blocked the tilt-in)',
           (BOARD_X1 - LEDGE_END/2, -y1), (-58, -40), textcoords='offset points',
           fontsize=8, ha='center', arrowprops=dict(arrowstyle='->', lw=.8))
# beam
yo = BEAM_PILLAR_Y + BEAM_PILLAR_W/2
rect(a, -20 - BEAM_PILLAR_W/2, -20 + BEAM_PILLAR_W/2, -yo, yo,
     fc=HOLD, ec='none', alpha=.75)
a.annotate(f'beam over the USB end\nz {BEAM_Z0:.2f}, board tops out at 4.00\n'
           f'-> {BEAM_Z0-4.0:.2f} mm of float, was 4.60',
           (-20, -yo), (-58, -78), textcoords='offset points', fontsize=8, ha='center',
           arrowprops=dict(arrowstyle='->', lw=.8))
# keeper
rect(a, BOARD_X1 + 0.30, KEEP_PLATE_X1, -KEEP_PLATE_HY, KEEP_PLATE_HY,
     fc=HOLD, ec='none', alpha=.30)
rect(a, BOARD_X1 - KEEP_TONGUE_L, BOARD_X1 + 0.30, -KEEP_TONGUE_HY, KEEP_TONGUE_HY,
     fc=HOLD, ec='none', alpha=.75)
for sy in (1, -1):
    a.add_patch(Circle((KEEP_SCREW_X, sy*KEEP_SCREW_Y), KEEP_SCREW_D/2,
                       fc='white', ec=EDGE, lw=.8))
a.annotate('keeper, 2 x M3\n(goes on AFTER the board -\nif it were fixed, the\n'
           'board could not tilt in)',
           (KEEP_SCREW_X, KEEP_SCREW_Y), (46, 30), textcoords='offset points',
           fontsize=8, arrowprops=dict(arrowstyle='->', lw=.8))
# usb-c bay
rect(a, USBC_FACE_X, USBC_BAY_X1, -USBC_RAIL_HY, USBC_RAIL_HY,
     fc='#ffffff', ec=EDGE, lw=0.9)
rect(a, USBC_FACE_X, USBC_FACE_X + USBC_PCB_L, -USBC_PCB_W/2, USBC_PCB_W/2,
     fc=USB, ec='#0d3a68', lw=.9, alpha=.85)
rect(a, -R_BODY - 12, USBC_FACE_X, -PLUG_CH_W/2, PLUG_CH_W/2,
     fc='#ffffff', ec=EDGE, lw=.9, ls='--')
a.annotate(f'USB-C breakout (ADA4090)\n20.4 x 14.2, 5.1k CC resistors\n'
           f'-> the board\'s 5V / GND pins',
           ((2*USBC_FACE_X + USBC_PCB_L)/2, USBC_PCB_W/2), (-52, 62),
           textcoords='offset points', fontsize=8, ha='center',
           arrowprops=dict(arrowstyle='->', lw=.8))
a.annotate(f'plug channel {PLUG_CH_W:.2f} x {PLUG_CH_H:.2f}\n'
           f'narrower than the 14.20 PCB,\nso pulling the plug cannot\ndrag the breakout out',
           (-52, -PLUG_CH_W/2), (10, -84), textcoords='offset points', fontsize=8, ha='center',
           arrowprops=dict(arrowstyle='->', lw=.8))
a.set_xlim(-82, 86); a.set_ylim(-70, 70); a.set_aspect('equal'); a.axis('off')
a.set_title('Looking at the back of the clock (deck towards you)', fontsize=11)

# ---------------------------------------------------------------- section
b.set_title("Section on the 6 o'clock axis: the plug comes in from outside",
            fontsize=11, pad=6)
b.axhspan(Z_DECK, Z_BACK, -100, 100, color='#eef0f2')
rect(b, -R_BODY, -WIRE_SLOT_END, Z_BACK, 14.0, fc='#eef0f2', ec=EDGE, lw=1.0)
rect(b, -R_BODY, R_BODY, Z_DECK, Z_BACK, fc='#eef0f2', ec=EDGE, lw=1.0)
# plug channel through the wall
rect(b, -R_BODY - 1, USBC_FACE_X, PLUG_CH_Z0, PLUG_CH_Z0 + PLUG_CH_H,
     fc='white', ec=EDGE, lw=.9)
# the breakout
rect(b, USBC_FACE_X, USBC_FACE_X + USBC_PCB_L, USBC_Z, USBC_Z + 1.6,
     fc=USB, ec='#0d3a68', lw=.9)
rect(b, USBC_FACE_X, USBC_FACE_X + 8.0, USBC_Z + 1.6, USBC_Z + USBC_PCB_H,
     fc='#9fc0e6', ec='#0d3a68', lw=.9)
rect(b, USBC_FACE_X, USBC_BAY_X1, -0.0, USBC_Z, fc=PLASTIC, ec=EDGE, lw=.6)
rect(b, USBC_FACE_X, USBC_BAY_X1, USBC_LIP_Z0, USBC_LIP_Z1, fc=PLASTIC, ec=EDGE, lw=.6)
# the plug
plug_x0 = USBC_FACE_X - 20.0
rect(b, plug_x0, USBC_FACE_X, USBC_PORT_Z - PLUG_H/2, USBC_PORT_Z + PLUG_H/2,
     fc='#3c3f45', ec='#1b1d20', lw=.9)
rect(b, USBC_FACE_X, USBC_FACE_X + 6.5, USBC_PORT_Z - 1.3, USBC_PORT_Z + 1.3,
     fc='#8b8f96', ec='#1b1d20', lw=.7)
b.plot([plug_x0 - 16, plug_x0], [USBC_PORT_Z, USBC_PORT_Z], color='#3c3f45', lw=4,
       solid_capstyle='round')
b.annotate(f'{20.0 - (R_BODY + USBC_FACE_X):.0f} mm of overmold\nstands proud - grippable',
           (plug_x0 + 6, USBC_PORT_Z + PLUG_H/2), (-14, 30), textcoords='offset points',
           fontsize=8, ha='center', arrowprops=dict(arrowstyle='->', lw=.8))
b.annotate(f'socket sits {R_BODY + USBC_FACE_X:.2f} mm inside the rim',
           (USBC_FACE_X, USBC_Z + USBC_PCB_H), (34, 24), textcoords='offset points',
           fontsize=8, arrowprops=dict(arrowstyle='->', lw=.8))
# board and beam
rect(b, BOARD_X0, BOARD_X1, Z_BACK - 0.80, Z_BACK - 0.80 + BOARD_T,
     fc=BOARD, ec='#1b4332', lw=.9)
rect(b, BOARD_X0, BOARD_X1, Z_BACK + 0.80, Z_BACK + 0.80 + BOARD_TALL,
     fc=BOARD, ec='#1b4332', lw=.6, alpha=.35)
rect(b, -20 - BEAM_PILLAR_W/2, -20 + BEAM_PILLAR_W/2, BEAM_Z0, BEAM_Z1,
     fc=HOLD, ec='none')
rect(b, BOARD_X1 - KEEP_TONGUE_L, BOARD_X1 + 0.30, KEEP_TONGUE_Z0, KEEP_TONGUE_Z1,
     fc=HOLD, ec='none')
b.axhline(Z_SEAT, color='#9aa1a9', lw=.8, ls=':')
b.text(30, Z_SEAT + .5, 'display seat 8.60', fontsize=7.5, color='#6a7078')
b.set_xlim(-90, 62); b.set_ylim(-7, 17); b.set_aspect('equal'); b.axis('off')

fig.patch.set_facecolor('#f7f7f5')
fig.suptitle('v5a — the S3 held down, and USB-C brought out through the wall',
             fontsize=13.5)
fig.text(0.5, 0.02, 'Every dimension drawn from params.py. Verified on the built '
         'STLs by check5_v5a.py.', ha='center', fontsize=8.5, color='#777')
fig.tight_layout()
fig.savefig('render_v5a.png', dpi=110, bbox_inches='tight')
print('wrote render_v5a.png')
