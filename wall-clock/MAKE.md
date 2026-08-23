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

| File | Material | Settings |
|---|---|---|
| `enclosure/mini/body.stl` | PETG (PLA fine) | Front face **down**. No supports. 0.2 mm, 3 walls, 15% gyroid. 108 mm dia. |
| `enclosure/mini/diffuser.stl` | **White PLA** | Diffusing face **down**. **Bottom layers = 2 exactly.** 0% infill, no supports. |
| `enclosure/mini/backcover.stl` | anything | Flat side down. |

**Bottom layers = 2 on the diffuser** is the single setting that decides whether
this looks good. More and it stops glowing. White PLA specifically — natural
pipes light along the layer lines and bleeds between cells.

The body prints a long bridge over the ring pocket. That is normal in this
orientation and slicers handle it.

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
| `esphome/mini-round-clock-with-display.yaml` | Ring **+** display, with the candidate GC9B71-derived init sequence. |

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
   lands, put it in `twelve_oclock_offset`, re-flash.
2. White pixel not white, or red not red → change `channel_colors: GRB` to `RGB`.
3. Say *"set a timer for two minutes"* and walk the chain in
   `docs/PHASE-6-TEST-PLAN.md`.

**Stage 5 of the test plan is the one that matters** — it is the only place the
*clock > timers > status* priority actually gets tested rather than asserted.

---

## Before you commit filament

Set **`DISP_TAB_ANGLE`** in `enclosure/mini/build.py` to whichever clock
position keeps the tab clear of where your ring's wires exit. It is 12 o'clock
now. Then:

```bash
cd enclosure/mini && python3 build.py --preview
```

That regenerates all three STLs and the SVG, and re-runs every fit check.
