#!/usr/bin/env python3
"""PASS 3 of 3 — printability.

Two different things get confused under the word "overhang", so they are
measured separately here:
  * a FLAT ceiling is a bridge. It is fine if the span is short.
  * a SLOPED downward face cannot be bridged. It is fine if it is steep enough.
"""
import sys, os, math; sys.path.insert(0,'.')
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
INHERITED = {'mini-round-clock-base.stl': 409.1,
             'mini-round-clock-base-32.stl': 409.1,
             'mini-round-clock-base-60.stl': 409.1}

# Sam's base also feathers out to nothing where the tab-slot ramp runs into the
# ring-pocket floor and the display-pocket wall. Rather than hand-draw boxes
# around those and risk widening them until the test passes, the baseline is
# recomputed from the uploaded file at run time and compared cluster to
# cluster. A slicer will not lay a bead below one extrusion width, so a feather
# edge is a non-event -- but it must be HIS feather edge, not one I added.
BASELINE = {'mini-round-clock-base.stl': 'sam-base',
            'mini-round-clock-base-32.stl': 'sam-base',
            'mini-round-clock-diffuser.stl': 'sam-diffuser',
            'mini-round-clock-base-60.stl': 'sam-base',
            'mini-round-clock-diffuser-32.stl': 'sam-diffuser',
            'mini-round-clock-diffuser-60.stl': 'sam-diffuser'}

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
    ('mini-round-clock-base.stl',                'deck face down',  MIN_WALL),
    ('mini-round-clock-housing.stl',             'rear plate down', MIN_WALL),
    ('mini-round-clock-deskstand.stl',           'flat on the desk face', MIN_WALL),
    ('mini-round-clock-base-32.stl',             'deck face down',  MIN_WALL),
    ('mini-round-clock-housing-32.stl',          'rear plate down', MIN_WALL),
    ('mini-round-clock-deskstand-32.stl',        'flat on the desk face', MIN_WALL),
    ('mini-round-clock-base-60.stl',             'deck face down',  MIN_WALL),
    ('mini-round-clock-housing-60.stl',          'rear plate down', MIN_WALL),
    ('mini-round-clock-deskstand-60.stl',        'flat on the desk face', MIN_WALL),
    ('mini-round-clock-light-guides-60.stl',     'flat',            MIN_WALL),
    ('mini-round-clock-battery-shelf-x2.stl',    'flat',            MIN_WALL),
    ('mini-round-clock-board-gauge.stl',         'plate down',      MIN_WALL),
    # 0.45, not 1.20: these are 0.50 mm inlays meant to be loaded as a second
    # part in the slicer, not printed on their own
    ('mini-round-clock-numerals.stl',            'a part, not a print', 0.45),
    ('mini-round-clock-numerals-32.stl',         'a part, not a print', 0.45),
    ('mini-round-clock-numerals-60.stl',         'a part, not a print', 0.45),
    ('mini-round-clock-diffuser.stl',            'face down',       0.18),
    ('mini-round-clock-diffuser-32.stl',         'face down',       0.18),
    ('mini-round-clock-diffuser-60.stl',         'face down',       0.18),
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


def inlay_strokes(m, nozzle, n=12000, seed=0):
    """How wide are the glyph strokes, and how much of the part is under a bead?

    Same ray probe as thin_clusters, but only on the SIDE walls -- the top and
    bottom faces of a 0.50 mm slab just measure the slab, which says nothing
    about whether a stroke can be printed. Returns (fraction under a nozzle
    width, median stroke width).
    """
    pts, fid = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fid]
    side = np.abs(nrm[:, 2]) < 0.5
    pts, nrm = pts[side], nrm[side]
    org = pts - nrm*1e-4
    loc, ri, _ = m.ray.intersects_location(org, -nrm, multiple_hits=True)
    best = {}
    d = np.linalg.norm(loc - org[ri], axis=1)
    for i, dist in zip(ri, d):
        if dist > 1e-4 and dist < best.get(i, 1e9): best[i] = dist
    v = np.array(list(best.values()))
    if len(v) == 0: return 0.0, np.inf
    return float((v < nozzle).mean()), float(np.median(v))


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
                        r=(r.min(), r.max()), z=(q[:,2].min(), q[:,2].max()),
                        xy=(q[:,0].min(), q[:,0].max(), q[:,1].min(), q[:,1].max())))
    return out, np.percentile(allv, 1.0)

