#!/usr/bin/env bash
# =============================================================================
# triage.sh — find out why the Immich mobile app can't connect or log in
# =============================================================================
# Run this ON the voice NUC (best — it can then read Docker and disk state):
#
#     bash triage.sh
#
# Or from any other machine on the same LAN as the NUC:
#
#     bash triage.sh 192.168.1.42     # if you know the NUC's address
#     bash triage.sh --scan           # sweep 192.168.1.0/24 for port 2283
#
# Options:
#     --login          also test a real login (prompts for the password;
#                      never pass it on the command line)
#     --scan           force a subnet sweep even if a host was given
#     --port N         non-default Immich port (default 2283)
#
# It changes NOTHING. Every check is a read. It prints numbered findings and
# a VERDICT at the end telling you which section of RUNBOOK.md to go to.
#
# The checks are ordered by how often each thing is actually the cause when a
# working Immich "stops working on the phone" with no config change:
#   1. containers not running after a reboot or an image pull
#   2. disk full -> Postgres goes read-only -> ping succeeds but LOGIN fails
#   3. the NUC's DHCP lease moved -> the app is pointed at a stale IP
#   4. the store auto-updated the app past the pinned server version
#   5. Postgres refusing to start after a major upgrade (extension mismatch)
# =============================================================================
set -uo pipefail

PORT=2283
HOST=""
DO_LOGIN=0
DO_SCAN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --login) DO_LOGIN=1 ;;
    --scan)  DO_SCAN=1 ;;
    --port)  shift; PORT="${1:-2283}" ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) HOST="$1" ;;
  esac
  shift
done

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; FINDINGS+=("$*"); }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$*"; FINDINGS+=("$*"); }
info() { printf '        %s\n' "$*"; }

FINDINGS=()
VERDICT=""
verdict() { [ -z "$VERDICT" ] && VERDICT="$1"; }   # first (most specific) wins

command -v curl >/dev/null 2>&1 || { echo "curl is required but not installed." >&2; exit 1; }

# Probe a TCP port without needing nc. Returns 0 if something is listening.
tcp_open() {
  timeout "${3:-2}" bash -c "exec 3<>/dev/tcp/$1/$2" 2>/dev/null
}

# ---------------------------------------------------------------------------
# 0. Work out which host to talk to
# ---------------------------------------------------------------------------
bold "0. Locating the Immich server"

if [ -n "$HOST" ] && [ "$DO_SCAN" -eq 0 ]; then
  info "using the host you gave: $HOST"
else
  # If Immich is on THIS box, localhost answers and no sweep is needed.
  if tcp_open 127.0.0.1 "$PORT" 1; then
    HOST="127.0.0.1"
    ok "port $PORT is open on this machine — Immich is running here"
  else
    # Derive the local /24 and sweep it.
    BASE="$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oE 'src [0-9.]+' | awk '{print $2}' | cut -d. -f1-3)"
    [ -z "$BASE" ] && BASE="192.168.1"
    info "sweeping ${BASE}.0/24 for port $PORT (about 15s)..."
    FOUND=()
    for i in $(seq 1 254); do
      ( tcp_open "${BASE}.$i" "$PORT" 1 && echo "${BASE}.$i" ) &
      # keep concurrency sane on a small box
      [ $((i % 64)) -eq 0 ] && wait
    done > /tmp/immich-scan.$$ 2>/dev/null
    wait
    mapfile -t FOUND < <(sort -V /tmp/immich-scan.$$ 2>/dev/null); rm -f /tmp/immich-scan.$$
    if [ "${#FOUND[@]}" -eq 0 ]; then
      bad "nothing is listening on port $PORT anywhere on ${BASE}.0/24"
      info "Either the NUC is off/off-network, or the Immich containers are down,"
      info "or Immich is on a different port. Run this script ON the NUC to find out which."
      verdict "A"
      HOST=""
    else
      HOST="${FOUND[0]}"
      ok "found Immich at ${FOUND[*]}"
      [ "${#FOUND[@]}" -gt 1 ] && warn "more than one host answered; using $HOST"
      info ">> If this is NOT the address in your phone app, that is your bug (section C)."
      verdict "C"
    fi
  fi
fi

BASE_URL=""
[ -n "$HOST" ] && BASE_URL="http://${HOST}:${PORT}"

