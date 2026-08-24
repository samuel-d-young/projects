# mini-round-clock enclosure — v2 rear end

What this adds to the base and diffuser Sam remodelled: a bay for the ESP32-S3
that holds it down, a USB-C inlet through the wall, a wall hanger, and a pocket
for a USB-C power bank.

Everything here is generated from `build_v2.py`, which reads Sam's uploaded
`base_in.stl` and adds to it. It never redraws his geometry: above z = 0 the
only differences are four screw pilot holes bored into it and four posts added
to locate the board, plus the USB-C bay and two more pilots — `check2_fit.py`
proves that as a boolean difference against a named envelope for each one, not
by eye.

```
python3 measure_uploaded.py    # re-derive every number in params.py from his STLs
python3 measure_fit.py         # the tab slot and diffuser features specifically
python3 build_v2.py            # write the STLs and 3MFs
./runchecks.sh                 # all five verification passes
python3 render.py              # picture sheets
python3 viz.py                 # cross-section atlas of the uploaded parts
```

`base_in.stl` and `diffuser_in.stl` are Sam's uploads, kept so the whole thing
re-derives from source. `measure_uploaded.py` prints the table that `params.py`
holds — if he sends new files, run it and diff.

---

## Print these

| File | Print orientation | Support | PLA | Time (est.) |
|---|---|---|---|---|
| `mini-round-clock-base-v2` | **deck face down** | see note | ~132 g | ~5 h |
| `mini-round-clock-rearhousing-battery` | **rear plate down** | none | ~73 g | ~3 h |
| *or* `mini-round-clock-rearhousing-slim` | rear plate down | none | ~57 g | ~2.5 h |
| `mini-round-clock-battery-shim-x2` | flat | none | ~11 g each, **print 2** | ~20 min |
| `mini-round-clock-board-keeper` | plate down | none | ~1 g | ~5 min |
| `mini-round-clock-diffuser-v3` | **face down** | none | ~17 g white PLA | ~55 min |

Both `.stl` and `.3mf` are provided, and for these files they carry **identical
geometry** — `finalise()` quantises to float32 before writing, so the STL round
trip has already happened and been healed by the time either file is saved. Use
whichever you prefer; the 3MF just carries units and metadata that Bambu Studio
likes.

**Support note for the base.** The part is designed to need none, and the checker
confirms it introduces none. But Sam's own geometry carries 409 mm² of shallow
overhang at 33–40° from horizontal — the lead-in ramp at the top of the
display-tab slot, at z 10.7–17.9. Whether that needs support depends on the
threshold you slice at; at Bambu's usual settings it will want a little, inside
the tab slot, which is open and easy to pick out. It is the same in the file Sam
uploaded, so nothing has changed here.

**Material.** PETG rather than PLA if a lithium cell is going in. PLA's glass
transition is ~55–60 °C; PETG's is ~80 °C. See §5.

---

## 1. What was found in the uploaded files

Three things worth knowing before printing anything.

### The base has a disconnected 605 mm³ solid in it

`Mini_Wall_Clock_Base.stl` contains a second shell — a crescent at
r 35.06–40.90, ±41.9° about +x, z 11.80–15.75 — that is **not attached to the
body**. Its faces sit exactly on the main body's cut surface, and it arrived as
a +2832 / −2227 mm³ shell pair. That is the signature of a CAD boolean that
failed to merge, not a feature.

It sits precisely in the window the display tab has to pass through. Sliced
as-is, it prints as an extra crescent of plastic exactly where the display goes.
`build_v2.py` drops it and says so when it runs.

### The module's rim is thinner than 4 mm — and you told me so without meaning to

An earlier version of this file said the diffuser's collar over-reaches the
module by 1.8 mm. **That was wrong, and the way it came apart is worth keeping.**

The collar (r 27.92–30.11, 8.2 tall) lands at base z = 19.00 − 8.20 = **10.80**.
The display seat is at **8.60**. So the collar clamps a module whose rim is
exactly 2.20 mm thick, and it fouls anything thicker. On a 4 mm module the
diffuser would stand 1.8 mm proud and the plywood would not sit down.

