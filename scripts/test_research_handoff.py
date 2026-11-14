#!/usr/bin/env python3
"""Guard research handoff against accidental editorial publication or unsafe paths."""
import copy
import json
from pathlib import Path

from check_research_handoff import OUT, safe_path, validate_versioned_handoff, verified_index_only_total
from editorial_passage_inventory import HistoryPassages
from check_research_handoff import audit_matrix_explicitly_unapproved
from handoff_new_audits import parse_new_audit

# The 73-batch producer reports its full historical index-only total (23)
# directly in the replay, while old v4 snapshots recorded the remaining 18
# plus five TE28 reclassifications. Test both strict provenance encodings.
assert verified_index_only_total(23, 23, 5, "research_to_app_handoff")
assert verified_index_only_total(23, 23, 5, "immutable_research_batch_handoff")
assert verified_index_only_total(23, 18, 5, "verified_research_to_app_handoff_history")
for bad in (
    (28, 23, 5, "research_to_app_handoff"),
    (23, 18, 5, "research_to_app_handoff"),
    (23, 23, 5, "verified_research_to_app_handoff_history"),
    (23, 23, -5, "research_to_app_handoff"),
    (True, 23, 5, "research_to_app_handoff"),
):
    assert not verified_index_only_total(*bad), f"Accepted unverified index-only totals: {bad}"

# New research records with paragraph-specific gates must remain private,
# pinned to the inspected historical reader blob and source-locator evidence.
_blob = "a" * 40
_audit = {
    "kind": "templo_mayor_actual_reader_targeted_claim_evidence_addendum",
    "branch": "research-persistence", "target_branch_read_only": "main",
    "target_path": "poi/templo-mayor/reader.html",
    "target_main_blob_sha": "b" * 40,
    "ready_for_editorial_review": False, "publication_approved": False,
    "gates": [{"id": "G-1", "reader_anchor": "Gamio opened this section",
               "historical_correction": "1913 and 1914 conflict",
               "source_locator_matrix": [{"source_id": "S-1", "pages": "p. 18"}],
               "hold": "Original primary text not inspected",
               "draft_candidate": "Unapproved proposed wording"}],
}
_out = parse_new_audit("research/audits/gamio.json", _audit, _blob)
assert len(_out) == 1 and _out[0]["publication_authorization"] is False
assert _out[0]["review_state"] == "awaiting_human_stale_reader_blob_reaudit"
assert _out[0]["source_locator_candidates_unverified"][0]["source"] == "S-1"
for mutation in (
    {"publication_approved": True},
    {"ready_for_editorial_review": True},
    {"target_main_blob_sha": "incorrect"},
    {"gates": [dict(_audit["gates"][0], source_locator_matrix=[])]},
    {"gates": [dict(_audit["gates"][0], hold="")]},
):
    try:
        parse_new_audit("research/audits/gamio.json",
                        dict(_audit, **mutation), _blob)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe dated reader audit admitted: " + str(mutation))
# Older gates sometimes cite a previous audit without a newly inspected
# primary source; preserve the audit pointer without upgrading it to evidence.
_prior = dict(_audit, gates=[{
    "id": "G-prior", "reader_anchor": "Existing dated claim",
    "source_locator_matrix": [{"prior_audit": "research/audits/earlier.json"}],
    "hold": "Original witness remains unexamined", "disposition": "retain"}])
_prior_result = parse_new_audit("research/audits/prior.json", _prior, _blob)
assert _prior_result[0]["source_ids_unverified"] == []
assert (_prior_result[0]["source_locator_candidates_unverified"][0]["document"]
        == "research/audits/earlier.json")
_cross = dict(_audit,
    kind="templo_mayor_discover_cross_period_and_current_reader_evidence_gate",
    gates=[{"topic": "Chronology", "reader_anchor": "Late 1420s",
            "status": "retain qualified date", "uncertainty": "Original not read",
            "source_locator_matrix": [{"source": "prior audit", "locator": "gate 2"}]}])
assert len(parse_new_audit("research/audits/cross.json", _cross, _blob)) == 1
# A gated chronology topic may explicitly lack any new source locator.
_no_source = dict(_cross, gates=[dict(_cross["gates"][0],
    source_locator_matrix=[])])
