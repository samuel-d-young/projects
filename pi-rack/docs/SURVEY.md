# What Raspberry Pis actually get used for — a 2026 survey

Ten categories researched against the live web, 183 distinct uses catalogued, each one
annotated against what you already run. Then two synthesis passes with opposite
instincts — one cataloguing, one sceptical.

**The headline, and both syntheses reached it independently:**

> Almost everything the internet tells you to put on a Raspberry Pi, you already run
> better on the NUC, the Synology, or the Home Assistant VM. The Pi jobs that survive
> are the ones that need a **separate** box (out-of-band access, DNS, a credential
> vault) or a box in a **different building** (offsite backup).

The fit breakdown across all 183:

| | Count |
|---|---|
| Good fit for you | 59 |
| Plausible | 45 |
| Poor fit | 34 |
| Redundant with your stack | 21 |
| **Actively a bad idea for you** | **19** |
| Already running | 5 |

One reframing worth having up front: **the Pi's power advantage over a mini PC is about
$10 a year**, not an order of magnitude — a Pi 5 idles ~3 W, an N100 mini PC ~6–8 W.
Since you already own the boards *and* two spare NUCs, "Pis are cheaper to run" is not
a real argument. The real arguments are GPIO, HATs, camera modules, and physical
separation.

---

## 1. The four genuine gaps

These are absent from your stack **and** from the plan I wrote you last week. That
makes them the most useful output of this survey.

### Remote access — there is none
The scan found no VPN, no tunnel, no overlay network anywhere. You are a wedding
videographer away from the house for entire days, and everything worth reaching is
LAN-only.

**Tailscale**, installed on the NUC and the workbench, not on a Pi. Minutes.
Tailscale's pricing v4 (8 April 2026) made the free Personal plan substantially better
for this: 6 users, **the 100-device cap removed entirely**, unlimited user-owned
devices.

Note **PiVPN is archived** (2 November 2024) — every "turn your Pi into a VPN server"
tutorial predates its death. If you want self-hosted WireGuard instead, `wg-easy` is
what people moved to.

### No password manager, and you hold client credentials
You carry Meta Business Suite and Google Business logins for multiple dental practices.
That is a real liability, and it is the one service that should **not** live on the NUC
or the NAS alongside everything else.

**Vaultwarden** — 66.4k stars, Rust, ~100 MB. This is a legitimate Pi job: small,
security-sensitive, and better on its own box.

### No hardware security keys
**Best value-per-minute in the entire survey**, and not a Pi at all. Two FIDO2 keys
(one primary, one in a drawer). One compromised Meta Business Suite login is a very bad
week across several clients. Twenty minutes, then never maintained again.

### No out-of-band console
`.66` is a headless hypervisor running the HA VM that 2005 entities, Alarmo and both
Voice satellites depend on. If it fails to POST, or a network config goes wrong,
recovery today means carrying a monitor to it.

**PiKVM** (V3 HAT, Pi 4 only) or — cheaper and simpler — a **JetKVM** at about
US$103. Buy the appliance rather than building it unless you want the project.

---

## 2. What the standard lists recommend that you already run

Skip past all of these when you read any "top Pi projects" article:

- **Frigate** with a Coral TPU — 6 cameras, face and plate recognition
- **Immich** — full self-hosted photo library on the NUC
- **Home Assistant** — 2005 entities, 44 integrations, Mosquitto, ESPHome, Matter
- **Music Assistant**, **go2rtc**, **openWakeWord/microWakeWord**
- **Docker + Compose**, on several hosts including the NAS
- A **NAS** — the Synology does SMB, NFS, snapshots and containers already

---

## 3. Worth doing, ranked

| # | Thing | Where | Effort |
|---|---|---|---|
| 1 | **VLAN the DVR** + deny-all-outbound | Cisco switch | an evening |
| 2 | **Tailscale** | NUC + workbench | minutes |
| 3 | **Two FIDO2 keys** | not a Pi | minutes |
| 4 | **Offsite restic + rest-server** (`--append-only`, LUKS, Tailscale) | **Pi 4, at a relative's house** | a weekend |
| 5 | **Vaultwarden** | Pi 4 on a USB SSD | an evening |
| 6 | **UPS + NUT**, with `.66` as master | not a Pi | an evening |
| 7 | **Uptime Kuma + Beszel** | Pi 4 | an evening |
| 8 | **Bermuda BLE trilateration** | your existing ESPHome fleet | an evening |
| 9 | **Docker registry pull-through cache** | NAS or a Pi | minutes |
| 10 | **ntfy** | any Pi | minutes |
| 11 | **AdGuard Home** | dedicated Pi 4 | an evening |
| 12 | **Anthias** signage | Pi 4 per practice | an evening |
| 13 | **Little Backup Box** | the spare Pi 5 | a weekend |
| 14 | **mmWave presence sensors** | ESPHome, not a Pi | minutes each |
| 15 | **Homebox** gear inventory | NAS or Pi | a weekend |

