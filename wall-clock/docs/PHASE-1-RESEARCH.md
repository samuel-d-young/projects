# Phase 1 — Research Ledger

Researched 2026-08-21. Pinned versions: **HA Core 2026.8.2** (git tag), **ESPHome 2026.8.0**,
**WLED v16.0.1**. Every claim below is tagged **(verified)** — a primary source was fetched and
quoted — or **(assumed)** — plausible, not confirmed. Nothing here has been run on hardware.

Method: 12 parallel research passes against primary sources, then 3 independent adversarial passes
whose job was to *refute* the conclusions. That mattered — see §1.2.

---

## 1. The crux: reading Assist timer state

### 1.1 What is genuinely closed (verified)

Assist timers live in `homeassistant/components/intent/timers.py`. Re-checked at tag `2026.8.2`:

- **No entities.** `intent/sensor.py`, `timer.py`, `binary_sensor.py`, `entity.py` all HTTP 404.
  No `Entity` / `async_add_entities` anywhere in `timers.py`.
- **No event-bus events.** `grep -c 'async_fire' timers.py` = **0**, at both `2026.8.2` and `dev`.
  `TimerEventType` is a `StrEnum` consumed by `type TimerHandler = Callable[[TimerEventType, TimerInfo], None]`
  — an in-process Python callback, never an `event_type`. **There is nothing to write an automation
  trigger on.**
- **No fan-out.** `self.handlers: dict[str, TimerHandler]` — one handler per `device_id`, registered
  by plain overwriting assignment. All six dispatch sites are `self.handlers[timer.device_id](...)`.
- **Unicast on the wire, enforced at both ends.** HA sends via that one device's `APIClient`. The
  ESP32 firmware drops any `VoiceAssistantTimerEventResponse` not from its single subscribed
  connection, and `client_subscription()` refuses a second subscriber
  ("Multiple API Clients attempting to connect to Voice Assistant").
- **`assist_satellite` carries no timer data.** `grep -c -i timer entity.py` = 0. Its only features
  are `ANNOUNCE = 1` and `START_CONVERSATION = 2`.
- **`TimerInfo` has no `finishes_at`.** Fields are `id, name, seconds, device_id, start_hours,
  start_minutes, start_seconds, created_at, updated_at, language, is_active, area_id, area_name,
  floor_id, conversation_command, conversation_agent_id, _created_seconds`.
  `created_at`/`updated_at` are `time.monotonic_ns()` — **arbitrary epoch, not unix time.** They
  cannot be converted to a wall clock outside the HA process.

**⇒ A second ESP32 cannot subscribe to the Voice PE's Assist timers. That is real and final.**
Do not build a passive listener. Do not write an automation that triggers on an Assist timer.
Do not open a second API connection to sniff events.

### 1.2 Where the first research pass was wrong (and why that matters)

Three independent researchers converged on *"this is closed, therefore you must reflash the Voice
PE"*, and all three explicitly warned away from the `timer` helper as "a dead end". The adversarial
pass overturned that. Recording it because convergence looked like confirmation and wasn't:

| Original claim | Verdict | Why |
|---|---|---|
| "Nothing is reachable over the network" | **refuted** | `intent/__init__.py:101` registers `IntentHandleView` at `/api/intent/handle`. All three greppped for `websocket`/`async_register_command` — patterns that cannot match `register_view`. |
| "No automation or template can observe an Assist timer" | **refuted for _observe_, stands for _trigger_** | `HassTimerStatus` → `_find_timers()` line 725: with no `device_id` it returns **every** timer, serialised with `total_seconds_left`, `is_active`, `name` into `speech_slots`. Correct wording: **pollable, not subscribable.** |
| "The `timer` helper is a dead end" | **refuted** | It is the destination, not a trap. See §1.3. |
| "`voice_assistant` won't compile without a mic" | **refuted as a barrier** | `i2s_audio`'s mic platform needs only GPIO numbers; `setup()` touches no hardware. A display-only ESP32 with a fake mic compiles and boots. The real blocker is HA's `device_id` routing, not compilation. |

