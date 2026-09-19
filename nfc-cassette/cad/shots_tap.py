"""Renders of the tap player from its exported STLs.

    K:\\Claude\\robot\\.venv\\Scripts\\python.exe cad\\shots_tap.py

Writes docs/nfc-cassette-tap.png: a cartridge being tapped on the top, the
face straight on, and the parts exploded the way they actually come apart -
the lid drops, and only then can the fascia slide down out of its channel.

The explosion is not decorative. It is the assembly order read backwards, and
on this machine that order is the whole design: the face has no fastener of
its own, so the lid is what holds it in, and the lid has to come off first.
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
FACE = (0.22, 0.24, 0.28)
CART = (0.80, 0.34, 0.30)
CBACK = (0.62, 0.26, 0.23)
KNOB = (0.16, 0.16, 0.17)
DIFF = (0.94, 0.94, 0.96)
# the four arcs of the contactless mark, in the four colours they print in
MARK = [(0.96, 0.78, 0.22), (0.92, 0.55, 0.20), (0.85, 0.32, 0.26), (0.55, 0.22, 0.30)]


def load(name, transform=None, dx=0.0, dy=0.0, dz=0.0):
    m = trimesh.load(str(STL / f"{name}.stl"))
    if transform is not None:
        m.apply_transform(transform)
    m.apply_translation([dx, dy, dz])
    return m


def cartridge(D, lift=0.0):
    """A cartridge lying on the tap pad, label up, bevel at the back left.

    The back plate is built in its print orientation, spigot UP, and installs
    turned over - so it is turned over here too. Rendering it the way it is
    built is what showed the spigot sitting on top of the cartridge like a
    doorknob, which is how the handedness came to light.
    """
    z0 = D["s_H"] + 0.3 + lift
    flip = rotation_matrix(np.pi, [1, 0, 0])
    items = [(load("cart_shell", dx=D["t_pad_cx"], dy=D["t_pad_cy"], dz=z0), CART)]
    items.append((load("cart_back", flip, dx=D["t_pad_cx"], dy=D["t_pad_cy"],
                       dz=z0 + D["cart_h"] + lift * 0.35), CBACK))
    return items


def marks(D, out=0.0):
    """The mark's arcs, in their recesses in the top face."""
    items = []
    for i in range(len(D["t_mark_r"])):
        items.append((load(f"tap_mark_{i + 1}", dx=D["t_pn_cx"], dy=D["t_pn_cy"],
                           dz=D["s_H"] - D["t_mark_t"] + out), MARK[i % len(MARK)]))
    return items


def front_bits(D, out=0.0):
    """Knobs and the dial's diffuser, which live on the fascia, not the body."""
    R = rotation_matrix(np.pi / 2, [1, 0, 0])          # +Z -> -Y
    face = -D["s_W"] / 2
    items = []
    for name, (cx, cz) in (("knob_big", D["k_knob_big_c"]), ("knob_small", D["k_knob_small_c"])):
        items.append((load(name, R, dx=cx, dy=face + D["k_recess"] - out, dz=cz), KNOB))
    cx, cz = D["k_vu_c"]
    items.append((load("vu_diffuser", R, dx=cx, dy=face + D["k_dimple"] - out, dz=cz), DIFF))
    return items


def scene(D, explode=0.0, cart=True):
    """Taken apart in the order it comes apart: the lid drops first, and only
    then can the fascia slide down out of its channel and away from the face."""
    items = [(load("tap_lid", dz=-explode), LID),
             (load("tap_fascia", dy=-explode * 0.9, dz=-explode * 1.5), FACE),
             (load("tap_body"), BODY)]
    items += front_bits(D, out=explode * 0.5)
    items += marks(D, out=explode * 0.6)
    if cart:
        items += cartridge(D, lift=explode * 1.5)
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
    # az = 0 puts the eye on +X, so the face at -Y is straight on at az = -90.
    # Getting this wrong is quiet: the body is near enough symmetrical that a
    # view of the BACK reads as a plausible render of the front until you
    # notice there is nothing on it.
    D = params.derive(params.nominal())
    fig, axes = plt.subplots(1, 4, figsize=(28, 7.4), dpi=100)
    frame(axes[0], scene(D), azim=-35, elev=26)
    axes[0].set_title(
        f"tap it  -  {D['s_L']:.0f} x {D['s_W']:.0f} x {D['s_H']:.0f} mm, cartridge "
        f"{D['cart_l']:.0f} x {D['cart_w']:.0f},\ntag {D['t_antenna_to_tag']:.1f} mm "
        "off the antenna", fontsize=11, pad=14)
    frame(axes[1], scene(D, cart=False), azim=-90, elev=2)
    axes[1].set_title(
        "the face, which comes off  -  knobs, counter window, REC lamp,\n"
        "transport keys, LED, and the VU dial that is now the only signal",
        fontsize=11, pad=14)
    frame(axes[2], scene(D, cart=False), azim=-90, elev=86)
    axes[2].set_title(
        "the top  -  no dish, because these are tapped, not posted.\n"
        f"{len(D['t_mark_r'])} arcs, one colour each, right over the antenna",
        fontsize=11, pad=14)
    frame(axes[3], scene(D, explode=26.0), azim=-35, elev=26)
    axes[3].set_title(
        "apart, in the order it comes apart  -  lid down,\n"
        "then the fascia slides out of the bottom of its channel",
        fontsize=11, pad=14)
    fig.suptitle(
        "NFC tap player  -  PN532 flat under the pad, antenna up;  ESP32 DevKit on "
        "the lid;  the face is its own part",
        fontsize=15, fontweight="bold", y=0.99)
    fig.subplots_adjust(top=0.82, wspace=0.02)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "nfc-cassette-tap.png", dpi=130, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT / 'nfc-cassette-tap.png'}")


if __name__ == "__main__":
    main()
