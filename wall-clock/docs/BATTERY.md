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

### Anker Nano Power Bank 22.5W, model A1653, 5,000 mAh — **A$49**

| | |
|---|---|
| Retailer | **Scorptec** (Melbourne) — **price verified, in stock** |
| Dimensions | **76.96 × 36.83 × 24.89 mm** — **verified**, from Anker's own product page (3.03 × 1.45 × 0.98 in) |
| Margin in the pocket | 3.04 mm on length, 1.17 on width, 1.11 on thickness |
| Connector | built-in USB-C, so no cable stub inside the box |
| Pass-through charging | **yes — verified from Anker's printed manual** |
| Auto-restart after depletion | **UNKNOWN — test this before it goes in the wall** |

Runtime:

```
usable Wh = 5000 mAh x 3.7 V x 0.88 / 1000 = 16.28 Wh
                                             (0.88 = a synchronous 5 V boost,
                                              derated for the tail of discharge)

  16.28 / 0.94 W  =  17.3 hours   typical
  16.28 / 0.66 W  =  24.7 hours   with the backlight at 30%
  16.28 / 2.18 W  =   7.5 hours   worst case
```

The shim (`mini-round-clock-battery-shim-x2`) is cut for exactly these
dimensions. If you buy something else, change `BAT_L`/`BAT_W` in `params.py` and
reprint the shim — 20 minutes. The pocket itself does not move.

### The one thing that decides whether this works at all

**Many power banks, once flat, will not resume output when mains comes back until
someone presses the button.** On a clock 2.4 m up a wall, that means it stays
dead until someone gets a ladder. Anker do not document A1653's behaviour either
way, and I could not establish it from owner reports.

**Test it on the bench, before it goes in the clock. Five minutes:**

1. Plug the bank into the clock (or any ~200 mA load) and let it run flat.
2. Leave the load connected. Plug the wall charger into the bank.
3. Watch the load. Does it come alive on its own?

If yes, buy a second one and stop reading. If no, the bank is not usable as a
wall-clock UPS at any price, and the alternative below is the answer.

Idle cutoff, the trap people usually worry about, is **not** the problem here: at
188 mA the clock sits well above the ~50–75 mA threshold banks use. It would only
bite if firmware dimmed everything hard on battery and dropped the draw below it
— worth remembering if you ever write that feature.

---

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
