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

## The two surfaces

The ring and the screen are controlled separately. `Display` is the master over
both; `Ring LEDs` and `Screen on` pick a surface. Every setting that used to
drive both at once is split, so "hands only on the ring, markers still on the
screen" is two switches rather than a compromise.

### Everything the ring can light

| what | where | colour | switch |
|---|---|---|---|
| Hour hand | the hour | orange | always on |
| Minute hand | the minute | blue | always on |
| Second hand | the second | grey | Ring second hand |
| Hour markers | all twelve | dim blue-white | Ring hour markers |
| Timer arc | from 12 | teal | while a timer runs |
| Timer pips | where each other timer finishes | dim teal | Extra timer pips |
| Bin night | 12 o'clock | breathing green, yellow for recycling | Status bin night |
| Garage open | 3 o'clock | amber | Status garage open |
| Driveway | 9 o'clock | blinking red | Status driveway |
| Who is home | either side of 6 | Sam blue, Laura magenta, Amanda green, Zac amber | Status who is home |
| Home Assistant dropped | 6 o'clock | dim red | automatic |

**A single blue dot just left of 6 o'clock is a presence pixel**, not a fault.

### Timers and the alarm

The ring counts a timer down in **whole seconds** inside the final minute — one
LED goes out per second. Above a minute it is one LED per minute remaining.

The **alarm sounds until it is cancelled**: it re-announces on a loop, and three
things stop it — the dismiss button, saying *stop the timer*, or starting another
one. The **clock** shows the alert for 15 s by default (`Clock shows it for`, 0 =
for as long as it sounds); a cancel clears the lights instantly either way.

## Status

All six phases drafted. Nothing bought, nothing cut, nothing flashed —
see BUILD-LOG.md for exactly what is verified vs assumed. In particular the
screen's `color_order: rgb`, the split ring/screen switches and the per-second
countdown have not been on hardware yet; `Face → colour test` puts three
labelled swatches on the panel to confirm the first one in a glance.
