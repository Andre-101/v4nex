#!/usr/bin/env bash
set -euo pipefail

echo "[check-no-secrets] Ejecutando validaciones básicas..."

if ! command -v rg >/dev/null 2>&1; then
  echo "[check-no-secrets] Error: ripgrep (rg) no está instalado o no está disponible en PATH."
  echo "[check-no-secrets] Instala ripgrep o usa WSL/Git Bash con rg disponible."
  exit 1
fi

if ! rg --version >/dev/null 2>&1; then
  echo "[check-no-secrets] Error: ripgrep (rg) está en PATH, pero no se puede ejecutar."
  echo "[check-no-secrets] Instala ripgrep o usa WSL/Git Bash con rg disponible."
  exit 1
fi

# Patrones simples para evitar llaves/secretos frecuentes en commits.
if rg -n --hidden --glob '!.git' --glob '!node_modules' \
  '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|xox[baprs]-|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z\-_]{35})' .; then
  echo "[check-no-secrets] Posible secreto detectado."
  exit 1
fi

echo "[check-no-secrets] OK: no se detectaron secretos obvios."
