"""Strict, private-only consumer for the 88-batch research handoff."""
from __future__ import annotations
import re

CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
CONTRACT = "88_batch_sqlite_integrity_github_full_binary_sha256_verified_noncanonical_unapproved"
COUNT_MAP = {"github_batches": "github_batches_replayed",
             "findings": "github_distinct_substantive_finding_ids",
             "sources": "github_source_candidates",
             "source_inspections": "github_inspection_entries"}

def require(condition, description):
    if not condition:
        raise ValueError("88-batch evidence handoff: " + description)

def validate_frozen(manifest, frozen):
    m, f = manifest, frozen
    require(m.get("schema_version") == f.get("schema_version") == 4
            and m.get("kind") == "research_to_app_handoff"
            and f.get("kind") == "append_only_research_to_app_verified_history"
            and f.get("branch") == "research-persistence"
            and m.get("handoff_contract_status") == CONTRACT, "schema")
    for field in ("research_commit_sha", "verified_replay_commit_sha",
                  "canonical_version", "canonical_hash", "canonical_status",
                  "canonical", "versioned_research_sqlite_gz_path",
                  "versioned_research_sha256", "compressed_sha256",
                  "replay_report_path"):
        require(m.get(field) == f.get(field), "immutable identity " + field)
    require(m.get("canonical") == CANONICAL and
            m.get("canonical_version") == "V97" and
            m.get("canonical_status") == "unchanged_provisional_V97_not_promoted",
            "protected original database")
    require(m.get("immutable_handoff_path") == m.get("latest_handoff_history_path")
            and m.get("immutable_handoff_path") in m.get("handoff_history_paths", [])
            and f.get("verification_ledger_path") ==
                m.get("latest_reconciliation_ledger_path") ==
                m.get("replay_evidence", {}).get("verification_ledger")
            and f.get("verification_ledger_path") in
                m.get("reconciliation_artifact_paths", [])
            and m.get("replay_evidence", {}).get("snapshot_commit_sha") ==
                m.get("verified_replay_commit_sha"), "provenance records")
    for key, rolling in (("source_batch_artifact_paths", "research_batch_artifact_paths"),
                         ("coverage_artifact_paths", "coverage_artifact_paths"),
                         ("chapter_audit_artifact_paths", "chapter_audit_artifact_paths")):
        paths = f.get(key)
        require(isinstance(paths, list) and len(paths) == 1
                and paths[0] in m.get(rolling, []), "research artifact " + key)
    for key, rolling in COUNT_MAP.items():
        require(type(f.get("staged_counts", {}).get(key)) is int
                and f["staged_counts"][key] == m.get("staged_counts", {}).get(rolling),
                "staged count " + key)
    staged = m["staged_counts"]
    require(len(f.get("source_identity_conflicts", [])) ==
            staged.get("source_metadata_collisions") == 2
            and f.get("unknown_source_ids") ==
            staged.get("unknown_source_refs_without_inspection_metadata")
            and len(f["unknown_source_ids"]) == staged.get("unknown_source_refs") == 1
            and f.get("detached_inspections_pending") ==
            staged.get("detached_source_identity_review_pending") == 37
            and staged.get("github_index_only_refs_unresolved") == 1,
            "unresolved evidence identities")
    require(m.get("evidence_status") == f.get("evidence_status") ==
            "research_database_integrated_noncanonical_not_editorially_corroborated",
            "provisional classification")
    for item in (m, f):
        require(all(item.get(key) is False for key in
                    ("ready_for_editorial_review", "ready_for_publication",
                     "canonical_promoted", "publication_approved"))
                and isinstance(item.get("blockers"), list) and item["blockers"],
                "unapproved research")
    require(f.get("no_auto_merge") is True and
            m.get("auto_merge_permitted") is False, "merge prohibition")

