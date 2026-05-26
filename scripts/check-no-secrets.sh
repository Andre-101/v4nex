#!/usr/bin/env bash
set -euo pipefail

echo "[check-no-secrets] Ejecutando validaciones básicas..."

# Patrones simples para evitar llaves/secretos frecuentes en commits.
if rg -n --hidden --glob '!.git' --glob '!node_modules' \
  '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|xox[baprs]-|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z\-_]{35})' .; then
  echo "[check-no-secrets] Posible secreto detectado."
  exit 1
fi

echo "[check-no-secrets] OK: no se detectaron secretos obvios."
