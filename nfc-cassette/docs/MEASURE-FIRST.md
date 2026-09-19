# Measure these before you print

Ten minutes with calipers, then `params.py`, then `verify.py`. The CAD is
parametric: every number below is a single line in `cad/params.py`, and the
parts rebuild from it. Nothing here needs editing a part file.

The design already survives the whole range of each of these — that is what the
sweep is for. What it cannot survive is a real part that sits **outside** the
range, and the four marked **critical** are the ones where that is plausible.

## The order to do it in

Measure, edit `cad/params.py`, then:

```bash
K:\Claude\robot\.venv\Scripts\python.exe cad\verify.py
```

If it prints `0 failures`, print the parts. If it names an invariant, the
number you entered is outside what the design can absorb — that is a redesign,
not a slicer setting, and the message says which relationship broke.

## The list

| # | Measure | Parameter | In range now | If you are wrong |
|---|---|---|---|---|
| 1 | **ESP32 board length** — the PCB, not the pins | `esp_l` | 48.0 – 56.5 | **Critical.** Sold as the same thing at 48.2, 51.5 and 55. The board is datumed from its USB end, so being wrong never moves the USB out of its cutout — it loses grip at the far end. The two mid-edge lips still hold it; the corner ones stop touching. |
| 2 | **ESP32 board width**, across the PCB | `esp_w` | 25.4 – 28.5 | **Critical.** Quantised, not continuous: the two header rows are either 1.0" or 1.1" apart. Guess the wrong one and the lips miss the board by 2.5 mm — they grip on width, so this is the one that actually holds it down. |
| 3 | **Tallest thing on the PN532's component side** (the DIP switch), above the PCB | `pn532_comp_h` | 4.0 – 5.5 | **Critical.** It sets how close the antenna gets to the tag. Too small and the module fouls its slot; too large and the read range quietly shrinks. Currently 4.5, giving 5.95 mm antenna-to-tag against a limit of 12. |
| 4 | **NTAG215 disc diameter** | `tag_d` | 22 – 30 | **Critical.** The cartridge's pocket is built around it. 25 mm is the common coin; check what actually arrived. |
| 5 | LED ring outer diameter | `s_ring_od` | 31 – 34 | The cradle grips this. Wrong by a millimetre and the ring is loose between its ribs. |
| 6 | LED ring centre hole | `s_ring_id` | 16 – 21 | Only matters because the single WS2812B lives in it. |
| 7 | The single WS2812B's board | `s_dot_od` | 8 – 12 | Has to clear the ring's hole. |
| 8 | Micro-USB plug boot, W × H | `esp_usb_w`, `esp_usb_h` | 12–14.5, 7–9.5 | The cutout is sized for the plug, not the socket. A fat boot will not go in. |
| 9 | PN532 header pin length below the board | `pin_below` | 2.5 – 3.5 | Your soldering choice, not the board's. Both headers ship unpopulated. |
| 10 | Game Boy cartridge, if you want the silhouette exact | `cart_l`, `cart_w`, `cart_h` | 54–60, 62–68, 7–9.5 | Cosmetic. Nothing functional depends on it. |

## What is already known and does not need measuring

- **PN532 board, 42.7 × 40.4 × 1.6** — datasheet, Elechouse V3 footprint, and
  the photos of Samuel's board agree to ±0.5 mm.
- **Compact cassette, 100.4 × 63.8 × 12.0** — IEC 60094-7.
- **ID-1 card, 85.60 × 53.98** — ISO/IEC 7810.
- **M3 clearance 3.4, pilot 2.5** — real fastener sizes, as everywhere else.

## The honest caveat

A photograph can measure a footprint. It cannot measure a height. Everything in
the "tallest component" line of the table came from looking at pictures of the
boards, and heights are the numbers most likely to be wrong. They are also the
ones the sweep protects least well, because a height that is wrong by 2 mm is
usually outside the range rather than inside it.
