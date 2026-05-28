#!/usr/bin/env bash
# Common helpers for v4nex production scripts.
# Source from scripts/prod/v4nex-*.sh.
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/v4nex/app}"
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
MANIFEST="${MANIFEST:-releases/v0.1.0.json}"
RUNTIME_DIR="${RUNTIME_DIR:-/opt/v4nex/runtime}"
BASE_URL="${BASE_URL:-https://v4nex.com}"
EXPECTED_ENV_OWNER="${EXPECTED_ENV_OWNER:-deploy:deploy}"
V4NEX_DRY_RUN="${V4NEX_DRY_RUN:-0}"

mkdir -p "$RUNTIME_DIR"

log() { printf '=== %s ===\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

require_base() {
  [ -d "$APP_DIR" ] || fail "APP_DIR not found: $APP_DIR"
  cd "$APP_DIR"
  [ -f "$MANIFEST" ] || fail "release manifest not found: $MANIFEST"
  [ -f "$ENV_FILE" ] || fail "env file not found: $ENV_FILE"
  [ -f "$COMPOSE_FILE" ] || fail "compose file not found: $COMPOSE_FILE"
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

dry_run_notice() {
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    echo "DRY_RUN=1: no mutating operation will be executed"
  fi
}

run_or_dry() {
  if [ "$V4NEX_DRY_RUN" = "1" ]; then
    printf 'DRY_RUN would run:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

manifest_get() {
  local expr="$1"
  python3 - "$MANIFEST" "$expr" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cur = data
for part in sys.argv[2].split("."):
    if part == "":
        continue
    if isinstance(cur, list):
        cur = cur[int(part)]
    else:
        cur = cur[part]
if cur is None:
    print("")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur, separators=(",", ":")))
elif isinstance(cur, bool):
    print("true" if cur else "false")
else:
    print(cur)
PY
}

manifest_json_array_lines() {
  local expr="$1"
  python3 - "$MANIFEST" "$expr" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cur = data
for part in sys.argv[2].split("."):
    if part == "":
        continue
    cur = cur[part]
if not isinstance(cur, list):
    raise SystemExit(f"{sys.argv[2]} is not a list")
for item in cur:
    print(item)
PY
}

safe_env_keys() {
  grep -E '^[A-Z0-9_]+=' "$ENV_FILE" | cut -d= -f1 | sort || true
}

load_env_names_only() {
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
}

check_env_permissions() {
  local stat_out mode owner_group
  stat_out="$(stat -c '%U %G %a %n' "$ENV_FILE")"
  echo "$stat_out"
  mode="$(stat -c '%a' "$ENV_FILE")"
  owner_group="$(stat -c '%U:%G' "$ENV_FILE")"
  [ "$mode" = "600" ] || fail "$ENV_FILE must have permissions 600, got $mode"
  [ "$owner_group" = "$EXPECTED_ENV_OWNER" ] || fail "$ENV_FILE must be owned by $EXPECTED_ENV_OWNER, got $owner_group. Override EXPECTED_ENV_OWNER if intentional."
}

redact_stream() {
  sed -E \
    -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/\1REDACTED/gI' \
    -e 's/(Bearer[[:space:]]+)[A-Za-z0-9._~+\/=-]+/\1REDACTED/gI' \
    -e 's/(access_token["]?[[:space:]]*[:=][[:space:]]*["]?)[^",[:space:]]+/\1REDACTED/gI' \
    -e 's/(password["]?[[:space:]]*[:=][[:space:]]*["]?)[^",[:space:]]+/\1REDACTED/gI' \
    -e 's/(CLOUDFLARE_API_TOKEN=)[^[:space:]]+/\1REDACTED/gI' \
    -e 's/(JWT_SECRET=)[^[:space:]]+/\1REDACTED/gI' \
    -e 's/(POSTGRES_PASSWORD=)[^[:space:]]+/\1REDACTED/gI' \
    -e 's/(token[":=][[:space:]]*)[^",[:space:]]+/\1REDACTED/gI' \
    -e 's/(secret[":=][[:space:]]*)[^",[:space:]]+/\1REDACTED/gI'
}

ensure_no_internal_ports_public() {
  local label="${1:-check}"
  log "port security: $label"
  ss -ltn | grep -E ':(80|443|2019|5432|8000|5173)\b' || true
  docker ps --format '{{.Names}} {{.Ports}}' | tee "/tmp/v4nex-${label}-ports.txt"
  if grep -E '2019->|5432->|8000->|5173->' "/tmp/v4nex-${label}-ports.txt" >/dev/null; then
    fail "forbidden internal port published by Docker during $label"
  fi
  # Do not require sudo. ss -ltn is enough to detect host listeners by port.
  if ss -ltn | grep -E ':(2019|5432|8000|5173)\b' >/dev/null; then
    fail "forbidden internal port listener detected during $label"
  fi
  echo "port-security-${label}-ok"
}

check_services_healthy() {
  local services=("$@")
  [ "${#services[@]}" -gt 0 ] || services=(db backend frontend caddy)
  for svc in "${services[@]}"; do
    local cid state health
    cid="$(compose ps -q "$svc" || true)"
    [ -n "$cid" ] || fail "service $svc is not running"
    state="$(docker inspect "$cid" --format '{{.State.Status}}')"
    health="$(docker inspect "$cid" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}')"
    echo "service=$svc state=$state health=$health"
    [ "$state" = "running" ] || fail "service $svc is not running"
    [ "$health" != "unhealthy" ] || fail "service $svc is unhealthy"
  done
}

wait_service_healthy() {
  local svc="$1"
  local attempts="${2:-90}"
  for i in $(seq 1 "$attempts"); do
    local cid state health
    cid="$(compose ps -q "$svc" || true)"
    if [ -n "$cid" ]; then
      state="$(docker inspect "$cid" --format '{{.State.Status}}')"
      health="$(docker inspect "$cid" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}')"
    else
      state="missing"
      health="missing"
    fi
    echo "wait service=$svc state=$state health=$health attempt=$i"
    if [ "$state" = "running" ] && { [ "$health" = "healthy" ] || [ "$health" = "no-healthcheck" ]; }; then
      return 0
    fi
    sleep 2
  done
  compose logs --no-color --tail=160 "$svc" | redact_stream || true
  fail "$svc did not become healthy"
}

check_platform_health() {
  local mode="${1:-$(manifest_get platform.platform_mode)}"
  log "platform checks mode=$mode"
  if [ "$mode" = "open" ]; then
    curl -fsSI "$BASE_URL/" --max-time 20 | head -20
  elif [ "$mode" = "closed_temporarily" ]; then
    code="$(curl -k -sS -o /tmp/v4nex-platform-root.txt -w '%{http_code}' --max-time 20 "$BASE_URL/" || true)"
    echo "platform_root_http_code=$code"
    [ "$code" = "403" ] || [ "$code" = "200" ] || fail "unexpected root HTTP code for closed_temporarily: $code"
  else
    fail "unknown platform_mode: $mode"
  fi
  curl -fsS "$BASE_URL/health" --max-time 20
  echo
  curl -fsS "$BASE_URL/_v4nex/health" --max-time 20
  echo
  echo "platform-health-ok"
}

check_docker_ipv6_networks() {
  log "docker IPv6 network checks"
  docker network inspect app_control app_edge --format 'name={{.Name}} enable_ipv6={{.EnableIPv6}}' || true
  [ "$(docker network inspect app_control --format '{{.EnableIPv6}}')" = "true" ] || fail "app_control IPv6 disabled"
  [ "$(docker network inspect app_edge --format '{{.EnableIPv6}}')" = "true" ] || fail "app_edge IPv6 disabled"
  echo "docker-ipv6-networks-ok"
}

check_caddyfile_base() {
  log "Caddyfile base check"
  [ -f "infra/caddy/Caddyfile.prod" ] || fail "infra/caddy/Caddyfile.prod not found"
  echo "caddyfile-base-exists-ok"
}

check_critical_volumes() {
  log "critical volume check"
  local missing=0
  for vol in app_postgres_data app_caddy_data app_caddy_config; do
    if docker volume inspect "$vol" >/dev/null 2>&1; then
      echo "volume-ok=$vol"
    else
      echo "volume-missing=$vol"
      missing=1
    fi
  done
  [ "$missing" = "0" ] || fail "one or more critical volumes are missing"
  echo "critical-volumes-ok"
}

image_ref_for_component() {
  local comp="$1"
  local image tag
  image="$(manifest_get "components.${comp}.image")"
  tag="$(manifest_get "components.${comp}.tag")"
  echo "${image}:${tag}"
}

digest_for_component() {
  local comp="$1"
  manifest_get "components.${comp}.digest"
}

validate_digest() {
  local comp="$1"
  local ref expected
  ref="$(image_ref_for_component "$comp")"
  expected="$(digest_for_component "$comp")"
  log "digest validation $comp"
  docker image inspect "$ref" --format '{{join .RepoDigests "\n"}}' | tee "/tmp/v4nex-${comp}-digests.txt"
  grep "$expected" "/tmp/v4nex-${comp}-digests.txt" >/dev/null || fail "$comp digest mismatch: expected $expected"
  echo "${comp}-digest-ok"
}

write_report_header() {
  local report="$1"
  {
    echo "v4nex report"
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host=$(hostname)"
    echo "app_dir=$APP_DIR"
    echo "manifest=$MANIFEST"
    echo "dry_run=$V4NEX_DRY_RUN"
    echo
  } > "$report"
}

write_release_current() {
  local result_json="$1"
  local out="$RUNTIME_DIR/release-current.json"
  python3 - "$MANIFEST" "$result_json" "$out" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out = Path(sys.argv[3])
doc = {
  "release_id": manifest.get("release_id"),
  "version": manifest.get("version"),
  "timestamp_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
  "components": {
    name: {
      "image": comp.get("image"),
      "tag": comp.get("tag"),
      "digest": comp.get("digest"),
    }
    for name, comp in manifest.get("components", {}).items()
  },
  "smoke": {
    "result": "ok" if result.get("ok") else "failed",
    "bridge_id": result.get("bridge_id"),
    "public_url": result.get("public_url"),
    "subdomain": result.get("subdomain"),
    "target_port": result.get("target_port"),
  }
}
out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
print(out)
PY
}
