#!/usr/bin/env python3
"""Offline checks for the wall clock HA package.

This does NOT replace `ha core check` — it cannot see your entity registry,
your areas, or whether Frigate is even installed. What it does catch, without
needing a running Home Assistant:

  1. YAML parses.
  2. Every Jinja template is syntactically valid. (HA only tells you about a
     broken template at restart, entity by entity, which is a slow way to find
     a stray {% endif %}.)
  3. The contract holds: every wall_clock_* entity the ESPHome firmware
     subscribes to is actually produced by this package. Rename one side and
     this fails immediately instead of silently leaving a dark ring.

Usage:  python3 homeassistant/test/check.py
"""
import pathlib
import re
import sys

import yaml
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError

ROOT = pathlib.Path(__file__).resolve().parents[2]   # the wall-clock/ directory
# EVERY package, and EVERY firmware -- not one of each.
#
# This checked packages/wall_clock.yaml against esphome/wall-clock.yaml, and
# both of those had moved on underneath it: the timer entities live in
# wall_clock_timers.yaml now, and the clock that is actually on the wall is
# mini-round-clock-with-display.yaml. So it reported three entities missing
# that exist, and checked none of the ones the round clock subscribes to. It
# had been failing for long enough that its output had stopped meaning
# anything, which is the state a check dies in.
PKGS = sorted((ROOT / "homeassistant" / "packages").glob("wall_clock*.yaml"))
FWS = [ROOT / "esphome" / "wall-clock.yaml",
       ROOT / "esphome" / "mini-round-clock-with-display.yaml"]
# The round clock's subscriptions are written with ${routine_slug} in them; the
# real slugs are whatever the per-device wrappers declare.
SLUGS = sorted(set(re.findall(
    r"^\s*routine_slug:\s*(\w+)",
    "\n".join(p.read_text() for p in
               (ROOT / "esphome" / "ha-device-configs").glob("*.yaml")),
    re.M))) or ["zac"]


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(node, str) and ("{{" in node or "{%" in node):
        yield path, node


class _Loader(yaml.SafeLoader):
    pass


for _tag in ("!secret", "!include", "!input", "!lambda"):
    _Loader.add_constructor(
        _tag, lambda ldr, node: ldr.construct_scalar(node)
        if isinstance(node, yaml.ScalarNode) else None)


