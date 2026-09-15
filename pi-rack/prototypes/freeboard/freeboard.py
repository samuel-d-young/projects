"""Freeboard — will the next job fit where it belongs?

Freeboard is the margin between the waterline and the deck. When it reaches zero you
are not sinking yet, but you have no reserve, and the next wave comes aboard.

THE MEASUREMENT THAT PROMPTED THIS (2026-08-28)

Twelve real wedding jobs on `K:\\Weddings` were measured. Median **278 GB**, mean
399 GB, largest 2,452 GB. Against that:

    K: (M1)            46.8 GB free  -> 0.17 of a wedding
    L: (Video Work)   151.8 GB free  -> 0.55 of a wedding
    V: (easystore)     20.1 GB free  -> 0.07 of a wedding
    ------------------------------------------------------
    combined          218.7 GB free  -> 0.79 of a wedding

**The three volumes that hold client work cannot accept one more job between them.**
There is plenty of room elsewhere — O: has 10.7 TB — but not where the work is filed,
which is why the shortage is invisible until a card will not offload.

That is the entire point of this tool: the question is never "is the disk full", it is
**"will Saturday's job fit in the place it actually goes?"**, and nothing on the machine
answers that today.

WHAT IT DELIBERATELY DOES NOT DO

It does not move, delete, or compress anything, and it never will. Freeing space is a
judgement about client work; this only tells you the judgement is due. Nor does it
extrapolate a fill date — there is no history here to extrapolate from, and inventing a
trend line from one sample is worse than saying nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime

# Measured from K:\Weddings on 2026-08-28: 12 jobs over 20 GB.
# Update these when the measurement is re-run; they are observations, not constants.
JOB_MEDIAN_GB = 277.6
JOB_MEAN_GB = 398.5
JOB_MAX_GB = 2451.8

# Where client work is actually filed. A volume with room that is not on this list
# does not solve the problem, it just means the machine is not out of disk.
WORKING_LABELS = {"M1", "VIDEO WORK", "EASYSTORE"}

GREEN, AMBER, RED, RESET, BOLD, DIM = (
    "\033[92m", "\033[93m", "\033[91m", "\033[0m", "\033[1m", "\033[2m",
)


def enable_ansi() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


@dataclass
class Volume:
    letter: str
    label: str
    total_gb: float
    free_gb: float

    @property
    def is_working(self) -> bool:
        return self.label.strip().upper() in WORKING_LABELS

    @property
    def jobs_free(self) -> float:
        return self.free_gb / JOB_MEDIAN_GB

    @property
    def pct_used(self) -> float:
        return 100.0 * (1 - self.free_gb / self.total_gb) if self.total_gb else 0.0


def volumes() -> list[Volume]:
    """Fixed volumes with a drive letter, via PowerShell so labels come with them."""
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        raise SystemExit("PowerShell not found; Freeboard is Windows-side by design")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$o=@(Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } |"
        "ForEach-Object { [PSCustomObject]@{L=[string]$_.DriveLetter;"
        "Lab=[string]$_.FileSystemLabel;T=[int64]$_.Size;F=[int64]$_.SizeRemaining} });"
        "ConvertTo-Json -InputObject $o -Depth 3 -Compress"
    )
    out = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=120,
    ).stdout.strip()
    data = json.loads(out or "[]")
    if isinstance(data, dict):
        data = [data]
    vols = [
        Volume(
            letter=d["L"],
            label=d.get("Lab") or "",
            total_gb=d["T"] / 1024**3,
            free_gb=d["F"] / 1024**3,
        )
        for d in data
        if d.get("T")
    ]
    return sorted(vols, key=lambda v: v.letter)


def bar(pct: float, width: int = 24) -> str:
    filled = int(round(width * min(pct, 100) / 100))
    return "#" * filled + "." * (width - filled)


def main() -> int:
    enable_ansi()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-gb", type=float, default=JOB_MEDIAN_GB,
                    help=f"size of the job you are about to shoot (default: measured median {JOB_MEDIAN_GB})")
    ap.add_argument("--json", metavar="PATH", help="write the report as JSON")
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    args = ap.parse_args()

    vols = volumes()
    working = [v for v in vols if v.is_working]
    spare = [v for v in vols if not v.is_working and v.free_gb > args.job_gb]

    best = max((v.free_gb for v in working), default=0.0)
    combined = sum(v.free_gb for v in working)
    fits_single = best >= args.job_gb
    fits_combined = combined >= args.job_gb

    if fits_single:
        state, colour = "OK", GREEN
    elif fits_combined:
        state, colour = "TIGHT", AMBER
    else:
        state, colour = "WILL NOT FIT", RED

    if args.quiet:
        print(f"{state}: {best:.0f} GB on the best working volume, job is {args.job_gb:.0f} GB")
        return 0 if fits_single else 1

    W = 68
    print()
    print("=" * W)
    print(f" FREEBOARD  -  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * W)
    print(f" A job of {args.job_gb:.0f} GB needs somewhere to land.")
    print(f" {DIM}(measured: median {JOB_MEDIAN_GB:.0f} GB, mean {JOB_MEAN_GB:.0f} GB, "
          f"largest {JOB_MAX_GB:.0f} GB){RESET}")
    print()

    print(f" {BOLD}WHERE CLIENT WORK IS FILED{RESET}")
    print(" " + "-" * (W - 2))
    for v in working:
        c = GREEN if v.free_gb >= args.job_gb else (AMBER if v.free_gb >= args.job_gb / 2 else RED)
        print(f"  {v.letter}: {v.label:<12} [{bar(v.pct_used)}] {v.pct_used:5.1f}% used  "
              f"{c}{v.free_gb:8.1f} GB free{RESET}  = {v.jobs_free:4.2f} jobs")
    print(f"  {'':4}{'COMBINED':<12} {' ' * 26} {colour}{combined:8.1f} GB free{RESET}"
          f"  = {combined / JOB_MEDIAN_GB:4.2f} jobs")

    print()
    print(f" {BOLD}VERDICT{RESET}   {colour}{state}{RESET}")
    if fits_single:
        room = max(working, key=lambda v: v.free_gb)
        print(f"  The job fits on {room.letter}: ({room.label}) with "
              f"{room.free_gb - args.job_gb:.0f} GB to spare.")
    else:
        print("  No single volume that holds client work can take this job.")
        if fits_combined:
            print("  It fits only if you split it across volumes - which is how a job ends up")
            print("  in two places and neither is the whole thing.")
        else:
            print(f"  It does not fit even if you combine them "
                  f"({combined:.0f} GB free vs {args.job_gb:.0f} GB needed).")

    if spare:
        print()
        print(f" {BOLD}ROOM EXISTS, BUT NOT WHERE THE WORK GOES{RESET}")
        print(" " + "-" * (W - 2))
        for v in sorted(spare, key=lambda v: -v.free_gb)[:4]:
            print(f"  {v.letter}: {v.label:<18} {v.free_gb:8.0f} GB free "
                  f"= {v.free_gb / JOB_MEDIAN_GB:3.0f} jobs")
        print(f"  {DIM}Using these means either moving the filing convention or accepting")
        print(f"  that client work lives on a drive named for something else.{RESET}")

    print()
    print("=" * W)
    print(" Freeboard moved nothing and deleted nothing. Freeing space is a judgement")
    print(" about client work; this only tells you that judgement is now due.")
    print("=" * W)
    print()

    if args.json:
        payload = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "job_gb": args.job_gb,
            "state": state,
            "fits_on_single_working_volume": fits_single,
            "working_free_gb": round(combined, 1),
            "volumes": [asdict(v) | {"is_working": v.is_working} for v in vols],
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"wrote {args.json}")

    return 0 if fits_single else 1


if __name__ == "__main__":
    raise SystemExit(main())
