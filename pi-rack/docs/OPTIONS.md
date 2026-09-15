# Ten options

You asked for ten things to do with five Raspberry Pis, and specifically to hear what
could be **created** that does not exist yet.

105 concepts were invented across eight lenses, then attacked by a pass whose only job
was to find the product that already does it. **47 were cut** — several because a real
product already does them better, one because published research beat it, one because
Instagram ships 80% of it free. 58 survived; 24 were rated strong. Three curators with
different priorities each picked ten, and two judges reconciled them.

**The honest headline: only three of the ten want a Raspberry Pi.**

That is not a dodge, it is the finding. The money and the bytes live on the workbench,
where the 49 TiB and the GPU are, and every measured fact in this project argues a Pi
out of the data path — 118 MB/s on the NIC, both USB3 ports sharing one VL805, no
ARMv8 crypto extensions, 120+ hours for a single pass over the archive. Where a board
genuinely is the right answer, it is marked. Where it is not, pretending otherwise
would cost you evenings and gain you nothing.

Two of these already run. Their output is quoted, not predicted.

---

## What tonight's survey found before any of this was designed

Four things were verified on your machine. They reorder the list on their own.

**1. resolve-sync is protecting nothing.** `%APPDATA%\ResolveSync\config.json` reads
`auto_sync: true` and `synced_projects: []`. Those are independent settings, so nothing
errors and nothing warns. Three projects were pushed by hand; the config was last
written 29 July. **Nine of your twelve most recently modified projects are in no store
at all**, including `NZ 360 Footage` and `R2W & R2B 20.8`.

**2. The next wedding does not fit.** Twelve real jobs measured under `K:\Weddings`:
median **278 GB**. `K:` has 46.7 GB free, `L:` 151.8, `V:` 20.1 — **219 GB between
them, 0.79 of one job.** `O:` has 10.7 TB, so the machine is not out of disk. It is out
of disk where the work is filed, which is why it stays invisible until a card will not
offload at a venue at midnight.

**3. Ten Resolve projects point at drive `F:`, which is not mounted.** All from
Feb–Jun 2024. Six have a plausible media folder elsewhere; **four have nothing findable
on any mounted drive, and one of those is a wedding (`bREE & eTHAN`).**

**4. `MediaPool:AutoSyncAudio()` exists.** Waveform-correlation multicam sync — what
PluralEyes sells for ~$400 — is one documented call in the Studio API you already own.
That turns option 6 from a DSP project into a scripting job.

---

## The ten

Ordered by *consequence × probability you actually finish it*, not by how interesting
they are to build.

---

### 1. Deadman — make resolve-sync stop lying
**0 Pi · ~3 hours · tonight**

Your own tool reports that syncing is on while its watch list is empty. Three parts:
tick the projects (two minutes); make the agent **structurally unable** to report
PROTECTED while `synced_projects` is empty — a status the UI derives rather than
asserts; then have it say so out loud if it ever happens again.

The third part is also a **product fix for every editor you ship this to**. Anyone can
hit this, and the failure is silent by construction.

> **First evening:** the nine unprotected projects are in a store, and a deliberately
> emptied config makes the status read NOT PROTECTED.
> **Kill criterion:** none for parts one and two — it is a config fix and a bug fix.

---

### 2. Ledger — what is safe to delete, and what exists exactly once
**1 Pi · ~20 hours · [prototype already runs](../prototypes/ledger/)**

One index over Resolve's own project database, the job folders, and which volumes are
mounted — reporting where they *disagree*. Eventually it answers the question that
currently has no answer: *can I delete this finished wedding?*

It has already earned its rank. Run tonight, it found the ten `F:` projects, the four
with no locatable media, **25 of 34 job folders with no matching Resolve project**, and
**260 loose media files** sitting in year folders belonging to no job (145 in `K:\2026`
alone).

The Pi's role is the database, the web UI and the schedule. **The volume walk and the
hashing run on the workbench** — a Pi in the data path is 120+ hours per pass.

> **First evening:** not code. Find out whether `F:` is unplugged, re-lettered or gone,
> and whether `bREE & eTHAN` is on a shelf somewhere. Twenty minutes.
> **Kill criterion:** if the first census shows most of Weddings already has a second
> copy, the delete-authority machinery solves a problem you do not have.

---

### 3. Freeboard — will Saturday's job fit where it belongs?
**0 Pi · ~8 hours · [prototype already runs](../prototypes/freeboard/)**

