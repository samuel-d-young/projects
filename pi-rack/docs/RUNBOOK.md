# Runbook — pushing it live

Ordered so that **every phase is shippable on its own** and leaves the house better
than it found it. If you stop after any phase, nothing is half-built.

Each phase has a verification step. Do not skip them — the most expensive failure in
this whole project is a node that reports success and does not work, because that
costs a trip to the rack with a monitor and a keyboard.

Log each phase in [`BUILD-LOG.md`](../BUILD-LOG.md) with the date and what actually
happened, including what went wrong. That log is the thing that makes the next session
cheap.

---

## Phase 0 — one evening, no Raspberry Pi, ~$0

**Do this before writing a single card.** It is the highest consequence-per-minute work
in the project, and completing it removes the justification for about a third of what
was originally proposed. Details and reasoning in [PLAN.md](PLAN.md) §Phase 0.

### 0.1 Cut the DVR's outbound path

On the router, block internet access for `192.168.1.49`.

**Verify:** from the workbench, confirm the DVR's web UI still answers locally:

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 http://192.168.1.49/
```

`200` means it is still reachable on the LAN (expected — this phase only cuts its path
*out*). Full segmentation comes later, and only after the switch model is known.

### 0.2 Reserve the addresses

MAC-reserve `.42`, `.66`, `.70`, `.75`, `.83` on the router. Then confirm the DHCP pool
does not overlap `.100–.130`.

**Verify:** reboot the Home Assistant VM and confirm it comes back on `.75`.

```bash
ssh vultron@192.168.1.66 "sudo virsh reboot haos"
```

Wait two minutes, then:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.75:8123/
```

### 0.3 Give the HA guest 8 GB

```bash
ssh vultron@192.168.1.66 "sudo virsh setmaxmem haos 8G --config && sudo virsh setmem haos 8G --config"
```

Then shut down and start the guest (a live `setmaxmem` needs a full power cycle, not a
reboot):

```bash
ssh vultron@192.168.1.66 "sudo virsh shutdown haos && sleep 45 && sudo virsh start haos"
```

**Verify:** Home Assistant → Settings → System → Hardware shows 8 GB.

### 0.4 Write down the tier-1 set, then back it up

**This is the blocking prerequisite for everything downstream.** Walk one complete
wedding job — cards, ingest, edit, delivery — and write down every path it touches.
Commit that list to `K:\Claude`.

Then install `restic` on the workbench and schedule it against a Backblaze B2 bucket
with **Object Lock** enabled and an application key that cannot delete.

**Verify — and this is the only verification that counts:**

```bash
restic -r <repo> snapshots
```

then restore a file you can check by eye into a scratch directory and open it. A
backup nobody has restored is a hypothesis.

> Record the date of that first successful restore in `BUILD-LOG.md`. It becomes the
> baseline for the `days_since_verified_restore` metric that `gaffer` will publish.

---

## Phase 1 — measure, ~20 minutes, $0

**Buy nothing before this.** Two of these answers decide whether hardware is bought at
all.

On each of the five spare boards (boot with a keyboard and monitor, or a temporary
card):

```bash
cat /proc/device-tree/model; echo; free -h; ip link show eth0 | awk '/ether/{print $2}'
```

Watch for **Pi 4B rev 1.1** — pre-~Feb 2020 boards have the USB-C CC-resistor fault and
refuse e-marked cables. It bites exactly on spare boards of unknown vintage.

On the production Frigate box:

```bash
ssh 192.168.1.70 "lsblk; free -h; cat /proc/device-tree/model"
```

From a browser: the Cisco model at `192.168.1.254`, and the Synology model and free
capacity at `192.168.1.83:5001`.

**Write every answer into `fleet.toml` and `BUILD-LOG.md`.** Update the `hardware` and
`boot` fields to match reality, then:

```bash
pi-wizard plan
```

---

## Phase 2 — the wizard's own preflight, ~10 minutes

```bash
pi-wizard doctor
```

