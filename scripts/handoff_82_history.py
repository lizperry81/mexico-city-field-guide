"""Validate compact append-only research-only handoffs with independent Git identities.

The producer's unapproved evidence status is a string. It must never be
interpreted as editorial approval, and these helpers authorize PRIVATE queues
only. Every assertion is checked against the pinned immutable history and
committed Git readback artifacts.
"""
from __future__ import annotations
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")


def check(ok, reason):
    if not ok:
        raise ValueError("82-style research handoff: " + reason)


def validate_frozen(pointer, frozen):
    """Strictly compare the rolling pointer to its immutable staged history."""
    check(pointer.get("schema_version") == frozen.get("schema_version") == 4,
          "unexpected schema")
    check(frozen.get("kind") == "append_only_research_to_app_handoff_history",
          "unexpected immutable record")
    check(pointer.get("kind") == "research_to_app_handoff"
          and frozen.get("branch") == "research-persistence", "wrong branch or type")
    for key in ("research_commit_sha", "canonical_hash", "canonical_version",
                "canonical_status", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256",
                "replay_report_path", "previous_manifest_blob_sha"):
        check(pointer.get(key) == frozen.get(key), "changed immutable " + key)
    check(pointer.get("canonical_status") == "unchanged_provisional_V97_not_promoted",
          "canonical promoted")
    canon = pointer.get("canonical", {})
    expected = {
        "sources": canon.get("sources"), "claims": canon.get("claims"),
        "claim_sources": canon.get("claim_source_links"),
        "canonical_findings": canon.get("findings"),
        "canonical_source_inspections": canon.get("source_inspections")}
    check(all(type(x) is int for x in expected.values()), "invalid canonical counts")
    check(frozen.get("canonical_counts") == expected, "canonical records altered")
    staged = pointer.get("staged_counts", {})
    check(isinstance(staged, dict) and frozen.get("staged_counts") == staged,
          "research counts or source conflicts changed")
    check(frozen.get("evidence_status") ==
          "staged_source_located_not_independently_editorially_corroborated_or_approved",
          "immutable evidence approval altered")
    check(pointer.get("evidence_status") ==
          "staged_source_located_not_independently_corroborated_or_publication_approved",
          "rolling evidence approval altered")
    for doc in (pointer, frozen):
        for key in ("ready_for_editorial_review", "ready_for_publication",
                    "canonical_promoted"):
            check(doc.get(key) is False, "research declared approved: " + key)
    check(frozen.get("main_modified") is False and frozen.get("auto_merge") is False
          and pointer.get("handoff_history_append_only") is True,
          "main or publication boundary violated")
    snap = frozen.get("snapshot_commit_sha")
    check(isinstance(snap, str) and bool(HEX40.fullmatch(snap)),
          "missing exact snapshot commit")
    check(pointer.get("verified_replay_commit_sha") == snap
          and pointer.get("replay_evidence", {}).get("snapshot_commit_sha") == snap
          and pointer.get("verified_binary_readback", {}).get("commit_sha") == snap,
          "snapshot commit identities disagree")
    for key in ("chapter_audit_artifact_paths", "coverage_artifact_paths",
                "research_batch_artifact_paths"):
        subset = frozen.get(key)
        check(isinstance(subset, list) and bool(subset)
              and set(subset).issubset(set(pointer.get(key, []))),
              "unbound research artifact group: " + key)
    replay = pointer.get("replay_evidence", {})
    readback = pointer.get("verified_binary_readback", {})
    check(frozen.get("verification_ledger_path") == replay.get("verification_ledger"),
          "verification ledger not bound")
    check(replay.get("readback_binary_git_blob_sha") == readback.get("git_blob_sha")
          and replay.get("readback_report_git_blob_sha") == readback.get("report_blob_sha"),
          "replay output Git identities disagree")
    check(readback.get("compressed_sha256") == pointer.get("compressed_sha256")
          and readback.get("uncompressed_sqlite_sha256") ==
          pointer.get("versioned_research_sha256"), "content digests disagree")
    check(readback.get("sqlite_integrity") == "ok"
          and readback.get("foreign_key_violations") == 0
          and readback.get("canonical_rows_unchanged") is True
          and readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is True,
          "readback not independently verified")
    instruction = pointer.get("consumer_instruction", "")
    check(isinstance(instruction, str) and
          "No automatic merge" in instruction and "never modify main or publish" in instruction,
          "publication restriction missing")
    return snap


def validate_ledger(pointer, ledger, actual):
    """Match every readback claim to independently addressed Git objects.

    actual contains the blob IDs read from the manifest-publishing commit.
    The caller separately checks the frozen snapshot commit ancestry and SHA.
    """
    staged = pointer["staged_counts"]
    canon = pointer["canonical"]
    readback = pointer["verified_binary_readback"]
    expected_canonical = {
        "sources": canon["sources"], "claims": canon["claims"],
        "claim_sources": canon["claim_source_links"],
        "canonical_findings": canon["findings"],
        "canonical_source_inspections": canon["source_inspections"]}
    for key, value in {
        "schema_version": 2,
        "kind": "independent_source_and_github_readback_verification",
        "branch": "research-persistence",
        "source_research_commit_sha": pointer["research_commit_sha"],
        "snapshot_commit_sha": pointer["verified_replay_commit_sha"],
        "canonical_sha256": pointer["canonical_hash"],
        "canonical_counts": expected_canonical,
        "canonical_tables_preserved": 88,
        "canonical_rows_unchanged": True,
        "staged_findings": staged["github_distinct_substantive_finding_ids"],
        "staged_batches": staged["github_batches_replayed"],
        "source_candidates": staged["github_source_candidates"],
        "source_inspection_payloads": staged["github_inspection_entries"],
        "detached_pending": staged["detached_source_identity_review_pending"],
        "replay_report_path": pointer["replay_report_path"],
        "replay_report_blob_sha": actual["report"],
        "gzip_path": pointer["versioned_research_sqlite_gz_path"],
        "gzip_git_blob_sha": actual["sqlite"],
        "checksum_blob_sha": actual["checksum"],
        "compressed_sha256_recomputed_on_binary_from_github": pointer["compressed_sha256"],
        "compressed_sha256_matches_committed_text": True,
        "uncompressed_sha256_from_workflow_report": pointer["versioned_research_sha256"],
        "sqlite_integrity": "ok", "foreign_key_violations": 0,
        "github_readback_examination": True,
        "findings_added": staged["new_historical_finding_candidates_this_run"],
        "sources_added": staged["new_source_candidates_all_types_this_run"],
        "inspections_added": staged["new_source_inspection_metadata_this_run"],
        "prior_manifest_blob_sha": pointer["previous_manifest_blob_sha"],
        "publication_approved": False, "ready_for_editorial_review": False,
    }.items():
        check(ledger.get(key) == value, "Git ledger mismatch: " + key)
    check(len(ledger.get("unknown_source_ids", [])) == staged["unknown_source_refs"]
          and len(ledger.get("metadata_conflicts", [])) == staged["source_metadata_collisions"],
          "unresolved source evidence changed")
    check(actual["sqlite"] == readback.get("git_blob_sha")
          and actual["report"] == readback.get("report_blob_sha"),
          "Git objects differ from declared readback")
