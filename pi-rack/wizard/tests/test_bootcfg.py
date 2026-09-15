"""Tests for cloud-init seed rendering and role bundling.

    python wizard/tests/test_bootcfg.py

These assert the properties that, if wrong, produce a Pi you have to physically
retrieve: no login, no network, or a stock `pi` account left enabled.
"""

from __future__ import annotations

import ipaddress
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piwiz import bootcfg, roles as roles_mod  # noqa: E402
from piwiz.fleet import Fleet, Network, Node  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


TMP = Path(tempfile.mkdtemp(prefix="piwiz-test-"))
KEY = TMP / "id_test.pub"
KEY.write_text(
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMb50hbWHK6UhF87Riqn+hU6NOFGw5LEw/53m9CzQ6Q5 test\n",
    encoding="utf-8",
)


def make_fleet(**kw) -> Fleet:
    base = dict(
        network=Network(
            cidr=ipaddress.IPv4Network("192.168.1.0/24"),
            gateway=ipaddress.IPv4Address("192.168.1.1"),
            dns=["192.168.1.1"],
            domain="lan",
            static_range=(100, 130),
        ),
        admin_user="vultron",
        ssh_pubkey_path=KEY,
        timezone="Australia/Melbourne",
        locale="en_AU.UTF-8",
        keyboard="us",
        wifi_country="AU",
    )
    base.update(kw)
    return Fleet(**base)


def make_node(**kw) -> Node:
    base = dict(hostname="rack-one", hardware="pi4-4gb", ip="192.168.1.101", roles=["base"])
    base.update(kw)
    return Node(**base)


F = make_fleet()
N = make_node()


print("\n[1] user-data: the properties that keep a node reachable and safe")
ud = bootcfg.render_user_data(F, N)
check("starts with the #cloud-config marker (cloud-init ignores it otherwise)",
      ud.splitlines()[0] == "#cloud-config", repr(ud.splitlines()[0]))

if yaml:
    d = yaml.safe_load(ud)
    check("parses as YAML", isinstance(d, dict))
    check("hostname set", d.get("hostname") == "rack-one", d.get("hostname"))
    check("ssh_pwauth is False", d.get("ssh_pwauth") is False, d.get("ssh_pwauth"))
    check("disable_root is True", d.get("disable_root") is True)
    names = [u["name"] for u in d["users"]]
    check("exactly one user, the admin", names == ["vultron"], names)
    check("'default' NOT in users, so the stock pi account is never created",
          "default" not in d["users"])
    check("admin password is locked", d["users"][0]["lock_passwd"] is True)
    check("admin has the ssh key", d["users"][0]["ssh_authorized_keys"][0].startswith("ssh-ed25519"))
    check("timezone", d.get("timezone") == "Australia/Melbourne")
    check("locale", d.get("locale") == "en_AU.UTF-8")
    check("package_update on", d.get("package_update") is True)
    check("package_upgrade off by default (a 15-min first boot looks like a dead card)",
          d.get("package_upgrade") is False)
else:
    print("  SKIP  YAML assertions (PyYAML not installed)")


print("\n[2] user-data refuses bad keys")
priv = TMP / "id_priv"
priv.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n",
                encoding="utf-8")
try:
    bootcfg.render_user_data(make_fleet(ssh_pubkey_path=priv), N)
    check("private key is rejected", False, "(it was accepted)")
except bootcfg.BootConfigError as exc:
    check("private key is rejected", "PRIVATE" in str(exc).upper(), str(exc))

notakey = TMP / "notakey.pub"
notakey.write_text("hello world\n", encoding="utf-8")
try:
    bootcfg.render_user_data(make_fleet(ssh_pubkey_path=notakey), N)
    check("non-key file is rejected", False, "(it was accepted)")
except bootcfg.BootConfigError:
    check("non-key file is rejected", True)


print("\n[3] network-config: static addressing")
nc = bootcfg.render_network_config(F, N)
if yaml:
    net = yaml.safe_load(nc)["network"]["ethernets"]["eth0"]
    check("version 2 netplan", yaml.safe_load(nc)["network"]["version"] == 2)
    check("dhcp4 off", net["dhcp4"] is False)
    check("address carries the prefix", net["addresses"] == ["192.168.1.101/24"], net["addresses"])
    check("default route via the gateway",
          net["routes"] == [{"to": "default", "via": "192.168.1.1"}], net["routes"])
    check("optional:false so boot waits for the link before apt runs",
          net["optional"] is False)
    check("nameservers set", net["nameservers"]["addresses"] == ["192.168.1.1"])
check("no tab characters anywhere (YAML forbids them for indentation)", "\t" not in nc)


