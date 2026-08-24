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
BOARD_L, BOARD_W, BOARD_T = 62.74, 25.40, 1.60
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
    return f"""
  base outer            {2*R_BODY:.2f} mm dia
  Sam's base depth      {Z_FRONT - Z_BACK:.2f} mm      (z 0 .. 22)
  + deck                {DECK_T:.2f} mm      (z {Z_DECK:.2f} .. 0)
  + rear housing        {REAR_H:.2f} mm      (z {Z_REAR:.2f} .. {Z_DECK:.2f})
  = total clock depth   {Z_FRONT - Z_REAR:.2f} mm
  battery clear depth   {POCKET_D:.2f} mm
  battery max size      {max_battery(38):.0f}x38, {max_battery(45):.0f}x45, {max_battery(50):.0f}x50 mm, up to {POCKET_BATTERY-1.5:.0f} mm thick
  battery fitted        {BAT_L:.0f} x {BAT_W:.0f} x {BAT_T:.0f} mm, centred at x={BAT_CX:+.1f}
  S3 board sits at      x {BOARD_X0:.2f} .. {BOARD_X1:.2f}, y +/-{BOARD_W/2:.2f}
  ...its parts top out  z {Z_BACK - 0.80 + BOARD_T + BOARD_TALL:.2f}, and the display seat is at z {Z_SEAT:.2f}
  clearance above it    {Z_SEAT - (Z_BACK - 0.80 + BOARD_T + BOARD_TALL):.2f} mm
"""

if __name__ == '__main__':
    print(summary())
    for nm, x, y in [('board -x corner', BOARD_X0, BOARD_W/2), ('board +x corner', BOARD_X1, BOARD_W/2)]:
        print(f'  {nm}: r = {math.hypot(x,y):.3f}')

# --- board window details ----------------------------------------------------
LEDGE_END   = 3.00          # ledge depth at the two short ends only
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
DIFF_COLLAR_RI, DIFF_COLLAR_RO = 27.9164, 30.1080
DIFF_COLLAR_H = 8.200

# press fit: the ring pocket wall is at 46.3516 and the diffuser was 46.000, so
# it had 0.35 mm of radial slop -- 0.70 on diameter. This takes it to a light
# interference. Back it off to 0.00 for a slip fit if it will not go in.
DIFF_FIT      = 0.05        # radial interference, i.e. 0.10 mm on diameter
DIFF_OUTER_NEW = R_RING_O + DIFF_FIT            # 46.4016

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
COLLAR_EXTEND = 2.00
COLLAR_EXT_RI, COLLAR_EXT_RO = 28.05, 29.95     # inset both faces 0.13/0.16 so
                            # the extension does not share a surface with the
                            # collar it grows from
