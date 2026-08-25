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

| | 24-LED (108 mm) | 32-LED (120 mm) |
|---|---|---|
| base | `v2/mini-round-clock-base` | `v2/mini-round-clock-base-32` |
| housing | `v2/mini-round-clock-housing` | `v2/mini-round-clock-housing-32` |
| diffuser | `v2/mini-round-clock-diffuser` | `v2/mini-round-clock-diffuser-32` |
| desk stand *(optional)* | `v2/mini-round-clock-deskstand` | `v2/mini-round-clock-deskstand-32` |
| battery shelves *(optional)* | `v2/mini-round-clock-battery-shelf-x2` — **print two**, either body | |

| File | Material | Settings |
|---|---|---|
| base | PETG (PLA fine) | **Deck face down.** 0.2 mm, 3 walls, 15% gyroid |
| housing | **PETG** if a cell goes in | **Rear plate down.** No supports |
| diffuser | **White PLA** | Face **down**. **0.20 mm layers.** 0% infill, no supports |
| desk stand | anything | Flat on its desk face. **8–10% infill** — it is a big blocky part and the volume figures are solid volume, not filament |
| battery shelf ×2 | anything | Flat. **Print two** |

Either `.3mf` or `.stl` — for these files they carry identical geometry, because
the generator quantises to float32 and heals the mesh *before* writing.

**Slice the diffuser at 0.20 mm layer height.** Each LED's aperture is a radial
tick thinned to 0.20 mm of geometry — one layer — so any other layer height does
not land on a whole number of layers. It prints face-side down, so that layer
goes straight onto the plate and there is nothing to bridge. White PLA
specifically — natural pipes light along the layer lines and bleeds between
cells.

**The diffuser is a proper press fit now.** 0.10 mm of clearance on the wall so
it starts square, then eight crush ribs give 0.60 mm of interference on
diameter. If it is still loose raise `DIFF_RIB_H` in `v2/params.py` to 0.45; if
it will not start, drop it to 0.25.

**Before you print the diffuser, measure the display module's rim thickness** at
the r = 29 mm circle and set `COLLAR_EXTEND = 2.20 - t` in `v2/params.py`.

**PETG for the housing if a battery goes in it.** PLA softens at 55–60 °C; about
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
5. Housing on: 4 × **M3 × 60** self-tapping.
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
