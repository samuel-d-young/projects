# Putting the tap player together

The order matters more here than on most printed boxes, because two of the
parts have no fastener of their own. The fascia is held by the lid. The PN532
is held by the fascia. Get the order wrong and you will be taking it apart
again — and one of the steps is only possible in one direction.

`cad/fitcheck_tap.py` checks every one of these moves against the real solids.
If you change anything near the front opening, the rails or the lid, run it.

## Parts

| Printed | Count | Prints |
|---|---|---|
| `tap_body` | 1 | upside down, top face on the bed |
| `tap_fascia` | 1 | face down |
| `tap_lid` | 1 | outside face down |
| `tap_mark_1..4` | 4 | flat — one colour each |
| `knob_big`, `knob_small` | 1 each | flat, base down |
| `vu_diffuser` | 1 | **white PLA**, smooth face down |
| `cart_shell` + `cart_back` | 1 each per cartridge | face down / flat |

Nothing needs supports. If something does, the change that caused it is wrong.

| Bought | |
|---|---|
| PN532 NFC module (Elechouse V3 footprint) | 1 |
| ESP32 DevKit | 1 |
| WS2812B 8-LED ring + one single WS2812B | 1 each |
| 5 mm LED, passive buzzer | 1 each |
| M3 pan head × the length in `params.py` | 4 |
| Small zip ties — **small, not medium** | 2 |
| NTAG215 25 mm disc | 1 per cartridge |

The zip-tie note is not fussiness. Behind the board the strap has
`pcb_clr + lip_t + s_mount_gap` to stand up in, which is **1.8 mm at the
tightest corner of the sweep**. A medium tie is 3.6 × 1.6 — it does not fit.

## Order

1. **Dress the fascia while it is still a flat plate on the bench.** Knobs into
   their two recesses, the white diffuser into the dial's dish, and the 5 mm
   LED pushed into its hole from the back. All three are far easier now than
   reaching into a closed machine, and the LED in particular has to go in
   before the face does — its hole is only reachable from inside afterwards.
2. **Glue the four mark arcs** into their recesses in the top of the body,
   smallest first. They are 0.8 mm deep and sit flush.
3. **Drop the VU ring in through the bottom**, into its cradle behind the
   front wall. It lands between the two ribs, against the back stops, with the
   single WS2812B in its centre hole. Solder before fitting — there is no room
   for an iron in there afterwards.
4. **Slide the PN532 in through the front opening**, flat, **component side
   up**, until it meets the stop at the back. It goes into a slot, not onto a
   ledge: it will feel snug, with about 0.35 mm of movement. Header tails hang
   down into the cavity.
5. **Slide the fascia UP into its channel from underneath.** The chamfer on
   the back of the flange is the lead-in — start it square and push until the
   top of the flange meets the roof. This is the step that only works in one
   direction, and it is why the lid is not on yet.
6. **Fit the ESP32 to the lid**, USB towards the left wall, under the corner
   lips and the two mid-edge lips. Zip-tie it through the two stations so
   plugging a cable in does not move it.
7. **Seat the buzzer** in its locating ring on the lid.
8. **Put the lid on and screw it down** — 4 × M3 from below. The lid is now
   also what stops the fascia sliding back out.

## Taking it apart

Backwards from 8. Four screws, lid off, then the fascia drops down and out of
the bottom of its channel. Everything else follows.

**That is the whole reason to own a second fascia in a different colour** — a
face change is four screws and no glue, provided you glued the knobs and the
diffuser onto the *fascia* and not into the body.

## Printing the label

The shell's face has a recess for a printed label, the same idea as the
cassette's sticker. Print, cut, peel, press — it finishes just below flush, so
nothing catches when the cartridge is picked up.

| | |
|---|---|
| **Artwork size** | **51.0 × 54.5 mm** |
| Corner radius | 0.5 mm |
| At 300 dpi | 602 × 644 px |
| Recess depth | 0.30 mm — paper is 0.10–0.20, vinyl 0.15–0.25 |
| Position | centred left to right, **2.25 mm below centre** top to bottom |

It sits low on purpose: the bevelled corner takes a 9 mm bite out of the top
left, and a label centred vertically would run into it.

The compact-cassette label, for comparison, is **94.3 × 57.7 mm**.

## Programming a cartridge

Tag, movie, automation: `home-assistant/docs/NFC-MOVIES.md`, under "Finding
the id for a cassette".

Building one:

1. Drop the NTAG215 disc into the **ring** on the shell's floor. It is a ring
   that stands up, not a pocket cut down — the floor is only 1.6 mm and the
   tag is most of that.
2. **Turn the back plate over** — it is printed spigot up and fits spigot
   down — and glue it into the rebate. The spigot lands on the tag and holds
   it against the floor, which is what keeps the read distance the same every
   time. Its bevelled corner is mirrored to suit the flip, so it will only go
   in one way round; if it does not drop in, it is the right part upside down.
3. Label on, and program it from the Projects → Cassettes tab.
