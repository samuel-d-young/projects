# pi-rack — Build Log

Append-only. Newest entry at the bottom. Every session working on this project adds a
dated entry: what was decided, *why*, and what the next open question is. If you are
picking this up cold, read the last entry first, then `docs/`.

Provenance follows the second-brain convention: facts are tagged **(verified)** — a
primary source was read or a command was run — or **(assumed)** — plausible but
unconfirmed. Never build on an assumed fact as if it were confirmed.

---

## 2026-08-28 — Project opened

Goal, in Samuel's words: set up the remaining Raspberry Pis and put them to use in a
server rack. Four Pi 4Bs and one Pi 5, currently spare. Deliverables: a plan, as many
grounded suggestions as possible, a go-live sequence, and a wizard that builds the
cards.

### Environment surveyed rather than assumed

Nothing here was taken from the existing notes without re-checking it. What the survey
found is in [docs/GROUND-TRUTH.md](docs/GROUND-TRUTH.md). The four findings that
changed the shape of the project:

**1. The first-boot mechanism is cloud-init, not `custom.toml`. (verified)**

The official image index declares `init_format: "cloudinit-rpi"`. The
`2026-06-18-raspios-trixie-arm64-lite` image was downloaded, its SHA-256 confirmed
against the published `extract_sha256`, its MBR parsed and both partitions opened.
The FAT32 `bootfs` partition contains `user-data`, `network-config` and `meta-data`;
the root filesystem contains a fully installed cloud-init whose
`/etc/cloud/cloud.cfg.d/99_raspberry-pi.cfg` reads
`datasource_list: [ NoCloud, None ]` with `seedfrom: file:///boot/firmware`.

This matters because essentially all current tutorials describe the Bookworm-era
`custom.toml`. A wizard built on that guidance writes a file the OS ignores and
produces a Pi with no user, no key and no network — a node you have to physically
retrieve. Finding this before writing the wizard rather than after is the single
highest-value thing this session did.

**2. Eight of the nine data drives report bus type USB. (verified)**

`Get-Disk` on the workbench shows the QNAP enclosures as USB. So the obvious safety
rule for an SD-card writer — *offer only removable disks* — would have offered the
12.7 TB `K:` volume holding 4.8 TB of wedding footage as a valid write target. The
gate therefore refuses on four independent grounds and a test asserts specifically
that the bus check alone would have failed.

**3. `K:` has 46.8 GB free of 13,039 GB, and `L:` and `V:` are the same story.
(verified)**

`K:` holds `K:\Claude` — every repo, the brain vault, property-watch's SQLite. A
volume at 99.6% is a live fuse. `$RECYCLE.BIN` (76.5 GB) and `CacheClip` (72.7 GB)
are about 150 GB of ten-minute wins, three times the current free space. Consequence
for the wizard: OS images are never cached on `K:`; `images.default_cache_dir()`
picks the fixed drive with the most free space and refuses anything under 20 GB.

**4. There is a device on the LAN running `uc-httpd 1.0.0`. (verified that it is
running)**

`192.168.1.49` serves a XiongMai `NETSurveillance WEB` interface. That web server has
well-known unauthenticated RCE and directory-traversal flaws and is a standard botnet
target. It sits on the flat `/24` alongside the Synology's open SMB and NFS and the
workbench. Not tested, and not going to be — the fix is containment, not proof.

### Also found, and worth writing down

- A **Synology NAS** (`VultronNAS`, `.83`) with **NFS already enabled** on 2049.
  Nothing in the existing notes mentioned it. It changes several answers.
- A **Cisco small-business managed switch** at `.254`. VLANs are available today.
  Whether it is a PoE model is **unconfirmed** and is the one hardware fact that most
  changes the rack build.
- The **Pi 5 at `.70` is in production** running Frigate with a Coral TPU, six
  cameras, `skipped_fps: 0.0` and 80.7% memory. It is not one of the five.
