#!/usr/bin/env bash
# canary - the node whose entire job is to distrust the others.
#
# WHY THIS IS GENUINELY PI-SHAPED WORK
#
# Almost everything else in this plan is better hosted on the NUC, the Synology or
# the workbench, because they are faster and already running. This role is the
# exception, and the reason is not performance - it is independence.
#
#   * A backup checked by the process that wrote it is not checked.
#   * A share monitored from the machine that exports it cannot detect the case
#     where the export is fine but nothing on the network can reach it.
#   * An alert that travels through Home Assistant cannot tell you Home Assistant
#     is down.
#
# So this node is deliberately small, boring, and coupled to nothing. It writes
# almost nothing, so an SD card is genuinely fine here.
#
# THE MOST VALUABLE CHECK IS THE LEAST GLAMOROUS
#
# Writing a timestamped file to every SMB share and NFS export every fifteen
# minutes and reading it back catches the failure that actually happens: a share
# that has silently gone read-only, an export whose session died at 3am, a disk
# that has filled. On a workbench with three volumes over 98% full, "the write
# failed" is not hypothetical.
#
# SILENCE IS THE ALARM
#
# Every check publishes with a retained MQTT message and a timestamp. A check that
# stops publishing is itself the signal - which is the only design that survives
# this node dying. Home Assistant sees the timestamp stop advancing.

set -Eeuo pipefail
ROLE_NAME=canary
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

CANARY_DIR=/etc/pi-rack/canary
STATE=/var/lib/pi-rack/canary
PORT=5115

setup_dirs() {
    mkdir -p "$CANARY_DIR" "$STATE" /mnt/canary
    chmod 0750 "$CANARY_DIR"
}

# Targets live in a file, not in this script, so adding a share is an edit and a
# timer run rather than a re-flash.
seed_targets() {
    local f="$CANARY_DIR/targets.conf"
    [ -s "$f" ] && { log "targets.conf exists, leaving it"; return 0; }
    cat > "$f" <<'CONF'
# One target per line:  <kind> <name> <spec>
#
#   smb  <name>  //host/share            (credentials from creds-<name>)
#   nfs  <name>  host:/export
#   http <name>  http://host:port/path   (expects 2xx/3xx)
#   tcp  <name>  host:port
#
# Lines starting with # are ignored. Addresses were verified on the LAN
# 2026-08-28; re-check them if anything moves.

# --- the things whose failure is expensive -------------------------------------
nfs   nas-restic     192.168.1.83:/volume1/restic
# smb  workbench-k   //192.168.1.32/K          <- needs creds-workbench-k, see below
# smb  nas-media     //192.168.1.83/media      <- needs creds-nas-media

# --- the things whose silence is the first symptom -----------------------------
http  home-assistant http://192.168.1.75:8123/
http  frigate        http://192.168.1.70:5000/api/version
http  agent-deck     http://192.168.1.42:5080/
tcp   mqtt           192.168.1.75:1883
tcp   hypervisor     192.168.1.66:22
tcp   nas-dsm        192.168.1.83:5001
CONF
    chmod 0640 "$f"

    cat > "$CANARY_DIR/creds-EXAMPLE" <<'CONF'
# Copy to creds-<name> matching the target name, chmod 0600.
# These are read by mount.cifs, so the format is exactly what it expects.
username=canary
password=CHANGEME
domain=WORKGROUP
CONF
    chmod 0600 "$CANARY_DIR/creds-EXAMPLE"
    log "seeded $f - edit it, then add creds-<name> files for any SMB targets"
}