A few notes on the ones where the reasoning is non-obvious:

**The offsite Pi is the only job no other machine you own can do.** Every other box is
in the same room. A Pi 4, one externally-powered USB disk, a LUKS volume, joined to
Tailscale, running `restic rest-server --append-only` so ransomware on the workbench
cannot delete it. Seed it by carrying the disk there. Its failure mode is social, not
technical — it gets unplugged during a house move and nobody tells you, so pair it with
a dead-man's-switch ping.

**AdGuard Home over Pi-hole, for you specifically.** Per-client filtering from one
binary means a hard blocklist for the camera/IoT range and a permissive one for the
editing workstation. Pi-hole needs groups plus a separate Unbound or cloudflared
container to match that. But note the real risk: you run a large Alexa fleet plus Ring,
Tapo, LIFX and Bambu — aggressive blocklists reliably break exactly that class of
device. Start with defaults and expect a fortnight of whitelisting.

**Anthias is the only genuinely commercial item in the survey.** A dental waiting-room
screen is a billable Dental Story deliverable and the content is video you already
produce. Its limit is that it is genuinely single-screen: one practice is delightful,
five practices is five Pis with no fleet management.

---

## 4. Still widely recommended, actually dead

This is the most valuable section, because every one of these still ranks well in
search and reads as current.

| Project | Status |
|---|---|
| **PiVPN** | Archived 2 Nov 2024 |
| **Gravity Sync** | Archived; structurally cannot work with Pi-hole v6's API |
| **wyoming-satellite** | Archived read-only **27 Jan 2026** → Linux Voice Assistant |
| **room-assistant** | Last release **March 2022**; v3 in beta since 2021 |
| **MinIO** | Archived 25 Apr 2026 — *"NO LONGER MAINTAINED"* |
| **File Browser** | Archived **1 Sep 2026**, 36k stars, no further security fixes |
| **motionEyeOS** | Last OS release **2020**; people still flash those images |
| **Shinobi** | Public repo frozen ~6 years |
| **Double-Take / CompreFace** | Superseded by Frigate's native face recognition |
| **Promtail** | EOL 2 Mar 2026 → Grafana Alloy |
| **Drone CI** | Now "Harness Open Source"; OSS moved to Woodpecker |
| **Dockge** | 24.2k stars, last release Mar 2025 — stars lagging reality |
| **Heimdall** | Feature-frozen; container base keeps `pushed_at` looking fresh |
| **Enviro+ HAT** | Discontinued; still the internet's default air-quality answer |
| **apt-cacher-ng** | Premise expired |
| **RetroPie** | Last tagged release 4.8, **March 2020**, no official Pi 5 image — use Batocera |

Three that deserve their own line:

**NOAA APT weather satellites are gone.** NOAA-18 decommissioned 6 June 2025, NOAA-19
on 13 August, NOAA-15 on 19 August. **The last APT transmitter in orbit is silent.**
Roughly half of every "SDR projects for Raspberry Pi" list is now instructions for
receiving nothing. Meteor M2-series (LRPT) still transmits; APT does not.

**`RPi.GPIO` is dead on the Pi 5.** The GPIO registers moved behind the RP1
southbridge, so `/dev/mem` poking cannot reach them. Any tutorial that starts
`import RPi.GPIO` fails on a Pi 5. Use `gpiozero` or `lgpio`.

**Repos that moved, where search still surfaces the corpse:** Homepage
(`benphelps` → `gethomepage`, old repo frozen at 199 stars), Homebox
(`hay-kot` → `sysadminsmedia`), BirdNET.

---

## 5. Traps — popular, and wrong for you

- **Jellyfin or Plex on a Pi.** Jellyfin's own docs now carry a deprecation notice for
  Pi V4L2 acceleration, citing the Pi 5's total lack of an H.264 encoder. Plex is worse
  — a recurring subscription for a server that physically cannot do what the
  subscription unlocks.