You have printed and test-fitted these and reported the screen **loose** — not
the diffuser standing proud. So the collar is not touching, and **the module's
rim is under 2.20 mm.** The 4 mm figure is the module overall, not the rim the
collar actually lands on. That retires the interference finding.

See §7 for what that means for the new collar height.

### The wire slot goes right through

The straight-down channel is open front to back — at 180° there is no material
at all from z = 0 to z = 22 for r 31–43. The plywood face covers it at the
front, so it was never visible, but the deck now closes it from behind, which
also encloses the electronics. A 4 × 16 mm port is cut through the deck beside
the S3's USB-C end so the battery lead can still get up to the board.

---

## 1b. v3 — the changes after your test fit

### The tab slot was the looseness

You measured the tab that sticks out of the bottom of the screen: **30.55 mm**.
The slot was cut as an angular wedge sized for a 40 mm tab, which at r = 35 is
**46.62 mm wide**. Against a 30.55 mm tab that is ±25.9° of free rotation — the
screen could sit a quarter-turn of a clock face off true. That is
"doesn't stay upright".

Two walls either side now bring it to **31.15 mm**:

| | before | after |
|---|---:|---:|
| slot width at the tab | 46.62 mm | **31.15 mm** |
| tab can rotate | ±25.90° | **±0.47°** |
| screen edge can move | 12.5 mm | **0.22 mm** |

The walls run from the deck up to the ring pocket floor, with a 45° lead-in
chamfer on the top inner edge so a slightly rotated tab still finds its way
down. They sit at |y| ≥ 15.575 and the S3 board is |y| ≤ 12.70, so the two never
meet.

**A side effect worth having:** the tab window had removed the ring pocket floor
across ±41.8°, leaving the ring unsupported over a 83° arc at 12 o'clock. The
walls put that floor back everywhere the tab is not — the checker measures it at
100% of the sector outboard of the slot.

### The diffuser is now a press fit

It was **46.000** in a **46.3516** pocket: 0.35 mm radial, **0.70 mm on
diameter**. It is now **46.4016** — a **0.10 mm diametral interference**.

If it will not go in, set `DIFF_FIT = 0.00` in `params.py` and rebuild for a
slip fit. That is the one number.

### One layer over the LEDs

The membrane was 0.80 mm. It is now **0.20 mm** — a single layer at 0.20 mm
layer height, and the diffuser prints membrane side **down**, so it is the first
layer and there is no bridging.

**Slice the diffuser at 0.20 mm layer height.** At any other layer height a
0.20 mm feature does not land on a whole number of layers.

The thinning cut **steps around all 24 cell walls** and leaves a small buttress
at each base. Thinning straight through them would have left every wall standing
on nothing — the checker confirms all 24 still reach full height.

A 0.2 mm sheet is fragile in the hand. It is captured between the ring and the
plywood once assembled, so it only has to survive the bench.

### The aperture is a radial tick now, not an arc

> *"the line needs to be perpendicular to the screen, like the lines are. I want
> the LED's to look more like the echo wall clock led's."*

v4 narrowed the lit band to a 2.50 mm arc. That was still the wrong axis: an arc
lies **along** the circle, so a lit LED reads as a dash going the wrong way. Each
cell's aperture is now a **radial tick** — 2.00 mm across, 4.00 mm long, pointing
at the centre, radiused ends, centred on the LED circle at r = 40.75.

| | v3 | v4 | **v5** |
|---|---:|---:|---:|
| lit aperture | 5.90 mm band | 2.50 mm arc | **2.00 × 4.00 mm tick** |
| one lit LED reads | 5.90 × 9.72 | 2.50 × 9.72 | **2.00 × 4.00** |
| which way it points | — | along the circle | **at the centre** |
| dark between two LEDs | 0.95 mm | 0.95 mm | **8.67 mm** |
| face either side | 0.80 (glows) | 2.00 | **2.00** |

Why it reads like the Echo: 8.67 mm of plain white between one tick and the
next, so the ring is 24 separate marks rather than a segmented ring, and each
mark is a mark rather than a blob. A 5050 spans r 38.25–43.25 and the tick sits
inside that at 38.75–42.75, so it is lit evenly end to end.

