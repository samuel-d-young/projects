#!/usr/bin/env python3
"""The cabinet: a desk box with the clock in the top bay and a drawer under it.

    python cabinet.py            # both desk bodies: STLs, 3MFs, Glowforge SVGs
    python cabinet.py --only -32
    python check13_cabinet.py    # then prove it
    python render_cabinet.py     # then look at it

Every dimension is in params.py under THE CABINET. The clock itself is not
touched: it goes in as the base + diffuser + back cover already printed for
the stand-box, so its parts come from build_v2.py and nothing here rebuilds them.

World frame, for every part and every check: X across (right +), Y front to
back with the sleeve's front plane at Y = 0, Z up with the sleeve's underside
at Z = 0. Parts are built in that frame, checked in it, and only rotated into
print orientation on the way out to disk.

Parts, per body (tag "" = 24 LED, "-32" = 32 LED):

  cabinet-sleeve     black. BACK FACE DOWN. The whole box: walls, divider,
                     partitions, shelves, the clock's saddle, the board's rails,
                     the feet, and the closed back every drawer shuts against.
  cabinet-hatch      black. OUTSIDE FACE DOWN. The one removable panel: the back
                     of the clock's own bay, recessed into the back face.
  cabinet-drawer     black. OPEN SIDE UP, as it sits in the box.
  cabinet-pull       black. GRIP FACE DOWN.
  cabinet-fronts.svg 3 mm ply, Glowforge. The face panel and the drawer front,
                     laid out as they sit on the box so the grain runs on.
"""
import math, os, sys, argparse
import numpy as np
import trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csg
from csg import box_lwh, cyl, prism, Manifold
from params import *

SEG = 144
HERE = os.path.dirname(os.path.abspath(__file__))

# the stack the clock brings with it, in its own frame (+z = front, +x = 12)
CLOCK_Z_FRONT = Z_FRONT                                            # 22.00
CLOCK_Z_BACK  = Z_DECK - (BACKCOVER_PLATE + BACKCOVER_POCKET)      # -11.30
CLOCK_DEPTH   = CLOCK_Z_FRONT - CLOCK_Z_BACK                       # 33.30

BODIES = {
    '':    dict(n=24, r_body=R_BODY,   r_lip_i=R_LIP_I),
    '-32': dict(n=32, r_body=R_BODY32, r_lip_i=R_LIP_I32),
    '-60': dict(n=60, r_body=R_BODY60, r_lip_i=R_LIP_I60),
}


# ------------------------------------------------------------------ primitives
def rrect4(x0, x1, z0, z1, r_top, r_bot, seg=16):
    """A rectangle with its top pair and bottom pair of corners radiused
    separately, as a CCW (x, z) point list."""
    return rrect_r(x0, x1, z0, z1, r_top, r_top, r_bot, r_bot, seg)


def rrect_r(x0, x1, z0, z1, r_tr, r_tl, r_bl, r_br, seg=16):
    """The same, with every corner its own radius -- a side bay is round only
    where it meets the sleeve's own corner. Order is top-right, top-left,
    bottom-left, bottom-right; a radius under 0.05 is a square corner."""
    pts = []
    lim = lambda r: min(r, (x1 - x0) / 2 - 0.01, (z1 - z0) / 2 - 0.01)
    r_tr, r_tl, r_bl, r_br = (lim(r) for r in (r_tr, r_tl, r_bl, r_br))
    for cx, cz, r, a0 in ((x1 - r_tr, z1 - r_tr, r_tr, 0),
                          (x0 + r_tl, z1 - r_tl, r_tl, 90),
                          (x0 + r_bl, z0 + r_bl, r_bl, 180),
                          (x1 - r_br, z0 + r_br, r_br, 270)):
        if r < 0.05:
            pts.append(({0: x1, 90: x0, 180: x0, 270: x1}[a0],
                        {0: z1, 90: z1, 180: z0, 270: z0}[a0]))
        else:
            for k in range(seg + 1):
                a = math.radians(a0 + 90.0 * k / seg)
                pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def xz_prism(pts, y0, y1):
    """A profile drawn in the front view (x, z), extruded front to back."""
    return prism(pts, -y1, -y0).rotate([90.0, 0.0, 0.0])


def yz_prism(pts, x0, x1):
    """A profile drawn in the side view (y, z), extruded across."""
    return prism(pts, x0, x1).transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], float))


def ycyl(r, x, z, y0, y1, seg=48):
    """A cylinder along Y."""
    return xz_prism(circle(r, x, z, seg), y0, y1)


def circle(r, cx, cz, seg=SEG):
    return [(cx + r * math.cos(2 * math.pi * k / seg), cz + r * math.sin(2 * math.pi * k / seg))
            for k in range(seg)]


