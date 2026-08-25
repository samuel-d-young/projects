#!/usr/bin/env python3
"""Z-buffered orthographic renderer with explicit camera + up vector.

The clock's +x axis is 12 o'clock, so every view is rolled to put +x at the top
of the image -- otherwise it is impossible to tell top from side at a glance.
"""
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def basis(eye, up_hint):
    """eye = direction FROM the scene TOWARDS the camera."""
    f = np.array(eye, float); f /= np.linalg.norm(f)
    u = np.array(up_hint, float)
    u = u - f*(u@f)
    if np.linalg.norm(u) < 1e-6:
        u = np.array([0.,0.,1.]) - f*(f[2])
    u /= np.linalg.norm(u)
    r = np.cross(u, f)
    return r, u, f

def render(m, eye, up_hint, px=680, light=(-0.30,0.45,0.84), pad=1.04):
    r, u, f = basis(eye, up_hint)
    V = m.vertices - m.bounds.mean(axis=0)
    U, W, D = V@r, V@u, V@f                 # D larger = nearer the camera
    lim = max(np.abs(U).max(), np.abs(W).max())*pad
    sx = (U + lim)/(2*lim)*(px-1)
    sy = (lim - W)/(2*lim)*(px-1)
    zb = np.full((px,px), -np.inf); nb = np.zeros((px,px,3))
    F = m.faces; N = m.face_normals
    A, B, C = F[:,0], F[:,1], F[:,2]
    area = (sx[B]-sx[A])*(sy[C]-sy[A]) - (sy[B]-sy[A])*(sx[C]-sx[A])
    for i in np.nonzero(np.abs(area) > 1e-9)[0]:
        a,b,c = A[i],B[i],C[i]
        x0 = max(int(min(sx[a],sx[b],sx[c])), 0); x1 = min(int(max(sx[a],sx[b],sx[c]))+1, px-1)
        y0 = max(int(min(sy[a],sy[b],sy[c])), 0); y1 = min(int(max(sy[a],sy[b],sy[c]))+1, px-1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0,x1+1), np.arange(y0,y1+1))
        d = area[i]
        l0 = ((sx[b]-gx)*(sy[c]-gy) - (sy[b]-gy)*(sx[c]-gx))/d
        l1 = ((sx[c]-gx)*(sy[a]-gy) - (sy[c]-gy)*(sx[a]-gx))/d
        l2 = 1.0 - l0 - l1
        ins = (l0>=-1e-9)&(l1>=-1e-9)&(l2>=-1e-9)
        if not ins.any(): continue
        z = l0*D[a] + l1*D[b] + l2*D[c]
        sub = zb[y0:y1+1, x0:x1+1]
        bt = ins & (z > sub)
        if not bt.any(): continue
        sub[bt] = z[bt]
        nb[y0:y1+1, x0:x1+1][bt] = N[i]
    hit = np.isfinite(zb)
    n = nb.copy()
    n[(n@f) < 0] *= -1                       # show the camera-facing side
    L = np.array(light, float); L /= np.linalg.norm(L)
    lam = np.clip(n@L, 0, 1)
    img = np.full((px,px), np.nan)
    img[hit] = 0.30 + 0.70*lam[hit]
    # depth-discontinuity outline: makes pockets and steps legible
    z = np.where(hit, zb, np.nan)
    gy_, gx_ = np.gradient(np.nan_to_num(z, nan=np.nanmin(z) if hit.any() else 0))
    edge = np.hypot(gx_, gy_)
    thr = np.nanpercentile(edge[hit], 99.0) if hit.any() else 1
    img[hit & (edge > thr)] *= 0.42
    return img, hit

VIEWS = {
    'front':  ([0,0, 1], [1,0,0]),
    'rear':   ([0,0,-1], [1,0,0]),
    'iso_r':  ([-0.55,-0.62,-0.56], [1,0,0]),
    'iso_f':  ([-0.55,-0.62, 0.56], [1,0,0]),
    'side':   ([0,-1,0.02], [1,0,0]),
}

