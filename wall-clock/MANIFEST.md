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
2. **`DISP_MODULE_D` / `DISP_T`** in `enclosure/mini/build.py` are assumed 1.85″ values. The ring dimensions are measured; these are not.
3. **Entity IDs** in `packages/wall_clock.yaml` are placeholders — the timer names must match your area IDs exactly.

Nothing here has been flashed, sliced, cut, or run against a real Home Assistant.