def main() -> int:
    docs = {}
    for p in PKGS:
        docs[p.name] = yaml.load(p.read_text(), Loader=_Loader) or {}
    keys = sorted({k for d in docs.values() for k in d})
    print(f"YAML OK — {len(docs)} packages, top-level keys: {', '.join(keys)}")

    # Stub HA's template globals/filters. We are checking SYNTAX, not results.
    env = Environment(undefined=StrictUndefined)
    for f in ("as_timestamp", "as_datetime", "area_id"):
        env.filters.setdefault(f, lambda v, *a, **k: v)
    env.globals.update(
        {k: (lambda *a, **k: "") for k in
         ("states", "state_attr", "is_state", "now", "utcnow", "areas", "has_value")}
    )

    bad = 0
    total = 0
    every = [(f"{name}{path}", tpl)
             for name, d in docs.items() for path, tpl in walk(d)]
    for path, tpl in every:
        total += 1
        try:
            env.parse(tpl)
        except TemplateSyntaxError as exc:
            bad += 1
            print(f"  TEMPLATE SYNTAX ERROR at {path}: line {exc.lineno}: {exc.message}")
    print(f"Jinja templates: {total} checked, {bad} with syntax errors")

    # Contract: firmware subscriptions must be satisfied by the package.
    fw_text = "\n".join(p.read_text() for p in FWS if p.exists())
    raw = set(re.findall(
        r"entity_id:\s*((?:sensor|binary_sensor|input_boolean)\.wall_clock_[\w${}]+)",
        fw_text))
    wanted = set()
    for w in raw:                       # ${routine_slug} -> one per real clock
        wanted.update(w.replace("${routine_slug}", s) for s in SLUGS) \
            if "${routine_slug}" in w else wanted.add(w)
    wanted = sorted(wanted)
    provided = set()
    for d in docs.values():
        for blk in d.get("template", []) or []:
            for dom in ("sensor", "binary_sensor"):
                for e in blk.get(dom, []) or []:
                    if isinstance(e, dict) and e.get("name"):
                        provided.add(f"{dom}.{e['name'].lower().replace(' ', '_')}")
        for k in (d.get("input_boolean", {}) or {}):
            provided.add(f"input_boolean.{k}")
    missing = [w for w in wanted if w not in provided]
    clocks = ", ".join(SLUGS)
    print(f"Firmware subscriptions: {len(wanted)} checked across {len(FWS)} "
          f"firmwares and {len(SLUGS)} clocks ({clocks}), {len(missing)} unsatisfied")
    for m in missing:
        print(f"  MISSING: {m} — firmware subscribes to it, package does not create it")

    # ---- 4. the Settings view only names entities the firmware creates ------
    # BUILD-LOG says "all 303 clock entity references check against the 102
    # entities the firmware creates: 0 dangling" -- but that was done by hand
    # once and never became code, so the next person to add a row to the view
    # had nothing to catch a typo. A wrong entity id does not error in Home
    # Assistant; it renders a blank row, which is the kind of wrong you find
    # six weeks later.
    view = ROOT / "homeassistant" / "dashboards" / "wall-clock-settings-view.yaml"
    dangling = []
    checked = 0
    if view.exists():
        fw = yaml.load((ROOT / "esphome" /
                        "mini-round-clock-with-display.yaml").read_text(),
                       Loader=_Loader) or {}
        def names_in(node):
            """Every `name:` anywhere under one entry.

            Not just the top level: the debug platform hangs its names off
            sub-keys (`free: {name: Free heap}`), so a flat look finds nothing
            and calls six real entities dangling."""
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "name" and isinstance(v, str):
                        yield v
                    else:
                        yield from names_in(v)
            elif isinstance(node, list):
                for v in node:
                    yield from names_in(v)

        made = set()
        # text_sensor is an ESPHome domain, not a Home Assistant one: it lands
        # as sensor.<device>_<name>. So does the debug platform's device_info.
        DOMAIN = {"text_sensor": "sensor"}
        for dom in ("switch", "number", "select", "sensor", "text_sensor",
                    "binary_sensor", "text", "button", "light", "lock", "fan"):
            for e in fw.get(dom, []) or []:
                for nm in names_in(e):
                    slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
                    made.add(f"{DOMAIN.get(dom, dom)}.{{}}_{slug}")
        # the device prefixes are whatever the wrappers call the devices
        devs = sorted(set(re.findall(
            r"^\s*device_name:\s*([\w-]+)", "\n".join(
                q.read_text() for q in
                (ROOT / "esphome" / "ha-device-configs").glob("*.yaml")), re.M)))
        prefixes = [d.replace("-", "_") for d in devs]
        known = {m.format(pre) for m in made for pre in prefixes}
        for ref in re.findall(r"entity:\s*([a-z_]+\.[a-z0-9_]+)", view.read_text()):
            if not any(ref.split(".", 1)[1].startswith(pre + "_") for pre in prefixes):
                continue                      # not a clock entity; not ours to judge
            checked += 1
            if ref not in known:
                dangling.append(ref)
    print(f"Settings view: {checked} clock entity references, {len(dangling)} dangling")
    for d in sorted(set(dangling)):
        print(f"  DANGLING: {d} — the view names it, the firmware does not create it")

    if bad or missing or dangling:
        print("\nFAILED")
        return 1
    print("\nAll checks passed. Now run `ha core check` on the HA box — that is "
          "the one that sees your real entities.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
