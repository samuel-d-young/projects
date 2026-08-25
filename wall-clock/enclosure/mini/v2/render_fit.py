#!/usr/bin/env python3
"""Draw the hardware where it actually lands, over a cross-section of the part.
The one picture that shows whether it fits."""
import sys, math; sys.path.insert(0,'.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, Circle
from params import *

def segs(m, z):
    V,F=m.vertices,m.faces; tri=V[F]; d=tri[:,:,2]-z
    ns=(d>0).sum(axis=1); sel=(ns==1)|(ns==2); tri,d=tri[sel],d[sel]
    o=[]
    for t,dd in zip(tri,d):
        p=[]
        for i in range(3):
            j=(i+1)%3
            if (dd[i]>0)!=(dd[j]>0):
                f=dd[i]/(dd[i]-dd[j]); p.append(t[i]+f*(t[j]-t[i]))
        if len(p)==2: o.append([p[0][:2],p[1][:2]])
    return np.array(o) if o else np.zeros((0,2,2))

B = trimesh.load('mini-round-clock-base.stl'); B.merge_vertices()
H = trimesh.load('mini-round-clock-housing.stl'); H.merge_vertices()
S = trimesh.load('mini-round-clock-battery-shelf-x2.stl'); S.merge_vertices()

fig, ax = plt.subplots(1, 2, figsize=(15, 7.6))

# ---- left: the S3, in the deck window
a = ax[0]
for z, c, lw in [(-1.2,'#8aa5c8',0.9), (-0.4,'#1c3d6e',1.3), (2.0,'#9fb6cd',0.9)]:
    s = segs(B, z)
    if len(s): a.add_collection(LineCollection(s, colors=c, linewidths=lw))
a.add_patch(Rectangle((BOARD_X0, -BOARD_W/2), BOARD_L, BOARD_W,
                      fc='#2f7d4f', ec='#14532d', lw=1.6, alpha=.42))
a.text((BOARD_X0+BOARD_X1)/2, 0, 'ESP32-S3-N16R8\n62.74 x 25.40',
       ha='center', va='center', fontsize=9.5, color='#0d3b22', weight='bold')
a.add_patch(Circle((0,0), R_BORE, fill=False, ec='#c0392b', ls='--', lw=1.0))
a.add_patch(Circle((0,0), R_TAB, fill=False, ec='#c0392b', ls=':', lw=1.0))
a.annotate('rear bore r=27.78', (0,-R_BORE), (-6,-34), fontsize=8, color='#c0392b',
           arrowprops=dict(arrowstyle='-', color='#c0392b', lw=.7))
a.annotate('tab window\nreaches r=42.66', (R_TAB*.72, R_TAB*.72), (26,44), fontsize=8,
           color='#c0392b', arrowprops=dict(arrowstyle='-', color='#c0392b', lw=.7))
a.annotate('wire slot,\n6 o\'clock', (-38, 13), (-52,26), fontsize=8, color='#c0392b',
           arrowprops=dict(arrowstyle='-', color='#c0392b', lw=.7))
a.set_title('The S3 in the deck window — corners at r 27.15 and 40.77', fontsize=11)

# ---- right: the battery and shims in the pocket
b = ax[1]
ZF = Z_DECK - (PLATE_T + POCKET_BATTERY) + PLATE_T
for z, c, lw in [(ZF+2.0,'#1c3d6e',1.3), (ZF+12.0,'#8aa5c8',0.9)]:
    s = segs(H, z)
    if len(s): b.add_collection(LineCollection(s, colors=c, linewidths=lw))
b.add_patch(Rectangle((BAT_CX-BAT_L/2, -BAT_W/2), BAT_L, BAT_W,
                      fc='#b8860b', ec='#7a5a06', lw=1.6, alpha=.40))
b.text(BAT_CX, 0, f'battery\n{BAT_L:.0f} x {BAT_W:.0f} x {BAT_T:.0f}',
       ha='center', va='center', fontsize=9.5, color='#4a3703', weight='bold')
for sy in (1,-1):
    s = segs(S, 4.0)
    if len(s):
        ss = s.copy(); ss[:,:,1] *= sy
        b.add_collection(LineCollection(ss, colors='#a0522d', linewidths=1.4))
b.add_patch(Circle((HANG_R,0), 4.0, fc='#c0392b', ec='#7b1c12', alpha=.55))
b.add_patch(Circle((HANG_R-KEY_DROP,0), 4.5, fill=False, ec='#c0392b', ls='--', lw=1.0))
b.annotate('wall screw head sits HERE once hung\n(pocket offset 7 mm to clear it)',
           (HANG_R, 3.0), (2, -46), fontsize=8, color='#c0392b', ha='center',
           arrowprops=dict(arrowstyle='->', color='#c0392b', lw=.8,
                           connectionstyle='arc3,rad=-0.25'))
b.annotate('shims, print 2', (0,34), (-34,44), fontsize=8, color='#a0522d',
           arrowprops=dict(arrowstyle='-', color='#a0522d', lw=.7))
b.annotate('cable exit', (-52,0), (-50,-30), fontsize=8, color='#1c3d6e',
           arrowprops=dict(arrowstyle='-', color='#1c3d6e', lw=.7))
b.set_title('The battery and shims in the pocket, viewed from the front', fontsize=11)

for a_ in ax:
    a_.set_xlim(-60,60); a_.set_ylim(-58,58); a_.set_aspect('equal')
    a_.grid(alpha=.2, lw=.4); a_.set_xlabel('+x is 12 o\'clock  (mm)')
fig.suptitle("Where the hardware actually lands — 12 o'clock to the right", fontsize=12.5)
fig.tight_layout(); fig.savefig('render_fit.png', dpi=110)
print('wrote render_fit.png')
