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

Use the **v2** parts in `enclosure/mini/v2/`. They are built on top of the base
and diffuser you remodelled, and they carry the S3 bay, the wall hanger and the
battery pocket. `enclosure/mini/body.stl` is the earlier generated body and is
superseded.

| File | Material | Settings |
|---|---|---|
| `v2/mini-round-clock-base-v2` | PETG (PLA fine) | **Deck face down.** 0.2 mm, 3 walls, 15% gyroid. |
| `v2/mini-round-clock-rearhousing-battery` | **PETG** if a cell goes in | **Rear plate down.** No supports. |
| *or* `v2/mini-round-clock-rearhousing-slim` | PETG or PLA | Rear plate down. No supports. Mains only, and 11 mm shallower. |
| `v2/mini-round-clock-battery-shim-x2` | anything | Flat. **Print two.** |
| `v2/mini-round-clock-board-keeper` | anything | Plate down. No supports. 1 g. Holds the S3 in. |
| `v2/mini-round-clock-diffuser-v3` | **White PLA** | Face **down**. **0.20 mm layers.** 0% infill, no supports. |

Either `.3mf` or `.stl` — for these files they carry identical geometry, because
the generator quantises to float32 and heals the mesh *before* writing, so the
STL round trip has already happened. The 3MF just carries units and metadata
Bambu Studio likes.

**Slice the diffuser at 0.20 mm layer height.** Each LED's aperture is a radial
tick thinned to 0.20 mm of geometry — one layer — so any other layer height does
not land on a whole number of layers. It prints face-side down, so that layer
goes straight onto the plate and there is nothing to bridge. White PLA
specifically — natural pipes light along the layer lines and bleeds between
cells.

**The hours are on the diffuser now**, debossed 0.50 mm: 12, 3, 6 and 9 as
numerals and the other eight as marks. Nothing to do about it at the slicer, but
it is why the diffuser takes ~5 minutes longer than it did.

**The diffuser is now a press fit** (0.10 mm on diameter). If it will not go in,
set `DIFF_FIT = 0.00` in `v2/params.py` and rebuild.

**Before you print the diffuser, measure the display module's rim thickness** at
the r = 29 mm circle and set `COLLAR_EXTEND = 2.20 - t` in `v2/params.py`. It
ships at 2.00, which assumes a 0.20 mm rim. See `v2/README.md` §1b.

**PETG for the housing if a battery goes in it.** PLA softens at 55–60 °C; about
1 W in a small closed box on a west-facing wall in a Victorian summer can sit
well above that. PETG's Tg is ~80 °C. The vents are already in the part.

The base wants a little support inside the display-tab slot — the lead-in ramp
there runs 33–40° from horizontal. That is your own geometry, unchanged, and the
slot is open so it picks straight out. Nothing else in any part needs support;
`v2/runchecks.sh` verifies that.

**Before printing the diffuser, read `v2/README.md` §1.** The screen collar on it
reaches 1.8 mm past the display's front face on the numbers as measured, which
would stop the diffuser seating. There are two one-line fixes and it may be a
non-issue — it turns on the module's thickness at the rim, which is the first
thing to measure.

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

**Order matters at steps 1 and 3.** The breakout cannot go in after the S3, and
the S3 cannot go in after the keeper.

1. **USB-C breakout into its bay first.** Reach in through the rear bore, slide
   it −x along the rails and under the lips until its PCB edge butts the
   shoulder at x = −47. It is then trapped: the channel through the wall is
   13.00 mm and the PCB is 14.20, so pulling on a plug cannot drag it out.
2. Display and ring into the base from the front, as before.
3. **S3 in from the rear, tilted +x end up** — about 18°. Put the raised end up
   into the display-tab window, swing it flat, and let it settle onto the two
   1.50 mm ledges. It will not go in flat and it will not go in −x end up; the
   bore only opens to 8.60 mm at that end. If your board has male headers
   pointing down, snip them; there is 1.6 mm under the PCB for solder joints,
   not pins.
4. **Keeper on**, tongue over the board's +x end, 2 × **M3 × 12** self-tapping.
   That is what stops the board floating into the clock — 0.20 mm of movement
   left, from 4.60.
5. Solder ring and display leads to the board. Power it at the **5V and GND
   pins**, not the board's own USB port — see `v2/README.md` §2 for why. Run the
   breakout's VBUS and GND to those same pins.
6. Battery, if you are fitting one: in the housing with a shim either side, its
   output lead up through the deck port at 6 o'clock (the slot at y +10…+13),
   and its input from the USB-C inlet.
7. Housing on: 4 × M3 self-tapping. **M3 × 30** for the slim housing, **M3 × 40**
   for the battery one.
8. One screw in the wall — 4 mm shank, head no wider than 8 mm. Hang it.
9. Plug a USB-C cable into the inlet at the bottom of the clock. About 13 mm of
   the plug's overmold stands proud, so there is something to get hold of.

**One part to buy for this:** Adafruit **ADA4090** USB-C breakout, A$5.40 inc GST
at Core Electronics, 20.4 × 14.2 × 5.0 mm, with the 5.1 kΩ CC resistors on it.
Those resistors are not optional — without them a USB-C supply never turns 5 V
on. **Not ordered.**

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
