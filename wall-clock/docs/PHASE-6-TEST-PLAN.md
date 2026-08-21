# Phase 6 — Test Plan

Run these **in order**. Each stage assumes the one before it passed. The whole
point of the ordering is that nothing expensive is ever powered by something
untested, and nothing goes on the wall until it has run for a day on the bench.

Tick the boxes as you go — this doubles as the record of what was actually
proven versus assumed.

---

## Stage 0 — Before anything is powered

- [ ] **Check the PSU polarity with a multimeter before it touches the build.**
      2.1 mm barrel, should be **centre positive**. The Core Electronics
      `AM8911B` is specified centre-positive; a reversed supply will kill the
      ring and the ESP32 in about a second. Measure, don't assume.
- [ ] Confirm the ring is the part you think it is: **measure OD and ID with
      calipers** and put the real numbers in `enclosure/params.py`.
- [ ] Count the LEDs. Confirm 60.
- [ ] Identify the ring's **DIN** pad (data *in*), not DOUT. Rings are marked
      inconsistently; if there is an arrow, it points away from DIN.
- [ ] Continuity-check your harness before it is connected at both ends:
      5 V, GND and DATA each end to end, and **no continuity between 5 V and GND**.

> **Wiring order, every time:** ground first on, ground last off. The DIN
> threshold is referenced to the ring's ground — without a shared return there
> is no defined logic level.

---

## Stage 1 — Bench PSU, ESP32 only, no LEDs

Set the bench supply to **5.0 V, current limit 300 mA**. An ESP32-S3 idles well
under 100 mA with WiFi up; if it trips a 300 mA limit, something is wrong and
you want the supply to stop rather than the magic smoke to start.

- [ ] Flash over USB **with the bench supply disconnected.**

> **Never USB and the PSU at the same time.** Espressif is categorical:
> *"The power supply must be provided using one and only one of the options
> above, otherwise the board and/or the power supply source can be damaged."*
> Flash once over USB, then use OTA for everything after.

```bash
esphome config  wall-clock.yaml     # schema check — do this FIRST
esphome run     wall-clock.yaml     # compile + flash + tail the log
```

`esphome config` has **not** been run by anyone yet. Expect it to be the first
thing that finds a problem, and that is exactly what it is for.

### What a good first boot looks like

Watch for these, in roughly this order. Component tags are stable; exact
wording varies by version, so match the **tag and the meaning**, not the string:

- [ ] `[I][app]` — ESPHome version banner, should say **2026.8.0**
- [ ] `[C][wifi]` config dump, then a connected message with an **IP address**
- [ ] `[C][esp32_rmt_led_strip]` — the strip component sets up.
      **If you see `Channel creation failed` here, that is RMT exhaustion, not
      a wiring fault** — it fails at setup, it does not manifest as flicker.
- [ ] `[C][api]` — API server starts
- [ ] `[C][homeassistant.time]` / a time-sync line once HA connects
- [ ] `Boot: ring on, Face effect selected` — the explicit log line from
      `on_boot` in the config. If this is missing, the effect was not selected
      and the ring will stay dark no matter what else is right.

### Red flags

- [ ] **No boot loop.** If the version banner repeats every few seconds you are
      in a reset loop — almost always brownout. Go back to the supply.
- [ ] No `Components should block for at most 30 ms` warnings.
- [ ] No `WARNING Recovered from bad state` messages.

---

## Stage 2 — Bench PSU + a SMALL test ring

Use one of the spare small circles, not the 60. Set `num_leds` in the
substitutions to match (12 / 16 / 24 — the render adapts).

Current limit: **LEDs × 60 mA + 150 mA**. For a 24-ring that is **1.6 A**.

- [ ] Fit the **470 Ω resistor in the data line at the ring end**, not the ESP32
      end, and the **1000 µF capacitor across the ring's 5 V/GND at the ring**.
      Fit the cap *before* first power-up, not after.
- [ ] Power the ring **before** the ESP32. Otherwise it back-powers
      parasitically through the data pin and can damage the MCU.

### Set `Mode` to `test chase` in Home Assistant and confirm

- [ ] Exactly **one white pixel** walks steadily around the ring.
- [ ] It goes **clockwise**. If it goes anticlockwise the ring is wired in the
      opposite direction — see troubleshooting.
- [ ] **One red pixel** marks the computed 12 o'clock.
- [ ] The white pixel is **white**, not yellow/cyan/magenta → colour order.
- [ ] The red pixel is **red**, not green or blue → colour order.
- [ ] Note **where the red pixel physically sits.** That is what
      `twelve_oclock_offset` exists to correct.

### Then set `Mode` back to `auto`

- [ ] Three hands are distinguishable: **amber hour** (wide), **blue minute**,
      **grey second**.
- [ ] The second hand advances once per second, smoothly, no stutter.
- [ ] Twelve dim markers are visible behind the hands.
- [ ] Cross-check against a phone clock: the hour hand should sit between hour
      marks as the hour progresses, not jump.

