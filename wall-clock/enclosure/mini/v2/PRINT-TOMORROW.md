# Print set — 32-LED mini round clock, desk stand version

Everything below is built from `build_v2.py` at commit `57bce1b` or later and
passes all six verification passes. `.3mf` beside every `.stl` — **use the
`.3mf`**, it carries the intended print orientation; the `.stl` is there if
your slicer wants one.

Path: `wall-clock/enclosure/mini/v2/`

## Print these

| # | file | size mm (x·y·z) | vol | notes |
|---|---|---|---|---|
| 1 | `mini-round-clock-standbox-32` | 120.7 · 72.0 · 61.4 | 197 cm³ | **the new one.** Rebuilt for the 29 mm board |
| 2 | `mini-round-clock-standbox-tray-32` | 51.4 · 70.0 · 30.0 | 11 cm³ | the board tray, and it *is* the lid |
| 3 | `mini-round-clock-base-32` | 119.8 · 119.8 · 24.4 | 138 cm³ | the clock body |
| 4 | `mini-round-clock-backcover-32` | 119.8 · 119.8 · 8.9 | 34 cm³ | flat back, for the stand version |
| 5 | `mini-round-clock-diffuser-32-plain` | 112.4 · 112.4 · 6.8 | 24 cm³ | no numerals — see the material note |
| 6 | `mini-round-clock-board-clamp` | 15.8 · 20.0 · 3.0 | 0.8 cm³ | tiny, print two |

If you only print one thing, print **1 and 2**. That is the stand rebuild and
it is what has been blocking the build.

`mini-round-clock-housing-32` is the *wall-mount* rear housing. You do **not**
need it for the desk stand — the stand-box replaces it.

## Material

**The diffuser must be cast acrylic or PLA/PETG — never PVC and never
chlorinated acrylic.** Cutting or heating those releases hydrogen chloride: it
ruins the optics, corrodes anything nearby, and is a genuine hazard. This has
been the standing rule on this build since the first BOM and it has not
changed.

Everything else is ordinary PLA or PETG. PETG for the stand-box if you have
it — it takes the M2 self-tappers better.

## The one number that might be wrong

The tray's board channel is **30.20 mm** for your 29.00 mm board — measured off
the built STL, rails at x ±15.10 inner, ±17.10 outer. That is about 0.80 mm of
real clearance once FDM squish is accounted for.

I chose it without the fit gauge because you wanted to print tomorrow. It is
deliberately the *loose* one of the two sensible options: a board that rattles
slightly is a nuisance, a board that will not go in wastes the print.

**If it is sloppy:** `STANDBOX_SLOT_W = 29.80` in `params.py`, re-run
`python3 build_v2.py`. **If it is tight:** `30.60`. One number, one re-slice.

Print `mini-round-clock-board-fit-gauge` (162 · 42 · 9, 23 cm³, ~15 min) first
if you would rather know than guess — it has four channels at 29.40 / 29.80 /
30.20 / 30.60 and the one that takes the board without force is the answer.

## Assembly order

1. Board into the **tray**: it slides under the two corner hooks, connector end
   at the open end. Four pads lift the PCB so the header tails clear.
2. Tray into the **stand-box** from the back; the tray's end plate closes the
   bay and takes two M2 self-tappers into the plinth's back face.
3. USB-C lines up with the window in that end plate.
4. Clock sits in the cradle, leaning back 12°. The leads drop through the
   6 o'clock notch straight into the bay.
