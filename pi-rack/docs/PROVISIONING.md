# Provisioning reference — what actually goes on the cards

The mechanics, in the order you need them. [GROUND-TRUTH.md](GROUND-TRUTH.md) §1 has
the evidence for the cloud-init part; this file is the operational how-to plus the
boot-media decisions.

Tagged **(verified)** — a primary source was read or a command was run here — or
**(assumed)**.

> **Coverage note.** Three research agents assigned to independently re-verify the
> imaging, first-boot and SSD-boot mechanics died on a session limit before
> reporting. Everything below still comes from a source-checked pass — the
> `rpi-imager` flags were read out of `src/cli.cpp`, the EEPROM values out of the
> official documentation, and the cloud-init behaviour was confirmed by extracting
> the real image on this machine — but it has had **one** verification pass rather
> than two. Treat the EEPROM and NVMe sections as good but unrepeated, and check
> them against `rpi-eeprom-config` output on the actual board before relying on
> them.

---

## 1. The image

**Raspberry Pi OS Lite (64-bit).** Every node here is headless; a desktop image is
2 GB of extra attack surface and SD wear for nothing.

Current as of 2026-08-28 **(verified — fetched and hashed on this machine)**:

```
2026-06-18-raspios-trixie-arm64-lite.img.xz
524,875,608 bytes compressed / 2,977,955,840 extracted
sha256 e235fd24fc5f039c08daba7d3abc04aecc7313f979d16d2a3fdad29dd44c33a9
```

Do **not** hard-code that hash anywhere. `piwiz` fetches
`https://downloads.raspberrypi.org/os_list_imagingutility_v4.json` and takes the URL
and `extract_sha256` from it, then verifies the decompressed image as it writes it to
the cache. A hand-copied hash with one wrong character fails every write with a
useless error.

```bash
pi-wizard fetch
```

**Cache location matters.** `K:` has under 50 GB free of 13 TB. `piwiz` picks the
fixed drive with the most free space and refuses anything under 20 GB — on this
machine it lands on `O:`.

---

## 2. The three files that turn a generic card into a node

Raspberry Pi OS trixie provisions with **cloud-init**, seeded from the root of the
FAT32 `bootfs` partition — the drive letter Windows mounts when you insert a freshly
written card. **(verified)**

| File | Purpose |
|---|---|
| `user-data` | `#cloud-config` — user, SSH key, hostname, packages, files, commands |
| `network-config` | netplan v2 — static address, gateway, DNS |
| `meta-data` | `instance-id`, `dsmode: local`, `local-hostname` |

This is **not** `custom.toml` and **not** `firstrun.sh`. Guidance written for Bookworm
and earlier says otherwise and is out of date; following it produces a card whose
config the OS silently ignores.

```bash
pi-wizard seed gaffer
```

That step needs **no Administrator**, which is the whole point of the split: however
the card got written — including by the Imager GUI — seeding it works.

### Four behaviours worth knowing

1. **The `pi` user is created *by* cloud-init**, not baked into the image. A `users:`
   block that omits `- default` means it is never created at all. That is how the
   wizard removes the stock account: by not asking for it.
2. **Host keys are generated on first boot** by `regenerate_ssh_host_keys.service`
   (`ssh_genkeytypes: []`, `ssh_deletekeys: false`). Writing the same image to five
   cards does *not* give five Pis the same host key.
3. **`optional: false` on `eth0` is load-bearing.** Every node installs packages on
   first boot; without it, cloud-init starts apt before the link is up. The shipped
   `network-config` warns about this in its own comments.
4. **`instance-id` decides whether first-boot setup re-runs.** `piwiz` derives it from
   the node's `fleet.toml` entry plus the `--revision` string, so editing the plan and
   re-seeding genuinely re-provisions.

### The trap that costs an evening

Raspberry Pi Imager appends ` ds=nocloud;i=<its own id>` to `cmdline.txt`. **A
kernel-cmdline instance id overrides `meta-data`.** Left stale, a re-seeded card boots
with none of your changes and reports no error anywhere.

`piwiz seed` rewrites it every time — and preserves the rule that `cmdline.txt` must
stay a **single line**, because the bootloader reads line one and silently ignores the
rest.

---

## 3. Writing the card

Three paths, in order of preference. `piwiz` picks automatically.

### Raspberry Pi Imager CLI (preferred)

Not currently installed on the workbench **(verified)**:

