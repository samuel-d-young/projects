"""Tests for the disk safety gate.

Run standalone - pytest is not assumed to be installed:

    python wizard/tests/test_disks.py

Why this file exists, in one paragraph: on 2026-08-28 the live workbench was
enumerated and *eight of the nine data drives reported bus type USB*, because
they sit in QNAP USB enclosures. A "refuse anything that is not removable"
check - the obvious first instinct, and what most SD-flashing tools do - would
have offered every one of them as a valid target, including the 12.7 TB volume
holding 4.8 TB of irreplaceable wedding footage. The size cap and the label
list are what actually stand between the wizard and that disaster. These tests
exist so nobody later "simplifies" the gate down to the bus check.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piwiz.disks import (  # noqa: E402
    MAX_TARGET_BYTES,
    Disk,
    DiskSafetyError,
    Volume,
    assert_writable,
    candidate_targets,
    human,
)

GB = 1024**3
TB = 1024**4

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


def make_disk(**kw) -> Disk:
    base = dict(
        number=99,
        friendly_name="Generic MassStorageClass",
        serial="0000",
        size=32 * GB,
        bus_type="USB",
        media_type="",
        partition_style="MBR",
        is_boot=False,
        is_system=False,
        is_offline=False,
        is_readonly=False,
        path=r"\\.\PHYSICALDRIVE99",
        volumes=[],
    )
    base.update(kw)
    return Disk(**base)


def vol(letter: str = "", label: str = "", size: int = 256 * 1024 * 1024, fs: str = "FAT32") -> Volume:
    return Volume(
        partition_number=1,
        drive_letter=letter,
        size=size,
        label=label,
        filesystem=fs,
    )


# --- The happy path must actually work -------------------------------------------
# A gate that refuses everything is safe and useless. These prove it says yes.

print("\n[1] a plausible SD card is accepted")
sd = make_disk(number=11, friendly_name="SDXC Card", size=64 * GB, bus_type="SD")
check("64 GB SD card is a valid target", sd.is_writable_target, sd.refusals())

usb_stick = make_disk(number=12, friendly_name="SanDisk Ultra", size=32 * GB, bus_type="USB")
check("32 GB USB reader is a valid target", usb_stick.is_writable_target, usb_stick.refusals())

ssd = make_disk(number=13, friendly_name="Samsung T7", size=500 * GB, bus_type="USB")
check("500 GB USB SSD is a valid target (Pi 4 USB boot)", ssd.is_writable_target, ssd.refusals())

used_card = make_disk(
    number=14,
    friendly_name="SDXC Card",
    size=64 * GB,
    bus_type="SD",
    volumes=[vol("F", "bootfs"), vol("", "rootfs", 30 * GB, "Unknown")],
)
check("a card already carrying Pi OS is still a valid target", used_card.is_writable_target,
      used_card.refusals())


# --- The real-world near-miss -----------------------------------------------------

print("\n[2] Samuel's actual data drives are refused (all report bus type USB)")
weddings = make_disk(
    number=7,
    friendly_name="ST14000N QNAP",
    size=int(12.7 * TB),
    bus_type="USB",
    volumes=[vol("K", "M1", int(12.7 * TB), "NTFS")],
)
check("12.7 TB K: (M1, holds the weddings) is refused", not weddings.is_writable_target)
check("  ...refused on size", any("over the" in r for r in weddings.refusals()))
check("  ...and independently on label", any("protected volume label" in r for r in weddings.refusals()))

video_work = make_disk(
    number=5,
    friendly_name="ST14000N QNAP",
    size=int(12.7 * TB),
    bus_type="USB",
    volumes=[vol("L", "Video Work", int(12.7 * TB), "NTFS")],
)
check("12.7 TB L: (Video Work) is refused", not video_work.is_writable_target)

print("\n[3] the bus check ALONE would not have saved them - proving the layers matter")
bus_only_would_allow = weddings.bus_type.upper() in {"USB", "SD", "MMC"}
check("bus type of the wedding drive is USB, i.e. 'removable' looking", bus_only_would_allow)
check("but the gate still refuses it", not weddings.is_writable_target)


# --- Each rule, isolated ----------------------------------------------------------

print("\n[4] every individual rule fires")
check("system disk refused", not make_disk(is_system=True).is_writable_target)
check("boot disk refused", not make_disk(is_boot=True).is_writable_target)
check("read-only disk refused", not make_disk(is_readonly=True).is_writable_target)
check("NVMe refused", not make_disk(bus_type="NVMe").is_writable_target)
check("SATA refused", not make_disk(bus_type="SATA").is_writable_target)
check("RAID refused", not make_disk(bus_type="RAID").is_writable_target)
check("iSCSI refused", not make_disk(bus_type="iSCSI").is_writable_target)
check("unknown bus refused", not make_disk(bus_type="").is_writable_target)
check("oversize refused", not make_disk(size=MAX_TARGET_BYTES + 1).is_writable_target)
check("undersize refused", not make_disk(size=1 * GB).is_writable_target)
check(
    "protected label refused even at valid size",
    not make_disk(size=64 * GB, volumes=[vol("Z", "M4", 64 * GB, "NTFS")]).is_writable_target,
)
check(
    "protected label match is case-insensitive",
    not make_disk(size=64 * GB, volumes=[vol("Z", "video work", 64 * GB, "NTFS")]).is_writable_target,
)
check(
    "exactly at the cap is allowed, one byte over is not",
    make_disk(size=MAX_TARGET_BYTES).is_writable_target
    and not make_disk(size=MAX_TARGET_BYTES + 1).is_writable_target,
)


# --- assert_writable must raise, not return ---------------------------------------

print("\n[5] assert_writable raises rather than returning a boolean")
try:
    assert_writable(weddings)
    check("assert_writable raised on the wedding drive", False, "(it returned instead)")
except DiskSafetyError as exc:
    check("assert_writable raised on the wedding drive", True)
    check("  ...and the message names the disk", "7" in str(exc) and "12.7 TB" in str(exc), str(exc))

try:
    assert_writable(sd)
    check("assert_writable passes a real SD card", True)
except DiskSafetyError as exc:
    check("assert_writable passes a real SD card", False, str(exc))


# --- candidate_targets filters ----------------------------------------------------

print("\n[6] candidate_targets returns only the safe ones")
pool = [weddings, video_work, sd, usb_stick, make_disk(is_system=True, number=0)]
cands = candidate_targets(pool)
check("only the two safe disks survive", sorted(d.number for d in cands) == [11, 12],
      [d.number for d in cands])


# --- fingerprint confirmation -----------------------------------------------------

print("\n[7] the confirmation fingerprint is specific and not guessable by mashing keys")
fp = sd.fingerprint
check("fingerprint contains the disk number", fp.startswith("11:"), fp)
check("fingerprint contains the model", "SDXC Card" in fp, fp)
check("fingerprint contains the size", "64.0 GB" in fp, fp)
check("two different disks have different fingerprints", sd.fingerprint != usb_stick.fingerprint)


print("\n[8] human() formatting")
check("bytes", human(512) == "512 B", human(512))
check("GB", human(64 * GB) == "64.0 GB", human(64 * GB))
check("TB", human(int(12.7 * TB)) == "12.7 TB", human(int(12.7 * TB)))
check("zero/None", human(0) == "0 B" and human(None) == "0 B")


print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all disk-safety tests passed")
