# mini-round-clock enclosure — v14

Built on top of the base and diffuser Sam remodelled. Three clock sizes: the
**24-LED** body at 107.99 mm, which is his; a **32-LED** body at 119.85 mm,
which the bigger ring forces; and a **60-LED** body at **240 mm**, where perspex
light guides make each LED read 30 mm long. All three share one rear housing
design that carries the ESP32-S3, and all three get a desk stand.

```
python3 measure_uploaded.py    # re-derive every number in params.py from his STLs
python3 build_v2.py            # write the STLs and 3MFs
./runchecks.sh                 # five verification passes, all three bodies
python3 render.py              # picture sheets
```

`base_in.stl` and `diffuser_in.stl` are Sam's uploads, kept so the whole thing
re-derives from source. `measure_uploaded.py` prints the table `params.py` holds
— if he sends new files, run it and diff.

---

## Print these

Pick a body. Everything in one column goes together; nothing crosses over.

| | 24-LED (108 mm) | 32-LED (120 mm) | 60-LED (240 mm) |
|---|---|---|---|
| base | `-base` | `-base-32` | `-base-60` |
| housing | `-housing` | `-housing-32` | `-housing-60` |
| diffuser | `-diffuser` | `-diffuser-32` | `-diffuser-60` |
| **numerals** (2nd colour, §9) | `-numerals` | `-numerals-32` | `-numerals-60` |
| **collar gauge** — print FIRST, §2 | `-collar-gauges` — one part, any body | | |
| **board gauge** — print FIRST, §2 | `-board-gauge` — one part, any body | | |
| **board clamp** + 2 × M3 × 10, §2 | `-board-clamp` — one part, any body | | |
| **bar screen** *(alternative)* | — | `-base-32-bar` + `-diffuser-32-bar` | `-base-60-bar` + `-diffuser-60-bar` |
| light guides *(optional)* | — | — | `-light-guides-60`, or cut perspex — §7 |
| desk stand *(optional)* | `-deskstand` | `-deskstand-32` | `-deskstand-60` (a very big print) |

Every filename is prefixed `mini-round-clock`.

| File | Orientation | Support | Solid volume (24 / 32 / 60) |
|---|---|---|---|
| base | **deck face down** | see note | 105 / 138 / 521 cm³ |
| housing | **rear plate down** | none | 55 / 66 / 210 cm³ |
| diffuser | **face down, 0.20 mm layers, SOLID face** | none | 16 / 26 / 140 cm³ |
| numerals | *not printed alone* — see §9 | none | 0.07 / 0.10 / 0.21 cm³ |
| desk stand | flat on its desk face | none | 219 / 264 / 1003 cm³ |
| light guides | flat, **clear or natural PETG** | none | — / — / 31 cm³ |
| board gauge | plate down | none | 13 cm³, any body |
| board clamp | **top face down** | none | 0.8 cm³, any body |
| base **-bar** | **deck face down** | see note | — / 140 / 523 cm³ |
| diffuser **-bar** | **face down, 0.20 mm layers, SOLID face** | none | — / 25 / 138 cm³ |

**Those are solid volumes, not filament.** The stand is a big blocky part —
print it at 8–10% infill with 3 walls and it lands around 60–80 g. Mass is not a
problem there; it is the counterweight for a 74 mm deep clock.

**Support note for the base.** The part is designed to need none and the checker
confirms it introduces none, but Sam's own geometry carries 409 mm² of shallow
overhang at 33–40° — the lead-in ramp at the top of the display-tab slot. That
is the same in the file he uploaded. It is inside the slot, which is open and
easy to pick out.

**Material.** PETG rather than PLA if a lithium cell is going in. PLA's glass
transition is ~55–60 °C; PETG's is ~80 °C. See §7.

---

## 1. What was found in the uploaded files

Three things worth knowing before printing anything.

### The base has a disconnected 605 mm³ solid in it

`Mini_Wall_Clock_Base.stl` contains a second shell — a crescent at
r 35.06–40.90, ±41.9° about +x, z 11.80–15.75 — that is **not attached to the
body**. Its faces sit exactly on the main body's cut surface, and it arrived as
a +2832 / −2227 mm³ shell pair. That is the signature of a CAD boolean that
failed to merge, not a feature.

It sits precisely in the window the display tab has to pass through. Sliced
as-is, it prints as an extra crescent of plastic exactly where the display goes.
`build_v2.py` drops it and says so when it runs.

### The module's rim — a conclusion that was wrong, twice over

**This section used to argue that the module's rim is under 2.20 mm.** The
argument ran: the collar lands at z = 10.80, the seat is at 8.60, so a collar
that is not touching means a rim under 2.20 — and Sam had reported the screen
*loose* rather than the diffuser standing proud.

He has since reported the opposite: *"the insides of the diffuser is still too
long that touches the screen."* So the rim is **over** 2.20, and the reasoning
above was inference from an absence, which is the weakest evidence there is.

Worse, it did not need inferring. `DISP_T` = **4.00** is the module's overall
thickness and it was in `params.py` the whole time; on a seat at 8.60 that puts
its front face at **12.60**. The collar at 10.83 was 1.77 mm inside it. The
assertion that should have caught that compared the tip against the module's
bare *tab* instead — see §7.

The collar's length is derived off `Z_SEAT + DISP_T` now, so this cannot drift
again. If your module is thicker than 4.00, change `DISP_T`.

### The wire slot goes right through

The straight-down channel is open front to back — at 180° there is no material
at all from z = 0 to z = 22 for r 31–43. The plywood face covers it at the
front, so it was never visible, but the deck now closes it from behind, which
also encloses the electronics. A 4 × 16 mm port is cut through the deck beside
the S3's USB-C end so the battery lead can still get up to the board.

---

## 1b. v3 — the changes after your test fit

### The tab slot was the looseness

You measured the tab that sticks out of the bottom of the screen: **30.55 mm**.
The slot was cut as an angular wedge sized for a 40 mm tab, which at r = 35 is
**46.62 mm wide**. Against a 30.55 mm tab that is ±25.9° of free rotation — the
screen could sit a quarter-turn of a clock face off true. That is
"doesn't stay upright".

Two walls either side now bring it to **31.15 mm**:

| | before | after |
|---|---:|---:|
| slot width at the tab | 46.62 mm | **31.15 mm** |
| tab can rotate | ±25.90° | **±0.47°** |
| screen edge can move | 12.5 mm | **0.22 mm** |

The walls run from the deck up to the ring pocket floor, with a 45° lead-in
chamfer on the top inner edge so a slightly rotated tab still finds its way
down. They sit at |y| ≥ 15.575 and the S3 board is |y| ≤ 12.70, so the two never
meet.

**A side effect worth having:** the tab window had removed the ring pocket floor
across ±41.8°, leaving the ring unsupported over a 83° arc at 12 o'clock. The
walls put that floor back everywhere the tab is not — the checker measures it at
100% of the sector outboard of the slot.

### The press fit is on the collar, inside, where the screen is

> *"The diffuser is now too tight and dones't fit properly. Also I want the
> press fit to be on the inside where the screen is not the outside."*

Both of those, and the first one was my fault. Here is what happened, because it
matters for trusting the rest of this.

#### Why v8 made it too tight

v8 measured where the diffuser comes to rest by pushing it into the **bare
base** — no LED ring in the pocket, no display module in the bore. With nothing
else in there, the outer crush ribs were the only thing stopping it, so it read
a seat of z = 21.52, concluded the band had only 1.40 mm inside the bore, and
took it from Sam's 4.00 mm to 6.00.

The seat is not set by the ribs at all. The base's inner wall — the one between
the screen bore and the ring pocket — tops out at **z = 19.03**, a 4.9 mm wide
annular land at r 30.19–35.11, and the diffuser's face lands on it. So the face
sits at 19.03–21.03 and everything on the diffuser is at `z = 21.03 − z_diff`.
Which puts the band's underside at:

| band | lands at | LED ring top | clearance |
|---|---:|---:|---:|
| 4.00 mm — Sam's | 17.03 | 15.00 | **+2.03 mm** |
| 6.00 mm — v8's | 15.03 | 15.00 | **+0.03 mm** |

0.03 mm is nothing. At 6.00 the band reaches the LED ring before the face
reaches its stop, so the diffuser jams proud and rocks on the ring instead of
seating. That is what "too tight and doesn't fit properly" feels like.
**The band is back to 4.00.**