# ------------------------------------------------------------------ the frame
class Frame:
    """Every number the parts have to agree on, worked out once. Parts are built
    from this and never from each other."""

    def __init__(self, tag):
        b = BODIES[tag]
        self.tag, self.n = tag, b['n']
        self.r_body, self.r_lip_i = b['r_body'], b['r_lip_i']
        T, R = CAB_WALL, self.r_body

        self.h_clock = 2 * R + 2 * CAB_GAP             # CAB_GAP above and below
        self.H = 2 * T + CAB_DRAWER_H + CAB_DIV_T + self.h_clock
        self.w_in = max(self.h_clock, CAB_ASPECT * self.H - 2 * T)
        self.W = self.w_in + 2 * T
        self.r_in = CAB_R_OUT - T                      # inner corner radius

        # z levels
        self.z_dr0 = T                                 # drawer bay floor
        self.z_dr1 = T + CAB_DRAWER_H                  # drawer bay ceiling
        self.z_cf = self.z_dr1 + CAB_DIV_T             # clock bay floor
        self.z_ct = self.z_cf + self.h_clock           # clock bay ceiling

        # the clock: saddle axis, and where the clock actually rests on the arcs
        self.rs = R + CAB_SADDLE_CLR
        self.z_saddle = self.z_cf + CAB_GAP + R
        a0 = math.radians(CAB_SADDLE_A0)
        # centre drop d so the clock circle passes through the arc at A0:
        #   rs^2 - 2 d rs cos(a0) + d^2 = R^2
        c = self.rs * math.cos(a0)
        self.drop = c - math.sqrt(c * c - (self.rs ** 2 - R ** 2))
        self.z_clock = self.z_saddle - self.drop

        # y levels, front to back
        self.y_ply0 = CAB_RECESS
        self.y_ply1 = CAB_RECESS + PLY_T
        self.y_clock_f = self.y_ply1 + CAB_AIR
        self.y_clock_b = self.y_clock_f + CLOCK_DEPTH
        self.y_lip0 = self.y_clock_b + CAB_LIP_CLR
        self.y_lip1 = self.y_lip0 + CAB_LIP_T
        # the rear lip's own ramp, which runs back from it down to the floor:
        # its length is the lip's height, so the slope is 45 degrees
        self.h_lip = (self.z_saddle + CAB_LIP_V) - math.sqrt(max(
            self.rs ** 2 - (self.rs * math.sin(math.radians(CAB_SADDLE_A1))) ** 2, 0.0))             - (self.z_cf - 0.6)
        self.y_ramp1 = self.y_lip1 + self.h_lip + 0.2
        # the board starts behind the LIP, not behind the ramp: the ramp is cut
        # away over the board's lane, so the two share that depth
        self.y_bstop0 = self.y_lip1 + CAB_LEAD_ROOM
        self.y_bstop1 = self.y_bstop0 + CAB_BSTOP_L
        self.y_board0 = self.y_bstop1 + CAB_STOP_GAP
        self.y_board1 = self.y_board0 + BOARD2_L

        self.D = CAB_DEPTH
        self.y_wall = self.D - CAB_BACK_T               # inside of the closed back
        self.y_hatch1 = self.D - CAB_HATCH_INSET        # the hatch, outside face
        self.y_hatch0 = self.y_hatch1 - CAB_HATCH_T     # ...and its seat
        need = self.y_board1 + HOUSING_S3_USB_GAP + CAB_HATCH_T + CAB_HATCH_INSET
        self.depth_needed = need
        assert self.D >= need - 1e-9, (
            f'{tag or "24"}: CAB_DEPTH {self.D:.2f} is short of the {need:.2f} the '
            f'clock + board stack needs')
        # the board is pushed back to the hatch, USB_GAP off it
        slack = self.y_hatch0 - HOUSING_S3_USB_GAP - self.y_board1
        self.y_board0 += slack
        self.y_board1 += slack
        self.y_bstop0 += slack
        self.y_bstop1 += slack

        self.aper_r = self.r_lip_i + CAB_APER_CLR
        self.pull_L = round(CAB_PULL_FRAC * self.W / 2.0) * 2.0
        self.pull_x = self.pull_L / 2 - CAB_PULL_H / 2      # leg centres, |x|
        self.z_pull = (self.z_dr0 + self.z_dr1) / 2

        # --- the side bays: whatever the aspect leaves either side of the clock
        self.side_w = (self.w_in - self.h_clock) / 2 - CAB_PART_T
        self.sides = self.side_w >= CAB_SIDE_MIN
        # the centre bay is the clock's own square when there are side drawers,
        # and the whole width when there are not
        self.cw = self.h_clock if self.sides else self.w_in
        self.x_part_i = self.cw / 2                          # partition, inner face
        self.x_part_o = self.cw / 2 + CAB_PART_T             # ...and outer
        self.x_side_c = (self.x_part_o + self.w_in / 2) / 2  # side bay centre
        self.side_pull_L = max(20.0, round(CAB_SIDE_PULL * self.side_w / 2.0) * 2.0)
        self.side_pull_x = self.side_pull_L / 2 - CAB_PULL_H / 2
        # the rows: as many as CAB_SIDE_ROWS asks for, while each is worth a
        # drawer, with a shelf between them
        self.side_rows = max(1, int(CAB_SIDE_ROWS))
        while self.side_rows > 1:
            h = (self.h_clock - (self.side_rows - 1) * CAB_SIDE_SHELF) / self.side_rows
            if h >= CAB_SIDE_ROW_MIN:
                break
            self.side_rows -= 1
        self.side_row_h = (self.h_clock - (self.side_rows - 1) * CAB_SIDE_SHELF) / self.side_rows
        self.side_z = [(self.z_cf + r * (self.side_row_h + CAB_SIDE_SHELF),
                        self.z_cf + r * (self.side_row_h + CAB_SIDE_SHELF) + self.side_row_h)
                       for r in range(self.side_rows)]

    # the clock's own frame -> world. +x (12 o'clock) up, +z (front) to -Y.
    def clock_matrix(self):
        ty = self.y_clock_f + CLOCK_Z_FRONT
        return np.array([[0, -1, 0, 0],
                         [0, 0, -1, ty],
                         [1, 0, 0, self.z_clock],
                         [0, 0, 0, 1]], dtype=float)

    def fits_bed(self):
        return max(self.W, self.H + CAB_FEET_H, self.D) <= CAB_BED


