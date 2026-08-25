#!/usr/bin/env python3
"""Dimensioned section drawings of the assembly -- the closest thing this
project has to a set of sketches.

There are no sketches. The STLs are not drawn, they are generated: params.py
holds every dimension with a note on where it came from, build_v2.py builds the
solids by constructive geometry, and five checkers measure the result. This
script closes the loop the other way -- it slices the BUILT files and annotates
them with the numbers from params, so the drawing cannot drift from the part.

    python3 sketch_sections.py     ->  sketch_sections.png

Everything on the left of a panel is a real section through a real STL. Every
dimension is read from params.py at draw time.
"""
import sys, math; sys.path.insert(0, '.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, Polygon
from params import *
import build_v2 as BV

INK, DIM, BUY = '#1c3d6e', '#c0392b', '#7a5a06'


def load(fn):
    m = trimesh.load(fn, process=False); m.merge_vertices(); return m


def section(m, flip_to=None):
    """The part's outline in the x-z plane, as line segments.

    Sliced on the plane y=0, which for a body this close to round is its
    profile. flip_to turns the diffuser over and drops it onto its seat, the
    way it is actually installed: z_base = flip_to - z_diff.
    """
    m = m.copy()
    if flip_to is not None:
        m.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))
        m.apply_translation([0, 0, flip_to])
    sec = m.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return np.zeros((0, 2, 2))
    out = []
    for e in sec.entities:
        p = sec.vertices[e.points]
        out.extend([[p[i][[0, 2]], p[i + 1][[0, 2]]] for i in range(len(p) - 1)])
    return np.array(out) if out else np.zeros((0, 2, 2))


def draw(ax, segs, colour, lw=1.1, half=True):
    if len(segs) == 0: return
    if half:                       # keep the +x half; the section is symmetric
        segs = segs[(segs[:, :, 0] >= -0.01).all(axis=1)]
    ax.add_collection(LineCollection(segs, colors=colour, linewidths=lw, zorder=3))


def hdim(ax, x0, x1, y, text, colour=DIM, off=0.0, fs=7.0):
    """A horizontal dimension with witness ticks."""
    ax.annotate('', (x0, y), (x1, y),
                arrowprops=dict(arrowstyle='<->', color=colour, lw=0.8), zorder=6)
    ax.text((x0 + x1) / 2, y + off, text, ha='center', va='bottom',
            fontsize=fs, color=colour, zorder=6)


def zdim(ax, x, z0, z1, text, colour=DIM, fs=7.0, side=1):
    """A vertical dimension, with a leader out to the label."""
    ax.annotate('', (x, z0), (x, z1),
                arrowprops=dict(arrowstyle='<->', color=colour, lw=0.8), zorder=6)
    ax.text(x + 1.2 * side, (z0 + z1) / 2, text, ha='left' if side > 0 else 'right',
            va='center', fontsize=fs, color=colour, zorder=6)


def level(ax, z, x0, x1, text, colour=DIM, fs=7.0):
    """A datum line across the drawing at height z."""
    ax.plot([x0, x1], [z, z], color=colour, lw=0.5, ls=(0, (6, 3)), zorder=2, alpha=.75)
    ax.text(x1 + 0.6, z, text, ha='left', va='center', fontsize=fs, color=colour, zorder=6)


def levels(ax, x0, x1, rows, colour=DIM, fs=7.0, gap=1.9):
    """A stack of datum lines whose LABELS are nudged apart, with a leader from
    each label back to its true height. Several of these heights are within a
    tenth of a millimetre of one another -- 19.03 and 21.93 and 22.00 -- and
    stacked labels at true height are unreadable."""
    rows = sorted(rows, key=lambda r: r[0])
    ys, last = [], -1e9
    for z, _ in rows:
        y = max(z, last + gap); ys.append(y); last = y
    span = ys[-1] - ys[0]
    if span > 0:                      # recentre the stack on the true range
        shift = ((rows[-1][0] + rows[0][0]) - (ys[-1] + ys[0])) / 2
        ys = [y + shift for y in ys]
    for (z, text), y in zip(rows, ys):
        ax.plot([x0, x1], [z, z], color=colour, lw=0.5, ls=(0, (6, 3)),
                zorder=2, alpha=.75)
        if abs(y - z) > 0.05:
            ax.plot([x1, x1 + 1.6], [z, y], color=colour, lw=0.5, alpha=.75, zorder=2)
        ax.text(x1 + 2.0, y, text, ha='left', va='center', fontsize=fs,
                color=colour, zorder=6)


