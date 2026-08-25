#!/usr/bin/env python3
"""Every dimension the v2 rear end is built from.

MEASURED values were probed off Sam's uploaded STLs (see measure*.py); they are
not guesses. DERIVED values fall out of them. CHOSEN values are design decisions
and each one carries the reason it is what it is.
"""
import math

# =============================================================================
# MEASURED — probed from Mini_Wall_Clock_Base.stl.  z = 0 is the BACK face,
# z = 22 the FRONT (the plywood side).  +x is 12 o'clock, -x is 6 o'clock.
# =============================================================================
R_BODY        = 53.9926     # outer cylinder
Z_BACK        = 0.0         # rear face of Sam's base
Z_FRONT       = 22.0
R_BORE        = 27.7800     # rear bore, behind the display
Z_SEAT        = 8.6000      # display module rests here
R_DISP_POCKET = 30.2788
# MEASURED on the built base: the inner wall between the screen bore and the ring
# pocket tops out here, a 4.9 mm wide annular land at r 30.19..35.11. The
# diffuser's face lands on it, and that -- not the press fit -- is what sets how
# deep the diffuser goes. Everything that has to line up with the diffuser is
# derived from DIFF_SEAT_Z.
DIFF_WALL_CREST = 19.0300
# DIFF_SEAT_Z = DIFF_WALL_CREST + FACE_T, defined with FACE_T further down --
# it was frozen at 21.03 here, which silently stopped tracking when FACE_T moved.
R_RING_I      = 35.1080     # ring pocket
R_RING_O      = 46.3516
Z_RING_FLOOR  = 11.8000
Z_RECESS      = 19.0000     # plywood face recess floor
R_LIP_I       = 51.9807

WIRE_SLOT_HW  = 13.0030     # Sam's straight-down wire channel, half width
WIRE_SLOT_END = -43.0000    # its outer end, on the -x axis
TAB_HALF_DEG  = 41.758      # display-tab window, half angle about +x
R_TAB         = 42.6566     # and how far out it reaches

# The disconnected boolean residue in the uploaded file, for the record.
RESIDUE_VOL   = 605.0

# =============================================================================
# THE PARTS THAT GO IN — Sam's own measurements, carried over from build.py
# =============================================================================
RING_OD, RING_ID = 92.0, 71.0
PCB_T, LED_H     = 1.6, 1.6
NUM_LEDS         = 24
DISP_PCB_D       = 60.0     # round part of the display's blue PCB
DISP_ACTIVE_D    = 55.0     # the black screen area
DISP_T           = 4.0      # module thickness -- see the note on the collar,
                            # this is the OVERALL figure, not the rim
DISP_OVERALL     = 67.0     # top of the round part to the end of the tab
DISP_TAB_T       = 1.6      # bare PCB. Assumes the 10-pin header is desoldered.

# =============================================================================
# THE ESP32-S3 DEVKIT — Espressif's own mechanical drawing,
# DXF_ESP32-S3-DevKitC-1_V1_20210312CB.pdf
# =============================================================================
BOARD_L, BOARD_W, BOARD_T = 62.865, 25.40, 1.60
BOARD_CLR   = 0.45          # per side, in the pocket
BOARD_LIFT  = 1.20          # pads under the PCB, so header tails have somewhere to go
BOARD_TALL  = 3.20          # tallest thing on top (USB-C shell ~3.2, WROOM ~3.1)

# Where it sits.  Both ends have to stay inside the dog-bone shaped void that
# Sam's bore + wire slot + tab slot already make, or the board fouls the base.
#   -x corner (-24.0, 12.7) -> r = 27.13 < 27.78  (inside the bore)      OK
#   +x corner ( 38.7, 12.7) -> r = 40.77 < 42.66  (inside the tab slot)  OK
BOARD_X0    = -24.00
BOARD_X1    = BOARD_X0 + BOARD_L          # 38.74
RAIL_T      = 1.80          # locating rail thickness
RAIL_H      = 4.00          # and how far they stand above the deck

# =============================================================================
# THE DECK — a full-disc floor added under Sam's base.  It closes the rear of
# his part, gives the S3 something to sit on, and becomes the ceiling of the
# battery box.  Printing the base deck-side-down means the first layer is a
# solid 108 mm disc, and every void above it opens upward: no support anywhere.
# =============================================================================
DECK_T      = 2.40
Z_DECK      = -DECK_T       # -2.40, the new flat mating face of the base

# =============================================================================
# THE REAR HOUSING — separate printed part, bolts to the deck.
# Printed rear-plate-down: again a solid disc first layer, pocket opens upward.
# =============================================================================
WALL_T      = 3.00                    # outer wall
R_INNER     = R_BODY - WALL_T         # 50.99  usable interior radius
PLATE_T     = 3.50                    # rear plate; also what the keyhole cuts through
# Two variants, because the battery decision is genuinely a trade and it is
# Sam's to make. Nothing else about the housing changes between them.
#   slim    - no battery, or a flat cell + charger board. Clock 44.4 mm deep.
#   battery - takes the only retail class that fits the disc: a 5000 mAh
#             "mini brick" about 79 x 38 x 26. Clock 55.4 mm deep, ~17 h.
POCKET_SLIM    = 15.00
POCKET_BATTERY = 27.50                # 26.0 battery + 1.5 clearance
POCKET_D    = POCKET_BATTERY          # what the summary quotes
REAR_H      = PLATE_T + POCKET_D
Z_REAR      = Z_DECK - REAR_H

# The battery the cradle is cut for. Change these two numbers, re-run, reprint
# just the cradle -- the housing does not move.
# Anker Nano Power Bank 22.5W, model A1653, 5000 mAh, built-in USB-C.
# 76.96 x 36.83 x 24.89 mm -- Anker publish 3.03 x 1.45 x 0.98 in on the product
# page. VERIFIED, along with A$49 in stock at Scorptec (Melbourne).
# It is the only retail bank found that is both small enough for a 108 mm disc
# and actually buyable in Australia. The POCKET is cut 1.1 mm deeper than this
# so a slightly fatter bank still goes in; only the shim keys off these numbers,
# and the shim is a 20-minute reprint.
BAT_L, BAT_W, BAT_T = 76.96, 36.83, 24.89
BAT_CX = -6.00              # pocket centre offset, to clear the hanging screw's head

# Largest rectangle that fits the interior circle:  L^2 + W^2 <= (2*R_INNER)^2
MAX_DIAG    = 2 * R_INNER             # 101.98

# --- mounting screws, base <-> rear housing ---------------------------------
# r=49 sits outboard of the ring pocket (ends at 46.35) and inboard of the lip,
# where Sam's base is solid from z=0 to z=19, so there is real material to bite.
SCREW_R     = 49.00
SCREW_ANG   = [45.0, 135.0, 225.0, 315.0]   # clear of 12 (hanger) and 6 (cable)
SCREW_PILOT = 2.50          # M3 self-tapper pilot in PLA
SCREW_CLEAR = 3.30
SCREW_HEAD  = 6.20
SCREW_DEPTH = 8.00          # engagement up into the base

# --- wall hanger -------------------------------------------------------------
# Keyhole at 12 o'clock. Entry hole takes an 8 mm screw head; it drops onto a
# 4.5 mm slot. The head then sits in a relief pocket inside the battery box, so
# the battery has to stay clear of the top of the compartment.
HANG_R       = 46.00        # radius of the keyhole's slot centre. Pushed out to
                            # 46 so the screw head, which sits INSIDE the box once
                            # the clock is hung, lands outboard of the battery.
KEY_ENTRY_D  = 9.00
KEY_SLOT_W   = 4.60
# Minimum workable drop is (entry + slot)/2 = 6.80; at 7.50 the clock must be
# lifted 6.5 mm before the head can pass back out through the entry hole.
# Every extra millimetre of drop pushes the head's swept zone further into the
# battery's footprint, and the battery is what is short of room here.
KEY_DROP     = 7.50         # how far the clock drops onto the screw
KEY_HEAD_CLR = 6.00         # half-width of the zone the screw head sweeps
KEY_HEAD_H   = 4.00         # how far it stands proud of the plate, inside the box

# --- bottom feet: hold the clock off the wall so the cable can leave ---------
FOOT_H       = 2.20
FOOT_R       = 46.00
FOOT_ANG     = [150.0, 210.0]