# ------------------------------------------------------------------ the sleeve
def _saddle_profile(F, centre_z, radius, side):
    """The region under an arc of the clock circle, between A0 and A1, down to
    below the bay floor -- one side (side = +1 right, -1 left)."""
    a0, a1 = math.radians(CAB_SADDLE_A0), math.radians(CAB_SADDLE_A1)
    x0 = F.rs * math.sin(a0)
    x1 = F.rs * math.sin(a1)
    zf = F.z_cf - 0.6
    pts = [(x0, zf)]
    n = 40
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        pts.append((x, centre_z - math.sqrt(max(radius * radius - x * x, 0.0))))
    pts.append((x1, zf))
    return [(side * x, z) for x, z in pts]


def build_sleeve(F):
    T, c = CAB_WALL, CAB_EDGE_CHAMF
    W, H, D = F.W, F.H, F.D
    xw = F.w_in / 2

    def outer(inset, y0, y1):
        return xz_prism(rrect4(-W / 2 + inset, W / 2 - inset, inset, H - inset,
                               CAB_R_OUT - inset, CAB_R_OUT - inset), y0, y1)
    s = (outer(c, 0.0, 0.01) + outer(0.0, c, D - c)).hull()
    s = (s + (outer(0.0, c, D - c) + outer(c, D - 0.01, D)).hull())

    # the bays, straight through front to back. With side drawers the clock's
    # bay is its own square between two partitions, and each side bay is round
    # only in the corner it shares with the sleeve.
    # Every drawer bay stops at the back wall, which is part of the sleeve and
    # is what those drawers close against. Only the clock's bay runs right
    # through: the hatch closes it, recessed into the back face.
    r_c = 0.0 if F.sides else F.r_in
    y_wall = D - CAB_BACK_T
    clock_bay = xz_prism(rrect4(-F.cw / 2, F.cw / 2, F.z_cf, F.z_ct, r_c, 0.0), -1.0, D + 1.0)
    drawer_bay = xz_prism(rrect4(-xw, xw, F.z_dr0, F.z_dr1, 0.0, F.r_in), -1.0, y_wall)
    s = s - clock_bay - drawer_bay
    if F.sides:
        for sx in (1, -1):
            for row in range(F.side_rows):
                s = s - xz_prism(side_bay_outline(F, sx, row), -1.0, y_wall)

    # ---- the clock saddle
    # Printed back face down, the saddle's own rear face would be the overhang,
    # so the 45 degree ramp is BEHIND the lip: material runs back from the lip
    # and down to the floor. It never stands above the lip, which is the height
    # the clock passes at on its way in, so it costs nothing on the journey.
    saddle = None
    lip = None
    ramp = None
    h_lip = F.h_lip
    for side in (1, -1):
        p = xz_prism(_saddle_profile(F, F.z_saddle, F.rs, side), F.y_ply1, F.y_lip0)
        q = xz_prism(_saddle_profile(F, F.z_saddle + CAB_LIP_V, F.rs, side), F.y_lip0, F.y_lip1)
        # started at the lip's own front face, not its back, so the two solids
        # OVERLAP: meeting on a plane leaves coincident faces, and float32
        # turns those into a hundred zero-volume shells
        w = xz_prism(_saddle_profile(F, F.z_saddle + CAB_LIP_V, F.rs, side),
                     F.y_lip0, F.y_ramp1)
        saddle = p if saddle is None else saddle + p
        lip = q if lip is None else lip + q
        ramp = w if ramp is None else ramp + w
    y_r = F.y_ramp1
    wedge = yz_prism([(F.y_lip0 - 1.0, F.z_cf - 1.0),
                      (F.y_lip0 - 1.0, F.z_cf - 0.6 + (y_r - F.y_lip0) + 1.0),
                      (y_r, F.z_cf - 0.6), (y_r, F.z_cf - 1.0)], -W, W)
    # The lip and its ramp keep out of the board's lane: at 6 o'clock the two
    # arcs start at |x| 13 and the board is 30 wide. The LIP goes too, not just
    # the ramp -- leave the lip standing there and its own back face is an
    # overhang with nothing behind it, which is what check13 measured. It still
    # runs from |x| 17 out to 41 on both sides, which is all the stop the clock
    # needs.
    # 1.50 of clearance each side of the board, not 2.00: the strip of saddle
    # left standing between the lane and where the arcs start at |x| 13 is the
    # widest overhang on the part, and on the 24 body 2.00 made it 3.55 mm
    lane = box_lwh(-BOARD2_W / 2 - 1.5, BOARD2_W / 2 + 1.5, F.y_lip0 - 1.0, y_r + 1.0,
                   F.z_cf - 1.0, F.z_cf + BOARD2_H + 2.0)
    s = s + saddle + (lip - lane) + ((ramp ^ wedge) - lane)

    # ---- panel stop tabs: two on each side wall, two on the ceiling
    ys0, ys1 = F.y_ply1, F.y_ply1 + CAB_STOP_L
    hw = CAB_STOP_W / 2
    for sx in (1, -1):
        for dz in (-0.45 * F.r_body, 0.45 * F.r_body):
            zc = F.z_clock + dz
            x_in, x_out = F.cw / 2 - CAB_STOP_T, F.cw / 2 + 0.5
            s = s + box_lwh(min(sx * x_in, sx * x_out), max(sx * x_in, sx * x_out),
                            ys0, ys1, zc - hw, zc + hw)
        xc = sx * 0.5 * F.r_body
        s = s + box_lwh(xc - hw, xc + hw, ys0, ys1, F.z_ct - CAB_STOP_T, F.z_ct + 0.5)

    # ---- board rails and end stop, on the clock bay floor
    rail_h = CAB_TAPE + BOARD_T + CAB_RAIL_OVER
    sw = HOUSING_S3_SLOT_W / 2
    for sx in (1, -1):
        x0, x1 = sorted((sx * sw, sx * (sw + CAB_RAIL_T)))
        s = s + box_lwh(x0, x1, F.y_board0, F.y_board1, F.z_cf - 0.5, F.z_cf + rail_h)
    s = s + box_lwh(-sw - CAB_RAIL_T, sw + CAB_RAIL_T, F.y_bstop0, F.y_bstop1,
                    F.z_cf - 0.5, F.z_cf + rail_h)


    # ---- the hatch's rebate: a 45 degree funnel from the back face in to the
    # seat it lands on. The seat cannot be a plain ledge -- printed back face
    # down, a ledge is a flat 4.5 mm overhang standing over the opening -- so
    # the rebate tapers instead, and what you see around the hatch is a
    # chamfer. It stops short of the board's lane, or the board could not slide
    # in over the floor.
    bay = rrect4(-F.cw / 2, F.cw / 2, F.z_cf, F.z_ct, r_c, 0.0)
    inset = rrect4(-F.cw / 2 + CAB_HATCH_LEDGE, F.cw / 2 - CAB_HATCH_LEDGE,
                   F.z_cf + CAB_HATCH_LEDGE, F.z_ct - CAB_HATCH_LEDGE,
                   max(r_c - CAB_HATCH_LEDGE, 0.0), 0.0)
    seat_d = CAB_BOSS_L                      # the seat runs forward this far, so
                                             # it overlaps the bosses rather than
                                             # meeting them on a plane
    funnel = (xz_prism(inset, F.y_hatch0 - seat_d, F.y_hatch0)
              + (xz_prism(inset, F.y_hatch0, F.y_hatch0 + 0.01)
                 + xz_prism(bay, D - 0.01, D)).hull())
    ring = xz_prism(bay, F.y_hatch0 - seat_d, D) - funnel
    ring = ring - box_lwh(-BOARD2_W / 2 - 6.0, BOARD2_W / 2 + 6.0,
                          F.y_hatch0 - seat_d - 1.0, D + 1.0,
                          F.z_cf - 1.0, F.z_cf + CAB_HATCH_LEDGE + 1.0)
    s = s + ring

    # ---- bosses for the hatch's four screws, in the clock bay's corners.
    # Printed back face down there is nothing under a boss -- the opening the
    # hatch sits in is under it -- so each one tapers back to its own corner on
    # a 45 degree cone, and the screw passes through the cone into the pilot.
    # Built AFTER the rebate, or the rebate's seat would fill the pilots.
    for (bx, bz, wall_pt) in boss_points(F):
        cone = math.hypot(bx - wall_pt[0], bz - wall_pt[1]) + CAB_BOSS_R
        y_c0 = F.y_hatch0 - cone
        boss = (ycyl(CAB_BOSS_R, bx, bz, y_c0 - CAB_BOSS_L, y_c0, 40)
                + xz_prism(circle(0.4, wall_pt[0], wall_pt[1], 12),
                           F.y_hatch0 - 0.2, F.y_hatch0)).hull()
        s = s + boss
        s = s - ycyl(CAB_PILOT_D / 2, bx, bz, y_c0 - CAB_BOSS_L + 1.0, F.y_hatch0 + 1.0, 24)

    # ---- feet: two rails under the floor, 45 degree ends
    fx = W / 2 - CAB_R_OUT - CAB_FEET_W / 2 - 2.0
    fy0, fy1, fh = CAB_FEET_IN, D - CAB_FEET_IN, CAB_FEET_H
    foot = [(fy0, 0.5), (fy0 + fh + 0.5, -fh), (fy1 - fh - 0.5, -fh), (fy1, 0.5)]
    for sx in (1, -1):
        s = s + yz_prism(foot, sx * fx - CAB_FEET_W / 2, sx * fx + CAB_FEET_W / 2)
    return s


