# Bill of materials

**Nothing is ordered. Nothing should be, until [Phase 1 of the runbook](RUNBOOK.md#phase-1--measure-20-minutes-0)
is done.** Two of those five measurements decide whether items on this list get bought
at all.

Every line is tagged **(verified)** — a live product page was read on 2026-08-28 and
the price taken off it — or **(assumed)** — indicative, re-check at the cart. AUD,
inc GST.

Following the `wall-clock` project's convention: **check the shed before ordering.**
Several of these are things a person with two 3D printers, a laser cutter, an xLights
box and a drawer of Pi accessories very likely already has.

---

## Tier 0 — buy nothing, do this first

| Item | Cost |
|---|---|
| Block the DVR's outbound path on the router | **$0** |
| MAC reservations for `.42`, `.66`, `.70`, `.75`, `.83` | **$0** |
| Give the HA guest 8 GB of the 16 GB host | **$0** |
| Backblaze B2 bucket with Object Lock for the tier-1 set | **~$0.30/month** |

Roughly thirty cents a month buys the only thing on this page that survives the house
burning down. Everything below is optional by comparison.

---

## Tier 1 — the three boards that deploy (~$130–220)

Assumes the boards, and probably several of the accessories, are already on hand.

| # | Item | Where | AUD | Status |
|---|---|---|---|---|
| 1 | 4× official Raspberry Pi 15 W USB-C PSU (`gaffer`, `sparks`, `runner`, spare) | Core Electronics | **~$12 ea / $48** | verified |
| 2 | 1× official Raspberry Pi 27 W USB-C PD PSU (Pi 5) | Core Electronics | **$21.07** | verified |
| 3 | 3× generic A1 32 GB microSD | any | ~$15–20 ea | assumed |
| 4 | 500 GB 2.5" SATA SSD + ASMedia USB3–SATA bridge — for `sparks` | general retail | **~$85** | assumed |
| 5 | 5× 20 × 20 × 6 mm passive aluminium heatsinks | AliExpress | ~$8 | assumed |
| 6 | FTDI USB-to-RJ45 Cisco console cable — for `gaffer` | — | ~$25–30 | assumed |
| 7 | Hard case, 0.25 m Cat6 whip, 5V/3A USB-C power bank — for `runner` | — | ~$60 | assumed |

### The three power traps, all of which cost an evening if missed

**Skip the multiport GaN charger.** It looks like the tidy answer — one brick, five
short leads — and it is a trap. Almost no GaN charger advertises a 5V/5A or 5.1V/5A
PPS profile; they jump straight to 9 V and 12 V. A Pi 5 on one boots, then silently
clamps its total USB peripheral budget to 600 mA. Five official bricks cost about $69
and each failure is independent.

**Check board revisions before buying cables.** Pi 4B **rev 1.1** boards (manufactured
before roughly February 2020) have the known USB-C CC-resistor fault and **refuse to
power from e-marked USB-C cables**. This bites precisely on spare boards of unknown
vintage — which is exactly what these five are.

**A2 microSD cards are a Pi 5 feature.** A2's advantage comes from Command Queueing,
which needs a CQHCI engine: BCM2712 has one, BCM2711 does not. An A2 card in a Pi 4
buys nothing and can measurably lose to a plain A1. And "high endurance" cards are the
wrong tool for a root filesystem — they carry no A-class rating and are specified for
sequential CCTV recording, not the small random I/O an OS does.

---

## Tier 2 — the rack itself (~$300–380) — **gated on the switch**

> **Read the Cisco's model number before ordering the rack.** Practical clearance in a
> 10-inch rack is about 210 mm. A 16- or 24-port managed switch is usually 19-inch —
> and if it is, a 10-inch rack cannot hold the one device everything else plugs into.
> That is a five-minute check that decides a $249 purchase.

| # | Item | Where | AUD | Status |
|---|---|---|---|---|
| 8 | **DeskPi RackMate T2**, 12U 10-inch, open frame | PLE Computers (VIC stock) | **$249** | verified |
| 9 | 0.5U 10" cable entry panel with brush strip | Core Electronics | **$29.95** | verified |
| 10 | ~15 short Cat6 leads (0.25 m / 0.5 m), two colours | AliExpress | ~$70 | assumed |
| 11 | M2.5 × 6 mm screws + brass standoffs, 100 pk | AliExpress | ~$12 | assumed |
| 12 | PETG filament | on hand | $0 | — |
| 13 | 3 mm Baltic birch ply, 600 × 300 | Melbourne supplier | ~$15–25 | assumed |

**Not the T1.** At ~198 mm deep it physically excludes a desktop Synology and most
mini-PCs. The T2's extra depth is the point.

**Do not pre-buy cage nuts.** The RackMate ships with its own M6 screw and nut set.
Open the box first.

**Do not re-terminate the camera runs** to fit a patch panel. That is a day of work to
make a photograph look better.

### Print and cut, rather than buy

Two Bambu printers and a Glowforge Aura make the mounting hardware nearly free:
four 1U Pi trays are about **$15 of PETG and an afternoon**, against roughly $100 each
for bought equivalents.

**The 254 mm vs 256 mm trap.** A full-width 10-inch rack panel is 254 mm. The P1S bed
is 256 × 256 mm *with an 18 × 28 mm front-left exclusion zone* for the AMS cutter — and
a 250 mm part already trips it. A 254 mm panel **will not print flat**.
*Fix:* rotate the plate 45° in Bambu Studio. A 254 × 44.45 mm panel rotated 45° has a
211 mm bounding box in both axes. Or use two 127 mm half-width panels, which is what
most community mini-rack designs adopted anyway.

**The Glowforge trap: not clear acrylic.** The Aura is a 6 W *diode* laser. Glowforge
explicitly lists clear, translucent and white acrylic as incompatible — a diode's
wavelength passes straight through transparent material instead of ablating it. Use
3 mm Baltic birch ply or **black cast** acrylic for blanking panels, vented panels and
engraved fascias.

Engrave the hostname *and* the address into each fascia — but **not before the DHCP
reservations from Phase 0 exist.** Engraving `.75` into a permanent panel while the
router is still free to move it is how a rack starts lying to you.

---

## Tier 3 — conditional, and each on a specific answer

| # | Item | Buy only if | AUD | Status |
|---|---|---|---|---|
| 14 | Pimoroni NVMe Base (2280-capable) + NVMe stick | `.70` boots from NVMe | ~$26 + stick | verified (base) |
| 15 | Official Raspberry Pi M.2 HAT+ | you want 2230/2242 only | $21.29 | verified |
| 16 | Pi 5 Active Cooler | the Pi 5 does sustained work | **$8.80** | verified |
| 17 | UPS, ~1200 VA / 720 W line-interactive | you want coordinated shutdown | ~$250–330 | assumed |
| 18 | Tapo P110/P115 energy-monitoring plug | you want the power figure measured, not estimated | ~$25–35 | assumed |
| 19 | ESP32 + SHT30 or DS18B20 rack temperature sensor | before considering any fan | ~$16 | assumed |
| 20 | Waveshare **isolated** RS485 HAT | the FPP show player happens | ~$40 | assumed |

**The official M.2 HAT+ takes 2230 and 2242 only.** A 2280 stick will not screw down.
If you want a large drive, buy a 2280-capable third-party base.

**Stay at PCIe Gen 2.** Raspberry Pi's own documentation says the Pi 5 is not certified
for Gen 3.0 and that Gen 3.0 links may be unstable. On a rack node that runs unattended,
take the stable link.

**Do not buy a fan yet.** A Pi 4B is 2.9 W idle and 6–8 W loaded; a passive heatsink
handles it indefinitely in an open rack. This rack lives in a house, a quiet bedroom is
about 30 dBA, and anything audible from two metres has failed. Fit the temperature
sensor first and only revisit a fan if it shows sustained rack air above ~40 °C.

**If the UPS happens, make `.66` the NUT master**, not the Synology. `.66` is the
machine whose shutdown *ordering* matters — the HA guest has to halt before its
hypervisor does. And note the step everyone misses: **the Home Assistant NUT
integration does not shut anything down by itself.** It gives you sensors. You still
need an automation on the battery-runtime sensor that calls `hassio.host_shutdown`.

---

## What it costs to run

| | Watts | kWh/yr | ~$/yr |
|---|---|---|---|
| This rack (3× Pi 4 + 1× Pi 5 idle, PSU losses) | ~19 W | 166 | **~$43** |
| Existing always-on infrastructure (separate) | — | — | ~$180–230 |

At roughly 26 c/kWh **(assumed — Victorian Default Offer 2026-27; confirm from an
actual bill, since most households are not on the default offer).**

The honest framing: **this rack adds about $43 a year.** It is not the reason the power
bill is what it is. Put the Tapo plug on it and turn that estimate into a measurement —
which is the house rule about (verified) versus (assumed) applied to itself.

---

## Rough totals

| Scenario | AUD |
|---|---|
| **Tier 0 only** — do nothing else | **~$4/year** |
| Tier 0 + the three boards, on a shelf | ~$130–220 |
| \+ the rack, printed trays, cut panels | ~$430–600 |
| \+ UPS and metering | ~$700–950 |

The first row is not a joke. It is the row with the best return on this page.
