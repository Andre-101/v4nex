#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/v4nex-common.sh
. "$SCRIPT_DIR/lib/v4nex-common.sh"

require_cmd docker
require_cmd python3
require_cmd curl
require_cmd ss
require_base

TS="$(date -u +%Y%m%d_%H%M%S)"
REPORT="$RUNTIME_DIR/open-platform-v0.1.0-$TS.txt"
write_report_header "$REPORT"

{
  log "R26 open platform"
  backup="${1:-}"
  if [ -z "$backup" ]; then
    backup="$(ls -1t "$RUNTIME_DIR"/caddy-live-before-platform-closed-*.json 2>/dev/null | head -1 || true)"
  fi
  [ -n "$backup" ] || fail "no Caddy backup found; pass backup path explicitly"
  [ -f "$backup" ] || fail "backup file not found: $backup"
  echo "restore_backup=$backup"

  log "restore Caddy live config"
  cat "$backup" | compose exec -T backend python -c 'import sys, urllib.request; data=sys.stdin.buffer.read(); req=urllib.request.Request("http://caddy:2019/load", data=data, headers={"Content-Type":"application/json"}, method="POST"); print("caddy_restore_status=", urllib.request.urlopen(req, timeout=15).status)'

  sleep 3

  log "verify platform"
  root_code="$(curl -k -sS -o /tmp/v4nex-open-platform-root.txt -w '%{http_code}' --max-time 15 "$BASE_URL/" || true)"
  echo "platform_root_http_code=$root_code"
  curl -fsS "$BASE_URL/health" --max-time 15
  echo
  curl -fsS "$BASE_URL/_v4nex/health" --max-time 15
  echo

  ensure_no_internal_ports_public "open-platform"

  log "open platform result"
  echo "platform-restore-ok"
} 2>&1 | redact_stream | tee -a "$REPORT"

echo "report=$REPORT"
