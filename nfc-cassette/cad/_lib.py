"""Export gate, borrowed from robot/luma. Nothing reaches stl/ without passing.

    watertight        no holes
    winding           consistent normals
    volume agreement  mesh volume within 1% of the B-rep volume - catches a
                      tessellation that silently dropped a face
    one body          the part is a single connected solid
    build volume      fits the P1S bed with a margin

The one-body check was added after the cartridge's back plate came out in two
disconnected pieces - a plate and, 1.6 mm away with air in between, its spigot.
Mirroring the outline had reversed the polygon's winding, so the plate extruded
downward from the sketch plane while the spigot was added above it. Nothing
else here noticed: two closed shells are still watertight, their windings are
still consistent, and their volumes still add up to what the B-rep says. It
would have sliced, printed as two parts, and only then made sense.

Every part records its print orientation. On this project every part prints
flat-face-down with no supports; "needs supports" is a design failure.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from build123d import Shape, export_step, export_stl

ROOT = Path(__file__).resolve().parent.parent
STL_DIR = ROOT / "stl"
STEP_DIR = ROOT / "step"
MANIFEST = STL_DIR / "manifest.json"

BUILD_VOLUME = (256.0, 256.0, 256.0)
EDGE_MARGIN = 6.0
VOLUME_DRIFT_MAX = 0.01


@dataclass
class PartRecord:
    name: str
    triangles: int
    watertight: bool
    winding_ok: bool
    volume_mm3: float
    brep_volume_mm3: float
    volume_drift: float
    extents_mm: list
    fits_build_volume: bool
    bodies: int
    mass_g_pla: float
    orientation: str = ""
    supports: str = "none"
    note: str = ""
    errors: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


_RECORDS: dict[str, PartRecord] = {}


def emit(part: Shape, name: str, orientation: str = "", supports: str = "none",
         note: str = "", tolerance: float = 0.04, infill: float = 0.2) -> PartRecord:
    import trimesh

    STL_DIR.mkdir(parents=True, exist_ok=True)
    STEP_DIR.mkdir(parents=True, exist_ok=True)
    stl_path = STL_DIR / f"{name}.stl"
    step_path = STEP_DIR / f"{name}.step"
    export_step(part, str(step_path))
    export_stl(part, str(stl_path), tolerance=tolerance)

    mesh = trimesh.load(str(stl_path))
    brep_v = float(part.volume)
    mesh_v = float(mesh.volume)
    drift = abs(mesh_v - brep_v) / brep_v if brep_v else 1.0
    ext = [round(float(x), 2) for x in mesh.extents]
    lim = [b - 2 * EDGE_MARGIN for b in BUILD_VOLUME]
    fits = all(e <= l for e, l in zip(sorted(ext, reverse=True), sorted(lim, reverse=True)))
    mass = mesh_v / 1000.0 * 1.24 * (0.42 + 0.58 * infill)
    bodies = len(mesh.split(only_watertight=False))

    rec = PartRecord(name=name, triangles=int(len(mesh.faces)),
                     watertight=bool(mesh.is_watertight), winding_ok=bool(mesh.is_winding_consistent),
                     volume_mm3=round(mesh_v, 2), brep_volume_mm3=round(brep_v, 2),
                     volume_drift=round(drift, 6), extents_mm=ext, fits_build_volume=fits,
                     bodies=int(bodies),
                     mass_g_pla=round(mass, 1), orientation=orientation, supports=supports, note=note)
    if not rec.watertight:
        rec.errors.append("not watertight")
    if not rec.winding_ok:
        rec.errors.append("inconsistent winding")
    if drift > VOLUME_DRIFT_MAX:
        rec.errors.append(f"volume drift {drift*100:.2f}% > {VOLUME_DRIFT_MAX*100:.0f}%")
    if bodies != 1:
        rec.errors.append(f"{bodies} disconnected bodies, not 1")
    if not fits:
        rec.errors.append(f"does not fit build volume: {ext}")
    if rec.errors:
        stl_path.unlink(missing_ok=True)
        step_path.unlink(missing_ok=True)
        print(f"  REJECTED {name}: {'; '.join(rec.errors)}")
    else:
        print(f"  ok  {name:18s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm  "
              f"{rec.mass_g_pla:5.1f} g  {rec.triangles:6d} tri  {orientation}")
    _RECORDS[name] = rec
    return rec


def write_manifest() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            data = {}
    data = {k: v for k, v in data.items() if (STL_DIR / f"{k}.stl").exists()}
    data.update({k: asdict(v) for k, v in _RECORDS.items()})
    MANIFEST.write_text(json.dumps(data, indent=1))
