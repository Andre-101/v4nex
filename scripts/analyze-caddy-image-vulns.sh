#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"

if [[ "$CADDY_LOCAL_TAG" == *":latest" || "$CADDY_LOCAL_TAG" == "latest" || "$CADDY_LOCAL_TAG" == */latest ]]; then
  echo "ERROR CADDY_LOCAL_TAG must not use latest."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

if ! docker image inspect "$CADDY_LOCAL_TAG" >/dev/null 2>&1; then
  echo "ERROR local image not found: $CADDY_LOCAL_TAG"
  echo "Run: bash scripts/build-caddy-custom-local.sh"
  exit 1
fi

echo "Analyzing Caddy image vulnerabilities"
echo "  tag: $CADDY_LOCAL_TAG"
echo "  push: disabled"
echo "  Cloudflare API: not called"
echo "  ACME/TLS issuance: not executed"

if docker scout version >/dev/null 2>&1; then
  echo "Docker Scout CVE summary"
  docker scout cves "$CADDY_LOCAL_TAG" || true
  echo "Docker Scout critical/high CVEs"
  docker scout cves "$CADDY_LOCAL_TAG" --only-severity critical,high || true
  echo "Docker Scout recommendations"
  docker scout recommendations "$CADDY_LOCAL_TAG" || true
else
  echo "WARN Docker Scout not available; skipped scout CVE analysis."
fi

if command -v trivy >/dev/null 2>&1; then
  echo "Trivy critical/high CVEs"
  trivy image --severity CRITICAL,HIGH "$CADDY_LOCAL_TAG" || true
else
  echo "WARN Trivy not available; skipped Trivy CVE analysis."
fi

echo "Caddy vulnerability analysis completed."
