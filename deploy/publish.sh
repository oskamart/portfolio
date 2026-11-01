#!/usr/bin/env bash
# Publish the portfolio to GitHub Pages, which serves osys.one.
#
# Steps: regenerate the measured manifest -> verify the site -> commit -> push
# -> confirm the live site answers.
#
# Usage:  deploy/publish.sh [--dry-run]
#
# The GitHub token is read from the gh CLI config if present, else from
# $GITHUB_TOKEN. Nothing is written to disk.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

say() { printf '\033[36m▸\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m✓\033[0m %s\n' "$*"; }
die() { printf '\033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

# ── token ────────────────────────────────────────────────────────────────────
token() {
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then printf '%s' "$GITHUB_TOKEN"; return; fi
  local f="$HOME/.config/gh/hosts.yml"
  [[ -f "$f" ]] || return 1
  python3 - "$f" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
m = re.findall(r"oauth_token:\s*(\S+)", s)
print(m[-1] if m else "")
PY
}

TOKEN="$(token || true)"
[[ -n "$TOKEN" ]] || die "no GitHub token found (set GITHUB_TOKEN or log in with gh)"

OWNER="oskamart"
REPO="portfolio"
BRANCH="main"

# ── 1. regenerate the measured manifest ──────────────────────────────────────
say "measuring the source trees (build/manifest.py)"
python3 "$ROOT/build/manifest.py" --root "$HOME" --out assets/manifest.json

# ── 2. verify the site ───────────────────────────────────────────────────────
say "verifying the site (build/verify.py)"
if [[ $DRY -eq 0 ]]; then
  # Start a temporary server so the served paths are checked too.
  PORT=$(( ( RANDOM % 2000 ) + 9000 ))
  python3 "$ROOT/serve.py" --port "$PORT" --no-browser >/tmp/portfolio-verify.log 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null || true' EXIT
  for _ in $(seq 1 30); do
    curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break
    sleep 0.2
  done
  python3 "$ROOT/build/verify.py" --url "http://127.0.0.1:$PORT/"
  kill $SRV 2>/dev/null || true
  trap - EXIT
else
  python3 "$ROOT/build/verify.py" --no-serve-check
fi
ok "site verified"

# ── 3. commit ────────────────────────────────────────────────────────────────
cd "$ROOT"
git add -A
if git diff --cached --quiet; then
  say "nothing to commit"
else
  MSG="Portfolio: refresh measured manifest"
  git -c user.name="oskamart" -c user.email="oskamart@proton.me" \
      commit -q -m "$MSG

Co-Authored-By: opencode <opencode@opencode.ai>"
  ok "committed"
fi

# ── 4. push ──────────────────────────────────────────────────────────────────
if [[ $DRY -eq 1 ]]; then
  say "dry run: would push to $OWNER/$REPO"
  exit 0
fi

say "pushing to $OWNER/$REPO ($BRANCH)"
git push -q "https://$OWNER:$TOKEN@github.com/$OWNER/$REPO.git" "$BRANCH" --force
ok "pushed"

# ── 5. confirm ───────────────────────────────────────────────────────────────
say "confirming the live site"
for host in "https://$OWNER.github.io/$REPO/" "https://$REPO.pages.dev/"; do
  code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' "$host" || echo 000)
  if [[ "$code" == "200" ]]; then
    ok "$host → $code"
  else
    say "$host → $code (may still be building)"
  fi
done

# The custom domain needs its A records at the registrar to point here.
say "checking osys.one"
code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' https://osys.one/ || echo 000)
[[ "$code" == "200" ]] && ok "https://osys.one/ → $code" \
                      || say "https://osys.one/ → $code (waiting on the registrar A records)"
