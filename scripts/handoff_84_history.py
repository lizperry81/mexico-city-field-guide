"""Strict, read-only adapter for 84-batch noncanonical research replay proofs.

The 84th producer attached a verified *main reader blob* to its historical
snapshot and changed the readback-ledger schema. Keep all 83-batch checks,
explicitly verify the new reader binding and check every new ledger identity.
Nothing in this module authorizes editorial approval or publication.
"""
from __future__ import annotations

import copy
import re
from handoff_83_history import validate_frozen as validate_83_frozen

HEX40 = re.compile(r"^[a-f0-9]{40}$")


def check(ok, reason):
    if not ok:
        raise ValueError("84-batch Git research handoff: " + reason)


def validate_frozen(pointer, frozen, main_reader_blob):
    proof = frozen.get("integrity", {})
    expected = {
        "sqlite_integrity": "ok",
        "foreign_key_violations": 0,
        "canonical_tables_preserved": 88,
        "canonical_rows_unchanged": True,
        "github_binary_sha256_readback_verified": True,
        "main_reader_blob_verified": main_reader_blob,
    }
    check(isinstance(main_reader_blob, str)
          and HEX40.fullmatch(main_reader_blob) is not None,
          "missing current main reader identity")
    check(proof == expected,
          "current main reader or independent staging integrity differs")
    # Reuse all existing 83-batch canonical, count, provenance, source binding,
    # immutable-history and nonpublication assertions without weakening them.
    legacy = copy.deepcopy(frozen)
    legacy["integrity"].pop("main_reader_blob_verified")
    validate_83_frozen(pointer, legacy)


def validate_ledger(pointer, ledger, actual, main_reader_blob):
    staged = pointer["staged_counts"]
    canon = pointer["canonical"]
    readback = pointer["verified_binary_readback"]
    replay = pointer["replay_evidence"]
    canonical_counts = {
        "sources": canon["sources"],
        "claims": canon["claims"],
        "claim_sources": canon["claim_source_links"],
        "canonical_findings": canon["findings"],
        "canonical_source_inspections": canon["source_inspections"],
    }
    expected = {
        "schema_version": 2,
        "kind": "verified_full_reconciliation_github_binary_readback",
        "branch": "research-persistence",
        "research_commit_sha": pointer["research_commit_sha"],
        "replay_commit_sha": pointer["verified_replay_commit_sha"],
        "canonical_version": "V97",
        "canonical_sha256": pointer["canonical_hash"],
        "canonical_counts": canonical_counts,
        "canonical_tables_preserved": 88,
        "canonical_rows_unchanged": True,
        "github_batches_replayed": staged["github_batches_replayed"],
        "github_staged_findings": staged["github_distinct_substantive_finding_ids"],
        "github_source_candidates": staged["github_source_candidates"],
        "github_inspection_entries": staged["github_inspection_entries"],
        "index_only_unresolved": staged["github_index_only_refs_unresolved"],
        "unknown_source_refs": staged["unknown_source_refs"],
        "source_metadata_conflicts": staged["source_metadata_collisions"],
        "detached_inspection_identity_pending":
            staged["detached_source_identity_review_pending"],
        "source_identity_crosswalk_preserved": True,
        "versioned_sqlite_gz_path": pointer["versioned_research_sqlite_gz_path"],
        "replay_report_path": pointer["replay_report_path"],
        "compressed_checksum_path": replay["compressed_checksum_path"],
        "github_binary_blob_sha": actual["sqlite"],
        "github_replay_report_blob_sha": actual["report"],
        "readback_compressed_sha256_calculated": pointer["compressed_sha256"],
        "readback_compressed_sha256_committed": pointer["compressed_sha256"],
        "readback_compressed_digest_matches": True,
        "gzip_header_valid": True,
        "uncompressed_sha256_from_github_replay":
            pointer["versioned_research_sha256"],
        "sqlite_integrity": "ok",
        "foreign_key_violations": 0,
        "current_main_reader_blob_verified": main_reader_blob,
        "current_main_was_edited": False,
        "canonical_promoted": False,
        "editorial_approval": False,
        "ready_for_editorial_review": False,
    }
    for field, value in expected.items():
        check(ledger.get(field) == value, "independent ledger drift: " + field)

    check(ledger.get("source_batch_path") in
          pointer.get("research_batch_artifact_paths", []),
          "ledger source batch not in manifest")
    check(ledger.get("source_audit_path") in
          pointer.get("chapter_audit_artifact_paths", []),
          "ledger source audit not in manifest")
    check(ledger.get("source_coverage_path") in
          pointer.get("coverage_artifact_paths", []),
          "ledger coverage not in manifest")
    check(ledger.get("preflight_path") in
          pointer.get("reconciliation_artifact_paths", []),
          "ledger preflight not in manifest")
    check(actual["sqlite"] == readback.get("git_blob_sha")
          == replay.get("readback_binary_git_blob_sha")
          and actual["report"] == readback.get("report_blob_sha")
          == replay.get("readback_report_git_blob_sha")
          and readback.get("compressed_sha256") ==
          pointer["compressed_sha256"]
          and readback.get("uncompressed_sqlite_sha256") ==
          pointer["versioned_research_sha256"]
          and readback.get("verified_report_path") ==
          pointer["replay_report_path"]
          and readback.get("sqlite_integrity") == "ok"
          and readback.get("foreign_key_violations") == 0
          and readback.get("canonical_rows_unchanged") is True
          and readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is True,
          "actual Git blob identities or compressed byte digests differ")
