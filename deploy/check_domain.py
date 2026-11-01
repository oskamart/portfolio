#!/usr/bin/env python3
"""Check whether osys.one is pointed at this deployment, and report what is
still missing.

The site is served by GitHub Pages under the CNAME osys.one. For that to work
the registrar must publish:

    osys.one.    A     185.199.108.153
    osys.one.    A     185.199.109.153
    osys.one.    A     185.199.110.153
    osys.one.    A     185.199.111.153
    www.osys.one. CNAME oskamart.github.io

GitHub then issues the certificate for osys.one automatically.

This script resolves the domain and compares it against those expectations.

Usage: python3 deploy/check_domain.py
"""

from __future__ import annotations

import socket
import ssl
import sys
import urllib.error
import urllib.request

EXPECTED_IPS = {
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
}

DOMAIN = "osys.one"
SITE = "https://osys.one/"


def resolve(host: str) -> set[str]:
    out = set()
    try:
        for info in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM):
            out.add(info[4][0])
    except socket.gaierror:
        pass
    return out


def main() -> int:
    print("── osys.one ─────────────────────────────────────────────────")
    ips = resolve(DOMAIN)
    if not ips:
        print(f"  ✗ {DOMAIN} does not resolve")
        return 1

    print(f"  resolves to: {', '.join(sorted(ips))}")

    if ips & EXPECTED_IPS:
        print("  ✓ points at GitHub Pages")
    else:
        print("  ✗ not pointing at GitHub Pages yet")
        print("    expected one of:")
        for ip in sorted(EXPECTED_IPS):
            print(f"      {ip}")

    # TLS
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((DOMAIN, 443), timeout=12) as sock:
            with ctx.wrap_socket(sock, server_hostname=DOMAIN) as tls:
                cert = tls.getpeercert()
        subject = dict(x[0] for x in cert.get("subject", []))
        cn = subject.get("commonName", "")
        print(f"  ✓ certificate CN: {cn}")
        if cn not in (DOMAIN, f"*.{DOMAIN}"):
            print("    note: certificate is not yet issued for this domain")
    except Exception as exc:
        print(f"  ✗ TLS: {exc}")

    # HTTP
    try:
        req = urllib.request.Request(SITE, headers={"User-Agent": "portfolio-check"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read(4096).decode("utf-8", "replace")
            print(f"  ✓ HTTP {resp.status} ({len(body)} bytes read)")
            if "osys.one" in body:
                print("  ✓ the portfolio is being served")
    except urllib.error.HTTPError as exc:
        print(f"  ✗ HTTP {exc.code}")
    except Exception as exc:
        print(f"  ✗ HTTP: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
