# What to make

Everything here is cut to your measured parts: **Mokungi 24-LED ring 92/71 mm**,
**GC9B72 360×360 display, 60 mm PCB / 55 mm screen / 40 mm tab / 67 mm overall
/ 4 mm thick**, **ESP32-S3-N16R8**.

---

## 1. Desolder two headers — do this first

| | |
|---|---|
| Display | the 10-pin header on the tab (`TE SDO BL CS DC RST SDA SCL VCC GND`) |
| Ring | the 4-pin header |

Solder wires flat to the pads instead.

**This is not optional.** The enclosure assumes `DISP_TAB_T = 1.6 mm`, the bare
PCB. With the header on, the tab is ~10 mm thick, the slot will not take it, and
the module has to move back another 9 mm into a well you cannot read.

---

## 2. Print — Bambu

Use the **v6** parts in `enclosure/mini/v2/`. There are two clock sizes and you
pick one — everything in a column goes together.

All in `enclosure/mini/v2/`, all prefixed `mini-round-clock`.

| | 24-LED (108 mm) | 32-LED (120 mm) | 60-LED (240 mm) |
|---|---|---|---|
| base | `-base` | `-base-32` | `-base-60` |
| housing | `-housing` | `-housing-32` | `-housing-60` |
| diffuser | `-diffuser` | `-diffuser-32` | `-diffuser-60` |
| **numerals** (2nd colour) | `-numerals` | `-numerals-32` | `-numerals-60` |
| **collar gauge** — print this FIRST | `-collar-gauges` — one part, any body | | |
| **board gauge** — print this FIRST | `-board-gauge` — one part, any body | | |
| **board clamp** + 2 × M3 × 10 | `-board-clamp` — one part, any body | | |

### The 1.9" bar screen instead of the round one

Two extra parts, and **only for the 32 and 60 bodies** — `-base-32-bar` +
`-diffuser-32-bar`, or the 60 equivalents. Housing, numerals and stand are the
round ones unchanged.

Everything works because of one derived number. The module is seated so its
**front face lands exactly where the round module's does** —

```
Z_SEAT_BAR = Z_SEAT + DISP_T − BAR_T = 8.60 + 4.00 − 5.10 = 7.50
```

— so the diffuser's collar still clears by 0.40 mm, the face still rests on the
land at 19.03, and the whole vertical stack is untouched.

The module is **62 mm long against a 60.38 mm bore**, so it cannot pass a round
hole. It doesn't have to: it overhangs the bore only in two ears at 12 and 6
o'clock, and those are exactly where the display-tab slot and the wire slot
already are. The `-bar` base cuts the ~194 mm³ that is left, and the module
**drops straight in from the front**.

Two rails at |y| 12.90–14.90 hold it up — outboard of the wire slot, which stays
clear for the ring leads. The diffuser's collar tip, 0.40 mm above the module's
top face, is what stops it lifting back out.

**The `-bar` diffuser has four collar ribs, not six**, at 45/135/225/315°. The
six-rib pattern puts two ribs straight into the +x ear with 4% of each having
anything to bite on, which throws the grip onto one side. Four on the diagonals
clear both ears by 15.4° and stay symmetric. Same interference, same rib width,
same lead-in — **the collar gauge still applies unchanged**.
| light guides *(optional)* | — | — | `-light-guides-60` |
| desk stand *(optional)* | `-deskstand` | `-deskstand-32` | `-deskstand-60` |

| File | Material | Settings |
|---|---|---|
| base | PETG (PLA fine) | **Deck face down.** 0.2 mm, 3 walls, 15% gyroid |
| housing | **PETG** if a cell goes in | **Rear plate down.** No supports |
| diffuser | **White PLA** | Face **down**. **0.20 mm layers.** **SOLID face — 100% infill**, no supports |
| numerals | **Black PLA** (filament 2) | Not a print of its own — added *as a part of the diffuser* and assigned filament 2. See below |
| desk stand | anything | Flat on its desk face. **8–10% infill** — it is a big blocky part and the volume figures are solid volume, not filament |
| light guides (60 only) | **clear or natural PETG** | Flat. White PLA is opaque and would do nothing |

**The housing is 25 mm deep now, and the clock is 49.4 mm overall.** Sam:
*"The housing can be 25mm deep, not 50mm anymore."* That leaves 14.1 mm of clear
space above the board for the display ribbon and the ring leads — and **no room
for a battery**. A cell needs a 43.3 mm housing, so the battery shelves are not
generated any more. Power it from USB. Putting `HOUSING_DEEP` back to 50.00 in
`v2/params.py` brings the deep housing and the shelves back.

