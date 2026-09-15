#!/usr/bin/env python3
"""The dock: tray, cap, and the clock sitting in it."""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render
from params import *
import build_v2 as BV

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
T = trimesh.load(csg.part(f'mini-round-clock-dock{TAG}.stl'), process=False)
C = trimesh.load(csg.part(f'mini-round-clock-dock{TAG}-cap.stl'), process=False)
F = BV._dock_frame(B)

th = math.radians(DOCK_TILT)
a  = math.radians(90.0 - DOCK_TILT)
Zb = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)
z0 = (DOCK_H - DOCK_BED) + B.r_body*math.cos(th) - Zb*math.sin(th)
y0 = B.r_body*math.sin(th) + Zb*math.cos(th)
M  = np.array([[1,0,0,0],[0,math.cos(a),-math.sin(a),y0],[0,math.sin(a),math.cos(a),z0],[0,0,0,1]])
clock = []
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-housing{TAG}.stl', f'mini-round-clock-diffuser{TAG}-plain.stl'):
    mm = trimesh.load(csg.part(fn), process=False); mm.apply_transform(M); clock.append(mm)
clock = trimesh.util.concatenate(clock)

scenes = [('the tray', T), ('cap on', trimesh.util.concatenate([T, C])),
          ('with the clock', trimesh.util.concatenate([T, C, clock]))]
fig, ax = plt.subplots(1, 3, figsize=(14.2, 5.4), dpi=150)
for k, (label, sc) in enumerate(scenes):
    img, _ = render(sc, (-0.72, -1.0, 0.58), (0, 0, 1), px=780)
    ax[k].imshow(img, cmap='bone', vmin=0, vmax=1)
    ax[k].set_title(label, fontsize=9); ax[k].axis('off')
fig.suptitle(f'dock{TAG or "-24"} — {T.extents[0]:.0f} x {T.extents[1]:.0f} x {DOCK_H:.0f} mm, '
             f'closed on every face but the USB tunnel; the clock beds {DOCK_BED:.0f} mm '
             f'into a seat cut by its own shape',
             fontsize=10)
fig.tight_layout(); fig.savefig(f'render_dock{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_dock{TAG or "-24"}.png')
