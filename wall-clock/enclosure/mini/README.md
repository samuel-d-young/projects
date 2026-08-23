# Mini test clock enclosure — 24-LED ring

For the bench rig: Wemos D1 mini (or the S3) + a 24-LED WS2812B ring.

## Print these

| File | Material | Notes |
|---|---|---|
| `mini-body.stl` | PETG or PLA | Front face **down** on the plate. No supports. ~36 cm³. |
| `mini-diffuser.stl` | **White PLA** | Diffusing face **down**. **Bottom layers = 2 exactly.** No supports, 0% infill. |
| `mini-backcover.stl` | any | Plugs into the back; 16 mm hole for the USB lead. |

## Laser this

`mini-face.svg` — 3 mm plywood, 84 × 84 mm sheet. Red `#FF0000` = **cut**,
black fill = **engrave**. Cut the outline **last** so the part stays supported.

**Plywood, not acrylic** — the Glowforge Aura is a ~5 W diode laser and cannot
cut clear, white or translucent acrylic at all. Full reasoning in
`../MATERIALS.md`.

## Measure the ring first

```bash
$EDITOR build.py        # correct RING_OD / RING_ID at the top
python3 build.py --preview
```

`RING_OD = 66.0` / `RING_ID = 51.0` are the standard 24-LED ring dimensions
(the Adafruit NeoPixel Ring 24 is 66.0 / 51.0 mm and the generic clones follow
it). **Not confirmed against a Mokungi datasheet.** Put calipers on yours before
printing — everything else follows from those two numbers.

## Assembly

1. Ring drops into the pocket, LEDs facing forward.
2. Diffuser sits on top of the ring, cells over the LEDs.
3. Plywood face drops into the 3 mm recess; the 2 mm proud lip retains its edge.
4. Back cover plugs into the central opening.

The mini uses a **friction fit** where the 60-LED build uses screw posts. That
is a deliberate difference, not an oversight: this rig gets opened constantly
during development, and there is no CSG in the mesh generator to model pilot
holes. A dab of tape or three dots of hot glue holds the face if you stand it
up. The production body (`../body.scad`) has proper modelled posts because
OpenSCAD can subtract them.

## How these STLs were made

No OpenSCAD in the environment they were written in, so `mesh.py` builds the
meshes directly: revolve a 2-D profile around Z, add boxes for the baffles,
write binary STL. Each part is validated by computing its signed volume with
the divergence theorem — a closed, correctly-wound mesh gives a positive volume
matching the analytic value. All three pass.

The baffles **overlap** the diffuser's revolved rings rather than being
booleaned into them. Slicers union overlapping closed shells at slice time, so
this prints correctly, but a mesh checker will call it non-manifold. That is
expected. If your slicer objects, run its repair function.