`check2` §9 now places the diffuser at that seat and measures the ring clearance
there, so this cannot happen again quietly.

#### And the fit itself moves inside

The outer wall grips **nothing**. It drops into the ring pocket with **0.40 mm
of clearance on diameter** and the eight outer crush ribs are gone.

#### Why it kept being too tight — and what v12 does about it

Three rounds of "too tight" in a row, so the answer stopped being a choice of
number.

**v10's mistake** was leaving the collar itself at Sam's own **30.108** OD in a
**30.19** bore. That is 0.164 mm on diameter, and on an FDM printer that is not
clearance at all — an external cylinder comes out 0.10–0.20 over and a bore
0.10–0.30 under, so the pair can print as an interference across the whole
190 mm of circumference. Six ribs on top of that were never a crush fit.

**v11 turned the collar to 29.90** and dropped the interference to 0.20 mm. Still
too tight in his hands — which is data: his printer is running further out than
the nominal figures allow for.

**v12 stops arguing about the number and separates the two things:**

```
bore            30.19 measured across the flats
collar OD       29.60  ->  1.18 mm of CLEARANCE on diameter
6 crush ribs    1.00 mm wide, standing 0.64 mm proud of that wall
crest           30.24  ->  0.10 mm of interference on diameter
```

The wall now has **twelve times** as much clearance as the ribs have
interference. A printer would have to be more than half a millimetre out before
the wall itself touches anything — and *that* is the failure a rib-height knob
cannot tune away, which is why it kept coming back. `check2` asserts that ratio
now, not just the interference.

The fit can afford to be light: the clock hangs with the diffuser's axis
horizontal, so gravity never pulls it out. It only has to resist being knocked.

#### Print the gauge first

`mini-round-clock-collar-gauges` — **three rings, five minutes, about 9 g.**

Each is a real 8 mm section of the collar — same OD, same wall, same rib width,
same lead-in — at a different rib height, with its figure in hundredths of a
millimetre debossed on top:

| marked | crest | against the 30.19 bore |
|---|---:|---:|
| **0** | 30.194 | +0.01 mm on diameter — line to line |
| **5** | 30.244 | +0.11 mm — what ships |
| **10** | 30.295 | +0.21 mm — what v11 shipped |

Push each into the base's screen bore. Whichever wants a firm push and stays put
is your printer's answer; put its number over 100 into `COLLAR_RIB_H`. If even
**0** is tight, your printer is running the boss over or the bore under, and the
answer is a negative figure — try −0.05.

#### And print the board gauge first too

`mini-round-clock-board-gauge` — **the S3 frame on a plate, about 15 g.** Same
reason, different fit: see §2. Between the two of them, the only two fits in
this design that have ever come back wrong can both be settled in half an hour
of printing before anything large goes on the plate.

This is what should have been shipped three rounds ago instead of another
guess.

#### How long the collar is, and why v11 overshot

> v11: *"the inside ring that goes onto the screen can be longer."*
> v12: *"The inside it now too long, make it the same length it was before."*

v11 derived the length from where the module's face was *assumed* to be — its
seat at 8.60 plus a bare 1.60 mm PCB — and reached the collar to exactly there.
It over-reached, which means the rim at the r = 29 circle is thicker than a bare
PCB.

That matters more than it sounds. The diffuser's face rests on the base's land;
a collar that touches the module **first** holds the whole diffuser off that land
and the clock sits proud — which is another of the ways this has felt tight.
**Too long is worse than too short.**

**v14: it is derived now, not chosen.** Sam, twice — *"the inside is now too
long"*, then *"the insides of the diffuser is still too long that touches the
screen"*. Both times a number was picked and both times it was too big, so it
stopped being a number:

```
tip        = DIFF_WALL_CREST − COLLAR_LEN            exact, by construction
COLLAR_LEN = DIFF_WALL_CREST − (Z_SEAT + DISP_T + COLLAR_TIP_CLR)
           = 19.03 − (8.60 + 5.60 + 0.90)
           = 3.93                        v14: 6.03    v13 and before: 8.20
```

**v18, the fourth report.** *"the inside of the diffuers it too long. Shorten it
and make the inside fit tighter."* `DISP_T` had also been wrong — 4.00 against a
module that measures **5.60** — and `COLLAR_TIP_CLR` went 0.40 → **0.90**,
because 0.40 mm is clear on paper and inside what two printed parts move by.
0.90 is still under the 1.00 mm ceiling on how far the module may float, so the
collar goes on restraining it. See below for where the lost grip is paid back.

**And the check that was meant to catch this was measuring the wrong surface.**
It compared the tip against `Z_SEAT + DISP_TAB_T` = **10.20** — the top of the
module's bare *tab*. The collar does not land there. It lands at r 28–30, on the
module's **front face**, and the module is `DISP_T` thick on a seat at 8.60 —
4.00 was the figure in params at the time, so that face was at **12.60**. (It is
5.60 now: the 4.00 was itself wrong, and v17 corrected it. See v18 below.) The collar was 1.77 mm inside the screen and
the assertion passed, because the ceiling in it was a feature 2.40 mm lower down
than the one the collar actually hits.

| | tip at | module face | |
|---|---:|---:|---|
| v13 | 10.83 | 12.60 | **1.77 mm into the screen** |
| v14 | 13.00 | 12.60 | +0.40 mm clear |
| v17 | 14.60 | 14.20 | +0.40 mm clear, on the real `DISP_T` = 5.60 |
| v18 | 15.10 | 14.20 | **+0.90 mm clear** |

`check2` takes the tip off the **built diffuser** — not off params — and compares
it to `Z_SEAT + DISP_T`, asserting both directions: clear of the screen, and
within 1.00 mm of it. Measuring the built mesh rather than recomputing is the
whole reason it caught v17's collar coming out 0.87 mm longer than params
claimed, when `COLLAR_EXTEND` went negative and there was no trim branch.

**A shorter collar has less of itself in the bore, so the grip moves to the
ribs**, which is what Sam allowed for: *"it can be a tight fit for that inside
part"*, then *"make the inside fit tighter"*. Retention on a crush fit is roughly
count × interference × friction, and of the two terms only the count is free:

| | v14 | v18 | why |
|---|---:|---:|---|
| ribs | 6 | **8** | the free term |
| interference | 0.15 (0.30 ⌀) | **0.19 (0.38 ⌀)** | 0.1975 is the hard ceiling |
| lead-in taper | 1.20 | **0.60** | so 3.23 mm of rib survives a 3.93 mm collar |

The ceiling is not arbitrary. The invariant is that **the wall behind the ribs
must have at least 4× the clearance the ribs have interference**, so the wall can
never quietly become the fit itself — which is the failure that produced *"still
too tight"* three times. At `COLLAR_OD` 29.40 the wall has 1.58 mm on diameter,
so 0.1975 is the most the ribs can have. Turning the collar down further to allow
more would make them tall thin fins that bend instead of crushing, which feels
loose, not tight. Hence the extra two ribs instead.

`check2` asserts **3.00 mm of rib engagement**, and a 1.20 lead-in on a 3.93 mm
collar leaves only 2.63. The taper moved, not the assertion — a check is not the
place to absorb a geometry change. At 0.19 mm of rib over 0.60 mm the ramp is
17.6°, which still leads the collar into the bore. The gauge prints **0.10 /
0.15 / 0.20**, which brackets 0.19.

**If your module is thicker than 5.60 mm, change `DISP_T` — not `COLLAR_LEN`.**
Everything downstream follows, including `COLLAR_RIB_Z1`.

### The face is thicker, and only the aperture is thin

> *"update the diffusers so that only the part that is meant to be seen through
> the LED is thin, otherwise there is bleed and you can see through where you're
> not meant to."*

First thing was to check whether the model was actually thin somewhere it
shouldn't be. Probed across the built face, it was not: a flat 2.00 mm
everywhere except the aperture at 0.20. So the bleed was not a hole in the
model — it was 2.00 mm of white PLA still passing light.

Two things changed, and one of them is a slicer setting rather than geometry.

**The face is 2.90 mm.** That is 45% more material in the way, and it is the
most that will fit: the face sits in the base's front recess between the wall
crest it rests on at 19.03 and the front of the clock at 22.00, which is 2.97 mm
and no more. At 2.90 it finishes 0.07 mm inside the front — effectively flush,
which it never was before. `DIFF_SEAT_Z` and `BAND_TOP` are both derived from
`FACE_T` now, so nothing downstream can drift when it moves.

