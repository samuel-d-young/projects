#!/usr/bin/env bash
# Shared helpers for pi-rack role bootstrap scripts.
#
# Sourced, not executed:   . /opt/pi-rack/common.sh
#
# Two rules every role script here follows, both learned the hard way elsewhere
# in this workbench:
#
#   1. Idempotent. A role script may be re-run - after a failed first boot, or
#      by hand while debugging - and must not double-install, double-append or
#      double-enable anything. Use the `once` guard.
#   2. Loud on failure, in a file. cloud-init's runcmd output goes to
#      /var/log/cloud-init-output.log, which is long. Roles log to
#      /var/log/pi-rack-bootstrap.log with their own name on every line, so
#      "which role broke" is one grep, not a reading exercise.
#
# LF line endings are mandatory. A CRLF checkout puts a carriage return in the
# shebang and the Pi reports "bad interpreter: No such file or directory" with
# no hint as to why. See .gitattributes at the repo root.

set -Eeuo pipefail

PI_RACK_DIR=/opt/pi-rack
PI_RACK_STATE=/var/lib/pi-rack
PI_RACK_LOG=/var/log/pi-rack-bootstrap.log

# Populated by piwiz at flash time. Contains PI_RACK_HOSTNAME, PI_RACK_IP,
# PI_RACK_HARDWARE, PI_RACK_BOOT, PI_RACK_ROLES.
# shellcheck disable=SC1091
[ -r /etc/pi-rack.env ] && . /etc/pi-rack.env

ROLE_NAME="${ROLE_NAME:-$(basename "${BASH_SOURCE[1]:-unknown}" .sh)}"

mkdir -p "$PI_RACK_STATE" "$PI_RACK_DIR"

log() {
    printf '%s [%s] %s\n' "$(date -Is)" "$ROLE_NAME" "$*" | tee -a "$PI_RACK_LOG" >&2
}

die() {
    log "FATAL: $*"
    exit 1
}

# Report the failing line rather than just a non-zero exit.
_on_err() {
    local code=$? line=${BASH_LINENO[0]}
    log "FAILED at line ${line} (exit ${code})"
    exit "$code"
}
trap _on_err ERR

# once <tag> <command...>
#
# Runs the command only if this tag has not succeeded before. The marker is
# written AFTER success, so a crashed step is retried on the next run rather
# than silently skipped - the failure mode that makes "idempotent" scripts lie.
once() {
    local tag="$1"; shift
    local marker="$PI_RACK_STATE/done.$tag"
    if [ -e "$marker" ]; then
        log "skip $tag (done $(cat "$marker"))"
        return 0
    fi
    log "run $tag"
    "$@"
    date -Is > "$marker"
    log "ok $tag"
}

# apt_install <packages...>  - quiet, non-interactive, retried.
# apt on a Pi that has just booted often races DNS or an unattended-upgrade
# lock; one retry loop removes most first-boot flakiness.
apt_install() {
    local tries=0
    export DEBIAN_FRONTEND=noninteractive
    while [ $tries -lt 5 ]; do
        if apt-get install -y --no-install-recommends "$@" >>"$PI_RACK_LOG" 2>&1; then
            return 0
        fi
        tries=$((tries + 1))
        log "apt-get install failed (attempt $tries), waiting for locks"
        sleep $((tries * 15))
        apt-get update >>"$PI_RACK_LOG" 2>&1 || true
    done
    die "could not install: $*"
}

apt_update() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update >>"$PI_RACK_LOG" 2>&1 || log "apt-get update failed, continuing"
}

# write_unit <name> <<'EOF' ... EOF
# Installs a systemd unit from stdin, but only reloads and restarts when the
# content actually changed. Avoids a pointless restart storm on re-runs.
write_unit() {
    local name="$1"
    local path="/etc/systemd/system/${name}"
    local tmp
    tmp="$(mktemp)"
    cat > "$tmp"
    if [ -f "$path" ] && cmp -s "$tmp" "$path"; then
        rm -f "$tmp"
        log "unit $name unchanged"
        return 0
    fi
    mv "$tmp" "$path"
    chmod 0644 "$path"
    systemctl daemon-reload
    log "unit $name installed"
}

enable_now() {
    systemctl enable --now "$1" >>"$PI_RACK_LOG" 2>&1
    log "enabled $1"
}

# has_cmd <name>
has_cmd() { command -v "$1" >/dev/null 2>&1; }

# is_pi5 - the Pi 5 is bcm2712; several roles care (PCIe, power, performance).
is_pi5() {
    grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null
}

model() {
    tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo unknown
}

# ram_mb - total RAM, for roles that should refuse to run on a 2 GB board.
ram_mb() {
    awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo
}

require_ram() {
    local want="$1" have
    have="$(ram_mb)"
    if [ "$have" -lt "$want" ]; then
        die "needs ${want} MB RAM, this board has ${have} MB"
    fi
}

# on_ssd - true when / is NOT on the SD card. Roles that write constantly
# (databases, logs, recordings) use this to warn rather than silently
# shorten the life of a card.
on_ssd() {
    local src
    src="$(findmnt -no SOURCE / 2>/dev/null || echo)"
    case "$src" in
        /dev/mmcblk*) return 1 ;;
        *) return 0 ;;
    esac
}

warn_if_sd() {
    if ! on_ssd; then
        log "WARNING: / is on an SD card and this role writes continuously."
        log "         Expect card wear. Move this node to a USB SSD or NVMe."
    fi
}

# docker_install - the official convenience script, guarded.
docker_install() {
    if has_cmd docker; then
        log "docker already present: $(docker --version)"
        return 0
    fi
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh >>"$PI_RACK_LOG" 2>&1
    rm -f /tmp/get-docker.sh
    # The admin user should be able to drive docker without sudo. Note this is
    # effectively root on this host - acceptable on a single-purpose node on a
    # home LAN, and stated plainly rather than done quietly.
    if [ -n "${PI_RACK_ADMIN:-}" ]; then
        usermod -aG docker "$PI_RACK_ADMIN" || true
    fi
    log "docker installed: $(docker --version)"
}

# compose_up <dir> - bring up a compose stack idempotently.
compose_up() {
    local dir="$1"
    ( cd "$dir" && docker compose up -d ) >>"$PI_RACK_LOG" 2>&1
    log "compose up in $dir"
}

# announce <state> - publish this node's status to Home Assistant over MQTT.
# Optional: only runs when the broker credentials were provisioned. Home
# Assistant and Mosquitto already exist on this LAN, so this is the cheapest
# possible "did the node come up" signal - no new monitoring stack required.
announce() {
    local state="${1:-online}"
    [ -r /etc/pi-rack-mqtt.env ] || return 0
    # shellcheck disable=SC1091
    . /etc/pi-rack-mqtt.env
    has_cmd mosquitto_pub || return 0
    mosquitto_pub -h "${MQTT_HOST}" -p "${MQTT_PORT:-1883}" \
        -u "${MQTT_USER}" -P "${MQTT_PASS}" \
        -t "pi-rack/${PI_RACK_HOSTNAME}/status" -r -m "${state}" \
        >>"$PI_RACK_LOG" 2>&1 || log "mqtt announce failed (non-fatal)"
}
