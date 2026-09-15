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

### Grow clock

One switch — **Grow clock** — turns the whole clock into a child's
sleep-training clock, the Gro-Clock idea on this hardware. The ring and the
panel show a *sleep* colour until it is time to get up and a *wake* colour
after, with an *almost time* window before wake and a warning before bed, each
in a colour of its own. The ring is the stars: they go out one by one through
the night, so "how long until morning" is something a child can count. The
panel draws two big Deskimon-style eyes glowing in the state colour on black —
flat bars asleep, half-lidded when morning is close, happy arches awake, heavy
drooping lids at bedtime, and they look around, blink, smile and yawn on their
own — with the digital time along the bottom. The default face, *eyes and
sky*, adds a sun or a moon above the eyes and the stars beneath; the same eyes
on a field of the colour, a sun and moon, or the colour alone are the other
faces.

The dials, every one of them an entity that lands in Home Assistant by itself:
weekday and weekend wake times, bedtime, the almost and bedtime warnings,
**ring and screen brightness on separate numbers** for night and day, a
sunrise fade, star count and shape, a minutes-to-go countdown, naps, *wake
now* / *sleep now*, *five more minutes*, holiday mode, a wake-up rainbow or
sparkle on the ring, and *clock by day*, which hands the panel back to the
ordinary clock an hour after wake and takes it back for the bedtime warning.
`esphome/preview/grow_faces.py` renders every face and state to a PNG from
the same coordinates the firmware draws, so a layout can be looked at before
it is flashed.

**It has no microphone.** *Respond to sound* is real, but the clock is told
about sound by Home Assistant — `packages/wall_clock_grow.yaml` ships the
helper and an example wired to a Voice PE's wake word. During sleep the clock
brightens in the **sleep** colour and says *shh*; it never shows the wake
colour for a noise, because that would reward calling out.

While grow mode is on the clock shows nothing else — no hands, timers or
status. A nursery clock that lights up because the kitchen timer finished is a
bug, not a feature.

## Status

All six phases drafted. Nothing bought, nothing cut, nothing flashed —
see BUILD-LOG.md for exactly what is verified vs assumed. In particular the
screen's `color_order: rgb`, the split ring/screen switches and the per-second
countdown have not been on hardware yet; `Face → colour test` puts three
labelled swatches on the panel to confirm the first one in a glance.
