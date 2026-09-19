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

## 2026-09-18 — The bottom could not go in, and the board measured

Samuel: "the bottom doesn't go in properly. Make it recessed and move the mount in
the bottom, it hits the edge." He is right, and it was worse than a tight fit.

**The lid was jammed, not tight.** Intersecting the two printed parts — which
nothing had ever done — puts **31.85 mm³ of the lid inside the body**. The D1
mini's mount (corner posts and lips) is derived to stand `pcb_clr + lip_t` =
1.5 mm outside the board, but the cavity was only sized to clear the *board*:
`f_back_inner` allowed `cavity_clr` = 1.0 mm behind it, so the mount drove
**0.5 mm into the back wall**. On the left it was exactly flush — `s_d1_cx` put
the outer lip face on the cavity wall, 0.00 mm of clearance, which is an
interference fit once a printer has had its say. **(verified — exact boolean
volume, not an estimate.)**

Why nothing caught it: `fitcheck_slot.py` intersected the *electronics* with the
body and with the lid, and never the body with the lid. The invariant that looks
like it covers this (`slot: D1 mini through the back wall`) checks the board's
edge plus air, not the mount that holds it. A full 128-corner sweep passed.

**Three fixes, all in params.**

- `s_mount_gap` (0.6, range 0.4–1.0): everything standing on the lid keeps this
  much off the cavity wall. `f_back_inner` and `d1_needs` now budget for the
  mount rather than the board, so the **body grows instead of the mount being
  squeezed** — the same pattern that already stopped a thick wall crushing the
  D1 against the module's rib. Body 127.4 × 47.0 → **127.9 × 48.1**.
- **The lid is recessed.** It was a flat plate butted against the bottom rim,
  located by nothing but four screws through 3.4 mm clearance holes. Now the
  outer wall carries on down past it (`s_lid_ledge`, 1.2 mm) and the lid drops
  into that pocket with `s_lid_clr` = 0.25 per side, flush with the bottom and
  stopped by the step where the pocket meets the narrower cavity. Printed
  top-face-down that rim is the last thing laid, on top of the full wall — no
  overhang, still no supports.
- **The lid is its own thickness.** It was `floor` = 2.4 mm with a 2.5 mm
  counterbore for the screw head: the counterbore went **through the plate**,
  leaving a 6.2 mm hole and nothing for the head to pull against. `s_lid_t` =
  `screw_head_h + s_lid_under_head` = **3.7 mm**. Costs 1.3 mm of height (body
  47.2 → 48.5) and gives a deeper, better-locating recess.

The cavity's inner fillet then became the binding constraint — a square mount
corner cannot sit in a round corner, and the first version of the new check
missed it because it measured the flat wall. `s_cavity_r` is now capped at
`s_mount_gap`, so the corners stop pinching, and the check measures the true
rounded boundary. At `s_mount_gap` = 0 the guard fails and the parts overlap;
at every value in the swept range they are clear. **(verified.)**

`fitcheck_slot.py` now intersects lid against body, seated and on the way in.

**The board, measured at last.** Samuel photographed the PN532, front and back.
Perspective-corrected and calibrated on the 2.54 mm header pitch, with the
PN532's 6 × 6 mm QFN as a cross-check, the back gives **40.3 × 42.6 mm** against
the drawing's 40.4 × 42.7 — **`pn532_l` and `pn532_w` are confirmed (verified,
±0.5 mm)**; the aspect ratio matches the drawing to 0.2%. (The front photo
rectified badly — a 207 px² edge residual against the back's 2.4 — and claimed
32 × 35. Ignore a rectification whose edges do not fit.)

What else the photos settle:

- The **42.7 mm edges are the ones the 8-pin and 10-pin headers run alongside**,
  at 6.3 and 9.5 mm in; the 4-pin runs alongside a 40.4 edge. The top and bottom
  lips press on the 42.7 edges, so they share an edge with the 8-pin header — but
  a 2.54 header body reaches no closer than ~5.1 mm and the lip reaches 1.5 mm,
  so `s_edge_free` = 2.0 has **~3.6 mm to spare (verified in plan)**.
