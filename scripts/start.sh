#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

Xvfb "${DISPLAY:-:99}" -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

cleanup() {
  kill "${XVFB_PID}" 2>/dev/null || true
}

trap cleanup EXIT TERM INT

sleep 2

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
