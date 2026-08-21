# Enclosure

Parametric. **Every dimension comes from `params.py`** — including the ones
baked into the laser file and the OpenSCAD parts.

## When the ring arrives: measure it first

The 172 / 156 mm figures are corroborated by three resellers but **not** by a
manufacturer datasheet, and 60-LED rings exist at other sizes. Put calipers on
it, then:

```bash
$EDITOR params.py          # correct RING_OD / RING_ID / RING_PCB_T
python3 generate.py --preview
```

That rewrites `face.svg` (the Glowforge file), rewrites `params.scad` (which
the `.scad` parts include), re-runs every geometry check, and re-renders
`preview.png`. Then re-export STLs from OpenSCAD.

**Do not hand-edit `params.scad` or `face.svg`** — both are generated and your
edits will be overwritten.

## Files

| File | What |
|---|---|
| `params.py` | The only file you edit. Every dimension, with the fits explained. |
| `generate.py` | Emits `face.svg` + `params.scad`, asserts the geometry, renders a preview. |
| `face.svg` | **Glowforge**: 3 mm plywood face. Generated. |
| `body.scad` | **Bambu**: main enclosure, PETG. |
| `diffuser.scad` | **Bambu**: 60-cell light guide, WHITE PLA. |
| `cleat.scad` | **Bambu**: wall half of the French cleat. |
| `MATERIALS.md` | Why plywood on the laser and white PLA for the diffuser. |

## Glowforge: colour → operation

The SVG is real-world scale (1 unit = 1 mm, with `mm` on width/height), so it
imports at the right size without scaling. Glowforge groups by colour and you
assign the operation in the UI:

| Colour | Operation |
|---|---|
| Red `#FF0000` | **Cut** — window apertures, fixing holes, outline |
| Black `#000000` fill | **Engrave** — the twelve hour ticks |

**There is no text in the file, deliberately.** Glowforge does not embed fonts,
so an SVG `<text>` node renders with whatever gets substituted, or not at all.
Every mark is geometry. If you want numerals, add them in a vector editor and
**convert text to paths before uploading**.

Cut the outline **last** so the part stays supported in the sheet — set the
step order in the Glowforge UI, since SVG order is only a hint.

## Servicing without taking it down

This is the part the design is actually organised around.

The cleat stays on the wall. The **face screws on from the front** with four
M3s, and behind it the diffuser lifts out and the ring is right there. The
ESP32 sits in the middle bay — inside the ring's own 156 mm hole — with its USB
port facing forward.

So: four screws, and you can reflash, rewire or swap the ring **with the clock
still hanging**. Nothing needs to come off the wall to change anything.

The fixings sit at 45°, deliberately between hour markers rather than on one.

## Status

**Not yet printed, cut, or rendered.** The environment this was written in has
no OpenSCAD, so the `.scad` files have never been previewed — open them and
press F5 before committing filament. The SVG *has* been generated and visually
checked, and all geometry checks pass, but it has not been cut.
