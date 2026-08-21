# Materials — and why

## The short version

| Part | Machine | Material | Why |
|---|---|---|---|
| Face / bezel | Glowforge Aura | **3 mm plywood** | Opaque, so a diode laser cuts it. Looks right in a kitchen. |
| Diffuser | Bambu | **White PLA** | The Aura physically cannot cut what a diffuser needs to be. |
| Body | Bambu | **PETG** (PLA acceptable) | Dimensional stability on a warm wall. |
| Cleat | Bambu | PETG or PLA | Carries the load; print it solid-ish. |

## The laser answer: plywood, and it isn't a preference

The brief said "cast acrylic or plywood only, and tell me which and why".

**Plywood — because the Aura is a ~5 W *diode* laser, not a CO₂ laser, and it
cannot cut clear, white or translucent acrylic at all.** Those materials are
largely transparent to the diode's wavelength: the beam passes through instead
of depositing enough energy to cut. Glowforge's own material set for the Aura
is limited to *opaque* acrylic — teal, black, red, orange, green, purple.

That matters because it rules acrylic out of the one job it would have been for.
**A diffuser is white or translucent by definition.** So the diffuser cannot be
lasered on this machine at any power or speed, and it moves to the printer.

What is left for the laser is the face and bezel, which want to be opaque
anyway — and plywood cuts and engraves beautifully on a diode laser, takes the
hour markers as a clean engrave, and looks better on a kitchen wall than
acrylic would.

### This turns out better, not worse

A printed diffuser can do something a flat acrylic sheet cannot: give each of
the 60 pixels its **own cell with a baffle between it and its neighbours**.
That is what makes a 60-point dial read as 60 discrete points rather than a
smeared glow. Lasered acrylic would have been one flat sheet with no cell
separation.

### Use white PLA specifically

Not natural, not clear. Natural PLA pipes light along its layer lines and bleeds
between cells; white PLA is loaded with titanium dioxide and scatters it. The
single most important slicer setting on the whole build is **bottom layers = 2**
on the diffuser. More than that and it stops glowing.

## The PVC warning stands

Correct, and worth restating: **never PVC, vinyl, or any chlorine-containing
sheet in a laser.** It releases hydrogen chloride gas, which corrodes the
optics and rails, and is genuinely hazardous to breathe. Nothing in this build
is PVC.

The same caution applies to unknown "acrylic-look" sheet from marketplace
sellers — if it is not labelled cast acrylic (PMMA) from a known supplier,
don't put it in the machine. Extruded acrylic is safe to cut but engraves
poorly and crazes; cast is the one to buy if acrylic is ever wanted for a
different part.

## Body: PETG over PLA

Both will work, and PLA is easier. PETG is preferred for two reasons:

1. **A clock on a wall that catches afternoon sun gets warm.** PLA starts to
   soften around 55–60 °C, and the part carries the ring in a press-fit channel
   plus its own weight on a cleat. PETG's glass transition is ~80 °C.
2. The ring channel is a **fit**, and PLA creeps under sustained load more than
   PETG does. A channel that is snug on day one can loosen.

If the clock is going somewhere shaded and PLA is what's loaded, use PLA — this
is a preference, not a requirement.

## Plywood thickness

3 mm nominal. Real plywood varies — measure the actual sheet and put it in
`params.py` as `FACE_T` if it differs, since the screw posts are sized from it.

The Aura cuts 3 mm ply comfortably. Draft ply with voids will leave uncut
patches on the bottom face; birch is worth the extra for a part where the cut
edge is visible all the way round.
