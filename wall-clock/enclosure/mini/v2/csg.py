#!/usr/bin/env python3
"""Manifold-backed CSG helpers. Every primitive is built watertight by construction."""
import numpy as np, trimesh, math
from manifold3d import Manifold, Mesh, CrossSection, FillRule

# ---------------------------------------------------------------- conversion
def to_manifold(m: trimesh.Trimesh) -> Manifold:
    v = np.asarray(m.vertices, dtype=np.float32)
    f = np.asarray(m.faces, dtype=np.uint32)
    man = Manifold(Mesh(vert_properties=v, tri_verts=f))
    if man.status().name != 'NoError':
        raise ValueError(f'not a manifold: {man.status()}')
    return man

def to_trimesh(man: Manifold) -> trimesh.Trimesh:
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)

# ---------------------------------------------------------------- primitives
def box(dx, dy, dz, centre=(0, 0, 0)):
    """Axis-aligned box, centred on `centre`."""
    return Manifold.cube([dx, dy, dz], center=True).translate(list(centre))

def box_lwh(x0, x1, y0, y1, z0, z1):
    """Box from explicit min/max on each axis."""
    return box(x1-x0, y1-y0, z1-z0, ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2))

def cyl(r, z0, z1, seg=192, centre=(0, 0)):
    return Manifold.cylinder(z1-z0, r, r, seg, center=False).translate([centre[0], centre[1], z0])

def cone(r0, r1, z0, z1, seg=192, centre=(0, 0)):
    return Manifold.cylinder(z1-z0, r0, r1, seg, center=False).translate([centre[0], centre[1], z0])

def tube(ri, ro, z0, z1, seg=192):
    return cyl(ro, z0, z1, seg) - cyl(ri, z0-1, z1+1, seg)

def wedge(r_in, r_out, z0, z1, a0_deg, a1_deg, seg=None):
    """Angular sector of an annulus as ONE closed polygon.

    Built as a single contour (inner arc reversed + outer arc) rather than a
    union of prisms: unioning prisms leaves coincident faces at every seam,
    which survive as zero-area triangles once the STL is written in float32.
    """
    a0, a1 = math.radians(a0_deg), math.radians(a1_deg)
    n = seg if seg else max(4, int(abs(a1_deg - a0_deg) / 2.0) + 2)
    k = 1.0 / math.cos((a1 - a0) / (2 * n))       # so flats still reach r_out
    outer = [((r_out*k)*math.cos(a0 + (a1-a0)*i/n), (r_out*k)*math.sin(a0 + (a1-a0)*i/n))
             for i in range(n + 1)]
    if r_in <= 1e-9:
        pts = outer + [(0.0, 0.0)]
    else:
        inner = [(r_in*math.cos(a0 + (a1-a0)*i/n), r_in*math.sin(a0 + (a1-a0)*i/n))
                 for i in range(n, -1, -1)]
        pts = outer + inner
    return _ex(pts, z0, z1)

def prism(pts_xy, z0, z1):
    """Extrude a closed CCW polygon."""
    return _ex(pts_xy, z0, z1)


def prism_taper(pts_xy, z0, z1, sx=1.0, sy=1.0):
    """Extrude a polygon, scaling it about the origin on the way up."""
    return _ex_taper(pts_xy, z0, z1, sx, sy)

def _ex_taper(pts_xy, z0, z1, sx, sy):
    """Extrude with the top scaled — a straight-line flare, for a lead-in."""
    p = np.array(pts_xy, dtype=np.float64)
    if _signed_area(p) < 0: p = p[::-1]
    cs = CrossSection([p])
    return Manifold.extrude(cs, z1 - z0, 0, 0.0, (sx, sy)).translate([0.0, 0.0, z0])


def _ex(pts_xy, z0, z1):
    """Extrude one closed polygon between two z planes, winding fixed for us."""
    p = np.array(pts_xy, dtype=np.float64)
    if _signed_area(p) < 0: p = p[::-1]
    cs = CrossSection([p])
    return Manifold.extrude(cs, z1 - z0).translate([0.0, 0.0, z0])

def _signed_area(p):
    x, y = p[:,0], p[:,1]
    return 0.5*np.sum(x*np.roll(y,-1) - np.roll(x,-1)*y)

