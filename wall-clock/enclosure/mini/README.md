# Round clock enclosure — 24-LED ring + 360×360 display

Sized to the **measured** Mokungi ring: **92.0 mm OD / 71.0 mm ID**.

That 71 mm centre is what makes this design work — a 1.85″ round display is
~48 mm across, so it drops into the middle with ~11.5 mm clearance per side.
At the 51 mm inner diameter of a smaller 24-ring it would not have fitted at all.

## Print these

| File | Material | Notes |
|---|---|---|
| `body.stl` | PETG or PLA | Front face **down**. No supports. 108 mm dia × 22 mm, ~118 cm³. |
| `diffuser.stl` | **White PLA** | Diffusing face **down**. **Bottom layers = 2 exactly.** 0% infill, no supports. |
| `backcover.stl` | any | Closes the S3 bay. 20 mm hole for the USB-C lead. |

`bottom layers = 2` on the diffuser is the single setting that decides whether
this looks good. More and it stops glowing.

## Laser this

`face.svg` — 3 mm plywood, 112 × 112 mm sheet.
Red `#FF0000` = **cut** (display aperture, ring window, outline).
Black fill = **engrave** (twelve hour ticks).

Cut the **outline last** so the part stays supported in the sheet — SVG order
is only a hint, set the step order in the Glowforge UI.

**Plywood, not acrylic.** The Aura is a ~5 W diode laser and cannot cut clear,
white or translucent acrylic at all. Full reasoning in `../MATERIALS.md`.

## Layout, front to back

```
  z 0.0 ..  3.0   plywood face, dropped into a recess, 2 mm proud lip retains it
  z 3.0 ..  8.0   display pocket (centre)     |  z 3.0 .. 9.0  diffuser (ring)
  z 8.0 .. 22.0   ESP32-S3 bay               |  z 9.0         LED tops
                                              |  z 10.6 .. 12.2  ring PCB
  z 12.2 .. 22.0  solid web behind the ring
```

The display sits **behind** the plywood aperture, resting on a 2 mm ledge. The
S3 goes in the bay behind it, reachable through the back cover's 20 mm hole.

## Before you print

```bash
$EDITOR build.py        # check DISP_MODULE_D / DISP_T against your panel
python3 build.py --preview
```

The ring numbers are measured and confirmed. **The display numbers are not** —
`DISP_MODULE_D = 48.0` and `DISP_T = 5.0` are typical 1.85″ values, but module
outline and thickness vary by vendor, especially with a touch controller or a
bulky FPC connector. Measure yours before committing 118 cm³ of filament.

## How these STLs were made

No OpenSCAD in the environment they were written in, so `mesh.py` builds the
meshes directly: revolve a 2-D profile around Z, add boxes for the baffles,
write binary STL. Each part is validated by computing its signed volume with
the divergence theorem — a closed, correctly-wound mesh gives a positive volume
matching the analytic value.

That check paid for itself: the first run produced **negative** volumes of
exactly the right magnitude, i.e. every part was inside-out. Silent, and a
slicer would have made nonsense of it.

The baffles **overlap** the diffuser's revolved rings rather than being
booleaned in. Slicers union overlapping closed shells at slice time, so this
prints correctly, but a mesh checker will call it non-manifold. Expected — run
your slicer's repair if it objects.

The face is held by a **friction fit** in the recess, not screws: the mesh
builder has no CSG to model pilot holes. A dab of tape holds it if you stand it
up. The 60-LED production body (`../body.scad`) has proper modelled posts,
because OpenSCAD can subtract them.