**Sam's own inner face is filled out too.** Raising `FACE_T` only thickens the
band this project rebuilds, from r = 34.50 out; inside that it is his mesh and it
stayed 2.00. It is filled to the same thickness now, so there is no step and no
thin ring around the screen window.

**The aperture flares behind the membrane.** A 2.90 mm face would otherwise
leave each dot at the bottom of a deep narrow slot, visible head-on and nowhere
else. The hole is 2.00 × 4.00 mm at the membrane and opens out 0.80 mm on every
side by the time it reaches the cell, so the viewing angle survives the thicker
face.

**And slice the face SOLID.** At 0% infill a 2.90 mm face is a shell with air in
it, and air does not block light. This is very likely a large part of what you
were seeing. Set the diffuser to 100% infill, or enough top and bottom shells
that 2.90 mm is solid at your layer height.

**If it still bleeds**, the remaining answer is material rather than geometry:
white PLA is translucent at any thickness a clock face can carry. The fix is an
opaque body with translucent lens inserts at the dots — the same two-filament
workflow as the numerals, but it needs the aperture to become a through-hole and
a third part. Say the word and I will add it.

### One layer over the LEDs### One layer over the LEDs

The membrane was 0.80 mm. It is now **0.20 mm** — a single layer at 0.20 mm
layer height, and the diffuser prints membrane side **down**, so it is the first
layer and there is no bridging.

**Slice the diffuser at 0.20 mm layer height.** At any other layer height a
0.20 mm feature does not land on a whole number of layers.

The thinning cut **steps around all 24 cell walls** and leaves a small buttress
at each base. Thinning straight through them would have left every wall standing
on nothing — the checker confirms all 24 still reach full height.

A 0.2 mm sheet is fragile in the hand. It is captured between the ring and the
plywood once assembled, so it only has to survive the bench.

### The aperture is a radial tick now, not an arc

> *"the line needs to be perpendicular to the screen, like the lines are. I want
> the LED's to look more like the echo wall clock led's."*

v4 narrowed the lit band to a 2.50 mm arc. That was still the wrong axis: an arc
lies **along** the circle, so a lit LED reads as a dash going the wrong way. Each
cell's aperture is now a **radial tick** — 2.00 mm across, 4.00 mm long, pointing
at the centre, radiused ends, centred on the LED circle at r = 40.75.

| | v3 | v4 | **v5** |
|---|---:|---:|---:|
| lit aperture | 5.90 mm band | 2.50 mm arc | **2.00 × 4.00 mm tick** |
| one lit LED reads | 5.90 × 9.72 | 2.50 × 9.72 | **2.00 × 4.00** |
| which way it points | — | along the circle | **at the centre** |
| dark between two LEDs | 0.95 mm | 0.95 mm | **8.67 mm** |
| face either side | 0.80 (glows) | 2.00 | **2.00** |

Why it reads like the Echo: 8.67 mm of plain white between one tick and the
next, so the ring is 24 separate marks rather than a segmented ring, and each
mark is a mark rather than a blob. A 5050 spans r 38.25–43.25 and the tick sits
inside that at 38.75–42.75, so it is lit evenly end to end.

#### v18: more of a line, and one length per body

> *"update the wall clocks diffusers so that there is more of a line for the
> LED's to shine through."*

`TICK_W` is 2.00 → **1.40** — a line is thin, and 1.40 is still 3.5 bead widths
— and the length stopped being a literal. Each body now derives its own from two
constraints, and takes the smaller:

* **its cell.** The tick stops `TICK_CELL_MARGIN` = 0.70 short of the ribs at
  each end, because those ribs are what stop the light leaking between LEDs —
  the bleed Sam reported two rounds ago. An aperture cannot outrun its own cell.
* **the face's radial budget.** Everything inboard of the tick — the gap, the
  hour marks, the numerals — is pushed toward the screen window as the tick
  grows, and a numeral is not allowed to reach the bore.

| | tick | ratio | limited by |
|---|---:|---:|---|
| 24 | 5.04 × 1.40 | 3.6:1 (was 2.0:1) | **the screen window** |
| 32 | 4.42 × 1.40 | 3.2:1 | the cell |
| 60 | 30.50 × 1.40 | 21.8:1 | the light guides |

On the 24 it is the **window** that binds, not the cell — the cell would allow
6.70. There are 12.83 mm between the LED circle and the window, and the stack
inboard of the tick already wants 9.80 of them (0.40 gap + 0.30 + 2.60 mark +
0.30 + 1.20 margin + 5.00 numeral), which leaves 3.03 for half a tick. The first
version of this took the cell figure and drove the numerals 0.32 mm over the edge
of the window before the second constraint existed.

**If a longer line on the 24 matters more than what is inboard of it**, there are
exactly three levers: `NUM_H_24` 5.00 → 4.40 (the floor at which the numeral stem
is still two clean 0.4 mm beads, worth 0.60 mm), `MARK_LEN` 2.60 → 2.20 (0.40),
or dropping the 24's separate hour marks altogether — on a 24-LED ring every
second tick already lands on an hour, so they are the one genuinely redundant
thing on that dial, worth 3.20 mm. None was pulled unasked: they are all features
already delivered.

The 32 gets the shorter mark despite being the bigger clock, and that is not an
oversight: its ring's inner edge sits 4.46 mm from the LED centres against the
24's 5.25, so the cell it can carry is narrower and the tick stays centred, so
the tighter side binds. If a genuinely long line is what is wanted, the mechanism
that delivers it is the 60-LED body's perspex light guides at 30 mm.

**`check4`'s `'it sits inside the LED'` assertion was replaced, not deleted.** It
required the tick to fit entirely within the 5 mm emitter, which is the opposite
of what was asked for. It is now a bounded overhang — at most `TICK_SPILL_MAX` =
1.00 mm past the die at each end, because past that the ends are lit by spill
alone and read as a gradient rather than a line. The intent changed on
instruction and the check changed with it, in the open. *(unverified: how a
1.00 mm overhang actually reads is an optical judgement and nothing has been
printed.)*

Crosstalk is stopped by the **cell wall**, not by the aperture: the walls run the
full 2.00 mm depth of the cell, from the face up to the LED PCB, so light from
the next LED never enters this cell at all. The aperture is 1.80 mm deep and
2.00 mm wide, which keeps a tick lit within about ±29° of straight on.

### The hours are written on the diffuser

> *"Write the clock times on the difuser too."*
> *"add the numbers from 1 to 12 on the diffuser that I can print in black on
> the 3D printer. Make them the same font as the Amazon Echo wall clock."*

All twelve, debossed 0.50 mm into the face, in the band just inboard of the lit
ticks — which is where the Echo has them. The plain marks that used to stand in
for the eight non-quarter hours are gone.

| | 24-LED | 32-LED | 60-LED |
|---|---|---|---|
| cap height | 5.00 mm | 6.00 mm | 9.00 mm |
| centre radius | 35.05 | 45.76 | 74.30 |
| clear of the ticks by | 1.20 mm | 1.20 mm | 1.20 mm |

They are **debossed, not thinned** — the Echo's markings are printed on a white
face and the LEDs are what lights up. 1.50 mm of filament is left under a
0.50 mm deboss, so they stay opaque.

**On the font, plainly: it is not Amazon Ember.** Ember is Amazon's proprietary
brand typeface. It is not installable here — matplotlib's font manager raises
`ValueError` when asked for it, which I checked rather than assumed. What is
available is Liberation Sans (Arial metrics), FreeSans (Helvetica metrics) and
DejaVu Sans. Ember is a humanist sans, so of those three **Liberation Sans Bold**
is the closest neutral match, and that is what is cut. It is not the same face
and I am not going to pretend it is. If you have an Ember licence, drop the
`.ttf` anywhere and set `NUM_FONT_FILE` in `params.py` to its path — that is the
only line that changes, and everything re-derives.

Why 5.00 mm on the small clock and not something daintier: at 3.60 mm Liberation
Sans Bold has a **0.66 mm stem**, which is 1.6 beads from a 0.4 mm nozzle — one
perimeter plus a gap-fill, and a visible seam down every stroke in a second
colour. At 5.00 mm the stem is 0.92 mm, two clean beads. `check3` measures this
on the built file rather than trusting the type designer.

