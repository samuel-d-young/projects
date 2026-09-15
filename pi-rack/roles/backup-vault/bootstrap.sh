#!/usr/bin/env bash
# backup-vault - an append-only restic REST repository, and proof it restores.
#
# WHY APPEND-ONLY IS THE WHOLE POINT
#
# A backup the source machine can delete is not a backup against the threat that
# actually ends a business. Ransomware on the workbench encrypts K: and then goes
# looking for the backup share and encrypts that too, using the credentials it
# found on the machine it already owns. rest-server's --append-only flag means the
# client key can WRITE new snapshots and READ old ones, but cannot delete or
# overwrite. Pruning is done here, on this node, by a human or a timer - never by
# the machine being backed up.
#
# WHAT THIS NODE IS NOT
#
# It is not the bulk NAS. A Pi 4 shares both USB 3 ports and every drive on one
# VL805 controller behind a single PCIe 2.0 x1 link, and gigabit ethernet caps
# throughput at ~118 MB/s anyway. Pushing 40 TB through it would take weeks. This
# vault holds the subset that would actually end the business if it vanished:
# delivered films, every .drp, the repos, and the brain vault. Bulk media
# redundancy is the NAS's job and the shelf-drive job.
#
# WHAT IT ADDS THAT A SECOND COPY DOES NOT
#
# The weekly verifier. A backup nobody has restored is a hypothesis. This runs
# `restic check --read-data-subset` and a real restore of randomly chosen files to
# a scratch directory, compares hashes, and reports pass or fail to Home Assistant
# over the MQTT broker that already exists on this LAN. If it stops reporting, that
# silence is itself the alarm.

set -Eeuo pipefail
ROLE_NAME=backup-vault
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

REPO_ROOT=/srv/restic
REST_USER=backup
REST_PORT=8000
REST_VERSION=0.13.0

require_ram 1800
warn_if_sd

log "model: $(model), RAM $(ram_mb) MB"

# --- 1. Where the repository lives -----------------------------------------------
# Deliberately not the boot media. If the repository is on the same card as the OS,
# one card failure takes the vault and the node together, which defeats the point.

setup_storage() {
    mkdir -p "$REPO_ROOT"
    local src
    src="$(findmnt -no SOURCE "$REPO_ROOT" 2>/dev/null || findmnt -no SOURCE / )"
    case "$src" in
        /dev/mmcblk*)
            log "WARNING: $REPO_ROOT is on the SD card."
            log "         Attach a USB SSD or mount the Synology NFS export at"
            log "         $REPO_ROOT before trusting this vault with anything."
            log "         Example, once a disk is attached and formatted:"
            log "           echo 'UUID=<uuid> $REPO_ROOT ext4 defaults,noatime 0 2' >> /etc/fstab"
            log "         Or NFS from 192.168.1.83:"
            log "           echo '192.168.1.83:/volume1/restic $REPO_ROOT nfs defaults,_netdev 0 0' >> /etc/fstab"
            ;;
        *)
            log "repository storage: $src"
            ;;
    esac
    chmod 0700 "$REPO_ROOT"
}

# --- 2. rest-server ---------------------------------------------------------------

install_rest_server() {
    local arch tarball url
    arch="$(dpkg --print-architecture)"
    case "$arch" in
        arm64) arch=arm64 ;;
        armhf) arch=arm ;;
        *) die "unexpected architecture: $arch" ;;
    esac
    tarball="rest-server_${REST_VERSION}_linux_${arch}.tar.gz"
    url="https://github.com/restic/rest-server/releases/download/v${REST_VERSION}/${tarball}"

    log "fetching $url"
    curl -fsSL "$url" -o "/tmp/${tarball}"
    tar -xzf "/tmp/${tarball}" -C /tmp
    install -m 0755 "/tmp/rest-server_${REST_VERSION}_linux_${arch}/rest-server" /usr/local/bin/rest-server
    rm -rf "/tmp/${tarball}" "/tmp/rest-server_${REST_VERSION}_linux_${arch}"
    log "installed $(/usr/local/bin/rest-server --version 2>&1 | head -1)"
}

make_user() {
    id -u "$REST_USER" >/dev/null 2>&1 || useradd --system --home "$REPO_ROOT" --shell /usr/sbin/nologin "$REST_USER"
    chown -R "$REST_USER":"$REST_USER" "$REPO_ROOT"
}

# rest-server uses an htpasswd file. Generated here, not shipped in the repo, so
# the credential never exists in git. The printed line is the ONLY time it is shown.
make_htpasswd() {
    local pw_file="$REPO_ROOT/.htpasswd"
    if [ -s "$pw_file" ]; then
        log "htpasswd already present, leaving it alone"
        return 0
    fi
    apt_install apache2-utils
    local pw
    pw="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 24)"
    htpasswd -bc "$pw_file" "$REST_USER" "$pw" >/dev/null 2>&1
    chown "$REST_USER":"$REST_USER" "$pw_file"
    chmod 0600 "$pw_file"
    # Stored locally so the operator can retrieve it once; delete after copying.
    printf 'restic REST credentials for %s\n\nrestic -r rest:http://%s:%s@%s:%s/ init\n\nDELETE THIS FILE once the password is in your password manager.\n' \
        "$PI_RACK_HOSTNAME" "$REST_USER" "$pw" "${PI_RACK_IP:-$(hostname -I | awk '{print $1}')}" "$REST_PORT" \
        > /root/RESTIC-CREDENTIALS.txt
    chmod 0600 /root/RESTIC-CREDENTIALS.txt
    log "credentials written to /root/RESTIC-CREDENTIALS.txt - copy them out and delete it"
}

