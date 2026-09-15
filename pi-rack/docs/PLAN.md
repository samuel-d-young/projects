# The plan

Five spare boards: 4× Raspberry Pi 4B, 1× Raspberry Pi 5.

**Three deploy. One waits for a two-minute check. One stays in its box on purpose.**

This is the synthesis of three independently designed allocations — one optimised for
reducing loss, one for value to the businesses, one for low operational burden — each
scored by three judges through different lenses. Where they disagreed, the reasoning
is given. What was considered and cut is in [REJECTED.md](REJECTED.md).

---

## Phase 0 — the best hour, and it involves no Raspberry Pi

Every one of the three strategies reached this independently and then buried it under
hostnames. It belongs at the top.

Four actions. About an hour. Roughly thirty cents a month. None of them needs a board,
a card, or the rack to exist — and doing them **deletes the justification for about a
third of everything else that was proposed.**

### 0.1 — Cut the DVR's path out (10 minutes, $0)

`192.168.1.49` runs `uc-httpd 1.0.0` — a XiongMai `NETSurveillance` DVR. That web
server has well-known unauthenticated RCE and directory-traversal flaws, it is a
standard botnet target, and it sits on the flat `/24` alongside the Synology's open
SMB and NFS and the workbench holding 4.8 TB of wedding footage. **(verified that it
is running; the vulnerability class is documented, and deliberately not tested here.)**

On the router: block that device's outbound internet access. It does not need it. This
is a checkbox, and it turns a remotely-exploitable device into a locally-exploitable
one — a very different risk.

Full VLAN segmentation on the Cisco is a better answer and it can come later. **Do not
wait for it.** And before touching VLANs, read the switch model and confirm 802.1Q
support, because one wrong management-VLAN line locks you out of the switch and
everything behind it.

> **Added 2026-08-28 — this DVR is load-bearing, and it changes the VLAN design.**
> Frigate's own `/api/stats` names its six cameras `xmeye_1`…`xmeye_5` plus
> `tapo_outdoor`. **Five of six come from that DVR**, so the camera estate, Alarmo,
> the driveway and the garage all depend on it. It is not a legacy box to unplug —
> if you ever see that advice, including from me, it is wrong.
>
> Blocking its **outbound** internet is unaffected and still correct: that is a WAN
> rule, and Frigate reaches it as same-subnet traffic. But a camera VLAN **cannot be a
> pure dead end** — the Frigate Pi needs a leg in it, or you lose five cameras.

### 0.2 — Reserve the addresses that already bit you (15 minutes, $0)

`192.168.1.75` is Home Assistant — 2005 entities, 44 integrations — **on a DHCP lease
with no reservation.** Samuel's own notes flag this, and the address has already moved
once during the migration.

MAC-reserve `.42`, `.66`, `.70`, `.75` and `.83`. Then confirm the DHCP pool does not
overlap `.100–.130`, which is where every Pi in this plan lands.

### 0.3 — Give the HA VM the RAM it is sitting next to (5 minutes, $0)

The `haos` guest has 4 GB on a 16 GB host. Several proposals across all three
strategies existed only to relieve pressure inside that VM — moving Music Assistant
out, moving Mosquitto out. Most of them evaporate if the guest simply gets 8 GB.

```bash
sudo virsh setmaxmem haos 8G --config && sudo virsh setmem haos 8G --config
```

### 0.4 — One verified offsite copy of the irreplaceable subset (1 hour, ~$0.30/month)

**This is the only item on the list that survives the house burning down.**

There is no automated offsite anywhere in the notes. `restic` has a native Windows
binary; run it from Task Scheduler on `.32` into a Backblaze B2 bucket with **Object
Lock** enabled and an application key that cannot delete.

Provider-enforced Object Lock is a *stronger* guarantee than an `--append-only` flag on
a board sitting in the same house as the thing it protects against. That is the single
best argument against spending the Pi 5 on a local vault, and it is why this is here
and not in the allocation.

> **The blocking prerequisite nobody has done.** Before any of this means anything,
> the *tier-1 set* has to be written down: walk one complete wedding job from cards to
> ingest to delivery and record every path it touches. Delivered films, `.drp` files,
> client asset folders, contracts, invoices, the repos, the brain vault. Commit that
> include-list to git.
>
> If one folder is missed it is backed up nowhere, verified by nothing, and — once the
> archive gate exists — eventually marked safe to delete. That is worse than having
> none of this. **It is not a big list.** It is probably 30–200 GB, against ~49 TiB of
> bulk media. That ratio is the whole point.

