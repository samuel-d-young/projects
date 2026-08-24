# mini-round-clock enclosure — v2 rear end

What this adds to the base and diffuser Sam remodelled: a bay for the ESP32-S3,
a wall hanger, and a pocket for a USB-C power bank.

Everything here is generated from `build_v2.py`, which reads Sam's uploaded
`base_in.stl` and adds to it. It never redraws his geometry — his part above
z = 0 comes through byte-for-byte except for four screw pilot holes.

```
python3 measure_uploaded.py    # re-derive every number in params.py from his STLs
python3 build_v2.py            # write the STLs and 3MFs
./runchecks.sh                 # all three verification passes
python3 render.py              # picture sheets
python3 viz.py                 # cross-section atlas of the uploaded parts
```

`base_in.stl` and `diffuser_in.stl` are Sam's uploads, kept so the whole thing
re-derives from source. `measure_uploaded.py` prints the table that `params.py`
holds — if he sends new files, run it and diff.

---

## Print these

| File | Print orientation | Support | PLA | Time (est.) |
|---|---|---|---|---|
| `mini-round-clock-base-v2` | **deck face down** | see note | ~132 g | ~5 h |
| `mini-round-clock-rearhousing-battery` | **rear plate down** | none | ~73 g | ~3 h |
| *or* `mini-round-clock-rearhousing-slim` | rear plate down | none | ~57 g | ~2.5 h |
| `mini-round-clock-battery-shim-x2` | flat | none | ~11 g each, **print 2** | ~20 min |
| `mini-round-clock-diffuser-fix` | *optional* — see §4 | none | ~12 g | ~40 min |

Both `.stl` and `.3mf` are provided. **Prefer the 3MF** — STL stores coordinates
as 32-bit floats, and the round trip through that is what generates most
"needs repair" warnings in slicers.

**Support note for the base.** The part is designed to need none, and the checker
confirms it introduces none. But Sam's own geometry carries 409 mm² of shallow
overhang at 33–40° from horizontal — the lead-in ramp at the top of the
display-tab slot, at z 10.7–17.9. Whether that needs support depends on the
threshold you slice at; at Bambu's usual settings it will want a little, inside
the tab slot, which is open and easy to pick out. It is the same in the file Sam
uploaded, so nothing has changed here.

**Material.** PETG rather than PLA if a lithium cell is going in. PLA's glass
transition is ~55–60 °C; PETG's is ~80 °C. See §5.

---

## 1. What was found in the uploaded files

Three things worth knowing before printing anything.

### The base has a disconnected 605 mm³ solid in it

`Mini_Wall_Clock_Base.stl` contains a second shell — a crescent at
r 35.06–40.90, ±41.9° about +x, z 11.80–15.75 — that is **not attached to the
body**. Its faces sit exactly on the main body's cut surface, and it arrived as
a +2832 / −2227 mm³ shell pair. That is the signature of a CAD boolean that
failed to merge, not a feature.

It sits precisely in the window the display tab has to pass through. Sliced
as-is, it prints as an extra crescent of plastic exactly where the display goes.
`build_v2.py` drops it and says so when it runs.

### The diffuser's screen collar over-reaches by 1.8 mm

The new collar on the diffuser is r 27.92–30.11, 8.2 mm tall. Working the stack
through:

```
display seat (measured, base)                     z =  8.60
+ module thickness (your measurement, 4 mm)       z = 12.60   <- module front face
diffuser seats when its baffles meet the LED tops z = 15.00
  -> its collar bottom lands at 19.00 - 8.20      z = 10.80
```

The collar bottom wants to be at 10.80 and the module's front face is at 12.60,
so the collar hits the display **1.8 mm before the diffuser seats**. The diffuser
would stand 1.8 mm proud and the plywood face would not sit down.

That arithmetic assumes the module is 4.00 mm thick at its rim. If it is 2.2 mm
there, it is already correct and nothing needs doing. **Measure the module rim
before touching this** — it is the one number the whole thing turns on.

If it does need fixing, there are two ways and both are provided:

- `mini-round-clock-diffuser-fix.stl` — collar shortened by 1.80 mm, nothing
  else changed. Reprint the diffuser.
- Set `SEAT_DROP = 1.80` in `params.py` and rebuild the base — this drops the
  display seat instead, so no diffuser reprint. Costs 1.8 mm more screen depth.

### The wire slot goes right through

The straight-down channel is open front to back — at 180° there is no material
at all from z = 0 to z = 22 for r 31–43. The plywood face covers it at the
front, so it was never visible, but the deck now closes it from behind, which
also encloses the electronics. A 4 × 16 mm port is cut through the deck beside
the S3's USB-C end so the battery lead can still get up to the board.

