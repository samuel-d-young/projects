#!/usr/bin/env bash
# esphome - a build server for ESP32 firmware, on a port you can actually reach.
#
# WHY THIS ROLE EARNS A BOARD
#
# This one is not speculative - it unblocks something already recorded as blocked.
# K:\Claude\home-assistant\STATUS.md logs three closed routes to rebuilding the
# Voice PE firmware for the Alexa wake word: the Supervisor API rejects long-lived
# tokens with a 401, the ESPHome Device Builder add-on is ingress-only so 6052 is
# not exposed, and building ESPHome from scratch on .66 failed because python3-venv
# needed apt and therefore sudo. The wake word eventually got built from the
# workbench in a venv under K:\Claude\projects\.esphome-venv.
#
# That works, but it means: firmware only builds when the Windows box is on, the
# build cache lives on K: which has under 50 GB free, and the wall-clock project
# now in progress needs the same toolchain again.
#
# A dashboard on a real port, on an always-on node, with its cache on its own disk,
# removes all three.
#
# THE RAM NUMBER IS NOT NEGOTIABLE
#
# Compiling an ESP32-S3 image with the esp-idf framework is the heaviest thing any
# node in this rack does. PlatformIO fetches a toolchain of well over a gigabyte
# and the compile itself is memory-hungry. A 2 GB Pi 4 will either thrash or get
# OOM-killed part way through, which looks like a mysterious hang. 4 GB is the
# floor; 8 GB is comfortable. This script refuses below 3.5 GB rather than let you
# find out during a build.
#
# AND IT MUST NOT BE ON AN SD CARD
#
# A single full build writes several GB. Doing that repeatedly to an SD card is
# how cards die. The script warns; take the warning seriously.

set -Eeuo pipefail
ROLE_NAME=esphome
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

ESPHOME_DIR=/srv/esphome
ESPHOME_USER=esphome
PORT=6052

require_ram 3500
warn_if_sd

setup_dirs() {
    id -u "$ESPHOME_USER" >/dev/null 2>&1 || \
        useradd --system --create-home --home-dir "$ESPHOME_DIR" --shell /bin/bash "$ESPHOME_USER"
    mkdir -p "$ESPHOME_DIR/config"
    chown -R "$ESPHOME_USER":"$ESPHOME_USER" "$ESPHOME_DIR"
}

# A venv, not pipx and not the system Python. ESPHome pins a lot of dependencies
# and Debian trixie enforces PEP 668 (externally-managed-environment), so pip into
# the system interpreter is refused outright.
install_esphome() {
    sudo -u "$ESPHOME_USER" python3 -m venv "$ESPHOME_DIR/venv"
    sudo -u "$ESPHOME_USER" "$ESPHOME_DIR/venv/bin/pip" install --upgrade pip wheel \
        >>"$PI_RACK_LOG" 2>&1
    sudo -u "$ESPHOME_USER" "$ESPHOME_DIR/venv/bin/pip" install esphome \
        >>"$PI_RACK_LOG" 2>&1
    log "installed $(sudo -u "$ESPHOME_USER" "$ESPHOME_DIR/venv/bin/esphome" version 2>&1 | head -1)"
}

install_service() {
    write_unit esphome.service <<UNIT
[Unit]
Description=ESPHome dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${ESPHOME_USER}
WorkingDirectory=${ESPHOME_DIR}/config
Environment=PLATFORMIO_CORE_DIR=${ESPHOME_DIR}/.platformio
ExecStart=${ESPHOME_DIR}/venv/bin/esphome dashboard ${ESPHOME_DIR}/config
Restart=on-failure
RestartSec=10
# A compile is long and memory-hungry; do not let systemd kill it early.
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT
    enable_now esphome.service
}

# The two things that will bite on the first real rebuild, written down where the
# person doing it will find them. Both are recorded in the home-assistant repo as
# lessons already paid for once.
write_notes() {
    cat > "$ESPHOME_DIR/config/README-FIRST.md" <<'NOTES'
# Before you rebuild the Voice PE firmware

Two things caused the first attempt to fail, both recorded in
`K:\Claude\home-assistant\STATUS.md`. They will cost you an evening again if
you skip them.

## 1. Use the FACTORY package

The package must be `home-assistant-voice.factory.yaml`, **not** the plain
`home-assistant-voice.yaml`. The plain one fails validation with *"Please
specify at least an SSID or an Access Point to create"*. The factory config
supplies `improv_serial` / `esp32_improv`, which is also what preserves the
device's stored WiFi credentials across a rebuild.

## 2. The API encryption key must match

If the `api:` encryption key does not match the one Home Assistant already
has for that device, HA loses the device after the OTA and you are driving to
it with a USB cable. The existing key can be read from a Home Assistant backup
at `data/.storage/core.config_entries`.

**That backup file also contains the MQTT password and the Music Assistant
token in cleartext.** Any copy you extract is a secret. Delete it when done,
and never put it in the brain vault - that repo has a remote.

## 3. Pin the version

Pin to the exact tag already on the device (`@26.6.0` last time) so the change
you are making is the *only* difference from what Nabu Casa shipped.

## Keep one device on the old firmware

When the Alexa wake word went on, the Kitchen Voice PE was deliberately left on
"Okay Nabu" as a working fallback. Do the same for anything risky: never flash
the last working device until the new one is confirmed good.
NOTES
    chown "$ESPHOME_USER":"$ESPHOME_USER" "$ESPHOME_DIR/config/README-FIRST.md"
}

selftest() {
    sleep 5
    if curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
        log "self-test: dashboard answering on ${PORT}"
    else
        log "self-test: dashboard not answering yet - check: journalctl -u esphome -n 50"
    fi
}

once dirs      setup_dirs
once esphome   install_esphome
once service   install_service
once notes     write_notes
selftest
announce online

log "done."
log "  Dashboard: http://${PI_RACK_IP}:${PORT}"
log "  Configs:   ${ESPHOME_DIR}/config   (read README-FIRST.md before rebuilding Voice PE)"
log "  First build downloads a >1 GB toolchain and takes a while. That is normal."
