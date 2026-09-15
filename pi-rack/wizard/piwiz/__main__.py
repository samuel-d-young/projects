"""piwiz - the pi-rack setup wizard.

    python -m piwiz                 guided flow, start here
    python -m piwiz doctor          check this machine can do the job
    python -m piwiz plan            validate fleet.toml and show what is planned
    python -m piwiz roles           list the role catalogue
    python -m piwiz fetch           download and verify the OS image
    python -m piwiz flash <node>    write a card for one node, end to end
    python -m piwiz seed <node>     write only the cloud-init files to a card
    python -m piwiz scan            re-scan the LAN for address collisions
    python -m piwiz verify          check which nodes have come up

The design rule: `seed` is the step that matters and it needs no Administrator.
If everything else fails, a card written by the Imager GUI plus `seed` gives a
correctly configured node.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import bootcfg, disks, images, roles as roles_mod, writer
from .fleet import Fleet, FleetError, Node
from . import fleet as fleet_mod

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FLEET = ROOT / "fleet.toml"
DEFAULT_ROLES = ROOT / "roles"

BOLD, DIM, RED, GREEN, YELLOW, CYAN, RESET = (
    "\033[1m", "\033[2m", "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[0m",
)


def _enable_ansi() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


def head(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")
    print(DIM + "-" * len(text) + RESET)


def ok(text: str) -> None:
    print(f"  {GREEN}OK{RESET}    {text}")


def warn(text: str) -> None:
    print(f"  {YELLOW}WARN{RESET}  {text}")


def bad(text: str) -> None:
    print(f"  {RED}FAIL{RESET}  {text}")


def info(text: str) -> None:
    print(f"        {text}")


def bar(done: int, total: int, label: str = "") -> None:
    if not total:
        return
    frac = min(1.0, done / total)
    width = 34
    filled = int(width * frac)
    sys.stdout.write(
        f"\r  {label:9} [{'#' * filled}{'.' * (width - filled)}] "
        f"{frac * 100:5.1f}%  {done / 1e6:7.1f} MB"
    )
    sys.stdout.flush()
    if done >= total:
        sys.stdout.write("\n")


def load(args) -> tuple[Fleet, dict[str, roles_mod.Role]]:
    fleet = fleet_mod.load(args.fleet)
    catalogue = roles_mod.load_all(args.roles) if Path(args.roles).is_dir() else {}
    return fleet, catalogue


# --- doctor -----------------------------------------------------------------------


def cmd_doctor(args) -> int:
    head("Environment")
    problems = 0

    v = sys.version_info
    if v >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        bad(f"Python {v.major}.{v.minor} - need 3.11+ for tomllib")
        problems += 1

    try:
        import yaml  # noqa: F401

        ok("PyYAML present - generated cloud-init will be parse-checked")
    except ImportError:
        warn("PyYAML missing - cloud-init YAML will be written unchecked")
        info("pip install pyyaml   (strongly recommended: a YAML typo means a dead node)")

    for tool in ("ssh", "ssh-keygen"):
        if shutil.which(tool):
            ok(f"{tool} found")
        else:
            bad(f"{tool} not found - needed to make and use the fleet key")
            problems += 1

    imager = writer.find_imager()
    if imager:
        ok(f"Raspberry Pi Imager: {imager}")
    else:
        warn("Raspberry Pi Imager not installed")
        for line in writer.imager_install_hint().splitlines():
            info(line)

    if writer.is_admin():
        ok("running as Administrator - the native writer is available")
    else:
        warn("not Administrator - cards must be written by Imager, or re-run elevated")
        info("`seed` still works without elevation, which is the important part")

    head("Image cache")
    try:
        cache = Path(args.cache) if getattr(args, "cache", None) else images.default_cache_dir()
        ok(f"cache location: {cache}")
        if str(cache).upper().startswith("K:"):
            bad("cache is on K:, which has under 50 GB free - pick another drive")
            problems += 1
    except images.ImageError as exc:
        bad(str(exc))
        problems += 1

    head("Disks visible right now")
    try:
        found = disks.enumerate_disks()
        targets = disks.candidate_targets(found)
        for d in found:
            reasons = d.refusals()
            mark = f"{GREEN}TARGET{RESET}" if not reasons else f"{DIM}protected{RESET}"
            print(f"  {mark:20} {d.describe().splitlines()[0]}")
        if targets:
            ok(f"{len(targets)} card(s) available: disk {', '.join(str(t.number) for t in targets)}")
        else:
            warn("no removable card detected - insert one before `flash`")
        info(f"{len(found) - len(targets)} disk(s) are protected and cannot be written")
    except Exception as exc:
        bad(f"disk enumeration failed: {exc}")
        problems += 1

    head("Fleet")
    try:
        fleet, catalogue = load(args)
        issues = fleet.validate(set(catalogue) if catalogue else None)
        if issues:
            for i in issues:
                bad(i)
            problems += len(issues)
        else:
            ok(f"{args.fleet} is valid: {len(fleet.active)} active node(s), "
               f"{len(catalogue)} role(s)")
    except FleetError as exc:
        warn(str(exc))

    print()
    if problems:
        print(f"{RED}{problems} problem(s) to fix before flashing.{RESET}")
        return 1
    print(f"{GREEN}Ready.{RESET}")
    return 0


# --- plan / roles ------------------------------------------------------------------


def cmd_plan(args) -> int:
    fleet, catalogue = load(args)
    issues = fleet.validate(set(catalogue) if catalogue else None)

    head(f"Plan: {args.fleet}")
    print(f"  network   {fleet.network.cidr}  gw {fleet.network.gateway}  "
          f"dns {', '.join(fleet.network.dns)}")
    print(f"  admin     {fleet.admin_user}   key {fleet.ssh_pubkey_path}")
    print(f"  locale    {fleet.timezone} / {fleet.locale}")
    print()
    print(f"  {'NODE':14} {'HARDWARE':10} {'IP':16} {'BOOT':9} ROLES")
    for n in fleet.nodes:
        flag = "" if n.enabled else f" {DIM}(disabled){RESET}"
        print(f"  {n.hostname:14} {n.hardware:10} {n.ip:16} {n.boot:9} "
              f"{', '.join(n.roles)}{flag}")

    if catalogue:
        head("Per-node warnings")
        any_warn = False
        for n in fleet.active:
            try:
                _, warnings = roles_mod.bundle_for(n, catalogue)
            except roles_mod.RoleError as exc:
                bad(str(exc))
                any_warn = True
                continue
            for w in warnings:
                warn(f"{n.hostname}: {w}")
                any_warn = True
        if not any_warn:
            ok("none")

    if issues:
        head("Validation")
        for i in issues:
            bad(i)
        return 1
    head("Validation")
    ok("plan is valid")
    return 0


FLEET_TEMPLATE = '''# pi-rack fleet definition.
#
# This file is the source of truth for the rack. Everything the wizard writes -
# the cloud-init seed, the static IP, the bootstrap scripts, the docs table - is
# derived from it. Edit this and re-flash; never configure a node by hand and let
# the two drift.
#
# Validate with:  python -m piwiz plan

[network]
cidr          = "192.168.1.0/24"
gateway       = "192.168.1.1"
dns           = ["192.168.1.1"]
domain        = "lan"
# Nodes must land inside this range, and it must sit OUTSIDE the router's DHCP
# pool or the router will eventually hand one of these addresses to a phone.
static_range  = [100, 130]

[fleet]
# Not "pi", not "admin". These nodes are reachable from the whole LAN.
admin_user      = "vultron"
# The PUBLIC key (.pub). Make one with:
#   ssh-keygen -t ed25519 -C pi-rack -f %USERPROFILE%\\.ssh\\pi_rack
ssh_pubkey_path = "~/.ssh/pi_rack.pub"
timezone        = "Australia/Melbourne"
locale          = "en_AU.UTF-8"
keyboard        = "us"
wifi_country    = "AU"
# Leave unset to auto-pick the fixed drive with the most free space.
# Never K: - it has under 50 GB free.
# image_cache   = "O:/pi-rack-images"

# --- nodes -------------------------------------------------------------------
# hardware : pi4-2gb | pi4-4gb | pi4-8gb | pi5-4gb | pi5-8gb | pi5-16gb
# boot     : sd | usb-ssd | nvme      (nvme is Pi 5 only)
# roles    : must match a directory under roles/

# [[node]]
# hostname = "example"
# hardware = "pi4-4gb"
# ip       = "192.168.1.101"
# roles    = ["base"]
# boot     = "sd"
# ports    = []
# notes    = "what this box is for, in one line"
'''


def cmd_keygen(args) -> int:
    """Make the one SSH key the whole fleet trusts.

    One key for the rack, separate from any key used for GitHub or other hosts:
    if it ever needs rotating, that is five cards, not an audit of everything
    Samuel has ever signed into.
    """
    try:
        fleet, _ = load(args)
        target = fleet.ssh_pubkey_path
    except FleetError:
        target = Path.home() / ".ssh" / "pi_rack.pub"

    private = target.with_suffix("") if target.suffix == ".pub" else target
    head("Fleet SSH key")

    if target.exists():
        ok(f"already exists: {target}")
        info(target.read_text(encoding="utf-8").strip())
        return 0

    private.parent.mkdir(parents=True, exist_ok=True)
    keygen = shutil.which("ssh-keygen")
    if not keygen:
        bad("ssh-keygen not found")
        return 1

    print(f"  Creating {private}")
    print(f"  {DIM}An empty passphrase is the usual choice here: the wizard and any")
    print(f"  scripted access need to use it unattended.{RESET}")
    passphrase = input("  Passphrase (Enter for none): ")

    proc = subprocess.run(
        [keygen, "-t", "ed25519", "-C", "pi-rack", "-f", str(private), "-N", passphrase],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        bad(proc.stderr.strip() or "ssh-keygen failed")
        return 1

    ok(f"private key {private}")
    ok(f"public key  {private}.pub")
    info((private.with_suffix(private.suffix + ".pub")).read_text(encoding="utf-8").strip()
         if private.suffix else Path(str(private) + ".pub").read_text(encoding="utf-8").strip())
    print()
    warn("The private key is the only way into every node. Back it up somewhere")
    info("that is not one of these Pis, and not the second-brain vault (public remote).")
    return 0


def cmd_init(args) -> int:
    target = Path(args.fleet)
    if target.exists():
        print(f"{YELLOW}{target} already exists - not overwriting.{RESET}")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(FLEET_TEMPLATE, encoding="utf-8", newline="\n")
    ok(f"wrote {target}")
    info("Edit it, then run:  python -m piwiz plan")
    return 0


def cmd_roles(args) -> int:
    catalogue = roles_mod.load_all(args.roles)
    head(f"Roles in {args.roles}")
    if not catalogue:
        warn("no roles defined yet")
        return 0
    for name, role in sorted(catalogue.items()):
        extra = []
        if role.pi5_only:
            extra.append("pi5-only")
        if role.min_ram_gb > 1:
            extra.append(f"{role.min_ram_gb}GB+")
        if role.wants_boot != "sd":
            extra.append(f"wants {role.wants_boot}")
        if role.ports:
            extra.append("ports " + ",".join(str(p) for p in role.ports))
        tag = f"  {DIM}[{', '.join(extra)}]{RESET}" if extra else ""
        print(f"  {BOLD}{name}{RESET}{tag}")
        print(f"      {role.summary}")
        if role.needs_hardware:
            print(f"      {YELLOW}needs:{RESET} {role.needs_hardware}")
    return 0


# --- fetch -------------------------------------------------------------------------


def cmd_fetch(args) -> int:
    fleet = None
    try:
        fleet, _ = load(args)
    except FleetError:
        pass
    cache = Path(args.cache) if args.cache else (
        fleet.image_cache if fleet and fleet.image_cache else images.default_cache_dir()
    )

    head("Fetching Raspberry Pi OS")
    info(f"cache: {cache}")

    def progress(stage: str, done: int, total: int) -> None:
        bar(done, total, stage)

    img, entry = images.ensure_image(cache, progress=progress)
    ok(f"{entry.name}  release {entry.release_date}")
    info(f"image      {img}")
    info(f"sha256     {entry.extract_sha256}  (verified)")
    info(f"init       {entry.init_format}"
         + ("  -> cloud-init seed files" if entry.uses_cloud_init else ""))
    return 0


# --- seed ---------------------------------------------------------------------------


def _resolve_boot_dir(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit if explicit.endswith(("/", "\\")) else explicit + "/")
        return p
    for d in disks.enumerate_disks():
        letter = disks.boot_partition_letter(d.number)
        if letter and Path(f"{letter}:/config.txt").exists() and Path(f"{letter}:/cmdline.txt").exists():
            return Path(f"{letter}:/")
    raise SystemExit(
        f"{RED}Could not find a mounted Raspberry Pi boot partition.{RESET}\n"
        "Insert the card, wait for Windows to mount it, and try again - or pass\n"
        "the drive explicitly:  python -m piwiz seed <node> --boot E:"
    )


def cmd_seed(args) -> int:
    fleet, catalogue = load(args)
    node = fleet.node(args.node)

    entry = images.catalogue_entry(node.image)
    if not entry.cloud_init:
        head(f"Cannot seed {node.hostname}")
        bad(f"its image is {node.image!r}, which is not cloud-init based.")
        for line in entry.note.split(". "):
            info(line.strip() + ("." if not line.strip().endswith(".") else ""))
        print()
        info("Writing user-data to that card would do nothing at all, so the wizard")
        info("refuses rather than leaving you to discover it at the rack.")
        return 1

    bundle, warnings = roles_mod.bundle_for(node, catalogue)

    boot_dir = _resolve_boot_dir(args.boot)
    head(f"Seeding {node.hostname} -> {boot_dir}")
    info(f"{node.hardware}  {node.ip}  roles: {', '.join(node.roles)}")
    for w in warnings:
        warn(w)

    written = bootcfg.write_seed(
        boot_dir, fleet, node, bundle,
        plan_revision=args.revision,
        package_upgrade=args.upgrade,
    )
    for p in written:
        ok(f"wrote {p}  ({p.stat().st_size} bytes)")

    print()
    print(f"{GREEN}Card is ready.{RESET} Eject it, put it in {node.hostname}, and power on.")
    info("First boot installs packages, so give it 3-8 minutes before it answers.")
    info(f"Then:  ssh {fleet.admin_user}@{node.ip}")
    info(f"Or:    python -m piwiz verify")
    return 0


# --- flash --------------------------------------------------------------------------


def _choose_card() -> disks.Disk:
    while True:
        found = disks.enumerate_disks()
        targets = disks.candidate_targets(found)
        if not targets:
            print(f"\n{YELLOW}No writable card detected.{RESET}")
            print(f"  {len(found)} disk(s) are visible and all are protected:")
            for d in found:
                info(f"disk {d.number}  {d.friendly_name}  {disks.human(d.size)}  "
                     f"-> {d.refusals()[0]}")
            if input("\n  Insert a card and press Enter to rescan, or 'q' to quit: ").strip().lower() == "q":
                raise SystemExit(1)
            continue

        print(f"\n{BOLD}Writable cards:{RESET}")
        for d in targets:
            print("  " + d.describe().replace("\n", "\n  "))
        if len(targets) == 1:
            return targets[0]
        choice = input("\n  Disk number to write: ").strip()
        for d in targets:
            if str(d.number) == choice:
                return d
        print(f"  {RED}Not one of the writable disks.{RESET}")


def cmd_flash(args) -> int:
    fleet, catalogue = load(args)
    node = fleet.node(args.node)
    bundle, warnings = roles_mod.bundle_for(node, catalogue)

    issues = fleet.validate(set(catalogue) if catalogue else None)
    if issues:
        head("Refusing to flash - the plan is invalid")
        for i in issues:
            bad(i)
        return 1

    head(f"Flashing {node.hostname}")
    info(f"{node.hardware}   {node.ip}   boot from {node.boot}")
    info(f"roles: {', '.join(node.roles)}")
    for w in warnings:
        warn(w)

    cat_entry = images.catalogue_entry(node.image)
    if not cat_entry.index_name:
        head(f"{node.hostname} uses the {node.image!r} image")
        for line in cat_entry.note.split(". "):
            info(line.strip())
        print()
        bad("piwiz cannot fetch or seed this image - write it with Raspberry Pi Imager.")
        return 1

    cache = Path(args.cache) if args.cache else (fleet.image_cache or images.default_cache_dir())
    img, entry = images.ensure_image(cache, name=cat_entry.index_name,
                                     progress=lambda s, d, t: bar(d, t, s))
    ok(f"{entry.name} {entry.release_date}, sha256 verified")

    disk = _choose_card()

    print()
    print(f"{RED}{BOLD}This erases disk {disk.number} completely.{RESET}")
    print("  " + disk.describe().replace("\n", "\n  "))
    print(f"\n  To confirm, type this exactly:  {BOLD}{disk.fingerprint}{RESET}")
    if input("  > ").strip() != disk.fingerprint:
        print(f"  {YELLOW}Did not match. Nothing was written.{RESET}")
        return 1

    disks.assert_writable(disks.find_disk(disk.number))

    print()
    used = writer.write(img, disk, progress=lambda d, t: bar(d, t, "writing"),
                        on_line=lambda line: info(line))
    ok(f"written via {used}")

    if args.verify and writer.is_admin():
        if writer.verify_written(img, disk, progress=lambda d, t: bar(d, t, "verify")):
            ok("read-back matches the image exactly")
        else:
            bad("read-back does NOT match - the card is bad or the write failed")
            return 1

    letter = writer.wait_for_boot_partition(disk.number)
    if not letter:
        bad("Windows did not mount the boot partition")
        info(f"Re-insert the card and run:  python -m piwiz seed {node.hostname}")
        return 1
    ok(f"boot partition mounted at {letter}:")

    args.boot = f"{letter}:/"
    return cmd_seed(args)


# --- scan / verify --------------------------------------------------------------------


def _alive(ip: str, port: int = 22, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def cmd_scan(args) -> int:
    base = "192.168.1"
    head(f"Scanning {base}.0/24")
    exe = shutil.which("powershell")
    live: list[str] = []
    if exe:
        script = (
            "$ErrorActionPreference='SilentlyContinue';"
            f"$j=1..254|ForEach-Object{{Test-Connection -ComputerName '{base}.'+$_ -Count 1 -AsJob}};"
            "$null=$j|Wait-Job -Timeout 45;"
            "($j|Receive-Job|Where-Object{$_.StatusCode -eq 0}).Address"
        )
        out = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=180,
        )
        live = [l.strip() for l in out.stdout.splitlines() if l.strip()]

    octets = sorted(int(ip.rsplit(".", 1)[1]) for ip in live)
    ok(f"{len(octets)} hosts answering")
    print("  " + ", ".join(str(o) for o in octets))

    known = fleet_mod.OBSERVED_IN_USE
    new = set(octets) - known
    gone = known - set(octets)
    if new:
        warn(f"new since the recorded scan: {sorted(new)}")
    if gone:
        info(f"recorded but silent now: {sorted(gone)}")
    info("Update OBSERVED_IN_USE in piwiz/fleet.py if this is the new truth.")
    return 0


def cmd_verify(args) -> int:
    fleet, _ = load(args)
    head("Node status")
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda n: (n, _alive(n.ip)), fleet.active))
    up = 0
    for node, alive in results:
        if alive:
            ok(f"{node.hostname:14} {node.ip:16} ssh answering")
            up += 1
        else:
            bad(f"{node.hostname:14} {node.ip:16} no answer on 22")
    print()
    print(f"  {up}/{len(results)} nodes up")
    return 0 if up == len(results) else 1


# --- guided ---------------------------------------------------------------------------


def cmd_wizard(args) -> int:
    print(f"""
{BOLD}pi-rack setup wizard{RESET}
{DIM}Writes cloud-init-seeded Raspberry Pi OS cards for the rack.{RESET}
""")
    if cmd_doctor(args) != 0:
        print(f"\n{YELLOW}Fix the failures above, then run this again.{RESET}")
        return 1

    fleet, catalogue = load(args)
    pending = [n for n in fleet.active if not _alive(n.ip)]

    head("Nodes")
    for n in fleet.active:
        state = f"{GREEN}up{RESET}" if n not in pending else f"{DIM}not yet built{RESET}"
        print(f"  {n.hostname:14} {n.ip:16} {', '.join(n.roles):40} {state}")

    if not pending:
        print(f"\n{GREEN}Every node in the plan is already up.{RESET}")
        return 0

    print(f"\n  {len(pending)} node(s) still to build: "
          f"{', '.join(n.hostname for n in pending)}")
    target = pending[0]
    answer = input(f"\n  Build {BOLD}{target.hostname}{RESET} now? [Y/n/name] ").strip()
    if answer.lower() in ("n", "no", "q"):
        return 0
    if answer and answer.lower() not in ("y", "yes"):
        target = fleet.node(answer)

    args.node = target.hostname
    return cmd_flash(args)


# --- entry -----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    _enable_ansi()
    p = argparse.ArgumentParser(prog="piwiz", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fleet", default=str(DEFAULT_FLEET), help="path to fleet.toml")
    p.add_argument("--roles", default=str(DEFAULT_ROLES), help="path to the roles/ directory")
    p.add_argument("--cache", default=None, help="image cache directory")
    p.add_argument("--revision", default="", help="plan revision stamped into instance_id")

    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("keygen").set_defaults(fn=cmd_keygen)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    sub.add_parser("roles").set_defaults(fn=cmd_roles)
    sub.add_parser("fetch").set_defaults(fn=cmd_fetch)
    sub.add_parser("scan").set_defaults(fn=cmd_scan)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)

    s = sub.add_parser("seed")
    s.add_argument("node")
    s.add_argument("--boot", default=None, help="boot partition drive, e.g. E:")
    s.add_argument("--upgrade", action="store_true", help="full apt upgrade on first boot")
    s.set_defaults(fn=cmd_seed)

    f = sub.add_parser("flash")
    f.add_argument("node")
    f.add_argument("--boot", default=None)
    f.add_argument("--upgrade", action="store_true")
    f.add_argument("--no-verify", dest="verify", action="store_false", default=True)
    f.set_defaults(fn=cmd_flash)

    w = sub.add_parser("wizard")
    w.add_argument("--boot", default=None)
    w.add_argument("--upgrade", action="store_true")
    w.add_argument("--no-verify", dest="verify", action="store_false", default=True)
    w.set_defaults(fn=cmd_wizard)

    args = p.parse_args(argv)
    if not getattr(args, "cmd", None):
        for name, default in (("boot", None), ("upgrade", False), ("verify", True)):
            setattr(args, name, default)
        args.fn = cmd_wizard

    try:
        return args.fn(args)
    except (FleetError, roles_mod.RoleError, disks.DiskSafetyError,
            writer.WriteError, images.ImageError, bootcfg.BootConfigError) as exc:
        print(f"\n{RED}{exc}{RESET}")
        return 1
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted. Nothing further was written.{RESET}")
        return 130


if __name__ == "__main__":
    sys.exit(main())
