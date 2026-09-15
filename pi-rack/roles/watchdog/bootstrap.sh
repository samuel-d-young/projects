#!/usr/bin/env bash
# watchdog - the box that can act when the thing that broke cannot fix itself.
#
# THE SPECIFIC GAP THIS FILLS
#
# Home Assistant runs as the libvirt guest `haos` on 192.168.1.66. If HA wedges,
# nothing inside HA can restart it, and nothing on .66 is watching. If .66 itself
# is fine but the guest is hung, the fix is one command - `virsh reset haos` - and
# there is currently no host on the LAN whose job it is to notice and run it.
#
# That is the whole role. It is small on purpose.
#
# THE SECURITY DESIGN, WHICH IS THE INTERESTING PART
#
# A box that can reboot other boxes is a box worth compromising. So the privilege
# does NOT live here. This node holds a key that is pinned on the TARGET side to a
# single dispatcher with an explicit allowlist:
#
#     command="/usr/local/bin/rack-recover",restrict ssh-ed25519 AAAA...
#
# The requested action arrives on the target in $SSH_ORIGINAL_COMMAND and is
# matched against a fixed list. Anything else is refused and logged. An injection
# like `reset-ha; rm -rf /` parses to one token that misses the allowlist, and the
# tail is never passed to a shell. This is the same pattern already used by
# K:\Claude\home-assistant\config\nuc-control - deliberately, because a second
# security model in the same house is a second thing to get wrong.
#
# **Never add a branch to the dispatcher that forwards arbitrary input onward.**
# The entire security property is that the allowlist is exhaustive.
#
# THREE RULES THAT KEEP AN AUTOMATED FIXER FROM BECOMING THE OUTAGE
#
#   1. Sustained failure only. Six consecutive failed checks, 30 s apart - three
#      minutes of genuinely down, not one dropped packet.
#   2. Rate limited. At most one action per target per hour. A boot loop must not
#      become a reset loop.
#   3. Always announced. Every action taken publishes to MQTT and is logged with a
#      reason. An automated actor that acts silently is impossible to trust or debug.
#
# And the honest limitation, stated up front: this node cannot recover ITSELF, and
# it cannot tell you it is dead. That is what the outbound dead-man's-switch ping
# at the bottom is for - an external service notices the silence.

set -Eeuo pipefail
ROLE_NAME=watchdog
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

WD_DIR=/etc/pi-rack/watchdog
STATE=/var/lib/pi-rack/watchdog

setup_dirs() {
    mkdir -p "$WD_DIR" "$STATE"
    chmod 0750 "$WD_DIR"
}

make_key() {
    local key="$WD_DIR/id_recover"
    if [ -s "$key" ]; then
        log "recovery key already present"
        return 0
    fi
    ssh-keygen -t ed25519 -N "" -C "pi-rack-watchdog-recovery" -f "$key" >>"$PI_RACK_LOG" 2>&1
    chmod 0600 "$key"
    log "generated recovery key"
    log "PUBLIC KEY - install this on the target, pinned to the dispatcher:"
    log "  $(cat "${key}.pub")"
}

seed_config() {
    local f="$WD_DIR/targets.conf"
    [ -s "$f" ] && { log "targets.conf exists, leaving it"; return 0; }
    cat > "$f" <<'CONF'
# <name> <check-kind> <check-spec> <recovery-host> <recovery-action>
#
# recovery-action must be a token the TARGET's dispatcher allowlists.
# Use "-" for watch-only: alert, never act. Start everything as "-" and promote
# a target to acting only once you have watched it be right for a few weeks.
#
# check-kind: http | tcp
#
# name          kind  spec                                        host           action
home-assistant  http  http://192.168.1.75:8123/                   192.168.1.66   -
hypervisor      tcp   192.168.1.66:22                             -              -
frigate         http  http://192.168.1.70:5000/api/version        -              -
nas             tcp   192.168.1.83:5001                           -              -
agent-deck      http  http://192.168.1.42:5080/                   -              -
CONF
    chmod 0640 "$f"

    cat > "$WD_DIR/watchdog.env" <<'CONF'
# How many consecutive failures before acting. 6 x 30s = 3 minutes down.
FAIL_THRESHOLD=6
# Seconds between polls.
INTERVAL=30
# Minimum seconds between two actions on the same target.
COOLDOWN=3600
# Optional outbound dead-man's switch. If this node dies, the external service
# notices the silence - the one failure this node cannot report itself.
# HEARTBEAT_URL=https://hc-ping.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CONF
    chmod 0640 "$WD_DIR/watchdog.env"
    log "seeded $f - every target starts WATCH-ONLY. Promote deliberately."
}