def boss_points(F):
    """(x, z, a point on the wall the boss grows from) for the four screws.

    With side drawers all four sit in the CENTRE bay's corners -- on the
    partitions, the ceiling and the divider. The sleeve's own rounded corners
    are inside the side bays now, and a boss there would block a drawer."""
    if F.sides:
        # halfway along the top and bottom edges, not in the corners: each boss
        # reaches its wall on a 45 degree cone, and a cone off a corner is
        # sqrt(2) longer -- which the screw has to cross before it bites
        out = []
        for sx in (1, -1):
            for z, zw in ((F.z_ct - CAB_BOSS_IN, F.z_ct + 0.6),
                          (F.z_cf + CAB_BOSS_IN, F.z_cf - 0.6)):
                out.append((sx * F.cw / 4, z, (sx * F.cw / 4, zw)))
        return out
    xw = F.w_in / 2
    out = []
    k = F.r_in - CAB_BOSS_IN
    for sx in (1, -1):
        # top corner: on the diagonal of the inner corner arc
        cx, cz = sx * (xw - F.r_in), F.z_ct - F.r_in
        d = (sx * math.cos(math.radians(45)), math.sin(math.radians(45)))
        out.append((cx + k * d[0], cz + k * d[1],
                    (cx + (F.r_in + 0.8) * d[0], cz + (F.r_in + 0.8) * d[1])))
        # on the divider, in the square corner
        out.append((sx * (xw - CAB_BOSS_IN), F.z_cf + CAB_BOSS_IN,
                    (sx * (xw + 0.6), F.z_cf - 0.6)))
    return out