Crosstalk is stopped by the **cell wall**, not by the aperture: the walls run the
full 2.00 mm depth of the cell, from the face up to the LED PCB, so light from
the next LED never enters this cell at all. The aperture is 1.80 mm deep and
2.00 mm wide, which keeps a tick lit within about ±29° of straight on.

### The hours are written on the diffuser

> *"Write the clock times on the difuser too."*

Debossed 0.50 mm into the face, in the 3.5 mm band between the plywood window's
inner edge (r = 35.0) and where the ticks start (r = 38.75):

- **12, 3, 6, 9** as numerals, 3.40 mm tall, upright — read from across a room,
  not rotated with the dial
- the other eight hours as marks: 1.00 × 2.60 mm, with the quarters at
  1.60 × 3.20 mm so they read as majors

They are **debossed, not thinned**, because the Echo's markings are printed on a
white face and the LEDs are what lights up. 1.50 mm of PLA is left under a
0.50 mm deboss, so they stay opaque. If you would rather they lit, set
`MARK_DEPTH = 0` and cut them to 0.20 mm instead — one line in `params.py`.

### The LED band is rebuilt, not patched

This is the change with the biggest effect on the file, and it is invisible.

Sam's diffuser carries **183 non-manifold edges**, and every one of them is in
the band r 35.5–46.0, z 0.8–4.0: his two annular ribs are notched at each of the
24 cell-wall angles, and the notches are modelled with faces that do not pair up.
Inside r = 35.0 the mesh is perfect — 0 bad edges, watertight.

Every earlier version unioned new geometry **through** that damage, and it got
worse each time: v5's first attempt came out with 160 bad edges and a 0.128%
disagreement between two ways of measuring its own volume. So the band — which
is exactly the part v5 replaces anyway — is now cut away and rebuilt from
measured numbers:

```
inner rib   r 35.4996 .. 36.6996, z 0 .. 4.000
outer rib   r 44.7995 .. 46.0000, z 0 .. 4.000   (now runs out to the press fit)
24 walls    1.000 mm thick, centres 7.5 + 15k deg to within 0.0003 deg
face        2.00 mm everywhere, ticks cut through it to a 0.20 mm skin
```

Result: **0 bad edges, watertight, one body, volume agreeing to 0.000%** — the
first time this part has been clean. The ribs are continuous now instead of
notched, which is also a better light seal and a stronger press fit.

One thing left alone: the plywood face's ring window is 11.5 mm wide, so you see
about 9 mm of plain white diffuser around the ticks. That is the Echo look.
Narrow the window in `face.svg` if you would rather see less of it.

### The collar reaches 2 mm further in

8.20 → **10.20 mm**, so it lands at base z = **8.80**.

**Read this before printing it.** The seat is at 8.60, so a 10.20 collar clamps a
module rim **0.20 mm** thick. From §1 we know the rim is under 2.20 mm but not
what it is. The exact answer is one caliper measurement:

```
measure the module's rim thickness at the r = 29 mm circle   -> call it t
set  COLLAR_EXTEND = 2.20 - t   in params.py, rebuild, print
```

If you print it as shipped and the diffuser stands proud, that gap **is**
`t − 0.20`: measure it with a ruler, subtract it from `COLLAR_EXTEND`, reprint.
Either way it is one number and a 45-minute print — but the caliper is cheaper.

---

## 2. The ESP32-S3 bay

The board is the official Espressif outline: **62.74 × 25.40 mm**, from
`DXF_ESP32-S3-DevKitC-1_V1_20210312CB.pdf`.

It does not get a box of its own. Sam's base already has a dog-bone shaped void
running along the x axis — the rear bore, plus his wire slot at 6 o'clock, plus
the display-tab window at 12 o'clock — and along the strip |y| ≤ 12.7 that void
is open from x = −43 to x = +40.7. That is 83.7 mm of clear length for a
62.74 mm board. So the deck simply gives it a floor.

