"""Validate the 89-batch workflow-readback handoff for PRIVATE editorial review.

This producer could not independently download its binary through the connector.
Accept the GitHub Actions checksum claim only in combination with immutable,
pinned Git objects and the existing consumer's own gzip/SHA-256 verification.
No function here can authorize publication or a canonical merge.
"""
from __future__ import annotations

import re

HEX = re.compile(r"^[0-9a-f]{40}$")
CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
CONTRACT = "89_batch_sqlite_integrity_and_workflow_git_readback_verified_noncanonical_unapproved"
COUNTS = {"batches": "github_batches_replayed",
          "findings": "github_distinct_substantive_finding_ids",
          "source_candidates": "github_source_candidates",
          "inspections": "github_inspection_entries"}


def require(ok, why):
    if not ok:
        raise ValueError("89-batch private research handoff: " + why)


def validate_frozen(m, f):
    require(m.get("schema_version") == f.get("schema_version") == 4 and
            m.get("kind") == "research_to_app_handoff" and
            f.get("kind") == "immutable_research_handoff_history_entry" and
            f.get("branch") == "research-persistence" and
            m.get("handoff_contract_status") == CONTRACT, "handoff type")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                "canonical_status", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256",
                "replay_report_path"):
        require(m.get(key) == f.get(key), "immutable identity " + key)
    require(m.get("verified_replay_commit_sha") == f.get("snapshot_commit_sha") ==
            m.get("replay_evidence", {}).get("snapshot_commit_sha") ==
            m.get("verified_binary_readback", {}).get("commit_sha"), "replay commit")
    require(all(HEX.fullmatch(str(v)) for v in
                (m.get("research_commit_sha"), m.get("verified_replay_commit_sha"))),
            "commit syntax")
    require(m.get("canonical") == CANONICAL and
            m.get("canonical_version") == "V97" and
            m.get("canonical_status") == "unchanged_provisional_V97_not_promoted", "V97 preservation")
    require(m.get("immutable_handoff_path") == m.get("latest_handoff_history_path")
            and m.get("immutable_handoff_path") in m.get("handoff_history_paths", [])
            and f.get("reconciliation_ledger_path") ==
            m.get("latest_reconciliation_ledger_path") ==
            m.get("replay_evidence", {}).get("verification_ledger")
            and f.get("reconciliation_ledger_path") in m.get("reconciliation_artifact_paths", []),
            "immutable handoff and ledger paths")
    require(f.get("source_batch_path") in m.get("research_batch_artifact_paths", [])
            and f.get("chapter_audit_artifact_paths") ==
            [m.get("latest_chapter_audit_artifact_path")]
            and f.get("coverage_artifact_paths") ==
            [m.get("latest_coverage_artifact_path")], "source and audit paths")
    for key, rolling in COUNTS.items():
        require(type(f.get("staged_counts", {}).get(key)) is int
                and f["staged_counts"][key] == m.get("staged_counts", {}).get(rolling),
                "count " + key)
    s = m["staged_counts"]
    require(s.get("github_index_only_refs_unresolved") == 1
            and s.get("unknown_source_refs") == 1
            and s.get("source_metadata_collisions") == 2
            and s.get("detached_source_identity_review_pending") == 37,
            "unresolved source identities")
    require(f.get("evidence_status") == m.get("evidence_status") ==
            "edited_primary_text_transcription_plus_institutional_web_summaries_provisional",
            "research status")
    require(all(obj.get("ready_for_editorial_review") is False and
                obj.get("publication_approved") is False and
                isinstance(obj.get("blockers"), list) and obj["blockers"]
                for obj in (m, f)), "not editorially approved")
    require(m.get("ready_for_publication") is False and
            m.get("canonical_promoted") is False and
            m.get("auto_merge_permitted") is False and
            m.get("reconciliation_verified") is True, "no publication or merge")
    require(f.get("github_readback", {}).get("independent_binary_sha256_recalculation_not_claimed") is True
            and f.get("github_readback", {}).get("github_external_binary_download_unavailable") is True
            and f.get("github_readback", {}).get("workflow_conclusion") == "success_both",
            "honest binary verification provenance")


