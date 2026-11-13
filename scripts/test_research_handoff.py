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
        assert gap["research_needed"]
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
