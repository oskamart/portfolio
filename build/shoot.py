# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env python3
"""Render the portfolio in headless Chromium and write screenshots to shots/.

Usage: python3 build/shoot.py [--url http://127.0.0.1:8080/] [--width 1440] [--height 900]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--out", default="shots")
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()

    if not os.path.exists(CHROME):
        print(f"chromium not found at {CHROME}")
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="shots-")
    profile = os.path.join(tmp, "profile")
    cmd = [
        CHROME,
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=3500",
        f"--user-data-dir={profile}",
        f"--window-size={args.width},{args.height}",
        f"--screenshot={os.path.abspath(str(out / f'viewport{args.suffix}.png'))}",
    ]
    cmd.append(args.url)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print("chromium timed out")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    shot = out / f"viewport{args.suffix}.png"
    if shot.exists():
        print(f"wrote {shot} ({shot.stat().st_size:,} bytes)")
    else:
        print("screenshot failed")
        print(res.stderr[-2000:])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
