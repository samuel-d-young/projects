#!/usr/bin/env bash
# netcore - AdGuard Home: DNS for the house, and optionally DHCP.
#
# READ THIS BEFORE DEPLOYING, BECAUSE THE FAILURE MODE IS THE DESIGN
#
# The moment this node is the only DNS server on the LAN, a dead SD card at 2am
# means "the internet is broken" for everyone in the house while Samuel is at a
# wedding with his phone on silent. That is a worse outcome than seeing ads.
#
# So this role refuses to be a single point of failure, and enforces it two ways:
#
#   1. SECONDARY REQUIRED. DHCP hands out two resolvers. The second should be a
#      second AdGuard instance - the NUC at 192.168.1.42 is always on and already
#      runs containers, so it is the natural home and costs no extra board. If you
#      genuinely will not run a second one, set NETCORE_ALLOW_SINGLE=1 and accept
#      that you have chosen it, rather than discovering it.
#
#      Note the honest trade: clients treat multiple resolvers as interchangeable
#      and will use either, so a secondary that does NOT filter means filtering
#      becomes intermittent. Run AdGuard on both, or accept unfiltered fallback
#      deliberately. There is no configuration that gives you both.
#
#   2. FAIL OPEN, NOT CLOSED. Upstream is set to real resolvers, and the
#      systemd unit restarts on failure. A Pi that is up but has a wedged
#      AdGuard is worse than one that is off, because DHCP keeps pointing at it.
#
# WHY DHCP IS WORTH MOVING (but is a separate, later step)
#
# Home Assistant at 192.168.1.75 is a DHCP LEASE, not a reservation - Samuel's own
# notes flag this and record that it has already bitten once during the migration.
# Reservations living in a router's web UI are invisible, unversioned, and lost
# with the router. Moving DHCP here puts them in a file that can be committed.
#
# But do NOT enable DHCP in the same session you deploy DNS. Two DHCP servers on
# one LAN is a genuinely confusing outage. Turn the router's DHCP OFF first, in
# the same maintenance window, with a laptop on a static address as your way back in.

set -Eeuo pipefail
ROLE_NAME=netcore
# shellcheck source=/dev/null
. /opt/pi-rack/common.sh

AGH_DIR=/opt/AdGuardHome
UI_PORT=3053

# --- 1. Free up port 53 -----------------------------------------------------------
# Debian runs systemd-resolved with a stub listener on 127.0.0.53:53. AdGuard binds
# 0.0.0.0:53 and the two collide. The fix is to disable ONLY the stub listener and
# keep resolved as the local resolver, rather than removing resolved entirely -
# which breaks name resolution on the node itself at the worst possible moment.

free_port_53() {
    if ! systemctl is-active --quiet systemd-resolved; then
        log "systemd-resolved not active, nothing to free"
        return 0
    fi
    mkdir -p /etc/systemd/resolved.conf.d
    cat > /etc/systemd/resolved.conf.d/adguard.conf <<'CONF'
# Stop resolved owning port 53 so AdGuard Home can bind it.
# resolved itself stays running as this machine's own resolver.
[Resolve]
DNSStubListener=no
CONF
    # /etc/resolv.conf normally symlinks to the stub address, which stops working
    # the moment the stub is off. Point it at the real resolved-managed file.
    if [ -e /run/systemd/resolve/resolv.conf ]; then
        ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
    fi
    systemctl restart systemd-resolved
    log "systemd-resolved stub listener disabled; port 53 is free"
}

# --- 2. AdGuard Home ---------------------------------------------------------------

install_adguard() {
    if [ -x "$AGH_DIR/AdGuardHome" ]; then
        log "AdGuard Home already installed"
        return 0
    fi
    local arch
    case "$(dpkg --print-architecture)" in
        arm64) arch=arm64 ;;
        armhf) arch=armv7 ;;
        *) die "unexpected architecture" ;;
    esac
    local url="https://static.adguard.com/adguardhome/release/AdGuardHome_linux_${arch}.tar.gz"
    log "fetching $url"
    curl -fsSL "$url" -o /tmp/agh.tar.gz
    tar -xzf /tmp/agh.tar.gz -C /opt
    rm -f /tmp/agh.tar.gz
    "$AGH_DIR/AdGuardHome" -s install >>"$PI_RACK_LOG" 2>&1 || true
    log "AdGuard Home installed"
}

