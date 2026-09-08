#!/usr/bin/env python3
"""The stand-box: the one Sam picked. Plinth, tray, and the clock in it."""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render
from params import *
import build_v2 as BV

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
S = trimesh.load(csg.part(f'mini-round-clock-standbox{TAG}.stl'), process=False)
T = trimesh.load(csg.part(f'mini-round-clock-standbox-cradle{TAG}.stl'), process=False)

# THE CLOCK, PUT WHERE THE CRADLE WAS CUT FOR IT. The cradle is cut with a
# cylinder spanning local z -depth..0, so the clock's FRONT face is at local
# z = 0: shift by -Z_FRONT first, then the same rotate-and-lift _stand_solid
# uses. Guessing this transform put the clock through the floor of the base in
# the first render, which is a good reminder that a placement is a measurement.
depth = Z_FRONT - (Z_DECK - HOUSING_DEEP)
_, _, h0 = BV._stand_solid(B, depth, STANDBOX_TILT)
a = math.radians(90.0 - STANDBOX_TILT)
M = np.array([[1, 0, 0, 0],
              [0, math.cos(a), -math.sin(a), 0.0],
              [0, math.sin(a),  math.cos(a), h0],
              [0, 0, 0, 1]])
clock = []
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-housing{TAG}.stl', f'mini-round-clock-diffuser{TAG}-plain.stl'):
    m = trimesh.load(csg.part(fn), process=False)
    m.apply_translation([0.0, 0.0, -Z_FRONT])
    m.apply_transform(M)
    clock.append(m)
clock = trimesh.util.concatenate(clock)

# the tray, drawn PULLED OUT of the back so it reads as a drawer
tray_out = T.copy(); tray_out.apply_translation([0.0, 0.0, 34.0])

scenes = [('the plinth', S),
          ('the cradle, lifted off', trimesh.util.concatenate([S, tray_out]))]
fig, ax = plt.subplots(1, 3, figsize=(14.6, 5.4), dpi=150)
EYES = [(-0.72, -1.0, 0.55), (-0.72, -1.0, 0.35)]   # front three-quarter, then
                                                  # from BEHIND, which is the
                                                  # only view the drawer reads in
for k, (label, sc) in enumerate(scenes):
    img, _ = render(sc, EYES[k], (0, 0, 1), px=780)
    ax[k].imshow(img, cmap='bone', vmin=0, vmax=1)
    ax[k].set_title(label, fontsize=9); ax[k].axis('off')
img, _ = render(trimesh.util.concatenate([S, T, clock]), (-0.72, -1.0, 0.5), (0, 0, 1), px=780)
ax[2].imshow(img, cmap='bone', vmin=0, vmax=1)
ax[2].set_title('with the clock', fontsize=9); ax[2].axis('off')
fig.suptitle(f'standbox{TAG or "-24"} — {S.extents[0]:.0f} x {S.extents[1]:.0f} x '
             f'{S.extents[2] + T.extents[2] - STANDBOX_ROOF:.0f} mm, leaning back '
             f'{STANDBOX_TILT:.0f}°; the board drops into the well from above with its '
             f'loom on, and the cradle is the lid. Nothing open underneath.',
             fontsize=10)
fig.tight_layout(); fig.savefig(f'render_standbox{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_standbox{TAG or "-24"}.png')