def sheet(specs, fn, cols=3, px=680):
    rows = (len(specs)+cols-1)//cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.7*cols, 5.0*rows))
    axes = np.atleast_1d(axes).ravel()
    for ax,(m, vname, title, cmap) in zip(axes, specs):
        eye, up = VIEWS[vname]
        img, hit = render(m, eye, up, px=px)
        rgb = plt.get_cmap(cmap)(np.nan_to_num(img))[...,:3]
        rgb[~hit] = 0.96
        ax.imshow(rgb); ax.axis('off'); ax.set_title(title, fontsize=10)
    for ax in axes[len(specs):]: ax.axis('off')
    fig.patch.set_facecolor('#f7f7f5'); fig.tight_layout(); fig.savefig(fn, dpi=100); plt.close(fig)
    print('wrote', fn)

if __name__ == '__main__':
    B  = trimesh.load('mini-round-clock-base.stl')
    H  = trimesh.load('mini-round-clock-housing.stl')
    D  = trimesh.load('mini-round-clock-diffuser.stl')
    S  = trimesh.load('mini-round-clock-deskstand.stl')
    C  = trimesh.load('mini-round-clock-battery-shelf-x2.stl')
    B2 = trimesh.load('mini-round-clock-base-32.stl')
    H2 = trimesh.load('mini-round-clock-housing-32.stl')
    D2 = trimesh.load('mini-round-clock-diffuser-32.stl')
    S2 = trimesh.load('mini-round-clock-deskstand-32.stl')
    sheet([
        (B,'front','BASE - FRONT (plywood side), 12 up','bone'),
        (B,'rear', 'BASE - REAR: annular deck, cable openings','bone'),
        (H,'iso_f','HOUSING - inside: S3 bay + battery pocket','summer'),
        (H,'rear', 'HOUSING - wall side, keyhole at 12','summer'),
        (D,'front','DIFFUSER - radial ticks + the hours','bone'),
        (S,'iso_f','DESK STAND','copper'),
    ], 'render_v6_24.png')
    sheet([
        (B2,'front','BASE 32 - FRONT, 119.85 mm','bone'),
        (B2,'rear', 'BASE 32 - REAR','bone'),
        (H2,'iso_f','HOUSING 32 - inside','summer'),
        (D2,'front','DIFFUSER 32 - 32 ticks','bone'),
        (S2,'iso_f','DESK STAND 32','copper'),
        (C,'iso_f','BATTERY SHELF (print two)','copper'),
    ], 'render_v6_32.png')
    B6 = trimesh.load('mini-round-clock-base-60.stl')
    H6 = trimesh.load('mini-round-clock-housing-60.stl')
    D6 = trimesh.load('mini-round-clock-diffuser-60.stl')
    G6 = trimesh.load('mini-round-clock-light-guides-60.stl')
    S6 = trimesh.load('mini-round-clock-deskstand-60.stl')
    sheet([
        (B6,'front','BASE 60 - FRONT, 240 mm','bone'),
        (B6,'rear', 'BASE 60 - REAR: ribbed and hollow','bone'),
        (B6,'iso_f','BASE 60 - inside: ring pocket + guide shelf','bone'),
        (D6,'front','DIFFUSER 60 - 60 tapered apertures','bone'),
        (G6,'iso_f','LIGHT GUIDES - print in clear PETG, or cut 60 in perspex','copper'),
        (S6,'iso_f','DESK STAND 60 - a very big print','copper'),
    ], 'render_v7_60.png')
    sheet([
        (H,'side', 'HOUSING - side (vents, USB window at 6)','summer'),
        (S,'side', 'DESK STAND - side, 8 deg back','copper'),
        (B,'side', 'BASE - side','bone'),
    ], 'render_v6_detail.png')