Lesson for later phases: three agents agreeing is not three confirmations if they all searched the
same way. The refutations came from opening files nobody had opened.

### 1.3 The clean path (verified by source, NOT yet bench-tested)

Don't read Assist's timers. **Stop the timer from entering `TimerManager` at all.**

- `homeassistant/helpers/intent.py` `async_register()`: if an intent_type already exists it logs
  `"Intent %s is being overwritten by %s"` **and then overwrites**. It does not refuse. (verified)
- `intent_script/__init__.py:116` calls exactly that. (verified)
- ⇒ Declaring `HassStartTimer:` under `intent_script:` **replaces** HA's built-in
  `StartTimerIntentHandler`. The built-in *sentence grammar* is preserved — only the handler changes.
  `TimerManager` is never involved. (verified)
- Voice PE stock firmware already declares `on_timer_*` triggers, so it already advertises
  `FEATURE_TIMERS`, so HA will not raise `TimersNotSupportedError`. **Works against a retail,
  unmodified, still-OTA-updating Voice PE.** (verified)
- A working reference implementation exists and ships the file:
  `djelibeybi/voice-assistant-persistent-timers` → `home-assistant/intent_scripts.yaml`.

```
Voice PE (stock firmware, untouched)
   │  "set a 5 minute timer" → built-in sentence grammar → HassStartTimer
   ▼
HA: intent_script override ──replaces──▶ StartTimerIntentHandler
   │  action: timer.start   target: timer.<area>
   ▼
timer.kitchen  ← REAL entity: state idle/active/paused,
                 attrs finishes_at / duration / remaining,
                 bus events timer.started/.finished, trigger platform
   │  ESPHome `homeassistant` text_sensor, attribute: finishes_at
   ▼
LED-ring ESP32 — counts down locally against `time: platform: homeassistant`
```

Why this wins: no firmware change on the Voice PE (OTA preserved), real entities on dashboards, an
absolute ISO-8601 `finishes_at` so the ring never drifts, survives an HA restart with `restore: true`.

**Cost of the override (verified):** HA stops sending `VoiceAssistantTimerEventResponse`, so the
Voice PE's own LED ring animation and ringing sound go dark. The reference project drives them back
with an ESPHome user-defined action plus `assist_satellite.announce`. **This is a real regression on
a device Sam is buying four of, and needs an explicit decision.**

**Must be tested before building (~20 min):** `intent_script`'s manifest declares no dependency on
`intent`, so the override's setup order is *empirically working*, not architecturally guaranteed.
**This single test gates the entire primary path.**

### 1.4 Fallbacks, in order

1. **Conversation sentence trigger.** (verified) `conversation/default_agent.py` checks
   `async_recognize_sentence_trigger()` **before** `async_recognize_intent()`, so a
   `trigger: conversation` automation cleanly shadows the built-in intent. *Cost:* you re-implement
   the grammar yourself — named timers, "add 5 minutes", multi-timer — losing the built-in sentence pack.
2. **Poll `POST /api/intent/handle {"name":"HassTimerStatus"}`.** (source-read only, **not tested**)
   Returns `speech_slots.timers[]` for all timers. No HA config change at all. Polling only, ~1 s
   granularity, ring free-runs between polls.
3. **Relay from the Voice PE firmware.** Template sensors on the satellite publishing
   `id(first_active_timer).seconds_left` etc. *Cost:* you own Voice PE firmware updates from then on,
   and whether reflashing a retail unit preserves official OTA is **unverified**.

### 1.5 Watch upstream — this will obsolete the design

`home-assistant/architecture` Discussion #1407 + draft PR `home-assistant/core#174847`
**"Add timer_list integration"** (synesthesiam, 2026-06-25, still **Draft** as of 2026-07-20).
Adds a `timer_list` entity domain modelled on `todo`, one per satellite, with automation triggers
and websocket subscribe/list APIs — exactly the three things that don't exist today.
Confirmed **not shipped** (404 at both `dev` and `2026.8.2`). It carries breaking changes: removes
the legacy `conversation_command` option and **will require devices to have a `timer_list` entity to
support voice timers.**

