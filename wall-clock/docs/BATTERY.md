# Battery — the decision, and the arithmetic behind it

**Nothing has been ordered.** Per the standing rule, this is a recommendation
with prices, not a purchase.

---

## The short version

**A battery that fits this clock cannot run it. It is a UPS for outages.**

The clock draws 0.94 W continuously — **22.6 Wh a day**. The largest battery that
fits a 108 mm disc holds about 16 Wh once boost losses are taken out. That is
**17 hours**. It does not survive a day, and nothing that fits does better.

If you want it on battery day to day, that is not this clock; it would need a
brick roughly the size of the clock itself.

If you want it to ride through a power cut without losing the time and the
Home Assistant connection, that works, and the part below is the one to buy.

---

## 1. What it actually draws

From datasheets, not estimates, except where marked.

| Load | typical | worst | basis |
|---|---:|---:|---|
| ESP32-S3-N16R8 devkit, WiFi associated, HA API connected | 60 mA | 140 mA | Espressif measured **(verified)** |
| Mokungi 24-LED WS2812B ring, clock face at ~25% | 33 mA | 145 mA | WS2812B-V5 datasheet **(verified)** |
| 2.1" 360×360 GC9B72 + backlight | 95 mA | 150 mA | **(assumed — extrapolated)** |
| **at 5 V** | **188 mA** | **435 mA** | |
| | **0.94 W** | **2.18 W** | |

Four things worth knowing about those numbers.

**The ESP32 figure hangs on one YAML line.** ESPHome defaults
`power_save_mode: light`, which maps to Espressif's `WIFI_PS_MIN_MODEM` — their
own measurement for that state is 40.1 mA average. Setting `power_save_mode:
none`, a common fix for API latency, parks the modem in continuous RX and more
than doubles the figure to ~140 mA. **Check the YAML before trusting the budget.**

**The 60 mA figure is a linear regulator's, and that matters thermally.** The
DevKitC-1 uses an LDO, not a buck, so it burns (5 − 3.3) × I as heat: 0.10 W at
60 mA, 0.24 W at 140 mA, inside the box.

**The worst case in the table is not the worst case.** A full-ring amber alert
flash is ~202 mA on the ring alone at 30% brightness, taking the total to about
490 mA; at 100% ring brightness the ring alone is ~593 mA and the total ~880 mA.
ESPHome's `max_power` cannot cap an addressable strip — the only limit is the
lambda. **Size any supply for 1 A at 5 V**, not 435 mA.

**The display is both the largest load and the least certain.** 95 mA is
extrapolated from a smaller GC9A01 module, because the 2.1" vendor drawing lists
luminance as "TBA" and gives no LED current at all. It could plausibly be 50 mA
or 100 mA. **Ten minutes with an inline meter settles it**, and it could change
the answer below.

### The free 30%

The backlight is ~85% of the display's draw and dims close to linearly with PWM.
At 30% backlight the display falls from 95 mA to ~38 mA, taking the total to
**131 mA / 0.66 W** — and a clock face at 30% backlight at night is not something
anyone complains about. That is the single largest lever available and it costs
nothing.

---

## 2. Why almost nothing fits

The pocket takes **up to 80 × 38 × 26 mm** (or 78 × 45, or 77 × 50 — the limit is
a rectangle inside the 102 mm interior circle, with the wall screw's swept zone
carved out of the top; `check2_fit.py` prints the table).

A sweep of Officeworks, JB Hi-Fi, Kogan, Amazon AU, Core Electronics, Zaitronics,
PB Tech, Cygnett, Anker AU, Belkin AU, Bunnings and Scorptec found that the
market is **bifurcated, and this clock lands in the gap**:

| | | fits? |
|---|---|---|
| Cygnett ChargeUp Boost Gen4 5K | 95 × 65 × 15 | no — 115 mm diagonal |
| Anker MagGo 10K Slim | 104 × 71 × 15 | no — 126 mm diagonal |
| Anker PowerCore 10000 | 92 × 60 × 22 | no — 110 mm diagonal |
| Core Electronics AD0505B 5000 | 110 × 66 × 10 | no — 128 mm diagonal |
| Kogan 5200 brick | 102 × 46 × 22 | no |
| **Anker Nano 22.5W, A1653** | **77 × 37 × 25** | **yes** |

Slim banks are wide. Banks narrow enough for a 108 mm circle are 25–26 mm thick.
That thickness is what takes the clock from **44 mm deep to 55 mm**.

---

## 3. What to buy

### Anker Nano Power Bank, model **A1653**, 5,000 mAh — **about A$49**

