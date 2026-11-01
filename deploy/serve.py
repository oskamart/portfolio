# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env python3
"""Production static server for the portfolio.

Deliberately small: a threaded HTTP server with correct MIME types, gzip
pre-compression, caching headers, and no directory listing. Binds to loopback
by default; pass --host 0.0.0.0 to expose on the LAN.

Used by the systemd unit (deploy/portfolio.service).

Usage: python3 deploy/serve.py [--port 8090] [--host 127.0.0.1] [--root DIR]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml",
    ".ico": "image/x-icon",
}

# Long cache for immutable assets; short for HTML and the manifest so an edit
# shows up on the next reload.
LONG = "public, max-age=31536000, immutable"
SHORT = "public, max-age=300, must-revalidate"

COMPRESSIBLE = {".html", ".css", ".js", ".json", ".svg", ".txt", ".xml"}


class Handler(BaseHTTPRequestHandler):
    server_version = "portfolio/1.0"
    protocol_version = "HTTP/1.1"

    root: Path = ROOT

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()

    # -- helpers -----------------------------------------------------------
    def _resolve(self) -> Path | None:
        path = unquote(urlparse(self.path).path)
        if path.endswith("/"):
            path += "index.html"
        target = (self.root / path.lstrip("/")).resolve()
        try:
            target.relative_to(self.root.resolve())
        except ValueError:
            return None  # path traversal
        if target.is_dir():
            target = target / "index.html"
        return target if target.is_file() else None

    def _send(self, code: int, body: bytes, ctype: str, cache: str, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data:; "
                         "style-src 'self'; script-src 'self'; font-src 'self'; "
                         "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, code: int, message: str):
        page = (
            "<!DOCTYPE html><html lang=en><head><meta charset=utf-8>"
            f"<title>{code}</title><style>body{{background:#07090d;color:#e9edf3;"
            "font:16px/1.6 system-ui,sans-serif;display:grid;place-items:center;"
            "height:100vh;margin:0}}p{{font-family:ui-monospace,monospace}}"
            "a{color:#72ffd9}</style></head><body><p>{code} — {message} · "
            '<a href="/">osys.one</a></p></body></html>'
        ).encode()
        self._send(code, page, "text/html; charset=utf-8", "no-store")

    # -- verbs -------------------------------------------------------------
    def do_GET(self):
        self._serve(with_body=True)

    def do_HEAD(self):
        self._serve(with_body=False)

    def _serve(self, with_body: bool):
        target = self._resolve()
        if target is None:
            self._error(404, "Not found")
            return

        ext = target.suffix.lower()
        ctype = MIME.get(ext, "application/octet-stream")
        cache = LONG if ext in (".woff2", ".png", ".jpg", ".webp", ".svg", ".ico") else SHORT

        raw = target.read_bytes()

        # Pre-compress once per file; the ETag is over the uncompressed bytes
        # so it stays stable across encodings.
        accepts_gzip = "gzip" in (self.headers.get("Accept-Encoding") or "")
        if accepts_gzip and ext in COMPRESSIBLE and len(raw) > 512:
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as gz:
                gz.write(raw)
            body = buf.getvalue()
            etag = '"%s-gz"' % hashlib.md5(raw).hexdigest()[:16]
            extra = {"Content-Encoding": "gzip", "Vary": "Accept-Encoding", "ETag": etag}
        else:
            body = raw
            etag = '"%s"' % hashlib.md5(raw).hexdigest()[:16]
            extra = {"ETag": etag}

        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache)
            self.end_headers()
            return

        self._send(200, body, ctype, cache, extra)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()

    Handler.root = Path(args.root).resolve()
    httpd = Server((args.host, args.port), Handler)
    print(f"osys.one portfolio on http://{args.host}:{httpd.server_address[1]}/ "
          f"(root {Handler.root})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