```
deck window   63.64 x 26.30 mm  (0.45 clearance per side)
board sits at x -24.00 .. +38.74, y +/-12.70
  -x corner r = 27.15  (bore wall is at 27.78)
  +x corner r = 40.77  (tab window reaches 42.66)
PCB occupies z -0.80 .. +0.80, tallest parts reach z +4.00
display seat is at z +8.60                        -> 4.60 mm of air above
```

**It loads from the rear, tilted +x end up.** This is the part v5a fixes: with a
3.00 mm ledge at *both* ends the opening was 57.64 mm against a 62.74 mm board,
and no tilt gets a rigid board through that — the old instruction "push it up
until it meets the ledges" could not actually be carried out. The ledges are now
**1.50 mm**, which leaves a 60.19 mm gap, so the board goes in at 17.9° and
swings flat. `check5_v5a.py` walks the real mesh through that motion in
half-degree steps and proves every pose is clear of the base.

It has to go **+x end up**: at 17.9° the raised end needs z = 8.87, and the tab
window at that end is open to 11.80 while the bore at the other end stops at
8.60.

The ledges are at the two **short** ends only — the DevKitC-1 carries its pad
rows down both long edges, 1.27 mm in, and a ledge there would foul any soldered
header.

### What holds it, now that something does

Three things, and between them the board has 0.20 mm of movement in every
direction:

| | what stops it | float left |
|---|---|---:|
| out the back (−z) | the two 1.50 mm ledges | 0 |
| into the clock (+z), USB end | the **beam** at z 4.20 | 0.20 mm |
| into the clock (+z), far end | the **keeper's tongue** at z 1.00 | 0.20 mm |
| sideways | the window walls, 0.45 mm per side | 0.45 mm |

**The beam** spans the board's USB end at z 4.20 — 0.20 mm above the tallest
thing the board carries (BOARD_TALL = 3.20 on a PCB whose top is at 0.80). It is
deliberately *above* everything rather than *on* the PCB edge, so it cannot foul
a connector or a soldered header whatever the board's exact layout. Its pillars
stand at x = −20 rather than over the board's end at −24 for a measured reason:
the bore is r = 27.78, so at x = −24 it is only open to |y| < 13.99 against a
deck window that already reaches 13.15 — 0.84 mm of landing. At x = −20 the bore
opens to |y| < 19.30 and the pillars get a 3 mm footprint.

**The keeper** is a separate printed part, 1 g, two M3 screws, and it goes on
*after* the board. It has to be separate: a fixed tongue over the +x end would
block the tilt-in, and a fixed tongue over the −x end would land on the USB
connectors. Its pilots sit at r = 46.76 — outside the tab window (42.66), outside
the tab-slot walls (43.50) and outside the ring pocket (46.35) — so they bite
solid base for their whole 6 mm rather than self-tapping a 2.4 mm deck.

The tongue covers the last 2.00 mm of the board's +x end, ±9.00 in y. **One
assumption, and one caliper glance to check it:** that strip is bare PCB. On the
DevKitC-1 the two 22-pin rows are 21 × 2.54 = 53.34 mm long on a 62.74 mm board,
which leaves 4.70 mm clear at each end. If your board puts something there, set
`KEEP_TONGUE_Z0 = 4.20` and it clamps over the top of it instead, with the same
0.20 mm of float.

**If your board has male headers soldered pointing down**, snip them or it will
not seat — there is 1.6 mm under the PCB, which takes solder joints but not pins.

### Powering it, and the USB-C inlet

> *"make sure ... the USB connector can be connected externally from the outside
> of the wall. I may or may not use a USB battery or USB power supply."*

Feed the board's **5V and GND pins**, not its own USB port. Two reasons, and the
second one is new:

1. A USB-C plug is ~20 mm long, and from the board's connector at x = −24 it
   would end 30 mm short of the rim — the plug would be swallowed inside the
   clock with no way to grip it.
2. **Which connector the board even has is not settled.** Espressif's own v1.1
   user guide calls both ports *Micro-USB*; the boards widely sold as
   "ESP32-S3-DevKitC-1" carry two Type-C. Nothing that depends on the board's own
   connector is safe to design around, so nothing here does.

