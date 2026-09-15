"""Renders of the exported STLs, drawn with robot/cad/render.py's painter.

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\shots.py

Writes docs/nfc-cassette.png: the player with a cassette in the bay, and the
same parts exploded so the stack is visible. Honest renders - they draw the
exported meshes, not an impression.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT.parent.parent / "robot" / "cad"))
import params  # noqa: E402
from render import _camera_basis, shade_multi  # noqa: E402

STL = ROOT / "stl"
OUT = ROOT / "docs"

BASE = (0.28, 0.30, 0.34)
TOP = (0.80, 0.80, 0.78)
TRAY = (0.93, 0.86, 0.62)
LID = (0.96, 0.92, 0.75)


def load(name: str, dx=0.0, dy=0.0, dz=0.0) -> trimesh.Trimesh:
    m = trimesh.load(str(STL / f"{name}.stl"))
    m.apply_translation([dx, dy, dz])
    return m


def scene(D: dict, explode: float):
    tray_z = D["bay_floor_z"] + explode * 2
    return [
        (load("player_base"), BASE),
        (load("player_top", dz=explode), TOP),
        (load("cassette_tray", dy=D["bay_cy"], dz=tray_z), TRAY),
        (load("cassette_lid", dy=D["bay_cy"], dz=tray_z + D["lid_bottom_z"] + explode * 0.6), LID),
    ]


def frame(ax, items, azim, elev):
    shade_multi(ax, items, azim, elev)
    # the painter draws antialiased triangles with no edges, which leaves hairline
    # seams between them; giving each triangle an edge in its own colour closes them
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


def main() -> None:
    D = params.derive(params.nominal())
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), dpi=100)
    frame(axes[0], scene(D, 0.0), azim=35, elev=28)
    axes[0].set_title(f"assembled - {D['L']:.0f} x {D['W']:.0f} x {D['H']:.0f} mm, tape stands "
                      f"{D['proud']:.0f} mm proud", fontsize=11)
    frame(axes[1], scene(D, 28.0), azim=35, elev=28)
    axes[1].set_title("exploded - base with the electronics, top slab with the bay, tray + lid", fontsize=11)
    fig.suptitle("NFC cassette player - PN532 under the bay floor, D1 mini beside it, four M3 screws",
                 fontsize=14, fontweight="bold")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "nfc-cassette.png", dpi=130, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT / 'nfc-cassette.png'}")


if __name__ == "__main__":
    main()
