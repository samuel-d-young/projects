"""Physical disk enumeration and the safety gate that stands in front of writing.

This module exists because of one number: the workbench has a 13 TB drive holding
4.8 TB of wedding footage, and the classic SD-card-imaging bug is picking the wrong
physical disk. Every rule here is deny-by-default. A disk is not writable unless it
affirmatively proves it is removable, small, non-system and unprotected.

Nothing in this file writes. It only decides whether writing would be allowed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Iterable

# --- The hard limits -------------------------------------------------------------
# A Raspberry Pi boot device is an SD card or a modest USB SSD. Nothing legitimate
# in this workflow is bigger than this, and every drive worth protecting is.
MAX_TARGET_BYTES = 2 * 1024**4  # 2 TiB
MIN_TARGET_BYTES = 3 * 1024**3  # 3 GiB - smaller than any usable Pi OS install

# Bus types we will write to. Anything not in this set is refused outright, which
# is what keeps NVMe, SATA, RAID, iSCSI and SAS disks out of reach entirely.
ALLOWED_BUS_TYPES = {"USB", "SD", "MMC"}

# Volume labels that must never appear on a write target. These are Samuel's data
# drives, read off the live machine on 2026-08-28. A label match is an instant,
# unappealable refusal - it survives even a correct-looking disk number.
PROTECTED_LABELS = {
    "M1",
    "M2",
    "M4",
    "M6 BACKUP",
    "VIDEO WORK",
    "GAMES",
    "GAMES (UNSTABLE)",
    "EASYSTORE",
    "LOCAL DISK",
}


class DiskSafetyError(RuntimeError):
    """Raised when something asks to write to a disk that failed the gate."""


@dataclass
class Volume:
    partition_number: int
    drive_letter: str
    size: int
    label: str
    filesystem: str

    @property
    def display(self) -> str:
        letter = f"{self.drive_letter}:" if self.drive_letter else "(no letter)"
        label = self.label or "(no label)"
        return f"{letter} {label} [{self.filesystem or '?'}] {human(self.size)}"


@dataclass
class Disk:
    number: int
    friendly_name: str
    serial: str
    size: int
    bus_type: str
    media_type: str
    partition_style: str
    is_boot: bool
    is_system: bool
    is_offline: bool
    is_readonly: bool
    path: str
    volumes: list[Volume] = field(default_factory=list)

    # -- the gate -----------------------------------------------------------------
    def refusals(self) -> list[str]:
        """Every reason this disk must not be written to. Empty list means allowed."""
        why: list[str] = []

        if self.is_system:
            why.append("it is the SYSTEM disk")
        if self.is_boot:
            why.append("it is the BOOT disk")
        if self.is_readonly:
            why.append("it is read-only")

        bus = (self.bus_type or "").upper()
        if bus not in ALLOWED_BUS_TYPES:
            why.append(
                f"bus type is {self.bus_type or 'unknown'}, not one of "
                f"{sorted(ALLOWED_BUS_TYPES)} - internal disks are never targets"
            )

        if self.size > MAX_TARGET_BYTES:
            why.append(
                f"it is {human(self.size)}, over the {human(MAX_TARGET_BYTES)} cap "
                "- no Pi boot device is this big, so this is a data drive"
            )
        if self.size < MIN_TARGET_BYTES:
            why.append(
                f"it is only {human(self.size)}, too small to hold Raspberry Pi OS"
            )

        for vol in self.volumes:
            if vol.label and vol.label.strip().upper() in PROTECTED_LABELS:
                why.append(f"it carries the protected volume label {vol.label!r}")

        return why

    @property
    def is_writable_target(self) -> bool:
        return not self.refusals()

    @property
    def fingerprint(self) -> str:
        """The phrase the operator must retype to confirm. Deliberately awkward:
        a fingerprint cannot be produced by mashing y-Enter."""
        name = (self.friendly_name or "disk").strip()
        return f"{self.number}:{name}:{human(self.size)}"

    def describe(self) -> str:
        head = (
            f"Disk {self.number}  {self.friendly_name or '(unnamed)'}  "
            f"{human(self.size)}  bus={self.bus_type or '?'}  media={self.media_type or '?'}"
        )
        flags = []
        if self.is_system:
            flags.append("SYSTEM")
        if self.is_boot:
            flags.append("BOOT")
        if self.is_offline:
            flags.append("offline")
        if flags:
            head += "  <" + ",".join(flags) + ">"
        lines = [head]
        for vol in self.volumes:
            lines.append(f"      - {vol.display}")
        if not self.volumes:
            lines.append("      - (no partitions)")
        return "\n".join(lines)


def human(n: int | None) -> str:
    if not n:
        return "0 B"
    step = 1024.0
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < step or unit == "PB":
            if unit in ("B", "KB"):
                return f"{value:.0f} {unit}"
            return f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} PB"


_PS_ENUMERATE = r"""
$ErrorActionPreference = 'SilentlyContinue'
$out = @(Get-Disk | ForEach-Object {
  $d = $_
  $vols = @(Get-Partition -DiskNumber $d.Number | ForEach-Object {
    $p = $_
    $v = Get-Volume -Partition $p
    [PSCustomObject]@{
      PartitionNumber = [int]$p.PartitionNumber
      DriveLetter     = [string]$p.DriveLetter
      Size            = [int64]$p.Size
      Label           = [string]$v.FileSystemLabel
      FileSystem      = [string]$v.FileSystem
    }
  })
  [PSCustomObject]@{
    Number         = [int]$d.Number
    FriendlyName   = [string]$d.FriendlyName
    SerialNumber   = [string]$d.SerialNumber
    Size           = [int64]$d.Size
    BusType        = [string]$d.BusType
    MediaType      = [string]$d.MediaType
    PartitionStyle = [string]$d.PartitionStyle
    IsBoot         = [bool]$d.IsBoot
    IsSystem       = [bool]$d.IsSystem
    IsOffline      = [bool]$d.IsOffline
    IsReadOnly     = [bool]$d.IsReadOnly
    Path           = [string]$d.Path
    Volumes        = $vols
  }
})
ConvertTo-Json -InputObject $out -Depth 6 -Compress
"""


def _powershell(script: str) -> str:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        raise DiskSafetyError("PowerShell not found; disk enumeration is Windows-only")
    proc = subprocess.run(
        [
            exe,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise DiskSafetyError(f"disk enumeration failed: {proc.stderr.strip()[:400]}")
    return proc.stdout.strip()


def enumerate_disks() -> list[Disk]:
    """Every physical disk the OS can see, with its partitions and volume labels."""
    raw = _powershell(_PS_ENUMERATE)
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]

    disks: list[Disk] = []
    for item in data:
        vols_raw = item.get("Volumes") or []
        if isinstance(vols_raw, dict):
            vols_raw = [vols_raw]
        disks.append(
            Disk(
                number=int(item.get("Number", -1)),
                friendly_name=(item.get("FriendlyName") or "").strip(),
                serial=(item.get("SerialNumber") or "").strip(),
                size=int(item.get("Size") or 0),
                bus_type=(item.get("BusType") or "").strip(),
                media_type=(item.get("MediaType") or "").strip(),
                partition_style=(item.get("PartitionStyle") or "").strip(),
                is_boot=bool(item.get("IsBoot")),
                is_system=bool(item.get("IsSystem")),
                is_offline=bool(item.get("IsOffline")),
                is_readonly=bool(item.get("IsReadOnly")),
                path=(item.get("Path") or "").strip(),
                volumes=[
                    Volume(
                        partition_number=int(v.get("PartitionNumber") or 0),
                        drive_letter=(v.get("DriveLetter") or "").strip(),
                        size=int(v.get("Size") or 0),
                        label=(v.get("Label") or "").strip(),
                        filesystem=(v.get("FileSystem") or "").strip(),
                    )
                    for v in vols_raw
                ],
            )
        )
    disks.sort(key=lambda d: d.number)
    return disks


def candidate_targets(disks: Iterable[Disk] | None = None) -> list[Disk]:
    """Only the disks that pass every rule. This is the list a user may choose from."""
    pool = list(disks) if disks is not None else enumerate_disks()
    return [d for d in pool if d.is_writable_target]


def assert_writable(disk: Disk) -> None:
    """Last gate before any write.

    Raises rather than returning a boolean, so a caller cannot ignore the result
    by accident. Every write path in this package must call this immediately
    before opening the device, not once at selection time - a card can be pulled
    and a data drive plugged in between the two moments.
    """
    why = disk.refusals()
    if why:
        raise DiskSafetyError(
            f"REFUSING to write to disk {disk.number} "
            f"({disk.friendly_name or 'unnamed'}, {human(disk.size)}): "
            + "; ".join(why)
        )


def find_disk(number: int) -> Disk:
    for disk in enumerate_disks():
        if disk.number == number:
            return disk
    raise DiskSafetyError(f"no physical disk with number {number}")


def boot_partition_letter(disk_number: int) -> str | None:
    """After a write, Windows mounts the Pi's FAT32 boot partition. Find its letter.

    Identified by shape, not by position: a FAT filesystem on the disk we just
    wrote. Returns the bare letter (no colon), or None if Windows has not mounted
    it yet - callers should retry for a few seconds before giving up.
    """
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$out=@(Get-Partition -DiskNumber {int(disk_number)} | ForEach-Object {{"
        "$v=Get-Volume -Partition $_;"
        "[PSCustomObject]@{Letter=[string]$_.DriveLetter;FS=[string]$v.FileSystem;"
        "Size=[int64]$_.Size;Label=[string]$v.FileSystemLabel}});"
        "ConvertTo-Json -InputObject $out -Depth 3 -Compress"
    )
    raw = _powershell(script)
    if not raw:
        return None
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    for part in data:
        letter = (part.get("Letter") or "").strip()
        fs = (part.get("FS") or "").upper()
        if letter and fs.startswith("FAT"):
            return letter
    return None