print("\n[4] meta-data: instance_id drives re-provisioning")
m1 = bootcfg.instance_id(N, "rev1")
m2 = bootcfg.instance_id(N, "rev2")
m3 = bootcfg.instance_id(make_node(roles=["base", "dns"]), "rev1")
m4 = bootcfg.instance_id(N, "rev1")
check("stable for the same node and revision", m1 == m4, (m1, m4))
check("changes when the plan revision changes", m1 != m2)
check("changes when the node's roles change", m1 != m3)
check("is not the stock 'rpios-image' (which would skip first-boot setup)",
      "rpios-image" not in m1, m1)
md = bootcfg.render_meta_data(N, "rev1")
if yaml:
    parsed = yaml.safe_load(md)
    check("dsmode local", parsed["dsmode"] == "local")
    check("local-hostname matches", parsed["local-hostname"] == "rack-one")


print("\n[5] write_seed refuses anywhere that is not a boot partition")
notboot = TMP / "notboot"
notboot.mkdir(exist_ok=True)
try:
    bootcfg.write_seed(notboot, F, N)
    check("refuses a directory with no config.txt/cmdline.txt", False, "(it wrote there)")
except bootcfg.BootConfigError as exc:
    check("refuses a directory with no config.txt/cmdline.txt",
          "boot partition" in str(exc), str(exc))

fakeboot = TMP / "fakeboot"
fakeboot.mkdir(exist_ok=True)
(fakeboot / "config.txt").write_text("arm_64bit=1\n", encoding="utf-8")
(fakeboot / "cmdline.txt").write_text("console=tty1 rootwait\n", encoding="utf-8")
written = bootcfg.write_seed(fakeboot, F, N, plan_revision="rev1")
check("writes exactly three files", len(written) == 3, [p.name for p in written])
check("named user-data / network-config / meta-data",
      sorted(p.name for p in written) == ["meta-data", "network-config", "user-data"])
raw = (fakeboot / "user-data").read_bytes()
check("written with LF endings, not CRLF", b"\r\n" not in raw)


print("\n[5b] cmdline.txt reconciliation - the stale-instance-id trap")
# Raspberry Pi Imager appends ` ds=nocloud;i=<its id>` when it writes a seed.
# A cmdline instance id OVERRIDES meta-data, so a stale one means a re-seeded
# card boots with none of your changes and reports no error at all.
cm = fakeboot / "cmdline.txt"

cm.write_text("console=tty1 root=PARTUUID=041bba91-02 rootwait\n", encoding="utf-8")
changed = bootcfg.reconcile_cmdline(fakeboot, "pi-rack-x-abc")
check("leaves cmdline alone when there is no ds= parameter", changed is False)
check("  ...and the file is untouched", "ds=" not in cm.read_text(encoding="utf-8"))

cm.write_text(
    "console=tty1 root=PARTUUID=041bba91-02 rootwait ds=nocloud;i=rpi-imager-1750000000\n",
    encoding="utf-8",
)
changed = bootcfg.reconcile_cmdline(fakeboot, "pi-rack-rack-one-deadbeef")
after = cm.read_text(encoding="utf-8")
check("rewrites a stale Imager instance id", changed is True)
check("  ...to ours", "ds=nocloud;i=pi-rack-rack-one-deadbeef" in after, after)
check("  ...and the old id is gone", "rpi-imager-1750000000" not in after, after)
check("  ...preserving the other kernel parameters",
      "root=PARTUUID=041bba91-02" in after and "rootwait" in after, after)
check("  ...as exactly ONE line (the bootloader ignores everything after line 1)",
      after.count("\n") == 1 and after.endswith("\n"), repr(after))

changed = bootcfg.reconcile_cmdline(fakeboot, "pi-rack-rack-one-deadbeef")
check("is idempotent - no change when already correct", changed is False)

# Restore a plain cmdline for the write_seed test that follows.
cm.write_text("console=tty1 rootwait\n", encoding="utf-8")


print("\n[6] roles: bundling and the CRLF trap")
roles_dir = TMP / "roles"
(roles_dir / "demo").mkdir(parents=True, exist_ok=True)
(roles_dir / "demo" / "role.toml").write_text(
    'name = "demo"\nsummary = "a demo role"\npackages = ["tmux"]\n'
    'ports = [8123]\nmin_ram_gb = 8\nwants_boot = "usb-ssd"\n',
    encoding="utf-8",
)
(roles_dir / "demo" / "bootstrap.sh").write_text(
    "#!/usr/bin/env bash\nset -Eeuo pipefail\necho demo\n", encoding="utf-8", newline="\n"
)
# Every bootstrap.sh sources /opt/pi-rack/common.sh on its third line. If the
# library is not on the card, first boot fails on every role with a "No such file
# or directory" buried in cloud-init's output. It must be bundled, and it must be
# written BEFORE the scripts that source it.
common_dir = TMP / "bootstrap" / "lib"
common_dir.mkdir(parents=True, exist_ok=True)
(common_dir / "common.sh").write_text(
    "#!/usr/bin/env bash\n# shared helpers\nonce() { :; }\n", encoding="utf-8", newline="\n"
)

