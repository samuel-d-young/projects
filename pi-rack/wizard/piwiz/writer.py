"""Write an image to a card. The one irreversible thing this wizard does.

Three paths, in order of preference:

  1. Raspberry Pi Imager's CLI, if it is installed. It is the best-tested code
     in this space and it handles volume locking properly.
  2. A native write, here. Needs Administrator. Fully guarded.
  3. Neither - print instructions for the Imager GUI and stop. The seeding step
     (`piwiz seed`) works afterwards regardless of how the card was written,
     which is why this is a perfectly acceptable outcome rather than a failure.

Every path calls `disks.assert_writable` immediately before touching anything.
Not once at selection time - immediately before, because a card can be pulled
and a 13 TB drive plugged into the same reader in the seconds between.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from . import disks
from .disks import Disk, DiskSafetyError, human

CHUNK = 4 * 1024 * 1024
SECTOR = 512

# On Windows the installer ships a SEPARATE CLI launcher, `rpi-imager-cli.cmd`,
# alongside the GUI exe (src/windows/rpi-imager.iss.in installs it to {app}).
# The GUI exe is a windowed binary: invoking it for a scripted write gives you no
# console output to read. Prefer the .cmd, fall back to the exe.
IMAGER_DIRS = [
    # The 64-bit installer's actual target: {autopf}\Raspberry Pi\Imager.
    r"C:\Program Files\Raspberry Pi\Imager",
    r"C:\Program Files (x86)\Raspberry Pi\Imager",
    # Older layouts and user-scope installs, kept as fallbacks.
    r"C:\Program Files\Raspberry Pi Imager",
    r"C:\Program Files (x86)\Raspberry Pi Imager",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Raspberry Pi Imager"),
    os.path.expandvars(r"%LOCALAPPDATA%\Raspberry Pi\Imager"),
]
IMAGER_NAMES = ["rpi-imager-cli.cmd", "rpi-imager.exe"]


class WriteError(RuntimeError):
    pass


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def find_imager() -> Path | None:
    for directory in IMAGER_DIRS:
        for name in IMAGER_NAMES:
            p = Path(directory) / name
            if p.exists():
                return p
    for name in ("rpi-imager-cli", "rpi-imager"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def imager_install_hint() -> str:
    return (
        "Raspberry Pi Imager is not installed. Either:\n"
        "  winget install -e --id RaspberryPiFoundation.RaspberryPiImager\n"
        "or download it from https://www.raspberrypi.com/software/\n"
        "The wizard can also write the card itself - run it as Administrator."
    )


# --- PowerShell helpers ----------------------------------------------------------


def _ps(script: str, timeout: int = 180) -> str:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        raise WriteError("PowerShell not found")
    proc = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise WriteError(proc.stderr.strip()[:600] or f"powershell exited {proc.returncode}")
    return proc.stdout.strip()


def clear_disk(disk: Disk) -> None:
    """Remove every partition so Windows stops holding the volumes open.

    Re-checks the gate first. `Clear-Disk -RemoveData` is destructive by design;
    it is the reason the gate above it has to be right.
    """
    disks.assert_writable(disk)
    _ps(
        f"Set-Disk -Number {disk.number} -IsOffline $false -ErrorAction SilentlyContinue;"
        f"Set-Disk -Number {disk.number} -IsReadOnly $false -ErrorAction SilentlyContinue;"
        f"Clear-Disk -Number {disk.number} -RemoveData -RemoveOEM -Confirm:$false"
    )


def rescan() -> None:
    try:
        _ps("Update-HostStorageCache; Start-Sleep -Milliseconds 500")
    except WriteError:
        pass


def wait_for_boot_partition(disk_number: int, timeout_s: int = 60) -> str | None:
    """Windows takes a few seconds to notice the new FAT32 partition."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rescan()
        letter = disks.boot_partition_letter(disk_number)
        if letter and Path(f"{letter}:/config.txt").exists():
            return letter
        time.sleep(2)
    return None


# --- Path 1: Raspberry Pi Imager CLI ---------------------------------------------


def write_with_imager(
    image: Path,
    disk: Disk,
    imager: Path,
    on_line: Callable[[str], None] | None = None,
    *,
    sha256: str | None = None,
    user_data: Path | None = None,
    network_config: Path | None = None,
) -> None:
    """Drive Raspberry Pi Imager's CLI.

    Flag names here are the real ones, taken from `src/cli.cpp` at tag v2.0.11.1:
    --disable-verify, --enable-writing-system-drives, --sha256, --cache-file,
    --first-run-script, --cloudinit-userdata, --cloudinit-networkconfig,
    --disable-eject, --debug, --quiet, --log-file, --secure-boot-key, then the
    positional source and destination. There is no `--cli` flag and no
    `--disable-telemetry` flag; passing invented options just fails.

    --enable-writing-system-drives is NEVER passed. Imager's own default is to
    refuse non-removable drives, and on this workbench that default is a second
    net under our own gate. Turning it off would remove both at once.

    When user_data / network_config are given, Imager writes the cloud-init seed
    itself as part of the write: it prepends `#cloud-config` to user-data, copies
    network-config verbatim, generates a meta-data with its own instance id, and
    appends ` ds=nocloud;i=<id>` to cmdline.txt.
    """
    disks.assert_writable(disk)
    device = f"\\\\.\\PHYSICALDRIVE{disk.number}"

    cmd: list[str] = [str(imager)]
    # The shipped wrapper's entire body is `start /WAIT rpi-imager.exe --cli %*`,
    # so it supplies --cli itself and, crucially, WAITS. The bare .exe is built as
    # a Windows GUI application: launch it directly and the process returns
    # immediately, so we would "finish" the write before it had started. Pass
    # --cli only in that case, and know that the exit code is then unreliable.
    if imager.suffix.lower() == ".exe":
        cmd.append("--cli")
    if sha256:
        cmd += ["--sha256", sha256]
    if user_data:
        cmd += ["--cloudinit-userdata", str(user_data)]
    if network_config:
        cmd += ["--cloudinit-networkconfig", str(network_config)]
    # Keep the card mounted afterwards so `seed` can still reconcile the boot
    # partition. An ejected card means a physical re-insert for no reason.
    cmd += ["--disable-eject", str(image), device]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        if on_line:
            on_line(line.rstrip())
    code = proc.wait()
    if code != 0:
        raise WriteError(
            f"{imager.name} exited {code}. If it refused the device, do NOT reach for "
            "--enable-writing-system-drives; that is the guard doing its job. Try "
            "running this wizard as Administrator, or write the card with the Imager "
            "GUI and then run `piwiz seed <node>`."
        )