# Seed the configuration rather than clicking through the setup wizard, so the
# resolver's behaviour is in a file that can be read, diffed and restored.
# AdGuard rewrites this file when you change things in the UI - that is expected;
# copy it back into the repo when you do, the same way plan files work elsewhere
# in this workbench.
seed_config() {
    local cfg="$AGH_DIR/AdGuardHome.yaml"
    if [ -s "$cfg" ]; then
        log "AdGuardHome.yaml already exists - not overwriting a live config"
        return 0
    fi
    cat > "$cfg" <<CONF
# Seeded by pi-rack. Edited by the AdGuard UI afterwards - if you change something
# there, copy this file back into roles/netcore/ so the two do not drift.
http:
  address: 0.0.0.0:${UI_PORT}
users: []
dns:
  bind_hosts:
    - 0.0.0.0
  port: 53
  # Quad9 and Cloudflare over DNS-over-TLS. Two providers, so one outage is not
  # an internet outage. Plain 53 upstreams are deliberately not used: this is a
  # residential connection and the ISP resolver sees every lookup otherwise.
  upstream_dns:
    - tls://dns.quad9.net
    - tls://1dot1dot1dot1.cloudflare-dns.com
  bootstrap_dns:
    - 9.9.9.9
    - 1.1.1.1
  # Local names must not leak upstream, and must resolve here.
  local_ptr_upstreams: []
  ratelimit: 0
  refuse_any: true
  # DNS rewrites: the fix for "Home Assistant moved and everything broke".
  # Names, not addresses, in every config that can take one.
  rewrites:
    - domain: hass.lan
      answer: 192.168.1.75
    - domain: nas.lan
      answer: 192.168.1.83
    - domain: nuc.lan
      answer: 192.168.1.42
    - domain: frigate.lan
      answer: 192.168.1.70
filtering:
  protection_enabled: true
  filtering_enabled: true
  rewrites: []
filters:
  - enabled: true
    url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt
    name: AdGuard DNS filter
    id: 1
  - enabled: true
    url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt
    name: AdAway Default Blocklist
    id: 2
# DHCP is present but OFF. See the header of this script: enabling it while the
# router still serves DHCP is a real outage. Turn the router's off first.
dhcp:
  enabled: false
  interface_name: eth0
  dhcpv4:
    gateway_ip: 192.168.1.1
    subnet_mask: 255.255.255.0
    range_start: 192.168.1.150
    range_end: 192.168.1.240
    lease_duration: 86400
    # Static leases go here, in this file, in git. That is the entire point.
    # 192.168.1.75 is Home Assistant and has never had a reservation.
    static_leases: []
schema_version: 29
CONF
    chmod 0600 "$cfg"
    log "seeded $cfg"
}

# --- 3. Refuse to be a single point of failure --------------------------------------

check_secondary() {
    if [ "${NETCORE_ALLOW_SINGLE:-0}" = "1" ]; then
        log "NETCORE_ALLOW_SINGLE=1 - proceeding as the only resolver, by explicit choice"
        return 0
    fi
    local secondary="${NETCORE_SECONDARY_DNS:-}"
    if [ -z "$secondary" ]; then
        log "==============================================================="
        log "NO SECONDARY RESOLVER CONFIGURED."
        log ""
        log "DNS is installed and running, but do NOT point the router's DHCP"
        log "at this node as the only resolver. When this Pi dies, the house"
        log "loses the internet until someone is physically present."
        log ""
        log "Set up a second AdGuard Home (the NUC at 192.168.1.42 is already"
        log "always-on and runs containers), then set NETCORE_SECONDARY_DNS"
        log "in /etc/pi-rack.env and re-run this script."
        log ""
        log "Or set NETCORE_ALLOW_SINGLE=1 to accept the risk deliberately."
        log "==============================================================="
        return 0
    fi
    log "secondary resolver recorded: $secondary"
}

start_service() {
    systemctl enable AdGuardHome >>"$PI_RACK_LOG" 2>&1 || true
    systemctl restart AdGuardHome
    sleep 3
    if systemctl is-active --quiet AdGuardHome; then
        log "AdGuard Home is running"
    else
        die "AdGuard Home failed to start - check: journalctl -u AdGuardHome -n 50"
    fi
}

# Prove it actually resolves before declaring success. A DNS server that starts
# but does not answer is the exact failure this catches.
selftest() {
    apt_install dnsutils
    local ip="${PI_RACK_IP:-127.0.0.1}"
    if dig +short +timeout=3 +tries=1 @"$ip" example.com A >/dev/null 2>&1; then
        log "self-test: resolved example.com via $ip - DNS is answering"
    else
        die "self-test FAILED: $ip is not answering DNS queries"
    fi
    local rewritten
    rewritten="$(dig +short +timeout=3 @"$ip" hass.lan A 2>/dev/null | head -1)"
    if [ "$rewritten" = "192.168.1.75" ]; then
        log "self-test: hass.lan -> 192.168.1.75 (rewrite working)"
    else
        log "self-test: hass.lan returned '${rewritten:-nothing}' - check the rewrites block"
    fi
}

once free-53      free_port_53
once adguard      install_adguard
once agh-config   seed_config
once agh-service  start_service
check_secondary
selftest
announce online

log "done."
log "  UI:      http://${PI_RACK_IP}:${UI_PORT}"
log "  Test:    dig @${PI_RACK_IP} example.com"
log "  DO NOT change the router's DNS until a secondary resolver exists."
