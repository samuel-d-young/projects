"""The vertical-slot player: the tape stands in a slot in the top, label to the
front, and comes out of the top. Samuel, 2026-09-15: "the cassette can go in
but also be taken out of the top rather than put into the side."

Three printed parts:
    slot_face   the front panel, printed FLAT, detail side UP. Every cosmetic
                thing lives here - the transport keys, the knob recesses, the
                counter window, the REC lamp and the VU dial - and it glues
                into a rebate in the body's front face the way the lid drops
                into its pocket. It comes out as three solids on one origin
                (plate, keys, trim) so an AMS gives each its own filament
                rather than the geometry pretending to be a colour.
    slot_body   the shell, printed UPSIDE DOWN (top face on the bed): the
                slot is an open channel from the bed, the module pocket and
                the cavity open upward, the screw posts grow from the bed.
                The slot floor is a 13 mm bridge, nothing else overhangs.
    slot_lid    the bottom plate, printed outside face down: counterbores
                open at the bed, the D1 mini posts, buzzer ring and the
                module shelf stand up from it. It is recessed INTO the body,
                not butted against it.

Inside: the PN532 stands vertically with its flat back against the wall
behind the slot (the antenna coil reads through its own PCB), held by two
side ribs, two keeper ribs hanging from the roof, and a shelf on the lid.
Everything on the module's component side - the DIP switch, the header,
the Dupont tails - faces the back. The D1 mini lies on the lid to the left,
USB out through the left wall. The buzzer sits under the slot floor on the
right with three sound holes through the front wall. LED and five cosmetic
transport buttons on the front panel, below the slot.
"""
from __future__ import annotations

import math

from build123d import Align, Axis, Box, Cylinder, Pos, Rot, fillet

C = (Align.CENTER, Align.CENTER, Align.MIN)
CC = (Align.CENTER, Align.CENTER, Align.CENTER)


def _rounded_box(l: float, w: float, h: float, r: float):
    b = Box(l, w, h, align=C)
    return fillet(b.edges().filter_by(Axis.Z), r)


