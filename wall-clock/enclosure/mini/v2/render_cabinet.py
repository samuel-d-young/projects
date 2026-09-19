#!/usr/bin/env python3
"""Colour pictures of the cabinet, clock in it: the look, not the proof.

    python cabinet.py && python render_cabinet.py [--only -32]

A perspective z-buffer rasteriser with per-part materials: black PETG for the
printed parts, procedural oak for the plywood, white PLA for the diffuser, and
shape-round.png from the firmware preview mapped onto the screen. The meshes
are the files cabinet.py and build_v2.py wrote -- nothing is re-modelled here.
"""
import os, sys, math, argparse
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csg
from params import *  # noqa: F403
from cabinet import Frame, world_dir, HERE, CLOCK_Z_FRONT, side_instances

SCREEN_PNG = os.path.join(HERE, '..', '..', '..', 'esphome', 'preview', 'shape-round.png')

MAT = {  # base rgb, ambient, diffuse, specular, shininess
    'black':    ((0.085, 0.087, 0.092), 0.55, 0.75, 0.30, 40),
    'wood':     ((0.80, 0.66, 0.50),    0.45, 0.60, 0.05, 10),
    'diffuser': ((0.93, 0.93, 0.91),    0.55, 0.45, 0.04, 10),
    'screen':   ((0.02, 0.02, 0.03),    1.00, 0.00, 0.00, 1),
    'clock':    ((0.10, 0.10, 0.11),    0.55, 0.75, 0.25, 30),
}


def load_world(fn):
    m = trimesh.load(os.path.join(world_dir(), fn), process=False)
    m.merge_vertices()
    return m


def clock_parts(F):
    """The real clock parts, placed where the cabinet puts them."""
    # the CLOCK does not change with the cabinet's depth, so these are named by
    # the body, not by the cabinet variant
    tg = F.body_tag
    M = F.clock_matrix()
    out = []
    def put(fn, pre=None):
        m = trimesh.load(csg.part(fn), process=False); m.merge_vertices()
        if pre is not None:
            m.apply_transform(pre)
        m.apply_transform(M)
        return m
    seat = np.diag([1.0, -1.0, -1.0, 1.0]); seat[2, 3] = DIFF_SEAT_Z
    out.append((put(f'mini-round-clock-base{tg}.stl'), 'clock'))
    out.append((put(f'mini-round-clock-backcover{tg}.stl'), 'clock'))
    out.append((put(f'mini-round-clock-diffuser{tg}-flange-plain.stl', seat), 'diffuser'))
    disc = trimesh.creation.cylinder(radius=DIFF_BORE_RI + 0.5, height=0.4, sections=96)
    disc.apply_translation([0, 0, 14.0])
    disc.apply_transform(M)
    out.append((disc, 'screen'))
    return out


def scene(F, drawer_out=0.0, explode=0.0, side_out=0.0):
    tg = F.tag
    pre = f'mini-round-clock-cabinet{tg}'
    parts = []
    def add(fn, mat, dy=0.0, mirror_x=False):
        m = load_world(fn)
        if mirror_x:
            m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0])); m.invert()
        m.apply_translation([0, dy, 0]); parts.append((m, mat))
    add(pre + '-sleeve.stl', 'black')
    add(pre + '-hatch.stl', 'black', explode * 1.6)
    add(pre + '-face-ply.stl', 'wood', -explode * 0.8)
    for fn, mat in (('-drawer.stl', 'black'), ('-pull.stl', 'black'), ('-drawer-ply.stl', 'wood')):
        add(pre + fn, mat, -drawer_out - explode * 0.8)
    if F.sides:
        # the right side's top drawer is the one pulled out in the pictures
        for inst in side_instances(F):
            out = side_out if (inst['side'] == 'r' and inst['top']) else 0.0
            dy = -out - explode * 0.8
            add(pre + inst['drawer'] + '.stl', 'black', dy)
            add(pre + inst['ply'] + '.stl', 'wood', dy)
            add(pre + inst['pull'] + '.stl', 'black', dy)
    for m, mat in clock_parts(F):
        m.apply_translation([0, explode * 1.0, 0]); parts.append((m, mat))
    return parts


