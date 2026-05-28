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
REPORT="$RUNTIME_DIR/close-platform-v0.1.0-$TS.txt"
BACKUP="$RUNTIME_DIR/caddy-live-before-platform-closed-$TS.json"
PATCHED="$RUNTIME_DIR/caddy-live-platform-closed-$TS.json"
write_report_header "$REPORT"

{
  log "R26 close platform"
  load_env_names_only
  domain="${DOMAIN:-${CADDY_DOMAIN:-v4nex.com}}"
  echo "domain=$domain"

  log "backup live Caddy config"
  compose exec -T backend python -c 'import urllib.request; print(urllib.request.urlopen("http://caddy:2019/config/", timeout=10).read().decode())' > "$BACKUP"
  chmod 640 "$BACKUP"
  echo "backup=$BACKUP"

  log "patch config with apex-only block preserving health and API"
  python3 - "$BACKUP" "$PATCHED" "$domain" <<'PY'
import json, sys
from pathlib import Path

src=Path(sys.argv[1])
dst=Path(sys.argv[2])
domain=sys.argv[3]
cfg=json.loads(src.read_text())

# Match only apex host, but explicitly exclude health/API paths.
# This prevents the block from capturing /health and /_v4nex/*.
block_route={
  "match":[{
    "host":[domain],
    "not":[
      {"path":["/health","/_v4nex/*"]}
    ]
  }],
  "handle":[{"handler":"static_response","status_code":403,"body":"v4nex platform temporarily closed\n"}],
  "terminal":True
}

servers=cfg.get("apps",{}).get("http",{}).get("servers",{})
if not servers:
    raise SystemExit("no http servers found in Caddy config")

for server in servers.values():
    routes=server.setdefault("routes",[])
    routes[:]=[
        r for r in routes
        if not (
            r.get("handle", [{}])[0].get("handler") == "static_response"
            and "v4nex platform temporarily closed" in r.get("handle", [{}])[0].get("body", "")
        )
    ]
    routes.insert(0, block_route)

dst.write_text(json.dumps(cfg, indent=2))
print(f"patched={dst}")
PY
  chmod 640 "$PATCHED"

  log "load patched config"
  cat "$PATCHED" | compose exec -T backend python -c 'import sys, urllib.request; data=sys.stdin.buffer.read(); req=urllib.request.Request("http://caddy:2019/load", data=data, headers={"Content-Type":"application/json"}, method="POST"); print("caddy_load_status=", urllib.request.urlopen(req, timeout=15).status)'

  sleep 3

  log "verify platform closed while health remains open"
  code="$(curl -k -sS -o /tmp/v4nex-close-platform-body.txt -w '%{http_code}' --max-time 15 "$BASE_URL/" || true)"
  echo "platform_root_http_code=$code"
  [ "$code" = "403" ] || fail "platform root is not closed with 403"

  curl -fsS "$BASE_URL/health" --max-time 15
  echo
  curl -fsS "$BASE_URL/_v4nex/health" --max-time 15
  echo

  log "verify active bridge if present"
  load_env_names_only
  bridge_url="$(compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select public_url from bridges where upper(status::text)='ACTIVE' order by activated_at desc nulls last, created_at desc limit 1;" | tr -d '[:space:]' || true)"
  echo "active_bridge_url=${bridge_url:-none}"
  if [ -n "$bridge_url" ]; then
    curl -k -I --max-time 20 "$bridge_url/" || true
  fi

  ensure_no_internal_ports_public "close-platform"

  log "close platform result"
  echo "platform-closed-ok"
} 2>&1 | redact_stream | tee -a "$REPORT"

echo "report=$REPORT"
echo "backup=$BACKUP"
