"""Renders of the vertical-slot player from its exported STLs.

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\shots_slot.py

Writes docs/nfc-cassette-slot.png: the tape standing in the player from the
front-left, the same from behind so the lid and its openings show, and the
parts exploded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from trimesh.transformations import rotation_matrix  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT.parent.parent / "robot" / "cad"))
import params  # noqa: E402
from render import _camera_basis, shade_multi  # noqa: E402

STL = ROOT / "stl"
OUT = ROOT / "docs"
BODY = (0.30, 0.32, 0.36)
LID = (0.55, 0.56, 0.58)
TRAY = (0.93, 0.86, 0.62)
TLID = (0.96, 0.92, 0.75)


def load(name, transform=None, dx=0.0, dy=0.0, dz=0.0):
    m = trimesh.load(str(STL / f"{name}.stl"))
    if transform is not None:
        m.apply_transform(transform)
    m.apply_translation([dx, dy, dz])
    return m


def tape(D, lift=0.0, dz_extra=0.0):
    """Tray + lid stood on the long edge: rotate the flat cassette +90 deg about X so
    its thickness runs along -Y (lid to the front) and its height along Z."""
    R = rotation_matrix(np.pi / 2, [1, 0, 0])
    y_back = D["y_slot1"] - D["s_slot_clr"]      # card side against the back of the slot
    z0 = D["s_plate_top_z"] + 0.3 + D["cassette_w"] / 2 + lift + dz_extra
    tr = load("cassette_tray", R, dy=y_back, dz=z0)
    li = load("cassette_lid", R, dy=y_back - D["lid_bottom_z"], dz=z0)
    return [(tr, TRAY), (li, TLID)]


KNOB = (0.16, 0.16, 0.17)


def knobs(D, out=0.0):
    """The two glued knobs, stood in their recesses on the front face (rotated so
    their axis points forward, -Y). `out` pulls them off the face for the explosion."""
    R = rotation_matrix(np.pi / 2, [1, 0, 0])          # knob +Z -> -Y
    face = -D["s_W"] / 2
    items = []
    for name, (cx, cz) in (("knob_big", D["k_knob_big_c"]), ("knob_small", D["k_knob_small_c"])):
        items.append((load(name, R, dx=cx, dy=face + D["k_recess"] - out, dz=cz), KNOB))
    return items


def scene(D, explode=0.0):
    items = [(load("slot_lid", dz=-explode), LID), (load("slot_body"), BODY)]
    items += knobs(D, out=explode * 0.5)
    items += tape(D, lift=explode * 1.6)
    return items


def frame(ax, items, azim, elev):
    shade_multi(ax, items, azim, elev)
    for coll in ax.collections:
        coll.set_edgecolor(coll.get_facecolor())
        coll.set_linewidth(0.5)
    basis = _camera_basis(azim, elev)
    pts = np.concatenate([m.vertices for m, _ in items]) @ basis.T
    lo, hi = pts[:, :2].min(axis=0), pts[:, :2].max(axis=0)
    pad = 0.06 * (hi - lo).max()
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    D = params.derive(params.nominal())
    fig, axes = plt.subplots(1, 3, figsize=(21, 7.5), dpi=100)
    frame(axes[0], scene(D), azim=-35, elev=22)
    axes[0].set_title(f"in use - {D['s_L']:.0f} x {D['s_W']:.0f} x {D['s_H']:.0f} mm, tape stands {D['s_proud']:.0f} mm out of the top", fontsize=11)
    frame(axes[1], scene(D), azim=0, elev=8)
    axes[1].set_title("straight on - knobs, counter window, REC lamp, transport keys, LED, speaker grille", fontsize=11)
    frame(axes[2], scene(D, explode=30.0), azim=-35, elev=22)
    axes[2].set_title("exploded - lid drops away, tape lifts out of the top", fontsize=11)
    fig.suptitle("NFC cassette player, slot version - PN532 upright behind the slot, D1 mini on the lid", fontsize=14, fontweight="bold")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "nfc-cassette-slot.png", dpi=130, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT / 'nfc-cassette-slot.png'}")


if __name__ == "__main__":
    main()
