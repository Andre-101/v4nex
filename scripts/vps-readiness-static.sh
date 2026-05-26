#!/usr/bin/env bash
set -euo pipefail

EXPECTED_DOMAIN="v4nex.com"
EXPECTED_IPV4="${EXPECTED_IPV4:?EXPECTED_IPV4 is required}"
EXPECTED_IPV6="${EXPECTED_IPV6:?EXPECTED_IPV6 is required}"
EXPECTED_SSH_PORT="${EXPECTED_SSH_PORT:?EXPECTED_SSH_PORT is required}"
EXPECTED_DEPLOY_USER="${EXPECTED_DEPLOY_USER:-deploy}"
EXPECTED_BASE_PATH="${EXPECTED_BASE_PATH:-/opt/v4nex/app}"

echo "VPS readiness static inventory"
echo "OK expected domain: ${EXPECTED_DOMAIN}"
echo "OK expected IPv4: ${EXPECTED_IPV4}"
echo "OK expected IPv6: ${EXPECTED_IPV6}"
echo "OK expected SSH port: ${EXPECTED_SSH_PORT}"
echo "OK expected deploy user: ${EXPECTED_DEPLOY_USER}"
echo "OK expected base path: ${EXPECTED_BASE_PATH}"
echo "OK expected dirs:"
echo "  /opt/v4nex/app"
echo "  /opt/v4nex/backups"
echo "  /opt/v4nex/logs"
echo "  /opt/v4nex/runtime"
echo "  /opt/v4nex/scripts"
echo "No SSH connection attempted."