So the inlet is its own USB-C socket at 6 o'clock, wired to the 5V and GND pins:

```
plug channel  13.00 x 7.20 mm through the wall, z 0.30 .. 7.50
socket mouth  x = -47.00, i.e. 6.99 mm inside the rim
breakout bay  20.40 x 14.20 x 5.00, PCB on a shelf at z 0.60
lips          z 2.50 .. 4.00, reaching to +/-5.50 -- over the PCB, clear of the
              8.94 mm connector shell by 1.03 mm
```

Two things make that safe to pull on. The channel is **13.00 mm wide and the
breakout PCB is 14.20**, so the PCB butts a 0.60 mm shoulder each side and
pulling the plug cannot drag the breakout out through the wall. And the socket
sits 6.99 mm in, so about 13 mm of a 20 mm overmold stands proud of the rim —
enough to get hold of.

**The part.** Adafruit **ADA4090**, "USB C Breakout Board – Downstream
Connection", 20.4 × 14.2 × 5.0 mm, with **two 5.1 kΩ resistors on CC1**.
A$5.40 inc GST at Core Electronics, on backorder when I checked. **Nothing has
been ordered.** The CC resistors are not optional: without them a USB-C charger
or power bank never turns 5 V on at all.

Wire VBUS → the board's 5V pin and GND → GND. It powers the clock from a USB
supply *or* from a power bank, and both work whether or not the battery pocket is
used — which is what "I may or may not" needed.

For flashing, take the rear housing off (4 screws), undo the keeper's two M3s and
the board lifts straight out. After the first flash it is OTA over WiFi anyway.

---

## 3. The rear housing

Two variants, identical apart from pocket depth:

| | pocket | housing | clock overall |
|---|---:|---:|---:|
| `-slim` | 15.0 mm | 18.5 mm | **44.4 mm** |
| `-battery` | 27.5 mm | 31.0 mm | **55.4 mm** |

### Wall hanger

A keyhole at 12 o'clock: 9.0 mm entry hole, 4.6 mm slot, 7.5 mm drop. Takes a
screw up to 8 mm across the head on a 4 mm shank. The clock has to be lifted
7.0 mm to come back off it.

The screw head ends up **inside** the compartment once the clock is hung — that
is what carries the load. The battery pocket is therefore offset 7 mm toward
6 o'clock so the battery never sits on it.

Load path is keyhole → 3.5 mm plate → outer wall. The four assembly screws carry
nothing. At a 400 g clock the shank bears on 4.6 × 3.5 mm of PLA, about 0.25 MPa
against a ~50 MPa yield.

An earlier version had stiffening ribs behind the hanger. The fit checker found
that they ate into the battery footprint, and the stress arithmetic says they
were never needed. They are gone.

### Assembly

Four M3 self-tappers at r = 49, at 45/135/225/315° — clear of 12 o'clock (hanger)
and 6 o'clock (cable). They pass through pillars in the housing, counterbored at
the rear so nothing stands proud against the wall, and thread 8 mm into pilot
holes in the base.

- slim housing → **M3 × 30** self-tapping
- battery housing → **M3 × 40** self-tapping

### Which way round the battery goes, and why it is not a free choice

A 77 mm bank in a 102 mm circle leaves about 25 mm split between its two ends,
and the 6 o'clock end is spoken for by the wall:

| | clearance |
|---|---:|
| 6 o'clock end (where the cable enters) | **6.51 mm** |
| 12 o'clock end, on the centreline | 18.51 mm — but the wall screw's head sweeps it |
| 12 o'clock end, at y = 6…18 mm | **15.2 mm** |
| beside the battery, either side | 22.8 mm |
| above the battery | 2.61 mm |

So: **put the battery in with its ports facing 12 o'clock, off the centreline,
and use a slim right-angle USB-C plug.** The mains lead comes in at 6 o'clock,
runs up the side of the battery — 22.8 mm of room there — and plugs in at the
top. `check2_fit.py` asserts all of this.

### Cable exit and vents

