// =============================================================================
// body.scad — main enclosure. Print in PETG (or PLA, see MATERIALS.md).
// =============================================================================
// Stack, measured back from the front face at z = 0:
//
//   z 0.0 .. 8.0    diffuser sits here, its glowing top flush with the rim
//   z 8.0           LED tops touch the back of the diffuser cells
//   z 9.6 .. 11.2   the ring PCB, resting on an annular shelf
//   z 11.2 .. 18.0  electronics bay — ESP32 lives in the middle
//   z 18.0 .. 20.0  back panel + cleat receiver
//
// The face screws on from the FRONT. That is the whole point of the layout:
// four M3 screws and the face, diffuser and ring are all accessible with the
// body still hanging on the wall. Nothing here requires taking it down.
//
// NOT YET RENDERED OR PRINTED — no OpenSCAD in the environment it was written
// in. Open it, F5 to preview, and sanity-check before committing filament.
// =============================================================================
include <params.scad>

// Depths of each feature, front-referenced.
DIFF_Z      = DIFF_H;                     // 8.0  back of the diffuser pocket
LED_TOP_Z   = DIFF_Z;                     // 8.0
PCB_FRONT_Z = LED_TOP_Z + RING_LED_H;     // 9.6
PCB_BACK_Z  = PCB_FRONT_Z + RING_PCB_T;   // 11.2
BAY_BACK_Z  = BODY_DEPTH - BACK_T;        // 18.0

SHELF_W     = 2.0;    // how far the PCB shelf projects under the board
POST_D      = 8.0;    // face screw post diameter
CABLE_W     = 10.0;   // cable exit slot
CABLE_H     = 6.0;

module ring_pocket() {
    // Where the diffuser and the LED ring live. One pocket, two depths.
    // Diffuser pocket is slightly wider than the diffuser so it drops in.
    translate([0, 0, -0.01])
        difference() {
            cylinder(h = DIFF_Z + 0.01, d = DIFF_OD + 2 * RING_CLEAR);
            cylinder(h = DIFF_Z + 0.02, d = DIFF_ID - 2 * RING_CLEAR);
        }
    // PCB pocket, from the back of the diffuser to the shelf.
    translate([0, 0, DIFF_Z - 0.01])
        difference() {
            cylinder(h = (PCB_BACK_Z - DIFF_Z) + 0.01, d = CHANNEL_OD);
            cylinder(h = (PCB_BACK_Z - DIFF_Z) + 0.02, d = CHANNEL_ID);
        }
    // Clear space behind the shelf, so the ring's solder pads and wiring have
    // somewhere to go rather than being crushed against the back panel.
    translate([0, 0, PCB_BACK_Z - 0.01])
        cylinder(h = BAY_BACK_Z - PCB_BACK_Z + 0.01,
                 d = CHANNEL_OD - 2 * SHELF_W);
}

module screw_posts() {
    // Four posts at 45deg, matching the face's fixing holes exactly.
    for (i = [0 : SCREW_POSTS - 1]) {
        a = 45 + i * (360 / SCREW_POSTS);
        translate([SCREW_POST_R * cos(a - 90), SCREW_POST_R * sin(a - 90), 0])
            difference() {
                cylinder(h = BAY_BACK_Z, d = POST_D);
                // Pilot hole for an M3 self-tapping screw. Deliberately
                // UNDERSIZE (M3 - 0.5) so the thread bites into the plastic:
                // this is a screw-into-plastic boss, not a clearance hole.
                translate([0, 0, -0.01])
                    cylinder(h = 12, d = SCREW_M - 0.5 + FDM_HOLE_FUDGE);
            }
    }
}

module cleat_receiver() {
    // The body half of a 45deg French cleat. The wall half is cleat.scad.
    // A cleat means the clock lifts straight off if it ever HAS to come down,
    // but sits dead flat and self-levelling when hung.
    w = 90; h = 18; t = 8;
    translate([-w / 2, -h / 2, BAY_BACK_Z - 0.01])
        difference() {
            cube([w, h, t]);
            // 45deg undercut, opening downward
            translate([-1, -1, -1])
                rotate([45, 0, 0])
                    cube([w + 2, h * 2, h * 2]);
        }
}

module body() {
    difference() {
        union() {
            // Outer shell
            cylinder(h = BODY_DEPTH, d = BODY_OD);
            cleat_receiver();
        }

        ring_pocket();

        // Electronics bay — the middle is otherwise solid, and the ring's
        // 156mm hole means there is a lot of free volume in there.
        translate([0, 0, PCB_BACK_Z - 0.01])
            cylinder(h = BAY_BACK_Z - PCB_BACK_Z + 0.01, d = ELEC_BAY_D);

        // Cable exit, at 6 o'clock so the lead runs straight down the wall.
        translate([-CABLE_W / 2, -BODY_OD / 2 - 1, BAY_BACK_Z - CABLE_H])
            cube([CABLE_W, BODY_WALL + 4, CABLE_H + 1]);

        // Vent slots. The ring is only ~2.4W at the brightness cap, so this is
        // about letting the ESP32's regulator breathe, not the LEDs.
        for (i = [0 : 11])
            rotate([0, 0, i * 30])
                translate([0, BODY_OD / 2 - BODY_WALL / 2 - 1,
                           BAY_BACK_Z + BACK_T / 2])
                    cube([12, BODY_WALL + 4, 1.6], center = true);
    }
    screw_posts();
}

body();

// ---------------------------------------------------------------------------
// PRINT SETTINGS
// ---------------------------------------------------------------------------
// Orientation : front face DOWN on the plate. The front is the only surface
//               anyone sees, and face-down gives it the plate finish with no
//               supports needed anywhere.
// Material    : PETG preferred. See MATERIALS.md — a PLA part on a sunlit
//               kitchen wall can creep, and the ring channel is a press fit.
// Layer       : 0.2mm
// Walls       : 3 perimeters (BODY_WALL is 2.4 = 3 x 0.8 line width)
// Infill      : 15% gyroid
// Supports    : none needed in this orientation
// Est. time   : ~7h, ~110g  (UNVERIFIED — not sliced, check in Bambu Studio)
