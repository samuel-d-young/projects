# Installing — end to end

Two halves, in this order:

**A. Home Assistant** (steps 1–5) — the timer helpers, the intent override, and
the `wall_clock_*` entities the clock reads.
**B. The device** (steps 6–10) — flashing `mini-round-clock`.

Do A first. The device works without it (the imports just read unavailable and
the clock still tells the time), but nothing else will do anything.

---

# A. Home Assistant

## 1. Install the package

From the **Terminal & SSH** add-on:

```bash
bash install.sh
```

It backs up any existing `wall_clock.yaml`, writes the package, runs
`ha core check`, and **restores the backup and stops if that check fails**.
Restart is opt-in and defaults to no.

`--check-only` validates and changes nothing. `--yes` skips the restart prompt.

<details>
<summary>Doing it by hand instead</summary>

```bash
cp packages/wall_clock.yaml        /config/packages/wall_clock.yaml
cp packages/wall_clock_timers.yaml /config/packages/wall_clock_timers.yaml
cp packages/wall_clock_ui.yaml     /config/packages/wall_clock_ui.yaml
cp packages/wall_clock_grow.yaml   /config/packages/wall_clock_grow.yaml
ha core check
```
</details>

> **`install.sh` installs `wall_clock.yaml` only.** It carries that one package
> inline and knows nothing about the other three. They have to be copied by
> hand, as above, and this is exactly how a box ended up running the timers
> package from before v18 with three helpers missing
> (`input_button.wall_clock_timer_dismiss`,
> `input_number.wall_clock_alert_repeat_max`,
> `input_number.wall_clock_alert_repeat_seconds`) while the dashboard asked for
> them. After copying: `homeassistant.reload_all` is enough for `_ui` and
> `_grow`; `_timers` introduces `timer:` and `intent_script:` on a first
> install and wants a restart.

## 2. Fill in the entity IDs

**Do this before restarting.** Several IDs cannot be known from outside your
system — HA 2026.8 builds entity IDs from *area + device + entity name*, so
anything an integration discovered depends on your area assignments. A guess
passes `ha core check` and then silently never fires.

Paste each into **Developer Tools → Template**, then edit
`/config/packages/wall_clock.yaml`:

```jinja
Areas — these decide the timer entity names, and matter most:
{{ areas() | map('area_id') | list }}

Frigate face sensors:
{{ states.sensor | selectattr('entity_id','search','face') | map(attribute='entity_id') | list }}

Frigate occupancy:
{{ states.binary_sensor | selectattr('entity_id','search','occupancy') | map(attribute='entity_id') | list }}

Garage cover:
{{ states.cover | map(attribute='entity_id') | list }}

People:
{{ states.person | map(attribute='entity_id') | list }}
```

> **The timer names are the ones to get right.** The override routes by
> `preferred_area_id` — the area of the Voice PE that heard you — and builds
> `timer.<area_id>`. If your area is "Living Room" the helper must be
> `timer.living_room`, or every voice command answers *"I don't have a timer
> set up for this room yet."*

## 3. Restart — once

```bash
ha core restart
```

**The first install genuinely needs a restart, not a reload.**
`homeassistant.reload_all` only calls `reload` on domains that are *already* set
up; it cannot bootstrap a new one. This package introduces `timer:` and
`intent_script:`, and neither ships in `default_config`.

**Every edit after this one** can use Developer Tools → Actions →
`homeassistant.reload_all`. It re-reads `configuration.yaml` and re-merges
packages each time, and runs a config check first — reloading nothing if it
fails, so it is safe to fire.

## 4. Confirm the override took

In the log you should see, once per intent:

```
Intent HassStartTimer is being overwritten by <ScriptIntentHandler ...>
```

**That warning is the success signal, not an error.** If it is absent, the
override did not load, timers are still going into Assist's internal
`TimerManager`, and the clock will never see them.

## 5. Confirm the entities exist

```jinja
{{ states.sensor | selectattr('entity_id','search','wall_clock') | map(attribute='entity_id') | list }}
{{ states.binary_sensor | selectattr('entity_id','search','wall_clock') | map(attribute='entity_id') | list }}
```

Expect **2 sensors** and **8 binary_sensors**. `test/check.py` already asserts
the firmware and package agree on these names, but only your HA can confirm the
IDs came out unprefixed.

---

# B. The device

## 6. Validate the config first

```bash
esphome config ../esphome/mini-round-clock.yaml
```

Nobody has run this yet. Expect it to be the first thing that finds a problem —
that is what it is for.

## 7. Add the secrets

In Device Builder's **secrets editor** (`/config/esphome/secrets.yaml`):

```yaml
wifi_ssid: "The Youngs"          # quoted — the SSID contains a space
wifi_password: "..."
wall_clock_api_key: "..."        # openssl rand -base64 32
wall_clock_ota_password: "..."
wall_clock_ap_password: "..."
```

API **password** auth was removed in ESPHome 2026.1 — the key is mandatory.

> **Credentials go here, never in the device YAML.** The configs reference them
> as `!secret`, and `secrets.yaml` stays on the HA box — it is gitignored, so it
> cannot end up in the repo. That separation is the only reason the configs are
> safe to push to GitHub.

## 8. Check the display pins

**Resolved as of 2026-08-24 — the display is working. Read this only if your
panel is wired differently to mine.**

The config drives a 2.1" 360x360 round TFT (**GC9B72**, 10-pin FPC) as plain
4-wire SPI via `model: CUSTOM`, with a verified GC9B72 init sequence. It is
*not* the quad-SPI `model: ESP-VOCAT` arrangement earlier drafts assumed.

