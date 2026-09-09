# Print set — 32-LED mini round clock, stand-box version

Built from `build_v2.py` and verified by `sh runchecks.sh`, which runs ten
passes, several of them once per body.

## Where the files are

    wall-clock/enclosure/mini/v2/
        3mf/      <- PRINT FROM HERE. Carries the intended print orientation.
        stl/      <- the same parts, if your slicer would rather have an STL
        input/    <- the two meshes Sam uploaded. Not print files.

Everything in `3mf/` and `stl/` is generated: delete either folder and
`python3 build_v2.py` puts it back. `input/` is the only thing here that
cannot be regenerated.

## What changed since the last print sheet

The base is the **stand-box**, the one you picked, and it is now **one part
with the bottom fully open**. The lid, the cradle, the sliding tray, the four
locating pins and the two M2 screws are all gone — you turn it over, tilt the
board in onto two shelves, and hold it with two cable ties. USB-C comes out the
back. Full detail is under **THE STAND-BOX** below, including the one step that
needs your hands.

Two faults were found and fixed while building it, both of the same kind — a
part that is the right shape and cannot be assembled:

* the shelf ran unbroken from the board's edge out to the wall, so **the cable
  tie you asked for had nowhere to pass**; and
* the plinth's roof was sitting **inside the clock** — 491 mm³ on the 24,
  1134 on the 60 — because the clock's seat was only ever cut from the cradle
  and the plinth was then unioned back into it. Seven checks had measured that
  stand and none of them had ever put the clock in it.

Both now have tests: check6 walks the tie's whole path, and booleans the real
clock against the real base.

## Print these

| # | file | size mm (x·y·z) | vol | notes |
|---|---|---|---|---|
| 1 | `mini-round-clock-standbox-32` | 120.7 · 72.0 · 61.4 | 155 cm³ | **the base.** One part, foot down, no support |
| 2 | `mini-round-clock-base-32` | 119.8 · 119.8 · 24.4 | 138 cm³ | the clock body |
| 3 | `mini-round-clock-backcover-32` | 119.8 · 119.8 · 8.9 | 34 cm³ | flat back, for the stand version |
| 4 | `mini-round-clock-diffuser-32-plain` | 112.4 · 112.4 · 6.8 | 24 cm³ | no numerals — see the material note |

If you only print one thing, print **1**. Nothing else has changed.

For the 24-LED clock print `mini-round-clock-standbox` (no suffix) instead, and
for the 240 mm one `mini-round-clock-standbox-60` — see the table under THE
STAND-BOX.

You will also need **two cable ties**, 3.6 mm wide or narrower. Nothing else:
no screws, no heat-set inserts.

`mini-round-clock-housing-32` is the *wall-mount* rear housing and you do not
need it. The **back-stand**, the **dock** and the **plinth** are earlier
answers to the same question, still built and still correct; they are described
further down and none of them is what you asked for last.

## Material

**The diffuser must be cast acrylic or PLA/PETG — never PVC and never
chlorinated acrylic.** Cutting or heating those releases hydrogen chloride: it
ruins the optics, corrodes anything nearby, and is a genuine hazard. This has
been the standing rule on this build since the first BOM and it has not
changed.

Everything else is ordinary PLA or PETG. The stand-box has no threads and no
screws in it at all, so PLA is fine; PETG if you want the foot to stop caring
about a warm room.

## The numbers that might be wrong

**On the stand-box there is no slot at all**, which is the point of holding the
board with ties instead of clamping it in a channel: a millimetre either way on
the board's width changes how much shelf is under its edge, not whether it goes
in. At 30.00 mm the ledge is 1.4 mm a side. At 31.00 it would be 0.9 — still a
ledge. At 29.00 it is 1.9. Nothing to re-slice.

What could still be wrong:

1. **Where the ties cross the board.** 14 mm in from each end, across the top.
   Unverified against your board's actual components — see the note under THE
   STAND-BOX. `STANDBOX_TIE_INSET` moves them.
2. **How tall your loom stands.** The cavity gives 21.0 mm over the shelves and
   the allowance is 20.6 — the board, 14 mm of headers with Dupont housings on
   them, and 5 mm of wire standing on those. If your connectors are taller than
   14 mm above the PCB, that 0.4 mm of slack is gone. Measure a plugged
   connector before printing if you want to be sure.
