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
REPORT="$RUNTIME_DIR/audit-state-v0.1.0-$TS.txt"
write_report_header "$REPORT"

{
  log "R26 audit state"
  echo "host=$(hostname)"
  date -u

  log "manifest summary"
  echo "release=$(manifest_get version)"
  echo "status=$(manifest_get status)"
  echo "platform_mode=$(manifest_get platform.platform_mode)"

  log "compose ps"
  compose ps

  log "running containers"
  docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'

  log "env metadata and keys only"
  check_env_permissions
  safe_env_keys

  log "release non-secret env keys present"
  for key in BACKEND_IMAGE_TAG FRONTEND_IMAGE_TAG CADDY_IMAGE_TAG ALLOWED_TARGET_PORTS; do
    if grep -q "^${key}=" "$ENV_FILE"; then
      echo "${key}=present"
    else
      echo "${key}=missing"
    fi
  done

  log "networks"
  docker network inspect app_control app_edge --format 'name={{.Name}} enable_ipv6={{.EnableIPv6}} driver={{.Driver}}'
  docker network inspect app_control app_edge --format '{{json .IPAM.Config}}'

  ensure_no_internal_ports_public "audit"

  log "services health"
  check_services_healthy db backend frontend caddy

  log "platform health"
  check_platform_health "$(manifest_get platform.platform_mode)"

  log "image tags"
  for svc in backend frontend caddy db; do
    cid="$(compose ps -q "$svc" || true)"
    if [ -n "$cid" ]; then
      echo "$svc image=$(docker inspect "$cid" --format '{{.Config.Image}}')"
    fi
  done

  log "db safe counts"
  load_env_names_only
  compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) as users_count from users;"
  compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select status, count(*) from bridges group by status order by status;"

  log "audit result"
  echo "audit-state-ok"
} 2>&1 | redact_stream | tee -a "$REPORT"

echo "report=$REPORT"