# ------------------------------------------------------------------ the hatch
def _grow(pts, d):
    """Push a closed polygon out by d, mitred -- the hatch's 45 degree edge."""
    from shapely.geometry import Polygon
    return list(Polygon(pts).buffer(d, join_style=2).exterior.coords)[:-1]


def hatch_outline(F):
    """The only removable panel: the back of the clock's own bay, sitting in
    the rebate. Every other bay is closed by the sleeve itself."""
    r_c = 0.0 if F.sides else F.r_in
    g = CAB_HATCH_LEDGE + CAB_BACK_CLR
    return rrect4(-F.cw / 2 + g, F.cw / 2 - g, F.z_cf + g, F.z_ct - g,
                  max(r_c - g, 0.0), 0.0)


def boss_axis(F):
    """Where each hatch screw actually threads: (x, z, thread start, thread end).
    The boss reaches its corner on a 45 degree cone, so the thread begins that
    cone's length in front of the hatch's seat."""
    out = []
    for (bx, bz, wall_pt) in boss_points(F):
        cone = math.hypot(bx - wall_pt[0], bz - wall_pt[1]) + CAB_BOSS_R
        y_c0 = F.y_hatch0 - cone
        out.append((bx, bz, y_c0 - CAB_BOSS_L, y_c0))
    return out


def build_hatch(F):
    """A plug, not a plate: its edge is chamfered 45 degrees to match the
    rebate's taper, so it centres itself and cannot fall through. A straight
    edged plate small enough to pass the rebate's narrow end has nothing to
    land on -- check13 caught that before this was printed."""
    y0, y1 = F.y_hatch0, F.y_hatch1
    out = hatch_outline(F)
    # the rebate's taper is not 45 degrees -- it runs CAB_HATCH_LEDGE out over
    # the CAB_HATCH_INSET + CAB_HATCH_T it has to do it in -- and the hatch's
    # edge matches THAT, or its back corner digs into the rebate's wall
    k = CAB_HATCH_LEDGE / (F.D - F.y_hatch0)
    p = (xz_prism(out, y0, y0 + 0.01)
         + xz_prism(_grow(out, CAB_HATCH_T * k), y1 - 0.01, y1)).hull()
    for (bx, bz, _) in boss_points(F):
        p = p - ycyl(SCREW_CLEAR / 2 + 0.1, bx, bz, y0 - 1, y1 + 1, 32)
        # 90 degree countersink from the outside face (the bed face as printed)
        p = p - countersink(bx, bz, y1)
    # the USB-C window, on the board's axis
    zc = F.z_cf + 0.2
    p = p - box_lwh(-HOUSING_S3_USB_W / 2, HOUSING_S3_USB_W / 2, y0 - 1, y1 + 1,
                    zc, zc + HOUSING_S3_USB_H)
    # vents, high in the clock bay
    vw = 0.30 * F.cw
    for i in range(CAB_VENTS):
        z = F.z_cf + 0.62 * F.h_clock + i * 2.4 * CAB_VENT_H
        p = p - xz_prism(rrect4(-vw, vw, z, z + CAB_VENT_H, CAB_VENT_H / 2 - 0.01,
                                CAB_VENT_H / 2 - 0.01, 6), y0 - 1, y1 + 1)
    return p


def countersink(x, z, y_face):
    r_head, r_hole = 3.20, SCREW_CLEAR / 2 + 0.1
    depth = r_head - r_hole
    top = xz_prism(circle(r_head, x, z, 32), y_face - 0.001, y_face + 0.5)
    bot = xz_prism(circle(r_hole, x, z, 32), y_face - depth - 0.001, y_face - depth)
    return (top + bot).hull()


