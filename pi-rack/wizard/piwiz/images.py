"""Fetch and verify Raspberry Pi OS images.

Uses the same index Raspberry Pi Imager uses:
https://downloads.raspberrypi.org/os_list_imagingutility_v4.json

That index carries `extract_sha256` - the hash of the *decompressed* .img - so a
download can be proven correct end to end rather than trusted. Verified against
the live endpoint on 2026-08-28: Raspberry Pi OS Lite (64-bit), release
2026-06-18, 524,875,608 bytes compressed, 2,977,955,840 extracted,
sha256 e235fd24fc5f039c08daba7d3abc04aecc7313f979d16d2a3fdad29dd44c33a9.

Cache location matters here and is not a detail: on this workbench K: has under
50 GB free of 13 TB. Images must not land there. `default_cache_dir()` picks the
fixed drive with the most free space and refuses anything too tight.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

OS_LIST_URL = "https://downloads.raspberrypi.org/os_list_imagingutility_v4.json"

# The image this project standardises on. Lite, because every node here is
# headless and a desktop is 2 GB of attack surface and SD wear for nothing.
DEFAULT_IMAGE_NAME = "Raspberry Pi OS Lite (64-bit)"


@dataclass(frozen=True)
class CatalogueEntry:
    """A named OS choice a node can ask for in fleet.toml."""

    key: str
    index_name: str | None      # look this up in the official index...
    url: str | None             # ...or download this directly
    cloud_init: bool            # can piwiz seed it?
    note: str


# Only the default is cloud-init seedable. That is the whole reason this
# catalogue exists: a node running something that ships as its own complete
# image cannot be provisioned by writing user-data to its boot partition, and
# the wizard should say so plainly rather than write three files that are
# silently ignored.
CATALOGUE: dict[str, CatalogueEntry] = {
    "raspios-lite": CatalogueEntry(
        key="raspios-lite",
        index_name=DEFAULT_IMAGE_NAME,
        url=None,
        cloud_init=True,
        note="Raspberry Pi OS Lite 64-bit (trixie). The default for every node.",
    ),
    "raspios-full": CatalogueEntry(
        key="raspios-full",
        index_name="Raspberry Pi OS (64-bit)",
        url=None,
        cloud_init=True,
        note="Desktop image. Only for a node that drives a screen.",
    ),
    "ubuntu-server": CatalogueEntry(
        key="ubuntu-server",
        index_name="Ubuntu Server 26.04 (64-bit)",
        url=None,
        cloud_init=True,
        note=(
            "Ubuntu Server for Pi. Also cloud-init, but its seed layout and default "
            "user differ from Raspberry Pi OS - piwiz targets Pi OS, so treat this "
            "as unverified until someone actually boots one."
        ),
    ),
    "fpp": CatalogueEntry(
        key="fpp",
        index_name=None,
        url=None,
        cloud_init=False,
        note=(
            "Falcon Player (FPP) for xLights ships as its own complete Raspberry Pi "
            "image from github.com/FalconChristmas/fpp/releases. It is NOT cloud-init "
            "seeded: write it with Raspberry Pi Imager, then configure FPP through its "
            "own web UI. `piwiz seed` will refuse this node, deliberately. The "
            "alternative is FPP_Install.sh on top of Raspberry Pi OS, which keeps the "
            "cloud-init path but is the less-travelled route."
        ),
    ),
}


def catalogue_entry(key: str) -> CatalogueEntry:
    try:
        return CATALOGUE[key]
    except KeyError:
        raise ImageError(
            f"unknown image {key!r}. Known: {', '.join(sorted(CATALOGUE))}"
        ) from None

# Room for the .xz plus the extracted .img plus headroom.
MIN_CACHE_FREE_BYTES = 20 * 1024**3


class ImageError(RuntimeError):
    pass


@dataclass
class ImageEntry:
    name: str
    url: str
    release_date: str
    download_size: int
    extract_size: int
    extract_sha256: str
    devices: list[str]
    init_format: str

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]

    @property
    def img_filename(self) -> str:
        return self.filename[:-3] if self.filename.endswith(".xz") else self.filename

    @property
    def uses_cloud_init(self) -> bool:
        """True when first-boot config is cloud-init seed files on the boot
        partition (user-data / network-config / meta-data) rather than the older
        custom.toml or firstrun.sh mechanisms."""
        return self.init_format.startswith("cloudinit")


def _walk(items: list[dict], path: str = "") -> Iterator[tuple[str, dict]]:
    for item in items:
        name = item.get("name", "")
        if "subitems" in item:
            yield from _walk(item["subitems"], f"{path}/{name}")
        elif item.get("url"):
            yield (f"{path}/{name}".strip("/"), item)


def fetch_index(timeout: int = 60) -> list[ImageEntry]:
    with urllib.request.urlopen(OS_LIST_URL, timeout=timeout) as resp:
        data = json.load(resp)

    entries: list[ImageEntry] = []
    for _path, item in _walk(data.get("os_list", [])):
        sha = item.get("extract_sha256") or ""
        entries.append(
            ImageEntry(
                name=item.get("name", "?"),
                url=item["url"],
                release_date=item.get("release_date", ""),
                download_size=int(item.get("image_download_size") or 0),
                extract_size=int(item.get("extract_size") or 0),
                extract_sha256=sha,
                devices=[str(d) for d in item.get("devices", [])],
                init_format=item.get("init_format", ""),
            )
        )
    return entries


def pick(entries: list[ImageEntry], name: str = DEFAULT_IMAGE_NAME) -> ImageEntry:
    for entry in entries:
        if entry.name == name and "arm64" in entry.url and "oldstable" not in entry.url:
            return entry
    raise ImageError(
        f"no image named {name!r} in the index. Available: "
        + ", ".join(sorted({e.name for e in entries})[:20])
    )


def default_cache_dir() -> Path:
    """The fixed drive with the most free space, plus a pi-rack-images folder.

    Explicitly not K: - see the module docstring. If nothing has room, this
    raises rather than silently filling a nearly-full disk, because the failure
    mode of doing that on this machine is losing the ability to save a project.
    """
    exe = shutil.which("powershell")
    if not exe:
        raise ImageError("PowerShell not found")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$out=@(Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } |"
        "ForEach-Object { [PSCustomObject]@{Letter=[string]$_.DriveLetter;"
        "Free=[int64]$_.SizeRemaining;Label=[string]$_.FileSystemLabel} });"
        "ConvertTo-Json -InputObject $out -Depth 3 -Compress"
    )
    proc = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    vols = json.loads(proc.stdout or "[]")
    if isinstance(vols, dict):
        vols = [vols]
    vols = [v for v in vols if int(v.get("Free") or 0) >= MIN_CACHE_FREE_BYTES]
    if not vols:
        raise ImageError(
            "no fixed drive has "
            f"{MIN_CACHE_FREE_BYTES // 1024**3} GB free for an image cache. "
            "Free some space or set image_cache in fleet.toml."
        )
    best = max(vols, key=lambda v: int(v["Free"]))
    return Path(f"{best['Letter']}:/") / "pi-rack-images"


def _sha256_of(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def download(
    entry: ImageEntry,
    cache_dir: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / entry.filename

    if target.exists() and target.stat().st_size == entry.download_size:
        return target

    tmp = target.with_suffix(target.suffix + ".part")
    done = 0
    with urllib.request.urlopen(entry.url, timeout=180) as resp, tmp.open("wb") as out:
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            out.write(block)
            done += len(block)
            if progress:
                progress(done, entry.download_size)
    tmp.replace(target)

    if entry.download_size and target.stat().st_size != entry.download_size:
        target.unlink(missing_ok=True)
        raise ImageError(
            f"downloaded {target.stat().st_size} bytes, index says {entry.download_size}"
        )
    return target


def extract_and_verify(
    entry: ImageEntry,
    archive: Path,
    cache_dir: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Decompress the .xz and check the result against the index's sha256.

    Hashing happens during decompression, so the image is never written to disk
    unverified and then trusted - if the hash is wrong the file is deleted.
    """
    cache_dir = Path(cache_dir)
    img = cache_dir / entry.img_filename
    stamp = img.with_suffix(img.suffix + ".sha256")

    if img.exists() and stamp.exists():
        if stamp.read_text(encoding="utf-8").strip() == entry.extract_sha256:
            return img

    digest = hashlib.sha256()
    done = 0
    tmp = img.with_suffix(img.suffix + ".part")
    with lzma.open(archive, "rb") as src, tmp.open("wb") as out:
        while True:
            block = src.read(1 << 22)
            if not block:
                break
            digest.update(block)
            out.write(block)
            done += len(block)
            if progress:
                progress(done, entry.extract_size)

    actual = digest.hexdigest()
    if entry.extract_sha256 and actual != entry.extract_sha256:
        tmp.unlink(missing_ok=True)
        raise ImageError(
            "IMAGE HASH MISMATCH - refusing to use it.\n"
            f"  expected {entry.extract_sha256}\n"
            f"  got      {actual}\n"
            "Delete the cached .xz and download again."
        )

    tmp.replace(img)
    stamp.write_text(actual + "\n", encoding="utf-8")
    return img


def ensure_image(
    cache_dir: Path | None = None,
    name: str = DEFAULT_IMAGE_NAME,
    progress: Callable[[str, int, int], None] | None = None,
) -> tuple[Path, ImageEntry]:
    """Index -> download -> extract -> verify. Returns the ready-to-write .img."""
    cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()
    entry = pick(fetch_index(), name)

    def dl(done: int, total: int) -> None:
        if progress:
            progress("download", done, total)

    def ex(done: int, total: int) -> None:
        if progress:
            progress("extract", done, total)

    archive = download(entry, cache_dir, dl)
    img = extract_and_verify(entry, archive, cache_dir, ex)
    return img, entry
