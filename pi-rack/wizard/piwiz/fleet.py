"""The fleet model: what nodes exist, what they are for, and where they live.

`fleet.toml` is the single source of truth for the rack. Every file the wizard
writes - the boot-partition config, the static IP, the bootstrap script, the
Home Assistant sensors, the docs table - is derived from it. Nothing is typed
twice, so nothing can drift.

Design rule inherited from the rest of this workbench: plan files are the source
of truth, and you edit the plan and re-apply rather than clicking it somewhere
and letting the two disagree.
"""

from __future__ import annotations

import ipaddress
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - the workbench runs 3.13
    raise RuntimeError("piwiz needs Python 3.11+ for tomllib")


# IPs observed live on 192.168.1.0/24 by port scan on 2026-08-28. The wizard
# refuses to assign any of these to a new node. Re-scan with `piwiz scan` to
# refresh - this list is a snapshot, not a law of nature.
OBSERVED_IN_USE = {
    1, 2, 4, 5, 6, 7, 8, 11, 12, 13, 18, 20, 21, 30, 31, 32, 33, 34, 39, 42, 43,
    44, 46, 49, 53, 54, 55, 59, 62, 63, 64, 65, 66, 70, 75, 76, 83, 93, 254,
}

# Ports already bound somewhere on the LAN, with what owns them. A node that
# asks for one of these is a configuration error, not a preference.
PORTS_IN_USE = {
    1883: "Mosquitto MQTT (192.168.1.75)",
    3000: "unidentified TP-Link/Tapo service (192.168.1.46)",
    5000: "Frigate (192.168.1.70)",
    5050: "RUBRIC console (workbench)",
    5060: "property-watch (workbench)",
    5080: "Agent Deck hub (192.168.1.42)",
    5175: "KIN dev server (workbench)",
    5210: "workspace map (workbench)",
    7788: "resolve-sync agent (workbench, loopback only)",
    8080: "DMX controller (N:\\DMX Controller)",
    8123: "Home Assistant (192.168.1.75)",
    9000: "unidentified service (192.168.1.34)",
    10200: "piper TTS (192.168.1.42)",
    10300: "faster-whisper STT (192.168.1.42 and .66)",
    10301: "faster-whisper base-int8 (192.168.1.66)",
}

HOSTNAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}[a-z0-9]$")


class FleetError(ValueError):
    """A fleet.toml that would produce a broken or dangerous deployment."""


