// =============================================================================
// diffuser.scad — 60-cell light guide. Print in WHITE PLA.
// =============================================================================
// This is the part the Glowforge cannot make. The Aura is a ~5W DIODE laser
// and clear, white and translucent acrylic are all largely transparent to its
// wavelength — Glowforge's own Aura material set is opaque acrylic only. A
// diffuser is white by definition, so it moves to the printer.
//
// That is not a consolation prize. A printed diffuser can do something a flat
// acrylic sheet cannot: give every pixel its OWN cell with a baffle between
// it and its neighbours. That is what keeps a 60-point dial reading as 60
// discrete points instead of a smeared glow.
//
// WHITE PLA specifically. Natural/clear PLA pipes light along the layer lines
// and bleeds between cells; white PLA is loaded with TiO2 and scatters it.
//
// NOT YET RENDERED OR PRINTED. Preview before printing.
// =============================================================================
include <params.scad>

CELL_A = 360 / NUM_LEDS;                          // 6 deg per pixel
MEAN_R = (DIFF_OD + DIFF_ID) / 4;                 // radius of the LED circle

module baffles() {
    // One radial wall per pixel boundary, offset half a cell so each wall sits
    // BETWEEN two LEDs rather than on top of one.
    for (i = [0 : NUM_LEDS - 1])
        rotate([0, 0, i * CELL_A + CELL_A / 2])
            translate([-DIFF_WALL / 2, DIFF_ID / 2 - 0.5, DIFF_TOP_T])
                cube([DIFF_WALL,
                      (DIFF_OD - DIFF_ID) / 2 + 1,
                      DIFF_H - DIFF_TOP_T]);
}

module diffuser() {
    union() {
        // The glowing face. Thin on purpose: 2 layers at 0.2mm is translucent
        // enough to light up and opaque enough to hide the LED die.
        difference() {
            cylinder(h = DIFF_TOP_T, d = DIFF_OD);
            translate([0, 0, -0.01])
                cylinder(h = DIFF_TOP_T + 0.02, d = DIFF_ID);
        }
        // Outer and inner skirts, which also locate the part in the body.
        difference() {
            cylinder(h = DIFF_H, d = DIFF_OD);
            translate([0, 0, -0.01])
                cylinder(h = DIFF_H + 0.02, d = DIFF_OD - 2 * 1.2);
        }
        difference() {
            cylinder(h = DIFF_H, d = DIFF_ID + 2 * 1.2);
            translate([0, 0, -0.01])
                cylinder(h = DIFF_H + 0.02, d = DIFF_ID);
        }
        baffles();
    }
}

diffuser();

// ---------------------------------------------------------------------------
// PRINT SETTINGS
// ---------------------------------------------------------------------------
// Orientation : diffusing face DOWN on the plate. Gives a smooth, even
//               surface and prints the 0.8mm top as the first two layers with
//               no bridging.
// Material    : WHITE PLA. Not natural, not clear — see the note above.
// Layer       : 0.2mm
// Top/bottom  : bottom layers = 2 EXACTLY. More and it stops glowing; this is
//               the one setting that decides whether the clock looks good.
// Walls       : 2
// Infill      : 0% (the baffles are the structure)
// Supports    : none
// Est. time   : ~2h, ~25g  (UNVERIFIED — not sliced)
//
// TUNING: if pixels bleed into each other, raise DIFF_H (deeper cells) in
// params.py. If pixels look like harsh dots rather than glowing segments,
// lower DIFF_H or add a third bottom layer. Print one and look at it before
// deciding — this is a judgement call no amount of maths settles.
