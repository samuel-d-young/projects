#!/usr/bin/env python3
"""Re-derive every number in params.py from Sam's uploaded STLs.

    python3 measure_uploaded.py

Nothing in this project's rear end is a guess about his geometry. This is where
the numbers came from: shoot a vertical line through the solid at a point, find
where it crosses the surface, and bisect for the exact boundary. Run it again
if he sends new files, and diff the output against params.py.
"""
import math
import numpy as np
import trimesh


# --------------------------------------------------------------------------- io
def load(path):
    """Largest volumetric shell, recentred on the outer circle. z is untouched."""
    m = trimesh.load(path, process=False)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    parts = [p for p in m.split(only_watertight=False) if abs(p.volume) > 1.0]
    parts.sort(key=lambda p: -abs(p.volume))
    b = parts[0].bounds
    cx, cy = (b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2
    out = []
    for p in parts:
        q = p.copy(); q.apply_translation([-cx, -cy, 0]); out.append(q)
    return out


# ------------------------------------------------------------------- the probe
def spans(m, x, y, lo=-60.0, hi=60.0):
    """Solid z-intervals along the vertical line through (x, y)."""
    V, F = m.vertices, m.faces
    tri = V[F]
    p = np.array([x, y])
    a, b, c = tri[:, 0, :2], tri[:, 1, :2], tri[:, 2, :2]

    def side(o, q, r):
        return (q[:, 0] - o[:, 0]) * (r[1] - o[:, 1]) - (q[:, 1] - o[:, 1]) * (r[0] - o[:, 0])

    d1, d2, d3 = side(a, b, p), side(b, c, p), side(c, a, p)
    inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
    zs = []
    for i in np.nonzero(inside)[0]:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = tri[i]
        den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(den) < 1e-12:
            continue
        l1 = ((y2 - y3) * (p[0] - x3) + (x3 - x2) * (p[1] - y3)) / den
        l2 = ((y3 - y1) * (p[0] - x3) + (x1 - x3) * (p[1] - y3)) / den
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) < -1e-9:
            continue
        z = l1 * z1 + l2 * z2 + l3 * z3
        if lo <= z <= hi:
            zs.append(z)
    if not zs:
        return []
    z = np.array(sorted(zs))
    z = z[np.concatenate(([True], np.diff(z) > 1e-4))]
    if len(z) % 2:
        return None                              # ray clipped an edge; jitter and retry
    return [(z[i], z[i + 1]) for i in range(0, len(z), 2)]


def solid_at(m, x, y, z, tol=1e-6):
    """Robust to the small holes both uploaded meshes carry."""
    for dx, dy in [(0, 0), (1e-3, 7e-4), (-9e-4, 1.1e-3), (1.3e-3, -8e-4), (-1.1e-3, -1.2e-3)]:
        sp = spans(m, x + dx, y + dy)
        if sp is None:
            continue
        return any(a - tol <= z <= b + tol for a, b in sp)
    return False


def bisect(f, lo, hi, n=60):
    flo = f(lo)
    if flo == f(hi):
        return None
    for _ in range(n):
        mid = (lo + hi) / 2
        if f(mid) == flo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ray(deg):
    a = math.radians(deg)
    return lambda r, z: (r * math.cos(a), r * math.sin(a), z)


def show(label, v, unit='mm'):
    print(f'  {label:44s} {"n/a" if v is None else f"{v:9.4f} {unit}"}')


