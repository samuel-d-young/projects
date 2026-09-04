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

---

## 2026-08-25 — Echo timer counting flashed; a duplicate card resource found

### The timer now counts minutes, then reverses

Deployed and flashed. Config hash `445c50ad → aae74ede`, compile 6m38s, upload
13s, exit 0 both. All eleven selects came up in Home Assistant, including the
new `select.mini_round_clock_timer_countdown_style` (`minutes`), and the stored
preferences survived this flash — theme still `cool`, face still `analog ring`.

Behaviour, verified against the ring lambda:

```
  90s ->  2 LEDs   minutes phase     "larger than 1 minute shows 2 LED's"
 121s ->  3 LEDs   minutes phase
  60s -> 24 LEDs   final minute      blooms to full ring
  30s -> 12 LEDs   final minute
   1s ->  1 LED    final minute
```

### The direction flip needed a setting change, not a code change

The final minute deliberately runs the OPPOSITE way to the minutes phase — that
reversal is the signal that you are inside the last minute. But `arc_dir` was
set to `anticlockwise`, which made the minutes run anticlockwise and therefore
the final minute run *clockwise* — the opposite of what was asked for.

Set `arc_dir` to `clockwise`. Minutes now accumulate clockwise and the final
minute unwinds anticlockwise. Worth writing down because the two controls
compose rather than stack: `arc_dir` names the direction of the MINUTES phase,
and the last minute is always its mirror. Nothing in the firmware pins the final
minute to one absolute direction.

### The Settings dashboard is blocked by the frontend, not by the cards

New cards installed into `/config/.storage/lovelace.wall_clock_build` (backup
`.bak-preEcho`), all four new controls present in the file. But the view renders
half empty: `switch` and `light` rows appear, while every `number`, `select`,
`markdown` and `timer` row is blank.

**The entities are fine.** The ESPHome device page renders all of them —
sliders, dropdowns, the lot — and reports firmware built 2026-08-25 14:32. That
page lives under `/config/` and is the one page that does NOT load Lovelace
custom resources, which is the whole clue.

Measured directly in the page, rather than inferred:

```
customElements.get('hui-toggle-entity-row')  -> true     renders
customElements.get('hui-number-entity-row')  -> false    blank
customElements.get('hui-select-entity-row')  -> false    blank
customElements.get('hui-markdown-card')      -> false    blank
```

The split is exactly main-bundle versus lazy-loaded. Forcing the import by hand
works instantly:

```js
const h = await window.loadCardHelpers();
await h.createRowElement({entity: 'number.mini_round_clock_brightness'});
// -> HUI-NUMBER-ENTITY-ROW, and the element is defined from then on
```

So the modules exist and are reachable; the dashboard simply never completes the
lazy import during render. It is also not deterministic — the Timers card had
its five `timer.*` rows on one load and lost them on the next.

**A false lead, recorded so it is not chased twice.** The console did show a
real error:

```
DOMException: Failed to execute 'define' on 'CustomElementRegistry':
the name "flightradar24-card" has already been used
```

Two resources defined that element: the HACS card, and the Flightradar24
integration's own bundled copy at `/flightradar24/`. Removed the HACS one — the
exception is gone and the console is now clean — **and the rows are still
blank**. So the collision was real but was never the cause. No dashboard
references `custom:flightradar24-card` at all, so nothing was lost either way.

**The remaining suspect is the resource list itself.** Fifteen HACS frontend
bundles load on every dashboard render, several of them code-split
(`advanced-camera-card` pulls `card-294f2ffb.js`). A custom card whose bundler
`publicPath` collides with Home Assistant's own chunk loading is a known way to
break exactly this. Narrowing it means disabling resources a few at a time,
which is disruptive and is Sam's call.

**Meanwhile there is a working path to every control:** Settings > Devices >
Mini Round Clock. Not as tidy as the grouped cards, but complete.

---

## 2026-08-25 — v10: the press fit moves inside, and v8's band was my mistake

> *"The diffuser is now too tight and dones't fit properly. Also I want the
> press fit to be on the inside where the screen is not the outside."*

Two asks, one root cause between them, and the first one was mine.

### What v8 got wrong

v8 set out to fix "it's still too loose" and decided the problem was engagement
depth rather than diameter. To find the engagement it measured where the
diffuser comes to rest — by bisecting its position against the **bare base**.
No LED ring in the pocket. No display module in the bore. With nothing else in
there the outer crush ribs were the only thing that could stop it, so the
measurement returned a seat of z = 21.52, an engagement of 1.40 mm, and the
conclusion that the band had to grow. It went 4.00 → 6.00 mm.

The seat is not set by the ribs. Measured against the base's actual geometry:
the inner wall between the screen bore and the ring pocket tops out at
**z = 19.03** — a 4.9 mm wide annular land at r 30.19..35.11 — and the
diffuser's face lands on it. So the face occupies 19.03..21.03 and everything on
the diffuser sits at `z = 21.03 - z_diff`:

```
band 4.00 (Sam's)  -> underside at 17.03, LED ring top 15.00, clear by +2.03
band 6.00 (v8's)   -> underside at 15.03, LED ring top 15.00, clear by +0.03
```

0.03 mm. At 6.00 the band reaches the LED ring before the face reaches its stop,
so the diffuser jams proud and rocks on the ring rather than seating. That is
precisely what Sam reported, and dropping a 1618 mm3 boolean of diffuser into
the ring's own solid says it without any argument.

**The lesson worth keeping:** a fit measurement taken against one part of an
assembly is not a fit measurement. The bisection was careful, repeatable and
wrong, because the thing it was searching for -- "where does it stop" -- was
being answered by the only obstacle present rather than by the real one.
`check2` §9 now places the diffuser at the seat the base defines and measures
the ring clearance as a boolean against the ring, on every body.

### The fit moves to the collar

Which he asked for independently, and which is the better place anyway.

The outer wall now grips nothing: 0.40 mm of clearance on diameter into the ring
pocket, and the eight outer crush ribs are gone. The press fit is six ribs on
the collar, the part that reaches down around the screen:

```
bore          30.19  MEASURED across the flats. R_DISP_POCKET (30.2788) is the
              circumradius of the 144-gon; a round collar touches flats.
collar OD     30.108 -> 0.16 mm clearance on diameter, so it starts square
6 ribs        1.60 mm wide, crest 30.34 -> 0.30 mm interference on diameter
engagement    4.50 mm of bore, z 3.00..7.50, entirely above the display module
lead-in       1.00 mm taper at the HIGH z end -- the collar goes in tip first
```

The argument for it, beyond preference: the outer wall is 92 mm around on the
108 mm body and **233 mm** on the 240 mm one, so a single interference figure is
three different fits — and on the big one it is smaller than the printer's own
error across that span. The collar is 60 mm around on all three. One fit, three
clocks. Each rib crushes 0.15 mm where the old outer ribs were asked for 0.35.

### Two things that fell out of moving the seat

The 60-LED body derives its entire vertical stack from where the diffuser's face
lands — the guide shelf is `seat - BAND_TOP60`, and the ring floor is that minus
the LED height, so the LED tops end up level with the shelf and fire into the
end of their perspex strip. That was built on a seat of 19.00. With the real
seat at 21.03 the whole stack moves up 2.03 mm: shelf 13.65 -> 15.68, ring floor
10.45 -> 12.48. Left alone, every strip would have rattled in a 2 mm gap.

And with the shelf level with the LED tops by construction, the 60's band came
down on the LEDs themselves. It now has a 0.40 mm relief across the ring's own
radius, so it rests on the shelf outboard of the ring and clears the LEDs.

### A check that was reading the wrong height

`check2` §2 -- "the LED ring drops into its pocket" -- probed at the global
`Z_RING_FLOOR` rather than the body's own. On the 60, whose floor was 10.45, it
had been testing a ring floating 1.35 mm above the real pocket and passing.
Moving the floor to 12.48 finally pushed the probe into the floor and made it
fail. It was wrong the whole time; it just had slack to hide in.

Five passes, sixteen parts, three bodies, all green.

---

## 2026-08-25 — v11: the collar had no clearance, the collar was short, and the face was thin

> *"its still too tight and the inside ring that goes onto the screen can be
> longer."*
> *"update the diffusers so that only the part that is meant to be seen through
> the LED is thin, otherwise there is bleed and you can see through where you're
> not meant to."*

### Third "too tight", so stop guessing at the number

v10 moved the press fit to the collar and put six crush ribs on it. What it did
NOT do is give the collar underneath any clearance. Sam's collar is **30.108**
OD; the bore measures **30.19** across the flats. That is **0.164 mm on
diameter**.

On an FDM printer that is not clearance. An external cylinder comes out
0.10-0.20 over on diameter; a bore comes out 0.10-0.30 under. So the pair can
easily print as an *interference across the whole 190 mm of circumference* --
and six ribs on top of that were never a crush fit, they were a solid
interference fit with lumps on it. Turning `COLLAR_RIB_H` down would not have
helped, because the interference was underneath the ribs, not in them.

The collar is turned to **29.90**: 0.58 mm of clearance on diameter, and the
ribs are now the only thing that touches. Interference down 0.30 -> 0.20, ribs
narrowed 1.60 -> 1.20 (a narrow rib crushes more easily than a wide one), lead-in
1.00 -> 2.00. And the knob means something now: with real clearance underneath
it, turning `COLLAR_RIB_H` down cannot leave a hidden interference behind it.

**The general lesson, which is the same shape as v8's:** a crush-rib fit is only
a crush-rib fit if the surface the ribs stand on is genuinely clear. Ribs on a
line-to-line surface are just a rougher press fit.

### The collar was not touching the screen at all

The module sits on its seat at 8.60 with a 1.60 mm PCB, so the face the collar
is meant to hold down is at **10.20**. The collar's tip reached **10.83**. It
was 0.63 mm short and the screen was free to lift -- exactly what Sam felt.

`COLLAR_EXTEND` is derived now rather than typed:

```
COLLAR_EXTEND = DIFF_SEAT_Z - (Z_SEAT + DISP_TAB_T) - DIFF_COLLAR_H
              = 21.93 - 10.20 - 8.20 = 3.53
```

And it is a CEILING, not a preference: the diffuser's face rests on the base's
land, so a collar reaching past the module holds it off that land and the clock
sits proud. `check2` asserts the tip never goes past the module's face.

### The bleed was not a hole in the model

First thing was to check rather than assume. Probed across the built face with a
ray cast, it was a flat 2.00 mm everywhere except the aperture at 0.20 -- so the
model was already doing what Sam asked for. The bleed was 2.00 mm of white PLA
passing light.

Three answers, one of which is not geometry at all:

* **The face is 2.90 mm**, up from 2.00. That is the most that fits: it sits in
  the front recess between the wall crest it rests on at 19.03 and the front of
  the clock at 22.00, which is 2.97 and no more. At 2.90 it finishes 0.07 inside
  the front -- effectively flush, which it never was before.
* **His inner face is filled out to match.** Raising FACE_T only thickens the
  band this project rebuilds, from r=34.50 out; inside that it is his mesh and
  it stayed 2.00. There was a step and a thin ring around the screen window.
* **The aperture flares behind the membrane** -- 2.00 x 4.00 at the front,
  opening 0.80 a side by the time it reaches the cell. Without that, a 2.90 mm
  face turns every dot into the bottom of a deep narrow slot you can only see
  head-on.
* **And the face has to be sliced SOLID.** At 0% infill -- which is what MAKE.md
  had been saying -- a 2.90 mm face is a shell with air in it, and air does not
  block light. That is very likely a large part of what he was seeing, and it is
  a settings change, not a reprint of anything.

Said plainly in the docs: if it still bleeds after all that, the answer is
material rather than geometry. White PLA passes light at any thickness a clock
face can carry, and the real fix is an opaque body with translucent lens inserts
at the dots -- the same two-filament workflow as the numerals, but it needs the
aperture to become a through-hole and a third part. Offered, not assumed.

### Two frozen constants and two tangencies

* **DIFF_SEAT_Z was frozen at 21.03** with a comment saying "= crest + FACE_T".
  It stopped tracking the moment FACE_T moved, and the first attempt at a 3.00 mm
  face drove 774 mm3 of diffuser into the base. Derived now, along with BAND_TOP
  and COLLAR_EXTEND -- and `check2` asserts the face fits the recess and its
  underside is on the land.
* **The rib lead-in cone started exactly at the crest radius**, so its surface
  was tangent to each rib along one line: 6 bad edges at r=30.29, z=6.00, and
  NotManifold after the float32 round trip. Started 0.40 outside the crest it
  crosses cleanly partway up.
* **The face fill's top plane landed on the rebuilt band's top plane.** Overlap
  into a coplanar face, which is the one thing float32 does not survive. Ends
  0.05 short, on the hidden side.
* **The collar extension was inset 0.10 inside the turned-down collar**, leaving
  a 0.10 mm ledge ringing it. The extension is added before the turn-down now,
  so one cut sizes both and they finish flush.

Five passes, sixteen parts, three bodies, all green.

---

## 2026-08-25 — v12: stop guessing the collar fit, ship a gauge

> *"The inside it now too long, make it the same length it was before but adjust
> the outside dimensions to not be as tight as before."*

### The length: reverted, and expressed so it cannot drift again

v11 derived the collar's length from where the display module's face was
*assumed* to be -- its seat at 8.60 plus a bare 1.60 mm PCB -- and reached the
tip to exactly there. It over-reached, which is itself a measurement: the rim at
the r=29 circle is thicker than a bare PCB.

That is worse than it sounds. The diffuser's face rests on the base's land, so a
collar that touches the module FIRST holds the whole diffuser off that land and
the clock sits proud -- another of the ways this has felt "tight". **Too long is
worse than too short.**

Back to what it was, and now expressed as the thing you can put calipers on:

```
COLLAR_LEN    = 8.20    the ring standing proud of the BACK of the face
                        (8.20 before v11, 8.83 in v11)
COLLAR_EXTEND = COLLAR_LEN + FACE_T - DIFF_COLLAR_H = 2.90
```

Written that way it stops moving when FACE_T moves -- which is exactly how it
drifted, since v11 thickened the face by 0.90 in the same change.

### The fit: the number was never the problem

Three rounds of "too tight" in a row:

```
v10   collar 30.108 in a 30.19 bore (0.164 clearance) + 0.30 interference
v11   collar 29.90                  (0.58  clearance) + 0.20 interference
v12   collar 29.60                  (1.18  clearance) + 0.10 interference
```

The thing v10 and v11 shared is that the *wall behind the ribs* did not have
enough clearance to be irrelevant. If a printer runs the boss over and the bore
under by a few tenths -- which Sam's evidently does -- the wall starts touching,
and then the rib height is no longer the fit and turning it down does nothing.
That is why it kept coming back.

v12 separates them properly: the wall has **twelve times** as much clearance as
the ribs have interference, and the ribs stand 0.64 mm proud so they can crush
most of that before anything else makes contact. `check2` asserts the RATIO now,
not just the interference -- the invariant that was missing while this was being
tuned three times.

The fit can afford to be light, too: the clock hangs with the diffuser's axis
horizontal, so gravity never pulls it out. It only has to resist being knocked.

### And the thing that should have shipped three rounds ago

`mini-round-clock-collar-gauges` -- three 8 mm sections of the real collar at
three rib heights, side by side, each with its figure in hundredths of a
millimetre debossed on top. Five minutes, 9 g.

```
marked  0   crest 30.194   +0.01 mm on diameter -- line to line
marked  5   crest 30.244   +0.11 mm            -- what ships
marked 10   crest 30.295   +0.21 mm            -- what v11 shipped
```

Push each into the base's screen bore; whichever wants a firm push is the
number. If even 0 is tight, the printer is running over and the answer is
negative.

The general lesson: after the second time a dimension comes back wrong, the
useful deliverable stops being a better dimension and becomes a way to measure.
Three iterations of a whole diffuser were spent finding out what 9 g of test
print would have said in one.

Five passes, seventeen parts, three bodies, all green.

---

## 2026-08-25 — v13: the S3 mount did not fit, and why

> *"The mount for th S3 doesn't fit at all. Update it so it actually fits. Find
> the correct dimensions for it."*

Two things to establish: what Sam's board actually measures, and whether the
clearances were ever printable. The second one is quick, so it went first.

```
board                62.74 x 25.40
slot between rails   25.60   -> 0.20 mm of clearance TOTAL across
slot end to end      63.04   -> 0.30 mm TOTAL along

an FDM slot prints 0.10-0.40 mm UNDERSIZE:
  a 25.60 slot comes out 25.20 .. 25.50
  the board is 25.40
  -> it can be up to 0.20 mm WIDER than the hole it has to enter
```

That is the answer, and it is not a dimension problem. **It is the collar
mistake, in a different place**: a nominal clearance smaller than what the
printer takes out is not a clearance, it is an interference fit wearing the
word. The collar took three rounds to find because the argument kept being
about the rib height. Here the argument would have been about the board size.

### Finding the correct dimensions anyway, since he asked

The web is useless on this. Searching for the board Sam owns returns, from
different vendors, all published as fact:

| source | claimed |
|---|---|
| espboards.dev | 70 × 28 mm |
| an AliExpress spec article | 67 × 31 × 8.5 |
| another one | 55 × 35 × 1.6 |
| Mischianti / VCC-GND | behind a PDF that 403s |

So: **downloaded Espressif's own dimension DXF and parsed it.**
`DXF_ESP32-S3-DevKitC-1_V1.1_20220429.dxf`, 744 kB, 2640 entities.

| layer | what it gave |
|---|---|
| `BOARD_OUTLINE` | **25.400 × 62.865**, 0.5 mm corner radii |
| `PADLAYER_TOP` | 226 pads; two columns of 22 at x 1.27 and 24.13, pitch 2.54, y 7.96 → 61.30 |
| `DRILLHOLE` | shell tabs at 7.15 mm spacing, four pairs, y 1.55–5.77 |
| `PLACEMENT_OUTLINE_TOP` | two connector bodies **9.32 and 9.40 wide × 7.62 deep**, at x 1.894–11.215 and 14.109–23.506 |
| `LAYNR3` (designators) | `UART` at x 4.06, `USB` at x 17.64, `J4` at 18.77 |

Four corrections and one discovery:

1. The board is **62.865 long, not 62.74**. The old figure came from assuming
   the connector end owned exactly 8.00 mm; the DXF says the first pad centre
   is at 7.960 and 7.96 + 53.34 + 1.565 = 62.865 exactly.
