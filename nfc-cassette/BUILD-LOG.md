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

## 2026-09-19 — The face comes off, and prints in three colours

Samuel: "change the front of the housing so that it can be glued on and be
printed in multiple colours. Similar to the base, but with the details printed
with an AMS system." So the front face stops being a face and becomes a part.
Three new solids — `slot_face`, `slot_face_keys`, `slot_face_trim` — twelve
parts in all.

**Why it could not be coloured where it was.** Every cosmetic thing lived on
the body's front wall, and the body prints top-face-down, so that wall is
vertical. A vertical face puts each key across a hundred layers with a sliver
of it in every one; an AMS changing filament by layer paints stripes, not
keys. The fix is not a slicer setting — the face has to lie flat on the bed,
which means it has to be its own part. Everything else follows from that.

**Detail side UP, not down.** The tempting orientation is show-face-down for
the bed's finish, with the detail as inlays the AMS fills. It is wrong here:
the keys stand 3 mm proud and the bezel 1 mm, and face-down those are
overhangs off the bed. Face-up, every raised thing grows upward and every dent
opens upward — which is the repo's standing rule, arrived at from the other
direction — and **the 45-degree chamfer on each key's top edge is no longer
structural.** It was there to keep that edge from overhanging on a vertical
wall. It stays because it is what a moulded key looks like.

**It is the lid's trick, turned through 90 degrees.** A rebate `s_face_t` deep
in the front face, a rim of wall `s_face_ledge` wide around it, the plate glued
in flush — the same shape as the pocket the lid drops into. Two clamps in
`derive()` keep panel and wall from starving each other: `s_face_t` can never
leave less than `s_face_back` of wall behind it, and `s_face_ledge` never less
than 0.8. At `wall` 2.0, the sweep's thin corner, that is 1.2 of panel and 0.8
of wall. **Glued over its whole area the two are one laminate again**, which is
the argument for taking the rebate out of the wall rather than growing the body
forward and moving everything inside it.

**What stayed on the body.** Only what has to reach through it: the LED hole
and the dial's eight wedge slots and centre hole. The panel spends `k_dimple`
of its thickness on the dial's dish, the wall behind keeps the rest, and the
slot depth that collimates each pixel is unchanged at 1.6 mm — so the diffuser
sits exactly where it sat, 0.40 proud of the face and 0.60 below the bezel rim,
and its own checks never moved.

**Three solids, one origin.** The plate carries every hole and dent, plus the
counter window's three digit bars (they rise out of its floor, so they belong
to the thing that supports them). The keys are one solid, the dial's bezel and
the counter frame another. They touch the plate at `z = s_face_t` and never
overlap it, so the slicer loads all three as one object and gives each a
filament. 3.2 g, 0.7 g, 0.2 g.

**Two leaks, both from the gate, neither visible in the B-rep.** The first
version built valid solids that exported as a **non-watertight** `slot_body`,
and `_lib.emit` deleted the STL rather than ship it:

- The rebate was inset from the body's ends by `s_face_ledge` alone, the way
  the lid's pocket is. That works for the lid because its pocket is extruded
  along the same axis as the body's corner fillets. This one is extruded along
  Y, **across** them, so an inset in X does not follow the curve: the rebate
  reached `|x| = 62.5` where the face is flat only to 59.7, and its floor met
  the rolling fillet at a **57 micron** tangent. Inset by `corner_r` first.
- The rebate's bottom edge sat exactly on `s_lid_t`, which is the seam where
  the lid skirt is unioned to the body. A cut landing precisely on a union seam
  tessellates into a leak. `s_face_sill` lifts it 0.6 clear — 0.2 was enough —
  and gives the panel a rim on its fourth side, so it is now captured all
  round, which is what "similar to the base" should have meant in the first
  place.

Both now have invariants, so neither can come back quietly.

**The keys moved up 1 mm**, `s_buttons_cz` 9.0 → 10.0. With the sill in, a key
at 9.0 had its bottom edge 0.2 mm off the panel's own bottom edge with no plate
under it. Nothing else on the face moved.

**Checks.** `verify.py`: twelve parts built and exported, **128 corners, 0
failures**, 966 s. `fitcheck_slot.py` passes and is **byte-identical to the
baseline** — as it must be, because nothing inside the body moved: the rebate
only takes material off the outer surface of a wall. Renders not re-run: this
session had no `robot/cad/render.py`, so `shots_slot.py` is updated for the new
part (it stands the flat panel up and puts its glue face on the rebate floor)
but unproven. Run it before trusting `docs/nfc-cassette-slot.png`.