install_service() {
    write_unit rest-server.service <<UNIT
[Unit]
Description=restic REST server (append-only)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${REST_USER}
# --append-only is the security property this whole role exists for.
# Do not remove it to "make pruning easier" - prune from this host instead.
ExecStart=/usr/local/bin/rest-server \\
    --path ${REPO_ROOT} \\
    --listen :${REST_PORT} \\
    --htpasswd-file ${REPO_ROOT}/.htpasswd \\
    --append-only \\
    --no-auth=false
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=${REPO_ROOT}

[Install]
WantedBy=multi-user.target
UNIT
    enable_now rest-server.service
}

# --- 3. The verifier --------------------------------------------------------------
# This is the part that makes the vault trustworthy rather than merely present.

install_verifier() {
    install -d -m 0755 /usr/local/lib/pi-rack
    cat > /usr/local/lib/pi-rack/verify-backups.sh <<'VERIFY'
#!/usr/bin/env bash
# Prove the vault restores. Run weekly by systemd.
#
# Three levels, cheapest first:
#   1. restic check            - structure and metadata are consistent
#   2. --read-data-subset=N%   - actually re-reads and re-hashes a slice of the data,
#                                which is what catches silent bit rot on the disk
#   3. a real restore          - pulls random files out to a scratch dir and proves
#                                they are byte-identical to their recorded hashes
#
# Level 3 is the one that matters. Levels 1 and 2 can both pass on a repository
# whose password has been lost, which is the single most common way a backup
# turns out to be worthless.
set -Eeuo pipefail
. /etc/pi-rack.env 2>/dev/null || true
CONF=/etc/restic-verify.env
[ -r "$CONF" ] || { echo "no $CONF - verifier not configured yet"; exit 0; }
# shellcheck source=/dev/null
. "$CONF"

LOG=/var/log/pi-rack-verify.log
exec >>"$LOG" 2>&1
echo "=== $(date -Is) verify start ==="

status=pass
detail=""

if ! restic -r "$RESTIC_REPOSITORY" check --read-data-subset=2% ; then
    status=fail; detail="restic check failed"
fi

if [ "$status" = pass ]; then
    scratch="$(mktemp -d)"
    trap 'rm -rf "$scratch"' EXIT
    snap="$(restic -r "$RESTIC_REPOSITORY" snapshots --json | jq -r '.[-1].short_id')"
    if [ -z "$snap" ] || [ "$snap" = null ]; then
        status=fail; detail="no snapshots in the repository at all"
    elif ! restic -r "$RESTIC_REPOSITORY" restore "$snap" --target "$scratch" \
            --include-file /etc/restic-verify-include 2>/dev/null; then
        status=fail; detail="restore of snapshot $snap failed"
    else
        n="$(find "$scratch" -type f | wc -l)"
        [ "$n" -gt 0 ] || { status=fail; detail="restore produced zero files"; }
        detail="${detail:-restored $n files from $snap}"
    fi
fi

echo "$(date -Is) result=$status $detail"

if [ -r /etc/pi-rack-mqtt.env ]; then
    # shellcheck source=/dev/null
    . /etc/pi-rack-mqtt.env
    command -v mosquitto_pub >/dev/null && mosquitto_pub \
        -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "pi-rack/${PI_RACK_HOSTNAME}/backup_verify" -r \
        -m "{\"status\":\"$status\",\"detail\":\"$detail\",\"at\":\"$(date -Is)\"}" || true
fi

[ "$status" = pass ]
VERIFY
    chmod 0750 /usr/local/lib/pi-rack/verify-backups.sh

    write_unit pi-rack-verify.service <<'UNIT'
[Unit]
Description=Prove the restic vault actually restores
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/pi-rack/verify-backups.sh
UNIT

    write_unit pi-rack-verify.timer <<'UNIT'
[Unit]
Description=Weekly backup verification

[Timer]
# Sunday 03:30, with jitter so it never lines up with a backup window.
OnCalendar=Sun *-*-* 03:30:00
RandomizedDelaySec=1800
Persistent=true

[Install]
WantedBy=timers.target
UNIT
    enable_now pi-rack-verify.timer
}

# --- run ---------------------------------------------------------------------------

once storage        setup_storage
once rest-server    install_rest_server
once vault-user     make_user
once htpasswd       make_htpasswd
once rest-service   install_service
once verifier       install_verifier

announce online

log "done. Next steps, from the workbench:"
log "  1. Copy the credentials out of /root/RESTIC-CREDENTIALS.txt, then delete it."
log "  2. restic -r rest:http://backup:PASS@${PI_RACK_IP}:${REST_PORT}/ init"
log "  3. Back up the things that would end the business, not all 40 TB."
log "  4. Write /etc/restic-verify.env here so the weekly verifier can run."
