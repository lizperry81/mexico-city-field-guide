"""Regressions for the 84-batch verified readback extension."""
from __future__ import annotations
from unittest.mock import patch
from handoff_84_history import validate_frozen, validate_ledger

READER = "b" * 40
INTEGRITY = {
    "sqlite_integrity": "ok",
    "foreign_key_violations": 0,
    "canonical_tables_preserved": 88,
    "canonical_rows_unchanged": True,
    "github_binary_sha256_readback_verified": True,
    "main_reader_blob_verified": READER,
}
with patch("handoff_84_history.validate_83_frozen") as older_guard:
    validate_frozen({}, {"integrity": INTEGRITY.copy()}, READER)
    older_guard.assert_called_once()
    assert "main_reader_blob_verified" not in older_guard.call_args.args[1]["integrity"]
    for changed in (
        dict(INTEGRITY, main_reader_blob_verified="c" * 40),
        dict(INTEGRITY, canonical_rows_unchanged=False),
        {k: v for k, v in INTEGRITY.items() if k != "main_reader_blob_verified"},
    ):
        try:
            validate_frozen({}, {"integrity": changed}, READER)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed 84-batch staging or reader proof was accepted")
print("PASS: 84-batch extra reader identity and staging proof fail closed")
