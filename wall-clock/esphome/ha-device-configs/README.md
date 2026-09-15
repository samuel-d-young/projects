# Flashing the clocks from Home Assistant, over WiFi

Put `zacs-clock.yaml` and `jakes-clock.yaml` in `/config/esphome/` on the Home
Assistant box. After that, updating a clock is **ESPHome Device Builder →
the device → Install → Wirelessly**. No PC, no terminal, no USB, no cable.

Each file is ten lines and never has to change again. The firmware itself is
pulled from GitHub at build time, so whatever is on the branch is what gets
built.

## What has to be in /config/esphome/secrets.yaml

Five keys:

```
wifi_ssid
wifi_password
wall_clock_api_key
wall_clock_ota_password
wall_clock_ap_password
```

**Two of them have to match what is already running on the clocks**, or the
first wireless install is also the last one:

* `wall_clock_ota_password` — OTA authenticates against the value compiled into
  the RUNNING firmware. A mismatch is rejected and it is back to USB.
* `wall_clock_api_key` — a mismatch builds fine, flashes fine, and then Home
  Assistant cannot talk to the clock. All 112 entities go unavailable.

Copy both from the `secrets.yaml` that flashed the clocks in the first place.
Do not generate new ones.

`!secret` inside a package resolves against the package's own directory first
and the main config's directory second. The repo has no `secrets.yaml` in it —
it never will — so it falls through to `/config/esphome/secrets.yaml`, which is
where the add-on keeps them anyway.

## Verified, not assumed

`esphome config zacs-clock.yaml` was run against this exact file from a machine
with no GitHub login and no HA:

```
INFO Cloning https://github.com/samuel-d-young/projects@claude/home-assistant-wall-clock-om42v2
esphome:
  name: mini-round-clock-3
  friendly_name: Zac's Clock
INFO Configuration is valid!
```

So: the repo clones anonymously, the substitutions land, and the secrets
fall through to the config directory as described.

## `device_name`, with the underscore

The substitution names are `device_name` and `friendly_name`. `-s devicename`
on a command line is **silently ignored** — ESPHome accepts an override for a
substitution the file does not use and builds with the defaults. Aimed at a
clock over OTA that renames it to `mini-round-clock` and takes every one of its
entities with it. These files use the correct names; a hand-typed command line
is where it goes wrong.
