#!/usr/bin/env bash
# eventkit - the LAN-party box that lives in the camera bag.
#
# THIS NODE IS NOT PART OF THE RACK
#
# It is the one Pi in this plan that is deliberately NOT always-on and NOT on the
# home LAN. It sits in the bag with the camera gear, comes out at Indie LAN / BIG
# LAN / LANSlide / Gamers Retreat, and goes back in afterwards.
#
# THE FOUR THINGS THAT GO WRONG AT EVERY EVENT
#
#   1. DHCP. Someone plugs in a home router "just for the switch" and it starts
#      handing out 192.168.0.x while the real range is something else. Half the
#      room cannot see the other half.
#   2. Clocks. No internet, so no NTP, so machines drift. Windows and Steam auth
#      both fail on clock skew, and the error message never says so.
#   3. Nobody knows anything. The WiFi password, the server IP, the schedule -
#      all of it is being shouted across a hall forty times an hour.
#   4. "The network is slow." Nobody can prove it either way, so it gets blamed
#      for everything, including someone's dying SSD.
#
# This box answers all four, and none of them need a fast Pi.
#
# SAFETY: DHCP IS OFF UNTIL YOU TURN IT ON
#
# A box that starts handing out addresses the moment it is plugged in is a way to
# take down a venue's network - including, potentially, the venue's own business
# systems. So dnsmasq ships disabled and is armed with one deliberate command:
#
#     event-dhcp on      (and event-dhcp off when you leave)
#
# Never leave DHCP armed when this node comes home. There is a systemd condition
# below that refuses to start DHCP if it sees the home LAN's gateway, as a second
# line of defence against exactly that mistake.

set -Eeuo pipefail
ROLE_NAME=eventkit
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

EVENT_NET=10.42.0
INFO_PORT=8090
HOME_GATEWAY=192.168.1.1

setup_dnsmasq() {
    # Disabled at boot, by design. Armed only by `event-dhcp on`.
    systemctl disable dnsmasq >>"$PI_RACK_LOG" 2>&1 || true
    systemctl stop dnsmasq >>"$PI_RACK_LOG" 2>&1 || true

    cat > /etc/dnsmasq.d/eventkit.conf <<CONF
# pi-rack eventkit - LAN party DHCP + DNS.
# Only active when armed with: event-dhcp on

interface=eth0
bind-interfaces

# A range nobody's home router uses, so if this box is ever accidentally armed on
# a home LAN the collision is obvious rather than subtle. Deliberately not
# 192.168.0.x or 192.168.1.x.
dhcp-range=${EVENT_NET}.50,${EVENT_NET}.200,255.255.255.0,4h
dhcp-option=option:router,${EVENT_NET}.1
dhcp-option=option:dns-server,${EVENT_NET}.1
dhcp-option=option:ntp-server,${EVENT_NET}.1

# Local names so people can type something memorable.
address=/event.lan/${EVENT_NET}.1
address=/info.lan/${EVENT_NET}.1

# Log every lease. At an event, "who has .137" is asked constantly.
log-dhcp
log-queries
CONF
    log "dnsmasq configured (disabled until armed)"
}

setup_chrony() {
    cat > /etc/chrony/conf.d/eventkit.conf <<CONF
# Serve time to the event LAN even with no internet.
#
# 'local stratum 10' is the load-bearing line: it makes chrony willing to be a
# time source using its own clock when it has no upstream at all. Without it,
# a disconnected server refuses to answer and every client stays wrong - which
# is the whole failure this is here to fix.
allow ${EVENT_NET}.0/24
local stratum 10
CONF
    systemctl restart chrony || true
    log "chrony serving ${EVENT_NET}.0/24, will serve time with no uplink"
}

