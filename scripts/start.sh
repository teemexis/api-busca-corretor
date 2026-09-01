#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
export DISPLAY="${DISPLAY:-:99}"

echo "[start] DISPLAY=${DISPLAY} PORT=${PORT}"

if ! command -v Xvfb >/dev/null 2>&1; then
  echo "[start] ERRO: Xvfb nao encontrado"
  exit 1
fi

if pgrep -f "Xvfb ${DISPLAY}" >/dev/null 2>&1; then
  echo "[start] Xvfb ja esta rodando em ${DISPLAY}"
else
  Xvfb "${DISPLAY}" -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
  XVFB_PID=$!
  trap 'kill "${XVFB_PID}" 2>/dev/null || true' EXIT TERM INT
fi

for _ in $(seq 1 20); do
  if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    echo "[start] Xvfb pronto em ${DISPLAY}"
    break
  fi
  sleep 1
done

if ! xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
  echo "[start] ERRO: Xvfb nao respondeu em ${DISPLAY}"
  exit 1
fi

echo "[start] Iniciando Uvicorn em 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
