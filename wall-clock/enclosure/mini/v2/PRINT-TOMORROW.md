# Print set — 32-LED mini round clock, back-stand version

Built from `build_v2.py` and verified by `sh runchecks.sh`, which now runs
seven passes and the seventh once for each body.

## Where the files are

    wall-clock/enclosure/mini/v2/
        3mf/      <- PRINT FROM HERE. Carries the intended print orientation.
        stl/      <- the same parts, if your slicer would rather have an STL
        input/    <- the two meshes Sam uploaded. Not print files.

Everything in `3mf/` and `stl/` is generated: delete either folder and
`python3 build_v2.py` puts it back. `input/` is the only thing here that
cannot be regenerated.

## What changed since the last print sheet

You asked for a base that isn't as bulky, open for the cables, sitting behind
the clock at an angle. So the plinth is gone. The old stand-box was a closed
box with a lid, two M2 screws and a slide-in tray — **197 cm³ plus an 11 cm³
tray, about 244 g of filament, to hold a 12 g board.**

The **back-stand** does the same job in one part, `47.2 cm³ / ~59 g`. The clock
comes down onto the desk and beds 4 mm into a trench in the foot; two
buttresses behind it take the lean. Everything between them is air — that is
the cable route and the board bay, an open channel with no lid, no tray and no
screws. Nothing is enclosed, so nothing needs closing.

It is **48 mm tall against 61**, **86 mm wide against 121**, and it prints flat
on its foot with no support: every overhang is 45° or steeper, and the two
windows have 45° gables rather than flat roofs.

You also told me the board is **30 mm**, not the 29 I had. Both the back-stand
and the old stand-box are cut for 30.00 now.

## Print these

| # | file | size mm (x·y·z) | vol | notes |
|---|---|---|---|---|
| 1 | `mini-round-clock-backstand-32` | 98.0 · 86.3 · 48.0 | 51 cm³ | **the new base.** One part, no lid |
| 1b | `mini-round-clock-backstand-clamp` | 81.5 · 20.0 · 6.9 | 7 cm³ | holds the board down. Two M2 self-tappers |
| 2 | `mini-round-clock-base-32` | 119.8 · 119.8 · 24.4 | 138 cm³ | the clock body |
| 3 | `mini-round-clock-backcover-32` | 119.8 · 119.8 · 8.9 | 34 cm³ | flat back, for the stand version |
| 4 | `mini-round-clock-diffuser-32-plain` | 112.4 · 112.4 · 6.8 | 24 cm³ | no numerals — see the material note |

If you only print one thing, print **1**. Nothing else has changed.

For the 24-LED clock print `mini-round-clock-backstand` (no suffix) instead —
see the table at the bottom.

`mini-round-clock-housing-32` is the *wall-mount* rear housing and you do not
need it. `mini-round-clock-standbox-32` and its tray are the old design; they
are still built and still correct, now for a 30 mm board, if you would rather
have the clock lifted.

## Material

**The diffuser must be cast acrylic or PLA/PETG — never PVC and never
chlorinated acrylic.** Cutting or heating those releases hydrogen chloride: it
ruins the optics, corrodes anything nearby, and is a genuine hazard. This has
been the standing rule on this build since the first BOM and it has not
changed.

Everything else is ordinary PLA or PETG. The back-stand has no threads in it,
so PLA is fine; PETG if you want the foot to stop caring about a warm room.

## The one number that might be wrong

The board channel is **30.60 mm** for your 30.00 mm board — measured off the
built STL, not off the drawing. That is 0.30 mm a side nominal, and a printed
slot can lose up to 0.40 mm across, so the worst case is still 0.10 a side.

**If it is sloppy:** `BACKSTAND_SLOT_W = 30.20` in `params.py`, re-run
`python3 build_v2.py`. **If it will not go in:** `31.00`. One number, one
re-slice.

`mini-round-clock-board-fit-gauge` (23 cm³, ~15 min) now has channels at
**30.20 / 30.60 / 31.00 / 31.40** — print it first if you would rather know
than guess. The one that takes the board without force is the answer.

## Assembly

1. **Board in:** slide its back long edge under the lip on the rear rail, then
   drop the front edge in over the low front rail. It lies **flat on the bay
   floor** — the four pads that used to lift it 4 mm are gone. Nothing screws
   down.

   If your board has header tails poking out underneath, say so: they need
   either the pads back (`BACKSTAND_POST_H = 4.00`, one number, everything
   else follows) or a ledge along the rails.

1b. **Bar on:** `mini-round-clock-backstand-clamp`, THIS SIDE DOWN debossed on
   the face that prints first — the feet go downward in use. It bridges over
   the USB shell and the module and comes down only on the bare 4 mm of PCB at
   each end. Two M2 x 6 self-tappers into the bosses either side of the board.
   Tighten until it stops: the pads sit 0.10 mm below the boss seats, so it
   lands on the board rather than bottoming out on its own bosses.
