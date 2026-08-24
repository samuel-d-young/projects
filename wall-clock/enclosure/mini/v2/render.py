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
    B = trimesh.load('mini-round-clock-base-v2.stl')
    R = trimesh.load('mini-round-clock-rearhousing-battery.stl')
    C = trimesh.load('mini-round-clock-battery-cradle.stl')
    sheet([
        (B,'front','BASE v2 - FRONT (plywood side), 12 up','bone'),
        (B,'rear', 'BASE v2 - REAR: deck + S3 window','bone'),
        (B,'iso_r','BASE v2 - iso from the rear','bone'),
        (R,'rear', 'REAR HOUSING - wall side, keyhole at 12','summer'),
        (R,'iso_f','REAR HOUSING - inside: battery pocket','summer'),
        (C,'iso_f','BATTERY CRADLE','copper'),
    ], 'render_v2.png')
    sheet([
        (B,'side', 'BASE v2 - side','bone'),
        (R,'side', 'REAR HOUSING - side (vents, cable exit)','summer'),
        (R,'front','REAR HOUSING - looking in from the base side','summer'),
    ], 'render_v2_detail.png')
