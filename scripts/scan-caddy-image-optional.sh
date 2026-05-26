#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"

if [[ "$CADDY_LOCAL_TAG" == *":latest" || "$CADDY_LOCAL_TAG" == "latest" || "$CADDY_LOCAL_TAG" == */latest ]]; then
  echo "ERROR CADDY_LOCAL_TAG must not use latest."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "WARN docker command not found; optional image scan skipped."
  exit 0
fi

if ! docker image inspect "$CADDY_LOCAL_TAG" >/dev/null 2>&1; then
  echo "WARN local image not found; optional image scan skipped: $CADDY_LOCAL_TAG"
  exit 0
fi

if command -v trivy >/dev/null 2>&1; then
  echo "Running optional Trivy scan for $CADDY_LOCAL_TAG"
  trivy image "$CADDY_LOCAL_TAG"
  exit 0
fi

if docker scout version >/dev/null 2>&1; then
  echo "Running optional Docker Scout quickview for $CADDY_LOCAL_TAG"
  docker scout quickview "$CADDY_LOCAL_TAG"
  echo "Running optional Docker Scout critical/high CVE view for $CADDY_LOCAL_TAG"
  docker scout cves "$CADDY_LOCAL_TAG" --only-severity critical,high || true
  exit 0
fi

echo "WARN no optional scanner found."
echo "Install trivy or enable docker scout to run an image vulnerability scan."