# --- cable exit, 6 o'clock ---------------------------------------------------
CABLE_W      = 12.00
CABLE_H      = 7.00

# --- ventilation -------------------------------------------------------------
VENT_W, VENT_L = 2.60, 14.00
VENT_ROWS      = 3

# --- battery retention shims -------------------------------------------------
SHIM_CLR     = 0.30

def max_battery(W, corner_r=0.0):
    """Longest battery of width W the pocket takes.

    Set by two things: where the hanging screw's head sweeps (which fixes the
    +x end) and the pocket wall (which fixes the -x end via the far corners).

    corner_r matters more than it looks. Treating a power bank as a sharp
    rectangle is conservative by a couple of millimetres, and a couple of
    millimetres is the difference between a candidate fitting and not. Every
    retail bank has radiused corners; 2 mm is a safe floor.
    """
    head_x0 = HANG_R - KEY_DROP - 4.5          # innermost the head ever reaches
    xe = head_x0 - 1.5                         # battery's +x edge, with clearance
    hw, rho = W / 2.0, corner_r
    if rho <= 0:
        lo = -math.sqrt(max(R_INNER**2 - hw**2, 0.0))
    else:
        inner = R_INNER - rho                  # the corner ARC's centre line
        dy = hw - rho
        lo = -(math.sqrt(max(inner**2 - dy**2, 0.0)) + rho)
    return xe - lo


def fits(L, W, T, corner_r=2.0):
    """Would this bank go in? -> (ok, why)."""
    if T > POCKET_BATTERY - 1.4:
        return False, f'{T:.1f} mm thick, pocket takes {POCKET_BATTERY - 1.4:.1f}'
    lim = max_battery(W, corner_r)
    if L > lim:
        return False, f'{L:.1f} long, {lim:.1f} available at {W:.1f} wide'
    return True, f'{lim - L:.1f} mm to spare on length'


def summary():
    return f"""mini-round-clock v6
  24-LED body           {2*R_BODY:.2f} mm dia   ring {RING_OD:.0f} / {RING_ID:.0f}
  32-LED body           {2*R_BODY32:.2f} mm dia   ring {RING32_OD:.2f} / {RING32_ID:.0f}
  Sam's base depth      {Z_FRONT - Z_BACK:.2f} mm      (z {Z_BACK:.0f} .. {Z_FRONT:.0f})
  + deck                {Z_BACK - Z_DECK:.2f} mm      (z {Z_DECK:.2f} .. {Z_BACK:.0f})
  + rear housing        {HOUSING_DEEP:.2f} mm      (pocket {POCKET_DEEP:.2f} clear)
  = total clock depth   {Z_FRONT - (Z_DECK - HOUSING_DEEP):.2f} mm
  the S3 lives in the housing now, at x {BRD_X0:.2f} .. {BRD_X1:.2f}, y +/-{BOARD_W/2:.2f}
  ...on {BRD_POST_H:.2f} mm posts, so it tops out {BRD_POST_H + BOARD_T + BOARD_TALL:.2f} mm above the pocket floor
  its own USB port looks out through a {USB_WIN_W:.0f} x {USB_WIN_H:.0f} mm window at 6 o'clock
  battery on its shelves {BAT_L:.0f} x {BAT_W:.0f} x {BAT_T:.0f} mm, and still
  {POCKET_DEEP - (BRD_POST_H + BOARD_T + BOARD_TALL) - BAT_T - 1.5:.2f} mm left over for the display and ring leads
  diffuser press fit    {2*COLLAR_RIB_H:.2f} mm on diameter at {COLLAR_RIB_N} collar ribs, INSIDE
  outer wall            {-2*DIFF_FIT:.2f} mm of clearance on diameter -- it grips nothing
  desk stand            clock {STAND_LIFT:.0f} mm off the desk, leaning back {STAND_TILT:.0f} deg
"""


if __name__ == '__main__':
    print(summary())
    for nm, x, y in [('board -x corner', BOARD_X0, BOARD_W/2), ('board +x corner', BOARD_X1, BOARD_W/2)]:
        print(f'  {nm}: r = {math.hypot(x,y):.3f}')

# --- board window details ----------------------------------------------------
# 1.50, not 3.00. The board cannot drop straight into a window that has a ledge
# at BOTH ends -- it has to go in tilted, and the tilt angle it needs is set by
# how much the ledges narrow the opening. 1.50 mm leaves a 60.19 mm gap for a
# 62.74 mm board, so it tilts in at 16.6 deg and its high end rises 8.96 mm
# above the seated plane. Go in +x end UP: there is 11.80 mm of headroom in the
# tab window at that end (3.6 mm to spare) against 8.60 in the bore at the other.
# Worst-case bearing is still 1.50 - 0.45 = 1.05 mm of PCB on each ledge.
LEDGE_END   = 1.50          # ledge depth at the two short ends only
POST_H      = 3.00          # corner posts above the deck

# --- battery pocket ----------------------------------------------------------
BAT_TOP_CLR = 1.50          # air above the battery, so it never presses on the
                            # board's underside where solder tails sit
# 0.00: matching Sam's own 144-segment outer wall exactly turns out to be
# clean once finalise() heals the float32 round trip, and it avoids a 0.3 mm
# overhanging ledge running right round the part at z=0 (101 mm2 of it).
DECK_INSET  = 0.00
COLLAR_TRIM = 1.80          # how much to take off the diffuser's screen collar

# The same 1.8 mm interference can be taken out of the BASE instead, by dropping
# the display seat. Set this to 1.80 and rebuild if you would rather not reprint
# the diffuser; it costs 1.8 mm more screen depth. 0.0 leaves Sam's seat alone.
SEAT_DROP   = 0.00

# --- battery shims (print two) -----------------------------------------------
SHIM_H      = 8.00
SHIM_WALL   = 2.50
SHIM_HALF_X = 22.00         # at x=+/-22 the pocket wall is still 45.6 mm out,
                            # so the straight end meets the arc at a steep
                            # angle and no sliver can form

# =============================================================================
# v3 — the fixes Sam asked for after test-fitting the printed parts
# =============================================================================

# --- 1. THE TAB SLOT WAS TOO LOOSE -------------------------------------------
# Sam measured the tab that sticks out of the bottom of the screen: 30.55 mm.
# The slot was cut as an angular wedge on an assumed 40 mm tab, which at r=35 is
# 46.62 mm wide. That let the module rotate +/-25.9 degrees -- which is exactly
# "it doesn't stay upright".
DISP_TAB_W    = 30.55       # MEASURED by Sam on the real module
TAB_CLR       = 0.30        # per side. FDM runs internal features slightly
                            # undersize, so this lands near 0.15 in the plastic.
TAB_SLOT_HW   = DISP_TAB_W / 2 + TAB_CLR        # 15.575
TAB_WALL_RI   = 31.00       # walls start here: clear of the module at r=30.0
TAB_WALL_RO   = 43.50       # over-reach into solid material, for a clean union
TAB_WALL_AHALF = 44.0       # ditto, angularly
# Taking the walls to the ring pocket floor also puts back the floor the tab
# window removed, so the ring is supported at 12 o'clock again.
TAB_WALL_TOP  = Z_RING_FLOOR                    # 11.80
# 45-degree lead-in on the top inner edge of the walls, so a slightly rotated
# tab still drops in. It has to start above the tab (which tops out at 10.20)
# and finish by the ring pocket floor, or it eats into the ring's space.
TAB_CHAMF_Z   = 10.60

# --- 2, 3, 4. THE DIFFUSER ----------------------------------------------------
# Measured off the uploaded file, 90-degree ray (clear of the baffles):
#     r 27.92 .. 30.11   collar        8.2 tall
#     r 30.20 .. 35.60   inner skirt   2.0
#     r 35.60 .. 36.70   cell rib      4.0
#     r 36.70 .. 39.00   skirt         2.0
#     r 39.00 .. 44.90   MEMBRANE      0.8
#     r 44.90 .. 46.00   outer wall    4.0
DIFF_OUTER    = 46.000
DIFF_WALL_RI  = 44.900
DIFF_MEM_RI   = 39.000
DIFF_MEM_RO   = 44.900
DIFF_WALL_H   = 4.000
DIFF_BORE_RI  = 27.6300      # MEASURED: the window you look at the screen
                             # through -- the diffuser's own inner radius
