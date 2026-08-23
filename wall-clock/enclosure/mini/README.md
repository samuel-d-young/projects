# Round clock enclosure — 24-LED ring + 360×360 display

All dimensions measured, not estimated.

| | |
|---|---|
| Ring | 92.0 OD / 71.0 ID, 24 LEDs, 10.67 mm pitch |
| Display | GC9B72, 60 mm round PCB, 55 mm screen, 4 mm thick |
| Tab | 40 mm wide, 67 mm overall top-to-bottom |

## Why the display sits 6.4 mm back

The tab is a rectangle on a round board, so its **corners** set its reach, not
its midline:

```
midline reach = 67 − 60/2            = 37.00 mm
corner radius = hypot(40/2, 37)      = 42.06 mm
LED circle                           = 40.75 mm
```

The corners land **1.3 mm past the LEDs**. There is no rotation that avoids
this — the tab cannot share the LED plane at all, so the module is seated
behind the ring PCB and the tab passes through a slot underneath it.

That costs screen depth, and the stack was tuned to give as much back as
possible: the diffuser is **4 mm rather than 6**, because every millimetre of
diffuser pushes the ring back and comes straight off the screen's viewing depth.

6.4 mm sounds like a lot and isn't. With a 54 mm aperture the recess only
shadows the screen edge past about 85° off-axis; head-on it is invisible.

## Print these

| File | Material | Notes |
|---|---|---|
| `body.stl` | PETG or PLA | Front face **down**. No supports. 108 mm dia × 22 mm, ~118 cm³. |
| `diffuser.stl` | **White PLA** | Diffusing face **down**. **Bottom layers = 2 exactly.** 0% infill, no supports. Now 4 mm tall, not 6. |
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
                      CENTRE (display)          RING
  z  0.0 ..  3.0      plywood face, in a recess, 2 mm proud lip retains it
  z  3.0 ..  7.0      pocket bore               diffuser, 4 mm, 24 cells
  z  7.0                                        LED tops
  z  8.6 .. 10.2                                ring PCB
  z 10.2 .. 11.4                                pocket floor (1.2 mm)
  z  9.4 .. 13.4      display module (4 mm), rim resting on the shelf at 13.4
  z 11.4 .. 13.4      TAB SLOT — 83 deg wide, out to r 42.7, under the ring
  z 13.4 .. 22.0      ESP32-S3 bay
```

**The tab slot is local in both axes** — it opens out to the tab's corner radius,
but only over the tab's clock angle and only across the 2 mm of depth the tab
occupies. Widening the whole pocket instead would delete the ring and diffuser
seats at that angle and leave a visible gap in the light ring.

The diffuser needs **no** notch: the tab is entirely behind the ring, so every
cell keeps its baffles and the ring of light is unbroken.

## Before you print

```bash
$EDITOR build.py        # check DISP_MODULE_D / DISP_T against your panel
python3 build.py --preview
```

Everything is measured now. The one assumption left is **`DISP_TAB_T = 1.6`**,
which is the bare PCB with the 10-pin header **desoldered**. Leave the header on
and the tab is ~10 mm thick, the slot no longer fits it, and the module has to
move back another 9 mm into a well you cannot read.

Desolder both headers — the display's 10-pin and the ring's 4-pin — and solder
wires flat to the pads. It is the highest-value five minutes in the build.

`DISP_TAB_ANGLE` sets which clock position the tab points; 0 is 12 o'clock.
Point it wherever the ring's wires are not.

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
