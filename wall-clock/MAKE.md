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
| light guides *(optional)* | — | — | `-light-guides-60` |
| desk stand *(optional)* | `-deskstand` | `-deskstand-32` | `-deskstand-60` |

| File | Material | Settings |
|---|---|---|
| base | PETG (PLA fine) | **Deck face down.** 0.2 mm, 3 walls, 15% gyroid |
| housing | **PETG** if a cell goes in | **Rear plate down.** No supports |
| diffuser | **White PLA** | Face **down**. **0.20 mm layers.** 0% infill, no supports |
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

**The diffuser press fit, fixed properly in v8.** v6 argued about diameter; the
problem was depth. The ring pocket's wall stops at z = 19.00 and the diffuser
rests with its face at z = 21.52, so a 4.00 mm band had only **1.40 mm** inside
the bore and 2.60 mm hanging in the front recess gripping nothing. The band is
6.00 mm now — **2.9 mm of measured rib contact** — and the lead-in taper has
moved to the end that actually goes in first. Wall clearance 0.10 mm, eight
crush ribs, 0.60 mm of interference on diameter. Still loose → raise
`DIFF_RIB_H` in `v2/params.py` to 0.45; will not start → drop it to 0.25.

**Before you print the diffuser, measure the display module's rim thickness** at
the r = 29 mm circle and set `COLLAR_EXTEND = 2.20 - t` in `v2/params.py`.

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
2. **S3 into the housing**, tilted: slide the +x end under its hook, drop the
   −x end, and it settles onto its four posts with its own connector facing the
   22 × 6 mm window at 6 o'clock. There is 37 mm of empty pocket above it, so
   this is not a fiddle.
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