DIFF_COLLAR_RI, DIFF_COLLAR_RO = 27.9164, 30.1080
DIFF_COLLAR_H = 8.200

# THE OUTER WALL IS A CLEARANCE FIT NOW. Sam: "I want the press fit to be on the
# inside where the screen is not the outside." So nothing out here grips: the
# wall drops into the ring pocket with 0.40 mm of clearance on diameter and the
# eight outer crush ribs are gone entirely.
#
# It is the better place for it anyway. The outer wall is 92 mm around on the
# small body and 233 on the 60-LED one, so the same interference is a completely
# different fit on each, and on the big one it is smaller than the printer's own
# error. The collar is 60 mm around on all three -- one fit, three clocks.
DIFF_FIT      = -0.20        # radial CLEARANCE, i.e. 0.40 mm on diameter
DIFF_OUTER_NEW = R_RING_O + DIFF_FIT            # 46.1516

# one layer over the LEDs. At 0.20 mm layers this is a single bottom layer, and
# the diffuser prints membrane-side DOWN so it is the first layer -- no bridging.
DIFF_MEM_T    = 0.20

# the 24 cell walls have to stay attached to the membrane, so the thinning cut
# steps around them and leaves a small buttress at each base.
DIFF_BAFFLE_N  = 24
DIFF_BAFFLE_A0 = 7.50       # first one; they run every 15 degrees
DIFF_BAFFLE_KEEP = 2.60     # degrees of membrane kept at full 0.8 either side

# Sam: "the inside of the diffuser can be 2 mm tall to go further into the LED
# screen area to hold it in too" -- the collar grows 2 mm so it reaches the
# module's front face and clamps it. See README for what that implies.
COLLAR_EXT_RI, COLLAR_EXT_RO = 28.05, 29.95     # RO is deliberately OVER
                            # COLLAR_OD: the extension is added before the collar
                            # is turned down, so one cut makes both surfaces and
                            # they finish flush. Insetting it instead left a
                            # 0.10 mm ledge ringing the collar at z=8.20.

# --- v4: the lit band becomes a LINE ------------------------------------------
# Sam: "more of a line where the LED shows through like the echo wall clock."
# The diffusing band was r 39.00 .. 44.90 -- 5.90 mm wide. A lit LED read as a
# 5.9 x 9.8 mm blob. The Echo shows a thin ring of light on a plain white face,
# so: keep the 0.20 mm skin only over a narrow slot centred on the LED circle,
# and thicken the rest until it reads as white rather than glow.
DIFF_LINE_R   = (RING_OD + RING_ID) / 4          # 40.75 -- the LED circle
DIFF_LINE_W   = 2.50                             # width of the lit line
DIFF_LINE_RI  = DIFF_LINE_R - DIFF_LINE_W / 2    # 39.50
DIFF_LINE_RO  = DIFF_LINE_R + DIFF_LINE_W / 2    # 42.00
# 2.00 mm of white PLA either side, which is also flush with the inner skirt, so
# the whole face inboard of the line is one continuous 2 mm shelf. White PLA at
# 0.20 mm glows; at 2.00 mm it does not.
DIFF_OPAQUE_T = 2.00

# --- v5: radial ticks, and the hours written on the face ----------------------
# Sam: "the line needs to be perpendicular to the screen, like the lines are.
#       I want the LEDs to look more like the echo wall clock LEDs."
# So each cell's aperture turns 90 degrees: a radial tick pointing at the
# centre, like an hour mark, instead of an arc lying along the circle.
TICK_W       = 2.00         # tangential width
TICK_RI      = 38.75        # a 5050 spans r 38.25..43.25, so the tick sits
TICK_RO      = 42.75        # inside the LED, centred on it, and is evenly lit
                            # end to end with 0.50 mm of LED beyond either end
TICK_END_R   = 0.85         # radiused ends
# Sam: "update the diffusers so that only the part that is meant to be seen
# through the LED is thin, otherwise there is bleed and you can see through where
# you're not meant to."
#
# The geometry was already doing that -- probed across the built face, it is a
# flat 2.00 mm everywhere except the aperture, which is 0.20. So the bleed is
# not a hole in the model; it is 2.00 mm of white PLA still passing light. The
# answer is more of it. 3.00 mm is half again as much material in the way, and
# it is the most that fits: the walled cell behind it keeps its full 2.00 mm
# depth and the band still clears the LED ring by 1.03 mm.
#
# Two things have to come with it, or thickening the face makes the clock worse:
#   * the aperture FLARES behind the membrane (APER_FLARE), so a 3 mm face does
#     not turn each dot into the bottom of a deep narrow slot you can only see
#     head-on;
#   * the face has to be SLICED SOLID. At 0% infill a 3 mm face is a shell with
#     air in it, and air does not block light. See MAKE.md.
# 2.90, not 3.00, and the ceiling is not a preference: the diffuser's face sits
# in the base's front recess, between the wall crest it rests on at 19.03 and
# the front of the clock at 22.00. That is 2.97 mm and no more. At 2.90 the face
# finishes 0.07 mm inside the front -- effectively flush, which it never was
# before -- and it is 45% more material in the way of the light than 2.00 was.
FACE_T       = 2.90         # the face either side of a tick. 0.20 glows.
DIFF_SEAT_Z  = DIFF_WALL_CREST + FACE_T      # 21.93, where the face's top lands
CELL_DEPTH   = 2.00         # walled cell behind the face, unchanged

# Sam, v12: "The inside it now too long, make it the same length it was before."
#
# v11 derived this from where the display module's face was ASSUMED to be --
# seat 8.60 plus a bare 1.60 mm PCB -- and reached the collar to exactly there.
# It over-reached, which means the module's rim at the r=29 circle is thicker
# than a bare PCB. That matters more than it sounds: the diffuser's face rests on
# the base's land, so a collar that touches the module first holds the whole
# thing off that land and the clock sits proud. Reverted.
#
# COLLAR_LEN is what you actually measure on the printed part: how far the ring
# stands proud of the BACK of the face. It was 8.20 mm before v11 and v11 made it
# 8.83. Expressed this way it no longer moves when FACE_T does, which is how it
# drifted in the first place.
COLLAR_LEN    = 8.20         # ring protruding beyond the back of the face
COLLAR_EXTEND = COLLAR_LEN + FACE_T - DIFF_COLLAR_H          # 2.90
# If you want it to actually TOUCH the screen, this is the knob and the
# arithmetic is one to one: every 0.10 on COLLAR_LEN is 0.10 mm of reach. It sits
# at z=10.83 now; measure your module's rim at r=29 and the number you want is
#     COLLAR_LEN = 19.03 - (8.60 + that rim thickness)
# Too long is worse than too short: too short leaves the screen unclamped, too
# long stops the diffuser seating at all.
APER_FLARE   = 0.80         # the aperture opens out this much on every side
                            # behind the membrane, so the viewing angle survives

# --- and the hours, written on the face ---------------------------------------
# Debossed, not thinned: the Echo's markings are printed on a white face and its
# LEDs are what lights up. Set MARK_DEPTH to 0 and cut them to 0.20 instead if
# you would rather they lit.
# Everything here lives in r 35.2..38.7, which is the band between the plywood
# window's inner edge (35.0) and where the ticks start. It is 3.5 mm, which is
# what decides the text size.
MARK_RI, MARK_RO = 35.60, 38.20      # the 8 plain hour marks
MARK_W           = 1.00
MARK_RI_MAJ, MARK_RO_MAJ = 35.30, 38.50
MARK_W_MAJ       = 1.60
MARK_DEPTH       = 0.50
NUM_R            = 37.00             # numerals at 12, 3, 6 and 9
NUM_H            = 3.40
NUM_DEPTH        = 0.50
# All twelve, not four. Sam: "add the numbers from 1 to 12 on the diffuser that
# I can print in black on the 3D printer."
#
# Keyed by the HOUR, not by an angle. Where each hour lands is worked out in
# build_v2.numerals() from two facts that were measured, not assumed:
#   * +x is 12 o'clock on the BASE. Two independent features say so -- the
#     keyhole's entry hole is at r=38.5 and its narrow end at r=46.0 on the +x
#     axis, so the clock is lifted and dropped onto the screw, which only works
#     if +x is up; and the ring's lead slot and the USB window are both at -x,
#     which is where a cable should leave a wall clock.
#   * the diffuser is modelled face-at-z=0 and is installed TURNED OVER, so the
#     face reads from the far side -- hence mirror=True. See text_prism.
NUMERALS = {h: str(h) for h in range(1, 13)}              # hour -> what to write