# The dispatcher that must be installed on each recovery target. Written here so
# it can be copied out; it does not run on this node.
write_target_dispatcher() {
    cat > "$WD_DIR/rack-recover.TARGET-SIDE" <<'DISPATCH'
#!/usr/bin/env bash
# Deploy to /usr/local/bin/rack-recover on the RECOVERY TARGET (e.g. 192.168.1.66),
# owned by root, mode 0755. Then pin the watchdog's key in that user's
# ~/.ssh/authorized_keys:
#
#   command="/usr/local/bin/rack-recover",restrict,no-agent-forwarding,no-port-forwarding,no-pty ssh-ed25519 AAAA... pi-rack-watchdog-recovery
#
# `restrict` is the important word. Without it the key is a general shell.
#
# The requested action arrives in $SSH_ORIGINAL_COMMAND. It is matched WHOLE
# against a case statement - never split, never interpolated into another command,
# never passed to eval. `reset-ha; rm -rf /` matches nothing and is refused.

set -Eeuo pipefail
LOG=/var/log/rack-recover.log
REQ="${SSH_ORIGINAL_COMMAND:-}"

log() { printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG"; }

case "$REQ" in
    status)
        log "ALLOW status"
        virsh list --all 2>/dev/null || echo "libvirt not available"
        ;;
    reset-ha)
        # A reset, not a destroy+start: shortest path back for a hung guest.
        log "ALLOW reset-ha"
        virsh reset haos
        echo "haos reset"
        ;;
    start-ha)
        log "ALLOW start-ha"
        virsh start haos || true
        echo "haos start requested"
        ;;
    *)
        log "REFUSE ${REQ@Q}"
        echo "refused: not in the allowlist" >&2
        exit 1
        ;;
esac
DISPATCH
    chmod 0644 "$WD_DIR/rack-recover.TARGET-SIDE"
    log "target-side dispatcher written to $WD_DIR/rack-recover.TARGET-SIDE"
}

install_daemon() {
    install -d -m 0755 /usr/local/lib/pi-rack
    cat > /usr/local/lib/pi-rack/watchdog.sh <<'WD'
#!/usr/bin/env bash
set -Eeuo pipefail
. /etc/pi-rack.env 2>/dev/null || true
WD_DIR=/etc/pi-rack/watchdog
STATE=/var/lib/pi-rack/watchdog
# shellcheck source=/dev/null
. "$WD_DIR/watchdog.env"

say() { printf '%s [watchdog] %s\n' "$(date -Is)" "$*"; }

publish() {
    [ -r /etc/pi-rack-mqtt.env ] || return 0
    # shellcheck source=/dev/null
    . /etc/pi-rack-mqtt.env
    command -v mosquitto_pub >/dev/null || return 0
    mosquitto_pub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "pi-rack/watchdog/$1" -r -m "$2" 2>/dev/null || true
}

check() {  # check <kind> <spec>
    case "$1" in
        http) curl -fsS -o /dev/null --max-time 10 "$2" ;;
        tcp)  timeout 5 bash -c ">/dev/tcp/${2%:*}/${2##*:}" 2>/dev/null ;;
        *)    return 1 ;;
    esac
}

say "starting; interval=${INTERVAL}s threshold=${FAIL_THRESHOLD} cooldown=${COOLDOWN}s"

