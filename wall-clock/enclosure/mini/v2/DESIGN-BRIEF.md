# mini-round-clock enclosure — design brief

**Read this first if you are picking this project up cold.** It is written for
another Claude session. It tells you what the design is, what the rules are, and
which of them were learned the hard way. `README.md` next to it is the full
narrative; this is the orientation.

---

## 0. There are no sketches

Nothing here was drawn. There is no CAD file, no DXF, no parametric feature
tree. The STLs are **generated**:

| | |
|---|---|
| `params.py` | every dimension, each with a note saying whether it was **measured**, **dimensioned from a datasheet**, **derived**, or **chosen** |
| `csg.py` | watertight-by-construction primitives, plus the float32 healing that makes the file on disk the thing that was checked |
| `build_v2.py` | builds all 17 parts by constructive solid geometry |
| `check1..5` + `runchecks.sh` | five verification passes that **measure the built STLs**, not the code that made them |
| `sketch_sections.py` | slices the built STLs and annotates them from `params.py` — the closest thing to a drawing, and it cannot drift from the part |

So "the sketch" is `params.py` + `build_v2.py`. If you change a number in
`params.py` and re-run `build_v2.py` and `runchecks.sh`, you have made a design
change and verified it. That is the whole workflow:

```
python3 measure_uploaded.py    # re-derive params from Sam's STLs, if he sends new ones
python3 build_v2.py            # write the STLs and 3MFs
./runchecks.sh                 # five passes; non-zero exit if anything is wrong
python3 sketch_sections.py     # the dimensioned drawing
```

---

## 1. What the thing is

A wall clock that replaces an Amazon Echo Wall Clock. A WS2812B LED ring shows
the minutes/hours as lit dots; a round LCD in the middle shows the time and
weather; an ESP32-S3 drives both and talks to Home Assistant over ESPHome.

It exists in **three sizes**, all from the same code, differing only by a
`Body` object in `build_v2.py`:

| | 24-LED | 32-LED | 60-LED |
|---|---|---|---|
| ring OD / ID | 92 / 71 | 111.85 / 96 | 172 / 156 |
| clock diameter | 107.99 | 119.85 | **240.00** |
| light guides | — | — | perspex strips, so each LED reads 30 mm long |

Five printed parts per clock: **base**, **housing**, **diffuser**, **numerals**
(second filament), **desk stand** (optional). Plus a **collar fit gauge** that is
not part of the clock.

---

## 2. The coordinate system — get this right or nothing else lands

- **z = 0 is the BACK of Sam's base.** The front of the clock is **z = 22.00**.
  The housing hangs below, to z = −27.40.
- **+x is 12 o'clock. −x is 6 o'clock.** This was not assumed. Two independent
  features prove it: the wall-hanger keyhole's entry hole is at r = 38.5 and its
  narrow end at r = 46.0 on the **+x** axis, so the clock is lifted and dropped
  onto the screw — which only works if +x is up; and the LED ring's lead slot and
  the USB window are both at **−x**, which is where a cable should leave a wall
  clock.
- Viewed from the front, **up = +x and right = −y.** So hour *h* sits at
  −30·h degrees in the base's frame.
- **The diffuser is modelled in its OWN frame**, face at z = 0, everything else
  behind it. It is installed **turned over**: `z_base = DIFF_SEAT_Z − z_diff`.
  This is why its numerals are mirrored in the model — see §5.

---

## 3. The one relationship the whole assembly hangs off

**The diffuser's face rests on a land in the base at z = 19.03**, a 4.9 mm wide
annulus at r 30.19–35.11 between the screen bore and the ring pocket. That, and
not the press fit, is what sets how deep the diffuser goes.

```
DIFF_WALL_CREST = 19.03            measured on the built base
DIFF_SEAT_Z     = 19.03 + FACE_T   where the diffuser's outer face ends up
```

Everything that has to line up with the diffuser is **derived from
`DIFF_SEAT_Z`** — `BAND_TOP`, `COLLAR_EXTEND`, and the 60-LED body's entire
vertical stack (`GUIDE_SHELF`, `Z_RING_FLOOR60`). Two separate bugs were caused
by one of these being frozen as a literal while something upstream moved. **If
you change `FACE_T`, do not hand-edit anything downstream of it.**

Two hard ceilings, both asserted by `check2` §9:

1. `DIFF_SEAT_Z ≤ Z_FRONT` — the face lives in a 2.97 mm recess between the land
   at 19.03 and the front at 22.00. `FACE_T` cannot exceed 2.97.
2. The collar tip must not reach past the display module's face. **Too long is
   worse than too short**: a collar that touches the module first holds the whole
   diffuser off its land and the clock sits proud.

---

## 4. Rules learned the hard way — these are not style preferences

### Geometry / meshing

- **Float32 is the enemy.** STL stores vertices as float32; two points a boolean
  left 1e-5 apart collapse and punch a hole. `finalise()` quantises *before*
  checking, so the file on disk is the thing that was verified. Never bypass it.
- **Bury, don't butt.** Butting two surfaces at exactly the same coordinate
  usually survives; *overlapping into a coplanar face* does not. Bury the feature
  into solid material by 0.5–1.0 mm instead.
