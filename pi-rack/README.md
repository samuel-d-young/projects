# pi-rack

Turning four spare Raspberry Pi 4Bs and one Pi 5 into a rack that earns its
power bill, and a wizard that builds the cards to do it.

| Path | What |
|---|---|
| [BUILD-LOG.md](BUILD-LOG.md) | Dated, append-only. **Read the last entry first** if picking this up cold. |
| [docs/GROUND-TRUTH.md](docs/GROUND-TRUTH.md) | Everything measured rather than assumed. Re-check here first when something breaks. |
| [docs/PLAN.md](docs/PLAN.md) | What each node is for, and why. |
| [docs/OPTIONS.md](docs/OPTIONS.md) | **Ten things worth building** — from 105 invented, 47 cut. Only three want a Pi. |
| [docs/SURVEY.md](docs/SURVEY.md) | What Pis actually get used for — 183 uses surveyed, plus what's **dead but still recommended**. |
| [docs/REJECTED.md](docs/REJECTED.md) | What was considered and deliberately not built. Often the more useful file. |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | The go-live sequence, phase by phase. |
| [docs/PROVISIONING.md](docs/PROVISIONING.md) | What goes on the cards, boot media, EEPROM, and fleet management. |
| [docs/BOM.md](docs/BOM.md) | Shopping list, AUD, with what to check before ordering. |
| [fleet.toml](fleet.toml) | **The source of truth.** Nodes, addresses, roles. |
| `wizard/` | `piwiz`, the setup wizard. |
| `roles/` | One directory per role: `role.toml` + `bootstrap.sh`. |
| `bootstrap/lib/common.sh` | Shared shell helpers every role sources. |
| `prototypes/` | Working proofs, not plans. `ledger` (what is where, and is it safe) and `freeboard` (will the next job fit). Both run today. |

---

## The wizard

```bash
pi-wizard
```

That runs the guided flow: preflight, pick a node, fetch and verify the OS image,
choose a card, write it, seed it, and tell you what to do next.

Individual steps, if you would rather drive it yourself:

```bash
pi-wizard doctor
```

```bash
pi-wizard keygen
```

```bash
pi-wizard plan
```

```bash
pi-wizard flash gaffer
```

| Command | What it does |
|---|---|
| `doctor` | Checks Python, PyYAML, ssh, Imager, Administrator, the image cache, every visible disk, and `fleet.toml`. Run it first. |
| `keygen` | Creates the one ed25519 key the whole fleet trusts. |
| `init` | Writes a commented `fleet.toml` template. |
| `plan` | Validates `fleet.toml` and prints the rack, with per-node warnings. |
| `roles` | Lists the role catalogue with RAM floors, ports and required hardware. |
| `fetch` | Downloads Raspberry Pi OS and verifies its SHA-256 against the official index. |
| `flash <node>` | The whole card, end to end: image, disk choice, confirmation, write, verify, seed. |
| `seed <node>` | Writes only the cloud-init files onto an already-written card. **No Administrator needed.** |
| `scan` | Re-scans the LAN and reports addresses that have appeared or vanished. |
| `verify` | Checks which nodes are answering on SSH. |

### The two things worth knowing before you run it

**1. Writing a card needs Administrator. Seeding one does not.**

That split is deliberate. The step that actually turns a generic Raspberry Pi OS
card into *this* node — hostname, static IP, your SSH key, no password login,
its role software — is `seed`, and it is just three text files written to a FAT32
partition. So if the writer will not cooperate, this always works:

1. Write a plain Raspberry Pi OS Lite (64-bit) card with the Raspberry Pi Imager
   GUI. Skip its customisation screen entirely — `piwiz` supplies all of it.
2. `pi-wizard seed gaffer`

**2. It will not write to your data drives, and it has been tested on yours.**

The workbench has eleven physical disks, and *eight of the nine data drives
report bus type USB* because they sit in QNAP enclosures. The obvious safety
check — "only offer removable disks" — would have happily offered the 12.7 TB
volume holding 4.8 TB of wedding footage.

So the gate refuses on four independent grounds, any one of which is enough:

- the disk is flagged system or boot
- its bus type is not USB, SD or MMC
- it is larger than 2 TiB (no Pi boot device is)
- it carries one of the protected volume labels (`M1`, `M2`, `M4`, `M6 Backup`,
  `Video Work`, `Games`, `easystore`, ...)

and then makes you retype a fingerprint like `11:SDXC Card:64.0 GB` before it
writes. `wizard/tests/test_disks.py` asserts specifically that the bus check
*alone* would have failed, so nobody later simplifies the gate down to it.

---

## What actually goes on the SD card

Short version: **Raspberry Pi OS Lite (64-bit)**, plus three cloud-init files.

Longer version, because this is the part where stale documentation costs you a
trip to the rack with a monitor: Raspberry Pi OS (trixie) does its first-boot
configuration with **cloud-init**, seeded from `user-data`, `network-config` and
`meta-data` in the root of the FAT32 `bootfs` partition. It is *not* the
`custom.toml` mechanism you will find in most guides, and it is not
`firstrun.sh`. This was confirmed by extracting the official image and reading
`/etc/cloud/cloud.cfg.d/99_raspberry-pi.cfg` out of it — see
[docs/GROUND-TRUTH.md](docs/GROUND-TRUTH.md) §1 for the full evidence.

What `piwiz` puts in those files:

- **`user-data`** — the admin user with your SSH key, password login disabled,
  root disabled, **no `pi` account created at all**, hostname, Melbourne
  timezone and `en_AU.UTF-8`, base packages, the role scripts, and the commands
  to run them.
- **`network-config`** — a static IPv4 address on `eth0` with
  `optional: false`, so first boot waits for the link before apt runs.
- **`meta-data`** — an `instance_id` derived from that node's plan entry, so
  editing `fleet.toml` and re-flashing genuinely re-provisions rather than
  silently doing nothing.

Nothing is typed twice. Every one of those values comes from `fleet.toml`.

---

## Conventions

- **`fleet.toml` is the source of truth.** Edit it and re-flash. Never configure
  a node by hand and let the two drift — the same rule the `home-assistant`
  project here uses for its plan files.
- **Roles are directories, not Python.** If a role needs a package, a port or
  8 GB of RAM, it says so in its own `role.toml`, and the wizard can then warn
  you *before* anything is written.
- **Role scripts are idempotent and loud.** They may be re-run. They log to
  `/var/log/pi-rack-bootstrap.log` with the role name on every line, so "which
  role broke" is one `grep`.
- **`*.sh` is `eol=lf` in `.gitattributes`.** A CRLF checkout puts a carriage
  return in the shebang and the Pi reports `bad interpreter` with no useful
  hint. `roles.py` refuses to load a script with CRLF rather than let that reach
  a card.
- **Facts are tagged `(verified)` or `(assumed)`.** Never build on an assumed
  fact as if it were confirmed.

## Tests

```bash
python wizard/tests/test_disks.py
```

```bash
python wizard/tests/test_bootcfg.py
```

No pytest required — both run standalone, matching `resolve-sync`.