---

## Phase 1 — measure, before buying anything

Every allocation below is conditional on facts nobody has read yet. Two of them decide
whether hardware gets bought at all. This is twenty minutes with a screwdriver and an
SSH session.

| # | Question | How | What it changes |
|---|---|---|---|
| 1 | RAM and revision of each of the four spare Pi 4s | `free -h`, `cat /proc/device-tree/model` on each | Which board gets which role. **Watch for Pi 4B rev 1.1** (pre-~Feb 2020): the USB-C CC-resistor fault makes them refuse e-marked cables, and it bites exactly on spare boards of unknown vintage |
| 2 | What the Frigate Pi 5 at `.70` boots from, and its RAM | `ssh .70 'lsblk; free -h'` | Whether the spare Pi 5 is genuine insurance or a labelled board telling a lie. **$15 card vs ~$150 of NVMe** |
| 3 | Is the Pi 4 at `.55` spare, or in service? | Log in and look | It is a live Debian 13 box patched by nobody. Either way it needs an owner |
| 4 | Cisco model at `.254` — 802.1Q? PoE? 19-inch? | Web UI, or SNMP `sysDescr` | Decides VLAN segmentation, whether PoE HATs are even possible, and whether a 10-inch rack is the right format |
| 5 | Synology model, free bays, free capacity | DSM | Whether Active Backup for Business is available, and whether a local second copy has anywhere to go |

**Write the answers into `fleet.toml` and `BUILD-LOG.md`. Buy nothing before then.**

---

## The allocation

Names follow a film-crew theme, because that is the trade this rack mostly serves.

### `gaffer` — Pi 4, smallest board in the draw — `192.168.1.101`

**Roles:** `canary`, `watchdog` · **Boot:** 32 GB A1 microSD, treated as a consumable
· **RAM floor:** ~512 MB · **New hardware:** a heatsink, and optionally a $30 FTDI
USB-to-RJ45 console cable

The gaffer is the one who notices when something has stopped working. This board is
the **highest-consensus item in the entire exercise** — every strategy proposed a
version of it and every judge kept it.

It is also the clearest case of genuinely Pi-shaped work, and the reason is not
performance. It is independence:

- A backup checked by the process that wrote it is not checked.
- A share monitored from the machine that exports it cannot detect the case where the
  export is fine but nothing on the network can reach it.
- An alert that travels through Home Assistant cannot tell you Home Assistant is down.
- Home Assistant is a KVM guest on `.66`, so **nothing inside HA can restart HA**, and
  nothing on `.66` is watching.

What it does:

1. **The canary.** Writes a timestamped file to every SMB share and NFS export,
   reads it back, compares, records latency, every 15 minutes. This catches the
   failure that actually happens on a workbench with three volumes over 98% full: a
   share that has silently gone read-only, a session that died at 3am, a disk that
   filled. A read-only check misses all three.
2. **The watchdog.** Polls `.75:8123`, `.66:22`, `.70:5000`, `.83:5001`. After six
   consecutive failures 30 s apart — three minutes of genuinely down, not one dropped
   packet — it runs exactly one allowlisted command over SSH, rate-limited to one
   action per host per hour, and announces every action taken. It ships **watch-only**;
   promoting a target to acting is a deliberate edit.
3. **A console into the switch**, so that when the network is the thing that broke
   there is still a way in.

Three details that are the actual safety design, not decoration:

- **Soft NFS mounts** (`soft,timeo=50,retrans=2`) in their own unit. A hung kernel NFS
  mount is the one thing that could wedge the exact box the house depends on to notice
  wedged boxes.
- **An outbound heartbeat** to an external service. A monitor's failure mode is
  silence, and a dead watchdog cannot raise its own alarm.
- **The SoC hardware watchdog** (`RuntimeWatchdogSec=15`). For the case software
  cannot catch: this board itself locking up.

**Build it on the board currently at `.55`**, renumbered and reflashed from
`fleet.toml`. That board is a live, unowned Debian 13 Pi that nobody is patching.
Reflashing rather than adopting it in place costs twenty minutes and buys the property
that matters: it becomes wizard-rebuildable instead of a hand-built snowflake.

*Failure story:* it dies, and nothing in the house changes — except that you stop
being told when something else breaks. The external heartbeat is what tells you.

---

### `sparks` — Pi 4, 4 GB or better — `192.168.1.102`