### They come out the right way round, and that is not free

The diffuser is modelled with its **visible face at z = 0** and everything else
behind it, so it goes into the base **turned over**. Text laid out the ordinary
way is therefore read from the far side and comes out back to front — "12" would
print as a mirrored 21.

So the numerals are mirrored in the model (`text_prism(..., mirror=True)`), and
the two reflections cancel. Which way is up was not assumed either: **+x is 12
o'clock on the base**, and two independent features say so — the keyhole's entry
hole is at r = 38.5 and its narrow end at r = 46.0 on the +x axis, so the clock
is lifted and dropped onto the screw, which only works if +x is up; and the
ring's lead slot and the USB window are both at −x, which is where a cable
should leave a wall clock.

`check4` tests this without anyone having to squint at a render: it probes the
**"10"**, whose left digit is a 1 and whose right digit is a 0, and only the 0
has a hole in the middle. If the layout were not mirrored those two would swap.

### The LED band is rebuilt, not patched

This is the change with the biggest effect on the file, and it is invisible.

Sam's diffuser carries **183 non-manifold edges**, and every one of them is in
the band r 35.5–46.0, z 0.8–4.0: his two annular ribs are notched at each of the
24 cell-wall angles, and the notches are modelled with faces that do not pair up.
Inside r = 35.0 the mesh is perfect — 0 bad edges, watertight.

Every earlier version unioned new geometry **through** that damage, and it got
worse each time: v5's first attempt came out with 160 bad edges and a 0.128%
disagreement between two ways of measuring its own volume. So the band — which
is exactly the part v5 replaces anyway — is now cut away and rebuilt from
measured numbers:

```
inner rib   r 35.4996 .. 36.6996, z 0 .. 4.000
outer rib   r 44.7995 .. 46.0000, z 0 .. 4.000   (now runs out to the press fit)
24 walls    1.000 mm thick, centres 7.5 + 15k deg to within 0.0003 deg
face        2.00 mm everywhere, ticks cut through it to a 0.20 mm skin
```

Result: **0 bad edges, watertight, one body, volume agreeing to 0.000%** — the
first time this part has been clean. The ribs are continuous now instead of
notched, which is also a better light seal and a stronger press fit.

One thing left alone: the plywood face's ring window is 11.5 mm wide, so you see
about 9 mm of plain white diffuser around the ticks. That is the Echo look.
Narrow the window in `face.svg` if you would rather see less of it.

### The collar reaches 2 mm further in

8.20 → **10.20 mm**, so it lands at base z = **8.80**.

**Read this before printing it.** The seat is at 8.60, so a 10.20 collar clamps a
module rim **0.20 mm** thick. From §1 we know the rim is under 2.20 mm but not
what it is. The exact answer is one caliper measurement:

```
measure the module's rim thickness at the r = 29 mm circle   -> call it t
set  COLLAR_EXTEND = 2.20 - t   in params.py, rebuild, print
```

If you print it as shipped and the diffuser stands proud, that gap **is**
`t − 0.20`: measure it with a ruler, subtract it from `COLLAR_EXTEND`, reprint.
Either way it is one number and a 45-minute print — but the caliper is cheaper.

---

## 2. The ESP32-S3 lives in the housing now

> *"I dont want to use a breakout board for power, move the board more towards
> the edge so that the power can be connected easily. Also, at the current
> moment, the new housing is not deep enough to account for the cables coming
> out of the screen and ESP32. Update the case so that it is at least 50mm deep
> and the ESP32 sits in the other mini rear round clock housing."*

All three of those, and they undo most of v5a. The board is out of the base's
deck bay; the deck is an annular floor again; the beam, the keeper and the
USB-C breakout are gone.

v9 halves the depth again, at his word: *"The housing can be 25mm deep, not
50mm anymore."*

```
housing            25.00 mm deep, 21.50 mm of clear pocket   (was 50.00 / 46.50)
clock overall      49.40 mm  (22.00 base + 2.40 deck + 25.00 housing)
board              63.27 x 28.19 MEASURED, on 4.00 mm posts off the pocket floor
                   x -48.50 .. +14.37; board and frame top out at 7.40
                   (the bay takes 60.0-64.2 long, up to 28.4 wide)
still free         14.10 mm for the display's ribbon and the ring's leads
battery            DOES NOT FIT ANY MORE -- see below
```

**The one thing 25 mm costs you is the battery.** The Anker A1653 is 24.89 mm on
its thinnest axis, and with the board's frame in the way a cell needs a 43.29 mm
housing. Nothing like it goes in a 21.50 mm pocket. So the build is
mains-or-USB-powered now, the two battery shelves are **not generated at all**
(rather than shipped as a part that cannot be used), and the build prints a line
saying so. Put `HOUSING_DEEP` back to 50.00 in `params.py` and everything --
shelves, pocket, checks -- comes back.

That last line is the point of the whole change. The old 15.0 and 27.5 mm
pockets had the board *and* the cables competing for the same space behind the
display; there is now a floor for the board, a shelf for the battery, and 11 mm
of nothing above both of them.

### Its own connector, straight out through the wall

The board sits as far out at 6 o'clock as its own corners allow. At
|y| = 13.15 the pocket wall is at x = −49.27, so the board's end is at
**−48.50** — 0.77 mm of margin at the corners — and its connector looks straight
out through a **22 × 6 mm window** in the rim.

The window is that generous on purpose. **v13 settled which connector the board
carries**, at least for Espressif's own drawing: the shell tabs in the DXF are
7.15 mm apart, which is the standard 16-pin USB-C receptacle footprint, so it is
**two USB-C** — even though the same version's user guide text calls them
Micro-USB. 22 × 6 clears either in either position regardless, and nothing else
in the design depends on knowing.

A plug's overmold ends up about **1 mm outside the rim**, so ~19 mm of it stands
proud and can be gripped. On a wall the lead hangs straight down. On the desk
stand that 19 mm is the number that sets how high the stand holds the clock —
see §5.

**No breakout board, and nothing to buy.** BOM item 11 (Adafruit ADA4090) is
withdrawn.

### What holds the board

**v13 rebuilt this, because v9's mount did not fit.** Sam: *"The mount for the
S3 doesn't fit at all. Update it so it actually fits. Find the correct
dimensions for it."* Both halves of that turned out to matter, but not equally.

#### First: the dimensions

**Sam measured his board: 63.27 × 28.19.** That is **2.79 mm wider** than
Espressif's DevKitC-1 v1.1 outline, so it is not that board — and every vendor
figure for a part sold under that name was already contradicting every other
one (70 × 28, 67 × 31, 55 × 35, all published as fact). `BOARD_L` and `BOARD_W`
are his calipers now. A measurement beats all of them.

Espressif's DXF is still the source for everything calipers cannot reach,
because the retention has to dodge those features and one real drawing of a
board in this family is better evidence than none:

| | | |
|---|---:|---|
| pad rows | 22 a side, 2.54 pitch, **22.86 mm apart** | that is 0.900 in, exactly |
| first / last pad | 7.960 and 61.300 from the connector end | |
| USB shells | two, **9.40 wide**, reaching \|y\| **10.81** | first 8.65 mm of the board |
| WROOM module | ends **55.33** from the connector end | leaving the top face bare after that |
| mounting holes | **none** | the only holes are the connectors' shell tabs |

The shell tabs are 7.15 mm apart, which is the standard 16-pin **USB-C**
receptacle footprint — so that drawing's board carries two USB-C, whatever its
own user-guide text says.

**But nothing in the frame depends on any of it being true of Sam's board.** The
snap lips land in the first 5 mm, before any copper whatever the pitch. The
clamp lands at \|y\| ≤ 9.80, inboard of any row a 0.9 in or wider board could
have. The posts sit at \|y\| = 6.50. Change the pad pitch, move the module,
widen the connectors — none of it reaches these features.

#### Second: why it did not fit, which was not the dimensions

The rails were drawn 0.10 mm a side clear of the board and the end wall 0.30 mm
clear of its end. Both read as clearances. Neither is one:

```
rail slot     25.60 drawn  ->  25.20 .. 25.50 printed   board 25.40  -> INTERFERENCE
end to end    63.04 drawn  ->  62.64 .. 62.94 printed   board 62.87  -> INTERFERENCE

(and the board was 28.19 wide all along, so it was never going to go in)
```