- **Never make a cutter tangent to a surface.** A cone starting exactly at a rib
  crest is tangent along a line and leaves a sliver per rib — 6 bad edges and
  `NotManifold`. Start it 0.4 mm outside.
- **A shell with fewer than 4 faces cannot enclose volume**, but trimesh's
  divergence-theorem volume returns a large number for it anyway. `drop_debris`
  judges by face count as well as volume.
- **Sealed cavities count as extra shells** and cannot drain — vent them.

### Printing

- Every part prints **without support** in its stated orientation, and the
  checkers enforce it. A face within 15° of horizontal is a **bridge**, judged by
  span; only a genuinely sloped face is an overhang.
- **A snap arm built up the Z axis bends across the layer bonds**, which is where
  printed snaps shear off. Every flexing feature here is a *wall with a slot
  behind it*, so its length and its bending are both in the layer plane.
- **A crush-rib fit is only a crush-rib fit if the wall behind the ribs is
  genuinely clear.** This one cost three iterations. On an FDM printer an
  external cylinder comes out 0.10–0.20 **over** on diameter and a bore 0.10–0.30
  **under**, so a nominal 0.16 mm clearance can print as a full-surface
  interference — and then the rib height is not the fit and turning it down does
  nothing. `check2` now asserts the *ratio*: wall clearance ≥ 4× rib
  interference, and ≥ 0.80 mm absolute.
- **After the second time a dimension comes back wrong, stop shipping a better
  dimension and ship a way to measure.** Hence
  `mini-round-clock-collar-gauges` — three 8 mm rings at three rib heights, 9 g,
  five minutes.

### Measuring

- **A fit measured against one part of an assembly is not a fit measurement.**
  The worst bug in this project came from bisecting the diffuser's resting
  position against a *bare* base — no LED ring, no display module — so the crush
  ribs were the only obstacle present. The measurement was careful, repeatable
  and wrong, and the "fix" it justified drove the band 2.00 mm into the LED ring.
- **`R_DISP_POCKET` (30.2788) is the circumradius of a 144-gon.** A round collar
  touches the **flats**, at 30.19. Probe the built mesh, don't read the nominal.

---

## 5. Things a fresh session will get wrong if not told

- **The numerals are mirrored on purpose.** The diffuser is read from the far
  side, so `text_prism(..., mirror=True)` swaps the glyph's x and y. Two
  reflections cancel, digit order included, so "12" reads 12 and not 21.
  `check4` tests it by probing the **"10"**: its left digit is solid (the 1) and
  its right digit is hollow (the 0). If the layout were unmirrored those swap.
- **The numerals are a second filament**, not a deboss to be painted. One
  function emits both the pockets and the solids that fill them, in the same
  coordinates.
- **The typeface is Liberation Sans Bold, not Amazon Ember.** Ember is Amazon's
  proprietary brand face and is not installable — checked, not assumed.
  `NUM_FONT_FILE` is the one-line swap.
- **The ESP32-S3-DevKitC-1 has NO mounting holes.** Its pad rows are 1.27 mm in
  from each long edge, so copper reaches within 0.42 mm of them, and the antenna
  end has 0.55 mm of clear board with the WROOM module on it. The **only** place
  anything may touch is the connector end — 7.15 mm of clear board in the strips
  at |y| 10.54–12.70.
- **Sam's own meshes are inputs, not outputs.** `base_in.stl` and
  `diffuser_in.stl` are his; the build keeps his geometry where it is good and
  rebuilds only what it must. His diffuser carries 183 non-manifold edges, all in
  the band at r 35.5–46.0 — that band is rebuilt, the rest is kept.
- **PVC / chlorine-containing acrylic is a standing safety rule.** Cast acrylic
  (PMMA, no chlorine) or plywood only. The Glowforge Aura is a ~5 W diode laser
  and **cannot cut clear/white/translucent acrylic at all** — verified.

---

## 6. What is verified and what is not

`README.md` §11 has the full list. The short version:

**Verified by running it** — every part is a closed, single-body,
self-intersection-free solid whose two volume calculations agree to 0.0000%;
nothing of Sam's is removed except the screw pilots and the wire gap; each ring
drops into its pocket; the board is located on all six degrees of freedom; the
diffuser clears the LED ring by 2.03 mm at its seat; no part introduces an
overhang below 45° or an unsupported bridge over 25 mm.

**Not verified** — *nothing here has been printed and fitted by the author.*
The collar fit has been called too tight three times, which is why it now ships
with a gauge. The display module's rim thickness at r = 29 is still unmeasured
and it is what sets the collar length. The snap fingers' strain and force are
beam theory at E ≈ 2500 MPa, not a bench test.

---

## 7. If you are asked to change something

1. Change the number in **`params.py`**, not in `build_v2.py`. If the number you
   want is derived, change what it derives from.
2. `python3 build_v2.py && ./runchecks.sh`. All five must pass.
3. If a check fails, **read what it measured** before touching the check. Three
   times in this project a failing check was correct and the design was wrong.
   Once, a check was reading the wrong height and had been passing for weeks
   because it had slack to hide in.
4. If you relax a check, say so out loud and say why. Do not tune a threshold to
   make a failure disappear.
5. Regenerate `sketch_sections.py` and the renders, update `README.md` and
   `../../../BUILD-LOG.md`, and commit.