3. **Header tails under the board.** They have 1.2 mm to the desk. Trimmed
   tails have plenty; untrimmed ones on a 2.54 mm header could touch.

*The back-stand, if you print that instead:* its board channel is **30.60 mm**,
0.30 a side nominal, and a printed slot can lose 0.40 across, so the worst case
is 0.10 a side. Sloppy → `BACKSTAND_SLOT_W = 30.20`; will not go in → `31.00`.
`mini-round-clock-board-gauge` (13 cm³, ~15 min) has channels at
**30.20 / 30.60 / 31.00 / 31.40** if you would rather know than guess.

## THE STAND-BOX — print this. Everything below is superseded.

`2026-09-05`. Shown four bases side by side, Sam picked it: "B, I like the
stand box." `2026-09-08`: "Make the base look much nicer, and the bottom can be
fully open, with a spot for ziptie down the ESP32 with the USB cable out he
back."

**It is now ONE part.** No lid, no cradle, no tray, no pins, no screws. That
permission — the bottom *can* be open — is what did it: with no floor to
protect there is nothing for a lid to close, so the base is a single shell you
turn over, drop the board into and set down.

| print | | |
|---|---|---|
| `mini-round-clock-standbox{tag}` | the whole base | **foot down**, no support |

The clock is untouched: base, back cover, the ORIGINAL `housing`, diffusers,
numerals. Nothing else to print, and nothing to screw together.

|  | 24 LED | 32 LED | 60 LED |
|---|---|---|---|
| stand-box | 108.8 × 72.0 × 58.7 mm | 120.7 × 72.0 × 61.4 mm | 240.8 × 105.7 × 88.8 mm |
| model volume | 136 cm³ | 155 cm³ | 566 cm³ |
| lean | 12° | 12° | 12° |

Model volume solid would be ~168 g of PLA on the 24 and ~193 g on the 32. It
will not be that: the part is now a shell, so most of that volume is already
absent and infill has little left to thin. **Let the slicer give you the real
number** — I am not going to guess it.

### How the board goes in

**The board goes in tilted, from underneath, and this is the one step that
needs your hands.**

1. Turn the base over, or hold it up on its back edge.
2. The board goes in **component side up**, so the loom stands into the
   headroom rather than hanging out of the bottom.
3. Two shelves run down the inside, 27.2 mm apart, tops 5.2 mm off the desk.
   The board is 30 mm wide, so **roll it about 32° to get it between them**,
   lift it past, and let it drop flat onto the shelves. It sweeps 17.3 mm of
   height into 20.9 mm of headroom, so there is room, but it is a deliberate
   move and not a drop-in. (Verified against the mesh, not the arithmetic: the
   rolled board is lifted through in half-millimetre steps and then rolled flat
   at the top, and it touches nothing at any of them.)
4. The board's back end sits 1 mm inside the back wall. **USB-C lines up with
   the window in the back wall** — that is how you know it is the right way
   round and the right way up.
5. **Two cable ties.** Each one goes over the board, down through the window cut
   through the shelf just outboard of the board's edge, across the open bottom,
   and up through the window on the other side. There is a shallow groove across
   each shelf top so the tie sits flush and cannot walk along the board. Tie
   positions are 14 mm in from each end of the board.
6. Plug the clock's leads on. They come down through the notch in the roof at
   6 o'clock, straight into the cavity.
7. Clock into the saddle.

**One thing to check with your own eyes, because I could not verify it:** the
tie crosses the *top* of the board at those two points. On the DevKitC-1 those
land in the middle third, clear of the USB shells at one end and the antenna
keep-out at the other, but I do not have a verified component map for your
board. If something tall is in the way, thread the tie beside it — the windows
are 4 mm long, so there is play — or tell me and I will move `STANDBOX_TIE_INSET`.

### Numbers, measured off the built mesh

