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
REPORT="$RUNTIME_DIR/preflight-v0.1.0-$TS.txt"
write_report_header "$REPORT"

{
  log "R26 preflight release $(manifest_get version)"
  dry_run_notice

  log "manifest JSON parse"
  python3 -m json.tool "$MANIFEST" >/dev/null
  echo "manifest-json-ok"

  log "latest check"
  python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
for name, c in m.get("components", {}).items():
    if str(c.get("tag","")).lower() == "latest":
        raise SystemExit(f"latest tag not allowed for {name}")
print("no-latest-component-tags-ok")
PY

  log "env file"
  check_env_permissions
  echo "env-keys:"
  safe_env_keys

  log "required env keys"
  python3 - "$MANIFEST" "$ENV_FILE" <<'PY'
import json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
env_path=Path(sys.argv[2])
keys=set()
for line in env_path.read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        keys.add(line.split("=",1)[0])
required=set(m["variables"]["non_secret"].keys()) | set(m["variables"]["sensitive_names_only"])
missing=sorted(required-keys)
if missing:
    raise SystemExit("missing env keys: " + ", ".join(missing))
print("required-env-keys-ok")
PY

  check_caddyfile_base
  check_critical_volumes

  log "compose config"
  compose config --quiet
  echo "compose-config-ok"

  check_docker_ipv6_networks

  log "current services"
  compose ps
  check_services_healthy db backend frontend caddy

  ensure_no_internal_ports_public "preflight"

  log "GHCR pull availability and digest check"
  for comp in backend frontend caddy; do
    ref="$(image_ref_for_component "$comp")"
    echo "pull-check $comp $ref"
    if [ "$V4NEX_DRY_RUN" = "1" ]; then
      echo "DRY_RUN skip docker pull $ref"
    else
      docker pull "$ref" >/dev/null
      validate_digest "$comp"
    fi
  done

  check_platform_health "$(manifest_get platform.platform_mode)"

  log "preflight result"
  echo "preflight-ok"
} 2>&1 | tee -a "$REPORT"

echo "report=$REPORT"
