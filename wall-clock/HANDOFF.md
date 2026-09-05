# Handoff to a local Claude session

---

# STATE AS OF 2026-09-05

Read this part first. Everything below it is older and still true, but this is
where the project actually is. Branch `claude/home-assistant-wall-clock-om42v2`
in both repos; tip **`070a7f3`**, firmware **`2726b0a`**.

> **CONFIRMED FIXED ON THE HARDWARE, 2026-09-05.** Sam, after flashing
> `06765c3`: "I flashed it, it doesn't flicker!" Eleven builds and ten wrong
> theories. What follows is why, kept because the mechanism explains several
> other things about this panel and because the A/B is still one switch away.

## The flicker: found, and it was the animator

The panel scans itself out of GRAM about sixty times a second. We write GRAM
over SPI, asynchronously, and a whole 360 x 360 frame is 259200 bytes -- 104 ms
at 20 MHz, six scans long. So the write walks down the glass while the scan
walks down the glass, they cross each other several times on the way, and every
crossing is visible. Over something that is CHANGING it reads as motion. Over
something being rewritten with the pixels it already had, it reads as a blink.

That is Sam's list, exactly:

| element | what it was doing | what he saw |
|---|---|---|
| eyes | change every frame | animation |
| z's | change every frame | animation |
| time | was not being redrawn | steady |
| moon | redrawn, never changes | **flickered** |
| stars | redrawn, never changes | **flickered** |

It is also the one measurement none of the ten theories fitted: with the
animator OFF the panel is perfectly steady, because then a full frame only goes
out when something actually changed, and one crossing a minute is not a
flicker. `c635533` had already removed the unconditional 1 Hz repaint. What was
left was the ANIMATOR: `grow_partial` defaulted OFF, so every animation frame
repainted all 360 x 360 at up to 4 Hz.

The init sequence turns TE on (0x35) but `mipi_spi` has no TE input, so the
write cannot be synced to the scan. The only lever is to write less.

**The fix, `2726b0a`.** `grow_partial` now defaults ON and an animation frame
repaints y 60..239 and nothing else. The sky, the star row, "shh" and the time
are left exactly as they are.

Three things had to be true for that to work, and all three are in the lambda's
"THE ANIMATION BOX" comment:

1. Every band must come back non-empty or `mipi_spi` RETURNS and abandons the
   rest of the frame. A 4 px column of field-coloured pixels down the far left,
   drawn only in the rows the box does not cover, marks them. On a round panel
   the glass at those rows does not reach x = 4, so it is off the picture.
2. That marker must never share a band with the box. The driver flushes the
   BOUNDING BOX of what was drawn, and anything inside it this pass did not
   write goes out as the previous band's contents. So `buffer_size` is pinned
   at **17%** -- bands of exactly 60 rows -- and 60 and 240 are multiples of 60.
   **Change one, change the other.** 45-row bands cannot be aligned without
   cutting through the z's.
3. The sky moved up to `CY - 144` so its longest ray stops at 58, clear of the
   box; the countdown moved to `CY + 40`, inside it, and suppresses the yawn.

**And the clip had to be drawn band by band, `06765c3`.** MEASURED, END TO END:
385 ms a frame before, **174 ms after** (six samples on 41eecc5: 176, 174, 174,
216, 174, 179; the 216 is a collision with the 1 s dispatcher). A 55% cut, and
the first build where a frame fits comfortably inside the animation interval --
at the 300 ms default the loop is busy about 60% of the time rather than over
100%, which is why every earlier value of that dial behaved identically.

The first version of it was measured on the bench at **385 ms a frame against
the full repaint's 269** -- 43% SLOWER than the thing it replaced. It drew its whole 248 x 180
rectangle on all six band passes and let `draw_pixel_at` reject five sixths of
it one pixel at a time: 272160 calls to lay down 45360 pixels. The SPI bus was
never the constraint; the draw loop was. Every rectangle is intersected with
the band now, the eye block is skipped in the three bands it cannot reach, and
the band index is counted in `an_band` because the driver does not expose it.

`grow_anim_ms` floors at 400 ms for the same reason: a dial should not offer an
interval the loop cannot honour.

**The A/B, if it ever comes back:** turn `grow_partial` OFF. The moon and the
star row should start blinking again within seconds. If they do not, the
diagnosis above is wrong and the next candidates are the panel flex, the SPI
jumpers and `-s lcd_hz 10MHz`.

## Why a dial sometimes reverts after a flash, and why it is not alarming

