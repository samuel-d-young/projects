#!/usr/bin/env python3
"""The stand-box, as ONE part with the bottom open.

Sam, 2026-09-08: "Make the base look much nicer, and the bottom can be fully
open, with a spot for ziptie down the ESP32 with the USB cable out he back."

Three views, and the middle one is the point: the stand turned over, which is
the only way anyone will ever see the shelves, the tie windows and the USB
opening, and the only view in which "there is a spot for the zip tie" is a
thing you can look at rather than a thing I claimed.
"""
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

# THE CLOCK, PUT WHERE THE SEAT WAS CUT FOR IT. The seat is cut with a cylinder
# spanning local z -depth..0, so the clock's FRONT face is at local z = 0: shift
# by -Z_FRONT first, then the same rotate-and-lift _stand_solid uses. Guessing
# this transform put the clock through the floor of the base in the first
# render, which is a good reminder that a placement is a measurement. depth is
# the FLAT back cover's -- the stand-box is cut for that clock, not the deep one.
depth = Z_FRONT - (Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET))
_, _, h0 = BV._stand_solid(B, depth, STANDBOX_TILT)
a = math.radians(90.0 - STANDBOX_TILT)
M = np.array([[1, 0, 0, 0],
              [0, math.cos(a), -math.sin(a), 0.0],
              [0, math.sin(a),  math.cos(a), h0],
              [0, 0, 0, 1]])
clock = []
for fn in (f'mini-round-clock-base{TAG}.stl', f'mini-round-clock-backcover{TAG}.stl',
           f'mini-round-clock-diffuser{TAG}-plain.stl'):
    m = trimesh.load(csg.part(fn), process=False)
    m.apply_translation([0.0, 0.0, -Z_FRONT])
    m.apply_transform(M)
    clock.append(m)
clock = trimesh.util.concatenate(clock)

# the board, on its shelves, drawn where check6 measures it
lo, hi = S.bounds
by1 = (hi[1] - STANDBOX_WALL) - 1.0
brd = trimesh.creation.box(extents=[BOARD2_W, BOARD2_L, BOARD_T])
brd.apply_translation([0.0, by1 - BOARD2_L/2.0,
                       STANDBOX_SHELF_Z + STANDBOX_SHELF_T + BOARD_T/2.0])

upside = S.copy()
upside.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
upside.apply_translation([0.0, 0.0, -upside.bounds[0][2]])

fig, ax = plt.subplots(1, 3, figsize=(14.6, 5.4), dpi=150)
views = [('the stand', S, (-0.72, -1.0, 0.55)),
         ('turned over: shelves, tie windows, USB', upside, (-0.62, -0.85, 0.75)),
         ('with the board and the clock',
          trimesh.util.concatenate([S, brd, clock]), (-0.72, -1.0, 0.5))]
for k, (label, sc, eye) in enumerate(views):
    img, _ = render(sc, eye, (0, 0, 1), px=780)
    ax[k].imshow(img, cmap='bone', vmin=0, vmax=1)
    ax[k].set_title(label, fontsize=9); ax[k].axis('off')
fig.suptitle(f'standbox{TAG or "-24"} — ONE part, {S.extents[0]:.0f} x {S.extents[1]:.0f} x '
             f'{S.extents[2]:.0f} mm, leaning back {STANDBOX_TILT:.0f}°. Bottom fully open; '
             f'the board tilts in from underneath onto two shelves and two cable ties '
             f'pass right round board and shelf. USB-C out the back.',
             fontsize=10)
fig.tight_layout(); fig.savefig(f'render_standbox{TAG or "-24"}.png'); plt.close(fig)
print(f'wrote render_standbox{TAG or "-24"}.png')
