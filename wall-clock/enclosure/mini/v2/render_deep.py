#!/usr/bin/env python3
"""The deep housing, alone and as the assembled clock, so the enclosure Sam
chose can be looked at before anything is sliced."""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from render import render
from params import *
import build_v2 as BV

TAG = sys.argv[1] if len(sys.argv) > 1 else '-32'
B   = {'': BV.BODY24, '-32': BV.BODY32, '-60': BV.BODY60}[TAG]
hou = trimesh.load(csg.part(f'mini-round-clock-housing{TAG}-deep.stl'), process=False)
stack = [hou]
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-diffuser{TAG}-plain.stl'):
    stack.append(trimesh.load(csg.part(fn), process=False))
clock = trimesh.util.concatenate(stack)

VIEWS = [('the housing, open', (-0.55, -0.85, 0.75)), ('from the back', (0.0, 0.0, -1.0))]
fig, ax = plt.subplots(1, 3, figsize=(13.8, 4.8), dpi=150)
for k, (label, eye) in enumerate(VIEWS):
    img, _ = render(hou, eye, (0, 0, 1) if k == 0 else (0, 1, 0), px=760)
    ax[k].imshow(img, cmap='bone', vmin=0, vmax=1); ax[k].set_title(label, fontsize=9)
    ax[k].axis('off')
img, _ = render(clock, (-0.75, -1.0, 0.55), (0, 0, 1), px=760)
ax[2].imshow(img, cmap='bone', vmin=0, vmax=1)
ax[2].set_title('the whole clock, closed', fontsize=9); ax[2].axis('off')
fig.suptitle(f'housing{TAG or "-24"}-deep — {hou.extents[2]:.1f} mm deep, '
             f'{hou.volume/1000:.1f} cm3; the clock is {Z_FRONT - hou.bounds[0][2]:.1f} mm front to back',
             fontsize=10)
fig.tight_layout(); fig.savefig(f'render_deep{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_deep{TAG or "-24"}.png')