---

## Stage 3 — Full 60-LED ring, still on the bench

Change `num_leds` to `60`, re-flash, current limit **4 A**.

### Measure the current and check it against the model

The model is `I = 60 + 3600 × duty` mA. Set `Brightness` in HA and read the
bench supply:

| Brightness | Predicted (ring only) | Measured |
|---|---|---|
| Typical clock face (~15 px lit) | ~0.96 A | ______ |
| 55 % (the default) | ~2.04 A | ______ |
| 100 % | ~3.66 A | ______ |

- [ ] Measured values are **within ~25 %** of predicted. Substantially lower is
      fine and expected — it means you received WS2812B-**V5** silicon, which
      specifies 36 mA/LED rather than the 60 mA the model assumes.
- [ ] Substantially **higher** is not fine. Stop and investigate.
- [ ] With everything off, the ring still draws **40–60 mA**. That is the
      per-LED standby current and is normal — the ring is never truly off.
- [ ] Nothing is warm to the touch after 10 minutes at 100 %.

> `Brightness` is a **comfort** setting, not a safety mechanism. The 4 A supply
> covers the 3.78 A absolute worst case on its own. That is deliberate: a
> firmware bug must not be able to become an electrical problem.

---

## Stage 4 — Home Assistant, end to end

### Install the package

- [ ] Entity IDs filled in — see `homeassistant/INSTALL.md`. Do this first;
      everything below fails confusingly if the timer names are wrong.
- [ ] `python3 homeassistant/test/check.py` passes.
- [ ] `ha core check` passes on the HA box.
- [ ] `ha core restart` — **a restart, not a reload, for the first install.**
      `reload_all` cannot bootstrap `timer:` or `intent_script:`.

### Confirm the override actually took

- [ ] The log contains, once per intent:
      `Intent HassStartTimer is being overwritten by <ScriptIntentHandler ...>`

      **This warning is the success signal, not an error.** If it is absent the
      override did not load, timers are still going into Assist's internal
      TimerManager, and the clock will never see them.

### The timer path, step by step

Say **"set a timer for two minutes"** to a Voice PE in the kitchen, then check
each link in the chain in order. Checking them in order is what turns "it
doesn't work" into a specific broken link:

- [ ] `timer.kitchen` → state `active`, and has a `finishes_at` attribute
- [ ] `sensor.wall_clock_timer_finish_epoch` → a ~10-digit unix epoch
- [ ] `sensor.wall_clock_timer_total` → `120`
- [ ] The ring shows a **teal arc** that drains anticlockwise as time passes
- [ ] The arc is **smooth**, not stepping in jumps of several pixels
- [ ] At zero: `input_boolean.wall_clock_timer_alert` turns **on**
- [ ] The ring **pulses amber over the whole circle**
- [ ] ~60 s later the alert clears by itself and the clock returns

### Timer edge cases

- [ ] **"Add five minutes"** → the arc grows but never jumps past full.
      (This is the `ratio > 1.0` clamp; it is the case most likely to look wrong.)
- [ ] **"Cancel the timer"** → arc disappears immediately, no alert
- [ ] **Restart HA while a timer runs** → the timer survives (`restore: true`)
      and the arc resumes at the right place
- [ ] Start a timer in a **different room** → the arc appears; the clock shows
      the soonest-finishing timer regardless of which room set it

### Ambient status

- [ ] Open the garage → **steady amber at 3 o'clock**
- [ ] Force the bin-night sensor on → **breathing green/yellow at 12 o'clock**,
      colour matching `sensor.next_bin`
- [ ] Force the driveway sensor on → **blinking red at 9 o'clock**
- [ ] Person entities home/away → **dim pixels near 6 o'clock** appear/disappear
- [ ] With a timer running, **ambient status disappears** — timers outrank it

---

## Stage 5 — Degradation. This is the one that matters.

Priority order is *reliable clock > timers > status*, and this stage is the
only place that claim actually gets tested.

- [ ] **Stop Home Assistant** (or disable the ESPHome integration) and leave the
      clock powered. **The clock keeps telling the time.** No reboot, no blank
      ring, no drift you can see.
- [ ] Leave it disconnected for **at least 20 minutes.** This specifically tests
      that `reboot_timeout: 0s` took effect — with the 15-minute default the
      device would reboot here, and on a cold boot with no RTC it would lose the
      time entirely.
- [ ] A faint red tint appears at 6 o'clock — the "status is stale" hint. The
      time is still trustworthy; only the status data is old.
- [ ] Bring HA back → the tint clears, status resumes, no reboot.
- [ ] **Power-cycle the clock with HA still down.** The ring should show the
      slow amber crawl (the deliberate "I don't know the time" pattern) and
      then pick up the time from **SNTP** within a minute or two.
- [ ] Confirm it shows **local time, not UTC**. If it is 10 hours out, the
      SNTP `timezone:` line is not doing its job.
- [ ] Bring HA back → time re-syncs, timezone stays correct.

### Overnight