# =============================================================================
B = BV.BODY24
BASE = load('mini-round-clock-base.stl')
HOUS = load('mini-round-clock-housing.stl')
DIFF = load('mini-round-clock-diffuser.stl')

ZP = Z_DECK - (PLATE_T + POCKET_DEEP) + PLATE_T          # housing pocket floor
RING_TOP = B.ring_floor + PCB_T + LED_H

fig = plt.figure(figsize=(19.0, 11.5))
gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1.0], height_ratios=[1.0, 0.82],
                      hspace=0.22, wspace=0.16)

# ---------------------------------------------------- A: the whole stack
a = fig.add_subplot(gs[:, 0])
draw(a, section(BASE), INK, 1.3)
draw(a, section(HOUS), '#2f7d4f', 1.1)
draw(a, section(DIFF, flip_to=DIFF_SEAT_Z), '#a0522d', 1.1)

# the bought parts, hatched
a.add_patch(Rectangle((B.ring_id/2, B.ring_floor), (B.ring_od - B.ring_id)/2,
                      PCB_T + LED_H, fc='none', ec=BUY, hatch='////', lw=1.0, zorder=4))
a.annotate(f'WS2812B ring  {B.ring_od:.0f} / {B.ring_id:.0f}, '
           f'PCB {PCB_T:.1f} + LED {LED_H:.1f}',
           (B.led_r, RING_TOP), (2.0, 4.0), fontsize=7.2, color=BUY,
           arrowprops=dict(arrowstyle='->', color=BUY, lw=.8))
a.add_patch(Rectangle((0, Z_SEAT), DISP_PCB_D/2, DISP_T,
                      fc='none', ec=BUY, hatch='\\\\\\\\', lw=1.0, zorder=4))
a.annotate(f'display module {DISP_PCB_D:.0f} dia x {DISP_T:.1f} overall\n'
           f'(rim thickness at r=29 NOT MEASURED)',
           (14.0, Z_SEAT + DISP_T), (2.0, 17.5), fontsize=7.2, color=BUY,
           arrowprops=dict(arrowstyle='->', color=BUY, lw=.8))
zt = ZP + BRD_POST_H
a.add_patch(Rectangle((0, zt), abs(BRD_X0), BOARD_T,
                      fc='none', ec=BUY, hatch='xxxx', lw=1.0, zorder=4))
a.annotate(f'ESP32-S3-DevKitC-1, {BOARD_L:.2f} x {BOARD_W:.2f} x {BOARD_T:.1f}\n'
           f'sectioned along its length. NO MOUNTING HOLES —\n'
           f'it is held by rails, an end wall, corner stops and two snap fingers',
           (25.0, zt), (2.0, -31.0), fontsize=7.2, color=BUY,
           arrowprops=dict(arrowstyle='->', color=BUY, lw=.8))

XR = 58.0
levels(a, 0, XR, [
    (Z_DECK - POCKET_DEEP - PLATE_T, f'{Z_DECK-POCKET_DEEP-PLATE_T:.2f}  housing rear plate'),
    (ZP,              f'{ZP:.2f}  housing pocket floor'),
    (Z_DECK,          f'{Z_DECK:.2f}  deck / the two halves mate'),
    (0.0,             f' 0.00  datum: the back of Sam\'s base'),
    (Z_SEAT,          f'{Z_SEAT:.2f}  display seat'),
    (B.ring_floor,    f'{B.ring_floor:.2f}  ring pocket floor'),
    (RING_TOP,        f'{RING_TOP:.2f}  LED tops'),
    (DIFF_WALL_CREST, f'{DIFF_WALL_CREST:.2f}  WALL CREST — the diffuser\'s face lands here.'
                      f'\n         This, not the press fit, is what sets its depth.'),
    (DIFF_SEAT_Z,     f'{DIFF_SEAT_Z:.2f}  outer surface of the diffuser'),
    (Z_FRONT,         f'{Z_FRONT:.2f}  front of the clock'),
], gap=3.4)

