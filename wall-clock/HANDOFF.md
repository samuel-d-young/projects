# Handoff to a local Claude session

## Why this file exists

The session that built this project ran in **Anthropic's cloud**. It verified,
by connection test, that it has no route to the LAN:

```
curl http://192.168.1.79:8123/   -> timed out after 6s
curl http://192.168.1.63:5000/   -> timed out after 6s
/dev/tcp/192.168.1.79/8123       -> no route
egress IP                        -> 160.79.106.139  (public cloud)
```

That block is left exactly as it was run. `192.168.1.79` was Home Assistant's
address at the time; **it now answers on `192.168.1.75`**. Rewriting a recorded
measurement to match a later address would turn evidence into fiction, and the
conclusion it supports — a cloud session has no route to this LAN — does not
depend on which address it failed to reach. (The Pi at `.79` is dead: no ping,
no ARP entry.)

**Three addresses that are easy to confuse, so they are written down here:**

| | what it is |
|---|---|
| `192.168.1.75` | **Home Assistant.** HA OS as the libvirt guest `haos`. This is the one you want. |
| `192.168.1.66` | the hypervisor that runs it, hostname `hass`. Not Home Assistant. |
| `192.168.1.42` | the NUC, `voice-core` — Agent Deck, and Whisper/Piper. |

I had `.66` here first and it was wrong: `.66` was verified as the *planned*
destination, and the move landed one layer of indirection past the plan — HA OS
in a VM *on* `.66`, answering on `.75`.

The account has exactly one environment, `anthropic_cloud`, so **any session
spawned from there is in the same position** — including a Cowork session.
Cloud sessions cannot install this.

A Claude session running **on Samuel's own machine** is on the LAN and can.

## What a local session can and cannot do

**Can**, over the LAN:

- SSH to Home Assistant and run `homeassistant/install.sh`
- Run `ha core check`, `ha core restart`
- Query Developer Tools via the HA REST API and fill in the real entity ids
- Verify the `wall_clock_*` entities and the intent-override log line
- Trigger an ESPHome build in Device Builder

**Cannot** — these need hands at the bench either way:

- Plug the ESP32-S3 into USB for the first flash (there is no ESPHome firmware
  on it yet, so OTA is not an option). *Unless* the S3 is plugged into the HA
  machine itself, in which case Device Builder can flash it directly.
- Wire the ring, print the parts, cut the face.

## Paste this into a local Claude session

> I'm picking up a project built in a cloud session that couldn't reach my LAN.
> The repo is `samuel-d-young/projects`, branch
> `claude/home-assistant-wall-clock-om42v2`, directory `wall-clock/`.
>
> Home Assistant is at 192.168.1.75:8123 (HA OS in the `haos` VM). I have the ESPHome
> Device Builder and Mosquitto add-ons, and `packages: !include_dir_named packages`
> is already enabled.
>
> Read `wall-clock/HANDOFF.md` and `wall-clock/homeassistant/INSTALL.md` first,
> then `wall-clock/BUILD-LOG.md` for why things are the way they are.
>
> Do steps 1–5 of INSTALL.md for me — the Home Assistant half:
>
> 1. Run `wall-clock/homeassistant/install.sh` on the HA box (Terminal & SSH
>    add-on). It backs up, validates and rolls back on failure; don't let it
>    restart yet.
> 2. Before restarting, find my real entity ids and edit
>    `/config/packages/wall_clock.yaml`. The queries are in INSTALL.md step 2.
>    The timer helper names must match my area ids exactly — the intent
>    override builds `timer.<area_id>` from `preferred_area_id`.
> 3. Restart HA once (a restart, not `reload_all` — this introduces `timer:`
>    and `intent_script:` and neither is in default_config).
> 4. Confirm the log shows `Intent HassStartTimer is being overwritten by
>    <ScriptIntentHandler ...>` — that warning is the success signal, not an
>    error.
> 5. Confirm 2 `sensor.wall_clock_*` and 8 `binary_sensor.wall_clock_*` exist.
>
> Then stop and tell me what the real entity ids turned out to be, and whether
> the override loaded. Don't flash the ESP32 yet — the display pins still need
> correcting against my actual panel.

## State when this was handed over

**Done and verified as far as it could be without hardware:**

- Research ledger, all claims tagged verified/assumed, adversarially re-checked
- `esphome/mini-round-clock.yaml` — both lambdas compile clean under
  `-Wall -Wextra` against stubbed ESPHome types; hand positions assert correct
  at 12/24/60 LEDs; all four display branches exercised
- `homeassistant/packages/wall_clock.yaml` — YAML parses, 35 Jinja templates
  syntax-check clean, all 10 firmware subscriptions satisfied by the package
- `enclosure/mini/` — three watertight STLs (signed-volume checked) + Glowforge
  SVG, sized to the measured 92/71 mm ring
- `install.sh` — all four paths exercised against a fake `/config` and a stub
  `ha` binary, including the rollback

**Never run, and known to be the next things to break:**

- `esphome config` and `ha core check` — no toolchain, no LAN
- **Display pins** are ESP-VoCat reference values, not Samuel's panel
- **`DISP_MODULE_D` / `DISP_T`** in `enclosure/mini/build.py` are assumed 1.85"
  values; the ring dimensions are measured, these are not
- `assist_satellite.*` entity naming in the announce automation — guessed,
  because the Voice PE units had not arrived

## How to resume on Windows (PowerShell)

This conversation ran in a cloud session, so its transcript is **not** in the
local `~/.claude` history on the Windows box — `claude --continue` and
`claude --resume` will not find it. The repo is the continuity mechanism:
`BUILD-LOG.md` carries the *why*, this file carries the *where we stopped*.

```powershell
# once, if Claude Code isn't installed
winget install --id Anthropic.ClaudeCode -e

# get the branch
git clone https://github.com/samuel-d-young/projects.git
cd projects
git checkout claude/home-assistant-wall-clock-om42v2

# if already cloned, just fetch
git fetch origin claude/home-assistant-wall-clock-om42v2
git checkout claude/home-assistant-wall-clock-om42v2
git pull origin claude/home-assistant-wall-clock-om42v2

# start on Opus, then type /effort ultracode at the prompt
claude --model opus "Read wall-clock/HANDOFF.md then wall-clock/BUILD-LOG.md, and pick up where the cloud session stopped. Do not re-derive anything already recorded there."
```

A local session is on the LAN, so unlike the cloud session it can reach
192.168.1.75 and actually run the install. The paste-ready install prompt is in
the section above.
