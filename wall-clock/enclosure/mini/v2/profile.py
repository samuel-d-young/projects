#!/usr/bin/env python3
"""Vertical sections through the part: the profile view that actually decides fits."""
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def clean(path):
    m = trimesh.load(csg.part(path), process=False); m.merge_vertices()
    m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts=[p for p in m.split(only_watertight=False) if abs(p.volume)>1.0]
    parts.sort(key=lambda p:-abs(p.volume))
    b=parts[0].bounds; cx,cy=(b[0][0]+b[1][0])/2,(b[0][1]+b[1][1])/2
    return [ (lambda q: (q.apply_translation([-cx,-cy,0]), q)[1])(p.copy()) for p in parts ]

def segs_plane(m, origin, normal, ax_u):
    """Segments of mesh cut by a plane; returned as (u, z) pairs."""
    V,F = m.vertices, m.faces
    tri = V[F]
    n = np.array(normal, float); o = np.array(origin, float)
    d = (tri - o) @ n
    ns = (d>0).sum(axis=1)
    sel = (ns==1)|(ns==2)
    tri, d = tri[sel], d[sel]
    out=[]
    for t,dd in zip(tri,d):
        pts=[]
        for i in range(3):
            j=(i+1)%3
            if (dd[i]>0)!=(dd[j]>0):
                f=dd[i]/(dd[i]-dd[j]); pts.append(t[i]+f*(t[j]-t[i]))
        if len(pts)==2:
            out.append([[pts[0][ax_u],pts[0][2]],[pts[1][ax_u],pts[1][2]]])
    return np.array(out) if out else np.zeros((0,2,2))

def draw(parts, cuts, title, fn, xlim, ylim):
    fig, axes = plt.subplots(len(cuts),1, figsize=(15, 4.2*len(cuts)))
    axes=np.atleast_1d(axes)
    for ax,(name,origin,normal,au) in zip(axes,cuts):
        for k,p in enumerate(parts):
            s=segs_plane(p,origin,normal,au)
            if len(s): ax.add_collection(LineCollection(s, colors='#c0392b' if k else '#1c3d6e', linewidths=1.3))
        ax.set_title(name, fontsize=11)
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal')
        ax.grid(alpha=.3,lw=.4); ax.set_xlabel('mm'); ax.set_ylabel('z (mm)')
        ax.set_xticks(np.arange(xlim[0],xlim[1]+1,5), minor=True)
        ax.set_yticks(np.arange(0,ylim[1]+1,1), minor=True)
        ax.grid(which='minor', alpha=.12, lw=.3)
    fig.suptitle(title, fontsize=13); fig.tight_layout(); fig.savefig(fn,dpi=100); plt.close(fig)
    print('wrote',fn)

base=clean('base_in.stl'); diff=clean('diffuser_in.stl')
draw(base, [('BASE — cut by the y=0 plane (looking along +y).  -x is the wire-channel side, +x is the tab side',[0,0,0],[0,1,0],0),
            ('BASE — cut by the x=0 plane (looking along +x)',[0,0,0],[1,0,0],1)],
     'BASE vertical sections', 'profile_base.png', (-58,58), (-1,24))
draw(diff, [('DIFFUSER — cut by the y=0 plane',[0,0,0],[0,1,0],0),
            ('DIFFUSER — cut by the x=0 plane',[0,0,0],[1,0,0],1)],
     'DIFFUSER vertical sections', 'profile_diffuser.png', (-50,50), (-1,10))
