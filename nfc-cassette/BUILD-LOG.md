# NFC cassette player — Build Log

Append-only. Newest entry at the bottom. Facts are **(verified)** or **(assumed)**.

---

## 2026-09-15 — Project opened: enclosure designed, nothing printed

**What it is.** A printed cassette player whose bay hides a PN532 NFC module,
and printed cassettes that each carry one NTAG215 PVC card. Samuel's brief:
"an enclosure like this" — bharms27's r/3Dprinting *Digital Nostalgia* build,
a Walkman-shaped body with a phone dock and printed NFC cassettes, no
supports, P1S **(verified from coverage; the Reddit post itself is blocked
from this machine)**. Here the phone becomes a D1 mini + PN532 and the
cassette lies flat in a top bay over the antenna.

**Decisions.**

- **Cassette = real compact-cassette size**, 100.4 × 63.8 × 12 **(verified,
  IEC 60094-7)**, so it feels right and any cassette-shaped sticker fits. Two
  parts (tray + glued lid) because a one-piece shell needs a 55 mm bridge.
  The whole ID-1 card slides into a rib frame in the tray, so nothing has to
  be cut down or centred by hand.
- **Top-loading flat bay**, not a front slot: the card lies parallel to the
  antenna at ~4.8 mm (module PCB 1.6 + bay floor 1.6 + tray floor 1.6), well
  inside the PN532's range, and a child can drop a tape in without aiming.
  The cassette stands 2 mm proud with a finger notch at each end.
- **Module held between four corner posts and the slab**, component side
  down, header pins down, Dupont tails hanging in the cavity. Nothing
  depends on the clone board's hole positions **(assumed unreliable)**.
- **D1 mini** to the right of the module, USB to a cutout in the back wall.
  The module sits 8 mm left of centre so the D1 mini clears the back-right
  screw post — the invariant that caught this is in `verify.py`.
- Four M3 screws from the top, in the strips front and back of the bay.
  Counterbored, so the heads sit flush next to the tape.
- Front face: one 5 mm LED hole (lit while a tape is in) and five raised
  cosmetic transport buttons. They do nothing. They are the point.

**Numbers at nominal.** Player 117 × 90 × 34 mm; 4 parts; everything prints
flat with no supports. `verify.py` sweeps the corners of seven parameters
(wall, bay/PCB/card clearances, DIP-switch height, D1 headroom, cassette
corner radius) and rebuilds every part at each.

**Assumed, measure before printing:** PN532 PCB 1.6 mm and 4.5 mm tallest
component (the DIP switch); header pins 3 mm below the board; micro-USB plug
boot 13 × 8 mm. All four have ranges in `params.py` and the sweep passes
across them, but a caliper takes a minute.

**Next:** print `cassette_tray` + `cassette_lid` first (cheap, proves the card
fit), then `player_base`, drop the module in, check the Dupont tails clear
the floor, then `player_top`.

## 2026-09-15 (later) — The tape sits higher

Samuel: the tape should sit in the top but not all the way in, so it comes out easily.
`bay_depth` 10 → **7** (range 6–8.5): 7 mm of the 12 mm shell is held by the bay, **5 mm
stands proud**, plus the finger notches. New invariants: at least 4 mm proud, at least
5 mm in the bay so it cannot tip out.

Knock-on: the top slab is now 8.6 mm thick, so M3 × 10 would put 1.4 mm of thread into the
post. Screw length is now a parameter (`screw_len` 16, the LUMA box has 24 of them), the
pilot depth is derived from it, and the sweep checks thread engagement ≥ 6 mm and that the
pilot never reaches the floor. Antenna-to-card distance unchanged at 4.8 mm.

Player is 118 × 90 × 31 mm now. Still nothing printed.

## 2026-09-15 (night) — Slot version: the tape stands in the top

Samuel: show me the STLs "if the cassette can go in but also be taken out of the top
rather than put into the side". So: a vertical slot in the top face, the tape standing
on its long edge, label to the front, 31 of its 64 mm proud. `cad/player_slot.py`, two
parts, `slot_body` (printed upside down, top face on the bed) and `slot_lid` (the bottom
plate). Body 127 × 47 × 47 mm.

**Inside.** The PN532 stands upright with its flat back against the 1.6 mm wall behind
the slot — the coil reads through its own board, and it puts the card 5.6 mm from the
antenna with the components, header and Dupont tails all facing the back. Held by two
full-height side ribs, two keeper ribs hanging from the roof, and a shelf on the lid; it
slides up into the pocket from below. The D1 mini lies on the lid to the left of the
module, USB through the left wall; the buzzer on the lid to the right, three sound holes
through the right wall; LED and five cosmetic buttons on the front, all below the slot
floor plate. Four M3 × 10 up from the lid into posts hanging from the roof: front-left,
front-right, back-right and back-middle — the back-left corner belongs to the D1 mini.

