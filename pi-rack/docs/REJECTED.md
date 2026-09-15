# Rejected, and why

126 ideas were generated across nine domains, then attacked by a second pass whose
only job was to refute them. 31 were cut outright and many more were re-scored down
or re-homed onto hardware that already exists. This file is the record.

It is deliberately the second file in this project, not an appendix. Samuel has said
he would rather be told something is not worth doing than be sold it, and the repos in
this workbench already correct their own earlier recommendations when a measurement
disagrees. Most of the value in a homelab plan is in the things you talk yourself out
of.

---

## The three structural rules that killed the most ideas

### 1. No Pi goes in the bulk data path

**All three independently designed allocations reached this conclusion separately.**

A Pi 4's two USB 3 ports hang off a single VL805 controller on one PCIe 2.0 x1 link,
and its gigabit NIC caps throughput near 118 MB/s regardless. One pass over ~49 TiB
through a single Pi NIC is **over 120 hours**. None of these boards has the ARMv8
crypto extensions, so hashing is CPU-bound on top of that.

So: the machines that already own the disks move the bytes. The workbench pushes its
own repositories. The Synology runs its own backup and sync jobs. What a Pi can
usefully own is the *control plane* — the copy that cannot be deleted, the third party
that checks the work, the thing that notices silence.

This cut: the mini-NAS, MinIO/Garage as an S3 target, the store-and-forward relay,
the cross-drive duplicate crawler, the continuous bit-rot manifest, and the
seed-and-ship cold offsite drive.

### 2. If a NUC, the NAS or the workbench does it better, it does not get a board

There are **two spare Intel NUCs**, an M720q with 16 GB and an unused 233 GB SSD, and
a Synology with NFS and SMB already running. Every one of them is faster and more
reliable than any Pi here. Spending a board on work they should do is not frugal, it
is five extra things that can break.