- [ ] At 22:00 the ring **dims** to the night brightness.
- [ ] At 07:00 it returns to day brightness.
- [ ] To test without waiting: temporarily set `night_start_hour` to the current
      hour and re-flash. Set it back afterwards.

### Soak

- [ ] Leave it running **24 hours** on the bench before mounting anything.
- [ ] After 24 h: time still correct to the second against a phone, no reboots
      in the log, no memory warnings.

---

## Stage 6 — Only now, assemble and mount

- [ ] Print the parts, cut the face (see `enclosure/README.md`).
- [ ] Dry-fit the ring in the body channel **before** gluing or screwing anything.
- [ ] Re-run the Stage 2 `test chase` **after assembly** — this is when you set
      `twelve_oclock_offset` for real, because the ring's rotation in the body
      is what finally decides it.
- [ ] Check the diffuser: **60 distinguishable points**, not a smeared glow. If
      it smears, see the tuning note in `diffuser.scad`.
- [ ] Mount the cleat. Level it — the cleat is what sets the clock's level, and
      a clock 2° off is more annoying than one that is 10° off.
- [ ] Hang, then confirm you can still get the face off and reach the USB port
      **without lifting the clock off the wall.** If you can't, the design has
      failed its main requirement and something is in the wrong place.

---

## Troubleshooting

### The ring flickers

In likely order:

1. **Missing common ground** between the ESP32 and the LED supply. The single
    most common cause, and it looks exactly like a data problem.
2. **No level shifter.** The ESP32 guarantees only `VOH` = 2.64 V; the original
    WS2812B wants 3.5 V and even the relaxed V5 wants 2.7 V. It works on the
    bench and fails on the wall — which is the whole reason the `74AHCT125` is
    in the BOM. If you skipped it, this is why.
3. **Missing 470 Ω series resistor**, or it is at the ESP32 end instead of the
    ring end.
4. **Missing 1000 µF bulk capacitor** at the ring.
5. **Data wire too long or unshielded.** Keep it under ~150 mm inside the case.
6. `use_psram: false` on the light component — the only remedy ESPHome
    documents for this symptom.

> Note: **RMT channel exhaustion does *not* cause flicker.** It fails loudly at
> setup with `Channel creation failed` and marks the component failed. If you
> are seeing flicker, RMT is not your problem. Also be aware the recurring
> upstream flicker issue (#10335) was closed **as stale, not fixed** — there is
> no known root cause upstream, so work the list above rather than expecting a
> software answer.

### The first pixel is the wrong colour

- **All colours wrong the same way** (white → yellow, red → green): colour
  order. Change `channel_colors: GRB` to `RGB` in the light block. Some
  batches differ even within the same product listing.
- **Only pixel 0 wrong, rest correct**: pixel 0 is taking a corrupted first
  bit. Almost always the level shifter or the series resistor — the first LED
  sees the rawest edge of the signal. Same list as flicker, items 2–4.
- **First few pixels wrong, rest fine**: same cause, worse. Check the resistor
  is at the ring end.

### The clock is rotated

Run `test chase`, note where the red pixel lands, and set
`twelve_oclock_offset` in the substitutions. Positive rotates clockwise. This
is expected — the ring's solder pads almost never end up at the top.

### The chase runs anticlockwise

The ring is physically wired the other way. Either flip the ring in the body,
or negate the direction in the render. There is no config key for it — the
sign lives in the `P()` helper in the lambda.

### Part of the ring is dark

- If exactly the **first N pixels work and the rest are dark**, and N looks
  like a number you typed: `num_leds` is smaller than the physical ring. This
  used to fail silently; the render now takes its size from the strip, so it
  should not happen — but check `num_leds` first anyway.
- If pixels work up to a point and then stop **at the same physical LED every
  time**, that LED has failed. WS2812Bs pass data through, so one dead chip
  kills everything downstream. Replace it or re-route around it.

### The timer arc never appears

Walk the chain from Stage 4 in order. The two common breaks:

- `sensor.wall_clock_timer_finish_epoch` stays `0` → the timer entity name does
  not match the list inside the template. Your area id is probably not what you
  assumed. Run the `areas()` query from `INSTALL.md`.
- The timer starts but Assist says *"I don't have a timer set up for this
  room"* → same cause, from the other end: `preferred_area_id` is producing an
  area id with no matching `timer.<area_id>`.

### The timer arc is frozen

You are reading the timer's `remaining` attribute somewhere instead of
`finishes_at`. `remaining` **does not tick down** — it is written once at start
and only recomputed on pause/change. The package publishes an absolute epoch
specifically to avoid this.

### Voice PE went silent when a timer finishes

Expected, and it was a deliberate trade. The `intent_script` override means HA
no longer sends timer events to the satellite, so its own ring and chime go
dark. The announce automation replaces the audio. If it is silent, the
`assist_satellite.*` entity name in the automation is wrong — that name is the
single thing in the package most likely to need correcting, since it was
written before the Voice PE units existed.
