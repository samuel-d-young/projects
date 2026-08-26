#!/usr/bin/env python3
"""How the ESP32-S3 is actually held, drawn over sections of the printed part.

v13. Sam: "The mount for the S3 doesn't fit at all. Update it so it actually
fits. Find the correct dimensions for it." Both halves of that are in this
picture: the board outline and every feature on it come from Espressif's own
v1.1 dimension DXF, parsed rather than read off a picture, and every clearance
is drawn as the printer will leave it as well as as drawn.

Everything here is either params.py or a cross-section of the built housing,
so it is the geometry being printed and not an illustration of it.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, Circle
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
x_tip  = BRD_X0 + BRD_FING_X0
x_root = x_tip + BRD_FING_L
x_end  = BRD_X1 + BRD_END_CLR
x_pad  = BRD_X0 + BRD_CLAMP_PAD0
PAD_I = BOARD_PAD_ROW/2 - BOARD_PAD_OD/2             # 10.58, where copper starts
PAD_O = BOARD_PAD_ROW/2 + BOARD_PAD_OD/2             # 12.28

fig, ax = plt.subplots(1, 2, figsize=(16.5, 8.0),
                       gridspec_kw={'width_ratios': [1.28, 1.0]})

# =============================================================== A: the whole frame
a = ax[0]
for z, c, lw in [(ZP + 2.0, '#9fb6cd', 0.9),
                 (ZP + BRD_LIP_Z0 + 0.6, '#1c3d6e', 1.4)]:
    s = segs(H, z)
    if len(s): a.add_collection(LineCollection(s, colors=c, linewidths=lw))

a.add_patch(Rectangle((BRD_X0, -HW), BOARD_L, BOARD_W,
                      fc='#2f7d4f', ec='#14532d', lw=1.6, alpha=.26))
for sy in (1, -1):
    y0 = PAD_I if sy > 0 else -PAD_O
    a.add_patch(Rectangle((BRD_X0 + BOARD_PAD_X0 - BOARD_PAD_OD/2, y0),
                          BOARD_PAD_X1 - BOARD_PAD_X0 + BOARD_PAD_OD,
                          PAD_O - PAD_I, fc='#c0392b', ec='none', alpha=.35))
for cy in (-6.70, 6.70):
    a.add_patch(Rectangle((BRD_X0 - BOARD_CONN_OVER, cy - BOARD_CONN_W/2),
                          BOARD_CONN_L + BOARD_CONN_OVER, BOARD_CONN_W,
                          fc='#555', ec='#222', lw=1.0, alpha=.45))
a.add_patch(Rectangle((BRD_X0 + 18.0, -9.0), BOARD_MOD_END - 18.0, 18.0,
                      fc='none', ec='#14532d', lw=0.9, ls=':'))
a.text(BRD_X0 + (18.0 + BOARD_MOD_END)/2, 0,
       f"Sam's ESP32-S3\n{BOARD_L:.2f} x {BOARD_W:.2f} x {BOARD_T:.2f}, MEASURED\n"
       f'no mounting holes',
       ha='center', va='center', fontsize=9.5, color='#0d3b22', weight='bold')
for px in (BRD_X0 + 3.0, (BRD_X0 + BRD_X1)/2, x_pad + 1.5):
    for py in (BRD_POST_HY, -BRD_POST_HY):
        a.add_patch(Circle((px, py), BRD_POST_D/2, fc='none', ec='#7a5a06',
                           lw=1.0, ls='--'))
for sy in (1, -1):
    a.add_patch(Rectangle((x_tip, sy*BRD_RAIL_Y - (0 if sy > 0 else BRD_FING_T)),
                          BRD_FING_L, BRD_FING_T,
                          fc='#d9a066', ec='#a0522d', lw=1.3))
    a.add_patch(Rectangle((x_tip, sy*BRD_FING_YI - (0 if sy > 0 else
                                                    BRD_RAIL_Y - BRD_FING_YI)),
                          BRD_FING_LIP_L, BRD_RAIL_Y - BRD_FING_YI,
                          fc='#a0522d', ec='#7a3b16', lw=1.0))
a.add_patch(Rectangle((x_pad - 1.5, -BRD_CLAMP_W),
                      (BRD_CLAMP_SX + BRD_CLAMP_BOSS/2 + 1.5) - (x_pad - 1.5),
                      2*BRD_CLAMP_W, fc='#6a8fb5', ec='#1c3d6e', lw=1.3, alpha=.50))
for sy in (1, -1):
    a.add_patch(Circle((BRD_CLAMP_SX, sy*BRD_CLAMP_SY), BRD_CLAMP_BOSS/2,
                       fc='#c9d8e8', ec='#1c3d6e', lw=1.1))
    a.add_patch(Circle((BRD_CLAMP_SX, sy*BRD_CLAMP_SY), SCREW_PILOT/2,
                       fc='#1c3d6e', ec='none'))


lab = dict(fontsize=8.3, color='#1c3d6e',
           arrowprops=dict(arrowstyle='->', color='#1c3d6e', lw=.8))
a.annotate(f'rails — a GUIDE, not a fit.\n'
           f'drawn {2*BRD_RAIL_Y:.2f}, worst printed {2*BRD_RAIL_Y-FDM_SLOT_UNDER:.2f},\n'
           f'against {BOARD_W:.2f} of board.  v9 drew {BOARD_W + 0.20:.2f} —\n'
           f'an interference fit wearing the word "clearance".',
           (-2.0, BRD_RAIL_Y + BRD_RAIL_T), (6, 46), ha='center', **lab)
a.annotate(f'clamp bar — SCREWED down, and a separate part.\n'
           f'presses from {BRD_CLAMP_PAD0:.0f} mm along at |y| <= {BRD_CLAMP_Y:.1f}, BETWEEN\n'
           f'the pad rows, and both M3s land past the board\'s end —\n'
           f'so nothing crosses a row at any height. It goes on AFTER\n'
           f'the board, which is why nothing here overhangs and why\n'
           f'the board\'s length stopped mattering.',
           (BRD_CLAMP_SX, -BRD_CLAMP_SY - BRD_CLAMP_BOSS/2), (6, -52),
           ha='center', **lab)







a.annotate('corner stops — the datum in x', (BRD_X0 - 0.5, BRD_STOP_RI + 1.5),
           (-40, 30), ha='center', **lab)
a.annotate('pad rows — copper to within\n0.42 mm of the edge, so nothing\n'
           'may clamp the long edges,\nand nothing here does',
           (-24.0, PAD_O), (-44, 46), ha='center', fontsize=8.3, color='#c0392b',
           arrowprops=dict(arrowstyle='->', color='#c0392b', lw=.8))
a.annotate(f'snap fingers, {BRD_FING_L:.0f} x {BRD_FING_T:.1f} mm.\n'
           f'lip at |y| = {BRD_FING_YI:.2f}, set by the USB-C shell\n'
           f'at {BOARD_CONN_Y:.2f} and not by the board edge.\n'
           f'flexes {BRD_FING_DEFL:.2f} mm outward, in the XY plane.',
           (x_tip + 9, -(BRD_RAIL_Y + BRD_FING_T)), (-30, -28), ha='center',
           fontsize=8.3, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))
a.set_title('The frame, seen into the pocket.  dark = at lip height, pale = at post height',
            fontsize=10.5)
a.set_xlim(-64, 46); a.set_ylim(-64, 64)

# =============================================================== B: one finger, detail
b = ax[1]
b.add_patch(Rectangle((BRD_X0, -HW), BOARD_L, BOARD_W,
                      fc='#2f7d4f', ec='#14532d', lw=1.4, alpha=.20))
b.add_patch(Rectangle((BRD_X0 + BOARD_PAD_X0 - BOARD_PAD_OD/2, PAD_I),
                      BOARD_PAD_X1 - BOARD_PAD_X0 + BOARD_PAD_OD,
                      PAD_O - PAD_I, fc='#c0392b', ec='none', alpha=.35))
b.text(BRD_X0 + 17.0, (PAD_I + PAD_O)/2, 'copper', fontsize=7.6, color='#c0392b',
       va='center')
b.add_patch(Rectangle((BRD_X0 - BOARD_CONN_OVER, 6.70 - BOARD_CONN_W/2),
                      BOARD_CONN_L + BOARD_CONN_OVER, BOARD_CONN_W,
                      fc='#555', ec='#222', lw=1.0, alpha=.45))
b.text(BRD_X0 + 4.0, 6.70, 'USB-C', fontsize=7.4, color='#f4f4f4', ha='center',
       va='center')
b.add_patch(Rectangle((x_tip, BRD_RAIL_Y), BRD_FING_L, BRD_FING_T,
                      fc='#d9a066', ec='#a0522d', lw=1.6))
b.add_patch(Rectangle((x_root, BRD_RAIL_Y), 10.0, BRD_RAIL_T,
                      fc='#c8c8c8', ec='#666', lw=1.2))
b.add_patch(Rectangle((x_tip, BRD_FING_YI), BRD_FING_LIP_L,
                      BRD_RAIL_Y - BRD_FING_YI, fc='#a0522d', ec='#7a3b16', lw=1.2))
b.add_patch(Rectangle((x_tip, BRD_RAIL_Y + BRD_FING_T),
                      BRD_FING_L, BRD_FING_GAP, fc='#eef2f7', ec='#9fb6cd',
                      lw=1.0, ls='--'))
b.text(x_tip + BRD_FING_L/2, BRD_RAIL_Y + BRD_FING_T + BRD_FING_GAP/2,
       f'slot, {BRD_FING_GAP:.2f} mm', ha='center', va='center',
       fontsize=8, color='#5b7896')
# these five |y| are within 2.3 mm of each other, so the labels go on a
# ladder to the right with a leader each rather than on top of one another
XR = x_tip + BRD_FING_L + 1.0
LAD = [(BOARD_CONN_Y, '#333', f'{BOARD_CONN_Y:.2f}   USB-C shell'),
       (BOARD_CONN_Y + BRD_SHIFT_Y, '#8a8a8a',
        f'{BOARD_CONN_Y + BRD_SHIFT_Y:.2f}   ...board shifted {BRD_SHIFT_Y:.2f}'),
       (BRD_FING_YI, '#7a3b16', f'{BRD_FING_YI:.2f}   the lip'),
       (HW, '#14532d', f'{HW:.2f}   board edge'),
       (BRD_RAIL_Y, '#666', f'{BRD_RAIL_Y:.2f}   rail')]
for i, (yv, col, txt) in enumerate(sorted(LAD)):
    ly = 1.0 + 3.2*i
    b.plot([BRD_X0 - 1.5, XR], [yv, yv], color=col, lw=.6, ls=':')
    b.plot([XR, XR + 2.5], [yv, ly], color=col, lw=.6)
    b.text(XR + 3.0, ly, txt, fontsize=7.9, color=col, va='center')
b.annotate('', (x_tip + 1.6, BRD_FING_YI), (x_tip + 1.6, BRD_FING_YI + BRD_FING_DEFL),
           arrowprops=dict(arrowstyle='<->', color='#c0392b', lw=1.2))
b.text(x_tip + 2.2, BRD_FING_YI + BRD_FING_DEFL/2,
       f'Y = {BRD_FING_DEFL:.2f}', fontsize=8.5, color='#c0392b', va='center')

txt = (f'straight cantilever\n'
       f'  e = 1.5 Y t / L$^2$\n'
       f'    = 1.5 x {BRD_FING_DEFL:.2f} x {BRD_FING_T:.2f} / {BRD_FING_L:.0f}$^2$\n'
       f'    = {100*BRD_FING_STRAIN:.2f} %   (PLA takes ~{100*BRD_FING_EMAX:.1f} %)\n'
       f'  L/t = {BRD_FING_L/BRD_FING_T:.1f}:1  (8:1 is the floor for PLA)\n'
       f'  P   = b t$^2$ E e / 6L  ~ 3.1 N a finger\n\n'
       f'printed rear-plate-down, so the finger is a WALL:\n'
       f'its length and its bending are both in the XY\n'
       f'plane. A finger standing up in Z would bend across\n'
       f'the layer bonds, which is where printed snaps break.\n\n'
       f'{BOARD_L:.2f} x {BOARD_W:.2f} is SAM\'S CALIPERS, not Espressif.\n'
       f'his board is 2.79 mm wider than the DevKitC-1 v1.1\n'
       f'outline, so it is a different board -- and every\n'
       f'vendor figure for the part contradicted every other\n'
       f'one anyway (70x28, 67x31, 55x35, all published).\n\n'
       f'the bay takes {BOARD_L_MIN:.1f}-{BOARD_L_MAX:.1f} long, up to {BOARD_W_MAX:.1f} wide. that\n'
       f'window is wide because the clamp is a SCREW: a\n'
       f'screwed bar does not care how long the board is,\n'
       f'it only has to land on it.')
b.text(BRD_X0 + 0.5, -12.0, txt, fontsize=8.3, family='monospace',
       va='top', color='#2b2b2b',
       bbox=dict(boxstyle='round,pad=0.5', fc='#fbfaf6', ec='#c9c2ac'))
b.set_title('One snap finger, to scale — and the numbers that place its lip',
            fontsize=10.5)
b.set_xlim(BRD_X0 - 3, BRD_X0 + 58); b.set_ylim(-46, 22)

for a_ in ax:
    a_.set_aspect('equal'); a_.grid(alpha=.16, lw=.4)
    a_.set_xlabel("+x is 12 o'clock  (mm)")
fig.suptitle("How the S3 is held (v14) — 6 o'clock to the left, where its own "
             "USB port looks out", fontsize=12.5)
fig.tight_layout(); fig.savefig('render_fit.png', dpi=110)
print('wrote render_fit.png')