def rot_rect(cx, cy, dx, dy, angle_deg, r=0.0, n=10):
    """A rounded rectangle centred on (cx, cy) and rotated -- for radial ticks."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = rounded_rect(dx, dy, r, n) if r > 0 else [
        (-dx/2, -dy/2), (dx/2, -dy/2), (dx/2, dy/2), (-dx/2, dy/2)]
    return [(x*ca - y*sa + cx, x*sa + y*ca + cy) for x, y in pts]


def rounded_rect(dx, dy, r, n=16):
    """CCW point list for a rectangle with radiused corners, centred on origin."""
    r = min(r, dx/2-1e-6, dy/2-1e-6)
    hx, hy = dx/2-r, dy/2-r
    pts = []
    for cx, cy, a0 in [(hx,hy,0), (-hx,hy,90), (-hx,-hy,180), (hx,-hy,270)]:
        for i in range(n+1):
            a = math.radians(a0 + 90*i/n)
            pts.append((cx+r*math.cos(a), cy+r*math.sin(a)))
    return pts

def slab_chamfer(dx, dy, z0, z1, chamfer, centre=(0,0)):
    """A box whose top tapers inward — gives a printable 45-degree roof."""
    lo = prism(rounded_rect(dx, dy, 0.01), z0, z0+1e-3)
    hi = prism(rounded_rect(dx-2*chamfer, dy-2*chamfer, 0.01), z1-1e-3, z1)
    return (lo + hi).hull().translate([centre[0], centre[1], 0])

# ---------------------------------------------------------------- text
def text_polys(txt, height, family='DejaVu Sans', weight='bold', fontfile=None):
    """Glyph outlines for `txt`, scaled to `height` and centred on the origin.

    Returns a list of contours; the counters in 6, 9 and 0 come back as their
    own contours, so extrude them with an even-odd fill rule or they fill in.
    """
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    prop = (FontProperties(fname=fontfile) if fontfile
            else FontProperties(family=family, weight=weight))
    tp = TextPath((0, 0), txt, size=100.0, prop=prop)
    polys = [np.asarray(p, dtype=np.float64) for p in tp.to_polygons() if len(p) >= 3]
    if not polys:
        raise ValueError(f'no outline for {txt!r}')
    allp = np.concatenate(polys)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    k = height / (hi[1] - lo[1])
    c = (lo + hi) / 2.0
    return [(p - c) * k for p in polys]


def text_prism(txt, height, centre, z0, z1, angle_deg=0.0, mirror=False, **kw):
    """Extruded text, centred on `centre`, rotated `angle_deg` about its centre.

    `mirror` swaps the glyph's own x and y before placing it. That is a
    reflection, and it is there for text that will be READ FROM THE OTHER SIDE:
    the diffuser is modelled with its visible face at z=0 and everything else
    behind it, so it is installed turned over, and text laid out the ordinary
    way comes out back to front. Reflecting it in the model and then viewing it
    from the far side cancels out -- including the digit order, so "12" still
    reads 12 and not 21. It also swaps the axes: with mirror on, the glyph's
    "up" is +x and its "right" is +y.
    """
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)

    def place(x, y):
        if mirror:
            x, y = y, x
        return (x*ca - y*sa + centre[0], x*sa + y*ca + centre[1])

    cs = CrossSection([[place(x, y) for x, y in p]
                       for p in text_polys(txt, height, **kw)],
                      fillrule=FillRule.EvenOdd)
    return Manifold.extrude(cs, z1 - z0).translate([0.0, 0.0, z0])


# ---------------------------------------------------------------- checks
def report(man, name):
    t = to_trimesh(man)
    print(f'  {name:34s} vol={man.volume():10.1f}mm3  tris={len(t.faces):6d}  '
          f'genus={man.genus():3d}  watertight={t.is_watertight}')
    return t


# ---------------------------------------------------------------- finalise
def finalise(man, name, quantise=True, rounds=6, strict=True):
    """Bring a solid through the float32 STL round trip and heal what that breaks.

    STL stores vertices as float32. Two vertices a boolean left 1e-5 apart
    collapse to the same point, turning the triangle between them into a
    zero-area face and punching a hole in an otherwise closed mesh. Doing the
    collapse HERE, then re-healing, means the file on disk is the thing that
    was checked -- not a cleaner version of it.
    """
    dropped = [0.0, 0]

    def drop_debris(t):
        """Discard zero-volume face fragments, keep everything with substance.

        A boolean between surfaces that land at the same coordinate leaves flat
        shells behind: no volume, but they count as separate bodies and they
        make slicers ask to repair the file. Only |volume| < 0.01 mm3 goes --
        anything real would trip the volume check two lines later.
        """
        parts = t.split(only_watertight=False)
        if len(parts) <= 1:
            return t
        # Two tests, because volume alone is not enough. A shell of 1 or 3 faces
        # cannot enclose anything, but trimesh's divergence-theorem volume on an
        # open sliver returns a large number anyway (+-9.02 mm3 was one), so it
        # survives the volume test and then breaks the concatenated mesh. The
        # smallest closed shell is a tetrahedron: 4 faces.
        def debris(p):
            return abs(p.volume) < 0.01 or len(p.faces) < 4
        keep = [p for p in parts if not debris(p)]
        gone = [p for p in parts if debris(p)]
        if gone:
            dropped[0] += sum(abs(p.volume) for p in gone)
            dropped[1] += len(gone)
        if not keep:
            return t
        return trimesh.util.concatenate(keep) if len(keep) > 1 else keep[0]

    def scrub(t):
        if quantise:
            t.vertices = np.asarray(t.vertices, dtype=np.float32).astype(np.float64)
        t.merge_vertices()
        t.update_faces(t.nondegenerate_faces())
        t.remove_unreferenced_vertices()
        t = drop_debris(t)
        if strict:
            # only safe on a mesh that IS closed; on an inherited-defect mesh
            # unique_faces() drops one of a coincident pair and fix_normals()
            # then flips a shell, turning a printable file into a broken one
            t.update_faces(t.unique_faces())
            t.fix_normals()
        return t

    import collections

    def bad_edges(t):
        c = collections.Counter(map(tuple, t.edges_sorted))
        return sum(1 for v in c.values() if v != 2)

    t = scrub(to_trimesh(man))
    for i in range(rounds):
        manifold_ok = False
        try:
            A = to_manifold(t)
            manifold_ok = abs((A ^ A).volume() - A.volume()) < 0.01
        except Exception:
            pass
        tight = t.is_watertight and t.body_count == 1
        if manifold_ok and (tight or not strict):
            be = bad_edges(t)
            note = 'clean' if tight else f'{be} inherited bad edges (slicers repair these)'
            if dropped[1]:
                note += f'; dropped {dropped[1]} zero-volume fragment(s)'
            print(f'  {name:34s} vol={t.volume:9.1f}  tris={len(t.faces):6d}  '
                  f'manifold=OK  {note}')
            return t
        t = scrub(to_trimesh(to_manifold(t)))
    raise RuntimeError(f'{name}: no clean float32 mesh after {rounds} rounds '
                       f'(watertight={t.is_watertight}, bad edges={bad_edges(t)})')