@dataclass
class Node:
    hostname: str
    hardware: str                     # "pi4-4gb", "pi4-8gb", "pi5-8gb", ...
    ip: str
    roles: list[str] = field(default_factory=list)
    boot: str = "sd"                  # "sd" | "usb-ssd" | "nvme"
    mac: str = ""                     # optional, for a DHCP reservation
    ports: list[int] = field(default_factory=list)
    notes: str = ""
    enabled: bool = True
    # Which OS goes on the card. A key from images.CATALOGUE. Almost always the
    # default; the exception is a node running software that ships as its own
    # complete image (FPP for xLights is the one that matters here), which is
    # NOT cloud-init seeded and therefore cannot be provisioned the same way.
    image: str = "raspios-lite"

    @property
    def is_pi5(self) -> bool:
        return self.hardware.lower().startswith("pi5")

    @property
    def ram_gb(self) -> int:
        m = re.search(r"(\d+)gb", self.hardware.lower())
        return int(m.group(1)) if m else 0

    @property
    def last_octet(self) -> int:
        return int(self.ip.rsplit(".", 1)[1])

    def validate(self, net: Network, known_roles: set[str] | None) -> list[str]:
        problems: list[str] = []

        if not HOSTNAME_RE.match(self.hostname):
            problems.append(
                f"hostname {self.hostname!r} is not a valid DNS label "
                "(lowercase letters, digits and hyphens; must start with a letter)"
            )

        try:
            addr = ipaddress.IPv4Address(self.ip)
        except ValueError:
            problems.append(f"{self.hostname}: {self.ip!r} is not an IPv4 address")
            return problems

        if addr not in net.cidr:
            problems.append(f"{self.hostname}: {self.ip} is outside {net.cidr}")
        if addr == net.gateway:
            problems.append(f"{self.hostname}: {self.ip} is the gateway")
        if self.last_octet in OBSERVED_IN_USE:
            problems.append(
                f"{self.hostname}: {self.ip} was answering on the LAN at last scan - "
                "pick a free address or re-scan to confirm it is gone"
            )
        if not (net.static_range[0] <= self.last_octet <= net.static_range[1]):
            problems.append(
                f"{self.hostname}: {self.ip} is outside the static range "
                f".{net.static_range[0]}-.{net.static_range[1]}, so the router may "
                "hand it to something else via DHCP"
            )

        if self.boot not in {"sd", "usb-ssd", "nvme"}:
            problems.append(f"{self.hostname}: boot={self.boot!r} must be sd, usb-ssd or nvme")
        if self.boot == "nvme" and not self.is_pi5:
            problems.append(
                f"{self.hostname}: boot=nvme but hardware is {self.hardware} - "
                "only the Pi 5 has a PCIe lane for an NVMe HAT"
            )

        # Imported lazily: images.py is about downloads, fleet.py is about the
        # plan, and a module-level import each way would be a cycle.
        from .images import CATALOGUE

        if self.image not in CATALOGUE:
            problems.append(
                f"{self.hostname}: image {self.image!r} is unknown "
                f"(known: {', '.join(sorted(CATALOGUE))})"
            )

        if self.mac and not re.match(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$", self.mac.lower()):
            problems.append(f"{self.hostname}: mac {self.mac!r} is not aa:bb:cc:dd:ee:ff")

        if not self.roles:
            problems.append(f"{self.hostname}: has no roles - it would boot and do nothing")
        if known_roles is not None:
            for role in self.roles:
                if role not in known_roles:
                    problems.append(
                        f"{self.hostname}: role {role!r} has no definition in roles/"
                    )

        for port in self.ports:
            if port in PORTS_IN_USE:
                problems.append(
                    f"{self.hostname}: port {port} is already {PORTS_IN_USE[port]}"
                )
            if not (1 <= port <= 65535):
                problems.append(f"{self.hostname}: port {port} is out of range")

        return problems


@dataclass
class Network:
    cidr: ipaddress.IPv4Network
    gateway: ipaddress.IPv4Address
    dns: list[str]
    domain: str = "lan"
    static_range: tuple[int, int] = (100, 130)


@dataclass
class Fleet:
    network: Network
    admin_user: str
    ssh_pubkey_path: Path
    timezone: str
    locale: str
    keyboard: str
    wifi_country: str
    nodes: list[Node] = field(default_factory=list)
    image_cache: Path | None = None
    source: Path | None = None

    def node(self, hostname: str) -> Node:
        for n in self.nodes:
            if n.hostname == hostname:
                return n
        raise FleetError(f"no node named {hostname!r} in {self.source or 'fleet.toml'}")

    @property
    def active(self) -> list[Node]:
        return [n for n in self.nodes if n.enabled]

    def validate(self, known_roles: set[str] | None = None) -> list[str]:
        problems: list[str] = []

        seen_names: dict[str, int] = {}
        seen_ips: dict[str, int] = {}
        for n in self.nodes:
            seen_names[n.hostname] = seen_names.get(n.hostname, 0) + 1
            seen_ips[n.ip] = seen_ips.get(n.ip, 0) + 1
        for name, count in seen_names.items():
            if count > 1:
                problems.append(f"hostname {name!r} is defined {count} times")
        for ip, count in seen_ips.items():
            if count > 1:
                problems.append(f"address {ip} is assigned to {count} nodes")

        # Two nodes must not claim the same port unless they are on different hosts,
        # which they are by definition - so this only catches a node colliding with
        # the LAN, handled per-node. What we check here is the SSH key existing,
        # because every node depends on it and a missing key fails at flash time.
        if not self.ssh_pubkey_path.exists():
            problems.append(
                f"ssh_pubkey_path {self.ssh_pubkey_path} does not exist - "
                "run `piwiz keygen` to make one before flashing anything"
            )
        elif not self.ssh_pubkey_path.read_text(encoding="utf-8").strip().startswith(
            ("ssh-ed25519", "ssh-rsa", "ecdsa-sha2")
        ):
            problems.append(
                f"ssh_pubkey_path {self.ssh_pubkey_path} does not look like a public key "
                "- did you point it at the PRIVATE key by mistake?"
            )

        if self.admin_user in {"pi", "root", "admin"}:
            problems.append(
                f"admin_user {self.admin_user!r} is a default or guessable name; "
                "pick something else - these Pis will be reachable from the whole LAN"
            )

        for n in self.nodes:
            problems.extend(n.validate(self.network, known_roles))

        return problems

    def assert_valid(self, known_roles: set[str] | None = None) -> None:
        problems = self.validate(known_roles)
        if problems:
            raise FleetError(
                "fleet.toml has "
                + str(len(problems))
                + " problem(s):\n  - "
                + "\n  - ".join(problems)
            )

    def next_free_ip(self) -> str:
        taken = {n.last_octet for n in self.nodes} | OBSERVED_IN_USE
        lo, hi = self.network.static_range
        for octet in range(lo, hi + 1):
            if octet not in taken:
                base = str(self.network.cidr.network_address).rsplit(".", 1)[0]
                return f"{base}.{octet}"
        raise FleetError(
            f"no free address in the static range .{lo}-.{hi}; widen it in fleet.toml"
        )


def _require(table: dict[str, Any], key: str, where: str) -> Any:
    if key not in table:
        raise FleetError(f"{where}: missing required key {key!r}")
    return table[key]


def load(path: str | Path) -> Fleet:
    path = Path(path)
    if not path.exists():
        raise FleetError(f"{path} does not exist - run `piwiz init` to create one")

    with path.open("rb") as fh:
        data = tomllib.load(fh)

    net_raw = _require(data, "network", str(path))
    cidr = ipaddress.IPv4Network(_require(net_raw, "cidr", "[network]"), strict=False)
    static_lo, static_hi = net_raw.get("static_range", [100, 130])

    network = Network(
        cidr=cidr,
        gateway=ipaddress.IPv4Address(_require(net_raw, "gateway", "[network]")),
        dns=[str(d) for d in net_raw.get("dns", [str(cidr.network_address + 1)])],
        domain=net_raw.get("domain", "lan"),
        static_range=(int(static_lo), int(static_hi)),
    )

    fleet_raw = _require(data, "fleet", str(path))
    cache = fleet_raw.get("image_cache")

    fleet = Fleet(
        network=network,
        admin_user=_require(fleet_raw, "admin_user", "[fleet]"),
        ssh_pubkey_path=Path(_require(fleet_raw, "ssh_pubkey_path", "[fleet]")).expanduser(),
        timezone=fleet_raw.get("timezone", "Australia/Melbourne"),
        locale=fleet_raw.get("locale", "en_AU.UTF-8"),
        keyboard=fleet_raw.get("keyboard", "us"),
        wifi_country=fleet_raw.get("wifi_country", "AU"),
        image_cache=Path(cache).expanduser() if cache else None,
        source=path,
    )

    for entry in data.get("node", []):
        fleet.nodes.append(
            Node(
                hostname=_require(entry, "hostname", "[[node]]"),
                hardware=_require(entry, "hardware", "[[node]]"),
                ip=_require(entry, "ip", "[[node]]"),
                roles=[str(r) for r in entry.get("roles", [])],
                boot=entry.get("boot", "sd"),
                mac=entry.get("mac", ""),
                ports=[int(p) for p in entry.get("ports", [])],
                notes=entry.get("notes", ""),
                enabled=bool(entry.get("enabled", True)),
                image=entry.get("image", "raspios-lite"),
            )
        )

    return fleet