A 12 × 7 mm notch through the outer wall at 6 o'clock takes a USB-C plug
(9 × 4.5 mm body clears it with room). 18 vent slots, 2.6 mm, in two groups —
low and high — so the box convects when it is on a wall rather than sitting as a
sealed oven.

---

## 4. Assembly order

1. Print the base, the housing you want, **two** shims and the keeper.
2. **USB-C breakout first.** From inside the bore, slide it −x along the bay's
   rails and under the lips until its PCB edge butts the channel shoulder at
   x = −47. Nothing else fits past it once the S3 is in.
3. Fit the display and ring to the base, front side.
4. **S3 in from the rear, tilted +x end up**, about 18°: put the raised end up
   into the tab window, swing it flat, and let it settle onto the two ledges.
5. Keeper on: tongue over the board's +x end, 2 × M3 × 12 self-tapping.
6. Solder the ring and display leads to the board. Run the breakout's VBUS and
   GND to the board's **5V and GND pins**.
7. If you are fitting a battery: in the housing with a shim either side, output
   lead up through the deck port at 6 o'clock (the slot at y +10 … +13) to the
   same 5V/GND pins, and its input from the USB-C inlet.
8. Screw the housing on, 4 × M3.
9. One screw in the wall, 4 mm shank, head no more than 8 mm. Hang it.
10. Plug a USB-C cable into the inlet at the bottom of the clock. No opening it
    up to power it, ever again.

---

## 5. The battery — read this before buying anything

**A battery this size cannot run this clock. It is a UPS for outages.**

The measured budget, from datasheets rather than estimates:

| Load | typical | worst |
|---|---:|---:|
| ESP32-S3-N16R8 devkit, WiFi up, HA API connected | 60 mA | 140 mA |
| 24-LED WS2812B ring, clock face at ~25% | 33 mA | 145 mA |
| 2.1" 360×360 GC9B72 + backlight | 95 mA | 150 mA |
| **at 5 V** | **188 mA = 0.94 W** | **435 mA = 2.18 W** |

That is **22.6 Wh a day**. A 5,000 mAh bank holds ~18.5 Wh nominal, ~16 Wh after
boost losses — **under 18 hours**. It does not last a day.

### What actually fits, and what to buy

The pocket takes **up to 80 × 38 × 26 mm**, or 78 × 45, or 77 × 50 — the limit is
a rectangle inside the 102 mm interior circle with the hanging screw's swept zone
carved out of the top. `check2_fit.py` prints the full table.

A sweep of Officeworks, JB Hi-Fi, Kogan, Amazon AU, Core Electronics, Zaitronics,
PB Tech, Cygnett, Anker AU, Belkin AU, Bunnings and Scorptec found **one** retail
bank that is both small enough and actually buyable here:

