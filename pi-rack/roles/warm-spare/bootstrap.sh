#!/usr/bin/env bash
# warm-spare - standby for the Frigate box at 192.168.1.70.
#
# WHY THIS ROLE EXISTS AT ALL, RATHER THAN JUST A BOARD ON A SHELF
#
# A cold spare is a board you will quietly repurpose in three weeks, and an
# untested spare is a story you tell yourself. The difference between a spare and
# a labelled board telling a lie is that someone has proved it can take over. So
# this role does exactly three things:
#
#   1. Keeps itself patched, so it is not two years behind on the day it is needed.
#   2. Pulls the Frigate image and a COPY of the production config on a timer, so
#      the slow parts of a failover are already done.
#   3. Nags - loudly, into Home Assistant - if nobody has run a real drill in a year.
#
# WHAT IT DELIBERATELY DOES NOT DO
#
# It does not run Frigate. Two Frigate instances pointed at the same six cameras
# and the same MQTT broker is a genuinely confusing outage: doubled detections,
# doubled notifications, and two writers to the same recordings path. The takeover
# is a deliberate human act, and the script below is the runbook, not a trigger.
#
# It also cannot take over on its own even if it wanted to: there is exactly ONE
# Coral TPU and it is plugged into .70. That is not a flaw in this design, it is
# the honest shape of the situation, and the failover procedure says so in step 1.
#
# THE UNVERIFIED FACT THIS ALL RESTS ON
#
# Nobody has checked what .70 boots from or how much RAM it has. If this board
# does not match, it is not a spare. The preflight below checks and refuses to
# report itself ready if it cannot confirm.

set -Eeuo pipefail
ROLE_NAME=warm-spare
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

PROD_HOST=192.168.1.70
PROD_PORT=5000
SPARE_DIR=/srv/frigate-spare
STATE=/var/lib/pi-rack/warm-spare

require_ram 3500

setup_dirs() {
    mkdir -p "$SPARE_DIR/config" "$SPARE_DIR/media" "$STATE"
}

# Compare ourselves against production and record the verdict. This is the check
# that turns "I have a spare" into a dated fact.
preflight() {
    local ok=1
    local our_ram prod_ver

    our_ram="$(ram_mb)"
    log "this board: $(model), ${our_ram} MB RAM, / on $(findmnt -no SOURCE /)"

    if prod_ver="$(curl -fsS --max-time 10 "http://${PROD_HOST}:${PROD_PORT}/api/version" 2>/dev/null)"; then
        log "production Frigate at ${PROD_HOST} is up, version ${prod_ver}"
        echo "$prod_ver" > "$STATE/prod_version"
    else
        log "WARNING: could not reach production Frigate at ${PROD_HOST}:${PROD_PORT}"
        ok=0
    fi

    # The two facts that decide whether this board is insurance or decoration.
    # They need SSH access to .70, which this node may not have - so a failure
    # here is a loud unknown, not a silent pass.
    if ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
           "${PROD_HOST}" 'free -m | awk "/Mem:/{print \$2}"; findmnt -no SOURCE /' \
           > "$STATE/prod_facts" 2>/dev/null; then
        local prod_ram prod_root
        prod_ram="$(head -1 "$STATE/prod_facts")"
        prod_root="$(tail -1 "$STATE/prod_facts")"
        log "production: ${prod_ram} MB RAM, / on ${prod_root}"

        if [ "$our_ram" -lt $(( prod_ram - 512 )) ]; then
            log "MISMATCH: this board has ${our_ram} MB, production has ${prod_ram} MB."
            log "          Frigate at .70 already sits at ~80% memory. This board"
            log "          would OOM under the same six cameras. It is NOT a spare."
            ok=0
        fi
        case "$prod_root" in
            /dev/mmcblk*) log "production boots from SD - a cloned card is a valid spare" ;;
            /dev/nvme*)   log "production boots from NVMe - this board needs the same base and stick" ;;
            *)            log "production boots from ${prod_root}" ;;
        esac
    else
        log "COULD NOT READ PRODUCTION FACTS over SSH."
        log "Run this by hand and record the answer in BUILD-LOG.md:"
        log "  ssh ${PROD_HOST} 'lsblk; free -h'"
        ok=0
    fi

    echo "$ok" > "$STATE/preflight_ok"
    if [ "$ok" = 1 ]; then
        log "PREFLIGHT PASSED - this board is a credible spare"
    else
        log "PREFLIGHT INCOMPLETE - do not count on this board until the above is resolved"
    fi
}

# Pull the image and a copy of production config so the slow parts are pre-done.
warm_up() {
    docker_install
    docker pull ghcr.io/blakeblackshear/frigate:stable >>"$PI_RACK_LOG" 2>&1 || \
        log "could not pull the Frigate image (no internet?) - retry later"

    # A COPY of the config, never a live mount. If this node could write to
    # production's config, it would no longer be a spare, it would be a risk.
    if scp -o BatchMode=yes -o ConnectTimeout=8 \
           "${PROD_HOST}:/opt/frigate/config/config.yml" \
           "$SPARE_DIR/config/config.yml.from-prod" >>"$PI_RACK_LOG" 2>&1; then
        log "copied production config (as .from-prod - review before using)"
    else
        log "could not copy production config; put a known-good copy in"
        log "  $SPARE_DIR/config/config.yml.from-prod  by hand"
    fi
}

