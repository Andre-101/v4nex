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
REPORT="$RUNTIME_DIR/deploy-v0.1.0-$TS.txt"
ENV_BACKUP="$RUNTIME_DIR/env-production-before-deploy-v0.1.0-$TS"
DEPLOY_OK=0
RECREATE_STARTED=0

restore_env_and_services_on_error() {
  local rc=$?
  if [ "$DEPLOY_OK" != "1" ]; then
    echo "ERROR: deploy failed; attempting transactional env restore"
    if [ -f "$ENV_BACKUP" ]; then
      cp "$ENV_BACKUP" "$ENV_FILE"
      chmod 600 "$ENV_FILE"
      echo "env-restored-from=$ENV_BACKUP"
    fi
    if [ "$RECREATE_STARTED" = "1" ] && [ "$V4NEX_DRY_RUN" != "1" ]; then
      echo "attempting service rollback for manifest recreate services"
      for comp in $(manifest_json_array_lines deployment.recreate); do
        compose up -d --no-deps "$comp" || true
      done
    fi
  fi
  exit "$rc"
}
trap restore_env_and_services_on_error ERR

write_report_header "$REPORT"

{
  log "R26 deploy release $(manifest_get version)"
  dry_run_notice

  log "safety prechecks"
  check_env_permissions
  cp "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  echo "env-backup=$ENV_BACKUP"

  compose config --quiet
  check_docker_ipv6_networks
  check_caddyfile_base
  check_critical_volumes
  ensure_no_internal_ports_public "deploy-pre"
  check_services_healthy db backend frontend caddy

  log "deployment policy"
  echo "recreate=$(manifest_get deployment.recreate)"
  echo "do_not_recreate=$(manifest_get deployment.do_not_recreate)"
  echo "validate_only=$(manifest_get deployment.validate_only)"
  echo "requires_manual_approval=$(manifest_get deployment.requires_manual_approval)"

  log "update env allowed non-secret values"
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN skip env mutation"
  else
    python3 - "$MANIFEST" "$ENV_FILE" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
env_path = Path(sys.argv[2])
allowed = manifest["variables"]["non_secret"]

lines = env_path.read_text(encoding="utf-8").splitlines()
seen=set()
out=[]
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key=line.split("=",1)[0]
        if key in allowed:
            out.append(f"{key}={allowed[key]}")
            seen.add(key)
            continue
    out.append(line)

if out and out[-1].strip():
    out.append("")

for key, value in allowed.items():
    if key not in seen:
        out.append(f"{key}={value}")

tmp = env_path.with_name(env_path.name + ".tmp-v4nex-deploy")
tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
tmp.chmod(0o600)
tmp.replace(env_path)
env_path.chmod(0o600)
print("env-updated-allowed-keys-only")
PY
  fi
  check_env_permissions
  grep -E '^(BACKEND_IMAGE_TAG|FRONTEND_IMAGE_TAG|CADDY_IMAGE_TAG|ALLOWED_TARGET_PORTS)=' "$ENV_FILE" || true

  log "pull and validate digests"
  for comp in $(manifest_json_array_lines deployment.recreate); do
    ref="$(image_ref_for_component "$comp")"
    echo "pull $comp $ref"
    if [ "$V4NEX_DRY_RUN" = "1" ]; then
      echo "DRY_RUN skip compose pull $comp"
    else
      compose pull "$comp"
      validate_digest "$comp"
    fi
  done

  log "validate-only component digests"
  for comp in $(manifest_json_array_lines deployment.validate_only); do
    ref="$(image_ref_for_component "$comp")"
    echo "validate-only image $comp $ref"
    if [ "$V4NEX_DRY_RUN" = "1" ]; then
      echo "DRY_RUN skip docker pull $ref"
    else
      docker pull "$ref" >/dev/null
      validate_digest "$comp"
    fi
  done

  log "migrations"
  if [ "$(manifest_get migrations.alembic_required)" = "true" ]; then
    cmd="$(manifest_get migrations.alembic_command)"
    [ -n "$cmd" ] || fail "alembic_required=true but alembic_command is empty"
    echo "Running Alembic command: $cmd"
    if [ "$V4NEX_DRY_RUN" = "1" ]; then
      echo "DRY_RUN skip compose run --rm backend $cmd"
    else
      compose run --rm backend $cmd
    fi
  else
    echo "alembic-not-required"
  fi

  log "container ids before"
  DB_ID_BEFORE="$(compose ps -q db || true)"
  CADDY_ID_BEFORE="$(compose ps -q caddy || true)"
  FRONTEND_ID_BEFORE="$(compose ps -q frontend || true)"

  log "recreate authorized services only"
  for comp in $(manifest_json_array_lines deployment.recreate); do
    echo "recreate $comp"
    if [ "$V4NEX_DRY_RUN" = "1" ]; then
      echo "DRY_RUN skip compose up -d --no-deps $comp"
    else
      RECREATE_STARTED=1
      compose up -d --no-deps "$comp"
      wait_service_healthy "$comp"
    fi
  done

  if [ "$V4NEX_DRY_RUN" != "1" ]; then
    log "verify protected services were not recreated"
    DB_ID_AFTER="$(compose ps -q db || true)"
    CADDY_ID_AFTER="$(compose ps -q caddy || true)"
    FRONTEND_ID_AFTER="$(compose ps -q frontend || true)"
    echo "db_id_before=$DB_ID_BEFORE"
    echo "db_id_after=$DB_ID_AFTER"
    echo "caddy_id_before=$CADDY_ID_BEFORE"
    echo "caddy_id_after=$CADDY_ID_AFTER"
    echo "frontend_id_before=$FRONTEND_ID_BEFORE"
    echo "frontend_id_after=$FRONTEND_ID_AFTER"

    [ "$DB_ID_BEFORE" = "$DB_ID_AFTER" ] || fail "db was recreated unexpectedly"
    [ "$CADDY_ID_BEFORE" = "$CADDY_ID_AFTER" ] || fail "caddy was recreated unexpectedly"
    [ "$FRONTEND_ID_BEFORE" = "$FRONTEND_ID_AFTER" ] || fail "frontend was recreated unexpectedly"
  fi

  check_services_healthy db backend frontend caddy
  ensure_no_internal_ports_public "deploy-post"
  check_platform_health "$(manifest_get platform.platform_mode)"

  DEPLOY_OK=1
  log "deploy result"
  echo "deploy-ok"
} 2>&1 | redact_stream | tee -a "$REPORT"

trap - ERR
echo "report=$REPORT"