This re-homed: the restic-to-B2 job (→ workbench, restic has a native Windows
binary), Uptime Kuma and cert monitoring (→ the Agent Deck health-check loop that
already runs on `.42` and already checks `.75`), the second-brain mirror
(→ a per-machine git hook, because a central node structurally *cannot* see a commit
sitting in another machine's working tree), Paperless-ngx, the staging Home Assistant
(→ a second libvirt guest on `.66`, where KVM and autostart are already proven), the
Ansible control node (→ `.42`, which is always on; the workbench gets rebooted
mid-render), and SMART monitoring.

### 3. Nothing goes in the critical path of the house without a fallback

A node that the internet, the lights or a client deliverable depends on needs an
answer to: *what happens when this dies at 2am while Samuel is at a wedding?*

---

## The notable individual noes

### DNS and DHCP on a Pi — rejected by two of the three strategies

The appeal is real: `192.168.1.75` is Home Assistant with 2005 entities on a **DHCP
lease with no reservation**, Samuel's own notes flag it, and it has already caused
pain once. Reservations living in a router's web UI are invisible, unversioned and
lost with the router.

But the fix for that is a reservation, not a Pi. Making one board the resolver for the
whole house converts "an SD card died" into "nobody in the house has internet", and
the mitigation — a second resolver — costs a second board to solve a problem that did
not exist before the first one. Clients treat multiple resolvers as interchangeable,
so a non-filtering secondary makes filtering intermittent; there is no configuration
that gives you both resilience and consistent filtering from one box.

**A `netcore` role exists in this repo and works.** It is kept because the DNS-rewrite
idea is genuinely good — names instead of addresses, so the next migration does not
break twenty configs — and because Samuel may simply want it. It refuses to come up
as a single resolver without an explicit override. It is *not* in the recommended
build.

### A Pi held as a cold spare for Frigate — cut, then partly rescued

Argued for: the Pi 5 at `.70` is the only single-purpose production machine on the LAN
with no redundancy, running six cameras at 80.7% memory.

Argued against, decisively: a board sitting in a rack doing nothing is not a spare,
it is a board you will quietly repurpose in three weeks, and it does not address the
actual failure — the Coral TPU has to be physically moved and the storage rebuilt
regardless. **A shelf, a labelled card and a written procedure are the real spare**,
and they cost nothing. What survives is the procedure, not the allocation.

### `fail2ban` — cut

With `PasswordAuthentication no` there is nothing to brute-force. What remains is a
daemon that can `nftables`-lock you out of a headless board you can only reach over
SSH. The actual threat model here is a compromised device *inside* the `/24` — which
keys-only authentication closes and fail2ban does not.

### `log2ram` — cut, on a factual correction

Raspberry Pi OS trixie already ships
`/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` containing
`Storage=volatile`. The journal is already in RAM; log2ram's headline job is done.
Installing it adds a sync timer and a class of "where did my logs go" bugs for
nothing.

**Worth knowing anyway:** because the journal is volatile, `journalctl -b -1` returns
nothing. You will want the previous boot's log the first time a node wedges, and it
will not be there. On a node that genuinely needs persistent logs, turn it back on
through `raspi-config` → Advanced Options → Logging.

### k3s across the four Pi 4s — cut

A control plane is 512 MB–1 GB, which is most of a 2 GB Pi 4, spent to reschedule five
long-lived services across five machines whose placement you already decided. For one
person with five nodes: Docker Compose per node, driven by Ansible. Revisit if the
node count ever passes about ten.

### PXE / netboot the fleet — cut

Real, documented, and roughly an afternoon of DHCP, TFTP, an rsynced rootfs, a chroot
to regenerate host keys and vendor option 43. The payoff is amortised over five
machines provisioned once or twice. Worse, it would make the Synology a single point
of failure for **every Pi at once**.

Leaving netboot in the `BOOT_ORDER` tail "as a recovery path" is also a bad trade:
`DHCP_TIMEOUT` defaults to 45,000 ms per iteration, so every failed boot adds up to
45 seconds waiting for a PXE server that does not exist.

### A golden image built with `rpi-image-gen` — cut, for now

Genuinely good technology, and it emits an SBOM. But it is the highest-effort item in
the set for a fleet provisioned once, and it creates two places to change a package.
The honest prediction: it gets built, admired, and never rebuilt — at which point
"slow first boot" has been traded for "quietly out of date".

### The Pi 5 RTC battery — cut, with a better free fix

An always-on wired rack node gets NTP within seconds of boot, so the wrong-clock
window is seconds. And the battery only helps the one board that has the connector.
The better answer works on all five and costs nothing:

```bash
sudo systemctl enable systemd-time-wait-sync.service
```

then order time-sensitive units `After=time-sync.target`.

### A rack status display — cut

8 hours, an ESP32, a dedicated supply, a diffuser, a bezel and 2U of a rack that is
already three-quarters empty — to show information the Agent Deck console at `:5080`
and the Home Assistant dashboard already display, in text, on a phone. This is the
textbook set-it-up-look-at-it-twice item.

### Uptime Kuma / Lighthouse monitoring for Dental Story client sites — cut

Dental Story does social media marketing, not web hosting. Monitoring practice
websites Samuel neither built nor hosts nor has credentials for produces alerts he
cannot act on, at 3am, while creating an implied availability responsibility he is not
being paid for.

### An ARM CI runner for resolve-sync and netscan — cut, on a verified fact

`resolve-sync/.github/workflows/build.yml` runs on `windows-latest` and ends in
`build-exe.bat` producing a Windows zip. **PyInstaller does not cross-compile** —
not across OS, not across architecture. An ARM runner cannot build that artefact. For
`kin`, GitHub's hosted runners are free and faster.

### A WordPress staging box for dental-story-theme — cut

`K:\Claude\dental-story-theme` contains four PHP/CSS files and an images folder. That
does not need a staging environment; it needs a local PHP server when it is being
worked on.

### A Resolve PostgreSQL project server on a Pi — cut

This puts the database every paying job depends on onto the least reliable hardware in
the house, behind a network hop. The failure mode is that no project opens on any
machine until a `pg_dump` is restored, on delivery week.

### A camera-card ingest appliance — cut, and the premise was wrong

The stated justification was that the workbench might not have room to ingest a
wedding. It has roughly 27 TB free across `E:`, `H:`, `M:`, `N:` and `O:` — `K:` and
`L:` are full, the machine is not. The problem is filing discipline, not capacity.

On the hardware: a Pi 4 sustains perhaps 60–90 MB/s writing two destinations at once,
so a 256 GB CFexpress card is 45–70 minutes before checksums. A laptop with the same
two SSDs is several times faster with tools that have a decade of field use. And this
is the one item where failure costs a **non-reshootable client deliverable** — the
worst possible place to put a self-built headless appliance with no screen.

Most cameras used for weddings have dual card slots and can record a simultaneous
backup. That is the industry answer to "only one copy exists at the venue", and it
costs the price of cards.

---

## Corrections to facts that were nearly built on

- The workbench volume table sums to about **49 TiB used**, not 40 TB.
- **A2 microSD cards only help the Pi 5.** A2's advantage comes from Command
  Queueing, which needs a CQHCI engine — BCM2712 has one, BCM2711 does not. An A2
  card in a Pi 4 buys nothing and can measurably lose to a plain A1.
- **"High endurance" cards are the wrong tool for a root filesystem.** They carry no
  A-class rating at all and are specified for sequential CCTV recording, not the small
  random I/O an OS does.
- **The official M.2 HAT+ takes 2230 and 2242 only** — a 2280 stick will not screw
  down. Use a 2280-capable third-party base if you want a large drive.
- **The DMX controller already has scene save/load.** `N:\DMX Controller\main.py`
  implements `save_scene`, `load_scene` and `delete_scene` with named scenes persisted
  to disk — so a "capture the wire" recorder role would have duplicated existing work.
- **xLights already does live output.** It sends E1.31 straight to a network
  controller, which *is* bridge mode. A permanent Pi bridge-mode bench rig duplicates
  the sequencer.