Not a disk-space alert. Every monitoring tool can tell you a volume is 99% full and you
have learned to ignore all of them. This answers *"will the next job fit in the place it
actually goes?"* — which needs three things a generic alert lacks: what a job costs
(measured, not guessed), which volumes count, and a verdict rather than a percentage.

Its verdict on your machine right now is **WILL NOT FIT**.

> **First evening:** no code at all. Empty `$RECYCLE.BIN` (76.5 GB) and `CacheClip`
> (72.7 GB), open a second job root on `M:` or `H:`, and watch it return WILL FIT for a
> 450 GB job for the first time.
> **Kill criterion:** if that evening gets you past ~560 GB free, stop. Do not build the
> scheduled version yet.

---

### 4. Tithe — the 2% that is genuinely irreplaceable, offsite tonight
**0 Pi · ~12 hours (tier 0 is one evening)**

The reason no offsite backup exists is that 49 TiB makes the problem look unaffordable.
It is not, because **you do not have 49 TiB of irreplaceable data.** Delivered masters,
every `.drp`, the repos, the brain vault, `property-watch`'s unbackfillable SQLite, the
receipts, the client assets — that set is small. Everything else is bulk media with a
different risk profile.

Tier 0 — the text-shaped part — is a few gigabytes and can be in a B2 bucket with
Object Lock before bed, for roughly the price of a coffee a month. Provider-enforced
immutability is stronger than any append-only flag on a box in the same house.

> **Kill criterion:** if the classifier's irreplaceable bin comes out above ~4 TB, the
> rule set is wrong, not the budget. Argue with the rules.

---

### 5. Housebox — your own DMX controller, permanently on
**1 Pi · ~2 hours · the embarrassingly simple one**

`N:\DMX Controller` already ships `pi_install.sh`: it makes the venv, installs
FastAPI/uvicorn, opens UDP 6454 and TCP 8080, and installs a systemd unit with
`Restart=on-failure`. **You wrote it. Deploying it is zero new code.**

And it is better positioned than you may realise — `main.py` exposes plain `GET`
endpoints clearly built for a Stream Deck:

```
/sd/blackout   /sd/full   /sd/preset/{id}   /sd/scene/{name}
```

Scene recall is a URL. So Home Assistant can drive the lighting rig with a one-line
`rest_command`, and a physical GO button is one HTTP call. The lighting stops being a
laptop job forever.

> **Two cautions:** give it a static IP outside any venue DHCP pool, and keep it
> mentally separate from xLights — `xlights_rgbeffects.xml` has **zero models** in it,
> so a Christmas show build is a different, much larger, and currently speculative
> project.

---

### 6. Chorus — come home to a synced multicam timeline
**0 Pi · ~14–30 hours · better on the workbench**

By the time you are home from a wedding, every camera is aligned to the ceremony and a
multicam timeline is waiting.

The reason this is now worth doing: **`MediaPool:AutoSyncAudio([items], {settings})`
with `resolve.AUDIO_SYNC_WAVEFORM` is a documented single call.** The FFT correlation
that looked like the bulk of an 80-hour build is already written, by Blackmagic, in the
Studio edition you own. What remains is import, grouping, timeline assembly and markers.

Realistically 1–2 hours per wedding × ~25 weddings — the largest recurring time saving
in the whole pool.

> **First evening:** import one already-shot wedding into a scratch project, call
> `AutoSyncAudio` in waveform mode, and look at the result.
> **Kill criterion:** if waveform and timecode results disagree by more than ~2 frames
> on more than 10% of clips across two weddings, stop.

---

### 7. On the Record — a publication register for Dental Story
**0 Pi · ~10 hours · the only one with an invoice attached**

A dated, hash-chained register of exactly what was published, for which practice, on
which date — because AHPRA complaints arrive a year later and Instagram lets history be
quietly edited.

**Why this matters more than it looks.** Section 133 of the National Law now carries a
maximum of **AUD $60,000 per offence for an individual** (up from $5,000) and $120,000
for a body corporate, in force in every jurisdiction including WA since July 2024. And
AHPRA's own enforcement strategy applies to *"anyone who advertises a regulated health
service"*, where **"the person or entity who controls part or all of the advertising
(who authorises the content) is considered the advertiser and is responsible."**

You write the copy. Australind Dental is in WA. **That puts Dental Story in scope, not
just the practice.** *(Verified against AHPRA and legal commentary — not legal advice;
confirm with your own adviser.)*

Every existing AHPRA tool audits a live website *after* publication. None keeps a
per-post record of why something passed.

The hook already exists: eight `Posted/` folders across both clients — a convention you
invented, which a register can read for free.