- The **Pi 4 at `.55`** is idle: Debian 13 trixie, only 22 and 111 open.
- **Raspberry Pi Imager is not installed** on the workbench. Python 3.13.6, PyYAML,
  OpenSSH, git and 7-Zip all are.

### Decision: `seed` must not require Administrator

Because Imager is absent and the native writer needs elevation, the wizard is split so
that the step which actually turns a generic card into *this node* — three text files
on a FAT32 partition — needs no privileges at all. Write the card any way you like,
including the Imager GUI, then `pi-wizard seed <node>`. This is the fallback that
always works, and it is deliberately the simplest part of the system.

### Built and verified this session

- `wizard/piwiz/disks.py` — the safety gate. Verified against all eleven real disks:
  every one correctly refused.
- `wizard/piwiz/bootcfg.py` — renders the three cloud-init seed files. Output is
  parse-checked with PyYAML before it is written.
- `wizard/piwiz/fleet.py` — `fleet.toml` as the source of truth, validating hostnames,
  addresses against the live LAN scan, ports against what is already bound, and
  `boot=nvme` against whether the board is a Pi 5.
- `wizard/piwiz/roles.py`, `images.py`, `writer.py`, `__main__.py` — role catalogue,
  verified image fetch, three write paths, eleven CLI commands.
- `bootstrap/lib/common.sh` — idempotent helpers with a `once` guard that only marks
  a step done *after* it succeeds.
- 33 disk-safety tests and 50 seed/role tests, both runnable standalone. All pass.

### Corrections applied after adversarial review

Research agents verified the wizard's assumptions against `rpi-imager`'s own source
and the official Raspberry Pi documentation, and found four real defects in what had
been written:

1. **Invented CLI flags.** The Imager invocation used `--cli --disable-telemetry`.
   The real flags at v2.0.11.1 are `--disable-verify`, `--sha256`, `--cache-file`,
   `--first-run-script`, `--cloudinit-userdata`, `--cloudinit-networkconfig`,
   `--disable-eject`, `--enable-writing-system-drives`, plus positional src/dst.
