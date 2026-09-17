#!/usr/bin/env python3
"""The laser-cut plywood face for the 60-LED clock, and the coupon that tells
you how deep to engrave it.

Sam, 2026-09-16: "Make a file that I can laser cut wood for the front of the
60LED clock. With lines for the LED's to shine through. Those areas won't be
cut all the way through, but be recessed from the laser so light shines
through."

WHAT THIS REPLACES. On the 60 the white printed diffuser carries a 0.20 mm
membrane over each tick and a 6 mm cell wall between them: the membrane glows,
the wall is opaque. The plywood does the same job the same way round -- opaque
everywhere, thinned to about half a millimetre on the sixty lines -- except
that plywood is opaque to start with, so the cell walls are not needed to stop
light crossing between ticks. The wood IS the mask.

THE SEAT WAS ALREADY THERE. Measured on the built base-60 mesh: the front face
is at z = 22.00, the front bore is r = 116.50, and the screen collar's top face
is at z = 18.99 in a ring from r 30.65 to 35.10. That collar is the seat, it is
3.01 mm down, and a 3 mm sheet lands flush. `Z_RECESS` in params.py has said
"plywood face recess floor" since the first version of the file.

MIRRORING. The lines are engraved from the BACK, so the natural question is
whether the file has to be flipped. It does not, and that is a property worth
keeping rather than a coincidence: every feature here is symmetric about the
12-6 axis, so the drawing and its mirror image are the same drawing. The plain
face is 60-fold symmetric as well, which means any of the sixty rotations seats
it correctly. Do not add an asymmetric mark to this file without also deciding
which side it is drawn from.

Run:  python3 make_face_svg.py          -> laser/*.svg and laser/*.png
"""
import math, os, sys
sys.path.insert(0, '.')
from params import *
import build_v2 as BV

B = BV.BODY60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laser')

CUT   = '#FF0000'      # stroke only: cut through
ENG   = '#000000'      # filled: raster engrave
SCORE = '#0000FF'      # stroke only: score, marks only


# ---------------------------------------------------------------- geometry
def stadium(r0, r1, w, ang_deg, seg=16):
    """A radial slot with half-round ends, as an explicit polygon.

    Explicit, and not an SVG arc, on purpose: `A` takes a large-arc and a sweep
    flag whose sense depends on which way the y axis runs, and this file flips y
    on the way out. A polygon cannot be got subtly wrong -- and check11 measures
    the polygon that lands in the file, not the intent behind it.
    """
    h = w/2.0
    pts = [(r0, -h), (r1, -h)]
    for i in range(1, seg):                      # outer cap, -y round to +y
        a = -math.pi/2 + math.pi*i/seg
        pts.append((r1 + h*math.cos(a), h*math.sin(a)))
    pts.append((r1, h))
    pts.append((r0, h))
    for i in range(1, seg):                      # inner cap, +y round to -y
        a = math.pi/2 + math.pi*i/seg
        pts.append((r0 + h*math.cos(a), h*math.sin(a)))
    t = math.radians(ang_deg)
    c, s = math.cos(t), math.sin(t)
    return [(x*c - y*s, x*s + y*c) for (x, y) in pts]


def poly(pts, fill=None, stroke=None, layer=''):
    d = 'M ' + ' L '.join(f'{x:.4f},{-y:.4f}' for x, y in pts) + ' Z'   # y flipped
    a = f' fill="{fill}"' if fill else ' fill="none"'
    a += f' stroke="{stroke}" stroke-width="0.1"' if stroke else ''
    return f'<path d="{d}"{a} data-layer="{layer}" />'


def circle(r, fill=None, stroke=None, layer=''):
    a = f' fill="{fill}"' if fill else ' fill="none"'
    a += f' stroke="{stroke}" stroke-width="0.1"' if stroke else ''
    return f'<circle cx="0" cy="0" r="{r:.4f}"{a} data-layer="{layer}" />'


def document(body, w, h, title):
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.4f} {h:.4f}">'
            f'<title>{title}</title>'
            f'<g transform="translate({w/2:.4f},{h/2:.4f})">' + ''.join(body) +
            '</g></svg>\n')


