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

---

## 2026-08-21 — Phases 5 and 6: enclosure and test plan

Enclosure: [enclosure/](enclosure/) — parametric, driven entirely by
`params.py`. Test plan: [docs/PHASE-6-TEST-PLAN.md](docs/PHASE-6-TEST-PLAN.md).

### The laser question has a specific answer, and it isn't a preference

The brief said "cast acrylic or plywood only, tell me which and why".

**Plywood — because the Aura is a ~5 W *diode* laser and physically cannot cut
clear, white or translucent acrylic.** Those are largely transparent to its
wavelength; Glowforge's own Aura material set is *opaque* acrylic only. Since a
diffuser is white by definition, **the diffuser cannot be lasered on this
machine at any setting.**

So the split is: **Aura → 3 mm plywood** for the face and engraved markers,
**Bambu → white PLA** for the diffuser. That turns out better, not worse: a
printed diffuser gives each of the 60 pixels its own cell with a baffle between
it and its neighbour, which is what makes a 60-point dial read as 60 discrete
points instead of a smeared glow. A flat acrylic sheet could never do that.

Sam's PVC/chlorine warning stands and is correct. Nothing in the build is PVC.
`MATERIALS.md` also flags the related trap: unlabelled "acrylic-look" sheet
from marketplace sellers should not go in the machine at all.

### Design organised around one requirement

*"Wall mounting that doesn't need me to take it down to change anything."*

The cleat stays on the wall. The face screws on **from the front**; behind it
the diffuser lifts out and the ring is right there, and the ESP32 sits in the
middle bay — inside the ring's own 156 mm hole — with its USB port facing
forward. Four M3 screws and everything is serviceable with the clock still
hanging. Fixings sit at 45°, between hour markers rather than on one.

### Geometry checks caught two collisions before any material was cut

`generate.py` asserts the parts fit each other and the machines, not just that
the file was written. On the first run it failed two checks:

1. M3 heads at r=92 fell outside the 190 mm face edge.
2. Hour ticks at r=89–98 overflowed a 95 mm face radius.

Both came from designing the markers for a face I had then shrunk. The fix was
better than a bigger bezel: **move the ticks onto the centre disc, pointing
inward.** The disc is 154 mm of otherwise-dead plywood, and using it keeps the
bezel slim instead of forcing a ~210 mm face. Rendered the SVG to PNG and
looked at it to confirm — numbers passing is not the same as it looking right.

### Single source of truth

`params.py` generates both `face.svg` (Glowforge) and `params.scad` (which the
`.scad` parts include). Measure the real ring, change three numbers, re-run,
re-export STLs. `params.scad` and `face.svg` are generated — hand edits get
overwritten, and both files say so at the top.

### Glowforge gotcha worth recording

**No `<text>` elements in the SVG, deliberately.** Glowforge does not embed
fonts, so a text node renders with whatever gets substituted, or not at all.
Every mark in `face.svg` is geometry. Numerals, if ever wanted, must be
converted to paths before upload. Also: cut the outline **last** so the part
stays supported in the sheet — SVG order is only a hint, set it in the UI.

### Test plan

Ordered so nothing untested ever powers anything expensive, and nothing goes on
the wall until it has soaked for 24 hours. Bench PSU current limits are given
per stage so the supply trips instead of something burning.

**Stage 5 is the one that matters** — it is the only place the *reliable clock >
timers > status* priority is actually tested rather than asserted. It
specifically requires leaving HA down for **20+ minutes**, because that is what
proves `reboot_timeout: 0s` took effect; with the 15-minute default the device
would reboot there and lose the time on a cold boot.

Troubleshooting is written around the failure modes the research turned up, not
generic advice: RMT exhaustion fails loudly at setup and is *never* the cause of
flicker; the upstream flicker issue was closed **as stale, not fixed**, so there
is no software answer to wait for; "only pixel 0 wrong" points at the level
shifter because the first LED sees the rawest edge of the signal.

### Status

**Nothing bought, cut, printed or flashed.** The `.scad` files have never been
rendered — no OpenSCAD in this environment — so preview them before committing
filament. `face.svg` has been generated and visually checked but not cut.
`esphome config` and `ha core check` have not been run.

### Next

Sam's hands. In order: order the ring, prove the software path on a small test
circle (Stages 1–2 need no 60-ring at all), then measure the real ring and
regenerate the enclosure.

---

## 2026-08-23 — Bench rigs: D1 mini, ESP32-S3 + round display, mini enclosure

Sam has a **D1 mini**, a **Mokungi 24-LED WS2812B ring**, and a **spare
ESP32-S3-N16R8**, and asked for a 360×360 round display in the middle showing
time over weather.

### The device question has a hard answer

**D1 mini runs the ring fine. It cannot run that display, and neither can a
plain ESP32.** A 360×360 RGB565 framebuffer is 253 KB against ~30 KB of ESP8266
heap and ~160 KB on a PSRAM-less ESP32.

It is enforced in code, not just tight: ESPHome's ST77916 model declares
`requires={"psram"}`, so a config without PSRAM **fails validation**. The
N16R8's 8 MB octal PSRAM satisfies it exactly — the right board was already in
the drawer.

**Worth recording:** the ESPHome docs page for `mipi_spi` does *not* list
ST77916 among its supported models. That listing is stale — `models/st77916.py`
is present in the source at tag 2026.8.0, exposed as `model: ESP-VOCAT`. Had
this been taken from the docs it would have concluded "unsupported, buy a
different panel". Checking the source is the only reason it didn't.

The caveat that matters: that model ships the init sequence **and the pins for
the ESP-VoCat v1.2 board**, because that is where Espressif's init data came
from. A generic Waveshare/Guition 1.85" module is wired differently. The GPIOs
are substitutions at the top of the config and must be corrected first.

### Delivered

- `esphome/test-clock-d1mini.yaml` — ESP8266 port. `neopixelbus` instead of
  `esp32_rmt_led_strip` (the latter is ESP32-only; the 2026.6 neopixelbus
  deprecation was ESP32-only, so ESP8266 is unaffected). Render buffer cut from
  256 to 64 pixels — 256 would be careless on 30 KB of heap. Default brightness
  30%, not 55%, because 24 LEDs at full white is ~1.44 A and a PC USB port
  will not supply that.
- `esphome/test-clock-s3-round.yaml` — S3 + ring + QSPI display + weather.
- `enclosure/mini/` — body, diffuser and back cover **as STLs**, plus the
  Glowforge SVG.
- `docs/wiring/` — both wiring diagrams, generated not drawn.
- `docs/DEVICE-CHOICE.md` — the framebuffer arithmetic and the source citation.

### STLs without OpenSCAD

No OpenSCAD in this environment, so `enclosure/mini/mesh.py` builds the meshes
directly: revolve a 2-D profile around Z, add boxes for baffles, write binary
STL. Every part is validated by computing its signed volume with the divergence
theorem — a closed, correctly-wound mesh gives a positive volume matching the
analytic value.

That check earned its keep immediately: the first run produced **negative**
volumes of exactly the right magnitude, i.e. every part was inside-out. Silent,
and a slicer would have produced nonsense. Fixed by reversing the winding; the
tube test now matches the analytic volume to 0.005%.

The baffles overlap the revolved rings rather than being booleaned in. Slicers
union overlapping closed shells, so this prints, but a mesh checker will call
it non-manifold. Noted in the mini README rather than left to surprise.

### Both new lambdas were compile-checked

Same harness as the production config. Both compile clean under `-Wall
-Wextra` and pass the hand-position assertions at 12/24/60 LEDs.

### Deliberate difference: the mini uses a friction fit

The 60-LED body has screw posts with modelled pilot holes because OpenSCAD can
subtract them. The mesh generator has no CSG, so the mini face drops into a
3 mm recess retained by a 2 mm proud lip. For a rig that gets opened constantly
during development that is arguably better anyway.

### Still unverified

`esphome config` has not been run on either new config. The `.stl` files have
never been sliced. The **Mokungi ring dimensions are assumed** to match the
standard 66.0 / 51.0 mm — measure before printing. And the display pins are
reference values, not Sam's panel.

---

## 2026-08-23 — Installer script

Sam asked for the HA side to be installed for him. **Not possible from here, and
this was tested rather than assumed:** `curl` to `192.168.1.79:8123` and
`192.168.1.63:5000` both time out, a raw TCP connect gets no route, and this
container's egress is a public cloud IP (`160.79.106.139`). There is also no
Home Assistant connector in this session — only GitHub, Google, Railway, Vercel
and Stripe. There is no path to that LAN.

So the next best thing: [`homeassistant/install.sh`](homeassistant/install.sh),
a self-contained installer to run from the Terminal & SSH add-on. The package
YAML is embedded in the script, so nothing has to be transferred.

It is written to be safe to run rather than merely convenient:

1. Refuses to start if the `ha` CLI is missing or `/config/packages` does not exist.
2. Timestamps a backup of any existing `wall_clock.yaml`.
3. Writes the package, then runs `ha core check`.
4. **If the check fails it restores the backup and stops** — it will never leave
   a broken config behind.
5. Only then offers a restart, and defaults to *no*.

All four paths were exercised locally against a fake `/config` and a stub `ha`
binary: missing CLI, missing packages dir, happy path, and a failing config
check (which correctly rolled back).

It also prints the Developer Tools queries for the entity ids that still have to
be filled in by hand, and the two post-restart checks — the
`Intent HassStartTimer is being overwritten` log line being the success signal,
and the `wall_clock_*` entity count.

The `--check-only` flag validates the current config and changes nothing.

---

## 2026-08-23 — Device named `mini-round-clock`

Sam named the device in ESPHome Device Builder. Renamed
`round-clock-s3.yaml` → **`mini-round-clock.yaml`** to match, since Device
Builder names the config file after the device, and updated the substitutions.

The device name is not cosmetic — it sets three things:

| | |
|---|---|
| Hostname | `mini-round-clock.local` |
| OTA target | the same, so it must match or OTA finds nothing |
| Entity prefix | every entity this device creates in HA |

Resulting Home Assistant entities:

- `number.mini_round_clock_brightness`
- `number.mini_round_clock_night_brightness`
- `select.mini_round_clock_mode`
- `switch.mini_round_clock_display`
- `light.mini_round_clock_backlight`

The LED ring itself stays `internal: true` and is deliberately **not** exposed —
exposing it alongside the brightness number invites a state fight between HA's
slider and the cap, with no way to tell which one won.

16 characters, against ESPHome's 24-character limit for `name:`. Fine.

**No change needed on the HA package side.** Everything the firmware subscribes
to is namespaced `wall_clock_*` and lives in Home Assistant, not on the device,
so renaming the device does not touch it. That indirection was the point.

Both lambdas re-checked after the rename: clean compile, all assertions pass,
all four display branches exercised.

---

## 2026-08-23 — Real hardware photos: wrong display driver, and the tab problem

Sam sent photos of the actual parts. Two findings, one of which would have cost
an evening.

### The display is a GC9B72, not an ST77916

Silkscreen: `VER:TFT 2.10 1.0 / Driver IC:GC9B72 / Resolution:360*360`.
Header: `TE SDO BL CS DC RST SDA SCL VCC GND`.

`SDA` + `SCL` + `SDO` and no `D0-D3` means **single 4-wire SPI**, not QSPI.

The config had `model: ESP-VOCAT` (an ST77916) on a `type: quad` bus. Wrong
driver *and* wrong bus. It would have failed as a blank or garbled panel — a
symptom that looks exactly like bad wiring, which is the worst kind of wrong.

**ESPHome 2026.8.0 has no GC9B72 model.** Swept the `mipi_spi/models/`
directory; there is no `gc9b72.py` and the string appears in no model file
reachable. `DriverChip("CUSTOM")` exists (`display.py:95`) and
`CONF_INIT_SEQUENCE` becomes **Required** for it (`display.py:139-143`).

So the path is `model: CUSTOM` + `bus_mode: single` + the panel's own init
sequence — which is not published anywhere verifiable. The display, fonts and
spi blocks are **commented out** so the ring config flashes and works today,
with a banner explaining exactly what is needed to re-enable them.

Recorded in the file, because it is a trap: **do not substitute a GC9A01 init
sequence.** GC9A01 is a 240x240 part; its gamma and power tables produce a
blank or garbled panel indistinguishable from a wiring fault.

### The tab problem, and why the answer is the plywood

Sam: *"I want the screen in the middle, but the connectors for the ring are also
in the middle and the screen isn't perfectly round because of the pins."*

The module is a round PCB with a **rectangular tab** carrying the 10-pin header.
The ring has its own 4-pin header pointing inward. Both want the centre.

The insight that dissolves most of it: **the PCB does not need to be round — the
plywood aperture does.** `APERTURE_D` is now `DISP_ACTIVE_D - 1`, i.e. 1 mm
*inside* the active area, so the plywood covers the tab and the ragged PCB edge
and all you see is a perfect circle of screen.

That leaves the physical clash, solved with a **notch**:

- `mesh.py` gained `revolve_mod()` — a revolve where tagged profile points have
  their radius modulated by angle. A point pushed outward over a narrow angular
  window carves a local pocket, which is how a rotationally-symmetric builder
  produces a notch **without any boolean geometry**. Validated: a notched test
  solid comes out watertight with positive volume, and `mod=None` still matches
  the analytic volume to 0.01%.
- At the tab's clock angle the pocket wall and the seating shelf both push out
  to the tab's reach, deleting the shelf locally so the tab drops through into
  the bay. Everywhere else the shelf carries the module.