1c. **Or zip ties instead of the bar.** Six slots in the foot, in three pairs.
   Thread a tie down one slot of a pair and back up the other: the two are
   joined by a **1.2 mm relief milled into the underside**, so the loop lies
   *inside* the foot and the stand still sits flat on the desk. That relief is
   the whole point — a pair of plain holes through a foot puts the tie's loop
   under the part and the stand rocks on it.

   | pair | where | holds |
   |---|---|---|
   | board tie ×2 | \|x\| = 26, crossing the board's width | the ESP32. The loop wraps the board **and** the floor between the slots, so pulling it tight seats the board on the bay floor |
   | lead tie ×2 | \|x\| = 16, either side of the cable gate | the ring and power leads, front-to-back, where they come out of the clock |
   | end tie ×2 | \|x\| = 35.5, on the bare floor past the board's end | the USB lead, which leaves the board sideways |

   The board ties and the bar are **alternatives, not companions** — the bar's
   plate lies right across where those two ties have to go. Pick one.

   2.5 mm ties (the common small ones, about 2.5 × 1.0 mm in section) go
   through a 2.00 mm slot. Anything up to 3 mm wide will still thread; a
   heavy 4.8 mm tie will not.
2. **USB-C** looks straight out through the window in the buttress beside it —
   an 18 mm opening with a 52° gable, one in each side so it does not matter
   which way round the board goes in.
3. **Clock in:** stand it in the trench. It beds 4 mm and leans back 14°; the
   two buttresses catch its back cover 48 mm up.
3b. **Screen wires:** the tab slot under the display goes **straight through
   to the back of the base** — 31 mm of open corridor, 32.35 mm wide, from the
   display's underside to the bottom face. It did not, until 2026-09-05: a
   1.40 mm plate sat right across it, left behind when the tab-slot walls were
   taken down to the bottom plane and the slot cut out of them was not. If you
   have a base printed before that, this is the floor Sam found; reprint the
   base only, nothing else changed.

   Behind it the cover and the housing carry a **cable port**, not a slot —
   87 mm² on the 32 and 60, 238 mm² on the 24 — starting at r = 34. Wires come
   off the tab, drop straight back, and leave through it.
4. **Leads:** they leave the clock through the 6 o'clock notch in the back
   cover and run back to the board along the 18 mm channel cut into the foot.
   Nothing pinches them and nothing closes over them. The gate takes the
   middle 18 mm out of the front rail so the leads reach the board without
   climbing anything.

## Numbers, measured off the built mesh

| | |
|---|---|
| envelope | 98.0 × 86.3 × 48.0 mm |
| volume | 51.1 cm³, about 63 g of PLA |
| lean | 14° back from vertical |
| clock bed | 4.00 mm into the foot |
| board slot | 30.60 mm, 0.30 a side on a 30.00 board |
| zip-tie slots | 2.00 mm, six of them, loop recessed 1.20 into the underside |
| tips forward at | 36.6° |
| tips backward at | 42.2° |
| tips sideways at | 39.4° |
| clock-to-stand contact | 0.50 mm clearance everywhere, 0 mm³ of overlap |

## The other two bodies

There is a back-stand for every body, and each one passes the same checks.
**Mind the filenames**: the 24 is the UNTAGGED one, the same convention as
`mini-round-clock-base` and everything else in this set. It is not a
"generic" file — it is the Ø108 body specifically.

| file | body | size mm | vol | tips fwd / back / side |
|---|---|---|---|---|
| `mini-round-clock-backstand` | **24 LED, Ø108** | 98.0 · 83.4 · 43.2 | 48 cm³ | 39.5° / 44.7° / 43.1° |
| `mini-round-clock-backstand-32` | 32 LED, Ø119.9 | 98.0 · 86.3 · 48.0 | 51 cm³ | 36.6° / 42.2° / 39.4° |
| `mini-round-clock-backstand-60` | 60 LED, Ø240 | 191.2 · 134.4 · 96.1 | 256 cm³ | ≥20° all three |

The 24's stand is the same 98 mm wide as the 32's even though its clock is
12 mm smaller, and that is deliberate: the footprint scales with the body but
the **board does not**, so the buttresses cannot come inboard of a 64 mm board
however small the clock gets. Below the 32 the width is held, not scaled.

The 60's does scale — 172 × 134 × 96. check7 measured an 86 mm foot tipping
backwards at 17.5° under a 240 mm clock, and that is not a stand, it is a
hazard. It still replaces a 936 cm³ stand-box and tray, so it is 26% of the
material even at that size.
