# Phase 2 — Bill of Materials

Priced 2026-08-21, AUD inc GST. **Nothing ordered. Waiting on Sam's approval.**

Every line is tagged **(verified)** — a live product page was fetched and the price/SKU/stock read off
it — or **(unverified)** — could not be loaded, treat the number as indicative.

---

## Design settled

| | |
|---|---|
| Light source | One-piece **WS2812B 60-LED ring, 172 mm OD / 156 mm ID** (Sam's choice) |
| LED circle | 164 mm diameter, 8.59 mm pitch |
| Enclosure body | ~196 mm OD — **prints in one piece** on the P1S / X2D (256 mm bed) |
| Face | ~196 mm — fits the Aura's 305 mm bed with room to spare |
| MCU | ESP32-S3, no display, no audio |
| Centre display | **None.** GC9A01 rejected — see §4 |

This supersedes the earlier 74 LEDs/m strip plan (258 mm, 12 soldered segments). The ring is smaller
but removes all the fabrication risk, and it makes the enclosure a single print instead of four arcs.

---

## 1. Buy list

| # | Item | Source | SKU | AUD | Status |
|---|---|---|---|---|---|
| 1 | WS2812B 60-LED ring, 172 mm | AliExpress | — | **~$10–25** | **unverified** — see §2 |
| 2 | ESP32-S3 Mini dev board (4 MB flash, 2 MB PSRAM, USB-C adapter incl.) | Core Electronics | `WS-27070` | **$9.85** | verified — 17 in stock |
| 3 | 74AHCT125 quad level shifter, DIP | Core Electronics | `ADA1787` | **$2.95** | verified — in stock |
| 4 | 1000 µF 25 V electrolytic capacitor | Core Electronics | `COM-08982` | **$0.98** | verified — in stock |
| 5 | Resistor pack, 600 pc / 30 values (contains the 470 Ω) | Core Electronics | `CE05092` | **$2.95** | verified — in stock |
| 6 | 5 V 4 A plugpack, AU plug, 2.1 mm centre-positive | Core Electronics | `AM8911B` | **$30.60** | verified — in stock, MEPS approved |
| 7 | Panel-mount 2.1 mm DC barrel jack | Core Electronics | `ADA610` | **$5.45** | verified — in stock |
| 8 | 3 mm plywood, ~250 × 250 mm, for the face | local / Glowforge | — | ~$10–20 | unverified |
| 9 | White PLA for the diffuser | **already owned** | — | $0 | — |
| 10 | Hookup wire, heatshrink, solder | **already owned** | — | $0 | — |
| ~~11~~ | ~~USB-C breakout (ADA4090)~~ | — | — | ~~$5.40~~ | **withdrawn, v6** |

Item 11 was added when the enclosure grew a USB-C inlet through the wall, and is
**withdrawn** — Sam: *"I dont want to use a breakout board for power, move the
board more towards the edge so that the power can be connected easily."* The
ESP32-S3 now sits in the rear housing with its own connector looking out through
a 22 × 6 mm window in the rim, so there is nothing to buy and nothing to solder
for the power inlet. See `enclosure/mini/v2/README.md` §2.

**Nothing has been added to this BOM since it was approved.**

**Core Electronics subtotal: $52.78** + shipping ($7 standard / $11 express, or free Newcastle pickup)
**Estimated total: $80–110** depending on the ring and the plywood.

### Check the shed before ordering

Sam runs xLights Christmas shows and has a DMX/Art-Net controller project, so several of these are
likely already on hand. Worth ten minutes before checkout:

- **An ESP32 board** (−$9.85). Any ESP32 or ESP32-S3 works. Plain ESP32 is technically the *better*
  RMT host here (8 TX channels / 512 symbols vs the S3's 4 / 192); the S3 is recommended only because
  Core no longer stocks a cheap plain WROOM-32 devkit. **If there's a spare in the xLights box, use it.**
- **A 470 Ω resistor** (−$2.95) — any ¼ W 300–500 Ω will do.
- **A 5 V supply** (−$30.60) — but read §3 before reusing an uncertified one.
- **Spare WS2812B strip** — not needed for the build now, but a 10-LED offcut makes the perfect bench
  rig for Phase 3 firmware work before the ring arrives.

---

## 2. The one thing to check on the AliExpress listing

The ring price could not be verified — AliExpress returns HTTP 503 or a login redirect to every
automated fetch, on five separate attempts. The **$10–25** figure is indicative only.

The **172 mm OD / 156 mm ID** dimensions are corroborated by three independent resellers (Grandado,
Thornsun, Cool Components) but **not by a manufacturer datasheet**. Two things to confirm on the
listing before ordering:

1. **That it is genuinely one piece.** Many "60 LED ring" listings ship as **four quarter-arcs you
   solder together** — that is what Adafruit's PID 1768 is, and it's what the AU stockists carry
   (4 × $18.90 = $75.60 at Core Electronics). If Sam's listing is quarter-arcs, it's still fine, just
   three extra solder joints and a different price.
2. **That it states 172 mm.** Some 60-LED rings are 170 mm and a few are quite different. The
   enclosure will be drawn parametrically so a measured value drops straight in, but the printed
   part can't be finalised until the real ring is in hand and measured with calipers.

GST note: imports under A$1000 have 10% GST collected by the platform at checkout, so an AliExpress
price shown to an AU buyer is already GST-inclusive. *(likely — from ATO guidance, the ATO page
itself 403s to direct fetch.)*

---

## 3. Electrical — the gotchas, answered

### Power budget

The **3.6 A figure in the brief is a worst-case ceiling, not a spec.** The original WS2812B datasheet
contains no current specification at all; the 60 mA/LED number originates in Adafruit's Überguide.
The current production part, **WS2812B-V5, specifies 12 mA per channel = 36 mA/LED** at full white.
Sellers rarely state which revision they ship, so **size for 60 mA anyway** — it costs $0 to be right.

| Case | Ring | + ESP32 |
|---|---|---|
| All 60 pixels, full white, no cap | 3.66 A | **3.78 A** |
| 60 % brightness cap | 2.22 A | 2.34 A |
| 35 % brightness cap | 1.32 A | 1.44 A |
| Typical clock face (~15 lit pixels) | 0.96 A | **1.08 A** |

**A 5 V 4 A supply is the right call.** QuinLED's rule is not to exceed 80 % continuous, giving
3.2 A usable — which covers the absolute worst case with margin, and means **the brightness cap is a
comfort setting, not a safety mechanism.** That is the right way round. (A 3 A supply would work but
only *because* of the cap, which makes a firmware bug into an electrical problem.)

> ⚠️ **The 60 LEDs still draw ~40–60 mA with everything "off"** (0.6–1 mA/LED standby). Irrelevant for
> PSU sizing, but it means the ring is never truly off.

> ⚠️ **ESPHome's `max_power` cannot cap an addressable strip.** It is documented as float-outputs-only
> (PWM, AC dimmer, sigma-delta) and does not reach `esp32_rmt_led_strip`. The cap has to be enforced
> inside the lambda. Flagged for Phase 3. *(verified — and it's exactly the kind of thing that looks
> like it works until you measure it.)*

> Note `gamma_correct` defaults to 2.8, so a UI brightness of 50 % is really ~14 % duty. That works in
> our favour, but raw-RGB writes and `gamma_correct: 1.0` both remove the cushion — **size the supply
> for the linear case**, which is what the table above does.

### Level shifter: yes, buy it — $2.95

Not a judgement call once the datasheets are side by side:

| | Guaranteed |
|---|---|
| ESP32 output high (`VOH`) | **0.8 × VDD = 2.64 V** |
| WS2812B original requires (`VIH`) | 0.7 × VDD = **3.5 V** |
| WS2812B-V5 requires (relaxed) | flat **2.7 V** |

The ESP32 is out of spec against **both** revisions at worst case. It usually works because a real
ESP32 sources ~3.2–3.3 V unloaded — that is the whole "everyone gets away with it" phenomenon, and
Adafruit openly admits relying on it: *"Even in our own projects, we'll often leave this part out."*
Their own conclusion is the one to act on: *"you're taking that small chance of unreliable operation,
or 'works on-desk but not in-field.'"* This is going on a wall. Buy the $2.95 part.

**It must be the HCT family** — 74**AHCT**125 has a flat 2.0 V TTL input threshold. A plain 74HC125
needs 3.5 V in and will not work. (Alternative if preferred: Adafruit Pixel Shifter `ADA6066`, $8.10,
in stock — same job, no breadboarding.)

### The rest

- **Series resistor 470 Ω**, on the data line, at the **ring** end of the wire — not the ESP32 end.
  (With the AHCT125 fitted, put it on the shifter's output.)
- **Bulk capacitor 1000 µF** across the ring's +5 V / GND, **at the ring**, fitted before first
  power-up. 25 V part is electrically fine on a 5 V rail, just physically bigger.
- **No power injection needed.** WLED's threshold is 150 LEDs; a single edge feed is rated to 4 A.
- **Common ground is mandatory** between ESP32, PSU and ring. Ground on first, off last.
- **Power-up order:** energise the ring **before** the ESP32, or it back-powers parasitically through
  the data pin and can damage the MCU.
- **Never USB and the PSU at the same time.** Espressif is categorical: *"The power supply must be
  provided using one and only one of the options above, otherwise the board and/or the power supply
  source can be damaged."* Flash once over USB with the PSU unplugged, then use OTA forever.

### Why the $30.60 supply and not the $15 one

Zaitronics list a 5 V 4 A AU-plug supply (`Z0180`) at **$15.00** — half the price. Their listing
states **no RCM or SAA approval** and doesn't specify jack polarity, and it's on a 5–10 day lead.

The Core Electronics `AM8911B` is **MEPS approved** and in stock. For a mains-powered device that will
be **permanently mounted on a kitchen wall in an Australian home**, that $15 difference buys
compliance and a known-good polarity. Sam's call, but that's the recommendation and the reason.

---

## 4. GC9A01 centre display — recommended against

Verdict: **skip it.** The argument is physical, not software.

The 1.28" module's active area is Ø32.4 mm. Four digits and a colon inscribed in a 240 px circle caps
digit height at ~88 px = **11.9 mm**. By the standard signage rule (1 inch of height per 10 feet of
viewing distance) that is legible to about **1.4 m**. A kitchen glance is 3–5 m and wants 30–50 mm
digits. It's short by a factor of 2.5–4, and no firmware tuning fixes that. Meanwhile the ring behind
it — high-contrast point sources — is already readable from the doorway.

To be fair about what *isn't* a problem, since the usual objections don't hold: ESPHome support is
current and native (`platform: mipi_spi`, `model: GC9A01A`); PSRAM is **not** required (ESPHome
auto-allocates a 19,200-byte partial buffer on a plain ESP32); there's no RMT pin conflict; and the
two recent `mipi_spi` regressions are already fixed in 2026.8.2.

The real cost is the main loop. The GC9A01A model carries no `data_rate` override, so it inherits the
10 MHz default — about **92 ms of pure SPI per full redraw**, against ESPHome's 50 ms blocking-warning
threshold — and the partial buffer means the drawing lambda runs **six times per update**. At the
default 1 s interval that's a ~100 ms stall every second: **a visible hitch in the ring animation.**
It won't garble the LEDs (RMT is hardware-timed and asynchronous), but it will make them stutter.

Saves $10.40 (Zaitronics `Z0241`) to $32.55 (Adafruit `ADA6178`), and a bring-up session.

*If Sam wants it anyway:* set `data_rate: 40MHz`, `update_interval: never` driven from an `on_time`
minute trigger, and restrict `glyphs: "0123456789:"`. Those three are non-negotiable.

---

## 5. Enclosure material — the Aura changes the answer

The brief said "cast acrylic or plywood only, and tell me which and why". The answer is
**plywood for the laser, white PLA for the diffuser** — and the reason is specific to Sam's machine.

**The Glowforge Aura is a ~5 W diode laser, not a CO₂ laser. It physically cannot cut clear, white or
translucent acrylic** — those materials are largely transparent to the diode's wavelength, so the beam
passes through without depositing enough energy. Glowforge's own material set for the Aura is limited
to *opaque* acrylic (teal, black, red, orange, green, purple).

That rules out acrylic for the one part that needs it: **the diffuser must be white or translucent by
definition.** So:

- **Glowforge Aura → 3 mm plywood** for the face/bezel and the engraved hour markers. Cuts and
  engraves well, looks good in a kitchen, and it's opaque so the diode has no trouble.
- **Bambu → white PLA** for the diffuser, printed thin (0.8–1.2 mm). This is the standard modern
  approach for LED diffusion and gives *better* pixel separation than a flat acrylic sheet, because
  the 60 cells can be printed as individual light wells with baffles between them.

Sam's PVC warning still stands and is correct — **never PVC or any chlorine-containing sheet**, it
releases hydrogen chloride which wrecks the optics and is a genuine hazard. Nothing in this BOM is PVC.

---

## 6. What is still unverified

1. **Ring price and exact dimensions** — AliExpress unfetchable. Confirm one-piece + 172 mm on the
   listing; measure with calipers on arrival before the enclosure is finalised.
2. **Plywood price** — depends on local supplier / Proofgrade.
3. **ESP32-S3 `VOH`** — the 2.64 V figure is from the original ESP32 datasheet. The S3 is very likely
   the same 0.8 × VDD, but it wasn't separately confirmed. Doesn't change the recommendation (the
   level shifter makes it moot).
4. **How to actually enforce a brightness cap on an addressable strip in ESPHome.** The *negative* is
   verified (`max_power` won't do it); the positive mechanism is a Phase 3 task.
