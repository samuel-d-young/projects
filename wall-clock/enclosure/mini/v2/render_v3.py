#!/usr/bin/env python3
"""Before and after, for the four changes. Sections, because that is where the
differences live."""
import sys, math; sys.path.insert(0,'.')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
import csg
from params import *
from build_v2 import load_sams_base, load_sams_diffuser

def segs_z(m, z):
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

def segs_plane(m, ax_u):
    """Section by the plane y=0 (ax_u=0) — returns (u, z)."""
    V,F=m.vertices,m.faces; tri=V[F]
    d=tri[:,:,1]
    ns=(d>0).sum(axis=1); sel=(ns==1)|(ns==2); tri,d=tri[sel],d[sel]
    o=[]
    for t,dd in zip(tri,d):
        p=[]
        for i in range(3):
            j=(i+1)%3
            if (dd[i]>0)!=(dd[j]>0):
                f=dd[i]/(dd[i]-dd[j]); p.append(t[i]+f*(t[j]-t[i]))
        if len(p)==2: o.append([[p[0][ax_u],p[0][2]],[p[1][ax_u],p[1][2]]])
    return np.array(o) if o else np.zeros((0,2,2))

OLD_B = csg.to_trimesh(load_sams_base())
NEW_B = trimesh.load('mini-round-clock-base-v2.stl'); NEW_B.merge_vertices()
OLD_D = csg.to_trimesh(load_sams_diffuser())
NEW_D = trimesh.load('mini-round-clock-diffuser-v3.stl'); NEW_D.merge_vertices()

fig = plt.figure(figsize=(16, 10.5))
gs = fig.add_gridspec(2, 2, hspace=0.22, wspace=0.16)

# ---- top row: the tab slot, before and after, at the tab's height
TAB_HW = DISP_TAB_W/2
for k,(m,title) in enumerate([(OLD_B, 'BEFORE — slot cut for a 40 mm tab'),
                              (NEW_B, 'AFTER — cut for the 30.55 mm tab you measured')]):
    ax = fig.add_subplot(gs[0,k])
    s = segs_z(m, 9.4)
    if len(s): ax.add_collection(LineCollection(s, colors='#1c3d6e', linewidths=1.2))
    ax.add_patch(Rectangle((R_DISP_POCKET, -TAB_HW),
                           (DISP_OVERALL-DISP_PCB_D/2)-R_DISP_POCKET, 2*TAB_HW,
                           fc='#2f7d4f', ec='#14532d', lw=1.6, alpha=.45))
    ax.text(34, 0, 'tab\n30.55', ha='center', va='center', fontsize=9,
            color='#0d3b22', weight='bold')
    rot = 25.9 if k==0 else 0.47
    ax.annotate(f'can rotate ±{rot:.2f}°', (30, 20 if k==0 else 17), (2, 40),
                fontsize=10, color='#c0392b', weight='bold',
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.0))
    ax.set_xlim(-10, 52); ax.set_ylim(-34, 46); ax.set_aspect('equal')
    ax.grid(alpha=.2, lw=.4); ax.set_title(title + '   (section at z = 9.4)', fontsize=11)

# ---- bottom row: the diffuser, radial half-section. Vertical scale is
#      exaggerated 3x, or the 0.6 mm that changed is invisible.
for k,(m,title,col) in enumerate([(OLD_D, 'BEFORE — 0.80 mm membrane, 46.000 OD, 8.2 collar', '#8a7638'),
                                  (NEW_D, 'AFTER — 0.20 mm membrane, 46.402 OD, 10.2 collar', '#1c3d6e')]):
    ax = fig.add_subplot(gs[1,k])
    s = segs_plane(m, 0)
    if len(s):
        s = s[s[:,:,0].mean(axis=1) > 0]           # right half only
        ax.add_collection(LineCollection(s, colors=col, linewidths=1.5))
    ax.axvline(R_RING_O, color='#c0392b', ls='--', lw=1.0)
    ax.text(R_RING_O+0.3, 8.6, 'ring pocket\nwall 46.352', fontsize=8, color='#c0392b')
    mem = 0.80 if k == 0 else DIFF_MEM_T
    ax.annotate(f'membrane {mem:.2f}', (42, mem), (36.5, 4.4), fontsize=9.5,
                color='#c0392b', weight='bold',
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.0))
    coll = 8.2 if k == 0 else 8.2 + COLLAR_EXTEND
    ax.annotate(f'collar {coll:.1f}', (29.0, coll), (31.0, coll + 1.4), fontsize=9.5,
                color='#c0392b', weight='bold',
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.0))
    ax.set_xlim(26, 49); ax.set_ylim(-0.6, 12.4)
    ax.set_aspect(1/3.0)                            # 3x vertical exaggeration
    ax.grid(alpha=.25, lw=.4); ax.set_title(title, fontsize=11)
    ax.set_xlabel('radius (mm)  —  section through y = 0, vertical scale x3')

fig.suptitle("v3: the four changes", fontsize=13.5)
fig.savefig('render_v3.png', dpi=105, bbox_inches='tight'); plt.close(fig)
print('wrote render_v3.png')
