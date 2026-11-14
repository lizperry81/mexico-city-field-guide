"""Validate the 87-batch immutable research handoff as PRIVATE evidence only.

All source identities and replay artifacts are checked against committed Git
objects by the caller. This adapter never approves prose or publishes research.
"""
from __future__ import annotations

import re

KIND = "append_only_research_to_app_verified_history"
LEDGER_KIND = "independent_github_replay_readback_and_integrity"
CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
COUNTS = {"github_batches": "github_batches_replayed",
          "staged_findings": "github_distinct_substantive_finding_ids",
          "source_candidates": "github_source_candidates",
          "source_inspections": "github_inspection_entries"}


def require(ok, why):
    if not ok:
        raise ValueError("87-batch handoff provenance: " + why)


def validate_frozen(m, f):
    require(m.get("schema_version") == f.get("schema_version") == 4
            and m.get("kind") == "research_to_app_handoff"
            and f.get("kind") == KIND and f.get("branch") == "research-persistence",
            "history schema")
    for key in ("research_commit_sha", "verified_replay_commit_sha",
                "canonical_version", "canonical_hash", "canonical_status",
                "canonical", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256",
                "replay_report_path"):
        require(m.get(key) == f.get(key), "immutable identity: " + key)
    require(m.get("canonical") == f.get("canonical") == CANONICAL and
            m.get("canonical_version") == "V97" and
            m.get("canonical_status") ==
            "unchanged_provisional_V97_not_promoted", "original canonical database")
    require(m.get("immutable_handoff_path") in m.get("handoff_history_paths", [])
            and f.get("verification_ledger_path") ==
            m.get("replay_evidence", {}).get("verification_ledger")
            and f.get("verification_ledger_path") in
            m.get("reconciliation_artifact_paths", []),
            "immutable archive and independent ledger paths")
    require(m.get("replay_evidence", {}).get("snapshot_commit_sha") ==
            m.get("verified_replay_commit_sha"), "replay commit identity")
    for field in ("source_batch_artifact_paths", "chapter_audit_artifact_paths",
                  "coverage_artifact_paths"):
        rolling = ("research_batch_artifact_paths" if
                   field == "source_batch_artifact_paths" else field)
        vals = f.get(field)
        require(isinstance(vals, list) and vals and len(vals) == len(set(vals))
                and set(vals).issubset(set(m.get(rolling, []))),
                "missing immutable source/audit paths: " + field)
    for old, new in COUNTS.items():
        require(type(f.get("staged_counts", {}).get(old)) is int and
                f["staged_counts"][old] == m.get("staged_counts", {}).get(new),
                "research count: " + old)
    require(f.get("source_identity_conflicts") ==
            m.get("staged_counts", {}).get("source_metadata_conflict_details",
                                         f.get("source_identity_conflicts")),
            "source metadata must remain explicitly contested")
    require(len(f.get("source_identity_conflicts", [])) ==
            m["staged_counts"]["source_metadata_collisions"]
            and len(f.get("unknown_source_ids", [])) ==
            m["staged_counts"]["unknown_source_refs"]
            and f.get("unknown_source_ids") ==
            m["staged_counts"]["unknown_source_refs_without_inspection_metadata"]
            and f.get("detached_inspections_pending") ==
            m["staged_counts"]["detached_source_identity_review_pending"],
            "unresolved source and inspection identities")
    require(f.get("evidence_status") ==
            "research_database_integrated_noncanonical_not_editorially_corroborated"
            and m.get("evidence_status") ==
            "noncanonical_source_located_not_independently_corroborated_or_publication_approved",
            "unapproved evidence classification")
    require(all(doc.get("ready_for_editorial_review") is False and
                doc.get("ready_for_publication") is False and
                doc.get("canonical_promoted") is False for doc in (m, f)),
            "editorial or canonical promotion prohibited")
    require(f.get("publication_approved") is False and
            f.get("no_auto_merge") is True and
            m.get("publication_approved") is False and
            m.get("auto_merge_permitted") is False,
            "publication/merge authorization prohibited")
    require(isinstance(f.get("blockers"), list) and f["blockers"] and
            isinstance(m.get("blockers"), list) and m["blockers"],
            "unresolved evidence blockers must be preserved")