The header reads `TE SDO BL CS DC RST SDA SCL VCC GND`. The GPIOs are
substitutions at the top of `mini-round-clock.yaml`:

```yaml
lcd_clk: GPIO12             # SCL
lcd_mosi: GPIO11            # SDA
lcd_cs: GPIO10              # CS
lcd_dc: GPIO13              # DC
lcd_reset: GPIO14           # RST
lcd_backlight: GPIO21       # BL
```

`TE` and `SDO` stay unconnected. `VCC` is **3V3**, not 5 V.

If you change `pixel_mode`, you must keep it at `16bit` unless you also change
the `0x3A` in the init table — ESPHome appends its own COLMOD from
`pixel_mode` and it overrides whatever the table says. See
[`../docs/gc9b72-display-block.yaml`](../docs/gc9b72-display-block.yaml) for
the full explanation and the sequence's provenance.

**Do not substitute a different controller's init sequence**, even a close
relative. A GC9B71 table on this panel lights it and renders stripes — see the
2026-08-24 entry in [`../BUILD-LOG.md`](../BUILD-LOG.md).

## 9. Flash it

Paste `mini-round-clock.yaml` into the `mini-round-clock` device in Device
Builder, then **Install → Manual download → `.factory.bin`**.

The first flash must be the **factory** image, not the OTA `.bin` — there is no
ESPHome firmware on the board yet to update.

Plug the S3 into your laptop and flash at **web.esphome.io** (Chrome or Edge,
WebSerial). After this, everything is OTA.

**Flash with the LED supply unplugged.** Never USB and external 5 V together —
Espressif is categorical that the board or the supply can be damaged.

Two S3 specifics:

- The logger defaults to `USB_SERIAL_JTAG` on S3. If your board has a UART
  bridge chip rather than native USB you will get no serial output until you set
  `logger: hardware_uart: UART0`.
- Some S3 boards need **BOOT held while you plug in** to enter download mode.

## 10. Adopt and check the boot log

The device should appear in **Settings → Devices & Services → ESPHome**. Watch
for these — match the component **tag and meaning**, not the exact wording:

- `[I][app]` — version banner, should read **2026.8.0**
- `[C][wifi]` — connected, with an IP
- `[C][esp32_rmt_led_strip]` — strip sets up.
  `Channel creation failed` here is **RMT exhaustion**, not wiring.
- `[C][psram]` — PSRAM initialises. If this fails the display will not work,
  and `mode: octal` vs `quad` is the usual reason.
- `[C][api]` — API server starts
- `Boot: ring + display up` — the explicit line from `on_boot`. Missing means
  the effect was not selected and the ring stays dark whatever else is right.

**No boot loop.** A repeating version banner is a reset loop — almost always
brownout. Go back to the supply.

---

# Then: bring-up

## 11. Find LED zero

Set `select.mini_round_clock_mode` to **`test chase`**.

One white pixel should walk **clockwise**, with one red pixel marking the
computed 12 o'clock. Note where the red pixel physically sits, put that in
`twelve_oclock_offset`, re-flash. Positive rotates clockwise.

If the white pixel is not white, or red is not red, the colour order is wrong —
change `channel_colors: GRB` to `RGB`.

## 12. End-to-end timer test

Say **"set a timer for two minutes"** to a Voice PE in the kitchen, then walk
the chain in order. Checking it in order turns "it doesn't work" into a specific
broken link:

| Check | Expect |
|---|---|
| `timer.kitchen` | state `active`, has a `finishes_at` attribute |
| `sensor.wall_clock_timer_finish_epoch` | a ~10-digit unix epoch |
| `sensor.wall_clock_timer_total` | `120` |
| The ring | teal arc, draining |
| The display | large `1:59` counting down, clock demoted to subtitle |
| At zero | `input_boolean.wall_clock_timer_alert` on, ring pulses amber |
| ~60 s later | clears itself |

Then the full checklist in [`../docs/PHASE-6-TEST-PLAN.md`](../docs/PHASE-6-TEST-PLAN.md)
— particularly **Stage 5**, which is the only place the *clock > timers >
status* priority actually gets tested rather than asserted.

---

# Troubleshooting

| Symptom | Cause |
|---|---|
| *"I don't have a timer set up for this room"* | `timer.<area_id>` does not match your real area id. Step 2. |
| Timer starts, epoch sensor stays `0` | Same cause, from the other end — the entity list inside the template does not match your timer names. |
| No `being overwritten` log line | The override did not load. The package is not being read; check `packages:` is in `configuration.yaml`. |
| Ring dark, everything else fine | The `Face` effect was not selected — look for the `Boot:` log line. |
| Ring flickers | Missing common ground first, then no level shifter, then the 470 Ω in the wrong place. RMT exhaustion does **not** cause flicker — it fails loudly at setup. |
| Only pixel 0 wrong | The first LED sees the rawest signal edge — level shifter or series resistor. |
| Display blank, ring fine | Wrong pins (step 8), or PSRAM failed to init — check `mode: octal` vs `quad`. |
| Timer arc frozen | Something is reading the timer's `remaining` attribute, which does not tick down. The package publishes an absolute epoch precisely to avoid this. |
| Voice PE went silent on timers | Expected. The override means HA no longer sends timer events to the satellite; the announce automation replaces the audio. If silent, the `assist_satellite.*` name in the automation is wrong. |

# Reverting

Delete `/config/packages/wall_clock.yaml` and restart. HA re-registers its
built-in timer intent handlers on startup and Assist timers behave exactly as
before. Nothing else needs undoing.