# --- Path 2: native write ---------------------------------------------------------


def write_native(
    image: Path,
    disk: Disk,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    """Raw-write the image to \\\\.\\PhysicalDriveN. Administrator required."""
    if not is_admin():
        raise WriteError(
            "the native writer needs Administrator (it opens the raw device).\n"
            "Either re-run this wizard from an elevated terminal, or install "
            "Raspberry Pi Imager and let the wizard drive that instead."
        )

    image = Path(image)
    if not image.exists():
        raise WriteError(f"{image} does not exist")
    total = image.stat().st_size

    disks.assert_writable(disk)
    if total > disk.size:
        raise WriteError(
            f"image is {human(total)} but the card is only {human(disk.size)} - it will not fit"
        )

    clear_disk(disk)
    # Offline keeps Windows from mounting and writing to anything mid-flash.
    _ps(f"Set-Disk -Number {disk.number} -IsOffline $true")

    device = f"\\\\.\\PhysicalDrive{disk.number}"
    written = 0
    try:
        # Final re-check with the disk in the exact state we are about to write to.
        disks.assert_writable(disks.find_disk(disk.number))
        with image.open("rb") as src, open(device, "r+b", buffering=0) as dst:
            while True:
                block = src.read(CHUNK)
                if not block:
                    break
                if len(block) % SECTOR:
                    # Raw device writes must be sector-aligned; pad the tail.
                    block += b"\0" * (SECTOR - (len(block) % SECTOR))
                dst.write(block)
                written += len(block)
                if progress:
                    progress(min(written, total), total)
            dst.flush()
            os.fsync(dst.fileno())
    except PermissionError as exc:
        raise WriteError(
            f"access denied opening {device}. Run as Administrator, and make sure "
            "no Explorer window or antivirus scan is holding the card."
        ) from exc
    finally:
        try:
            _ps(f"Set-Disk -Number {disk.number} -IsOffline $false")
        except WriteError:
            pass
        rescan()


def verify_written(image: Path, disk: Disk, progress: Callable[[int, int], None] | None = None) -> bool:
    """Read the card back and compare it with the image, byte for byte.

    A write that reported success and produced a card that does not boot is the
    most expensive failure in this whole process - it costs a trip to the rack,
    a monitor, and a keyboard. Reading back a 3 GB image takes about a minute.
    """
    if not is_admin():
        raise WriteError("verification reads the raw device, which needs Administrator")

    image = Path(image)
    total = image.stat().st_size
    device = f"\\\\.\\PhysicalDrive{disk.number}"

    src_hash = hashlib.sha256()
    dst_hash = hashlib.sha256()
    done = 0
    with image.open("rb") as src, open(device, "rb", buffering=0) as dst:
        while done < total:
            want = min(CHUNK, total - done)
            aligned = want + (-want % SECTOR)
            a = src.read(want)
            b = dst.read(aligned)[:want]
            if not a:
                break
            src_hash.update(a)
            dst_hash.update(b)
            done += len(a)
            if progress:
                progress(done, total)
    return src_hash.hexdigest() == dst_hash.hexdigest()


# --- Dispatcher -------------------------------------------------------------------


def write(
    image: Path,
    disk: Disk,
    *,
    prefer: str = "auto",
    progress: Callable[[int, int], None] | None = None,
    on_line: Callable[[str], None] | None = None,
    sha256: str | None = None,
) -> str:
    """Write `image` to `disk`. Returns the name of the path actually used."""
    disks.assert_writable(disk)

    imager = find_imager()
    if prefer in ("auto", "imager") and imager is not None:
        write_with_imager(image, disk, imager, on_line, sha256=sha256)
        return f"rpi-imager ({imager.name})"

    if prefer in ("auto", "native"):
        if not is_admin() and prefer == "auto":
            raise WriteError(
                "no write path available.\n\n"
                + imager_install_hint()
                + "\n\nOr write the card with the Imager GUI now, then run:\n"
                "    piwiz seed <node>\n"
                "which needs no Administrator and does the part that actually matters."
            )
        write_native(image, disk, progress)
        return "native writer"

    raise DiskSafetyError(f"unknown write path {prefer!r}")