# ---------------------------------------------------------------- the face
def face(hours=False, through=False):
    """The plywood face. `through` cuts the sixty lines out instead of
    engraving them, for the version whose lines are filled with printed plugs.

    Sam, 2026-09-17: "I will be cutting out the 60 lines instead of engraving."

    THE ORDER IS THE SAME AND IT MATTERS MORE, not less. Glowforge runs steps in
    the order it finds them, and every one of these operations needs the disc
    still attached to the sheet. Cut the outline first and the piece lifts,
    shifts, or catches the gantry -- and with sixty through-slots in it, the
    disc that is left is a lot more fragile than the engraved one was. Lines
    first, screen bore next, outline last.

    The lines are drawn at their TRUE width, 1.80. The beam takes its kerf off
    the part, so the hole comes out about 2.00 -- which is the number the plugs
    are built to, and the reason they are not drawn at 1.80 either.
    """
    r_out = B.r_lip_i - PLY_CLR
    parts = []
    for k in range(B.n):
        a = 90.0 - k*(360.0/B.n)          # k = 0 at 12 o'clock, clockwise
        w = PLY_HOUR_W if (hours and k % 5 == 0) else PLY_TICK_W
        pts = stadium(B.tick_ri, B.tick_ro, w, a)
        parts.append(poly(pts, stroke=CUT, layer='cut-ticks') if through
                     else poly(pts, fill=ENG, layer='engrave-ticks'))
    parts.append(circle(PLY_BORE_R, stroke=CUT, layer='cut-screen'))
    parts.append(circle(r_out,      stroke=CUT, layer='cut-outline'))
    d = 2*r_out + 2.0
    what = 'lines cut through' if through else 'lines engraved'
    return document(parts, d, d,
                    f'60-LED clock face - {PLY_T:.0f} mm plywood - '
                    f'{"hours emphasised" if hours else "plain"} - {what}')


# ---------------------------------------------------------------- the coupon
# A seven-segment digit, drawn as rectangles. No font, no text-to-path tool and
# nothing to go wrong between here and the laser: the label has to survive being
# engraved at a DIFFERENT depth from the patch it labels, so it is its own
# colour and its own shape rather than a string somebody's SVG renderer might
# substitute a font for.
# (x0, y0, x1, y1) as fractions of the digit's box. The first version of this
# had the three horizontal bars as x 0.5 -> 0.5, which is a rectangle of zero
# width: the digits came out as a few vertical ticks and were unreadable. The
# check passed anyway because it counted segments and never asked whether they
# had any area. Rendering it is what found it.
SEGS = {
    'a': (0.16, 0.84, 0.84, 1.00),   # top
    'g': (0.16, 0.42, 0.84, 0.58),   # middle
    'd': (0.16, 0.00, 0.84, 0.16),   # bottom
    'f': (0.00, 0.50, 0.16, 1.00),   # upper left
    'b': (0.84, 0.50, 1.00, 1.00),   # upper right
    'e': (0.00, 0.00, 0.16, 0.50),   # lower left
    'c': (0.84, 0.00, 1.00, 0.50),   # lower right
}
DIGIT = {0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc',
         5: 'afgcd', 6: 'afgecd', 7: 'abc', 8: 'abcdefg', 9: 'afgbcd'}


def digit(n, cx, cy, h):
    """One digit, centred on (cx, cy), h tall. Returns a list of polygons."""
    w = h * 0.62
    out = []
    for seg in DIGIT[n]:
        x0, y0, x1, y1 = SEGS[seg]
        # the fractions above are of a unit box laid out a..g; scale and place
        ax, ay = cx - w/2.0, cy - h/2.0
        out.append([(ax + x0*w, ay + y0*h), (ax + x1*w, ay + y0*h),
                    (ax + x1*w, ay + y1*h), (ax + x0*w, ay + y1*h)])
    return out