**Roles:** `esphome` · **Boot:** USB SSD strongly preferred · **RAM floor:** 4 GB —
**not negotiable**

The sparks wires the electrics. This board builds ESP32 firmware.

This is not speculative — it unblocks something already recorded as blocked.
`home-assistant/STATUS.md` logs three closed routes to rebuilding the Voice PE
firmware: the Supervisor API rejects long-lived tokens with a 401, the ESPHome Device
Builder add-on is ingress-only so 6052 is not exposed, and building from scratch on
`.66` failed because `python3-venv` needed sudo. The Alexa wake word eventually got
built from a venv on the Windows box.

That works, but firmware only builds when the workbench is on, the ESP-IDF cache lives
on `K:` which has under 50 GB free, and the wall-clock project in progress needs the
same toolchain again.

**The RAM floor is real.** Compiling an ESP32-S3 image with `esp-idf` is the heaviest
thing any node here does — a >1 GB toolchain and a memory-hungry compile. A 2 GB board
will thrash or get OOM-killed part way through, which presents as a mysterious hang.
The role refuses below 3.5 GB rather than let you find that out mid-build.

**And it should not be on an SD card.** A single full build writes several GB. Doing
that repeatedly is how cards die.

*Failure story:* builds fall back to the workbench venv — which is exactly how they are
done today. Capability unchanged, convenience lost. That is the right failure mode for
a convenience node.

---

### `runner` — Pi 4, smallest remaining board — `192.168.1.103`

**Roles:** `eventkit` · **Boot:** 32 GB A1 microSD, rewritten before each event
· **New hardware:** a hard case, a short Cat6 whip, a 5V/3A power bank (~$60)

**This node is not part of the rack.** It lives in the camera bag.

The counter-intuitive argument for it, and the reason all three strategies included
it: it is the **lowest-burden board in the plan precisely because it is switched off
about 360 days a year.** It cannot page anyone at 2am from inside a cupboard.

Samuel does not just attend Indie LAN, BIG LAN X, LANSlide, Gamers Retreat, Redflag
LAN, Garage LAN and BIG LAN 9 — he films them. That makes this the only node that is
simultaneously a hobby item and billable.

Every event has the same four failures, and none of them need a fast Pi:

1. Someone plugs in a home router "just for the switch" and it starts serving DHCP.
2. No internet means no NTP, clocks drift, and Windows and Steam auth fail with an
   error that never mentions the clock.
3. Nobody knows the WiFi password, the schedule, or the server IPs.
4. "The network is slow" — unprovable either way, so it gets blamed for everything.

**The safety interlock matters more than the features.** DHCP ships disabled and is
armed by one deliberate command, which *refuses to run if it can see the home
gateway*. A box that starts handing out addresses the moment it is plugged in is a way
to take down a venue's network — possibly including the venue's own business systems.

---

### `standby` — the Pi 5 — `192.168.1.104` — **gated on question 2**

**Role:** warm spare for the Frigate box at `.70`, plus deferrable work

`.70` is the only single-purpose production machine on this LAN with no redundancy:
Frigate 0.17.2, six cameras, a Coral TPU at 10.55 ms inference, feeding Home
Assistant, Alarmo, the driveway and the garage. And a Pi 4 is **not** a drop-in for it.

The three strategies wanted this board for three different things — an append-only
NVMe vault, a client review host, and nothing at all. Here is how that resolves:

- **Not the vault.** B2 Object Lock is a stronger WORM guarantee than `--append-only`
  on a board in the same house as the threat, and spending this board forfeits the only
  real spare Samuel has.
- **Not a video review host.** **BCM2712 has no hardware H.264 encoder** — the Pi 5
  dropped the block the Pi 4 had. Every review transcode would be software x264 on
  four Cortex-A76 cores, while `.32` has Resolve and two Intel NUCs sit idle. This is
  the single sharpest technical correction the review turned up.
- **A warm spare beats a cold one**, provided its job is genuinely deferrable. The
  archive gate (below) qualifies: its output is advice, and advice can wait a week.

**Everything here hangs on a two-minute command.** SSH to `.70` and run `lsblk` and
`free -h`:

- If `.70` boots from SD and this board matches its RAM → the spare costs a **$15
  card**. Clone, label, shelf.
- If `.70` boots from NVMe, or the RAM does not match → the spare costs an **NVMe base
  plus a stick**, or it is not a spare at all, just a labelled board telling a lie.