An FDM slot comes off the plate up to 0.40 mm narrower than drawn. A nominal
clearance smaller than that is not a clearance — it is an interference fit
wearing the word. **This is the collar mistake again**, and it gets the collar's
cure: size every clearance off the *worst printed* case, and have `check2`
assert that rather than trusting the drawing.

```
rail slot     28.99 drawn  ->  28.59 .. 28.99 printed   0.40 .. 0.80 clear
end to end    64.77 drawn  ->  64.37 .. 64.77 printed   1.10 .. 1.50 clear
```

#### What stops it now

| | what stops it | |
|---|---|---:|
| sideways | two **rails**, touching only the board's 1.60 mm edge | 0.80–1.20 mm total, deliberately |
| along, +x | an **end wall** — the plug's insertion load goes here | 1.10–1.50 mm |
| along, −x | two **corner stops** against the board's end face | the datum |
| down | three pairs of **posts** at \|y\| = 6.50 | — |
| up, connector end | two **snap fingers** | 0.20 mm |
| up, antenna end | a **screwed clamp bar** | clamped |

The rails no longer pretend to locate the board. They are a guide; 1.20 mm of
sideways slop is fine, because nothing downstream needs better — the USB window
is 22 mm wide for a 9.4 mm connector.

**The snap lips are placed by an absolute \|y\|, not by a reach over the board,
and that is the change that matters.** What limits them is not the board's edge,
it is the USB-C shell 0.29 mm inboard of them. At \|y\| = 11.50 the lip clears
a shell on a board sitting 0.40 mm off centre, and still catches 0.80 mm of
board edge with the board sitting 0.40 mm the other way. Both of those are
asserted.

**The antenna end is screwed down.** Sam: *"add a way to screw it down to
fasten it."* That request solved three problems at once, which is why it got the
whole antenna end rather than being bolted onto what was there.

v9 left the far end unclamped, arguing that a board held at one end cannot lift
at the other. Wrong: the lips have 0.20 mm of slack over a 4.00 mm base, and on
a 63 mm board that is a **15:1 lever and 3.1 mm of lift**. v13 answered it with
a moulded hood and got it wrong twice — first as a 47° wedge whose ramp climbed
*away* from its wall, so its first layer was a 31 mm² island in mid-air; then as
a flat 2.00 mm ledge, which prints, but which cannot be dropped past and which
had to buy its reach out of the end clearance, closing the length window to
±0.5 mm.

**A screwed bar has none of those problems.** It goes on after the board, so
nothing overhangs and there is no assembly move. It is a separate flat part, so
it prints face-down with no support. And it does not care how long the board is
— it only has to land on it, which is why the window reopened to **60.0–64.2**.

`mini-round-clock-board-clamp` — 1 g, and **2 × M3 × 10 self-tappers**:

| | |
|---|---|
| presses | from 59 mm along the board, at \|y\| ≤ 9.80 — **between the pad rows** |
| screws | at 65.25 mm along, **beyond the longest board the bay takes** |
| so | nothing crosses a pad row at any height, either way up, headers or none |
| seat | 5.50, which is 0.10 **below** the board's top face |

That last row is the whole trick. The bar bottoms on the **board**, not on its
own bosses, so tightening it actually clamps — 0.10 mm of flex in a 3 mm PLA bar
is a few newtons, which cannot crack FR4 and takes up any board from 1.50 to
1.70 thick. Its underside is relieved 1.50 mm everywhere short of the pad, so it
cannot come down on the WROOM module however far back that ends.

**It works with or without headers soldered on, pointing either way.** The rails
only ever touch the board's edge; the posts sit at \|y\| = 6.50 with 4.00 mm of
space under the board for tails; the lips land 1–5 mm along the connector end,
before any copper; and the clamp lands between the pad rows and screws down beyond the board's end.

#### Fitting it, and getting it out again

1. Drop the board straight down between the rails, square, connector end first.
2. Press it down. The two fingers cam outward — about 3 N each — and click over
   the connector end's clear strips.
3. Lay the clamp bar over the antenna end, relieved end toward 6 o'clock, and
   run in the two M3 × 10 self-tappers. Snug, not hard: it bottoms on the board
   by design.

To get it out: take the two screws out, lift the bar off, push both fingers
outward — a fingernail or a small screwdriver on each — and lift the connector
end. The lips' retaining faces are horizontal, so nothing lets go on its
own, which is the point.

#### If you are not sure your board is the one in the drawing

Print **`mini-round-clock-board-gauge`** first. It is this exact frame — same
rails, same fingers, same stops, same posts, same clamp bosses — on a 2.5 mm
plate
instead of inside a clock. About **15 g and twenty minutes**. Drop the board in, press it down until
the fingers click, and screw the clamp bar on; if it goes together on that, it
goes together in the housing. the plate carries a 5 mm scale off
the connector end and deeper marks at 60.0 / 63.27 / 64.2, so if it does not,
you can read the length straight off it and `BOARD_L` is the one number to
change.

That is the same answer the collar got after the third "too tight": once a
dimension has come back wrong, stop shipping a better dimension and ship a way
to measure.

### Why the snap fingers are shaped like that

Two constraints, and they happen to agree.

**Mechanically**, a cantilever snap is a strain problem. For a straight beam,

```
e = 1.5 · Y · t / L²        Y  deflection    1.60 mm
                            t  thickness     1.50 mm
                            L  length       20.00 mm
                            ->  e = 0.90 %
```

PLA yields around 1.5–2 % and PETG higher, so that has margin, and L/t is
13.3:1 against the 8:1 floor usually quoted for PLA. The force follows from the
same numbers: `P = b·t²·E·e / 6L` ≈ **3.1 N a finger**, 6.2 N for the pair —
a firm thumb, not a press. `check2` measures `t` on the built STL and does this
arithmetic rather than taking it on trust.

A finger short enough to stand up beside the board would have been hopeless: at
L = 6 mm the same deflection is over 10 % strain, which snaps.

**For printing**, the housing goes on the plate rear-plate-down, so the pocket
opens upward and everything in this frame is a vertical wall. Each finger is a
wall too, with a slot behind it — so its long axis and its bending direction are
**both in the XY plane**, along the layers rather than across them. That matters:
in FDM a part loaded across the layer bonds loses roughly half its elongation at
break, and a snap arm built up the Z axis is the classic way to have one shear
off at a layer line. Nothing here is built that way.

The only overhangs in the whole frame are the two lips, each a 1.60 mm ledge
whose upper face is a 45° lead-in ramp rather than a flat roof — so pressing the
board down wedges the fingers open, and there is nothing to bridge. Nothing
else in the frame overhangs at all now — the clamp is a separate part.

That ramp is also why `check3` learned something in v13. Its thin-wall probe
shoots along the surface **normal**, which is right for a wall and wrong for a
**chamfer**: across a 45° lead-in the normal distance runs to zero at the tip
while every individual layer stays full width. It now measures the largest
circle that fits inside each **layer** of a flagged region before calling it a
defect, and reports both numbers. The lips read 0.21 mm along the normal and
**2.40 mm in every layer that prints them**. The threshold did not move.

## 3. The rear housing

One housing now, not two. It is the electronics box: the S3, the battery if you
want one, the cables, the hanger and the vents.

| | |
|---|---:|
| depth | **25.00 mm** |
| clear pocket | 21.50 mm |
| clock overall | **49.40 mm** |
| screws to the base | 4 × M3 self-tapping, **M3 × 35** |

**Check your screws.** At 50 mm the housing needed M3 × 60; at 25 mm it needs
about **M3 × 35** — the pillar is 25.00 mm plus 8.00 mm into the base's boss.
An M3 × 60 will bottom out and split the boss.

### Wall hanger

A keyhole at 12 o'clock: 9.0 mm entry hole, 4.6 mm slot, 7.5 mm drop. Takes a
screw up to 8 mm across the head on a 4 mm shank. The clock has to be lifted
7.0 mm to come back off it.

The screw head ends up **inside** the compartment once the clock is hung — that
is what carries the load. The battery pocket is therefore offset 7 mm toward
6 o'clock so the battery never sits on it.

Load path is keyhole → 3.5 mm plate → outer wall. The four assembly screws carry
nothing. At a 400 g clock the shank bears on 4.6 × 3.5 mm of PLA, about 0.25 MPa
against a ~50 MPa yield.

