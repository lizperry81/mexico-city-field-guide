"""Strict 86-batch read-only research handoff adapter; never authorizes publication."""
from __future__ import annotations
import re

KIND = "research_to_app_handoff_append_only_history"
LEDGER_KIND = "github_binary_readback_and_full_replay_verification"

def require(ok, reason):
    if not ok:
        raise ValueError("86-batch research provenance: " + reason)

def validate_frozen(m, f, reader):
    require(m.get("schema_version") == f.get("schema_version") == 4 and
            m.get("kind") == "research_to_app_handoff" and
            f.get("kind") == KIND, "history schema")
    for field in ("research_commit_sha", "canonical_hash", "canonical_version",
                  "canonical_status", "canonical", "versioned_research_sqlite_gz_path",
                  "versioned_research_sha256", "compressed_sha256", "evidence_status"):
        require(m.get(field) == f.get(field), "immutable drift: " + field)
    require(m.get("verified_replay_commit_sha") ==
            f.get("workflow_snapshot_commit_sha") and
            m.get("replay_evidence", {}).get("snapshot_commit_sha") ==
            m.get("verified_replay_commit_sha"), "pinned replay commit")
    require(m.get("immutable_handoff_path") == m.get("latest_handoff_history_path") and
            f.get("reconciliation_report_path") == m.get("replay_report_path") and
            f.get("verification_ledger_path") ==
            m.get("replay_evidence", {}).get("verification_ledger") ==
            m.get("latest_reconciliation_ledger_path"), "history and ledger pointers")
    require(f.get("batch_artifact_path") in m.get("research_batch_artifact_paths", []) and
            f.get("supplemental_source_audit_path") in
            m.get("reconciliation_artifact_paths", []), "new source artifacts missing")
    for field in ("chapter_audit_artifact_paths", "coverage_artifact_paths"):
        paths = f.get(field)
        require(isinstance(paths, list) and len(paths) == 1 and
                set(paths).issubset(set(m.get(field, []))), "audit paths: " + field)
    count_map = {
        "batches": "github_batches_replayed",
        "findings": "github_distinct_substantive_finding_ids",
        "source_candidates": "github_source_candidates",
        "inspections": "github_inspection_entries",
        "detached_original_inspections": "detached_original_inspection_rows_replayed",
        "unknown_source_ids": "unknown_source_refs",
        "metadata_conflicts": "source_metadata_collisions",
        "unresolved_index_only": "github_index_only_refs_unresolved",
    }
    for old, new in count_map.items():
        v = f.get("staged_counts", {}).get(old)
        require(type(v) is int and v == m.get("staged_counts", {}).get(new),
                "staged count: " + old)
    require(m.get("canonical") ==
            {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9},
            "V97 canonical counts")
    for doc in (m, f):
        require(doc.get("ready_for_editorial_review") is False and
                doc.get("ready_for_publication") is False and
                doc.get("canonical_promoted") is False, "unauthorized editorial approval")
    require(m.get("auto_merge_permitted") is False and
            m.get("evidence_status") ==
            "noncanonical_source_located_not_independently_corroborated_or_publication_approved",
            "publication gate")
    integrity = m.get("latest_research_integrity", {})
    require(isinstance(reader, str) and re.fullmatch(r"[0-9a-f]{40}", reader) and
            integrity.get("main_reader_blob_verified") == reader,
            "main reader Git identity differs")
    require(integrity.get("sqlite_integrity") == "ok" and
            integrity.get("foreign_key_violations") == 0 and
            integrity.get("canonical_tables_preserved") == 88 and
            integrity.get("canonical_rows_unchanged") is True and
            integrity.get("github_binary_sha256_readback_verified") is True and
            integrity.get("workflow_generated_snapshot_commit_sha_verified") is True,
            "independent snapshot integrity")

def validate_ledger(m, f, ledger, actual):
    require(ledger.get("schema_version") == 2 and
            ledger.get("kind") == LEDGER_KIND and
            ledger.get("branch") == "research-persistence", "ledger schema")
    fields = {
        "research_commit_sha": "research_commit_sha",
        "workflow_snapshot_commit_sha": "verified_replay_commit_sha",
        "canonical_version": "canonical_version",
        "canonical_sha256": "canonical_hash",
        "sqlite_gz_path": "versioned_research_sqlite_gz_path",
        "replay_report_path": "replay_report_path",
        "compressed_sha256": "compressed_sha256",
        "decompressed_sqlite_sha256": "versioned_research_sha256",
    }
    for old, new in fields.items():
        require(ledger.get(old) == m.get(new), "ledger identity: " + old)
    require(ledger.get("branch_head_at_verification") ==
            m.get("verified_replay_commit_sha") and
            ledger.get("canonical_counts") == m.get("canonical") == f.get("canonical"),
            "replay commit or original canonical identity")
    require(ledger.get("canonical_promoted") is False and
            ledger.get("canonical_rows_unchanged") is True and
            ledger.get("canonical_tables_preserved") == 88 and
            ledger.get("sqlite_integrity") == "ok" and
            ledger.get("foreign_key_violations") == 0 and
            ledger.get("ready_for_editorial_review") is False and
            ledger.get("publication_approved") is False and
            ledger.get("validation_status") ==
            "RESEARCH_STAGING_VERIFIED_NOT_CANONICAL_NOT_EDITORIALLY_APPROVED",
            "ledger nonpublication or integrity")
    counts = {"batches":"github_batches_replayed",
              "findings":"github_distinct_substantive_finding_ids",
              "source_candidates":"github_source_candidates",
              "inspections":"github_inspection_entries",
              "detached_original_inspections":"detached_original_inspection_rows_replayed",
              "unknown_source_ids":"unknown_source_refs",
              "metadata_conflicts":"source_metadata_collisions",
              "unresolved_index_only":"github_index_only_refs_unresolved"}
    for old, new in counts.items():
        require(ledger.get("staged_counts", {}).get(old) ==
                m.get("staged_counts", {}).get(new), "ledger staged count: " + old)
    readback = m.get("verified_binary_readback", {})
    replay = m.get("replay_evidence", {})
    integrity = m.get("latest_research_integrity", {})
    require(actual.get("sqlite") == ledger.get("sqlite_gzip_github_blob_sha") ==
            readback.get("git_blob_sha") == replay.get("readback_binary_git_blob_sha") ==
            integrity.get("github_binary_blob_sha"), "SQLite Git object mismatch")
    require(actual.get("report") == ledger.get("replay_report_blob_sha") ==
            readback.get("report_blob_sha") == replay.get("readback_report_git_blob_sha") ==
            integrity.get("github_report_blob_sha"), "replay report Git object mismatch")
    require(readback.get("compressed_sha256") == m.get("compressed_sha256") and
            readback.get("uncompressed_sqlite_sha256") ==
            m.get("versioned_research_sha256") and
            readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is True and
            readback.get("canonical_rows_unchanged") is True, "binary digest")
    binary = ledger.get("github_binary_readback", {})
    require(binary.get("fetched_from") == "research-persistence" and
            binary.get("gzip_magic_verified") is True and
            binary.get("compressed_sha256_recalculated_matches_repo_checksum") is True and
            type(binary.get("decoded_bytes_len")) is int and
            binary["decoded_bytes_len"] > 0, "independent binary readback")
    require(set(ledger.get("new_paths", [])) ==
            {f["batch_artifact_path"], *f["chapter_audit_artifact_paths"],
             *f["coverage_artifact_paths"]}, "unexpected newly reviewed paths")