| | 24 | 32 | 60 |
|---|---|---|---|
| envelope mm | 108.8 × 72.0 × 58.7 | 120.7 × 72.0 × 61.4 | 240.8 × 105.7 × 88.8 |
| model volume | 135.6 cm³ | 155.2 cm³ | 566.0 cm³ |
| open underneath | 23.6 cm² | 23.5 cm² | 35.5 cm² |
| cavity | 35.7 wide × 66.0 deep | 35.7 × 66.0 | 35.7 × 99.5 |
| ceiling over the board | 26.2 mm flat, 24.7 at the board's edge | same | same |
| headroom over the shelves | 20.9 mm, against 20.6 needed | same | same |
| shelves | 27.2 mm apart, tops at z 5.2 | 27.3 apart | 27.2 apart |
| ledge under each board edge | 1.4 mm | 1.3 mm | 1.4 mm |
| roll to get the board in | 32° | 31° | 32° |
| under the board | 1.2 mm to the desk under a 4 mm tail; 3.2 mm for the tie's loop | same | same |
| worst flat bridge | 13.2 mm | 15.1 mm | 22.0 mm |
| clock-to-stand overlap | 0.0 mm³ | 0.0 mm³ | 0.0 mm³ |
| roof between clock and cavity | 2.88 mm | 2.88 mm | 2.88 mm |
| tips forward / back | 21.0° / 31.3° | 21.0° / 28.2° | 21.0° / 21.2° |

### What changed today

* **One part instead of three.** The lid, the cradle, the four locating pins
  and the two M2 screws are gone.
* **The bottom is fully open** — 23.6 cm² under the 24, 35.5 cm² under the 60 —
  and the wings either side of the board's cavity are hollowed out to the desk
  as well, ribbed so no stretch of ceiling bridges more than 28 mm. That took
  the 60 from 1037 cm³ to 566 and the 32 from 274 to 155 — the same shell
  measured before and after the wings were opened.
* **It looks like something.** 6 mm radii on the vertical corners, a 2.5 mm
  chamfer round the top edge, and a 1.5 mm reveal at the foot so the plinth
  reads as floating rather than sitting in a puddle of its own plastic.
* **A real spot for the zip ties**, which the first version of this did not
  have: the shelf ran unbroken from the board's edge out to the wall, so the tie
  had nowhere to pass. check6 now walks the tie's whole path.
* **The clock's seat is cut from the whole base.** It was only ever cut from the
  cradle, and the plinth's roof was then unioned back into it — 491 mm³ of
  plastic inside the clock on the 24, 1134 on the 60. No check had ever put the
  clock in the stand and looked. There is one now, and it reads 0.0 mm³.
* **The shelves sit 5.2 mm up, not 8.** The cavity's ceiling is not the plinth's
  roof — it is the *clock*, which leans into the plinth and bottoms out at
  z 29.1. That leaves a ceiling at 26.2 with 2.9 mm of roof under the clock, so
  20.9 mm of headroom for a board and a loom that want 20.6. The 5.4 mm left
  over goes downwards: 1.2 mm under a 4 mm header tail to the desk, and 3.2 mm
  under the shelf for the tie's loop.

## Superseded: assembling the back-stand

The back-stand is not the base you asked for last. This is kept because the
part is still built, still correct and still passes its checks.

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

## Superseded: the dock

`2026-09-05`. Sam: "I hate the stand. Start again. I want it enclosed."

Two parts replace the stand, the plinth and its lid:

| print | | |
|---|---|---|
| `mini-round-clock-dock{tag}` | the tray | open side UP, no support |
| `mini-round-clock-dock{tag}-cap` | the lid, with the clock's seat in it | seat UP, flat side on the bed, no support |

plus `mini-round-clock-backstand-clamp`, unchanged, to hold the board down.

The clock itself is untouched: base, back cover, the ORIGINAL `housing`,
diffusers, numerals.

|  | 24 LED | 32 LED |
|---|---|---|
| dock | 92 × 79 × 40 mm | 104 × 79 × 40 mm |
| tips fwd / back / side | 29.2° / 31.5° / 34.2° | 28.1° / 29.1° / 35.5° |

**Why two parts.** A closed box with a seat on its top cannot be printed in one
piece without support: hollowed from below it has to bridge its whole ceiling,
and turned over the seat becomes a 90 mm cavern. Split at the cavity's ceiling,
the tray is walls and a floor and the cap is a slab with a valley in it — and a
valley is open to the sky, so there is nothing to bridge in either.