# --- v5b: the LED band is REBUILT, not patched --------------------------------
# Sam's diffuser carries 183 non-manifold edges, and every one of them is in the
# band r 35.5..46.0, z 0.8..4.0: his two annular ribs are notched at each of the
# 24 cell-wall angles, and those notches are modelled with faces that do not
# pair up. Inside r=35.0 the mesh is perfect -- 0 bad edges, watertight.
#
# The band is exactly the part v5 replaces anyway (2 mm opaque face, radial
# slits), so rather than union new geometry onto broken geometry, keep his mesh
# only inside BAND_CUT_R and rebuild the band parametrically. Every number below
# is measured off his file by measure_uploaded.py / the probe in csg.py:
#   inner rib   r 35.4996 .. 36.6996, z 0..4.000
#   outer rib   r 44.7995 .. 46.0000, z 0..4.000
#   24 walls    1.000 mm thick (constant, not wedges), centres 7.5 + 15k deg
#               to within 0.0003 deg, r 36.70 .. 44.80, z 0..4.000
# Result: 0 bad edges, watertight, one body, volume agrees to 0.000%.
BAND_CUT_R    = 35.00       # Sam's mesh kept only inside this
BAND_FACE_RI  = 34.50       # new face starts 0.5 mm inside the cut, so the seam
                            # is an overlap inside solid material, not a butt
# BAND_TOP is 4.00 -- Sam's own height -- and v8 was WRONG to raise it to 6.00.
#
# v8 measured where the diffuser comes to rest by pushing it into the BARE base,
# with no LED ring and no display module in it, and found the crush ribs
# stopping it at z=21.52. From that it concluded the band had only 1.40 mm
# inside the bore and needed to be taller. Both halves of that were wrong.
#
# MEASURED properly, on the built files: the base's inner wall -- the one between
# the screen bore and the ring pocket -- tops out at z=19.03, and the diffuser's
# face lands on it. That is the axial stop, a 4.9 mm wide annular land at
# r 30.19..35.11. So the face sits at 19.03..21.03 and z_base = 21.03 - z_diff.
# Which puts the band's underside at:
#
#     band 4.00  ->  lands at z=17.03, LED ring top 15.00, clear by  2.03 mm
#     band 6.00  ->  lands at z=15.03, LED ring top 15.00, clear by  0.03 mm
#
# 0.03 mm is nothing. At 6.00 the band reaches the LED ring before the face
# reaches its stop, so the diffuser jams proud and rocks on the ring -- which is
# exactly what Sam reported: "now too tight and doesn't fit properly". At 4.00
# it clears the ring by 2.03 and the face seats on its land. check4 measures
# that clearance now, so this cannot happen again quietly.
BAND_TOP      = FACE_T + CELL_DEPTH   # 4.90. Derived, so the cell keeps its
                            # depth and the band keeps its clearance to the LED
                            # ring whatever FACE_T is set to.
RIB_I_RI, RIB_I_RO = 35.50, 36.70
RIB_O_RI      = 44.80       # outer rib now runs out to DIFF_OUTER_NEW
CELL_N        = 24
CELL_WALL_A0  = 7.50        # wall centres, degrees
CELL_WALL_T   = 1.00
CELL_WALL_RI  = 35.90       # 0.4 mm inside the inner rib -- ends buried, so no
CELL_WALL_RO  = 45.40       # razor sliver where a chord meets a 144-gon


# =============================================================================
# v5a — hold the S3 down, and bring a USB-C inlet out through the wall
# =============================================================================
# Sam: "make sure that the ESP32 S3 is held in properly and that the USB
#       connector can be connected externally from the outside of the wall.
#       I may or may not use a USB battery or USB power supply."

# --- 1. the beam over the USB end --------------------------------------------
# The ledges stop the board falling out the back. Nothing stopped it lifting
# INTO the clock -- 4.60 mm of float. A beam over the board's -x end fixes that.
# It sits ABOVE everything on the board (BOARD_TALL = 3.20 -> parts top out at
# z 4.00), so it cannot foul a connector or a soldered header whatever the
# board's exact layout: it only ever touches the board if the board lifts.
BEAM_X       = BOARD_X0          # -24.00, centred on the board's -x end
BEAM_W       = 3.00              # how much of x it covers
BEAM_Z0      = 4.20              # 0.20 mm above the tallest part on the board
BEAM_Z1      = 5.80
BEAM_PILLAR_Y = 15.50            # pillars stand on solid deck, outside the window
BEAM_PILLAR_W = 3.00

# --- 2. the keeper, over the far end -----------------------------------------
# The beam alone lets the board pivot about it. A tongue over the +x end takes
# that out -- but a fixed tongue there would block the tilt-in, so the tongue is
# on a separate printed part that goes on AFTER the board.
# ASSUMPTION, and it is one caliper glance to check: the last 2.00 mm of the
# board's +x end is bare PCB. On the DevKitC-1 the two 22-pin rows are 53.34 mm
# long on a 62.74 mm board, which leaves 4.70 mm clear at each end -- but if
# your board puts something there, raise KEEP_TONGUE_Z0 to 4.20 and it clamps
# over the top of it instead, with 0.20 mm of float.
KEEP_TONGUE_X1 = BOARD_X1        # 38.74, the board's +x end
KEEP_TONGUE_L  = 2.00
KEEP_TONGUE_HY = 9.00            # +/-9.00: inboard of the pad rows either side
KEEP_TONGUE_Z0 = 1.00            # board top is 0.80 -> 0.20 mm of float
KEEP_TONGUE_Z1 = 2.60
KEEP_PLATE_T   = 2.00            # plate against the deck's rear face
KEEP_SCREW_X   = 42.50
KEEP_SCREW_Y   = 19.50           # r = 46.72. 41.00/16.00 put it at r = 44.02,
                                 # which left 0.11 mm of wall between the pilot
                                 # and the tab window's outer edge at 42.66 --
                                 # the print checker found it. 46.72 is outside
                                 # the ring pocket (46.35) as well, so the pilot
                                 # runs in solid base for its whole depth.
KEEP_PLATE_X1  = 47.00
KEEP_PLATE_HY  = 23.00
KEEP_PLATE_R   = 50.40           # plate clipped to this, so it cannot touch the
                                 # housing's pocket wall at R_INNER = 50.99
KEEP_SCREW_D   = 3.30            # M3 clearance in the keeper
KEEP_SCREW_PIL = 2.50            # pilot in the base
KEEP_SCREW_DEP = 6.00
WINDOW_X1_EXT  = 42.00           # window carried past the board so the keeper's
                                 # riser has somewhere to pass

# --- 3. the USB-C inlet -------------------------------------------------------
# The board's own connector cannot reach the outside: from a board edge at
# x = -24 the plug ends up 30 mm short of the rim, and Espressif's own v1.1
# guide calls both ports Micro-USB while the clones sold as "DevKitC-1" have
# Type-C -- so nothing that depends on which connector the board carries is
# safe. The inlet is therefore its own USB-C socket, wired to the board's 5V and
# GND pins, which is how README section 2 already says to power it.
#
# VERIFIED PART: Adafruit ADA4090 "USB C Breakout Board - Downstream
# Connection", 20.4 x 14.2 x 5.0 mm, two 5.1 kohm resistors on CC1 so a charger
# or power bank actually turns 5 V on. A$5.40 inc GST at Core Electronics
# (backorder at the time of writing). NOT ORDERED.
USBC_PCB_L, USBC_PCB_W, USBC_PCB_H = 20.40, 14.20, 5.00
USBC_CLR      = 0.30
USBC_FACE_X   = -47.00           # where the socket's mouth sits: 7 mm inside the
                                 # rim, so the plug's overmold stands ~13 mm
                                 # proud and there is something to grip
