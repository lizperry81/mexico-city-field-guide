"""Fail-closed research-only validation for verified 83-batch append-only handoffs.

The consumer may create PRIVATE audit-review assignments from these objects.
Neither the string evidence status nor Git readback approves any finding for publication.
"""
from __future__ import annotations

import re
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def check(condition, detail):
    if not condition:
        raise ValueError("83-batch Git research handoff: " + detail)


def validate_frozen(pointer, frozen):
    check(pointer.get("schema_version") == frozen.get("schema_version") == 4,
          "unexpected schema")
    check(pointer.get("kind") == "research_to_app_handoff"
          and frozen.get("kind") == "verified_noncanonical_research_to_app_handoff_history"
          and frozen.get("branch") == "research-persistence",
          "incorrect source or history kind")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                "versioned_research_sqlite_gz_path", "versioned_research_sha256",
                "compressed_sha256", "replay_report_path", "previous_manifest_blob_sha"):
        check(pointer.get(key) == frozen.get(key), "immutable " + key + " drift")
    check(pointer.get("canonical_version") == "V97"
          and pointer.get("canonical_status") == "unchanged_provisional_V97_not_promoted"
          and frozen.get("canonical_status") == "unchanged_not_promoted",
          "canonical promotion")
    canon = pointer.get("canonical", {})
    expected_canon = {
        "sources": canon.get("sources"), "claims": canon.get("claims"),
        "claim_sources": canon.get("claim_source_links"),
        "canonical_findings": canon.get("findings"),
        "canonical_source_inspections": canon.get("source_inspections"),
    }
    check(all(type(x) is int and x >= 0 for x in expected_canon.values())
          and frozen.get("canonical_counts") == expected_canon
          and frozen.get("canonical_tables_preserved") == 88
          and frozen.get("canonical_rows_unchanged") is True,
          "canonical rows or counts differ")
    staged = pointer.get("staged_counts", {})
    check(isinstance(staged, dict) and isinstance(frozen.get("staged_counts"), dict),
          "missing staged counts")
    for key in ("github_batches_replayed", "github_distinct_substantive_finding_ids",
                "github_inspection_entries", "github_source_candidates",
                "source_metadata_collisions", "unknown_source_refs",
                "detached_source_identity_review_pending"):
        check(type(staged.get(key)) is int and staged[key] >= 0
              and frozen["staged_counts"].get(key) == staged[key],
              "changed staged " + key)
    check(frozen["staged_counts"].get("index_only_refs_unresolved")
          == staged.get("github_index_only_refs_unresolved"),
          "changed unresolved index-only references")
    for doc in (pointer, frozen):
        check(doc.get("ready_for_editorial_review") is False
              and doc.get("ready_for_publication") is False
              and doc.get("canonical_promoted") is False,
              "unapproved evidence marked ready")
    check(pointer.get("evidence_status") ==
          "staged_source_located_not_independently_corroborated_or_publication_approved"
          and frozen.get("evidence_status") ==
          "noncanonical_source_located_not_independently_corroborated_or_publication_approved",
          "editorial evidence status changed")
    check(frozen.get("integrity") == {
        "sqlite_integrity": "ok", "foreign_key_violations": 0,
        "canonical_tables_preserved": 88, "canonical_rows_unchanged": True,
        "github_binary_sha256_readback_verified": True,
    }, "independent staging integrity differs")
    snap = frozen.get("verified_snapshot_commit_sha")
    check(isinstance(snap, str) and bool(HEX40.fullmatch(snap))
          and pointer.get("verified_replay_commit_sha") == snap
          and pointer.get("verified_binary_readback", {}).get("commit_sha") == snap
          and pointer.get("replay_evidence", {}).get("snapshot_commit_sha") == snap,
          "replay commit pin differs")
    check(frozen.get("reconciliation_ledger_path") ==
          pointer.get("replay_evidence", {}).get("verification_ledger"),
          "Git verification ledger not pinned")
    check(frozen.get("previous_immutable_handoff_path") ==
          pointer.get("previous_immutable_handoff_path"),
          "previous approved history pointer differs")
    check(pointer.get("handoff_history_append_only") is True
          and pointer.get("canonical_promoted") is False,
          "append-only or canonical protections removed")
    for field in ("chapter_audit_artifact_paths", "coverage_artifact_paths",
                  "research_batch_artifact_paths", "reconciliation_artifact_paths"):
        subset = frozen.get(field)
        check(isinstance(subset, list) and bool(subset)
              and set(subset).issubset(set(pointer.get(field, []))),
              "unbound research paths in " + field)
    check(isinstance(pointer.get("consumer_instruction"), str)
          and "Do not publish" in pointer["consumer_instruction"]
          and "auto-merge" in pointer["consumer_instruction"],
          "publication boundary missing")
    return snap