def coupon(n=5):
    """The real tick, at its real length, at n settings -- plus a 0 that is not
    engraved at all.

    Sam, 2026-09-17: "Create a small test cut to check the depth cut for the
    LED's to shine through."

    Each step is a PAIR: the 1.80 mm minute line and the 2.80 mm hour line. A
    wider slot glows brighter at the same depth, so a setting that is right for
    one can be wrong for the other, and testing only the narrow one is how you
    find that out after cutting a 232 mm disc.

    Every step is its own colour, so the laser gives each its own passes. The
    NUMERALS are a colour of their own too, engraved shallow and identically:
    a label that got deeper along with the patch it labels would be unreadable
    at exactly the setting you most want to identify.

    Column 0 is left bare on purpose. Wood that has not been touched is the
    only honest reference for "is this one glowing".
    """
    pitch = 13.0
    W = pitch * (n + 1) + 10.0
    tick_len = B.tick_ro - B.tick_ri            # the real 30.5 mm
    H = tick_len + 22.0
    cols = ['#FF00FF', '#00A0A0', '#804000', '#008000', '#606060', '#FF8000']
    parts = []
    ty = 3.0                                    # ticks centred a little high
    for i in range(n + 1):
        x = -W/2.0 + 5.0 + pitch*i + pitch/2.0
        if i:                                   # 0 is the bare reference
            c = cols[(i - 1) % len(cols)]
            for dx, w in ((-2.6, PLY_TICK_W), (2.6, PLY_HOUR_W)):
                pts = stadium(-tick_len/2.0, tick_len/2.0, w, 90.0)
                parts.append(poly([(x + dx + px, ty + py) for px, py in pts],
                                  fill=c, layer=f'engrave-test-{i}'))
        for g in digit(i, x, -H/2.0 + 7.0, 7.0):
            parts.append(poly(g, fill=ENG, layer='engrave-labels'))
    body = [(-W/2.0, -H/2.0), (W/2.0, -H/2.0), (W/2.0, H/2.0), (-W/2.0, H/2.0)]
    parts.append(poly(body, stroke=CUT, layer='cut-outline'))
    return document(parts, W + 2.0, H + 2.0,
                    f'Engrave depth coupon - {n} settings + a bare reference')


def slot_coupon(n=6):
    """The other half of the plug fit test: six REAL slots to press them into.

    A set of test plugs with nothing to test them in is half an experiment. Cut
    this from the same sheet, on the same settings, with the same lens -- then
    the kerf in it is the kerf in the face, which is the whole unknown.

    The slots are drawn at the true 1.80 like the face is, so the hole this
    leaves IS the hole the plugs meet. Numbered 1..6 to match the numbers on
    the plugs, though every slot is identical -- it is the PLUGS that differ,
    and the numbers are there so you can say which one went in.
    """
    tick_len = B.tick_ro - B.tick_ri
    pitch = 11.0
    W = pitch * n + 10.0
    H = tick_len + 22.0
    parts = []
    for i in range(n):
        x = -W/2.0 + 5.0 + pitch*i + pitch/2.0
        # engrave the number first -- the sheet must still be whole
        for g in digit(i + 1, x, -H/2.0 + 7.0, 7.0):
            parts.append(poly(g, fill=ENG, layer='engrave-labels'))
    for i in range(n):
        x = -W/2.0 + 5.0 + pitch*i + pitch/2.0
        pts = [(x + px, 3.0 + py)
               for px, py in stadium(-tick_len/2.0, tick_len/2.0,
                                     PLY_TICK_W, 90.0)]
        parts.append(poly(pts, stroke=CUT, layer='cut-slots'))
    parts.append(poly([(-W/2, -H/2), (W/2, -H/2), (W/2, H/2), (-W/2, H/2)],
                      stroke=CUT, layer='cut-outline'))
    return document(parts, W + 2.0, H + 2.0,
                    f'Plug fit test - {n} real {PLY_TICK_W:.2f} mm slots')


def number(n, cx, cy, h):
    """A multi-digit number, centred on (cx, cy)."""
    ds = [int(c) for c in str(n)]
    w = h * 0.62
    gap = w * 0.25
    total = len(ds) * w + (len(ds) - 1) * gap
    out = []
    for i, d in enumerate(ds):
        x = cx - total / 2.0 + w / 2.0 + i * (w + gap)
        out += digit(d, x, cy, h)
    return out


