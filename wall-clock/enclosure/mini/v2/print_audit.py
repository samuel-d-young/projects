#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
print_audit.py - measure what each STL actually costs to print.

WHY THIS EXISTS
---------------
check3_print.py answers "is this printable" - a pass/fail on overhangs,
bridges and thin walls. It does not answer "is this EXPENSIVE", and those are
different questions: a part can pass every printability check and still waste
half a spool because it is solid where it could be a shell, or tall where it
could be flat.

This measures the cost side, per file, so a change can be argued about with
numbers instead of adjectives:

  material     mesh volume in cm3, which is what you pay for
  bbox         footprint and height. Height drives time far harder than
               volume does - every layer pays the same fixed cost in travel
               and acceleration regardless of how little is on it
  layers       at LAYER height, the count the slicer will produce
  support      downward-facing area steeper than the printer can hold up,
               split into what a slicer would actually support
  flat-down    area lying flat on the plate. Big is good: it is adhesion,
               and it is the one surface that needs no perimeters above it

It reports, it does not judge. The verdict lines at the end are the only
opinion, and they are thresholds you can move.

USAGE
    python print_audit.py                  # every STL here
    python print_audit.py --glob '*base*'  # a subset
    python print_audit.py --json out.json  # machine-readable, for diffing
"""

import argparse
import glob
import json
import math
import os

import numpy as np
import trimesh

LAYER = 0.20          # matches check3_print.py
NOZZLE = 0.40
SLOPE_MIN = 45.0      # a face shallower than this wants support
BED = (256.0, 256.0)  # a common 256 bed; only used to flag "will not fit"


def audit(path):
    # process=False then merge_vertices(), exactly as check1_topology.py does.
    # Loading with process=False alone leaves every triangle with its own three
    # vertices, so nothing is topologically joined and EVERY mesh reports as
    # not watertight and has no volume. That is an artefact of the loader, not
    # a defect in the file.
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.merge_vertices()

    ext = m.bounding_box.extents
    # Face normals and areas, used for every angular measure below.
    n = m.face_normals
    a = m.area_faces
    nz = n[:, 2]

    # Downward-facing area, by how steep it is. A face pointing straight down
    # (nz = -1) is a flat ceiling and gets bridged; a face at exactly SLOPE_MIN
    # is the boundary the slicer will start supporting below.
    down = nz < -1e-6
    # angle from the horizontal plane of the face itself
    with np.errstate(invalid="ignore"):
        slope = np.degrees(np.arcsin(np.clip(-nz, 0.0, 1.0)))
    needs = down & (slope < SLOPE_MIN) & (slope > 1.0)   # sloped, too shallow
    flat_ceiling = down & (slope >= 89.0)                # true bridges
    flat_down = down & (slope >= 89.0) & (
        m.triangles_center[:, 2] < m.bounds[0][2] + LAYER * 1.5)

    vol = float(m.volume) / 1000.0 if m.is_volume else float("nan")

    return {
        "file": os.path.basename(path),
        "volume_cm3": vol,
        "bbox": [float(x) for x in ext],
        "height": float(ext[2]),
        "layers": int(math.ceil(ext[2] / LAYER)),
        "area_cm2": float(m.area) / 100.0,
        "support_cm2": float(a[needs].sum()) / 100.0,
        "bridge_cm2": float(a[flat_ceiling].sum()) / 100.0,
        "plate_cm2": float(a[flat_down].sum()) / 100.0,
        "watertight": bool(m.is_watertight),
        "faces": int(len(m.faces)),
        "fits_bed": bool(ext[0] <= BED[0] and ext[1] <= BED[1]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="*.stl")
    ap.add_argument("--json")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.dir, args.glob)))
    rows = []
    for p in paths:
        try:
            rows.append(audit(p))
        except Exception as exc:                     # noqa: BLE001
            print("  !! %-44s %s" % (os.path.basename(p), exc))

    rows.sort(key=lambda r: -(r["volume_cm3"] if r["volume_cm3"] == r["volume_cm3"] else 0))

    print("%-42s %8s %7s %6s %8s %8s %8s" %
          ("file", "vol cm3", "height", "layers", "supp cm2", "bridge", "plate"))
    print("-" * 92)
    tot_v = tot_s = 0.0
    for r in rows:
        v = r["volume_cm3"]
        tot_v += 0 if v != v else v
        tot_s += r["support_cm2"]
        print("%-42s %8.1f %7.1f %6d %8.2f %8.2f %8.2f%s" %
              (r["file"], v, r["height"], r["layers"], r["support_cm2"],
               r["bridge_cm2"], r["plate_cm2"],
               "" if r["watertight"] else "   NOT WATERTIGHT"))
    print("-" * 92)
    print("%-42s %8.1f %7s %6s %8.2f" % ("TOTAL", tot_v, "", "", tot_s))

    print("\nthe expensive ones, by material:")
    for r in rows[:5]:
        print("   %-40s %6.1f cm3   %5d layers" %
              (r["file"], r["volume_cm3"], r["layers"]))

    sup = sorted(rows, key=lambda r: -r["support_cm2"])
    print("\nthe ones a slicer would put support under:")
    any_sup = False
    for r in sup[:6]:
        if r["support_cm2"] > 0.5:
            any_sup = True
            print("   %-40s %6.2f cm2 of shallow downward face" %
                  (r["file"], r["support_cm2"]))
    if not any_sup:
        print("   none above 0.5 cm2 - nothing here needs support")

    bad = [r for r in rows if not r["watertight"]]
    if bad:
        print("\nNOT WATERTIGHT (a slicer will guess at these):")
        for r in bad:
            print("   %s" % r["file"])

    if args.json:
        json.dump(rows, open(args.json, "w"), indent=2)
        print("\nwrote %s" % args.json)


if __name__ == "__main__":
    main()
