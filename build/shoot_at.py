# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env python3
"""Capture a page region by scrolling, using a temporary instrumented copy.

The headless shell screenshots the viewport at scroll position 0, so we make a
throwaway copy of index.html with an inline script that scrolls to the wanted
element, shoot it, then remove the copy. The original page is never modified.

Usage: python3 build/shoot_at.py --selector "#measurements" --name measurements
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
)
ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/")
    ap.add_argument("--selector", default="#measurements")
    ap.add_argument("--name", default="section")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1100)
    ap.add_argument("--out", default="shots")
    ap.add_argument("--offset", type=int, default=0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    # Scroll on the next frame after layout, then hold still: the hero canvas
    # keeps requesting frames, which would otherwise re-trigger the scroll.
    inject = f"""
<style>html {{ scroll-behavior: auto !important; }}</style>
<script>
(function () {{
  var done = false;
  function go() {{
    if (done) return;
    var el = document.querySelector({args.selector!r});
    if (!el) return;
    var top = el.getBoundingClientRect().top + window.scrollY + {args.offset};
    window.scrollTo(0, top);
    done = true;
  }}
  window.addEventListener("load", function () {{
    requestAnimationFrame(function () {{ requestAnimationFrame(go); }});
  }});
}})();
</script>
</body>"""
    probe = ROOT / f"__shot_{args.name}.html"
    probe.write_text(doc.replace("</body>", inject, 1), encoding="utf-8")

    tmp = tempfile.mkdtemp(prefix="shotat-")
    profile = os.path.join(tmp, "profile")
    shot = out / f"{args.name}.png"

    cmd = [
        CHROME,
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=4000",
        f"--user-data-dir={profile}",
        f"--window-size={args.width},{args.height}",
        f"--screenshot={os.path.abspath(str(shot))}",
        args.url.rsplit("/", 1)[0] + "/" + probe.name,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        print("timed out")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        probe.unlink(missing_ok=True)

    if shot.exists():
        print(f"wrote {shot} ({shot.stat().st_size:,} bytes)")
        return 0
    print("screenshot failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