# ------------------------------------------------------------------ raster
def render(parts, F, eye, target, px=(1100, 900), fov=26.0, section_x=None):
    W, H = px
    eye, target = np.array(eye, float), np.array(target, float)
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    foc = 0.5 * H / math.tan(math.radians(fov / 2))
    zb = np.full((H, W), np.inf)
    col = np.zeros((H, W, 3)); nrm = np.zeros((H, W, 3)); pos = np.zeros((H, W, 3))
    mid = np.full((H, W), -1, int)
    mats = []
    for pi, (m, mat) in enumerate(parts):
        mats.append(mat)
        if section_x is not None:
            try:
                m = m.slice_plane([section_x, 0, 0], [-1, 0, 0], cap=True)
            except Exception:
                m = m.slice_plane([section_x, 0, 0], [-1, 0, 0])
            if m is None or len(m.faces) == 0:
                continue
        V = m.vertices - eye
        cx, cy, cz = V @ r, V @ u, V @ f
        sx = W / 2 + foc * cx / cz
        sy = H / 2 - foc * cy / cz
        Fc = m.faces; N = m.face_normals
        for i in range(len(Fc)):
            a, b, c = Fc[i]
            x0 = max(int(min(sx[a], sx[b], sx[c])), 0); x1 = min(int(max(sx[a], sx[b], sx[c])) + 1, W - 1)
            y0 = max(int(min(sy[a], sy[b], sy[c])), 0); y1 = min(int(max(sy[a], sy[b], sy[c])) + 1, H - 1)
            if x1 < x0 or y1 < y0:
                continue
            d = (sx[b] - sx[a]) * (sy[c] - sy[a]) - (sy[b] - sy[a]) * (sx[c] - sx[a])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l0 = ((sx[b] - gx) * (sy[c] - gy) - (sy[b] - gy) * (sx[c] - gx)) / d
            l1 = ((sx[c] - gx) * (sy[a] - gy) - (sy[c] - gy) * (sx[a] - gx)) / d
            l2 = 1 - l0 - l1
            ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not ins.any():
                continue
            # perspective-correct depth and position
            w0, w1, w2 = l0 / cz[a], l1 / cz[b], l2 / cz[c]
            ws = w0 + w1 + w2
            z = 1.0 / ws
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            hit = ins & (z < sub)
            if not hit.any():
                continue
            sub[hit] = z[hit]
            P = (w0[..., None] * m.vertices[a] + w1[..., None] * m.vertices[b]
                 + w2[..., None] * m.vertices[c]) / ws[..., None]
            pos[y0:y1 + 1, x0:x1 + 1][hit] = P[hit]
            nrm[y0:y1 + 1, x0:x1 + 1][hit] = N[i]
            mid[y0:y1 + 1, x0:x1 + 1][hit] = pi
    return shade(zb, nrm, pos, mid, mats, eye, F, section_x is not None)


def oak(p):
    x, z = p[..., 0], p[..., 2]
    warp = 2.2 * np.sin(x * 0.021 + 1.3) + 0.9 * np.sin(x * 0.067 + z * 0.05)
    t = (z + warp) * 1.35
    ring = 0.5 + 0.5 * np.sin(t + 0.6 * np.sin(t * 0.37))
    fine = 0.5 + 0.5 * np.sin((z + 0.4 * warp) * 7.3 + np.sin(x * 0.9) * 0.4)
    k = 0.72 * ring ** 3 + 0.28 * fine
    lo, hi = np.array([0.86, 0.73, 0.57]), np.array([0.70, 0.55, 0.40])
    return lo * (1 - k[..., None]) + hi * k[..., None]