- **A Pi as router or firewall.** pfSense and OPNsense are x86-only, so this is not a
  config question, it is impossible as stated. And every Pi 4 has one NIC, so routing
  means a USB3 adapter on the same VL805 the storage uses.
- **Nextcloud.** Duplicates Synology Drive, duplicates Immich (worse), and PHP stats
  every file individually against an NFS mount — the known-worst deployment shape.
- **A k3s cluster on the four Pi 4s.** Every workload you care about is pinned to
  specific hardware: Frigate to the Coral, Immich to NAS mounts, HA to a VM with USB
  passthrough. There is nothing to schedule.
- **Ollama on a Pi CPU.** 2–5 tok/s, and published benchmarks are first-run numbers —
  without active cooling a Pi 5 halves throughput within ~90 seconds. You have a NUC one
  hop away.
- **LanCache on a Pi for LAN events.** The use case is real, the host is wrong: a Pi 4
  with USB storage has been measured serving 30–40 MB/s — **slower than a decent NBN
  connection**, so the cache makes downloads worse.
- **Klipper or OctoPrint for the Bambus.** Closed firmware, no exposed serial host port.
  Getting Klipper on means X1Plus-style jailbreaking, which risks the AMS.
- **A Zigbee/Z-Wave coordinator on a spare Pi.** You have no Zigbee or Z-Wave network to
  separate. Starting one in 2026 means buying a coordinator *and* devices.
- **A self-hosted GitHub Actions runner for resolve-sync.** The justification evaporated
  — GitHub gave public repos free hosted arm64 runners in January 2025.
- **MagicMirror².** The framework is alive (23.8k stars); the *project* is the problem —
  two-way glass, a frame, a monitor and a wall, for a clock you have three of.

### And one correction to my own earlier enthusiasm

Earlier tonight I flagged that **Frigate no longer recommends Coral for new installs**
and points builders at Hailo instead, and that Google archived the Coral toolchain —
**pycoral 3 July 2025 and libedgetpu 14 October 2025, both verified by fetching the
repos directly.**

That is all true, and worth knowing. **It is not a reason to replace your Coral.** It
does 11.5 ms across six cameras with `skipped_fps: 0.0`; the Hailo-8L benches around
10–13 ms. That is a lateral move at higher cost, and several users report the Coral is
*better* at night with IR illumination. Archived does not mean broken.

The correct read: your current setup is fine, and the archive matters for the **next**
build, not this one. If the Coral ever dies or you go past six cameras, the AI HAT+
(Hailo-8L ~$70 / Hailo-8 ~$110) is the succession path — and the spare Pi 5 is the
board for it.

---

## 6. If you filled all five boards from this survey alone

| Board | Job |
|---|---|
| Pi 4 #1 | **The offsite box — and it leaves the house.** The only job no other machine you own can do. |
| Pi 4 #2 | **Vaultwarden** — small, security-sensitive, deserves its own box |
| Pi 4 #3 | **AdGuard Home** — decoupled from the hypervisor, so a HA reboot is not a DNS outage |
| Pi 4 #4 | **Uptime Kuma + Beszel + ntfy** — the "did something break" board |
| Pi 5 | **Little Backup Box**, or hold it as the Frigate succession board with an AI HAT+ |

That is a coherent fleet, and notably it **overlaps only partly with the plan from last
week** — which allocated boards to a canary/watchdog, an ESPHome build server and a
travelling LAN kit. Both are defensible. The survey's version is more conventional; the
plan's version is more specific to your businesses.

### One correction the survey forces on last week's plan

I put an **ESPHome build server** on `sparks` (a 4 GB Pi 4). The survey rates that
*actively a bad idea*, and it is right on the facts — but the correction needs to be
precise, because the two arguments are about different things.

- **My reason was reachability**, and it still stands: your STATUS.md records that the
  ESPHome Device Builder add-on is **ingress-only**, so port 6052 is not exposed, which
  is why the Alexa wake-word rebuild had to happen from a venv on the Windows box.
- **The survey's reason is speed**, and it is the stronger point: that add-on already
  runs inside the HA VM on an **i5-8400T with 16 GB**. Moving compiles to a Pi 4 makes
  them dramatically slower — community reports around **27 minutes for a single ESP32
  build**. The 4 GB RAM floor I specified was real, and even meeting it, the board is
  the wrong host.

So the *problem* was real and the *fix* was wrong. The right fixes, in order: expose the
existing add-on on the LAN, or run the ESPHome CLI on the NUC or the workbench — both of
which are several times faster than any Pi you own.

**Drop the `sparks` role. Keep the goal.**