**The cap is modelled solid** (107–124 cm³). That is not what it weighs: it is a
slab and the slicer hollows it. At 15% infill expect roughly 35–45 g.

**Assembly.** Board into the tray between the rails, hold-down bar over it, two
M2 × 6 into the bosses. Leads up through the wire drop. Cap into the rim, two
M2 × 10 through the **back** of the rim. Clock into the seat.

**Nothing pierces the underside** — not a slot, not a countersink. The screws go
in from the back for exactly that reason, and the seat's fixings would have been
under the clock where no screwdriver reaches.

**The wire drop runs the full length of the seat** (30 mm), so it does not matter
which way round the rim the clock's port ends up.

## Superseded: the plinth — electronics in the base

`2026-09-05`, and this supersedes the deep-housing set below. Sam: "Actually,
change of plans. I like having the electronics in the base under the clock."

**Two parts, and they replace the back-stand only:**

| print | instead of | |
|---|---|---|
| `mini-round-clock-plinth{tag}` | `mini-round-clock-backstand{tag}` | the same stand with the bay walled up to a lid height |
| `mini-round-clock-plinth{tag}-lid` | — | 2.5 mm plate, prints flat, two M2 x 8 screws |

The clock itself is **unchanged**: base, back cover, the ORIGINAL `housing`
(not `-deep`), diffusers, numerals.

**The hold-down bar is REQUIRED, not optional.** An earlier version of this
sheet said the board was captive under the lid. It is not — the lid sits
12.4 mm above the board and never touches it. `mini-round-clock-backstand-clamp`
and two M2 x 6 self-tappers are what hold the board down.

**The underside is solid.** Sam: "Make the base enclosed underneath." The six
cable-tie slots were the only holes in the foot, and the plinth does not cut
them — everything else down there is a blind pocket. The open back-stand keeps
them, because there they are the only thing holding anything.

**Why it was a small change.** The bay was already walled on all four sides —
front rail, back rail, two buttresses. It never had a lid. The plinth adds a
collar that carries those four walls up to one flat plane, and the lid closes
it. **12.4 mm of clear air over the board**, which is a Dupont shell plus room.

**Assembly.** Board into the bay as before, cable ties if you want them, leads
in through the gate from the trench. Then slide the lid's front tongue into the
slot in the front wall, drop the back onto its seat, two screws. The USB looks
out through the buttress window as it always did, and those windows are the
bay's ventilation — this is a closed box, not a sealed one.

## The deep-housing build — superseded, kept because it works

`2026-09-05`. The open back-stand is superseded for anyone who wants the clock
closed. Sam: "The current back stand doesn't work... I want the clock to be
enclosed."

Swap **two** parts and nothing else:

| instead of | print | why |
|---|---|---|
| `mini-round-clock-housing{tag}` | `mini-round-clock-housing{tag}-deep` | 31.5 mm instead of 20-25, and the ESP32 lives inside it |
| `mini-round-clock-backstand{tag}` | `mini-round-clock-backstand{tag}-deep` | the clock's back face is 22.6 mm further back; the shallow stand's buttresses would stand through the housing |

You do **not** need `backstand-clamp` any more, and the base, back cover,
diffusers and numerals are all unchanged.

The whole clock becomes **55.9 mm front to back** (was 44.4). The screen's wires
never leave it, which is the entire point: they were coming out at x = +41,
level with the top of a buttress and 50 mm above the board, with the buttress in
between.

**Assembly.** The housing prints rear-plate-down, no support. Slide the board's
far end under the lip, drop the USB end down between the rails — its end sits
1.6 mm off the wall, so a USB-C plug reaches it through the window. Two small
cable ties across the board, threaded down one slot and back up the other; the
relief in the underside keeps the loop inside the plate so the clock still lies
flat on a wall. Screen tail and ring leads come in through the base's own port
at +x and have 26.4 mm of plenum to sit in.

## Numbers, measured off the built mesh — the back-stand

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

## The other two bodies — the back-stand

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
hazard. At 256 cm³ it is 45% of the stand-box's 566 — a margin that was much
wider before the stand-box's bottom was opened and its wings hollowed out.