Filed wrongly three times as "restore_value clamps to an endpoint". It does
not. The verified rule, from a controlled comparison inside a single flash on
2026-09-05 (2726b0a -> 41eecc5):

| number | traits | stored | after the flash |
|---|---|---|---|
| `grow_anim_ms` | min 250 -> **200, changed** | 600 | **300**, the new `initial_value` |
| `ring_size` | 8..60, **unchanged** | 24 | **24**, survived |

So: **change a number's min, max or step and its stored value is discarded and
it takes the firmware's new default.** Leave the range alone and a customised
value survives any number of reflashes. That is benign -- it lands on the
intended default, not on an endpoint -- and it is worth knowing only so that
nobody spends an afternoon on it again.

WHAT IS STILL NOT EXPLAINED, kept because pretending otherwise is how this got
mis-filed the first time: on 2026-09-04 `grow_ring_day_bright` read 5 and
`grow_ring_night_bright` read 2, when their ranges had NOT changed and their
`initial_value`s were 25 and 7. Those were stored values, and where they came
from is unknown. One candidate nobody has checked: ESPHome batches preference
writes, so a value set in Home Assistant and then reflashed over within the
minute is lost before it reaches flash. Plausible, unverified, and it would fit
-- the bench had set those two by hand shortly before.

## The base: a back-stand, not a plinth

`070a7f3`. The stand-box is superseded by **`mini-round-clock-backstand-32`**:
one part, 51.1 cm3, 98 x 86 x 48 mm, no lid, no tray, no screws. The clock sits
on the desk and beds 4 mm into a trench in the foot; two A-frame buttresses
take the 14-degree lean; the board bay between them is an open channel with a
30.60 mm slot and one retaining lip. The board lies flat -- the four posts came
out on 2026-09-05 at Sam's request. `PRINT-TOMORROW.md` in
`enclosure/mini/v2/` is the print sheet.

**Sam's board is 30.00 mm**, not the 29.00 the old tray was cut for. Both parts
and the fit gauge are corrected.

There is one for **every body**, and the 24's is the UNTAGGED file --
`mini-round-clock-backstand.stl`, same convention as `mini-round-clock-base`.
The 24's stand is the same 98 mm wide as the 32's because the footprint scales
with the clock but the board does not.

| file | body | size mm | vol |
|---|---|---|---|
| `mini-round-clock-backstand` | 24 LED, O108 | 98.0 x 83.4 x 43.2 | 47.6 cm3 |
| `mini-round-clock-backstand-32` | 32 LED, O119.9 | 98.0 x 86.3 x 48.0 | 51.1 cm3 |
| `mini-round-clock-backstand-60` | 60 LED, O240 | 191.2 x 134.4 x 96.1 | 255.5 cm3 |

`check7_backstand.py` is new; `runchecks.sh` runs it once per body. It measures
off the exported mesh, never off the parameters.

### Holding the board down: a bar, or zip ties

Two ways, and they are ALTERNATIVES, not companions -- the bar's plate lies
right across where the board zip ties have to go.

* `mini-round-clock-backstand-clamp` -- a bridge that stands over the USB shell
  and the module and comes down on the bare PCB at each end. Two M2 x 6
  self-tappers. It prints FEET UP, with THIS SIDE DOWN debossed on the face
  that prints first.
* six 2.00 mm zip-tie slots in the foot, in three pairs: board (|x| = 26),
  leads either side of the cable gate (|x| = 16), USB (|x| = 35.5).

**Every tie pair is joined by a 1.20 mm relief milled into the foot's
underside**, and that is the part worth remembering. Two plain holes through a
foot that sits on a desk put the tie's loop under the part and the stand rocks
on it. The relief is deeper than a 2.5 mm tie is thick, so the loop is recessed
and the foot still lies flat. `render_ties.py` draws the plan view.

## Do not put this back in any flashing recipe

`git checkout FETCH_HEAD -- wall-clock/esphome/mini-round-clock-with-display.yaml`

Sam keeps uncommitted work in that file -- 134 lines of it as of 2026-09-05 --
and that command destroys it without asking. Flash from a detached worktree at
the branch tip instead; it produces byte-identical firmware and touches nothing
of his.

## Switches added during the hunt, and what each is for