def shade(zb, nrm, pos, mid, mats, eye, F, section=False):
    H, W = zb.shape
    img = np.ones((H, W, 3)) * np.array([0.955, 0.950, 0.940])
    # soft floor fade
    yy = np.linspace(0, 1, H)[:, None]
    img = img * (1.0 - 0.06 * yy[..., None])
    hit = np.isfinite(zb)
    L = [(np.array([-0.45, -0.75, 0.55]), 0.85), (np.array([0.7, -0.2, 0.4]), 0.35)]
    V = eye[None, None, :] - pos
    V /= np.linalg.norm(V, axis=2, keepdims=True) + 1e-9
    n = nrm.copy()
    flip = (n * V).sum(axis=2) < 0
    n[flip] *= -1
    Minv = np.linalg.inv(F.clock_matrix())
    screen = plt.imread(SCREEN_PNG)[..., :3] if os.path.exists(SCREEN_PNG) else None
    for pi, mat in enumerate(mats):
        sel = hit & (mid == pi)
        if not sel.any():
            continue
        base, amb, dif, spc, shin = MAT[mat]
        if section and mat in ('black', 'clock'):
            base = (0.42, 0.43, 0.45) if mat == 'black' else (0.25, 0.25, 0.27)
        P = pos[sel]
        c = np.tile(np.array(base), (len(P), 1))
        if mat == 'wood':
            c = oak(P)
        loc = (Minv[:3, :3] @ P.T).T + Minv[:3, 3]
        if mat == 'screen' and screen is not None:
            rr = DIFF_BORE_RI
            col_ = ((-loc[:, 1] / rr + 1) / 2 * (screen.shape[1] - 1)).clip(0, screen.shape[1] - 1).astype(int)
            row_ = ((1 - loc[:, 0] / rr) / 2 * (screen.shape[0] - 1)).clip(0, screen.shape[0] - 1).astype(int)
            c = screen[row_, col_] * 1.0
            # the star row came out of the firmware on 2026-09-17
            c[(row_ > 232) & (row_ < 266)] = screen[5, 180]
        nn = n[sel]
        out = c * amb * 0.55
        for Ld, Li in L:
            Ld = Ld / np.linalg.norm(Ld)
            lam = np.clip(nn @ Ld, 0, 1)
            h = Ld[None, :] + V[sel]; h /= np.linalg.norm(h, axis=1, keepdims=True)
            spec = np.clip((nn * h).sum(1), 0, 1) ** shin
            out += Li * (c * dif * lam[:, None] + spc * spec[:, None])
        if mat == 'diffuser':
            # the ring at 6:45: hour hand orange, minute hand blue, dim markers
            ring_od, ring_id = (RING_OD, RING_ID) if F.n == 24 else (RING32_OD, RING32_ID)
            led_r = (ring_od + ring_id) / 4
            rad = np.hypot(loc[:, 0], loc[:, 1])
            ang = np.degrees(np.arctan2(-loc[:, 1], loc[:, 0])) % 360
            pitch = 360.0 / F.n
            def glow(a_deg, rgb, k):
                da = np.abs((ang - a_deg + 180) % 360 - 180) * np.pi / 180 * led_r
                d = np.hypot(da, rad - led_r)
                return np.exp(-(d / 3.2) ** 2)[:, None] * np.array(rgb) * k
            hour = round((6.75 / 12 * 360) / pitch) * pitch
            minute = round((45 / 60 * 360) / pitch) * pitch
            out = out + glow(hour, (1.0, 0.55, 0.15), 0.9) + glow(minute, (0.25, 0.45, 1.0), 0.9)
            for q in range(12):
                out = out + glow(q * 30, (0.55, 0.6, 0.75), 0.18)
        if mat == 'screen':
            out = c
        img[sel] = np.clip(out, 0, 1)
    # outline on depth steps
    z = np.where(hit, zb, np.nan)
    zf = np.nan_to_num(z, nan=np.nanmax(z) * 1.5)
    gy, gx = np.gradient(zf)
    edge = np.hypot(gx, gy) / zf
    img[(edge > 0.012) & hit] *= 0.55
    return img


def views(F, only=None):
    cx, cz = 0.0, F.H * 0.45
    tgt = np.array([cx, F.D * 0.45, cz])
    dist = 3.3 * max(F.H, F.W)
    def at(az, el, d=dist, t=tgt):
        a, e = math.radians(az), math.radians(el)
        return t + d * np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    out = []
    out.append(('hero', 'drawers open, three-quarter',
                scene(F, drawer_out=0.45 * F.D, side_out=0.30 * F.D),
                at(-32, 18), tgt + [0, -25, -8], None))
    out.append(('front', 'front', scene(F), at(0, 4, dist * 1.1), tgt, None))
    out.append(('exploded', 'exploded: the back is closed but for the hatch, which is the way in',
                scene(F, drawer_out=0.3 * F.D, explode=60.0, side_out=0.2 * F.D),
                at(145, 24, dist * 1.25),
                tgt + [0, 30, 0], None))
    out.append(('section', 'section on the centreline', scene(F), at(90, 6, dist * 1.05),
                tgt, 0.0))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--px', type=int, default=900)
    ap.add_argument('--depth', type=float, default=None,
                    help='render a depth variant, e.g. 70 or 150')
    args = ap.parse_args()
    # a depth variant is the same body under another name; 70 only exists with
    # the board on edge, which is what gets it under the 119.30 the flat one needs
    flat = None if args.depth is None else args.depth >= CAB_DEPTH
    for tag in ('', '-32'):
        if args.only is not None and tag != args.only:
            continue
        F = Frame(tag, args.depth, flat)
        vs = views(F)
        fig, axes = plt.subplots(2, 2, figsize=(15, 12.5))
        for ax, (key, title, parts, eye, tgt, sec) in zip(axes.ravel(), vs):
            img = render(parts, F, eye, tgt, px=(int(args.px * 1.2), args.px), section_x=sec)
            ax.imshow(img); ax.axis('off'); ax.set_title(title, fontsize=12)
            if key == 'hero':
                plt.imsave(os.path.join(HERE, 'cabinet', f'render_cabinet{F.tag}_hero.png'), img)
        fig.suptitle(f'mini-round-clock cabinet{F.tag}  --  {F.n}-LED clock, sleeve '
                     f'{F.W:.0f} x {F.H:.0f} x {F.D:.0f} mm', fontsize=14)
        fig.patch.set_facecolor('#f4f3f0'); fig.tight_layout()
        out = os.path.join(HERE, 'cabinet', f'render_cabinet{F.tag}.png')
        fig.savefig(out, dpi=90)
        print('wrote', os.path.relpath(out, HERE))
