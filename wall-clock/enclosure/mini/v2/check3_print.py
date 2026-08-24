#!/usr/bin/env python3
"""PASS 3 of 3 — printability.

Two different things get confused under the word "overhang", so they are
measured separately here:
  * a FLAT ceiling is a bridge. It is fine if the span is short.
  * a SLOPED downward face cannot be bridged. It is fine if it is steep enough.
"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, trimesh
from scipy.cluster.hierarchy import fcluster, linkage
import csg
from params import *

FAIL=[]
def ck(cond, msg, detail=''):
    print(f'  [{"ok  " if cond else "FAIL"}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

LAYER, NOZZLE = 0.20, 0.40
SLOPE_MIN   = 45.0     # a sloped face flatter than this wants support
MAX_BRIDGE  = 25.0     # a flat ceiling wider than this wants support
MIN_WALL    = 1.20     # three perimeters at 0.4 mm

# Sam's base already carries this much shallow sloped overhang: the lead-in ramp
# at the top of the display-tab slot, 33-40 deg from horizontal. Measured off
# the uploaded file, not assumed. It is his geometry and it is unchanged.
INHERITED = {'mini-round-clock-base-v2.stl': 409.1}

# Sam's base also feathers out to nothing where the tab-slot ramp runs into the
# ring-pocket floor and the display-pocket wall. Rather than hand-draw boxes
# around those and risk widening them until the test passes, the baseline is
# recomputed from the uploaded file at run time and compared cluster to
# cluster. A slicer will not lay a bead below one extrusion width, so a feather
# edge is a non-event -- but it must be HIS feather edge, not one I added.
BASELINE = {'mini-round-clock-base-v2.stl': 'sam-base',
            'mini-round-clock-diffuser-v3.stl': 'sam-diffuser'}

def overlaps(a, b, pad=0.6):
    """Do two thin regions occupy the same (r, z) band?"""
    return not (a['r'][0] > b['r'][1] + pad or a['r'][1] < b['r'][0] - pad or
                a['z'][0] > b['z'][1] + pad or a['z'][1] < b['z'][0] - pad)

# baselines: the thin regions already present in the files Sam uploaded
from build_v2 import load_sams_base, load_sams_diffuser
_sam = csg.to_trimesh(load_sams_base()); _sam.merge_vertices()
_samd = csg.to_trimesh(load_sams_diffuser()); _samd.merge_vertices()

# (file, orientation, min wall). The diffuser's minimum wall is deliberately
# 0.20 -- that is the whole point of it -- so it is held to that, not to 1.20,
# and its membrane and cell walls are measured explicitly in check4 instead.
PARTS = [
    ('mini-round-clock-base-v2.stl',             'deck face down',  MIN_WALL),
    ('mini-round-clock-rearhousing-slim.stl',    'rear plate down', MIN_WALL),
    ('mini-round-clock-rearhousing-battery.stl', 'rear plate down', MIN_WALL),
    ('mini-round-clock-battery-shim-x2.stl',     'flat',            MIN_WALL),
    ('mini-round-clock-board-keeper.stl',        'plate down',      MIN_WALL),
    ('mini-round-clock-diffuser-v3.stl',         'membrane face down', 0.18),
]

def bridge_span(m, face_idx):
    """How far the nozzle is actually unsupported over a flat ceiling.

    The bounding box of a patch is the wrong measure. A 0.1 mm wide ring 78 mm
    across has a 78 mm bounding box and is not a bridge at all -- the nozzle is
    never more than 0.05 mm from solid. So: find the patch's own boundary edges
    (used once within the patch), then take twice the greatest distance from any
    point on the patch to the nearest of them.
    """
    tri = m.triangles[face_idx][:, :, :2]
    e = []
    for k in range(3):
        a = m.faces[face_idx][:, k]; b = m.faces[face_idx][:, (k+1) % 3]
        e.append(np.sort(np.stack([a, b], axis=1), axis=1))
    e = np.concatenate(e)
    uniq, cnt = np.unique(e, axis=0, return_counts=True)
    bnd = uniq[cnt == 1]
    if len(bnd) == 0: return np.inf, None
    P, Q = m.vertices[bnd[:,0]][:, :2], m.vertices[bnd[:,1]][:, :2]
    # sample the patch: triangle vertices plus centroids is enough resolution
    S = np.concatenate([tri.reshape(-1,2), tri.mean(axis=1)])
    if len(S) > 4000: S = S[::max(1, len(S)//4000)]
    d = Q - P
    L2 = np.einsum('ij,ij->i', d, d)
    L2[L2 == 0] = 1e-12
    best = np.full(len(S), np.inf)
    for i in range(0, len(S), 512):
        s = S[i:i+512]
        t = np.clip(np.einsum('sij,ij->si', s[:,None,:] - P[None,:,:], d) / L2, 0, 1)
        proj = P[None,:,:] + t[:,:,None] * d[None,:,:]
        best[i:i+512] = np.linalg.norm(s[:,None,:] - proj, axis=2).min(axis=1)
    k = int(np.argmax(best))
    return 2.0 * best[k], tuple(np.round(S[k], 1))


def thin_clusters(m, thr=MIN_WALL, n=12000, seed=0, min_pts=5):
    """Find REGIONS thinner than thr, not individual samples.

    Shooting a ray inward from a point near a feature edge exits almost at once
    and reads as a near-zero wall; on this geometry that produced 4 false hits
    in 12000. A genuine thin wall shows up as a cluster, so single hits are
    dropped and only clusters are reported.
    """
    pts, fid = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fid]
    org = pts - nrm*1e-4
    loc, ri, _ = m.ray.intersects_location(org, -nrm, multiple_hits=True)
    if len(ri) == 0: return [], np.inf
    best = {}
    d = np.linalg.norm(loc - org[ri], axis=1)
    for i, dist in zip(ri, d):
        if dist > 1e-3 and dist < best.get(i, 1e9): best[i] = dist
    allv = np.array(list(best.values()))
    idx = np.array([i for i, v in best.items() if v < thr], dtype=int)
    if len(idx) < min_pts:
        return [], np.percentile(allv, 1.0)
    p = pts[idx]; v = np.array([best[i] for i in idx])
    lab = fcluster(linkage(p, 'single'), t=4.0, criterion='distance')
    out = []
    for L in np.unique(lab):
        q, w = p[lab == L], v[lab == L]
        if len(q) < min_pts: continue
        r = np.hypot(q[:,0], q[:,1])
        out.append(dict(n=len(q), tmin=w.min(), tmax=w.max(),
                        r=(r.min(), r.max()), z=(q[:,2].min(), q[:,2].max())))
    return out, np.percentile(allv, 1.0)

BASE_THIN, _ = thin_clusters(_sam)
DIFF_THIN, _ = thin_clusters(_samd, thr=0.18)
SAM_THIN = {'sam-base': BASE_THIN, 'sam-diffuser': DIFF_THIN}
for k, v in SAM_THIN.items():
    print(f"\nbaseline: Sam's uploaded {k.split('-')[1]} has {len(v)} thin region(s)")
    for s_ in v:
        print(f"   {s_['n']:3d} pts, {s_['tmin']:.2f}-{s_['tmax']:.2f} mm, "
              f"r {s_['r'][0]:.1f}-{s_['r'][1]:.1f}, z {s_['z'][0]:.1f}-{s_['z'][1]:.1f}")

for fn, orient, min_wall in PARTS:
    m = trimesh.load(fn, process=False); m.merge_vertices()
    zmin = m.bounds[0][2]
    print(f'\n{fn}   ({orient})')
    print(f'         {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm, '
          f'{m.volume/1000:.1f} cm3 (~{m.volume*1.24/1000:.0f} g PLA)')

    n, ar = m.face_normals, m.area_faces
    zc = m.triangles[:,:,2].mean(axis=1)
    above = zc > zmin + 2*LAYER

    # --- first layer ---------------------------------------------------------
    first = (n[:,2] < -0.999) & (np.abs(zc - zmin) < 1e-3)
    # 400 mm2 absolute, OR 40% of the part's own footprint -- a 1 g keeper is
    # well seated on 206 mm2 and would fail a flat threshold written for a
    # 108 mm disc. Both mean the same thing: it will not come off the plate.
    foot, bbox = ar[first].sum(), m.extents[0] * m.extents[1]
    ck(foot > 400.0 or foot > 0.40 * bbox, 'first layer has a generous footprint',
       f'{foot:.0f} mm2 ({100*foot/bbox:.0f}% of its own footprint)')

    # --- sloped overhangs: cannot be bridged, judged by angle ----------------
    slope = above & (n[:,2] < -1e-6) & (n[:,2] > -0.999) \
            & (n[:,2] < -math.sin(math.radians(SLOPE_MIN)))
    a_slope = ar[slope].sum()
    inh = INHERITED.get(fn, 0.0)
    ck(a_slope - inh < 5.0, f'introduces no sloped face flatter than {SLOPE_MIN:.0f} deg',
       f'{a_slope:.1f} mm2 total, {inh:.1f} inherited from Sam, {a_slope-inh:.1f} new')
    if a_slope > 0:
        ang = np.degrees(np.arccos(np.clip(-n[slope][:,2], 0, 1)))
        print(f'         (those slopes run {ang.min():.1f} to {ang.max():.1f} deg from horizontal, '
              f'z {zc[slope].min():.1f} to {zc[slope].max():.1f})')

    # --- flat ceilings: bridges, judged by how far the extruder is unsupported
    ceil = above & (n[:,2] < -0.999)
    worst, worst_at = 0.0, None
    if ceil.any():
        for z in np.unique(np.round(zc[ceil], 2)):
            sel = np.nonzero(ceil & (np.abs(zc - z) < 1e-2))[0]
            if len(sel) < 1: continue
            w, at = bridge_span(m, sel)
            if w > worst: worst, worst_at = w, (z, at)
    ck(worst <= MAX_BRIDGE, f'every flat ceiling bridges <= {MAX_BRIDGE:.0f} mm',
       f'worst {worst:.1f} mm' + (f' at z={worst_at[0]:.1f}' if worst_at else ''))
    ck(ar[ceil].sum() < 2000, 'total ceiling area is modest', f'{ar[ceil].sum():.0f} mm2')

    # --- wall thickness ------------------------------------------------------
    cl, p1 = thin_clusters(m, thr=min_wall)
    allowed = SAM_THIN.get(BASELINE.get(fn, ''), [])
    unexplained = []
    for c_ in cl:
        ok = any(overlaps(c_, a) for a in allowed)
        if not ok: unexplained.append(c_)
        print(f"         thin region: {c_['n']:3d} pts, {c_['tmin']:.2f}-{c_['tmax']:.2f} mm, "
              f"r {c_['r'][0]:.1f}-{c_['r'][1]:.1f}, z {c_['z'][0]:.1f}-{c_['z'][1]:.1f}"
              f"{'   [same place in Sam''s file]' if ok else '   << NEW'}")
    ck(not unexplained, f'no NEW region thinner than {min_wall} mm',
       f'1st percentile {p1:.2f} mm, {len(cl)} thin region(s), {len(unexplained)} new')

print()
if FAIL:
    print(f'PASS 3: {len(FAIL)} FAILURES'); [print('   -',f) for f in FAIL]; sys.exit(1)
print('PASS 3: prints without support in the stated orientation')