**The S3 is properly held now**, not resting in a tray: rails that touch only
the board's edge, an end wall that takes the plug's push, corner stops the other
way, three pairs of posts, and two snap fingers clamping the connector end. Push
both fingers outward to get the board back out. See `v2/README.md` §2 and
`v2/render_fit.png`.

**The 60-LED build is 240 mm across.** It fits a 256 mm bed with 8 mm to spare —
watch the brim. Its desk stand is over a litre of enclosed volume; print that
one only if you really want a 24 cm clock on a desk.

**The perspex, if you are using it.** 60 off **6.00 × 3.00 × 25.50 mm**, and
**not on the Aura** — a 5 W diode laser cannot cut clear acrylic at all. Table
saw, bandsaw, scroll saw, or 6 mm acrylic rod. **Frost one face** with 400 grit
and put that face down, or the strip pipes the light to its far end instead of
glowing along its length. Perspex is PMMA and contains no chlorine, so it is
safe to cut and to laser; PVC is the one your rule is about, and unlabelled
"acrylic-look" sheet is often exactly that. See `v2/README.md` §7.

Either `.3mf` or `.stl` — for these files they carry identical geometry, because
the generator quantises to float32 and heals the mesh *before* writing.

**Slice the diffuser at 0.20 mm layer height.** Each LED's aperture is a radial
tick thinned to 0.20 mm of geometry — one layer — so any other layer height does
not land on a whole number of layers. It prints face-side down, so that layer
goes straight onto the plate and there is nothing to bridge. White PLA
specifically — natural pipes light along the layer lines and bleeds between
cells.

**The hours, in a second colour.** In Bambu Studio: load the diffuser, then
right-click it → **Add part → Load…** → the matching `-numerals` file, and
assign that part **filament 2**. It has to go in as a *part of the diffuser
object*, not as a separate object, or the slicer will move it and the register
is lost. The pockets are 0.50 mm deep and the inlay is 0.50 mm thick, so the
numerals finish flush with the face, right against the plate where the finish is
best. No AMS? Print the diffuser in one colour — the hours still read perfectly
well as a 0.50 mm shadow — or print the numerals separately and glue them in.

**PRINT `mini-round-clock-collar-gauges.stl` BEFORE THE DIFFUSER.** Three 8 mm
rings of the real collar section at three rib heights — five minutes, about 9 g,
each marked with its figure in hundredths of a millimetre on top:

| marked | crest | against the 30.19 bore |
|---|---:|---:|
| **10** | 30.290 | +0.20 mm on diameter |
| **15** | 30.340 | +0.30 mm |
| **20** | 30.390 | +0.40 mm — **what ships (0.19) sits just under this** |

Push each into the base's screen bore. Whichever wants a firm push and stays put
is your printer's answer: put its number over 100 into `COLLAR_RIB_H` in
`v2/params.py`. If even **10** is tight, your printer runs the boss over or the
bore under — try 0.05.

**0.1975 is the hard ceiling on that number**, and it is not arbitrary: `check2`
asserts that the wall behind the ribs has at least 4× the clearance the ribs have
interference, so the wall can never quietly become the fit itself. At
`COLLAR_OD` 29.40 the wall has 1.58 mm on diameter, which puts the cap there. If
you need more grip than that, add ribs (`COLLAR_RIB_N`, currently 8) rather than
height — turning the collar down to make room for taller ribs gives you thin
fins that bend instead of crushing, which feels loose, not tight.

**PRINT `mini-round-clock-board-gauge.stl` BEFORE THE HOUSING.** It is the S3
frame — same rails, same snap fingers, same corner stops, same hood, same posts
— on a 2.5 mm plate instead of inside a clock. About 15 g, twenty minutes.

Drop the board straight in between the rails, press the connector end down
until the two fingers click over it, then screw the clamp bar on over the far
end with two M3 × 10 self-tappers. If it goes together on the gauge, it goes
together in the housing.

If it does not, the plate has a 5 mm scale off the connector end with deeper
marks at **60.0 / 63.27 / 64.2** — the shortest board the bay takes, Sam's
measured length, and the longest. Read yours off it and put it in
`BOARD_L` in `v2/params.py`, then rebuild. If it is wider than the slot rather
than longer, raise `BRD_RAIL_CLR`.

Why bother: the bay is built around **63.27 × 28.19**, which is Sam's calipers
on his own board — 2.79 mm wider than Espressif's DevKitC-1 v1.1 drawing, so it
is a different board. The vendors selling boards under that name publish
**70 × 28**, **67 × 31** and **55 × 35** between them. Fifteen grams settles
which one you have.