Fix anything it reports. Then create the fleet key:

```bash
pi-wizard keygen
```

**Back the private key up somewhere that is not one of these Pis** — and not the brain
vault, which has a remote. It is the only way into every node.

Optionally install Raspberry Pi Imager so the wizard can drive its CLI:

```bash
winget install -e --id RaspberryPiFoundation.RaspberryPiImager
```

Then pre-fetch and verify the OS image:

```bash
pi-wizard fetch
```

**Verify:** `doctor` ends with `Ready.` and `plan` ends with `plan is valid`.

---

## Phase 3 — `gaffer`, the witness, ~1 hour

The first board, and the one with the clearest payoff: after this, you find out when
something breaks instead of discovering it later.

```bash
pi-wizard flash gaffer
```

Insert the card, retype the fingerprint when asked, and let it write and seed. Then put
the card in the board (use the one currently at `.55`, after confirming it is genuinely
idle) and power on.

First boot installs packages, so give it **3–8 minutes** before it answers.

**Verify:**

```bash
pi-wizard verify
```

then:

```bash
ssh vultron@192.168.1.101 "cat /var/lib/pi-rack-provisioned; systemctl is-active pi-rack-canary.timer pi-rack-watchdog"
```

If `/var/lib/pi-rack-provisioned` is missing, cloud-init did not run at all — a
completely different problem from a failed service, and knowing which saves an hour.
Check `/var/log/cloud-init-output.log`.

Open `http://192.168.1.101:5115` and confirm the probe table is populating.

### Then, deliberately, in this order

1. Edit `/etc/pi-rack/canary/targets.conf` and add the real SMB shares with their
   credential files. Run `systemctl start pi-rack-canary` and watch the status page.
2. Point MQTT at Home Assistant by writing `/etc/pi-rack-mqtt.env`, so the probes
   become HA sensors and Alarmo can escalate them.
3. **Leave the watchdog watch-only for at least two weeks.** Read its log. Confirm it
   would have been right before you let it act.
4. Only then install the target-side dispatcher on `.66` and promote
   `home-assistant` from `-` to `reset-ha`. **Test the refusal first:**

```bash
ssh -i /etc/pi-rack/watchdog/id_recover vultron@192.168.1.66 "status; id"
```

That **must** be refused. If it returns a uid, the key is not pinned correctly — stop
and fix it before going further.

---

## Phase 4 — `sparks`, the build server, ~1 hour + a long first build

Needs a 4 GB board and a USB SSD. Audit the enclosure **before** imaging:

```bash
lsusb -t
```

The bridge must show driver `uas`, not `usb-storage`. If it shows `usb-storage`, the
enclosure needs a `usb-storage.quirks` entry — worth knowing now rather than after a
card has been written.

Set the boot order on that board:

```bash
sudo rpi-eeprom-config --edit
```

`BOOT_ORDER=0xf14` — nibbles read right-to-left: `4` USB first, `1` SD, `f` restart.
**Then leave the SD slot empty**, so a failed SSD gives a clean, obvious no-boot rather
than a silent boot into a stale rootfs at 2am.

```bash
pi-wizard flash sparks
```

**Verify:** `http://192.168.1.102:6052` shows the ESPHome dashboard. The first real
build downloads a >1 GB toolchain and takes a while — that is normal, not a hang.

Read `/srv/esphome/config/README-FIRST.md` before rebuilding any Voice PE firmware. It
carries the two mistakes that already cost an evening once: the factory package, and
the API encryption key.

---

## Phase 5 — `runner`, the event kit, ~45 minutes

```bash
pi-wizard flash runner
```

**Verify, at home, with DHCP disarmed:**

```bash
ssh vultron@192.168.1.103 "sudo event-dhcp status"
```

It must say `disarmed`. Then confirm the interlock actually works:

```bash
ssh vultron@192.168.1.103 "sudo event-dhcp on"
```