# The PCB is lifted 0.60 mm off the deck on a shelf, purely so the plug channel
# clears the deck: the socket's mouth then centres on z 3.90 and a 7.20 mm
# channel around it starts at z 0.30, which is above the deck's top face.
USBC_Z        = 0.60             # underside of the breakout PCB
USBC_SHELF_HY = 5.00             # the shelf it rests on, inboard of the rails
USBC_RAIL_H   = 6.00             # rails: connector top is at 0.60 + 5.00 = 5.60
USBC_RAIL_HY  = 9.40
USBC_LIP_Z0   = 2.50             # PCB top is 2.20 -> 0.30 mm of float
USBC_LIP_Z1   = 4.00             # 1.50 thick: 0.80 was under the 1.20 minimum
USBC_LIP_HY   = 5.50             # clear of the 8.94 mm connector shell by 1.03
USBC_PORT_Z   = USBC_Z + 1.60 + (USBC_PCB_H - 1.60) / 2      # 3.90, the mouth
# The plug channel. USB-IF caps a Type-C plug's overmold at 12.35 x 6.50 mm;
# 0.65 / 0.70 of clearance on that, and the channel is deliberately NARROWER
# than the 14.20 mm PCB, so the breakout cannot be dragged out through it when
# the plug is pulled -- the PCB's own edge is the stop.
PLUG_W, PLUG_H = 12.35, 6.50
PLUG_CH_W, PLUG_CH_H = PLUG_W + 0.65, PLUG_H + 0.70      # 13.00 x 7.20
PLUG_CH_Z0   = USBC_PORT_Z - PLUG_CH_H / 2               # 0.30
USBC_BAY_X1  = -26.00            # +x end of the bay; the S3 window starts -24.45
WIRE_PORT    = (-38.0, -30.0, 10.0, 13.0)   # battery lead, beside the bay


# =============================================================================
# v6 — the S3 moves into the housing, the diffuser gets crush ribs, and there is
#      a 32-LED body and a desk stand
# =============================================================================
# Sam, after test-fitting v5:
#   "I dont want to use a breakout board for power, move the board more towards
#    the edge so that the power can be connected easily. Also, at the current
#    moment, the new housing is not deep enough to account for the cables coming
#    out of the screen and ESP32. Update the case so that it is at least 50mm
#    deep and the ESP32 sits in the other mini rear round clock housing."
#   "update the tolerance on the difuser, it's still too loose. I want it to be
#    press fit"
#   "build a stand for the clock to go in so that it can sit on a desk too"
#   "make another version for an LED ring ... that has 32 LED's. The outside
#    width is 111.85mm and the inside is 96mm"

# --- 1. the housing is now the electronics box --------------------------------
# v9: 25.00, not 50.00. Sam: "The housing can be 25mm deep, not 50mm anymore."
# That is his call and it is a big one, so the consequence is stated rather than
# buried: the board and its frame stand 7.40 mm off the pocket floor, which
# leaves 14.10 mm of clear plenum above it for the display ribbon and the ring
# leads. What it does NOT leave is room for a battery -- the Anker A1653 is
# 24.89 mm on its thinnest axis, so nothing like it fits in a 21.50 mm pocket
# any more. See BATTERY_MIN_HOUSING below.
HOUSING_DEEP  = 25.00                    # Sam: "can be 25mm deep, not 50mm"
POCKET_DEEP   = HOUSING_DEEP - PLATE_T   # 21.50 clear

# =============================================================================
# WHAT IS ACTUALLY ON THE S3 BOARD
# Espressif DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf, read as a drawing.
# This block exists because the retention has to land on bare board, and where
# that is depends on where the copper and the connectors are -- not on a guess.
#
#   DIMENSIONED on the drawing: 62.74 x 25.40 board, 2.54 pad pitch, pad rows
#   1.27 mm in from each long edge, and the two USB shells occupying the last
#   8.00 mm of the length.
#   MEASURED off the same drawing (scaled, so +/- 2%): pad OD about 1.70, the
#   shells 7.95 mm wide reaching to |y| = 10.54, and overhanging the board's
#   end by 0.87 mm.
#   DERIVED: 22 pins at 2.54 is a 53.34 mm row, so the two end margins sum to
#   62.74 - 53.34 = 9.40. With the connector-end margin at 8.00 the antenna-end
#   margin is 1.40 -- and 1.40 + 53.34 + 8.00 = 62.74 exactly, which is the
#   check that the reading is right.
#
# AND CRITICALLY: there are NO MOUNTING HOLES. The drawing shows two 22-pin
# rows and nothing else. So the board can only be captured mechanically.
# =============================================================================
BOARD_PAD_PITCH = 2.54
BOARD_PAD_N     = 22
BOARD_PAD_EDGE  = 1.27       # pad row centre, in from the long edge  (DXF)
BOARD_PAD_ROW   = 22.86      # so the two rows are 0.900 in apart     (DXF)
BOARD_PAD_OD    = 1.70       # so copper spans |y| 10.58 .. 12.28
BOARD_PAD_X0    = 7.960      # first pad centre, from the connector end (DXF)
BOARD_PAD_X1    = 61.300     # last pad centre                          (DXF)
BOARD_CONN_L    = 8.65       # the two USB shells own the first 8.65 mm (DXF)
BOARD_CONN_Y    = 10.81      # and reach this far out across the board  (DXF)
BOARD_CONN_W    = 9.40       # each shell body                          (DXF)
BOARD_CONN_OVER = 0.87       # allowance for the mouth standing proud of the edge
BOARD_MOD_END   = 55.33      # the WROOM module's far edge              (DXF)
BOARD_PAD_X_ANT = BOARD_L - BOARD_PAD_X1                               # 1.565
# The clear top surface, which is what the retention has to live on:
#   antenna end   0.55 mm -- and the WROOM module sits on it. Nothing can hook
#                 there, and nothing should: it is the antenna end.
#   connector end 7.15 mm long, in the two strips at |y| 10.54..12.70 outboard
#                 of the USB shells. THIS is where the board gets held down.
BOARD_CLEAR_ANT = BOARD_PAD_X_ANT - BOARD_PAD_OD/2                     # 0.715
BOARD_CLEAR_CON = BOARD_PAD_X0 - BOARD_PAD_OD/2                        # 7.11
# And the one that matters most, which the earlier reading missed entirely:
# between the pad rows, the board's TOP is bare from the module's far edge to
# the antenna end -- 7.53 mm long by 21.16 mm wide. That is where the antenna
# end gets held down, and it is clear whether or not headers are soldered on.
BOARD_CLEAR_ANT_L = BOARD_L - BOARD_MOD_END                            # 7.535
BOARD_CLEAR_ANT_Y = BOARD_PAD_ROW/2 - BOARD_PAD_OD/2                   # 10.58

# What the frame is built to swallow. The DXF is one board; Sam's is bought as
# an "ESP32-S3-DevKitC-1 N16R8" and the sellers' dimensions contradict each
# other flatly (70x28, 67x31, 55x35 -- all published, all different). The 0.900
# in pad rows are the one thing every DevKitC-1-shaped board must keep, and
# they force the width, so the width is trusted and the LENGTH is given room.
BOARD_L_MIN, BOARD_L_MAX = 61.30, 64.00
BOARD_W_MAX = 25.70

# The two numbers that made v9's mount unbuildable. An FDM slot comes out
# NARROWER than drawn and an FDM boss comes out FATTER, and a nominal clearance
# smaller than the first of these is not a clearance at all -- it is an
# interference fit that has been labelled a clearance. check2 now asserts it.
FDM_SLOT_UNDER = 0.40        # worst case a printed slot loses, across
FDM_BOSS_OVER  = 0.20        # worst case a printed boss gains

# --- the frame that holds it --------------------------------------------------
# v9 rebuild. What was there before was a tray, not a mount: the board rested on
# four posts at |y| = 5.50 with NOTHING locating it across, 0.50 mm of slop
# along, and the -x retainer sitting 3.40 mm above the board's top face -- so it
# could lift 3.4 mm at that end. Measured on the built file, not argued.
#
# What the mount actually has to resist is modest: the housing is closed and
# bolted, so the only real load is the USB plug pushing the board in +x. Every-
# thing else is rattle. So: rails locate it across, an end wall takes the plug
# load, and two snap fingers clamp the connector end down. The antenna end needs
# no clamp -- a 1.6 mm FR4 board 62.74 mm long is rigid, and an end that is held
# top, bottom and sideways cannot let the far end rise.
#
# NOTHING here touches the board's faces except the two snap lips, and those
# land in the connector-end clear strips, so it works whether or not header
# strips are soldered on.
BRD_POST_H    = 4.00         # PCB underside above the pocket floor; header
                             # tails from a 2.54 strip are about 3 mm