# ------------------------------------------------------------------ drawer
def drawer_outline(F):
    """The drawer box seen from the front, as (x, z) points: square top, and a
    chord across each bottom corner where the bay is round -- from the point
    where the bay's arc leaves the side wall (less CAB_DR_SIDE_CLR) to the
    point where it meets the floor. A chord lies inside the arc, so it cannot
    touch it, and at ~46 degrees it prints: the drawer goes on the bed open side
    up, and a round bottom corner would start as a 2.5 mm overhang on its
    second layer. The gap under the chord is hidden behind the wood front."""
    xw = F.w_in / 2 - CAB_DR_SIDE_CLR
    cx, cz = F.w_in / 2 - F.r_in, F.z_dr0 + F.r_in      # the bay's corner centre
    z0, z1 = F.z_dr0, F.z_dr1 - CAB_DR_TOP_CLR
    # the floor end comes in by the side clearance too: at x = cx the bay's arc
    # is tangent to the floor, so a corner exactly there has no sideways play
    xb = cx - CAB_DR_SIDE_CLR
    return [(xw, z1), (-xw, z1), (-xw, cz), (-xb, z0), (xb, z0), (xw, cz)]


def build_drawer(F):
    from shapely.geometry import Polygon
    y0 = F.y_ply1
    y1 = F.y_wall                             # closed, it stops on the back wall
    out = drawer_outline(F)
    d = xz_prism(out, y0, y1)
    w = CAB_DR_WALL
    inner = list(Polygon(out).buffer(-w, join_style=2).exterior.coords)[:-1]
    top = max(z for _, z in inner)
    z_floor = F.z_dr0 + CAB_DR_FLOOR
    inner = [(x, top + 5.0) if abs(z - top) < 1e-6 else
             (x, z_floor) if z < F.z_dr0 + w + 1e-6 else (x, z) for x, z in inner]
    hollow = xz_prism(inner, y0 + CAB_DR_FRONT_T, y1 - w)
    d = d - hollow
    for sx in (1, -1):
        d = d - ycyl(SCREW_CLEAR / 2 + 0.1, sx * F.pull_x, F.z_pull, y0 - 1, y0 + CAB_DR_FRONT_T + 1, 32)
    return d


def build_pull(F, L=None, z=None, leg_x=None, xc=0.0):
    """A bar on two legs. The same part, shorter, is the side drawers' pull."""
    yf = F.y_ply0                                  # the wood's face
    yb1 = yf - CAB_PULL_STAND                      # grip's back face
    yb0 = yb1 - CAB_PULL_D                         # grip's front face
    L = F.pull_L if L is None else L
    z = F.z_pull if z is None else z
    leg_x = F.pull_x if leg_x is None else leg_x
    h = CAB_PULL_H
    grip = xz_prism(rrect4(xc - L / 2, xc + L / 2, z - h / 2, z + h / 2,
                           h / 2 - 0.01, h / 2 - 0.01, 16), yb0, yb1)
    legs = None
    for sx in (1, -1):
        leg = ycyl(h / 2, xc + sx * leg_x, z, yb1 - 0.5, yf, 48)
        legs = leg if legs is None else legs + leg
    p = grip + legs
    for sx in (1, -1):
        p = p - ycyl(CAB_PILOT_D / 2, xc + sx * leg_x, z, yf - CAB_PULL_PILOT, yf + 1, 24)
    return p


# ------------------------------------------------------------------ side drawers
def side_instances(F):
    """Every side drawer in the box: which side, which row, and the names its
    three files carry. cabinet.py, check13 and the renderer all read the box's
    side drawers from here, so none of them can disagree about how many there
    are or where they sit."""
    out = []
    for sx, s in ((1, 'r'), (-1, 'l')):
        for row in range(F.side_rows):
            rn = row + 1
            out.append(dict(sx=sx, side=s, row=row, top=(row == F.side_rows - 1),
                            z0=F.side_z[row][0], z1=F.side_z[row][1],
                            z_pull=sum(F.side_z[row]) / 2,
                            drawer=f'-drawer-side-{s}{rn}', ply=f'-side-ply-{s}{rn}',
                            pull=f'-pull-side-{s}{rn}'))
    return out


def side_bay_outline(F, sx, row):
    """One side bay row, as (x, z) points: round only in the corner it shares
    with the sleeve's own top corner, which only the top row touches."""
    x_i, x_o = F.x_part_o, F.w_in / 2
    z0, z1 = F.side_z[row]
    r = F.r_in if row == F.side_rows - 1 else 0.0
    pts = rrect_r(x_i, x_o, z0, z1, r, 0.0, 0.0, 0.0)
    return [(sx * x, z) for x, z in pts]


def side_drawer_outline(F, sx, row):
    """One side drawer box, seen from the front. In the top row the bay's outer
    corner is round, so that corner is a chord: it lies inside the arc and,
    with the drawer printed open side up, it is at the TOP, where nothing
    overhangs. Every row below is a plain rectangle."""
    g = CAB_DR_SIDE_CLR
    x_i, x_o = F.x_part_o + g, F.w_in / 2 - g
    z0, z1 = F.side_z[row][0], F.side_z[row][1] - CAB_DR_TOP_CLR
    if row < F.side_rows - 1:
        pts = [(x_i, z0), (x_o, z0), (x_o, z1), (x_i, z1)]
    else:
        cx, cz = F.w_in / 2 - F.r_in, F.z_ct - F.r_in    # the bay's corner centre
        pts = [(x_i, z0), (x_o, z0), (x_o, cz), (min(cx, x_o - g), z1), (x_i, z1)]
    return [(sx * x, z) for x, z in pts]