def centre_gauge(lo=52, hi=66, step=2):
    """A PAPER gauge for the one number that wasted a sheet.

    Sam, 2026-09-17: "The hole in the middle was too small for the 3D printed
    housing." The housing's diameter is a fact about his clock, not about this
    repo -- params only knows the screen collar is 59.90 and the display's PCB
    is 60.0, and neither is a promise about what is actually in there.

    Print on A4 AT 100% -- no "fit to page", and check the scale bar reads
    100 mm with a ruler before trusting anything else. Cut roughly round the
    outside, hold it over the middle of the clock, and read off the smallest
    circle the housing fits inside. That number rebuilds the face in one line.

    Costs a sheet of paper instead of a sheet of plywood.

    The labels are spread AROUND the circles, not stacked at twelve o'clock.
    The first version put every one at (0, r + 3.2) and the radii are only a
    millimetre apart, so all eight landed on top of each other and the gauge was
    unreadable -- found by rendering it, which is becoming a habit.
    """
    black = '#000000'
    parts, n = [], len(range(lo, hi + 1, step))
    for i, d in enumerate(range(lo, hi + 1, step)):
        parts.append(circle(d / 2.0, stroke=black, layer=f'gauge-{d}'))
        a = math.radians(100.0 + i * (150.0 / max(1, n - 1)))
        r = d / 2.0 + 4.0
        parts += [poly(g, fill=ENG, layer='engrave-labels')
                  for g in number(d, r * math.cos(a), r * math.sin(a), 4.5)]
    # A SCALE BAR, because a printer that quietly scales turns this into a
    # confident lie. 100.00 mm between the two end ticks.
    y = -hi / 2.0 - 14.0
    parts.append(poly([(-50.0, y), (50.0, y)], stroke=black, layer='gauge-scale'))
    for x in (-50.0, 50.0):
        parts.append(poly([(x, y - 3.0), (x, y + 3.0)], stroke=black,
                          layer='gauge-scale'))
    parts += [poly(g, fill=ENG, layer='engrave-labels')
              for g in number(100, 0.0, y - 8.0, 5.0)]
    W = 108.0                      # the scale bar is the widest thing on it
    H = 2.0 * (hi / 2.0 + 14.0 + 8.0 + 6.0)
    return document(parts, W, H,
                    'Centre-hole gauge - print at 100%, check the 100 mm bar')


def main():
    os.makedirs(OUT, exist_ok=True)
    files = {'face-60-wood.svg':             face(hours=False),
             'face-60-wood-hours.svg':       face(hours=True),
             # the cut-through pair, for the printed-plug build
             'face-60-wood-cut.svg':         face(hours=False, through=True),
             'face-60-wood-cut-hours.svg':   face(hours=True,  through=True),
             'face-60-depth-test.svg':       coupon(),
             'face-60-slot-test.svg':        slot_coupon(),
             'centre-hole-gauge.svg':        centre_gauge()}
    for name, svg in files.items():
        with open(os.path.join(OUT, name), 'w') as f:
            f.write(svg)
        print(f'  wrote laser/{name:26s} {len(svg):6d} bytes')
    r_out = B.r_lip_i - PLY_CLR
    print(f'\n  disc      {2*r_out:.2f} mm across, into a {2*B.r_lip_i:.2f} bore')
    print(f'  screen    {2*PLY_BORE_R:.2f} mm bore, active area is {DISP_ACTIVE_D:.1f}')
    print(f'  ticks     {B.n} x {PLY_TICK_W:.2f} wide, r {B.tick_ri:.1f} to {B.tick_ro:.1f}, '
          f'every {360.0/B.n:.0f} deg from 12 o\'clock')
    print(f'  thickness {PLY_T:.2f} nominal; the seat is {Z_FRONT - Z_RECESS:.2f} below the face')


if __name__ == '__main__':
    main()
