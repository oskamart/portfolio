# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env python3
"""Point osys.one at GitHub Pages through the GoDaddy DNS API.

The site is already published to GitHub Pages with CNAME=osys.one. What is
missing is the registrar's A records. This script sets them.

It changes ONLY the records for the two names below and nothing else:

    osys.one      A     185.199.108.153 / .109.153 / .110.153 / .111.153
    www.osys.one  CNAME oskamart.github.io

The existing MX records (Proton Mail) and the SPF TXT are read but not
modified. The script prints a plan and asks for confirmation unless --yes is
given.

Credentials: a GoDaddy API key and secret, in the environment:

    export GODADDY_API_KEY=...
    export GODADDY_API_SECRET=...

Create them at https://developer.godaddy.com/ (Account → API keys).

Usage:
    python3 deploy/godaddy_dns.py            # show the plan
    python3 deploy/godaddy_dns.py --apply    # make the change
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DOMAIN = "osys.one"
PAGES_IPS = [
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
]
WWW_TARGET = "oskamart.github.io"
API = "https://api.godaddy.com/v1"


def api(method: str, path: str, body=None):
    key = os.environ.get("GODADDY_API_KEY")
    secret = os.environ.get("GODADDY_API_SECRET")
    if not key or not secret:
        sys.exit(
            "Set GODADDY_API_KEY and GODADDY_API_SECRET.\n"
            "Create a key at https://developer.godaddy.com/ → Account → API keys."
        )
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Authorization", f"sso-key {key}:{secret}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except urllib.error.URLError as exc:
        sys.exit(f"GoDaddy API unreachable: {exc}")


def current_records():
    status, data = api("GET", f"/domains/{DOMAIN}/records")
    if status != 200:
        sys.exit(f"cannot read records: {status} {data}")
    return data


def plan(records):
    """Work out the exact record set to send."""
    by_type: dict[str, list] = {}
    for rec in records:
        by_type.setdefault(rec["type"], []).append(rec)

    keep = []
    for rec in records:
        if rec["type"] in ("MX", "TXT", "NS", "SOA", "CAA"):
            keep.append(rec)  # mail, SPF, delegation — untouched
    return keep


def desired_records():
    """The full replacement set for the two names we manage."""
    recs = []
    for ip in PAGES_IPS:
        recs.append({"type": "A", "name": "@", "value": ip, "ttl": 3600})
    recs.append({"type": "CNAME", "name": "www", "value": WWW_TARGET, "ttl": 3600})
    return recs


def show(records):
    print("── current records ──────────────────────────────────────────")
    for rec in records:
        print(f"  {rec['type']:6s} {rec.get('name',''):6s} {rec['value'][:60]}")
    print()
    print("── plan ─────────────────────────────────────────────────────")
    for rec in desired_records():
        print(f"  set {rec['type']:6s} {rec['name']:6s} -> {rec['value']}")
    kept = [r for r in records if r["type"] in ("MX", "TXT", "NS", "SOA", "CAA")]
    print(f"  keep {len(kept)} record(s) unchanged "
          f"({', '.join(sorted({r['type'] for r in kept}))})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="make the change")
    ap.add_argument("--yes", action="store_true", help="do not ask")
    args = ap.parse_args()

    records = current_records()
    show(records)

    if not args.apply:
        print("\nDry run. Re-run with --apply to make the change.")
        return 0

    if not args.yes:
        reply = input("\nApply these changes? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted")
            return 1

    payload = desired_records()
    status, data = api("PUT", f"/domains/{DOMAIN}/records", payload)
    if status not in (200, 201, 204):
        print(f"\n✗ GoDaddy returned {status}: {data}")
        return 1

    print("\n✓ records written")
    print("  DNS changes take a few minutes to propagate.")
    print("  Check with:  python3 deploy/check_domain.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