- The DIP switch **is** the tallest thing on the component side **(verified)**.
  Its height is still **(assumed)** — a caliper job.
- **Both headers are unpopulated.** `pin_below` is Samuel's soldering choice, not
  the board's, and it sets `s_tail` = 17 mm and so the body's whole depth.
  Right-angle headers or wires straight to the pads would save ~14 mm.

Still nothing printed. `pn532_t`, `pn532_comp_h`, `usb_w`/`usb_h` and
`s_corner_zone` remain **(assumed)**; a photo cannot measure a height.

`docs/nfc-cassette-slot.png` is **stale** — it still shows the butted lid. `shots_slot.py`
imports the render module from the robot repo, so it has to be re-run on Samuel's machine.

**Sweep:** `s_mount_gap` joins the swept parameters, so the corner sweep is **256
corners, not 128** — eight parts rebuilt at each. **0 failures**, 2516 s on the
machine that ran it; budget roughly double whatever `verify.py` used to take.

## 2026-09-18 (later) — A VU dial: nine pixels behind eight wedges

Samuel has a WS2812B 8-LED ring and a single WS2812B, and wants the player to
change colour with what it is doing, in a retro register. Shown four ways it
could read through the right-hand grille, he picked the **VU dial** — a bezel
with eight wedge slots, one per pixel — and solved the problem that had made me
rule it out: **"just move the tape insert back."**

**Why that was the unlock.** On the old body the only part of the front face
with open cavity behind it was the strip between the lid and the underside of
the slot floor — **9.8 mm**. Everything above that backs onto the cassette slot,
where a through-hole would open into the tape. A 32 mm ring could not go there.
Moving the slot back puts the ring in front of it instead: the ring now lives in
the gap between the inside of the front wall and the front face of the slot
block. **`f_slot0` = wall + ring stack + 0.5**, so the body goes **48.1 → 52.8 mm
deep (verified)**; width and height do not move, so the face keeps its shape.

**The dial.** Shallow raised bezel (a tall boss on a vertical face is a
half-cylinder overhang — the reason the knobs are separate parts), a dished
face, eight wedge slots and a centre hole for the single LED. My worry that the
wedges were a print risk was **wrong**: each bridges ~9 mm, in a wall that
already bridges 13 mm for the slot floor. No supports anywhere, still.

**The ring is held** by two ribs that run vertically — so they print as fins on
a vertical wall rather than as overhangs — a stop across the top, and two posts
on the lid. Two things the geometry caught, both about the posts' tops: taking
the height from the post's **centre** leaves them 1.2 mm proud of the rim, and
from the **outer** edge 3.1 mm proud. The rim curves away, so across the post's
width it is lowest at the **inner** edge, and that is what sets the top.

**The face had to be re-laid-out.** A 38 mm dial put the ring straight through
the front-right screw post. The front LED moves left and the keys with it; the
dimpled speaker grille is gone, the dial replaced it, and the body dropped from
55k triangles to 13k.

**And the sweep caught the re-layout.** The first attempt put the LED at −51,
which is fine at nominal and **failed 16 of 128 corners**. At `wall` = 3.0 a
thicker wall grows `s_L` through `d1_needs` but pulls the screw post inward
faster, and −51 left **0.05 mm between the LED body and the post** — touching.
The face is now LED **−49.5**, keys **−39.5**, dial **36.5**, which passes all
128. Tightest margins across the sweep: ring to post **+0.65**, LED to post
**+1.05**, keys to dial **+2.00**. A face this crowded has to be placed against
the worst corner, not against nominal.