| entity | default | what it does |
|---|---|---|
| `Grow clock flat art (test)` | off | the INSTRUMENT. Square moon and dots. Ugly on purpose; turn it back off after reading it |
| `Grow clock blocky art` | off | the FIX if the test confirms. Pixel-art crescent + crossed-bar sparkles |
| `Grow clock partial redraw (test)` | off | on = the old partial repaint. Off = every repaint is a full frame, as the first working build effectively had |
| `Screen freeze (test)` | off | stops **all** panel writes and backlight changes. Flicker with this on = hardware |
| `Grow clock repaint every second` | off | on = the old unconditional 1 Hz repaint |
| `Ring current limit` | 400 mA | WS2812 budget; 32 LEDs can ask for 1.9 A |
| `Firmware built` (sensor) | — | compiler `__DATE__ __TIME__`. **Check this postdates your flash before trusting any observation** |
| `Grow clock frame time` (sensor) | — | ms per frame. Asked for ten times, never yet read |

## Real bugs fixed along the way (these stay fixed)

* The digital time was being repainted 60×/minute unchanged — now on a content
  key, once a minute.
* Backlight had no `default_transition_length`, so it inherited ESPHome's **1 s
  default** and ramped on every change. Now `0s`.
* Round panel SPI was raised to 40 MHz mid-hunt; the GC9B72 library documents
  ~20 MHz **on short leads** and says go lower on jumpers. Back to 20 via the
  `lcd_hz` substitution.
* Smile arc was overdrawing the clock's time every animation frame.

## Enclosure: done, ready to print

`57bce1b`. **`mini-round-clock-standbox-32.3mf` + `-standbox-tray-32.3mf`.**
See `enclosure/mini/v2/PRINT-TOMORROW.md`.

The tray used to be cut from the drawing's 28.19 mm board, putting the rails
**28.99 apart against a 29.00 board** — a negative fit that could never have
worked. Now `STANDBOX_SLOT_W = 30.20`, measured off the built STL. **If the
board is sloppy set 29.80, if tight 30.60**, then re-run `build_v2.py`. All six
checks pass.

## Blocked, needing Samuel's hands

* **The flash route is dead.** Seven pokes to the bench session, all delivered,
  none executed. Flash directly instead — the command is in "How to resume on
  Windows" below.
