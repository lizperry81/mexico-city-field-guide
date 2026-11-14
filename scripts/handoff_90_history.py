"""Strict read-only consumer of the 90-batch CUPA research handoff.

The ledger is a provenance statement, not an editorial approval. Git object
identities and the gzip/SQLite SHA-256 bytes are checked by the caller.
"""
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
CONTRACT = "90_batch_sqlite_integrity_workflow_git_readback_verified_noncanonical_unapproved"
METRICS = {"batches": "github_batches_replayed",
           "findings": "github_distinct_substantive_finding_ids",
           "source_candidates": "github_source_candidates",
           "inspections": "github_inspection_entries"}


def require(ok, what):
    if not ok:
        raise ValueError("90-batch private handoff: " + what)


def validate_frozen(m, f):
    require(m.get("schema_version") == f.get("schema_version") == 4
            and m.get("kind") == "research_to_app_handoff"
            and f.get("kind") == "immutable_research_handoff_history_entry"
            and f.get("branch") == "research-persistence"
            and m.get("handoff_contract_status") == CONTRACT, "handoff schema")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                "canonical_status", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256", "replay_report_path"):
        require(m.get(key) == f.get(key), "frozen identity " + key)
    require(all(HEX40.fullmatch(str(x)) for x in (
            m.get("research_commit_sha"), m.get("verified_replay_commit_sha"),
            f.get("workflow_fix_commit_sha"), f.get("integrity_ledger_commit_sha"))),
            "unverifiable commit")
    require(m.get("verified_replay_commit_sha") == f.get("snapshot_commit_sha")
            == m.get("replay_evidence", {}).get("snapshot_commit_sha"), "replay identity")
    require(all(HEX64.fullmatch(str(m.get(k))) for k in (
            "canonical_hash", "compressed_sha256", "versioned_research_sha256")),
            "malformed SHA-256")
    require(m.get("canonical") == CANONICAL
            and m.get("canonical_version") == "V97"
            and m.get("canonical_status") == "unchanged_provisional_V97_not_promoted",
            "canonical V97 protection")
    require(m.get("immutable_handoff_path") == m.get("latest_handoff_history_path")
            and m.get("immutable_handoff_path") in m.get("handoff_history_paths", [])
            and f.get("reconciliation_ledger_path") ==
            m.get("latest_reconciliation_ledger_path") ==
            m.get("replay_evidence", {}).get("verification_ledger")
            and f.get("reconciliation_ledger_path") in
            m.get("reconciliation_artifact_paths", []), "versioned evidence paths")
    require(f.get("source_batch_path") == m.get("latest_batch_artifact_path")
            and f.get("source_batch_path") in m.get("research_batch_artifact_paths", [])
            and f.get("chapter_audit_artifact_paths") ==
            [m.get("latest_chapter_audit_artifact_path")]
            and f.get("coverage_artifact_paths") ==
            [m.get("latest_coverage_artifact_path")], "batch and audit paths")
    for local, rolling in METRICS.items():
        require(type(f.get("staged_counts", {}).get(local)) is int
                and f["staged_counts"][local] == m.get("staged_counts", {}).get(rolling),
                "replay counts " + local)
    require(m["staged_counts"]["github_batches_replayed"] == 90
            and m["staged_counts"]["github_distinct_substantive_finding_ids"] == 596,
            "90-batch total")
    require(m["staged_counts"]["unknown_source_refs"] == 1
            and m["staged_counts"]["github_index_only_refs_unresolved"] == 1
            and m["staged_counts"]["source_metadata_collisions"] == 2
            and m["staged_counts"]["detached_source_identity_review_pending"] == 37,
            "unresolved identities")
    # Producer's frozen summary and rolling pointer describe different scopes:
    # a full-text read versus overall research evidence. Do not demand identical
    # prose labels; demand an explicit restrictive status at both levels.
    require(isinstance(m.get("evidence_status"), str)
            and "uncorroborated" in m["evidence_status"]
            and isinstance(f.get("evidence_status"), str)
            and "unverified_originals" in f["evidence_status"],
            "unapproved evidence status")
    for obj in (m, f):
        require(obj.get("ready_for_editorial_review") is False
                and obj.get("publication_approved") is False
                and isinstance(obj.get("blockers"), list) and obj["blockers"],
                "not approved for publication")
    require(m.get("ready_for_publication") is False
            and m.get("canonical_promoted") is False
            and m.get("auto_merge_permitted") is False
            and m.get("reconciliation_verified") is True, "publication barrier")
    readback = f.get("github_readback", {})
    require(readback.get("workflow_conclusion") == "success"
            and readback.get("repository_sqlite_checksum_workflow_verified") is True
            and readback.get("persisted_report_file_readback") is True
            and readback.get("independent_external_binary_download_not_done") is True
            and readback.get("canonical_rows_unchanged") is True
            and readback.get("paths_changed_under_research_only_except_workflow_fix") is True,
            "honest GitHub readback provenance")