def validate_ledger(pointer, ledger, actual):
    staged = pointer["staged_counts"]
    canon = pointer["canonical"]
    canonical_counts = {
        "sources": canon["sources"], "claims": canon["claims"],
        "claim_sources": canon["claim_source_links"],
        "canonical_findings": canon["findings"],
        "canonical_source_inspections": canon["source_inspections"],
    }
    readback = pointer["verified_binary_readback"]
    replay = pointer["replay_evidence"]
    fields = {
        "schema_version": 2,
        "kind": "independent_research_batch_github_readback_verification",
        "branch": "research-persistence",
        "source_research_commit_sha": pointer["research_commit_sha"],
        "snapshot_commit_sha": pointer["verified_replay_commit_sha"],
        "canonical_version": pointer["canonical_version"],
        "canonical_sha256": pointer["canonical_hash"],
        "canonical_counts": canonical_counts,
        "canonical_tables_preserved": 88,
        "canonical_rows_unchanged": True,
        "staged_findings": staged["github_distinct_substantive_finding_ids"],
        "staged_batches": staged["github_batches_replayed"],
        "source_candidates": staged["github_source_candidates"],
        "source_inspection_payloads": staged["github_inspection_entries"],
        "detached_pending": staged["detached_source_identity_review_pending"],
        "unresolved_index_only_count": staged["github_index_only_refs_unresolved"],
        "replay_report_path": pointer["replay_report_path"],
        "replay_report_blob_sha": actual["report"],
        "gzip_path": pointer["versioned_research_sqlite_gz_path"],
        "gzip_git_blob_sha": actual["sqlite"],
        "checksum_path": replay["compressed_checksum_path"],
        "checksum_blob_sha": actual["checksum"],
        "compressed_sha256_recomputed_on_binary_from_github": pointer["compressed_sha256"],
        "compressed_sha256_matches_committed_text": True,
        "uncompressed_sha256_from_workflow_report": pointer["versioned_research_sha256"],
        "sqlite_integrity": "ok",
        "foreign_key_violations": 0,
        "github_readback_examination": True,
        "findings_added": staged["new_historical_finding_candidates_this_run"],
        "sources_added": staged["new_source_candidates_all_types_this_run"],
        "inspections_added": staged["new_source_inspection_metadata_this_run"],
        "prior_manifest_blob_sha": pointer["previous_manifest_blob_sha"],
        "publication_approved": False,
        "ready_for_editorial_review": False,
    }
    for field, expected in fields.items():
        check(ledger.get(field) == expected, "ledger evidence drift: " + field)
    check(isinstance(ledger.get("unknown_source_ids"), list)
          and len(ledger["unknown_source_ids"]) == staged["unknown_source_refs"],
          "unregistered source tally differs")
    check(isinstance(ledger.get("metadata_conflicts"), list)
          and len(ledger["metadata_conflicts"]) == staged["source_metadata_collisions"],
          "source identity collision tally differs")
    check(actual["sqlite"] == readback.get("git_blob_sha")
          and actual["report"] == readback.get("report_blob_sha")
          and actual["sqlite"] == replay.get("readback_binary_git_blob_sha")
          and actual["report"] == replay.get("readback_report_git_blob_sha")
          and readback.get("compressed_sha256") == pointer["compressed_sha256"]
          and readback.get("uncompressed_sqlite_sha256") == pointer["versioned_research_sha256"]
          and readback.get("sqlite_integrity") == "ok"
          and readback.get("foreign_key_violations") == 0
          and readback.get("canonical_rows_unchanged") is True
          and readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is True,
          "committed Git proof does not match pointer")