# ---------------------------------------------------------------------------
# 1. Is the API actually answering?
# ---------------------------------------------------------------------------
SERVER_VER=""
if [ -n "$BASE_URL" ]; then
  bold "1. API reachability — $BASE_URL"

  # /api/server/ping is current; /api/server-info/ping is pre-v1.118.
  PING=""
  for p in /api/server/ping /api/server-info/ping; do
    R="$(curl -s -m 8 -o /dev/null -w '%{http_code}' "${BASE_URL}${p}" 2>/dev/null)"
    if [ "$R" = "200" ]; then PING="$p"; break; fi
  done

  if [ -n "$PING" ]; then
    ok "the API answers ping on $PING"
    info "So the network path, the port and the web server are all fine."
    info "If the phone still cannot reach it, the phone is the problem: wrong URL"
    info "in the app, phone on mobile data instead of wifi, or a VPN / Private Relay."
    verdict "C"
  else
    bad "no HTTP response from ${BASE_URL}/api/server/ping"
    if tcp_open "$HOST" "$PORT" 3; then
      info "The port IS open but the API does not answer — the server container is up"
      info "but unhealthy, usually because it cannot reach Postgres or Redis."
      verdict "E"
    else
      info "Nothing is listening on $PORT. The containers are down."
      verdict "A"
    fi
  fi

  # Version is a public endpoint. Needed to spot an app/server mismatch.
  for p in /api/server/version /api/server-info/version; do
    V="$(curl -s -m 8 "${BASE_URL}${p}" 2>/dev/null)"
    if printf '%s' "$V" | grep -q '"major"'; then
      SERVER_VER="v$(printf '%s' "$V" | grep -oE '"major":[0-9]+' | cut -d: -f2).$(printf '%s' "$V" | grep -oE '"minor":[0-9]+' | cut -d: -f2).$(printf '%s' "$V" | grep -oE '"patch":[0-9]+' | cut -d: -f2)"
      break
    fi
  done
  if [ -n "$SERVER_VER" ]; then
    ok "server version $SERVER_VER"
    info ">> Compare this with the app's version (Settings -> About in the Immich app)."
    info "   They must match. The Play Store / App Store auto-updates the app; a"
    info "   pinned server does not follow, and the app then refuses to log in (section D)."
  else
    warn "could not read the server version"
  fi
fi

# ---------------------------------------------------------------------------
# 2. Optional: does a real login succeed?
# ---------------------------------------------------------------------------
# This is the check that separates "cannot connect" from "connects, login fails".
if [ "$DO_LOGIN" -eq 1 ] && [ -n "$BASE_URL" ]; then
  bold "2. Login test"
  printf '  email: '; read -r EMAIL
  printf '  password (not echoed, not stored, not in your shell history): '
  read -rs PASSWORD; echo
  warn_plain=""
  CODE="$(curl -s -m 15 -o /tmp/immich-login.$$ -w '%{http_code}' \
      -X POST "${BASE_URL}/api/auth/login" \
      -H 'Content-Type: application/json' \
      --data-binary "$(printf '{"email":"%s","password":"%s"}' "$EMAIL" "$PASSWORD")" 2>/dev/null)"
  BODY="$(cat /tmp/immich-login.$$ 2>/dev/null)"; rm -f /tmp/immich-login.$$
  unset PASSWORD
  case "$CODE" in
    200|201) ok "login succeeded — the account and the server are both fine"
             info "Your phone's problem is the app side: the Server Endpoint URL, the"
             info "network the phone is on, or an app/server version mismatch (section C/D)."
             verdict "C" ;;
    401)     bad "login rejected (401) — wrong email or password for this server"
             info "The server itself is healthy. Reset the password from the web UI as admin."
             verdict "F" ;;
    500|502|503)
             bad "login returned $CODE — the server is up but broken behind the API"
             info "Almost always Postgres: down, or read-only because the disk is full."
             info "Body: $(printf '%s' "$BODY" | head -c 200)"
             verdict "B" ;;
    000)     bad "the login request did not complete (timeout / connection refused)"
             verdict "A" ;;
    *)       warn "login returned HTTP $CODE"
             info "Body: $(printf '%s' "$BODY" | head -c 200)" ;;
  esac
fi