An earlier version had stiffening ribs behind the hanger. The fit checker found
that they ate into the battery footprint, and the stress arithmetic says they
were never needed. They are gone.

### Assembly

Four M3 self-tappers at r = 49, at 45/135/225/315° — clear of 12 o'clock (hanger)
and 6 o'clock (cable). They pass through pillars in the housing, counterbored at
the rear so nothing stands proud against the wall, and thread 8 mm into pilot
holes in the base.

- slim housing → **M3 × 30** self-tapping
- battery housing → **M3 × 40** self-tapping

### Which way round the battery goes, and why it is not a free choice

A 77 mm bank in a 102 mm circle leaves about 25 mm split between its two ends,
and the 6 o'clock end is spoken for by the wall:

| | clearance |
|---|---:|
| 6 o'clock end (where the cable enters) | **6.51 mm** |
| 12 o'clock end, on the centreline | 18.51 mm — but the wall screw's head sweeps it |
| 12 o'clock end, at y = 6…18 mm | **15.2 mm** |
| beside the battery, either side | 22.8 mm |
| above the battery | 2.61 mm |

So: **put the battery in with its ports facing 12 o'clock, off the centreline,
and use a slim right-angle USB-C plug.** The mains lead comes in at 6 o'clock,
runs up the side of the battery — 22.8 mm of room there — and plugs in at the
top. `check2_fit.py` asserts all of this.

### Cable exit and vents

A 12 × 7 mm notch through the outer wall at 6 o'clock takes a USB-C plug
(9 × 4.5 mm body clears it with room). 18 vent slots, 2.6 mm, in two groups —
low and high — so the box convects when it is on a wall rather than sitting as a
sealed oven.

---

## 4. Assembly order

1. Print a base, a housing, a diffuser — all from the **same column** of the
   table at the top — and the two battery shelves if you are fitting a cell.
2. Ring and display into the base from the front. Diffuser pressed in after
   them: it goes square, then the eight crush ribs bite.
3. **S3 into the housing**, tilted: slide the +x end under its hook, drop the
   −x end, and it settles onto its four posts with its connector facing the
   window at 6 o'clock.
4. Battery, if you are fitting one: a shelf either side, cell on top of the
   pair — it never rests on the board.
5. Solder the ring and display leads to the board. They come down through the
   deck's openings: the ribbon at 12 o'clock, the ring's leads at 6.
6. Housing on: 4 × M3 × 35 self-tapping.
7. Either hang it — one screw in the wall, 4 mm shank, head no wider than 8 mm
   — or drop it in the desk stand.
8. Plug a USB lead into the window at the bottom of the rim.

---

## 5. The desk stand

> *"build a stand for the clock to go in so that it can sit on a desk too. But
> the stand is another print that the clock sits in."*

A separate print. The clock drops into a cylindrical cradle cut to the body's
own radius plus 0.35 mm, so it contacts along an arc rather than at points,
and leans back 8°.

```
cradle      coaxial with the clock, wrapping +/-55 deg about bottom dead centre
stop wall   inner r 46, behind the clock's rear face -- it cannot slide back
arch        a 45-degree gable through it front to back: halves the filament and
            is the cable route
footprint   108 x 85 mm (24) / 120 x 85 mm (32), stands 59 / 61 mm tall
tips at     22 deg backwards, 29 deg forwards
```

**The one number that is not a style choice is the height.** The clock's USB
socket is at 6 o'clock — exactly where a cradle wants to hold it — and a plug's
overmold stands about 19 mm proud, pointing at the desk, 64 mm back from the
front face where the 8° tilt has already dropped the rim 8.8 mm. So the clock
sits **36 mm off the desk** and there is a slot right through the stand for the
plug and its lead, opening at the back.

If you will use a **right-angle** USB lead, that only needs about 8 mm: set
`STAND_LIFT = 24` and rebuild for a stand 12 mm shorter.

The cradle deliberately misses everything on the clock: it wraps 125–235°, the
vents are at 43–107° and 253–317°, and the wall keyhole is at 12 o'clock. Two of
the four housing screws end up behind the stop wall — recessed, so nothing
binds, but take the clock out of the stand to reach them.

---

## 6. The 32-LED body

> *"make another version for an LED ring of the same brand that has 32 LED's.
> The outside width is 111.85mm and the inside is 96mm"*

**That ring does not fit the clock.** 111.85 mm across against a 107.99 mm body
— it is 3.86 mm too wide, and the pocket it needs reaches r = 56.42 against an
outer wall at 53.99. So the body grows to **119.85 mm**.

Everything inside **r = 46** is Sam's and is kept exactly: the bore, the display
pocket and seat, the display-tab window, his wire slot. Only the outer ring is
replaced — his ring pocket, outer wall and face recess — and `check2` proves that
as a boolean difference, not by eye.

```
ring pocket   r 47.50 .. 56.42, floor still at z = 11.80
LED circle    r 51.96
outer wall    3.50 mm, body r 59.93
face recess   r <= 57.93, still 3 mm deep at z = 19
screws        moved to r 44.00 at 60/120/240/300 deg -- at 49 they would have
              bored straight into the new ring pocket
ring leads    a slot at 6 o'clock from the pocket down to the deck
```

His old ring pocket is filled in to **z = 17.00**, which becomes the shelf the
new diffuser's face lands on. The display tab's slot is cut back out of that
fill, or the tab could not be got in.

**One thing to know before you commit to it.** With the LEDs out at r = 52 and
the 2.1″ display ending at r = 30, there is a **22 mm wide blank annulus**
between the screen and the lit ring. The plywood face covers it, and it is a
different look from the 24-LED version — much more ring, much less screen. Worth
holding the printed face plate up before cutting plywood for it.

---

## 7. The 60-LED clock, 240 mm, with perspex light guides

> *"I have some perspex that can be used to make the LED's look longer than they
> are ... make the clock larger by using the perspex in strips to make the light
> shine down it. I would like to make the clock of the 60LED ring 24cm wide, and
> use the perspex, or other material to make the LED's shine further away from
> the LED"*

A third body: **240 mm across**, for the 60-LED ring, where each LED feeds a
radial strip and **reads 30 mm long instead of about 5**.

```
ring          172 / 156 mm, 60 LEDs, LED circle r = 82.00
body          240 mm.  ring pocket r 77.50 .. 86.50, floor at z = 10.45
guide channel r 79.00 .. 113.60, 6.70 wide, 3.35 deep
the strip     r 86.50 .. 112.00 -- 6.00 x 3.00 x 25.50, resting on a shelf at
              z = 13.65, which is exactly the height of the LED tops
aperture      r 80.00 .. 110.50, thinned to 0.20 mm, widening 1.40 -> 3.00
hours         inboard of the ring, r 70.3 .. 73.7
```

Three things about that layout are decisions, not arbitrary:

- **The channel starts inboard of the LED circle** (r = 79 against LEDs at 82),
  so the LED fires into the space above itself and the aperture starts at r = 80
  — the LED is the head of the lit line, not a separate dot.
- **The strip starts outboard of the ring** (r = 86.5), so it rests on the
  base's shelf and never on an LED.
- **The aperture widens as it goes out**, 1.40 → 3.00 mm. Light falls off along
  a strip; opening the slot pays some of that back so the line looks even rather
  than hot at the inner end.

### The material, against your standing rule

Your rule is *"never PVC or acrylic containing chlorine … cast acrylic or
plywood only, and tell me which and why."*

**Perspex is a brand of PMMA, and PMMA contains no chlorine.** It is safe to cut
and safe to laser. The material that rule is about is **PVC** — sold as "vinyl",
and what unlabelled "acrylic-look" marketplace sheet often turns out to be. That
one releases hydrogen chloride, and it is the one to keep out of the machine.

So: Perspex-branded, or any sheet **labelled** cast or extruded PMMA from a
known supplier, is fine. Unlabelled sheet is not. **Cast** is the better of the
two — extruded crazes and engraves poorly — but for a strip that is sawn and
sanded rather than lasered, either works.

### You cannot cut it on the Aura, and that is already in this project's notes

`enclosure/MATERIALS.md`: the Glowforge Aura is a **~5 W diode laser**, and it
**cannot cut clear, white or translucent acrylic at all** — those materials are
transparent at 445 nm and the beam goes straight through. Glowforge's own Aura
material list is limited to *opaque* acrylic.

So the strips come off something mechanical:

