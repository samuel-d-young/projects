# pi-rack — project context

Read this before touching anything here. This file is the map and the list of things
that were expensive to learn. **[BUILD-LOG.md](BUILD-LOG.md) is the running record —
read its last entry first if you are picking this up cold.**

## What this is

Putting Samuel's four spare Raspberry Pi 4Bs and one spare Pi 5 to work, and a wizard
(`piwiz`) that builds their SD cards from a single declarative file.

Three boards deploy, one waits on a two-minute measurement, one stays in its box on
purpose. The reasoning is in [docs/PLAN.md](docs/PLAN.md); the things deliberately
*not* built are in [docs/REJECTED.md](docs/REJECTED.md), which is the more useful file.

## Layout

| Path | What |
|---|---|
| `BUILD-LOG.md` | Dated, append-only. Newest at the bottom. Start here. |
| `fleet.toml` | **The source of truth.** Nodes, addresses, roles, boot media. |
| `docs/GROUND-TRUTH.md` | Everything measured rather than assumed, with how to re-check it. |
| `docs/PLAN.md` | The allocation and the reasoning behind each board. |
| `docs/OPTIONS.md` | Ten vetted build options. Most are not Pi jobs, deliberately. |
| `docs/SURVEY.md` | The 2026 survey of standard Pi uses, annotated against his stack. Has the dead-project list. |
| `docs/REJECTED.md` | 31 cut ideas and the structural rules that killed them. |
| `docs/RUNBOOK.md` | Phase-by-phase go-live, each phase shippable alone. |
| `docs/PROVISIONING.md` | Card contents, boot media, EEPROM values, fleet management. |
| `docs/BOM.md` | Shopping list, AUD, with what to confirm before ordering. |
| `wizard/piwiz/` | The wizard. `disks`, `bootcfg`, `fleet`, `roles`, `images`, `writer`. |
| `wizard/tests/` | Standalone tests — no pytest, matching `resolve-sync`. |
| `roles/<name>/` | `role.toml` (data the wizard reasons about) + `bootstrap.sh` (the work). |
| `bootstrap/lib/common.sh` | Shared shell helpers every role sources. |
| `prototypes/` | Runnable proofs behind the options: `ledger`, `freeboard`. Read-only, stdlib-only. |
| `pi-wizard.cmd` | Front door, matching the workbench's `.cmd` convention. |

## The facts that shape everything

These were verified on 2026-08-28 and are the reason the code looks the way it does.
Full evidence in `docs/GROUND-TRUTH.md`.

1. **Raspberry Pi OS trixie provisions with cloud-init, not `custom.toml`.** The seed
   is `user-data`, `network-config` and `meta-data` in the root of the FAT32 `bootfs`
   partition, because `/etc/cloud/cloud.cfg.d/99_raspberry-pi.cfg` sets
   `datasource_list: [ NoCloud, None ]` with `seedfrom: file:///boot/firmware`.
   Nearly all current tutorials describe the Bookworm-era mechanism. Building on them
   produces a Pi with no user, no key and no network.

2. **Eight of the nine data drives on the workbench report bus type USB**, because they
   live in QNAP enclosures. "Only offer removable disks" — the obvious safety rule —
   would have offered the 12.7 TB volume holding 4.8 TB of wedding footage.

3. **`K:` has 46.8 GB free of 13,039 GB.** Nothing this project generates may be cached
   there.

4. **The `pi` user is created *by* cloud-init**, not baked into the image. A `users:`
   block that omits `- default` means it is never created. That is how the wizard
   removes it — by not asking for it.

5. **The Pi 5 has no hardware H.264 encoder.** BCM2712 dropped the block the Pi 4 had.
   Any proposal involving Pi 5 video transcoding is wrong on arrival.

## Rules that must not be broken

These are all real bugs or near-misses. Each cost something.

1. **`disks.assert_writable()` is called immediately before every write, not once at
   selection time.** A card can be pulled and a 13 TB drive plugged into the same
   reader in the seconds between. The gate refuses on four independent grounds —
   system/boot flag, bus type, a 2 TiB cap, and a protected-label list — any one of
   which is sufficient. `tests/test_disks.py` asserts specifically that *the bus check
   alone would have failed*. Do not "simplify" the gate down to it.

