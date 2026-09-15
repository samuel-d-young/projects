# Ledger — prototype

A read-only reconciler that answers *"where is this job, and is it safe?"*

```bash
python ledger.py
```

Nothing to install. Standard library only. It moves nothing and writes nothing except
an optional `--json` report.

---

## Why it exists

On 2026-08-28 a scan of Resolve's own project index found **ten projects whose gallery
paths point at drive `F:`, which is not mounted**. All ten were last modified between
February and June 2024. They include two weddings (`Stacey & Mark`, `bREE & eTHAN`) and
paid commercial work (`BM Motorcycles`, `Reuben Dentist Training Video IG`).

Nobody noticed for two years, because nothing on the machine was looking.

That is the failure this makes impossible to miss.

### But be careful what you claim

A follow-up check matched those ten project names against every folder two levels deep
on all nine mounted volumes. **Six have a plausible media folder somewhere; four do
not:**

| Project | Candidate media folder |
|---|---|
| Harry Potter Experience | `L:\Youtube\Harry Potter Experience` |
| BM Motorcycles | `L:\BM Motorcycles` |
| Orchard Youth | `L:\Boronia\Orchard Youth` |
| Training Night | `L:\Boronia\Volunteer Night` *(weak match)* |
| Stacey & Mark | `K:\Video Work\Mark` *(weak match)* |
| Untitled Project 2024-02-22 | `V:\2024` *(weak match)* |
| **Spirit of the Games Award** | **nothing found** |
| **Volunteers Night** | **nothing found** |
| **bREE & eTHAN** | **nothing found — and this is a wedding** |
| **Reuben Dentist Training Video IG** | **nothing found** |

So the honest headline is *not* "ten projects are lost". It is: **ten projects have a
dead gallery path, and four of them have no obvious media on any mounted drive — one of
which is a wedding.** That is twenty minutes of checking, tonight, not a catastrophe.

Getting that distinction right is the whole design brief. A tool that cries "lost!"
about six projects that are fine is a tool nobody runs twice.

## What it actually found, first run

```
 132 Resolve projects | 34 job folders | volumes mounted: CDEHIKLMNOVZ

 ** 10 PROJECTS REFERENCE A VOLUME THAT IS NOT MOUNTED: F: **
   2024-06-14  Spirit of the Games Award       F:   1 timelines
   2024-05-16  Stacey & Mark                   F:   3 timelines
   2024-05-03  Volunteers Night                F:   1 timelines
   ... 7 more

 JOB FOLDERS
   34 folders across 3 roots
   25 have no matching Resolve project
   8 contain ONLY delivered files - no project, no source
     Monique & Liam       140 file(s)
     Oceanlord             94 file(s)
     Samantha & Micheal    71 file(s)
     PremRest              28 file(s)

 LOOSE MEDIA AT THE ROOT OF A YEAR FOLDER (belongs to no job)
   2018:    59 loose files alongside 7 folders
   2025:    38 loose files alongside 13 folders
   2026:   145 loose files alongside 9 folders
   260 files in total with no job association.

 PROTECTION (resolve-sync)
   backend=drive  auto_sync=True  watching=0 project(s)  last written 2026-07-29

   ** AUTO-SYNC IS ON AND ITS WATCH LIST IS EMPTY. **

   Of the 12 most recently modified projects, 9 are in no store:
     2026-08-26  NZ 360 Footage
     2026-08-20  R2W & R2B 20.8
     2026-08-07  Lynbrook Dental Care
     ... 6 more
```

That last section is the one that matters most, and it is the reason a reconciler
beats a backup report. `auto_sync: true` and `synced_projects: []` are **independent
settings**. Together they mean the interface says syncing is on while the watch list is
empty — nothing errors, nothing warns, and nothing is protected. Only a tool that
compares *what exists* against *what is protected* can see it.

Fixing it is two minutes of ticking boxes in resolve-sync's own UI.

## How it works

It reads three sources that already exist and reports where they **disagree**:

1. **Resolve's `ProjectMetadataCache/*.db`** — every project's name, dates, resolution,
   timeline count and gallery volume. Opened `mode=ro&immutable=1`, so Resolve's own
   file is never touched and it works with Resolve closed.
2. **The job folders** on `K:\Weddings`, `K:\Video Work`, `K:\Dental Story` — one level
   deep only.
3. **Which drive letters are mounted right now.**

Matching project names to folder names is deliberately fuzzy (`Abby & Stephen` in
Resolve is `Abigail and Stephen` on disk) and deliberately **not authoritative**. The
output is a worklist for a human, never a verdict — which matters, because the eventual
version of this decides whether 400 GB can be deleted.

## Deliberate limits

- **Shallow scans only.** A recursive walk of a 13 TB volume is minutes of spinning
  disk for information it does not need. It therefore reports *file counts*, not sizes.
- **No hashing.** Proving two copies are identical is the next step, not this one — and
  no Pi here has ARMv8 crypto extensions, so that work belongs on the workbench.
- **It cannot tell you a drive is lost**, only that it is not here. `F:` may be
  unplugged, re-lettered, or gone. Distinguishing those is a human question.
- **Out-of-scope databases and volumes are excluded by name** and never appear in the
  report.

## What it would take to become the real thing

This prototype proves the reconciliation is possible and useful. A finished version adds:

- **Sizes**, so "you could recover 400 GB by archiving this job" is answerable.
- **Content hashes** with a stored manifest, so *identical* can be proven rather than
  assumed — the four-proof GREEN verdict from `docs/PLAN.md`.
- **The offsite leg**, proven by stored hash and never by "a file of that name exists
  in the bucket".
- **A schedule and a history**, so drift is caught within a day instead of two years.
  That is the part that wants an always-on box rather than a script someone remembers
  to run.

The Pi's role in the finished version is the database, the web UI and the scheduler.
**The volume walk and the hashing run on the workbench against local NTFS** — one pass
over ~49 TiB through a single Pi NIC is over 120 hours.
