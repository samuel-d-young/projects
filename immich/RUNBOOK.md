# Immich — "it stopped working on my phone"

Immich runs on the **voice NUC**. This session was in Anthropic's cloud with no
route to `192.168.1.0/24`, so nothing below has been run against the real server —
it is written to be run by Samuel, or by a Claude session on his own machine.
Treat every step as **unverified against your hardware** until you report back.

Reported symptom: **the app cannot connect / the login fails.**

---

## Start here (60 seconds)

On the NUC:

```bash
bash triage.sh --login
```

From a laptop on the same wifi, if you can't get to the NUC:

```bash
bash triage.sh --scan --login
```

It reads only — it changes nothing — and ends with a VERDICT naming one of the
sections below. If you'd rather not run a script, the same fork in the road by
hand, replacing `NUC` with the NUC's address:

```bash
curl -m 5 http://NUC:2283/api/server/ping     # expect {"res":"pong"}
```

- **No response** → the server or the network is down. Sections **A**, **E**.
- **`pong`, but the phone still fails** → the server is fine and the phone is
  pointed somewhere else, or the versions disagree. Sections **C**, **D**.
- **`pong`, and login specifically fails** → sections **B**, **E**, **F**.

That single command is the whole diagnosis: it separates "can't reach the
server" from "reaches the server, can't log in", and those have no causes in
common.

---

## A. The containers aren't running

The usual case after a power cut, a reboot, or an interrupted `docker compose pull`.

```bash
docker ps -a --filter name=immich
docker compose -f /path/to/immich/docker-compose.yml ps
```

Anything not `Up`, start it and watch what it says:

```bash
docker compose up -d
docker compose logs -f immich-server
```

If a container comes up and immediately dies, don't loop on restarting it —
read the log and go to **E**.

If Docker itself isn't running (`Cannot connect to the Docker daemon`), the NUC
rebooted and Docker isn't enabled at boot:

```bash
sudo systemctl enable --now docker
```

Then make Immich survive the next reboot on its own — every service in the
compose file should carry `restart: always`.

## B. The disk is full

A photo server fills its disk as a matter of routine, and this is the cause
people miss, because **it doesn't look like a disk problem from the phone** — the
server answers `ping` normally and only the *login* fails. Postgres stops
accepting writes, and a login is a write (it creates a session row).

```bash
df -h
du -sh /path/to/UPLOAD_LOCATION/*        # from your .env
docker system df                          # old images are often several GB
```

To recover:

```bash
docker image prune -a          # safe: re-pulled on next `up`
docker builder prune
```

Then clear real space — Immich's own thumbnail/encoded-video caches can be
regenerated, so they're the safest large thing to drop from the web UI under
Administration → Jobs. Once there's headroom, restart the stack.

Postgres sometimes needs a nudge after the disk frees up: `docker compose restart`.

## C. The app is pointed at the wrong address

The most likely cause of "worked yesterday, not today, nothing changed": the
NUC's **DHCP lease moved** and the app is still calling the old IP.

In the app: **Settings → Server → Server Endpoint URL** (you may have to log out
to see it). Set it to what `triage.sh` prints at the end:

```
http://<NUC-IP>:2283
```

If the app rejects that, add the API path — older builds want it explicitly:

```
http://<NUC-IP>:2283/api
```

Also worth ruling out, in this order:

- **The phone is on mobile data**, not wifi. A `192.168.x.x` endpoint only works
  on the LAN. This is the single most common false alarm.
- **A VPN is up on the phone** (or iCloud Private Relay), routing LAN traffic out
  to the internet. Turn it off and retry.
- **The URL is `https://` but the server is plain HTTP**, or a reverse proxy in
  front has an expired certificate. Certificates expire on a 90-day cycle, which
  is exactly the shape of "it worked for months and then stopped".

**Fix it permanently:** give the NUC a **DHCP reservation** in your router, or a
static IP. Until you do, this breaks again at every lease renewal.

## D. The app and the server are on different versions

The store auto-updates the mobile app. A self-hosted server pinned to
`IMMICH_VERSION=` in `.env` does not follow it, and Immich requires the two to
match — the app refuses to log in and says so, in a message that's easy to read
as a connection failure.

Compare:

- server: `curl -s http://NUC:2283/api/server/version` (also printed by `triage.sh`)
- app: Settings → About

If they differ, upgrade the server to match the app:

```bash
cd /path/to/immich
# back the database up FIRST — see the Immich docs; upgrades run migrations
docker compose pull
docker compose up -d
```

Read the release notes between your version and the target before doing this;
Immich occasionally ships a breaking change that needs a manual step.

## E. The server is up but a dependency isn't

`ping` fails or hangs while the container shows as running. Look at what it's
complaining about:

```bash
docker compose logs --tail 200 immich-server
docker compose logs --tail 100 database
docker exec <db-container> pg_isready
```

Two failures dominate here:

- **Postgres won't accept connections.** Check the `database` container's log for
  a startup abort. If the host lost power mid-write, Postgres may need to finish
  a recovery pass — give it a few minutes before intervening.
- **Vector-extension version mismatch after an upgrade.** The log names
  `vchord`, `vectors`, or `pgvecto.rs` and says the installed extension doesn't
  match what the server expects. This happens when the server image moves ahead
  of the database image. Fix: make the `database` image in your compose file the
  one that release expects, `docker compose up -d`, and let the migration run.
  Don't drop the volume — that's your library metadata.

## F. Credentials

If `triage.sh --login` returns **401**, the server is healthy and the password is
simply wrong for that account. Reset it from the web UI at `http://NUC:2283` as
admin (Administration → Users), or if the admin password itself is lost, use
Immich's admin password reset via the server console.

Worth checking before you assume it's forgotten: is the app trying to log in to
the *right* server? An endpoint pointing at some other Immich instance produces
exactly this.

---

## Stopping the recurrence

Three changes remove most of the ways this fails:

1. **DHCP reservation for the NUC.** Removes section C entirely.
2. **Pin `IMMICH_VERSION`** and update deliberately, or the app will drift ahead
   of the server again (section D).
3. **Alert on the NUC's disk before it's full.** You already run Home Assistant
   at `192.168.1.79` — a `command_line` or SNMP sensor on the NUC's disk usage
   with an automation at 85% turns section B from an outage into a warning.

---

## Handing this to a local Claude session

This repo already carries `wall-clock/HANDOFF.md` for the same reason. Paste
this into a Claude session running **on your own machine**, on the LAN:

> Immich on my voice NUC has stopped working from the phone app — it can't
> connect / login fails. The repo is `samuel-d-young/projects`, branch
> `claude/immich-mobile-issue-grdje9`, directory `immich/`.
>
> Read `immich/RUNBOOK.md` first. Then run `bash immich/triage.sh --login` —
> from the NUC if you can reach it over SSH, otherwise with `--scan` from this
> machine. It's read-only.
>
> Work the section its VERDICT names. Don't restart containers in a loop before
> reading the logs, don't delete any Docker volume, and back the database up
> before any `docker compose pull`. Tell me what the actual cause was so I can
> record it here.
