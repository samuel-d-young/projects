#!/usr/bin/env python3
"""The back-stand, alone and with the clock in it. Two views each, so the lean
and the open bay are both obvious before anything is sliced."""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render
from params import *
import build_v2 as BV

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
stand = trimesh.load(csg.part(f'mini-round-clock-backstand{TAG}.stl'), process=False)

# the clock, put where the stand expects it -- same transform the builder used
th = math.radians(BACKSTAND_TILT)
ct, st_ = math.cos(th), math.sin(th)
Zb = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)
z0 = BACKSTAND_SIT + B.r_body*ct - Zb*st_
y0 = B.r_body*st_ + Zb*ct
a  = math.radians(90.0 - BACKSTAND_TILT)
M  = np.array([[1, 0, 0, 0],
               [0, math.cos(a), -math.sin(a), y0],
               [0, math.sin(a),  math.cos(a), z0],
               [0, 0, 0, 1]], float)
clock = []
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-diffuser{TAG}-plain.stl'):
    m = trimesh.load(csg.part(fn), process=False); m.apply_transform(M); clock.append(m)
clock = trimesh.util.concatenate(clock)

VIEWS = [('three-quarter', (-0.75, -1.0, 0.55)), ('side', (-1.0, -0.06, 0.16))]
for name, scene in (('backstand', stand),
                    ('backstand-with-clock', trimesh.util.concatenate([stand, clock]))):
    fig, ax = plt.subplots(1, len(VIEWS), figsize=(4.6*len(VIEWS), 4.6), dpi=150)
    for k, (label, eye) in enumerate(VIEWS):
        img, hit = render(scene, eye, (0, 0, 1), px=760)
        ax[k].imshow(img, cmap='bone', vmin=0.0, vmax=1.0)
        ax[k].set_title(label, fontsize=9); ax[k].axis('off')
    fig.suptitle(f'{name}{TAG or "-24"}   {stand.extents[0]:.0f} x {stand.extents[1]:.0f} x '
                 f'{stand.extents[2]:.0f} mm, {stand.volume/1000:.1f} cm3',
                 fontsize=10)
    fig.tight_layout(); fig.savefig(f'render_{name}{TAG or "-24"}.png'); plt.close(fig)
    print(f'wrote render_{name}{TAG or "-24"}.png')