def validate_ledger(m, f, l, actual):
    require(l.get("schema_version") == 2 and
            l.get("kind") == "research_reconciliation_and_github_readback_ledger"
            and l.get("branch") == "research-persistence"
            and l.get("research_commit_sha") == m.get("research_commit_sha")
            and l.get("snapshot_commit_sha") == m.get("verified_replay_commit_sha")
            and l.get("source_batch_path") == f.get("source_batch_path")
            and l.get("coverage_path") == f.get("coverage_artifact_paths", [None])[0]
            and l.get("chapter_audit_path") == f.get("chapter_audit_artifact_paths", [None])[0]
            and l.get("report_path") == m.get("replay_report_path")
            and l.get("compressed_database_path") == m.get("versioned_research_sqlite_gz_path")
            and l.get("checksum_file_path") == m.get("replay_evidence", {}).get("compressed_checksum_path"),
            "ledger identity and paths")
    for key in ("batch", "coverage", "audit", "report", "sqlite", "checksum"):
        require(HEX.fullmatch(str(actual.get(key, ""))), "missing Git blob " + key)
    require(l.get("github_blob_sha", {}).get("compressed_database") ==
            actual["sqlite"] == m.get("verified_binary_readback", {}).get("git_blob_sha") ==
            m.get("replay_evidence", {}).get("readback_binary_git_blob_sha")
            and l.get("github_blob_sha", {}).get("report") ==
            actual["report"] == m.get("verified_binary_readback", {}).get("report_blob_sha") ==
            m.get("replay_evidence", {}).get("readback_report_git_blob_sha"), "pinned binary Git objects")
    sha = l.get("sha256", {})
    require(sha.get("canonical") == m.get("canonical_hash")
            and sha.get("uncompressed_sqlite") == m.get("versioned_research_sha256")
            and sha.get("compressed_git_workflow_verified") == m.get("compressed_sha256") ==
            m.get("verified_binary_readback", {}).get("compressed_sha256")
            and m.get("verified_binary_readback", {}).get("uncompressed_sqlite_sha256") ==
            m.get("versioned_research_sha256"), "hash claim consistency")
    before, after, delta = (l.get("replay_before"), l.get("replay_after"), l.get("delta"))
    require(isinstance(before, dict) and isinstance(after, dict) and
            isinstance(delta, dict), "replay count records")
    for key, rolling in COUNTS.items():
        require(type(before.get(key)) is int and type(after.get(key)) is int
                and after[key] == m["staged_counts"][rolling]
                and type(delta.get(key)) is int
                and delta[key] == after[key] - before[key] >= 0, "replay delta " + key)
    s = m["staged_counts"]
    require(delta["batches"] == 1 and
            delta["findings"] == s.get("new_historical_finding_candidates_this_run") and
            delta["source_candidates"] == s.get("new_source_candidates_all_types_this_run") and
            delta["inspections"] == s.get("new_source_inspection_metadata_this_run"),
            "new batch arithmetic")
    require(l.get("original_canonical_counts") == m.get("canonical") == CANONICAL
            and l.get("preserved_tables") == 88
            and l.get("original_canonical_rows_unchanged") is True
            and l.get("sqlite_integrity") == "ok"
            and l.get("foreign_key_violations") == 0
            and l.get("unresolved_source_refs") ==
            s.get("unknown_source_refs_without_inspection_metadata")
            and len(l.get("metadata_collisions", [])) == s["source_metadata_collisions"]
            and l.get("detached_inspection_count") ==
            s.get("detached_source_identity_review_pending") == 37
            and len(l.get("index_only_unresolved", [])) ==
            s.get("github_index_only_refs_unresolved") == 1, "integrity and conflicts")
    proof = l.get("github_verification", {})
    require(proof.get("workflow_conclusion") == "success_both" and
            proof.get("workflow_git_push_readback_verified") is True and
            proof.get("github_file_metadata_and_checksum_refetched") is True and
            proof.get("github_external_binary_download_unavailable") is True and
            proof.get("independent_binary_sha256_recalculation_not_claimed") is True and
            proof.get("paths_changed_under_research_only") is True and
            proof.get("workflow_replay_run") ==
            f.get("github_readback", {}).get("workflow_replay_run") and
            proof.get("workflow_validation_run") ==
            f.get("github_readback", {}).get("workflow_validation_run"),
            "GitHub Actions readback, without invented external digest")
    require(l.get("ready_for_editorial_review") is False and
            l.get("publication_approved") is False and
            l.get("canonical_promoted") is False
            and isinstance(l.get("blockers"), list) and l["blockers"],
            "ledger cannot approve publication")