* Clocks 1 and 2 are off the network (task #27).
* HA packages still not installed: ports 22/445 closed on the guest. Needs the
  Samba share or Terminal & SSH add-on. Note the hypervisor `.66` **does** have
  SSH if you need file access to the VM's host.

---


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

## State when this was FIRST handed over (historical — see the top of this file for current state)

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

## Flashing from the bench

The clock is on the bench PC over USB, not on the network the cloud session
can see, so every flash is a hands step. What the bench session settled:

- Run `esphome` from the PowerShell where its venv is active, with
  `$env:ESPHOME_ESP_IDF_PREFIX = "K:\idf"` set first, or the ESP-IDF toolchain
  re-downloads into the profile and the build fails on path length.
- Never pipe the compile through `tail` or `Select-Object -Last`; it hides the
  error and the exit code.
### THE BOARDS ON THIS BENCH, BY MAC. READ THIS BEFORE YOU FLASH ANYTHING.

THE TABLE IS THE AUTHORITY, NOT THE PORT AND NOT THE PANEL. Every one of
these boards is an ESP32-S3 carrying the same 2.1in GC9B72, so they are
indistinguishable on a bench by sight or by what is plugged in where.

| MAC | what it is | do |
|---|---|---|
| `ac:27:6e:a4:cd:98` | clock #2, `mini-round-clock-2`, 32 LED | flash as clock #2 |
| `ac:27:6e:a3:3b:ac` | **Zac's Clock** (clock #3), 192.168.1.69, **24 LED** | flash as clock #3 only |
| `ac:27:6e:a3:de:6c` | **Jake's Clock** (clock #4), 2026-09-05. Was Sam's Flight Deck; he rewired it. Same wiring as clock 3, **32 LED**. COM10, **192.168.1.68**, `mini-round-clock-4.local`, 112 entities. Kept the Flight Deck's DHCP lease | flash as clock #4 |
| anything else | unknown board | report the MAC and STOP |

2026-09-05, MORNING: Sam said "the second ESP 32 plugged into the computer,
flash it", twice. The second ESP32 on USB was then his **Flight Deck**, and
clock firmware would have destroyed it. He has since rewired that board into
clock #4, so the row above has changed and the near-miss is history -- but the
RULE is not, and this is why it exists. It carries the same 2.1in GC9B72 panel as the clocks,
which is exactly why it looks like one on a bench. The bench session read its
MAC, found no match, stopped, and only then read its boot banner:

    [deck] board profile 2 2.1in GC9B72 (ACTIVE_BOARD)
    [deck] up. mode=radar wifi=OK ip=192.168.1.68

**NEVER RUN esptool AT A CLOCK THAT IS IN SERVICE.** It reads the chip by
driving DTR/RTS into the ROM bootloader, and **it LEAVES THE CHIP THERE.** It
does not hand the board back. Measured on 2026-09-05: `read-mac` on COM11 took
clock 3 off the network entirely -- 1 of 112 entities available, mDNS gone,
.69 not answering -- and it stayed that way until the bench toggled DTR/RTS by
hand, after which it came straight back to 112 of 112.

(An earlier version of this note said it recovers on esptool's own hard reset.
That was wrong, it was written here from assumption rather than measurement,
and the bench found it out the hard way. If you must read the MAC of a LIVE
board, take it from the ESPHome boot banner instead, or expect to power-cycle
it afterwards. On a board you are about to overwrite anyway, none of this
matters.)

The flash task for clock #4 opened by "validating the method" against clock 3,
and it should never have been touched: COM10's expected MAC was already known
from the previous run, so the target could have been checked against its own
known value and nothing in service needed disturbing. If a method needs
proving, prove it on the board you are about to write to.

**Read the MAC with `python -m esptool --port COMx read-mac`, not off a boot
banner.** It reads the chip whatever firmware is on it, so it also works on a
blank board, and it is the only identification that cannot be faked by a
device that merely looks familiar. Validate the method against a known board
first -- COM11 must return `ac:27:6e:a3:3b:ac`.

- Clock #1 (round 360x360, 24 LEDs, `mini-round-clock`) is **COM7**. Clock #2
  (`mini-round-clock-2`, 32 LEDs) is **COM12**, and needs its substitutions on
  the command line. Clock 3 (`mini-round-clock-3`, 32 LEDs) is **COM11** and
  **192.168.1.69**.
- **THE OLD IP ADDRESSES ARE GONE.** Clock #1 was 192.168.1.23 and clock #2
  was .64; as of 2026-09-03 neither answers. .23 now belongs to something
  else entirely -- MAC C4-E7-AE-16-6B-A6 where the clocks are `ac:27:6e:*`,
  port 80 open, 3232 and 6053 closed. **Do not flash blind at a recorded
  address**: check the MAC or the mDNS name first, or you will push clock
  firmware at a stranger's device. Neither `mini-round-clock.local` nor
  `mini-round-clock-2.local` resolves. Both boards are off the network and
  cannot be flashed until they are back on it.
- Flash with the LED supply unplugged; USB and the external 5 V together can
  damage the board.

```powershell
$env:ESPHOME_ESP_IDF_PREFIX = "K:\idf"
cd <repo>\wall-clock\esphome

# clock #1, over USB
esphome run mini-round-clock-with-display.yaml --device COM7

# the same, over the air once it is on WiFi
esphome run mini-round-clock-with-display.yaml --device 192.168.1.23

# clock #2
esphome run mini-round-clock-with-display.yaml --device COM12 `
  -s device_name mini-round-clock-2 -s friendly_name "Mini Round Clock 2" -s num_leds 32

# clock 3 -- the third board, 2026-09-03. THE ONE THAT IS ACTUALLY RUNNING.
# COM11 on the bench; 192.168.1.69, MAC ac:27:6e:a3:3b:ac,
# mini-round-clock-3.local. 24 LEDs -- Sam, 2026-09-05: "Zac's is the 24 LED
# board. num_leds is only the compile-time DEFAULT in any case; the ring size
# is a runtime number in Home Assistant with a ceiling of 60.
esphome -s device_name mini-round-clock-3 -s friendly_name "Mini Round Clock 3" `
  -s num_leds 24 run mini-round-clock-with-display.yaml --device COM11

# clock 4 -- "Jake's Clock". COM10, 192.168.1.68, ac:27:6e:a3:de:6c. 32 LEDs.
esphome -s device_name mini-round-clock-4 -s friendly_name "Mini Round Clock 4" `
  -s num_leds 32 run mini-round-clock-with-display.yaml --device COM10
```

**Identify a board before writing to it.** `esphome logs
mini-round-clock-with-display.yaml --device COMx`, or any serial monitor at
115200, prints the ESPHome banner with the device's name in it. Flashing a
clock with another clock's substitutions renames it in Home Assistant and
leaves the old entities behind as orphans.

`esphome run` compiles, uploads and then opens the log; watch for the
`[app]` banner once (a repeating banner is a boot loop) and `Boot: ring +
display up`. Ctrl-C leaves the clock running.

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
