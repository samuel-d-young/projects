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
cad/player_slot.py   THE player: body with the slot and the front face, bottom lid, two knobs
cad/player.py        the earlier flat-bay player (base + top slab), kept as an alternative
cad/verify.py        the gate: build, export, invariants, corner sweep - all eight parts
cad/fitcheck_slot.py "does the reader sit inside?": the electronics as solids, exact
                     intersections with body and lid, and the module's insertion path
cad/shots_slot.py    docs/nfc-cassette-slot.png; shots.py does the flat version
cad/_lib.py          export gate (watertight, winding, volume drift, build volume)
stl/ step/           build output + manifest.json. Regenerating is always safe.
```

## Run

```
K:\Claude\robot\.venv\Scripts\python.exe cad\verify.py          # ~10 min: nominal + 128-corner sweep
K:\Claude\robot\.venv\Scripts\python.exe cad\fitcheck_slot.py   # ~20 s: must end "the reader sits inside"
K:\Claude\robot\.venv\Scripts\python.exe cad\shots_slot.py
```

Run the fit check after any change near the module pocket, the slot, the
front face or the lid: it found three real collisions the invariants missed.

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
- The module is held by four corner posts and the slab, not by its mounting
  holes, on purpose: the hole positions on the clone boards are not trusted.
