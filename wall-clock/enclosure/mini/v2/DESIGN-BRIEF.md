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

Six printed parts per clock: **base**, **housing**, **diffuser**, **numerals**
(second filament), **board clamp** (+ 2 x M3 x 10), **desk stand** (optional).
Plus two **fit gauges** that are not part of the clock.

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
2. The collar tip must not reach past the display module's face — which is at
   `Z_SEAT + DISP_T` = **12.60**, not at `Z_SEAT + DISP_TAB_T` = 10.20. The tab
   is the flat ear that sticks out of the module; the collar lands at r 28..30,
   on the module's front face, 2.40 mm higher. `check2` asserted against the tab
   for three versions and passed a collar that was 1.77 mm inside the screen.
   `COLLAR_LEN` is derived off `DISP_T` now. **Too long is worse than too
   short**: a collar that touches the module first holds the whole diffuser off
   its land and the clock sits proud.

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
- **A nominal clearance is not a clearance.** An FDM slot comes off the plate up
  to `FDM_SLOT_UNDER` (0.40 mm) narrower than drawn and a boss up to
  `FDM_BOSS_OVER` (0.20) fatter. Anything tighter than that is an interference
  fit that has been labelled a clearance, and it will not go together. This has
  now caused two separate failures — the collar, and the S3 mount, where the
  rails were drawn 0.10 mm a side clear of a 25.40 board and printed *narrower
  than it*. Both are now asserted against the worst printed case, not the
  drawing.
- **Locate a feature by the thing that actually limits it.** The S3's snap lips
  were placed as a reach over the board's edge and fouled the USB-C shell; they
  are now placed by an absolute |y| taken from the shell. If a dimension has a
  real constraint, derive it from the constraint, not from something adjacent.
- **A chamfer is not a thin wall.** A ray along the surface normal runs to zero
  at the tip of any 45° lead-in, while every layer that prints it stays full
  width. `check3.layer_width()` measures the largest circle that fits inside
  each layer before calling anything a defect — the snap lips read 0.21 mm along
  the normal and 2.40 mm in every layer.
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

- **Assert against the surface the part actually touches.** Two separate
  failures now: the collar checked against the module's TAB when it lands on the
  module's FACE, and the S3's snap lips positioned off the board's EDGE when
  what limits them is the USB-C shell. If a feature has a real constraint,
  measure against the constraint, not against something adjacent that happens to
  be easy to name.
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
- **The board is 63.27 x 28.19 — Sam's calipers, not a datasheet.** It is 2.79
  mm wider than Espressif's DevKitC-1 v1.1 outline, so it is not that board, and
  the vendors publish 70x28, 67x31 and 55x35 for the same part number. Nothing
  in the frame depends on the pad row spacing: the snap lips land in the first
  5 mm before any copper, the clamp lands at |y| <= 9.80 inboard of any row, the
  posts at |y| = 6.50.
- **The antenna end is held by a SCREWED BAR, not by anything moulded.** That is
  what makes the length window 60.0-64.2 instead of +/-0.5 mm: a screwed bar
  goes on after the board, so nothing overhangs, there is no assembly move, and
  it does not care how long the board is. Two M3 x 10 self-tappers, both landing
  beyond the longest board the bay takes.
- **The ESP32-S3-DevKitC-1 has NO mounting holes**, and every number about it
  here comes from **parsing Espressif's v1.1 DXF**, not from reading a picture
  of it or a vendor listing. `62.865 × 25.400 × 1.60`; pad rows 22 a side at
  2.54 pitch, **22.86 mm apart (0.900 in exactly)**, so copper reaches within
  0.42 mm of each long edge; two **USB-C** shells 9.40 wide reaching |y| 10.81.
  Two places anything may touch: the connector end, in the strips at
  |y| 10.81–12.70 before the copper starts at 7.11 mm along; and the last
  **7.53 × 21.16 mm** of the top face, behind the module and between the pad
  rows. Nothing may cross the pad rows at any height — headers may point up.
- **Vendor dimensions for this board are worthless.** The same part is published
  as 70 × 28, 67 × 31 and 55 × 35 by different sellers. The 0.900 in pad rows
  force the width, so the width is trusted; the length is not, and the frame
  takes **60.0–64.2**. `mini-round-clock-board-gauge` settles it in 15 g.
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
The collar fit has been called too tight three times and the S3 mount "doesn't
fit at all" once, which is why both now ship with a gauge. The display module's rim thickness at r = 29 is still unmeasured
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

---

## The back-stand does not work, and the reason is measurable

Sam, 2026-09-05: "The current back stand doesn't work. The placement of the
ESP32 is too close to the wires coming out from the screen and the ESP32 can't
be placed there. I want the clock to be enclosed."

**The screen's wires leave the back of the clock at x = +41.** That is not a
guess: mapping the housing's cable port through the same transform the stand
builds the clock with puts its mouth at