**Two things the sweep caught.** (1) The body length was a fixed margin around the slot,
so a 3 mm wall squeezed the D1 mini into the module's side rib; the length is now the
larger of the slot-plus-margins and what the board needs. (2) The first pass passed at
exactly 0.5 mm of gap, which floating point read as 0.4999; the design gap is 0.6 and
the check stays at 0.5. Six parts, 128 corners, 0 failures.

**Printing.** The body prints top-face-down: the slot is an open channel from the bed,
the module pocket and the cavity open upward, the posts grow from the bed, and the only
bridge is the 13 mm slot floor. The lid prints outside-face-down so its counterbores are
open at the bed. No supports anywhere. Render: `docs/nfc-cassette-slot.png`.

The flat-bay version from earlier tonight stays in the folder as an alternative.
**Still nothing printed**; the four assumed dimensions still want a caliper first.

## 2026-09-16 — A face for it: keys, knobs, counter, lamp, grille

Samuel: "add some fake buttons and knobs on the tape enclosure to make it look more
realistic." On the front face of the slot player now:

- five transport keys (REW PLAY FF STOP REC), 10 × 9 mm, 3 mm proud, with a groove across
  each and a 45° chamfer on the edge that would otherwise overhang in the print;
- two knobs, Ø16 and Ø11, knurled with 16 flutes and a pointer groove — **separate parts**
  (`knob_big`, `knob_small`) printed flat and glued into 0.6 mm recesses, because a boss
  on a vertical face is a half-cylinder overhang in the print;
- a tape-counter window: recessed rounded rectangle, raised frame, three digit bars;
- a REC lamp recess; and a speaker grille of 90 dimples at 3 mm pitch on the right.

None of it opens the wall: keys add material, everything else dents the 2.4 mm wall by
0.6–0.8 mm, so the only through-hole on the face is still the LED below the slot floor.
The sweep gained checks that the recesses stay shallow and every feature stays on the face
clear of the LED and the corner radius. Eight parts now; the body's triangle count went from
8k to 55k with the dimples, which the slicer will not mind.

## 2026-09-16 — Does the reader sit inside? Proved, and three things it found

Samuel: "make sure the reader can sit inside." Two changes.

**Retention no longer touches the component side.** The keeper ribs that hung behind the
PCB's face (top 8 mm, 4 mm wide) sat in the zone where the clone board has parts. Now the
module is held by: the slot wall against its flat back, the two side ribs against its side
edges, a 16 mm top lip hanging from the roof behind the top **edge strip**, and an L on the
lid — a shelf under the bottom edge plus a 16 mm lip behind the bottom edge strip. The
lips reach 1.5 mm over the edges, inside the ~2 mm band the listing photos show bare (the
antenna trace is inset that far; parts sit inside it). That band is an **assumed**
parameter (`s_edge_free`), as is the 10 mm corner zone where headers, holes and the DIP
switch may run right to the edge; the lips stay out of the corner zones.

**`cad/fitcheck_slot.py`** builds the electronics as solids where the design puts them —
the board, a component envelope that respects the two assumptions above, the Dupont tails
off the header, the D1 mini with its Dupont headroom, its USB plug, the buzzer, the LED,
the tape in the slot — and intersects each with the body and the lid in build123d. Exact
volumes, not bounding boxes. Then it slides the module down its insertion path in six
steps. First run: **five collisions**.

1. The slot's plan-view corners were rounded 2.5 mm (copied from the cassette's *face*
   radius). A cassette's thickness edges are square, so the slot would have pinched all
   four corners — 14.8 mm³ of overlap. Now 0.8 mm (`s_slot_r`), with a check that it
   never grows past 1.2.
2. The LED body ran 0.7 mm into the front-left screw post. Moved 6 mm right, keys with it.
3. The top lip's ends reached the corner zones. Narrowed from 24 to 16 mm.
4–5. Modelling artefacts: the USB plug is *meant* to stand outside the wall, the tape is
   meant to stand out of the top. The check now knows.

Second run: **0.00 mm³ on every part, insertion path clear.** So "the reader sits inside"
is a computed statement about the exported geometry, resting on two photographed-not-
measured assumptions that the sweep also carries. Full sweep: eight parts, 128 corners,
0 failures, 694 s.