---

## 2. The ESP32-S3 bay

The board is the official Espressif outline: **62.74 × 25.40 mm**, from
`DXF_ESP32-S3-DevKitC-1_V1_20210312CB.pdf`.

It does not get a box of its own. Sam's base already has a dog-bone shaped void
running along the x axis — the rear bore, plus his wire slot at 6 o'clock, plus
the display-tab window at 12 o'clock — and along the strip |y| ≤ 12.7 that void
is open from x = −43 to x = +40.7. That is 83.7 mm of clear length for a
62.74 mm board. So the deck simply gives it a floor.

```
deck window   63.64 x 26.30 mm  (0.45 clearance per side)
board sits at x -24.00 .. +38.74, y +/-12.70
  -x corner r = 27.15  (bore wall is at 27.78)
  +x corner r = 40.77  (tab window reaches 42.66)
PCB occupies z -0.80 .. +0.80, tallest parts reach z +4.00
display seat is at z +8.60                        -> 4.60 mm of air above
```

**It loads from the rear**, pushed up until its rim meets the ledges. The ledges
are at the two **short** ends only — the DevKitC-1 carries its pad rows down both
long edges, 1.27 mm in, and a ledge there would foul any soldered header. Four
posts stand 3 mm proud of the deck at the corners to stop it tipping.

Nothing screws it down and nothing needs to. Hanging on a wall, gravity acts
along −x, which is in the board's own plane; the only way out is backwards, and
the rear housing is 2 mm behind it.

**If your board has male headers soldered pointing down**, snip them or it will
not seat — there is 1.6 mm under the PCB, which takes solder joints but not pins.

### Powering it

Feed the board's **5V and GND pins**, not its USB-C port. That is why there is no
port cut-out at board level: a USB-C plug is ~20 mm long, and from a board edge
at r ≈ 36 it would end up at r ≈ 56, outside the 108 mm body. The mains lead
comes in through the cable exit at 6 o'clock and goes to the battery; a short
lead runs from the battery output to the board's pins.

For flashing, take the rear housing off (4 screws) and the board lifts straight
out. After the first flash it is OTA over WiFi anyway.

---

## 3. The rear housing

Two variants, identical apart from pocket depth:

| | pocket | housing | clock overall |
|---|---:|---:|---:|
| `-slim` | 15.0 mm | 18.5 mm | **44.4 mm** |
| `-battery` | 27.5 mm | 31.0 mm | **55.4 mm** |

### Wall hanger

A keyhole at 12 o'clock: 9.0 mm entry hole, 4.6 mm slot, 7.5 mm drop. Takes a
screw up to 8 mm across the head on a 4 mm shank. The clock has to be lifted
7.0 mm to come back off it.

The screw head ends up **inside** the compartment once the clock is hung — that
is what carries the load. The battery pocket is therefore offset 7 mm toward
6 o'clock so the battery never sits on it.

Load path is keyhole → 3.5 mm plate → outer wall. The four assembly screws carry
nothing. At a 400 g clock the shank bears on 4.6 × 3.5 mm of PLA, about 0.25 MPa
against a ~50 MPa yield.

An earlier version had stiffening ribs behind the hanger. The fit checker found
that they ate into the battery footprint, and the stress arithmetic says they
were never needed. They are gone.

### Assembly

Four M3 self-tappers at r = 49, at 45/135/225/315° — clear of 12 o'clock (hanger)
and 6 o'clock (cable). They pass through pillars in the housing, counterbored at
the rear so nothing stands proud against the wall, and thread 8 mm into pilot
holes in the base.

- slim housing → **M3 × 30** self-tapping
- battery housing → **M3 × 40** self-tapping

### Cable exit and vents

A 12 × 7 mm notch through the outer wall at 6 o'clock takes a USB-C plug
(9 × 4.5 mm body clears it with room). 18 vent slots, 2.6 mm, in two groups —
low and high — so the box convects when it is on a wall rather than sitting as a
sealed oven.

---

## 4. Assembly order

1. Print the base, the housing you want, and **two** shims.
2. Fit the display and ring to the base as before, front side.
3. From the rear, push the S3 into the deck window until it meets the ledges.
4. Solder the ring and display leads to the board.
5. Put the battery in the housing with a shim either side; run its output lead up
   through the deck port to the board's 5V/GND pins.
6. Bring the mains lead in through the cable exit at 6 o'clock to the battery
   input.
7. Screw the housing on, 4 × M3.
8. One screw in the wall, 4 mm shank, head no more than 8 mm. Hang it.