**The diffuser press fit is on the INSIDE, on the collar.** The outer wall drops
into the ring pocket with 0.40 mm of clearance and grips nothing. On the collar,
the wall has **1.58 mm** of clearance on diameter and **eight** 1.00 mm ribs
standing 0.98 mm proud of it give **0.38 mm** of interference, over 3.23 mm of
bore engagement. The wall has four times as much clearance as the ribs have
interference, so a printer would have to be most of a millimetre out before the
wall itself became the fit — which is the failure that kept bringing this back.
The fit can be light: the clock hangs with the diffuser's axis horizontal, so
gravity never pulls it out.

**The collar is 3.93 mm long, and that is after being called too long four
times.** A collar that touches the module before the diffuser's face reaches its
land holds the whole thing proud — **too long is worse than too short**. The tip
now sits 0.90 mm clear of the module's front face, which still restrains it to
0.90 mm of float.

Do not set `COLLAR_LEN` by hand; it is derived. Measure your module's **overall
thickness** — the seat to the front glass, 5.60 mm on Sam's — and put it in
`DISP_T` in `v2/params.py`, then rebuild. Everything follows from it:

```
COLLAR_LEN = 19.03 − (8.60 + DISP_T + 0.90)
```

If you would rather check the built part than the module: the collar should
stand **3.93 mm** proud of the back of the face.

**SLICE THE DIFFUSER'S FACE SOLID.** Sam: *"there is bleed and you can see
through where you're not meant to."* The model was already 2.00 mm everywhere
but the aperture — checked, not assumed — so the bleed was light coming through
the PLA, and at 0% infill a face is a shell with air in it. Set the diffuser to
100% infill. The face is also 2.90 mm now, up from 2.00, which is the most the
front recess will take, and the aperture flares behind its membrane so the
thicker face does not turn each dot into the bottom of a narrow slot.

If it still bleeds after that, the answer is material, not geometry: white PLA
passes light at any thickness a clock face can carry, and the real fix is an
opaque body with translucent lens inserts at the dots.

**Before you print the diffuser, measure the display module's overall thickness**
and set `DISP_T` in `v2/params.py` — see the collar note above. `COLLAR_EXTEND`
is derived and is **negative** now (−1.37): the collar this build wants is
shorter than the one in Sam's uploaded mesh, so the build *trims* it rather than
extending it. Do not set it by hand.

**PETG for the housing if it will sit in the sun.** (There is no battery in
it any more — see above.) PLA softens at 55–60 °C; about
1 W in a small closed box on a west-facing wall in a Victorian summer can sit
well above that. PETG's Tg is ~80 °C. The vents are already in the part.

The base wants a little support inside the display-tab slot — the lead-in ramp
there runs 33–40° from horizontal. That is Sam's own geometry, unchanged, and
the slot is open so it picks straight out. Nothing else in any part needs
support; `v2/runchecks.sh` verifies that.

---

## 3. Cut — Glowforge Aura

`enclosure/mini/face.svg` — **3 mm plywood**, 112 × 112 mm sheet.

| Colour | Operation |
|---|---|
| Red `#FF0000` | **Cut** — display aperture, ring window, outline |
| Black fill | **Engrave** — twelve hour ticks |

**Cut the outline last** so the part stays supported. SVG order is only a hint;
set the step order in the Glowforge UI.

**Plywood, not acrylic.** The Aura is a ~5 W diode laser and physically cannot
cut clear, white or translucent acrylic — see `enclosure/MATERIALS.md`.

---

## 4. Flash — ESPHome Device Builder

Two configs. **Start with the first.**

| File | |
|---|---|
| `esphome/mini-round-clock.yaml` | **Ring only. Known good.** Display section commented out. |
| `esphome/mini-round-clock-with-display.yaml` | Ring **+** display, with the VERIFIED GC9B72 init sequence. **This is the one that is flashed and working** (2026-08-24). |

```bash
esphome config esphome/mini-round-clock.yaml     # validate before flashing
```

First flash over USB with the LED supply **unplugged** — Install → Manual
download → **`.factory.bin`**, then flash at web.esphome.io. OTA after that.

Secrets go in `/config/esphome/secrets.yaml` — you have that file already.

### Then try the display

Swap to `mini-round-clock-with-display.yaml` and re-flash.

- **Works** → done.
- **Photo-negative colours** → set `invert_colors: true`. One line, one cause.
- **Blank or garbled** → go back to the ring-only config and get the vendor demo
  code from the seller (Baishun, 2.1″ 360×360 GC9B72). Do **not** hand-tune the
  registers. See `docs/gc9b72-display-block.yaml`.

---

## 5. Home Assistant

```bash
bash homeassistant/install.sh
```

Fill in your real entity IDs **before** restarting — the queries are in
`homeassistant/INSTALL.md` step 2. First install needs a restart, not a reload.

---

## 6. Bring-up