| body | port mouth, stand frame |
|---|---|
| 24 LED | x +41, y 28.7, z 49.5 |
| 32 LED | x +41, y 25.3, z 56.5 |

and the buttresses stand at **|x| 40.0 .. 46.5, up to z 48**. So the port is
directly outboard, level with the top of a buttress, and **50 mm above the
board's top face at z 6.6** — with a buttress between the two. The wires have
to come out sideways, over a buttress, and down. There is nowhere for the
board's connector end to be, which is exactly what Sam hit.

None of the seven checks caught it because every one of them models the clock
as a plain cylinder. `check7` proves the stand never touches that cylinder;
nothing looked at what comes OUT of it. **A checker that models a part by its
envelope cannot see a hole in it.**

### What fits inside the clock, measured

Probing a 66 x 32 mm footprint through the assembled stack:

| gap | 24 LED | 32 LED |
|---|---|---|
| deck to back cover | z -3 .. -7.5 | z -3 .. -7.5 |
| back cover to housing plate | z -12 .. -16.5 (4.5 mm) | z -12 .. -13 (1.5 mm) |

The board needs 4.8 mm (1.6 PCB + 3.2 of USB shell and module). So it does NOT
fit in today's housing on either body — the 24 is marginal, the 32 is not close.
Housing depth is 25 mm on the 24 and 20 mm on the 32; **option A below needs
about +12 mm.**

### Four ways out

`enclose-options.png` draws the first three to scale.

* **A — deepen the rear housing and put the board inside the clock.** The wires
  never leave. The stand becomes a plain cradle: no bay, no gate, no zip ties.
  Costs 12 mm of depth and a reprint of the housing and the stand.
* **B — a closed plinth under the clock.** Clock body untouched; a lidded box
  under it holds the board. Needs ~60 mm of wire down a channel.
* **C — a lidded pod on the back plate.** Least change; a visible backpack.
* **D — turn the clock 90 degrees in the stand so the port points DOWN**, and
  add `rotation:` to the display so the picture stays upright. No new parts at
  all, and the wires then drop straight into the trench and the cable gate the
  stand already has. It does not enclose anything -- it is the make-it-work-
  tonight option.

### Built: option A

Sam, 2026-09-05: "I like the deeper housing idea. It could be up to 85mm deep."

`mini-round-clock-housing{tag}-deep`, **31.5 mm deep, whole clock 55.9 mm front
to back**. Not 85 -- the board is 4.80 mm lying flat and the loom wants a bend
radius, not a hall. 28 mm of clear pocket leaves 26.4 mm of plenum over the
board and the clock still reads as a disc. `HOUSING_S3_POCKET` is one number if
a battery ever goes back in (`BATTERY_MIN_HOUSING` is 43.29).

It reuses `build_rear_housing` for the shell, keyhole, screw pillars, vents and
mains gate, with `with_board=False`. **The mount inside that function is sized
for 63.27 x 28.19 and Sam's board is 64.00 x 30.00** -- it would never have gone
in. Everything else is new:

| | why it is where it is |
|---|---|
| board along **y** | the keyhole is cut through the rear plate at x 34..46. A board along x wants its hold-down at \|x\| 36, y 0 -- straight through it |
| USB end at **-y**, 1.60 mm off the wall | a centred 64 mm board leaves **19 mm** between its connector and the wall, and no USB-C plug bridges that. The old mount accepted it |
| rails on the **edge** | 1.60 mm of PCB edge only, never a face, so pads and solder fillets are irrelevant |
| far-end lip | slide the far end under, drop the USB end in |
| two cable ties | recessed into the rear plate, same pattern as the back-stand: a pair of plain holes puts the loop between them and the clock hangs on a ridge of nylon |

`mini-round-clock-backstand{tag}-deep` goes with it. `build_backstand` takes
`deep=True` and everything follows from one line -- the clock's back face is
22.6 mm further back, so the trench, the buttresses and the front lip all move
with it. Build the shallow stand for a deep clock and the buttresses stand
straight through the housing.

**The vents had to move.** First build put one 10 degrees from the USB window
and the two merged into a single 24 mm hole where 13 was drawn -- manifold,
clean, and wrong, with the vent no longer a vent. They are pushed clear by the
sum of the two half-widths plus a margin, and check8 measures the opening off
the mesh rather than trusting the parameter.

`check8_deep_housing.py` tests the JOURNEY, not the shape -- board in, plug in,
wires through, board out -- because the back-stand failed precisely by passing
every shape test there was.

### Then built: option B instead

Sam, 2026-09-05: "Actually, change of plans. I like having the electronics in
the base under the clock."

`mini-round-clock-plinth{tag}` + `-lid`. **It turned out to be a far smaller
change than the write-up above implied, and the reason is worth recording: the
bay was already walled on all four sides** -- the front rail, the back rail and
the two buttresses. What it had never had was a lid. So the plinth is the
back-stand plus a collar that carries those four walls up to one flat plane,
plus a 2.5 mm plate. 12.4 mm of clear air over the board.