def validate_ledger(m, f, ledger, actual):
    require(ledger.get("schema_version") == 4
            and ledger.get("kind") == "noncanonical_research_replay_readback_ledger"
            and ledger.get("branch") == "research-persistence"
            and ledger.get("research_batch_commit_sha") == m["research_commit_sha"]
            and ledger.get("workflow_fix_commit_sha") == f["workflow_fix_commit_sha"]
            and ledger.get("versioned_sqlite_snapshot_commit_sha") ==
            m["verified_replay_commit_sha"]
            and ledger.get("workflow_run_id") == f["github_readback"]["workflow_replay_run"],
            "replay and ledger provenance")
    paths = ledger.get("paths", {})
    expected = {
        "batch": f["source_batch_path"],
        "coverage": f["coverage_artifact_paths"][0],
        "audit": f["chapter_audit_artifact_paths"][0],
        "compressed_db": m["versioned_research_sqlite_gz_path"],
        "report": m["replay_report_path"],
        "checksum": m["replay_evidence"]["compressed_checksum_path"],
    }
    require(paths == expected, "ledger paths")
    require(set(actual) == set(expected)
            and all(HEX40.fullmatch(str(v)) for v in actual.values()),
            "Git blob identity missing")
    require(actual["compressed_db"] ==
            m["replay_evidence"]["readback_binary_git_blob_sha"]
            and actual["report"] ==
            m["replay_evidence"]["readback_report_git_blob_sha"]
            == ledger.get("verified_hashes", {}).get("replay_report_git_blob_sha"),
            "binary/replay Git object mismatch")
    hashes = ledger.get("verified_hashes", {})
    require(hashes.get("canonical_sha256") == m["canonical_hash"]
            and hashes.get("compressed_sqlite_sha256") == m["compressed_sha256"]
            and hashes.get("reconciled_sqlite_uncompressed_sha256") ==
            m["versioned_research_sha256"], "unverified SHA-256 claims")
    before, after = ledger.get("counts_before"), ledger.get("counts_after")
    require(isinstance(before, dict) and isinstance(after, dict),
            "missing replay counts")
    for key, source_key in (("github_batches", "github_batches_replayed"),
                            ("staged_findings", "github_distinct_substantive_finding_ids"),
                            ("source_candidates", "github_source_candidates"),
                            ("source_inspections", "github_inspection_entries")):
        require(type(before.get(key)) is int and type(after.get(key)) is int
                and after[key] == m["staged_counts"][source_key]
                and after[key] >= before[key], "replay count " + key)
    require(after["github_batches"] - before["github_batches"] == 1
            and after["staged_findings"] - before["staged_findings"] ==
            m["staged_counts"]["new_historical_finding_candidates_this_run"]
            and after["source_candidates"] - before["source_candidates"] ==
            m["staged_counts"]["new_source_candidates_all_types_this_run"]
            and after["source_inspections"] - before["source_inspections"] ==
            m["staged_counts"]["new_source_inspection_metadata_this_run"],
            "batch arithmetic")
    for key, val in (("canonical_sources", 616), ("canonical_claims", 422),
                     ("canonical_links", 403), ("canonical_findings", 68)):
        require(before.get(key) == after.get(key) == val,
                "canonical count drift")
    check = ledger.get("validation", {})
    require(check.get("canonical_rows_unchanged") is True
            and check.get("canonical_tables_preserved") == 88
            and check.get("sqlite_integrity") == "ok"
            and check.get("foreign_key_violations") == 0
            and check.get("raw_batch_documents_in_sqlite") == 90
            and check.get("workflows_tests") == "passed"
            and check.get("gzip_test") == "passed"
            and check.get("github_persisted_binary_hash_compared_inside_workflow") is True
            and check.get("independent_external_binary_retrieval") is False,
            "SQLite and workflow attestation")
    conflicts = ledger.get("source_identity_review", {})
    require(conflicts.get("detached_inspections") == 37
            and conflicts.get("detached_same_url_candidates") == 9
            and conflicts.get("detached_no_match") == 28
            and conflicts.get("source_metadata_collisions") == 2
            and conflicts.get("unresolved_index_only_count") == 1
            and conflicts.get("unknown_source_ids") ==
            m["staged_counts"]["unknown_source_refs_without_inspection_metadata"],
            "unresolved source conflicts")
    research = ledger.get("new_research", {})
    require(research.get("findings") == 11
            and research.get("new_provisional_source_ids") == 7
            and research.get("new_source_inspection_metadata_records") == 7
            and research.get("primary_government_archives_examined") == 0
            and research.get("editorial_status") ==
            "provisional_not_corroborated_or_publication_approved",
            "new material cannot be published")
    require(ledger.get("no_main_changes") is True
            and ledger.get("canonical_promoted") is False
            and ledger.get("ready_for_editorial_review") is False
            and ledger.get("publication_approved") is False
            and isinstance(ledger.get("blockers"), list) and ledger["blockers"],
            "ledger forbids automatic publication")