⇒ Build on `timer.*` helpers now. That is the cleanest thing to swap to a `timer_list` read later.

---

## 2. Start from an existing project?

**Yes: [`markusressel/ESPHome-Analog-Clock`](https://github.com/markusressel/ESPHome-Analog-Clock)** (verified)

- CC0-1.0 — effectively public domain, no attribution or copyleft burden.
- 38★, 97 commits, 0 open issues. Purpose-built for a 60-LED ring. `clock.h` is 115 lines.
- CI runs `esphome/build-action@v8.0.0` on every push — a **real firmware compile**, not a lint.
- Ships a `Watchface.svg` cut for a 60-LED ring, plus a 3D-printed case.
- Last push 2026-07-21 (dependabot); last functional commit 2026-01-26. Low velocity, **not abandoned**.
- **Port needed:** targets `esp8266: board: nodemcuv2` with `platform: neopixelbus` /
  `method: ESP8266_DMA`. Both are ESP8266-only. `clock.h` is coupled to the YAML's template switches
  and the `clock_brightness` global — port the pair together.

**Steal the timer arc from `esphome/home-assistant-voice-pe`** (last commit 2026-07-07). Change `12.0f` → `60.0f`:

```cpp
auto timer_ratio = 60.0f * id(first_active_timer).seconds_left
                   / max(id(first_active_timer).total_seconds, static_cast<uint32_t>(1));
```

Also worth stealing: its `partition` light trick to rotate physical LED 0 to 12 o'clock, and its
100 ms `addressable_lambda` update interval decoupled from the 1 Hz tick.

**Do not use (verified abandoned or wrong shape):** `jgruen/ESPHome-custom-addressable-lambdas`
(2024-12-12 **and no LICENSE file** → legally unsafe to copy); `RoadkillUK/ESPHome-WS2812B-Clock`
(2020, 7-segment); `baruch/circle-clock` (2016, raw Arduino); `trip5/EspHome-Led-Clock` (maintained
but Sinilink 7-segment hardware). **WLED `Analog_Clock` usermod** — 1D-only, no readme, frozen since
2022-11-14, needs a custom PlatformIO build, and `usermods/readme.md` says verbatim: *"I am not
actively maintaining any usermod in this directory."*

**Nothing off the shelf does both a 60-point clock face AND an Assist timer arc.** That integration
is the single biggest build risk.

---

## 3. LED component: `esp32_rmt_led_strip`

Verified, and **enforced by code, not just advice**: `esp32:` defaults to `framework: esp-idf`, and
both `neopixelbus` and `fastled_clockless` carry
`cv.only_with_framework(frameworks=Framework.ARDUINO, suggestions={Framework.ESP_IDF: ("esp32_rmt_led_strip", …)})`
— they **fail config validation** on a default ESP32 config.

- `neopixelbus` on ESP32: deprecated **2026.6**, removal **≤2027.1** (upstream lib won't build on ESP-IDF 6).
- `fastled_clockless`: docs 404 at both URL forms; ESPHome had to patch `-DFL_RMT5_INTERRUPT_LEVEL=0`
  because FastLED's RMT5 driver hard-codes priority 3 and `show()` hangs ~3 s.

### Three traps that will burn a build day (all verified)

1. **`rgb_order` is deprecated as of 2026.8.0 — exactly the version in play.** Use
   **`channel_colors: GRB`** (one string absorbing the old `rgb_order` + `is_rgbw` + `is_wrgb`).
   Old keys warn until removal in 2027.3.0. Mixing raises `'channel_colors' cannot be combined with …`.
2. **`rmt_channel` no longer exists.** The constant survives in `const.py` with zero references.
   Channels are allocated dynamically by `rmt_new_tx_channel()`. Passing it = unknown-key error.
   The current key is **`rmt_symbols`** (memory, not a channel index).
3. **`chipset: WS2812B` is invalid.** Valid set is exactly `WS2811, WS2812, SK6812, APA106, SM16703`.
   A WS2812B strip uses **`chipset: WS2812`**. `fastled_clockless` *did* accept `WS2812B`, so a
   copy-paste migration fails.

Other verified facts: `use_dma` accepted **only** on ESP32-S3 and ESP32-P4. Component unavailable on
ESP32-C2/C61 (no RMT hardware). RMT exhaustion presents as a setup-time `"Channel creation failed"`
+ `mark_failed()`, **not** flicker. The only documented flicker remedy is `use_psram: false`.
`addressable_lambda` is a **captureless function pointer** — `void (*f)(AddressableLight &, Color, bool)`;
negative indices wrap (`it[-1]` = last LED); **the lambda only runs while that effect is selected.**

**(assumed / unresolved):** whether WiFi causes RMT flicker. No mention in docs or source; the
recurring community flicker issue (#10335) was closed **as stale, not fixed**. Budget for it.

---

## 4. WLED matrix vs buying a ring

**This forks entirely on which panel is in the drawer.**

### If 16×16 — viable, and free

- **Perimeter = 4×16 − 4 = exactly 60 pixels**, evenly spaced, 15 per side = 15 minutes per quadrant.
  A coincidence unique to a 16-wide square. Angular error vs a true circular dial: ±4.02° ≈ ±0.67 min
  (~6.7 mm on a 160 mm panel).
- **The inscribed circle does NOT work** — r=7.5 gives 52 pixels, spacing 4.59°–9.87°, and 60
  minute-marks collapse onto only **44 distinct pixels** with 16 doubled. Don't attempt it.
- WLED has a **built-in analogue clock overlay in core** (`wled00/overlay.cpp:10 _overlayAnalogClock()`),
  **not a usermod** — no custom build. Size-agnostic. UI at Settings → Time & Macros → Clock;
  fields `OL`, `O1`, `O2`, `OM`, `O5`, `OS`, `OB`.
- Its writes pass through the ledmap (`setRange` → `setPixelColor` → `BusManager::setPixelColor(getMappedPixelIndex(i), c)`),
  so a `ledmap.json` placing the 60 perimeter pixels at logical 0–59 turns the stock overlay into a
  real 60-point perimeter clock with **zero code and zero purchases**.
- **(assumed)** — that chain was traced by source-reading only, never run. Prove it before deciding
  not to buy a ring.
- Caveat: realtime/UDP modes bypass ledmaps unless `realtimeRespectLedMaps` is on. Don't drive it
  over E1.31/DDP.

### If 8×32 — not viable

Perimeter = 76, not 60. Largest inscribed circle r=3.5 → **20 pixels**. 20 positions cannot
represent 60 minutes. Buy a ring, or use WLED's free digital clock (`Scrolling Text` 2D effect
substitutes `#TIME`/`#HHMM` in the segment name). **There is no native 2D analogue clock in WLED.**

### Two limits worth knowing (verified)

- The **HA WLED integration exposes no per-pixel control.** Per-pixel from HA needs the JSON API
  segment `i` key via `rest_command`: `{"seg":{"i":[0,8,"FF0000",10,18,"0000FF"]}}`.
- **ESPHome can drive the same matrix**: `display: platform: addressable_light` gives the full
  rendering engine (`it.line()`, `it.filled_circle()`, `it.strftime()`) over a `pixel_mapper:`,
  natively HA-integrated. Strong option for one firmware doing both clock face and timer arc.

---

## 5. Electrical (verified — and the premise needs correcting)

**The 3.6 A figure is a worst-case ceiling invented by Adafruit, not a datasheet value.**

- The original WS2812B datasheet (Worldsemi V1.0) contains **no current specification at all**. No
  `IDD`, no `IOUT`, no power row. The 60 mA number originates in Adafruit's Uberguide.
- The **current production part, WS2812B-V5, specifies 12 mA per channel = 36 mA/LED** at full white,
  with 0.6 mA quiescent. Real bench measurement lands ~40 mA/LED. WLED's shipped default assumption
  is 55 mA/LED.
- ⇒ 60 LEDs at full white is **~2.4 A realistically, 3.6 A worst case.** Size for 60 mA anyway —
  sellers rarely state the revision and may ship either.

**Level shifter: buy it.** The engineering answer is unambiguous with the datasheets side by side:

| Part | Required `VIH` |
|---|---|
| ESP32 guaranteed output `VOH` | **0.8 × VDD = 2.64 V** |
| WS2812B original | 0.7 × VDD = **3.5 V** |
| WS2812B-V5 (relaxed) | flat **2.7 V** |

The ESP32 is out of spec against **both** revisions at worst case. It usually works because a real
ESP32 sources ~3.2–3.3 V unloaded — that is the entire "everyone gets away with it" phenomenon, and
Adafruit admits to relying on it: *"Even in our own projects, we'll often leave this part out."*
Their own conclusion is the one to act on: *"you're taking that small chance of unreliable operation,
or 'works on-desk but not in-field.'"* For ~$3, buy certainty. **It must be the HCT family** (flat
2.0 V TTL input threshold) — a plain 74HC125 needs 3.5 V in and will not work.

**Other verified values:**

- **Series resistor 330–470 Ω**, placed at the **strip** end of the data wire, not the ESP32 end.
  (If the AHCT125 is fitted, put the resistor on its output.)
- **Bulk capacitor 1000 µF**, ≥6.3 V (buy 10–25 V), across strip +5 V/GND, at the strip, fitted
  before first power-up.
- **Power injection not needed.** WLED's threshold is 150 LEDs; QuinLED rates a single edge feed at
  4 A, above the 3.6 A worst case.
- **Common ground is mandatory.** Ground on first, off last.
- **Power-up order matters:** energise the strip **before** the ESP32, or it back-powers
  parasitically through the data pin and can damage the MCU.
- **Never USB + PSU at once.** Espressif is categorical: *"The power supply must be provided using
  one and only one of the options above, otherwise the board and/or the power supply source can be
  damaged."* The genuine DevKitC V4 has a blocking Schottky (D3, BAT760-7); **(assumed)** for the
  common DOIT 30-pin clone — no authoritative schematic found. Adopt the rule that is safe on every
  board: flash once over USB with the PSU unplugged, then use OTA.

**Two firmware traps found here (verified):**

1. **ESPHome's `max_power` cannot cap an addressable strip.** It is documented as float-outputs-only
   (PWM, AC dimmer, sigma-delta). It will not reach `esp32_rmt_led_strip`. The positive capping
   mechanism is **unverified** and must be checked in Phase 3 — do not assume `max_power` protects
   the supply.
2. **`gamma_correct` defaults to 2.8**, so a UI brightness of 50% is only ~14% duty. That works in
   our favour, but raw-RGB effects and `gamma_correct: 1.0` both remove the cushion. **Size the
   supply for the linear case.**

Current is linear in PWM duty (confirmed from WLED source and QuinLED bench data: 50% brightness =
48.7% of full-white power). Model: `I = 60 + 3600 × duty` mA.

---

## 6. Open questions

**Blocking the BOM — needs Sam's answer:**

1. **Is the WLED matrix 16×16 or 8×32?** 16×16 → the ring purchase may be unnecessary.
2. **Must the Voice PE stay stock?** The `intent_script` override silences its own ring and chime.
3. **Multi-timer / named timers — required or nice-to-have?**
4. **Is there spare WS2812B strip on hand?** (Sam runs xLights shows — likely.) At 144 LEDs/m, 60
   LEDs makes a 132.6 mm circle; at 96/m, 198.9 mm; at 60/m, 318.3 mm.

**Needs a bench test before spending money:**

5. **`intent_script` override actually loads after `intent`.** ~20 min. **Gates the whole primary path.**
6. `POST /api/intent/handle {"name":"HassTimerStatus"}` really returns `speech_slots.timers[]`.
7. WLED built-in overlay + `ledmap.json` renders a 60-point perimeter clock.
8. `markusressel/ESPHome-Analog-Clock` compiles against ESPHome 2026.8.0.
9. Does reflashing a retail Voice PE preserve official OTA updates? **Unverified in every pass.**
10. Flicker on `esp32_rmt_led_strip` — no root cause established upstream.
11. Does `text_sensor: platform: homeassistant` with `attribute: finishes_at` re-push when a timer
    restarts to the *same* `finishes_at`?
12. Lateral bend of flat strip, if the cut-strip route is chosen — flat strip bends only
    perpendicular to the PCB, so a viewer-facing flat circle needs zigzag stock or ~180 hand-soldered
    joints. Confirm stock availability before committing.

---

## 7. Exact names for the firmware

**Intents to override in `intent_script:`** — `HassStartTimer`, `HassCancelTimer`, `HassPauseTimer`,
`HassUnpauseTimer`, `HassTimerStatus`, `HassIncreaseTimer`, `HassDecreaseTimer`

**`timer` helper entity** — state `idle` / `active` / `paused`; attributes `duration`, `editable`,
`last_transition`, `finishes_at`, `remaining`, `restore`

> ⚠️ **`remaining` does NOT tick down while active.** It is set once at start and only recomputed on
> pause/change. **Use `finishes_at` (ISO-8601) for live progress.** (verified in `async_start`)
>
> ⚠️ **`duration` and `remaining` are `H:MM:SS` strings**, so `sensor: platform: homeassistant`
> (numeric-only) **cannot import them**. Use `text_sensor`.

**`timer` bus events** — `timer.started`, `.restarted`, `.paused`, `.cancelled`, `.changed`, `.finished`
**`timer` trigger platform** (2026.5+, present in 2026.8.2) — `started`, `paused`, `restarted`,
`cancelled`, `finished`, `remaining_time_reached`
**`timer` services** — `timer.start` (field `duration`), `.pause`, `.cancel`, `.change`, `.finish`, `.reload`

**ESPHome HA→device import** — `homeassistant` platform, schema is exactly 3 keys: `entity_id`
(required), `attribute`, `internal` (default `true`). `USE_API_HOMEASSISTANT_STATES` is auto-defined;
`api: homeassistant_states: true` is **not** needed.

**ESPHome device→HA push** — `homeassistant.action:` (current name; `homeassistant.service:` still
works). Requires per-device *"Allow the device to perform Home Assistant actions"*.
Also available: `homeassistant.event`, `api: actions:`, `on_client_connected` /
`on_client_disconnected`, condition `api.connected`.

> ⚠️ `api: password:` was **removed in ESPHome 2026.1.0**. Use `api: encryption: key:`. (verified —
> Sam's recollection was correct.)

---

## Sources

Primary sources fetched and quoted, not summarised from memory. Full per-claim source URLs are in
the raw research artefacts. Load-bearing ones:

- `raw.githubusercontent.com/home-assistant/core/2026.8.2/homeassistant/components/intent/timers.py`
- `raw.githubusercontent.com/home-assistant/core/2026.8.2/homeassistant/components/intent/__init__.py`
- `esphome.io/components/light/esp32_rmt_led_strip.html`, `/components/api.html`, `/components/light/index.html`
- `github.com/markusressel/ESPHome-Analog-Clock`, `github.com/esphome/home-assistant-voice-pe`
- `github.com/djelibeybi/voice-assistant-persistent-timers`
- `raw.githubusercontent.com/wled/WLED/main/wled00/{overlay.cpp,bus_manager.cpp,const.h}`
- WS2812B V1.0 datasheet (SparkFun mirror); WS2812B-V5 datasheet; ESP32 datasheet (Espressif)
- Adafruit NeoPixel Überguide; `kno.wled.ge/basics/faq/`; `quinled.info` data-wire + injection guides
