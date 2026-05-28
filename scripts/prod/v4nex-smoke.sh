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

MODE="${1:-minimal}" # minimal | extended
TS="$(date -u +%Y%m%d_%H%M%S)"
REPORT="$RUNTIME_DIR/smoke-v0.1.0-$TS.txt"
RESULT_JSON="$RUNTIME_DIR/smoke-v0.1.0-$TS-result.json"
write_report_header "$REPORT"

run_minimal() {
  log "smoke minimal"
  compose config --quiet
  check_services_healthy db backend frontend caddy
  check_platform_health "$(manifest_get platform.platform_mode)"
  ensure_no_internal_ports_public "smoke-minimal"
  echo "smoke-minimal-ok"
}

run_extended() {
  log "smoke extended"
  [ "$(manifest_get bridge_smoke.enabled)" = "true" ] || fail "bridge_smoke.enabled is not true"

  local target_ipv6 target_port prefix subdomain name
  target_ipv6="${TARGET_IPV6:-$(manifest_get bridge_smoke.target_ipv6)}"
  target_port="${TARGET_PORT:-$(manifest_get bridge_smoke.target_port)}"
  prefix="$(manifest_get bridge_smoke.test_subdomain_prefix)"
  [ -n "$target_ipv6" ] || fail "TARGET_IPV6 is required because bridge_smoke.target_ipv6 is null/empty"
  [ -n "$target_port" ] || fail "TARGET_PORT is required"
  subdomain="${prefix:-smoke}-$(date -u +%Y%m%d%H%M%S)"
  name="smoke-v0.1.0-$(date -u +%Y%m%d%H%M%S)"

  log "extended smoke required variables"
  echo "TARGET_IPV6=$target_ipv6"
  echo "TARGET_PORT=$target_port"
  echo "V4NEX_EMAIL=${V4NEX_EMAIL:+set}"
  echo "V4NEX_PASSWORD=${V4NEX_PASSWORD:+set}"
  echo "BASE_URL=$BASE_URL"

  log "target reachability"
  curl -g -sS -I --max-time 10 "http://[${target_ipv6}]:${target_port}/"
  compose exec -T backend python - <<PY
import socket, urllib.request
target="${target_ipv6}"
port=int("${target_port}")
url=f"http://[{target}]:{port}/"
sock=socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
sock.settimeout(10)
sock.connect((target, port, 0, 0))
sock.close()
print("backend_ipv6_tcp_ok")
with urllib.request.urlopen(url, timeout=15) as resp:
    print("backend_http_status=", resp.status)
PY

  if [ -z "${V4NEX_EMAIL:-}" ]; then
    read -r -p "v4nex email: " V4NEX_EMAIL
    export V4NEX_EMAIL
  fi
  if [ -z "${V4NEX_PASSWORD:-}" ]; then
    read -r -s -p "v4nex password: " V4NEX_PASSWORD
    echo
    export V4NEX_PASSWORD
  fi

  export V4NEX_RESULT_JSON="$RESULT_JSON"
  export V4NEX_TEST_NAME="$name"
  export V4NEX_TEST_SUBDOMAIN="$subdomain"
  export V4NEX_TARGET_IPV6="$target_ipv6"
  export V4NEX_TARGET_PORT="$target_port"
  export BASE_URL

  python3 - <<'PY'
import json, os, urllib.error, urllib.request
from pathlib import Path

BASE_URL=os.environ.get("BASE_URL","https://v4nex.com")
email=os.environ["V4NEX_EMAIL"]
password=os.environ["V4NEX_PASSWORD"]
name=os.environ["V4NEX_TEST_NAME"]
subdomain=os.environ["V4NEX_TEST_SUBDOMAIN"]
target_ipv6=os.environ["V4NEX_TARGET_IPV6"]
target_port=int(os.environ["V4NEX_TARGET_PORT"])
result_path=Path(os.environ["V4NEX_RESULT_JSON"])

def request(path, payload=None, token=None, method=None):
    data=None
    headers={"Accept":"application/json"}
    if payload is not None:
        data=json.dumps(payload).encode()
        headers["Content-Type"]="application/json"
    if token:
        headers["Authorization"]=f"Bearer {token}"
    req=urllib.request.Request(BASE_URL+path, data=data, headers=headers, method=method or ("POST" if payload is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")

result={"name":name,"subdomain":subdomain,"target_port":target_port,"ok":False}

status, body = request("/_v4nex/auth/login", {"email": email, "password": password})
print("login_status=", status)
if status != 200:
    print("login_failed_body_prefix=", body[:500])
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise SystemExit(1)
token=json.loads(body)["access_token"]
print("token_received= yes")

payload={"name":name,"subdomain":subdomain,"target_ipv6":target_ipv6,"target_port":target_port}
status, body = request("/_v4nex/bridges", payload, token)
print("create_status=", status)
if status not in (200, 201):
    print("create_failed_body_prefix=", body[:700])
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise SystemExit(1)
bridge=json.loads(body)
bridge_id=bridge["id"]
public_url=bridge["public_url"]
print("bridge_id=", bridge_id)
print("public_url=", public_url)
print("create_state=", bridge.get("status"))
if bridge.get("status") != "DRAFT":
    raise SystemExit("created bridge is not DRAFT")

status, body = request(f"/_v4nex/bridges/{bridge_id}/validate", {}, token, "POST")
print("validate_status=", status)
if status != 200:
    print("validate_failed_body_prefix=", body[:700])
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise SystemExit(1)

status, body = request(f"/_v4nex/bridges/{bridge_id}", token=token)
after_validate=json.loads(body)
print("after_validate_status=", after_validate.get("status"))
print("last_tcp_validation_result=", after_validate.get("last_tcp_validation_result"))
if after_validate.get("status") != "READY" or after_validate.get("last_tcp_validation_result") != "OK":
    raise SystemExit("bridge not READY with OK validation")

status, body = request(f"/_v4nex/bridges/{bridge_id}/activate", {}, token, "POST")
print("activate_status=", status)
if status != 200:
    print("activate_failed_body_prefix=", body[:700])
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise SystemExit(1)

status, body = request(f"/_v4nex/bridges/{bridge_id}", token=token)
after_activate=json.loads(body)
print("after_activate_status=", after_activate.get("status"))
if after_activate.get("status") != "ACTIVE":
    raise SystemExit("bridge not ACTIVE")

result.update({"bridge_id":bridge_id,"public_url":public_url,"ok":True})
result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("api-lifecycle-ok")
PY

  unset V4NEX_PASSWORD

  check_platform_health "$(manifest_get platform.platform_mode)"
  ensure_no_internal_ports_public "smoke-extended"

  local public_url
  public_url="$(python3 - "$RESULT_JSON" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text()).get("public_url",""))
PY
)"
  [ -n "$public_url" ] || fail "public_url missing from smoke result"
  echo "public_url=$public_url"

  curl -sS -D /tmp/v4nex-smoke-bridge-headers.txt -o /tmp/v4nex-smoke-bridge-body.txt --max-time 30 "$public_url/"
  code="$(awk 'toupper($0) ~ /^HTTP\// {code=$2} END {print code}' /tmp/v4nex-smoke-bridge-headers.txt)"
  echo "bridge_http_code=${code:-none}"
  [ "$code" = "200" ] || fail "bridge public URL did not return HTTP 200"

  if grep -qiE 'v4nex frontend|Frontend Skeleton|<div id="root"></div>' /tmp/v4nex-smoke-bridge-body.txt; then
    fail "bridge public URL returned frontend base"
  fi

  echo "bridge-public-url-ok"
  echo "bridge-public-url-not-frontend-ok"

  if [ "$(manifest_get cleanup.delete_smoke_bridge_after_success)" = "true" ]; then
    warn "delete_smoke_bridge_after_success=true, but delete endpoint is not guaranteed; cleanup not implemented in v0.1.0 script"
  fi

  if [ "$(manifest_get cleanup.restore_caddy_base_after_success)" = "true" ]; then
    warn "restore_caddy_base_after_success=true requested; use v4nex-open-platform.sh or manual Caddy restore policy if required"
  fi

  release_current="$(write_release_current "$RESULT_JSON")"
  echo "release-current-written=$release_current"
  echo "smoke-extended-ok"
}

{
  log "R26 smoke release $(manifest_get version) mode=$MODE"
  if [ "$MODE" = "minimal" ]; then
    run_minimal
  elif [ "$MODE" = "extended" ]; then
    run_minimal
    run_extended
  else
    fail "usage: $0 [minimal|extended]"
  fi
} 2>&1 | redact_stream | tee -a "$REPORT"

echo "report=$REPORT"
echo "result_json=$RESULT_JSON"