- When the tab overhangs the ring's inner wall, the **diffuser's inner skirt is
  notched at the same angle** so the tab sits in the diffuser's plane. Costs the
  inner baffle on two or three cells — invisible behind plywood.

The first attempt instead seated the module deep enough to tuck the tab behind
the ring, and the geometry check caught that this put the screen **9.6 mm** down
a well. Rejected: a shadowed screen is a worse outcome than a missing baffle.
The check now enforces `WELL_DEPTH < 6.0`; the current design is **0.0 mm**.

### Desolder both headers

The single highest-value physical change. `DISP_TAB_T` assumes **1.6 mm** — the
bare PCB fin with the header removed and wires soldered flat. Left on, the
header adds ~9 mm behind the tab and forces the deep well back. The ring's 4-pin
header is the same story. Two connectors removed is the difference between a
clean build and a shadowed one.

### Still estimated — these gate printing

`DISP_PCB_D` 60, `DISP_ACTIVE_D` 53, `DISP_T` 4, `DISP_TAB_REACH` 36,
`DISP_TAB_W` 24. All from photos. The ring is measured; the display is not.
With the current estimates the tab overhangs the ring's inner wall by 1.5 mm,
which is exactly the collision Sam described — but whether that is real depends
on a caliper.

---

## 2026-08-23 — Measured display; the tab forces a behind-the-ring seat

Sam measured: round PCB **60 mm**, screen **55 mm**, tab **40 mm wide**,
**67 mm** overall top-to-bottom, **4 mm** thick.

### The tab is a rectangle, so its corners decide everything

```
midline reach = 67 - 60/2       = 37.00 mm
corner radius = hypot(20, 37)   = 42.06 mm
LED circle                      = 40.75 mm
```

The corners land **1.3 mm past the LED circle**. Estimating the tab by its
midline reach (37 mm) would have looked survivable; the corners are the real
constraint and they are not. **No rotation avoids this** — the tab cannot share
the LED plane at any angle, so the module seats behind the ring PCB and the tab
passes through a slot underneath.

### The slot is local in both axes

Opening the whole pocket wall to the corner radius would have deleted the ring
and diffuser seats at that angle and left a visible gap in the light ring. The
slot instead widens only over the tab's clock angle (83°) *and* only across the
2 mm of depth the tab occupies (z 11.4–13.4). The diffuser needs no notch at
all now — every cell keeps its baffles.

### Two mistakes the checks caught before any filament

1. **Slot touching the ring.** `Z_TAB_FRONT` came out exactly equal to
   `Z_PCB_B` — the slot's own 0.4 mm front clearance had been carved out of the
   0.4 mm ring gap, leaving zero. Now `RING_TAB_GAP` is sized so both survive.
2. **A 0.4 mm floor membrane.** At the tab angle the slot removes everything
   behind it, so whatever remains between the ring pocket floor and the slot
   *is* the floor there. At 0.8 mm gap that was a 0.4 mm skin spanning 7.5 mm
   radially — it would have cracked under the ring. Raised to 1.6 mm gap for a
   **1.2 mm floor**, at a cost of ~1 mm of screen depth. New check enforces it.

### The depth trade, stated honestly

Diffuser cut from **6 mm to 4 mm**, because every millimetre of diffuser pushes
the ring back and comes straight off the screen's viewing depth. Final recess is
**6.4 mm**.

That is fine, and the earlier 6 mm limit was arbitrary. With a 54 mm aperture a
6.4 mm recess only shadows the screen edge past ~85° off-axis — head-on and at
any normal viewing angle it is invisible. Structural floor and diffuser depth
are worth more than the last millimetre. Threshold relaxed to 8 mm with that
reasoning recorded in the file.

### Still an assumption

`DISP_TAB_T = 1.6` — the bare PCB with the 10-pin header **desoldered**. Leave
it on and the tab is ~10 mm thick, the slot will not take it, and the module
moves back another 9 mm into a well that cannot be read.

---

## 2026-08-23 — A candidate init sequence for the GC9B72

Product listing confirmed the silkscreen: **GC9B72**, **SPI**, 2.1", 360x360,
made by **Baishun (Baishundianzi)**. (The listing also claims "320x240
resolution" in one bullet — boilerplate, ignore it; the silkscreen and the
headline both say 360*360.)

### What exists, and what doesn't

Searched properly for a GC9B72 driver. There isn't one:

- **ESPHome 2026.8.0** — no `gc9b72` model file anywhere in `mipi_spi/models/`
- **esp-iot-solution** — no `esp_lcd_gc9b72` component
- **LovyanGFX / Arduino_GFX** — nothing
- **Espressif's datasheet CDN** — `GC9B72_DataSheet_V1.0.pdf` returns 404

### But the GC9B71 is the same family and the same panel geometry

`espressif/esp-iot-solution/components/display/lcd/esp_lcd_gc9b71` ships a full
init table, and the GC9B71 datasheet
(`dl.espressif.com/AE/esp-iot-solution/GC9B71_DataSheet_V1.0.pdf`, 6 MB, fetched
and read) states **"360 RGB x 360 Resolution"** — the same geometry as the
GC9B72, same Galaxycore family, same SPI/QSPI interface options. The table opens
with `0xFE` / `0xEF`, the Galaxycore inter-command unlock pair, so it is the same
register dialect.

Its 48-entry table is converted to ESPHome `init_sequence:` form in
[docs/gc9b72-display-block.yaml](docs/gc9b72-display-block.yaml) — 47 entries
after dropping `0x11` SLPOUT, which mipi_spi appends itself along with DISPON
and the reset pulse. Parses clean; all bytes in range.

### This is not the same as the GC9A01 substitution warned about earlier

Worth being precise, because it looks like a reversal and isn't:

|  | GC9A01 | GC9B71 |
|---|---|---|
| Resolution | 240x240 | **360x360, same as the GC9B72** |
| Family | GC9A | **GC9B, same as the GC9B72** |
| Unlock pair | different | **0xFE / 0xEF, same dialect** |

A GC9A01 sequence would have been a different-sized panel from a different
family. The GC9B71 is the immediate sibling. It is still **not verified** for
the GC9B72 and is labelled that way in the file.

### If it does not work