BRD_X0        = -48.50       # the connector end, at the 6 o'clock wall
BRD_X1        = BRD_X0 + BOARD_L         # 14.24, the antenna end
BRD_POST_D    = 5.00
BRD_POST_HY   = 6.50         # between the USB shells' end tabs (|y| 2.6 and
                             # 10.5) and well inboard of the pad rows
# v13. BRD_RAIL_CLR was 0.10 a side, and that is why the mount did not fit.
# A 25.60 slot for a 25.40 board reads as 0.20 mm of clearance and prints as an
# interference fit: a slot loses up to FDM_SLOT_UNDER across, so 25.60 comes off
# the plate somewhere between 25.20 and 25.50 and the board is WIDER than the
# hole it has to enter. Same mistake as the collar, same cure -- size the
# clearance so that the worst printed slot still clears the widest board, and
# let check2 assert it rather than trusting the nominal.
#     slot 26.20 nominal -> 25.80 .. 26.20 printed -> 0.40 .. 0.80 clear
BRD_RAIL_CLR  = 0.40         # per side. The rails touch only the board's 1.6 mm
                             # EDGE -- never a face -- so pads and solder
                             # fillets are irrelevant to them.
BRD_RAIL_Y    = BOARD_W/2 + BRD_RAIL_CLR                    # 13.10
BRD_RAIL_T    = 2.00
BRD_END_CLR   = 1.80         # board's antenna end to the end wall. Was 0.30,
                             # which printed as 0.00 .. 0.20 -- the second
                             # reason nothing would go in. At 1.80 the worst
                             # printed slot is still 64.27, so it swallows
                             # anything up to BOARD_L_MAX, and the board floats
                             # 1.40-1.70 in x. That float is the price of not
                             # knowing the length: it recesses the USB port by
                             # that much when a plug is pushed home, and a
                             # Type-C plug has about 6.5 mm of tongue to give.
BRD_SHIFT_Y   = BRD_RAIL_CLR # worst the board can sit off centre, either way
BRD_LIP_CLR   = 0.20         # over the board's top face
BRD_LIP_Z0    = BRD_POST_H + BOARD_T + BRD_LIP_CLR          # 5.80
BRD_LIP_T     = 1.60         # lip and rail height above that
BRD_RAIL_TOP  = BRD_LIP_Z0 + BRD_LIP_T                      # 7.40

# The snap fingers. Each is a WALL with a slot behind it, not a post: its long
# axis is x and it flexes in y, so both are in the print's XY plane. That is the
# whole point -- a finger standing up in z would put the bending stress straight
# across the layer bonds, which is where printed snap fits break. Printed rear-
# plate-down, a finger like this is just another vertical wall.
#
#   strain, straight cantilever:  e = 1.5 * Y * t / L^2
#     Y 1.60 mm deflection, t 1.50 thick, L 20.00 long  ->  0.90%
#   PLA yields around 1.5-2% and PETG higher, so this still has margin, and it
#   is well under the 8:1 length/thickness floor that gets quoted for PLA
#   (20/1.5 = 13:1).
#   force,  P = b*t^2*E*e / (6*L), b = 7.40 finger height, E ~ 2500 MPa
#     -> about 3.1 N a finger, 6.2 N to press the board home. A firm thumb.
#
# The lip is positioned by an ABSOLUTE |y|, not by a reach over the board, and
# that is the point. What limits it is not the board's edge, it is the USB-C
# shell: 9.40 mm wide, reaching |y| = 10.81, and the board can sit BRD_SHIFT_Y
# off centre, so anything closer in than 11.21 lands on a connector instead of
# on the board. 11.50 clears the worst case by 0.29 and still catches 0.80 mm
# of board edge with the board shifted the other way.
BRD_FING_L     = 20.00       # root to tip
BRD_FING_T     = 1.50        # thickness in the flexing direction
BRD_FING_X0    = 1.00        # tip, measured from the board's connector end
BRD_FING_YI    = 11.50       # the lip's inner face, as an absolute |y|
BRD_FING_OVER  = BRD_RAIL_Y - BRD_FING_YI                   # 1.60, derived
BRD_FING_GAP   = 2.00        # slot behind it, so it has somewhere to flex to
BRD_FING_LIP_L = 4.00        # length of the lip at the tip
BRD_FING_BURY  = 0.60        # lip buried into the finger rather than butted
BRD_FING_DEFL  = BOARD_W/2 + BRD_SHIFT_Y - BRD_FING_YI      # 1.60, what it flexes
BRD_FING_STRAIN = 1.5 * BRD_FING_DEFL * BRD_FING_T / BRD_FING_L**2      # 0.0090
BRD_FING_EMAX  = 0.015       # PLA's working limit. PETG is roughly twice this.
BRD_STOP_RI    = 11.50       # corner stops at the connector end: they butt the
                             # board's end face in the strips outboard of the USB
                             # shells (|y| 10.81) and clear the USB window
                             # (|y| 11.00) by 0.50 mm. Without them the board can
                             # walk toward the wall when a plug is pulled out,
                             # and jam in its own window.

# --- the antenna-end hood ----------------------------------------------------
# v9 left the antenna end unclamped, on the argument that a board held down at
# one end cannot lift at the other. That argument is wrong: the connector-end
# lips have BRD_LIP_CLR of slack over a 4.00 mm base, and 62.865/4.00 is a
# 15.7:1 lever, so 0.20 mm of slack at the lips is 3.1 mm of lift at the far
# end. It rattles.
#
# So the far end gets a hood. It is a WEDGE hanging off the end wall whose
# underside rises at 45 degrees going +x, which buys three things at once:
#   * its lowest point is a single edge, so the board still drops STRAIGHT
#     DOWN -- no tilting it in, no sliding it under anything;
#   * a 45 degree underside is self-supporting, so there is no bridge and no
#     overhang to print;
#   * the low edge sits 4.00 mm in from the wall, so any board from
#     BOARD_L_MIN to BOARD_L_MAX still passes under it.
# It lands between the pad rows, on the 7.53 x 21.16 mm patch of bare board
# behind the WROOM module, so it works with headers soldered on or off, and
# pointing either way.
BRD_HOOD_L     = 4.00        # how far the low edge stands in from the end wall
BRD_HOOD_Y     = 9.80        # |y| it spans -- inside the pad rows, worst shift
BRD_HOOD_ROOT  = 2.00        # its height where it meets the wall
BRD_HOOD_LAND  = 1.40        # and the flat it presents to the board. Without
                             # it the wedge comes to a knife edge, which is a
                             # sub-wall-thickness feather and a poor thing to
                             # bear on; with it the hood has a real 1.40 mm
                             # land, and check3 stops finding a thin region.
BRD_HOOD_RAMP  = 47.0        # degrees from horizontal, taken to the FAR corner
                             # of the buried end -- the hull's lower chain runs
                             # to that corner, not to the near one, so sizing
                             # off the near one lands you at 45.06 deg and one
                             # float32 rounding away from an unprintable face.

# the window the power lead comes in through, at 6 o'clock. 22 x 6 because
# which connector the board carries is still not a settled fact -- Espressif's
# v1.1 guide says Micro-USB, the boards sold as DevKitC-1 have two Type-C -- so
# the window clears either, in either position.
USB_WIN_W     = 22.00
USB_WIN_H     = 6.00
USB_WIN_Z     = BRD_POST_H + BOARD_T + BOARD_TALL/2 - USB_WIN_H/2   # above the floor

# A battery needs the deep housing back. Stated as a number so the builder and
# the checker use the same one.
BATTERY_MIN_HOUSING = PLATE_T + BRD_RAIL_TOP + BAT_T + BAT_TOP_CLR + 6.0

# --- 2. the deck is just a floor now ------------------------------------------
# With the board out of the base there is nothing to hold, so the deck goes back
# to being an annulus: it carries the mating face, the screw pilots, and gets
# out of the way of every cable.
DECK_RI       = 30.00