def build_side_drawer(F, sx, row):
    from shapely.geometry import Polygon
    y0 = F.y_ply1
    y1 = F.y_wall                                       # it stops on the back wall
    z_bay = F.side_z[row][0]
    out = side_drawer_outline(F, sx, row)
    d = xz_prism(out, y0, y1)
    w = CAB_DR_WALL
    inner = list(Polygon(out).buffer(-w, join_style=2).exterior.coords)[:-1]
    top = max(z for _, z in inner)
    z_floor = z_bay + CAB_DR_FLOOR
    inner = [(x, top + 5.0) if abs(z - top) < 1e-6 else
             (x, z_floor) if z < z_bay + w + 1e-6 else (x, z) for x, z in inner]
    d = d - xz_prism(inner, y0 + CAB_DR_FRONT_T, y1 - w)
    z_pull = sum(F.side_z[row]) / 2
    for s2 in (1, -1):
        d = d - ycyl(SCREW_CLEAR / 2 + 0.1, sx * F.x_side_c + s2 * F.side_pull_x,
                     z_pull, y0 - 1, y0 + CAB_DR_FRONT_T + 1, 32)
    return d


# ------------------------------------------------------------------ wood
def face_panel_outline(F):
    xw = F.cw / 2 - CAB_REVEAL
    r = 0.3 if F.sides else F.r_in - CAB_REVEAL
    return rrect4(-xw, xw, F.z_cf + CAB_REVEAL, F.z_ct - CAB_REVEAL, r, 0.3)


def side_front_outline(F, sx, row):
    """One side drawer's wood front: in the top row, round where it meets the
    sleeve's corner and square everywhere else, so left and right are mirror
    images; below that, a plain rectangle."""
    x_i, x_o = F.x_part_o + CAB_REVEAL, F.w_in / 2 - CAB_REVEAL
    z0, z1 = F.side_z[row]
    r = F.r_in - CAB_REVEAL if row == F.side_rows - 1 else 0.3
    pts = rrect_r(x_i, x_o, z0 + CAB_REVEAL, z1 - CAB_REVEAL, r, 0.3, 0.3, 0.3)
    return [(sx * x, z) for x, z in pts]


def build_side_front(F, sx, row):
    p = xz_prism(side_front_outline(F, sx, row), F.y_ply0, F.y_ply1)
    z_pull = sum(F.side_z[row]) / 2
    for s2 in (1, -1):
        p = p - ycyl(SCREW_CLEAR / 2 + 0.1, sx * F.x_side_c + s2 * F.side_pull_x,
                     z_pull, F.y_ply0 - 1, F.y_ply1 + 1, 32)
    return p


def drawer_front_outline(F):
    xw = F.w_in / 2 - CAB_REVEAL
    return rrect4(-xw, xw, F.z_dr0 + CAB_REVEAL, F.z_dr1 - CAB_REVEAL, 0.3,
                  F.r_in - CAB_REVEAL)


def build_face_panel(F):
    return (xz_prism(face_panel_outline(F), F.y_ply0, F.y_ply1)
            - xz_prism(circle(F.aper_r, 0.0, F.z_clock), F.y_ply0 - 1, F.y_ply1 + 1))


def build_drawer_front(F):
    p = xz_prism(drawer_front_outline(F), F.y_ply0, F.y_ply1)
    for sx in (1, -1):
        p = p - ycyl(SCREW_CLEAR / 2 + 0.1, sx * F.pull_x, F.z_pull, F.y_ply0 - 1, F.y_ply1 + 1, 32)
    return p


def _offset(pts, d):
    """Grow a closed polygon by d (negative shrinks), via shapely."""
    from shapely.geometry import Polygon
    g = Polygon(pts).buffer(d, join_style=2 if d < 0 else 1, resolution=16)
    return list(g.exterior.coords)[:-1]


