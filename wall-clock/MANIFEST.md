# Wall Clock — file manifest

Everything in this archive, and what each thing is for.
Repo: `samuel-d-young/projects`, branch `claude/home-assistant-wall-clock-om42v2`.

## Start here

| File | |
|---|---|
| `README.md` | What the project is |
| `BUILD-LOG.md` | **Read this first if picking up cold.** Dated, append-only, records *why* each decision was made |
| `HANDOFF.md` | Paste-ready prompt for a LAN-connected Claude session |
| `homeassistant/INSTALL.md` | **The end-to-end install guide.** Steps 1–12 |

## Flash this

| File | |
|---|---|
| `esphome/mini-round-clock.yaml` | **THE firmware.** ESP32-S3-N16R8 + 24-LED ring + 360×360 display |
| `esphome/secrets.yaml.example` | Template — your filled-in copy was sent separately |
| `esphome/wall-clock.yaml` | The future 60-LED production build |
| `esphome/test-clock-d1mini.yaml` | ESP8266 port — superseded, kept for reference |
| `esphome/test/run.sh` | Compile-checks the render lambda without the ESPHome toolchain |

## Install this

| File | |
|---|---|
| `homeassistant/install.sh` | Self-contained installer. Backs up, validates, **rolls back on failure** |
| `homeassistant/packages/wall_clock.yaml` | The package itself (also embedded in install.sh) |
| `homeassistant/test/check.py` | Offline checks: YAML, 35 Jinja templates, firmware↔package entity contract |

## Print and cut — mini (24-LED, 92/71 mm)

| File | |
|---|---|
| `enclosure/mini/body.stl` | PETG or PLA, front face **down**, no supports |
| `enclosure/mini/diffuser.stl` | **White PLA, bottom layers = 2 exactly** |
| `enclosure/mini/backcover.stl` | Any material |
| `enclosure/mini/face.svg` | **Glowforge**, 3 mm plywood, 112 × 112 mm |
| `enclosure/mini/build.py` | Regenerates all of the above from measured dimensions |
| `enclosure/mini/mesh.py` | The STL builder (revolve + boxes, volume-validated) |

## Print — mini v12, the current parts

Built on top of Sam's remodelled `base_in.stl` / `diffuser_in.stl`, which are
kept in the folder so everything re-derives from source. **These supersede
`enclosure/mini/body.stl` and `diffuser.stl` above.** Three clock sizes — pick a
column, everything in it goes together.

All in `enclosure/mini/v2/`, prefixed `mini-round-clock`.

| File | 24-LED, 108 mm | 32-LED, 120 mm | 60-LED, 240 mm |
|---|---|---|---|
| base — deck face down | `-base` | `-base-32` | `-base-60` |
| housing — rear plate down. **Holds the S3** | `-housing` | `-housing-32` | `-housing-60` |
| diffuser — **white PLA, 0.20 mm layers, face down** | `-diffuser` | `-diffuser-32` | `-diffuser-60` |
| numerals — **filament 2**, added as a part of the diffuser | `-numerals` | `-numerals-32` | `-numerals-60` |
| collar fit gauge — **print first**, 3 rings, ~9 g | `-collar-gauges` | same part | same part |
| light guides — **clear/natural PETG**, or cut perspex | — | — | `-light-guides-60` |
| desk stand — flat, 8–10% infill | `-deskstand` | `-deskstand-32` | `-deskstand-60` |

| File | |
|---|---|
| `enclosure/mini/v2/params.py` | Every dimension, each with where it came from |
| `enclosure/mini/v2/build_v2.py` | Generates all 16 parts, all three bodies |
| `enclosure/mini/v2/measure_uploaded.py` | Re-derives `params.py` from Sam's STLs. **Run this first if he sends new files** |
| `enclosure/mini/v2/runchecks.sh` | Five verification passes — topology, fit, printability, diffuser, desk stand |
| `enclosure/mini/v2/README.md` | What changed and why, section by section |
| `enclosure/mini/v2/render_*.py` `*.png` | Picture sheets, all drawn from `params.py` |

## Print and cut — 60-LED production

| File | |
|---|---|
| `enclosure/body.scad` `diffuser.scad` `cleat.scad` | OpenSCAD — **never rendered, preview before printing** |
| `enclosure/face.svg` | Glowforge, 3 mm plywood, 206 × 206 mm |
| `enclosure/generate.py` | Regenerates face.svg + params.scad, validates geometry |
| `enclosure/MATERIALS.md` | Why plywood on the laser and white PLA for the diffuser |

## Reference

| File | |
|---|---|
| `docs/PHASE-1-RESEARCH.md` | Research ledger, every claim tagged verified/assumed |
| `docs/PHASE-2-BOM.md` | BOM in AUD, power budget, level-shifter reasoning |
| `docs/PHASE-6-TEST-PLAN.md` | The runnable checklist. **Stage 5 is the one that matters** |
| `docs/DEVICE-CHOICE.md` | Why the display needs PSRAM, with the source citation |
| `docs/wiring/*.png` | Wiring diagrams for both rigs |

## Not in this archive

`secrets.yaml` — sent separately, deliberately kept out of anything that might
get moved around or shared. It holds your WiFi password and API key.

## The six things most likely to break

1. **Display pins** in `mini-round-clock.yaml` are ESP-VoCat reference values, not your panel's.
2. **The display module's rim thickness.** `COLLAR_EXTEND` in `v2/params.py` ships at 2.00, which assumes a 0.20 mm rim. Measure it at the r = 29 circle and set `COLLAR_EXTEND = 2.20 − t` before printing the diffuser.
3. **Entity IDs** in `packages/wall_clock.yaml` are placeholders — the timer names must match your area IDs exactly.

4. **Which USB connector the ESP32-S3 board carries** — Espressif's v1.1 guide says Micro-USB, the boards sold as DevKitC-1 have two Type-C. The 22 × 6 mm window in the housing rim is sized so it does not matter, but it has not been checked against a board in hand.
5. **The 32-LED ring's dimensions** (111.85 / 96 mm, 32 LEDs) are Sam's numbers, taken as given and not checked against a listing. The whole 120 mm body follows from them.
6. **The 60-LED ring's 172 / 156 mm** is corroborated by three resellers but not by a datasheet — put calipers on it before printing a 240 mm base. And **how far the light carries along a perspex strip** is the one thing in the light-guide design that needs a bench test, not a calculation: `enclosure/mini/v2/README.md` §7 says how to try it in ten minutes.

Nothing here has been flashed, sliced, cut, or run against a real Home Assistant.