```bash
winget install -e --id RaspberryPiFoundation.RaspberryPiImager
```

The 64-bit installer targets `C:\Program Files\Raspberry Pi\Imager\` and ships a
separate `rpi-imager-cli.cmd` whose body is `start /WAIT rpi-imager.exe --cli %*`. Use
the `.cmd`. The bare `.exe` is a GUI binary that does not wait, so a script "finishes"
the write before it has started.

Real flags at v2.0.11.1, read from `src/cli.cpp`: `--disable-verify`, `--sha256`,
`--cache-file`, `--first-run-script`, `--cloudinit-userdata`,
`--cloudinit-networkconfig`, `--disable-eject`, `--debug`, `--quiet`, `--log-file`,
`--secure-boot-key`, `--enable-writing-system-drives`, then positional src and dst.

> **Never pass `--enable-writing-system-drives`.** Imager's default refusal of
> non-removable drives is a second net under `piwiz`'s own gate. If Imager refuses a
> device, that is the guard working — do not reach for the flag that switches it off.

### The native writer

Needs Administrator; `piwiz` uses it when Imager is absent and the shell is elevated.
It clears the disk, takes it offline, writes sector-aligned, and can read the card back
and compare hashes.

### The GUI, then seed

The fallback that always works:

1. Write a plain Raspberry Pi OS Lite card with the Imager GUI. **Skip its
   customisation screen entirely** — `piwiz` supplies all of it.
2. `pi-wizard seed <node>`

---

## 4. The disk-safety gate

The single most dangerous step in the whole project, because a wrong disk number here
destroys a business.

Eight of the nine data drives on this workbench report bus type **USB** — they are in
QNAP enclosures — so "only offer removable disks" would have offered the 12.7 TB
volume holding 4.8 TB of wedding footage. **(verified against all eleven real disks.)**

`piwiz` refuses on four independent grounds, any one sufficient:

- flagged system or boot
- bus type not USB / SD / MMC
- larger than 2 TiB (no Pi boot device is)
- carries a protected volume label (`M1`, `M2`, `M4`, `M6 Backup`, `Video Work`,
  `Games`, `Games (Unstable)`, `easystore`, `Local Disk`)

Then it makes you retype a fingerprint like `11:SDXC Card:64.0 GB`. And it re-checks
immediately before the write, not once at selection — a card can be pulled and a data
drive plugged into the same reader in between.

`wizard/tests/test_disks.py` asserts specifically that *the bus check alone would have
failed*. Do not simplify the gate down to it.

---

## 5. Which media for which node

| Node | Media | Why |
|---|---|---|
| `gaffer` | 32 GB A1 microSD | Writes almost nothing. The card is a consumable, and recovery is `pi-wizard flash gaffer` |
| `sparks` | USB SSD | One esp-idf build writes several GB. Repeatedly doing that to a card is how cards die |
| `runner` | 32 GB A1 microSD | Rewritten before each event anyway |
| `standby` | **Match `.70` exactly** | It is not a spare if it does not boot the same way |

### Card buying, corrected

- **A2 is a Pi 5 feature.** Its advantage comes from Command Queueing, which needs a
  CQHCI engine: BCM2712 has one, BCM2711 does not. An A2 card in a Pi 4 buys nothing
  and can measurably lose to a plain A1.
- **"High endurance" cards are the wrong tool for a root filesystem.** They carry no
  A-class rating at all and are specified for sequential CCTV recording, not the small
  random I/O an OS does.
- So: generic **A1 32 GB** for the Pi 4s. Bigger cards do not last meaningfully longer
  at these write rates.

---

## 6. Booting from something better than a card

### Pi 4 — USB SSD

**Audit the enclosure before imaging**, not after:

```bash
lsusb -t
```

The bridge must show driver `uas`, not `usb-storage`. If it shows `usb-storage`, that
enclosure needs a `usb-storage.quirks` kernel parameter — a fact worth having before a
card has been written and a node is silently slow.

Then set the boot order:

```bash
sudo rpi-eeprom-config --edit
```

`BOOT_ORDER=0xf14` — nibbles read **right to left**: `4` USB-MSD first, `1` SD, `f`
RESTART (loop). The stock default is `0xf41` (SD then USB).

**Then leave the SD slot empty.** A failed SSD should give a clean, obvious no-boot,
never a silent boot into a stale rootfs at 2am.

Useful EEPROM settings for slow enclosures: `USB_MSD_DISCOVER_TIMEOUT` (default
20000 ms, min 5000), `USB_MSD_STARTUP_DELAY` (max 30000), `USB_MSD_LUN_TIMEOUT`
(default 2000, min 100).

Two more worth setting on any headless rack node:

```
NET_INSTALL_AT_POWER_ON=0
BOOT_WATCHDOG_TIMEOUT=60
```

The first removes the network-install UI and about a second of boot time spent
initialising USB to look for a keyboard that is not there. The second hard-resets the
board if the OS has not started in 60 seconds — it is cancelled the moment the Arm CPU
starts, so it breaks a hung *boot*, not a hung OS.

### Pi 5 — NVMe

Only if `.70` turns out to boot from NVMe, per [RUNBOOK](RUNBOOK.md) Phase 1.

```
BOOT_ORDER=0xf416     # right-to-left: 6 NVMe, 1 SD, 4 USB, f restart
```

- The **official M.2 HAT+ takes 2230 and 2242 only** — a 2280 stick will not screw
  down. Use a 2280-capable third-party base if you want a large drive.
- HAT+ compliant boards are auto-detected. Non-HAT+ adapters also need `PCIE_PROBE=1`
  in the EEPROM config and `dtparam=pciex1` in `config.txt`.
- **Stay at Gen 2.** `dtparam=pciex1_gen=3` exists, but Raspberry Pi's own
  documentation says the Pi 5 is not certified for Gen 3.0 and that Gen 3.0 links may
  be unstable. On an unattended rack node, take the stable link.

Confirm afterwards with `ls -l /dev/nvme*` and `lsblk`.

---

## 7. After first boot

```bash
pi-wizard verify
```

Then, on the node:

```bash
ssh vultron@192.168.1.101 "cat /var/lib/pi-rack-provisioned; cloud-init status --long"
```

**If `/var/lib/pi-rack-provisioned` is missing, cloud-init never ran at all** — a
completely different problem from a service that failed, and knowing which saves an
hour. Look in `/var/log/cloud-init-output.log`.

Check `cloud-init status --long` rather than assuming: there is an open upstream defect
(`raspberrypi/trixie-feedback#26`) where once-per-instance modules run with frequency
`always` on Pi OS trixie Lite, so `growpart` and `resizefs` re-execute every boot.