zdim(a, 124.0, Z_DECK - POCKET_DEEP - PLATE_T, Z_FRONT,
     f'{Z_FRONT - (Z_DECK - POCKET_DEEP - PLATE_T):.2f} overall', colour='#111', fs=8.5)
zdim(a, 117.0, Z_DECK - POCKET_DEEP - PLATE_T, Z_DECK, f'{HOUSING_DEEP:.2f} housing')
zdim(a, 117.0, Z_DECK, Z_FRONT, f'{Z_FRONT - Z_DECK:.2f} base')
zdim(a, 56.0, DIFF_SEAT_Z - BAND_TOP, RING_TOP,
     f'{DIFF_SEAT_Z - BAND_TOP - RING_TOP:.2f}', side=-1)

a.set_title('A — the stack in section, 24-LED body. Blue = base, green = housing, '
            'brown = diffuser (drawn installed)', fontsize=10.5)
a.set_xlim(-3, 132); a.set_ylim(-37, 28)
a.set_xlabel('radius (mm)'); a.set_ylabel('z (mm) — 0 is the back of Sam\'s base')

# ---------------------------------------------------- B: the collar fit
b = fig.add_subplot(gs[0, 1])
draw(b, section(BASE), INK, 1.3)
draw(b, section(DIFF, flip_to=DIFF_SEAT_Z), '#a0522d', 1.3)
b.add_patch(Rectangle((0, Z_SEAT), DISP_PCB_D/2, DISP_T,
                      fc='none', ec=BUY, hatch='\\\\\\\\', lw=1.0, zorder=4))
TIP = DIFF_SEAT_Z - (DIFF_COLLAR_H + COLLAR_EXTEND)
for z, txt in [(DIFF_WALL_CREST, f'{DIFF_WALL_CREST:.2f}  wall crest'),
               (DIFF_SEAT_Z, f'{DIFF_SEAT_Z:.2f}  face')]:
    level(b, z, 46.5, 51.0, txt)
b.plot([22.0, 30.5], [TIP, TIP], color='#a0522d', lw=0.6, ls=(0, (5, 3)), zorder=2)
b.plot([22.0, 30.5], [Z_SEAT + DISP_TAB_T]*2, color=BUY, lw=0.6, ls=(0, (5, 3)), zorder=2)
b.annotate(f'collar tip {TIP:.2f}, the module\'s face {Z_SEAT+DISP_TAB_T:.2f} —\n'
           f'ASSUMING a bare {DISP_TAB_T:.2f} PCB rim, which is the one\n'
           f'number in this drawing nobody has measured.\n'
           f'Too long here holds the face off its crest.',
           (26.0, TIP), (31.0, 5.6), fontsize=7.0, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))
b.annotate(f'bore {R_DISP_BORE:.2f}, measured across the FLATS.\n'
           f'R_DISP_POCKET is {R_DISP_POCKET:.4f} — the circumradius\n'
           f'of a 144-gon; a round collar touches the flats.',
           (R_DISP_BORE, 16.5), (33.0, 14.0), fontsize=7.0, color=INK,
           arrowprops=dict(arrowstyle='->', color=INK, lw=.8))
b.annotate(f'collar turned to {COLLAR_OD:.2f} — {2*(R_DISP_BORE-COLLAR_OD):.2f} mm of\n'
           f'CLEARANCE on diameter, so the wall itself\n'
           f'can never become the fit. {COLLAR_RIB_N} ribs stand to\n'
           f'{R_DISP_BORE+COLLAR_RIB_H:.2f} = {2*COLLAR_RIB_H:.2f} interference.\n'
           f'THE PRESS FIT IS HERE AND NOWHERE ELSE.',
           (COLLAR_OD, 13.0), (32.0, 25.0), fontsize=7.0, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))
