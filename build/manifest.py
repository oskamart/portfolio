# osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
#!/usr/bin/env python3
"""Measure the portfolio's own numbers from the machine and emit assets/manifest.json.

Every figure the site states is computed here from the real trees, so the page
can be regenerated and re-checked at any time. Nothing is hand-typed.

Usage:  python3 build/manifest.py [--root /home/o] [--out assets/manifest.json]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Extensions that count as authored source. Vendored trees and build output
# are excluded so the numbers describe work, not bytes copied in.
CODE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".css", ".html",
    ".sv", ".svh", ".v", ".vh", ".pyi", ".sh",
}
DOC_EXT = {".md"}

# Directories never counted.
SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "__pycache__",
    ".venv", "venv", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".eggs", "site-packages", ".next", ".cache", "coverage",
}


def count_tree(root: Path) -> dict:
    """Return {files, code_loc, doc_loc, bytes} for an authored tree."""
    files = code_loc = doc_loc = total_bytes = 0
    if not root.exists():
        return {"files": 0, "code_loc": 0, "doc_loc": 0, "bytes": 0}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in CODE_EXT and ext not in DOC_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(path)
                with open(path, "rb") as fh:
                    lines = sum(1 for _ in fh)
            except OSError:
                continue
            files += 1
            total_bytes += size
            if ext in CODE_EXT:
                code_loc += lines
            else:
                doc_loc += lines
    return {"files": files, "code_loc": code_loc, "doc_loc": doc_loc, "bytes": total_bytes}


def git_commits(repo: Path) -> int:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return int(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def count_tree_text(path: Path) -> int:
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


# The shared temporal-AA core: one implementation, byte-identical across the
# four designs that use it. Measured from the files themselves.
TAA_CORE_FILES = ["taa-glsl.js", "taa-runtime.js", "taa-three.js"]
TAA_DESIGN_DIRS = [
    "Desktop/ardverium-reworked/4-chip/js",
    "Desktop/ardverium-reworked/5-graph/js",
    "Desktop/ardverium-reworked/6-prism/dist/js",
    "Desktop/ardverium-reworked/7-silicon/dist/js",
]


def measure_taa_core(base: Path) -> dict:
    """Line count and md5 of the shared TAA core, plus whether the copies match.

    The claim on the page is that one implementation is shared by four designs
    without modification, so this verifies it rather than assuming it: every
    copy of every core file must hash identically.
    """
    import hashlib

    core_loc = 0
    per_file: dict[str, dict] = {}

    for name in TAA_CORE_FILES:
        digests = {}
        loc = 0
        for rel_dir in TAA_DESIGN_DIRS:
            path = base / rel_dir / name
            if not path.exists():
                continue
            digests[rel_dir] = hashlib.md5(path.read_bytes()).hexdigest()
            loc = count_tree_text(path)
        unique = set(digests.values())
        per_file[name] = {
            "copies": len(digests),
            "identical": len(unique) == 1 and len(digests) > 1,
            "md5": next(iter(unique)) if len(unique) == 1 else None,
            "loc": loc,
        }
        core_loc += loc

    return {
        "loc": core_loc,
        "designs": len(TAA_DESIGN_DIRS),
        "identical_across_designs": all(f["identical"] for f in per_file.values()),
        "files": per_file,
    }


# --- The systems the portfolio documents -----------------------------------
# Note: UVMStack (the verification engine, github.com/trishinraj/uvm_engine)
# is Trishna Raj's work, not the portfolio owner's, so it is NOT measured here.
# It appears on the page only as the external thing Haelo and Oden Flow attach
# to. No number on the page may claim its LOC as authored source.
SYSTEMS = {
    "haelo": {
        "label": "Haelo",
        "root": "Desktop/haelo-proxy",
        "repo": None,
    },
    "odenflow": {
        "label": "Oden Flow",
        "root": "oden-uvm-staging/oden_flow",
        "repo": "oden-uvm-staging/oden_flow",
    },
    "ardverium": {
        "label": "Ardverium",
        "root": "Desktop/ardverium-reworked",
        "repo": None,
    },
    "lorapilot": {
        "label": "LoRA pilot",
        "root": "lora-pilot/lorapilot",
        "repo": "lora-pilot",
    },
    "lorapilot_tests": {
        "label": "LoRA pilot tests",
        "root": "lora-pilot/tests",
        "repo": None,
    },
    "origobackup": {
        "label": "Origo Backup",
        "root": "backup-app",
        "repo": None,
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~"))
    ap.add_argument("--out", default="assets/manifest.json")
    args = ap.parse_args()
    base = Path(args.root).resolve()

    systems = {}
    for key, spec in SYSTEMS.items():
        root = base / spec["root"]
        stats = count_tree(root)
        stats["commits"] = git_commits(base / spec["repo"]) if spec["repo"] else 0
        systems[key] = stats

    totals = {
        "code_loc": sum(s["code_loc"] for s in systems.values()),
        "doc_loc": sum(s["doc_loc"] for s in systems.values()),
        "files": sum(s["files"] for s in systems.values()),
        "commits": sum(s["commits"] for s in systems.values()),
    }

    taa = measure_taa_core(base)

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "build/manifest.py",
        "systems": systems,
        "totals": totals,
        "taa_core": taa,
    }

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(__file__).resolve().parent.parent / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    for key, stats in systems.items():
        print(f"  {key:18s} {stats['code_loc']:>8,} loc  {stats['files']:>5} files  {stats['commits']:>4} commits")
    print(f"  {'TOTAL':18s} {totals['code_loc']:>8,} loc  {totals['files']:>5} files  {totals['commits']:>4} commits")
    print(f"  {'taa core':18s} {taa['loc']:>8,} loc  identical={taa['identical_across_designs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