# --- 3. the diffuser press fit, done properly ---------------------------------
# 0.10 mm on diameter is inside a printer's own tolerance, which is why it still
# drops in. Crush ribs are the fix: clearance on the wall so it starts easily,
# interference only at eight narrow ribs that deform as it goes home.
# --- THE PRESS FIT, on the collar, inside, where the screen is ------------------
# MEASURED on the built base: R_DISP_POCKET (30.2788) is the circumradius of a
# 144-gon, so the flats -- which is what a round collar actually touches -- are
# at 30.19 at the mouth, opening very slightly to 30.24 further down. Sam's
# collar is 30.108 OD, so it has 0.08 mm of radial clearance in there.
#
# Six crush ribs take that to an interference. They are on the MAIN collar, not
# the 2 mm extension, and they sit between z 3.00 and 7.50 in the diffuser's own
# frame -- which is 4.50 mm of engagement, entirely inside the bore and entirely
# above the display module.
R_DISP_BORE     = 30.19      # MEASURED across the flats, not the param radius
# THE COLLAR IS TURNED DOWN. v10 left Sam's own 30.108 OD, which is 0.164 mm of
# clearance on diameter against a 30.19 bore -- and on an FDM printer that is not
# clearance at all. An external cylinder comes out 0.10-0.20 over on diameter and
# a bore 0.10-0.30 under, so that pair can easily print as an INTERFERENCE across
# the whole 190 mm of circumference. Six ribs on top of that were not a crush
# fit; they were a solid interference fit with lumps on it. Hence "still too
# tight" a third time.
# Turned to 29.90 there is 0.58 mm of clearance on diameter -- enough to swallow
# what both parts' printers do -- and the ribs are the only thing touching.
COLLAR_OD       = 29.60      # was Sam's 30.108, then 29.90
COLLAR_RIB_N    = 6
COLLAR_RIB_W    = 1.00       # tangential. Narrower crushes more easily than wide
COLLAR_RIB_H    = 0.05       # radial interference -> 0.10 mm on diameter
COLLAR_RIB_Z0   = 3.00       # in the diffuser's frame
COLLAR_RIB_Z1   = 8.00
COLLAR_RIB_LEAD = 2.00       # taper at the end that enters the bore first, which
                             # is the HIGH z end: the collar goes in tip first
COLLAR_RIB_BURY = 0.60       # into the collar, so the rib does not sit on a face
                             # coincident with it -- that does not survive float32
# v12, third time of asking: looser again. 29.90 with 0.20 mm of interference was
# still tight in Sam's hands, which says his printer is running the boss over
# and/or the bore under by more than the nominal figures allow for. So:
#   * the collar goes to 29.60 -- 1.18 mm of clearance on diameter. A printer
#     would have to be over half a millimetre out before the WALL touches
#     anything, which is the failure that cannot be tuned away by rib size.
#   * the ribs drop to 0.10 mm of interference on diameter, on 1.00 mm ribs, and
#     they now stand 0.64 mm proud of the wall -- a tall crush rib that can
#     deform a long way before anything binds.
# The clock hangs with the diffuser's axis horizontal, so gravity never pulls it
# out; the fit only has to resist being knocked. Light is fine.
#
# ONE KNOB. Too tight -> COLLAR_RIB_H = 0.00 (a slip fit on the ribs alone).
# Falls out -> 0.12. And print mini-round-clock-collar-gauges.stl first: three
# rings at 0.00 / 0.05 / 0.10, five minutes, and it tells you which one YOUR
# printer wants without committing a whole diffuser to it.
GUIDE_LED_CLR   = 0.40       # 60-LED only. Its band comes right down to the guide
                             # shelf, which is level with the LED tops by design --
                             # that is how an LED fires into the end of its strip.
                             # This relieves the band's underside over the ring's
                             # own radius so it rests on the shelf and not on the
                             # LEDs.
# --- the fit gauge -------------------------------------------------------------
# Three short rings of the collar, at three rib heights, so the fit can be found
# on a five-minute print instead of a whole diffuser. Each carries its own
# hundredths-of-a-mm number debossed on the top.
GAUGE_H         = 8.00       # tall enough to feel the fit, short enough to be quick
GAUGE_HS        = (0.00, 0.05, 0.10)     # radial rib heights to try
GAUGE_PITCH     = 68.00      # centres on the plate
GAUGE_NUM_H     = 4.00       # the number on top of each
DIFF_SEAT_CLR   = 0.20       # air between the 32/60 pocket fill and the underside
                             # of the diffuser's band, so they never share a face
DIFF_CHAMF      = 0.60       # chamfer where the band enters the ring pocket, and
                             # a matching one on the visible rim

# --- 4. the 32-LED ring, and the body it needs --------------------------------
RING32_OD, RING32_ID, RING32_N = 111.85, 96.00, 32
RING32_R      = (RING32_OD + RING32_ID) / 4          # 51.9625, the LED circle
# 111.85 will not go in a 107.99 body, so the body grows. Everything inside
# r = 46 is Sam's, untouched; everything outboard is rebuilt at the new size.
KEEP_R32      = 46.00
R_RING_I32    = RING32_ID/2 - 0.50                   # 47.50
R_RING_O32    = RING32_OD/2 + 0.50                   # 56.425
R_BODY32      = R_RING_O32 + 3.50                    # 59.925 -> OD 119.85
R_LIP_I32     = R_BODY32 - 2.00
WIRE32_HW     = 6.50         # slot from the new ring pocket down to the deck
RING32_PITCH  = 360.0 / RING32_N                     # 11.25 deg

# --- 5. the desk stand --------------------------------------------------------
STAND_TILT    = 10.00        # degrees back from vertical. 8 was upright enough
                             # to read as "not quite straight" rather than as a
                             # deliberate lean; 12 is unambiguous without
                             # looking like it is falling over.
                             #
                             # Tilt is not free: the clock's USB plug points at
                             # the desk 64 mm behind the front face, so every
                             # extra degree drops it 64*sin -- about 1.1 mm per
                             # degree here.
                             #
                             # 12 was tried first and check5 rejected it: the
                             # backward tip margin fell to 19 deg against a
                             # 20 deg floor. Leaning a clock back moves its
                             # centre of mass toward the heels, and raising
                             # STAND_LIFT to buy plug clearance raises the CoM
                             # and makes that worse -- the two fixes fight.
                             # 10 deg keeps both: the margin holds and the plug
                             # still clears on the original lift.
STAND_CLR     = 0.35         # on the clock's rim
STAND_WRAP    = 55.00        # half angle of the cradle, from bottom dead centre
STAND_LIFT    = 36.00        # air under the clock at the front face, and not a
                             # style choice. The board's own USB socket is 1 mm
                             # inside the rim, so a plug's 20 mm overmold stands
                             # about 21 mm proud -- at 6 o'clock, pointing at the
                             # desk, 64 mm back from the front face where the
                             # 10 degree tilt has already dropped the rim
                             # 11.1 mm. 36 still leaves about 5.7 mm under the
                             # plug -- check5 measures it. A right-angle USB
                             # lead only needs about 8 mm of that: drop this to
                             # 24 if that is what you will use.
STAND_TOE_TARGET = 22.5      # design angle for tipping FORWARD, same idea as
                             # TAIL_TARGET is for backwards. A shallower clock
                             # sits further forward in its own cradle, so at
                             # HOUSING_DEEP = 25 the 240 mm stand's forward
                             # margin fell to 18 deg against a 20 deg floor --
                             # the 108 and 120 mm ones never came close and get
                             # no toe at all. Unlike TAIL_TARGET this one is
                             # exact: foot_front = -(h*tan(tilt) + toe/cos(tilt))
                             # is closed form, and it agrees with what check5
                             # measures on the built file to a tenth of a degree.
STAND_FOOT    = 0.60         # the stand is built upright, tilted back and then
                             # trimmed by the desk plane, and a plane through a
                             # tilted solid leaves knife edges wherever a face
                             # meets it at a shallow angle -- 0.01 mm at the
                             # front corners and along the heel, measured on the
                             # built file. Everything below this height is
                             # replaced by a straight extrusion of the section
                             # AT this height, so every edge on the footprint is
                             # vertical and nothing tapers to nothing.
STAND_FOOT_OFF = 0.10        # and pulled in by this, so the cutting wall is
                             # strictly inside the solid rather than tangent to it