**One compromise, written down.** The wedges reach r = 15 and the LEDs' outer
corners are at 15.25, so **0.25 mm of each pixel sits behind the wall**. Making
the wedge swallow the LED whole needs r1 ≥ 15.25, which pushes the bezel past
what the face has room for. The invariant asks the wedge to *overlap* the LED
generously, not contain it.

**Not keyed.** Nothing clocks the ring's rotation. There is ±6° of slack between
a wedge and its LED, and the LEDs are visible through the wedges at assembly, so
it is set by eye. A locating pin would need the ring's mounting-hole positions,
which have not been measured.

Electronics, firmware and the wiring drawing are in the **home-assistant** repo:
nine pixels chained on **D8**, ring first, `DO` into the single LED's `DI`.

`docs/nfc-cassette-slot.png` is stale again — it predates both the recessed lid
and the dial.

---

---

## 2026-09-18 (later still) — Render re-run; zip ties hold the D1 mini down

**The render is current again.** `docs/nfc-cassette-slot.png` was rebuilt from the
committed STLs on Samuel's machine. The assembled views now show the body's outer
wall running unbroken to the table with no grey plate under it — the recessed lid
reads correctly **(verified: the body's cross-section is a 409.6 mm² ring from
z = 0 to 3.7 and opens out to the floor at 4.0; the lid plate is solid to 3.7 and
its 125.0 × 45.2 footprint sits inside the body's 127.9 × 48.1 at the table)**.

**Zip-tie hold-down** (Samuel: "hold down the d1 mini too, and so the board is
fastened when plugging in the cable"). Two small straps cross the board.

- **Why across and not along.** The D1 mini is boxed in. Both short ends have
  `s_mount_gap` = 0.6 mm to the cavity wall and the module rail, and the back
  edge has 2.10 mm; only the front has room (15.6 mm to the cavity wall below the
  slot block) **(verified from `derive()`)**. A strap running along the board
  would have to anchor at the USB end, which is where the plug goes. Across is
  the only way, and it only works because the corner lips are 4 mm stubs — the
  middle 29.2 mm of both long edges is clear.
- **The detail.** Each strap is a pair of through-slots in the lid — one in the
  gap behind the board, one just outside the front lip line — joined by a groove
  in the lid's **outside** face, so the return run sits below flush and the
  player still stands flat. The groove is `tie_t + tie_clr` = 1.6 mm deep and
  leaves 2.10 mm of the 3.70 mm lid, which is only affordable because the lid
  got thicker when it was recessed.
- **It cuts, it does not add.** Nothing new stands on the lid, so the mount keeps
  its `s_mount_gap` and the fit check is unchanged: still `RESULT: the reader
  sits inside`, lid seated 0.00, approach clear **(verified)**.
- **Small ties only.** The strap stands up in `pcb_clr + lip_t + s_mount_gap`
  behind the board — 2.10 mm at nominal but **1.80 mm at the tightest corner of
  the sweep**, so `tie_t` is capped at 1.3 and a medium 3.6 × 1.6 tie does not
  fit **(verified: the invariant fails at that corner)**. The 2.5 × 1.2 figures
  are off a bag marked "100 mm × 2.5 mm" and are **(assumed)** until Samuel puts
  calipers on one.
- **Assembly consequence, not a CAD collision.** The whole 14 mm above the board
  is reserved for Dupont plugs, and a strap crossing the board crosses both
  header rows. Leave the two header positions under each strap unpopulated, or
  take those wires off the other end. The fit check cannot see this — the strap
  is not modelled.

**Checks.** `fitcheck_slot.py` passes. The four tie parameters swept against the
four that move the D1 mini — 256 corners — give **0 failures**.

---

## 2026-09-18 (evening) — A diffuser for the dial, in white PLA

Samuel: "create a diffuser for where the LED rings will be. It will be printed
in white PLA." One new part, `vu_diffuser` — the ninth. **The body does not
change**, on purpose: the disc is clamped to what the existing dish and bezel
allow rather than the dish being deepened to suit it, so nothing that was
already verified moves.

**A disc, not plugs.** The obvious design fills each wedge slot with a plug.
That is worse: the 2.4 mm slot behind the face is a collimator, and a plug
would carry light sideways into the web instead of letting the wall block it.
The diffuser is a plain disc that caps the slots and the centre hole, r = 16.20
against the dish's 16.50, and it glues in like the knobs glue into their
recesses.

**It sits inside the bezel.** The dish is `k_dimple` = 0.80 deep and the disc is
1.20 thick, so it stands **0.40 mm off the face and 0.60 mm below the bezel
rim** — proud enough to glue against a flat floor, sunk enough that the bezel
takes any knock. `k_vu_diff_t_eff` clamps the thickness to
`k_dimple + k_vu_bezel_proud - 0.2`, so no corner of the sweep can push the disc
above the rim.

**The grooves, and why they taper.** A continuous disc lets light cross the web
between neighbouring wedges, which blurs the eight segments Samuel picked the
dial for. Eight grooves on the back face, one per web, cut that path in half
(0.60 mm of PLA left of 1.20). They keep a **constant 0.45 mm margin of web at
every radius**, so they are not annular sectors: the web is an annular strip and
widens with radius, and a constant-angle slot is starved at `k_vu_r0` or opens
into a wedge at `k_vu_r1`. Half-angle is `gap/2 - margin/r`:

| radius | web | groove | margin each side |
|---|---|---|---|
| 8.50 (`k_vu_r0`) | 1.34 | 0.44 | 0.45 |
| 12.75 (LED circle) | 2.00 | **1.10** | 0.45 |
| 15.00 (`k_vu_r1`) | 2.36 | 1.46 | 0.45 |

**Where the groove cannot go, it does not go.** The web pinches at `k_vu_r0`,
and over the dial's full parameter ranges most corners leave less than a nozzle
width once the margins are taken. `k_vu_diff_grooved` is derived, and the disc
comes out **plain** rather than carrying a groove the slicer would silently
drop. **3072 of 4096 corners come out plain; nominal is grooved, at 0.44 mm.**
The wall's 1.60 mm webs are still doing most of the segmenting either way — the
groove is an improvement, not the mechanism.

**Prints smooth-face-down, grooves up.** No supports. The face that shows gets
the bed's finish. 951.8 mm³, about 1.2 g.

**Checks.** The six diffuser parameters swept against the six that move the dial
and the wall — 4096 corners — give **0 diffuser failures**. `fitcheck_slot.py`
is unchanged, as it must be: the body did not move.

---

## 2026-09-19 — Tapped, not slotted: the cartridge format, and a face that comes off

**The brief changed twice in one sitting.** First: the compact cassette is too
big, give me four retro sizes that still read as retro, build the Game Boy one.
Then, mid-answer: *"it will no longer be a slot to put the cards into, they
will be tapped. So that light is really important here."* And then two more: no
indent on the top, a multicoloured contactless symbol instead; and the front
face has to come off so it can be printed in other colours.

Those are four different machines' worth of change, and they all land on the
same body.

### Why tapping makes the light the whole interface

A slot gave three confirmations for free: a detent you can feel, a thunk you
can hear, and a tape standing 30 mm proud that you can see across the room.
Tapping gives none of them. The dial going amber and then white is now the
*only* signal that anything happened, which is why the dial stays on the
**front** — visible from where you are standing — rather than moving to the
top, under the hand that is doing the tapping. **(decision, Samuel confirmed:
"Still the front.")**

### The body barely moved, which was the surprise

Take the slot out and the box stays 127.4 x 73.7 x 48.5. The slot was never
what set the size: the face has to carry a 38 mm dial, which is what makes the
body ~48 tall, and the ESP32 plus the face's furniture is what makes it ~127
long. What changed is the inside — the PN532 stops standing upright behind a
slot and lies **flat under the top, antenna up**, 5.95 mm from a tapped
cartridge's tag **(derived; the limit is 12)**.

### The face took three designs, and only the fit check could tell

Each of the first two seated perfectly. Each satisfied every invariant. Each
was impossible to assemble, and the sweep said nothing, because a sweep checks
that numbers stay sane and only a path check asks whether a person can put the
thing together.

1. **Flange behind the opening.** The flange is wider than the hole, so the
   only way out is backwards into the cavity — past the VU ring, the module's
   rails and the ESP32. Measured: the flange was **124.4 wide against a 122.6
   cavity**. It could not have been fitted in the first place.
2. **Hook or tilt in over a top lip.** Killed by the dial. The bezel is 38 mm
   tall in a cavity 42.4 mm tall, which leaves **2.1 mm of frame above the
   opening**. There is nothing up there to grab.
3. **Slide up into a channel, open at the bottom.** Left, right and the roof
   hold the flange; the lid, screwed on underneath, is what stops it sliding
   back down. Taking the lid off is already the way into this machine, so a
   face change costs four screws and no new parts. The fascia is a flat plate:
   no hooks, no undercuts, nothing that prints badly face down. The step
   between plate and flange is chamfered 1.0 mm, which is both the lead-in that
   finds the channel and the thing that turns a 1.5 mm unsupported ledge into a
   45-degree wall.

The strip of front wall above the opening — **1.55 mm** — is the entire
retention at the top, so `params.py` sizes it from the dial rather than from a
typed number, and the sweep guards it.

### The dial can outgrow the body, and always could

Deriving the opening's top edge from the dial turned up a fault that predates
all of this: **`k_vu_r1` at the top of its range makes a bezel that does not fit
the cavity at all**, fascia or no fascia. The old sweep never touched
`k_vu_r1`, so it had never been asked. `s_H` is now `max(module stack, what the
dial needs)` — at nominal the stack wins by 2 mm and nothing moves, and the
term only binds where the dial would otherwise be cut. Three more range faults
fell out of the same pass:

| Found | Why it never showed | Fix |
|---|---|---|
| `k_vu_r1` low end puts the wedge slots inside the LED circle | `k_vu_r1` was not swept | low end raised to 14.3, the floor for the widest ring in range |
| REC lamp hard-coded at x 12.0, collides with a grown bezel | same | placed from the bezel's edge instead of from a number |
| a 1.8 mm channel in a 2.0 mm wall leaves 0.2 mm of front | new relationship | the choice is a ceiling: `min(choice, wall - 0.8)` |
| a 2.5 mm ledge inside a 2.0 mm frame leaves nothing | new relationship | `min(choice, inset - 0.8)` |

And one real coupling: **the slot player's top lip hangs off the roof** while
its PCB sits on the lid's shelf. That only worked while the module's stack was
what set the body height. The moment anything else could make the body taller,
the lip rose away from the board it is meant to hold down. It is now set from
the PCB.

### The three mounts, which were all located and none held

Samuel asked for the best dimensions for mounting the LEDs, the Node MCU and
the NFC module. Measuring what was actually there first:

| | Was | Now |
|---|---|---|
| **PN532** | rested on two ledges with **1.95 mm of daylight** to the roof — and that daylight *is* the read distance, so the same tap read differently depending on how the board settled | a **slot**: a second ledge over the top turns two rails into a channel, 0.35 mm of play on a 1.6 mm board. The upper ledge reaches in 1.0 mm, less than the lower one, so it stays on the board's edge margin and off the antenna coil |
| **VU ring** | located in X and Z by two ribs and two lid posts, held in Y by **nothing** — 64 mm of cavity to fall back into | a back stop 2.5 mm deep x 12 tall on each rib, so the ring is trapped between the stop and the fascia and cannot rock |
| **ESP32** | four corner lips, sized to the length keyed into `params.py` | plus **two lips at the middle of each long edge**. The board is sold at 48.2, 51.5 and 55 mm under the same name; on a short one the corner lips hold nothing at all, and the middle is where every variant has board. `esp_l`'s swept range now covers all three |

The board is datumed from its **USB end**, so being wrong about the length
loses grip at the far end but never moves the USB out of its cutout. That was
worth getting right — a centred board once put the USB 22.3 mm from its hole.

`docs/MEASURE-FIRST.md` is the ten-minute calipers card: which four numbers are
critical, what each one breaks, and what is already known from datasheets and
does not need measuring at all.

### Edges

Every printed body now has its outline broken top and bottom, 0.6 mm. Not only
cosmetic: these bodies print top face down, so the break at the top of the part
is the first layer and takes the elephant's foot that a square edge shows as a
lip you can feel, and the break at the bottom is the last layer, sloping inward
as it rises, so it is self-supporting.

It is done by **subtracting a tapered ring**, not with `chamfer()`, because
`chamfer()` could not do it. A chamfer propagates along tangent-continuous
edges, so asking for the tap body's back edge asks for the whole loop, and the
loop runs through the junction where the front opening, the skirt and a corner
fillet all meet at z = 0. OCC refuses that junction, and refusing it fails the
whole operation — **all seven bottom edges failed individually, for the same
reason**. A boolean has no opinion about junctions. The cartridge is a clean
bevelled prism with no such junction, so it keeps `chamfer()`.

### Checks

`cad/fitcheck_tap.py` is new and is the reason any of this is trustworthy. On
the real built solids, never on the numbers that made them: every board
intersected with body and lid, everything inside the envelope, the lid's
approach, **the fascia sliding out of the bottom of its channel**, the module
sliding out the front, the ring dropping out, and a tapped cartridge sitting
clear with its tag in range.

The gate now runs in two stages. The geometry sweep can only afford a handful
of parameters because every corner rebuilds eighteen solids; the invariants
cost microseconds, so they get their own exhaustive pass first, over the
eighteen that drive the face and the mounts — **262144 corners**. That pass is
where all five range faults above were caught, and it is where the fascia's two
impossible designs would have been caught if the relationships had existed to
catch them.

### The cartridge had no invariants, and both of its features were broken

Grepping the gate for cartridge checks returned nothing: the newest part in the
repo had never been guarded. Writing the checks found two faults immediately,
and neither would have shown up on a print — both parts would have come off the
bed looking right.

**The tag's pocket did nothing.** It was cut as a cylinder starting at
`cart_wall`, which is exactly the z the cavity floor already starts at, so it
removed material that was already gone. Every cartridge would have had a 25 mm
disc loose in a 54 × 62 box, which is the precise failure the comment above it
said it was preventing. Cutting the pocket any lower is not the fix either: the
floor is 1.6 mm and the tag is most of that. It is now a **ring that adds
material** — ID `tag_d + 2 × tag_clr`, 1.2 wall — plus a **spigot on the back
plate** that holds the disc down on the floor. The ring stops it sliding; the
spigot stops it floating, and floating is read distance. The spigot is derived,
not assumed: at the thin end of the cartridge with the thick end of the tag
there is no room for one, and it comes out without rather than with a 0.45 mm
boss the slicer would drop. **15360 of 16384 corners get it; nominal does.**

**The tag did not land on the antenna.** `t_pad_cx` was 0 and the module sits
at −6.65, so a cartridge tapped in the middle of the pad put its tag 6.65 mm to
the side of the coil. Nothing said so, because `t_antenna_to_tag` only ever
measured the **gap** and never the **offset**. The pad now follows the module —
the mark, the pad and the antenna are the same place by construction — and
there is an invariant that a tapped tag lands inside the module's footprint in
both directions.

Four more range faults fell out of the cartridge's first invariant pass, all
the same shape as the fascia's: a choice whose range does not fit the thing it
is cut into.

| Found | Fix |
|---|---|
| a 0.60 recess in a 1.2 wall leaves 0.6 mm of shell | depth is `min(choice, wall − 0.9)` |
| a 2.0 label margin inside a 4.0 corner radius cuts through the rounded corner | margin is `max(choice, corner_r)` |
| the locating ring taller than the cavity it stands in | height is `min(tag + clearance + 0.4, cavity − 0.4)` |
| a 0.45 mm spigot | derived away, as above |

### The gate, final shape

Two exhaustive invariant passes that build nothing, then the geometry sweep:

| Stage | Corners | Cost |
|---|---|---|
| face and mounts — 18 parameters | 262144 | 23 s |
| cartridge — 14 parameters | 16384 | 1 s |
| geometry — 10 parameters, 18 solids each | 1024 | the long one |

In groups, exhaustive within each, rather than all twenty-eight parameters at
once: 2²⁸ is not a stronger check so much as one that never finishes. Each
group holds the parameters that actually reach each other and the rest sit at
nominal. `tag_t` is in the **geometry** sweep for one reason — it is what
decides whether the back plate gets its spigot, and a conditional feature only
ever built at nominal is a feature nobody has checked.

Every range fault in this design was found in those first two stages. Each of
them satisfied nominal perfectly.

### One part in two pieces, and what that found

The back plate is handed now, and it was not before. It was a flat bevelled
prism, symmetrical top to bottom, so it did not matter which way up it went in.
The spigot made it matter: it is **built in its print orientation, spigot up**,
and it **installs turned over**, and that flip swings the bevelled corner across
to the other side of a bevelled seat. The outline is mirrored to suit, so it
lands the right way round once it is turned over.

This came to light in the render, of all places — the spigot was sitting on top
of the cartridge like a doorknob, because the render placed the part the way it
was built rather than the way it is fitted.

**And mirroring it broke it in a way nothing could see.** Reversing the
polygon's points reverses its winding, `extrude` follows the face normal, so
the plate extruded *downward* from the sketch plane while the spigot was added
*above* it. The part came out as two solids with 1.6 mm of air between them.

It exported clean. Two closed shells are still watertight. Their windings are
still consistent. Their volumes still add up to exactly what the B-rep says,
because the B-rep is also two solids. Every check in `_lib.py` passed, and the
file would have sliced, printed as two loose parts, and only then made sense.

So `_lib.py` now counts bodies, and refuses anything that is not exactly one.
Running every part back through it found the bug I was looking for — and two
more I was not:

> **`slot_body`: 4 disconnected bodies, not 1**
> **`tap_fascia`: 4 disconnected bodies, not 1**

The three loose pieces in each are the **tape counter's digit bars**. The
window recess is cut from `face − 1.6 − k_dimple` back to `face + k_dimple`, so
its floor is at `face + k_dimple`; the bars were centred at `face − 0.4`,
0.8 mm in front of that floor, touching nothing. Three 4 × 0.8 × 5.5 slivers
floating in a hole — in **every build of this face since the counter window was
first drawn**, on a part that has been through the sweep 128 corners at a time
and come back clean every single run.

Watertight. Consistent winding. Volume exactly as the B-rep said. They would
have come off the bed loose and nobody would have known what they were.

The bars now stand on the window's floor, derived from it rather than from a
number that happened to be right once.

### What the checks actually catch, in order of what they have found

| Check | What only it can see |
|---|---|
| invariants | a relationship between two numbers going wrong at the edge of a range |
| **one body** | a part in pieces. Watertight, correct volume, correct winding - and in pieces |
| fit check | a part that fits where it sits and cannot be got there |
| volume drift | a tessellation that quietly dropped a face |
| corner sweep | a boolean that fails somewhere other than nominal |

Three of the five have now found something the other four could not.

**Parts: 18.** Tap player = body, fascia, lid, four mark arcs; cartridge =
shell + back. Everything prints flat or recessed side up, no supports.
