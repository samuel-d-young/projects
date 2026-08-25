#!/usr/bin/env python3
"""How the perspex makes an LED read 30 mm long instead of 5.

Two views: a section through one guide, and the face as it would look lit.
Everything is drawn from params.py.
"""
import sys, math; sys.path.insert(0,'.')
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from params import *
import build_v2 as BV

B = BV.BODY60
PLASTIC='#d8dce1'; ACRYL='#bfe3f5'; LEDC='#ff8c1a'; INK='#5a6069'

fig, (a, b) = plt.subplots(2, 1, figsize=(13.0, 10.4),
                           gridspec_kw={'height_ratios': [1.0, 1.5]})

# ---------------------------------------------------------------- section
a.set_title('Section through one light guide — the LED is at r = 82, the lit line '
            'runs to r = 110.5', fontsize=11)
def rect(ax,x0,x1,y0,y1,**k): ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,**k))
# base
rect(a, 60, 120, 0, Z_RING_FLOOR60, fc=PLASTIC, ec=INK, lw=.8)
rect(a, R_RING_I60, R_RING_O60, Z_RING_FLOOR60, GUIDE_SHELF, fc='none', ec=INK, lw=.6, ls=':')
rect(a, R_RING_O60, R_LIP_I60, Z_RING_FLOOR60, GUIDE_SHELF, fc=PLASTIC, ec=INK, lw=.8)
a.text((R_RING_O60+R_LIP_I60)/2, (Z_RING_FLOOR60+GUIDE_SHELF)/2, 'guide shelf',
       ha='center', va='center', fontsize=7.5, color=INK)
# the ring
rect(a, RING60_ID/2, RING60_OD/2, Z_RING_FLOOR60, Z_RING_FLOOR60+PCB_T, fc='#2c6e49', ec='#1b4332', lw=.8)
rect(a, RING60_R-2.5, RING60_R+2.5, Z_RING_FLOOR60+PCB_T, GUIDE_SHELF, fc=LEDC, ec='#9a4a00', lw=.8)
a.text(RING60_R, Z_RING_FLOOR60-1.6, 'LED', ha='center', fontsize=8, color='#9a4a00')
# the diffuser: face + channel walls
rect(a, 60, R_LIP_I60, Z_RECESS-FACE_T, Z_RECESS, fc='#f2f2ef', ec=INK, lw=.8)
a.text(66, Z_RECESS-FACE_T/2, 'face 2.00', ha='center', va='center', fontsize=7.5, color=INK)
# the strip
rect(a, GUIDE_RI, GUIDE_RO, GUIDE_SHELF, GUIDE_SHELF+GUIDE_T, fc=ACRYL, ec='#3f7f9c', lw=1.0)
a.text((GUIDE_RI+GUIDE_RO)/2, GUIDE_SHELF+GUIDE_T/2, 'perspex  6.00 x 3.00 x 25.5',
       ha='center', va='center', fontsize=8, color='#20536b')
# the aperture, tapering
a.plot([APER_RI, APER_RO], [Z_RECESS-DIFF_MEM_T]*2, color=LEDC, lw=2.2, solid_capstyle='butt')
a.annotate(f'aperture thinned to {DIFF_MEM_T:.2f} mm, widening '
           f'{APER_W_IN:.2f} -> {APER_W_OUT:.2f}',
           (APER_RO-6, Z_RECESS), (-40, 26), textcoords='offset points', fontsize=8,
           arrowprops=dict(arrowstyle='->', lw=.8))
# plywood
rect(a, 60, R_BODY60, Z_RECESS, Z_FRONT, fc='#e0d3ba', ec=INK, lw=.8)
a.text(66, (Z_RECESS+Z_FRONT)/2, '3 mm plywood', ha='center', va='center', fontsize=7.5, color=INK)
rect(a, R_LIP_I60, R_BODY60, 0, Z_RECESS, fc=PLASTIC, ec=INK, lw=.8)
for r_, lbl in ((RING60_R,'r 82'), (GUIDE_RI,'86.5'), (GUIDE_RO,'112'), (R_BODY60,'120')):
    a.plot([r_,r_], [-3,-1], color=INK, lw=.7); a.text(r_,-6.5,lbl,ha='center',fontsize=7.5,color=INK)
a.set_xlim(58, 126); a.set_ylim(-9, 30); a.set_aspect('equal'); a.axis('off')

# ---------------------------------------------------------------- face
b.set_facecolor('#14161a')
b.add_patch(Circle((0,0), R_BODY60, fc='#e8e4d9', ec='none', zorder=1))
b.add_patch(Circle((0,0), 64.0, fc='#14161a', ec='none', zorder=2))
LIT = {5:'#ff5a14', 23:'#1e78ff', 44:'#9a9a9a'}
for k in range(B.n):
    ang = 360.0/B.n*k
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    pts = [(APER_RI, -APER_W_IN/2), (APER_RO, -APER_W_OUT/2),
           (APER_RO, APER_W_OUT/2), (APER_RI, APER_W_IN/2)]
    P = [(u*ca - v*sa, u*sa + v*ca) for u, v in pts]
    on = k in LIT
    col = LIT.get(k, '#ddd8ca')
    for gr, al in ([(2.4,.12),(1.2,.24),(0.0,1.0)] if on else [(0.0,.34)]):
        b.add_patch(Polygon([(x*(1+gr/100), y*(1+gr/100)) for x,y in P],
                            closed=True, fc=col, alpha=al, ec='none',
                            zorder=3, lw=0))
# All twelve, in the viewer's frame -- see render_line.py
NR = BV.BODY60.num_r
for h in range(1, 13):
    ang = 90.0 - (h % 12)*30.0
    b.text(NR*math.cos(math.radians(ang)), NR*math.sin(math.radians(ang)),
           NUMERALS[h], ha='center', va='center', fontsize=11, color='#8d8778',
           zorder=6, weight='bold')
b.add_patch(Circle((0,0), DISP_ACTIVE_D/2, fc='#0b0d10', ec='#2a2e35', lw=1.0, zorder=7))
b.text(0, 3.5, '10:09', ha='center', va='center', fontsize=17, color='#dfe3ea', zorder=8)
b.set_xlim(-128,128); b.set_ylim(-128,128); b.set_aspect('equal'); b.axis('off')
b.set_title(f'{B.n} LEDs on a {2*B.r_body:.0f} mm face — each one reads '
            f'{APER_RO-APER_RI:.0f} mm long', fontsize=11, color='#1c1c1c')

fig.patch.set_facecolor('#f7f7f5')
fig.suptitle('The 60-LED clock: perspex strips make each LED read 30 mm long', fontsize=13.5)
fig.text(0.5, 0.012, 'Drawn from params.py. How far the light actually carries along '
         'a strip is the one thing here that needs a bench test, not a calculation.',
         ha='center', fontsize=8.5, color='#777')
fig.tight_layout()
fig.savefig('render_guides.png', dpi=110, bbox_inches='tight')
print('wrote render_guides.png')