1. `select.mini_round_clock_mode` → **`test chase`**. Note where the red pixel
   lands, then dial **Twelve o'clock offset** on the dashboard until it sits at
   the top. It is a runtime number now — no re-flash. Same for **Ring LED
   count**, so any ring up to 60 LEDs works without rebuilding.
2. White pixel not white, or red not red → change `channel_colors: GRB` to `RGB`.
3. Say *"set a timer for two minutes"* and walk the chain in
   `docs/PHASE-6-TEST-PLAN.md`.

**Stage 5 of the test plan is the one that matters** — it is the only place the
*clock > timers > status* priority actually gets tested rather than asserted.

---

## Assembly, once the parts are off the plate

1. Ring and display into the base from the front. Press the diffuser in after
   them — it goes in square, then the eight crush ribs bite.
2. **S3 into the housing**, straight down: drop it square between the two
   rails, connector end toward 6 o'clock and facing the 22 × 6 mm window, then
   press the connector end down until the two snap fingers click over it —
   about 3 N each, a firm thumb. It settles onto its six posts.
2b. **Screw the clamp bar on** over the far end, relieved end pointing back
   toward 6 o'clock, with **2 × M3 × 10 self-tappers**. Snug, not hard: it is
   designed to bottom on the board rather than on its own bosses, so it takes
   up the last 0.10 mm as a light clamp. That is what stops the far end
   lifting — the snap fingers alone leave a 15:1 lever.
3. Battery, if you are fitting one: a shelf either side, cell on top of the
   pair. It never rests on the board.
4. Solder the ring and display leads to the board. They come down through the
   deck's openings — the display's ribbon at 12 o'clock, the ring's leads at 6.
   **Power the board at its own USB port now**, or at 5V/GND if you prefer;
   there is no breakout board any more.
5. Housing on: 4 × **M3 × 35** self-tapping. (It was M3 × 60 when the
   housing was 50 mm deep — a 60 will now bottom out and split the boss.)
6. Either hang it — one screw in the wall, 4 mm shank, head no wider than 8 mm
   — or drop it into the desk stand.
7. Plug a USB lead into the window at the bottom of the rim. On the stand the
   lead runs down into the arch and out the back.

### Wiring the 1.9" bar screen instead of the round one

The firmware carries both drivers. Which one it draws is the **"Screen"** select
in Home Assistant — *auto*, *round 360x360*, or *bar 320x170* — and *auto*
follows a strap wire in the panel's own cable.

The bar module's header is **8 pins in a different order** to the round one's
10, so it needs its own lead regardless:

| bar module pin | goes to | note |
|---|---|---|
| GND | GND | |
| VCC | 3V3 | |
| SCL | **GPIO12** | shared with the round panel |
| SDA | **GPIO11** | shared |
| RES | **GPIO17** | **its own — not the round panel's GPIO14** |
| DC | **GPIO13** | shared |
| CS | **GPIO16** | **its own — not the round panel's GPIO10** |
| BLK | **GPIO21** | shared |
| — | **GPIO18 → GND** | **the strap.** One extra wire; this is what *auto* reads |

**CS and RES must not be shared, and that is not a style preference.** Both
panels are initialised at boot, because ESPHome's `mipi_spi` throws the init
sequence away once it has sent it — so there is no way to re-initialise a panel
later when you pick it. Separate chip selects are what stop each panel seeing
the other's init; a separate reset is what stops the second driver's reset pulse
wiping the first panel after it has been set up.

**There is no way to auto-detect these panels over SPI.** Both are write-only:
the round module brings SDO out but it is unconnected, and the bar module has no
such pin at all — Waveshare's own page says the slave-to-host data pin "is
hidden as it only needs to display". Hence the strap. If you make a cable
without it, set the "Screen" select explicitly and it will behave.

**Two things about the bar are inherited rather than measured** — `color_order:
bgr` and `invert_colors: true`, which are what ESPHome uses for every other
170×320 ST7789 it ships. If the picture comes out as a photo negative, flip
`invert_colors`; if red and blue swap, flip `color_order`. One line each.

**Screws, all told:** 4 × **M3 × 35** self-tapping (housing to base) and
2 × **M3 × 10** self-tapping (clamp bar to its bosses). Both are plain
coarse-thread self-tappers into PLA — 2.50 mm pilots, no inserts, no nuts.

**Nothing to buy for the power inlet.** The ADA4090 breakout in the BOM is
withdrawn.

---

## Before you commit filament

```bash
cd enclosure/mini/v2
python3 measure_uploaded.py    # re-derive every number from your STLs
python3 build_v2.py            # regenerate the parts
./runchecks.sh                 # five verification passes
```

If you send new STLs, run `measure_uploaded.py` first and diff it against
`params.py` — everything downstream keys off those numbers.
