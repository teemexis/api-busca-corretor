#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
export DISPLAY="${DISPLAY:-:99}"

echo "[start] DISPLAY=${DISPLAY} PORT=${PORT}"

if ! command -v Xvfb >/dev/null 2>&1; then
  echo "[start] ERRO: Xvfb nao encontrado"
  exit 1
fi

Xvfb "${DISPLAY}" -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

cleanup() {
  kill "${XVFB_PID}" 2>/dev/null || true
}

trap cleanup EXIT TERM INT

sleep 3

echo "[start] Iniciando Uvicorn em 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
