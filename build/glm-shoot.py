#!/usr/bin/env python3
"""glm-shoot — GLM agent's capture tool (does not touch the shared shoot.py).

Like build/shoot.py, but with a configurable --virtual-time-budget (the shared
3500 ms budget can expire before the manifest fetch resolves when several
agents are sharing the CPU) and an optional scroll-to selector; output names
are prefixed "glm-" so other agents' files are never overwritten.

Usage:
  python3 build/glm-shoot.py                          # hero, viewport
  python3 build/glm-shoot.py --selector "#origobackup" --name origo
  python3 build/glm-shoot.py --name full --height 10500
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


def capture(doc_html: str, url: str, shot: Path, width: int, height: int,
            budget: int) -> bool:
    tmp = tempfile.mkdtemp(prefix="glm-shoot-")
    profile = os.path.join(tmp, "profile")
    cmd = [
        CHROME,
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--virtual-time-budget={budget}",
        f"--user-data-dir={profile}",
        f"--window-size={width},{height}",
        f"--screenshot={os.path.abspath(str(shot))}",
        url,
    ]
    ok = False
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print("timed out")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        ok = shot.exists()
    if ok:
        print(f"wrote {shot} ({shot.stat().st_size:,} bytes)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8742/")
    ap.add_argument("--selector", default="", help="scroll to this element first")
    ap.add_argument("--name", default="hero", help="output name (gets glm- prefix)")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1100)
    ap.add_argument("--budget", type=int, default=9000)
    ap.add_argument("--offset", type=int, default=0)
    args = ap.parse_args()

    out = ROOT / "shots"
    out.mkdir(exist_ok=True)
    shot = out / f"glm-{args.name}.png"

    doc = (ROOT / "index.html").read_text(encoding="utf-8")

    if args.selector:
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
        probe = ROOT / f"__glm_shot_{args.name}.html"
        probe.write_text(doc.replace("</body>", inject, 1), encoding="utf-8")
        target_url = args.url.rsplit("/", 1)[0] + "/" + probe.name
    else:
        probe = None
        target_url = args.url

    ok = capture(doc, target_url, shot, args.width, args.height, args.budget)
    if probe:
        probe.unlink(missing_ok=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
