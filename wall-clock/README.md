# HA Wall Clock

A 60-LED ring wall clock driven by Home Assistant, replacing an Amazon Echo Wall Clock.

- Analogue time on a 60-LED ring (hour / minute / second)
- Timer progress from Home Assistant Assist timers
- Ambient status when idle (bin night, garage, driveway faces, who's home)
- No cloud, no account, no phone app

Priority order when something has to give: **reliable clock > timers > status.**

## Layout

| Path | What |
|---|---|
| `BUILD-LOG.md` | Dated running log. Read this first if picking the project back up. |
| `docs/` | Research ledger, BOM, test plan |
| `esphome/` | Device firmware YAML |
| `homeassistant/` | The `packages/wall_clock.yaml` package |
| `enclosure/` | Bambu (FDM) and Glowforge (laser) sources — parametric, see its README |
| `docs/PHASE-6-TEST-PLAN.md` | The runnable checklist. Start here when parts arrive. |

## Status

All six phases drafted. Nothing bought, nothing cut, nothing flashed —
see BUILD-LOG.md for exactly what is verified vs assumed.