| | |
|---|---|
| SKU in stock | **A1653H21** (white) at **Scorptec**, Melbourne |
| Link | https://www.scorptec.com.au/product/power-&-chargers/power-banks/109295-a1653h21 |
| Price | **A$49.00 — seen on StaticICE AU, dated 24-08-2026.** Scorptec's own page returns HTTP 403 to automated fetch, so the retailer page could not be loaded directly. **Confirm the price on screen before paying.** Anker AU's own RRP is A$59.95 and Anker direct shows Sold Out. |
| Dimensions | **76.96 × 36.83 × 24.89 mm — verified**, from Anker's US product page spec table (3.03 × 1.45 × 0.98 in). Corroborated by a hands-on review at 77 × 37 × 25 mm, 101 g. |
| Margin in the pocket | **3.7 mm** on length at its width, 1.2 mm on width, 1.5 mm on thickness |
| Pass-through | **yes — verified** from the printed Quick Start Guide: *"Simultaneous Charging and Recharging"* |
| Idle cutoff | **not a problem — verified.** Anker document a 30–90 mA minimum sustaining draw; the clock's 188 mA is 2–6× above it. The A1653 has no trickle mode, so there is nothing to re-arm after a power cut. |
| Auto-restart after full drain | **UNKNOWN — this is the one that decides it** |

Three traps, all worth knowing before you order:

- **A1259 is a different product.** 10,000 mAh, 103.9 × 52.3 × 25.9 mm. It is 24 mm
  too long and will not go in. Only **A1653**.
- **"22.5W" is marketing.** Anker's own manual says 18 W max total output. Irrelevant
  at 0.94 W, but don't size anything off 22.5.
- **Ignore Anker's support-page figure of 130 × 100 × 30 mm** — that is the retail carton.

It also looks like it is going end-of-life here: Anker AU shows it sold out, and a
national price search returns exactly one listing in the country. **If you go this
way, buy two in the same order.**

Runtime:

```
usable Wh = 5000 mAh x 3.7 V x 0.88 / 1000 = 16.28 Wh
                                             (0.88 = a synchronous 5 V boost,
                                              derated for the tail of discharge)

  16.28 / 0.94 W  =  17.3 hours   typical
  16.28 / 0.66 W  =  24.7 hours   with the backlight at 30%
  16.28 / 2.18 W  =   7.5 hours   worst case
```

### The mechanical catch, which is more likely to bite than the size

**The A1653's output is a rigid fold-out MALE USB-C plug on the body. Its single
female port is the input.** Both are bidirectional, so it can be run either way
round, but in a closed pocket that male plug has to mate with something — a
female-to-female coupler, or a lead with a socket on it — and it stands proud
when deployed.

The pocket has **15.2 mm** at the 12 o'clock end once you step off the centreline
the wall screw's head sweeps, and only 6.5 mm at 6 o'clock. A fold-out plug plus a
coupler plus a lead will not fit in 15.2 mm.

**So: check the A1653's plug and port geometry against the pocket before you
order.** The bounding box is fine with 3.7 mm to spare; the connectors are the
risk. If they do not work out, the Baseus below is a plain brick with ordinary
ports and no fold-out anything.

### Runner-up: Baseus Compact Power Bank, Type-C Edition, 5,000 mAh 20W — **A$45.99**

- **baseus.com.au, in stock, ships from Australia. Price verified.**
- **80 × 40.2 × 25.6 mm.** That lands **exactly** on the pocket's limit — 0.0 mm of
  spare length at that width, assuming 2 mm corner radii. `params.fits()` computes it.
- Mechanically simpler than the Anker: ordinary ports, nothing folds out.
- **Measure the actual unit before committing.** At zero margin, a millimetre of
  vendor optimism is the difference between it going in and not.

### Everything else

| | | fits? |
|---|---|---|
| UGREEN Nexode PB503 5000 | 79 × 38 × 26 | fits, but **no Australian stock** |
| Cygnett ChargeUp Boost Gen4 5K | 95 × 65 × 15 | no |
| Anker MagGo 10K Slim | 104 × 71 × 15 | no |
| Anker PowerCore 10000 | 92 × 60 × 22 | no |
| Core Electronics AD0505B 5000 | 110 × 66 × 10 | no |
| Kogan 5200 brick | 102 × 46 × 22 | no |
| Anker Nano A1259 10000 | 104 × 52 × 26 | no — and not the same part |

### Which way round it goes

Not a free choice. A 77 mm bank in a 102 mm circle leaves ~25 mm split between
its ends, and the 6 o'clock end has only **6.51 mm** — no plug fits there. The
12 o'clock end has **15.2 mm** once you step off the centreline the screw head
sweeps, and there is **22.8 mm** beside the battery on each side for routing.

**Ports face 12 o'clock, off centre, slim right-angle USB-C plug. The mains lead
enters at 6 o'clock and runs up the side.**

### The one thing that decides whether this works at all

**Many power banks, once flat, will not resume output when mains comes back until
someone presses the button.** On a clock 2.4 m up a wall, that means it stays
dead until someone gets a ladder.

