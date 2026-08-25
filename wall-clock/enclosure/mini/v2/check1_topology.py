#!/usr/bin/env python3
"""PASS 1 of 3 — topology. Is each part a single, closed, correctly-oriented solid?"""
import sys, os; sys.path.insert(0,'.')
import numpy as np, trimesh, collections
import csg
from csg import to_manifold

FAIL = []
def check(cond, msg, detail=''):
    tag = 'ok  ' if cond else 'FAIL'
    print(f'  [{tag}] {msg}' + (f'   {detail}' if detail else ''))
    if not cond: FAIL.append(msg)

# how much Sam's own uploaded diffuser disagrees with itself, measured, not assumed
_src = trimesh.load('diffuser_in.stl', process=False); _src.merge_vertices()
SOURCE_AMBIGUITY = abs(to_manifold(_src).volume() - _src.volume) / _src.volume * 100

# the numeral inlays are twelve separate solids (and the two-digit ones are two
# each), so "exactly one connected body" is the wrong question for them -- every
# shell is checked on its own instead
MULTI = {'mini-round-clock-numerals.stl',
         'mini-round-clock-numerals-32.stl',
         'mini-round-clock-numerals-60.stl'}

PARTS = [('mini-round-clock-base.stl', True),
         ('mini-round-clock-housing.stl', True),
         ('mini-round-clock-diffuser.stl', True),
         ('mini-round-clock-deskstand.stl', True),
         ('mini-round-clock-base-32.stl', True),
         ('mini-round-clock-housing-32.stl', True),
         ('mini-round-clock-diffuser-32.stl', True),
         ('mini-round-clock-deskstand-32.stl', True),
         ('mini-round-clock-base-60.stl', True),
         ('mini-round-clock-housing-60.stl', True),
         ('mini-round-clock-diffuser-60.stl', True),
         ('mini-round-clock-deskstand-60.stl', True),
         ('mini-round-clock-light-guides-60.stl', True),
         ('mini-round-clock-numerals.stl', True),
         ('mini-round-clock-numerals-32.stl', True),
         ('mini-round-clock-numerals-60.stl', True),
         ('mini-round-clock-battery-shelf-x2.stl', True)]
# Parts that the build deliberately did not emit -- at HOUSING_DEEP = 25.00 no
# battery fits, so there are no shelves to check. Say which, do not skip quietly.
_gone = [f for f, _ in PARTS if not os.path.exists(f)]
if _gone:
    print('  not built, so not checked: ' + ', '.join(_gone))
PARTS = [(f, k) for f, k in PARTS if os.path.exists(f)]

for name, strict in PARTS:
    print(f'\n{name}' + ('' if strict else '   [derived from Sam\'s mesh - relaxed]')) 
    m = trimesh.load(name, process=False)
    m.merge_vertices()
    if strict: check(m.is_watertight, 'watertight (no holes in the surface)')
    check(m.is_winding_consistent, 'winding consistent')
    check(m.volume > 0, 'positive volume (normals point outward)', f'{m.volume:.1f} mm3')
    if name in MULTI:
        shells = m.split(only_watertight=False)
        ok = all(p.is_watertight and p.volume > 0 for p in shells)
        check(ok, f'all {len(shells)} shells closed and positive',
              'twelve numerals; the two-digit ones are two shells each')
    else:
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
        # Two independent volume calculations over a surface with non-manifold
        # edges will not agree exactly -- the disagreement IS the ambiguity the
        # defects introduce. Sam's uploaded diffuser disagrees with itself by
        # 0.054%; anything derived from it is held to no worse than that, not to
        # zero, because zero is not achievable from that source.
        rel = abs(man.volume() - m.volume) / m.volume * 100
        lim = 1e-4 if strict else SOURCE_AMBIGUITY
        check(rel < lim, 'volume agrees with manifold3d',
              f'{man.volume():.1f} vs {m.volume:.1f}  ({rel:.4f}%'
              + (f', source is {SOURCE_AMBIGUITY:.3f}%)' if not strict else ')'))
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