install_prober() {
    cat > /usr/local/lib/pi-rack/canary-probe.sh <<'PROBE'
#!/usr/bin/env bash
# Probe every target. Report each result to MQTT with a retained message.
#
# Deliberately does NOT exit non-zero on a failed target: one dead share must not
# stop the other nine being checked, and systemd marking the unit failed would
# hide which target it was.
set -Eeuo pipefail
. /etc/pi-rack.env 2>/dev/null || true
CANARY_DIR=/etc/pi-rack/canary
STATE=/var/lib/pi-rack/canary
LOG=/var/log/pi-rack-canary.log
MNT=/mnt/canary
STAMP="$(date -Is)"

exec >>"$LOG" 2>&1

publish() {  # publish <name> <status> <detail> <ms>
    [ -r /etc/pi-rack-mqtt.env ] || return 0
    # shellcheck source=/dev/null
    . /etc/pi-rack-mqtt.env
    command -v mosquitto_pub >/dev/null || return 0
    mosquitto_pub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" \
        -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "pi-rack/canary/$1" -r \
        -m "{\"status\":\"$2\",\"detail\":\"$3\",\"ms\":$4,\"at\":\"$STAMP\"}" \
        2>/dev/null || true
}

record() {  # record <name> <status> <detail> <ms>
    printf '%s %-16s %-4s %5sms %s\n' "$STAMP" "$1" "$2" "$4" "$3"
    echo "$2" > "$STATE/$1.status"
    publish "$1" "$2" "$3" "$4"
}

# Round-trip a real file: write, sync, read back, compare. A share that mounts but
# cannot be written to is the failure this catches, and a read-only check misses it.
roundtrip() {  # roundtrip <name> <mountpoint>
    local name="$1" mp="$2"
    local f="$mp/.pi-rack-canary-${PI_RACK_HOSTNAME:-pi}"
    local payload="canary $STAMP $RANDOM"
    if ! echo "$payload" > "$f" 2>/dev/null; then
        echo "write failed"; return 1
    fi
    sync -f "$f" 2>/dev/null || true
    local got
    got="$(cat "$f" 2>/dev/null || true)"
    rm -f "$f" 2>/dev/null || true
    if [ "$got" != "$payload" ]; then
        echo "read-back mismatch"; return 1
    fi
    return 0
}

while read -r kind name spec _rest; do
    case "$kind" in ''|\#*) continue ;; esac
    start=$(date +%s%3N)
    mp="$MNT/$name"
    mkdir -p "$mp"
    status=fail detail=""

    case "$kind" in
      smb)
        creds="$CANARY_DIR/creds-$name"
        if [ ! -r "$creds" ]; then
            detail="no credentials file $creds"
        elif mount -t cifs "$spec" "$mp" -o "credentials=$creds,vers=3.0,noserverino" 2>/dev/null; then
            if detail="$(roundtrip "$name" "$mp")"; then status=ok; detail="round-trip ok"; fi
            umount "$mp" 2>/dev/null || umount -l "$mp" 2>/dev/null || true
        else
            detail="mount failed"
        fi
        ;;
      nfs)
        if mount -t nfs "$spec" "$mp" -o "soft,timeo=50,retrans=2" 2>/dev/null; then
            if detail="$(roundtrip "$name" "$mp")"; then status=ok; detail="round-trip ok"; fi
            umount "$mp" 2>/dev/null || umount -l "$mp" 2>/dev/null || true
        else
            detail="mount failed"
        fi
        ;;
      http)
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$spec" || echo 000)"
        if [ "$code" -ge 200 ] && [ "$code" -lt 400 ]; then
            status=ok; detail="HTTP $code"
        else
            detail="HTTP $code"
        fi
        ;;
      tcp)
        host="${spec%:*}"; port="${spec##*:}"
        if timeout 5 bash -c ">/dev/tcp/$host/$port" 2>/dev/null; then
            status=ok; detail="connect ok"
        else
            detail="no connect"
        fi
        ;;
      *) detail="unknown kind $kind" ;;
    esac

    ms=$(( $(date +%s%3N) - start ))
    record "$name" "$status" "${detail:-}" "$ms"
done < "$CANARY_DIR/targets.conf"

# A heartbeat for this node itself. If THIS stops advancing, the canary is dead -
# which is exactly the case a canary cannot report on its own behalf.
publish "_heartbeat" ok "canary alive" 0
PROBE
    chmod 0750 /usr/local/lib/pi-rack/canary-probe.sh
    install -d -m 0755 /usr/local/lib/pi-rack
}

