#!/usr/bin/env python3
"""How the ESP32-S3 is actually held, drawn over sections of the printed part.

Sam: "make sure that the mount for the ESP32 actually hold it and followed 3D
printer constraints." This is that answer as a picture. Everything is drawn
from params.py and from cross-sections of the built housing, so it is the
geometry being printed and not an illustration of it.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, Circle, FancyArrow
from params import *


def segs(m, z):
    V, F = m.vertices, m.faces; tri = V[F]; d = tri[:, :, 2] - z
    ns = (d > 0).sum(axis=1); sel = (ns == 1) | (ns == 2); tri, d = tri[sel], d[sel]
    o = []
    for t, dd in zip(tri, d):
        p = []
        for i in range(3):
            j = (i + 1) % 3
            if (dd[i] > 0) != (dd[j] > 0):
                f = dd[i] / (dd[i] - dd[j]); p.append(t[i] + f * (t[j] - t[i]))
        if len(p) == 2: o.append([p[0][:2], p[1][:2]])
    return np.array(o) if o else np.zeros((0, 2, 2))


H = trimesh.load('mini-round-clock-housing.stl'); H.merge_vertices()
ZP = Z_DECK - (PLATE_T + POCKET_DEEP) + PLATE_T      # pocket floor
HW = BOARD_W / 2
x_tip = BRD_X0 + BRD_FING_X0
x_root = x_tip + BRD_FING_L
PAD_I = HW - BOARD_PAD_EDGE - BOARD_PAD_OD / 2       # 10.58, where copper starts
PAD_O = HW - BOARD_PAD_EDGE + BOARD_PAD_OD / 2       # 12.28

fig, ax = plt.subplots(1, 2, figsize=(15.5, 7.4),
                       gridspec_kw={'width_ratios': [1.35, 1.0]})

# =============================================================== A: the whole frame
a = ax[0]
for z, c, lw in [(ZP + 2.0, '#9fb6cd', 1.0),
                 (ZP + BRD_LIP_Z0 + 0.6, '#1c3d6e', 1.5)]:
    s = segs(H, z)
    if len(s): a.add_collection(LineCollection(s, colors=c, linewidths=lw))

# the board
a.add_patch(Rectangle((BRD_X0, -HW), BOARD_L, BOARD_W,
                      fc='#2f7d4f', ec='#14532d', lw=1.6, alpha=.30))
# its pad rows -- the reason nothing can clamp the long edges
for sy in (1, -1):
    a.add_patch(Rectangle((BRD_X0 + BOARD_CONN_L, sy * PAD_I - (0 if sy > 0 else PAD_O - PAD_I)),
                          (BOARD_PAD_N - 1) * BOARD_PAD_PITCH + BOARD_PAD_OD,
                          PAD_O - PAD_I, fc='#c0392b', ec='none', alpha=.35))
# the two USB shells
for y0 in (-BOARD_CONN_Y, BOARD_CONN_Y - 7.95):
    a.add_patch(Rectangle((BRD_X0 - BOARD_CONN_OVER, y0), BOARD_CONN_L + BOARD_CONN_OVER,
                          7.95, fc='#555', ec='#222', lw=1.0, alpha=.45))
a.text((BRD_X0 + BRD_X1) / 2 + 6, 0, 'ESP32-S3-DevKitC-1\n62.74 x 25.40 x 1.60\nno mounting holes',
       ha='center', va='center', fontsize=9.5, color='#0d3b22', weight='bold')

lab = dict(fontsize=8.2, color='#1c3d6e',
           arrowprops=dict(arrowstyle='->', color='#1c3d6e', lw=.8))
a.annotate(f'rails, {2*BRD_RAIL_CLR:.2f} mm of slop across.\n'
           f'they touch the 1.60 mm EDGE only',
           (4.0, BRD_RAIL_Y + 1.0), (6, 30), ha='center', **lab)
a.annotate('end wall — takes the plug\'s push', (BRD_X1 + 1.5, -4.0), (22, -26), **lab)
a.annotate(f'snap finger, {BRD_FING_L:.0f} x {BRD_FING_T:.1f} mm.\n'
           f'flexes {BRD_FING_DEFL:.2f} mm outward, in the XY plane',
           (x_tip + 9, -(BRD_RAIL_Y + BRD_FING_T)), (-30, -34), ha='center',
           fontsize=8.2, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))
a.annotate('corner stops', (BRD_X0 - 0.5, BRD_STOP_RI + 1.0), (-50, -18),
           ha='center', **lab)
a.annotate('pad rows — copper to within\n0.42 mm of the edge, so nothing\ncan clamp the long edges',
           (-24, PAD_O), (-30, 42), ha='center', fontsize=8.2, color='#c0392b',
           arrowprops=dict(arrowstyle='->', color='#c0392b', lw=.8))
for px in (BRD_X0 + 3.0, (BRD_X0 + BRD_X1) / 2, BRD_X1 - 4.0):
    for py in (BRD_POST_HY, -BRD_POST_HY):
        a.add_patch(Circle((px, py), BRD_POST_D / 2, fc='none', ec='#7a5a06', lw=1.0, ls='--'))
a.annotate('posts, under bare board', (BRD_X0 + 3.0, -BRD_POST_HY), (-30, -46),
           fontsize=8.2, color='#7a5a06',
           arrowprops=dict(arrowstyle='->', color='#7a5a06', lw=.8))
for sy in (1, -1):
    a.add_patch(Rectangle((x_tip, sy*BRD_RAIL_Y - (0 if sy > 0 else BRD_FING_T)),
                          BRD_FING_L, BRD_FING_T,
                          fc='#d9a066', ec='#a0522d', lw=1.3))
    a.add_patch(Rectangle((x_tip, sy*(HW - BRD_FING_OVER) - (0 if sy > 0 else
                                      BRD_RAIL_Y - (HW - BRD_FING_OVER))),
                          BRD_FING_LIP_L, BRD_RAIL_Y - (HW - BRD_FING_OVER),
                          fc='#a0522d', ec='#7a3b16', lw=1.0))
a.set_title('The frame, seen into the pocket. Dark = at lip height, pale = at post height',
            fontsize=10.5)
a.set_xlim(-58, 40); a.set_ylim(-52, 52)

# =============================================================== B: one finger, detail
b = ax[1]
b.add_patch(Rectangle((BRD_X0, -HW), BOARD_L, BOARD_W,
                      fc='#2f7d4f', ec='#14532d', lw=1.4, alpha=.25))
b.add_patch(Rectangle((BRD_X0 + BOARD_CONN_L, PAD_I),
                      (BOARD_PAD_N - 1) * BOARD_PAD_PITCH + BOARD_PAD_OD,
                      PAD_O - PAD_I, fc='#c0392b', ec='none', alpha=.35))
b.add_patch(Rectangle((BRD_X0 - BOARD_CONN_OVER, BOARD_CONN_Y - 7.95),
                      BOARD_CONN_L + BOARD_CONN_OVER, 7.95,
                      fc='#555', ec='#222', lw=1.0, alpha=.45))
# the finger itself
b.add_patch(Rectangle((x_tip, BRD_RAIL_Y), BRD_FING_L, BRD_FING_T,
                      fc='#d9a066', ec='#a0522d', lw=1.6))
b.add_patch(Rectangle((x_root, BRD_RAIL_Y), 12.0, BRD_RAIL_T,
                      fc='#c8c8c8', ec='#666', lw=1.2))
b.add_patch(Rectangle((x_tip, HW - BRD_FING_OVER), BRD_FING_LIP_L,
                      BRD_RAIL_Y - (HW - BRD_FING_OVER),
                      fc='#a0522d', ec='#7a3b16', lw=1.2))
b.add_patch(Rectangle((x_tip, BRD_RAIL_Y + BRD_FING_T),
                      BRD_FING_L, BRD_FING_GAP, fc='#eef2f7', ec='#9fb6cd',
                      lw=1.0, ls='--'))
b.text(x_tip + BRD_FING_L / 2, BRD_RAIL_Y + BRD_FING_T + BRD_FING_GAP / 2,
       f'slot, {BRD_FING_GAP:.2f} mm', ha='center', va='center',
       fontsize=8, color='#5b7896')
b.annotate('', (x_tip + 2, BRD_RAIL_Y - 0.2),
           (x_tip + 2, BRD_RAIL_Y + BRD_FING_DEFL - 0.2),
           arrowprops=dict(arrowstyle='<->', color='#c0392b', lw=1.2))
b.text(x_tip + 2.6, BRD_RAIL_Y + BRD_FING_DEFL / 2,
       f'Y = {BRD_FING_DEFL:.2f}', fontsize=8.5, color='#c0392b', va='center')
b.annotate(f'lip, {BRD_FING_OVER:.2f} mm over the board,\n'
           f'landing {x_tip-BRD_X0:.0f}-{x_tip+BRD_FING_LIP_L-BRD_X0:.0f} mm along the board —\n'
           f'before the copper at {BOARD_CLEAR_CON:.2f}',
           (x_tip + 2, HW - BRD_FING_OVER / 2), (x_tip - 3, 3.0),
           fontsize=8.2, color='#7a3b16',
           arrowprops=dict(arrowstyle='->', color='#7a3b16', lw=.8))
b.annotate('root', (x_root, BRD_RAIL_Y + BRD_FING_T / 2), (x_root + 3, 19.0),
           fontsize=8.2, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))

txt = (f'straight cantilever\n'
       f'  e = 1.5 Y t / L$^2$\n'
       f'    = 1.5 x {BRD_FING_DEFL:.2f} x {BRD_FING_T:.2f} / {BRD_FING_L:.0f}$^2$\n'
       f'    = {100*BRD_FING_STRAIN:.2f} %   (PLA takes ~1.5 %)\n'
       f'  L/t = {BRD_FING_L/BRD_FING_T:.0f}:1   (8:1 is the floor for PLA)\n'
       f'  P   = b t$^2$ E e / 6L  ~ 2.7 N a finger\n\n'
       f'printed rear-plate-down, so the finger is a\n'
       f'WALL: its length and its bending are both in\n'
       f'the XY plane. A finger standing up in Z would\n'
       f'bend across the layer bonds, which is where\n'
       f'printed snap fits break.')
b.text(BRD_X0 + 1, -19.5, txt, fontsize=8.4, family='monospace',
       va='top', color='#2b2b2b',
       bbox=dict(boxstyle='round,pad=0.5', fc='#fbfaf6', ec='#c9c2ac'))
b.set_title('One snap finger, to scale', fontsize=10.5)
b.set_xlim(BRD_X0 - 4, BRD_X0 + 44); b.set_ylim(-30, 26)

for a_ in ax:
    a_.set_aspect('equal'); a_.grid(alpha=.18, lw=.4)
    a_.set_xlabel("+x is 12 o'clock  (mm)")
fig.suptitle('How the S3 is held — 6 o\'clock to the left, where its own USB port looks out',
             fontsize=12.5)
fig.tight_layout(); fig.savefig('render_fit.png', dpi=110)
print('wrote render_fit.png')