| how | notes |
|---|---|
| **table saw or bandsaw**, fine blade | Rip 6.00 mm strips from 3 mm sheet, then crosscut 60 off at 25.5 mm. Leave the protective film on. Fastest if you have the saw. |
| **scroll saw**, then a sanding jig | Slower, but 60 short pieces is not a big job with a stop block. |
| **6 mm acrylic rod or strip stock** | Skips the ripping. Round rod works too — the channel is 6.70 wide, so a 6 mm round rod drops in and will actually spread light more evenly than a square strip. |
| **a CO₂ laser** at a makerspace | The one laser that does cut clear PMMA. |

**Frost one face.** A polished strip is a *pipe*, not a lamp: light goes in one
end and comes out the other, and the middle stays dark. Wet-sand the face that
sits **downward** (against the base's shelf) with 400 grit until it is evenly
milky. That face scatters light up through the aperture along the whole length,
which is the difference between a lit line and a bright dot at the far end.

### If you would rather not cut anything

`mini-round-clock-light-guides-60` is all 60 strips as one printed part, joined
by a 1.40 mm ring at the outer end. **Print it in clear or natural PETG** —
white PLA is opaque and would do nothing. A printed guide is a worse pipe than
acrylic and a better lamp for exactly the same reason: the layer lines scatter,
so it glows along its length instead of dumping the light out of the end.

And if you fit neither: **the channels still work empty.** They are white
troughs with an opaque face over them and a slot in it, lit from one end. Not as
crisp, but it is not a broken clock — it is the fallback, and it costs nothing
to try first.

### What I cannot tell you without a bench test

**How far the light actually carries.** That depends on the coupling from a
top-emitting 5050 into the end of a strip 4.5 mm away, on how evenly you frost
it, and on the acrylic itself. The geometry is right and the aperture taper is
the knob — `APER_W_IN` and `APER_W_OUT` in `params.py`. If the far end is dim,
widen `APER_W_OUT`; if the inner end is a hot spot, narrow `APER_W_IN`.

Test it before you commit to a 240 mm print: put the ring on the bench, lay one
strip on it, tape a strip of paper over as a mask, and look.

### The size of these prints

A 240 mm clock is a big object and the parts are honest about it.

| part | solid volume | note |
|---|---:|---|
| `base-60` | 514 cm³ | hollow, ribbed, with two shelves. Fits a 256 mm bed with 8 mm to spare |
| `housing-60` | 264 cm³ | |
| `diffuser-60` | 109 cm³ | white PLA, 0.20 mm layers |
| `light-guides-60` | 31 cm³ | clear/natural PETG, if you print them |
| `deskstand-60` | **1047 cm³** | see below |

Those are solid volumes, not filament — at 15% infill the base is around 200 g.
**The 240 mm desk stand is a different matter**: it is over a litre of enclosed
volume and about 10–12 hours even at 8% infill. It exists because it is the same
parametric part, and it checks out, but a 24 cm clock is a wall clock. Print it
only if you actually want one on a desk.

---

## 8. The battery — read this before buying anything

> **v9: no battery fits any more.** Sam took the housing to 25 mm, and a cell
> needs 43.29. The two shelves are no longer generated. Everything below is kept
> because the power arithmetic still decides what supply to use, and because
> putting `HOUSING_DEEP` back to 50.00 in `params.py` brings the whole thing
> back — the pocket, the shelves and the checks all key off that one number.

**A battery this size cannot run this clock. It is a UPS for outages.**

The measured budget, from datasheets rather than estimates:

| Load | typical | worst |
|---|---:|---:|
| ESP32-S3-N16R8 devkit, WiFi up, HA API connected | 60 mA | 140 mA |
| 24-LED WS2812B ring, clock face at ~25% | 33 mA | 145 mA |
| 2.1" 360×360 GC9B72 + backlight | 95 mA | 150 mA |
| **at 5 V** | **188 mA = 0.94 W** | **435 mA = 2.18 W** |

That is **22.6 Wh a day**. A 5,000 mAh bank holds ~18.5 Wh nominal, ~16 Wh after
boost losses — **under 18 hours**. It does not last a day.

### What actually fits, and what to buy

The pocket takes **up to 80 × 38 × 26 mm**, or 78 × 45, or 77 × 50 — the limit is
a rectangle inside the 102 mm interior circle with the hanging screw's swept zone
carved out of the top. `check2_fit.py` prints the full table.

A sweep of Officeworks, JB Hi-Fi, Kogan, Amazon AU, Core Electronics, Zaitronics,
PB Tech, Cygnett, Anker AU, Belkin AU, Bunnings and Scorptec found **one** retail
bank that is both small enough and actually buyable here:

> **Anker Nano Power Bank, model A1653, 5,000 mAh — about A$49 at Scorptec
> (Melbourne).** 76.96 × 36.83 × 24.89 mm (verified, Anker's own spec table),
> so 3.7 mm of spare length in the pocket. Pass-through verified in their
> manual. **~17 hours.**
>
> Two things to settle first: its output is a **fold-out male USB-C plug**, and
> only 15.2 mm is available at the 12 o'clock end; and nobody documents whether
> it restarts by itself after being drained. Both are in `docs/BATTERY.md`,
> with the bench tests. Runner-up if either fails: Baseus Compact Type-C
> Edition 5000, A$45.99 verified in stock — a plain brick, but it lands
> exactly on the pocket's limit.

The shim is cut for exactly those dimensions. Buy something else and you change
two numbers in `params.py` and reprint the shim; the pocket does not move.

The market is otherwise bifurcated and this clock lands in the gap: slim banks
are wide (Cygnett 95 × 65, Anker MagGo 104 × 71), and banks narrow enough for a
108 mm circle are 25–26 mm thick — which is what pushes the clock from 44 mm to
55 mm deep.

### The failure mode that decides it

At 188 mA the clock sits above the ~50–75 mA idle cutoff most banks use, so it
would probably not get switched off in normal running. The one that would bite is
different: **many banks, once flat, will not resume output when mains comes back
until someone presses the button.** On a clock 2.4 m up a wall that means it stays
dead. Anker do not document A1653 either way.

**Test it before it goes in the wall.** Run the bank flat into the clock, leave
the load connected, plug the charger into the bank, and watch. If it comes alive
on its own, you are done. If not, no power bank is usable here at any price —
`docs/BATTERY.md` §4 has the alternative.

### Safety, and the material

A lithium cell sealed in a printed box on a wall in a family home deserves a
plain answer:

- **Print the housing in PETG, not PLA.** PLA softens at 55–60 °C. About 1 W of
  dissipation in a small closed box on a west-facing Victorian wall in summer can
  plausibly put the interior at 50–70 °C. PETG's Tg is ~80 °C. The vents help but
  they do not make PLA the right choice here.
- A **certified sealed power bank is materially safer** than a bare cell on a
  hobby charger board, in one specific way: it ships as a tested assembly with
  protection on the cell and a liability path behind it. A charger IC is not a
  protection circuit — it gives you no over-discharge cutoff and no short-circuit
  protection. If you go the bare-cell route, the cell must be a *protected* one.
- Do not leave the first few charge cycles unattended.
- If the battery is not worth 11 mm of depth and this list of caveats to you,
  print the **slim** housing and run it on mains. The clock is better at 44 mm and
  nothing else changes.

The full working — power budget, every candidate scored, the runtime arithmetic,
the alternative if the Anker fails its test — is in **`docs/BATTERY.md`**.

---

## 9. Printing the numerals in a second colour

> *"I will 3d print the diffuser with the numbers printed in a different colour
> on the same printer."*

That is exactly what these files are for. The numerals are debossed into the
diffuser **and** written out again as their own STL — a set of solids 0.50 mm
thick that fill those pockets exactly. Both come out of one function, so they
cannot drift apart, and both are exported in the same coordinates, so they land
in register with nothing to line up by hand.

**In Bambu Studio (or PrusaSlicer / OrcaSlicer — same idea):**

1. Add `mini-round-clock-diffuser.stl` (or `-32` / `-60`). Leave it where it
   lands — **face down**, which is how it arrives.
2. Right-click it → **Add part → Load…** → `mini-round-clock-numerals.stl`
   (matching suffix). It must be added *as a part of the diffuser object*, not
   as a separate object, or the slicer will move it.
3. Select the numerals part and assign it **filament 2** — black, or whatever
   you want the hours to be.
4. Slice at **0.20 mm layer height**. Nothing else changes.

The pockets are 0.50 mm deep and the inlay is 0.50 mm thick, so the numerals
finish **flush with the face** — 2½ layers of the second colour at the very
bottom of the print, against the plate, where the finish is best.

`check4` proves the fit rather than assuming it: every one of the twelve pockets
is measured against the solid meant to fill it (within 2%), the two parts are
shown never to occupy the same space, and the whole numeral band is shown to
have **no hole left anywhere** once the two are put together.

**If you have no AMS or second extruder**, this cannot be done as a filament
change at a layer: the black and the white are in the *same* layers, not
stacked. Your options are to print the diffuser in one colour and leave the
hours as a plain 0.50 mm deboss (they read perfectly well as a shadow), or to
print the numerals part on its own and glue them in — it is 0.07 cm³ of
filament, and the pockets locate them.

---

## 10. The wire gap between the middle and the ring

> *"update the main clock bases so that there is a gap between the middle and
> the LEd ring so that the cables connecting the LED ring dont need to bend
> straight down. The 24LED looks like this ... UPdate all the sizes for this."*

Sam's own 108 mm base has this and I had not carried it across. Measured on his
upload: at 6 o'clock his base is open **top to bottom** from r = 28 out to
r = 41 — so a lead leaves the ring at ring level, runs inward, and only then
drops. The 32 and 60 bodies had a shallow channel *under* the ring-pocket floor
instead, which means the lead has to be bent flat against the floor first and
then ducked under. That is the bend he is talking about.

Both bigger bodies now have the same gap he does: **±13.00 mm** at 6 o'clock,
from the bore out past the ring's inner edge, open all the way up to the shelf
the diffuser's face lands on. The deck under it is cut to match.

`check2` §8 probes it on all three bodies, as a solid an 8 mm cable bundle would
occupy: it runs inward at ring level from the ring's inner edge to the bore with
nothing in the way, and then straight down to the deck.

While fixing this I found the pocket fill on the 32 and 60 bases was pinned to
`z = 17.00` when the 60's shelf is at 15.65 — a real **1.35 mm collision with
the 60 diffuser's face**, and it left a shelf blocking the new gap at r = 40.
Both now derive from the body's own shelf height.

---

## 11. What is verified and what is not

**Verified here, by running it — 17 parts, three bodies, five passes:**

- Every part is a closed, single-body, self-intersection-free solid, and the two
  volume calculations agree to 0.0000% (`check1`)
- Inside r = 46 nothing of Sam's is removed but the screw pilots and the wire
  gap, and nothing is added but the tab-slot walls and the pocket fill —
  measured as a boolean difference against a named envelope, not eyeballed
  (`check2`)
- Each ring drops into its own pocket with the pocket bracketing it on both
  edges and a real wall outboard (`check2`)
- The board fits the housing, its posts are under it, its hooks are over it, the
  window is bored right through the wall and a plug reaches the board from
  outside (`check2`)
- Base and housing touch only at the mating plane — zero interference volume —
  and the clock is **49.40 mm** deep with 14.10 mm of clear plenum above the
  board's frame for the display ribbon and the ring leads (`check2`)
- The S3 is **held, not just rested on**: located across to 0.20 mm on rails
  that touch only its edge, stopped along by an end wall one way and corner
  stops the other, carried on three pairs of posts, and clamped down by two snap
  lips that land on the 7.15 mm of clear board at the connector end — outboard
  of the USB shells and before the pad rows, so headers make no difference
  (`check2` §5)
- Each snap finger flexes 1.00 mm at **0.69 % strain** — the thickness measured
  on the built STL, not taken from params — on a 12:1 beam, for about 2.7 N a
  finger (`check2` §5)
- No part introduces a sloped overhang below 45°, a flat ceiling spanning more
  than 25 mm, or a wall thinner than 1.2 mm that is not already in Sam's file
  (`check3`)
- A lead can leave each ring at ring level, run inward to the bore, and drop
  to the deck, on all three bodies, with an 8 mm bundle's worth of room
  (`check2` §8)
- The diffuser rests on the base's own annular land at z = 19.03 and, placed
  there, **clears the LED ring by 2.03 mm** on every body — measured as a
  boolean against the ring's own solid, which is the check v8 did not have
  (`check2` §9)
- The press fit is **on the collar and nowhere else**: 0.38 mm of interference
  on diameter over eight 1.00 mm ribs with 3.23 mm of bore engagement, on a wall
  that is clear by **1.58 mm** — four times the interference, so the wall can
  never become the fit itself whatever the printer does. The ribs are tapered at
  the end that meets the bore first and drop back to nominal between them, and
  the outer wall is clear by 0.40 mm all round (`check2` §3, `check4` §5)
- The face fits inside the front recess rather than standing proud, its
  underside is exactly on the land by construction, and the collar reaches the
  screen's face without pushing past it — the three numbers that silently
  drifted before are now asserted (`check2` §9)
- Every cell has a tick, every wall is full height, all twelve hours are
  debossed, the inlay part fills every pocket to within 2% and leaves no hole in
  the numeral band, and the numerals **read the right way round** once the
  diffuser is turned over (`check4`)
- The numeral stems are two nozzle beads wide or more — 0.92 / 1.11 / 1.68 mm
  measured on the built inlays — and only glyph corners fall under a bead
  (`check3`)
- The crush ribs are all there, tapered at the end that goes into the bore
  first, and bevelled on the visible rim (`check4`)
- The clock sits in the stand without interference, lifts straight out over
  40 mm, is stopped from sliding back, and a full-size plug clears the desk by
  7.9 mm with the lead running out the back (`check5`)

**Not verified — these need hands or a purchase:**

- Nothing has been sliced. Print times and masses are from volume.
- **Which USB connector the ESP32-S3 board carries.** Espressif's v1.1 guide
  says Micro-USB; the boards sold as DevKitC-1 have two Type-C. The 22 × 6 mm
  window is sized to make it not matter, but I have not held one.
- The +x hook assumes the last 2.50 mm of that end of the board is bare PCB.
  Derived from the 22-pin row length, not measured.
- The display module's rim thickness at r = 29, which sets `COLLAR_EXTEND`.
- The 32-LED ring itself: 111.85 / 96 mm and 32 LEDs are Sam's numbers, taken as
  given. Nothing about that ring has been checked against a listing.
- Collar-rib interference of **0.38 mm on diameter over eight ribs** is a
  judgement from moulding practice, not a measurement on this printer.
  `COLLAR_RIB_H` and `COLLAR_RIB_N` are the two knobs, and the gauge brackets
  the first one.
- The bore figure of **30.19** is measured on the generated base, so it carries
  whatever your printer does to a 30 mm hole. If the collar will not start, that
  is the number to suspect first.
- **Nothing here has been printed and fitted by me.** The collar fit has now been
  called too tight three times running, which is why v12 ships a gauge instead of
  a fourth guess — 9 g of plastic that measures your printer rather than my
  arithmetic.
- **The display module's rim thickness at r = 29 is still unmeasured**, and it is
  what sets how long the collar should be. v11 assumed a bare 1.60 mm PCB and
  over-reached, so it is thicker than that. `COLLAR_LEN` is back to its old value
  until there is a number.
- **The snap fingers have not been printed and flexed.** The strain and force
  numbers are beam theory with E ≈ 2500 MPa for PLA; the real modulus depends
  on your filament, infill and layer height. If they feel stiff, drop
  `BRD_FING_T` to 1.30; if they feel loose, raise `BRD_FING_OVER`.
- The USB shells' width and reach across the board (7.95 mm, |y| ≤ 10.54) were
  **scaled off** the drawing, not dimensioned on it — so ±2%. The retention is
  0.96 mm clear of them, which is more than that error.
- **The typeface is Liberation Sans Bold, not Amazon Ember.** Ember is Amazon's
  proprietary brand face and is not installable here — checked, not assumed.
  `NUM_FONT_FILE` is the one line to change if you have a licensed .ttf.
- Nothing has been printed in two colours. The register between the pockets and
  the inlay is exact in the geometry; whether your slicer and AMS hold it on the
  plate is a bench question.
- The 95 mA display figure is still the weakest number in the power budget.
- The interior temperature rise is an estimate, and the safety argument in §7
  rests on it. Worth a probe before a cell goes in.