---

## 5. The battery — read this before buying anything

**A battery this size cannot run this clock. It is a UPS for outages.**

The measured budget, from datasheets rather than estimates:

| Load | typical | worst |
|---|---:|---:|
| ESP32-S3-N16R8 devkit, WiFi up, HA API connected | 60 mA | 140 mA |
| 24-LED WS2812B ring, clock face at ~25% | 33 mA | 145 mA |
| 2.1" 360×360 GC9B72 + backlight | 95 mA | 150 mA |
| **at 5 V** | **188 mA = 0.94 W** | **435 mA = 2.18 W** |

That is **22.6 Wh a day**. A 5,000 mAh bank holds ~18.5 Wh nominal, ~16 Wh after
boost losses — **under 18 hours**. It does not last a day.

### What actually fits

The pocket takes **up to 80 × 38 × 26 mm**, or 78 × 45, or 77 × 50 — the limit is
a rectangle inside the 102 mm interior circle with the hanging screw's swept zone
carved out of the top. `check2_fit.py` prints the full table.

A sweep of Officeworks, JB Hi-Fi, Kogan, Amazon AU, Core Electronics, Zaitronics,
PB Tech, Cygnett, Anker AU, Belkin AU and Bunnings found that **almost nothing on
the retail market is both small enough and thin enough**. The market splits into
slim-and-wide (Cygnett 95 × 65, Anker MagGo 104 × 71) and small-and-fat. Only the
second kind fits a 108 mm circle, and those are 25–26 mm thick — which is what
pushes the clock from 44 mm to 55 mm deep.

### The failure mode that decides it

At 188 mA the clock sits above the ~50–75 mA idle cutoff most banks use, so it
would probably not get switched off in normal running. The one that would bite is
different: **many banks, once flat, will not resume output when mains comes back
until someone presses the button.** On a clock 2.4 m up a wall that means it stays
dead. That behaviour is the single thing to test on the bench before a bank goes
in the wall — drain it, reconnect mains, and see whether the output comes back on
its own.

### Safety, and the material

A lithium cell sealed in a printed box on a wall in a family home deserves a
plain answer:

- **Print the housing in PETG, not PLA.** PLA softens at 55–60 °C. About 1 W of
  dissipation in a small closed box on a west-facing Victorian wall in summer can
  plausibly put the interior at 50–70 °C. PETG's Tg is ~80 °C. The vents help but
  they do not make PLA the right choice here.
- A **certified sealed power bank is materially safer** than a bare cell on a
  hobby charger board, in one specific way: it ships as a tested assembly with
  protection on the cell and a liability path behind it. A charger IC is not a
  protection circuit — it gives you no over-discharge cutoff and no short-circuit
  protection. If you go the bare-cell route, the cell must be a *protected* one.
- Do not leave the first few charge cycles unattended.
- If the battery is not worth 11 mm of depth and this list of caveats to you,
  print the **slim** housing and run it on mains. The clock is better at 44 mm and
  nothing else changes.

---

## 6. What is verified and what is not

**Verified here, by running it:**

- Every part is a closed, single-body, self-intersection-free solid (`check1`)
- Sam's geometry above z = 0 differs by exactly four screw pilots and four posts,
  and nothing else — measured as a boolean difference, not eyeballed (`check2`)
- The board, the battery, an M3 shank, an 8 mm screw head and a USB-C plug body
  each fit where they have to, with the clearances printed (`check2`)
- The base and the housing touch only at the mating plane — zero interference
  volume (`check2`)
- No part introduces a sloped overhang below 45°, a flat ceiling over 25 mm, or
  a wall thinner than 1.2 mm that is not already in Sam's file (`check3`)

**Not verified — these need hands or a purchase:**

- Nothing has been sliced. Print time and mass are estimates from volume.
- The display module's 4 mm thickness is Sam's measurement of the whole module,
  not of the rim the collar lands on. §1 turns on it.
- No power bank price or stock has been confirmed in Australia yet.
- The 95 mA display figure is the weakest number in the budget — it is
  extrapolated from a smaller GC9A01 module, because the 2.1" drawing lists
  luminance as "TBA" and gives no LED current. An inline meter settles it in ten
  minutes and could change the battery decision.
- The ring's die revision is unknown; V5 versus original silicon is a 2×
  difference in per-channel current. Power the ring alone, write all zeros, read
  the supply current: ~14 mA means V5, ~24–36 mA means older.
- The interior temperature rise is an estimate, and the safety argument in §5
  rests on it. Worth a probe before a cell goes in.
