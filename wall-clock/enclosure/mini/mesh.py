"""Minimal STL mesh builder — revolve a 2D profile, add boxes, write binary STL.

Written because this environment has no OpenSCAD. Everything here is
rotationally simple (dishes, annular rings) plus rectangular baffles, so a
revolve-and-boxes builder covers the whole part set without needing CSG.

Watertightness is checked by computing the signed volume with the divergence
theorem: a closed, consistently-wound mesh gives a positive volume that matches
the analytic value. A leaky or inside-out mesh does not.
"""
import math
import struct

Tri = tuple  # ((x,y,z), (x,y,z), (x,y,z))


def revolve(profile, seg=180):
    """Revolve a closed (r, z) polygon around the Z axis.

    profile: list of (r, z). Traced so the interior is on the left when walking
    the list — i.e. counter-clockwise in the r-z half-plane. Closes automatically.
    """
    tris = []
    n = len(profile)
    for i in range(n):
        r0, z0 = profile[i]
        r1, z1 = profile[(i + 1) % n]
        for j in range(seg):
            a0 = 2 * math.pi * j / seg
            a1 = 2 * math.pi * (j + 1) / seg
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)
            p00 = (r0 * c0, r0 * s0, z0)
            p10 = (r1 * c0, r1 * s0, z1)
            p11 = (r1 * c1, r1 * s1, z1)
            p01 = (r0 * c1, r0 * s1, z0)
            # Two triangles per quad. Degenerate ones (r == 0) are dropped.
            # Wound so the outward normal points away from the axis.
            if r0 > 1e-9 or r1 > 1e-9:
                tris.append((p00, p11, p10))
                tris.append((p00, p01, p11))
    return tris


def box(cx, cy, cz, sx, sy, sz, rot_deg=0.0):
    """Axis-aligned box, optionally rotated about Z, centred on (cx,cy,cz)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    pts = []
    ca, sa = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    for dx, dy, dz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                       (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
        x, y, z = dx * hx, dy * hy, dz * hz
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z))
    faces = [(0, 1, 2), (0, 2, 3),      # bottom (-Z)
             (4, 6, 5), (4, 7, 6),      # top (+Z)
             (0, 4, 5), (0, 5, 1),      # -Y
             (1, 5, 6), (1, 6, 2),      # +X
             (2, 6, 7), (2, 7, 3),      # +Y
             (3, 7, 4), (3, 4, 0)]      # -X
    return [(pts[a], pts[c], pts[b]) for a, b, c in faces]


def signed_volume(tris):
    """Divergence theorem. Positive => closed and outward-wound."""
    v = 0.0
    for a, b, c in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return v


def bounds(tris):
    xs = [p[0] for t in tris for p in t]
    ys = [p[1] for t in tris for p in t]
    zs = [p[2] for t in tris for p in t]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def write_stl(path, tris, name="part"):
    with open(path, "wb") as f:
        f.write(struct.pack("<80sI", name.encode()[:80].ljust(80, b"\0"), len(tris)))
        for a, b, c in tris:
            ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f.write(struct.pack("<3f", nx / ln, ny / ln, nz / ln))
            for p in (a, b, c):
                f.write(struct.pack("<3f", *p))
            f.write(struct.pack("<H", 0))
    return len(tris)