### Two operational surprises

**`journalctl -b -1` returns nothing.** Pi OS trixie ships
`/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` with
`Storage=volatile`, so the journal lives in RAM and the previous boot's log does not
survive. You will want it the first time a node wedges.

Do **not** install log2ram to "fix" this — the job it does is already done, and it adds
a sync timer and a class of "where did my logs go" bugs. If a specific node genuinely
needs persistent logs, use `raspi-config` → Advanced Options → Logging.

**There is no battery-backed clock.** Rather than fitting an RTC cell to the one board
that can take one, order time-sensitive units after the clock is right — this works on
all five boards and costs nothing:

```bash
sudo systemctl enable systemd-time-wait-sync.service
```

then `After=time-sync.target` in the unit.

---

## 8. Managing the fleet afterwards

**cloud-init owns identity. Something else owns everything after.**

Identity — hostname, user, key, network — must be baked in, because it has to be right
before the node is reachable. Everything else should be re-runnable, because you will
change your mind.

For five nodes owned by one person: **Docker Compose per node for workloads, plain
Ansible over SSH if and when config drift becomes annoying.** No AWX, no pull agent, no
Salt master.

If you do run Ansible, put the control node on **`.42`** — it is always on and already
the fleet's control plane. Not WSL on the workbench, which gets rebooted mid-render and
whose `K:` has under 50 GB free.

**Not k3s.** A control plane is 512 MB–1 GB, which is most of a 2 GB Pi 4, spent to
reschedule five long-lived services across five machines whose placement you already
decided. Revisit past about ten nodes.

**Not PXE/netboot.** An afternoon of DHCP, TFTP, an rsynced rootfs and a chroot to
regenerate host keys, amortised over five machines provisioned once — and it would make
the Synology a single point of failure for every Pi at once.

---

## 9. Rebuilding a dead node

This is the property the whole design exists to give you:

```bash
pi-wizard flash gaffer
```

`fleet.toml` plus the wizard is the backup. There is no node-specific state to restore
because there is no node-specific state — anything a role needs is either in its
`role.toml`, in `bootstrap.sh`, or written on first boot.

Roughly twenty minutes, most of it waiting for apt.