# ---------------------------------------------------------------------------
# 3. Local checks — only meaningful when run ON the NUC
# ---------------------------------------------------------------------------
if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
  bold "3. Container state (this machine)"

  PS="$(docker ps -a --filter 'name=immich' --format '{{.Names}}\t{{.State}}\t{{.Status}}' 2>/dev/null)"
  if [ -z "$PS" ]; then
    warn "no containers named *immich* on this box — is Immich on a different machine?"
  else
    printf '%s\n' "$PS" | while IFS=$'\t' read -r n s st; do
      case "$s" in
        running) printf '  \033[32mOK\033[0m    %-34s %s\n' "$n" "$st" ;;
        *)       printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$n" "$st" ;;
      esac
    done
    if printf '%s' "$PS" | grep -qvE $'\trunning\t'; then
      bad "at least one Immich container is not running"
      verdict "A"
    fi
    if printf '%s' "$PS" | grep -qi 'restarting'; then
      bad "a container is stuck in a restart loop — read its logs (section E)"
      verdict "E"
    fi
    if printf '%s' "$PS" | grep -qi 'unhealthy'; then
      bad "a container reports unhealthy"
      verdict "E"
    fi
  fi

  # Postgres is the single most common reason login fails while ping succeeds.
  DB="$(docker ps -a --filter 'name=immich' --format '{{.Names}}' | grep -iE 'postgres|database|_db' | head -1)"
  if [ -n "$DB" ]; then
    if docker exec "$DB" pg_isready >/dev/null 2>&1; then
      ok "Postgres ($DB) is accepting connections"
    else
      bad "Postgres ($DB) is NOT accepting connections — this alone breaks login"
      verdict "E"
    fi
  fi

  bold "4. Recent errors in the server log"
  SRV="$(docker ps -a --filter 'name=immich' --format '{{.Names}}' | grep -iE 'server' | head -1)"
  if [ -n "$SRV" ]; then
    ERRS="$(docker logs --tail 400 "$SRV" 2>&1 | grep -iE 'error|fatal|refus|denied|ENOSPC|no space|extension|version' | tail -12)"
    if [ -n "$ERRS" ]; then
      warn "errors found in $SRV (most recent last):"
      printf '%s\n' "$ERRS" | sed 's/^/        /'
      if printf '%s' "$ERRS" | grep -qiE 'ENOSPC|no space'; then
        bad "the server is out of disk space"; verdict "B"
      fi
      if printf '%s' "$ERRS" | grep -qiE 'extension|vchord|vectors|pgvecto'; then
        bad "a Postgres vector-extension version mismatch — classic post-upgrade failure"
        verdict "E"
      fi
    else
      ok "no obvious errors in the last 400 lines of $SRV"
    fi
  fi
else
  bold "3. Container state"
  info "Docker is not usable from here, so container checks were skipped."
  info "Re-run this script ON the voice NUC to get them."
fi

# ---------------------------------------------------------------------------
# 5. Disk — a full disk looks exactly like "login is broken"
# ---------------------------------------------------------------------------
bold "5. Disk space (this machine)"
# A photo server fills its disk as a matter of routine. When it does, Postgres
# stops accepting writes and the symptom on the phone is a failed LOGIN, not a
# disk error -- which is why this is checked even when everything above passed.
FULL=0; TIGHT=0
while read -r pct mnt; do
  n="${pct%\%}"
  if [ "$n" -ge 95 ] 2>/dev/null; then
    bad "$mnt is ${pct} full — Postgres cannot write at this level"
    FULL=1
  elif [ "$n" -ge 85 ] 2>/dev/null; then
    warn "$mnt is ${pct} full — not fatal yet, but clear it down"
    TIGHT=1
  fi
done < <(df -P -x tmpfs -x devtmpfs -x overlay 2>/dev/null | awk 'NR>1 {print $5, $6}')
if [ "$FULL" -eq 1 ]; then
  verdict "B"
elif [ "$TIGHT" -eq 0 ]; then
  ok "no filesystem is close to full"
fi

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
bold "VERDICT"
if [ "${#FINDINGS[@]}" -eq 0 ]; then
  printf '  Nothing failed here. The server looks healthy from this machine, which\n'
  printf '  points at the phone: see section C (app-side causes) in RUNBOOK.md.\n'
  [ -n "$SERVER_VER" ] && printf '  Check the app version against the server: %s\n' "$SERVER_VER"
else
  printf '  %d finding(s) above.\n' "${#FINDINGS[@]}"
  case "${VERDICT:-C}" in
    A) printf '  Most likely: the Immich containers are not running.  -> RUNBOOK.md section A\n' ;;
    B) printf '  Most likely: the disk is full, so Postgres cannot write. -> RUNBOOK.md section B\n' ;;
    C) printf '  Most likely: the app is pointed at the wrong address, or the phone is\n'
       printf '  off the LAN.                                          -> RUNBOOK.md section C\n' ;;
    D) printf '  Most likely: app/server version mismatch.             -> RUNBOOK.md section D\n' ;;
    E) printf '  Most likely: the server is up but a dependency (Postgres/Redis) is not.\n'
       printf '                                                        -> RUNBOOK.md section E\n' ;;
    F) printf '  Most likely: credentials.                             -> RUNBOOK.md section F\n' ;;
  esac
fi
[ -n "$BASE_URL" ] && printf '\n  Endpoint to put in the phone app: %s\n' "$BASE_URL"
echo
