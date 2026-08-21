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
PKG = ROOT / "homeassistant" / "packages" / "wall_clock.yaml"
FW = ROOT / "esphome" / "wall-clock.yaml"


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(node, str) and ("{{" in node or "{%" in node):
        yield path, node


def main() -> int:
    doc = yaml.safe_load(PKG.read_text())
    print(f"YAML OK — top-level keys: {', '.join(doc)}")

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
    for path, tpl in walk(doc):
        total += 1
        try:
            env.parse(tpl)
        except TemplateSyntaxError as exc:
            bad += 1
            print(f"  TEMPLATE SYNTAX ERROR at {path}: line {exc.lineno}: {exc.message}")
    print(f"Jinja templates: {total} checked, {bad} with syntax errors")

    # Contract: firmware subscriptions must be satisfied by the package.
    wanted = sorted(set(re.findall(
        r"entity_id:\s*((?:sensor|binary_sensor|input_boolean)\.wall_clock_\w+)",
        FW.read_text())))
    provided = {
        f"{dom}.{e['name'].lower().replace(' ', '_')}"
        for blk in doc["template"]
        for dom in ("sensor", "binary_sensor")
        for e in blk.get(dom, [])
    }
    missing = [w for w in wanted if w not in provided]
    print(f"Firmware subscriptions: {len(wanted)} checked, {len(missing)} unsatisfied")
    for m in missing:
        print(f"  MISSING: {m} — firmware subscribes to it, package does not create it")

    if bad or missing:
        print("\nFAILED")
        return 1
    print("\nAll checks passed. Now run `ha core check` on the HA box — that is "
          "the one that sees your real entities.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
