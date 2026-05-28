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
REPORT="$RUNTIME_DIR/rollback-v0.1.0-$TS.txt"
ENV_BACKUP="$RUNTIME_DIR/env-production-before-rollback-v0.1.0-$TS"
ROLLBACK_OK=0

restore_env_on_error() {
  local rc=$?
  if [ "$ROLLBACK_OK" != "1" ] && [ -f "$ENV_BACKUP" ]; then
    echo "ERROR: rollback failed; restoring env from $ENV_BACKUP"
    cp "$ENV_BACKUP" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  fi
  exit "$rc"
}
trap restore_env_on_error ERR

write_report_header "$REPORT"

{
  log "R26 rollback release $(manifest_get version)"
  dry_run_notice

  log "rollback scope"
  echo "rollback_services=$(manifest_get rollback.rollback_services)"
  echo "rollback_env_keys=$(manifest_get rollback.rollback_env_keys)"

  check_env_permissions
  cp "$ENV_FILE" "$ENV_BACKUP"
  chmod 600 "$ENV_BACKUP"
  echo "env-backup=$ENV_BACKUP"

  compose config --quiet
  ensure_no_internal_ports_public "rollback-pre"

  previous_backend_tag="$(manifest_get rollback.previous_backend_tag)"
  previous_backend_digest="$(manifest_get rollback.previous_backend_digest)"
  [ -n "$previous_backend_tag" ] || fail "previous_backend_tag missing"
  [ -n "$previous_backend_digest" ] || fail "previous_backend_digest missing"

  log "update backend tag only"
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN skip BACKEND_IMAGE_TAG rollback to $previous_backend_tag"
  else
    python3 - "$ENV_FILE" "$previous_backend_tag" <<'PY'
import sys
from pathlib import Path
path=Path(sys.argv[1])
tag=sys.argv[2]
lines=path.read_text().splitlines()
out=[]
found=False
for line in lines:
    if line.startswith("BACKEND_IMAGE_TAG="):
        out.append(f"BACKEND_IMAGE_TAG={tag}")
        found=True
    else:
        out.append(line)
if not found:
    out.append(f"BACKEND_IMAGE_TAG={tag}")
tmp=path.with_name(path.name+".tmp-v4nex-rollback")
tmp.write_text("\n".join(out)+"\n")
tmp.chmod(0o600)
tmp.replace(path)
path.chmod(0o600)
print("backend-tag-rolled-back")
PY
  fi
  check_env_permissions
  grep -E '^BACKEND_IMAGE_TAG=' "$ENV_FILE" || true

  log "pull backend previous image"
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN skip compose pull backend"
  else
    compose pull backend
  fi

  log "validate previous backend digest"
  backend_image="$(manifest_get components.backend.image):${previous_backend_tag}"
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN skip digest validation for $backend_image"
  else
    docker image inspect "$backend_image" --format '{{join .RepoDigests "\n"}}' | tee /tmp/v4nex-rollback-backend-digests.txt
    grep "$previous_backend_digest" /tmp/v4nex-rollback-backend-digests.txt >/dev/null || fail "rollback backend digest mismatch"
  fi

  log "recreate backend only"
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN skip compose up -d --no-deps backend"
  else
    compose up -d --no-deps backend
    wait_service_healthy backend
  fi

  check_services_healthy db backend frontend caddy
  check_platform_health "$(manifest_get platform.platform_mode)"
  ensure_no_internal_ports_public "rollback-post"

  ROLLBACK_OK=1
  log "rollback result"
  echo "rollback-ok"
} 2>&1 | redact_stream | tee -a "$REPORT"

trap - ERR
echo "report=$REPORT"
