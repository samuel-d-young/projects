# Wall Clock — Build Log

Append-only. Newest entry at the bottom. Every session working on this project adds a
dated entry: what was decided, *why*, and what the next open question is. If you are
picking this up cold, read the last entry first, then `docs/`.

Provenance follows the second-brain convention: facts are tagged **(verified)** — a
primary source was read — or **(assumed)** — plausible but unconfirmed. Never build on
an assumed fact as if it were confirmed.

---

## 2026-08-21 — Project opened

Goal: replace the Amazon Echo Wall Clock. It did two things — showed the time, and lit
a 60-LED ring to visualise voice timers. Rebuild both on Home Assistant, and add the
ambient status the Echo could never do.

**Priority order when something has to give: reliable clock > timers > status.**
This ordering is the tiebreaker for every design decision that follows. The clock must
survive Home Assistant being down; the timer and status features may not.

### Environment (given by Samuel, treated as fact, not re-derived)

- Home Assistant OS at `192.168.1.79:8123`, Core 2026.8.2, admin user Vultron
- ESPHome Device Builder add-on + Mosquitto MQTT installed
- YAML packages enabled: `/config/packages/*.yaml` via `packages: !include_dir_named packages`
- Frigate 0.17.2 on a Pi 5 at `192.168.1.63` — 6 cameras, face + plate recognition.
  Entities: `sensor.next_bin` (state `Green waste`/`Recycling`, attr `next_bin_night`),
  `sensor.vehicle_plate_log`, `sensor.<name>_last_seen` for Sam, Laura, Amanda, Zac
- HA Voice PE satellites on order: Kitchen, Living, Bedroom, Garage
- Location: Victoria, Australia — DST applies, prices AUD, buys from AliExpress /
  Core Electronics / Zaitronics
- Tools on hand: 2x Bambu Lab printers, Glowforge Aura laser, 3x spare Pi 4B,
  2x spare Intel NUC, 1x unused WLED LED matrix

### Constraint noted up front

This session runs in a cloud container with no route to `192.168.1.0/24`. It cannot
reach Home Assistant, cannot run `ha core check`, and cannot flash a device. Anything
requiring those is written out precisely for Samuel to run, and marked as **not yet
verified on real hardware** until he reports back.

### Next

Phase 1 research: how Assist timer state is actually exposed in HA 2026.8, and whether
a separate ESPHome device can subscribe to it. That answer determines the whole design,
so it gets verified against primary sources and then adversarially re-checked before
anything is built on it.

---

## 2026-08-21 — Phase 1 research complete

Full ledger: [docs/PHASE-1-RESEARCH.md](docs/PHASE-1-RESEARCH.md). Headlines:

**The crux question has a clean answer, and it is not the obvious one.** Assist timers really are a
closed subsystem — no entities, no bus events, dispatch hard-keyed to the `device_id` of the device
that set the timer, and the ESP32 firmware itself refuses a second subscriber. A separate ESP32
cannot listen. That part is verified at HA Core tag 2026.8.2 and is final.

But the right move is to **never let the timer enter `TimerManager`**. `intent_script:` can override
`HassStartTimer`, routing a spoken timer into a real `timer.*` helper entity — real state, real bus
events, an absolute `finishes_at`, and **no firmware change on the Voice PE**, so it keeps its OTA
updates. Verified by source; **not yet bench-tested**.

**Process note worth remembering:** the first three research passes all concluded "closed, therefore
reflash the Voice PE", and all three explicitly warned away from the `timer` helper as a dead end.
Three independent agents, same wrong answer — because they all grepped the same way and missed the
same file. Only the adversarial pass, told to *refute* rather than confirm, opened
`intent/__init__.py` and found `/api/intent/handle` and the override mechanism. Convergence is not
confirmation. Keep the refutation step in later phases.

### Decisions taken (subject to Sam's sign-off)

- **Timer path:** `intent_script` override → `timer.<area>` helper → ESPHome `text_sensor` importing
  `attribute: finishes_at`, counted down locally. Fallbacks ranked in the ledger.
  *Revert:* delete the `HassStartTimer:` block from `intent_script:` and HA's built-in handler
  re-registers on restart. Nothing else to undo.
- **Base project:** port `markusressel/ESPHome-Analog-Clock` (CC0, 60-LED, real CI compile) from
  ESP8266/neopixelbus to ESP32/`esp32_rmt_led_strip`. Steal the timer arc from the Voice PE firmware.
- **LED component:** `esp32_rmt_led_strip`. Not a preference — `neopixelbus` and `fastled` *fail
  config validation* under the default `esp-idf` framework.

### Corrections to the brief

