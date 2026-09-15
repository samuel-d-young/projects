#!/usr/bin/env python3
"""The plinth and its lid, open and closed, with the clock in place."""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render
from params import *
import build_v2 as BV

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
P = trimesh.load(csg.part(f'mini-round-clock-plinth{TAG}.stl'), process=False)
L = trimesh.load(csg.part(f'mini-round-clock-plinth{TAG}-lid.stl'), process=False)
lid = L.copy(); lid.apply_translation([0, 0, BACKSTAND_FOOT_T + PLINTH_LID_Z])

th = math.radians(BACKSTAND_TILT); ct, st_ = math.cos(th), math.sin(th)
Zb = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)
z0 = BACKSTAND_SIT + B.r_body*ct - Zb*st_
y0 = B.r_body*st_ + Zb*ct
a  = math.radians(90.0 - BACKSTAND_TILT)
M  = np.array([[1,0,0,0],[0,math.cos(a),-math.sin(a),y0],[0,math.sin(a),math.cos(a),z0],[0,0,0,1]])
clock = []
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-housing{TAG}.stl', f'mini-round-clock-diffuser{TAG}-plain.stl'):
    mm = trimesh.load(csg.part(fn), process=False); mm.apply_transform(M); clock.append(mm)
clock = trimesh.util.concatenate(clock)

scenes = [('bay open', P),
          ('lid on', trimesh.util.concatenate([P, lid])),
          ('with the clock', trimesh.util.concatenate([P, lid, clock]))]
fig, ax = plt.subplots(1, 3, figsize=(14.2, 4.9), dpi=150)
for k, (label, sc) in enumerate(scenes):
    img, _ = render(sc, (-0.75, -1.0, 0.62), (0, 0, 1), px=760)
    ax[k].imshow(img, cmap='bone', vmin=0, vmax=1)
    ax[k].set_title(label, fontsize=9); ax[k].axis('off')
fig.suptitle(f'plinth{TAG or "-24"} — {P.extents[0]:.0f} x {P.extents[1]:.0f} x '
             f'{P.extents[2]:.0f} mm, {P.volume/1000:.1f} cm3 plus a '
             f'{L.volume/1000:.1f} cm3 lid; {PLINTH_LID_Z - BOARD_T:.1f} mm of clear air over the board',
             fontsize=10)
fig.tight_layout(); fig.savefig(f'render_plinth{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_plinth{TAG or "-24"}.png')
