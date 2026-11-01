# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env bash
# Open the portfolio locally.
#
# Starts the local server if it is not already up, then opens the browser.
# The server binds 0.0.0.0 so the page is reachable from other machines on
# the LAN as well as from this one.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8743}"
URL="http://127.0.0.1:${PORT}/"

if ! curl -sf -o /dev/null --max-time 3 "$URL"; then
  echo "starting the portfolio server on port ${PORT}…"
  setsid nohup python3 "$ROOT/deploy/serve.py" --host 0.0.0.0 --port "$PORT" \
    >/tmp/opencode/opencode-logs/portfolio.log 2>&1 </dev/null &
  disown || true
  for _ in $(seq 1 40); do
    curl -sf -o /dev/null --max-time 2 "$URL" && break
    sleep 0.25
  done
fi

echo "portfolio: ${URL}"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v sensible-browser >/dev/null 2>&1; then
  sensible-browser "$URL" >/dev/null 2>&1 &
fi
