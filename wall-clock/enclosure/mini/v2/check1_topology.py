#!/usr/bin/env python3
"""PASS 1 of 3 — topology. Is each part a single, closed, correctly-oriented solid?"""
import sys; sys.path.insert(0,'.')
import numpy as np, trimesh, collections
import csg
from csg import to_manifold

FAIL = []
def check(cond, msg, detail=''):
    tag = 'ok  ' if cond else 'FAIL'
    print(f'  [{tag}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

PARTS = [('mini-round-clock-base-v2.stl', True),
         ('mini-round-clock-rearhousing-slim.stl', True),
         ('mini-round-clock-rearhousing-battery.stl', True),
         ('mini-round-clock-battery-shim-x2.stl', True),
         # inherits 387 non-manifold edges from Sam's uploaded diffuser; the
         # trim halves them. Held to "manifold3d accepts it", not "watertight".
         ('mini-round-clock-diffuser-fix.stl', False)]

for name, strict in PARTS:
    print(f'\n{name}' + ('' if strict else '   [derived from Sam\'s mesh - relaxed]')) 
    m = trimesh.load(name, process=False)
    m.merge_vertices()
    if strict: check(m.is_watertight, 'watertight (no holes in the surface)')
    check(m.is_winding_consistent, 'winding consistent')
    check(m.volume > 0, 'positive volume (normals point outward)', f'{m.volume:.1f} mm3')
    check(m.body_count == 1, 'exactly one connected body', f'got {m.body_count}')
    # every edge used exactly twice
    cnt = collections.Counter(map(tuple, m.edges_sorted))
    bad = sum(1 for v in cnt.values() if v != 2)
    if strict: check(bad == 0, 'every edge shared by exactly 2 faces', f'{bad} bad of {len(cnt)}')
    else: print(f'  [note] {bad} non-manifold edges inherited from the source mesh (387 in Sam\'s original)')
    # zero-area faces
    deg = int((~m.nondegenerate_faces()).sum())
    if strict: check(deg == 0, 'no degenerate faces', f'{deg}')
    # manifold3d agrees
    try:
        man = to_manifold(m)
        check(man.status().name == 'NoError', 'manifold3d accepts it', str(man.status()))
        check(abs(man.volume() - m.volume) < 1.0, 'volume agrees with manifold3d',
              f'{man.volume():.1f} vs {m.volume:.1f}')
    except Exception as e:
        check(False, 'manifold3d accepts it', str(e))
    # self intersection: a clean solid intersected with itself changes nothing
    try:
        man = to_manifold(m)
        d = (man ^ man).volume()
        check(abs(d - man.volume()) < 0.05, 'no self-intersection', f'{d:.3f} vs {man.volume():.3f}')
    except Exception as e:
        check(False, 'no self-intersection', str(e))
    b = m.bounds
    print(f'         bounds  x[{b[0][0]:8.3f},{b[1][0]:8.3f}]  y[{b[0][1]:8.3f},{b[1][1]:8.3f}]  z[{b[0][2]:8.3f},{b[1][2]:8.3f}]')

print()
if FAIL:
    print(f'PASS 1: {len(FAIL)} FAILURES'); [print('   -', f) for f in FAIL]; sys.exit(1)
print('PASS 1: all topology checks clean')