2. **Never pass `--enable-writing-system-drives` to `rpi-imager`.** Its default refusal
   of non-removable drives is a second net under our own gate. Turning it off removes
   both at once. If Imager refuses a device, that is the guard working.

3. **`cmdline.txt` must stay a single line.** The bootloader reads line one and
   silently ignores the rest — a stray newline removes every parameter after it, with
   no error anywhere. `reconcile_cmdline()` preserves this.

4. **Imager appends ` ds=nocloud;i=<its id>` to `cmdline.txt`, and a cmdline instance
   id overrides `meta-data`.** Left stale, a re-seeded card boots with none of your
   changes and reports success. `write_seed()` reconciles it every time.

5. **`meta-data` emits both `instance-id` and `instance_id`.** cloud-init's canonical
   NoCloud key is the hyphenated one and that is what Imager writes; the file shipped
   inside the Pi OS image uses the underscore. Emitting both removes the guess.

6. **`*.sh` is `eol=lf` in `.gitattributes`, and `roles.py` refuses to load a
   `bootstrap.sh` containing CRLF.** A carriage return in a shebang fails on the Pi
   with `bad interpreter` and no useful hint. This has bitten this workbench before —
   see the `home-assistant` project.

7. **`seed` must never require Administrator.** It is the step that actually configures
   a node, and it must work when everything else fails: write the card with the Imager
   GUI, then `pi-wizard seed <node>`. Do not add a privileged dependency to that path.

8. **Role scripts are idempotent and loud.** The `once` guard writes its marker *after*
   success, so a crashed step retries rather than being silently skipped — the failure
   mode that makes "idempotent" scripts lie. Every role logs to
   `/var/log/pi-rack-bootstrap.log` with its own name on every line.

9. **`fleet.toml` is the source of truth.** Edit it and re-flash. Never configure a node
   by hand and let the two drift — the same rule `home-assistant` uses for plan files.

10. **Never add a branch to `rack-recover` that forwards arbitrary input onward.** The
    whole security property of the watchdog is that the allowlist is exhaustive. Same
    design as `home-assistant/config/nuc-control/ha-control`, deliberately — a second
    security model in one house is a second thing to get wrong.

## Conventions

- Facts are tagged **(verified)** — a primary source was read or a command was run —
  or **(assumed)**. Never build on an assumed fact as if it were confirmed.
- Roles are directories, not Python. If a role needs a package, a port, or 8 GB of RAM,
  it says so in its own `role.toml` so the wizard can warn *before* anything is written.
- The wizard is stdlib-only apart from PyYAML, which is optional and used only to prove
  that generated cloud-init parses.
- Tests run standalone: `python wizard/tests/test_disks.py`. No pytest.
- Anything a role needs to explain to a human goes in a file *on the node*
  (`README-FIRST.md`, `FAILOVER.md`), not only in this repo. The person reading it will
  be SSH'd into the box at the time.

## Things worth knowing before you debug something

- **`journalctl -b -1` returns nothing.** Pi OS trixie ships `Storage=volatile`, so the
  journal is in RAM and the previous boot's log does not survive. This is a genuine
  surprise the first time a node wedges. Do **not** install log2ram to "fix" it — the
  job it does is already done. If a specific node needs persistent logs, use
  `raspi-config` → Advanced Options → Logging.
- **`/var/lib/pi-rack-provisioned` missing means cloud-init never ran at all** — a
  different problem from a failed service. Check `/var/log/cloud-init-output.log`.
- **There is an open upstream defect** (`raspberrypi/trixie-feedback#26`) where
  once-per-instance cloud-init modules run with frequency `always` on Pi OS trixie Lite
  — `growpart` and `resizefs` re-execute every boot. Check `cloud-init status --long`
  after first boot rather than assuming.
- **No `fail2ban`, deliberately.** With password auth off there is nothing to
  brute-force, and a daemon that can firewall you out of a headless board is a net
  liability.
- **No k3s, deliberately.** A control plane is most of a 2 GB Pi 4, spent scheduling
  five services whose placement you already decided.

## Out of scope

Everything in `docs/REJECTED.md`. Before proposing something, check whether it is
already there and why — several ideas were cut on facts that were verified against
this very workbench.
