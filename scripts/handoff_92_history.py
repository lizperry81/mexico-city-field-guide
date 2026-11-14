"""Strict immutable 92-batch Ciudadela research handoff checks (no publication)."""
import re

KIND = "immutable_research_to_app_handoff_history"
CONTRACT = "92_batch_integrity_workflow_github_readback_verified_noncanonical_not_approved"
CANONICAL = {"sources": 616, "claims": 422, "claim_sources": 403,
             "canonical_findings": 68, "canonical_source_inspections": 9}
COUNTS = {"github_batches_replayed": 92,
          "github_distinct_substantive_finding_ids": 618,
          "github_source_candidates": 276, "github_inspection_entries": 314,
          "github_inspection_payload_rows": 314}
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")

def require(ok, reason):
    if not ok:
        raise ValueError("92-batch private research: " + reason)

def paths(m, f):
    return {
        "binary": m["versioned_research_sqlite_gz_path"],
        "report": m["replay_report_path"],
        "checksum": m["replay_evidence"]["compressed_checksum_path"],
        "batch": f["source_batch_artifact_paths"][0],
        "coverage": f["coverage_artifact_paths"][0],
        "audit": f["chapter_audit_artifact_paths"][0],
        "preflight": f["source_identity_preflight_path"],
    }

def validate_frozen(m, f):
    require(m.get("schema_version") == f.get("schema_version") == 4
            and m.get("kind") == "research_to_app_handoff"
            and f.get("kind") == KIND and f.get("branch") == "research-persistence"
            and m.get("handoff_contract_status") == CONTRACT, "contract")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                "canonical_status", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256",
                "replay_report_path", "evidence_status"):
        require(m.get(key) == f.get(key), "frozen field " + key)
    require(HEX40.fullmatch(str(m.get("research_commit_sha")))
            and HEX40.fullmatch(str(m.get("verified_replay_commit_sha")))
            and m["verified_replay_commit_sha"] == f.get("validated_sqlite_commit_sha")
            == m.get("replay_evidence", {}).get("snapshot_commit_sha")
            == m.get("verified_binary_readback", {}).get("commit_sha"),
            "research/replay SHA lineage")
    for key in ("canonical_hash", "versioned_research_sha256", "compressed_sha256"):
        require(HEX64.fullmatch(str(m.get(key))), "hash syntax " + key)
    require(m.get("canonical_version") == "V97"
            and m.get("canonical_status") == "unchanged_provisional_V97_not_promoted"
            and m.get("canonical") == CANONICAL, "canonical preserved")
    require(f.get("previous_handoff_path") == m.get("previous_immutable_handoff_path")
            and f["previous_handoff_path"] in m.get("handoff_history_paths", [])
            and m.get("immutable_handoff_path") in m.get("handoff_history_paths", [])
            and f.get("verification_ledger_path") == m.get("latest_reconciliation_ledger_path")
            == m.get("replay_evidence", {}).get("verification_ledger"),
            "append-only provenance")
    expected = paths(m, f)
    require(f.get("source_batch_artifact_paths") == [m.get("latest_batch_artifact_path")]
            and f.get("chapter_audit_artifact_paths") == [m.get("latest_chapter_audit_artifact_path")]
            and f.get("coverage_artifact_paths") == [m.get("latest_coverage_artifact_path")]
            and all(p in m.get("research_batch_artifact_paths", [])
                    for p in f["source_batch_artifact_paths"])
            and all(p in m.get("chapter_audit_artifact_paths", [])
                    for p in f["chapter_audit_artifact_paths"])
            and all(p in m.get("coverage_artifact_paths", [])
                    for p in f["coverage_artifact_paths"])
            and f.get("source_identity_preflight_path") in m.get("reconciliation_artifact_paths", [])
            and all(p.startswith("research/") for p in expected.values()),
            "exact staged artifact paths")
    counts = m.get("staged_counts", {})
    frozen = f.get("staged_counts", {})
    require(isinstance(frozen, dict) and
            all(counts.get(k) == v for k,v in frozen.items()),
            "staged count, source type, or conflict changed")
    for key, number in COUNTS.items():
        require(type(counts.get(key)) is int and counts[key] == number, "count " + key)
    require(counts.get("unknown_source_refs") == 1
            and counts.get("source_metadata_collisions") == 2
            and counts.get("github_index_only_refs_unresolved") == 1
            and counts.get("detached_source_identity_review_pending") == 37
            and counts.get("new_historical_finding_candidates_this_run") == 11
            and counts.get("new_source_candidates_all_types_this_run") == 8
            and counts.get("external_staging_semantic_join_verified") is False,
            "open source-identity conflicts or finding delta")
    for doc in (m, f):
        require(all(doc.get(k) is False for k in
                    ("ready_for_editorial_review", "ready_for_publication",
                     "publication_approved", "canonical_promoted", "auto_merge_permitted"))
                and isinstance(doc.get("blockers"), list) and doc["blockers"],
                "research falsely approved")
    require("not_editorially_corrobated" in str(m.get("evidence_status")),
            "unreviewed status lost")
    readback = m.get("verified_binary_readback", {})
    require(readback.get("sqlite_integrity") == "ok"
            and readback.get("foreign_key_violations") == 0
            and readback.get("canonical_rows_unchanged") is True
            and readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is False
            and m.get("replay_evidence", {}).get("independent_binary_download_blocked") is True,
            "readback limitation incorrectly reported")

