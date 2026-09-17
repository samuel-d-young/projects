#!/usr/bin/env python3
"""Look at the plugs. The coupon's numerals passed a check that counted
segments and were still unreadable; rendering is what found it."""
import numpy as np, trimesh, csg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from params import *


def load(n):
    t = trimesh.load(csg.part(n), process=False); t.merge_vertices()
    return t


def silhouette(ax, m, ax0, ax1, colour):
    tris = m.vertices[m.faces][:, :, [ax0, ax1]]
    ax.add_collection(PolyCollection(tris, facecolors=colour, edgecolors='none'))
    v = m.vertices
    ax.set_xlim(v[:, ax0].min() - 1, v[:, ax0].max() + 1)
    ax.set_ylim(v[:, ax1].min() - 1, v[:, ax1].max() + 1)


fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))

# ---- one plug, from the side (length x height) ----------------------------
pl = load('mini-round-clock-face-60-plugs.stl').split(only_watertight=False)
p = pl[0].copy(); p.apply_translation(-p.bounds.mean(axis=0) * [1, 1, 0])
silhouette(axes[0], p, 1, 2, '#d8d8d8')
axes[0].axhline(0.0, color='#b06000', lw=1.2)
axes[0].axhline(PLUG_T, color='#b06000', lw=1.2, ls='--')
axes[0].text(0, PLUG_T + 0.45, 'front of the clock (flush)', ha='center',
             fontsize=8, color='#b06000')
axes[0].text(0, -PLUG_FLANGE_T - 1.0, "wood's back face", ha='center',
             fontsize=8, color='#b06000')
axes[0].set_title(f'one plug from the side — body {PLUG_T:.2f} through the ply,\n'
                  f'flange {PLUG_FLANGE_T:.2f} behind it', fontsize=9)

# ---- the same plug end-on (width x height), with the slot drawn round it --
silhouette(axes[1], p, 0, 2, '#d8d8d8')
hw = (PLY_TICK_W + PLUG_KERF) / 2.0
axes[1].add_collection(PolyCollection(
    [[(-hw, 0), (hw, 0), (hw, PLUG_T), (-hw, PLUG_T)]],
    facecolors='none', edgecolors='#c00000', linewidths=1.4, linestyles='--'))
axes[1].set_xlim(-4, 4); axes[1].set_ylim(-1.4, 4)
axes[1].set_title(f'end-on — plug {PLUG_W:.2f} wide (grey) in the {2*hw:.2f} hole\n'
                  f'the laser leaves (red): {PLUG_W-2*hw:.2f} interference',
                  fontsize=9)

# ---- the fit test, seen from BEHIND, which is where the numbers are -------
ft = load('mini-round-clock-face-60-plug-fit-test.stl')
# Pick the numeral's faces off the ORIGINAL mesh by height. slice_plane(cap=True)
# looked like the obvious way and is not: its cap spans the whole flange
# cross-section, so the projection came out as six solid stadiums with no
# numbers on them -- which is exactly what an unreadable digit would look like.
# The check said the marks were there and measured 0.80 to 2.84 mm3; the render
# was the thing that was wrong.
cut = ft.bounds[0][2] + PLUG_TEST_MARK_H
tri = ft.vertices[ft.faces]
is_mark = (tri[:, :, 2] < cut - 1e-6).all(axis=1)
axes[2].add_collection(PolyCollection(tri[~is_mark][:, :, :2],
                                      facecolors='#ededed', edgecolors='none'))
axes[2].add_collection(PolyCollection(tri[is_mark][:, :, :2],
                                      facecolors='#202020', edgecolors='none'))
v = ft.vertices
axes[2].set_xlim(v[:, 0].min() - 2, v[:, 0].max() + 2)
axes[2].set_ylim(v[:, 1].min() - 2, v[:, 1].max() + 2)
axes[2].set_title('the fit test from behind — 1 is loosest, 6 tightest\n'
                  f'{1.95:.2f} to {2.20:.2f} in 0.05 steps', fontsize=9)

for a in axes:
    a.set_aspect('equal'); a.axis('off')
fig.suptitle('White press-fit plugs for a cut-through plywood face — '
             f'{PLUG_W:.2f} x {PLUG_FLANGE_LEN - 2*PLUG_END_INSET:.2f} body, '
             f'{PLUG_FLANGE_W:.2f} x {PLUG_FLANGE_LEN:.2f} flange', fontsize=11)
fig.tight_layout()
fig.savefig('render_plugs.png', dpi=110)
print('wrote render_plugs.png')
