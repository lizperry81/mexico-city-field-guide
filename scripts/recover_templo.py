#!/usr/bin/env python3
"""Restore the ORIGINAL V81 Templo Mayor research from the lossless GitHub archive.

The recovery file is a zlib-compressed JSON dictionary of UTF-8 ORIGINAL file
bytes (strings). This is deliberate: GitHub's connector accepts text uploads,
not arbitrary binary ZIP files. SHA-256 checks ensure zero content loss.
Do not use the smaller earlier redesign ZIP as the historical source.
"""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib

SOURCE = Path("research/recovered/templo_v81_original_json.zlib.b64")
EXPECTED = {
    "templo_walk_v63.json": ("5f0aa7f8a57511e3277f90aba7c6a6eb4fca12bf0b6ed5981a35fca359c2b63a", "chapters", 8),
    "templo_mayor_pilot.json": ("778ac52157b1d76558134937f739f9b97e1cab70c3f128892462b6df4c8c6596", "claims", 21),
    "templo_verified_discoveries_v68.json": ("bdd54da92729a087de3016e2aa8255f5e5cb3126f47e87c9e80855bd5cbaf98a", None, 12),
}

def recover(target=Path("site")):
    if not SOURCE.exists():
        raise FileNotFoundError(f"Required recovered research archive missing: {SOURCE}")
    payload = SOURCE.read_text(encoding="ascii").strip()
    files = json.loads(zlib.decompress(base64.b64decode(payload, validate=True)))
    if set(files) != set(EXPECTED):
        raise AssertionError(f"Unexpected source files in recovery package: {sorted(files)}")
    dest = target / "data" / "research"
    dest.mkdir(parents=True, exist_ok=True)
    for name, (digest, key, count) in EXPECTED.items():
        original = files[name].encode("utf-8")
        actual = hashlib.sha256(original).hexdigest()
        assert actual == digest, f"Preservation checksum mismatch for {name}: {actual}"
        parsed = json.loads(original)
        n = len(parsed[key]) if key else len(parsed)
        assert n == count, f"Unexpected {name} count: {n}"
        path = dest / name
        if path.exists() and path.read_bytes() != original:
            raise RuntimeError(f"Existing {path} differs from preserved V81; stop for reconciliation rather than overwrite")
        path.write_bytes(original)
        print(f"Restored and SHA-verified: {name}, {n} records, {len(original)} bytes", flush=True)
    return dest

if __name__ == "__main__":
    recover(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("site"))