- **3.6 A is a worst case, not a spec.** The original WS2812B datasheet has no current figure at all;
  the current V5 part specifies 36 mA/LED. Realistic full white on 60 LEDs is ~2.4 A. Still size for
  60 mA/LED, because sellers don't state the revision.
- **`api: password:` removal in ESPHome 2026.1.0 — confirmed correct.**
- **Level shifter: yes, buy one.** ESP32 guarantees `VOH` = 2.64 V; the original WS2812B wants 3.5 V
  and even the relaxed V5 wants 2.7 V. Out of spec against both. It usually works on the bench and
  that is exactly the failure mode to avoid in a wall-mounted device.

### Landmine flagged

Draft PR `home-assistant/core#174847` adds a `timer_list` entity domain with real triggers and
websocket APIs — the three things missing today. Still Draft, not shipped. It **will require devices
to have a `timer_list` entity to support voice timers**. Building on `timer.*` helpers now is the
cleanest thing to swap over later.

### Next

Blocked on Sam: which WLED matrix he owns (16x16 has *exactly* 60 perimeter pixels and could make
this free), whether the Voice PE must stay stock (the override silences its own ring and chime), and
whether he has spare WS2812B strip from the xLights rig. Then Phase 2 BOM. **Nothing bought yet.**

---

## 2026-08-21 — Decisions locked, Phase 2 BOM ready

Full BOM: [docs/PHASE-2-BOM.md](docs/PHASE-2-BOM.md). **Nothing ordered — waiting on approval.**

### Sam's answers

- **Ring size:** initially 258 mm from 74 LEDs/m strip; **then changed to a one-piece 60-LED
  WS2812B ring, 172 mm OD.** The ring supersedes the strip plan.
- **Voice PE:** accept the `intent_script` override and let the Voice PE's own ring and chime go
  dark. The wall clock is the visual; `assist_satellite.announce` covers audio. Voice PE stays stock
  and keeps OTA.
- **Printers:** P1S and X2D.
- **WLED matrix:** size unknown — dropped from the plan. A strip offcut will be the bench rig instead.

### Why the ring beat the strip, in hindsight

The strip plan was sound but the ring is simply better here. Recording the analysis because it was
non-obvious and shouldn't be re-derived:

Flat WS2812B strip **cannot bend sideways in its own plane** — it only curls perpendicular to the
PCB. So a viewer-facing flat circle needs the strip cut into pieces. Cutting all 60 into singles is
60 joints / 180 wire ends. But approximating the circle as a **12-sided polygon of 5-LED segments**
costs only 12 joints and lands every LED within **0.118° of the ideal 6° dial grid** — 1.2 seconds of
dial, invisible. That was going to be the plan.

The ring removes it entirely: no cuts, no joints, LEDs already facing the viewer, and at 172 mm the
enclosure body (~196 mm) **prints in one piece** on a 256 mm bed instead of four arcs. Smaller clock,
far less risk.

*(Kept for reference: the 12-segment maths is reusable if a bigger clock is ever wanted. Diameter is
locked to strip density — 60/m → 320 mm, 74/m → 261 mm, 96/m → 200 mm, 144/m → 133 mm — because the
LED pitch must subtend 6°, which fixes the radius-to-pitch ratio.)*

### Two findings that changed the plan