Three things the mesh caught that reading the code would not have:

* **The collar slabbed the bay floor.** Drawn as a solid block hollowed from
  `FT + 0.50`, it left 1.50 mm of new material lying across the whole bay --
  burying the hold-down bosses and lifting the board. The void has to start
  BELOW the foot's top: the collar is a ring of walls and the floor is the
  foot's, already there. It exported as four negative-volume bodies, which is
  how it was found.
* **Two of the four lid screws were inside a buttress.** At |x| >= 40 the side
  wall is buttress all the way to z = 48, so a vertical pilot there is a blind
  hole in solid material that no screwdriver reaches. Two screws at the back at
  |x| = 30, and the front edge slides into a slot instead.
* **The front is a slot and the back is a seat, and they cannot be the same
  height.** The collar is drawn to `lid_z + LID_T` so the front wall can roof
  the tongue; left at that height all the way round, the back wall stands
  exactly where the lid's back edge goes -- 768 mm3 of interference, which is
  the whole back of the lid.

The deep housing stays in the tree and still passes check8. It is the better
answer if the clock ever goes on a wall, where a base is dead weight.

### And enclosed underneath

Sam, 2026-09-05: "Make the base enclosed underneath."

Measured first: the only holes in the foot were the six cable-tie slots, at
|x| 16, 26 and 35.5. Everything else in the underside -- the tie reliefs, the
boss pilots, the lid pilots -- is a blind pocket. So the plinth simply does not
cut them, and check9 proves it by firing a column up from below the desk at
every square millimetre of the bay and requiring material in the way. The open
back-stand keeps them: there they are the only thing holding the board and the
leads.

**Two things this turned up that were already wrong.**

* **The hold-down bar has never fitted.** At `CLAMP_SX + BOSS_R + 1.50` the
  plate is 81.5 mm wide and the bay is 81.0, so it fouled both buttresses by
  0.25 mm -- and by 0.75 in the plinth, where the collar was putting back the
  half millimetre the bay cut had taken. It went unseen for the same reason the
  wire port did: check7 tested the bar against the BOARD and against its own
  bosses, and never against the stand it goes into. The plate is now
  `min(that, XI - 1.00)`, and both check7 and check9 do the boolean.
* **The plinth's bay was half a millimetre narrower than the stand's**, because
  the collar's void was drawn to XI while the bay cut goes to XI + 0.50. Two
  parts meant to hold the same board, disagreeing.

The rule, for the third time in this file: **a part that goes INSIDE another one
gets a boolean against it.** Testing it against what it grips is not the same
test.

And a correction to what was said out loud: the board is NOT captive under the
lid. The lid clears it by 12.4 mm and never touches it. The bar is required.

## The dock: a clean sheet

Sam, 2026-09-05: "I hate the stand. Start again. I want it enclosed."

Fair. The back-stand had been through five generations -- open A-frame, a 30 mm
board, zip ties, a hold-down bar, a bolted-on collar and lid -- and every one
was a patch on the one before. It was a skeleton with a box grafted to it.

`mini-round-clock-dock{tag}` + `-cap`. A closed block, 92 x 79 x 40 (24) or
104 x 79 x 40 (32), with the clock's own shape scooped out of the top.

**THE SPLIT IS FORCED, NOT CHOSEN.** A closed box with a seat on top cannot be
printed in one piece without support: hollowed from below it has to bridge its
entire ceiling, and turned over the seat becomes a 90 mm cavern. Split at the
cavity's ceiling and both halves are trivial -- the tray is walls and a floor,
the cap is a slab with a valley in it, and a valley is open to the sky.

Everything else followed from print orientation too:

* **The locating rim is on the TRAY.** The cap prints seat-up with its flat
  underside on the bed, so it cannot have a spigot, skirt or boss on that face
  -- they would be under the build plate.
* **The screws go in from the BACK.** Down through the cap puts two heads in the
  seat, under the clock, where a screwdriver cannot reach. Up from below puts
  two counterbores in the underside, and Sam had already said what he thinks of
  holes underneath. Through the rim's back face does neither.
* **The wire drop runs the FULL length of the seat.** The port sits at 12
  o'clock in the model and Sam turns the clock to suit; a design that has to
  know which way up he fits it is a design that will be wrong.

**The footprint scales with the body, and the 60 is why.** At the 32's tail the
240 mm clock -- 1.1 kg with its centre of mass 125 mm up -- tipped backwards at
12.9 degrees. Scaled, it makes 28.1. The floor at k = 1.0 leaves the 24 and the
32 exactly where they were.

The cap is modelled solid, 107-124 cm3. That is not its weight: it is a slab and
the slicer hollows it.