_no_source_items = parse_new_audit("research/audits/cross.json", _no_source, _blob)
assert _no_source_items[0]["source_locator_candidates_unverified"] == []
assert _no_source_items[0]["publication_authorization"] is False

_seven = dict(_cross,
    kind="templo_mayor_discover_exact_reader_seven_topic_source_locator_audit")
assert len(parse_new_audit("research/audits/seven.json", _seven, _blob)) == 1
_boundary = dict(_audit,
    kind="templo_mayor_exact_reader_blob_and_urban_chronology_boundary",
    boundary="Modern City chapter, not Templo Mayor excavation",
    reader_anchors=[{"topic": "Alliance", "anchor": "Late 1420s",
                     "status": "qualified", "needs": "Primary account"}],
    source_locator_matrix=[{"source_ids": ["S-1"], "locator": "p. 81",
                            "use": "Modern City chapter"}])
assert len(parse_new_audit("research/audits/boundary.json", _boundary, _blob)) == 1
assert (parse_new_audit("research/audits/boundary.json", _boundary, _blob)[0]
        ["proposed_editorial_addition_unapproved"] is None)

# Historical date disputes are review assignments. The producer's new
# claim-to-source addendum must never authorize manuscript publication.
date_contrast = {
    "kind": "templo_mayor_discover_exact_prose_claim_to_source_locator_addendum",
    "claim_to_source_locator_matrix": [{"locator": "INAH Huexotla history"}],
    "publication_approved": False, "ready_for_editorial_review": False,
    "main_modified": False,
    "proposed_unpublished_historical_addition":
        "Date of Triple Alliance formation requires original-source comparison.",
}
assert audit_matrix_explicitly_unapproved(date_contrast)
for changed in (
    {"publication_approved": True},
    {"ready_for_editorial_review": True},
    {"main_modified": True},
    {"proposed_unpublished_historical_addition": ""},
    {"claim_to_source_locator_matrix": []},
    {"kind": "untrusted_approval_claim"},
):
    candidate = dict(date_contrast, **changed)
    assert not audit_matrix_explicitly_unapproved(candidate), changed

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

# New source/replay-separated producer format remains unapproved even when
# its source and snapshot identifiers agree with the handoff manifest.
readback_manifest = {
    "schema_version": 4, "research_commit_sha": "b"*40,
    "verified_replay_commit_sha": "c"*40,
    "canonical_version": "V97", "canonical_hash": "d"*64,
    "canonical_status": "unchanged_provisional_V97_not_promoted",
    "canonical_promoted": False, "ready_for_editorial_review": False,
    "ready_for_publication": False,
    "versioned_research_sha256": "e"*64, "compressed_sha256": "f"*64,
    "versioned_research_sqlite_gz_path": "research/reconciled/test/research_only.sqlite.gz",
    "replay_report_path": "research/reconciled/test/replay_report.json",
    "evidence_status": {"publication_approved": False,
                        "independently_corroborated_new_findings": 0},
    "staged_counts": {"github_batches_replayed": 79,
                      "github_distinct_substantive_finding_ids": 475,
                      "github_source_candidates": 176,
                      "github_inspection_entries": 214},
    "chapter_audit_artifact_paths": ["research/audits/cu.json"],
    "coverage_artifact_paths": ["research/coverage/cu.json"],
    "research_batch_artifact_paths": ["research/batches/cu.json"],
    "reconciliation_artifact_paths": ["research/ledgers/readback.json"]
}
readback_history = {
    "schema_version": 4, "kind": "append_only_research_to_app_verified_handoff",
    "branch": "research-persistence",
    "source_research_commit_sha": "b"*40, "verified_replay_commit_sha": "c"*40,
    "canonical_version": "V97", "canonical_hash": "d"*64,
    "canonical_status": "unchanged_provisional",
    "versioned_research_sha256": "e"*64, "compressed_sha256": "f"*64,
    "versioned_research_sqlite_gz_path": "research/reconciled/test/research_only.sqlite.gz",
    "verified_replay_report_path": "research/reconciled/test/replay_report.json",
    "evidence_status": readback_manifest["evidence_status"],
    "ready_for_editorial_review": False, "ready_for_publication": False,
    "no_automatic_merge": True,
    "staged_counts": {"batches": 79, "findings": 475,
                      "source_candidates": 176, "source_inspections": 214},
    "chapter_audit_artifact_paths": ["research/audits/cu.json"],
    "coverage_artifact_paths": ["research/coverage/cu.json"],
    "research_batch_artifact_paths": ["research/batches/cu.json"],
    "verification_ledger_path": "research/ledgers/readback.json"
}
validate_versioned_handoff(readback_manifest, readback_history, "a"*40)
# 80-batch history uses a compact summary, while the rolling manifest keeps
# additional source-access details. Authenticate every count and publication
# restriction; never accept an arbitrary mismatch between these documents.
compact_manifest = copy.deepcopy(readback_manifest)
compact_manifest["staged_counts"]["new_source_candidates_all_types_this_run"] = 12
compact_manifest["evidence_status"] = {
    "new_historical_finding_candidates_researched_this_run": 11,
    "new_source_inspection_metadata_this_run": 12,
    "independently_corroborated_new_findings": 0,
    "ready_for_editorial_review": False,
    "publication_approved": False}