install_timers() {
    write_unit pi-rack-canary.service <<'UNIT'
[Unit]
Description=Probe every share and service, report to MQTT
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/pi-rack/canary-probe.sh
# Mounting needs root. Everything else here is deliberately unprivileged work.
User=root
UNIT

    write_unit pi-rack-canary.timer <<'UNIT'
[Unit]
Description=Run the canary probes every 15 minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=15min
# Do NOT set Persistent=true: a missed run while the node was off is not
# information worth replaying, and a burst of catch-up mounts on boot is noise.
AccuracySec=30s

[Install]
WantedBy=timers.target
UNIT
    enable_now pi-rack-canary.timer
}

# A status page, so "is anything broken" is answerable from a phone without
# depending on Home Assistant being up - which is half the point of this node.
install_status_page() {
    cat > /usr/local/lib/pi-rack/canary-status.py <<'PY'
#!/usr/bin/env python3
"""Tiny status page. Reads the last result of each probe off disk.

Stdlib only, no framework: this must keep working on a node that is otherwise
untouched for a year, and every dependency is a thing that can break during an
unattended upgrade.
"""
import http.server, pathlib, socketserver, datetime

STATE = pathlib.Path("/var/lib/pi-rack/canary")
LOG = pathlib.Path("/var/log/pi-rack-canary.log")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rows, bad = [], 0
        for f in sorted(STATE.glob("*.status")):
            status = f.read_text().strip()
            when = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            age = (datetime.datetime.now() - when).total_seconds()
            # Stale counts as bad. A probe that stopped running is not "ok".
            stale = age > 3600
            if status != "ok" or stale:
                bad += 1
            rows.append(
                f"<tr class='{'bad' if status != 'ok' or stale else 'ok'}'>"
                f"<td>{f.stem}</td><td>{status}</td>"
                f"<td>{int(age // 60)} min ago{' STALE' if stale else ''}</td></tr>"
            )
        tail = ""
        if LOG.exists():
            tail = "".join(LOG.read_text(errors="replace").splitlines(True)[-25:])
        body = f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>canary</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;background:#111;color:#eee;
margin:0;padding:1.2rem;max-width:44rem}}
h1{{font-size:1.2rem}}table{{width:100%;border-collapse:collapse}}
td{{padding:.35rem .5rem;border-bottom:1px solid #333}}
.ok td:nth-child(2){{color:#6c6}}.bad td:nth-child(2){{color:#f66;font-weight:600}}
pre{{background:#000;padding:.8rem;overflow-x:auto;font-size:12px}}</style>
<h1>canary &mdash; {bad} failing of {len(rows)}</h1>
<table>{''.join(rows) or '<tr><td>no probes have run yet</td></tr>'}</table>
<h2 style="font-size:1rem">recent</h2><pre>{tail}</pre>"""
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", 5115), Handler) as srv:
    srv.serve_forever()
PY
    chmod 0755 /usr/local/lib/pi-rack/canary-status.py

    write_unit pi-rack-canary-status.service <<'UNIT'
[Unit]
Description=canary status page
After=network.target

[Service]
ExecStart=/usr/local/lib/pi-rack/canary-status.py
Restart=on-failure
RestartSec=10
User=nobody
Group=nogroup
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
UNIT
    enable_now pi-rack-canary-status.service
}

once dirs     setup_dirs
once targets  seed_targets
once prober   install_prober
once timers   install_timers
once status   install_status_page

# Run once immediately so there is something on the page before the first timer fire.
systemctl start pi-rack-canary.service || true
announce online

log "done."
log "  Status:  http://${PI_RACK_IP}:${PORT}"
log "  Targets: ${CANARY_DIR}/targets.conf   (edit, then: systemctl start pi-rack-canary)"
log "  SMB targets need a creds-<name> file at 0600 before they will pass."
log "  Set /etc/pi-rack-mqtt.env to get these into Home Assistant."
