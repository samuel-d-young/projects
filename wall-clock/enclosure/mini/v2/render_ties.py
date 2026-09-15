#!/usr/bin/env python3
"""Where the zip ties go. A plan view of the back-stand with every tie point
called out, because "add some holes for zip ties" is only useful if you can
tell at a glance which pair of slots is which and which way the tie runs.

Drawn from the EXPORTED mesh's own outline, not from the parameters -- the same
rule the checks follow, so a hole that did not survive the boolean does not
survive this drawing either.
"""
import sys; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from params import *

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
m = trimesh.load(csg.part(f'mini-round-clock-backstand{TAG}.stl'), process=False)

# A slice at mid-plate reads the through-slots; one just under the bay floor's
# top reads the rail notches as well.
def outline(ax, z, **kw):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None: return
    # to_2D() puts the section in ITS OWN frame, which for a z-normal plane
    # comes back mirrored in y -- the bosses drew below the board instead of
    # inside it. Push the vertices back through the transform it hands you
    # rather than trusting the 2D coordinates.
    p, T = sec.to_2D()
    for ent in p.entities:
        pts = p.vertices[ent.points]
        h = np.column_stack([pts, np.zeros(len(pts)), np.ones(len(pts))])
        w = (T @ h.T).T
        ax.plot(w[:, 0], w[:, 1], **kw)

fig, ax = plt.subplots(figsize=(9.0, 7.4), dpi=150)
outline(ax, (BACKSTAND_TIE_RELIEF + BACKSTAND_FOOT_T)/2.0, color='0.35', lw=1.1)
outline(ax, BACKSTAND_FOOT_T + 1.0, color='0.72', lw=0.8)

# the board, where it lands
bx, by0 = BOARD2_L/2.0, BACKSTAND_BAY_Y0
ax.add_patch(plt.Rectangle((-bx, by0), 2*bx, BOARD2_W, fc='#cfe3f5', ec='#5b87ad',
                           lw=1.0, zorder=0))
ax.text(0, by0 + BOARD2_W/2.0, 'ESP32-S3\n64 x 30', ha='center', va='center',
        fontsize=8, color='#2c5674', zorder=1)

def tie(cx, cy, gap, axis, label, note, lx, ly, ha='left'):
    d = np.array([0.0, 1.0]) if axis == 'x' else np.array([1.0, 0.0])
    a = np.array([cx, cy]) - d*gap/2.0
    b = np.array([cx, cy]) + d*gap/2.0
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<|-|>', mutation_scale=9,
                                 color='#c2410c', lw=1.6, zorder=3))
    ax.plot([cx], [cy], marker='o', ms=3, color='#c2410c', zorder=3)
    ax.annotate(f'{label}\n{note}', xy=(cx, cy), xytext=(lx, ly), ha=ha,
                fontsize=7.4, color='#7c2d12', zorder=4,
                arrowprops=dict(arrowstyle='-', color='#c2410c', lw=0.7,
                                shrinkA=0, shrinkB=2))

for sx in (-1.0, 1.0):
    tie(sx*BACKSTAND_TIE_BOARD_X,
        (BACKSTAND_TIE_BOARD_F + BACKSTAND_TIE_BOARD_B)/2.0,
        BACKSTAND_TIE_BOARD_B - BACKSTAND_TIE_BOARD_F, 'x',
        'board tie', 'over the board,\nunder the floor',
        sx*BACKSTAND_TIE_BOARD_X + sx*9, -12.0, 'center')
    tie(sx*BACKSTAND_TIE_LEAD_X, BACKSTAND_TIE_LEAD_Y,
        BACKSTAND_TIE_LEAD_G, 'y', 'lead tie', 'ring + power',
        sx*24.0, -20.0, 'center')
    tie(sx*BACKSTAND_TIE_END_X, BACKSTAND_TIE_END_Y,
        BACKSTAND_TIE_END_G, 'x', 'end tie', 'USB strain relief',
        sx*52.0, 40.0, 'center')

ax.set_aspect('equal'); ax.axis('off')
ax.set_title(f'back-stand{TAG or "-24"}: where the zip ties go\n'
             f'arrows show the loop; each pair of slots is joined by a '
             f'{BACKSTAND_TIE_RELIEF:.1f} mm relief in the underside, so the '
             f'tie sits flush and the stand still lies flat',
             fontsize=9.5)
fig.tight_layout(); fig.savefig(f'render_ties{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_ties{TAG or "-24"}.png')
