#!/usr/bin/env python3
"""Cross-section atlas via raw plane/triangle segments — no shapely assembly needed."""
import numpy as np, trimesh, matplotlib
import csg
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def clean(path):
    m = trimesh.load(csg.part(path), process=False); m.merge_vertices()
    m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    b = parts[0].bounds
    cx, cy = (b[0][0]+b[1][0])/2, (b[0][1]+b[1][1])/2
    out=[]
    for p in parts:
        q=p.copy(); q.apply_translation([-cx,-cy,0]); out.append(q)
    return out

def segs_at_z(m, z):
    """All triangle/plane intersection segments at height z."""
    V, F = m.vertices, m.faces
    tri = V[F]                                   # (n,3,3)
    d = tri[:,:,2] - z
    sign = d > 0
    ns = sign.sum(axis=1)
    sel = (ns == 1) | (ns == 2)
    tri, d = tri[sel], d[sel]
    out = []
    for t, dd in zip(tri, d):
        pts = []
        for i in range(3):
            j = (i+1) % 3
            if (dd[i] > 0) != (dd[j] > 0):
                f = dd[i] / (dd[i] - dd[j])
                pts.append(t[i] + f*(t[j]-t[i]))
        if len(pts) == 2:
            out.append([pts[0][:2], pts[1][:2]])
    return np.array(out) if out else np.zeros((0,2,2))

def atlas(parts, zs, title, fn, lim, annot=None):
    n=len(zs); cols=4; rows=(n+cols-1)//cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.9*cols, 3.9*rows))
    axes=np.atleast_1d(axes).ravel()
    for ax, z in zip(axes, zs):
        ax.set_title(f'z = {z:.2f}', fontsize=10)
        ax.set_xlim(-lim,lim); ax.set_ylim(-lim,lim); ax.set_aspect('equal')
        ax.grid(alpha=.25, lw=.4); ax.axhline(0,lw=.5,c='k',alpha=.35); ax.axvline(0,lw=.5,c='k',alpha=.35)
        for k,p in enumerate(parts):
            s = segs_at_z(p, z)
            if len(s)==0: continue
            from matplotlib.collections import LineCollection
            ax.add_collection(LineCollection(s, colors='#c0392b' if k else '#1c3d6e', linewidths=1.1))
        if annot:
            for (ax0,ay0,txt) in annot: ax.plot([ax0],[ay0],'g+',ms=6)
    for ax in axes[n:]: ax.axis('off')
    fig.suptitle(title, fontsize=13); fig.tight_layout(); fig.savefig(fn, dpi=95); plt.close(fig)
    print('wrote', fn)

base = clean('base_in.stl'); diff = clean('diffuser_in.stl')
atlas(base, [0.3, 2.0, 5.0, 8.0, 8.7, 9.5, 10.4, 11.0, 11.7, 12.5, 15.0, 17.0, 19.5, 21.0, 21.9],
      'BASE (Sam edit) — outlines of material at each depth. z=0 .. 22', 'atlas_base.png', 58)
atlas(diff, [0.3, 0.9, 1.5, 1.9, 2.3, 3.0, 4.5, 5.5, 7.0, 8.1],
      'DIFFUSER (Sam edit) — z=0 .. 8.2', 'atlas_diffuser.png', 50)
