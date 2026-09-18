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
cad/cassette.py      tray + lid
cad/player_slot.py   THE player: body with the slot and the front face, bottom lid, two
                     knobs, and the VU dial's white-PLA diffuser
cad/player.py        the earlier flat-bay player (base + top slab), kept as an alternative
cad/verify.py        the gate: build, export, invariants, corner sweep - all nine parts
cad/fitcheck_slot.py "does the reader sit inside?": the electronics as solids, exact
                     intersections with body and lid, the two printed parts against
                     each other, and the module's and the lid's insertion paths
cad/shots_slot.py    docs/nfc-cassette-slot.png; shots.py does the flat version
cad/_lib.py          export gate (watertight, winding, volume drift, build volume)
stl/ step/           build output + manifest.json. Regenerating is always safe.
                     STEP carries an export timestamp in its header, so all nine
                     files go dirty on every run even when nothing moved - and so
                     do the STLs, which re-tessellate. Neither file going dirty
                     means a part moved: diff manifest.json on volume_mm3 and
                     extents_mm, and check out whatever reads 0.000.
```

## Run

```
K:\Claude\robot\.venv\Scripts\python.exe cad\verify.py          # ~12 min: nominal + 128-corner sweep
K:\Claude\robot\.venv\Scripts\python.exe cad\fitcheck_slot.py   # ~20 s: must end "the reader sits inside"
K:\Claude\robot\.venv\Scripts\python.exe cad\shots_slot.py
```

Run the fit check after any change near the module pocket, the slot, the
front face or the lid: it found three real collisions the invariants missed,
and a fourth once it started intersecting the body with the lid — the D1
mini's mount was 0.5 mm inside the back wall, so the bottom could not go on.
**Two printed parts that touch must be intersected with each other.** Checking
each of them against the electronics is not the same check.

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