compact_history = copy.deepcopy(readback_history)
compact_history["evidence_status"] = {
    "new_findings": 11, "new_sources": 12, "new_inspections": 12,
    "independent_corroboration": False, "publication_approved": False,
    "source_types": "unverified source metadata, originals pending"}
validate_versioned_handoff(compact_manifest, compact_history, "a"*40)
for mutation in (
    {"new_findings": 10}, {"new_sources": 13},
    {"new_inspections": 11}, {"independent_corroboration": True},
    {"publication_approved": True}, {"source_types": ""},
    {"unexpected_field": "claimed source review"},
):
    altered = copy.deepcopy(compact_history)
    altered["evidence_status"].update(mutation)
    try:
        validate_versioned_handoff(compact_manifest, altered, "a"*40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unverified compact research evidence accepted: " + str(mutation))
for key, value in [("source_research_commit_sha", "z"*40),
                   ("no_automatic_merge", False),
                   ("ready_for_publication", True)]:
    altered = copy.deepcopy(readback_history)
    altered[key] = value
    try:
        validate_versioned_handoff(readback_manifest, altered, "a"*40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe immutable readback allowed: " + key)
cu_audit = {
    "kind": "chapter_level_claim_to_source_locator_audit",
    "branch": "research-persistence", "target_branch_read_only": "main",
    "target_path": "poi/templo-mayor/reader.html",
    "reader_blob_sha": "a"*40, "reader_re_read_this_run": True,
    "no_publication_of_unverified_claims": True,
    "publication_approved": False, "ready_for_editorial_review": False,
    "gates": [{"topic": "CU murals as later interpretation",
               "reader_anchor": "In the late 1420s", "status": "unapproved",
               "uncertainty": "Not a primary Mexica source",
               "source_locators": [{"path": "research/batches/cu.json", "locator": "CU-08"}]}]
}
cu_items = parse_new_audit("research/audits/cu.json", cu_audit, "a"*40)
assert len(cu_items) == 1 and cu_items[0]["publication_authorization"] is False
assert cu_items[0]["reader_audit_matches_main_blob"] is True
# The 80-batch Metro/Pino Suárez research did NOT re-read the reader.
# A previously pinned HTML blob is useful for identifying proposed passages,
# but must NEVER count as a fresh current-reader audit or publication approval.
metro_stale = copy.deepcopy(cu_audit)
metro_stale.pop("reader_blob_sha")
metro_stale["reader_blob_sha_last_verified"] = "a" * 40
metro_stale["reader_re_read_this_run"] = False
metro_stale["gates"] = [
    {"topic": "Pino Suárez and Templo Mayor were distinct rescue campaigns",
     "reader_anchor": "In February 1978, electrical workers",
     "status": "separate_1967_1968_1978_salvage_sites",
     "uncertainty": "Original 1968 newspaper and excavation fieldbook absent",
     "historical_addition": "Optional unapproved cross-period sidebar",
     "source_locators": [
         {"path": "research/batches/metro-80.json", "locator": "METRO-07"}
     ]}
]
metro_items = parse_new_audit(
    "research/audits/metro-80.json", metro_stale, "a" * 40)
assert len(metro_items) == 1
assert metro_items[0]["reader_audit_matches_main_blob"] is False
assert metro_items[0]["review_state"] == "awaiting_human_stale_reader_blob_reaudit"
assert metro_items[0]["publication_authorization"] is False
assert metro_items[0]["editorial_passage_id"] is None
assert metro_items[0]["source_id_confirmed"] is None
assert metro_items[0]["remaining_source_check"] == (
    "Original 1968 newspaper and excavation fieldbook absent")
assert metro_items[0]["proposed_editorial_addition_unapproved"] == (
    "Optional unapproved cross-period sidebar")
assert metro_items[0]["source_locator_candidates_unverified"][0]["locator"] == "METRO-07"
# Reject missing or conflicting stale pins, unsafe approval, and false
# claims of a fresh re-read based only on a historical SHA.
for mutation in (
    {"reader_blob_sha_last_verified": None},
    {"reader_blob_sha_last_verified": "not-a-committed-blob"},
    {"reader_blob_sha": "b" * 40},
    {"reader_re_read_this_run": True},
    {"no_publication_of_unverified_claims": False},
    {"ready_for_editorial_review": True},
    {"publication_approved": True},
):
    unsafe = dict(metro_stale, **mutation)
    try:
        parse_new_audit("research/audits/metro-80.json", unsafe, "a" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe stale reader audit admitted: " + str(mutation))
# Earlier 1910 modern-city boundary audits provide only previous-audit
# pointers, never original-source corroboration or publication authority.
boundary_audit = {
    "kind": "templo_mayor_chapter_evidence_maintenance_and_1910_chronology_boundary",
    "branch": "research-persistence", "target_branch_read_only": "main",
    "target_path": "poi/templo-mayor/reader.html", "target_main_blob_sha": "a"*40,
    "original_text_was_re_read": True, "publication_approved": False,
    "ready_for_editorial_review": False, "boundary": "Modern City chapter",
    "claim_source_locator_matrix": [
        {"topic": "Triple Alliance dates", "reader_anchor": "In the late 1420s",
         "source_locator": "research/audits/older.json",
         "status": "unverified", "next": "Inspect original chronology"}
    ]
}
items = parse_new_audit("research/audits/boundary.json", boundary_audit, "a"*40)
assert len(items) == 1 and items[0]["publication_authorization"] is False
assert items[0]["source_locator_candidates_unverified"][0]["document"] == "research/audits/older.json"
bad_boundary = copy.deepcopy(boundary_audit)
bad_boundary["publication_approved"] = True
try:
    parse_new_audit("research/audits/boundary.json", bad_boundary, "a"*40)
except ValueError:
    pass
else:
    raise AssertionError("Published historical boundary report accepted")

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
    "blockers": [
        "One proposed Sload botanical DATASET source remains unregistered",
        "Manzanilla and Sload metadata identities remain in conflict",
        "Nine detached inspection URL overlaps and 28 unmatched records",
        "Templo Mayor Gamio date still requires original-source review",
        "1913 photo originals and reproduction rights are unverified",
        "1847 primary sources and 1985 reconstruction ledgers remain unexamined",
    ],
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
# A 74-batch producer may freeze an exact copy of the manifest under a
# distinct kind. It must then publish BOTH exact immutable Git identities.
# Missing Git blob/history pins cannot turn mutable research into a review queue.
centenary = copy.deepcopy(batch_manifest)
centenary["kind"] = "research_to_app_handoff"
centenary["handoff_history_commit_sha"] = "b" * 40
centenary["immutable_handoff_blob_sha"] = "a" * 40
centenary["evidence_status"]["ready_for_editorial_review"] = False
centenary["replay_evidence"] = {
    "sqlite_integrity": "ok", "foreign_key_violations": 0,
    "canonical_rows_unchanged": True, "github_snapshot_readback": True,
}
centenary_snapshot = copy.deepcopy(centenary)
centenary_snapshot["kind"] = "research_to_app_handoff_immutable_snapshot"
centenary_snapshot["immutable_handoff_blob_sha"] = None
centenary_snapshot["handoff_history_commit_sha"] = None
validate_versioned_handoff(centenary, centenary_snapshot, "a" * 40)
assert verified_index_only_total(
    23, 23, 5, "research_to_app_handoff_immutable_snapshot")
for label, patch, frozen_patch in (
    ("missing blob pin", {"immutable_handoff_blob_sha": None}, {}),
    ("wrong blob pin", {"immutable_handoff_blob_sha": "9" * 40}, {}),
    ("missing history commit", {"handoff_history_commit_sha": None}, {}),
    ("staged findings drift", {"staged_counts": dict(
        centenary["staged_counts"], github_batches_replayed=999)}, {}),
    ("unreviewed evidence published", {"ready_for_publication": True}, {}),
    ("replay readback denied", {"replay_evidence": dict(
        centenary["replay_evidence"], github_snapshot_readback=False)}, {}),
    ("frozen source drift", {}, {"canonical_hash": "9" * 64}),
):
    candidate = copy.deepcopy(centenary)
    immutable = copy.deepcopy(centenary_snapshot)
    candidate.update(patch)
    immutable.update(frozen_patch)
    try:
        validate_versioned_handoff(candidate, immutable, "a" * 40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unpinned or altered 74-batch snapshot accepted: " + label)

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
                       and x["reader_audit_matches_main_blob"] is False
                       and x["review_state"] == "awaiting_human_stale_reader_blob_reaudit"
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
                       status["matches_current_main_reader"] is False
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
                       and item["reader_audit_matches_main_blob"] is False
                       and item["review_state"] == "awaiting_human_stale_reader_blob_reaudit"
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
        # The 10:58 reader audit and 13:20 matrix are pinned to an older
        # Git blob and must remain marked stale. The 17:10 audit targets
        # the actual main reader and identifies seven private evidence gates.
        legal = [x for x in queue["items"]
                 if "1985-reconstruction-primary-legal-locators" in x["audit_path"]]
        if any("1985-reconstruction-primary-legal-locators" in p
               for p in report["chapter_audit_artifact_paths"]):
            assert len(legal) == 7
            assert all(x["source_locator_candidates_unverified"]
                       and x["remaining_source_check"]
                       and x["publication_authorization"] is False for x in legal)
        modes = [x for x in queue["items"]
                 if "templo-mayor-historical-vs-site-reading-gates" in x["audit_path"]]
        if any("templo-mayor-historical-vs-site-reading-gates" in p
               for p in report["chapter_audit_artifact_paths"]):
            assert len(modes) == 5
            assert all(x["reader_audit_matches_main_blob"] is False
                       and x["review_state"] == "awaiting_human_stale_reader_blob_reaudit"
                       for x in modes)
        new_reader = [x for x in queue["items"]
                      if "templo-mayor-discover-20261113T1710Z-main-current-blob" in x["audit_path"]]
        if any("templo-mayor-discover-20261113T1710Z-main-current-blob" in p
               for p in report["chapter_audit_artifact_paths"]):
            assert len(new_reader) == 7
            # Reader HTML changed after the audit was captured. Compare
            # the pinned Git blob to HEAD instead of assuming a permanently
            # current audit or silently reapproving old source locators.
            import subprocess
            audited_path = ("research/audits/"
                "templo-mayor-discover-20261113T1710Z-main-current-blob-claim-source-gates.json")
            audited = json.loads(subprocess.check_output(
                ["git", "show", "origin/research-persistence:" + audited_path],
                text=True))
            actual_blob = subprocess.check_output(
                ["git", "rev-parse", "HEAD:poi/templo-mayor/reader.html"],
                text=True).strip()
            current = audited["target_main_blob_sha"] == actual_blob
            assert all(x["reader_audit_matches_main_blob"] is current
                       and x["reader_anchor_proposed"]
                       and x["source_locator_candidates_unverified"]
                       and x["review_state"] ==
                           ("awaiting_human_source_and_passage_check" if current
                            else "awaiting_human_stale_reader_blob_reaudit")
                       and x["editorial_passage_id"] is None
                       and x["publication_authorization"] is False
                       for x in new_reader)
        period = [x for x in queue["coverage_gaps"]
                  if "cross-period-place-explanatory-readiness" in x["coverage_path"]]
        if any("cross-period-place-explanatory-readiness" in p
               for p in report["coverage_artifact_paths"]):
            assert len(period) == 15
            assert len([x for x in period if x["readiness"] == "developing"]) == 9
            assert len([x for x in period if x["readiness"] == "sparse"]) == 5
            assert len([x for x in period if x["readiness"] == "missing"]) == 1
            assert all(x["research_needed"] and
                       isinstance(x["candidate_finding_ids_unverified"], list)
                       and x["publication_authorization"] is False for x in period)
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