Anker do not document A1653's behaviour: not in the Quick Start Guide (read in
full), not on the US or AU product pages, not in their support articles. Owner
reports on Reddit could not be reached from here — that is a real gap in
coverage, not evidence of absence.

There is a second failure in the same family: pass-through banks often drop their
output for about a second on the mains↔battery transition, which reboots the
ESP32 every time the power blinks — the opposite of what a UPS is for.

**Test both on the bench, before the bank goes in the clock:**

1. Clock on the bank, bank on mains. Confirm it runs.
2. **Pull mains.** The clock should carry on with no flicker and no reboot. Plug
   mains back in and watch again. *(This catches the transition dropout.)*
3. Leave it on battery until the bank goes flat and the clock dies.
4. Plug mains back in. **Touch nothing.** If the clock comes back on its own
   within a minute or two — pass. If it needs a button press — fail.

If it fails step 2 or step 4, no consumer power bank will do this job, and §4 is
the answer.

## 4. The alternative, if the bank fails the test

**Adafruit bq25185 USB / DC / Solar charger — A$13.10 at Core Electronics
(price and stock verified), or A$14.05 at Little Bird.**

A true power-path charger: the load runs off the wall adapter while the cell
charges on a separate leg, so the cell is not micro-cycled — which is the exact
thing that kills power banks in UPS duty. It supports LiFePO4 (cut the VS jumper,
bridge 3.65 V), has a jumper-selectable 250 mA / 500 mA / 1 A charge rate, and
has a thermistor input for temperature-qualified charging. There is no
auto-shutoff logic and nothing volatile to re-arm after an outage, because the
configuration is solder jumpers on pin-programmable silicon.

**But it is not a battery, and two more parts are needed, neither verified:**

- a 5 V boost, 1 A capable (Adafruit TPS61023 breakout, ~A$10 — **unverified**)
- a **protected** LiFePO4 cell — 18650 LFP 1500 mAh gives ~4.5 h
  (**part, price, stock and dimensions all unverified**)

Realistically A$45–60 all in, of which A$13.10 is verified. It is more work and
less runtime than the Anker, and it is a bare cell rather than a sealed
assembly — see §5. Its advantage is that it definitely behaves correctly as a
UPS, which the Anker may or may not.

---

## 5. Safety, plainly

A lithium cell sealed in a printed box on a wall in a family home deserves a
straight answer rather than a shrug.

**Print the housing in PETG, not PLA.** PLA's glass transition is 55–60 °C — it
does not melt, it softens and stops holding the cell where you put it. About 1 W
of dissipation in a small closed box, on a west-facing wall, in a Victorian
summer with 35–40 °C indoors, can plausibly put the interior at 50–70 °C. That
estimate is *an estimate* — no measurement of this enclosure has been made, and
the whole argument rests on it, so it is worth a probe before a cell goes in.
PETG's Tg is ~80 °C and the change costs nothing. The vents are already in the
part: two groups of slots, low and high, so it convects rather than sitting as a
sealed oven.

**A certified sealed bank is materially safer than a bare cell on a hobby
board**, in one specific sense: it ships as a tested assembly, with protection on
the cell, a cell of known provenance, and a recall path behind it. The bq25185 is
a *charger*, not a protection circuit — no over-discharge cutoff, no
short-circuit protection. If you go that route, the cell must be a **protected**
one; skipping that gives you a worse safety story than a A$49 Anker, not a
better one.

Whatever you build, do not leave the first few charge cycles unattended.

---

## 6. Or don't

The honest summary of the trade:

| | slim housing | battery housing |
|---|---|---|
| clock depth | **44.4 mm** | 55.4 mm |
| runtime in an outage | 0 | ~17 h |
| extra cost | 0 | A$49 |
| extra risk | none | a lithium cell on the wall |
| extra unknown | none | whether it restarts by itself |

Both housings are in `enclosure/mini/v2/`, so this stays your call and can be
revisited with one reprint of one part. The clock is better looking at 44 mm.

---

## 7. Still unverified

1. **Whether the Anker restarts by itself after depletion.** §3 has the test.
2. **The display's 95 mA** — extrapolated, largest load, least certain. An inline
   meter settles it in ten minutes.
3. **The ring's die revision** — V5 versus original silicon is 2× per channel.
   Power the ring alone, write all pixels to zero, read the supply current:
   ~14 mA means V5, ~24–36 mA means older.
4. **The 88% boost efficiency** — assumed from typical curves, not measured.
5. **The interior temperature rise** — an estimate, and §5 rests on it.
6. **Whether the clone S3 devkit has the backfeed diode** the official
   DevKitC-1 v1.1 has (D1, 1N5819HW). Matters only if you ever power it from USB
   and the 5 V pin at once — so don't.
7. **The 5 V boost and the LiFePO4 cell** in §4 — neither priced nor stock-checked.
8. Every price here except **A$49 (Scorptec)**, **A$13.10 (Core Electronics)** and
   **A$14.05 (Little Bird)**.