b.annotate(f'outer wall: {-2*DIFF_FIT:.2f} of clearance, grips nothing',
           (B.diff_outer, 18.3), (36.0, 9.0), fontsize=7.0, color='#a0522d',
           arrowprops=dict(arrowstyle='->', color='#a0522d', lw=.8))
b.set_title('B — the collar, which is the whole fit', fontsize=10.5)
b.set_xlim(20, 60); b.set_ylim(3, 31)
b.set_xlabel('radius (mm)')

# ---------------------------------------------------- C: the aperture
c = fig.add_subplot(gs[1, 1])
d2 = DIFF.copy()
d2.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0])); d2.apply_translation([0, 0, DIFF_SEAT_Z])
a_tick = math.radians(B.wall_a0 + 0.5 * B.pitch)
sec = d2.section(plane_origin=[0, 0, 0],
                 plane_normal=[-math.sin(a_tick), math.cos(a_tick), 0])
if sec is not None:
    segs = []
    for e in sec.entities:
        p = sec.vertices[e.points]
        rr = np.hypot(p[:, 0], p[:, 1]) * np.sign(p[:, 0]*math.cos(a_tick) +
                                                  p[:, 1]*math.sin(a_tick))
        segs.extend([[[rr[i], p[i][2]], [rr[i+1], p[i+1][2]]] for i in range(len(p)-1)])
    segs = np.array(segs)
    c.add_collection(LineCollection(segs[(segs[:, :, 0] > 0).all(axis=1)],
                                    colors='#a0522d', linewidths=1.3, zorder=3))
c.add_patch(Rectangle((B.ring_id/2, B.ring_floor), (B.ring_od - B.ring_id)/2,
                      PCB_T + LED_H, fc='none', ec=BUY, hatch='////', lw=1.0, zorder=4))
levels(c, B.tick_ri - 6, B.tick_ro + 3, [
    (DIFF_SEAT_Z,              f'{DIFF_SEAT_Z:.2f}  face, outer surface'),
    (DIFF_SEAT_Z - DIFF_MEM_T, f'{DIFF_SEAT_Z-DIFF_MEM_T:.2f}  {DIFF_MEM_T:.2f} membrane — ONE layer'),
    (DIFF_SEAT_Z - FACE_T,     f'{DIFF_SEAT_Z-FACE_T:.2f}  the face is {FACE_T:.2f} everywhere else'),
    (DIFF_SEAT_Z - BAND_TOP,   f'{DIFF_SEAT_Z-BAND_TOP:.2f}  band bottom'),
    (RING_TOP,                 f'{RING_TOP:.2f}  LED tops'),
], gap=0.75)
hdim(c, B.tick_ri, B.tick_ro, DIFF_SEAT_Z + 1.2,
     f'aperture {B.tick_ro-B.tick_ri:.2f} long x {TICK_W:.2f} wide,\n'
     f'flaring {APER_FLARE:.2f} a side behind the membrane', off=0.3)
c.set_title('C — one LED aperture, sectioned along its tick. Only this is thin.',
            fontsize=10.5)
c.set_xlim(B.tick_ri - 7, B.tick_ro + 17); c.set_ylim(RING_TOP - 2, DIFF_SEAT_Z + 4)
c.set_xlabel('radius (mm)')

for ax in (a, b, c):
    ax.set_aspect('equal'); ax.grid(alpha=.15, lw=.4)

fig.suptitle('mini-round-clock — dimensioned sections. Sliced from the BUILT STLs, '
             'annotated from params.py, so the drawing cannot drift from the part.',
             fontsize=12.5)
fig.savefig('sketch_sections.png', dpi=120, bbox_inches='tight')
print('wrote sketch_sections.png')
