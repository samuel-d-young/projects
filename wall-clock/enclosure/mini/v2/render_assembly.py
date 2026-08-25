#!/usr/bin/env python3
"""Exploded and assembled views — the picture that makes the build obvious."""
import sys; sys.path.insert(0,'.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render, VIEWS
from params import *

def shift(fn, dz, dy=0.0, mirror_y=False):
    m = trimesh.load(fn, process=False); m.merge_vertices()
    if mirror_y:
        m.apply_transform(np.diag([1.0,-1.0,1.0,1.0])); m.invert()
    m.apply_translation([0, dy, dz]); return m

def stack(parts, sep=0.0):
    ms = []
    for fn, dz, dy, mir in parts:
        ms.append(shift(fn, dz + sep*0, dy, mir))
    return trimesh.util.concatenate(ms)

EXPLODE = 26.0
sets = {
 'assembled': [('mini-round-clock-base.stl',0,0,False),
               ('mini-round-clock-housing.stl',0,0,False),
               ('mini-round-clock-battery-shelf-x2.stl', Z_REAR+PLATE_T, 0, False),
               ('mini-round-clock-battery-shelf-x2.stl', Z_REAR+PLATE_T, 0, True)],
 'exploded':  [('mini-round-clock-base.stl', EXPLODE,0,False),
               ('mini-round-clock-housing.stl',0,0,False),
               ('mini-round-clock-battery-shelf-x2.stl', Z_REAR+PLATE_T-EXPLODE*1.6, 0, False),
               ('mini-round-clock-battery-shelf-x2.stl', Z_REAR+PLATE_T-EXPLODE*1.6, 0, True)],
}
A = stack(sets['assembled']); E = stack(sets['exploded'])

fig, axes = plt.subplots(1, 3, figsize=(16, 6.0))
for ax,(m,v,t) in zip(axes, [(A,'iso_r','ASSEMBLED - from the rear'),
                             (A,'side','ASSEMBLED - side. 12 o\'clock up, wall to the right'),
                             (E,'iso_r','EXPLODED - base / housing / two shims')]):
    eye, up = VIEWS[v]
    img, hit = render(m, eye, up, px=760)
    rgb = plt.get_cmap('bone')(np.nan_to_num(img))[...,:3]; rgb[~hit]=0.96
    ax.imshow(rgb); ax.axis('off'); ax.set_title(t, fontsize=11)
fig.patch.set_facecolor('#f7f7f5'); fig.tight_layout(); fig.savefig('render_assembly.png', dpi=105)
print('wrote render_assembly.png')
