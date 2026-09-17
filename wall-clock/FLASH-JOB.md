# FLASH-JOB — update all three clocks over WiFi, from a session on Sam's PC

This is a job for a Claude Code session running **on Sam's PC** (or any machine
on 192.168.1.0/24). A cloud session cannot do it: it has no route to the LAN.
Read this whole file before running anything.

## Why this file exists

The cloud session has asked for "flash all three" to be done four times today
and could never do it itself. Historically the job was handed to a Remote
Control session on the PC via a Routine — and the record shows that hand-off
failing silently ("seven pokes delivered, none executed", HANDOFF). So the job
lives HERE, versioned, where either a poked session or Sam typing
`claude "do wall-clock/FLASH-JOB.md"` can run it identically.

## Preconditions — check every one, stop on the first that fails

1. You are on Sam's LAN: `ping -n 1 192.168.1.75` (HA) answers.
2. The repo is on the right branch and current:
   ```powershell
   cd projects
   git fetch origin claude/home-assistant-wall-clock-om42v2
   git checkout claude/home-assistant-wall-clock-om42v2
   git pull origin claude/home-assistant-wall-clock-om42v2
   ```
3. `esphome version` reports **2026.8.x** or newer. The firmware uses
   `online_image` as an `image:` platform, which 2026.6 rejects.
4. **`wall-clock/esphome/secrets.yaml` exists.** It is gitignored and lives
   only on this PC and the HA box. It must carry `wall_clock_ota_password` and
   `wall_clock_api_key` matching the RUNNING firmware, or OTA is rejected and
   HA silently loses every entity.
   **If it is missing, STOP and say so. Never create one with placeholder
   values — a placeholder OTA password flashes nothing and a placeholder API
   key strands the clock.**
5. Each clock answers on its mDNS name (below). Target by NAME, not IP:
   `192.168.1.69` is recorded against two different clocks and one of those is
   a stale lease.

## The three flashes — one at a time, in this order, from `wall-clock/esphome/`

`-s` flags go BEFORE `run`, `--device` AFTER the file. The substitution names
are `device_name`, `friendly_name`, `routine_slug` — with underscores.
`-s devicename` is accepted, ignored, and **silently renames the clock**,
taking its 112 entities with it. Check the name in the build banner before
letting an OTA proceed.

```powershell
cd wall-clock\esphome

# Zac's Clock — 24 LED
esphome -s device_name mini-round-clock-3 -s friendly_name "Zac's Clock" -s routine_slug zac `
  run mini-round-clock-with-display.yaml --device mini-round-clock-3.local

# Jake's Clock — 32 LED
esphome -s device_name mini-round-clock-4 -s friendly_name "Jake's Clock" -s routine_slug jake `
  run mini-round-clock-with-display.yaml --device mini-round-clock-4.local

# Third Clock — 60 LED
esphome -s device_name mini-round-clock -s friendly_name "Mini Round Clock" -s routine_slug third `
  run mini-round-clock-with-display.yaml --device mini-round-clock.local
```

These match `esphome/ha-device-configs/*.yaml` exactly. If any differ, the
wrapper files are the truth — update this file, not them.

Wait for each to finish and reboot before starting the next. Do not run them in
parallel.

## Verify, per clock

- The build banner names the right device (`mini-round-clock-3`, not
  `mini-round-clock`).
- The clock comes back on WiFi and Home Assistant shows it available.
- `sensor.<slug>_firmware_built` postdates the flash.
- The ring count is still right (it is stored on the device; a reflash should
  not touch it).

## Then

Paste `homeassistant/dashboards/wall-clock-settings-view.yaml` into the
dashboard's raw editor, and copy `homeassistant/packages/wall_clock_update.yaml`
to `/config/packages/` on the HA box if not already there.

## Report back

For each clock: flashed / not flashed, and if not, the exact error. Do not
summarise an error you did not read.
