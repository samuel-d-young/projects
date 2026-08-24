#!/usr/bin/env python3
"""Measure the specific features Sam says are wrong: the tab slot, the diffuser's
outer wall, its membrane, and its baffles."""
import math, numpy as np, trimesh, sys
sys.path.insert(0,'.')
from measure_uploaded import load, solid_at, bisect, ray, show

base = load('base_in.stl')[0]
diff = load('diffuser_in.stl')[0]

def sa(m):
    def f(x,y,z,tol=1e-6):
        for dx,dy in [(0,0),(1e-3,7e-4),(-9e-4,1.1e-3),(1.3e-3,-8e-4),(-1.1e-3,-1.2e-3)]:
            from measure_uploaded import spans
            sp = spans(m, x+dx, y+dy)
            if sp is None: continue
            return any(a-tol<=z<=b+tol for a,b in sp)
        return False
    return f
sb, sd = sa(base), sa(diff)

print('BASE — the display-tab slot, at the height the tab actually occupies')
print('  (module back on the seat at z=8.60, its PCB 1.6 thick -> tab at z 8.6..10.2)')
for z in (6.0, 9.0, 9.4, 10.0, 11.0, 11.6):
    for r in (32.0, 36.0, 40.0):
        f = lambda y: sb(math.sqrt(max(r*r-y*y,0)) if r*r>y*y else 0, y, z)
        # walk +y until solid
        yy = None
        for y in np.arange(0, r, 0.05):
            x = math.sqrt(max(r*r - y*y, 0))
            if sb(x, y, z):
                yy = y; break
        half = f'{yy:6.2f}' if yy is not None else '  open'
        print(f'   z={z:5.1f} r={r:5.1f}  slot half-width = {half} mm', end='')
    print()

print()
print(f'  tab as Sam measures it: 30.55 wide -> half-width 15.275')
print(f'  tab corner radius = hypot(15.275, 67 - 60/2) = {math.hypot(15.275, 37.0):.2f}')
print(f'  current slot reaches r = 42.657, half-angle 41.758 deg')
print(f'    -> at r=35 the slot is {2*35*math.sin(math.radians(41.758)):.2f} mm wide')
print(f'    -> the tab can rotate about +/-{math.degrees(math.asin(min(1,15.275/35))):.1f} deg before it touches. '
      f'That is the looseness.')

print()
print('DIFFUSER — the features to change')
a = ray(90); P = lambda r,z: (r*math.cos(math.radians(90)), r*math.sin(math.radians(90)), z)
Sz = lambda z: (lambda r: sd(*P(r,z)))
Zr = lambda r: (lambda z: sd(*P(r,z)))
show('outer wall OUTER radius (z=1.0)', bisect(Sz(1.0), 47.5, 44))
show('outer wall INNER radius (z=3.0)', bisect(Sz(3.0), 40, 46))
show('outer wall top (r=45.6)',        bisect(Zr(45.6), 0.5, 9))
show('membrane inner radius (z=0.4)',  bisect(Sz(0.4), 36, 41))
show('membrane outer radius (z=0.4)',  bisect(Sz(0.4), 47.5, 43))
show('membrane top (r=42)',            bisect(Zr(42.0), 0.2, 3))
show('inner skirt outer radius (z=1.5)', bisect(Sz(1.5), 41, 33))
show('inner skirt top (r=33)',         bisect(Zr(33.0), 0.4, 6))
show('collar inner radius (z=6)',      bisect(Sz(6.0), 20, 30))
show('collar outer radius (z=6)',      bisect(Sz(6.0), 34, 29))
show('collar top (r=29)',              bisect(Zr(29.0), 0.5, 12))

print()
print('  baffle angular width at r=42, z=2.0:')
hits=[d for d in np.arange(0,30,0.05)
      if sd(42*math.cos(math.radians(d)), 42*math.sin(math.radians(d)), 2.0)]
grp=[]
for d in hits:
    if grp and d-grp[-1][-1] <= 0.06: grp[-1].append(d)
    else: grp.append([d])
for g in grp[:2]:
    w = (g[-1]-g[0])
    print(f'     centre {np.mean(g):6.2f} deg, angular width {w:5.2f} deg '
          f'-> {2*42*math.sin(math.radians(w/2)):.2f} mm at r=42')
