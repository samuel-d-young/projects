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
