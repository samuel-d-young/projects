"""Ledger — a read-only reconciler that answers "where is this job, and is it safe?"

WHY THIS EXISTS

On 2026-08-28 a scan of Resolve's own project index found ten projects whose gallery
paths point at drive `F:`, which is not mounted. All ten were last modified between
February and June 2024, and they include two weddings and paid commercial work. Nobody
noticed for two years.

That is the failure this tool is built to make impossible to miss. It is not a backup
tool and it moves nothing. It reads three sources that already exist and tells you where
they disagree:

  1. Resolve's own ProjectMetadataCache SQLite databases — names, dates, timeline
     counts, gallery volumes — readable without Resolve running.
  2. The job folders on disk.
  3. Which volumes are actually mounted right now.

STRICTLY READ-ONLY. It opens every database with `mode=ro&immutable=1`, never writes
outside its own report, and never recurses into media directories — a deep walk of a
13 TB volume is minutes of spinning disk for information this tool does not need.

SCOPE NOTE: databases and volumes belonging to work that is out of scope for this
workbench are skipped by name via EXCLUDE, and never appear in the report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import string
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

RESOLVE_CACHE = Path(
    os.path.expandvars(
        r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Resolve Disk Database"
        r"\Resolve Projects\Users\guest\ProjectMetadataCache"
    )
)

# Job folders worth reconciling. Shallow listing only.
JOB_ROOTS = [
    Path(r"K:\Weddings"),
    Path(r"K:\Video Work"),
    Path(r"K:\Dental Story"),
]

# Year folders are camera-card dumping grounds rather than job folders, so they are
# reported separately: loose media at their root belongs to no job at all.
# NOTE the trailing separator. Path("K:") is DRIVE-RELATIVE on Windows - it means
# "the current directory on K:", not the root of K:. Path("K:") / "2026" yields
# WindowsPath("K:2026"), which silently matches nothing. Path("K:/") is the root.
YEAR_ROOTS = [Path("K:/") / str(y) for y in range(2016, 2027)]

# Anything whose name matches is skipped entirely and never reported on.
EXCLUDE = re.compile(r"anzuk", re.I)

DELIVERABLE_EXT = {".mp4", ".mov", ".mxf", ".m4v"}
MEDIA_EXT = DELIVERABLE_EXT | {".jpg", ".jpeg", ".png", ".dng", ".arw", ".cr2", ".raf", ".wav", ".mp3"}


def mounted_letters() -> set[str]:
    return {d for d in string.ascii_uppercase if os.path.exists(d + ":\\")}


@dataclass
class Project:
    name: str
    database: str
    modified: str
    created: str
    width: int
    height: int
    fps: float
    timelines: int
    gallery: str

    @property
    def gallery_volume(self) -> str:
        g = (self.gallery or "").strip()
        return g[0].upper() if len(g) > 1 and g[1] == ":" else ""

    @property
    def is_vertical(self) -> bool:
        return bool(self.height and self.width and self.height > self.width)


@dataclass
class Job:
    folder: str
    root: str
    files: int = 0
    subdirs: int = 0
    deliverables: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)


def read_projects() -> list[Project]:
    """Every Resolve project across every database, minus excluded ones."""
    out: list[Project] = []
    if not RESOLVE_CACHE.is_dir():
        return out

    dbs: list[tuple[str, Path]] = []
    root_db = RESOLVE_CACHE / "Metadata.db"
    if root_db.exists():
        dbs.append(("(default)", root_db))
    for child in sorted(RESOLVE_CACHE.iterdir()):
        if child.is_dir() and (child / "Metadata.db").exists():
            if EXCLUDE.search(child.name):
                continue
            dbs.append((child.name, child / "Metadata.db"))

    for label, path in dbs:
        try:
            con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True)
            rows = con.execute(
                "SELECT key,modDateTime,createDateTime,width,height,fps,numTimelines,galleryPath"
                " FROM project_metadata"
            ).fetchall()
            con.close()
        except sqlite3.Error:
            continue
        for k, mod, cre, w, h, fps, tl, gal in rows:
            if EXCLUDE.search(k or ""):
                continue
            out.append(
                Project(
                    name=k or "(unnamed)",
                    database=label,
                    modified=(mod or "")[:19],
                    created=(cre or "")[:19],
                    width=int(w or 0),
                    height=int(h or 0),
                    fps=float(fps or 0),
                    timelines=int(tl or 0),
                    gallery=gal or "",
                )
            )
    return out


def scan_jobs() -> list[Job]:
    """Shallow scan: one level into each job root, and one level inside each job."""
    jobs: list[Job] = []
    for root in JOB_ROOTS:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir() or EXCLUDE.search(entry.name):
                continue
            job = Job(folder=entry.name, root=str(root))
            try:
                for child in entry.iterdir():
                    if child.is_dir():
                        job.subdirs += 1
                    else:
                        job.files += 1
                        if child.suffix.lower() in DELIVERABLE_EXT:
                            job.deliverables.append(child.name)
            except (PermissionError, OSError):
                pass
            jobs.append(job)
    return jobs


def scan_loose_media() -> list[tuple[str, int, int]]:
    """Loose media sitting at the root of a year folder — belonging to no job."""
    out = []
    for root in YEAR_ROOTS:
        if not root.is_dir():
            continue
        loose = 0
        folders = 0
        try:
            for child in root.iterdir():
                if child.is_dir():
                    folders += 1
                elif child.suffix.lower() in MEDIA_EXT:
                    loose += 1
        except (PermissionError, OSError):
            continue
        if loose or folders:
            out.append((root.name, loose, folders))
    return out


RESOLVE_SYNC_DIR = Path(os.path.expandvars(r"%APPDATA%\ResolveSync"))


def read_sync_state() -> tuple[dict, set[str], bool, str]:
    """What resolve-sync is actually protecting, as opposed to what it says it is.

    Returns (config, set of project names present in any backend's state,
    auto_sync flag, last-written date).

    The distinction this exists to expose: `auto_sync: true` and
    `synced_projects: []` are independent settings, and together they mean the UI
    reports syncing is on while the watch list is empty. Nothing is wrong, nothing
    errors, and nothing is being protected.
    """
    cfg_path = RESOLVE_SYNC_DIR / "config.json"
    state_path = RESOLVE_SYNC_DIR / "state.json"
    if not cfg_path.exists():
        return {}, set(), False, ""

    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, set(), False, ""

    pushed: set[str] = set()
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            for backend in state.values():
                if isinstance(backend, dict):
                    pushed.update(backend.keys())
        except (OSError, json.JSONDecodeError):
            pass

    when = datetime.fromtimestamp(cfg_path.stat().st_mtime).strftime("%Y-%m-%d")
    return cfg, pushed, bool(cfg.get("auto_sync")), when


def normalise(s: str) -> str:
    """Lowercase alphanumeric words, with '&' and 'and' unified — because a job is
    'Abigail and Stephen' on disk and 'Abby & Stephen' in Resolve."""
    s = s.lower().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", s))


def tokens(s: str) -> set[str]:
    stop = {"and", "the", "video", "wedding", "final", "edit", "project", "v1", "v2", "2024", "2025", "2026"}
    return {t for t in normalise(s).split() if t not in stop and len(t) > 2}


def match_score(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def reconcile(projects: list[Project], jobs: list[Job], threshold: float = 0.34):
    """Associate projects with job folders by name. Deliberately fuzzy and deliberately
    NOT authoritative — the output is a worklist for a human, not a decision."""
    for p in projects:
        best, score = None, 0.0
        for j in jobs:
            s = match_score(p.name, j.folder)
            if s > score:
                best, score = j, s
        if best and score >= threshold:
            best.projects.append(p.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", metavar="PATH", help="also write the full report as JSON")
    args = ap.parse_args()

    live = mounted_letters()
    projects = read_projects()
    jobs = scan_jobs()
    reconcile(projects, jobs)
    loose = scan_loose_media()

    W = 78
    def rule(ch="-"):
        print(ch * W)

    print()
    rule("=")
    print(f" LEDGER  -  {datetime.now():%Y-%m-%d %H:%M}")
    rule("=")
    print(f" {len(projects)} Resolve projects | {len(jobs)} job folders | volumes mounted: "
          f"{''.join(sorted(live))}")

    # --- 1. the headline: work on volumes that are not here ---------------------
    orphaned = [p for p in projects if p.gallery_volume and p.gallery_volume not in live]
    print()
    rule()
    if orphaned:
        vols = sorted({p.gallery_volume for p in orphaned})
        print(f" ** {len(orphaned)} PROJECTS REFERENCE A VOLUME THAT IS NOT MOUNTED: "
              f"{', '.join(v + ':' for v in vols)} **")
        rule()
        for p in sorted(orphaned, key=lambda p: p.modified, reverse=True):
            print(f"   {p.modified[:10]}  {p.name[:44]:44} {p.gallery_volume}:  "
                  f"{p.timelines:>3} timelines")
        print()
        print("   These are not necessarily lost - the drive may simply be unplugged or")
        print("   re-lettered. But nothing on this machine currently knows which.")
    else:
        print(" All project gallery volumes are mounted.")

    # --- 2. jobs with deliverables but no project, and vice versa ----------------
    print()
    rule()
    print(" JOB FOLDERS")
    rule()
    no_project = [j for j in jobs if not j.projects]
    delivered_only = [j for j in jobs if j.deliverables and not j.subdirs]
    print(f"   {len(jobs)} folders across {len(JOB_ROOTS)} roots")
    print(f"   {len(no_project)} have no matching Resolve project")
    print(f"   {len(delivered_only)} contain ONLY delivered files - no project, no source")
    if delivered_only:
        print()
        print("   Delivered-only (the edit that made these lives somewhere else):")
        for j in delivered_only[:12]:
            print(f"     {j.folder[:40]:40} {len(j.deliverables)} file(s)")

    # --- 3. loose media in year folders ------------------------------------------
    if loose:
        print()
        rule()
        print(" LOOSE MEDIA AT THE ROOT OF A YEAR FOLDER (belongs to no job)")
        rule()
        total = 0
        for name, n, folders in loose:
            if n:
                print(f"   {name}:  {n:>4} loose files alongside {folders} folders")
                total += n
        print(f"   {total} files in total with no job association.")

    # --- 3b. is any of it actually protected? -------------------------------------
    cfg, pushed, auto_sync, cfg_when = read_sync_state()
    if cfg:
        watch = cfg.get("synced_projects") or []
        print()
        rule()
        print(" PROTECTION (resolve-sync)")
        rule()
        print(f"   backend={cfg.get('backend','?')}  auto_sync={auto_sync}  "
              f"watching={len(watch)} project(s)  config last written {cfg_when}")
        if auto_sync and not watch:
            print()
            print("   ** AUTO-SYNC IS ON AND ITS WATCH LIST IS EMPTY. **")
            print("   The UI reports syncing is enabled. Nothing is being pushed.")
            print("   These two settings are independent, so nothing errors and")
            print("   nothing warns - it just quietly protects nothing.")
        if pushed:
            print(f"\n   {len(pushed)} project(s) have been pushed at some point:")
            for name in sorted(pushed):
                print(f"     - {name}")
        # Recent work that has never reached any store is the number that matters.
        recent = sorted([p for p in projects if p.modified], key=lambda p: p.modified,
                        reverse=True)[:12]
        never = [p for p in recent if not any(match_score(p.name, q) >= 0.5 for q in pushed)]
        if never:
            print(f"\n   Of the 12 most recently modified projects, {len(never)} are in no store:")
            for p in never[:8]:
                print(f"     {p.modified[:10]}  {p.name[:48]}")

    # --- 4. what the ledger can say about the recent stuff ------------------------
    print()
    rule()
    print(" MOST RECENT WORK")
    rule()
    for p in sorted([p for p in projects if p.modified], key=lambda p: p.modified, reverse=True)[:10]:
        mark = "!" if p.gallery_volume and p.gallery_volume not in live else " "
        shape = "vertical" if p.is_vertical else f"{p.width}x{p.height}"
        print(f"  {mark} {p.modified[:10]}  {p.name[:38]:38} {shape:>9}  "
              f"{p.timelines:>3}tl  [{p.database}]")

    print()
    rule("=")
    print(" This tool moved nothing and wrote nothing. It only says where the three")
    print(" sources disagree. Every line above is a question for a human, not a verdict.")
    rule("=")
    print()

    if args.json:
        payload = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "mounted": sorted(live),
            "projects": [asdict(p) for p in projects],
            "jobs": [asdict(j) for j in jobs],
            "orphaned": [p.name for p in orphaned],
            "loose_media": [{"year": y, "loose": n, "folders": f} for y, n, f in loose],
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