def _posts_and_lips(cx, cy, pl, pw, D, top_z, lip_top_z, z0):
    """Corner posts under a PCB's corners plus L-shaped lips outside them (see player.py)."""
    parts = []
    post = D["ledge"] + D["pcb_clr"] + D["lip_t"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            py = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] - post / 2)
            parts.append(Pos(px, py, z0) * Box(post, post, top_z - z0, align=C))
            lx = cx + sx * (pl / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            ly = cy + sy * (pw / 2 + D["pcb_clr"] + D["lip_t"] / 2)
            parts.append(Pos(lx, py, z0) * Box(D["lip_t"], post, lip_top_z - z0, align=C))
            parts.append(Pos(px, ly, z0) * Box(post, D["lip_t"], lip_top_z - z0, align=C))
    return parts


def build_body(D: dict):
    L, W, H, wall = D["s_L"], D["s_W"], D["s_H"], D["wall"]
    floor = D["s_lid_t"]                      # "floor" here is the top of the lid
    body = Pos(0, 0, floor) * _rounded_box(L, W, H - floor, D["corner_r"])
    cavity = Pos(0, 0, floor - 0.01) * _rounded_box(D["s_cavity_l"], D["s_cavity_w"],
                                                     D["s_roof_z"] - floor + 0.01, D["s_cavity_r"])
    body = body - cavity
    # The skirt: the outer wall carries on down past the lid, so the lid drops into
    # a pocket and finishes flush instead of butting against the bottom rim with
    # nothing to locate it (Samuel, 2026-09-18: "the bottom doesn't go in properly").
    # The step from this pocket to the narrower cavity is the seat it stops against.
    # Printed top-face-down this rim is the last thing laid, on top of the full
    # wall beneath it - no overhang.
    skirt = _rounded_box(L, W, floor, D["corner_r"]) - Pos(0, 0, -0.01) * _rounded_box(
        D["s_pocket_l"], D["s_pocket_w"], floor + 0.02, D["s_pocket_r"])
    body = body + skirt

    # the slot block: solid from the slot-floor plate up to the roof, spanning the
    # slot plus an end wall each side and the module wall behind; then the slot itself
    blk_l = D["s_slot_l"] + 2 * D["s_end_wall"]
    blk_y0, blk_y1 = D["y_slot0"] - 0.5, D["y_pcb0"]           # overlaps the front wall a touch
    blk = Pos(0, (blk_y0 + blk_y1) / 2, D["s_plate_bot_z"]) * Box(blk_l, blk_y1 - blk_y0, D["s_roof_z"] - D["s_plate_bot_z"] + 0.5, align=C)
    body = body + blk
    # plan-view corners of the slot stay nearly square: the tape's thickness edges
    # are square, and a 2.5 mm radius here pinched its corners (fit check, 2026-09-16)
    slot = Pos(0, (D["y_slot0"] + D["y_slot1"]) / 2, D["s_plate_top_z"]) * _rounded_box(
        D["s_slot_l"], D["s_slot_w"], H - D["s_plate_top_z"] + 1.0, D["s_slot_r"])
    body = body - slot

    # the detent: a ridge on each long wall of the slot, its axis ON the wall so
    # it stands s_click_r into the slot. Printed top-face-down these are small
    # horizontal beads on a vertical face - the widest point is a 90 degree
    # overhang, which at this radius bridges without a thought.
    for yy in (D["y_slot0"], D["y_slot1"]):
        body = body + Pos(0, yy, D["s_click_z"]) * Rot(0, 90, 0) * Cylinder(
            D["s_click_r"], D["s_click_len"], align=CC)

    # module pocket: two full-height side ribs beside the PCB's side edges, and a
    # top lip hanging from the roof behind the PCB's top edge strip. The PCB's
    # component side faces the back; nothing here touches it except that strip,
    # which the listing photos show is bare (the antenna trace is inset ~2 mm).
    rib_len = D["s_rail_y1"] - D["s_rail_y0"]
    for sx in (-1, 1):
        body = body + Pos(sx * D["s_rail_x"], (D["s_rail_y0"] + D["s_rail_y1"]) / 2, floor) * Box(
            D["s_keeper"], rib_len, D["s_roof_z"] - floor + 0.5, align=C)
    body = body + Pos(0, D["s_lip_y"], D["s_lip_top_z0"]) * Box(
        D["s_lip_top_w"], D["s_keeper"], D["s_roof_z"] - D["s_lip_top_z0"] + 0.5, align=C)

    # The ring's cradle. It sits in the front of the cavity, between the inside
    # of the front wall and the front face of the slot block - which is why the
    # slot moved back. Two VERTICAL ribs locate it across the face (vertical so
    # they print as fins on a vertical wall rather than as overhangs) and a stop
    # across the top sets how far up it can go; the lid carries the two posts it
    # rests on, so it is trapped once the lid is screwed down.
    cx, cz = D["k_vu_c"]
    ry = -W / 2 + wall + D["s_ring_depth"] / 2
    rx = D["s_ring_rib_x"]
    for sx in (-1, 1):
        body = body + Pos(cx + sx * rx, ry, cz) * Box(
            D["s_ring_rib"], D["s_ring_depth"], D["s_ring_od"] + 8.0, align=CC)
    body = body + Pos(cx, ry, cz + D["s_ring_od"] / 2 + D["s_ring_clr"] + 1.0) * Box(
        2 * rx, D["s_ring_depth"], 2.0, align=CC)

    # The single WS2812B, in the ring's middle. s_dot_od was declared when the
    # dial was designed and never used - the pixel showed through the centre
    # hole with nothing holding it. Two fins either side and a ledge under it,
    # the same idea as the ring's own cradle and for the same reason: a fin on
    # a vertical wall prints, a boss on one is a half-cylinder overhang.
    dr = D["s_dot_od"] / 2 + D["s_ring_clr"]
    body = body + Pos(cx, ry, cz - dr - D["s_dot_ledge"] / 2) * Box(
        D["s_dot_od"], D["s_ring_depth"], D["s_dot_ledge"], align=CC)
    # the fins' far corners have to stay inside the ring's own hole, so their
    # height comes from that circle rather than from a guess
    x_out = dr + D["s_ring_rib"]
    fin_h = 2 * math.sqrt(max(D["s_dot_fin_r"] ** 2 - x_out ** 2, 1.0))
    for sx in (-1, 1):
        body = body + Pos(cx + sx * (dr + D["s_ring_rib"] / 2), ry, cz) * Box(
            D["s_ring_rib"], D["s_ring_depth"], fin_h, align=CC)

    # screw posts from the roof down to the lid, pilot-drilled from below
    for (x, y) in D["s_posts"]:
        body = body + Pos(x, y, floor) * Cylinder(D["post_d"] / 2, D["s_roof_z"] - floor + 0.5, align=C)
        body = body - Pos(x, y, floor - 0.1) * Cylinder(D["screw_pilot"] / 2, D["s_pilot_depth"] + 0.1, align=C)

    # openings: USB through the left wall, LED and buzzer holes through the front wall
    body = body - Pos(-L / 2, D["s_brd_cy"], D["s_usb_cz"]) * Box(wall * 3, D["esp_usb_w"], D["esp_usb_h"], align=CC)
    body = body - Pos(D["s_led_cx"], -W / 2, D["s_led_cz"]) * Rot(90, 0, 0) * Cylinder(
        (D["led_d"] + 2 * D["led_clr"]) / 2, wall * 3, align=CC)
    for dy in (-3.0, 0.0, 3.0):
        body = body - Pos(L / 2, D["s_buzzer_cy"] + dy, 6.0) * Rot(0, 90, 0) * Cylinder(1.0, wall * 3, align=CC)

    return _front_rebate(body, D)


def _front_rebate(body, D: dict):
    """The front face is no longer a face: it is a rebate that slot_face glues
    into, plus the two things that still have to reach light through what is
    left of the wall behind the panel - the dial's eight wedge slots and its
    centre hole.

    The rebate is cut from the wall's OUTER surface and is s_face_t deep, so
    s_face_back of wall stays behind it (params clamps both). Everything
    cosmetic moved to the panel; the LED hole stays in build_body because it
    is an opening, not a decoration.

    Printed top-face-down the rebate is a pocket in a vertical wall: its sides
    and its floor are vertical, and only the rim's two horizontal runs face
    down, s_face_ledge wide, which bridges.
    """
    face = -D["s_W"] / 2
    body = body - Pos(0, face + D["s_face_t"], D["s_face_cz"]) * Rot(90, 0, 0) * _rounded_plate(
        D["s_face_pocket_l"], D["s_face_h"], D["s_face_t"] + 0.5, D["s_face_pocket_r"])
    # The dial, through the wall that is left. The slot BEHIND the panel is what
    # collimates each pixel, so its depth is the whole point of it: the panel
    # spends k_dimple of the face on the dish and this keeps the rest.
    cx, cz = D["k_vu_c"]
    half = math.radians(360.0 / 8 - D["k_vu_gap_deg"]) / 2
    for k in range(8):
        a = math.pi / 2 + 2 * math.pi * k / 8          # one wedge at twelve o'clock
        body = body - Pos(cx, face, cz) * Rot(90, 0, 0) * _sector(
            D["k_vu_r0"], D["k_vu_r1"], a - half, a + half, D["wall"] * 3)
    body = body - Pos(cx, face, cz) * Rot(90, 0, 0) * Cylinder(
        D["k_vu_centre_d"] / 2, D["wall"] * 3, align=CC)
    return body


def _rounded_plate(l: float, h: float, t: float, r: float):
    """A plate lying in XY, `l` by `h`, `t` thick along +Z with its back face on
    the bed, corners rounded `r`: the shape of the front panel, of the rebate it
    drops into, and the orientation the panel prints in."""
    b = Box(l, h, t, align=C)
    return fillet(b.edges().filter_by(Axis.Z), r)


def _sector(r0: float, r1: float, a0: float, a1: float, t: float, n: int = 16):
    """An annular sector as a solid `t` thick along its own Z, for cutting a
    wedge slot. Polygonal, because a 37-degree slot only has to look round."""
    from build123d import Polygon, extrude, Plane
    pts = [(r1 * math.cos(a0 + (a1 - a0) * i / n), r1 * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    pts += [(r0 * math.cos(a1 + (a0 - a1) * i / n), r0 * math.sin(a1 + (a0 - a1) * i / n)) for i in range(n + 1)]
    return extrude(Plane.XY * Polygon(*pts, align=None), t / 2, both=True)


def _web_groove(r0: float, r1: float, a_mid: float, gap: float, margin: float,
                t: float, n: int = 12):
    """A groove that follows a web between two wedge slots, keeping `margin` mm of
    web either side at EVERY radius. The web is an annular strip, so it widens
    with radius - a constant-angle slot would be starved at r0 or would open into
    a wedge at r1. Half-angle at radius r is gap/2 - margin/r."""
    from build123d import Polygon, extrude, Plane
    def half(r):
        return max(gap / 2 - margin / r, 1e-4)
    inner = [(r0 + (r1 - r0) * i / n) for i in range(n + 1)]
    pts = [(r * math.cos(a_mid - half(r)), r * math.sin(a_mid - half(r))) for r in inner]
    pts += [(r * math.cos(a_mid + half(r)), r * math.sin(a_mid + half(r))) for r in reversed(inner)]
    return extrude(Plane.XY * Polygon(*pts, align=None), t / 2, both=True)


def _key_chamfer(length: float, size: float):
    """A 45-degree triangular prism `length` long along X, its right angle on the
    +Y/+Z corner. Subtracted from a transport key it cuts the key's top edge back
    at 45 degrees - which on the body was what made that edge printable, and on
    the flat panel is simply what a moulded key looks like."""
    from build123d import Polygon, extrude, Plane
    tri = Polygon((0, 0), (-size, 0), (0, -size), align=None)
    return extrude(Plane.YZ * tri, length / 2, both=True)


def build_face(D: dict):
    """The front panel's plate: everything that is a hole or a dent. It lies in
    XY exactly as it prints - back face on the bed, show face up - so a feature
    the body knows at (x, z) is at (x, z - s_face_cz) here, a dent of depth d is
    cut down from z = s_face_t, and anything proud stands up from it.

    Nothing overhangs: every dent opens upward, every hole goes through, and the
    back is flat, which is both the bed side and the glue side. The plate is the
    body colour; build_face_keys and build_face_trim are the other two filaments
    and share this origin, so the three load as one object in the slicer.
    """
    t, cz0 = D["s_face_t"], D["s_face_cz"]
    plate = _rounded_plate(D["s_face_l"], D["s_face_panel_h"], t, D["s_face_r"])
    thru = 4 * t                                   # comfortably through the plate

    # the LED, and the two recesses the glued knobs locate in
    plate = plate - Pos(D["s_led_cx"], D["s_led_cz"] - cz0, t) * Cylinder(
        (D["led_d"] + 2 * D["led_clr"]) / 2, thru, align=CC)
    for (cx, cz), d in ((D["k_knob_big_c"], D["k_knob_big_d"]), (D["k_knob_small_c"], D["k_knob_small_d"])):
        plate = plate - Pos(cx, cz - cz0, t) * Cylinder((d + 0.3) / 2, 2 * D["k_recess"], align=CC)

    # the tape counter window, with three "digit" bars standing back up out of
    # its floor to the face. The bars stay on the PLATE rather than joining the
    # trim: they read as body colour behind the frame, and they print supported.
    cx, cz = D["k_counter_c"]
    cw, ch, cy = D["k_counter_w"], D["k_counter_h"], cz - cz0
    plate = plate - Pos(cx, cy, t + 0.8) * Box(cw, ch, 1.6 + 2 * D["k_dimple"], align=CC)
    for i in (-1, 0, 1):
        plate = plate + Pos(cx + i * 6.0, cy, t - D["k_dimple"] / 2) * Box(
            4.0, ch - 2.5, D["k_dimple"], align=CC)

    # REC lamp
    rx, rz = D["k_rec_c"]
    plate = plate - Pos(rx, rz - cz0, t) * Cylinder(2.0, 2 * D["k_dimple"], align=CC)

    # The VU dial: the dish the white diffuser glues into, the eight wedge slots
    # and the centre hole. The wedges and the hole go through; the wall behind
    # the panel carries the same cuts, and THAT depth is what keeps one pixel
    # out of its neighbour's wedge.
    vx, vz = D["k_vu_c"]
    vy = vz - cz0
    bi = D["k_vu_bezel_od"] / 2 - D["k_vu_bezel_w"]
    plate = plate - Pos(vx, vy, t) * Cylinder(bi, 2 * D["k_dimple"], align=CC)
    half = math.radians(360.0 / 8 - D["k_vu_gap_deg"]) / 2
    for k in range(8):
        a = math.pi / 2 + 2 * math.pi * k / 8          # one wedge at twelve o'clock
        plate = plate - Pos(vx, vy, t) * _sector(D["k_vu_r0"], D["k_vu_r1"], a - half, a + half, thru)
    plate = plate - Pos(vx, vy, t) * Cylinder(D["k_vu_centre_d"] / 2, thru, align=CC)
    return plate


def build_face_keys(D: dict):
    """The five transport keys, as their own solid so the AMS prints them in a
    second filament. They stand k_key_proud off the plate and share its origin.
    The 45-degree chamfer on each key's top edge is no longer structural - on
    the body it was what kept that edge from overhanging - but it is what a
    moulded key looks like, so it stays."""
    t, cz0 = D["s_face_t"], D["s_face_cz"]
    kw, kh, kp = D["k_key_w"], D["k_key_h"], D["k_key_proud"]
    y = D["s_buttons_cz"] - cz0
    keys = None
    for i in range(5):
        x = D["s_buttons_x0"] + i * D["s_buttons_pitch"]
        key = Pos(x, y, t) * Box(kw, kh, kp, align=C)
        key = key - Pos(x, y + kh / 2, t + kp) * _key_chamfer(kw + 0.2, kp)
        # a shallow groove across each key face, like a worn piano key
        key = key - Pos(x, y - kh / 2 + 2.0, t + kp) * Box(kw - 3.0, 0.6, 1.0, align=CC)
        keys = key if keys is None else keys + key
    return keys


def build_face_trim(D: dict):
    """The bright work in a third filament: the dial's bezel ring and the counter
    window's frame. Both stand off the plate's face and are opened by the same
    cuts the plate is, so they sit on it and never into it."""
    t, cz0 = D["s_face_t"], D["s_face_cz"]
    vx, vz = D["k_vu_c"]
    bo, prd = D["k_vu_bezel_od"] / 2, D["k_vu_bezel_proud"]
    bi = bo - D["k_vu_bezel_w"]
    bezel = (Pos(vx, vz - cz0, t) * Cylinder(bo, prd, align=C)
             - Pos(vx, vz - cz0, t - 0.1) * Cylinder(bi, prd + 0.2, align=C))
    cx, cz = D["k_counter_c"]
    cw, ch, cy = D["k_counter_w"], D["k_counter_h"], cz - cz0
    frame = (Pos(cx, cy, t) * Box(cw + 2.4, ch + 2.4, 0.8, align=C)
             - Pos(cx, cy, t + 0.8) * Box(cw, ch, 1.6 + 2 * D["k_dimple"], align=CC))
    return bezel + frame


def build_knob(D: dict, d: float):
    """A knob printed flat: a knurled cylinder with a pointer groove, a 45-degree
    lead-in at the base so it drops into its recess, and a dome-ish top."""
    h = D["k_knob_h"]
    knob = Cylinder(d / 2, h, align=C)
    # knurl: 16 shallow flutes around the side
    import math
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        knob = knob - Pos((d / 2) * math.cos(a), (d / 2) * math.sin(a), h / 2 + 0.6) * Cylinder(0.7, h - 1.2, align=CC)
    # pointer groove across the top
    knob = knob - Pos(d / 4, 0, h) * Box(d / 2 - 0.5, 1.2, 1.0, align=CC)
    # chamfer the top edge a little
    knob = knob - Pos(0, 0, h) * (Cylinder(d / 2 + 1, 1.0, align=CC) - Cylinder(d / 2 - 0.8, 1.2, align=CC))
    return knob


def build_diffuser(D: dict):
    """The VU dial's diffuser: a white-PLA disc that glues into the dish inside
    the bezel, the way the knobs glue into their recesses. It caps the eight
    wedge slots and the centre hole without plugging them - the 2.4 mm slot
    behind it collimates, and a plug would only pipe light sideways.

    Eight grooves on the BACK face, one per web, break the lateral path a disc
    would otherwise give light between neighbouring wedges. They are annular
    sectors following the web, because at the inner radius the web is only
    radians(k_vu_gap_deg) * k_vu_r0 wide and a straight slot would open into a
    wedge. Prints smooth-face-down, grooves up: no overhang, and the face that
    shows gets the bed's finish.
    """
    t = D["k_vu_diff_t_eff"]
    disc = Cylinder(D["k_vu_diff_r"], t, align=C)
    if D["k_vu_diff_grooved"]:
        for k in range(8):
            a = math.pi / 2 + 2 * math.pi * k / 8 + math.pi / 8   # centred on a web
            disc = disc - Pos(0, 0, t - D["k_vu_diff_groove_d_eff"] / 2) * _web_groove(
                D["k_vu_diff_groove_r0"], D["k_vu_diff_groove_r1"], a,
                math.radians(D["k_vu_gap_deg"]), D["k_vu_diff_groove_margin"],
                D["k_vu_diff_groove_d_eff"] + 0.02)
    return disc


def build_lid(D: dict):
    """The bottom plate. It is inset from the body's footprint by the ledge plus a
    clearance so it drops into the pocket in the body's underside and finishes
    flush, located on all four sides; and it is `s_lid_t` thick rather than the
    shared `floor`, because a 2.4 mm plate counterbored 2.5 mm for a pan head is
    not a plate, it is a hole."""
    floor = D["s_lid_t"]
    lid = _rounded_box(D["s_lid_l"], D["s_lid_w"], floor, D["s_lid_r"])
    for (x, y) in D["s_posts"]:
        lid = lid - Pos(x, y, -0.1) * Cylinder(D["screw_hole"] / 2, floor + 0.2, align=C)
        lid = lid - Pos(x, y, -0.1) * Cylinder(D["screw_head_d"] / 2, D["screw_head_h"] + 0.1, align=C)
    # shelf the PCB's bottom edge rests on, and a lip behind its bottom edge strip
    # (middle only, between the I2C header and the DIP switch)
    lid = lid + Pos(0, (D["y_pcb0"] + D["y_pcb1"]) / 2, floor) * Box(30.0, D["pn532_t"] + D["pcb_clr"], D["s_shelf_h"], align=C)
    lid = lid + Pos(0, D["s_lip_y"], floor) * Box(D["s_lip_bot_w"], D["s_keeper"], D["s_lip_bot_z1"] - floor, align=C)
    # D1 mini posts + lips
    for p in _posts_and_lips(D["s_brd_cx"], D["s_brd_cy"], D["esp_l"], D["esp_w"], D,
                             top_z=D["s_brd_board_z"], lip_top_z=D["s_brd_board_z"] + D["esp_t"] + 3.0, z0=floor):
        lid = lid + p

    # the two posts the ring stands on. They sit under its rim, between LEDs,
    # and are pulled back off the cavity wall by s_mount_gap like every other
    # thing that stands on the lid.
    cx, cz = D["k_vu_c"]
    py0 = D["s_ring_y0"] - 0.2
    py1 = D["s_ring_y1"] + 0.2
    for sx in (-1, 1):
        lid = lid + Pos(cx + sx * D["s_ring_post_dx"], (py0 + py1) / 2, floor) * Box(
            D["s_ring_post_w"], py1 - py0, D["s_ring_post_top"] - floor, align=C)

    # zip-tie hold-down for the D1 mini: two straps across the board. Each is a
    # pair of through-slots - one in the gap behind the board, one in front of
    # the lip line - joined by a groove in the OUTSIDE face, so the return run of
    # the strap is below flush and the player still stands flat. Cutting only,
    # nothing stands on the lid, so the mount keeps its s_mount_gap.
    sl, sw = D["s_tie_slot_l"], D["s_tie_slot_w"]
    yf, yb = D["s_tie_y_front"], D["s_tie_y_back"]
    for x in D["s_tie_x"]:
        for y in (yf, yb):
            lid = lid - Pos(x, y, -0.1) * Box(sl, sw, floor + 0.2, align=C)
        lid = lid - Pos(x, (yf + yb) / 2, -0.1) * Box(sl, yb - yf, D["s_tie_groove_d"] + 0.1, align=C)
    # buzzer locating ring
    lid = lid + Pos(D["s_buzzer_cx"], D["s_buzzer_cy"], floor) * (
        Cylinder(D["buzzer_d"] / 2 + 0.3 + 1.2, 3.0, align=C) - Cylinder(D["buzzer_d"] / 2 + 0.3, 3.2, align=C))
    return lid


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import params
    from _lib import emit, write_manifest

    D = params.derive(params.nominal())
    emit(build_body(D), "slot_body", "upside down, top face on the bed", note="slot floor bridges 13 mm")
    emit(build_face(D), "slot_face", "flat, detail side up",
         note="the front panel; glue into the rebate in the body's face. Load it with "
              "slot_face_keys and slot_face_trim as ONE object (they share this origin) "
              "and give each its own AMS filament")
    emit(build_face_keys(D), "slot_face_keys", "flat, with the plate",
         note="AMS: the transport keys' filament")
    emit(build_face_trim(D), "slot_face_trim", "flat, with the plate",
         note="AMS: the dial's bezel and the counter frame")
    emit(build_lid(D), "slot_lid", "outside face down",
         note=f"4 x M3 x {D['screw_len']:.0f} pan head from below; the lid recesses into the body; "
              f"2 small zip ties ({D['s_tie_slot_l']:.1f} x {D['s_tie_slot_w']:.1f} mm slots) hold the D1 mini down, "
              f"return run in the groove on the outside face")
    emit(build_diffuser(D), "vu_diffuser", "smooth face down, grooves up",
         note="WHITE PLA; glue into the dial's dish inside the bezel")
    emit(build_knob(D, D["k_knob_big_d"]), "knob_big", "flat, base down", note="glue into the left recess")
    emit(build_knob(D, D["k_knob_small_d"]), "knob_small", "flat, base down", note="glue into the right recess")
    write_manifest()