setup_info_page() {
    mkdir -p /srv/event
    cat > /etc/nginx/sites-available/eventkit <<CONF
server {
    listen ${INFO_PORT} default_server;
    root /srv/event;
    index index.html;
    autoindex on;
    # Somewhere for people to drop footage and screenshots during the event.
    location /dump/ {
        alias /srv/event/dump/;
        autoindex on;
    }
}
CONF
    ln -sf /etc/nginx/sites-available/eventkit /etc/nginx/sites-enabled/eventkit
    rm -f /etc/nginx/sites-enabled/default
    mkdir -p /srv/event/dump
    chmod 0777 /srv/event/dump

    # Edited on the night. Kept deliberately plain: it gets read on phones over a
    # network that may have no internet, so nothing external may be referenced.
    if [ ! -s /srv/event/index.html ]; then
        cat > /srv/event/index.html <<'HTML'
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Event info</title>
<style>
  body{font:16px/1.6 system-ui,sans-serif;margin:0;padding:1.5rem;
       background:#111;color:#eee;max-width:38rem}
  h1{font-size:1.4rem;margin:0 0 1rem}
  dt{color:#8bd;font-weight:600;margin-top:1rem}
  dd{margin:.2rem 0 0}
  code{background:#222;padding:.15rem .4rem;border-radius:3px}
</style>
<h1>Event info</h1>
<dl>
  <dt>WiFi</dt><dd>SSID <code>—</code> password <code>—</code></dd>
  <dt>Schedule</dt><dd>—</dd>
  <dt>Game servers</dt><dd>—</dd>
  <dt>Speed test</dt><dd><code>iperf3 -c info.lan</code></dd>
  <dt>Drop files</dt><dd><a href="/dump/">/dump/</a></dd>
</dl>
<p>Edit me: <code>/srv/event/index.html</code> on the event box.</p>
HTML
    fi
    nginx -t >>"$PI_RACK_LOG" 2>&1 && systemctl reload nginx
    log "info page on :${INFO_PORT}"
}

setup_iperf() {
    write_unit iperf3.service <<'UNIT'
[Unit]
Description=iperf3 server for settling "the network is slow" arguments
After=network.target

[Service]
ExecStart=/usr/bin/iperf3 --server --interval 5
Restart=on-failure
User=nobody

[Install]
WantedBy=multi-user.target
UNIT
    enable_now iperf3.service
}

# The arming command, with the home-LAN interlock.
install_control() {
    cat > /usr/local/bin/event-dhcp <<CONTROL
#!/usr/bin/env bash
# Arm or disarm the event DHCP server. Never leave it armed at home.
set -Eeuo pipefail

case "\${1:-}" in
  on)
    # Interlock: if the home gateway answers, this box is at home, and arming
    # DHCP here would fight the house router. Refuse unless forced.
    if ping -c1 -W1 ${HOME_GATEWAY} >/dev/null 2>&1 && [ "\${2:-}" != "--force" ]; then
        echo "REFUSING: ${HOME_GATEWAY} answered, so this looks like the home LAN."
        echo "Arming DHCP here would fight the house router."
        echo "If you really mean it: event-dhcp on --force"
        exit 1
    fi
    ip addr replace ${EVENT_NET}.1/24 dev eth0
    systemctl start dnsmasq
    echo "DHCP ARMED on eth0 as ${EVENT_NET}.1 - range ${EVENT_NET}.50-200"
    echo "Info page: http://${EVENT_NET}.1:${INFO_PORT}"
    ;;
  off)
    systemctl stop dnsmasq || true
    ip addr del ${EVENT_NET}.1/24 dev eth0 2>/dev/null || true
    echo "DHCP disarmed."
    ;;
  status)
    systemctl is-active dnsmasq >/dev/null 2>&1 \\
      && echo "ARMED - serving DHCP" || echo "disarmed"
    ip -4 addr show dev eth0 | sed -n 's/^ *inet /  /p'
    ;;
  leases)
    cat /var/lib/misc/dnsmasq.leases 2>/dev/null || echo "(no leases file yet)"
    ;;
  *)
    echo "usage: event-dhcp {on [--force]|off|status|leases}"
    exit 2
    ;;
esac
CONTROL
    chmod 0755 /usr/local/bin/event-dhcp
    log "installed /usr/local/bin/event-dhcp"
}

once dnsmasq   setup_dnsmasq
once chrony    setup_chrony
once infopage  setup_info_page
once iperf     setup_iperf
once control   install_control

log "done. This node is a travelling kit, not rack infrastructure."
log "  At the event:  sudo event-dhcp on"
log "  Leaving:       sudo event-dhcp off        <- do not forget this"
log "  Who is here:   sudo event-dhcp leases"
log "  Speed test:    iperf3 -c ${EVENT_NET}.1"
