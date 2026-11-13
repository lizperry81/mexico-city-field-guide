#!/usr/bin/env python3
"""Guard research handoff against accidental editorial publication or unsafe paths."""
import copy
import json
from pathlib import Path

from check_research_handoff import OUT, safe_path, validate_versioned_handoff
from editorial_passage_inventory import HistoryPassages

for unsafe in ("../site/index.html", "research/../../site/index.html",
               "/research/handoff/manifest.json", r"research\..\site"):
    try:
        safe_path(unsafe)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe handoff path accepted: " + unsafe)
assert safe_path("research/audits/valid.json") == "research/audits/valid.json"
assert (safe_path(".github/workflows/research-replay-staging.yml") ==
        ".github/workflows/research-replay-staging.yml")
for unsafe_workflow in (".github/workflows/pages.yml",
                        ".github/workflows/../deploy.yml", "site/index.html"):
    try:
        safe_path(unsafe_workflow)
    except ValueError:
        pass
    else:
        raise AssertionError("Non-research path accepted: " + unsafe_workflow)

# The 69-batch handoff is a different v4 schema. Its pinned immutable
# history can be accepted for PRIVATE review only when every source delta,
# replay identity and unpublished evidence restriction matches.
batch_manifest = {
    "schema_version": 4, "handoff_history_append_only": True,
    "immutable_handoff_blob_sha": "a" * 40,
    "research_commit_sha": "b" * 40, "canonical_version": "V97",
    "canonical_hash": "c" * 64, "previous_manifest_blob_sha": "d" * 40,
    "previous_manifest_generated_at": "2026-11-13T16:13:18Z",
    "canonical_status": "unchanged_provisional_V97_not_promoted",
    "canonical_promoted": False, "ready_for_editorial_review": False,
    "ready_for_publication": False, "compressed_sha256": "e" * 64,
    "versioned_research_sha256": "f" * 64,
    "replay_report_path": "research/reconciled/v4_69/replay_report.json",
    "versioned_research_sqlite_gz_path": "research/reconciled/v4_69/research_only.sqlite.gz",
    "canonical": {"sources": 616, "claims": 422, "claim_source_links": 403,
                  "findings": 68, "source_inspections": 9},
    "staged_counts": {
        "github_batches_replayed": 69,
        "github_distinct_substantive_finding_ids": 375,
        "github_source_candidates": 124, "github_inspection_entries": 162,
        "unknown_source_refs": 1, "source_metadata_collisions": 2,
        "new_historical_finding_candidates_this_run": 9,
        "new_source_inspection_metadata_this_run": 4,
        "source_id_provisional_recoveries_this_run": 3,
        "new_scholarly_source_candidate_records_this_run": 1,
    },
    "replay_evidence": {
        "integrity": "ok", "foreign_key_violations": 0,
        "original_tables_preserved": 88, "canonical_rows_unchanged": True,
        "github_readback_verified": True,
        "github_replay_report_blob_sha": "1" * 40,
        "github_replay_binary_blob_sha": "2" * 40,
    },
    "evidence_status": {
        "ready_for_editorial_review": False, "publication_approved": False,
        "independently_corroborated_new_findings": 0,
    },
    "blockers": ["Original photographs and rights not independently checked"],
    "reconciliation_artifact_paths": ["research/ledgers/69.json"],
    "research_batch_artifact_paths": ["research/batches/69.json"],
    "chapter_audit_artifact_paths": ["research/audits/templo-69.json"],
    "coverage_artifact_paths": ["research/coverage/69.json"],
}
batch_snapshot = {
    "schema_version": 4, "kind": "immutable_research_batch_handoff",
    "branch": "research-persistence",
    "research_commit_sha": batch_manifest["research_commit_sha"],
    "canonical_version": "V97", "canonical_hash": batch_manifest["canonical_hash"],
    "previous_manifest_blob_sha": batch_manifest["previous_manifest_blob_sha"],
    "canonical_status": batch_manifest["canonical_status"],
    "canonical_promoted": False, "ready_for_publication": False,
    "ready_for_editorial_review": False, "main_modified": False,
    "compressed_sha256": batch_manifest["compressed_sha256"],
    "versioned_research_sha256": batch_manifest["versioned_research_sha256"],
    "versioned_research_sqlite_gz_path": batch_manifest["versioned_research_sqlite_gz_path"],
    "replay_report_path": batch_manifest["replay_report_path"],
    "replay_report_git_blob_sha": "1" * 40,
    "replay_binary_git_blob_sha": "2" * 40,
    "canonical_counts": copy.deepcopy(batch_manifest["canonical"]),
    "baseline_counts": {"batches": 68, "assertion_bearing_findings": 366,
                        "source_candidates": 120, "source_inspection_metadata": 158,
                        "unregistered_source_ids": 4, "metadata_collisions": 2},
    "staged_counts": {"batches": 69, "assertion_bearing_findings": 375,
                      "source_candidates": 124, "source_inspection_metadata": 162,
                      "unregistered_source_ids": 1, "metadata_collisions": 2},
    "new_candidate_findings": 9, "new_inspection_metadata": 4,
    "new_source_candidate_records": 1, "new_provisional_source_id_resolutions": 3,
    "verification": {
        "sqlite_integrity": "ok", "foreign_key_violations": 0,
        "all_88_original_tables_preserved": True,
        "canonical_rows_unchanged": True, "versioned_db_git_readback": True,
        "report_git_readback": True,
        "github_replay_workflow_internal_persisted_sha256_check": True,
    },
    "evidence_status": {
        "ready_for_editorial_review": False, "publication_approved": False,
        "new_findings_are": "source_linked_provisional_uncorroborated",
        "original_historical_photographs_examined": False,
        "source_photo_rights_cleared": False,
    },
    "blockers": copy.deepcopy(batch_manifest["blockers"]),
    "reconciliation_artifact_paths": copy.deepcopy(batch_manifest["reconciliation_artifact_paths"]),
    "research_batch_artifact_paths": copy.deepcopy(batch_manifest["research_batch_artifact_paths"]),
    "chapter_audit_artifact_paths": copy.deepcopy(batch_manifest["chapter_audit_artifact_paths"]),
    "coverage_artifact_paths": copy.deepcopy(batch_manifest["coverage_artifact_paths"]),
}
validate_versioned_handoff(batch_manifest, batch_snapshot, "a" * 40)
mutations = (
    ("immutable blob", {"immutable_handoff_blob_sha": "9" * 40}, None),
    ("staged batch", {"staged_counts": dict(batch_manifest["staged_counts"],
                                          github_batches_replayed=70)}, None),
    ("staged source count", {"staged_counts": dict(batch_manifest["staged_counts"],
                                                github_source_candidates=126)}, None),
    ("false approval", {"ready_for_publication": True}, None),
    ("reader audit path", {"chapter_audit_artifact_paths": []}, None),
    ("historical blockers", {"blockers": []}, None),
    ("new findings delta", None, {"new_candidate_findings": 8}),
    ("recovered source identity", None, {"new_provisional_source_id_resolutions": 4}),
    ("photo permissions", None, {"evidence_status": dict(
        batch_snapshot["evidence_status"], source_photo_rights_cleared=True)}),
    ("Git readback", None, {"replay_report_git_blob_sha": "9" * 40}),
    ("metadata collisions", None, {"baseline_counts": dict(
        batch_snapshot["baseline_counts"], metadata_collisions=0)}),
    ("database integrity", None, {"verification": dict(
        batch_snapshot["verification"], canonical_rows_unchanged=False)}),
    ("new audit missing", None, {"chapter_audit_artifact_paths": ["research/audits/fake.json"]}),
)
for label, manifest_patch, snapshot_patch in mutations:
    modified_manifest, modified_snapshot = copy.deepcopy(batch_manifest), copy.deepcopy(batch_snapshot)
    if manifest_patch:
        modified_manifest.update(manifest_patch)
    if snapshot_patch:
        modified_snapshot.update(snapshot_patch)
    try:
        validate_versioned_handoff(modified_manifest, modified_snapshot, "a" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Immutable v4 batch mutation accepted: " + label)

# Schema v2 requires exact equality; v3 has two historically valid provenance
# formats; v4 requires the complete immutable record, including audit flags.
snap = {"schema_version": 3, "kind": "research_to_app_handoff",
        "research_commit_sha": "a" * 40, "ready_for_publication": False,
        "chapter_audit_artifact_paths": ["research/audits/valid.json"]}
v3 = dict(snap, immutable_handoff_snapshot_sha="b" * 40,
          previous_manifest_blob_sha="c" * 40,
          previous_manifest_generated_at="2026-11-13T03:14:04Z",
          handoff_history_append_only=True)
validate_versioned_handoff(v3, snap, "b" * 40)

# The latest research handoff has inline provenance: its immutable historical
# file is byte-identical to the moving manifest, without a separate snapshot
# SHA. Validate it without accepting altered or missing fields.
inline_v3 = dict(snap, previous_manifest_blob_sha="c" * 40,
                 previous_manifest_generated_at="2026-11-13T04:14:00Z",
                 handoff_history_append_only=True)
validate_versioned_handoff(inline_v3, copy.deepcopy(inline_v3), "d" * 40)

v4 = dict(inline_v3, schema_version=4, canonical_status="unchanged_provisional_V97_not_promoted",
          staged_counts={"github_batches_replayed": 58, "unknown_source_refs": 22},
          evidence_status={"publication_approved": False})
validate_versioned_handoff(v4, copy.deepcopy(v4), "d" * 40)

# A frozen v4 handoff may be followed by exactly two Git provenance fields.
# This must not become a permissive schema fallback: EVERY earlier field,
# including historical evidence flags and staged counts, must remain identical.
frozen = dict(v4,
              canonical_promoted=False, ready_for_publication=False,
              ready_for_editorial_review=False,
              replay_evidence={"integrity": "ok", "foreign_key_violations": 0,
                               "canonical_rows_unchanged": True,
                               "github_readback_verified": True})
with_provenance = dict(frozen, immutable_handoff_blob_sha="d" * 40,
                       handoff_history_commit_sha="e" * 40)
validate_versioned_handoff(with_provenance, copy.deepcopy(frozen), "d" * 40)
for tampered in (
    dict(with_provenance, immutable_handoff_blob_sha="a" * 40),
    dict(with_provenance, ready_for_publication=True),
    dict(with_provenance, canonical_promoted=True),
    dict(with_provenance, evidence_status={"publication_approved": True}),
    dict(with_provenance, staged_counts={"github_batches_replayed": 999}),
    dict(with_provenance, unknown_approval="allowed"),
):
    try:
        validate_versioned_handoff(tampered, frozen, "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Tampered frozen v4 handoff was accepted")
altered_archive = copy.deepcopy(frozen)
altered_archive["staged_counts"]["github_batches_replayed"] = 999
try:
    validate_versioned_handoff(with_provenance, altered_archive, "d" * 40)
except ValueError:
    pass
else:
    raise AssertionError("Edited frozen v4 staged counts were accepted")

# New research handoffs anchor immutable verified-replay metadata rather than
# copying the moving manifest. All critical identities, counts and audit paths
# must still be pinned, and approval can never be inferred from staging.
v4_replay = dict(v4,
                 research_commit_sha="a" * 40,
                 canonical_hash="b" * 64,
                 canonical_version="V97",
                 versioned_research_sqlite_gz_path="research/reconciled/v4_a/research_only.sqlite.gz",
                 versioned_research_sha256="c" * 64,
                 compressed_sha256="d" * 64,
                 replay_report_path="research/reconciled/v4_a/replay_report.json",
                 previous_manifest_blob_sha="c" * 40,
                 previous_manifest_generated_at="2026-11-13T04:14:00Z",
                 ready_for_editorial_review=False,
                 canonical_promoted=False,
                 staged_counts={
                     "github_batches_replayed": 58,
                     "github_distinct_substantive_finding_ids": 300,
                     "github_inspection_entries": 84,
                     "github_source_candidates": 66,
                     "unknown_source_refs": 14,
                     "source_metadata_collisions": 2,
                     "github_index_only_refs_unresolved": 16,
                     "detached_local_inspections_not_reconciled": 37,
                 },
                 chapter_audit_artifact_paths=["research/audits/base.json",
                                               "research/audits/addendum.json"],
                 coverage_artifact_paths=["research/coverage/one.json"])
immutable_replay = {
    "kind": "verified_replay_after_schema_unit_tests",
    "research_commit_sha": v4_replay["research_commit_sha"],
    "canonical_hash": v4_replay["canonical_hash"],
    "canonical_version": "V97",
    "canonical_status": "unchanged_not_promoted",
    "canonical_rows_unchanged": True,
    "versioned_research_sqlite_gz_path": v4_replay["versioned_research_sqlite_gz_path"],
    "versioned_research_sha256": v4_replay["versioned_research_sha256"],
    "compressed_sha256": v4_replay["compressed_sha256"],
    "replay_report_path": v4_replay["replay_report_path"],
    "previous_manifest_blob_sha": v4_replay["previous_manifest_blob_sha"],
    "previous_manifest_generated_at": v4_replay["previous_manifest_generated_at"],
    "ready_for_editorial_review": False,
    "canonical_promoted": False,
    "publication_approved": False,
    "integrity": "ok",
    "foreign_key_violations": 0,
    "unit_tests_path": "research/pipeline/test_reconcile_batch_schemas.py",
    "workflow_path": ".github/workflows/research-replay-staging.yml",
    "chapter_audit_artifact_paths": ["research/audits/base.json"],
    "coverage_artifact_paths": ["research/coverage/one.json"],
    "staged_counts": {
        "github_batches_replayed": 58,
        "github_distinct_substantive_finding_ids": 300,
        "github_inspection_metadata_entries": 84,
        "candidate_source_identities": 66,
        "unresolved_source_refs": 14,
        "source_metadata_collisions": 2,
        "unresolved_index_only_refs": 16,
        "detached_inspections_not_in_github_replay": 37,
    }
}
validate_versioned_handoff(v4_replay, immutable_replay, "d" * 40)
# Schema v4 append-only snapshots require identity, before/after count and
# evidence-status agreement; none of their proposed citations are approved.
v4_append = dict(v4_replay,
                 verified_replay_commit_sha="e" * 40,
                 research_batch_artifact_paths=["research/batches/new.json"])
append_snapshot = {
    "schema_version": 4,
    "kind": "append_only_research_handoff_snapshot",
    "research_branch": "research-persistence",
    "research_commit_sha": v4_append["research_commit_sha"],
    "batch_commit_sha": "f" * 40,
    "verified_replay_commit_sha": v4_append["verified_replay_commit_sha"],
    "canonical_version": "V97",
    "canonical_hash": v4_append["canonical_hash"],
    "canonical_status": "unchanged_not_promoted",
    "canonical_counts": {"sources": 616, "claims": 422},
    "versioned_research_sqlite_gz_path": v4_append["versioned_research_sqlite_gz_path"],
    "versioned_research_sha256": v4_append["versioned_research_sha256"],
    "compressed_sha256": v4_append["compressed_sha256"],
    "replay_report_path": v4_append["replay_report_path"],
    "before": {"batches": 59, "staged_finding_ids_with_assertions": 300,
               "inspection_metadata_entries": 121, "source_candidate_ids": 66},
    "after": {"batches": 60, "staged_finding_ids_with_assertions": 316,
              "inspection_metadata_entries": 122, "source_candidate_ids": 75,
              "unknown_source_refs": 14, "source_metadata_collisions": 2,
              "unresolved_index_only_ids": 6},
    "evidence_status": {"previously_staged_full_assertions_restored": 10,
                        "new_source_linked_candidate_findings": 6,
                        "new_public_html_catalogue_inspections": 1,
                        "independently_corroborated_new_claims": 0,
                        "publication_approved": False,
                        "ready_for_editorial_review": False},
    "chapter_audit_artifact_paths": ["research/audits/new.json"],
    "coverage_artifact_paths": ["research/coverage/new.json"],
    "research_batch_artifact_paths": ["research/batches/new.json"],
}
v4_append["canonical"] = {"sources": 616, "claims": 422}
v4_append["staged_counts"] = {
    **v4_append["staged_counts"],
    "github_batches_replayed": 60,
    "github_distinct_substantive_finding_ids": 316,
    "github_inspection_entries": 122,
    "github_source_candidates": 75,
    "github_index_only_refs_unresolved": 6,
}
v4_append["evidence_status"] = {
    "restored_prior_staged_findings_this_run": 10,
    "new_historical_finding_candidates_researched_this_run": 6,
    "new_public_institutional_html_source_inspections_this_run": 1,
    "independently_corroborated_new_findings": 0,
    "ready_for_editorial_review": False, "publication_approved": False,
}
v4_append["chapter_audit_artifact_paths"].append("research/audits/new.json")
v4_append["coverage_artifact_paths"].append("research/coverage/new.json")
validate_versioned_handoff(v4_append, append_snapshot, "d" * 40)

# The November 13 research producer moved database provenance into a nested
# object and renamed its before/after metrics. This is a different immutable
# encoding; a changed checksum, source count, or false approval must be blocked.
v4_nested = copy.deepcopy(v4_append)
v4_nested["canonical"] = {
    "sources": 616, "claims": 422, "claim_source_links": 403,
    "findings": 68, "source_inspections": 9,
}
v4_nested["staged_counts"].update({
    "github_batches_replayed": 61,
    "github_distinct_substantive_finding_ids": 329,
    "github_inspection_entries": 126,
    "github_source_candidates": 79,
    "unknown_source_refs": 14,
    "source_metadata_collisions": 2,
    "github_index_only_refs_unresolved": 1,
})
v4_nested["evidence_status"].update({
    "new_historical_finding_candidates_researched_this_run": 8,
    "new_public_institutional_html_source_inspections_this_run": 2,
})
v4_nested["reconciliation_artifact_paths"] = ["research/reconciled/new.json"]
nested_snapshot = {
    "schema_version": 4,
    "kind": "append_only_research_handoff_snapshot",
    "research_branch": "research-persistence",
    "research_commit_sha": v4_nested["research_commit_sha"],
    "pipeline_fix_commit_sha": "f" * 40,
    "verified_replay_commit_sha": v4_nested["verified_replay_commit_sha"],
    "canonical_version": "V97",
    "canonical_hash": v4_nested["canonical_hash"],
    "canonical_status": "unchanged_not_promoted",
    "canonical_counts": copy.deepcopy(v4_nested["canonical"]),
    "before": {
        "github_batch_files": 60, "assertion_bearing_staged_finding_ids": 316,
        "inspection_metadata": 122, "source_candidate_ids": 75,
        "index_only_unresolved": 6, "unresolved_source_ids": 14,
        "source_metadata_collisions": 2,
    },
    "after": {
        "github_batch_files": 61, "assertion_bearing_staged_finding_ids": 329,
        "inspection_metadata": 126, "source_candidate_ids": 79,
        "index_only_unresolved": 1, "unresolved_source_ids": 14,
        "source_metadata_collisions": 2,
    },
    "changes": {
        "legacy_TE28_findings_reclassified_from_index_only_to_substantive": 5,
        "new_historical_finding_candidates": 8,
        "new_source_candidates": 4,
        "new_inspection_metadata_entries": 4,
    },
    "database": {
        "sqlite_gz": v4_nested["versioned_research_sqlite_gz_path"],
        "replay_report": v4_nested["replay_report_path"],
        "compressed_sha256": v4_nested["compressed_sha256"],
        "sqlite_sha256": v4_nested["versioned_research_sha256"],
        "integrity": "ok", "foreign_key_violations": 0,
        "original_V97_tables_preserved": 88,
        "canonical_rows_unchanged": True,
    },
    "evidence_status": {
        "publication_approved": False, "ready_for_editorial_review": False,
        "full_public_institutional_html_pages_examined_this_run": 2,
        "independently_corroborated_new_findings": 0,
    },
    "canonical_promoted": False, "publication_approved": False,
    "ready_for_editorial_review": False,
    "chapter_audit_artifact_paths": ["research/audits/new.json"],
    "coverage_artifact_paths": ["research/coverage/new.json"],
    "research_batch_artifact_paths": ["research/batches/new.json"],
    "reconciliation_artifact_paths": ["research/reconciled/new.json"],
}
validate_versioned_handoff(v4_nested, nested_snapshot, "d" * 40)
# Latest 1985 legal/architecture research uses a separate immutable v4 record.
# Matching source claims and audit paths are insufficient if its Git blob SHA
# disagrees with the rolling pointer. The bad snapshot must remain unpublished.
legal_manifest = copy.deepcopy(v4_nested)
legal_manifest.update({
    "canonical_status": "unchanged_provisional_V97_not_promoted",
    "immutable_handoff_blob_sha": "d" * 40,
    "canonical_promoted": False,
    "ready_for_editorial_review": False,
    "ready_for_publication": False,
    "replay_evidence": {
        "integrity": "ok", "foreign_key_violations": 0,
        "canonical_rows_unchanged": True, "github_readback_verified": True,
    },
    "blockers": ["Original image annexes not examined"],
    "reconciliation_artifact_paths": [
        "research/reconciled/new.json", "research/ledgers/legal-inventory.json",
    ],
})
legal_manifest["evidence_status"]["ready_for_editorial_review"] = False
legal_manifest["evidence_status"]["publication_approved"] = False
legal_shared = (
    "schema_version", "research_commit_sha", "verified_replay_commit_sha",
    "previous_manifest_blob_sha", "previous_manifest_generated_at",
    "canonical_version", "canonical_hash", "canonical_status", "canonical",
    "staged_counts", "versioned_research_sqlite_gz_path",
    "versioned_research_sha256", "compressed_sha256", "replay_report_path",
    "evidence_status", "replay_evidence", "ready_for_editorial_review",
    "ready_for_publication", "blockers",
)
legal_immutable = {key: copy.deepcopy(legal_manifest[key]) for key in legal_shared}
legal_immutable.update({
    "kind": "immutable_research_to_app_handoff",
    "source_audit_paths": ["research/audits/new.json"],
    "chapter_audit_artifact_paths": ["research/audits/new.json"],
    "coverage_artifact_paths": ["research/coverage/new.json"],
    "batch_artifact_paths": ["research/batches/new.json"],
    "inventory_path": "research/ledgers/legal-inventory.json",
})
validate_versioned_handoff(legal_manifest, legal_immutable, "d" * 40)
for mutated_manifest, mutated_immutable, actual_blob in (
    (dict(legal_manifest, immutable_handoff_blob_sha="a" * 40),
     legal_immutable, "d" * 40),
    (legal_manifest,
     dict(legal_immutable, staged_counts={"github_batches_replayed": 999}),
     "d" * 40),
    (legal_manifest,
     dict(legal_immutable, ready_for_publication=True), "d" * 40),
    (legal_manifest,
     dict(legal_immutable, source_audit_paths=["research/audits/unknown.json"]),
     "d" * 40),
    (legal_manifest,
     dict(legal_immutable, inventory_path="research/ledgers/unknown.json"),
     "d" * 40),
):
    try:
        validate_versioned_handoff(mutated_manifest, mutated_immutable, actual_blob)
    except ValueError:
        pass
    else:
        raise AssertionError("Tampered immutable legal research handoff was accepted")

for mutation in (
    {"canonical_counts": dict(nested_snapshot["canonical_counts"], sources=617)},
    {"canonical_promoted": True},
    {"ready_for_editorial_review": True},
    {"database": dict(nested_snapshot["database"], integrity="corrupt")},
    {"database": dict(nested_snapshot["database"], sqlite_sha256="0" * 64)},
    {"after": dict(nested_snapshot["after"], source_candidate_ids=80)},
    {"changes": dict(nested_snapshot["changes"], new_historical_finding_candidates=9)},
    {"evidence_status": dict(nested_snapshot["evidence_status"], publication_approved=True)},
    {"coverage_artifact_paths": ["research/coverage/unknown.json"]},
):
    try:
        validate_versioned_handoff(
            v4_nested, dict(nested_snapshot, **mutation), "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe nested v4 snapshot accepted: " + str(mutation))
for mutation in (
    {"canonical_hash": "f" * 64},
    {"verified_replay_commit_sha": "0" * 40},
    {"canonical_counts": {"sources": 617, "claims": 422}},
    {"after": dict(append_snapshot["after"], unresolved_index_only_ids=7)},
    {"evidence_status": dict(append_snapshot["evidence_status"],
                             publication_approved=True)},
    {"chapter_audit_artifact_paths": ["research/audits/unseen.json"]},
    {"research_batch_artifact_paths": ["research/batches/missing.json"]},
):
    try:
        validate_versioned_handoff(v4_append, dict(append_snapshot, **mutation), "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unbound append-only v4 handoff accepted: " + str(mutation))

for mutation in (
    {"canonical_hash": "f" * 64},
    {"publication_approved": True},
    {"integrity": "corrupt"},
    {"chapter_audit_artifact_paths": ["research/audits/not-in-handoff.json"]},
    {"staged_counts": dict(immutable_replay["staged_counts"],
                           unresolved_source_refs=15)},
):
    try:
        validate_versioned_handoff(
            v4_replay, dict(immutable_replay, **mutation), "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Modified immutable replay was trusted: " + str(mutation))
for altered, immutable in (
    (dict(v4, ready_for_publication=True), v4),
    (dict(v4, staged_counts={"github_batches_replayed": 59}), v4),
    (dict(v4, previous_manifest_generated_at="2026-11-13T06:58:00Z"), v4),
    (dict(v4, immutable_handoff_snapshot_sha="d" * 40), v4),
    (v4, dict(v4, evidence_status={"publication_approved": True})),
    (v4, dict(v4, changed_after_commit=True)),
):
    try:
        validate_versioned_handoff(altered, immutable, "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unbound or changed v4 research handoff accepted")
for invalid_manifest, invalid_history in (
    (dict(inline_v3, handoff_history_append_only=False), inline_v3),
    (dict(inline_v3, previous_manifest_blob_sha="not-a-sha"), inline_v3),
    (dict(inline_v3, ready_for_publication=True), inline_v3),
    (inline_v3, dict(inline_v3, rogue_field=True)),
    (dict(inline_v3, unreviewed_extra=True), inline_v3),
):
    try:
        validate_versioned_handoff(invalid_manifest, invalid_history, "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Altered inline v3 handoff was accepted")
v2 = {"schema_version": 2, "kind": "research_to_app_handoff"}
validate_versioned_handoff(v2, v2, "")
for changed, old_snapshot, actual_blob in (
    (dict(v3, immutable_handoff_snapshot_sha="d" * 40), snap, "b" * 40),
    (dict(v3, handoff_history_append_only=False), snap, "b" * 40),
    (dict(v3, previous_manifest_blob_sha="invalid"), snap, "b" * 40),
    (v3, dict(snap, research_commit_sha="e" * 40), "b" * 40),
    (v3, dict(snap, rogue_new_field=True), "b" * 40),
    (dict(v3, new_unreviewed_field=True), snap, "b" * 40),
):
    try:
        validate_versioned_handoff(changed, old_snapshot, actual_blob)
    except ValueError:
        pass
    else:
        raise AssertionError("Drift or invalid v3 handoff provenance went undetected")
try:
    validate_versioned_handoff(v2, dict(v2, extra="changed"), "")
except ValueError:
    pass
else:
    raise AssertionError("v2 immutable snapshot drift went undetected")



# The newest producer publishes a compact verified *history* record rather
# than the older append-only database object. Pin its counts, evidence audit,
# paths, readback metadata and explicitly unapproved status.
history_manifest = copy.deepcopy(v4_nested)
history_manifest["staged_counts"].update({
    "github_batches_replayed": 62,
    "github_distinct_substantive_finding_ids": 336,
    "github_inspection_entries": 131,
    "github_source_candidates": 84,
    "unknown_source_refs": 14,
    "source_metadata_collisions": 2,
    "github_index_only_refs_unresolved": 1,
})
history_manifest["evidence_status"].update({
    "new_historical_finding_candidates_researched_this_run": 7,
    "new_source_candidate_records_this_run": 5,
    "new_source_inspection_metadata_this_run": 5,
    "ready_for_editorial_review": False, "publication_approved": False,
})
history_manifest["ready_for_publication"] = False
history_manifest["ready_for_editorial_review"] = False
history_manifest["blockers"] = ["Unresolved Gamio dating/source comparison"]
history_manifest["research_batch_artifact_paths"].append("research/batches/last.json")
history_manifest["reconciliation_artifact_paths"].extend([
    "research/ledgers/history.json", "research/reconciled/compressed_sha256.txt"])
history_snapshot = {
    "schema_version": 4, "kind": "verified_research_to_app_handoff_history",
    "generated_at": "2026-11-13T11:07:00Z",
    "research_commit_sha": history_manifest["research_commit_sha"],
    "replay_persistence_commit_sha": history_manifest["verified_replay_commit_sha"],
    "previous_manifest_sha": history_manifest["previous_manifest_blob_sha"],
    "canonical_version": "V97", "canonical_hash": history_manifest["canonical_hash"],
    "canonical_status": "unchanged_not_promoted",
    "canonical_counts": {
        "sources": 616, "claims": 422, "claim_sources": 403,
        "canonical_findings": 68, "canonical_source_inspections": 9,
    },
    "staged_counts": {
        "research_batches": 62, "assertion_bearing_finding_ids": 336,
        "inspection_metadata_entries": 131, "source_candidate_identities": 84,
        "unresolved_source_refs": 14, "source_metadata_collisions": 2,
        "index_only_unresolved": 1,
    },
    "previous_counts": {
        "research_batches": 61, "assertion_bearing_finding_ids": 329,
        "inspection_metadata_entries": 126, "source_candidate_identities": 79,
    },
    "artifact_paths": {
        "batch": "research/batches/last.json",
        "audit": "research/audits/new.json",
        "coverage": "research/coverage/new.json",
        "ledger": "research/ledgers/history.json",
        "report": history_manifest["replay_report_path"],
        "sqlite": history_manifest["versioned_research_sqlite_gz_path"],
        "compressed_sha": "research/reconciled/compressed_sha256.txt",
    },
    "uncompressed_sqlite_sha256": history_manifest["versioned_research_sha256"],
    "compressed_sha256": history_manifest["compressed_sha256"],
    "verification": {
        "sqlite_integrity": "ok", "foreign_key_violations": 0,
        "canonical_rows_unchanged": True, "canonical_tables_preserved": 88,
        "github_readback": {
            "replay_report_blob_sha": "a" * 40,
            "compressed_sha_file_blob_sha": "b" * 40,
        },
        "github_actions_run":
            "https://github.com/lizperry81/mexico-city-field-guide/actions/runs/123",
        "github_actions_conclusion": "success",
    },
    "historical_evidence": {
        "new_findings": 7, "new_source_candidates": 5,
        "new_inspection_metadata": 5,
        "source_access": "Publisher PDF text and institutional HTML, not originals",
        "editorial_conflict": "Gamio chronology 1913 versus 1914",
        "chapter_audit_artifact_paths": ["research/audits/new.json"],
        "coverage_artifact_paths": ["research/coverage/new.json"],
        "ready_for_editorial_review": False, "ready_for_publication": False,
    },
    "blockers": copy.deepcopy(history_manifest["blockers"]),
    "publication_approved": False, "canonical_promoted": False,
    "main_modified": False,
}
history_manifest["canonical"] = {
    "sources": 616, "claims": 422, "claim_source_links": 403,
    "findings": 68, "source_inspections": 9,
}
validate_versioned_handoff(history_manifest, history_snapshot, "d" * 40)
for mutation in (
    {"research_commit_sha": "e" * 40},
    {"previous_manifest_sha": "f" * 40},
    {"staged_counts": dict(history_snapshot["staged_counts"], source_candidate_identities=85)},
    {"previous_counts": dict(history_snapshot["previous_counts"],
                             assertion_bearing_finding_ids=340)},
    {"historical_evidence": dict(history_snapshot["historical_evidence"],
                                  new_findings=9)},
    {"artifact_paths": dict(history_snapshot["artifact_paths"],
                             audit="research/audits/not-checked.json")},
    {"verification": dict(history_snapshot["verification"],
                           github_actions_conclusion="failure")},
    {"verification": dict(history_snapshot["verification"],
                           canonical_rows_unchanged=False)},
    {"canonical_counts": dict(history_snapshot["canonical_counts"], sources=617)},
    {"publication_approved": True},
    {"main_modified": True},
    {"blockers": []},
):
    try:
        validate_versioned_handoff(
            history_manifest, dict(history_snapshot, **mutation), "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unbound v4 history handoff accepted: " + str(mutation))


# The 12:15 UTC producer handoff pins the delta for 1847 research; only
# privately staged review material may be consumed by the application build.
cross_manifest = copy.deepcopy(history_manifest)
cross_manifest["staged_counts"].update({
    "github_batches_replayed": 63, "github_distinct_substantive_finding_ids": 342,
    "github_inspection_entries": 137, "github_source_candidates": 89,
    "unknown_source_refs": 14,
})
cross_manifest["evidence_status"].update({
    "new_historical_finding_candidates_researched_this_run": 6,
    "new_source_candidate_records_this_run": 5,
    "new_source_inspection_metadata_this_run": 6,
    "independently_corroborated_new_findings": 0,
})
cross_manifest["source_identity_crosswalk_path"] = "research/ledgers/crosswalk.json"
cross_manifest["research_batch_artifact_paths"].append("research/batches/1847.json")
cross_manifest["coverage_artifact_paths"].append("research/coverage/1847.json")
cross_snapshot = {
    "schema_version": 4, "kind": "immutable_cross_automation_research_handoff",
    "research_commit_sha": cross_manifest["research_commit_sha"],
    "original_research_batch_commit_sha": "f" * 40,
    "verified_replay_commit_sha": cross_manifest["verified_replay_commit_sha"],
    "canonical_version": cross_manifest["canonical_version"],
    "canonical_hash": cross_manifest["canonical_hash"],
    "canonical_status": "unchanged",
    "before": {"batch_files": 62, "staged_substantive_findings": 336,
               "inspection_metadata_rows": 131, "source_candidates": 84,
               "missing_registered_sources": 14},
    "after": {"batch_files": 63, "staged_substantive_findings": 342,
              "inspection_metadata_rows": 137, "source_candidates": 89,
              "missing_registered_sources": 14},
    "versioned_sqlite_gz_path": cross_manifest["versioned_research_sqlite_gz_path"],
    "versioned_sqlite_sha256": cross_manifest["versioned_research_sha256"],
    "compressed_sha256": cross_manifest["compressed_sha256"],
    "verified_replay_report_path": cross_manifest["replay_report_path"],
    "reconciliation_ledger_path": cross_manifest["source_identity_crosswalk_path"],
    "new_findings_staged": 6, "new_inspection_metadata": 6,
    "independent_corroborations": 0,
    "previous_manifest_blob_sha": cross_manifest["previous_manifest_blob_sha"],
    "replay_workflow_url":
        "https://github.com/lizperry81/mexico-city-field-guide/actions/runs/123",
    "research_batch_artifact_paths": ["research/batches/1847.json"],
    "coverage_artifact_paths": ["research/coverage/1847.json"],
    "chapter_audit_artifact_paths": ["research/audits/new.json"],
    "ready_for_publication": False, "ready_for_editorial_review": False,
}
validate_versioned_handoff(cross_manifest, cross_snapshot, "d" * 40)
for mutation in (
    {"canonical_hash": "0" * 64},
    {"ready_for_publication": True},
    {"ready_for_editorial_review": True},
    {"after": dict(cross_snapshot["after"], staged_substantive_findings=343)},
    {"before": dict(cross_snapshot["before"], source_candidates=83)},
    {"new_findings_staged": 7},
    {"independent_corroborations": 1},
    {"reconciliation_ledger_path": "research/ledgers/unbound.json"},
    {"research_batch_artifact_paths": ["research/batches/unverified.json"]},
    {"original_research_batch_commit_sha": "invalid"},
    {"replay_workflow_url": "https://example.invalid/claim"},
):
    try:
        validate_versioned_handoff(
            cross_manifest, dict(cross_snapshot, **mutation), "d" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe cross-automation v4 replay was trusted: " + str(mutation))


report = json.loads((OUT / "handoff-report.json").read_text(encoding="utf-8"))
assert report["ready_for_publication"] is False
if report["status"] == "no_verified_handoff":
    assert not (OUT / "editorial-review-queue.json").exists()
    assert not (OUT / "editorial-passage-inventory.json").exists()
    print("PASS: unverified handoff is blocked and has no editorial queue")
else:
    assert report["status"] == "verified_handoff_not_approved"
    assert len(report["research_commit_sha"]) == 40
    assert report["handoff_schema_version"] in (2, 3, 4)
    assert len(report["handoff_manifest_commit_sha"]) == 40
    if any(x["group"] == "versioned_research_sqlite_gz_path"
           for x in report["artifact_checks"]):
        assert report["handoff_schema_version"] in (3, 4)
    assert report["immutable_handoff_path"].startswith("research/handoff/history/")
    assert len(report["immutable_handoff_blob_sha"]) == 40
    assert not report["canonical_promoted"]
    assert report["artifact_checks"]
    assert report["chapter_audit_artifact_paths"]
    assert report["coverage_artifact_paths"]
    if report["handoff_schema_version"] == 4:
        staged = report["staged_reconciliation"]
        assert staged["status"] == "verified_staged_not_canonical_or_editorially_approved"
        assert staged["github_batches_replayed"] > 0
        assert staged["candidate_finding_ids"] >= 0
        assert staged["unresolved_index_only_refs"] >= 0
        assert staged["unresolved_source_refs"] >= 0
        assert staged["source_metadata_collisions"] >= 0
        assert staged["semantic_join_verified"] is False
        assert isinstance(report["research_ready_for_editorial_review"], bool)
        assert isinstance(report["audit_ready_for_editorial_review"], bool)
        assert not report["ready_for_publication"]
        assert len(report["chapter_audit_artifact_paths"]) >= 2
    queue = json.loads((OUT / "editorial-review-queue.json").read_text(encoding="utf-8"))
    assert queue["research_commit_sha"] == report["research_commit_sha"]
    assert queue["status"] == "human_review_required_not_for_publication"
    assert len(queue["items"]) == report["review_queue_count"]
    assert report["audit_documents_reviewed"] >= 1
    assert report["coverage_gap_review_count"] == len(queue["coverage_gaps"])
    for gap in queue["coverage_gaps"]:
        assert gap["coverage_path"].startswith("research/coverage/")
        assert gap["explanation"]
        assert gap["readiness"]
        assert gap["research_needed"] is None or isinstance(gap["research_needed"], str)
        assert gap["assigned_to_published_chapter"] is None
        assert gap["publication_authorization"] is False
    assert report["historical_discrepancies_pending_review"] == len(
        queue["unresolved_historical_discrepancies"])
    assert len({item["audit_path"] for item in queue["items"]}) == report["audit_documents_reviewed"]
    assert len({(item["audit_path"], item["audit_claim_id"])
                for item in queue["items"]}) == len(queue["items"])
    if report["handoff_schema_version"] == 4:
        # Cross-corpus schema v4 exposes both Templo Mayor and 1913 audits
        # for review, not merely the first Templo Mayor topic list.
        assert any(item["audit_claim_id"].startswith("TM-OP-")
                   for item in queue["items"])
        assert any(item["audit_claim_id"].startswith("DTR-")
                   for item in queue["items"])
        assert report["historical_discrepancies_pending_review"] >= 1
        # Source-locator addenda are provisional private evidence tasks.
        # They are not full-text archaeology checks or published sources.
        assert any("DETAIL" in item["audit_claim_id"] for item in queue["items"])
        assert report["coverage_gap_review_count"] >= 4
        # New period/theme/site readiness deltas must not vanish when the
        # research producer calls the array 'readiness' rather than 'cells'.
        reform = [gap for gap in queue["coverage_gaps"]
                  if "reform-munal-reforma-readiness" in gap["coverage_path"]]
        if "reform-munal-reforma-readiness" in " ".join(report["coverage_artifact_paths"]):
            assert len(reform) == 6, "New research readiness cells were dropped"
            assert all(gap["research_needed"] and gap["publication_authorization"] is False
                       for gap in reform)
        # Newer research coverage carries site-specific readiness and blockers.
        hospital = [gap for gap in queue["coverage_gaps"]
                    if "hospital-jesus-" in gap["coverage_path"]]
        if hospital:
            assert all(gap["explanation"] and gap["research_needed"]
                       for gap in hospital)
            assert all(isinstance(gap["candidate_finding_ids_unverified"], list)
                       and gap["publication_authorization"] is False
                       for gap in hospital)
        # The source team's exact published-reader audit is a separate,
        # paragraph-indexed human-review queue, never an approved chapter.
        exact_name = "templo-mayor-reader-20261113T1058Z-exact-prose-audit.json"
        if exact_name in " ".join(report["chapter_audit_artifact_paths"]):
            prose = [item for item in queue["items"]
                     if exact_name in item["audit_path"]]
            assert len(prose) == 10, "Exact published-reader checks were lost"
            assert len({x["audit_claim_id"] for x in prose}) == 10
            assert all(x["audit_claim_id"].startswith("reader-prose-review-")
                       and x["editorial_passage_id"] is None
                       and x["reader_audit_matches_main_blob"] is True
                       and x["publication_authorization"] is False for x in prose)
            assert any(x["reader_paragraph_index_proposed"] == 31
                       and x["candidate_evidence_status"] == "historical_date_conflict"
                       for x in prose)
            assert any("1913" in d["issue"] and "1914" in d["issue"]
                       for d in queue["unresolved_historical_discrepancies"])
            assert report["source_locator_review_count"] >= 5
            assert len([slot for slot in queue["source_locator_slots"]
                        if exact_name in slot["audit_path"]]) == 5
            assert all(slot["source_locator_confirmed"] is False and
                       slot["publication_authorization"] is False and
                       slot["source_locator_proposed"]
                       for slot in queue["source_locator_slots"])
            assert any(exact_name in status["audit_path"] and
                       status["matches_current_main_reader"] is True
                       for status in report["exact_reader_audit_status"])
        centro = [gap for gap in queue["coverage_gaps"]
                  if "centro-layered-city-readiness" in gap["coverage_path"]]
        if "centro-layered-city-readiness" in " ".join(report["coverage_artifact_paths"]):
            assert len(centro) == 7, "New Centro historical coverage gaps were dropped"
            assert all(gap["readiness"] in ("sparse", "developing")
                       and gap["research_needed"]
                       and gap["publication_authorization"] is False for gap in centro)
        # The 1847 matrix's finding_ids must remain in the PRIVATE queue.
        war1847 = [gap for gap in queue["coverage_gaps"]
                   if "1847-matrix-readiness" in gap["coverage_path"]]
        if "1847-matrix-readiness" in " ".join(report["coverage_artifact_paths"]):
            assert len(war1847) == 6, "1847 coverage cells disappeared"
            assert any("STG-20261113-1847-01" in gap[
                "candidate_finding_ids_unverified"] for gap in war1847)
            assert any(gap["readiness"] == "missing" and
                       gap["candidate_finding_ids_unverified"] == []
                       for gap in war1847)
            assert all(gap["publication_authorization"] is False and
                       gap["assigned_to_published_chapter"] is None
                       for gap in war1847)
        # The 13:20 Templo Mayor source matrix records seven paragraph-
        # specific research proposals. It is a PRIVATE evidence queue, and
        # neither proposed copy nor locator strings are approved citations.
        gate_name = "templo-mayor-discover-20261113T1320Z-chapter-evidence-gates.json"
        if gate_name in " ".join(report["chapter_audit_artifact_paths"]):
            gates = [item for item in queue["items"]
                     if gate_name in item["audit_path"]]
            assert len(gates) == 7, "Seven Templo Mayor evidence gates were not retained"
            assert len({item["audit_claim_id"] for item in gates}) == 7
            assert all(item["source_locator_candidates_unverified"]
                       and item["proposed_editorial_addition_unapproved"]
                       and item["reader_audit_matches_main_blob"] is True
                       and item["editorial_passage_id"] is None
                       and item["publication_authorization"] is False
                       for item in gates)
            assert any(item["reader_paragraph_index_proposed"] == 31
                       and item["candidate_evidence_status"] ==
                       "historical_chronology_conflict_blocker"
                       for item in gates)
        # The research producer's new 1847 readiness matrix contains ten
        # evidence-limited cells. Every missing-source reason stays private.
        civilian_1847 = [gap for gap in queue["coverage_gaps"]
                         if "1847-civilian-source-recovery" in gap["coverage_path"]]
        if "1847-civilian-source-recovery" in " ".join(report["coverage_artifact_paths"]):
            assert len(civilian_1847) == 10, "1847 readiness cells disappeared"
            assert all(gap["research_needed"] and gap["explanation"]
                       and gap["assigned_to_published_chapter"] is None
                       and gap["publication_authorization"] is False
                       for gap in civilian_1847)
        new_templo_audit = [item for item in queue["items"]
                           if item["audit_claim_id"].startswith("TM-DISC-")]
        if new_templo_audit:
            assert len(new_templo_audit) >= 6
            assert all(item["source_url_proposed"] and
                       item["source_locator_proposed"] and
                       item["editorial_passage_id"] is None and
                       item["publication_authorization"] is False
                       for item in new_templo_audit)
    for discrepancy in queue["unresolved_historical_discrepancies"]:
        assert discrepancy["audit_path"].startswith("research/audits/")
        assert discrepancy["issue"]
        assert discrepancy["source_comparison_completed"] is False
        assert discrepancy["publication_authorization"] is False
        assert discrepancy["review_state"].startswith("awaiting_human")
    for item in queue["items"]:
        assert item["audit_path"].startswith("research/audits/")
        assert item["editorial_passage_id"] is None
        assert item["source_id_confirmed"] is None
        assert item["page_or_section_checked"] is None
        assert item["review_state"].startswith("awaiting_human")
        assert item["publication_authorization"] is False
        if "DETAIL" in item["audit_claim_id"]:
            assert item["source_url_proposed"].startswith("https://")
            assert item["source_locator_proposed"]
            assert item["source_id_confirmed"] is None
    passages = json.loads((OUT / "editorial-passage-inventory.json").read_text(encoding="utf-8"))
    assert passages["status"] == "private_passage_inventory_human_evidence_review_required"
    assert passages["source_sha256"] == report["app_reader_sha256"]
    assert passages["passage_count"] == report["reader_passages_pending_evidence_review"]
    assert passages["passage_count"] >= 10
    assert all(f"dossier-topic-{n}" in passages["section_ids"] for n in range(1, 7))
    assert len(set(p["passage_id"] for p in passages["passages"])) == passages["passage_count"]
    for passage in passages["passages"]:
        assert passage["human_review_status"] == "not_reviewed"
        assert passage["source_id_confirmed"] is None
        assert passage["page_or_section_checked"] is None
        assert passage["audit_claim_ids_assigned"] == []
        assert passage["publication_authorization"] is False
    print("PASS: version-pinned handoff and private paragraph evidence slots remain unpublished")

assert not Path("site/data/editorial-review-queue.json").exists()
assert not Path("site/data/handoff-report.json").exists()
assert not Path("site/data/editorial-passage-inventory.json").exists()

# Nested archaeological explanations may be useful, but they are not automatically
# equivalent to independently verified main-narrative paragraphs.
parser = HistoryPassages()
parser.feed('<article id="history"><p>Existing <em>narrative</em> passage</p>'
            '<details><p>Optional deep dive</p></details></article>'
            '<section id="explore"><p>Physical field instructions</p></section>')
assert len(parser.passages) == 1
assert parser.passages[0]["section_id"] == "history-introduction"
assert parser.passages[0]["publication_authorization"] is False
