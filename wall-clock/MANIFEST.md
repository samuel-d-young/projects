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

## Print — mini v2, the current parts

Built on top of Sam's remodelled `base_in.stl` / `diffuser_in.stl`, which are kept
in the folder so everything re-derives from source. **These supersede
`enclosure/mini/body.stl` and `diffuser.stl` above.**

| File | |
|---|---|
| `enclosure/mini/v2/mini-round-clock-base-v2` | PETG or PLA, **deck face down**. S3 bay, beam, USB-C inlet, tab-slot walls |
| `enclosure/mini/v2/mini-round-clock-rearhousing-battery` | **PETG** if a cell goes in. Rear plate down |
| `enclosure/mini/v2/mini-round-clock-rearhousing-slim` | The no-battery variant, 11 mm shallower |
| `enclosure/mini/v2/mini-round-clock-battery-shim-x2` | Flat. **Print two** |
| `enclosure/mini/v2/mini-round-clock-board-keeper` | 1 g, plate down. **This is what holds the S3 in** |
| `enclosure/mini/v2/mini-round-clock-diffuser-v3` | **White PLA, 0.20 mm layers, face down.** Radial ticks + the hours |
| `enclosure/mini/v2/params.py` | Every dimension, each with where it came from |
| `enclosure/mini/v2/build_v2.py` | Generates all six parts |
| `enclosure/mini/v2/measure_uploaded.py` | Re-derives `params.py` from Sam's STLs. **Run this first if he sends new files** |
| `enclosure/mini/v2/runchecks.sh` | Five verification passes — topology, fit, printability, v3 changes, v5a |
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

## The three things most likely to break

1. **Display pins** in `mini-round-clock.yaml` are ESP-VoCat reference values, not your panel's.
2. **The display module's rim thickness.** `COLLAR_EXTEND` in `v2/params.py` ships at 2.00, which assumes a 0.20 mm rim. Measure it at the r = 29 circle and set `COLLAR_EXTEND = 2.20 − t` before printing the diffuser.
3. **Entity IDs** in `packages/wall_clock.yaml` are placeholders — the timer names must match your area IDs exactly.

4. **The keeper's tongue** assumes the last 2.00 mm of the S3's +x end is bare PCB. If yours has something there, `KEEP_TONGUE_Z0 = 4.20` clamps over the top of it instead.

Nothing here has been flashed, sliced, cut, or run against a real Home Assistant.