Whatever the answer, the spare is only real if it is **tested**: boot it quarterly,
`apt upgrade`, log the date in `BUILD-LOG.md`, and run one timed failover drill a
year. An untested spare is a story you tell yourself.

---

### The fifth board — **stays in its box**

Deliberately not deployed. Labelled, with the wizard's `fleet.toml` entry written and
disabled, so bringing it up is one command rather than an evening of remembering.

This is not laziness, it is the honest answer. A board sitting in a rack "as a spare"
is a board that gets quietly repurposed in three weeks. Five always-on boards is five
things that can break and page a solo operator on a wedding weekend, and the burden
lens is the one that decides plans like this. Three of the three judges, and the
plan that won two of them, all made a version of this call.

Keep it as the physical spare for whichever of `gaffer`, `sparks` or `runner` dies
first. With `fleet.toml` and the wizard, that recovery is about twenty minutes.

---

## Conditional — worth a board, but only if the answer is yes

Neither of these is recommended yet, because each rests on a question only Samuel can
answer. Both have real upside if the answer is yes.

### An FPP show player for xLights — **is there actually a 2026 display?**

FPP (Falcon Player) is the canonical Pi application in that hobby: the show runs
standalone, so it no longer depends on the Windows workbench being awake, unlocked and
not mid-Resolve-render. Given `.32` is the machine Samuel grades on, that is a real
improvement, and xLights season starts in weeks.

**But the evidence on disk is one 10 KB sequence from October 2022 and no models.** If
a display is genuinely being built this year, this is a board, a card and an afternoon.
If not, it stays rejected.

Note a wrinkle the wizard already handles: **FPP ships as its own complete Raspberry Pi
image.** It is not cloud-init seeded, so `piwiz seed` refuses that node by design and
tells you why rather than writing three files the OS would ignore.

### Waiting-room signage for Dental Story — **would a practice pay for it?**

The only genuinely revenue-generating item in the whole exercise. Dental Story already
produces the Reels and the practice content; the marginal cost of putting it on the
screen a patient stares at for fifteen minutes is a ~$150 box, and it converts a
one-off content engagement into a monthly retainer.

**Has any practice been asked?** If the answer is no, that is the next action, not a
purchase. And if it is built, the AHPRA compliance manifest — what is on screen, why
it complies, and when it was reviewed — is part of the deliverable, not an afterthought.

---

## The archive gate — the highest-dollar item, and the last one to build

`K:` has 46.8 GB free of 13,039 GB. `L:` has 151.8 GB. `V:` has 20.1 GB. A volume with
no headroom is a live fuse: one Resolve cache flush and a write fails mid-job.

Nothing gets deleted today because **nothing can prove a finished job is redundantly
archived.** That is the actual blocker, and it is worth 2–4 TB.

The build, if it happens, is correctly Pi-shaped in one specific way: the Pi holds the
SQLite database, the web UI and the scheduler, while the volume walk, the hashing and
the media inspection all run on `.32` against local NTFS. **No Pi goes in the data
path** — one pass over ~49 TiB through a single Pi NIC is over 120 hours.

Two rules that came out of the review and are worth writing down now:

- **A GREEN verdict needs four proofs:** the file exists; its hash matches the ingest
  manifest; at least two distinct on-site volumes hold a copy; and it is present in
  the offsite repo **proven by stored hash**, never by "a file of that name exists in
  the bucket".
- **Never parse the `.drp`.** It is an undocumented compressed blob and `resolve-sync`
  contains no parser — it moves ~18 KB files and lets Resolve relink. Use Resolve
  Studio's documented scripting API instead.

It is last on purpose. It is the only item whose output is advice rather than
protection, and its GREEN verdict is only meaningful once Phase 0.4 exists to be the
fourth proof.

---

## Summary

| Board | Name | Address | Roles | Deploy when |
|---|---|---|---|---|
| Pi 4 (smallest) | `gaffer` | `.101` | canary, watchdog | After Phase 0 |
| Pi 4 (4 GB+) | `sparks` | `.102` | esphome | Any time |
| Pi 4 (smallest) | `runner` | `.103` | eventkit | Before the next LAN |
| Pi 5 | `standby` | `.104` | Frigate warm spare | After question 2 is answered |
| Pi 4 | — | — | — | **Stays boxed** |

Two boards always on. One on when firmware is being built. One warm. One in a box.

If only Phase 0 ever happens, that hour is still the best return in this document.