def write_svg(F, path):
    """Both fronts on one sheet, stacked as they sit on the box, so the grain
    runs on from the face panel into the drawer front. Real-world scale,
    red = cut. Outlines grow by half the kerf, holes shrink by half."""
    k = PLY_KERF / 2
    margin = 5.0
    parts = []
    # sheet coordinates: x right, y DOWN. World z flips.
    x_off = F.W / 2 + margin
    z_top = F.z_ct + margin
    def tr(pts):
        return [(x + x_off, z_top - z) for x, z in pts]
    parts.append(('outline', tr(_offset(face_panel_outline(F), +k))))
    parts.append(('hole', tr(_offset(circle(F.aper_r, 0.0, F.z_clock, 360), -k))))
    parts.append(('outline', tr(_offset(drawer_front_outline(F), +k))))
    for sx in (1, -1):
        parts.append(('hole', tr(_offset(circle(SCREW_CLEAR / 2 + 0.1, sx * F.pull_x, F.z_pull, 48), -k))))
    if F.sides:
        for inst in side_instances(F):
            parts.append(('outline', tr(_offset(
                side_front_outline(F, inst['sx'], inst['row']), +k))))
            for s2 in (1, -1):
                parts.append(('hole', tr(_offset(circle(
                    SCREW_CLEAR / 2 + 0.1, inst['sx'] * F.x_side_c + s2 * F.side_pull_x,
                    inst['z_pull'], 48), -k))))
    w = F.W + 2 * margin
    h = z_top - (F.z_dr0 - margin)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" '
           f'viewBox="0 0 {w:.2f} {h:.2f}">',
           f'<!-- mini-round-clock cabinet{F.tag} fronts: {PLY_T:.2f} mm ply, kerf {PLY_KERF:.2f}. '
           f'Red = cut. Holes first, outlines last. -->']
    # holes first, outlines last: SVG order is only a hint, set it in the UI too
    for kind in ('hole', 'outline'):
        for kd, pts in parts:
            if kd != kind:
                continue
            d = 'M ' + ' L '.join(f'{x:.3f} {y:.3f}' for x, y in pts) + ' Z'
            out.append(f'<path d="{d}" fill="none" stroke="#FF0000" stroke-width="0.1"/>')
    out.append('</svg>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')


# ------------------------------------------------------------------ out
# print orientation: rows are the new axes in world coordinates
FRONT_DOWN = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
OPEN_UP    = np.eye(4)
BACK_DOWN  = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)


def parts_for(F):
    """(solid, world name, print name or None, print orientation).

    A part with no print name is another instance of one already in the list --
    a side pull four rows up is the same print as the one below it -- so it is
    written to cabinet/world/ for the checks and the pictures, and not to
    stl/ as a file to print twice."""
    tg = F.tag
    p = lambda n: f'mini-round-clock-cabinet{tg}{n}'
    out = [
        (build_sleeve(F), p('-sleeve'), p('-sleeve'), BACK_DOWN),
        (build_hatch(F),  p('-hatch'),  p('-hatch'),  BACK_DOWN),
        (build_drawer(F), p('-drawer'), p('-drawer'), OPEN_UP),
        (build_pull(F),   p('-pull'),   p('-pull'),   FRONT_DOWN),
    ]
    if F.sides:
        # left and right are mirror images, and both are emitted rather than
        # one being printed mirrored: the slicer can do it, but a file that is
        # the part is one less thing to get wrong. Every side pull is the same
        # print, so only the first one is written as a part.
        for i, inst in enumerate(side_instances(F)):
            out.append((build_side_drawer(F, inst['sx'], inst['row']),
                        p(inst['drawer']), p(inst['drawer']), OPEN_UP))
            out.append((build_pull(F, F.side_pull_L, inst['z_pull'], F.side_pull_x,
                                   inst['sx'] * F.x_side_c),
                        p(inst['pull']), p('-pull-side') if i == 0 else None, FRONT_DOWN))
    return out


def world_dir():
    p = os.path.join(HERE, 'cabinet', 'world')
    os.makedirs(p, exist_ok=True)
    return p


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='mini-round-clock cabinet')
    ap.add_argument('--only', default=None, help='"" or -32')
    args = ap.parse_args()
    for tag in ('', '-32', '-60'):
        if args.only is not None and tag != args.only:
            continue
        F = Frame(tag)
        print(f'body {tag or "24"}: sleeve {F.W:.1f} W x {F.H:.1f} H (+{CAB_FEET_H:.1f} feet) x '
              f'{F.D:.1f} D; stack needs {F.depth_needed:.1f} deep')
        if not F.fits_bed():
            print(f'  cabinet{tag} SKIPPED: {F.W:.1f} x {F.H:.1f} x {F.D:.1f} does not fit a '
                  f'{CAB_BED:.0f} mm bed')
            continue
        for man, fn, pn, M in parts_for(F):
            t = csg.finalise(man, fn)
            t.export(os.path.join(world_dir(), fn + '.stl'))
            if pn is None:
                continue
            tp = t.copy()
            tp.apply_transform(M)
            tp.apply_translation(-tp.bounds[0])
            tp.export(csg.part_out(pn + '.stl'))
            tp.export(csg.part_out(pn + '.3mf'))
        plys = [(build_face_panel(F), f'mini-round-clock-cabinet{tag}-face-ply'),
                (build_drawer_front(F), f'mini-round-clock-cabinet{tag}-drawer-ply')]
        if F.sides:
            print(f'  side drawers: {2 * F.side_rows} of them, {F.side_w:.1f} wide x '
                  f'{F.side_row_h:.1f} high, {F.side_rows} rows a side')
            plys += [(build_side_front(F, i['sx'], i['row']),
                      f'mini-round-clock-cabinet{tag}{i["ply"]}')
                     for i in side_instances(F)]
        else:
            print(f'  no side drawers: the bay leaves {F.side_w:.1f} each side and '
                  f'CAB_SIDE_MIN is {CAB_SIDE_MIN:.0f}')
        for man, fn in plys:
            csg.finalise(man, fn).export(os.path.join(world_dir(), fn + '.stl'))
        svg = os.path.join(HERE, 'cabinet', f'mini-round-clock-cabinet{tag}-fronts.svg')
        write_svg(F, svg)
        print(f'  wrote {os.path.relpath(svg, HERE)}')
    print('done')