It **must refuse**, because it can see the home gateway. If it arms, stop and fix it —
that interlock is the only thing standing between this box and someone's venue network.

Fill in `/srv/event/index.html`, pack the case with the board, a power bank, a short
Cat6 whip and a spare card.

**The habit that matters:** `sudo event-dhcp off` before it comes home. Every time.

---

## Phase 6 — `standby`, the Pi 5 — only after Phase 1 question 2

Do not do this before you know what `.70` boots from and how much RAM it has.

- **RAM matches, `.70` boots SD** → clone a card, label it, shelf it. Set
  `enabled = true` and flash.
- **`.70` boots NVMe** → buy a 2280-capable base (the official M.2 HAT+ is 2230/2242
  only) and a matching stick. `BOOT_ORDER=0xf416`. Stay at PCIe Gen 2 for a rack node
  — Raspberry Pi's own documentation says the Pi 5 is not certified for Gen 3 and that
  Gen 3 links may be unstable.
- **RAM does not match** → it is not a spare. Say so in `BUILD-LOG.md` and leave it
  boxed.

```bash
pi-wizard flash standby
```

**Verify:** the role's preflight writes its verdict:

```bash
ssh vultron@192.168.1.104 "cat /var/lib/pi-rack/warm-spare/preflight_ok"
```

`1` means a credible spare. Anything else means read the log and resolve it.

**Then run one real drill, and time it.** Follow `/srv/frigate-spare/FAILOVER.md`,
record the elapsed time in `BUILD-LOG.md`, and set the drill date:

```bash
ssh vultron@192.168.1.104 "date -Is | sudo tee /var/lib/pi-rack/warm-spare/last_drill"
```

A drill you did not time tells you nothing about whether this works at 2am.

---

## Phase 7 — the rack itself, ~half a day

Deliberately last. **The rack is the fun part, and the fun part is not the valuable
part** — every node above works fine on a shelf. Racking it is tidiness and airflow,
and it is worth doing, but not before the things that prevent losses.

Order and reasoning are in [BOM.md](BOM.md). The two decisions that need the Phase 1
answers first:

- **10-inch vs 19-inch** depends on the Cisco's width. A 16- or 24-port managed switch
  is usually 19-inch, and if it is, a 10-inch rack cannot hold the one device that
  every other device plugs into.
- **PoE HATs vs USB-C PSUs** depends on whether the switch is a `-P` model. If it is
  not — and it may well not be — the answer is individual official PSUs, which is
  cheaper and simpler anyway.

Print the 1U trays rather than buying them: two Bambu printers make four trays about
$15 of PETG and an afternoon, against roughly $100 each for bought equivalents.

**Verify:** everything still answers after the move.

```bash
pi-wizard verify
```

Then take one photo of the front and one of the back with the cables labelled, and put
them in `docs/`. The photo is the documentation you will actually use.

---

## Rolling back

Every node in this plan is designed so that its failure is survivable:

| Node | If it dies | Rollback |
|---|---|---|
| `gaffer` | You stop being told when things break. Nothing else changes. | `pi-wizard flash gaffer` onto the swing board, ~20 min |
| `sparks` | Firmware builds fall back to the workbench venv — how they are done today | Nothing to undo |
| `runner` | Only matters at an event, and only if it was armed | `sudo event-dhcp off`, or unplug it |
| `standby` | Nothing. It is a spare. | Nothing |

**Undoing Phase 0** is the only part with LAN-wide consequences, and none of it is
destructive: unblock the DVR, remove the reservations, set the VM's memory back. Keep
the B2 repository regardless — it costs cents and there is no version of this where
having an offsite copy is the wrong call.

---

## When you come back to this cold

1. Read the last entry in [`BUILD-LOG.md`](../BUILD-LOG.md).
2. `pi-wizard plan` — what is supposed to exist.
3. `pi-wizard verify` — what actually answers.
4. `pi-wizard scan` — what has appeared or vanished on the LAN since.

The gap between 2 and 3 is your to-do list.