> **Kill criterion, and it is a real one:** show one page of output to a lawyer or your
> insurer **before** it goes near a client or an invoice. A self-maintained register
> could create an expectation you do not want.

---

### 8. Roar — the room writes your edit markers
**0 Pi · ~20 hours · the one that compounds**

Record the room across an event on a standalone recorder, analyse it afterwards on the
workbench, and hand every camera card a Resolve marker file saying where the good bits
were — the cheer, the laugh, the applause.

`AddMarker(frameId, color, name, note, duration, customData)` exists on timelines and
media pool items, and the `customData` field means the tool can tag its own markers and
later delete only its own without touching yours.

It gets better the longer it runs: after twenty events you know things about your own
rooms that nobody else knows.

> **Kill criterion:** measure camera clock drift on one past job *first*. One hour, and
> it decides the whole project.

---

### 9. Customs — does the card actually contain valid files?
**1 Pi · 4 hours to decide, ~40 hours to build**

Every offload tool on the market answers *"did the bytes copy faithfully?"* — Hedge and
ShotPut via checksums, Little Backup Box not even that. **None opens the file to ask
whether the camera wrote a valid one.** That is a real, verified gap.

But do not build the box first. **Build the four-hour script that walks ten years of
footage and counts how many files are actually truncated or malformed.** That single
number decides whether the other thirty-six hours guard a failure that has ever
happened to you.

> **Kill criterion:** if the script finds zero malformed files across ten years, the box
> guards a failure that has never occurred. Stop, and enjoy the four hours.

---

### 10. Kit Wall — the garage knows what is not in the car
**0 Pi (ESP32s) · ~16 hours · the only object with a body**

At 5am on a wedding morning the garage says *"the drone case and one Hollyland mic bag
are still on the shelf"*. At 11pm it says *"the second body never came home."*

The gear-tracking market is checkout ledgers — a human scans a barcode on the way out.
This is sensors: reed switches in printed cradles, so the shelf knows what is on it
without anyone remembering to tell it. You have two printers and an ESPHome fleet, so
the parts cost is trivial.

> **First evening:** two slots, not twelve. One reed switch, one magnet, one ESP32,
> appearing in Home Assistant, and one spoken automation.
> **Kill criterion:** print **one** cradle and test magnet alignment before printing
> twelve. 5 mm tolerance across sixteen printed parts is two or three reprints.

---

## What this means for the five boards

Only three options claim a board, and one of those is co-tenancy:

| Board | Job |
|---|---|
| Pi 4 — `gaffer` | canary + watchdog *(from last session, unchanged)* |
| Pi 4 — `sparks` | ESPHome build server *(unchanged — and Kit Wall needs it)* |
| Pi 4 — `runner` | travelling LAN kit *(unchanged)* + **Housebox** (option 5) |
| Pi 4 — the boxed one | **Ledger** (option 2) — the always-on index and web UI |
| Pi 5 — `standby` | Frigate warm spare, or **Customs** (option 9) if the script justifies it |

The Pi 5 is the only board whose USB3 ports do not share one controller, which is
exactly what a card-in-one-port, SSD-in-the-other copy needs — so if Customs survives
its four-hour test, that is where it goes.

---

## If you only do one thing

**Option 1, tonight, and it takes three hours.** Your backup tool believes it is
running. Nine of your last twelve projects are in no store. Everything else on this list
is an improvement; that one is a fault, and it is in the code you ship to other editors.

## Notable things that were cut

- **A wireless-mic dropout detector** — your Hollyland Lark transmitters are already
  32-bit float onboard recorders explicitly marketed as dropout backups, and the system
  auto-selects the least congested channel. The gear you own already solves it.
- **A gear-bag NFC tracker** — CRDBAG Gear Organizer and ShootPrep already exist, aimed
  at exactly your profession.
- **An LED timecode beacon** — RocSync (arXiv 2511.14948) does it with a better
  encoding than the one proposed.
- **A comment-moderation bot for dental clients** — Instagram's own Hidden Words filter
  and AHPRA's free testimonial tool give you ~80% this afternoon for no code.
- **A stage timer for LAN events** — `cpvalente/ontime` is free, open source and
  self-hostable. Put it on a Pi and spend the afternoon on option 8.
- **A duplicate finder for the 52 GB Dental Story folder** — install Czkawka and delete
  them. Writing a deduplicator is a classic satisfying trap, and automated deletion on a
  99.6%-full volume with no offsite copy is genuinely dangerous.

Full reasoning for all 47 cuts is in the run journal; the structural rules that killed
most of them are in [REJECTED.md](REJECTED.md).