def validate_ledger(m, f, ledger, actual):
    require(ledger.get("schema_version") == 3
            and ledger.get("kind") == "research_only_sqlite_and_github_readback_verification"
            and ledger.get("branch") == "research-persistence"
            and ledger.get("source_research_commit_sha") == m["research_commit_sha"]
            and ledger.get("verified_snapshot_commit_sha") == m["verified_replay_commit_sha"]
            and ledger.get("canonical_version") == "V97"
            and ledger.get("canonical_sha256") == m["canonical_hash"]
            and ledger.get("canonical_counts") == CANONICAL
            and ledger.get("canonical_rows_unchanged") is True
            and ledger.get("canonical_tables_preserved") == 88,
            "replay ledger identity")
    require(ledger.get("versioned_database_path") == m["versioned_research_sqlite_gz_path"]
            and ledger.get("versioned_database_uncompressed_sha256") == m["versioned_research_sha256"]
            and ledger.get("versioned_database_compressed_sha256") == m["compressed_sha256"]
            and ledger.get("validated_replay_report_path") == m["replay_report_path"],
            "replay path/checksum")
    required = paths(m, f)
    require(set(actual) == set(required)
            and all(bool(HEX40.fullmatch(str(actual.get(key)))) for key in required),
            "actual Git artifact identities incomplete")
    checks = ledger.get("github_readback", {})
    blob_map = {"binary": "binary_git_blob_sha",
                "report": "report_git_blob_sha",
                "checksum": "checksum_git_blob_sha",
                "batch": "batch_git_blob_sha",
                "coverage": "coverage_git_blob_sha",
                "audit": "chapter_audit_git_blob_sha",
                "preflight": "preflight_git_blob_sha"}
    for key, ledger_key in blob_map.items():
        require(actual[key] == checks.get(ledger_key),
                "Git blob mismatch " + key)
    require(actual["binary"] == m["replay_evidence"]["readback_binary_git_blob_sha"]
            == m["verified_binary_readback"]["git_blob_sha"]
            and actual["report"] == m["replay_evidence"]["readback_report_git_blob_sha"]
            == m["verified_binary_readback"]["report_blob_sha"]
            and checks.get("workflow_compressed_git_readback_digest_matched") is True
            and checks.get("workflow_gzip_integrity_passed") is True
            and checks.get("workflow_full_sqlite_integrity_passed") is True
            and checks.get("independent_external_binary_digest_recomputed") is False
            and checks.get("binary_content_readback_empty_from_connector") is True,
            "published readback evidence limitation or digest")
    count_map = {"github_batch_files": "github_batches_replayed",
                 "staged_finding_ids": "github_distinct_substantive_finding_ids",
                 "provisional_sources": "github_source_candidates",
                 "inspections": "github_inspection_entries",
                 "unknown_source_refs": "unknown_source_refs",
                 "metadata_collisions": "source_metadata_collisions",
                 "detached_inspections": "detached_original_inspection_rows_replayed",
                 "unresolved_index_only": "github_index_only_refs_unresolved"}
    require(all(ledger.get("replay_counts", {}).get(lk) ==
                m.get("staged_counts", {}).get(mk) for lk, mk in count_map.items()),
            "ledger staged counts")
    integrity = ledger.get("integrity", {})
    require(integrity.get("sqlite_integrity") == "ok"
            and integrity.get("foreign_key_violations") == 0
            and integrity.get("canonical_rows_unchanged") is True
            and integrity.get("canonical_tables_preserved") == 88
            and ledger.get("changed_paths_entirely_research") is True
            and ledger.get("publication_approved") is False
            and ledger.get("ready_for_editorial_review") is False
            and ledger.get("blockers"),
            "ledger publication guard")
