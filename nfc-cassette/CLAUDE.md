# nfc-cassette — the cassette player for the NFC movie cards

A 3D-printed "cassette player" that is really an NFC reader, and printed
cassettes that each hold one NTAG215 card. Drop a tape in, the movie plays.
The idea is bharms27's r/3Dprinting build (a printed Walkman body with a
phone dock and NFC cassettes for Spotify); here the phone is replaced by a
PN532 + D1 mini under the bay floor, and Home Assistant does the playing.

The electronics, firmware, automation and the step-by-step guide live in the
**home-assistant** repo (`docs/NFC-MOVIES.md`, `config/esphome/nfc-reader-d1mini.yaml`).
This repo is only the enclosure. Read `BUILD-LOG.md` last entry first.

## Layout

```
cad/params.py        every dimension, with provenance (datasheet / derived / choice / assumed)
cad/cassette.py      tray + lid, compact-cassette size
cad/cartridge.py     THE cartridge: Game Boy silhouette, one 25 mm NTAG215 disc + back plate
cad/player_tap.py    THE player: tapped, not slotted. Body, the removable fascia, the lid,
                     and the four arcs of the contactless mark on the top
cad/player_slot.py   the slot player it replaced. Still built, and still the home of
                     _front_cosmetics, _rounded_box, _posts_and_lips and break_outer_edges
cad/player.py        the earlier flat-bay player (base + top slab), kept as an alternative
cad/verify.py        the gate: nominal build + export, then two exhaustive invariant
                     passes that build nothing, then the geometry sweep - all 18 parts
cad/fitcheck_tap.py  "does it go together, and does it read?" - the electronics as solids,
                     exact intersections with body and lid, and the path every hand-fitted
                     part has to travel: the fascia out of the bottom of its channel, the
                     module out the front, the ring down through the lid opening
cad/fitcheck_slot.py the same for the slot player
cad/shots_slot.py    docs/nfc-cassette-slot.png; shots.py does the flat version
cad/_lib.py          export gate (watertight, winding, volume drift, build volume)
stl/ step/           build output + manifest.json. Regenerating is always safe.
                     STEP carries an export timestamp in its header, so all eighteen
                     files go dirty on every run even when nothing moved - and so
                     do the STLs, which re-tessellate. Neither file going dirty
                     means a part moved: diff manifest.json on volume_mm3 and
                     extents_mm, and check out whatever reads 0.000. Diff `bodies`
                     too - a part can come apart into pieces without its volume or
                     its extents moving at all, which is exactly what the counter
                     window's digit bars did.
```

## Run

```
K:\Claude\robot\.venv\Scripts\python.exe cad\verify.py          # the gate: nominal + 278528 invariant corners + 1024-corner geometry sweep
K:\Claude\robot\.venv\Scripts\python.exe cad\verify.py --quick  # nominal only, ~15 s
K:\Claude\robot\.venv\Scripts\python.exe cad\fitcheck_tap.py    # must end "the tap player goes together and reads"
K:\Claude\robot\.venv\Scripts\python.exe cad\fitcheck_slot.py   # must end "the reader sits inside"
```

Before the first print, read `docs/MEASURE-FIRST.md`: four of the numbers
this design is built on have never been near a pair of calipers.

`docs/ASSEMBLY.md` is the order it goes together in, which on this machine
is load-bearing: the fascia is held by the lid and the module is held by the
fascia, so two of the steps only work in one direction.

Run the fit check after any change near the module's rails, the front
opening, the fascia or the lid. It has now found six real problems the
invariants missed, and every one of them was a part that **fitted where it
sat and could not be got there**: a mount 0.5 mm inside the back wall, a VU
ring with something standing in its centre hole, a module whose components
stood 0.75 mm above the opening it slides through, and two complete fascia
designs that seated perfectly and could never have been assembled.

**A sweep checks that numbers stay sane. Only a path check asks whether a
person can put it together.** And **two printed parts that touch must be
intersected with each other** — checking each against the electronics is
not the same check.

The robot venv is the one with build123d and trimesh. Nothing here needs
anything else.

## Rules

- **No dimension in a part file.** Parts read `D[...]` from `params.derive()`.
  Change a number in `params.py`, run `verify.py`, look at the render.
- Every part prints flat, open or recessed side up, **no supports**. If a
  change needs supports, the change is wrong.
- `assumed` parameters (module thickness, the DIP switch height, USB plug
  boot, header pin length) have never been measured on Samuel's parts. Check
  them with calipers before the first print; the sweep covers their ranges,
  but a value outside the range is a redesign, not a slicer setting.
  Photos of the board (2026-09-18) confirmed `pn532_l`/`pn532_w` to ±0.5 mm and
  settled `s_edge_free` in plan, but a photo cannot measure a height, so the
  heights are all still assumed.
- The module is held by four corner posts and the slab, not by its mounting
  holes, on purpose: the hole positions on the clone boards are not trusted.
  (The photos show only two holes, on a diagonal, which settles that.)
- **Anything standing on the lid keeps `s_mount_gap` off the cavity wall**, and
  the check measures the ROUNDED cavity: a square mount corner does not fit a
  filleted one, and measuring the flat wall misses it.
- The front face can only be opened **below the slot floor** unless the slot is
  moved back: above it, the cassette slot is directly behind the wall. The VU
  dial exists because `f_slot0` now includes the LED ring's depth.
- A support whose top meets a curved part sets its height from the **inner**
  edge of its own footprint — where the curve is lowest across that width.
- **A part that passes the export gate can still be in pieces.** Watertight,
  consistent winding and correct volume are all true of two closed shells
  sitting next to each other. `_lib.py` counts bodies for exactly this reason;
  if you add a feature by union, check it actually touches something.
- **A part that is printed one way up and fitted another is handed.** The flip
  moves any asymmetry — a bevel, a keyed corner — to the other side. Build it
  in print orientation and mirror the outline so it lands right when turned
  over; do not print a mirrored copy.