Do **not** hand-tune the registers. Get the vendor demo code for this exact
module from the seller (Baishun, 2.1" 360x360 GC9B72) — ten minutes of asking
beats an evening of poking gamma tables. The file says so too.

---

## 2026-08-24 — The display works. The GC9B71 substitution was wrong.

The panel lights and renders the clock face correctly. Flashed 00:20 over OTA,
ESPHome 2026.8.0, 20 MHz, `pixel_mode: 16bit`.

### The answer was a real GC9B72 table, and it does exist

Yesterday's entry concluded no GC9B72 init sequence was public, having checked
ESPHome, esp-iot-solution, LovyanGFX and Arduino_GFX. That conclusion was
wrong, and the reason is worth recording: **those are all library indexes.**
A plain code search across GitHub for the literal string `GC9B72` finds it
immediately, in projects that are not display libraries at all.

- `xboot/xstar` — `xstar/driver/framebuffer/fb-gc9b72.c` (MIT). The original.
  A bare-metal framebuffer driver for an Allwinner V821 board. Nothing about
  it is discoverable by looking for "display library with GC9B72 support".
- `MaliosDark/Arduino_GC9B72` — an Arduino_GFX-style port that cites xboot.

Both were fetched and compared by hand. They agree byte-for-byte, including
the gamma banks and the 32-byte `0x6E` gate-mux table. Two independent copies
agreeing is what promoted this from "candidate" to "transcription".

xboot drives the panel as SPI mode 0 at 50 MHz with separate CS / D-C / RST —
the same 4-wire arrangement as this board, which is what makes the table
transferable at all.

### Why the GC9B71 substitution failed, and why the reasoning still looked good

The GC9B71 is the same Galaxycore family, the same 360x360 geometry, and opens
with the same `0xFE`/`0xEF` unlock pair. All true, all verified, and all
insufficient. The register map differs. The panel lit and accepted data — a
uniform fill came out as stripes — which is the signature of a controller that
is clocked and addressed correctly but scanning out with the wrong timing.

**Family resemblance is not a substitute for the actual table.** The previous
entry's own advice ("do not hand-tune the registers, get the vendor code")
was right; the mistake was spending the evening on substitutes before
exhausting the search for the real thing.

### Two ESPHome behaviours that made the debugging much harder than it was

Both verified by reading `components/mipi/__init__.py` at tag 2026.8.0,
`Model.get_sequence()` — not inferred from behaviour:

1. `SLPOUT` (0x11) and `DISPON` (0x29) are appended automatically, with their
   delays. Correctly documented, and the config already did this.

2. **`COLMOD` (0x3A) is appended unconditionally from `pixel_mode`.** The
   docstring claims it is added "if not already in the custom sequence". The
   code does not check:

   ```python
   sequence.append((PIXFMT, pixel_mode))
   ```

   So a hand-written `0x3A` inside `init_sequence` is always overridden.
   `MADCTL` (0x36) is appended the same way.

This invalidated two consecutive experiments. Adding `[0x3A, 0x05]` "changed
nothing" because ESPHome overwrote it; the follow-up `pixel_mode: 18bit` test
then sent `0x3A, 0x06` to a panel that wants `0x05`, so it was not testing the
hypothesis it appeared to test. Both readings were measuring ESPHome, not the
panel.

The lesson generalises: when a register write appears to have no effect,
confirm it actually reached the wire before concluding anything about the
hardware. `pixel_mode: 16bit` is now pinned with a comment saying why.

### What was ruled out along the way, and how

Worth keeping, because each one was cheap and each one narrowed the field:

| Hypothesis | Ruled out by |
|---|---|
| Not receiving data at all | Pattern changed horizontal -> vertical purely from changing frame content |
| Signal integrity / too fast | Identical output at 10 MHz and 40 MHz |
| Wrong bus width (QSPI vs 1-bit) | Config is `clk_pin` + `mosi_pin`, 4-wire; and 207 ms at 10 MHz is exactly 360x360x2 bytes, so the right volume was going out |
| Backlight not driven | Panel visibly lit once anything rendered |

### Files

- `docs/gc9b72-display-block.yaml` — rewritten. Was the unverified GC9B71
  table; is now the verified GC9B72 one, with both ESPHome gotchas documented
  inline.
- `esphome/mini-round-clock-with-display.yaml` — the flashed config. Byte
  identical to `/config/esphome/mini-round-clock.yaml` on the box (32346 B,
  md5 `af1016fdd8911fd6f45dee4a22c1b20b`).
- Previous config on the box is backed up as `.pre-gc9b72-bak`.

---

## 2026-08-24 — First local session: the timer path runs end to end on real HA

Picked up from `HANDOFF.md` on Samuel's Windows box. The handoff's premise —
"a local session is on the LAN and can install this" — is confirmed:
`192.168.1.79:8123` and `192.168.1.63:5000` both answer immediately.

### The handoff's steps 1–5 were already done

Worth stating plainly so nobody re-runs `install.sh` over a working system: a
later cloud session (commits `c98f9a43`, `8f15ce9b`) had already installed the
**multi-timer pool** package, and it is live. Verified against the running
instance rather than assumed:

| Handoff step | State |
|---|---|
| 1. Package installed | Done — 10 `sensor.wall_clock_*`, 8 `binary_sensor.wall_clock_*`, `input_boolean.wall_clock_timer_alert` |
| 2. Entity ids filled in | Done — the file's own header records them as resolved 2026-08-23, and they match the live registry |
| 3. Restarted | Done — domains came up 18:33 |
| 4. Override loaded | **Confirmed** — `Intent HassPauseTimer is being overwritten by <ScriptIntentHandler - HassPauseTimer>`, "shows up 8 times" (the eight Echo-parity intents) |
| 5. Entities exist | Confirmed, unprefixed |

`custom_templates/wall_clock_timer_match.jinja` is installed and importable —
`spoken(125)` returns `2 minutes and 5 seconds` from Developer Tools. The
Settings dashboard view from `8f15ce9b` is live at `/wall-clock-build/settings`.

### The thing that had never been tested, tested

Every previous entry flagged the same gap: the override was verified *by source*
and had never actually fired. It has now, via
`conversation.process: "set a timer for two minutes"`.

```
response: "Timer set for 2 minutes."   response_type: action_done
```

The whole chain, sampled while running:

| | |
|---|---|
| `timer.wall_clock_1` | `active`, `finishes_at 2026-08-24T12:16:56+00:00`, `duration 0:02:00` |
| `sensor.wall_clock_timer_finish_epoch` | `1787573816` |
| `sensor.wall_clock_timer_total` | `120` |
| `sensor.wall_clock_timer_count` | `1` |
| `sensor.wall_clock_timer_slots` | `[{'i': 1, 'entity': 'timer.wall_clock_1', 'st': 'active', 'label': '', 'area': '', 'total': 120, 'fin': 1787573816}]` |

**The central design claim holds on real hardware.** Sampled at 91 s and again
at 37 s remaining, `finish_epoch` was byte-identical both times. That is the
whole reason the package publishes an absolute epoch instead of the timer's
`remaining` — Phase 4 argued it from source, and it is now observed.

At zero: slot released to `idle`, `binary_sensor.wall_clock_timer_alert` **and**
`input_boolean.wall_clock_timer_alert` both `on`, every sensor reset to `0`/`[]`.
~60 s later both cleared themselves. Nothing left latched.

**The announce automation did not error.** With `assist_satellite` empty (the
Voice PE units still are not here), the guessed entity naming that Phase 4
called "the single thing most likely to be wrong" simply did not fire. It is
still unverified — but it fails silent, not loud, which is the right way round.

`area` came back `''` because `conversation.process` carries no device context,
so `preferred_area_id` is absent. That path — a real satellite in a real area —
is the one thing the timer feature still has untested.

### The device is not on the network at all

All `mini_round_clock` entities are `unavailable`. HA logs
`Can't connect to ESPHome API for mini-round-clock @ 192.168.1.80`.

A sweep of `6053` across the whole `/24` found **nothing**, so it is not a
changed DHCP lease — the board is unpowered or not joining wifi.

**A trap worth recording:** `ping 192.168.1.80` reports `0% loss`, which looks
like the device is up. It is not. The reply is
`Reply from 192.168.1.32: Destination host unreachable` — an ICMP unreachable
from a *different* host, which Windows `ping` still counts as a received packet.
There is no ARP entry for `.80`. Check the port, not the ping.

### Registry leftovers

The real areas are `living_room`, `kitchen`, `bedroom`, `garage`, `front_door`.
The pre-pool design's per-area helpers still exist in the entity registry as
`timer.kitchen`, `timer.living_room`, `timer.bedroom`, `timer.garage`,
`timer.front_door`, all `unavailable` — they are no longer in the YAML. Harmless,
but they clutter the timer domain and should be deleted from
Settings > Devices & Services > Entities.

### Next

Hands at the bench. Power the S3 and get it back on wifi — everything on the
Home Assistant side is installed, loaded and now actually exercised, so the
ring going live is the next thing that can be observed rather than reasoned
about. Then the one remaining untested path: a spoken timer from a real
satellite, which is what finally exercises `preferred_area_id`.

---

## 2026-08-24 — Colour is customisable, and resolved in one place

Ring bring-up closed out first: **twelve o'clock is at the top with
`twelve_oclock_offset: 0`**, so the offset needed no correction, and the face
rendering in its intended colours settles `channel_colors: GRB` as correct.
Both were outstanding from MAKE.md step 6.

### A control that only half-worked

`select.mini_round_clock_colour_theme` described itself as covering "hands and
accents". It covered the ring only — **every colour on the 360x360 display was
hardcoded and ignored the theme entirely**. Six `Color(...)` literals: the
timer countdown, its label, the extra-timer lines, and the three analogue
hands. Changing the theme moved the ring and left the screen alone.

### The design, and why HSV rather than RGB

Twelve numbers — hue, saturation and intensity for hour, minute, second and
timer — plus a fifth theme option, `custom`, that consults them. The four
presets are untouched and stay one click away, so there is always a known-good
palette to come back to.

HSV is not a preference here, it is what makes one palette drive two very
different surfaces. **A bare LED at a metre and a backlit LCD do not want the
same value.** The ring's timer colour is deliberately dim (V 35) so the arc can
never be mistaken for a hand; the same teal as screen text has to be bright to
be legible at all. Storing RGB would weld those together and one surface would
always be wrong. Storing hue and saturation separately lets the screen reuse
the hue at its own value:

- **ring** — value as authored
- **screen** — saturation x0.6 (fully saturated text on a dark panel is harsh)
  and a value set by the element's *role*, because the ring's value encodes LED
  power, not importance

Checked against what the screen used to hardcode: the rule reproduces the old
timer text `(120,235,220)` as `(94,235,219)`, and the old analogue minute hand
`(120,180,255)` as `(106,153,224)`. Close enough that the change reads as a
unification rather than a restyle.

### One place decides colour

The palette resolver lives under `interval:` at 250 ms and writes two globals,
`pal_ring` and `pal_scr`. Neither render lambda does any colour maths.

That is the same argument the brightness cap makes: a value computed in one
auditable place can be reasoned about, one scattered across two lambdas cannot.
It was also forced — `addressable_lambda` compiles to a bare function pointer
and cannot capture, so a shared helper was never available. A global was.

Globals are seeded with the resolved *default* palette so the first frames are
correct in the gap before the resolver's first tick.

**Pips are derived, not controlled.** All four presets already set the pip
colour to ~62% of the timer colour, so custom does the same. One fewer control,
and the two can never drift into looking like unrelated features.

**`mono` pins saturation to zero on every element.** Custom must never leak
into it — it is the accessible palette and nothing on the face may depend on
telling one hue from another.

### Verified, at last, by the real toolchain

Previous entries all carry the same caveat: `esphome config` had never been
run, and the lambdas were only checked against a stub harness. Neither applies
now. There is no `g++`, `esphome` CLI or Docker on the Windows box, but the
**ESPHome Device Builder add-on compiles for real**, which is strictly better
than the stub:

- `esphome config` -> **`INFO Configuration is valid!`** — the first time this
  project has ever passed it
- full ESP-IDF build, 115 objects, **compiled and linked clean**; the only
  warnings are upstream `mipi_spi.cpp` `-Wempty-body` noise
- OTA uploaded, device rebooted, `safe_mode:154: Boot seems successful;
  resetting boot loop counter`
- `[S][select]: 'Colour theme' >> custom` accepted with no crash, and no
  `mini_round_clock` entity is unavailable

Switching to `custom` is visually identical to `default`, which is the useful
test: it means the RGB -> HSV -> RGB round-trip of the presets is faithful.

**Before overwriting the box's config it was diffed against the repo** by
copying it out of the Device Builder editor. Byte-identical, so nothing
unrecorded was discarded. Worth doing rather than assuming.

### A stale banner, corrected

The file's header still said **"THE DISPLAY SECTION IS COMMENTED OUT"** and
"`esphome config` NOT yet run", and warned about ESP-VoCat pin defaults. All
three were false — `display:` is live, the pins are this module's real ones,
and the panel has worked since 2026-08-24. Replaced with what is actually true.
A header that lies about the file underneath it is exactly the thing that costs
someone an evening.

### Not done

`esphome/mini-round-clock.yaml` — the ring-only fallback — still has the old
hardcoded theme block. It is not flashed and nothing depends on it, but the two
configs have now diverged and it should be brought to parity before anyone
reaches for it as a fallback.

---

## 2026-08-24 — Rain radar: RainViewer, one tile, no compositing

Plane B's first real feature. Everything below was checked against the live API
and the live ESPHome rather than reasoned about.

### The shortcut that does not work

The obvious design is to have the ESP32 build the tile URL from its own clock.
RainViewer's index encourages it — frames are exactly 600 s apart and `time`
sits on a 600 s boundary:

```json
{"time": 1787578800, "path": "/v2/radar/461614397c0b"}
```

**But the URL does not contain the timestamp.** `path` carries an opaque hash
that cannot be derived from anything. A device built on the obvious assumption
would 404 forever while looking entirely correct — the exact failure shape this
log keeps running into. Home Assistant therefore has to poll the index; there
is no version of this where the device works alone.

### Melbourne fits in one tile, and only at one zoom

Solved rather than eyeballed (`z/x/y` is standard Web Mercator):

| zoom | tile | Melbourne at | covers |
|---|---|---|---|
| 6 | 57/39 | (0.77, 0.27) | 495 x 485 km |
| **7** | **115/78** | **(0.54, 0.54)** | **247 x 246 km** |
| 8 | 231/157 | (0.08, 0.09) | 124 x 122 km |

z=7 lands 4% off dead centre, so **nothing has to be stitched or composited**,
anywhere, by anyone. The firmware draws the image at `(-14, -14)` — 4% of
360 px — which takes out the residual offset. z=6 and z=8 both put the city in
a corner.

Fetched live to confirm: `512x512`, PNG **colour type 6 (RGBA)**, ~58 KB,
HTTP 200. The alpha is genuine, so clear sky is transparent and the clock face
shows through instead of sitting on a coloured slab.

Alpha coverage is **identical across every colour scheme** (measured: 27.9%
fully transparent, 70.6% solid on a wet night). Scheme choice is therefore
purely about how the rain reads, never about how much of the face it covers.
Scheme 2 picked for a dark face.

### `online_image` exists — and `RGBA` does not

Both settled by making ESPHome answer rather than by reading docs, which this
project has already been burned by once:

- `'type' is a required option for [online_image]` — proves the component
  ships in 2026.8.0
- feeding it a junk value made it print the enum:
  `'BINARY', 'GRAYSCALE', 'RGB565', 'RGB', 'TRANSPARENT_BINARY', 'RGB24', 'RGBA'`
- **and `RGBA` still fails**: *"Image type RGBA is removed; replace with
  `type: RGB` and `transparency: alpha_channel`"*

That last one is a trap worth naming: **the removed spelling is still listed as
valid by the enum**, purely so the validator can emit that message. Trusting
the list gets you a config that looks right and will not build.

### Design

- HA (`packages/wall_clock_radar.yaml`) polls the index every 300 s and
  publishes `sensor.wall_clock_radar_url` — the finished string — plus
  `sensor.wall_clock_radar_age` in minutes.
- The device subscribes to the URL, calls `set_url()` on a new value, and
  re-fetches. **No JSON on the device.**
- HTTPS straight from the ESP32 with `verify_ssl: false`. The alternative —
  proxying via `/config/www` — needs `allowlist_external_dirs` and a snapshot
  automation for the same picture. No credentials are involved.
- Readiness comes from the component's own `on_download_finished`, not from
  asking the image its width: `resize:` gives it a size before a byte arrives,
  so it would claim to be ready while holding nothing.
- **Stale radar is not drawn.** Anything over 45 minutes old is skipped, because
  a two-hour-old frame still reads as "it is raining now". RainViewer runs ~8
  min behind and publishes every 10, so 45 is several missed frames.
- Drawn immediately after the background fill, so the clock is always on top,
  behind a switch that defaults **off**.

### State

`esphome config` **passes** ("YAML saved", no errors) and the config is saved on
the box. **Not yet compiled or flashed** — the add-on's editor toolbar became
unresponsive and the remaining step is one click on Install. The running
firmware is still the colour build; the radar changes it in no way until
installed, and the switch defaults off even then.

`packages/wall_clock_radar.yaml` still has to be placed in `/config/packages/`
by hand — this session has no write path to `/config` (no SSH, no Samba, no
file-editor add-on), which is recorded above under the installer entry.

---

## 2026-08-25 — Radar works, then crashes the device. Reverted.

The whole chain was built and every link verified. It downloads. It also
**crash-loops the ESP32**, so it is reverted and the clock is back on the
colour build.

### What was proven to work

- HA package installed at `/config/packages/wall_clock_radar.yaml` (fetched
  from the public repo with `curl` inside the **Terminal & SSH add-on** — which
  *is* installed here, it simply was not in the sidebar; the earlier claim that
  this box has no write path to `/config` was wrong)
- `ha core check` -> `Command completed successfully`, exit 0
- **A restart, not `reload_all`** — checked rather than assumed: `rest:` appears
  in no other package and not in `configuration.yaml`, so it is a new domain and
  `reload_all` cannot bootstrap one. Same trap as `timer:`/`intent_script:`.
- `sensor.wall_clock_radar_url` produced a real tile URL, 77 chars
- Firmware compiled, flashed, rebooted clean, all entities present

### Two silent defects found by checking rather than assuming

**1. `device_class: timestamp` on a unix epoch.** That device class demands ISO
8601. Given an integer, HA rejects the state as `unknown` *but still populates
`json_attributes`* — so the URL sensor kept working perfectly and the whole
thing looked correct. The only symptom was the age sensor falling through to
its 999 sentinel, which made the firmware refuse to draw a frame it had
downloaded fine.

**2. `set_url()` does not fetch.** It stores the URL. With
`update_interval: never` nothing ever triggered a download, so the device would
have held a correct URL forever and drawn nothing. Needs an explicit
`update()`.

Both would have presented as "the radar just doesn't work" with nothing in any
log.

### The one that actually stops this: the download blocks the main loop

```
[I][online_image:132]: Downloading image (Size: 66942)
[W][component:421]: api took a long time for an operation (2031 ms), max is 50 ms
INFO Processing unexpected disconnect from ESPHome API
[E][esp32.crash:404]: *** CRASH DETECTED ON PREVIOUS BOOT ***
    Reason: Fault - Unknown   Crashed core: 1
[W][safe_mode:085]: Last reset too quick; invoke in 7 restarts
```

The fetch *succeeds* — 66942 bytes, the right size for the tile. But it runs
**synchronously in the main loop for ~2 seconds**, forty times ESPHome's 50 ms
budget. The API drops, the device faults, reboots, re-reads the URL from HA on
reconnect, downloads again, and faults again. A self-sustaining crash loop,
and `safe_mode` was counting down towards taking the clock out entirely.

Note the trigger is the **URL arriving**, not the radar switch. The switch only
gates *drawing*. So "turn the radar off" would not have stopped it — a design
error worth fixing whatever approach comes next: never fetch what you are not
going to draw.

### Reverted, deliberately

Priority ordering decides this. Radar is status tier; a crash-looping clock
fails tier one. So:

- `/config/packages/wall_clock_radar.yaml` -> `/config/wall_clock_radar.yaml.disabled`
- HA restarted, which removed the URL sensor and **immediately stopped the
  crash loop** (device then stable, verified by polling port 6053)
- device reflashed from commit `63eee3f` — the colour build, `online_image`
  count 0, 1364 lines
- the crashing config kept at `/config/esphome/mini-round-clock.yaml.radar-crashing`

### What to try next, in order of promise

1. **Fetch a much smaller image.** 360x360 RGB+alpha is ~518 KB decoded from a
   67 KB PNG. A 128x128 tile would cut both dramatically. The blocking window
   scales with it.
2. **Let HA do the work.** `/config/www/` is writable and served at `/local/`
   without auth (that is how `flightdeck.html` is served), so HA can fetch,
   downscale and re-encode a small PNG and the ESP32 pulls it over plain HTTP
   on the LAN — no TLS handshake, less data, no decode of a full-size frame.
3. **Gate the fetch on the switch**, so the radar cannot destabilise a clock
   that is not even showing it.
4. Check whether this ESPHome exposes a non-blocking download for
   `online_image`; the 50 ms budget warning suggests the component expects to
   be used with much smaller images.

### Also noted

`online_image:` as a top-level block is **deprecated, removed in ESPHome
2027.1.0** — it becomes `image: - platform: online_image`. Whatever comes next
should be written in the new form.
## 2026-08-24 — v2 rear end: S3 bay, wall hanger, battery pocket

Sam uploaded a reworked `Mini_Wall_Clock_Base.stl` and `Mini_Wall_Clock_Difuser.stl` —
the LED ring's wires now run straight down, and the diffuser has grown a collar that
grips the screen. He asked for three additions: somewhere at the rear for the ESP32-S3
and its wiring, a way to hang it on a wall, and a pocket for a small USB-C battery,
plus a recommendation on which battery.

Everything new lives in `enclosure/mini/v2/`. `build_v2.py` reads his STL and adds to
it; it never redraws his geometry.

### Reading his files rather than assuming

His parts are not `build.py` output any more, so the first job was to measure them
instead of guessing. Probing along rays and bisecting the solid boundary gives
**(verified — measured off the uploaded mesh)**:

| | |
|---|---|
| body OD | r = 53.9926, 144-gon, vertex at 0° |
| face recess | floor z = 19.0, lip inner r = 51.9807 |
| ring pocket | r 35.1080 … 46.3516, floor z = 11.8 |
| display pocket | wall r = 30.2788, seat top z = 8.6, rear bore r = 27.78 |
| wire slot (new) | \|y\| ≤ 13.003, x −27.78 … −43, open front to back |
| tab slot | half-angle 41.758°, out to r = 42.6566 |
| diffuser | 24 baffles at 15° pitch; new collar r 27.916 … 30.108, 8.2 tall |

The wire slot settles the clock's orientation: **−x is 6 o'clock**, so +x is up.

### Three things wrong with the uploaded files

1. **A disconnected 605 mm³ solid in the base.** A crescent at r 35.06–40.90,
   ±41.9°, z 11.80–15.75, whose faces lie exactly on the body's cut surface, and
   which arrived as a +2832 / −2227 mm³ shell pair — a boolean that failed to merge.
   It sits precisely in the window the display tab passes through. Sliced as-is it
   prints as extra plastic where the display goes. Dropped, and `build_v2.py` says so
   when it runs. **(verified)**

2. **The diffuser collar over-reaches by 1.8 mm.** Seat at 8.60 + a 4 mm module puts
   the module's front face at 12.60; the diffuser seats when its baffles meet the LED
   tops at 15.00, which lands the collar bottom at 10.80. The collar hits the display
   1.8 mm before the diffuser is down. **(verified arithmetic, on an assumed 4 mm rim
   thickness — the 4 mm is Sam's measurement of the whole module, not of the rim the
   collar actually lands on, and that is the number to check first.)**
   Both fixes are shipped: a trimmed diffuser, or `SEAT_DROP = 1.80` in `params.py`
   which drops the seat instead and needs no diffuser reprint.

3. **The wire slot is a through-slot** — no material at 180° from z = 0 to 22. Hidden
   by the plywood, so never visible, but the deck now closes it from behind.

### Where the S3 went, and why it needed nothing built for it

The board is 62.74 × 25.40 mm **(verified — Espressif's own
`DXF_ESP32-S3-DevKitC-1_V1_20210312CB.pdf`; a web search had claimed 58 × 28, which is
wrong)**.

The base already has a dog-bone void along the x axis — rear bore, plus the wire slot
at 6 o'clock, plus the tab window at 12 o'clock — and along \|y\| ≤ 12.7 it is clear
from x = −43 to +40.7. That is 83.7 mm for a 62.74 mm board. So the deck just gives it
a floor. The board's parts top out at z = 4.00 with the display seat at 8.60: 4.6 mm of
air.

Ledges catch it at the two **short** ends only. The DevKitC-1 runs its pad rows down
both long edges 1.27 mm in, so a ledge there fouls any soldered header.

Nothing screws it down and nothing needs to: hanging on a wall, gravity acts along −x,
which is in the board's own plane, and the only way out is backwards into the housing
2 mm behind it.

### Why two printed parts, not one

A single part cannot print without support. Its rear cavities open one way and its
front pockets the other, so whichever face goes on the plate, the other end needs
propping. Split at z = −2.4 and each half prints in its natural orientation with a
near-solid first layer and every void opening upward.

### What the checkers caught

Three passes, `./runchecks.sh`. They were not ceremony — each found real defects:

- **A stepped void that broke the mesh.** Cutting the board window as two overlapping
  boxes left coincident coplanar faces where they met; in double precision that is
  fine, but quantised to float32 for the STL it became a 404 mm³ phantom
  self-intersection. Cutting the window straight through and adding the ledges back as
  solids gives the same shape and a clean mesh. **The lesson generalises: subtracting
  a stepped void whose lobes share full side walls is a mesh bug waiting to happen.**
- **Screws with nothing to bite.** The pilot holes were being subtracted from the deck
  alone — 2.4 mm of guide, then 8 mm of solid PLA for the screw to find its own way
  through. Now bored from the assembled part.
- **The hanger fighting the battery.** Stiffening ribs behind the keyhole reached
  inward to r = 28 and ate the battery footprint. Running the numbers, they were never
  needed: at 400 g the shank bears on 4.6 × 3.5 mm of PLA, about 0.25 MPa against a
  ~50 MPa yield. Removed. Then the same check found the *screw head* — which ends up
  inside the box once the clock is hung — in the same place, so the keyhole moved out
  to r = 46, the drop came down to 7.5 mm, and the pocket shifted 7 mm toward
  6 o'clock.
- **Slivers in the battery cradle.** A frame clipped to the pocket circle went
  tangent at its corners and left walls down to 0.03 mm. Replaced with a shim whose
  outer edge *is* the circle, so it cannot.
- **A 0.3 mm overhanging ledge round the whole part**, from insetting the deck to
  avoid coincident cylinders. Matching Sam's 144-segment wall exactly turned out to be
  clean anyway, and removed 101 mm² of overhang.

Two findings were kept rather than fixed, because they are Sam's geometry and
unchanged: 409 mm² of 33–40° overhang on the tab-slot ramp, and the feather edges where
that ramp runs out. `check3` now baselines against the uploaded file at run time rather
than against hand-drawn boxes, so it can tell his from mine.

### The battery: the answer is "it is a UPS, not a power source"

Power budget from datasheets **(verified, except the display)**:

| | typical | worst |
|---|---:|---:|
| ESP32-S3-N16R8 devkit, WiFi up, HA API connected | 60 mA | 140 mA |
| 24-LED WS2812B ring, clock face at ~25% | 33 mA | 145 mA |
| 2.1" 360×360 GC9B72 + backlight **(assumed — extrapolated)** | 95 mA | 150 mA |
| **at 5 V** | **188 mA = 0.94 W** | **435 mA = 2.18 W** |

That is 22.6 Wh a day. A 5,000 mAh bank holds ~18.5 Wh nominal, ~16 Wh after boost
losses — **under 18 hours**. It does not last a day, and nothing that fits a 108 mm
disc does better.

Two useful facts fell out of the sweep:

- **The retail market is bifurcated and this clock lands in the gap.** Slim banks are
  wide (Cygnett 95 × 65, Anker MagGo 104 × 71); banks narrow enough for a 108 mm circle
  are 25–26 mm thick. That is what takes the clock from 44 mm deep to 55 mm.
- **Idle cutoff is not the failure mode here** — at 188 mA the clock sits above the
  usual 50–75 mA threshold. The one that bites is that many banks, once flat, will not
  resume output when mains returns until someone presses the button. On a clock 2.4 m
  up a wall, that is fatal, and it is the thing to test on the bench before one goes
  in.

Also worth acting on: **print the housing in PETG if a cell goes in it.** PLA's Tg is
55–60 °C; ~1 W in a small closed box on a west-facing Victorian wall can plausibly sit
at 50–70 °C inside. Vents are in the design; the material change is nearly free.

Both housing depths are shipped so the trade is Sam's: `-slim` (44.4 mm, mains only) or
`-battery` (55.4 mm, ~17 h).

### The battery, after verification

Adversarial verification against the retailers found exactly one bank that is
both small enough for a 108 mm disc and buyable in Australia:

**Anker Nano A1653, 5,000 mAh, 76.96 x 36.83 x 24.89 mm** (verified from Anker's
own spec table, corroborated by a hands-on review), about **A$49 at Scorptec**
in Melbourne. 3.7 mm of spare length in the pocket. Pass-through verified in the
printed manual. ~17 hours. The shim is cut for exactly these dimensions.

Three things the verification changed, all of which would have cost an evening:

- **The output is a rigid fold-out MALE USB-C plug; the single female port is
  the input.** The pocket has 15.2 mm at 12 o'clock and 6.5 mm at 6 o'clock, and
  a fold-out plug plus a coupler plus a lead does not fit in 15.2 mm. The
  bounding box was never the risk — the connectors are. **(verified)**
- **A1259 is a different product** — 10,000 mAh, 104 mm long, will not go in.
  Easy substitution to accept at a counter.
- **"22.5W" is marketing**; Anker's manual says 18 W max total output.

Two pieces of good news: Anker document a 30-90 mA minimum sustaining draw, and
the clock's 188 mA is 2-6x above it, so idle cutoff will not bite; and the A1653
has no trickle mode, so there is nothing to re-arm after an outage. **(verified)**

Still unknown, and it is the thing that decides the whole idea: **whether it
resumes output by itself after being drained.** Not in the manual, not on either
product page, not in Anker's support articles; owner reports on Reddit were
unreachable from here, which is a gap in coverage rather than evidence of
absence. `docs/BATTERY.md` has a four-step bench test that settles it, plus the
related transition-dropout test — a pass-through bank that blinks its output for
a second when mains comes and goes reboots the ESP32 every time.

Runner-up if either test fails: **Baseus Compact Type-C Edition 5,000 mAh,
A$45.99, verified in stock at baseus.com.au** — a plain brick with ordinary
ports and nothing that folds out, but at 80 x 40.2 x 25.6 it lands *exactly* on
the pocket's limit, so measure the real unit first.

`params.fits()` and `check2` now score candidates against the pocket properly,
including corner radius: treating a bank as a sharp-cornered rectangle is
conservative by about 0.7 mm at 2 mm radii, and 0.7 mm was the difference for
one of these.

### Open

- Nothing sliced, nothing printed, nothing bought.
- The display's 95 mA is the weakest number in the budget and the largest load. Ten
  minutes with an inline meter settles it and could change the battery decision.
- The ring's die revision is unknown — V5 vs original is 2× per channel. Power the ring
  alone, all pixels zero, read the supply: ~14 mA means V5, ~24–36 mA means older.
- The display module's rim thickness, per finding 2 above.

---

## 2026-08-24 — v3: the four fixes after Sam's test fit

Sam printed the v2 parts, fitted the display, and reported: the pocket the bottom
of the screen sits in is too loose and the screen doesn't stay upright; the
diffuser should be a tight press fit; the part over the LEDs should be one layer;
and the diffuser's inner collar can go 2 mm further in to help hold the screen.

He also gave the number that mattered most: **the tab that sticks out of the
bottom of the screen is 30.55 mm wide. (verified — measured on the real module.)**

### The looseness was a wrong assumption, and it was mine

`DISP_TAB_W` had been 40.0 since Phase 5 — never measured, just carried forward.
The slot is cut as an angular wedge sized for it, which at r = 35 is **46.62 mm
wide**. Against a 30.55 mm tab that is **±25.9° of free rotation**: the module
could sit more than a clock-hour off true and there was nothing to stop it.

Two walls either side now bring the slot to 31.15 mm.

| | before | after |
|---|---:|---:|
| slot width at the tab | 46.62 mm | 31.15 mm |
| tab can rotate | ±25.90° | **±0.47°** |
| screen edge can move | 12.5 mm | **0.22 mm** |

The walls run from the deck to the ring pocket floor with a 45° lead-in chamfer
on the top inner edge, sit at |y| ≥ 15.575 (the S3 board is |y| ≤ 12.70, so they
never meet), and — a side effect worth having — **put back the ring pocket floor
the tab window had removed**, so the ring is no longer unsupported across 83° at
12 o'clock. The checker measures the restored sector at 100%.

### What Sam's report told me that he didn't mean to tell me

The v2 notes said the diffuser's collar over-reaches the module by 1.8 mm, on
the assumption that the module is 4 mm thick at its rim. **That was wrong, and
the report is what disproves it.**

The collar lands at base z = 19.00 − 8.20 = 10.80; the seat is at 8.60; so it
clamps a rim of exactly 2.20 mm and fouls anything thicker. Sam has assembled
these and reports the screen **loose** — not the diffuser standing 1.8 mm proud.
So the collar is not touching and **the rim is under 2.20 mm**. The 4 mm figure
is the module overall, not the rim the collar lands on. Interference finding
retired. **(verified by assembly, which beats my arithmetic.)**

That also fixes the collar problem: the right extension is exactly (2.20 − rim).
Sam asked for 2.00, which corresponds to a 0.20 mm rim and is almost certainly
long. It is shipped at 2.00 as asked, with the one-caliper-measurement fix
written next to it: measure the rim at the r = 29 circle, set
`COLLAR_EXTEND = 2.20 - t`. If it prints proud, the proud gap *is* `t − 0.20`.

### The other two

- **Press fit.** The diffuser was 46.000 in a 46.3516 pocket — 0.70 mm of slop on
  diameter, which is why it rattled. Now 46.4016, a 0.10 mm diametral
  interference. `DIFF_FIT = 0.00` backs it off to a slip fit.
- **One layer over the LEDs.** Membrane 0.80 → 0.20, which is a single layer at
  0.20 mm layer height, printed membrane-side down so it lands straight on the
  plate with no bridging. **The cut steps around all 24 cell walls** — thinning
  through them would have left every wall standing on nothing. All 24 verified
  still at full height. Slice this part at 0.20 mm or the arithmetic stops
  working.

### Two things the checker got wrong, and now doesn't

Both were measurement bugs in the checks, not in the parts, and both were
over-reporting:

- **Bridge span was measured as a bounding box.** A 0.1 mm wide ring 78 mm
  across has a 78 mm bounding box and is not a bridge at all — the nozzle is
  never more than 0.05 mm from solid. It now finds the patch's own boundary
  edges and takes twice the greatest distance to them. Worst bridge across all
  five parts dropped from a reported 6.6 mm to a real 2.6 mm.
- **The diffuser had no thin-wall baseline.** It reported four 0.00 mm regions
  at r = 35.5 as new. Running the same analysis on Sam's uploaded diffuser finds
  them in the same place — they are artefacts of his mesh, like the base's.

### Open

- Nothing sliced, nothing printed since the change.
- The module's rim thickness, per above. One caliper measurement, and it is the
  only thing standing between the collar and an exact clamp.
- Whether 0.10 mm diametral is the right press. It is a judgement; the number is
  one line.

---

## 2026-08-24 — v4: the lit band becomes a line

Sam: *"Update the diffuser to be more of a line where the LED shows through like
the echo wall clock."*

The diffusing band was **r 39.00 … 44.90 — 5.90 mm wide**, so a lit LED read as a
5.90 × 9.72 mm rectangle. That is 1.6:1 — a blob, not a line. The Echo Wall
Clock is a plain white face with a thin ring of light on it.

The 0.20 mm skin is now only a **2.50 mm slot centred on the LED circle at
r = 40.75**; everything either side is **2.00 mm** of white PLA.

| | before | after |
|---|---:|---:|
| lit aperture | 5.90 mm | **2.50 mm** |
| one lit LED shows | 5.90 × 9.72 mm | **2.50 × 9.72 mm** |
| aspect of one segment | 1.6 : 1 | **3.9 : 1** |

Three decisions inside that:

- **The slot is narrower than the LED it sits over.** A 5050 is 5 mm and spans
  r 38.25–43.25; a 2.50 mm slot inside that acts as an aperture, not a window,
  which is what makes the lit edge crisp rather than fading out. **(verified —
  geometry, checked in check4.)**
- **The inner band is flush with the skirt at 2.00 mm**, so the face inboard of
  the line is one continuous shelf and not a step.
- **The cell walls stay at full height.** They leave 91% of the circle open, so
  adjacent LEDs read as one line, but each LED still gets its own cell. Dropping
  them would give a smoother line and smear the hands, and the priority order
  for this project is clock > timers > status. **(assumed — the 2.00 mm
  surround's opacity is a judgement; white PLA transmission at that thickness
  has not been measured.)**

### Two mesh problems this surfaced, both worth keeping

- **Zero-volume debris.** Adding the two bands took the diffuser from 1 body to
  10 — one real solid of 12653 mm³ and nine flat shells with no volume, left
  where a new surface landed at exactly the same coordinate as an old one. Five
  of them came from a single mistake: the outer band stopped at r = 45.00, which
  is exactly where the thinning cut ended, leaving a 0.01 mm sliver. Overlapping
  further in killed those; `finalise()` now drops the rest, but only shells under
  0.01 mm³, and it reports how many so the cleanup cannot hide a real break.
- **The volume check was measuring the wrong thing.** Two independent volume
  calculations over a surface with non-manifold edges do not agree, and the
  disagreement *is* the ambiguity those defects introduce. Sam's uploaded
  diffuser disagrees with itself by **0.054%**; the derived part by **0.043%**,
  with 160 bad edges against his 387. It is now held to "no worse than the
  source", because zero is not reachable from that source.

Also corrected a claim in the README: the STL and 3MF carry **identical**
geometry for these parts, because `finalise()` quantises to float32 before
writing either. The earlier "prefer the 3MF, the STL round trip is what breaks
things" was true in general and not true of these files.

### Open

- `DIFF_LINE_W` (2.50) and `DIFF_OPAQUE_T` (2.00) are both judgements. The
  first is cosmetic; the second decides whether the face reads as white or as a
  dim glow, and a light meter or a test print settles it.
- The plywood face's ring window is still 11.5 mm wide, so ~9 mm of white
  diffuser shows around the line. Left alone deliberately — that is the Echo
  look — but `face.svg` is where to change it.

---

## 2026-08-24 — v5: radial ticks, the hours on the diffuser, and the S3 actually held

Four things Sam asked for, in two messages:

> *"Update the difuser to be more of a line where the LED shows through like the
> echo wall clock."* … *"the line needs to be perpendicular to the screen, like
> the lines are. I want the LED's to look more like the echo wall clock led's."*
> … *"Write the clock times on the difuser too."* … *"make sure that the ESP32 S3
> is held in properly and that the USB connector can be connected externally from
> the outside of the wall. I may or may not use a USB battery or USB power
> supply."*

### The aperture was the right size and the wrong axis

v4 narrowed the lit band from 5.90 mm to a 2.50 mm arc. Sam's follow-up said what
was still wrong: an arc lies *along* the circle. Each cell's aperture is now a
**radial tick**, 2.00 mm across × 4.00 mm long with radiused ends, centred on the
LED circle at r = 40.75 and sitting inside the 5050's own r 38.25–43.25 so it is
lit evenly end to end.

| | v3 | v4 | v5 |
|---|---:|---:|---:|
| lit aperture | 5.90 mm band | 2.50 mm arc | **2.00 × 4.00 tick** |
| points | — | along the circle | **at the centre** |
| dark between two LEDs | 0.95 mm | 0.95 mm | **8.67 mm** |

The 8.67 mm of dark is what makes it read like an Echo: 24 separate marks, not a
segmented ring.

One claim in v4's notes was wrong and is now corrected in `check4`: it said the
aperture's aspect ratio stops crosstalk. It does not — the **cell wall** does.
The walls run the full 2.00 mm depth of the cell, from the face to the LED PCB,
so light from the next LED never enters the cell at all. The aperture's 1.80 ×
2.00 mm shape decides the viewing angle (±29°), which is a different thing.

### The hours, debossed on the face

12, 3, 6 and 9 as 3.40 mm upright numerals; the other eight as marks, quarters
heavier. All of it in the 3.5 mm band between the plywood window's inner edge
(r = 35.0) and where the ticks start (r = 38.75), debossed 0.50 mm with 1.50 mm
of PLA left under them so they stay opaque. Debossed rather than thinned because
the Echo's markings are printed on a white face — the LEDs are what lights up.
`MARK_DEPTH = 0` and a 0.20 mm cut makes them lit instead, if that turns out to
be the nicer thing.

### The real find: 183 non-manifold edges, and where they were

Adding the ticks broke the build outright — `Error.NotManifold` out of
`finalise()`. Chasing it was worth the time.

Every construction step was clean in isolation and clean in double precision. It
only broke after the float32 quantise, where the mesh split into six parts: the
body, plus three razor shells of ±9.02 mm³ with **1 and 3 faces each**. A shell
with 3 faces cannot enclose anything, but trimesh's divergence-theorem volume on
an open sliver returns a large number anyway, so `drop_debris` kept them, and
concatenating them is what made the mesh non-manifold. `drop_debris` now judges
by face count as well as volume: under 4 faces, it goes.

That fixed the crash and left a worse problem. The part came out with **160
non-manifold edges** and its two volume measurements disagreeing by 0.128% —
against 0.054% for Sam's own file, which is the baseline the checker uses. So I
went looking for where the damage actually lives, and it is not spread out at
all:

```
Sam's diffuser: 183 bad edges, ALL of them in r 35.5-46.0, z 0.8-4.0
                (his two annular ribs are notched at each of the 24 wall angles,
                 and the notches are modelled with faces that do not pair up)
inside r = 35.0: 0 bad edges, watertight, perfect
```

Every version so far had been unioning new geometry **through** that damage and
making it worse. So: keep his mesh only inside r = 35.00, and rebuild the band
from measured numbers — inner rib 35.4996–36.6996, outer rib 44.7995–46.0000, 24
walls 1.000 mm thick with centres at 7.5 + 15k° to within 0.0003°, all z 0–4.000.

Result: **0 bad edges, watertight, one body, volumes agreeing to 0.000%.** The
first clean version of this part. The rebuilt ribs are continuous where his were
notched, which is a better light seal and a stronger press fit as well. The
diffuser is now held to `strict` in `check1` like every other part.

Two smaller lessons from the same chase, both about coincident surfaces:

- The face fill's top plane at z = 2.00 is coplanar with the skirt top. Five
  variants were tested; **butting** the skirt gave 0 stray shells and every
  overlap gave 2–3. Coincident-and-coextensive is fine. Coincident-and-
  overlapping is what breaks.
- The 24 cell walls butting the ribs' 144-gon at exactly r = 36.70 gave one razor
  sliver per wall — a straight chord meeting a faceted arc. Burying the wall ends
  0.4/0.6 mm inside the ribs gave 0.

### "Held in properly" turned out to mean the old instruction was impossible

The v2 note said *"push it up into the deck window until its rim meets the
ledges."* That cannot be done. With a 3.00 mm ledge at **both** ends the opening
is 57.64 mm and the board is 62.74 mm; a rigid board tilts in only if its
projection fits, and 62.74·cos θ ≤ 57.64 needs θ ≥ 23.4°, at which the raised end
wants 13.3 mm of headroom against 8.60 in the bore and 11.80 in the tab window.
It does not go in. Nobody had noticed because nobody had printed it yet.

`LEDGE_END` is now **1.50 mm** — a 60.19 mm gap, 17.9° of tilt, 8.87 mm of rise
against 11.80 available at the +x end. It has to go in **+x end up**; the bore at
the other end stops at 8.60. `check5_v5a.py` does not take my word for that: it
walks the real mesh through the motion in half-degree steps, searching for a
clear pose at each angle, and fails if any angle has none. Worst-case ledge
bearing is 1.50 − 0.45 = 1.05 mm of PCB, which is plenty for a shear ledge.

Then the actual retention, and the thing that took the longest to see: **you
cannot capture a rigid board in a through-window from both sides at the same
places.** Ledges below and lips above at the same ends make insertion impossible;
that is geometry, not a detail. So:

- a **beam** across the USB end at z 4.20, integral to the base. 0.20 mm above
  the tallest thing the board carries, so it cannot foul a connector or a
  soldered header whatever the board's layout — it only ever touches the board if
  the board lifts. Its pillars stand at x = −20, not over the board's end at −24,
  because the bore is r = 27.78 and at x = −24 it is only open to |y| < 13.99
  against a deck window that already reaches 13.15. 0.84 mm of landing. At −20 it
  is 19.30, and they get 3 mm.
- a **keeper**, 1 g, two M3, that goes on *after* the board with a tongue over
  the far end. Separate because it has to be: fixed at +x it blocks the tilt-in,
  fixed at −x it lands on the USB connectors.

Float in every direction is now 0.20 mm, from 4.60.

### The USB inlet, and a fact that decided its design

The plan was to bring the board's own connector out to the rim. Two things killed
that. The plug would end 30 mm short with nothing to grip — and, checking rather
than assuming: **Espressif's own v1.1 user guide calls both ports Micro-USB**,
while the boards widely sold as "ESP32-S3-DevKitC-1" carry two Type-C. Which
connector the board has is not a settled fact, so nothing here depends on it.

The inlet is its own USB-C socket at 6 o'clock wired to the 5V/GND pins, which is
how `README` §2 already said to power the thing:

```
plug channel  13.00 x 7.20 mm through the wall   (USB-IF caps a Type-C overmold
                                                  at 12.35 x 6.50)
socket mouth  6.99 mm inside the rim -> ~13 mm of a 20 mm overmold stands proud
breakout bay  20.40 x 14.20 x 5.00 on a shelf, rails and lips either side
```

The channel is deliberately **narrower than the breakout PCB** — 13.00 against
14.20 — so the PCB butts a 0.60 mm shoulder each side and pulling the plug cannot
drag the breakout out through the wall. That is the whole retention scheme, and
it needs no screw.

Part: **Adafruit ADA4090**, 20.4 × 14.2 × 5.0 mm, two 5.1 kΩ resistors on CC1,
**A$5.40 inc GST at Core Electronics** (backorder, dispatch 2–7 Sep). Added to
the BOM as item 11. **Not ordered.** The CC resistors are the reason to buy this
rather than a bare socket: without them a USB-C source never turns 5 V on.

### What the checkers caught this time

- The keeper's pilots at r = 44.02 left **0.11 mm** of wall between the hole and
  the tab window's outer edge. Moved to r = 46.76, outside the ring pocket too.
- The USB-C lips were 0.80 mm thick, under the 1.20 minimum. Now 1.50.
- The keeper failed the first-layer footprint test at 206 mm² against a 400 mm²
  floor written for a 108 mm disc. The threshold was wrong, not the part: it now
  passes on 400 mm² **or** 40% of the part's own footprint. A 1 g part is well
  seated on 206 mm².
- `check2`'s "Sam's geometry is untouched" test failed until every new cut and
  addition was given its own named envelope. That is the test working: it is not
  a blanket allowance, and it should fail whenever something new appears.

`check5_v5a.py` is new and `runchecks.sh` runs five passes now. All five green.

---

## 2026-08-25 — Radar v2: it downloads without crashing

v1's fetch held the main loop for **2031 ms** and crash-looped the device.
v2 attacks the size of the work instead of hoping, and the number moved:

```
v1  [online_image]: Downloading image (Size: 66942)
    [component:421]: api took a long time for an operation (2031 ms), max is 50 ms
    *** CRASH DETECTED ON PREVIOUS BOOT ***

v2  [online_image:132]: Downloading image (Size: 14334)
    [component:421]: online_image.image took a long time for an operation (452 ms), max is 50 ms
    (no crash; device up continuously since)
```

**452 ms against 2031 ms, and the device stayed up.** Still over ESPHome's
50 ms budget, so it still logs a warning — but a warning is not a fault, and
two minutes of continuous port polling showed zero drops.

### What actually changed

| | v1 | v2 |
|---|---|---|
| Tile | 512 px | **256 px** |
| Download | 55896 B | **17718 B** (measured; 14334 on the wire for this frame) |
| Device-side resize | 512 -> 360 | **none**, drawn at native 256 |
| Decoded | ~1024 KB | **~256 KB** |
| Transport | HTTPS to RainViewer | **plain HTTP to HA on the LAN** |
| Fetch gated on the switch | no | **yes** |

The last row is the one that matters most for safety. In v1 the download was
triggered by the URL arriving, so the radar switch only gated *drawing* —
turning it off did not stop the crash loop. Now nothing is fetched that is not
going to be drawn, and off is genuinely off.

HA does the internet-facing half: it holds the HTTPS session and writes the
tile to `/config/www/wall_clock_radar.png`, served at `/local/` with no auth
token — the same mechanism that already serves `flightdeck.html` on this box.
The device is told to re-read by an `input_text` stamp that HA bumps *after*
the file is on disk, so it can never chase a fetch that failed upstream.

### Confirmed end to end

- `/local/wall_clock_radar.png` -> HTTP 200, **14334 bytes**
- device log -> `Downloading image (Size: 14334)` — exact match
- `sensor.wall_clock_radar_age` 9 min, inside the 45-minute staleness gate
- automation fired on switch-on; stamp bumped
- no `mini_round_clock` entity unavailable

### Two loose ends

**`on_download_finished` did not log.** Neither it nor `on_error` printed,
which means `radar_ready` may still be false — and that flag gates the draw.
The download plainly succeeded, so this is about the trigger, not the fetch.
Needs eyes on the screen to settle whether the radar is actually visible
before guessing at a fix.

**A harmless 404 race on switch-on.** The switch's `on_turn_on` fetches
immediately, but HA's automation has not written the file yet, so the first
attempt 404s and the stamp bump a second later succeeds. Self-healing, but the
`on_turn_on` fetch could simply be dropped — the stamp alone is enough.

### Also fixed this session

The twelve HSV colour controls were invisible in practice: `entity_category:
config` hides them from dashboards, and the device page sorts them
alphabetically, scattering each hue/saturation/intensity trio between "Mode"
and "Ring LED count". Added a grouped **Colour** card to the Settings view,
inserted into `/config/.storage/lovelace.wall_clock_build` with `jq` (backup at
`.bak-preColour`) — the Device Builder's own editors have been unreliable all
session, whereas fetching from the repo with `curl` in the Terminal & SSH
add-on and editing with `jq` has been exact every time.

---

## 2026-08-25 — Eleven more options; radar shelved

### The radar was a design failure, not a bug

It drew. Sam's verdict: *"it's just a static square image."* Both halves of that
are correct and neither is fixable by tuning:

- **Square.** A 256 px web-mercator tile is a rectangle. Pasting one on a round
  360 px face gives you a square of weather sitting on a circular clock — it
  reads as something stuck on rather than part of the face. Masking it to a
  circle would help, but the real fix is a radar rendered FOR a circle.
- **Static.** One frame every ten minutes is, correctly, almost motionless.
  `flightdeck.html` looks alive because it cross-fades seven cached frames every
  600 ms — the motion is animation, not new data.

Shelved rather than deleted: it downloads in 452 ms without crashing, and the
analysis (opaque frame hash, tile maths, alpha measurements, the v1 crash) is
worth keeping. The package now lives at
`homeassistant/packages-disabled-wall_clock_radar.yaml` so it cannot be
deployed by accident.

**Anything that revisits this should mask to a circle and hold several frames
to animate.** ~256 KB per frame at 256 px means seven fit in PSRAM easily.

### Eleven new runtime options

All are `entity_category: config`, all restore across reboots, and none needs a
reflash to change once this firmware is on.

| | |
|---|---|
| Second hand style | tick / **sweep** — sweep interpolates with the render counter, which is already running at 20 fps for the alert pulse, so it costs one line |
| Hour markers | twelve / **quarters** / none — on a 24-LED ring twelve markers use half the pixels and drown the hands |
| Hour marker brightness | 0-100% |
| Timer arc direction | clockwise / anticlockwise — `P()` already normalises negatives, so this is a sign flip |
| Alert pattern | pulse / **chase** (a four-pixel comet) / solid |
| Alert hue | 0-360° |
| Status pixel brightness | 0-100%, one scale over every ambient pixel |
| Show date | screen |
| Show day of week | screen |
| Weather tint strength | 0-100%, blends the weather colour back toward the plain ground |
| Blank screen at night | screen only — the ring keeps the time |

**The alert colour is deliberately outside the theme.** An alert is a single
state with nothing to be distinguished from, so the only axis worth exposing is
which hue catches *your* eye — saturation and value are pinned full. `mono`
still drops it to grey, because mono's promise is that nothing on the face
depends on telling one hue from another.

**Subtitle lines now stack down a y cursor** rather than sitting at fixed
offsets. Turning one off closes the gap instead of leaving a hole, nothing can
land on top of anything else, and the cursor stops at CY+150 because past that
a centred line on a round screen is already running out of width.

### Compiled, not installed — the device is off the network

```
INFO Successfully compiled program.
     RAM 35.2% (120147 / 341760)   Flash 58.5% (1072955 / 1835008)
WARNING Connecting to 192.168.1.80 port 3232 failed: [Errno 113] No route to host
ERROR Upload failed after 3 attempts
```

Confirmed independently: `.80` answers only with an ICMP unreachable from
`192.168.1.32`, and a sweep of the whole `/24` finds **nothing** on 6053 or
3232. The ESP32 is unpowered or not joining wifi — the same signature, and the
same ping trap, recorded on 2026-08-24.

Nothing is broken. The device still holds radar v2; the new build is compiled
and waiting on the box. One Install once it is back on the network.

The radar square will disappear on its own without any flash: the HA package is
gone, so `sensor.wall_clock_radar_age` is unavailable, the draw's `isnan` guard
fails, and it stops being drawn.

### Dashboard

Three more cards on the Settings view — **Ring detail**, **Alert**, **Screen** —
grouped by what they affect. HA sorts config entities alphabetically on the
device page, which is what scattered each hue/saturation/intensity trio between
"Mode" and "Ring LED count" and made them impossible to find. Inserted with
`jq` (backup `.bak-preOptions`); the entities read unavailable until the device
is flashed.

---

## 2026-08-25 — v6: the S3 moves into the housing, a 32-LED body, and a desk stand

Five things in three messages, and between them they undo most of v5a:

> *"I dont want to use a breakout board for power, move the board more towards
> the edge so that the power can be connected easily. Also, at the current
> moment, the new housing is not deep enough to account for the cables coming
> out of the screen and ESP32. Update the case so that it is at least 50mm deep
> and the ESP32 sits in the other mini rear round clock housing."*
> … *"update the tolerance on the difuser, it's still too loose. I want it to be
> press fit"* … *"build a stand for the clock to go in so that it can sit on a
> desk too. But the stand is another print that the clock sits in."* … *"make
> another version for an LED ring of the same brand that has 32 LED's. The
> outside width is 111.85mm and the inside is 96mm"*

### The board is in the housing, and its own connector is the inlet

Out of the base's deck bay, onto four posts off the housing's pocket floor, as
far out at 6 o'clock as its own corners allow: at |y| = 13.15 the pocket wall is
at x = −49.27, so the board's end sits at −48.50 with 0.77 mm of margin. Its own
connector then looks out through a 22 × 6 mm window in the rim, and the ADA4090
breakout is withdrawn from the BOM.

The window is that generous deliberately. **Which connector the board carries is
still not a settled fact** — Espressif's v1.1 guide says Micro-USB, the boards
sold as DevKitC-1 have two Type-C — so the window clears either in either
position and nothing depends on knowing.

Depth: housing 50.00, pocket 46.50 clear, clock 74.40 overall. The budget that
matters is the last line of it:

```
board on 4 mm posts   8.80 mm
battery on shelves   12.00 .. 36.89
left for cables      11.31 mm
```

That 11.31 is what Sam was actually asking for. The old 15.0 and 27.5 mm pockets
had the board and the cables competing for the same space.

Retention: **the two ends are held differently, on purpose.** The last 2.50 mm
of the board's +x end is bare PCB — 22-pin rows are 53.34 mm on a 62.74 mm board
— so a hook there sits 0.20 mm over it. At the −x end the wall is the window and
the long edges are the pad rows, so that pair sits above everything the board
carries instead: 3.4 mm of lift there, which does not matter with gravity in the
board's plane, and it cannot foul a connector whatever the layout.

The base got simpler as a result: the deck is an annulus again, the beam and the
screwed-on keeper are gone, and Sam's geometry inside r = 46 is now touched by
nothing but the four screw pilots.

### The press fit, done the way moulders do it

v3 gave the diffuser a 0.10 mm interference on diameter and Sam still reports it
loose. That is the right diagnosis to take seriously rather than just tightening
further: **0.10 mm is inside a printer's own tolerance**, so on a given day the
part comes out with clearance. Tightening the wall only moves the coin toss.

So: 0.10 mm of *clearance* on the wall, and eight crush ribs 1.60 mm wide and
0.35 mm proud — 0.60 mm of interference on diameter, at eight narrow places that
can actually yield. A single conical cut takes a lead-in off the ribs and the
wall together, so nothing has to deform until it is already aligned. One knob,
`DIFF_RIB_H`, if it is still wrong.

Mesh note worth keeping: a rib whose inner face sits **exactly** on the wall's
outer surface separates from it in float32 — the diffuser came out as 9 bodies.
Burying it 1.00 mm into the wall fixed it. Same lesson as the cell walls butting
the ribs' 144-gon: bury, do not butt.

### The 32-LED ring does not fit the clock

111.85 mm across against a 107.99 mm body. It needs a pocket to r = 56.42
against an outer wall at 53.99. So the body grows to **119.85 mm**, and the way
it grows is the same trick that fixed the diffuser: keep Sam's mesh where it is
good and rebuild the rest.

```
keep      everything inside r = 46 -- bore, display pocket and seat, tab window
rebuild   ring pocket 47.50..56.42, outer wall to 59.93, face recess to 57.93
fill      his old ring pocket up to z = 17.00, which becomes the shelf the new
          diffuser's face lands on -- with the tab's slot cut back out of it, or
          the tab could not be got in
screws    moved to r 44.00 at 60/120/240/300; at r 49 they bored straight into
          the new ring pocket
```

**A consequence worth flagging before he prints one:** with the LEDs at r = 52
and the 2.1″ display ending at r = 30, there is a 22 mm wide blank annulus
between the screen and the lit ring. Much more ring, much less screen. That is a
look, not a fault, but it is one to see before cutting plywood.

### The stand, and the number that sets its height

A cylindrical cradle cut to the body's radius + 0.35, wrapping ±55° about bottom
dead centre, leaning back 8°, with a stop wall behind the clock's rear face and
a 45° gabled arch through it front to back that halves the filament and doubles
as the cable route.

The height is the only number that is not a style choice, and it is set by
something easy to miss: **the USB socket is at 6 o'clock, which is exactly where
a cradle wants to hold the clock.** A plug's overmold stands ~19 mm proud,
pointing at the desk, 64 mm back from the front face where the 8° tilt has
already dropped the rim 8.8 mm. So the clock sits 36 mm off the desk and the
checker measures the plug tip at 7.9 mm of clearance. A right-angle lead only
needs about 8 mm of that — `STAND_LIFT = 24` and it is 12 mm shorter.

Two design facts fell out of building it, both worth keeping:

- **A rigid disc cannot be located axially by a coaxial surface.** A taper that
  narrows going back cannot be entered at all; a stop ring at a fixed station
  fouls the rim. It has to be a wall beyond the rear face, which is why the
  stand is per-depth rather than universal.
- **Cutting the cable slot through the whole length split the stand into two
  legs** — they are joined only by the shell under the cradle. The slot now
  opens over the last 28 mm and the stop wall, which is where the plug is
  anyway.

### What the checkers caught this time

- The USB window was cut with the *global* R_BODY, so on the 32 body it stopped
  inside the pocket and never reached the outer wall. `check2` found it by
  pushing a plug envelope in from outside.
- The 32 housing's vents at 85/100° left a **1.00 mm** wall between them.
- Cutting the deck at exactly Sam's own wire-slot half-width left two coincident
  planes and a 2 mm³ disagreement between two ways of measuring the same solid.
  Cutting the deck's ribbon slot wider than the tab-slot walls' feet did the
  same. Both are the float32 lesson again, in a new place.
- The deck at r = 44 left Sam's underside with a 16 mm annular bridge to print
  into thin air, and a sliver where the tab cut met the deck's inner circle.
- `check3` was wrong about one thing and it is now fixed: a face within 15° of
  horizontal is a **bridge**, not a slope. An 8° stand tilt made every flat
  ceiling in the part read as an unsupported overhang.

`check5_v5a.py` is retired and `check5_stand.py` replaces it. Five passes, nine
parts, two bodies, all green.

---

## 2026-08-25 — Options flashed; "analog ring" face written; the device keeps dropping off wifi

### Flashed and verified live

The eleven-option build went on and every control reported back:

```
second hand style tick | hour markers twelve | marker brightness 100
arc direction clockwise | alert pattern pulse | alert hue 20
status brightness 100 | show date off | show day of week off
weather tint 100 | blank at night off
totals: numbers 22, selects 7, switches 10 — none unavailable
```

Zero dropouts across a two-minute poll immediately after.

**Note for next time: a flash resets stored preferences.** ESPHome keys them by
a hash of the config, so changing the config invalidates them. The colour theme
came back as `default` rather than the `custom` it had been set to. Nothing is
lost — the HSV numbers are the default preset's own values — but the theme
select has to be put back to `custom`.

### "analog ring" — a fourth screen face

Sam: *"the outside of the screen shows the analog clock that follows the LEDs
on the outside."* So the dial is pushed out to r=170, and the screen and the
physical ring are meant to read as **one instrument**, not two clocks that agree.

**Quantisation is the whole trick.** A smoothly drawn hand and a ring that can
only light whole LEDs disagree by up to half a pixel-step, and the eye catches
it instantly — the screen looks right and the ring looks broken. So every outer
mark snaps to the ring's own grid, `round(f * N) / N`, and each screen dot sits
radially inward of a real LED.

**No `twelve_oclock_offset` is applied on screen, deliberately.** The offset
renumbers *which LED* is twelve; it does not move where twelve physically sits.
Twelve is the top of the object on both surfaces, so both use frac 0 -> -90°
and they line up by construction. Applying the offset twice would break them
apart — an easy and very confusing mistake to make later.

Hands stop short of the dial so they point *at* it, which is what lets the LED
beyond read as the continuation of the hand. Hands are drawn as several
parallel offset lines because ESPHome lines are one pixel and one pixel
vanishes at 360 px. The timer arc is echoed on the same track and honours the
arc-direction option.

Written, YAML-validated, deployed to `/config/esphome/` (1720 lines) —
**not flashed.** The device went off the network before the install.

### The device is intermittently dropping off wifi

This is the real blocker now, and it is not the firmware.

- It vanished for ~15 min, came back on its own, took the option flash fine,
  ran clean for several minutes, then vanished again for 8+ min.
- When gone it is **completely** gone: no ARP entry, no ICMP, nothing on 6053
  or 3232 anywhere in a full `/24` sweep — and **no `mini-round-clock` fallback
  AP** in a wifi scan either, so it is not falling back to its captive portal.
- When present, ping RTT is **69–563 ms, averaging 164 ms, on a LAN**. That is
  terrible for a local wifi device and is the strongest clue: a marginal link,
  not a crash. A crashing device reboots and comes back in seconds; this one
  disappears for many minutes at a time.

Suspects, in order: weak signal where it currently sits, then marginal power
(USB from a PC while the LED ring is also drawing), then the AP steering it
between the 2.4 and 5 GHz SSIDs.

**Unrelated but worth chasing:** something at `192.168.1.32` opens and drops
the device's API roughly every 15 seconds — `[api.connection] Socket operation
failed CONNECTION_CLOSED errno=128` fills the log. `.32` is also the host that
answers ICMP-unreachable for `.80`. Whatever it is, it is noise at best.

---

## 2026-08-25 — v7: a 240 mm clock for the 60-LED ring, with perspex light guides

> *"I have some perspex that can be used to make the LED's look longer than they
> are or for the 60LED ring, make the clock larger by using the perspex in
> strips to make the light shine down it. I would like to make the clock of the
> 60LED ring 24cm wide, and use the perspex, or other material to make the LED's
> shine further away from the LED"*

A third body, and the first one where the interesting part is optical rather
than mechanical: each LED feeds a radial strip and **reads 30 mm long instead of
about 5**.

```
ring          172 / 156, 60 LEDs, LED circle r = 82.00   (three resellers, no
                                                          datasheet -- measure it)
body          240 mm.  ring pocket 77.50..86.50, floor z = 10.45
channel       r 79.00..113.60, 6.70 wide, 3.35 deep, one per LED
strip         r 86.50..112.00 -- 6.00 x 3.00 x 25.50 on a shelf at z = 13.65
aperture      r 80.00..110.50, one layer, WIDENING 1.40 -> 3.00
```

Three of those are decisions rather than arbitrary numbers:

- **The channel starts inboard of the LED circle** (79 against LEDs at 82) and
  the aperture starts at 80, so the LED itself is the head of the lit line
  rather than a separate dot beside it.
- **The strip starts outboard of the ring** (86.5), so it lands on the base's
  shelf and never rests on an LED.
- **The aperture widens going out.** Light falls off along a strip; opening the
  slot pays some of it back, so the line reads even instead of hot at the inner
  end. That is the tuning knob if the first one looks wrong.

### The two facts that decided the material story

Both were already in this project's own notes and both are worth restating,
because the obvious plan — laser the strips — does not work.

- **Perspex is PMMA and contains no chlorine.** Sam's standing rule is *"never
  PVC or acrylic containing chlorine."* PMMA satisfies it. **PVC** is the one
  the rule is about, and unlabelled "acrylic-look" marketplace sheet is often
  exactly that. Labelled cast PMMA from a known supplier, or nothing.
- **The Aura cannot cut it.** `enclosure/MATERIALS.md`: a ~5 W *diode* laser at
  445 nm goes straight through clear, white and translucent acrylic. Glowforge's
  own Aura material list is opaque acrylic only. So the strips come off a table
  saw, a bandsaw or a scroll saw, or out of 6 mm acrylic rod, or a CO2 laser
  somewhere else.

And one that is physics rather than a project note: **a polished strip is a
pipe, not a lamp.** Light goes in one end and out the other and the middle stays
dark. Wet-sanding the downward face with 400 grit is what turns it into a lit
line. That instruction matters more than any dimension in the part.

### Three ways to fill the channels, and the channels work empty

Because I cannot promise how far the light carries without building one:

1. **60 cut perspex strips** -- the thing he asked for, and the crispest.
2. **`mini-round-clock-light-guides-60`** -- all 60 as one printed part joined by
   a 1.40 mm ring, in clear or natural PETG. A worse pipe and a better lamp: the
   layer lines scatter, so it glows along its length instead of dumping the
   light out of the end.
3. **Nothing.** The channels are white troughs with an opaque face over them and
   a slot in it, lit from one end. Not as crisp, but not a broken clock.

That fallback is deliberate. A design that only works if a 60-piece hand-cutting
job goes well is a design that does not work.

### Hollowing a 240 mm part, and what it costs

A solid 240 mm annulus is 855 cm³ -- over a kilogram. Hollowed to a floor plate,
two shelves, the pocket walls, twelve radial ribs and one circumferential rib
per cavity, it is 514.

Two things went wrong on the way and both are general:

- **Sealed cavities are a second body.** The hollow closed on itself and the
  topology check counted 25 shells. They need a vent: two Ø6 holes per rib gap
  per cavity, and *two* rather than one, because the circumferential rib splits
  each cavity in half and each half needs its own way out.
- **Hollowing without a circumferential rib gives a 28 mm ceiling.** The radial
  ribs do nothing for the radial span. One circumferential rib per cavity takes
  the worst bridge from 28 mm to 14.

### The check that was wrong, again

`check3`'s "total ceiling area is modest" was a flat 2000 mm² written for a
108 mm disc. A deliberately hollowed 240 mm part is ~47% ceiling by plan area
**and every bit of it spans 14 mm or less**. The span test is the one that
carries the meaning; the area test is now proportional and only fires if a part
is essentially a lid over a void.

### And the desk stand for it is silly, so it says so

1047 cm³. It exists because it is the same parametric part and it passes every
check, but a 24 cm clock is a wall clock. The docs say to print it only if you
actually want one on a desk. The big body did surface one real bug in the stand,
though: at 240 mm the clock's centre of mass is 155 mm up, and the cradle's own
footprint tips at 11°. It now grows a low plinth behind the stop wall, sized
from the geometry to bring that back over 20°.

Five passes, fourteen parts, three bodies, all green.

---

## 2026-08-25 — Edge-to-edge analog face, and the dashboard goes multi-clock

### The dial had to reach the rim, and dots cannot

First cut drew the outer marks as dots at r=170. Sam: *"make sure the analog
clock goes right to the edge."* A dot fundamentally cannot: **its own radius
has to fit inside the panel**, so a 4 px dot centred at 175 already overhangs
179 and gets clipped. Pushing the centre outward makes it worse, not better.

Marks are now **radial lines** — a line lying along the radius ends exactly
where you tell it to. Every tick runs out to r=179, one pixel inside the panel.
That matters more than it sounds: the whole point is that the drawn dial and
the LED ring beyond the bezel read as **one instrument**, and a visible dead
band between them is the one flaw nothing else compensates for.

Also flashed, and confirmed live:
`face options = ['digital', 'minimal', 'analog', 'analog ring']`.

### Multi-clock: why the dashboard has to be generated

*"Select which clock is being customised… there will be more than one."*

The obstacle is that **every control is an ESPHome entity, and ESPHome derives
entity ids from the device `name:`**. Two clocks therefore have two disjoint
sets of entities — `mini_round_clock_hour_hue` and `kitchen_clock_hour_hue` are
unrelated — and no Home Assistant card abstracts over that natively. There is
no "device" variable a card can be pointed at.

So the view carries **one set of cards per clock and shows only the selected
one**, using card-level `visibility` against `input_select.wall_clock_target`.
That is core HA; no HACS card is involved.

Written by hand that is N copies of ~60 rows to keep in sync, and it will drift
the first time a control is added — which has now happened three times in two
days. So `dashboards/build_clock_dashboard.py` generates it. Adding a clock is:

1. a different `name:` in ESPHome (sets entity prefix, hostname, OTA target)
2. one line in `CLOCKS`, re-run the script
3. one option in the input_select

**The label is only a label** — rename it freely. The entity prefix is the real
identity, and changing that means renaming the device and reflashing.

**Timers stay outside the switching.** The `wall_clock_1..5` pool belongs to
Home Assistant and is shared by every clock, so it is a global card. Getting
that wrong would have produced five timer cards for five clocks, all showing
the same five timers.

Verified after install: `input_select.wall_clock_target = Mini Round Clock`,
options `['Mini Round Clock']`, per-clock cards rendering, Timers global.

### Flashing through a flaky link

The device kept dropping off wifi mid-session, and an OTA that fails wastes the
whole compile. The working pattern:

1. Kick off the install even while the device is down. The **compile still
   succeeds** and the binary is cached; only the upload fails.
2. Poll `3232` from outside until it opens.
3. Hit **Retry** — the build is cached, so it goes straight to upload and lands
   in seconds rather than minutes.

That turned a several-minute window requirement into a few-second one, and is
how both of today's flashes actually got on.

---

## 2026-08-25 — Stands lean back 10 deg; a digital readout on the analogue faces

### The stand tilt is bounded at both ends, and it fought back

Sam: *"update the angle of the stands so they have a slight tilt back."* It
already leaned 8 deg — enough to read as "not quite straight" rather than as a
deliberate lean. Went for 12. Both existing checks pushed back, which is
exactly what they are for:

**Plug clearance.** The clock's USB plug points at the desk 64 mm behind the
front face, so every extra degree of tilt drops it `64*sin` — about 1.1 mm per
degree. 8 -> 12 costs 4.4 mm of the 7.9 mm the plug had.

**Stability.** Raising `STAND_LIFT` to buy that clearance back raises the
centre of mass, and leaning further back moves it toward the heels. **The two
fixes fight each other.** At 12 deg with LIFT 38.5, `check5` measured the
backward tip margin at **19 deg against a 20 deg floor** and failed the 240 mm
body.

Settled at **10 deg on the original 36 mm lift** — but that still measured
exactly **20.0 deg** on the 60-LED stand, a hair under. Rather than give the
lean back, the fix went where the design already had a lever: the **tail
plinth** behind the stop wall, which exists precisely to buy tip margin on the
big bodies. Its sizing uses a *design* angle (the crude `depth/2` CoM estimate
lands several degrees optimistic), tuned to 27 when the clock leaned 8. Raised
to 30.

Result — every stand now has **more** margin than it did at 8 deg:

| body | was (8 deg) | now (10 deg) |
|---|---|---|
| 24-LED | — | 25 deg back, 30 fwd |
| 32-LED | — | 24 back, 29 fwd |
| 60-LED | 21 back, 21 fwd | **23 back, 22 fwd** |

Plug clears the desk by 5.7 mm on all three, against a 3.0 floor. All five
verification passes clean.

### An ana-digi complication

*"add a digital clock to the analog face too."* New switch **Digital time on
analog face**, off by default — an analogue face is chosen for the shape of the
time, so a number in the middle of it is an addition, not something to inflict
on everyone.

It applies to **both** analogue faces. Time low, date high, on opposite sides
of the hub so no combination of the three switches can collide, and both sit
inside the sweep of the hands rather than fighting the dial at the rim. Drawn
**last**, after the hands — legibility is the entire reason for adding it, so a
hand passing over must not hide it.

While there: `Show date` and `Show day of week` now work on the analogue faces
too. They existed and silently did nothing there, which reads as a bug.

### Toolchain note for the next session

The geometry checks need more than trimesh: `numpy trimesh manifold3d networkx
scipy matplotlib shapely lxml rtree`. Missing `rtree` made `check3_print` look
like a geometry failure when it was an import error, and missing `networkx`
made trimesh's `split()` fail with "no graph engines available". Install the
lot before believing any check result.

---

## 2026-08-25 — v8: the wire gap, all twelve numerals, and why the diffuser was really loose

Two asks. Both landed, and chasing the second one turned up a third thing that
had been wrong since v6.

### The gap between the middle and the ring

> *"update the main clock bases so that there is a gap between the middle and
> the LEd ring so that the cables connecting the LED ring dont need to bend
> straight down. The 24LED looks like this ... UPdate all the sizes for this."*

He attached a base to show me. I measured it before assuming anything, and the
attachment turned out to be **my own v5a base returned unmodified** — 109,229.9
mm³, byte-for-byte the geometry I had sent. So it was not an edit to merge; it
was a pointer at a feature already in his 108 mm base that I had not carried
across to the bigger ones.

The feature: at 6 o'clock his base is open **top to bottom** from r = 28 out to
r = 41. A lead leaves the ring at ring level, runs inward, and only then drops.
What the 32 and 60 bodies had instead was a shallow channel *under* the
ring-pocket floor — which means the lead must be pressed flat against the floor
and ducked under. That is exactly the bend he is describing.

Both bigger bodies now get the same gap: ±13.00 mm at 6 o'clock, from the bore
out past the ring's inner edge, open to the shelf the diffuser's face lands on,
with the deck cut to match. `check2` §8 probes it as the solid an 8 mm bundle
would occupy, on all three bodies.

**And it caught a live collision.** The pocket fill on the 32 and 60 bases was
hardcoded to z = 17.00 while the 60's shelf is at 15.65 — a real 1.35 mm
interference with the 60 diffuser's face, plus a shelf sitting right across the
new gap at r = 40. Both now derive from the body's own shelf height.

### All twelve hours, in a second colour

> *"add the numbers from 1 to 12 on the diffuser that I can print in black on
> the 3D printer. Make them the same font as the Amazon Echo wall clock."*
> *"I will 3d print the diffuser with the numbers printed in a different colour
> on the same printer."*

The plain marks are gone; there are twelve numerals, and a second STL per body
of solids 0.50 mm thick that fill those pockets exactly. One function emits both,
so they cannot drift apart. Add the diffuser in Bambu Studio, right-click → Add
part → the `-numerals` file, assign filament 2.

**The font is not Ember, and the log should say so plainly.** Amazon Ember is
Amazon's proprietary brand typeface. I checked rather than assumed — matplotlib's
font manager raises `ValueError` for it. Liberation Sans Bold is the closest
neutral sans available and that is what is cut. `NUM_FONT_FILE` is a one-line
swap for anyone with a licensed .ttf.

### Three things that were quietly wrong, found by checking rather than by luck

**1. `num_r` was assigned three times.** I added the v8 rule at the top of
`Body.__init__` and left two legacy assignments below it, so the legacy value
won. Result: the numerals sat *on top of the LED apertures* — the 32's reached
r = 52.86 against a tick inner edge of 49.96. One rule now, set once, at the end
of `__init__`, after `tick_ri` is known: outer edge 1.20 mm inboard of the
apertures, on every body.

**2. They would have printed mirrored.** The diffuser is modelled with its
visible face at z = 0 and everything else behind it, so it goes into the base
**turned over** — text laid out the ordinary way is read from the far side and
comes out back to front. That was not a guess: the aperture membrane is at
z = 0..0.20 with the cavity above it, which only prints if z = 0 is the face and
the part goes on the plate face-down; and a placement scan against the base
finds the diffuser seats flipped, at C = 21.6, with the only interference being
3.9 mm³ at r = 46.30..46.66 — the crush ribs, which is the press fit.

Which way is up was not assumed either. **+x is 12 o'clock**, and two features
say so independently: the keyhole's entry hole is at r = 38.5 and its narrow end
at r = 46.0 on the +x axis, so the clock is lifted and dropped onto the screw,
which only works if +x is up; and the ring's lead slot and the USB window are
both at −x. The old numeral code used `a = 90 - 30h`, which is 90° out.

`text_prism` gained a `mirror` flag that swaps the glyph's x and y. Two
reflections cancel, digit order included, so "12" reads 12 and not 21. `check4`
tests it without anyone squinting at a render: it probes the **"10"**, whose left
digit is a 1 and whose right digit is a 0, and only the 0 is hollow in the
middle. Mirrored the wrong way, those swap.

**3. The diffuser was loose because of DEPTH, not diameter.**

Sam said "it's still too loose" twice. v6 answered both times by arguing about
interference on diameter. Measured on the built files:

```
ring pocket's outer wall stops at         z = 19.00
diffuser comes to rest with its face at   z = 21.52
band was                                  4.00 mm tall
=> actually inside the bore               1.40 mm
```

The other 2.60 mm was hanging in the 3 mm front recess, where the wall is
**5.3 mm away radially**. No amount of diameter fixes a 1.4 mm-deep press fit on
a 108 mm part; it rocks. There is 4.00 mm of clear space above the LED ring
inside that pocket, so the band goes to 6.00 mm: it lands at 15.52, keeps
0.52 mm off the ring, and the checker now measures **2.9 mm of rib contact**. It
also drops the cell walls down beside the LEDs, where they were sitting 3 mm
above the ring doing very little masking.

And the lead-in taper was on the **wrong end** — at z = 0, the visible face,
which is the trailing edge. The diffuser was meeting the bore square with
full-height ribs and no run-up at all. It is now at the top of the band, with a
0.25 mm bevel left on the visible rim for a squashed first layer.

### The check that was wrong, again

`check3`'s thin-wall test failed the numeral inlays, and the honest answer was
not to lower the threshold. A glyph is not a wall: every letterform has corners
that taper to nothing, and they cluster there however fat the stems are. The
inlays now get their own two tests — median stroke width against a nozzle bead,
and what fraction of the surface falls under one — and the plate-adhesion test
is skipped for them, because they never touch the plate on their own.

That test then earned its keep immediately: at 3.60 mm cap height Liberation
Sans Bold has a **0.66 mm stem**, 1.6 beads from a 0.4 mm nozzle — one perimeter
and a gap-fill, and a visible seam down every stroke in a second colour. The
24-LED numerals went to 5.00 mm, where the stem is 0.92 mm. The band inboard of
the ticks runs 30.95..37.55, so that still leaves 2.55 mm clear of the collar.

Five passes, seventeen parts, three bodies, all green.

---

## 2026-08-25 — v9: a 25 mm housing, and a mount that actually holds the board

> *"The housing can be 25mm deep, not 50mm anymore. Also, make sure that the
> mount for the ESP32 actually hold it and followed 3D printer constraints.
> (Research this if you need to)"*

### Half the depth, and what it costs

50.00 → 25.00. The clock goes from 74.40 mm deep to **49.40**, and there is
14.10 mm of clear plenum above the board's frame for the display ribbon and the
ring leads — which is the thing the 50 mm was originally for, and it is still
comfortably there.

What it does cost is the battery, and that is worth saying plainly rather than
letting him find out with a cell in his hand. The Anker A1653 is 24.89 mm on its
thinnest axis; with the board's frame under it a cell needs a **43.29 mm**
housing. So the two battery shelves are **not generated at all** now — shipping
a part that cannot be used is worse than not shipping it — and the build prints
a line saying why. `HOUSING_DEEP = 50.00` brings the lot back; the pocket, the
shelves and the checks all key off that one number.

The screws change with it: the pillars were M3 × 60 and are now **M3 × 35**.
A 60 in a 25 mm housing bottoms out and splits the boss.

### The mount was a tray, and he was right about it

Measured on the built file before touching anything:

```
down        four posts under it at |y| = 5.50
up, +x      a hook 0.20 mm over the bare end            0.20 mm of float
up, -x      two arms above everything on the board      3.40 mm of float
sideways    nothing at all                              +/-7 mm
along       a post 3.50 mm from the end                 0.50 mm
```

A board that can lift 3.4 mm at one end and slide 7 mm sideways is not mounted.

### What the drawing said, which is what the design had to follow

Espressif's v1.1 dimension drawing, read as a drawing rather than remembered:

- **62.74 × 25.40**, pad rows **1.27 mm** in from each long edge at 2.54 pitch,
  the two USB shells owning the **last 8.00 mm**. All dimensioned.
- 22 pins at 2.54 is a 53.34 mm row, so the end margins sum to 9.40. With the
  connector end at 8.00 the antenna end is **1.40** — and 1.40 + 53.34 + 8.00 =
  62.74 exactly. That arithmetic closing is the check that the reading is right.
- Scaled off the same drawing: pad OD ~1.70, shells 7.95 wide reaching to
  |y| = 10.54 and overhanging the board's end by 0.87.
- **And there are no mounting holes.** Two 22-pin rows and nothing else.

So copper reaches to within **0.42 mm of each long edge**, and the antenna end
has **0.55 mm** of clear board with the WROOM module standing on it. That kills
every obvious answer: no screws, no lip on the long edges (it lands on pads or
solder or a header body), no lip at the antenna end. What is left is the
**connector end** — 7.15 mm of clear board in the two strips at |y| 10.54–12.70,
outboard of the shells and before the pads. That is where the board is held, and
it is the only place it can be.

### The frame

Rails that touch only the board's 1.60 mm edge (0.20 mm of total slop, and
completely indifferent to headers). An end wall at the antenna end, which is
what takes the USB plug's insertion load — the only real force in here. Corner
stops at the connector end so pulling a plug cannot drag the board into its own
window. Three pairs of posts, including one pair under the middles of the two
USB shells, where a plug pushes down. And two snap fingers clamping the
connector end.

The antenna end gets no clamp and does not need one: a 1.6 mm FR4 board is rigid
over 62.74 mm, so an end held top, bottom and sideways cannot let the far end
lift.

### The bit that needed research, and the two constraints that agreed

A cantilever snap is a strain problem: `e = 1.5·Y·t/L²`. The obvious shape here
— a short finger standing up beside the board — is hopeless: at L = 6 mm the
1.00 mm deflection needed is **6.3 % strain**, and PLA yields around 1.5–2 %. It
would snap off on the first board.

At L = 18, t = 1.50 it is **0.69 %**, on a 12:1 beam against the 8:1 floor
usually quoted for PLA, at about 2.7 N a finger.

The print constraint pointed the same way. The published FDM guidance is
consistent: a snap arm built up the Z axis bends across the layer bonds, which
costs roughly half the elongation at break, and that is where printed snaps
shear off. The arm has to lie in the XY plane.

Both wanted the same thing, and the housing's own print orientation gave it for
free: it goes on the plate rear-plate-down, so the pocket opens upward and every
feature in the frame is a vertical wall. Each finger is a wall too, with a slot
behind it — long axis in X, flexing in Y, both in the layer plane. The only
overhangs in the part are the two 0.90 mm lips, and each lip's top is a 63°
lead-in ramp, so pressing the board down wedges the fingers open and there is
nothing to bridge.

`check2` §5 now measures the finger's thickness on the built STL and does the
strain arithmetic from that, rather than reading it back out of params.

### Three things the depth change broke, all caught by the checks

- **The corner stops poked 0.07 mm through the outside of the clock.** At
  |y| = 14.80 the outer wall is only at x = −51.92 and the stop ran to −51.99.
  Starting it inboard still buries it 0.8–1.7 mm into the wall, which is what
  fuses it on.
- **The desk stands grew knife edges.** The stand is built upright, tilted and
  then trimmed by the desk plane, and a plane through a tilted solid feathers to
  nothing wherever a face meets it shallowly — 0.01 mm at the front corners and
  along the heel. Fixed properly with a real flat foot: everything below 0.60 mm
  is replaced by a straight extrusion of the section at 0.60 mm, so every edge
  on the footprint is vertical. Doing that as cut-and-re-union left two shells;
  doing it as one subtraction with the section shrunk 0.10 mm first (so the
  cutting wall is inside the solid rather than tangent to it) is clean.
- **The 240 mm stand's forward tip margin fell to 18°** against a 20° floor. A
  shallower clock sits further forward in its own cradle, so its centre of mass
  moves toward the front edge. It now grows a front toe, sized closed-form:
  `foot_front = -(h·tan t + toe/cos t)` falls straight out of the tilt, so
  unlike the tail plinth the design angle and the measured angle agree to a
  tenth of a degree. 12 mm of toe on the 240; the 108 and 120 mm stands compute
  a negative toe — they were never close — and get none.

Plug clearance on the stand went the other way and doubled, from 5.7 mm to
**10.0 mm**: the USB window is 39 mm back from the front face now instead of 64,
so the 10° lean drops it less.

Five passes, sixteen parts, three bodies, all green.
