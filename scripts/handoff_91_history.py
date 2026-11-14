"""Validate the 91-batch La Bombilla research handoff without publishing it.

All identities are checked against the immutable history, the independent
readback ledger, and Git objects supplied by the calling validator.
"""
import re

CONTRACT = "91_batch_sqlite_integrity_workflow_git_readback_verified_noncanonical_unapproved"
KIND = "immutable_research_to_app_handoff_history"
LEDGER_KIND = "append_only_91_batch_replay_verified_readback_ledger"
CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
COUNTS = {"github_batches_replayed": 91,
          "github_distinct_substantive_finding_ids": 607,
          "github_source_candidates": 268,
          "github_inspection_entries": 306}
PATH_NAMES = {
    "batch": "latest_batch_artifact_path",
    "coverage": "latest_coverage_artifact_path",
    "audit": "latest_chapter_audit_artifact_path",
    "sql": "versioned_research_sqlite_gz_path",
    "report": "replay_report_path",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def require(condition, message):
    if not condition:
        raise ValueError("91-batch nonpublication validation: " + message)


def validate_frozen(m, f):
    require(m.get("schema_version") == f.get("schema_version") == 4
            and m.get("kind") == "research_to_app_handoff"
            and f.get("kind") == KIND and f.get("branch") == "research-persistence"
            and m.get("handoff_contract_status") == CONTRACT, "kind / schema")
    for k in ("research_commit_sha", "canonical_version", "canonical_hash",
              "versioned_research_sqlite_gz_path", "versioned_research_sha256",
              "compressed_sha256", "replay_report_path"):
        require(m.get(k) == f.get(k), "immutable identity " + k)
    for k in ("research_commit_sha", "verified_replay_commit_sha"):
        require(bool(HEX40.fullmatch(str(m.get(k)))), "commit identity " + k)
    require(m["verified_replay_commit_sha"] == f.get("verified_replay_commit_sha")
            == m.get("replay_evidence", {}).get("snapshot_commit_sha")
            == m.get("verified_binary_readback", {}).get("commit_sha"),
            "replay commit disagreement")
    for k in ("canonical_hash", "compressed_sha256", "versioned_research_sha256"):
        require(bool(HEX64.fullmatch(str(m.get(k)))), "content checksum " + k)
    require(m.get("canonical") == f.get("canonical") == CANONICAL
            and m.get("canonical_version") == f.get("canonical_version") == "V97"
            and m.get("canonical_status") == "unchanged_provisional_V97_not_promoted"
            and f.get("canonical_status") == "unchanged_provisional_not_promoted",
            "canonical preservation")
    require(m.get("immutable_handoff_path") == m.get("latest_handoff_history_path")
            and m["immutable_handoff_path"] in m.get("handoff_history_paths", [])
            and m.get("latest_reconciliation_ledger_path") ==
            f.get("latest_reconciliation_ledger_path") ==
            m.get("replay_evidence", {}).get("verification_ledger")
            and m["latest_reconciliation_ledger_path"] in
            m.get("reconciliation_artifact_paths", []), "historical provenance paths")
    require(f.get("latest_batch_artifact_path") == m.get("latest_batch_artifact_path")
            and f["latest_batch_artifact_path"] in m.get("research_batch_artifact_paths", [])
            and f.get("chapter_audit_artifact_paths") ==
            [m.get("latest_chapter_audit_artifact_path")]
            and f.get("coverage_artifact_paths") ==
            [m.get("latest_coverage_artifact_path")], "batch / coverage / audit linkage")
    for k, n in COUNTS.items():
        require(type(m.get("staged_counts", {}).get(k)) is int
                and m["staged_counts"][k] == n
                and f.get("staged_counts", {}).get(k) == n, "verified count " + k)
    staged = m["staged_counts"]
    for k, expected in (("github_index_only_refs_unresolved", 1),
                        ("source_metadata_collisions", 2),
                        ("detached_source_identity_review_pending", 37)):
        require(staged.get(k) == f["staged_counts"].get(k) == expected,
                "source-identity backlog " + k)
    require(staged.get("unknown_source_refs") == 1
            and staged.get("new_historical_finding_candidates_this_run") == 11
            and staged.get("new_source_candidates_all_types_this_run") == 8
            and staged.get("new_source_inspection_metadata_this_run") == 8
            and staged.get("external_staging_semantic_join_verified") is False,
            "provisional research count or semantic join")
    for doc in (m, f):
        require(doc.get("ready_for_editorial_review") is False
                and doc.get("publication_approved") is False
                and doc.get("canonical_promoted") is False
                and isinstance(doc.get("blockers"), list) and doc["blockers"],
                "explicit editorial nonapproval")
    require(m.get("ready_for_publication") is False
            and m.get("auto_merge_permitted") is False
            and f.get("ready_for_publication") is False
            and f.get("auto_merge_permitted") is False
            and m.get("reconciliation_verified") is True, "nonpublication gate")
    require(isinstance(m.get("evidence_status"), str)
            and "uncorroborated" in m["evidence_status"]
            and isinstance(f.get("evidence_status"), str)
            and f.get("immutable") is True, "unapproved immutable evidence")
    require(m.get("verified_binary_readback", {}).get(
                "compress_digest_recomputed_independently_from_github_fetched_base64") is False
            and m.get("replay_evidence", {}).get("independent_binary_download_blocked") is True,
            "independent binary download must not be falsely claimed")


def validate_ledger(m, f, ledger, actual):
    require(ledger.get("schema_version") == 2
            and ledger.get("kind") == LEDGER_KIND
            and ledger.get("branch") == "research-persistence"
            and ledger.get("input_batch_commit_sha") == m["research_commit_sha"]
            and ledger.get("input_coverage_commit_sha") == f["coverage_commit_sha"]
            and ledger.get("input_templo_audit_commit_sha") == f["chapter_audit_commit_sha"]
            and ledger.get("verified_snapshot_commit_sha") ==
            m["verified_replay_commit_sha"], "research commit chain")
    expected = {k: m[v] for k, v in PATH_NAMES.items()}
    expected["checks"] = m["replay_evidence"]["compressed_checksum_path"]
    require(ledger.get("paths") == expected, "exact six artifact paths")
    require(set(actual) == set(expected)
            and all(bool(HEX40.fullmatch(str(v))) for v in actual.values()),
            "actual Git blob identities missing")
    check = ledger.get("checks", {})
    require(actual["sql"] == check.get("readback_compressed_binary_blob_sha")
            == m["replay_evidence"]["readback_binary_git_blob_sha"]
            == m["verified_binary_readback"]["git_blob_sha"]
            == f["integrity"]["readback_compressed_binary_blob_sha"]
            and actual["report"] == check.get("readback_report_blob_sha")
            == m["replay_evidence"]["readback_report_git_blob_sha"]
            == m["verified_binary_readback"]["report_blob_sha"]
            == f["integrity"]["readback_report_blob_sha"]
            and actual["checks"] == check.get("readback_checksum_blob_sha")
            == f["integrity"]["readback_checksum_blob_sha"],
            "recorded Git objects differ from repository")
    require(ledger.get("canonical_V97", {}).get("counts") == CANONICAL
            and ledger["canonical_V97"].get("sha256") == m["canonical_hash"]
            and ledger["canonical_V97"].get("rows_unchanged") is True
            and ledger["canonical_V97"].get("tables_preserved") == 88
            and ledger["canonical_V97"].get("status") ==
            "unchanged_provisional_not_promoted", "canonical V97 readback")
    staged = m["staged_counts"]
    field_map = {"github_batches_replayed": "github_batches_replayed",
                 "github_distinct_substantive_finding_ids":
                     "github_distinct_substantive_finding_ids",
                 "github_source_candidates": "github_source_candidates",
                 "github_inspection_entries": "github_inspection_entries"}
    before, after = ledger.get("before", {}), ledger.get("after", {})
    for src, dest in field_map.items():
        require(type(after.get(dest)) is int and after[dest] == staged[src]
                and type(before.get(dest)) is int and after[dest] >= before[dest],
                "replay ledger total " + src)
    for k, change in (("github_batches_replayed", 1),
                      ("github_distinct_substantive_finding_ids", 11),
                      ("github_source_candidates", 8),
                      ("github_inspection_entries", 8)):
        require(after[k] - before[k] == change, "append-only delta " + k)
    require(ledger.get("delta") ==
            {"batches": 1, "findings": 11, "sources": 8, "source_inspections": 8},
            "batch delta declaration")
    require(check.get("sqlite_integrity") == f["integrity"]["sqlite_integrity"] == "ok"
            and check.get("foreign_key_violations") == 0
            and f["integrity"]["foreign_key_violations"] == 0
            and check.get("uncompressed_sha256") ==
            f["integrity"]["uncompressed_sha256"] == m["versioned_research_sha256"]
            and check.get("compressed_sha256") ==
            f["integrity"]["compressed_sha256"] == m["compressed_sha256"]
            and check.get("readback_compressed_size_bytes") == 1076100
            and check.get("workflow_outcome") == "both_success"
            and check.get("external_binary_download_or_hash_performed") is False,
            "SQLite integrity or workflow readback")
    backlog = ledger.get("reconciliation_backlog", {})
    require(backlog.get("detached_original_inspections") == 37
            and backlog.get("cross_batch_source_metadata_collisions") == 2
            and len(backlog.get("unknown_source_ids", [])) == 1
            and len(backlog.get("unresolved_index_only_finding_ids", [])) == 1,
            "source identity backlog cannot be hidden")
    require(ledger.get("ready_for_editorial_review") is False
            and ledger.get("publication_approved") is False
            and ledger.get("canonical_promoted") is False
            and ledger.get("auto_merge_permitted") is False
            and ledger.get("main_modified") is False
            and isinstance(ledger.get("blockers"), list) and ledger["blockers"],
            "ledger forbids publication")
