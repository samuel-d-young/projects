// =============================================================================
// cleat.scad — wall half of the French cleat. Print in PETG or PLA.
// =============================================================================
// Screws to the wall; the body hooks over it. Deliberately WIDER than the
// body's receiver so there is left-right adjustment when hanging — you level
// the clock by sliding it, not by re-drilling.
//
// Two fixings on a 60mm horizontal pitch, which lands on a single stud OR
// takes two plasterboard anchors. Countersunk for a flat seat.
// =============================================================================
include <params.scad>

W = 110; H = 18; T = 8;
HOLE_PITCH = 60;

module cleat() {
    difference() {
        // The 45deg wedge, mating face pointing up and away from the wall.
        translate([-W / 2, -H / 2, 0])
            difference() {
                cube([W, H, T]);
                translate([-1, H + 1, T + 1])
                    rotate([225, 0, 0])
                        cube([W + 2, H * 3, H * 3]);
            }
        // Countersunk fixings
        for (x = [-HOLE_PITCH / 2, HOLE_PITCH / 2])
            translate([x, 0, -0.01]) {
                cylinder(h = T + 1, d = 4.5 + FDM_HOLE_FUDGE);
                translate([0, 0, T - 2.5])
                    cylinder(h = 2.6, d1 = 4.5, d2 = 9.5);
            }
    }
}

cleat();

// ---------------------------------------------------------------------------
// Orientation : flat face down. Layer : 0.2mm. Walls : 4. Infill : 40%.
// This part carries the whole clock — do not print it sparse.
// Supports    : none.
// ---------------------------------------------------------------------------
