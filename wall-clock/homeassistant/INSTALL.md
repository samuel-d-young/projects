# Installing the Home Assistant side

## 1. Fill in the entity ids first

Several ids in `packages/wall_clock.yaml` **cannot be known from outside your
system** and are marked `!! FILL IN !!`. In HA 2026.8 the default entity_id
format is *area + device + entity*, so anything an integration discovered
depends on your area assignments — a guessed Frigate id will be wrong.

Paste each of these into **Developer Tools → Template** and correct the file:

```jinja
Areas (these decide the timer entity names):
{{ areas() | map('area_id') | list }}

Frigate face sensors:
{{ states.sensor | selectattr('entity_id','search','face')
   | map(attribute='entity_id') | list }}

Frigate occupancy:
{{ states.binary_sensor | selectattr('entity_id','search','occupancy')
   | map(attribute='entity_id') | list }}

Garage cover:
{{ states.cover | map(attribute='entity_id') | list }}

People:
{{ states.person | map(attribute='entity_id') | list }}

Voice satellites (once the Voice PE units arrive):
{{ states.assist_satellite | map(attribute='entity_id') | list }}
```

**The timer entity names matter most.** The intent override routes by
`preferred_area_id` — the area of the Voice PE that heard you — and builds
`timer.<area_id>`. If your area is "Living Room" the area_id is `living_room`
and the helper must be `timer.living_room`. Mismatch and every timer command
answers *"I don't have a timer set up for this room yet."*

## 2. Copy and check

```bash
# on the HA box
cp wall_clock.yaml /config/packages/wall_clock.yaml
ha core check
```

`ha core check` is the more comprehensive check — more so than the UI's
Settings → Tools → YAML → Check configuration.

## 3. Restart — once

**The first install genuinely needs a full restart, not a reload.**

`homeassistant.reload_all` only calls `reload` on domains that are *already*
set up; it cannot bootstrap a new one. This package introduces `timer:` and
`intent_script:`, and neither ships in `default_config`. So:

```bash
ha core restart
```

**Every edit after that**, a reload is enough — Developer Tools → Actions →
`homeassistant.reload_all`. It re-reads `configuration.yaml` from disk and
re-merges packages each time, so even a brand-new *file* is picked up, as long
as its domains are already loaded. It also runs a config check first and
reloads **nothing** if that fails, so it is safe to fire.

## 4. Confirm the override took

In the log after restart you should see, once per overridden intent:

```
Intent HassStartTimer is being overwritten by <ScriptIntentHandler ...>
```

**That warning is the success signal, not an error.** If it is absent, the
override did not load and timers are still going into Assist's internal
TimerManager, where the clock cannot see them.

Then check the entities exist with the exact ids the firmware expects:

```jinja
{{ states.sensor | selectattr('entity_id','search','wall_clock')
   | map(attribute='entity_id') | list }}
{{ states.binary_sensor | selectattr('entity_id','search','wall_clock')
   | map(attribute='entity_id') | list }}
```

Expected: `sensor.wall_clock_timer_finish_epoch`, `sensor.wall_clock_timer_total`,
and eight `binary_sensor.wall_clock_*`. `homeassistant/test/check.py` asserts
the firmware and package agree on these names, but only your HA can confirm
the ids came out unprefixed.

## 5. End-to-end test

Say *"set a timer for two minutes"* to a Voice PE in the kitchen, then:

- `timer.kitchen` should go `active` with a `finishes_at` attribute
- `sensor.wall_clock_timer_finish_epoch` should become a ~10-digit unix epoch
- `sensor.wall_clock_timer_total` should read `120`
- when it fires, `input_boolean.wall_clock_timer_alert` goes on for 60s

If the timer starts but the epoch sensor stays `0`, the timer entity name does
not match the list inside the template — see step 1.

## Reverting

Delete `/config/packages/wall_clock.yaml` and restart. HA re-registers its
built-in timer intent handlers on startup and Assist timers behave exactly as
they did before. Nothing else needs undoing.