2. The USB shells reach **|y| 10.81, not 10.54**.
3. The pad rows are **22.86 mm apart — 0.900 in, exactly.** That is why every
   DevKitC-1-shaped board is 25.4 wide, and it is the reason the *width* can be
   trusted while the length cannot.
4. **7.15 mm shell tabs is the standard 16-pin USB-C receptacle footprint.**
   That settles an open question that has been in `MANIFEST.md` since v5: the
   v1.1 board carries **two USB-C**, whatever the user-guide text says.
5. And the one that the fix hangs on, which the earlier reading missed
   completely: **between the pad rows, the board's top is bare for the last
   7.53 mm** — a 7.53 × 21.16 mm patch behind the WROOM module, clear whether or
   not headers are soldered on and pointing either way.

### The repair

**Clearances sized off the worst printed case, not the drawing.**

```
                    was        now       worst printed      board
rail slot          25.60      26.20      25.80 .. 26.20     25.40   (25.70 max)
end to end         63.04      64.67      64.27 .. 64.67     62.87   (64.00 max)
```

`check2` §5 now asserts that directly — `FDM_SLOT_UNDER` is in `params.py` and
the test is *the worst printed slot still clears the widest board this frame
claims to take*, with 0.10 mm to spare. That is the assertion that would have
caught v9 before it shipped.

**The snap lips moved to an absolute |y|.** They were placed as a reach over the
board's edge, which is the wrong datum: what limits them is the **USB-C shell**,
not the edge. At |y| = 11.50 a lip clears a shell on a board sitting 0.40 mm off
centre by 0.29 mm and still catches 0.80 mm of board edge with the board sitting
0.40 the other way. Both asserted.

**The antenna end got a hood, and v9's argument for not having one was wrong.**
v9 reasoned that a board held at one end cannot lift at the other. But the lips
have 0.20 mm of slack over a 4.00 mm base, and 62.865/4.00 is a **15.7:1
lever** — 0.20 mm at the lips is **3.1 mm of lift** at the far end.

The hood is a wedge off the end wall with a 47° underside and a 1.40 mm land.
That shape does three jobs with one feature: the lowest thing on it is a single
land, so the board still **drops straight in**; a 47° underside is
**self-supporting**, so no bridge and no overhang; and the land stands 4.00 mm
in from the wall, so **any** board from 61.3 to 64.0 passes under it. It lands
on that bare 7.53 × 21.16 patch, 0.38 mm clear of the pad rows at worst shift.

**Envelope: 61.3–64.0 long, up to 25.7 wide.** Stated, and asserted.

### A gauge, because this is the second fit to come back wrong

`mini-round-clock-board-gauge` — the frame itself on a 2.5 mm plate. Same rails,
fingers, stops, hood and posts; 13 cm³, about 16 g, twenty minutes. If the board
clicks into it, it clicks into the housing. The plate carries a 5 mm scale off
the connector end with deeper marks at 61.3 / 62.865 / 64.0.

Same lesson as the collar, applied one round earlier this time.

### And check3 learned to tell a chamfer from a thin wall

The first build of the hood failed check3 with two new thin regions, and it was
right about one of them: the wedge came to a **knife edge**, which is a poor
thing to bear on as well as a sub-wall feature. That got the 1.40 mm land.

The second was the snap lip's 45° lead-in ramp, reading 0.21 mm — and there the
checker was measuring the wrong thing. `thin_clusters` shoots its ray along the
surface **normal**, which is right for a wall and wrong for a chamfer: across a
45° lead-in the normal distance runs to zero at the tip, while every individual
layer stays full width, because the tip is just the top layer of something
thicker underneath.

Measured directly, layer by layer, the lip is **1.61 to 3.01 mm wide** in every
0.20 mm layer that prints it.

So `check3` gained `layer_width()`: for any region flagged as thin, it slices
the mesh at each layer the region spans and finds the largest circle that fits
inside the cross-section there. It reports both numbers and fails only if the
in-layer figure is also under the threshold. The lips now read
`[chamfer: 2.40 mm wide in every layer]`. **The threshold did not move**, and
nothing was exempted by name.

### Files

Changed: `params.py`, `build_v2.py`, `check2_fit.py`, `check3_print.py`,
`render_fit.py`. New part: `mini-round-clock-board-gauge`. All five passes green
on all three bodies, eighteen parts.

---

## 2026-08-25 — v13a: the hood was 47° and still unprintable

