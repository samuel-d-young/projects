#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalise_entity_ids.py — put every entity of every clock back under its slug.

    python normalise_entity_ids.py            # rename, and say what was renamed
    python normalise_entity_ids.py --dry-run  # only say

WHY THIS EXISTS
---------------
`build_clock_dashboard.py` addresses every control as `<kind>.<slug>_<key>`,
where the slug is the ESPHome device name (`mini_round_clock_3`). That held
while a clock's entities were all created at once. It stops holding the first
time a firmware update ADDS entities: Home Assistant names a new ESPHome entity
after the device's *friendly name* at the moment it appears, so the night-sky
controls, the message, the board LED and the safe-mode button that arrived with
the 2026-09-15 flash registered as `switch.zac_s_clock_grow_clock_night_sky`
and friends — and the dashboard rows for them read "Entity not found" while
the older 112 entities of the same clock kept `mini_round_clock_3_*`.

Renaming a device's friendly name back would not help (ids are only assigned
once), and teaching the generator two prefixes per clock means knowing which
entity arrived when. So: after any flash that adds entities, run this. It
looks up each clock in CLOCKS by its Home Assistant device name (the label),
finds every entity on that device whose id does not start with the slug, and
renames it to `<kind>.<slug>_<rest>` where `<rest>` is what followed the
friendly-name prefix. Names, history and the dashboard are untouched — only
the id changes, exactly as Settings → Entities → rename would.

Needs the home-assistant repo's admin client for the WebSocket registry call
(the REST API cannot rename entities) and its long-lived token in
`K:\\Claude\\home-assistant\\.token`.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "dashboards"))
sys.path.insert(0, r"K:\Claude\home-assistant\tools")
from build_clock_dashboard import CLOCKS  # noqa: E402
from hass import Ws, load_token  # noqa: E402

HOST, PORT = "192.168.1.75", 8123


def slugify(name: str) -> str:
    """Home Assistant's own rule for turning a friendly name into an id prefix."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def main() -> int:
    dry = "--dry-run" in sys.argv
    async with Ws(HOST, PORT, load_token()) as ws:
        devices = await ws.cmd("config/device_registry/list")
        entities = await ws.cmd("config/entity_registry/list")
        taken = {e["entity_id"] for e in entities}
        renamed = 0
        for clock in CLOCKS:
            slug, label = clock["slug"], clock["label"]
            dev = [d for d in devices if (d.get("name_by_user") or d.get("name")) == label]
            if not dev:
                print(f"  {label}: no device by that name in Home Assistant - skipped")
                continue
            mine = [e for e in entities if e.get("device_id") == dev[0]["id"]]
            fprefix = slugify(label) + "_"
            off = [e for e in mine if not e["entity_id"].split(".", 1)[1].startswith(slug + "_")]
            print(f"  {label}: {len(mine)} entities, {len(off)} off-slug")
            for e in off:
                kind, obj = e["entity_id"].split(".", 1)
                if not obj.startswith(fprefix):
                    print(f"    ? {e['entity_id']}: neither slug nor friendly-name prefix - left alone")
                    continue
                new = f"{kind}.{slug}_{obj[len(fprefix):]}"
                if new in taken:
                    print(f"    ! {e['entity_id']} -> {new} already exists - left alone")
                    continue
                print(f"    {'would rename' if dry else 'rename'} {e['entity_id']} -> {new}")
                if not dry:
                    await ws.cmd("config/entity_registry/update", entity_id=e["entity_id"], new_entity_id=new)
                    taken.add(new)
                    renamed += 1
        print(f"  {'dry run, nothing changed' if dry else f'{renamed} renamed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