def validate_ledger(m, f, ledger, actual):
    require(ledger.get("schema_version") == 2 and
            ledger.get("kind") == LEDGER_KIND and
            ledger.get("branch") == "research-persistence", "ledger schema")
    for old, new in (("research_commit_sha", "research_commit_sha"),
                     ("verified_replay_commit_sha", "verified_replay_commit_sha"),
                     ("report_path", "replay_report_path"),
                     ("sqlite_gzip_path", "versioned_research_sqlite_gz_path"),
                     ("compressed_sha256", "compressed_sha256"),
                     ("canonical_sha256", "canonical_hash"),
                     ("canonical_version", "canonical_version")):
        # The checksum is stored as a separate independent field below.
        if old == "compressed_sha256":
            continue
        require(ledger.get(old) == m.get(new), "ledger pin: " + old)
    require(ledger.get("independent_compressed_sha256") ==
            ledger.get("committed_compressed_sha256") ==
            m.get("compressed_sha256") and
            ledger.get("compressed_readback_sha256_match") is True and
            ledger.get("uncompressed_sha256_reported_after_workflow_gzip_decode") ==
            m.get("versioned_research_sha256"), "independent compressed binary digest")
    require(ledger.get("checksum_path") ==
            m.get("replay_evidence", {}).get("compressed_checksum_path")
            and m.get("replay_evidence", {}).get("compressed_readback_sha256_matched") is True,
            "checksum record")
    for key, path in (("sqlite_gzip", "sqlite"),
                      ("report", "report"),
                      ("batch", "batch"),
                      ("coverage", "coverage"),
                      ("audit", "audit")):
        require(ledger.get("github_blob_sha", {}).get(key) == actual.get(path) and
                re.fullmatch("[0-9a-f]{40}", str(actual.get(path, ""))),
                "Git object identity: " + key)
    replay = m.get("replay_evidence", {})
    require(actual["sqlite"] == replay.get("readback_binary_git_blob_sha") and
            actual["report"] == replay.get("readback_report_git_blob_sha") and
            replay.get("snapshot_commit_sha") == m.get("verified_replay_commit_sha"),
            "rolling manifest readback identities")
    require(ledger.get("canonical_counts") == f.get("canonical") == CANONICAL
            and ledger.get("canonical_rows_unchanged") is True and
            ledger.get("canonical_tables_preserved") == 88 and
            ledger.get("sqlite_integrity") == "ok" and
            ledger.get("foreign_key_violations") == 0 and
            ledger.get("raw_batch_documents_in_sqlite") ==
            m.get("staged_counts", {}).get("raw_batch_documents_in_new_sqlite"),
            "SQLite or canonical integrity")
    after = ledger.get("counts_after")
    before = ledger.get("counts_before")
    require(isinstance(after, dict) and isinstance(before, dict) and
            after == f.get("staged_counts") and
            all(type(before.get(k)) is int and before[k] <= after[k]
                for k in COUNTS), "reconciliation totals")
    require(after["github_batches"] - before["github_batches"] == 1 and
            after["staged_findings"] - before["staged_findings"] ==
            m["staged_counts"]["new_historical_finding_candidates_this_run"] and
            after["source_candidates"] - before["source_candidates"] ==
            m["staged_counts"]["new_source_candidates_all_types_this_run"] and
            after["source_inspections"] - before["source_inspections"] ==
            m["staged_counts"]["new_source_inspection_metadata_this_run"],
            "new research delta")
    require(ledger.get("source_id_conflicts") == f.get("source_identity_conflicts")
            and ledger.get("unknown_source_ids") == f.get("unknown_source_ids")
            and ledger.get("detached_original_inspections_review_pending") ==
            f.get("detached_inspections_pending")
            and ledger.get("unresolved_index_only_count") ==
            m["staged_counts"]["github_index_only_refs_unresolved"],
            "unresolved evidence reconciliation")
    require(ledger.get("evidence_status") ==
            "noncanonical_research_staging_not_editorially_corroborated" and
            ledger.get("ready_for_editorial_review") is False and
            ledger.get("ready_for_publication") is False and
            ledger.get("publication_approved") is False,
            "ledger publication authorization")
    require(ledger.get("blockers") == f.get("blockers") and
            isinstance(ledger.get("independent_sha256_algorithm"), str) and
            ledger.get("compressed_bytes_fetched", 0) > 0,
            "evidence blockers or binary readback absent")
