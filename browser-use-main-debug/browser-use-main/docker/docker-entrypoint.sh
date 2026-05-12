#!/bin/sh
set -eu

XVFB_DISPLAY="${XVFB_DISPLAY:-:99}"
XVFB_ARGS="${XVFB_ARGS:--screen 0 1920x1080x24}"
XVFB_AUTH_DIR="$(mktemp -d -t browseruse-xvfb.XXXXXX)"
XVFB_AUTH_FILE="$XVFB_AUTH_DIR/Xauthority"

cleanup() {
  if [ -n "${BROWSER_PID:-}" ] && kill -0 "$BROWSER_PID" 2>/dev/null; then
    kill "$BROWSER_PID" 2>/dev/null || true
    wait "$BROWSER_PID" 2>/dev/null || true
  fi
  if [ -n "${XVFB_PID:-}" ] && kill -0 "$XVFB_PID" 2>/dev/null; then
    kill "$XVFB_PID" 2>/dev/null || true
    wait "$XVFB_PID" 2>/dev/null || true
  fi
  rm -rf "$XVFB_AUTH_DIR"
}
trap cleanup EXIT INT TERM

touch "$XVFB_AUTH_FILE"
xauth -f "$XVFB_AUTH_FILE" add "$XVFB_DISPLAY" . "$(mcookie)" >/dev/null 2>&1

Xvfb "$XVFB_DISPLAY" $XVFB_ARGS -nolisten tcp -auth "$XVFB_AUTH_FILE" &
XVFB_PID=$!

for _ in $(seq 1 50); do
  if kill -0 "$XVFB_PID" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

export DISPLAY="$XVFB_DISPLAY"
export XAUTHORITY="$XVFB_AUTH_FILE"

/app/.venv/bin/browser-use "$@" &
BROWSER_PID=$!
wait "$BROWSER_PID"
