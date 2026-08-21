"""Single source of truth for every enclosure dimension.

Both the OpenSCAD parts and the Glowforge SVG are generated from these numbers.
Change them here, re-run generate.py, and re-render the .scad files.

!! MEASURE THE RING WHEN IT ARRIVES. !!
The 172/156 figures are corroborated by three resellers but NOT by a
manufacturer datasheet, and 60-LED rings exist at 170mm and other sizes.
Put calipers on it, correct RING_OD / RING_ID / RING_THICKNESS below, and
regenerate. Everything downstream follows automatically.
"""

# ---------------------------------------------------------------------------
# THE RING — measure these
# ---------------------------------------------------------------------------
RING_OD = 172.0          # outer diameter of the PCB
RING_ID = 156.0          # inner diameter of the PCB
RING_PCB_T = 1.6         # PCB thickness
RING_LED_H = 1.6         # LED package height above the PCB (5050 = 1.6mm)
NUM_LEDS = 60

# ---------------------------------------------------------------------------
# FITS
# ---------------------------------------------------------------------------
# Radial slop around the PCB. 0.75mm total is a comfortable slip fit for FDM;
# tighten to 0.4 if your printer is well calibrated and you want no rattle.
RING_CLEAR = 0.75
# Printers under-size holes and over-size pegs. This is added to every hole.
FDM_HOLE_FUDGE = 0.2
# Laser kerf. The Aura's beam removes material, so cut lines sit on the true
# geometry and the operator compensates in the UI if a press fit is needed.
# Nothing here press-fits into plywood, so this is documentation only.
LASER_KERF = 0.2

# ---------------------------------------------------------------------------
# BODY (3D printed)
# ---------------------------------------------------------------------------
BODY_WALL = 2.4          # 3 perimeters at 0.4mm nozzle / 0.42 line width
BODY_RIM = 12.0          # radial material outside the ring
BODY_DEPTH = 20.0        # front face to back face
BACK_T = 2.0             # thickness of the back panel
ELEC_BAY_D = 140.0       # clear diameter in the middle for the ESP32
SCREW_POSTS = 4          # face fixings
SCREW_M = 3.0            # M3
SCREW_POST_R = 92.0      # radius the fixings sit on (at 45deg, between ticks)

# ---------------------------------------------------------------------------
# DIFFUSER (3D printed, WHITE PLA — see MATERIALS.md for why not acrylic)
# ---------------------------------------------------------------------------
DIFF_H = 8.0             # cell depth: taller = smoother, shorter = crisper
DIFF_TOP_T = 0.8         # 2 layers at 0.4 — thin enough to glow, thick enough
                         # to be opaque-ish. THIS is the diffusing surface.
DIFF_WALL = 1.0          # baffle between adjacent pixels

# ---------------------------------------------------------------------------
# FACE (laser-cut 3mm plywood)
# ---------------------------------------------------------------------------
FACE_T = 3.0
FACE_SPOKES = 4          # bridges holding the centre disc in the window
FACE_SPOKE_W = 6.0
TICK_MINOR_W = 2.0
TICK_MAJOR_W = 3.5
TICK_MINOR_L = 5.0
TICK_MAJOR_L = 9.0
# Ticks live on the INNER disc pointing outward-to-inward, not on the outer
# rim. The centre disc is 154mm of otherwise-dead plywood, and putting the
# markers there keeps the bezel slim instead of forcing a 210mm face.

# ---------------------------------------------------------------------------
# MACHINE LIMITS — asserted by generate.py, do not silently exceed
# ---------------------------------------------------------------------------
BED_XY = 256.0           # Bambu P1S and X2D are both 256 x 256
LASER_XY = 305.0         # Glowforge Aura printable area, 12in x 12in


# ---------------------------------------------------------------------------
# DERIVED — do not edit, these follow from the above
# ---------------------------------------------------------------------------
LED_CIRCLE_D = (RING_OD + RING_ID) / 2.0
LED_PITCH = 3.14159265358979 * LED_CIRCLE_D / NUM_LEDS

CHANNEL_OD = RING_OD + RING_CLEAR          # pocket the PCB drops into
CHANNEL_ID = RING_ID - RING_CLEAR
CHANNEL_DEPTH = RING_PCB_T + 0.2

BODY_OD = RING_OD + 2 * BODY_RIM
DIFF_OD = RING_OD
DIFF_ID = RING_ID
WINDOW_OD = RING_OD + 2.0                  # face aperture, shows the diffuser
WINDOW_ID = RING_ID - 2.0
FACE_OD = BODY_OD
TICK_OUTER_R = WINDOW_ID / 2 - 2.0   # ticks run inward from here