STAND_NOTCH_BACK = 28.00     # the cable slot only opens over the last 28 mm +
                             # the stop wall, so the two legs stay joined by the
                             # shell under the front of the cradle
STAND_WALL    = 5.50         # at the cradle's top edges
STAND_STOP_RI = 46.00        # rear stop wall, inner radius
STAND_STOP_T  = 3.00
STAND_NOTCH_HW = 9.00       # cable slot at 6 o'clock, through everything
STAND_ARCH_HW = 42.00        # the arch that lightens it and carries the lead
STAND_SHELL   = 6.00         # material left under the cradle at the crown
STAND_FLARE   = 9.00         # the outer face flares out over this height


# =============================================================================
# v7 — a 240 mm clock for the 60-LED ring, with perspex light guides
# =============================================================================
# Sam: "I have some perspex that can be used to make the LED's look longer than
#       they are ... make the clock larger by using the perspex in strips to
#       make the light shine down it. I would like to make the clock of the
#       60LED ring 24cm wide, and use the perspex, or other material to make the
#       LED's shine further away from the LED"
#
# MATERIAL, against the standing rule ("never PVC or acrylic containing
# chlorine ... cast acrylic or plywood only, and tell me which and why"):
# Perspex is a brand of PMMA. PMMA contains NO chlorine and is safe to cut and
# to laser. PVC -- sold as "vinyl", and what unlabelled "acrylic-look" sheet
# often turns out to be -- is the one that releases hydrogen chloride. So the
# rule is satisfied by Perspex-branded or any labelled cast/extruded PMMA, and
# violated by anything unlabelled. Cast PMMA is the better of the two: extruded
# crazes and engraves poorly.
#
# CUTTING, and this one is already in the project's own findings: the Glowforge
# Aura is a ~5 W DIODE laser and cannot cut clear, white or translucent acrylic
# at all -- those materials are transparent at 445 nm and the beam goes straight
# through (enclosure/MATERIALS.md). So the strips CANNOT be cut on the Aura.
# They come off a table saw, a bandsaw or a scroll saw, or out of 6 mm acrylic
# rod, or they are printed instead -- see build_light_guides().

RING60_OD, RING60_ID, RING60_N = 172.00, 156.00, 60
RING60_R      = (RING60_OD + RING60_ID) / 4       # 82.00, the LED circle
R_BODY60      = 120.00                            # Sam: "24cm wide"
R_RING_I60    = RING60_ID/2 - 0.50                # 77.50
R_RING_O60    = RING60_OD/2 + 0.50                # 86.50
R_LIP_I60     = R_BODY60 - 3.50
SCREW_R60     = 68.00                             # inboard of the ring: at any
                                                  # larger radius a pilot bores
                                                  # into the pocket or a guide
# --- the z stack has to change to make room for a 3 mm strip -------------------
# 24/32 body:  ring floor 11.80, ring 3.20, diffuser 4.00, face recess at 19.00
# 60 body:     ring floor 10.50, ring 3.20, diffuser 5.30, face recess at 19.00
#              ...so the guide channel is 3.30 deep and the face above it 2.00
BAND_TOP60_    = None        # (set below, once FACE_T and GUIDE_T are known)
GUIDE_T        = 3.00        # the perspex: 3 mm sheet, the same as the plywood
GUIDE_W        = 6.00
GUIDE_CLR      = 0.35
BAND_TOP60     = FACE_T + GUIDE_T + GUIDE_CLR     # 5.35 of diffuser
# Derived from DIFF_SEAT_Z, not from Z_RECESS. The 60's whole vertical stack
# hangs off where the diffuser's face actually comes to rest, and that is
# 21.03 -- its underside on the base's inner wall crest at 19.03 -- not 19.00.
# Getting that wrong by 2.03 mm would have left every perspex strip rattling.
GUIDE_SHELF    = DIFF_SEAT_Z - BAND_TOP60         # 15.68, what the strips rest on
Z_RING_FLOOR60 = GUIDE_SHELF - (PCB_T + LED_H)    # 12.48, so the LED tops are
                                                  # level with the strip's underside
GUIDE_CH_RI    = 79.00       # the CHANNEL starts inboard of the LED circle, so
                             # the LED at r=82 fires into the space above it
GUIDE_CH_RO    = 113.60      # ...and runs past the strips, for the printed
                             # guide part's connecting ring
GUIDE_RI       = 86.50       # the STRIP itself starts at the ring's outer edge,
GUIDE_RO       = 112.00      # so it never rests on an LED. 25.5 mm long.
# the aperture over each guide is a slot thinned to one layer, and it WIDENS
# going out, to pay for the light falling off along the strip
APER_W_IN, APER_W_OUT = 1.40, 3.00
APER_RI, APER_RO = 80.00, 110.50    # starts inboard of the LED, so the LED
                                    # itself is the head of the lit line
# the hours go inboard of the ring on this body -- there is no room for them
# between the guides
MARK60_RI, MARK60_RO = 70.60, 73.20
MARK60_RI_MAJ, MARK60_RO_MAJ = 70.30, 73.50
NUM60_R       = 72.00
NUM60_H       = 5.00
# --- and the 240 mm annulus has to be hollow, or it is a kilogram of PLA ------
HOLLOW_FLOOR  = 3.00         # floor plate under the whole annulus
HOLLOW_RIBS   = 12           # radial ribs tying floor to walls
HOLLOW_RIB_W  = 3.00
HOLLOW_WALL   = 2.50         # either side of the ring pocket


# =============================================================================
# v8 — the wire gap on every size, and all twelve numerals in two colours
# =============================================================================
# Sam: "update the main clock bases so that there is a gap between the middle and
#       the LED ring so that the cables connecting the LED ring dont need to bend
#       straight down ... update all the sizes for this."
#       "add the numbers from 1 to 12 on the diffuser that I can print in black
#       on the 3D printer. Make them the same font as the Amazon Echo wall clock."
#
# THE FONT. The Echo Wall Clock is set in Amazon Ember, Amazon's own brand
# typeface. It is proprietary, licensed to Amazon, and not installed here -- I
# checked rather than guessed, and matplotlib cannot find it. What is available
# is Liberation Sans (Arial-metric), FreeSans (Helvetica-metric) and DejaVu Sans.
# Ember is a humanist sans, so of those three Liberation Sans is the closest
# neutral match; it is NOT the same face and I am not going to pretend it is.
# If you have an Ember licence, or want any other face, drop the .ttf somewhere
# and put its path in NUM_FONT_FILE -- it is the only line that changes.
NUM_FONT        = 'Liberation Sans'
NUM_FONT_FILE   = None        # e.g. '/path/to/AmazonEmber-Medium.ttf'
NUM_WEIGHT      = 'bold'      # at these sizes a regular weight prints too thin
                              # to hold a second filament cleanly

# The numerals sit just INBOARD of the LED apertures, which is where the Echo
# has them. Their outer edge is NUM_MARGIN inside the aperture's inner edge, on
# every body, so they never break into the 0.20 mm aperture membrane -- and on
# the 32 that is the only band wide enough anyway: between its ring ID (96) and
# the LED circle there is only 2 mm.
NUM_MARGIN      = 1.20        # clear space between a numeral and the dots
# 5.00, not 3.60. MEASURED on the built inlay: at 3.60 mm cap height Liberation
# Sans Bold has a 0.66 mm stem, which is 1.6 beads from a 0.4 mm nozzle -- one
# perimeter and a gap-fill, and a visible seam down every stroke in a second
# colour. At 5.00 the stem is 0.92 mm, two clean beads. It is 4.6% of a 108 mm
# face against the Echo's 3.2% of a 203 mm one, and a small clock needs the
# proportionally bigger numeral anyway. The band inboard of the ticks runs
# 30.95..37.55, so 5.00 still leaves 2.55 mm clear of the collar.
NUM_H_24        = 5.00
NUM_H_32        = 6.00
NUM_H_60        = 9.00
# printed in black: the numerals are ALSO written as their own STL, a set of
# solids 0.50 mm thick that exactly fill the debossed pockets. Load the diffuser
# in Bambu Studio, right-click -> Add part -> Load the numerals file, and assign
# it filament 2. Both are exported in the same coordinates, so they land in
# register with no moving about.
NUM_INLAY_T     = NUM_DEPTH   # 0.50 -- at 0.20 mm layers that is 2 layers +.5