# ------------------------------------------------------------------------ base
def measure_base():
    parts = load('base_in.stl')
    m = parts[0]
    print('BASE  (Mini_Wall_Clock_Base.stl)')
    print(f'  {len(parts)} volumetric shell(s); main = {m.volume:.1f} mm3')
    for p in parts[1:]:
        b = p.bounds
        r = np.hypot(p.vertices[:, 0], p.vertices[:, 1])
        a = np.degrees(np.arctan2(p.vertices[:, 1], p.vertices[:, 0]))
        print(f'  !! DISCONNECTED SHELL {p.volume:.1f} mm3 at r {r.min():.2f}-{r.max():.2f}, '
              f'{a.min():.1f} to {a.max():.1f} deg, z {b[0][2]:.2f}-{b[1][2]:.2f}')
        print('     boolean residue, sitting in the display-tab window. build_v2.py drops it.')

    P = ray(90)                                   # a clean quadrant, away from both slots
    S = lambda z: (lambda r: solid_at(m, *P(r, z)))
    Z = lambda r: (lambda z: solid_at(m, *P(r, z)))
    print('\n  measured on the 90-degree ray:')
    show('R_BODY        body outer (z=10)',       bisect(S(10.0), 40, 58))
    show('R_LIP_I       face recess inner (z=20.5)', bisect(S(20.5), 45, 53.5))
    show('Z_RECESS      recess floor (r=49)',     bisect(Z(49.0), 14, 24))
    show('R_RING_O      ring pocket outer (z=15)', bisect(S(15.0), 42, 50))
    show('R_RING_I      ring pocket inner (z=15)', bisect(S(15.0), 32, 42))
    show('Z_RING_FLOOR  ring pocket floor (r=41)', bisect(Z(41.0), 6, 16))
    show('R_DISP_POCKET display pocket wall (z=12)', bisect(S(12.0), 20, 34))
    show('Z_SEAT        display seat top (r=29)', bisect(Z(29.0), 4, 12))
    show('R_BORE        rear bore wall (z=4)',    bisect(S(4.0), 20, 34))

    print('\n  the wire slot Sam added (6 o\'clock):')
    f = lambda y: solid_at(m, -38.0, y, 4.0)
    lo, hi = bisect(f, 0, -30), bisect(f, 0, 30)
    show('WIRE_SLOT_HW  half width', (hi - lo) / 2 if lo is not None else None)
    show('WIRE_SLOT_END outer end (x)', bisect(lambda x: solid_at(m, x, 0.0, 4.0), -30, -52))
    thru = not solid_at(m, -38.0, 0.0, 15.0) and not solid_at(m, -38.0, 0.0, 20.0)
    print(f'  {"open front to back — the deck now closes it" if thru else "blind":44s} '
          f'{"(through)" if thru else ""}')

    print('\n  the display-tab window (12 o\'clock):')
    g = lambda a: solid_at(m, 35 * math.cos(math.radians(a)), 35 * math.sin(math.radians(a)), 4.0)
    show('TAB_HALF_DEG  half angle at r=35', bisect(g, 0, 90), 'deg')
    show('R_TAB         reach on the +x axis', bisect(lambda x: solid_at(m, x, 0.0, 4.0), 30, 52))


# -------------------------------------------------------------------- diffuser
def measure_diffuser():
    m = load('diffuser_in.stl')[0]
    print('\n\nDIFFUSER  (Mini_Wall_Clock_Difuser.stl)')
    print(f'  {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.2f} mm, {m.volume:.1f} mm3')
    P = ray(90)
    S = lambda z: (lambda r: solid_at(m, *P(r, z)))
    Z = lambda r: (lambda z: solid_at(m, *P(r, z)))
    print('  local z: 0 is the flat face that goes under the plywood.')
    show('membrane top (r=42)',            bisect(Z(42.0), 0.2, 4))
    show('baffle / outer wall top (r=45.5)', bisect(Z(45.5), 1, 9))
    show('inner skirt top (r=33)',         bisect(Z(33.0), 0.5, 6))
    show('screen collar inner r (z=6)',    bisect(S(6.0), 20, 30))
    show('screen collar outer r (z=6)',    bisect(S(6.0), 34, 29))
    show('screen collar top (r=29)',       bisect(Z(29.0), 0.5, 12))

    hits = [d for d in np.arange(0, 360, 0.2)
            if solid_at(m, 41 * math.cos(math.radians(d)), 41 * math.sin(math.radians(d)), 3.0)]
    groups = []
    for d in hits:
        if groups and d - groups[-1][-1] <= 0.25:
            groups[-1].append(d)
        else:
            groups.append([d])
    if len(groups) > 1:
        centres = [float(np.mean(g)) for g in groups]
        print(f'  {len(groups)} baffles at r=41, pitch {np.mean(np.diff(centres)):.2f} deg '
              f'(24 LEDs would be 15.00), first at {centres[0]:.1f} deg')


# ------------------------------------------------------------------ the clash
def collar_clash(module_t=4.00):
    """Does the diffuser's collar reach the display before the diffuser seats?"""
    Z_SEAT, LED_TOP, DIFF_LOCAL_TOP, Z_DIFF_FACE = 8.60, 15.00, 8.20, 19.00
    module_front = Z_SEAT + module_t
    collar_bottom = Z_DIFF_FACE - DIFF_LOCAL_TOP
    print('\n\nCOLLAR vs DISPLAY')
    print(f'  display seat                    z = {Z_SEAT:6.2f}')
    print(f'  + module thickness {module_t:.2f}          z = {module_front:6.2f}   <- module front face')
    print(f'  diffuser seats when its baffles')
    print(f'    meet the LED tops at          z = {LED_TOP:6.2f}')
    print(f'  -> collar bottom lands at       z = {collar_bottom:6.2f}')
    d = module_front - collar_bottom
    if d > 0:
        print(f'\n  INTERFERENCE {d:.2f} mm. The collar hits the module before the diffuser')
        print(f'  is down, so it stands {d:.2f} mm proud and the plywood will not seat.')
        print(f'  Fix either way: COLLAR_TRIM = {d:.2f} (reprint the diffuser),')
        print(f'                  or SEAT_DROP = {d:.2f} (rebuild the base instead).')
    else:
        print(f'\n  {-d:.2f} mm of clearance. Nothing to do.')
    print('  NB: module_t is the thickness at the RIM the collar lands on, which is not')
    print('  necessarily the 4 mm overall figure. Measure that rim before acting.')


if __name__ == '__main__':
    measure_base()
    measure_diffuser()
    collar_clash()