cat = roles_mod.load_all(roles_dir)
check("role loads", "demo" in cat)
check("packages parsed", cat["demo"].packages == ["tmux"])

node = make_node(hardware="pi4-2gb", roles=["demo"], boot="sd")
bundle, warns = roles_mod.bundle_for(node, cat)
check("warns that 2 GB is under the role's 8 GB floor",
      any("8 GB" in w and "2 GB" in w for w in warns), warns)
check("warns that the role wants an SSD but the node is on SD",
      any("usb-ssd" in w for w in warns), warns)
check("warns that port 8123 is already Home Assistant",
      any("8123" in w and "Home Assistant" in w for w in warns), warns)
check("bundle carries the role's packages", "tmux" in bundle.packages)
paths = [p for p, _c, _m in bundle.write_files]
check("bundle writes the shared library", "/opt/pi-rack/common.sh" in paths, paths)
check("  ...BEFORE the role scripts that source it",
      paths.index("/opt/pi-rack/common.sh") < paths.index("/opt/pi-rack/demo.sh"), paths)
check("bundle writes the identity file", "/etc/pi-rack.env" in paths, paths)
check("bundle writes the role script", "/opt/pi-rack/demo.sh" in paths, paths)

# A role with no bootstrap.sh has nothing to source, so the library is not needed.
(roles_dir / "noscript").mkdir(exist_ok=True)
(roles_dir / "noscript" / "role.toml").write_text(
    'name = "noscript"\nsummary = "metadata only"\npackages = ["tree"]\n', encoding="utf-8"
)
cat2 = roles_mod.load_all(roles_dir)
b2, _ = roles_mod.bundle_for(make_node(roles=["noscript"]), cat2)
check("no shared library when no role has a script",
      "/opt/pi-rack/common.sh" not in [p for p, _c, _m in b2.write_files])

# And a CRLF common.sh must be refused for the same reason a CRLF role script is.
crlf_common = TMP / "crlfbootstrap" / "bootstrap" / "lib"
crlf_common.mkdir(parents=True, exist_ok=True)
(crlf_common / "common.sh").write_bytes(b"#!/usr/bin/env bash\r\nonce() { :; }\r\n")
try:
    roles_mod.load_common(TMP / "crlfbootstrap" / "roles")
    check("CRLF common.sh is rejected", False, "(it loaded)")
except roles_mod.RoleError as exc:
    check("CRLF common.sh is rejected", "bad interpreter" in str(exc), str(exc))

try:
    roles_mod.load_common(TMP / "nowhere" / "roles")
    check("missing common.sh is a clear error", False)
except roles_mod.RoleError as exc:
    check("missing common.sh is a clear error", "no node will provision" in str(exc), str(exc))
check("runcmd invokes the role script", any("demo.sh" in c for c in bundle.runcmd), bundle.runcmd)
check("runcmd logs a named failure rather than a bare exit",
      any("ROLE-FAILED-demo" in c for c in bundle.runcmd), bundle.runcmd)

crlf_role = roles_dir / "crlf"
crlf_role.mkdir(exist_ok=True)
(crlf_role / "role.toml").write_text('name = "crlf"\nsummary = "bad endings"\n', encoding="utf-8")
(crlf_role / "bootstrap.sh").write_bytes(b"#!/usr/bin/env bash\r\necho hi\r\n")
try:
    roles_mod.load_role(crlf_role)
    check("CRLF bootstrap.sh is rejected", False, "(it loaded)")
except roles_mod.RoleError as exc:
    check("CRLF bootstrap.sh is rejected", "bad interpreter" in str(exc), str(exc))

try:
    roles_mod.bundle_for(make_node(roles=["nosuchrole"]), cat)
    check("unknown role is rejected", False)
except roles_mod.RoleError:
    check("unknown role is rejected", True)


print("\n[7] the rendered seed round-trips through YAML with a full bundle")
full = bootcfg.render_user_data(F, make_node(roles=["demo"]), bundle)
bootcfg.validate(full, "user-data")
if yaml:
    parsed = yaml.safe_load(full)
    check("write_files survives block-scalar encoding",
          any(w["path"] == "/opt/pi-rack/demo.sh" for w in parsed["write_files"]))
    script = next(w for w in parsed["write_files"] if w["path"].endswith("demo.sh"))["content"]
    check("script content preserved exactly", script.startswith("#!/usr/bin/env bash"), repr(script[:40]))
    check("script permissions are 0750", script and
          next(w for w in parsed["write_files"] if w["path"].endswith("demo.sh"))["permissions"] == "0750")
    check("env file content preserved",
          "PI_RACK_HOSTNAME=rack-one" in
          next(w for w in parsed["write_files"] if w["path"] == "/etc/pi-rack.env")["content"])


print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all bootcfg/roles tests passed")