2. **Wrong install path.** The 64-bit installer targets
   `C:\Program Files\Raspberry Pi\Imager\`, and ships a separate `rpi-imager-cli.cmd`
   wrapper whose body is `start /WAIT rpi-imager.exe --cli %*`. The bare `.exe` is a
   GUI binary that does not wait — calling it directly means "finishing" the write
   before it starts.
3. **The stale-instance-id trap.** Imager appends ` ds=nocloud;i=<its id>` to
   `cmdline.txt`. A cmdline instance id **overrides** `meta-data`, so re-seeding a
   card that Imager wrote would silently *not* re-provision. `reconcile_cmdline()`
   now rewrites it, preserving the single-line rule the bootloader depends on.
4. **unattended-upgrades that upgrades nothing.** A Debian-security-only
   `Origins-Pattern` matches almost nothing on Raspberry Pi OS, and naming
   `Automatic-Reboot-Time` without `Automatic-Reboot "true"` means the node never
   reboots into a new kernel. Both fixed.

Also settled, and deliberately *not* built: no `fail2ban` (with password auth off
there is nothing to brute-force, and it can firewall you out of a headless board);
no `log2ram` (trixie already ships `Storage=volatile`, so the journal is in RAM
already — with the operational surprise that `journalctl -b -1` returns nothing);
no k3s (a control plane is most of a 2 GB Pi 4, to schedule five services whose
placement you already know).

### Next

Three independently designed allocations of the five boards are being scored. The
thing all three already agree on, and which is the most important sentence in this
log: **the highest-value work in the whole project involves no Raspberry Pi at all.**
Containing the DVR is minutes on the router. Getting one verified offsite copy of the
irreplaceable subset is a scheduled task on the workbench and a few dollars a month.
Both should happen before a single board is racked, precisely because a rack is more
fun than either.

---

## 2026-08-28 (overnight) — plan settled, wizard built and verified end to end

### The allocation

Three independently designed allocations were scored by three judges through
different lenses. Two judges picked the minimalist plan and both said it
under-deploys; the third picked the value-first plan. The synthesis is in
[docs/PLAN.md](docs/PLAN.md). Summary:

| Board | Name | Address | Roles | Status |
|---|---|---|---|---|
| Pi 4 (smallest) | `gaffer` | `.101` | canary, watchdog | deploy |
| Pi 4 (4 GB+) | `sparks` | `.102` | esphome | deploy |
| Pi 4 (smallest) | `runner` | `.103` | eventkit | deploy |
| Pi 5 | `standby` | `.104` | warm-spare | **gated** on measuring `.70` |
| Pi 4 | — | — | — | **stays boxed, on purpose** |

**The finding that outranks the allocation**, and which all three strategies reached
independently before burying it: the four highest-value actions available need zero
Raspberry Pis. Cut the DVR's outbound path, reserve the addresses that have already
moved once, give the HA guest the RAM it is sitting next to, and put one verified
offsite copy of the irreplaceable subset in B2 with Object Lock. About an hour, about
thirty cents a month. That is Phase 0 of the runbook, and it deletes the justification
for roughly a third of everything else that was proposed.

### Decisions taken, and the reasoning

- **The Pi 5 is not a video review host.** BCM2712 has **no hardware H.264 encoder** —
  the Pi 5 dropped the block the Pi 4 had. Every transcode would be software x264 on
  four A76 cores while `.32` has Resolve and two Intel NUCs sit idle. This was the
  sharpest single correction of the whole review.
- **The Pi 5 is not the backup vault either.** Provider-enforced Object Lock on a B2
  bucket is a stronger WORM guarantee than `--append-only` on a board sitting in the
  same house as the threat — and spending it forfeits the only real spare.
- **No Pi goes in the bulk data path.** One pass over ~49 TiB through a single Pi NIC
  is over 120 hours. The machines that own the disks move the bytes; the Pi owns the
  control plane.
- **Deploying four boards, not five.** A board sitting in a rack "as a spare" is a
  board that gets repurposed in three weeks. Five always-on boards is five things that
  can page a solo operator on a wedding weekend.
- **`netcore` (DNS/DHCP on a Pi) is built but not recommended.** Two of three
  strategies rejected it: it converts "an SD card died" into "nobody has internet".
  Kept because the DNS-rewrite idea is good and the choice is Samuel's; it refuses to
  come up as a single resolver without an explicit override.

### The wizard, and one real bug found by testing it

`piwiz` is eleven commands over six modules, with 33 disk-safety tests and 54
seed/role tests, all standalone. Verified end to end against the real role scripts and
a simulated boot partition: seed files render, parse as YAML, and **both role scripts
round-trip byte-for-byte identical** through block-scalar encoding (11,758 and 11,032
bytes).

**The bug:** every `bootstrap.sh` sources `/opt/pi-rack/common.sh` on its third line,
and nothing was writing it. Every first boot would have failed on every role, with a
"No such file or directory" buried in cloud-init's output. Found by reading the
generated `write_files` list rather than by trusting that it looked right. Fixed, plus
tests asserting the library is bundled, ordered ahead of the scripts that source it,
and refused if it ever acquires CRLF.

### Left for Samuel

1. **Phase 0.** One evening, no hardware. It is worth more than everything below it.
2. **Phase 1 — measure.** Five questions in `docs/PLAN.md`. Two of them decide whether
   hardware gets bought at all. In particular: `ssh 192.168.1.70 'lsblk; free -h'`
   decides whether the Pi 5 spare costs $15 or $150.
3. **Write down the tier-1 set.** Walk one complete wedding job and record every path
   it touches. Everything downstream operates on that list, and it does not exist yet.
4. `pi-wizard keygen`, then `pi-wizard doctor`, then flash `gaffer`.

### Two honest gaps

- **Three research agents died on a session limit** before independently
  re-verifying the imaging, first-boot and SSD-boot mechanics. That material is
  covered by the provisioning pass that did complete and by direct measurement here,
  but it has had **one** verification pass rather than two. `docs/PROVISIONING.md`
  says so at the top; treat the EEPROM and NVMe sections as good but unrepeated.
- **Nothing has been booted on real hardware.** Every claim about what happens on
  first boot is derived from the image's own configuration, read out of the image.
  It is not yet **(verified)** on a running Pi, and it will not be until the first
  card goes in.

---

## 2026-08-28 (later) — a wider survey, and one piece of yesterday's advice was wrong

Samuel asked for more options, and specifically for things that could be *created* that
do not exist. Before generating any, I re-surveyed — and the second look changed several
facts. Full detail in [docs/GROUND-TRUTH.md](docs/GROUND-TRUTH.md) §6.

### The correction that matters

**The XiongMai DVR at `.49` is load-bearing, not legacy.** Frigate's own
`/api/stats` names its six cameras: `xmeye_1` through `xmeye_5`, plus `tapo_outdoor`.
**Five of six come from that DVR.** So the camera estate, Alarmo, the driveway and the
garage all depend on it.

Yesterday's docs carried a research suggestion that "if legacy, the correct answer is to
unplug it". That is **wrong** and is now struck. What survives unchanged is the actual
recommendation — block its **outbound internet** on the router — which does not touch
same-subnet reachability from `.70`. And it adds a constraint to any future VLAN work:
the camera VLAN cannot be a pure dead end, because the Frigate Pi needs a leg in it.

Also corrected: **`tapo_outdoor` works again** (5.1 fps, `skipped_fps 0.0`), where the
`home-assistant` repo still records it as dead.

### Why I missed this the first time

The first scan tested **a fixed list of ports I had guessed at**. That is the whole
reason it concluded the NUC was running "only" Agent Deck and the Wyoming services.
A wider list immediately found **Immich 3.0.3 on `192.168.1.42:2283`**. A port scan only
ever tells you about the ports you asked about — worth remembering next time.

### What else the wider survey found

- **The Synology is doing real work.** Five shares, with the owner's own comments:
  `frigate` ("served to the Frigate Pi 5 over NFS"), `photos` ("Immich photo library,
  served to the NUC over NFS"), plus `docker`, `home`, `homes`. `photos` is mapped on
  the workbench as `Z:` and holds `Footage`, `HASS Backups` and `immich-library`.
  **`Z:` has 4,257 GB free** — the only real headroom on this network — and Home
  Assistant backups already land there, which closes a gap flagged yesterday.
- **Resolve's own index is readable and rich**: 129 projects, 1,946 timelines, dates,
  resolutions and gallery paths, all without Resolve running. A separate `Dental Story`
  database holds 3 projects, all 1080×1920, one with **24 timelines**.
- **Ten of those 129 projects point at drive `F:`, which is not mounted.** All modified
  between February and June 2024, including two weddings and paid commercial work.
  That is not a hypothetical archiving risk — it is the failure already having happened,
  to client work, unnoticed for two years. It is now the strongest single argument in
  this project for a job ledger.
- **`K:\Weddings` has gear-test dumps in it** (`RODE MIC 1`, `Rode Mic Dump Feb.3.24`),
  a finished job folder holds only delivered MP4s with no link to its source, and the
  year folders are camera-card dumping grounds — `K:\2026` mixes named events with loose
  `C5151.MP4` files belonging to no job.
- **`N:\DMX Controller` already ships `pi_install.sh`** — a venv, systemd unit and
  firewall rules for a Pi 4. Putting his own Art-Net controller on a Pi needs zero new
  code.
- **xLights is barely started**: one controller defined at `192.168.1.61` (which does not
  answer), and `xlights_rgbeffects.xml` is 5.7 KB with **zero models**. Any large show
  build is speculative and should be marked as such.
- Toolchain correction: `ffmpeg`, `ffprobe`, `node` and `npm` **are** installed;
  `rclone`, `restic`, `exiftool` and Docker are not.

### Next

Eight invention lenses are running, each required to search before claiming novelty, and
each vetted by a pass whose only job is to find the product that already does it. The
output is ten distinct options for the five boards.

---

## 2026-08-29 (overnight) — ten options, and four faults found before designing any of them

Samuel asked for ten options for the five boards, weighted to things that could be
*created* that do not exist. Result in [docs/OPTIONS.md](docs/OPTIONS.md).

**105 concepts across eight lenses, 47 cut, 58 survived, 24 rated strong.** Three
curators with different priorities each picked ten; two judges reconciled them. Every
invention lens was required to search before claiming novelty, and the vetting pass was
told its job was to find the product that already does it.

### The four faults, all verified before any option was designed

1. **resolve-sync is protecting nothing.** `auto_sync: true`, `synced_projects: []`.
   Independent settings, so nothing errors. Nine of the twelve most recently modified
   projects are in no store. This is now option 1, and it is three hours.
2. **The next wedding does not fit.** Median job 278 GB (measured across 12 real jobs);
   `K:`+`L:`+`V:` have 219 GB free between them.
3. **Four of the ten `F:` projects have no locatable media**, one of them a wedding —
   refined down from "ten are lost", which would have been wrong.
4. **`MediaPool:AutoSyncAudio()` is a documented single call.** Automatic multicam sync
   is a scripting job, not a DSP project.

### Two prototypes, both running

- `prototypes/ledger/` — reconciles Resolve's project index against the job folders and
  the mounted volumes. Found faults 1 and 3, plus 25 of 34 job folders with no matching
  project and 260 loose media files belonging to no job.
- `prototypes/freeboard/` — answers "will the next job fit where it belongs". Current
  verdict on the real machine: **WILL NOT FIT**.

A bug worth recording: `Path("K:")` on Windows is **drive-relative** — it means "the
current directory on K:", not the root. `Path("K:") / "2026"` yields `K:2026` and
silently matches nothing, which is why the first run reported no loose media at all.
`Path("K:/")` is correct.

### The finding that shapes the answer

**Seven of the ten options need no Raspberry Pi.** Stated plainly rather than dressed
up: the money and the bytes are on the workbench, and every measured fact argues a Pi
out of the data path — 118 MB/s NIC, both USB3 ports on one VL805, no ARMv8 crypto
extensions, 120+ hours per pass over 49 TiB. The list claims exactly one new board
(Ledger, on the boxed spare) and one co-tenancy (Housebox alongside the LAN kit).

**Housebox is the standout Pi answer precisely because it is boring**: `N:\DMX
Controller` already ships `pi_install.sh` and a systemd unit, and exposes plain GET
endpoints (`/sd/scene/{name}`) built for a Stream Deck. Deploying it is zero new code,
and it makes Home Assistant able to drive the lighting rig with one `rest_command`.

### Notable cuts

The wireless-mic dropout detector died because the Hollyland Lark transmitters are
already 32-bit float onboard recorders sold as dropout backups. The gear-bag tracker
died because CRDBAG and ShootPrep already exist for exactly this profession. The LED
timecode beacon died to published research (RocSync, arXiv 2511.14948). The dental
comment-moderation bot died because Instagram's Hidden Words gives ~80% of it free.

### Left for Samuel

1. **Option 1 tonight.** Three hours, and two of them are a bug fix in his own shipped
   product.
2. Twenty minutes finding out what `F:` was, and whether `bREE & eTHAN` still exists.
3. Empty `$RECYCLE.BIN` and `CacheClip` — about 150 GB, three times the current free
   space on `K:`.

---

## 2026-08-29 — the survey, and a correction to my own plan

Samuel asked what Raspberry Pis actually get used for, including what the internet
recommends. Ten categories researched against the live web, **183 distinct uses**
catalogued and annotated against his stack, then two synthesis passes with opposite
instincts. Result in [docs/SURVEY.md](docs/SURVEY.md).

Fit breakdown: 59 good-fit, 45 plausible, 34 poor-fit, 21 redundant with his stack,
**19 actively a bad idea**, 5 already running.

### Four gaps that both my earlier plan and his stack missed

The most useful output, because they are absent from everything written so far:

1. **No remote access anywhere** — no VPN, no tunnel, no overlay. Tailscale, on the
   NUC, minutes. (Tailscale's April 2026 pricing removed the 100-device cap on the free
   personal plan.)
2. **No password manager**, and he holds Meta and Google Business logins for multiple
   dental clients. Vaultwarden — a legitimate Pi job, precisely because it should not
   live alongside everything else.
3. **No hardware security keys.** Best value-per-minute in the survey and not a Pi.
4. **No out-of-band console** for `.66`, the headless hypervisor running the HA VM.
   PiKVM, or just buy a JetKVM.

### The currency corrections are the real prize

Every one of these still ranks well in search and reads as current:

- **PiVPN** archived 2024-11-02 — every "Pi as a VPN" tutorial predates its death.
- **wyoming-satellite** archived read-only **2026-01-27**, replaced by Linux Voice
  Assistant. Relevant to him directly: he has Voice PE satellites.
- **Gravity Sync** archived and structurally incompatible with Pi-hole v6's API.
- **MinIO** archived 2026-04-25; **File Browser** archived 2026-09-01 (36k stars, no
  further security fixes); **room-assistant** last release March 2022;
  **motionEyeOS** last OS release 2020; **Shinobi** frozen ~6 years.
- **Promtail** EOL 2026-03-02 → Grafana Alloy. **Drone CI** → Harness; OSS is Woodpecker.
- **NOAA APT satellites are all decommissioned** (NOAA-18 6 Jun, NOAA-19 13 Aug,
  NOAA-15 19 Aug 2025). Half of every "SDR projects" list is now instructions for
  receiving silence.
- **`RPi.GPIO` is dead on the Pi 5** — GPIO moved behind the RP1 southbridge, so
  `/dev/mem` cannot reach it. Any `import RPi.GPIO` tutorial fails.
- **RetroPie**'s last tagged release is 4.8, March 2020, with no official Pi 5 image.

### Verified myself rather than taken on trust

**Google archived the entire Coral toolchain** — `pycoral` on **3 July 2025** and
`libedgetpu` on **14 October 2025**, both confirmed by fetching the repositories
directly. Frigate no longer recommends Coral for new installs and points builders at
Hailo instead.

**But this is not a reason to replace his Coral**, and the survey caught me being too
enthusiastic about that earlier in the day. His does 11.5 ms across six cameras with
`skipped_fps: 0.0`; the Hailo-8L benches ~10–13 ms — a lateral move at higher cost, and
several users report Coral is *better* at night under IR. Archived is not broken. The
archive matters for the **next** build; the AI HAT+ is the succession path if the Coral
dies or the camera count grows.

### The correction to my own plan

The survey rates the **ESPHome build server on `sparks` as actively a bad idea**, and
on the facts it is right — though the two arguments are about different things. My
reason was *reachability* (the Device Builder add-on is ingress-only, 6052 closed,
which is why the wake-word rebuild happened in a venv on Windows) and that still
stands. The survey's reason is *speed*: that add-on already runs in the HA VM on an
i5-8400T with 16 GB, and a Pi 4 takes ~27 minutes for a single ESP32 build.

**The problem was real; the fix was wrong.** Better: expose the existing add-on, or run
the ESPHome CLI on the NUC. A prominent correction block is now in `fleet.toml` above
that node — left enabled rather than silently disabled, because it is Samuel's call.

### The framing worth keeping

Both syntheses reached the same headline independently: *almost everything the internet
tells you to put on a Pi, he already runs better on the NUC, the Synology or the HA VM.
The Pi jobs that survive need a **separate** box (DNS, credentials, out-of-band access)
or a box in a **different building** (offsite backup).*

And the power argument is weaker than folklore suggests: a Pi 5 idles ~3 W against
~6–8 W for an N100 mini PC — about **$10 a year**. Since he owns both the boards and
two spare NUCs, "cheaper to run" is not a real reason to pick a Pi. GPIO, HATs, camera
modules and physical separation are.