> **Anker Nano Power Bank, model A1653, 5,000 mAh — about A$49 at Scorptec
> (Melbourne).** 76.96 × 36.83 × 24.89 mm (verified, Anker's own spec table),
> so 3.7 mm of spare length in the pocket. Pass-through verified in their
> manual. **~17 hours.**
>
> Two things to settle first: its output is a **fold-out male USB-C plug**, and
> only 15.2 mm is available at the 12 o'clock end; and nobody documents whether
> it restarts by itself after being drained. Both are in `docs/BATTERY.md`,
> with the bench tests. Runner-up if either fails: Baseus Compact Type-C
> Edition 5000, A$45.99 verified in stock — a plain brick, but it lands
> exactly on the pocket's limit.

The shim is cut for exactly those dimensions. Buy something else and you change
two numbers in `params.py` and reprint the shim; the pocket does not move.

The market is otherwise bifurcated and this clock lands in the gap: slim banks
are wide (Cygnett 95 × 65, Anker MagGo 104 × 71), and banks narrow enough for a
108 mm circle are 25–26 mm thick — which is what pushes the clock from 44 mm to
55 mm deep.

### The failure mode that decides it

At 188 mA the clock sits above the ~50–75 mA idle cutoff most banks use, so it
would probably not get switched off in normal running. The one that would bite is
different: **many banks, once flat, will not resume output when mains comes back
until someone presses the button.** On a clock 2.4 m up a wall that means it stays
dead. Anker do not document A1653 either way.

**Test it before it goes in the wall.** Run the bank flat into the clock, leave
the load connected, plug the charger into the bank, and watch. If it comes alive
on its own, you are done. If not, no power bank is usable here at any price —
`docs/BATTERY.md` §4 has the alternative.

### Safety, and the material

A lithium cell sealed in a printed box on a wall in a family home deserves a
plain answer:

- **Print the housing in PETG, not PLA.** PLA softens at 55–60 °C. About 1 W of
  dissipation in a small closed box on a west-facing Victorian wall in summer can
  plausibly put the interior at 50–70 °C. PETG's Tg is ~80 °C. The vents help but
  they do not make PLA the right choice here.
- A **certified sealed power bank is materially safer** than a bare cell on a
  hobby charger board, in one specific way: it ships as a tested assembly with
  protection on the cell and a liability path behind it. A charger IC is not a
  protection circuit — it gives you no over-discharge cutoff and no short-circuit
  protection. If you go the bare-cell route, the cell must be a *protected* one.
- Do not leave the first few charge cycles unattended.
- If the battery is not worth 11 mm of depth and this list of caveats to you,
  print the **slim** housing and run it on mains. The clock is better at 44 mm and
  nothing else changes.

The full working — power budget, every candidate scored, the runtime arithmetic,
the alternative if the Anker fails its test — is in **`docs/BATTERY.md`**.

---

## 6. What is verified and what is not

**Verified here, by running it:**

- Every part is a closed, single-body, self-intersection-free solid (`check1`)
- Sam's geometry above z = 0 differs by exactly six screw pilots, two posts, the
  beam, the tab-slot walls and the USB-C bay, and nothing else — measured as a
  boolean difference against a named envelope for each, not eyeballed (`check2`)
- The diffuser is watertight, one body, 0 non-manifold edges — the first version
  of it that is, because the LED band is rebuilt rather than patched (`check1`)
- The S3 can physically be got in: the tilt-in is walked through on the real mesh
  in half-degree steps, and every pose is clear (`check5`)
- The board has 0.20 mm of float in every direction once the keeper is on, and
  neither the beam nor the tongue touches the PCB or anything on it (`check5`)
- A full-size USB-C overmold — 12.35 × 6.50 mm, the USB-IF maximum — reaches the
  socket from outside the rim without touching the base (`check5`)
- The board, the battery, an M3 shank, an 8 mm screw head and a USB-C plug body
  each fit where they have to, with the clearances printed (`check2`)
- The base and the housing touch only at the mating plane — zero interference
  volume (`check2`)
- No part introduces a sloped overhang below 45°, a flat ceiling over 25 mm, or
  a wall thinner than 1.2 mm that is not already in Sam's file (`check3`)

**Not verified — these need hands or a purchase:**

- Nothing has been sliced. Print time and mass are estimates from volume.
- The display module's 4 mm thickness is Sam's measurement of the whole module,
  not of the rim the collar lands on. §1 turns on it.
- The USB-C breakout (ADA4090, A$5.40 at Core Electronics) is priced and
  dimensioned from the vendor's own listing, but **nothing has been ordered** and
  I have not had one in my hand. The bay is drawn to the published
  20.4 × 14.2 × 5.0 mm.
- Which USB connector the ESP32-S3 board itself carries is *not* settled — see
  §2. Nothing in the design depends on it, which is the point.
- The keeper's tongue assumes the last 2.00 mm of the board's +x end is bare
  PCB. Derived, not measured: 22-pin rows are 53.34 mm on a 62.74 mm board.
- The 95 mA display figure is the weakest number in the budget — it is
  extrapolated from a smaller GC9A01 module, because the 2.1" drawing lists
  luminance as "TBA" and gives no LED current. An inline meter settles it in ten
  minutes and could change the battery decision.
- The ring's die revision is unknown; V5 versus original silicon is a 2×
  difference in per-channel current. Power the ring alone, write all zeros, read
  the supply current: ~14 mA means V5, ~24–36 mA means older.
- The interior temperature rise is an estimate, and the safety argument in §5
  rests on it. Worth a probe before a cell goes in.