while true; do
    while read -r name kind spec host action _rest; do
        case "$name" in ''|\#*) continue ;; esac
        fails_file="$STATE/$name.fails"
        fails=$(cat "$fails_file" 2>/dev/null || echo 0)

        if check "$kind" "$spec"; then
            [ "$fails" -gt 0 ] && say "$name recovered after $fails failures"
            echo 0 > "$fails_file"
            publish "$name" "up"
            continue
        fi

        fails=$((fails + 1))
        echo "$fails" > "$fails_file"
        say "$name FAILED ($fails/$FAIL_THRESHOLD)"
        publish "$name" "down"

        [ "$fails" -ge "$FAIL_THRESHOLD" ] || continue
        [ "$action" != "-" ] && [ "$host" != "-" ] || { say "$name: watch-only, no action"; continue; }

        last_file="$STATE/$name.lastaction"
        last=$(cat "$last_file" 2>/dev/null || echo 0)
        now=$(date +%s)
        if [ $((now - last)) -lt "$COOLDOWN" ]; then
            say "$name: within cooldown ($((COOLDOWN - (now - last)))s left), NOT acting"
            continue
        fi

        say "$name: ACTING - ssh $host '$action'"
        publish "$name/action" "$action at $(date -Is)"
        if ssh -i "$WD_DIR/id_recover" \
               -o BatchMode=yes -o ConnectTimeout=10 \
               -o StrictHostKeyChecking=accept-new \
               "vultron@$host" "$action" >>/var/log/pi-rack-watchdog.log 2>&1; then
            say "$name: action succeeded"
            publish "$name/action_result" "ok"
        else
            say "$name: ACTION FAILED - escalating to a human"
            publish "$name/action_result" "failed"
        fi
        echo "$now" > "$last_file"
        echo 0 > "$fails_file"
    done < "$WD_DIR/targets.conf"

    # Outbound dead-man's switch. The only way the failure of THIS node reaches
    # anyone, because a dead watchdog cannot raise its own alarm.
    [ -n "${HEARTBEAT_URL:-}" ] && curl -fsS -m 10 "$HEARTBEAT_URL" >/dev/null 2>&1 || true

    sleep "$INTERVAL"
done
WD
    chmod 0750 /usr/local/lib/pi-rack/watchdog.sh

    write_unit pi-rack-watchdog.service <<'UNIT'
[Unit]
Description=Out-of-band watchdog and recovery arbiter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/lib/pi-rack/watchdog.sh
Restart=always
RestartSec=30
StandardOutput=append:/var/log/pi-rack-watchdog.log
StandardError=append:/var/log/pi-rack-watchdog.log

[Install]
WantedBy=multi-user.target
UNIT
    enable_now pi-rack-watchdog.service
}

# The hardware watchdog on the SoC, for the one failure software cannot catch:
# this node itself wedging. Without this, a kernel lockup here is silent forever.
enable_soc_watchdog() {
    mkdir -p /etc/systemd/system.conf.d
    cat > /etc/systemd/system.conf.d/pi-rack-watchdog.conf <<'CONF'
# BCM2711/2712 hardware watchdog. If systemd stops petting it for 15 seconds the
# SoC resets the board. RebootWatchdogSec covers a hung shutdown.
[Manager]
RuntimeWatchdogSec=15
RebootWatchdogSec=2min
CONF
    systemctl daemon-reexec || true
    log "SoC hardware watchdog armed (15s)"
}

once dirs        setup_dirs
once key         make_key
once config      seed_config
once dispatcher  write_target_dispatcher
once daemon      install_daemon
once socwatchdog enable_soc_watchdog
announce online

log "done - but it is WATCH-ONLY until you finish the target side."
log ""
log "  1. Copy ${WD_DIR}/rack-recover.TARGET-SIDE to /usr/local/bin/rack-recover on"
log "     192.168.1.66, root-owned, mode 0755."
log "  2. Pin this node's key in vultron's authorized_keys there, with"
log "     command=\"/usr/local/bin/rack-recover\",restrict"
log "  3. Test the refusal first:  ssh -i ${WD_DIR}/id_recover vultron@192.168.1.66 'status; id'"
log "     It MUST be refused. If it returns a uid, stop and fix the pinning."
log "  4. Only then set the home-assistant action in targets.conf from - to reset-ha."