def layer_width(m, c, min_wall=MIN_WALL, layer=LAYER, cap=6.0, step=0.05):
    """The narrowest thing a slicer actually has to lay down in this region.

    thin_clusters shoots its ray along the surface NORMAL. That is the right
    measure for a wall and the wrong one for a CHAMFER: across a 45 degree
    lead-in the normal distance runs to zero at the tip, while every individual
    layer stays full width -- the tip is simply the top layer of something
    thicker underneath. A printer works layer by layer in XY, so the question
    that decides printability is how wide the solid is WITHIN a layer.

    Returned: the smallest, over the layers the cluster spans, of the largest
    circle that fits inside the cross-section there. A genuine thin wall is
    thin by this measure too; a chamfer is not.
    """
    from shapely.geometry import box as sbox
    x0, x1, y0, y1 = c['xy']; z0, z1 = c['z']
    # the window has to hold the WHOLE feature or it truncates it and reads
    # narrow for the wrong reason; 2 x min_wall is enough to reach across
    # anything that is about to be called too thin, and clipping can only ever
    # make this reading pessimistic
    pad = 2.0 * min_wall
    win = sbox(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    worst = np.inf
    z = z0 + layer/2
    while z <= z1:
        try:
            sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            pl, _ = sec.to_planar(to_2D=np.eye(4))
        except Exception:
            z += layer; continue
        best = 0.0
        for poly in pl.polygons_full:
            q = poly.intersection(win)
            if q.is_empty or q.area < 1e-6: continue
            d = 0.0
            while d < cap and not q.buffer(-(d + step)/2).is_empty:
                d += step
            best = max(best, d)
        if best > 0: worst = min(worst, best)
        z += layer
    return worst


BASE_THIN, _ = thin_clusters(_sam)
DIFF_THIN, _ = thin_clusters(_samd, thr=0.18)
SAM_THIN = {'sam-base': BASE_THIN, 'sam-diffuser': DIFF_THIN}
for k, v in SAM_THIN.items():
    print(f"\nbaseline: Sam's uploaded {k.split('-')[1]} has {len(v)} thin region(s)")
    for s_ in v:
        print(f"   {s_['n']:3d} pts, {s_['tmin']:.2f}-{s_['tmax']:.2f} mm, "
              f"r {s_['r'][0]:.1f}-{s_['r'][1]:.1f}, z {s_['z'][0]:.1f}-{s_['z'][1]:.1f}")

# The numeral inlays are not prints. They are the second filament of the
# diffuser: loaded as a part alongside it in the slicer, laid down inside the
# same layers, in pockets whose walls are the diffuser itself. They never touch
# the plate on their own and they are never a free-standing wall, so the
# plate-adhesion and thin-wall tests written for a print do not apply to them --
# they get their own, below.
INLAY = {'mini-round-clock-numerals.stl', 'mini-round-clock-numerals-32.stl',
         'mini-round-clock-numerals-60.stl'}
NOZZLE = 0.42       # narrowest bead a 0.4 mm nozzle will actually lay down

_gone = [f for f, _, _ in PARTS if not os.path.exists(f)]
if _gone:
    print('not built, so not checked: ' + ', '.join(_gone))
PARTS = [t for t in PARTS if os.path.exists(t[0])]

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
    if fn in INLAY:
        ck(foot > 10.0, 'sits flat, and is held by the diffuser around it',
           f'{foot:.0f} mm2 of glyph on the diffuser\'s own first layer')
    else:
        ck(foot > 400.0 or foot > 0.40 * bbox, 'first layer has a generous footprint',
           f'{foot:.0f} mm2 ({100*foot/bbox:.0f}% of its own footprint)')

    # --- sloped overhangs: cannot be bridged, judged by angle ----------------
    # A face within 15 degrees of horizontal is a BRIDGE, not a slope -- the
    # extruder spans it the same way whether it is dead flat or tipped 8 degrees
    # by a stand's tilt. Judge those by span, below, and only treat the genuinely
    # sloped band as an overhang.
    FLAT = -0.966                       # cos(15 deg)
    slope = above & (n[:,2] < -1e-6) & (n[:,2] > FLAT) \
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
    ceil = above & (n[:,2] <= FLAT)
    worst, worst_at = 0.0, None
    if ceil.any():
        for z in np.unique(np.round(zc[ceil], 0)):
            sel = np.nonzero(ceil & (np.abs(zc - z) < 3.0))[0]
            if len(sel) < 1: continue
            w, at = bridge_span(m, sel)
            if w > worst: worst, worst_at = w, (z, at)
    ck(worst <= MAX_BRIDGE, f'every flat ceiling bridges <= {MAX_BRIDGE:.0f} mm',
       f'worst {worst:.1f} mm' + (f' at z={worst_at[0]:.1f}' if worst_at else ''))
    # The span test above is the one that carries the meaning -- a bridge either
    # crosses or it does not. Total area only says "how much bridging", and a
    # deliberately hollowed part is mostly bridging by design: the 240 mm base
    # is a floor plate with two shelves over ribbed cavities, so ~47% of its
    # plan area is ceiling and every bit of it spans 14 mm or less. So this is a
    # proportional sanity check now, not a flat 2000 mm2 written for a 108 mm
    # disc: it only fires if the part is essentially a lid over a void.
    plan = math.pi * (max(np.hypot(m.vertices[:,0], m.vertices[:,1]))**2) \
           if abs(m.extents[0] - m.extents[1]) < 1.0 else m.extents[0]*m.extents[1]
    ck(ar[ceil].sum() < 0.60*plan, 'total ceiling area is in proportion',
       f'{ar[ceil].sum():.0f} mm2, {100*ar[ceil].sum()/plan:.0f}% of its plan area')

    # --- wall thickness ------------------------------------------------------
    cl, p1 = thin_clusters(m, thr=min_wall)
    allowed = SAM_THIN.get(BASELINE.get(fn, ''), [])
    unexplained = []
    for c_ in cl:
        ok = any(overlaps(c_, a) for a in allowed)
        note = '   [same place in Sam''s file]' if ok else '   << NEW'
        if not ok and fn not in INLAY:
            # measure it the way a slicer sees it before calling it a defect
            lw = layer_width(m, c_, min_wall)
            c_['lw'] = lw
            if lw >= min_wall:
                ok = True
                note = f'   [chamfer: {lw:.2f} mm wide in every layer]'
            else:
                note = f'   << NEW, and only {lw:.2f} mm wide in a layer'
        if not ok: unexplained.append(c_)
        print(f"         thin region: {c_['n']:3d} pts, {c_['tmin']:.2f}-{c_['tmax']:.2f} mm, "
              f"r {c_['r'][0]:.1f}-{c_['r'][1]:.1f}, z {c_['z'][0]:.1f}-{c_['z'][1]:.1f}"
              f"{note}")
    if fn in INLAY:
        # A glyph is not a wall. Every letterform has corners and stroke ends
        # that taper to nothing, and they cluster here however fat the stems
        # are, so the question is not "is anything thin" but "how much of it".
        # Anything under a nozzle width simply does not get extruded: the black
        # stops a fraction of a millimetre short in a glyph corner, inside a
        # pocket whose floor is 1.50 mm of solid white. Nothing is at risk.
        frac, stem = inlay_strokes(m, NOZZLE)
        ck(stem >= 2*NOZZLE, 'the numeral stems are two beads wide or more',
           f'median stroke {stem:.2f} mm, against a {NOZZLE:.2f} mm bead')
        ck(frac < 0.03, 'and only glyph corners fall under a nozzle width',
           f'{100*frac:.1f}% of the surface, which just will not be extruded')
    else:
        ck(not unexplained,
           f'no NEW region thinner than {min_wall} mm in the layers that print it',
           f'1st percentile {p1:.2f} mm, {len(cl)} thin region(s), {len(unexplained)} new')

print()
if FAIL:
    print(f'PASS 3: {len(FAIL)} FAILURES'); [print('   -',f) for f in FAIL]; sys.exit(1)
print('PASS 3: prints without support in the stated orientation')
