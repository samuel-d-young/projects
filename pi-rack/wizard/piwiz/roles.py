"""Role definitions: what a node is actually for.

A role is a directory under `roles/`:

    roles/<name>/
      role.toml       metadata, packages, ports, hardware floor
      bootstrap.sh    the real work, run once on first boot as root

The split is deliberate. `role.toml` is data the wizard reasons about - it can
check that a 2 GB Pi 4 is not being asked to run something that needs 4 GB, or
that a role's port is not already taken on the LAN, *before* anything is
flashed. `bootstrap.sh` is ordinary shell that a human can read, run by hand on
a node to debug, and diff against what actually happened.

Nothing role-specific belongs in the wizard's Python. If a role needs something,
it says so in its own directory.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .bootcfg import RoleBundle
from .fleet import PORTS_IN_USE, Node

BOOTSTRAP_DIR = "/opt/pi-rack"


class RoleError(ValueError):
    pass


@dataclass
class Role:
    name: str
    summary: str
    packages: list[str] = field(default_factory=list)
    ports: list[int] = field(default_factory=list)
    min_ram_gb: int = 1
    wants_boot: str = "sd"          # "sd" | "usb-ssd" | "nvme" - recommended, not enforced
    pi5_only: bool = False
    needs_hardware: str = ""        # a HAT, a dongle, a Coral - free text, shown in the BOM
    bootstrap: str = ""             # contents of bootstrap.sh, empty if the role has none
    path: Path | None = None

    def warnings_for(self, node: Node) -> list[str]:
        """Things that are legal but probably wrong. These do not block a flash;
        they are printed so the operator decides knowingly."""
        out: list[str] = []
        if self.pi5_only and not node.is_pi5:
            out.append(
                f"role {self.name!r} is marked pi5-only but {node.hostname} is {node.hardware}"
            )
        if node.ram_gb and node.ram_gb < self.min_ram_gb:
            out.append(
                f"role {self.name!r} wants {self.min_ram_gb} GB but {node.hostname} "
                f"has {node.ram_gb} GB - expect swapping or an OOM kill under load"
            )
        if self.wants_boot != "sd" and node.boot == "sd":
            out.append(
                f"role {self.name!r} recommends booting from {self.wants_boot}; "
                f"{node.hostname} is on an SD card, which will wear out faster and "
                "be markedly slower for this workload"
            )
        for port in self.ports:
            if port in PORTS_IN_USE:
                out.append(
                    f"role {self.name!r} wants port {port}, already {PORTS_IN_USE[port]}"
                )
        # "none" is an answer, not a warning. Only surface a hardware note when
        # there is something to actually go and buy or plug in - otherwise the
        # useful warnings drown in boilerplate and stop being read.
        needs = self.needs_hardware.strip()
        if needs and needs.lower().lstrip().split(".")[0].strip() not in {"none", "none required"}:
            out.append(f"role {self.name!r} needs hardware: {needs}")
        return out


def load_role(directory: Path) -> Role:
    directory = Path(directory)
    meta_path = directory / "role.toml"
    if not meta_path.exists():
        raise RoleError(f"{directory} has no role.toml")

    with meta_path.open("rb") as fh:
        data = tomllib.load(fh)

    bootstrap_path = directory / "bootstrap.sh"
    bootstrap = ""
    if bootstrap_path.exists():
        # newline="" so we see exactly what is on disk; CRLF here would reach a Pi
        # as a shebang with a carriage return and fail with "bad interpreter".
        raw = bootstrap_path.read_text(encoding="utf-8", newline="")
        if "\r\n" in raw:
            raise RoleError(
                f"{bootstrap_path} has CRLF line endings. It will fail on the Pi with "
                "'bad interpreter'. Add a .gitattributes with '*.sh eol=lf' and re-checkout."
            )
        bootstrap = raw

    return Role(
        name=data.get("name", directory.name),
        summary=data.get("summary", ""),
        packages=[str(p) for p in data.get("packages", [])],
        ports=[int(p) for p in data.get("ports", [])],
        min_ram_gb=int(data.get("min_ram_gb", 1)),
        wants_boot=data.get("wants_boot", "sd"),
        pi5_only=bool(data.get("pi5_only", False)),
        needs_hardware=data.get("needs_hardware", ""),
        bootstrap=bootstrap,
        path=directory,
    )


def load_all(roles_dir: Path) -> dict[str, Role]:
    roles_dir = Path(roles_dir)
    if not roles_dir.is_dir():
        raise RoleError(f"{roles_dir} is not a directory")
    out: dict[str, Role] = {}
    for child in sorted(roles_dir.iterdir()):
        if child.is_dir() and (child / "role.toml").exists():
            role = load_role(child)
            out[role.name] = role
    return out


def load_common(roles_dir: Path) -> str:
    """The shared shell library every role sources.

    Every `bootstrap.sh` starts with `. /opt/pi-rack/common.sh`, so if this is not
    written to the card the first boot fails on line three of every role - with a
    "No such file or directory" buried in cloud-init's output. It is included in
    the bundle unconditionally for that reason.
    """
    path = Path(roles_dir).parent / "bootstrap" / "lib" / "common.sh"
    if not path.exists():
        raise RoleError(
            f"{path} is missing. Every role sources it as /opt/pi-rack/common.sh, "
            "so without it no node will provision."
        )
    raw = path.read_text(encoding="utf-8", newline="")
    if "\r\n" in raw:
        raise RoleError(
            f"{path} has CRLF line endings and would fail on the Pi with "
            "'bad interpreter'. Check .gitattributes has '*.sh eol=lf'."
        )
    return raw


def bundle_for(node: Node, catalogue: dict[str, Role]) -> tuple[RoleBundle, list[str]]:
    """Collapse a node's roles into one first-boot bundle, plus any warnings.

    Ordering is the order the roles appear in fleet.toml, so a node that lists
    `["docker", "gitea"]` gets docker installed before gitea's bootstrap runs.
    """
    packages: list[str] = []
    write_files: list[tuple[str, str, str]] = []
    runcmd: list[str] = []
    warnings: list[str] = []
    summary_lines: list[str] = []

    for name in node.roles:
        role = catalogue.get(name)
        if role is None:
            raise RoleError(
                f"{node.hostname} asks for role {name!r}, which has no directory under roles/"
            )
        warnings.extend(role.warnings_for(node))
        packages.extend(role.packages)
        summary_lines.append(f"{role.name}: {role.summary}")

        if role.bootstrap:
            script_path = f"{BOOTSTRAP_DIR}/{role.name}.sh"
            write_files.append((script_path, role.bootstrap, "0750"))
            # Logged per role, so a failure names the role rather than "runcmd[3]".
            runcmd.append(
                f'[ sh, -c, "{script_path} >> /var/log/pi-rack-bootstrap.log 2>&1 '
                f'|| echo ROLE-FAILED-{role.name} >> /var/log/pi-rack-bootstrap.log" ]'
            )

    # The node identity file, written before any role script runs so the scripts
    # can source it rather than having their values baked in by string substitution.
    env = "\n".join(
        [
            "# pi-rack node identity - written by piwiz at flash time.",
            f"PI_RACK_HOSTNAME={node.hostname}",
            f"PI_RACK_IP={node.ip}",
            f"PI_RACK_HARDWARE={node.hardware}",
            f"PI_RACK_BOOT={node.boot}",
            f"PI_RACK_ROLES={','.join(node.roles)}",
            "",
        ]
    )
    write_files.insert(0, ("/etc/pi-rack.env", env, "0644"))

    # The shared library goes in ahead of everything, because every role script's
    # third line sources it. Only when there is at least one script to source it.
    if any(catalogue[name].bootstrap for name in node.roles if name in catalogue):
        roles_dir = next(
            (r.path.parent for r in catalogue.values() if r.path is not None), None
        )
        if roles_dir is None:
            raise RoleError("cannot locate the roles directory to find common.sh")
        write_files.insert(0, (f"{BOOTSTRAP_DIR}/common.sh", load_common(roles_dir), "0644"))

    return (
        RoleBundle(
            packages=packages,
            write_files=write_files,
            runcmd=runcmd,
            summary="\n".join(summary_lines),
        ),
        warnings,
    )