def validate_ledger(manifest, frozen, ledger, actual):
    m, f, l = manifest, frozen, ledger
    require(l.get("schema_version") == 2
            and l.get("kind") == "github_research_reconciliation_full_binary_readback"
            and l.get("branch") == "research-persistence"
            and l.get("repository") == "lizperry81/mexico-city-field-guide"
            and l.get("input_research_commit_sha") == m.get("research_commit_sha")
            and l.get("replay_snapshot_commit_sha") == m.get("verified_replay_commit_sha"),
            "ledger and pinned commits")
    paths = {"input":f["source_batch_artifact_paths"][0],
             "coverage":f["coverage_artifact_paths"][0],
             "chapter":f["chapter_audit_artifact_paths"][0],
             "report":m["replay_report_path"],
             "compressed":m["replay_evidence"]["compressed_checksum_path"]}
    for key, path in paths.items():
        entry = l.get("verified_file_blobs", {}).get(key, {})
        require(entry.get("path") == path and entry.get("blob_sha") == actual.get(key)
                and re.fullmatch("[0-9a-f]{40}", str(actual.get(key, ""))),
                "actual Git blob " + key)
    require(re.fullmatch("[0-9a-f]{40}", str(actual.get("sqlite", "")))
            and l.get("versioned_sqlite_gz_path") == m["versioned_research_sqlite_gz_path"]
            and l.get("github_readback_sqlite_gz_git_blob_sha") == actual["sqlite"] ==
                m.get("verified_binary_readback", {}).get("git_blob_sha") ==
                m.get("replay_evidence", {}).get("readback_binary_git_blob_sha")
            and actual["report"] == m.get("verified_binary_readback", {}).get("report_blob_sha") ==
                m.get("replay_evidence", {}).get("readback_report_git_blob_sha"),
            "replay Git object identity")
    require(l.get("github_readback_hash_matches") is True
            and l.get("github_readback_compressed_size_bytes", 0) > 0
            and l.get("github_readback_compressed_sha256_independently_recomputed") ==
                l.get("committed_compressed_sha256") == m["compressed_sha256"]
            and l.get("uncompressed_sqlite_sha256_from_workflow_report") ==
                m["versioned_research_sha256"]
            and m.get("verified_binary_readback", {}).get(
                "compress_digest_recomputed_independently_from_github_fetched_base64") is True,
            "independent binary digest")
    require(l.get("canonical_counts") == f.get("canonical") == CANONICAL
            and l.get("canonical_version") == "V97"
            and l.get("canonical_hash") == m["canonical_hash"]
            and l.get("canonical_tables_preserved") == 88
            and l.get("canonical_rows_unchanged") is True
            and l.get("sqlite_integrity") == "ok"
            and l.get("foreign_key_violations") == 0,
            "canonical/SQLite integrity")
    before, after = l.get("staged_before"), l.get("staged_after")
    require(isinstance(before, dict) and after == f.get("staged_counts")
            and all(type(before.get(k)) is int and before[k] <= after[k]
                    for k in COUNT_MAP), "replay before/after counts")
    staged = m["staged_counts"]
    require(after["github_batches"] - before["github_batches"] == 1
            and after["findings"] - before["findings"] ==
                staged["new_historical_finding_candidates_this_run"]
            and after["sources"] - before["sources"] ==
                staged["new_source_candidates_all_types_this_run"]
            and after["source_inspections"] - before["source_inspections"] ==
                staged["new_source_inspection_metadata_this_run"],
            "strict 88th batch deltas")
    require(l.get("unresolved_source_ids") == f.get("unknown_source_ids")
            and l.get("source_metadata_collisions") ==
                f.get("source_identity_conflicts")
            and len(l.get("unresolved_index_only_finding_ids", [])) ==
                staged["github_index_only_refs_unresolved"]
            and l.get("detached_inspection_count") == f["detached_inspections_pending"]
            and l.get("source_identity_auto_merges") == 0,
            "preserve source conflicts")
    require(l.get("workflow_runs_success") is True
            and all(l.get(key) is False for key in
                    ("canonical_promoted", "publication_approved", "ready_for_editorial_review"))
            and l.get("no_main_modification") is True
            and isinstance(l.get("warnings"), list) and bool(l["warnings"]),
            "producer not publication-authorized")