> *"Remember the constraints of 3d printing when creating 3d files. The board
> gauge has overhangs that can[']t be printed."*

He is right, and it was in the housing too, not just the gauge.

### What I got wrong

The v13 hood was a **wedge** hanging off the end wall with a 47° underside that
**climbed away from the wall**, so its lowest point was a 1.40 mm land standing
out over the board. The reasoning was: a single low edge means the board can
still drop straight down past it, and 47° is steeper than 45°, so it is
self-supporting.

The second half of that is wrong, and it is wrong in a way worth writing down:

> **A sloped face is self-supporting only when the material it grows from is
> BELOW it.** The angle is necessary and not sufficient.

That ramp climbed the wrong way. The hood's first layer was therefore the land
alone — a **31 mm² island 5.80 mm up in mid-air**, three millimetres from the
nearest wall, with nothing under it. It would have printed as a bird's nest.

### Why five checks missed it

Because none of them asked the question. `check3` had:

- a **slope** test — is any downward face flatter than 45°? The hood's was 47°,
  so: no.
- a **bridge** test — how far does a flat ceiling reach before it is supported?
  Measured as twice the greatest distance from a point on the patch to that
  patch's own **boundary** — which quietly assumes the boundary is supported.
  For an island, nothing is. 1.40 mm of land scored 1.40 mm and passed.

Two tests about *how* material is unsupported, and no test asking *whether* it
is. That is the hole.

### The check that closes it

`check3.unsupported()`. An island can only begin at a flat ceiling, so at every
z where the part has one: slice the layer above and the layer below, grow the
lower slice by one layer height — which is exactly what a 45° face is allowed
to overhang — and look at what is left over. Anything left that touches the
grown lower slice **nowhere** is an island, and that is a hard failure.

It is a handful of slices per part rather than the whole part, so it costs about
a second each. Results on the seventeen parts: **no islands anywhere** now, and
the only unsupported patches left are the USB window's ceiling, the vents, the
two snap lips and the hood ledge — all anchored.

I also wrote and then deleted a companion test for how far a one-sided ledge
reaches. It duplicated `bridge_span`, my distance metric was a symmetric
Hausdorff where it needed a directed one, and it re-flagged Sam's own inherited
tab-slot ramps as new defects. The right home for that rule is `check2` §5,
where the reach is a parameter rather than a measurement:
`LEDGE_MAX = 2.50`, against 1.60 for the snap lips and 2.00 for the hood.

### The hood now

A **flat 2.00 mm ledge** off the end wall, underside at `BRD_LIP_Z0` — the same
shape as the two snap lips, which is the whole point: short, off a wall, every
layer above it carried by the one below.

Two things are the price, and both are real:

- **A flat ledge cannot be dropped past.** The board now goes in antenna-end
  first: slide it under the hood, lower the connector end, press until the
  fingers click, push it back onto the corner stops. At 6° of tilt the
  connector end clears the fingers entirely.
- **The reach comes out of the end clearance**, so `BRD_END_CLR` fell from 1.80
  to 1.00 and the length window narrowed from the 61.3–64.0 the wedge promised
  to **62.4–63.3**. That is about ±0.5 mm around Espressif's 62.865.

Which makes the board gauge the load-bearing part of this delivery rather than a
nicety. It is 15 g and it answers the only question the window leaves open.

### The lesson, stated plainly

I replaced a fit I could not verify with a shape I had not verified, and shipped
it because it passed the tests I had. "It's 45°" is a rule of thumb about a
face; printability is a property of a **layer** and its neighbours. Both of the
checks added this week — `layer_width` for chamfers and `unsupported` for
islands — are the same correction: stop reasoning about faces, measure the
layers.

---

## 2026-08-26 — v14: measured board, screwed clamp, and a collar that was inside the screen

Two messages, and between them they retired the last two moulded-in fits in the
design.

> *"The board dimensions are 28.19mm wide and 63.27mm long. Update the housing to
> hold this. Also, add a way to screw it down to fasten it."*

> *"The insides of the diffuser is still too long that touches the screen. It must
> be shorter, but it can be a tight fit for that inside part."*

### The board is not the board in the drawing

**63.27 × 28.19.** Espressif's DevKitC-1 v1.1 outline is 62.865 × 25.400, so
Sam's board is **2.79 mm wider** — a different board, and every vendor figure for
a part sold under that name was already contradicting every other one (70 × 28,
67 × 31, 55 × 35, all published as fact). `BOARD_L` and `BOARD_W` are his
calipers now.

The DXF stays as the source for what calipers cannot reach — where the pad rows
are, how far the USB shells stand out, where the module ends — because the
retention has to dodge those and one real drawing of a board in this family beats
none. **But nothing in the frame depends on any of it now:**

| feature | what it depends on |
|---|---|
| snap lips | the first 5 mm of board, before any copper whatever the pitch |
| clamp pad | \|y\| ≤ 9.80 — inboard of any row a 0.9 in or wider board could have |
| posts | \|y\| = 6.50 |

Change the pad pitch, move the module, widen the connectors: none of it reaches
these features.

Everything else follows: rails at \|y\| 14.495 (slot 28.99, worst printed 28.59
against a 28.19 board), lips at \|y\| 12.495, corner stops at 11.80, fingers
lengthened 20 → 22 so the bigger deflection stays at 0.93% strain.

### "A way to screw it down" solved three problems, not one

The antenna end had already been wrong twice. v9 left it unclamped on the
argument that a board held at one end cannot lift at the other — wrong, the lips
have 0.20 mm of slack over a 4.00 mm base and on a 63 mm board that is a 15:1
lever and 3.1 mm of lift. v13 answered it with a moulded hood: first a 47° wedge
whose ramp climbed away from its wall, so its first layer was an island in
mid-air; then a flat 2.00 mm ledge, which prints, but which cannot be dropped
past and which had to buy its reach out of the end clearance, closing the length
window to ±0.5 mm.

**A screwed bar has none of those problems.** It goes on after the board, so
nothing overhangs and there is no assembly move. It is a separate flat part, so
it prints face-down with no support. And it does not care how long the board is
— which is why the window reopened to **60.0–64.2**.

`mini-round-clock-board-clamp`, 1 g, two M3 × 10 self-tappers:

- presses from **59 mm** along the board at **\|y\| ≤ 9.80**, between the pad rows
- both screws land at **65.25 mm**, beyond the longest board the bay takes
- so **nothing crosses a pad row at any height** — headers either way up, or none
- seat at **5.50**, which is 0.10 *below* the board's top face

That last one is the trick: the bar bottoms on the **board**, not on its own
bosses, so tightening it actually clamps. 0.10 mm of flex in a 3 mm PLA bar is a
few newtons — cannot crack FR4, and takes up any board from 1.50 to 1.70 thick.
Its underside is relieved 1.50 mm everywhere short of the pad so it cannot come
down on the WROOM module however far back that ends.

**And it is verified in the assembly, not just on its own.** It is built and
printed lying on its top face, so nothing had ever measured it against the thing
it bolts to. `check2` now loads the STL, turns it over, drops it on its bosses
and checks the whole stack — seat plane, no overlap with the housing, pad over
the PCB, clear of every pad row, clear of the module, screw holes over their
pilots. The first run of that test read **−1.7 mm³** of pad on the board: trimesh
already fixes winding for a negative-determinant transform, and the extra
`invert()` had turned the bar inside out, which would have made every boolean in
the section meaningless. Caught because a volume came back negative.

### The collar was 1.77 mm inside the screen, and the check said it was fine

This one is the worst of the three, because it had an assertion pointed at it.

```
tip                 10.83
Z_SEAT + DISP_TAB_T 10.20    <- what check2 compared against.  PASSED.
Z_SEAT + DISP_T     12.60    <- the surface the collar actually lands on
```

`DISP_TAB_T` is the module's bare **tab** — the flat ear that sticks out of the
bottom. The collar lands at r 28–30, on the module's **front face**, 2.40 mm
higher up. So the assertion was aimed 2.40 mm below the thing it was protecting,
and a collar driving 1.77 mm into the screen sailed through it for three
versions.

`DISP_T = 4.00` was in `params.py` the whole time.

Worse, §1 of the README had reasoned *from the absence of a complaint* that the
module's rim must be under 2.20 mm — inference from silence, which is the
weakest evidence there is, and it was wrong.

Fixed properly: the length is **derived**, and the check takes the tip off the
**built diffuser** rather than recomputing it from the same parameters the part
was built from.

```
COLLAR_LEN = DIFF_WALL_CREST − (Z_SEAT + DISP_T + COLLAR_TIP_CLR)
           = 19.03 − (8.60 + 4.00 + 0.40)  =  6.03      (was 8.20)
```

Tip at **13.00** against a module face at 12.60: **+0.40 mm clear**, and still
close enough to restrain the module to 0.40 mm of float. Both directions
asserted.

A shorter collar has less of itself in the bore, so the grip moves to the ribs —
which is exactly what Sam allowed for in the same sentence. `COLLAR_RIB_H`
doubled, 0.05 → **0.10**: 0.20 mm of interference on diameter over six ribs, with
the wall behind them still 1.18 mm clear on diameter, six times the interference,
so it is still a crush-rib fit and not a full-surface one. The gauge now prints
**0.05 / 0.10 / 0.15** to bracket the new default instead of 0.00 / 0.05 / 0.10.

### The triple check

> *"Don't stop until you're triple checked everything for all the parts."*

- **five passes, three bodies, nineteen parts** — all green
- **the island detector run independently** over every built STL: 0 floating
  patches in all nineteen
- **the clamp put back in the assembly** and measured there, per above
- **the collar tip taken off the built diffuser**, not off params

Three separate assertions in this project have now failed the same way: aimed at
a surface adjacent to the one that matters. The collar against the tab instead of
the face. The snap lips off the board's edge instead of the USB-C shell. The
bridge test against a patch's own boundary instead of against what holds it up.
That is the pattern to watch for, and it is in the design brief now.

---

## 2026-08-26 — v15: a second screen, and why "auto detect" had to be a wire

> *"Add the following screen to the wall clock. I have a couple. Add an option
> in HASS to select which screen and also auto detect."*
> — a 1.9" ST7789 bar, 320×170, against the 360×360 round panel already fitted.

Three findings decided the whole design, and all three are the kind that would
have quietly wrecked it if assumed instead of checked.

### 1. Neither module can talk back

The obvious auto-detect is to read the controller's ID register and branch on
it. It is not available here.

- The **round** module brings SDO out on its 10-pin header, but it is left
  unconnected and the `spi:` block declares no `miso_pin`.
- The **bar** module has no such pin **at all**. Waveshare's own page for it:
  *"the data pin from the slave device to the host device is hidden as it only
  needs to display."* done.land's independent teardown of the same module lists
  eight pins — GND VCC SCL SDA RES DC CS BLK — with no SDO and no TE.

There is no bus to ask the question over. So the detection is a **strap**: one
wire from GPIO18 to GND in the bar panel's cable. That cable has to be made
specially anyway — eight pins in a different order against the round one's ten
— so the marginal cost is one conductor, and the answer is deterministic rather
than inferred. The HA select can override it either way.

### 2. The init sequence is gone after boot

`mipi_spi` sends the init sequence in `setup()` and then does
`this->init_sequence_.clear()` — verified in `mipi_spi.h` at 2026.8.0. So
"re-initialise the panel the user just picked" **cannot be done at runtime, by
any lambda, at all.** Calling `setup()` a second time would send nothing, and on
the buffered variant would allocate a second framebuffer on top of the first.

That killed the design I would otherwise have reached for by default.

### 3. Which is only safe because each panel gets its own CS *and* its own RESET

Both drivers are compiled in and both initialise at boot. That works only
because each init goes out addressed to its own chip select, so neither panel
ever sees the other's. Sharing the reset line would break it just as thoroughly
in the other direction: the second component's reset pulse would clear the first
panel *after* it had been initialised, and whichever panel was actually fitted
would end up reset and blank.

CLK, MOSI, DC and BL are shared, and can be — DC only means anything while a CS
is low.

### The rest

Both displays are `update_interval: never` and a 1 s dispatcher updates only the
active one. Left self-polling, the panel that is *not* fitted would still push a
full framebuffer down the shared bus every second: 253 KB at 20 MHz is about
100 ms, a tenth of the bus, spent on a panel that is not there — and the panel
that *is* there would stutter for it.

The bar layout is its own, not a scaled round face. The design priority at the
top of the file survives the change of shape: the time is always drawn and
always the largest thing; a running timer takes the right-hand two thirds and
pushes the time up into the corner rather than replacing it. **The analogue
faces are deliberately not offered on the bar** — a circle in a letterbox wastes
two thirds of the panel, and a control that does nothing useful is worse than no
control.

Geometry is forced rather than chosen: 170×320 native with `offset_width: 35`,
because the ST7789 has 240×320 of RAM and a 170-wide panel is centred in it —
(240−170)/2 = 35, which is the same figure ESPHome carries for T-EMBED and
T-DISPLAY-S3. `color_order: bgr` and `invert_colors: true` are inherited from
those same models and are the only two things here taken on family resemblance;
both are one-line flips and both are flagged in MANIFEST.

### One bug worth recording

The first draft appended a second top-level `display:` key. YAML does not treat
a duplicate key as an error — the later one silently **replaces** the earlier —
so the round panel vanished from the document entirely. Caught by parsing the
built file and counting the entries, which now reads 2. The block carries a
comment saying why its indentation is what it is.

### Verification

No compiler here, so: the file parses; both display entries survive with
distinct ids, models, CS and RESET pins; all 26 `id()` references in the new
code resolve against ids declared in the document; the ten GPIO assignments are
unique and clear of the ESP32-S3's flash (26–32), octal PSRAM (33–37) and USB
(19–20) pins. Framebuffers are 253 KB + 106 KB against 8 MB of PSRAM.

**Not verified:** it has not been compiled or flashed. That needs a machine with
the board on the end of a USB lead, which this session is not.

### Still open: it does not physically fit yet

The bar module is **62 × 29 × 5.1 mm**. Dropped flat it needs a **68.45 mm**
circle; the base's screen bore is **60.38**. It is 8.07 mm short, so it cannot
go in the existing pocket on any body.

| body | clear middle inside the ring | takes a 68.45 mm diagonal? |
|---|---:|---|
| 24-LED (108 mm) | 70.22 mm | only with ~0.9 mm of wall left — **not viable** |
| 32-LED (120 mm) | 95.00 mm | comfortably |
| 60-LED (240 mm) | 155.00 mm | easily |

So the bar version wants the 32-LED body or larger, and it needs a rectangular
pocket, a different diffuser centre, and no tab slot — the bar module has no
tab. Put to Sam rather than guessed at, because building it for the wrong body
would be waste, and because the diffuser's collar grips that same round bore.

---

## 2026-08-26 — v16: -bar bases and diffusers for the 32 and 60

Sam picked "both 32 and 60" for the 1.9" bar screen. It turned out to be a far
smaller change than the first arithmetic suggested, and the reason is worth
keeping.

### The 68.45 mm figure was the wrong question

Dropped flat through a circular hole, a 62 × 29 module needs a **68.45 mm**
circle and the bore is **60.38** — 8.07 mm short. That is what got reported as
"does not fit any body".

But the module does not need a circle. It exceeds the bore only in **two ears at
±x**, 4.52 mm deep and 29 mm wide, and those are exactly where the base is
**already open** — the display-tab slot at 12 o'clock and the wire slot at 6.
Measured against the built base, the module's entire swept volume from seat to
front recess clashes with only:

```
   +x ear (12 o'clock, tab slot) :  45.9 mm3 of 1507
   -x ear ( 6 o'clock, wire slot): 140.3 mm3 of 1507
   the 1.10 mm the seat drops    :   7.7 mm3
                                   -------
                                   193.9 mm3
```

So the `-bar` base is not a redesigned middle. It is 194 mm³ of relief.

### One derived number does all the work

```
Z_SEAT_BAR = Z_SEAT + DISP_T − BAR_T = 8.60 + 4.00 − 5.10 = 7.50
```

Seat the bar module so its **front face lands exactly where the round module's
does** and nothing downstream moves: the collar tip still clears by 0.40 mm, the
face still rests on the land at 19.03, the vertical stack is untouched. The
diffuser's central hole is r 27.92 against the bar's 24.18 of active
half-diagonal, so the picture is fully visible through geometry that already
exists.

### Two things the measurement caught that the reasoning had not

**The module had no seat at all.** First build: the pocket was 0.0% solid
underneath. The wire slot goes right through under the bore, so cutting the
relief left the module nothing to rest on — it would have dropped straight into
the housing. Fixed with two rails at |y| 12.90–14.90, outboard of the wire
slot's own 13.00 half width so the slot stays clear for the ring leads.

**Two of the six collar ribs were biting on air.** With the ears open, the ribs
at 30° and 330° had **4% and 5%** of themselves over solid bore wall, which puts
the entire grip on the −x side and shoves the collar sideways. The phase was
then swept rather than guessed:

| ribs | angles | worst margin to an ear edge |
|---|---|---:|
| 4 | 45/135/225/315 | **+15.4°** |
| 4 | 60/150/240/330 | +0.4° |
| 4 | 67.5/157.5/… | −7.1° |
| 4 | 90/180/270/0 | −27.8° |

So the `-bar` diffuser carries **four ribs at 45/135/225/315** — symmetric about
both axes, 15.4° clear of both ears, same interference and lead-in as before, so
**the collar gauge still applies unchanged**. Measured on the built parts: 4 of
4 ribs bite at 90–95%, and 77.8% of the land survives.

### A reporting error of mine, corrected

`mini-round-clock-board-clamp` was **never in check3's PARTS list.** The edit
that was supposed to add it used a plain `.replace()` with no assertion, the
string did not match, and it silently did nothing — while I reported the clamp
as having passed the printability pass. It had not been checked at all.

It is in the list now, along with the four new `-bar` parts, and all five pass.
Every edit in this session that mattered used an asserted replace; that one did
not, and this is what that costs. The independent island sweep did cover it, so
the claim about floating geometry was sound — but the thin-wall, overhang,
bridge and first-layer tests had never run on it.

### Verification

Five passes, three bodies, **23 parts**, 0 failures — now including the clamp
and all four `-bar` parts. Independent island sweep over every built STL: 0
floating patches. `check2` gained a section 8 that asserts the bar fit
permanently rather than leaving it as something I measured once: face height
identical to the round module's, no interference in the pocket or on the way in,
both seat rails solid, the wire slot still clear, all four ribs biting, and the
land above 60%.

The 24-LED body still gets no bar variant: the module's corners reach r 34.22
against a ring pocket starting at 35.11, which would leave 0.89 mm of wall.

---

## 2026-08-27 — v18. The ring and the screen come apart, and the panel's colours were backwards

Six things in one session, four of them Sam's, two found on the way.

### 1. The screen's colours were inverted, and it was not the code (verified)

Sam: *"The colours seem to be opposite on the screen"* and *"The hour hand on the
screen is blue but it's orange on the LED ring. And the opposite to the minutes."*

There is no swap anywhere in the firmware. The ring reads `pal_ring[0..2]` for the
hour and `[3..5]` for the minute; the screen reads `pal_scr[0..2]` and `[3..5]`.
Both come out of the same resolver, from the same HSV table, in the same order.
I checked every index before changing anything.

What is wrong is the **byte order the panel is fed.** Red and blue were arriving in
each other's channel:

| element | authored | as it reached the panel |
|---|---|---|
| hour | (235,144,105) orange | (105,144,235) **blue** |
| minute | (106,153,224) blue | (224,153,106) **orange** |
| second | (158,158,158) grey | (158,158,158) unchanged |

That is Sam's report exactly, down to why the grey second hand and the white hand
boss looked fine.

**`invert_colors` is ruled out** — a photo negative swaps orange and blue too, but it
would also turn the near-black ground (10,12,18) into near-white, and the screen is
not white. An R/B swap leaves greys and the background exactly where they are.

The fix is one line: **`color_order: rgb` on `face_lcd`.** Three sources agree, and
I had it backwards for ten minutes before Sam's own repo settled it:

1. xboot's `fb-gc9b72.c` — the driver this init table came from — sets MADCTL to
   `0x00`. Bit 3 clear is RGB. **The vendor drives this panel in RGB.** (verified)
2. ESPHome's `mipi_spi` **appends its own MADCTL** after a custom `init_sequence`,
   built from `color_order`/`rotation`/`mirror` — the same way it appends COLMOD.
   The `[0x36, 0x00]` in our table never reaches the panel. (verified)
3. `samuel-d-young/esphome-gc9b72-360x360`, this panel's own repo, records the
   resolved config for a `model: CUSTOM` block with no `color_order:` line as
   **`color_order: BGR`** — so the default was overriding the vendor's RGB — and its
   troubleshooting table says it outright: *"Red shows as blue → … Default is BGR;
   try RGB."* (verified)

**Do not "fix" this by editing the `0x36` in the table.** It is overridden, so the
edit appears to do nothing — the identical trap this file already documents for
`0x3A`. The vendor table stays byte-for-byte as verified.

Added a **`clock_face: "colour test"`** face: three swatches, each labelled with the
colour it is meant to be, green in the middle because green is the channel a swap
never touches. If the middle block is green and the outer two disagree with their
labels, it is colour order; if the middle one is wrong too, it is `invert_colors`.
One look settles it instead of remembering which way round it was.

### 2. The ring and the screen are separate surfaces now

Sam: *"Update the wall clock so you can control the screen and LED seperately. I
would like to turn off the LED's on the outside and only show the hours and minutes
on the LED ring, but keep the markers on the screen."*

`display_on` — the switch called "Display" — actually gated the **ring** and nothing
else. So "turn the display off" turned the LEDs off and left the panel lit, and there
was no way to have one without the other. It is now the master over two new switches:

```
ring lit    iff  display_on AND ring_on          switch.…_ring_leds
screen lit  iff  display_on AND screen_on        switch.…_screen_on
```

Every control that drove both surfaces from one entity is split, with the existing id
kept on the screen's side:

| was | screen keeps | ring gets |
|---|---|---|
| `marker_style` "Hour markers" | `marker_style` → **Screen hour markers** | **Ring hour markers**, ships as `none` |
| `show_seconds` "Second hand" | `show_seconds` → **Screen second hand** | **Ring second hand** |

`show_status` and `show_pips` were always ring-only and keep their names, so nothing
that referenced them breaks.

**Entity ids change** for the two split controls. The dashboard generator is updated
and regenerated; a cross-check now asserts that every row in the generated JSON
resolves to an entity that actually exists in the firmware — 64 rows, 0 dangling.

### 3. What is on the ring, and the blue light

Sam: *"why is there a blue light on the LED, what else is showing on the LED ring.
The hours, minutes, seconds and what else?"*

Everything the ring can light:

| what | where | colour | switch |
|---|---|---|---|
| Hour hand | the hour | orange | always on |
| Minute hand | the minute | blue | always on |
| Second hand | the second | grey | Ring second hand |
| Hour markers | all twelve | dim blue-white (14,14,18) | Ring hour markers |
| Timer arc | from 12 | teal | while a timer runs |
| Timer pips | where each other timer finishes | dim teal | Extra timer pips |
| Bin night | 12 o'clock | breathing green, yellow for recycling | **Status bin night** |
| Garage open | 3 o'clock | amber | Status garage open |
| Driveway | 9 o'clock | blinking red | Status driveway |
| Who is home | either side of 6 | Sam **(0,40,90) blue**, Laura magenta, Amanda green, Zac amber | Status who is home |
| HA dropped | 6 o'clock | dim red | automatic |

**The single blue dot just left of 6 o'clock is Sam's own presence pixel.** The hour
markers are faintly blue too, but they are dim and there are twelve of them.

The four ambient hints now have **one switch each** instead of sharing one, and
**bin night ships OFF** — the one Sam asked to turn off, off in the message that
asked. The same table is on the dashboard, next to the switches, rather than only in
this log.

### 4. Timers count down in seconds

Sam: *"Make sure that when a timer is set, that the LED's count down the seconds."*

New `timer_style: "seconds"`, and it is the default. Above a minute it is the Echo's
minute count, unchanged. **Inside the final minute it lights one LED per whole second
remaining**, one going out every second, draining the opposite way.

Being straight about what a 24-LED ring can do: one LED per second needs 60 LEDs to
cover a minute. So the ring sits **full** for the first part of the final minute —
36 s on the 24, 28 s on the 32, none on the 60 — and starts counting real seconds
when the count fits. `min(N, ceil(left))` rather than a second scale for that
stretch, so the arc stays monotonic and can never look like the timer got longer.
Simulated over 0–600 s on all three ring sizes: the only increase is the deliberate
flood at the 60 s boundary, which `minutes` style already had and which reverses
direction, so it cannot be misread. If movement across the whole final minute
matters more, `minutes` style is one click away at 2.5 s per LED on the 24.

### 5. The alarm sounds until it is cancelled

Sam: *"just like Alexa, I want the alarm to go off until it is cancelled. When it is
cancelled the wall clock stops showing the alarm too. Otherwise have the alarm stop
after 15 seconds on the wall clock."*

It used to announce **once**, wait 60 seconds, and clear the flag. Two lifetimes now,
deliberately different:

* **The alarm** re-announces every 20 s until dismissed —
  `input_number.wall_clock_alert_repeat_seconds`, and
  `…_alert_repeat_max` = 0 means *never gives up*, which is the default and what was
  asked for. `wait_template`, not `delay`, so a dismiss breaks the loop immediately.
* **The clock** shows it for `alert_shows_for` (15 s) — but a cancel clears the ring
  and both panels within one 50 ms frame, because the flag is read every frame and no
  timer is involved in that direction. Set it to 0 to make the lights last exactly as
  long as the sound.

**A finished timer is idle, not running.** `timer.cancel` on it fires no
`timer.cancelled` event, which is why the existing clear-on-cancel automation never
saw it and saying *"stop the timer"* at a beeping clock was answered with *"there's
no timer running"* while it kept beeping. Three dismiss paths now:
`input_button.wall_clock_timer_dismiss`, turning the boolean off by hand, and
`HassCancelTimer` / `HassCancelAllTimers`, which now clear the flag unconditionally.

### 6. The diffuser: a longer line, and a shorter, tighter collar

Sam: *"update the wall clocks diffusers so that there is more of a line for the LED's
to shine through. Also, the inside of the diffuers it too long. Shorten it and make
the inside fit tighter."*

**The line.** `TICK_W` 2.00 → 1.40, and the length is derived per body instead of
being a frozen literal — from the light-tight cell that wraps that body's LED, and
now also from the face's own radial budget. On the 24 that budget is what binds, not
the cell, and the first version of this drove the numerals 0.32 mm over the edge of
the screen window before the constraint was added:

| | tick | ratio | limited by |
|---|---|---|---|
| 24 | 5.04 × 1.40 | 3.6:1 (was 2.0:1) | **the screen window** |
| 32 | 4.42 × 1.40 | 3.2:1 | the cell |
| 60 | 30.50 × 1.40 | 21.8:1 | the light guides |

The 24's face has 12.83 mm between the LED circle and the window, and the stack
inboard of the tick — gap, hour marks, margin, numeral — already wants 9.80 of them.
Three levers exist if a longer line matters more than what is inboard of it
(`NUM_H_24` 5.00→4.40, `MARK_LEN` 2.60→2.20, or dropping the 24's redundant hour
marks entirely, worth 3.20 mm), and none of them was pulled unasked — they are all
features already delivered.

**check4's `'it sits inside the LED'` assertion was replaced, not deleted.** It
required the tick to fit *entirely within* the 5 mm emitter, which is the opposite of
what Sam asked for. It is now a bounded overhang: at most `TICK_SPILL_MAX` = 1.00 mm
past the die at each end, because past that the ends are lit by spill alone and read
as a gradient rather than a line. The design intent changed on instruction; the
check changed to match, and it is said out loud rather than quietly tuned.

**The collar, fourth report.** v17 took the tip from 1.77 mm *inside* the module to
0.40 mm clear of it. 0.40 is clear on paper and inside what two printed parts move
by, so it is not clear in the hand. Now **0.90 mm** — still under the 1.00 ceiling on
how far the module may float, so it goes on restraining it. That costs 0.50 mm of
engagement (collar 4.43 → **3.93 mm**), which is paid back in the ribs:

| | was | now | why |
|---|---|---|---|
| ribs | 6 | **8** | grip ∝ count × interference, and count is the free term |
| interference | 0.15 (0.30 ⌀) | **0.19 (0.38 ⌀)** | 0.1975 is the hard ceiling from the 4× wall-clearance invariant |
| lead-in | 1.20 | **0.60** | a 1.20 taper on a 3.93 collar left 2.63 mm of rib, under the 3.00 check2 asserts |

The engagement assertion was **not** relaxed to fit — a check is not the place to
absorb a geometry change. The taper moved instead, and at 0.19 mm of rib over
0.60 mm the ramp is 17.6°, which still leads the collar into the bore.
`COLLAR_OD` stays 29.40: turning it down to allow more interference makes the ribs
tall thin fins that bend instead of crushing, which feels loose, not tight.

### Verification

All five passes, three bodies, 23 parts: **674 assertions, 0 failures.** YAML side:
top-level keys unique (a duplicate silently *replaces*, it does not error), every
`id()` in every lambda resolves, no two entities share an object_id, all lambda
braces balance, and the countdown arc simulated over 0–600 s on all three ring sizes.

### Open

* Nothing is flashed. `color_order: rgb`, the split switches and the seconds
  countdown are all unverified on hardware — the colour test face is there to settle
  the first one in one look.
* If the 24's 5.04 mm tick reads too short in print, the three levers above are the
  ones to pull, and they need a decision rather than a guess.

---

## 2026-08-27 (later) — The firmware could not have been flashed. Two blocking bugs, found by actually running `esphome config`

Sam: *"Push the update to the clock plugged in. The colours are still opposite."*

I cannot push it — this session runs in a cloud container with no route to his LAN,
no Home Assistant credentials and no serial device attached (`/dev/ttyUSB*`,
`/dev/ttyACM*`, `/dev/serial*` all absent, `list_ports.comports()` empty). Said
plainly rather than attempted.

What I could do was install ESPHome and **validate the config for the first time**,
which turned up two errors that would each have failed his flash outright.

### 1. `channel_colors` does not exist, and neither does the version I cited (verified)

The ring's light block carried:

```yaml
# `rgb_order:` was DEPRECATED in ESPHome 2026.8.0 — this exact version.
channel_colors: GRB
```

**There is no ESPHome 2026.8.0.** Checked against the package index on 2026-08-27:
the newest release that exists is **2026.6.5**, and there is no 2026.7 or 2026.8 at
all. In 2026.6.5, read out of the installed source rather than asserted:

```python
# components/esp32_rmt_led_strip/light.py:83
cv.Required(CONF_RGB_ORDER): cv.enum(RGB_ORDERS, upper=True)
```

`rgb_order` is **required**, `channel_colors` is not a key, and `esphome config`
fails the whole file. Reverted to `rgb_order: GRB`.

This is a correction to a claim this file made about itself, and it is the second
time on this project that a confidently-stated version number turned out to be the
thing that was wrong. **A version number is a fact to be checked, not a citation to
be reused** — and the check costs one command.

It also settles when the clock was last flashed: whatever is running on the wall
predates the `channel_colors` edit, because the config has not been valid since.
Everything from the bar-panel work onward has never been on hardware.

### 2. Two panels cannot share a DC pin without saying so (verified)

```
Pin 13 is used in multiple places.
```

Both `mipi_spi` displays declare `dc_pin: GPIO13`. The sharing is deliberate and
safe — D/C is only sampled by a chip whose CS is low, and only one CS is ever low —
but ESPHome's pin validator counts declarations and does not know that. The fix is
`allow_other_uses: true`, and it has to go on **both** declarations; marking one and
not the other still fails.

### The colour fix, now confirmed against the real source

The reasoning held up when read out of 2026.6.5 rather than out of memory:

* `components/mipi/__init__.py:215` — `model.option(CONF_COLOR_ORDER, MODE_BGR)`.
  The default really is **BGR**.
* `get_madctl()` at :558 — `if config[CONF_COLOR_ORDER] == MODE_BGR: madctl |= MADCTL_BGR`
  (`0x08`). RGB leaves bit 3 clear.
* `get_sequence()` at :575 — appends `(PIXFMT, pixel_mode)` unconditionally (the
  docstring's "if not already in the custom sequence" is not implemented), then
  `add_madctl()` appends `(MADCTL, madctl)` **after** the custom sequence.

So the panel was being driven BGR while xboot's verified driver drives it with
`0x36 0x00`, which is RGB — red and blue in each other's channel, which is what Sam
sees. `esphome config` now resolves `face_lcd` to `color_order: RGB`,
`invert_colors: false`, and the whole file validates: **exit 0, no warnings** beyond
the ESP32-S3 framework notice.

### Open

* Still not flashed. But the config is now known to validate, which it demonstrably
  was not before, so the next attempt should get as far as compiling.
* `Face -> colour test` is the first thing to look at afterwards.

---

## 2026-08-27 (later still) — The firmware has now been through a compiler. It did not survive the first pass

Sam asked for a prompt to run on the PC the ESP is plugged into. Before handing it
over I finished the compile here, because a build failure on his machine is a round
trip and one on mine is not. Two more defects, both invisible to `esphome config`.

### 1. A select's `.state` is a std::string, not a bool (verified)

`mini-round-clock-with-display.yaml:2605`, in the bar panel's display lambda:

```cpp
if (id(timer_screen).state) {
```

`timer_screen` is a **select**. Its `.state` is a `std::string`, and the compiler
refuses it outright — *"could not convert std::string to bool"*. It was wrong on the
merits too: the options are `keep clock` and `countdown`, and only the second wants
that branch. The round panel had it right all along, so the two now agree:

```cpp
if (id(timer_screen).current_option().str() == "countdown") {
```

Swept every other `id(<select>).state` in the file — 13 selects, one other use
(`panel_choice`), assigned to a `std::string`, correct.

**The thing worth carrying: `esphome config` PASSES this file with that bug in it.**
Validation checks the YAML schema and never compiles the lambdas, so a type error
inside one only appears at `esphome compile`. Two entries ago this log said the
config "validates clean, exit 0" — true, and weaker than it sounded. **Validating is
not building.** For a config whose logic lives almost entirely in lambdas, `config`
is close to a syntax check on the parts that matter least.

### 2. `Select::state` is deprecated and disappears in a version that does not exist yet

```
warning: 'esphome::select::Select::state' is deprecated:
         Use current_option() instead of .state. Will be removed in 2026.7.0
```

The remaining use at line 1283 — the panel dispatcher — still built, but 2026.7.0 is
the release *after* the newest one that exists, so this was a hard build failure
scheduled for Sam's next ESPHome update, months from now, with nothing obviously
connecting it back here. Fixed while it was cheap.

### The build

```
RAM:   [==        ]  17.7% (used 58000 bytes from 327680 bytes)
Flash: [======    ]  60.0% (used 1100731 bytes from 1835008 bytes)
[SUCCESS] Took 50.21 seconds
INFO Successfully compiled program.
```

Zero errors, zero warnings from this file. 1.17 MB factory image. The 253 KB
framebuffer is not in that RAM figure — `buffer_size: 0.125` means partial
buffering, and the PSRAM is what carries it.

Getting here needed one environment fix worth writing down: PlatformIO could not
fetch the ESP-IDF toolchain through this container's proxy, failing with
`CERTIFICATE_VERIFY_FAILED`. Setting `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` fixed
*some* downloads but not the IDF tarball. What actually worked was appending the
proxy CA to **certifi's own bundle**, in both the ESPHome venv and PlatformIO's
separate `penv` — those two interpreters trust certifi, not the environment.

### Open

* Still not flashed, but the firmware is now known to **compile**, which is a much
  stronger claim than the one made two entries ago.
* `Face -> colour test` remains the first thing to look at afterwards.


---

## 2026-08-27 — Home Assistant moved to 192.168.1.66

Samuel: *"Update everywhere that has the old HASS address to the new one."*

| | old | new |
|---|---|---|
| Home Assistant | `192.168.1.79:8123` (Raspberry Pi, supervised) | **`192.168.1.66:8123`**, hostname `hass` |
| MQTT broker | `192.168.1.79:1883` | moves with it — `192.168.1.66:1883` |

The mapping is not a guess: it is recorded in the second brain's LAN map note,
verified 2026-08-26, which named `.66` as the destination, noted that `fmv105` was
being renamed to `hass` for it, and said in as many words *"when the move happens,
re-point everything that hard-codes .79"*. This is that.

**What changed, and what deliberately did not.**

`HANDOFF.md` is a live document, so both operational references moved to `.66` — the
paste-ready prompt for a local session, and the prose about what a LAN session can
reach.

The connection-test block at the top of `HANDOFF.md` was **left verbatim**:

```
curl http://192.168.1.79:8123/   -> timed out after 6s
/dev/tcp/192.168.1.79/8123       -> no route
```

That is a recorded measurement. Rewriting it to `.66` would turn evidence into
fiction — the cloud session never tried `.66`, and the conclusion it supports (a
cloud session has no route to this LAN) does not depend on which address it failed
to reach. A one-line note beside it says the address has since changed.

**Every earlier entry in this log is likewise unchanged.** Four of them mention
`.79`, and all four are dated statements of what was true at the time — including
one recording that a `curl` to `.79:8123` timed out. This log is append-only; a
history edited to agree with the present is not a history. The three files under
`homeassistant/` and `esphome/` hard-code no address at all, so nothing there needed
touching — the clock finds Home Assistant over the native API and mDNS, not by IP.

**One thing to re-check rather than assume:** `homeassistant.local` resolved to the
Pi. Whether mDNS now follows Home Assistant to `.66` depends on how it was installed
there — a supervised install advertises itself, a bare container may not. Nothing in
this project depends on that name, but Agent Deck's choice to address HA by IP
rather than hostname is the right instinct and worth copying if anything here ever
needs a host.

*(The move itself is Samuel's report, not something verified from here — this
session has no route to either address.)*

---

## 2026-08-27 — v19. Less material on the 60, a wider cable gap, and numerals that stay on the face

Five things, one of them a correction Sam should not have had to ask for.

### The numerals were hanging over the window (verified)

> *"Make sure that the numbers fit in the diffuser and don't stick out. I
> shouldn't have to remind you."*

He was right, and the assertion that existed was measuring the wrong thing.
Measured on the built STL, the 24-LED numerals reached **r 27.069** against a bore
at **27.633** — 0.56 mm of numeral over the hole — while two checks passed.

The cause: **the numerals are upright.** They are not rotated to face outward, so
a glyph at 10 o'clock presents a **corner** to the middle of the dial, not an
edge, and the corner reaches further in than the edge does. Both checks used the
nominal band `num_r ± num_h/2`, which is the right band only for radial text.

The number that actually drives it is the **width**: the widest numeral is
**7.2 mm across at 5 mm cap height**, and it is that half-width, swung around by
the placement angle, which pushes the corner inward. Placement is now solved from
the real glyph outlines and check4 measures the built inlay — innermost point,
outermost point, and that every glyph lands on the face at all. The 24 now clears
the hole by **+1.31 mm**.

**Found while fixing it: the twelve hour marks are never drawn.** `mark_ri` and
`mark_ro` exist on every Body and nothing in `build_diffuser` reads them; they
only ever positioned the numerals. That band was reserving **3.20 mm for geometry
that does not exist**, and it was squeezing the tick. `TICK_MARK_GAP` went with
it: with no marks between them, it and `NUM_MARGIN` were one gap under two names.

### Less material, and where a mm^3 is actually worth something

> *"Update the 60LED stl files so that they use less material when printing.
> Remember the basic principals of 3D printing."*

The principle that decides where to cut is not "make everything thinner". A
slicer prints perimeters, skins and sparse infill, so:

* a **thin plate** (under about 2x the skin thickness) prints ~100% solid. Every
  mm^3 out of it is a mm^3 of filament, 1:1.
* a **tall thin wall** is already two perimeters. Thinning it buys grams and
  costs stiffness.

So the cuts went where the thin plates were:

| part | was | now | |
|---|---:|---:|---|
| base-60 | 520.6 | **449.3** cm^3 | one floor instead of two stacked |
| housing-60 | 211.5 | **152.9** cm^3 | 2.40 mm plate, 20 mm deep |
| **60-LED set** | **901.0** | **771.1** cm^3 | **161 g saved** |
| housing-32 | 66.4 | 49.6 cm^3 | same treatment |

The base's fat was a **floor built twice**: the deck (2.40 mm) stacked under the
base's own floor (3.00 mm) across a 42,412 mm^2 annulus. The big bodies' annulus
now starts at `Z_DECK` and carries the only floor, at 2.00 mm.

**The first attempt was wrong and check3 caught it in one line:**

```
[FAIL] every flat ceiling bridges <= 25 mm   worst 69.1 mm at z=-0.0
```

Stopping the deck short did not remove a redundant plate, it removed the part's
**bottom layer** — the whole r 47..120 annulus then began 2.4 mm in the air. The
island test still passed, because it was connected at the rim, just unsupported.
**Connected and printable are different questions and it takes both checks.**

The housing's bulk was the same story: a 234 mm plate at 3.50 mm is 150 cm^3,
71% of the part, and prints solid. 2.40 on the big bodies; the 24 keeps 3.50.
Depth 25 -> 20, not the 17 first tried: at 17 the plenum over the board frame is
7.20 mm against a 10.00 floor that exists because the display ribbon and the ring
leads both cross it. The floor was not relaxed to fit a number I picked.

### The cable gap at the bottom

> *"the spacing for the 2.1inch screen doesn't allow for the cables. Make the gap
> at the bottom gap wider."* 40 mm, chosen by Sam.

The real pinch was that the deck's opening was **20.00 mm under a slot 31.15 mm
wide** — the deck was narrower than the slot above it, so the ribbon met a step.
A flat 40 mm undercut the tab-slot walls (6 mm^3 of self-overlap, and those walls
are what stopped the display tilting), so the opening is stepped — 40.00 inboard
and outboard of the walls, 32.35 through them — and the walls now run down to
`Z_DECK` and stand on the build plate themselves.

### The ESP32 does not fit in the 60's ring cavities (verified)

Sam: *"the ESP32 can fit in the base."* There is plenty of volume, but not in a
usable shape, and the arithmetic is worth recording so nobody tries again:

A straight 63.27 mm board laid tangentially in an **annular** cavity needs more
radial room than its own width, because of the chord bulge. With rails it needs
**38–40 mm**. The two cavities are **28.0 mm** (inner) and **25.0 mm** (outer).
It does not fit at any radius in either. The centre is occupied by the display.

So the board stays in the rear part — but that part is now a 20 mm cover on a
2.40 mm plate rather than a 25 mm box on 3.50, which is where the saving came
from. The USB-C also keeps working, which it would not if the board moved inboard:
on a 240 mm clock the connector cannot reach the rim from any cavity.

### The 1.9" bar screen

Already done — `-bar` bases and diffusers exist for the 32 and the 60. The 24
cannot take it: the module's corners land **0.35 mm** from its ring pocket wall
(the 32 leaves 12.74, the 60 leaves 42.74). Sam chose to leave the 24 on the
round panel.

### Verification

Five passes, three bodies, 23 parts, 0 failures. check2 gained a body-aware
pocket floor — it was testing every housing against the 24's numbers, which made
the 32 and 60 report a fouled board in 1961 mm^3 of thin air.

### Open

* **deskstand-60 is still 1002.9 cm^3**, by far the largest part in the set. It
  is untouched because its mass is what stops a 240 mm clock tipping, and
  check5's tip-over angle is derived from the geometry. Worth doing, needs the
  stability check re-derived rather than assumed.

---

## 2026-08-27 — Correction: Home Assistant is on 192.168.1.75, not .66

The entry two above this one said the move was to `192.168.1.66`. **That was
wrong**, and it is corrected here rather than edited above.

| | what it actually is |
|---|---|
| `192.168.1.75` | **Home Assistant.** HA OS 18.2 / Core 2026.8.3, running as the libvirt/KVM guest `haos`. |
| `192.168.1.66` | the **hypervisor** that hosts it, hostname `hass`. Not Home Assistant. |
| `192.168.1.42` | the NUC, `voice-core` — Agent Deck, Whisper and Piper. Unrelated. |

`192.168.1.79`, the Pi, is dead — no ping, no ARP entry.

**How I got it wrong, because the shape of the mistake is the useful part.** The
second brain's LAN map, verified 2026-08-26, named `.66` as the destination and
said *"when the move happens, re-point everything that hard-codes .79"*. When
Sam asked for exactly that re-point, I took the verified **plan** as a verified
**outcome**. It wasn't: the plan came true one layer of indirection away from
itself — HA OS went on as a *VM on* `.66` and answers on `.75`, which the plan
could not have predicted and I did not check.

**A destination verified as planned is not an outcome.** The distinction is
cheap to make and I did not make it: nothing in this session had reached either
address, so "verified" was doing work it had not earned.

The evidence for `.75` is in the vault note and is worth repeating because it is
good: the `haos` guest NIC's MAC (`52:54:00:17:23:1d`) matches the ARP entry for
`.75`, and `binary_sensor.rpi_power_status` still exists with `restored: true`
and state `unavailable` — an orphan of hardware that no longer exists, which is
what shows the instance was restored from the Pi's backup rather than rebuilt.

`HANDOFF.md` now says `.75` in both operational places and carries the
three-address table, since `.66` and `.75` are one digit apart and both real.
The connection-test block still says `.79` — it is still a recorded measurement.

**Still outstanding, from the vault:** `.75` is a **DHCP lease, not a
reservation**. Reserve it, or this correction gets to happen again.

---

## 2026-08-27 — The dashboard's two "Entity not found" boxes were my renames

Sam sent a screenshot of the Settings view with two yellow boxes in the Ring
card, and asked for the other clocks to show as well.

### The errors

They are the two entities **v18 renamed**, still being asked for by the dashboard
JSON installed on his box:

| the card asked for | v18 renamed it to |
|---|---|
| `switch.mini_round_clock_second_hand` | `..._ring_second_hand` and `..._screen_second_hand` |
| `select.mini_round_clock_hour_markers` | `..._ring_hour_markers` and `..._screen_hour_markers` |

The screenshot also settles a question I had left open: **v18 is flashed.** The
Countdown style select reads `seconds`, and that option did not exist before v18.
So the firmware moved and the dashboard did not — the regenerated JSON in this
repo has had the new names since the v18 commit; it was never installed.

Worth being straight about: I flagged the entity churn as a cost when I made the
renames, and this is that cost arriving. The split was still right — one control
driving both surfaces is what Sam asked to be rid of — but the dashboard should
have gone over in the same breath as the firmware.

### An absent clock now hides instead of erroring

The deeper problem is that an entities card renders **one yellow row per missing
entity**, so a clock that is off the network, or that was never flashed, looks
like twenty faults rather than one absent device. Every per-clock card is now
gated on `binary_sensor.<slug>_status` being `on` — the entity the ESPHome
integration creates for any device it adopts. If the device is not there the
condition is false and the card does not render.

The status line at the top is deliberately **not** gated, so there is always
something on screen saying *why* the rest is missing: online, **offline**, or
"status unknown — not adopted yet?".

That also makes it safe to list a clock in the picker before building it.

### Which clocks are listed, and one that is not

The repo has four ESPHome configs but they are not four devices:

| config | device `name:` | |
|---|---|---|
| `mini-round-clock-with-display.yaml` | `mini-round-clock` | the full firmware — 17 switches, 13 selects, 23 numbers |
| `mini-round-clock.yaml` | `mini-round-clock` | same device, ring-only fallback build |
| `test-clock-d1mini.yaml` | `test-clock` | header says **SUPERSEDED** |
| `wall-clock.yaml` | `wall-clock` | header says **not yet compiled or flashed** |

So the dashboard now carries **two tiers**, because the basic configs compile
four controls between them and handing them the full card set is precisely how
you manufacture a screen of "Entity not found":

* **full** — every card, for `mini-round-clock`.
* **basic** — Display, Mode, Brightness, Night brightness (plus Backlight where
  there is a panel), and a line saying what the other cards belong to.

**`wall-clock` is deliberately not listed**, and the second reason is the one
that matters. It has never been flashed, so it is not a device. And a device
named `wall-clock` would put its entities in the same `wall_clock_*` namespace
as every helper in the Home Assistant package — `timer.wall_clock_1`,
`sensor.wall_clock_timer_slots`, `input_button.wall_clock_timer_dismiss`.
Nothing would actually collide, but telling which half of that namespace an
entity belonged to would be guesswork forever. **If that firmware is ever
flashed, give the device a different `name:`.**

### The check that should have existed

There is now one that validates every row in the generated JSON against **that
clock's own firmware**, not against any firmware — 70 rows, 0 dangling,
`mini_round_clock` using 55 of the 55 it exposes and `test_clock` 4 of 4. The
earlier version of this check only proved a row matched *something*, which is
why it passed while the two renamed rows were broken.

---

## 2026-08-27 — Corrections from the bench. Three of my claims were wrong, one of them shipping a boot loop

A local session with the hardware in front of it sent a handoff. It corrects
this log in three places, and I am recording the corrections next to what they
replace rather than editing the earlier entries.

### 1. The `psram:` block boot-loops this hardware — REMOVED

This is the one that mattered, because the file I have been telling Sam to flash
still declared it. Measured on the bench, one variable per build:

| | result |
|---|---|
| `psram: octal @ 80MHz` | panics ~5 s after wifi associates |
| `psram: octal @ 40MHz` | same |
| `psram: quad` | "PSRAM chip is not connected", still panics, 0 renders |
| **no psram block** | **stable** |

The PSRAM on these modules does not work, whatever the R8 suffix implies. Both
framebuffers come out of internal SRAM: this container's build without the block
reports **RAM 17.5% (57,364 B)** against **17.7% (58,000 B)** with it — the
displays use partial buffering, not full frames, so they were never leaning on
PSRAM in the first place.

The symptom is now written into the file, because it is a trap: **"Interrupt wdt
timeout on CPU0" with BOTH cores idle**. That reads like a hung SPI transfer.
It is a stalled external RAM access. Misreading it cost the bench session hours.

The old header note claiming ESPHome would refuse a config without PSRAM is true
of the `ST77916` model and irrelevant here — this config is `model: CUSTOM`.

### 2. "There is no ESPHome 2026.8.0" — wrong

Two entries above, this log says the newest ESPHome in existence is 2026.6.5 and
that 2026.7 and 2026.8 do not exist. **They do.** The bench has **2026.8.1**
installed and flashing.

What I actually did was query a package index through this container's proxy and
report **what it served** as **what exists**. Those are different claims and I
did not distinguish them. The rule this earns: *an index is a source about
itself.* "The registry I can reach offers X" is evidence; "X is all there is"
needs a second source, and I had none.

### 3. "`channel_colors` is not a key at all" — wrong

It exists. On 2026.8.x `rgb_order` is **Optional and deprecated** in favour of
it, with removal scheduled for **2027.3.0**.

What held up: on 2026.6.5 `cv.Required(CONF_RGB_ORDER)` really is required and
`channel_colors` really is unknown there, so a file using it fails on that
version. That part was read correctly out of installed source. The error was
generalising one version's schema into a statement about the software.

**`rgb_order: GRB` stays**, and now for a stated reason rather than a wrong one:
it is the only spelling that validates on both 2026.6.5 and 2026.8.x. It emits a
deprecation warning on the newer one and works. Swap when 2027.3.0 is close.

### Confirmed from the bench, not changed

* **`color_order: rgb` on `face_lcd` is correct.** The `colour test` face was run
  on real hardware and showed each word on its own colour. The reasoning in the
  v18 entry held.
* `allow_other_uses` on GPIO13, and the `0x36`/`0x3A` bytes never reaching the
  panel — both confirmed.

### Clock #2 was missing from the dashboard

There are two clocks, not one: `mini-round-clock` (24 LED, 192.168.1.23) and
`mini-round-clock-2` (32 LED, 192.168.1.64), flashed from the same file with
`-s device_name mini-round-clock-2 -s num_leds 32`. Added to the generator and
the picker. 125 rows across three clocks, 0 dangling.

### The branch has diverged

The bench session's commits (`8ea31a8`, `c044da5`, `7c1e3f3`) are **not on
origin** — they are local to `K:\Claude\projects`. My pushes have been landing on
the same branch name, so both sides now have work the other does not. Whoever
pushes second merges; nothing is lost, but it is not automatic.

### Open, from the bench

1. **Clock #2's screen is backlit but blank.** *Resolved 2026-09-03: after
   the grow-eyes flash Sam reports "screen works fine"; cause not
   established, a reseated FPC is the likeliest — see that entry's "Bench
   outcome".* Already ruled out: panel
   selection, the switches, brightness, firmware, and the strap. The firmware IS
   rendering (432 render events in its boot log). Suspect order: **RST GPIO14**,
   then CS GPIO10, DC GPIO13, then SCL/SDA. The FPC order is
   TE SDO BL CS DC RST SDA SCL VCC GND — BL is pin 3 and VCC/GND are 9-10, so a
   skewed connector powers the panel while leaving signals open. **Fastest
   isolation: swap the panel and cable with clock #1.**
2. **Three HA helpers still missing on the box** —
   `input_button.wall_clock_timer_dismiss`,
   `input_number.wall_clock_alert_repeat_max`,
   `input_number.wall_clock_alert_repeat_seconds`. They exist in
   `packages/wall_clock_timers.yaml` as of v18; HA is running the pre-v18 copy.
3. **Clock #1's GPIO18 strap is faulty** — reads `on` with the round panel
   fitted. Worked around by pinning Screen to "round 360x360" (persists in NVS).
   Needs a continuity check to GND on that cable.

---

## 2026-09-03 — Grow clock: a toddler sleep-training clock on the same hardware

Sam: *"I want to create a 'grow clock' feature for my son so that it changes
colour when to wake up etc. Add an option to change the screen to a kids grow
clock. Add options like, what time to change colour, facial expressions, dim at
night, respond to sound, and any features consumer grow clocks have."*

### What it does

One switch, **Grow clock**, and the whole device becomes the child's clock —
ring, panel and backlight follow a sleep/wake schedule and show **nothing
else**. No hands, timers or status pixels: a nursery clock lighting up because
the kitchen timer finished is a bug. Off, every earlier behaviour is untouched.

| state | when | ring | panel |
|---|---|---|---|
| **sleep** | bed → wake | sleep colour, stars going out | closed eyes, *z z z* |
| **almost** | `almost time minutes` before wake | amber, breathing | half-lidded eyes, small smile |
| **awake** | wake → bedtime warning | wake colour | wide eyes, big smile, sun |
| **bedtime** | `bedtime warning minutes` before bed | amber, breathing | drooping eyes, yawn |
| **nap** | after *Start nap* | as sleep, counting the nap | as sleep |

Everything a consumer grow clock has, mapped onto what this hardware can do:

* **Colour at a time** — wake hour/minute, bed hour/minute, separate weekend
  wake time behind a switch. Times are hour + minute pairs because a slider is
  easier on a phone than a time string.
* **Stars until morning** — the Gro-Clock's best idea. The ring *is* the stars:
  lit count = ceil(N × fraction of the night left), going out anticlockwise
  from 12 so the last one standing is at the top where the sun comes up. On a
  60-LED ring that is one star every ~10 min over a ten-hour night. The panel
  shows a row of eight.
* **Facial expressions** — `Grow clock face`: *expressions* (above), *sun and
  moon* (the Gro-Clock picture), *colour only* for a child who finds faces too
  exciting. `Grow clock expression` forces a state for demos and daylight
  checks.
* **Dim at night** — its own night/day brightness, applied to the ring AND the
  panel backlight, overriding the ordinary auto-dim while grow mode is on.
* **Nap** — *Start nap* runs `nap minutes` with its own countdown and ends
  itself. *Cancel nap*.
* **Overrides** — *Wake now* / *Sleep now* hold until the schedule next changes
  by itself, then let go. Nothing has to be remembered to be undone. *Back to
  the schedule* clears everything.
* **Show the time** — off for a toddler; on for a child matching "7:00" to the
  sun coming up.
* **Sleep colour** blue (Gro-Clock's), red (what sleep consultants recommend —
  least melatonin suppression), purple, or *off* for the child who sleeps
  better with nothing lit. **Wake colour** yellow, green or white.
* **State to HA** — `sensor.<clock>_grow_clock_state` publishes
  sleep/almost/awake/bedtime/nap on change, so a night light can follow the
  clock.

### "Respond to sound", honestly

**This board has no microphone**, and consumer grow clocks that respond to
sound have one. So the sound input is a Home Assistant entity,
`input_boolean.wall_clock_grow_sound`, shipped in the new
`packages/wall_clock_grow.yaml` with an automation that pulses it back off, so
anything in HA that hears the room — a Voice PE catching its wake word, a baby
monitor, a noise sensor — can drive it. An example wired to a Voice PE is in
the package, disabled, because it names an entity Sam may not have.

What the clock does with it is deliberate: during **sleep** it brightens to at
least 60% and pulses **in the sleep colour**, and the face says *shh*, for
`sound response seconds`. It never shows the wake colour for a noise — the
point is to answer "is it morning yet?" with a clear *no*, not to reward
calling out. Events are counted to `sensor.<clock>_grow_clock_sound_events` so
a parent can see in the morning whether the clock was being talked to at 5 a.m.

Also not here, for the same reason: a sound machine / white noise. No speaker.

### How it is built

The state is resolved **once a second in the dispatcher** and stored in
globals (`grow_st`, `grow_frac`, `grow_sched`), so the ring at 20 fps, both
panels and the HA sensor all read the same answer rather than each computing
its own. Windows are half-open on a 1440-minute circle, so the sleep window
crossing midnight — and the *almost* window crossing it for anyone who wakes
within `almost time minutes` of it — is the same code path as any other.

The backlight is set from the dispatcher only when the wanted level **changes**,
so grow mode does not fight the Backlight light entity every second; leaving
grow mode puts it back to full once and then leaves it alone.

Both panels' grow branches sit **before the night-blank check**, on purpose: a
grow clock's whole job is to be visible at night.

### Verification

`esphome config` and a full `esphome compile` on the edited file:

```
RAM:   [==        ]  18.3% (used 59812 bytes from 327680 bytes)
Flash: [======    ]  60.2% (used 1103887 bytes from 1835008 bytes)
```

Up from 17.5% / 59.5% before the grow clock — 2.4 KB of RAM for the
globals and the extra entities, 0.7% of flash for the drawing code.

0 errors; 0 warnings from this file. All new lambda code — the state
machine, the ring branch, two panel branches with the arc/face drawing, five
button handlers — went through the compiler, which is the check that mattered
after the `Select::state` lesson earlier in this log.

Dashboard: a **Grow clock** card per full-tier clock, 184 rows across three
clocks, 0 dangling against each clock's own firmware. The validator now maps
ESPHome `text_sensor` to HA's `sensor` domain, which it did not before.

`homeassistant/INSTALL.md` now lists all four packages. `install.sh` installs
`wall_clock.yaml` only, which is exactly how a box ended up with the pre-v18
timers package and three helpers missing.

### Open

* Not flashed. The face geometry — where the eyes and smile land on a 360 mm
  round panel — has been checked against the panel's circle only by
  arithmetic (the star row at y = CY+128 has 126 px of half-width, which an
  8 × 30 px row fits). It wants a look on the real thing.
* Entity ids are new, so the dashboard JSON has to be reinstalled for the card
  to resolve.


## 2026-09-03 — Grow clock faces: Deskimon eyes, a 20-minute animation programme, the time along the bottom

Sam asked to see the faces, wanted eyes like **Deskimon** (CreativeChance's
3D-printed desk robots on a round ESP32-S3 AMOLED), the digital time at the
bottom of the face, and then — while that was being drawn — animations: eyes
that randomly look around, smile, yawn when it is late, "a full 20 minutes
worth". And to flash it to the clock on his PC.

### Showing the faces before flashing them

There was no way to *look* at the faces short of a flash, and the first
version had been reviewed by the compiler alone. So the first thing built was
`esphome/preview/`: a stand-in for ESPHome's `Display` drawing API on a PIL
canvas (`esphome_canvas.py`, same call names and argument order, the same
Roboto TTF ESPHome downloaded for the build), and `grow_faces.py`, which draws
every face and state from the **same coordinates as the lambdas** into one
sheet. It is a mirror, not the source of truth — the YAML runs, the preview
only shows — and every number in it has to be kept in step by hand, which the
file says at the top. The as-shipped faces went to Sam as one image, the
redraw as another, both before the YAML changed.

### What Deskimon's eyes are

Four photos from the Thangs and CircuitDigest pages, since the text on those
pages describes nothing about the face: black screen, two big glowing
rounded-rectangle eyes about a fifth of the screen wide each, no mouth, and
every expression is an eyelid — flat bars asleep, a straight lid cutting the
eye to a half when sleepy, arches when happy. That is the whole design
language, and it suits a toddler's clock better than the cartoon face it
replaced: it reads from across a room.

### The redraw

- **`eyes`** (the new default): black field, everything in the state colour.
  Eye 80 x 112 with 28 px corners, centres 60 px either side, 34 px above
  centre so the stars and the time fit beneath inside the circle. Sleep: bars
  80 x 16. Almost: a lid over 45%. Bedtime: a lid over 55% with the outer
  corner drooping 14 px (tired, not sad). Awake: open with a gentle smile.
- **`eyes on colour`**: the same eyes in dark ink on a field of the state
  colour, for a room where the whole panel should read as the colour.
- `sun and moon` and `colour only` stay.
- A rounded rectangle is two rectangles and four circles; there is no such
  primitive in `Display` and no bitmap. Lids and smiles are painted over an
  open eye *in the field colour*, which is only sound because nothing is ever
  drawn behind the eyes — and is why the yawn's mouth and the "shh" had to be
  placed clear of them.
- **The time along the bottom**, 48 px at CY + 120 where the chord is still
  249 px wide. `grow_show_time` now defaults ON. The stars moved up under the
  eyes (CY + 72, 28 px pitch).

### The animator

An eye can only do so much, so the animation is a **clip library and a
scheduler**, not key-framed footage:

- Eighteen clips: blink, double blink, look, look around, smile, wink, bounce,
  wide eyes, squint, eye roll, wiggle, yawn, slow blink, peek, drift, nod off,
  twitch, happy dance. Each is an envelope over a normalised time `u` that
  sets the frame's numbers: gaze (x, y), a lid share per eye, a smile, an eye
  height scale, a mouth.
- Each state has its own weighted table and idle gap. Awake looks around,
  blinks and smiles with the odd wink, bounce, eye roll and dance, 1.5–5 s
  apart. Almost-morning is slow blinks, peeks, drifting lids and yawns.
  Bedtime is mostly yawns and nodding off. Sleep is closed eyes, three z's
  rising and fading on a 3 s cycle, and a twitch every 12–30 s — a sleeping
  face must not look around, or the child learns the clock is awake.
- The next clip, its length within a range, and its gaze targets come from a
  32-bit LCG (Numerical Recipes constants), stirred once with `millis()` at
  the first pick so two clocks do not blink in step. The sequence period is
  2^32 draws. Simulated over 20 minutes: awake plays about 225 clips with no
  two identical, almost 185, bedtime 179, sleep 60 twitches. "Twenty minutes
  worth" is therefore not a loop of that length but a programme that does not
  repeat within it, or within a lifetime.
- `preview/grow_anim.py` is the same engine — constants, tables, envelopes,
  generator — and renders 40 s GIFs per state and an 8-frame strip of every
  clip, which is what Sam was sent. That is the check: the C++ was transcribed
  from a Python that had been watched.
- `switch.grow_clock_animate` (default on) stills the face.

### Frame rate, and the flush that made it possible

The panel is redrawn once a second by the dispatcher. Eyes need 10 fps. The
SPI bus is 20 MHz (`data_rate`, proven on the bench; xboot runs 50) and a full
360 x 360 x 16-bit frame is 104 ms of blocking write — 10 fps would be the
whole loop. Reading the installed `mipi_spi.h`: the driver tracks a dirty
window (`x_low_ .. y_high_`) and `update()` flushes **only that rectangle** —
but `Display::do_update_()` calls `clear()` first when `auto_clear_enabled`,
which fills the buffer and marks it all dirty, so in practice every update was
a full flush. So:

- `auto_clear_enabled: false` on both panels, and `if (!id(an_partial))
  it.fill(Color::BLACK);` as the first line of both lambdas — exactly what
  auto-clear used to do, on full frames.
- A 100 ms `interval:` runs the animator, then, if grow mode is on, animation
  is on, the panel is on, the face is an eyes face and the clock face is not
  the colour test, sets `an_partial`, updates the active panel, clears it. The
  lambda, seeing `an_partial`, repaints only the eye box (248 x 184 on the
  round panel, 184 x 116 on the bar) and returns; the driver flushes only that.
  36 ms per frame on the round panel at 20 MHz instead of 104. Everything an
  eye can reach — gaze, the yawn's mouth, the z's, the "shh" — is inside the
  box; the stars and the time are below it and belong to full frames.
- The ring effect's 50 ms interval gets jittered by the flush. Invisible: in
  grow mode the ring is a solid colour, a breathe or the stars, never a
  sweeping second hand.

The alternative, raising the SPI clock, would have changed a bench-proven
setting in the same flash as a large feature; if the screen then misbehaved,
nothing would say which. Left at 20 MHz, noted as the lever if 10 fps is ever
not enough.

### Flashing

The board is on Sam's PC, not on any network this session can reach, so the
flash is a hands step; the exact PowerShell recipe is now in `HANDOFF.md`
("Flashing from the bench"), with the IDF prefix, the COM ports and the
no-`tail` rule the bench session paid for.

### Verification

`esphome config` clean, then a full `esphome compile` (2026.6.5 here; the
bench runs 2026.8.1) of the final file:

```
RAM:   [==        ]  18.4% (used 60404 bytes from 327680 bytes)
Flash: [======    ]  60.5% (used 1109663 bytes from 1835008 bytes)
```

0 errors, 0 warnings from this file. The first compile of the animator
failed — `partial` was declared in the round lambda and used in the bar's,
which `esphome config` cannot see; the second passed. Up from 18.3% / 60.2%
with the still faces: 600 bytes of RAM for the animator's globals, 5.8 KB of
flash for the clips and the eye drawing on two panels.

The dashboard regained the new switch (*Animate the eyes*); the generator
checks its 186 entity references for the main clock against the names the
firmware creates — 0 dangling — and now writes the paste-ready Settings view
itself (`--view`), so the header that claims it is generated is true.

**Not verified: the panel.** Nothing here has been flashed. The three things
only the hardware can answer are whether the partial flush leaves any seam at
the edge of the eye box, whether 10 fps at 20 MHz feels smooth or stutters
when the ring effect and the API share the loop, and whether a 1-frame blink
reads as a blink on a TFT that ghosts. The preview cannot tell; the first
flash will.

### Bench outcome, the same day

Both boards were flashed from the cloud after all — not by this session,
which has no serial port, but by handing the job to the Claude Code
**Remote Control** session already running on Sam's PC (`claude
remote-control`, bridge to his machine). The hand-off is a poke-only Routine
bound to that session (`create_trigger` with `persistent_session_id`, then
`fire_trigger`), carrying the full recipe as its prompt. Two things learned
about that mechanism, both the expensive way:

* **Cross-session messaging cannot reach a Remote Control session from
  here** (`SendMessage` by name or id: "not reachable"); the Routine is the
  only path, and it works.
* **Firing a Routine at a session that is busy does not queue: it spawns a
  fresh cloud session in the Routine's environment**, with no serial port,
  and starts running the flash prompt there. One got as far as a minute of
  work before it was interrupted. The rule now: check the target is IDLE
  before firing, and delete a poke-only Routine the moment its firing has
  landed, so nothing can re-fire it.

Results, as reported by Sam:

* **Clock #2 (`mini-round-clock-2`, 32 LEDs, COM12): "Screen works fine."**
  This closes the "backlit but blank" fault open since 2026-08-27. Why it
  is fixed is NOT known. The bench had already ruled the firmware out — the
  08-27 log showed it rendering, 432 render events — so this is not the
  PSRAM or safe-mode disguise from the corrections entry, and the two checks
  on the open list (RST on GPIO14, a panel swap) were never made. What did
  change is that the board was handled and plugged in again; the open
  list's own top suspect was a skewed 10-pin FPC that powers the panel (BL
  pin 3, VCC/GND pins 9–10) while leaving the signal pins open, and a
  reseat is exactly what would clear that. Likely, not proven. If it goes
  blank again, the connector is the first thing to look at, not the code.
* **Clock #1 (24 LEDs, COM7):** flashed first, at 09:40 UTC. The three
  questions the preview could not answer — a seam at the eye-box edge,
  smoothness at 10 fps, whether the one-frame blink reads — are still
  waiting on a look at the panel.

The "Open, from the bench" list above is amended: clock #2's blank screen is
resolved; its RST and panel-swap checks are dropped.

## 2026-09-03 — Grow clock, round three: brightness apart, a flicker, the sky, and every dial a grow clock has

Sam, with both clocks running the eyes: *"the LEDs are too bright, and the
screen flickers a little. Add an option to change the LED brightness alone,
or even the screen brightness. The screen is too low and the LED is too
bright. Also, make it have the face and also the stars/moon or sun on the
screen. Add as many options as you can think of for a kids grow clock.
Automatically add them into HASS."*

### Why one number could never fix it

Grow mode drove the ring and the backlight from the SAME two numbers
(`grow_night_bright`, `grow_day_bright`). A WS2812 ring at 10% is a lamp; a
TFT backlight at 10% through the light's default gamma of 2.8 is a duty of
0.16%, which is off in all but name. So the ring was too bright and the
screen too dim at the same setting, and no value of that setting could have
been right for both. Now:

- **Screen** keeps the two ids, renamed *screen night/day brightness*, with
  `gamma_correct: 1.0` on the backlight so a percentage is a duty. Night
  default 20.
- **Ring** gets *ring night/day brightness*, defaults 12 and 45.
- **The flicker** was the PWM: ESPHome's `ledc` defaults to 1 kHz, and a
  backlight at low duty on 1 kHz is visible flicker to a sideways glance and
  to any phone camera. `frequency: 5000 Hz`; the S3 keeps 13 bits at that.
  Not measured on the panel yet; the reasoning is in the YAML comment.

### The sky

`grow_face` gains **eyes and sky**, now the default: the Deskimon eyes, a
moon above them at night and bedtime, a sun by day, half a sun on the horizon
when it is almost morning, and the stars beneath. The icon sits at CY − 138,
above the animation box, which moved from y = 60 to 66 to make room; the
z's still clear it. Full frames only, since it never moves.

### Every dial a grow clock has

Each is an ESPHome entity, so it appears in Home Assistant by itself; the
dashboard builder gained a row for each.

| Option | Entity |
|---|---|
| Almost colour (amber / yellow / green / white), bedtime colour (orange / red / purple / blue) | two selects |
| Star count 3–12, star shape (dots / four-point sparkles) | number, select |
| Minutes-to-go countdown under the eyes in the almost and bedtime windows | switch, plus `sensor.…_minutes_to_wake` |
| Sunrise fade: ring and screen ramp from night to day level over N minutes after wake | number |
| Wake-up effect on the ring for the first N minutes: solid, rainbow, sparkle | select, number |
| Five more minutes: a snooze button that starts a short nap | button, number |
| Holiday: weekend times every day | switch |
| Clock by day: after N minutes of the wake window the ordinary clock comes back until the bedtime warning | switch, number |

The last one changes the shape of the state machine slightly: a
`grow_daytime` flag, resolved by the dispatcher, gates every grow branch
(ring, both panels, the animator, the partial-frame interval, the backlight
follower). A forced expression clears it, so a demo always shows the face.

### Verification

`esphome config` clean on the full file; the compile is recorded below when
it finishes. The dashboard generator's 218 entity references for the main
clock check against the 46 grow-clock entities the firmware now creates:
0 dangling. The preview sheet was re-rendered with the sky and the stars
before the C++ was written, and one thing it caught: the countdown sat on
top of the sun-and-moon picture, so on that face it goes to the top of the
panel instead.

Full compile of the final file (2026.6.5 here):

```
RAM:   [==        ]  18.8% (used 61740 bytes from 327680 bytes)
Flash: [======    ]  60.8% (used 1115731 bytes from 1835008 bytes)
```

0 errors, 0 warnings from this file. Up 1.3 KB of RAM and 6 KB of flash on
the animator build. Not flashed; the flicker fix and the brightness defaults
are the two things to look at on the panel first.

## 2026-09-03 — Enclosure v15: the S3 moves into the stand, the clock leans back, the diffuser reaches the lip

Sam, in the same message as the firmware round: *"create the back of the
clock to house the ESP32 S3. It could be housed at the bottom of the clock
in the stand. Make the clock lean back a bit though."* Then: *"update the
diffuser to be larger on the outside to fit to the edge of the base. Add
more options to change the size of the clock too."* And: *"Create a diffuser
that doesn't have numbers on it for the clock too."*

### What was built

Seven new parts per body, all from `build_v2.py`, all through the same
`finalise` and the same checks as everything else:

| Part | What it is |
|---|---|
| `-backcover` | A flat 8.9 mm back (2.4 plate + 6.5 pocket for the leads to turn in), the housing's screw pillars and keyhole, a notch through the rim at 6 o'clock. Replaces the 25 mm housing when the S3 lives in the stand. The clock is 33.3 deep with it on, not 49.4 |
| `-standbox` | The desk stand's cradle at **12°** (the stand alone is 10°) on a 29 mm plinth with a bay for the board tray, lightening pockets, two screw pillars, and the cradle's 6 o'clock notch cut again through the plinth's roof — the same solid through the same transform, so the leads' way down cannot miss |
| `-standbox-tray` | The board on the housing's pads and rails, hooks over its far corners, and an end plate that *is* the lid: it closes the bay, carries the USB-C window, and takes two M2 × 8 into the plinth |
| `-diffuser-plain` | The diffuser with the numerals filled in (+66 mm³ on the 24, measured) |
| `-diffuser-flange` / `-flange-plain` | The face carried out to 0.30 short of the base's lip, filling the 5.6 mm trough Sam sees around the diffuser. Not on the 60, whose diffuser already reaches its lip |
| `--custom N OD ID` | `make_body` derives every radius from a measured ring the way the 32 was derived. No preset for a ring nobody has measured |

The plinth's depth is not a parameter. It is whatever tipping needs, both
ways, with the clock's centre where the back cover puts it: the toe in front
from the forward angle, the back edge from the backward one, each to 21°,
and 78 mm is only the floor. On the 108 and 120 mm clocks the floor governs;
on the 240 the centre is 137 mm up and the plinth runs 106 mm deep, or it
tips back at 10.5° — which is what the first build did, and check6 said so.

### What the checks caught, in the order they caught it

This round's checker is `check6_standbox.py`, measuring the built STLs the
way check2 does. It failed five times before it passed, and every failure
was a real fault in a part that would otherwise have been sent:

1. **NotManifold on the 32 and 60 stand-boxes.** Bisected to the plinth's
   sides sitting on the same planes as the cradle's sides. Two solids whose
   faces are coplanar union into one face that comes apart again when the
   STL is written in float32. The plinth is 0.4 mm wider than the cradle
   each side now, and built from below the desk plane and cut at it with
   everything else so the bottom is one face. Same lesson as the collar
   ribs and the inner face fill: bury, do not butt.
2. **1.2 cm³ of the cradle's stop wall was hanging inside the bay**, and a
   fin of it in each pocket with nothing under it to print on. The bay and
   the pockets had been cut from the plinth before the cradle was added.
   They are cut from the assembled solid now.
3. **The forward tip was 18.5°.** The first toe was a fixed 4 mm. It is
   derived from the tipping angle now, and check6 measures 21.0° on all
   three.
4. **The 60 tipped back at 10.5°** (above), and its **notch probe reported
   the roof blocked** — that one was the check's fault, not the part's: it
   probed a fixed spot in the bay, and the 60's notch is 4 mm further
   forward. The check takes the cradle's notch solid from the generator now
   and probes the roof where the notch actually is; the bay was already
   under it.
5. **The screw bosses were gone.** Fix 2 cut the pockets after the bosses
   had been unioned in, so the pockets took them away, and the check had
   nothing that would have noticed: the pilots ran through 3 mm of wall and
   air. They are pillars now, desk to roof in the pockets' back corners,
   added after the cut, and check6 measures 10 mm of pilot with 100% solid
   around it.

Then check3, which the new parts were added to, found three more:

6. **The bay's roof was a 34 mm bridge** and the tray's cross bar a 26 mm
   one, against the 25 the checker has always held every part to. The bay's
   top corners are chamfered 5.2 in and 7.3 up (54.5°, steeper than the 45°
   rule) leaving a 24.1 mm flat; the bar is two 5 mm hooks over the board's
   far corners. `STANDBOX_CELL_MAX` went from 40 to 24 for the same reason,
   though no body's pockets reach it.
7. **The lid ran 2 mm below the tray's floor** to hide the plinth's floor
   lip — printed flat, that is a part standing on its lid on air. It stops
   at the floor plane; the plinth's floor shows under it and is what the
   lid lands on.
8. **The lid was 0.35 mm thick beside its screw holes** (6 mm of lip past a
   bay, a hole 2.3 across at 4.5 past the bay's edge), and **both horizontal
   holes had ceilings of 22–37° facets**. The lip is 8 mm; both holes are
   teardrops with a 45° point on top.

### The flange, and the version that would have hit the base

The first flange stood **1.6 mm proud of the face** to cover the base's
lip. Placed at its seat the way check2 places every diffuser, it overlapped
the base by **211 mm³** on the 24 and 233 on the 32: the lip is 0.07 mm
short of the face, not behind it. And face-down printing — the only way the
0.20 mm membrane prints — would have put the whole face 1.6 mm off the bed.
So it fills the trough instead: the face's front plane carries on outward
as one disc, 2.63 deep, to 0.30 short of the lip and 0.30 above the recess
floor, and nothing on it stands in front of the face. Inside the band it is
the numbered diffuser to the last triangle (0.00 mm³ of difference,
measured, membrane included). It stops at the lip and cannot go over it,
for the printing reason alone; that is why the answer to *"to the edge of
the base"* is *"to the lip"*, and the lip stays a hairline rim around it.

One probe of my own was wrong here too: the seated-overlap test first
reported 1.16 mm³ on the flange diffuser — and exactly 1.16 on the plain
numbered one. It was the collar's crush ribs biting the bore, which is the
press fit, and check2's number to own. The test looks only outboard of the
band now.

### Verification

Full rebuild through `python3 build_v2.py` (every part, all three bodies,
every one manifold and clean), then `./runchecks.sh` — all six passes,
all three bodies:

```
check1_topology.py     PASS 1: all topology checks clean
check2_fit.py          PASS 2: every fit and clearance check holds, on all three bodies
check3_print.py        PASS 3: prints without support in the stated orientation
check4_v3.py           CHECK 4: the diffuser checks out on all three bodies
check5_stand.py        CHECK 5: the clock sits in the stand and can be plugged in on a desk
check6_standbox.py     CHECK 6: the S3 lives in the stand, the clock leans back, the covers and diffusers fit
```

check6's numbers, measured on the STLs: bay 34.2 × 67.4 × 23.0 clear;
roof flat span 24.1 mm at 54.5° chamfers; tray 50.19 wide, sits on z = 0
with the lid reaching 27.00; 1.20 mm total bay clearance against 0.80
needed; both rails and both 5 mm hooks; USB window open; notch through the
roof with 0.0 mm³ in the way on every body; both pilots 10.0 deep with
100% solid around; tips forward past 21.0° and back past 34.7 / 31.5 /
21.2°; back cover 8.90 deep, notch open; plain = numbered + 66 / 95 / 215
mm³; flange 0.30 short of the lip, front at the face plane, 2.63 deep,
0.00 mm³ of overlap with the base seated, 0.00 mm³ different inside the
band. Solid volumes: stand-box 172 / 213 / 902 cm³, tray 9.9, back cover
28 / 34 / 123, flange diffuser 19 / 25.

Not verified: nothing printed. The 120 mm lead figure is from the model;
the M2-in-PLA pilot of 1.60 is the M3 rule scaled, not tested; a 24 mm
bridge and a 47° teardrop are the checker's rules, which have held on
every part so far but are rules, not prints. The renders
(`render_*.py`) do not draw the stand-box yet.

## 2026-09-03 — The dashboard was gated on an entity that does not exist, and clock 3

Sam: *"Flash the new firmware to both clocks now. Only clock 3 is plugged in
to my computer at the moment."* Then: *"Then update HASS with the settings
I've asked to add."*

### The gate

Every card in the generated Settings view carries a visibility condition on
`binary_sensor.<device>_status`, added a week ago so that a clock which is
absent hides its rows instead of drawing twenty "Entity not found" boxes.
The generator's own docstring said, in as many words, that this entity is
"the entity the ESPHome integration creates for every device it adopts".

It is not. `platform: status` is an opt-in ESPHome component (its
documentation page, checked today), and nothing in either firmware declared
it. So the entity never existed, and a `condition: state` on a missing
entity is false — meaning the whole Settings view would have rendered
**blank**. The mechanism that was supposed to hide one absent clock would
have hidden all of them, including the two that work.

Worth naming the shape, because it is the second time this project has been
bitten by it: the failure is silent and total, and it is *downstream of a
safety feature*. A gate that fails closed hides the thing it was protecting
as thoroughly as it hides the fault. The give-away was not on the panel —
the view has never been opened since the gate was added — it was a
generated-file validator that resolves every entity reference in the cards
against the entities the firmware actually creates. It had reported "0
dangling" before only because I had exempted the three `_status` refs as
"created by the integration". An exemption in a checker is a claim, and this
one was never verified.

Fixed by making the docstring true: the firmware declares

```yaml
binary_sensor:
  - platform: status
    name: "Status"
    entity_category: diagnostic
```

which gives exactly `binary_sensor.${device_name}_status`, and the
docstring now says where the entity comes from and that any clock added to
`CLOCKS` needs firmware that declares it.

### Clock 3

There is a third board on Sam's bench and nothing in this repo has ever
mentioned it, so the flash job sent to the bench session identifies the
board before writing to it: read the boot banner, and flash as clock #1 or
#2 if it names itself one of those, otherwise as `mini-round-clock-3` /
"Mini Round Clock 3" with `num_leds 24`. The 24 is only a compile-time
default — the ring size is a runtime number in Home Assistant with a
ceiling of 60 — so a wrong guess there costs a dropdown, not a reflash.

It is listed in `CLOCKS` and in the `input_select` options now. Listing a
clock that may not exist costs nothing precisely *because* the gate works:
its cards do not render until the device is on the network.

### Verification

`esphome config` valid on the full file (2026.6.5 in a throwaway venv here;
the bench runs 2026.8.1). The status sensor resolves with `device_class:
connectivity`. The generated view is 38 cards over 4 clocks, and all 303
clock entity references in it check against the 102 entities the firmware
creates: **0 dangling, with no exemptions**.

Not verified: the view has still not been opened in a browser. The flash of
round three was in flight when this was found, so the boards need one more
pass to pick the status sensor up — OTA, and queued behind the running job.

## 2026-09-03 — One aperture, on both clocks, and it is the die

Sam: *"Update the diffuser for the 32 and 24 clocks and make sure each of the
plain diffusers have the same size LED hole for the LED to shine through. They
are not even at the moment. And they can be slightly larger, each of the
holes."*

He is right, and it was measurable on the built files before anything was
changed — the opening at the membrane, taken off the mesh:

| | before | now |
|---|---|---|
| 24-LED | 4.74 × 1.43 mm | 5.02 × 1.82 mm |
| 32-LED | 4.44 × 1.43 mm | 5.02 × 1.82 mm |

They differed because each body solved for the longest tick **it** could
carry, and the two are bound by different things: the 24 by the screen window
inboard of the mark, the 32 by its own light-tight cell. "As long as this one
can manage" is a reasonable rule for one part and the wrong rule across a set.
Two clocks on one wall want one mark.

So the length is a constant now, and it is the emitter: a 5050 die is 5.00 mm
across, so the slot is exactly as long as the lit thing behind it. That is the
only length with a reason — shorter wastes die, longer is spill — and it lands
between the two it replaces. The growth Sam asked for is in the width, 1.40 →
1.80, where it actually shows.

**What gives way instead.** The mark is hardware and the typography is not, so
the causality is inverted from before: the tick is placed first, and the
numerals are solved DOWN from their nominal height until they clear it by
`NUM_MARGIN`. On the 24 that takes them from 5.00 to 4.92 mm — the floor where
a stem is still two clean 0.40 mm beads is 4.40, and it is an assert, not a
clamp. On the 32 nothing moves: its numerals were never the binding
constraint.

**What it costs on the 32**, and it is paid where it cannot be seen: its cell
has 6.02 mm between the ribs, so a 5.00 mm mark leaves 0.40 of standing rib at
each end rather than 0.70.

### The check earned its keep twice in ten minutes

check4 failed the first build, on two counts, and only one was the part's
fault.

- **"and centred on the LED circle"** — I had centred the tick on the CELL
  rather than the LED, to buy 0.10 mm of rib on the 32's tight side. The check
  was right to refuse it: a 5.00 mm slot over a 5.00 mm die is only exactly as
  long as the lit thing if the two share a centre, and that was the entire
  argument for the length. The tenth was not worth it. Centred on the LED, the
  rib is 0.61 inboard and 0.41 outboard, both over the floor.
- **"r=48.76 is 2.90 mm, outside the tick" — measured 4.556** — this one was
  the check's fault. It asked for *exactly* the face thickness at a point 0.60
  mm past the tick's end, and on the 32 that point now lands on the standing
  rib, which is thicker. What the assertion means is "the thinning is confined
  to the tick", and thicker does not violate it. It reads `>=` now, with the
  reason written next to it, and the rib's own continuity is checked
  separately two lines below so nothing is lost.

### Verified

All six checks pass on all three bodies. check4 measures the mark on the built
mesh: 5.00 radial × 1.80 tangential on both flat bodies, centred on the LED
circle, spill +0.00 at each end, membrane 0.200 mm inside it and full face
thickness outside, all 24 and all 32 cells present, cell walls continuous. The
opening measured independently off the STL section is 5.02 × 1.82 on every
diffuser variant of both clocks, numbered and plain alike.

## 2026-09-03 — Correction: the partial flush never drew anything, and that is the "slight screen flashing"

Sam: *"Update the clock to fix the slight screen flashing too."*

### What I got wrong last week

The build-log entry above, and a note in the vault, say that turning
`auto_clear_enabled` off gives the grow-clock eyes a 36 ms partial flush
instead of a 104 ms full one, and that this "is the difference between 10 fps
eyes and none". The dirty-window half of that is true. The conclusion is not,
and the eyes have never animated on the panel.

`mipi_spi` with a partial buffer does not run the display lambda once per
frame. It runs it **once per band** — six times down a 360-line panel at
`buffer_size` 1/6 — flushing each band's dirty rectangle as it goes. And when
a band comes back with nothing drawn in it, the driver does not skip that band:

```cpp
for (this->start_line_ = 0; this->start_line_ < this->get_height_internal();
     this->start_line_ = this->end_line_) {
  ...
  (*this->writer_)(*this);
  if (this->x_low_ > this->x_high_ || this->y_low_ > this->y_high_)
    return;                       // <-- the whole frame, not this band
```

An animation frame draws only the eye box, at y 66..244. The first band is
y 0..59. It came back empty, and `update()` returned before a single pixel
reached the panel. **Every partial frame was thrown away.** The face changed
only on the once-a-second full frame, which sweeps the panel band by band —
and a face that jumps once a second in a top-to-bottom sweep is exactly what
"the screen flashes a little" describes.

Verified on the version the clock actually runs: esphome **2026.8.1**,
`components/mipi_spi/mipi_spi.h`, read from the tag on GitHub, because this
container's Python is too old to install that release. The 2026.6.5 source in
a local venv says the same thing.

### The fix

One column of pixels at x = 0, the full height of the panel, drawn in the
**field colour**, on partial frames only:

```cpp
if (partial) {
  it.filled_rectangle(0, 0, 1, 360, field);
  it.filled_rectangle(CX - 124, 66, 248, 178, field);
}
```

Every band now has something in it, so no band aborts the frame. It costs 360
pixels and is invisible: x = 0 is the extreme edge of the panel, and it is
painted in the field's own colour rather than black — which matters, because
the "eyes on colour" face has a field that is not black, and a black column
there would have been a hairline down the left of the screen. The bar panel
gets the same, 170 tall.

The flush grows from the eye box (248 px wide) to x 0..304 in the bands the
eyes occupy, and one pixel wide in the bands they do not. That is about 23%
more than the box alone and roughly a third of a full frame.

### What this says about the earlier claim

The mistake was reading one half of a function and stopping at the part that
confirmed what I wanted. `update()` was read for its dirty-window logic, found
to have exactly the optimisation the design needed, and closed. The band loop
is nine lines above it. **A source read that stops when it finds the answer
it went looking for is a search, not a reading** — and the note it produced
was filed as "verified by reading the source", which is how it then got
believed twice.

### Verification

`esphome config` valid, and a full compile is recorded below. Not verified on
the panel: nobody has yet seen the eyes animate, which is the whole point of
the change, and it is the first thing to look at after the next flash.

## 2026-09-03 — Three clocks, one of them new; the panel in sections; and the LED that is a lamp

A long round with the bench session, and most of what it produced was
corrections to things this log already asserted.

### There are three boards, and the one on the desk is not clock #2

The board Sam plugged in tonight identified itself, was flashed as
`mini-round-clock-2`, and **Home Assistant refused to adopt it**: the MAC did
not match the one already registered under that name (new `ac:27:6e:a3:3b:ac`
against the existing `ac:27:6e:a4:cd:98`). It is a third physical board. It
was reflashed as `mini-round-clock-3` and adopted cleanly — 192.168.1.69, 32
LEDs, 102 entities, status sensor on.

Which means **the entry above claiming both boards were flashed and clock #2's
blank screen was resolved cannot be corroborated**. Clock #2 has been
unavailable in Home Assistant since 2026-08-31T23:53Z. Whatever was flashed
that day, the bench cannot reach it now.

**And the recorded addresses are dangerous.** 192.168.1.23 was clock #1; it
now answers on MAC `C4-E7-AE-16-6B-A6` with port 80 open and 3232/6053 closed.
Another device holds that lease. Flashing at a remembered address would have
pushed clock firmware at a stranger's hardware, and the bench was right to
refuse. HANDOFF.md now carries the addresses as dead, with the rule: check the
MAC or the mDNS name before an OTA, never the address alone.

### The gate I was so pleased with was not in the live view at all

The entry above says the settings view would have rendered blank because every
card is gated on a status sensor nothing declared. True of **this** repo's
generator. The live dashboard is a different one: when the bench ported the
grow-clock cards into Sam's sections layout it deliberately left `vis()`
behind, having spotted that gating would hide everything. So the live view has
42 visibility conditions and not one of them mentions the status sensor. The
"Entity not found" icons Sam is seeing are two offline clocks with nothing
hiding them, which is a different fault with the same fix.

### And the fix needed a second half

Gating alone replaces a page of yellow rows with **nothing**, and the bench
declined to paste it for exactly that reason: clocks 1 and 2 would vanish from
their own picker rather than read as unavailable. It was right, and the
refusal was worth more than compliance. Each clock now gets an `absent_card()`
on the opposite condition, saying it is not connected and why. Whether it
renders for a clock whose status entity does not exist *at all* is the one
thing that cannot be checked from here; the bench is looking.

### An instruction of mine inverted between writing and reading

I told the bench: if the two generators collide, keep yours and delete mine.
By the time it got there I had pushed a generator that was ahead of its own —
a real sections view, 39 card groups against 14 — so obeying me would have
deleted the better work. It read the diff, saw that, and stopped. Taken
literally it would also have dropped the `tier` mechanism and the Test Clock
entry, which only my side had.

The rule I should have written, and the one it acted on: **keep the layout
that is live, keep every feature either side has, and never resolve a
collision by deleting work you have not read.** An instruction about a merge
is written before you can see the merge.

### The LED is a lamp, and the number says so

*"The LED is too bright!"* — three times now. The ring brightness is a linear
multiplier straight onto the emitter, so 45 really is 45% of a 32-LED ring at
full tilt, which in a bedroom is a lamp and not a night light. Day 45 → 25,
grow ring day 45 → 25, grow ring night 12 → 7, and the step is 1 rather than 5
with the floor at 1: at 5% steps there were three positions below a quarter.

`restore_value` is true on all of them, so this is what a **fresh flash**
ships with. A clock already running keeps its stored value, which is why the
answer to "it is too bright right now" is the device page in Home Assistant,
not a reflash.

### Still open, and none of it can be settled from here

- **The flicker is on the ring AND the screen.** That is new information and it
  points away from the backlight PWM, which cannot affect the ring, and toward
  the 5 V rail: a 32-LED ring at 45% is ~0.9 A on top of the panel and the
  radio, and the build notes have the board powered from its own USB port. The
  decisive test is one click — switch the ring off and watch the screen.
- **The eye animation has still never been seen.** The band fix is flashed
  nowhere yet.
- **The packages cannot be installed.** 192.168.1.75 has 22 and 445 closed and
  only 8123 open, and the REST API has no file-write endpoint. It needs the
  Terminal & SSH or Samba add-on enabled, which is Sam's to do. Until then the
  clock picker's options are set at runtime and die at the next restart.

## 2026-09-04 — The repaint that had nothing to repaint

Sam, once the band fix was on the panel: *"The screen is now flickering the
graphics."*

That is mine. The band fix did not cause it, it **uncovered** it: while every
animation frame was being discarded by the driver, the panel only ever redrew
on the once-a-second full frame, and the second fault could not show. The
moment those frames started arriving, it did.

The 100 ms animation interval repainted **whether or not anything had moved**.
The animator spends far longer holding a resting pose in an idle gap than it
does inside a clip, so most of those repaints drew the identical eye box over
the identical eye box — six lambda passes and four banded flushes each time,
roughly 60 ms of SPI, ten times a second, to change nothing. On the panel that
is the graphics flickering.

The frame is skipped now unless the pose has actually changed: gaze, both
lids, the smile, the height scale, the yawn, and the z-drift quantised to 8
steps a cycle so it does not tick on its own ten times a second. Thresholds
are below what a pixel can show. Through an idle gap nothing is drawn at all;
inside a clip it runs at the full rate.

Two details that are easy to get wrong and are worth the words:

- The recorded pose is set **after** the update, not before, so a frame that
  never reached the panel is not recorded as shown.
- A **full** frame records it too. A full frame repaints the eye box as well,
  so the next partial frame is correctly skipped — and recording it means
  that staying correct does not depend on anyone remembering that.

```
RAM:   [==        ]  18.9% (used 61924 bytes from 327680 bytes)
Flash: [======    ]  60.9% (used 1116707 bytes from 1835008 bytes)
```

0 errors. Up 128 bytes of RAM on the previous build, which is the eight
globals. Not seen on the panel yet. The immediate workaround, and it is a
real one, is the **Grow clock animate** switch: off, there are no partial
frames at all.

**Not a bug, reported the same minute:** the grow clock handing the panel back
to the ordinary clock during the wake window is `Grow clock clock by day`
doing exactly what it says. It defaults off. Sam found the switch himself
before this could be read out of the code.

### The shape of both of these

Both faults were one layer below where the symptom pointed, and the second was
hidden behind the first. A driver that silently discarded work made a wasteful
caller invisible; fixing the driver made the caller's waste the loudest thing
on the panel. Worth expecting the pattern rather than being surprised by it:
**when a fix reveals a new symptom immediately, the first suspect is not the
fix but whatever the old behaviour was masking.** The instinct to revert would
have restored a screen that was calm because it was broken.

## 2026-09-04 — The drawing ran outside the region it declared

Sam, after the dirty check: *"It still flickers on the animations."*

Which was the right report, because the dirty check only stops repaints when
nothing has moved. During an actual clip it still repaints, and the flicker
was in the repaint itself.

**The smile is a circle that bites the eye from below.** Radius 0.9 of the
eye's width, centre *below* the eye, so most of the circle falls outside it:

| pose | circle spans | eye box | on the panel at those rows |
|---|---|---|---|
| awake resting, smile 0.35 | y 172 – **316** | 66 – 243 | countdown at 252, **time at 300** |
| full grin, smile 1.0 | y 115 – 259 | 66 – 243 | countdown at 252 |

The animation frame declares the eye box, `CX-124, 66, 248, 178`, and then
drew 73 px past the bottom of it in field colour. So every animation frame
erased part of the countdown and the digital time, and the once-a-second full
frame put them back. The time was being blanked and repainted at the
animation rate. The bar panel had it too, over its own time readout.

The bite is drawn as horizontal spans clipped to the eye now, so it cannot
reach past what it is biting. `std::max(cy - h/2, yc - Rb)` to
`std::min(cy + h/2, yc + Rb)`, one `filled_rectangle` per row.

### Three faults, one shape

This is the third in a row and they are all the same mistake wearing
different clothes:

1. The driver discarded any frame with an empty band — **a promise about what
   would be drawn, silently broken by the caller.**
2. The animation repainted when nothing had changed — **a claim that
   something needed drawing, which was not true.**
3. The smile drew 73 px outside the box the frame declared — **a region
   declared to the driver and then not respected by the drawing.**

Every one is the boundary between "what I said I would draw" and "what I
drew", and nothing in the code was checking that boundary. The eye box is a
promise to the driver, and until tonight it was only ever a comment. If
anything still flickers, that is where to look next: for anything else the
animation draws outside the rectangle it names.

**And the ordering mattered.** Faults 2 and 3 were both invisible while fault
1 was discarding the frames. Fixing the driver did not cause them; it
published them. A fix that immediately produces a new symptom is usually a
fix that has stopped hiding something.

Verified: `esphome config` valid, and a full compile:

```
RAM:   [==        ]  18.9% (used 61924 bytes from 327680 bytes)
Flash: [======    ]  60.9% (used 1116983 bytes from 1835008 bytes)
```

0 errors. RAM unchanged and 276 bytes of flash for the span loop, replacing
one `filled_circle` call with a bounded one. Not seen on the panel yet.

## 2026-09-04 — Third diagnosis, and the first one that came from the driver rather than the screen

Sam, after the smile clip was flashed: *"The animation still flickers and so
does the time."*

Two wrong diagnoses preceded this one, and both were argued from what the
panel looked like. The backlight PWM could not have been it, because the ring
flickers too. The smile overdraw was real — it genuinely drew outside its box
— but it was not the cause. This one came from reading
`draw_absolute_pixel_internal` and `fill` in `mipi_spi.h`, and the tell that
it is right is that it explains the detail the other two could not: **why the
TIME flickered rather than the eyes.**

### The mechanism

The driver tracks a dirty rectangle widened one pixel at a time, and flushes
**that whole rectangle** out of the buffer. The buffer is one band tall,
reused for all six bands of a frame, and with `auto_clear_enabled: false` it
is never cleared. So every pixel inside the flushed rectangle that was not
written on this pass is sent to the panel as whatever the buffer held — which
is a *different horizontal slice of the screen* from the previous pass. Not a
stale copy of the same region. The wrong region.

**A dirty rectangle is a bounding box, not a set.** Draw two small things far
apart and you have promised the driver everything between them.

And the thing that carried this onto Sam's clock face was my own fix from two
hours earlier. The one-pixel marker column at x = 0, added to stop the driver
abandoning frames on an empty band, forced `x_low_` to 0 on every band. On the
band that straddles the bottom of the eye box, the flush then ran from x 0 to
the box's right edge and from y 240 down to 299 — across the top of the
digital time at y 300 with its 48-pixel font. Every animation frame wrote
garbage over the top of the time; the once-a-second full frame put it back.

### Why drawing more carefully cannot fix it

Every candidate ran into the same wall. Keeping the empty bands alive requires
drawing *something* in them, and anything drawn outside the region of interest
widens the box past what was drawn. Making the drawn set equal its own
bounding box means drawing a full-width strip — and then there is nothing
partial left to save. When every repair widens the same contradiction, the
optimisation is unsound rather than buggy.

### So animation frames are full frames

`it.fill()` writes every pixel of the band and sets the box to the whole band,
so nothing stale can survive. What pays for it:

- **the dirty check** — nothing is drawn at all unless the pose has moved, and
  the animator holds still between clips;
- **a 200 ms floor** between repaints, while the animator keeps stepping at
  100 ms so the interpolation stays smooth.

The guards that read `an_partial` are left in place and the global carries the
whole reasoning, so the next person to have this idea finds the note attached
to the thing they would touch.

```
RAM:   [==        ]  18.9% (used 61924 bytes from 327680 bytes)
Flash: [======    ]  60.9% (used 1116943 bytes from 1835008 bytes)
```

0 errors. **Not flashed at time of writing, deliberately** — Sam has already
spent one flash on a wrong fix of mine, and the ring-off test (switch the ring
off, watch the screen) is still unrun and still the fastest way to find out
whether any of this is the display at all.

## 2026-09-04 — Animate off is clean, so the sweep is the whole story

Sam ran the discriminating test at last: **"Turned animate off, doesn't
flicker."** Two things follow, and between them they close the diagnosis.

**A redraw of unchanged pixels is invisible.** With animate off the dispatcher
still repaints the entire panel every second — the 1 s interval calls
`component.update` unconditionally, which my animation throttle never
controlled and which is why turning that dial to 2000 ms changed nothing.
Sixty full repaints a minute, and the screen is steady. So the six-strip
write is not visible in itself.

**What is visible is the changed region, and how long it takes to arrive.**
Any change to the face is written to the glass in six strips, top to bottom.
At 20 MHz a 360 x 360 frame is 104 ms of SPI before the drawing is counted,
so an eye that moves takes the better part of a fifth of a second to finish
moving, in strips. Frequent small changes read as constant sweeping; the
2000 ms throttle made each change bigger and more abrupt instead, which is
worse, not better — at that rate a blink is never caught in the act, only
jumped over.

So the earlier "frames are overlapping" story was wrong twice over: the
frames were not overlapping, and the 1 Hz repaint I did not know about was
doing more redrawing than the animation ever did.

### The only lever left, and it is a one-liner

`data_rate` on the round panel was **20MHz**, with a comment on it reading
"50MHz is what xboot uses; 20 is a safe first pass". It has been the safe
first pass since August. The **bar panel on the same bus has run at 40MHz
since the day it was added**, and the vendor driver drives this controller at
50. Raising the round panel to 40 halves every flush and therefore halves the
sweep.

That is a mechanism rather than a hope, and the revert is the same line back
to 20MHz if the panel garbles or the boot banner repeats.

```
RAM:   [==        ]  18.9% (used 62012 bytes from 327680 bytes)
Flash: [======    ]  60.9% (used 1117091 bytes from 1835008 bytes)
```

0 errors.

### What is actually fixed, and what is a limit

Fixed and confirmed on the panel: the backlight flicker (PWM 1 kHz to 5 kHz),
the digital time being erased every animation frame (the stale-pixel bug), and
the eye animation never drawing at all (the band-abort). **Not a bug:** a face
that changes takes a visible moment to change on a panel with no working PSRAM
and a sixth of a frame in memory. 40 MHz halves it. Nothing in software
removes it.

The honest fallback, and it works today: **Grow clock animate** off gives a
still face and everything else — the sky, the stars, the countdown, the
colours, the time — with no flicker at all.

---

## 2026-09-04 — The supply, at last: a 32-LED ring on a PC USB port

Six firmware theories about the flicker, five of them wrong, and the thing
none of them touched was the wall socket. Asked what was powering the board,
Sam answered: **"It's plugged into a USB port on my PC."**

That is not a detail. Here is the arithmetic that should have been done on day
one, and was not:

| draw | current |
| --- | --- |
| WS2812B, per lit channel at full | 20 mA |
| ...so one pixel at full white | 60 mA |
| **32 pixels, full white** | **1920 mA** |
| 32 pixels, white, at the shipped 25% brightness | ~480 mA |
| ESP32-S3, WiFi associated, average | ~100 mA |
| ESP32-S3, WiFi transmit burst (~1 ms) | 350–500 mA |
| Panel backlight at full | ~60–120 mA |

Against that: a **USB 2.0 port is specified at 500 mA**, a USB 3.0 port at
900 mA. A dev board also drops ~0.3 V across its input protection diode, and a
thin 1 m USB cable drops more again under load. So the rail at the ring can be
well under 4.5 V while the port is still nominally "working" — ports sag long
before their polyfuse trips.

A sagging rail does not look like a power fault. It looks like **the ring and
the screen dimming together, in step with whatever is drawing most at that
moment** — which, on this clock, is an animation frame: a 40 MHz SPI burst and
a fresh set of pixels at the same instant.

This is a *hypothesis*, not a finding, and it is written down as one. What
makes it worth acting on is that it is the only candidate never excluded, it
explains the one thing no renderer theory ever did (why the **LED ring**
flickers too), and it is falsifiable in ten seconds with no hardware.

### The two tests, cheapest first

1. **Turn off "Ring LEDs" in Home Assistant** and watch the animation. That
   drops the ring from a few hundred mA to its quiescent ~32 mA and changes
   nothing else. Screen steadies → the rail. Screen still flickers → not the
   ring's current, and the freeze switch from the previous build says whether
   it is the content or the act of writing.
2. **Move the board off the PC to a 5 V 2 A supply** (a phone charger, same
   cable) and re-check with animate on.

### The limiter, which the clock should have had regardless

Independently of how the tests land, a ring that can ask for 1.9 A with no
notion of a budget is a defect. Added a **"Ring current limit"** number, in mA,
default 400, 0 to disable. Every frame, immediately before the lambda returns,
`cap()` sums the channels it is about to write, converts at 20 mA per channel,
and if the total is over budget scales the whole ring by one multiply. Same
idea as WLED's automatic brightness limiter.

It reads the strip back rather than the compositing buffer, because grow mode
writes `it[]` directly and never touches `buf` — the buffer is not the whole
truth. Three call sites: the wake-effect return, the grow-plain return, and the
end of the face path. Quiescent draw is left out of the sum on purpose: it
cannot be scaled away, so counting it would only clamp harder for nothing.

Suggested budgets: **350 mA on a PC USB 2.0 port, 600 on USB 3.0, 1500+ on a
proper supply.** Note that at 25% brightness an ordinary clock face is nowhere
near any of these — the limiter only bites when the ring goes bright and wide,
which is exactly the grow clock's wake sparkle.

```
RAM:   [==        ]  19.0% (used 62276 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1118671 bytes from 1835008 bytes)
```

0 errors. Compiled, not just `esphome config`-ed — the change is in a lambda,
and `config` never compiles lambdas.

---

## 2026-09-04 (later) — "The eyes aren't flickering, but the sun and clock are"

That sentence falsifies the supply theory in one line. A sagging 5 V rail dims
the whole panel through a single backlight PWM channel; it cannot pick out the
sun and leave the eyes alone. **Spatially selective flicker is content.** The
limiter from earlier today stays — a ring that can ask for 1.9 A with no budget
is still a defect — but it is not the flicker, and the build log should not
pretend otherwise.

### Reading the driver instead of guessing again

Checked, in 2026.6.5 source, every step of the partial path:

* `start_clipping(left, top, right, bottom)` → `Rect(56, 0, 248, 244)`, so the
  clip is x 56–303, y 0–243. CX/CY are 180, the sun sits at (180, 42) with rays
  to r=22, the eyes at y 90–202. **Both are inside the clip.**
* `mipi_spi::fill()` **is** overridden — but it checks `get_clipping().is_set()`
  and falls back to `display::Display::fill()` when a clip is active. So a
  clipped fill really does touch only the clip.
* `draw_pixel_at` rejects out-of-band pixels *before* widening the watermark, so
  each band's dirty rectangle is honest.
* The band abort (`x_low_ > x_high_ → return`) fires only on band 5, which is
  last, so nothing is lost.

The partial path is sound. Which means the renderer cannot be treating the sun
and the eyes differently, and I could not explain the symptom from it. Six
theories in, that is the point to stop theorising.

### What the reading did turn up, and it is not small

The 1 s dispatcher ended with an **unconditional** `component.update`. Every
second. Always. And a full frame has no clip, so `fill()` takes its fast path:
wipe the band buffer, mark the **entire band** dirty. So every one of those
pushed the whole panel down the bus — **259,200 bytes, ~52 ms at 40 MHz, at a
panel that refreshes in about 16** — sixty times a minute, on a screen where
between one second and the next almost nothing changes.

It is also **the only path that draws the time**, since the time sits below the
animation clip. Sam reports the time flickering. That is at minimum a strong
coincidence, and at best the whole answer.

### Repaint on change, not on the tick

The dispatcher now hashes everything a full frame draws that an animation frame
does not — field colour, the star row (the *count* lit, not `grow_frac`, which
slides every second), the countdown, the digital time — and repaints only when
that key moves. The eyes, z's, sky and "shh" are deliberately **not** in the
key: they are inside the clip and the partial frames own them, so hashing them
would repaint the whole panel on every blink, which is the behaviour being
removed.

Gated in grow mode only — the ordinary face has a second hand and has earned
its second. A **10 s floor** underneath: if the key is ever missing an input the
panel goes stale for ten seconds rather than forever. A bounded bug instead of
an unbounded one.

In grow mode this takes the panel from **60 full repaints a minute to about 1**.

### The A/B, so this is a test and not another assertion

New switch **"Grow clock repaint every second"**, default off (= the fix), on
= the old behaviour. Flip it and compare on the glass in a few seconds, no
reflash. Together with "Freeze the eyes" and the "Frame time" sensor already
flashed, that is a 2×2 that isolates full frames from partial frames:

| animate | repaint every second | what it means if it flickers |
| --- | --- | --- |
| off | on | full frames alone |
| on | off | partial frames alone |
| on | on | current behaviour |
| off | off | neither — something outside the renderer |

```
RAM:   [==        ]  19.1% (used 62460 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1119603 bytes from 1835008 bytes)
```

0 errors, compiled.

---

## 2026-09-04 (later still) — "I feel like the first version worked"

Sam's best clue of the whole saga, and it is a bisect rather than a theory. So
I went and read the first version instead of inventing a ninth explanation.

`7776635`, the first animator, drew its animation frame as:

```cpp
if (partial) it.filled_rectangle(CX - 124, 60, 248, 184, field);
```

**Starting at y = 60.** Band 0 is y 0–59. So band 0 always came back empty, and
`mipi_spi::update()` **returns from the whole frame** on the first empty band.
Not one animation frame ever reached the glass.

That is why the first version worked. The panel was repainted **once a second,
by one path, cleanly**, and the eyes moved at 1 fps. It also had no sky: the
face styles were `"eyes"` and `"eyes on colour"` — `"eyes and sky"` did not
exist yet. There was no sun to flicker.

Everything since has been me adding a second writer to a panel that was only
ever quiet because the second writer was broken.

### The asymmetry, at last

I could not explain from the code why the sun flickered and the eyes did not,
because **mechanically it doesn't** — both sat inside the animation clip and
both were erased and repainted identically. The difference is not in the
driver, it is perceptual:

> **Repainting something that has not changed is what reads as a flicker.**

The eyes get away with it because they are supposed to move — an erase and a
repaint reads as animation. The sun does not move. Erasing it to the field
colour and painting it back about twice a second, forever, reads as a fault.
Same for the digital time, which the 1 s full frame was rewriting unchanged
sixty times a minute.

Every previous fix asked "is the repaint correct?" — and after the clip work,
it was. The right question was "why is it repainting at all?"

### The fix

The animation box now starts **below the sky**, and the sky is drawn by full
frames only:

* `it.filled_rectangle(CX - 124, 68, 248, 176, field)` — was the whole clip
  from y = 0.
* `if (sky && !partial)` — an animation frame neither erases nor repaints the
  sun, so it just stays on the glass. It changes only when the state does, and
  `st` is in the full frame's content key, so the change still lands at once.

**y = 68 is derived, not chosen.** The sun's lowest ink is a ray tip at y = 64
and the half-sun's eraser rectangle reaches y = 67. The highest the eye can
ever reach is y = 72 — gaze −9, squash 1.15, less the one-pixel lid overhang.
68 is the only clean lane between them, with 4 px of margin over the eye.

**Band 0 still has to be kept alive**, or we are back to the first version
silently discarding every frame. One pixel does it:
`it.draw_pixel_at(CX - 124, 0, field)`. A single pixel, so that band's dirty
box is that pixel and nothing else — unlike the marker *column* I tried in
`6702d52`, which forced `x_low` to 0 on every band and dragged the flush across
the clock's time. (56, 0) is 219 px from the centre of a 360 circle, so it is
off the visible glass entirely.

**And `filled_rectangle`, not `fill()`.** `Display::fill()` is
`filled_rectangle(0, 0, w, h)`, so under a clip it walks all 129,600 pixels of
the panel and discards seven eighths of the work — per band, six times a frame.
The rectangle walks 43,648 and keeps them. Same change on the bar panel.

```
RAM:   [==        ]  19.1% (used 62460 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1119643 bytes from 1835008 bytes)
```

0 errors, compiled.

### What is now repainted, and how often

| | before today | now |
| --- | --- | --- |
| digital time | 60 x / min | on the minute |
| sun / moon | ~100 x / min | on a state change |
| star row, countdown | 60 x / min | on change |
| eyes | ~100 x / min | ~100 x / min (they move) |

Nothing on that screen is now redrawn unless it has changed.

---

## 2026-09-04 (06:05) — The instrument I should have built first, and a revert

Sam: "The sun and the clock are still flickering." Before writing another line
I checked what was actually on the clock. The bench session had not moved since
05:53:57 — `c635533` probably had not finished flashing and `fd8efee` certainly
had not. **He was reporting on firmware that predated the fix being discussed,
and neither of us had any way to know.**

That has now happened at least twice, and it is not a display bug. It is a
missing instrument, and it is mine to have missed.

### Firmware built

A `text_sensor` publishing `__DATE__ " " __TIME__` — filled in by the compiler,
so it cannot drift from the binary the way a hand-maintained version string
can. It appears in Home Assistant as **"Firmware built"** and is on the
settings page. **Read it before reporting a symptom.**

### The round panel goes back to 20 MHz

And on the flicker itself, the strongest remaining lead is a revert, not an
addition. `6c5e232` raised the round panel from **20MHz to 40MHz** as a
speculative flicker fix. Every build Sam remembers as working ran at 20.

The symptom profile fits a marginal SPI clock better than anything else I have
considered:

* **Fine detail corrupts visibly.** The sun's rays are 1 px lines; the time's
  digits are thin strokes. A dropped or mistimed bit shows immediately.
* **Solid blocks do not.** A wrong pixel inside an 80×112 eye is one wrong
  pixel in a field of identical ones. Invisible.
* Which is precisely "the eyes aren't flickering, but the sun and clock are" —
  the one detail no rendering theory ever explained, and the reason I kept
  looking for a *structural* difference between the sun and the eyes when the
  real difference is that **one is drawn in thin strokes and the other isn't.**

My argument for 40 was that the bar panel runs at 40 and xboot drives this
controller at 50. Both true; neither is evidence about **this link**. Signal
integrity is a property of the wiring, not the chip, and this is a dev board on
jumper wires with a GC9B72 init sequence that was reverse-engineered rather
than taken from a datasheet. There was never a spec basis for 40.

Now a substitution, so it is one flag to A/B without editing:

```
esphome run ... -s lcd_hz 40MHz     # back to the fast one
```

Default is `20MHz`. The bar panel keeps its own 40 — different controller,
different flex, and it has never been reported as flickering.

```
RAM:   [==        ]  19.1% (used 62524 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1119923 bytes from 1835008 bytes)
```

0 errors, compiled.

### The order to test in

1. Check **"Firmware built"** matches the build being discussed. If it does not,
   stop — the report is about something else.
2. Sun and time steady at 20 MHz with animation on? Then it was the SPI clock
   and everything since `6c5e232` was chasing a hardware margin with software.
3. Still flickering? Then `-s lcd_hz 40MHz` to confirm it makes no difference
   either way, and the clock is exonerated.

### Verified: 40 MHz was double the tested ceiling

Rather than leave "no spec basis for 40" as a hunch, went and looked. The
**Arduino_GC9B72** library — written for this exact panel, a 2.1-inch 360×360
round SPI TFT — says, verbatim:

> "The controller handles fast SPI (tested up to ~20 MHz on short leads); if you
> use long/breadboard jumpers and see **speckle**, lower the clock via
> `gfx->begin(<hz>)`."
>
> — https://github.com/MaliosDark/Arduino_GC9B72

Three things fall out of that:

1. **~20 MHz is the ceiling on SHORT leads.** I ran it at 40 — double — on a dev
   board with jumper wires.
2. **For jumper wiring the advice is to go BELOW 20, not above.** So if 20 still
   misbehaves on Sam's wiring, the next step is *down*: 10 MHz.
3. **The named failure mode is "speckle."** Scattered wrong pixels. That erases
   1 px sun rays and eats the thin strokes of digits, and is invisible inside an
   80×112 solid eye. It is the symptom, described by someone else, before I ever
   saw it.

This reframes the whole day. `6c5e232` is not a fix that failed to help — it is
a change that made the panel worse, shipped in the middle of a hunt for why the
panel was misbehaving, on an argument ("the bar runs at 40, xboot uses 50") that
was about other hardware entirely. Every subsequent renderer theory was
explaining a symptom I had introduced two commits earlier.

The rule this earns: **when a knob has a documented safe range, find the
documentation before turning it, not after the symptom fails to go away.** And
when the argument for a change is "something else runs at this speed", that is
not evidence about the link in front of you.

---

## 2026-09-04 (13:40) — 20 MHz did not fix it. Stop theorising, freeze the panel.

Sam flashed c491474 and the flicker is unchanged. So the SPI clock is not it
either — or at least not on its own. Two things follow, and the second matters
more than the first.

**First, the record.** The library figure was real and worth acting on: 40 MHz
was double the documented ceiling for this panel and should never have been
set. Reverting it was correct. It was not the flicker. Both of those are true
at once and the build log should not quietly drop the second half.

**Second, I checked the one piece of flush arithmetic I had never read.**
`round_buffer(size)` is `ceil(size/ROUNDING)*ROUNDING`, and this config sets
`draw_rounding: 1`, so it is the identity. There is no alignment expansion
turning a small dirty box into a large one. That kills the last structural
theory I had.

### The state of the evidence

| observation | kills |
| --- | --- |
| eyes steady, sun + time flicker | anything uniform (supply, backlight) |
| ring off, still flickers | ring current |
| 40 MHz flickers, 20 MHz flickers | SPI clock alone |
| sun no longer drawn on animation frames, still flickers | the animation frame drawing it |
| `round_buffer` is the identity | dirty-box expansion |
| partial path verified line by line in the driver | the partial flush |

Nine theories. Three real bugs fixed, one real mistake of mine reverted, and
the flicker is exactly where it started. At that point another theory is not
worth having.

### Screen freeze

New switch, **"Screen freeze (test)"**. With it on the dispatcher stops calling
`component.update` on the panel entirely — no full frames, no animation frames,
not one byte down the SPI bus. The last picture drawn stays on the glass.

* **Still flickers with it on** → nothing the firmware draws is responsible,
  because nothing is being drawn. It is the panel, the wiring or the backlight,
  and I stop editing the renderer for good.
* **Goes still** → it is in what we write, and the frame-time sensor and the
  repaint switch narrow it from there.

It overrides everything, including the 10 s floor and the non-grow path that is
otherwise never gated. Leave it off for normal use: with it on the clock never
updates again.

This should have existed nine theories ago. Every instrument I have added today
— the freeze, the frame timer, the build stamp — has been worth more than the
fix it was attached to, and each one was added late, after another round of
guessing had already been spent.

```
RAM:   [==        ]  19.1% (used 62596 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1120059 bytes from 1835008 bytes)
```

### Two tests that need no flash at all

Both use switches already on the clock:

1. **"Grow clock use the ordinary clock by day"** — if that is ON and it is
   daytime, the screen is showing the ORDINARY clock face, there are no eyes on
   it at all, and the panel gets an **unconditional full 360x360 repaint every
   second**. At 20 MHz that is ~104 ms of SPI per second, sweeping the glass.
   The content-key gate from `c635533` only covers grow mode, so this path was
   never gated — and dropping to 20 MHz **doubled** its cost. Turn it off and
   look again.
2. **"Grow clock animate"** off, on the eyes-and-sky face. A completely static
   picture. If that flickers, the renderer is already exonerated before the
   freeze switch arrives.

---

## 2026-09-04 (14:30) — "The zzz's don't flicker, neither do the eyes or time"

The best diagnostic sentence of the whole build, because it is a list of what
is *working*. Line that list up against the panel's six bands:

| element | band | repainted each animation frame? | flickers |
| --- | --- | --- | --- |
| eyes | 1–3 | yes, inside a filled rectangle | no |
| z's | 1–2 | yes, inside a filled rectangle | no |
| time | 5 | no — and band 5 is drawn on not at all, so the driver aborts it cleanly | no |
| **sky** | **0** | **no — band 0 got ONE lone marker pixel** | **yes** |

The sun/moon is the only element in band 0, and band 0 was the only band doing
a degenerate 1×1 window write on every animation frame. Everything that
survives is repainted inside a rectangle that is exactly its own bounding box.
The one element left to persist on its own is the one element that flickers.

### fd8efee had it backwards, and this reverses it

That commit's reasoning was "repainting something that has not changed is what
reads as a flicker", so it pulled the sky out of the animation box and left it
to persist between full frames. It sounded right. It is wrong on this panel:
with an uncleared shared band buffer, **the safe state is a full, honest
rectangle per band — persistence is the fragile thing, not repaint.**

* `filled_rectangle(CX - 124, 0, 248, 244, field)` — the whole clip again, so
  band 0 is entirely covered by drawn pixels.
* The lone marker pixel is **gone**. It is not needed once band 0 is genuinely
  painted, and it was the only thing making band 0 unlike every other band.
* `if (sky)` — the sky is repainted every frame, exactly like the z's and the
  eyes, the two things confirmed steady.

Bands 1–3 carry the eyes, band 4 takes the last four rows, band 5 stays
untouched so the time below is safe. That is the arrangement the working
elements already had; the sky now shares it.

```
RAM:   [==        ]  19.1% (used 62596 bytes from 327680 bytes)
Flash: [======    ]  61.0% (used 1120023 bytes from 1835008 bytes)
```

0 errors, compiled.

### The lesson worth keeping

I spent the day asking "what is wrong with the thing that is broken?" The
answer came from asking the opposite: **what do the working parts have in
common, and is the broken one arranged the same way?** It was not. Three
elements shared a treatment and behaved; one had its own treatment — which I
had given it, that morning, as a fix — and misbehaved.
