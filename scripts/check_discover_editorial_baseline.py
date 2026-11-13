#!/usr/bin/env python3
"""Fail closed when approved Discover content is modified without explicit editorial approval.

Usage: python scripts/check_discover_editorial_baseline.py [--base-ref REF]
Checks the protected baseline policy and any archived Discover chapters in
editorial/approved/. Newly approved chapter archives must be committed with
an adjacent .sha256 file containing the SHA-256 of the chapter's UTF-8 bytes.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY = "editorial/DISCOVER_APPROVED_BASELINE_2026-11-13.md"
ARCHIVES = ROOT / "editorial" / "approved"

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, text=True,
                          capture_output=True, check=True).stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", help="Git ref to compare against")
    args = parser.parse_args()
    failures = []
    policy = ROOT / POLICY
    if not policy.is_file():
        failures.append(f"Missing protected policy: {POLICY}")
    if args.base_ref:
        changed = git("diff", "--name-only", args.base_ref, "--").splitlines()
        # The JSON manuscript carries publication status and can publish prose.
        # Treat it as protected editorial content, even before archives exist.
        protected = [p for p in changed
                     if p == POLICY or p.startswith("editorial/approved/")
                     or (p.startswith("editorial/discover/") and p.endswith(".json"))]
        if protected:
            failures.append("Approved Discover files changed; explicit editorial approval and review required: " + ", ".join(protected))
    if ARCHIVES.exists():
        for chapter in sorted(ARCHIVES.glob("*.md")):
            checksum = chapter.with_suffix(chapter.suffix + ".sha256")
            if not checksum.is_file():
                failures.append(f"Missing checksum for {chapter.relative_to(ROOT)}")
                continue
            expected = checksum.read_text(encoding="utf-8").split()[0].lower()
            actual = hashlib.sha256(chapter.read_bytes()).hexdigest()
            if expected != actual:
                failures.append(f"Checksum mismatch for {chapter.relative_to(ROOT)}")
    if ARCHIVES.exists():
        for checksum in sorted(ARCHIVES.glob("*.md.sha256")):
            chapter = checksum.with_suffix("")
            if not chapter.is_file():
                failures.append(f"Orphaned approval checksum: {checksum.relative_to(ROOT)}")
    if failures:
        for item in failures:
            print("FAIL:", item, file=sys.stderr)
        return 1
    print("PASS: Discover editorial baseline policy present; archive checksums valid.")
    if not ARCHIVES.exists() or not list(ARCHIVES.glob("*.md")):
        print("NOTICE: No verbatim approved chapter archive exists yet; archive text before claiming it is protected.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