write_runbook() {
    cat > "$SPARE_DIR/FAILOVER.md" <<'RUNBOOK'
# Failing over from .70 to this board

Read the whole thing before starting. Two Frigate instances on the same cameras
and the same MQTT broker is a worse outage than no Frigate at all.

## 0. Confirm .70 is actually dead

Not slow, not rebooting. `ping`, then the web UI, then power. If .70 comes back
mid-failover you get doubled detections and two writers to the same recordings.

## 1. Move the Coral

There is exactly one Coral USB TPU and it is in .70. Unplug it and plug it in
here. **Without it, detection falls back to CPU** and six cameras will not keep
up — expect `skipped_fps` above zero immediately, which is the number that says
frames are being dropped.

## 2. Take the address

Frigate is referenced by IP in Home Assistant and elsewhere. Either move the DHCP
reservation for `192.168.1.70` to this board's MAC, or set `.70` statically here.
Do **not** leave both boards claiming it.

## 3. Bring up the config

    cp config/config.yml.from-prod config/config.yml
    # review it: paths, camera credentials, the detector block
    docker compose up -d

## 4. Verify — do not assume

    curl -s http://localhost:5000/api/stats | jq '.detectors, .cameras'

`skipped_fps` must be `0.0` on every camera. If it is not, the Coral is not being
used, or this board is not keeping up. Check `.detectors` shows the Coral and an
inference speed near 10 ms — CPU detection shows tens of milliseconds.

Then confirm in Home Assistant that the camera entities are back and Alarmo is
seeing motion.

## 5. Write it down

Add a dated entry to `BUILD-LOG.md`: what failed, how long the failover took, and
what was missing from this runbook. The timing is the point — a drill you did not
time tells you nothing about whether this is viable at 2am.
RUNBOOK

    cat > "$SPARE_DIR/docker-compose.yml" <<'COMPOSE'
# NOT started automatically. See FAILOVER.md - bringing this up while .70 is alive
# gives you two Frigates on the same cameras and the same broker.
services:
  frigate:
    container_name: frigate
    image: ghcr.io/blakeblackshear/frigate:stable
    restart: unless-stopped
    privileged: true          # required for the Coral USB device
    shm_size: "256mb"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./config:/config
      - ./media:/media/frigate
      - type: tmpfs
        target: /tmp/cache
        tmpfs:
          size: 1000000000
    ports:
      - "5000:5000"
      - "8554:8554"
      - "8555:8555/tcp"
      - "8555:8555/udp"
COMPOSE
    log "runbook and compose file written to $SPARE_DIR"
}

# The nag. A spare nobody has drilled is not a spare.
install_drill_reminder() {
    install -d -m 0755 /usr/local/lib/pi-rack
    cat > /usr/local/lib/pi-rack/spare-check.sh <<'CHECK'
#!/usr/bin/env bash
set -Eeuo pipefail
. /etc/pi-rack.env 2>/dev/null || true
STATE=/var/lib/pi-rack/warm-spare
DRILL="$STATE/last_drill"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get -qq -y upgrade >/dev/null 2>&1 || true
docker pull ghcr.io/blakeblackshear/frigate:stable >/dev/null 2>&1 || true
date -Is > "$STATE/last_patched"

days=9999
[ -r "$DRILL" ] && days=$(( ( $(date +%s) - $(date -d "$(cat "$DRILL")" +%s) ) / 86400 ))

status=ok
[ "$days" -gt 365 ] && status=stale

if [ -r /etc/pi-rack-mqtt.env ]; then
    # shellcheck source=/dev/null
    . /etc/pi-rack-mqtt.env
    command -v mosquitto_pub >/dev/null && mosquitto_pub \
        -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "pi-rack/${PI_RACK_HOSTNAME}/spare" -r \
        -m "{\"status\":\"$status\",\"days_since_drill\":$days,\"at\":\"$(date -Is)\"}" || true
fi

if [ "$status" = stale ]; then
    echo "WARM SPARE HAS NOT BEEN DRILLED IN $days DAYS."
    echo "Run the drill in /srv/frigate-spare/FAILOVER.md, time it, then:"
    echo "  date -Is | sudo tee $DRILL"
fi
CHECK
    chmod 0750 /usr/local/lib/pi-rack/spare-check.sh

    write_unit pi-rack-spare-check.service <<'UNIT'
[Unit]
Description=Keep the warm spare current and nag if it has never been drilled
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/pi-rack/spare-check.sh
UNIT

    write_unit pi-rack-spare-check.timer <<'UNIT'
[Unit]
Description=Weekly warm-spare currency check

[Timer]
OnCalendar=Mon *-*-* 04:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
UNIT
    enable_now pi-rack-spare-check.timer
}

once dirs      setup_dirs
once warmup    warm_up
once runbook   write_runbook
once drill     install_drill_reminder
preflight
announce online

log "done. This board is a STANDBY - Frigate is installed but NOT running."
log "  Runbook:   $SPARE_DIR/FAILOVER.md"
log "  Preflight: $(cat "$STATE/preflight_ok" 2>/dev/null || echo '?') (1 = credible spare)"
log "  Record a drill:  date -Is | sudo tee $STATE/last_drill"