**The Glowforge Aura cannot cut the diffuser.** It is a ~5 W **diode** laser, not CO₂, and clear,
white and translucent acrylic are largely transparent to its wavelength. Glowforge's own Aura material
set is opaque acrylic only. Since a diffuser is white/translucent *by definition*, the split becomes:
**Aura → 3 mm plywood** for the face and engraved markers; **Bambu → white PLA** for the diffuser,
printed thin with 60 individual light wells. That's a better diffuser than flat acrylic anyway.
*(Sam's PVC/chlorine warning stands and is correct — nothing in the BOM is PVC.)*

**The MCU recommendation inverted on availability, not merit.** Plain ESP32 is the *better* RMT host
(8 TX channels / 512 symbols vs the S3's 4 / 192). But Core Electronics no longer stocks a cheap
WROOM-32 devkit, so plain ESP32 is now effectively AliExpress-only in AU. The S3 Mini (`WS-27070`,
$9.85, in stock) wins on availability alone. **If there's a spare ESP32 in the xLights box, use that
instead** — it's technically preferable and free.

### Corrections carried forward

- **`max_power` cannot cap an addressable strip in ESPHome** — float-outputs-only. The brightness cap
  must be enforced inside the lambda. Phase 3 must not assume otherwise.
- **A 4 A supply covers the absolute worst case (3.78 A)**, which makes the brightness cap a comfort
  setting rather than a safety mechanism. That is the right way round — a firmware bug should not
  become an electrical problem.
- **GC9A01 rejected:** 11.9 mm digits are legible to ~1.4 m; a kitchen glance is 3–5 m. Also costs a
  ~100 ms main-loop stall every second, which would visibly stutter the ring.

### Next

**Stop. Waiting on Sam to approve the BOM before anything is ordered.** Then Phase 3 firmware —
which can start on a strip offcut before the ring arrives.

---

## 2026-08-21 — Phase 3: firmware written and bench-tested (not yet flashed)

Firmware: [esphome/wall-clock.yaml](esphome/wall-clock.yaml). Test rig:
[esphome/test/run.sh](esphome/test/run.sh).

Sam confirmed the ring is **one piece**, and that he has **smaller LED circles to test with** —
which shaped the design more than anything else this session.

### The single most important line in the file

`api: reboot_timeout: 0s`

The ESPHome default is **15 minutes**: the device reboots itself if no API client connects for that
long. That default would have quietly destroyed priority #1. During an HA outage the clock would
reboot, and because a bare ESP32 has no battery-backed RTC, a **power-on reset loses the time
entirely** — so the clock would go dark at precisely the moment we most want it working. `wifi:` has
the same default and the same fix.

Nothing about this is obvious from the symptom. Worth remembering.

### Graceful degradation, as actually verified

- **HA unreachable → clock keeps perfect time.** Verified by reading `homeassistant_time.cpp`:
  `update()` just asks the API server, and with no clients there is no request and *no error path*.
  Time only ever moves on a real sync. An outage does not disturb the display at all.
- **DST still works during an outage.** HA pushes a POSIX TZ string *plus pre-parsed DST rules*
  alongside the epoch, and the device stores them — so the transition happens on-device. This is why
  `timezone:` is deliberately **omitted** on the `homeassistant` time platform: setting one would
  stop HA pushing updates, which is the opposite of what was asked for.
- **Power-on reset is the one real gap** — the ESP32 RTC does not survive it. SNTP is added as a
  second time source to recover from that without HA. Its `timezone:` is the only hand-set value in
  the file and applies only to a cold boot while HA is down; HA overrides it on first sync.
- If the time is genuinely unknown, the ring shows a deliberate crawling amber dot rather than a
  plausible-looking wrong time. **A confidently wrong clock is worse than an obviously broken one.**

### Design notes worth keeping

- **The render adapts to the actual ring.** `N` comes from `it.size()`, not the substitution, and
  every position is computed as a *fraction of the circle*. So the same firmware draws a correct
  (coarser) face on a 12, 16, 24 or 60 LED ring. Develop on the small rings, change `num_leds`, flash.
- **Brightness is applied exactly once**, on write-out from an off-screen buffer. Layers composite at
  full range and get scaled in one place. This matters because ESPHome's `max_power` **cannot** cap
  an addressable strip (float-outputs only), so the cap is hand-rolled — and a hand-rolled cap that
  is scattered across five layers is a cap you cannot audit.
- `gamma_correct: 1.0` on purpose, so 50% means 50% of current and the brightness number doubles as
  the power story. Revert to 2.8 for a smoother curve, but then stop reasoning about amps from it.
- **The raw light is `internal: true`.** Exposing both it and the brightness number invites a state
  fight between HA's slider and the cap, with no way to tell which one won.
- Timer arc clamps `ratio` at 1.0 — "add five minutes" grows the denominator mid-timer and the arc
  would otherwise jump backwards past full.

### Testing done, and its limits

This container cannot reach HA and has no ESPHome toolchain, so `esphome config` has **not** been
run. Instead the render lambda is extracted, the ESPHome types it touches are stubbed from
`color.h` / `esp_color_view.h` at tag 2026.8.0, and it is compiled with `g++ -Wall -Wextra`.
`esphome/test/run.sh` reproduces it in one command.

That found two real defects before any hardware existed:

1. A malformed `std::min` (three-argument call from a misplaced paren) that would not have compiled.
2. **A silent half-render.** `N` was originally a compile-time constant from the substitution, with a
   `it.size() < N` guard. Connect a 60-LED ring while `num_leds` still said 24 and it renders the
   first 24 pixels and leaves 36 dark — no error, no warning. Fixed by taking `N` from `it.size()`.
   This is exactly the bug that would have been blamed on wiring for an hour.

Current state: clean compile, zero warnings, and hand positions assert correct at 12/24/60 LEDs
(03:00 → pixel 15 of 60, pixel 6 of 24, pixel 3 of 12) with alert covering every pixel at every size.

**Still unverified, and only real hardware settles it:** the YAML schema itself (`esphome config`),
`channel_colors` vs `rgb_order` on the real 2026.8.0 build, the `sntp` + `homeassistant` time
coexistence, and whether `ota:`'s schema is unchanged. Run `esphome config wall-clock.yaml` first.

### Next

Phase 4 — the HA package. It has to publish `sensor.wall_clock_timer_finish_epoch` (absolute unix
epoch, static while running) rather than the timer's own `remaining`, because **`remaining` does not
tick down** and `duration`/`remaining` are `H:MM:SS` *strings* the numeric sensor platform cannot
import at all.

---

## 2026-08-21 — Phase 4: Home Assistant package

Package: [homeassistant/packages/wall_clock.yaml](homeassistant/packages/wall_clock.yaml).
Install steps: [homeassistant/INSTALL.md](homeassistant/INSTALL.md).
Offline checks: [homeassistant/test/check.py](homeassistant/test/check.py).

### The intent override, now verified rather than assumed

Phase 1 called this "verified by source, not bench-tested". Two things were
checked properly this session before writing a line of it:

- **`preferred_area_id` is real.** It is in `intent_script`'s slot schema at
  `components/intent_script/__init__.py:162`, and slots become the template
  variables via `action.async_run(slots, ...)` at line 252. So routing by the
  area of the Voice PE that heard the command is a supported mechanism, not a
  trick. Corroborated by a working reference implementation
  (`djelibeybi/voice-assistant-persistent-timers`).
- **Unlisted slots survive validation.** The slot schema does *not* name
  `hours`/`minutes`/`seconds`, which looked like it would silently zero every
  timer. It does not: `_slot_schema` is built with `extra=vol.ALLOW_EXTRA`
  (`helpers/intent.py:850`), so they pass through to the template. Worth having
  checked — the failure mode would have been every timer lasting zero seconds.

### Correction to the brief

The instruction was "don't restart HA if `homeassistant.reload_all` will do".
For this package, **it won't — the first time.**

`reload_all` only calls `reload` on domains that already have a reload service
registered (`components/homeassistant/__init__.py`, `async_handle_reload_all`).
It cannot bootstrap a domain that was never set up, and this package introduces
`timer:` and `intent_script:`, neither of which is in `default_config`.

So: **one restart on first install, reloads forever after.** After the domains
exist, a reload *does* pick up brand-new package files, because the reload path
re-reads `configuration.yaml` and re-merges packages every time. `reload_all`
also runs a config check first and reloads nothing if it fails, so it is safe
to fire blind.

### Design decisions

- **The package publishes an absolute unix epoch, not "seconds remaining".**
  HA's `remaining` attribute does not tick down while running, and both
  `duration` and `remaining` are `H:MM:SS` *strings* that ESPHome's numeric
  sensor platform cannot import at all. The epoch is genuinely static while the
  timer runs, so the ESP32 counts down against its own clock — no drift, no
  polling, no string parsing on the device.
- **Trigger-based template sensors, not state-based.** State-based templates
  that iterate a whole domain are rate-limited by HA to one update per second
  (whole-system: one per minute). Naming entities explicitly avoids the limit
  entirely, and a state trigger fires on attribute changes too.
- **Everything the firmware reads is namespaced `wall_clock_*`.** The ESP32
  knows nothing about Frigate, area ids, or how many timers exist. All of that
  can change here without reflashing.

### Things deliberately left as FILL-IN rather than guessed

HA 2026.8's default entity_id format is *area + device + entity*, so any
integration-discovered id depends on Sam's area assignments and cannot be
derived from here. `INSTALL.md` has the Developer Tools queries to dump the
real ones. Guessing them would have produced a package that looks right,
passes a config check, and silently never fires.

Two Frigate 0.17 traps are noted in the file where the logic has to survive them:
`sub_label` in `frigate/events` is a two-element **array** `[name, score]`, not
a string; and a null face name renders as the literal string `"None"` — the
same string the 60-second timeout writes, so templates cannot tell them apart.
The unknown-face sensor is written as "person present AND face not in known
list" to sidestep both.

### Known limitation

**One timer per area.** Saying "set a second timer" in the same room replaces
the first. Multi-timer needs a pool of helpers per area plus a free-slot search
in the intent script — deliberately not built until the single-timer path is
proven on hardware.

### Testing done

`homeassistant/test/check.py`: YAML parses, all **35 Jinja templates**
syntax-check clean, and all **10** `wall_clock_*` entities the firmware
subscribes to are produced by the package. That last check is the useful one —
rename either side and it fails loudly instead of leaving a dark ring.

Still unverified: `ha core check` has not been run (no route to 192.168.1.79
from here), the override has never actually fired, and the
`assist_satellite.*` entity naming is a guess because the Voice PE units have
not arrived. That naming is the single thing in the file most likely to be wrong.

### Next

Phase 5 enclosure, sized to the real ring once it is measured. Phase 6 test plan.
