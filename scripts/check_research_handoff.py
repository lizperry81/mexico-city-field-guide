#!/usr/bin/env python3
"""Read-only, provenance-checked research handoff for editorial review.

Run from a full-history main checkout after fetching research-persistence.
Writes private CI artifacts only; NEVER writes to site/, edits research, or
authorizes publication. A failed validation exits nonzero.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from editorial_passage_inventory import inventory

RESEARCH_REF = "refs/remotes/origin/research-persistence"
MANIFEST_PATH = "research/handoff/manifest.json"
OUT = Path("artifacts/editorial-handoff")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
GROUPS = ("chapter_audit_artifact_paths", "coverage_artifact_paths",
          "research_pipeline_paths", "reconciliation_artifact_paths",
          "new_research_artifact_paths", "research_batch_artifact_paths",
          "handoff_history_paths")


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, check=True
    ).stdout


def git_json(ref, path):
    return json.loads(git("show", f"{ref}:{path}").decode("utf-8"))


def safe_path(path):
    if not isinstance(path, str) or not path or "\\" in path:
        raise ValueError("Invalid research artifact path")
    p = PurePosixPath(path)
    # Schema v4 references its CI proof workflow as a provenance artifact.
    # Accept exactly that workflow, never arbitrary application or site paths.
    allowed_workflow = path == ".github/workflows/research-replay-staging.yml"
    if p.is_absolute() or ".." in p.parts or not (path.startswith("research/") or allowed_workflow):
        raise ValueError(f"Out-of-scope research artifact path: {path}")
    return path


def validate_versioned_handoff(manifest, immutable_manifest, snapshot_sha):
    """Verify complete immutable handoffs without accepting snapshot drift.

    v2 requires identical files. v3 accepts two explicitly bound encodings.
    v4 accepts identical manifests, verified replay records, or a new
    append-only research snapshot with individually cross-checked identities,
    evidence counts, source manifests, and immutable artifacts.
    """
    version = manifest.get("schema_version")
    if version == 2:
        if immutable_manifest != manifest:
            raise ValueError("Versioned v2 handoff differs from current manifest")
        return
    if version not in (3, 4):
        raise ValueError("Unsupported handoff schema")
    if not isinstance(snapshot_sha, str) or not HEX40.fullmatch(snapshot_sha):
        raise ValueError("Missing immutable snapshot blob SHA")
    if manifest.get("handoff_history_append_only") is not True:
        raise ValueError("Research handoff must record append-only history")
    previous = manifest.get("previous_manifest_blob_sha")
    if not isinstance(previous, str) or not HEX40.fullmatch(previous):
        raise ValueError("Research handoff missing previous manifest provenance")
    if not isinstance(manifest.get("previous_manifest_generated_at"), str):
        raise ValueError("Research handoff missing previous handoff date")

    # The research producer has two valid v3 encodings. Some snapshots have
    # manifest-only provenance plus an explicit immutable-blob hash. Other
    # snapshots include provenance IN the immutable copy itself and therefore
    # have identical Git blobs (with no extra hash field). Only accept that
    # second form on exact full-object equality; no unbound fields allowed.
    if version == 4:
        if "immutable_handoff_snapshot_sha" in manifest:
            raise ValueError("v4 requires a fully provenance-bound snapshot")
        if immutable_manifest == manifest:
            return
        # Newer handoffs use an append-only, research-only snapshot containing
        # a before/after reconciliation record instead of a rolling-manifest
        # copy. Bind every key input/output to that immutable object. Only
        # separately reviewed evidence may ever be published.
        if immutable_manifest.get("kind") == "append_only_research_handoff_snapshot":
            if immutable_manifest.get("schema_version") != 4:
                raise ValueError("Append-only snapshot has wrong schema")
            shared = (
                "research_commit_sha", "canonical_version", "canonical_hash",
                "versioned_research_sqlite_gz_path", "versioned_research_sha256",
                "compressed_sha256", "replay_report_path", "verified_replay_commit_sha",
            )
            for field in shared:
                if immutable_manifest.get(field) != manifest.get(field):
                    raise ValueError("Append-only v4 identity drift: " + field)
            if (immutable_manifest.get("canonical_status") != "unchanged_not_promoted"
                    or immutable_manifest.get("ready_for_publication") is True
                    or immutable_manifest.get("canonical_promoted") is True
                    or manifest.get("canonical_promoted") is not False
                    or manifest.get("ready_for_publication") is not False
                    or immutable_manifest.get("research_branch") != "research-persistence"
                    or not isinstance(immutable_manifest.get("batch_commit_sha"), str)
                    or not HEX40.fullmatch(immutable_manifest["batch_commit_sha"])):
                raise ValueError("Append-only v4 snapshot is not safe staged research")
            snapshot_canonical = immutable_manifest.get("canonical_counts")
            if not isinstance(snapshot_canonical, dict):
                raise ValueError("Append-only v4 missing canonical count provenance")
            for key, value in manifest.get("canonical", {}).items():
                if snapshot_canonical.get(key) != value:
                    raise ValueError("Append-only v4 canonical counts drift: " + key)
            after = immutable_manifest.get("after")
            before = immutable_manifest.get("before")
            if not isinstance(after, dict) or not isinstance(before, dict):
                raise ValueError("Append-only v4 missing before/after metrics")
            count_keys = {
                "github_batches_replayed": "batches",
                "github_distinct_substantive_finding_ids": "staged_finding_ids_with_assertions",
                "github_inspection_entries": "inspection_metadata_entries",
                "github_source_candidates": "source_candidate_ids",
                "unknown_source_refs": "unknown_source_refs",
                "source_metadata_collisions": "source_metadata_collisions",
                "github_index_only_refs_unresolved": "unresolved_index_only_ids",
            }
            for key, after_key in count_keys.items():
                value = manifest.get("staged_counts", {}).get(key)
                if not isinstance(value, int) or after.get(after_key) != value:
                    raise ValueError("Append-only v4 staged count drift: " + key)
            for key in ("batches", "staged_finding_ids_with_assertions",
                        "inspection_metadata_entries", "source_candidate_ids"):
                if (not isinstance(before.get(key), int)
                        or after[key] < before[key]):
                    raise ValueError("Append-only v4 inconsistent research history: " + key)
            snapshot_evidence = immutable_manifest.get("evidence_status", {})
            current_evidence = manifest.get("evidence_status", {})
            evidence_keys = {
                "previously_staged_full_assertions_restored": "restored_prior_staged_findings_this_run",
                "new_source_linked_candidate_findings": "new_historical_finding_candidates_researched_this_run",
                "new_public_html_catalogue_inspections": "new_public_institutional_html_source_inspections_this_run",
                "independently_corroborated_new_claims": "independently_corroborated_new_findings",
            }
            for source_key, current_key in evidence_keys.items():
                if snapshot_evidence.get(source_key) != current_evidence.get(current_key):
                    raise ValueError("Append-only v4 evidence status drift: " + current_key)
            if (snapshot_evidence.get("publication_approved") is not False
                    or snapshot_evidence.get("ready_for_editorial_review") is not False
                    or manifest.get("ready_for_editorial_review") is not False
                    or current_evidence.get("publication_approved") is not False
                    or current_evidence.get("ready_for_editorial_review") is not False):
                raise ValueError("Append-only v4 falsely authorized research")
            for group in ("chapter_audit_artifact_paths", "coverage_artifact_paths",
                          "research_batch_artifact_paths"):
                snapshot_paths = immutable_manifest.get(group, [])
                current_paths = manifest.get(group, [])
                if (not isinstance(snapshot_paths, list) or not snapshot_paths
                        or not set(snapshot_paths).issubset(set(current_paths))):
                    raise ValueError("Append-only v4 lost evidence artifacts: " + group)
            return

        # Research previously emitted an independently committed, verified replay
        # record as the immutable anchor. It intentionally is NOT a copy of the
        # rolling manifest. Bind all essential immutable facts, rather than
        # treating a different object schema as an invalid or approved handoff.
        if immutable_manifest.get("kind") != "verified_replay_after_schema_unit_tests":
            raise ValueError("Unrecognized v4 immutable research snapshot")
        must_match = (
            "research_commit_sha", "canonical_version", "canonical_hash",
            "versioned_research_sqlite_gz_path", "versioned_research_sha256",
            "compressed_sha256", "replay_report_path",
            "previous_manifest_blob_sha", "previous_manifest_generated_at",
            "ready_for_editorial_review", "canonical_promoted",
        )
        for field in must_match:
            if immutable_manifest.get(field) != manifest.get(field):
                raise ValueError("Versioned v4 research snapshot drift: " + field)
        if (immutable_manifest.get("canonical_status") != "unchanged_not_promoted"
                or immutable_manifest.get("canonical_rows_unchanged") is not True
                or immutable_manifest.get("publication_approved") is not False
                or immutable_manifest.get("integrity") != "ok"
                or immutable_manifest.get("foreign_key_violations") != 0
                or not immutable_manifest.get("unit_tests_path")
                or not immutable_manifest.get("workflow_path")):
            raise ValueError("Unverified research-only v4 replay status")
        required_staged = {
            "github_batches_replayed": "github_batches_replayed",
            "github_distinct_substantive_finding_ids": "github_distinct_substantive_finding_ids",
            "github_inspection_entries": "github_inspection_metadata_entries",
            "github_source_candidates": "candidate_source_identities",
            "unknown_source_refs": "unresolved_source_refs",
            "source_metadata_collisions": "source_metadata_collisions",
            "github_index_only_refs_unresolved": "unresolved_index_only_refs",
            "detached_local_inspections_not_reconciled":
                "detached_inspections_not_in_github_replay",
        }
        producer_counts = immutable_manifest.get("staged_counts", {})
        current_counts = manifest.get("staged_counts", {})
        for current_key, snapshot_key in required_staged.items():
            if current_counts.get(current_key) != producer_counts.get(snapshot_key):
                raise ValueError("Versioned v4 staged counts drift: " + current_key)
        for group in ("chapter_audit_artifact_paths", "coverage_artifact_paths"):
            if not set(immutable_manifest.get(group, [])).issubset(
                    set(manifest.get(group, []))):
                raise ValueError("Versioned v4 removed snapshot audit: " + group)
        return
    if "immutable_handoff_snapshot_sha" not in manifest:
        if immutable_manifest != manifest:
            raise ValueError("Versioned inline-provenance v3 handoff differs")
        return
    if manifest["immutable_handoff_snapshot_sha"] != snapshot_sha:
        raise ValueError("Immutable v3 snapshot blob SHA mismatch")
    extensions = {
        "immutable_handoff_snapshot_sha", "handoff_history_append_only",
        "previous_manifest_blob_sha", "previous_manifest_generated_at",
    }
    base = {key: value for key, value in manifest.items() if key not in extensions}
    if immutable_manifest != base:
        raise ValueError("Versioned v3 handoff differs from immutable snapshot")


def validate():
    manifest = git_json(RESEARCH_REF, MANIFEST_PATH)
    if (manifest.get("schema_version") not in (2, 3, 4)
            or manifest.get("kind") != "research_to_app_handoff"):
        raise ValueError("Unrecognized research handoff schema")
    sha = manifest.get("research_commit_sha", "")
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        raise ValueError("Missing or invalid pinned research commit SHA")
    resolved = git("rev-parse", f"{sha}^{{commit}}").decode().strip()
    if resolved != sha:
        raise ValueError("Pinned research SHA could not be resolved")
    subprocess.run(["git", "merge-base", "--is-ancestor", sha, RESEARCH_REF],
                   check=True, capture_output=True)

    # The pinned research SHA identifies INPUT research. Replayed artifacts
    # may be generated and committed AFTER that input commit. Bind every
    # artifact to the immutable commit that published the manifest, rather
    # than falsely expecting all output files at the input SHA.
    handoff_commit = git("log", "-1", "--format=%H", RESEARCH_REF,
                         "--", MANIFEST_PATH).decode().strip()
    if not HEX40.fullmatch(handoff_commit):
        raise ValueError("Cannot locate committed handoff manifest")
    subprocess.run(["git", "merge-base", "--is-ancestor", sha, handoff_commit],
                   check=True, capture_output=True)
    if git("show", f"{handoff_commit}:{MANIFEST_PATH}") != git(
            "show", f"{RESEARCH_REF}:{MANIFEST_PATH}"):
        raise ValueError("Research manifest changed outside handoff commit")

    def bound_blob(path):
        safe_path(path)
        blob = git("show", f"{handoff_commit}:{path}")
        if not blob:
            raise ValueError(f"Empty handoff artifact: {path}")
        # No artifact may change after the handoff manifest without creating
        # a fresh handoff. Compare Git blobs, not timestamps or filenames.
        anchored = git("rev-parse", f"{handoff_commit}:{path}").strip()
        current = git("rev-parse", f"{RESEARCH_REF}:{path}").strip()
        if anchored != current:
            raise ValueError(f"Artifact changed after handoff: {path}")
        return blob

    inspected = []
    for group in GROUPS:
        paths = manifest.get(group, [])
        if not isinstance(paths, list):
            raise ValueError(f"Invalid handoff path group: {group}")
        for path in paths:
            blob = bound_blob(path)
            inspected.append({"group": group, "path": path,
                              "bytes": len(blob),
                              "sha256": hashlib.sha256(blob).hexdigest()})
    if not inspected or not manifest.get("chapter_audit_artifact_paths") or not manifest.get("coverage_artifact_paths"):
        raise ValueError("Research handoff lacks audit or coverage artifacts")

    immutable = safe_path(manifest.get("immutable_handoff_path"))
    snapshot_blob_sha = git("rev-parse", f"{handoff_commit}:{immutable}").decode().strip()
    immutable_manifest = json.loads(bound_blob(immutable).decode("utf-8"))
    if immutable_manifest.get("research_commit_sha") != sha:
        raise ValueError("Versioned handoff snapshot points to a different research commit")
    validate_versioned_handoff(manifest, immutable_manifest, snapshot_blob_sha)
    if manifest["schema_version"] in (3, 4):
        # Validate provenance against the actual previous committed manifest,
        # not merely a 40-character value copied into the new handoff.
        previous_blob = git("cat-file", "-p", manifest["previous_manifest_blob_sha"])
        previous_manifest = json.loads(previous_blob.decode("utf-8"))
        if (previous_manifest.get("kind") != "research_to_app_handoff" or
                previous_manifest.get("generated_at") != manifest["previous_manifest_generated_at"]):
            raise ValueError("Previous research handoff provenance does not match")

    compressed_path = manifest.get("versioned_research_sqlite_gz_path")
    if manifest["schema_version"] == 4 and not compressed_path:
        raise ValueError("v4 handoff requires its versioned research replay")
    if compressed_path:
        compressed = bound_blob(compressed_path)
        compressed_sha = hashlib.sha256(compressed).hexdigest()
        if compressed_sha != manifest.get("compressed_sha256"):
            raise ValueError("Staged research SQLite compressed checksum mismatch")
        extracted = gzip.decompress(compressed)
        if (not extracted.startswith(b"SQLite format 3\x00") or
                hashlib.sha256(extracted).hexdigest() !=
                manifest.get("versioned_research_sha256")):
            raise ValueError("Staged research SQLite content checksum mismatch")
        inspected.append({"group": "versioned_research_sqlite_gz_path",
                          "path": compressed_path, "bytes": len(compressed),
                          "sha256": compressed_sha})
        replay_path = manifest.get("replay_report_path")
        if not replay_path:
            raise ValueError("Versioned research SQLite lacks replay report")
        replay = json.loads(bound_blob(replay_path).decode("utf-8"))
        if (replay.get("output_sha256") != manifest["versioned_research_sha256"]
                or replay.get("status") != "research_database_staging_only_NOT_CANONICAL"
                or replay.get("ready_for_publication") is not False):
            raise ValueError("Replayed research status or checksum is inconsistent")
    # v4 preserves a larger cross-corpus research replay. It is NOT a
    # publication-ready database: independently check the replay's identity,
    # counts, staged-only status, conflicts and canonical preservation.
    # This prevents a syntactically valid manifest from laundering altered
    # counts or an accidentally promoted research snapshot.
    staged_reconciliation = None
    if manifest["schema_version"] == 4:
        staged = manifest.get("staged_counts")
        canonical = manifest.get("canonical")
        evidence = manifest.get("evidence_status")
        if not all(isinstance(x, dict) for x in (staged, canonical, evidence)):
            raise ValueError("v4 requires staged, canonical and evidence provenance")
        if (manifest.get("canonical_status") != "unchanged_provisional_V97_not_promoted"
                or manifest.get("canonical_version") != "V97"
                or manifest.get("canonical_hash") != replay.get("canonical_sha256")
                or replay.get("staging_sha256") != manifest["canonical_hash"]
                or replay.get("canonical_rows_unchanged") is not True
                or replay.get("sqlite_integrity") != "ok"
                or replay.get("foreign_key_violations") != 0
                or not isinstance(replay.get("ready_for_editorial_review"), bool)):
            raise ValueError("v4 canonical preservation or staging integrity failed")
        expected_canonical = {
            "sources": "sources", "claims": "claims",
            "claim_source_links": "claim_sources",
            "findings": "canonical_findings",
            "source_inspections": "canonical_source_inspections",
        }
        for handoff_key, replay_key in expected_canonical.items():
            if (not isinstance(canonical.get(handoff_key), int)
                    or canonical[handoff_key] !=
                    replay.get("canonical_counts", {}).get(replay_key)):
                raise ValueError("v4 canonical record counts differ from replay")
        metric_map = {
            "github_batches_replayed": "github_batch_json_files_examined",
            "github_distinct_substantive_finding_ids": "github_candidate_finding_ids",
            "github_index_only_refs_total": "index_only_finding_refs",
            "github_index_only_refs_unresolved": "unresolved_index_only_count",
            "raw_batch_documents_in_new_sqlite": "raw_batch_documents_in_sqlite",
            "github_inspection_entries": "github_inspection_entries",
            "github_source_candidates": "candidate_source_identities",
            "source_metadata_collisions": "cross_batch_conflict_count",
        }
        for handoff_key, replay_key in metric_map.items():
            if (not isinstance(staged.get(handoff_key), int)
                    or staged[handoff_key] != replay.get(replay_key)):
                raise ValueError("v4 staged count mismatch: " + handoff_key)
        if (staged.get("unknown_source_refs") !=
                len(replay.get("unknown_source_ids", []))
                or staged.get("github_index_only_refs_unresolved") !=
                len(replay.get("unresolved_index_only_ids", []))
                or staged.get("external_staging_semantic_join_verified") is not False
                or not isinstance(manifest.get("ready_for_editorial_review"), bool)
                or not isinstance(evidence.get("ready_for_editorial_review"), bool)
                or evidence.get("publication_approved") is not False):
            raise ValueError("v4 unresolved evidence or approval status changed")
        staged_reconciliation = {
            "status": "verified_staged_not_canonical_or_editorially_approved",
            "github_batches_replayed": staged["github_batches_replayed"],
            "candidate_finding_ids": staged["github_distinct_substantive_finding_ids"],
            "unresolved_index_only_refs": staged["github_index_only_refs_unresolved"],
            "unresolved_source_refs": staged["unknown_source_refs"],
            "source_metadata_collisions": staged["source_metadata_collisions"],
            "detached_source_inspections_pending":
                staged.get("detached_local_inspections_not_reconciled"),
            "semantic_join_verified": False,
        }
    # Only audit documents (not research batches) become PRIVATE review tasks.
    # They describe candidate historical problems; none of their citations or
    # suggested edits may be silently attached to existing paragraphs.
    audit_paths = [path for path in manifest["chapter_audit_artifact_paths"]
                   if path.startswith("research/audits/") and path.endswith(".json")]
    if not audit_paths:
        raise ValueError("Research handoff has no chapter audit documents")
    audits = [(path, json.loads(bound_blob(path).decode("utf-8")))
              for path in audit_paths]
    for path, audit_doc in audits:
        # Historical audits supply "claims", locator "evidence_entries",
        # or an explicit "claim_to_source" review matrix. All are private
        # human-review assignments, never publication-ready claim records.
        if (not isinstance(audit_doc, dict) or
                not any(isinstance(audit_doc.get(key), list)
                        for key in ("claims", "evidence_entries", "claim_to_source"))):
            raise ValueError("Invalid chapter audit format: " + path)
        if audit_doc.get("ready_for_publication") is True or audit_doc.get("editorial_approved") is True:
            raise ValueError("Unreviewed audit incorrectly marked as approved: " + path)
    audit = audits[0][1]
    coverage = json.loads(bound_blob(manifest["coverage_artifact_paths"][0]).decode("utf-8"))
    if not isinstance(coverage.get("counts"), dict):
        raise ValueError("Handoff coverage artifact has invalid structure")
    if manifest.get("ready_for_publication") is not False or manifest.get("canonical_promoted") is not False:
        raise ValueError("Cannot safely classify research handoff as unapproved")
    manuscript = Path("poi/templo-mayor/reader.html")
    passage_inventory = inventory(manuscript) if manuscript.is_file() else None
    manuscript_sha = passage_inventory["source_sha256"] if passage_inventory else None

    # This is a queue of REVIEW QUESTIONS. Sources and topics are not copied
    # into public content or attached to a passage without a human line audit.
    queue = []
    discrepancies = []
    for audit_path, audit_doc in audits:
        for candidate in (audit_doc.get("claims", []) +
                          audit_doc.get("evidence_entries", []) +
                          audit_doc.get("claim_to_source", [])):
            if not isinstance(candidate, dict):
                raise ValueError("Malformed audit candidate in " + audit_path)
            is_evidence = "claim_key" in candidate or "source_url" in candidate
            claim_id = candidate.get("claim_id") or candidate.get("claim_key")
            topic = (candidate.get("topic") or candidate.get("risk") or
                     candidate.get("event"))
            if not claim_id or not topic:
                raise ValueError("Research audit contains unidentified review topics")
            queue.append({
                "audit_path": audit_path,
                "audit_claim_id": claim_id,
                "topic_for_review": topic,
                "candidate_finding_id": candidate.get("finding_id"),
                "candidate_evidence_status":
                    candidate.get("evidence_status", candidate.get("status",
                                                                   candidate.get("confidence"))),
                "source_url_proposed": candidate.get("source_url") if is_evidence else None,
                "source_locator_proposed":
                    (candidate.get("exact_locator") or candidate.get("locator"))
                    if is_evidence else None,
                "source_access_claimed":
                    (candidate.get("access_scope") or candidate.get("access"))
                    if is_evidence else None,
                "remaining_source_check":
                    (candidate.get("remaining_gap") or candidate.get("uncertainty")
                     or candidate.get("editorial_action")) if is_evidence else None,
                "read_before_context_proposed":
                    candidate.get("read_before") if is_evidence else None,
                "on_site_context_proposed":
                    candidate.get("on_site") if is_evidence else None,
                "editorial_passage_id": None,
                "source_id_confirmed": None,
                "page_or_section_checked": None,
                "publication_authorization": False,
                "review_state": "awaiting_human_source_and_passage_check",
            })
        for discrepancy in audit_doc.get("existing_record_discrepancies", []):
            if not isinstance(discrepancy, dict) or not discrepancy.get("issue"):
                raise ValueError("Invalid historical conflict in " + audit_path)
            discrepancies.append({
                "audit_path": audit_path,
                "issue": discrepancy["issue"],
                "current_status": discrepancy.get("status"),
                "source_comparison_completed": False,
                "publication_authorization": False,
                "review_state": "awaiting_human_original_source_comparison",
            })

    # The research team also publishes an explanatory-coverage assessment.
    # Retain the gaps as structured human assignments, NOT as app content.
    coverage_gaps = []
    for coverage_path in manifest["coverage_artifact_paths"]:
        coverage_doc = json.loads(bound_blob(coverage_path).decode("utf-8"))
        cells = coverage_doc.get("cells", [])
        if not isinstance(cells, list):
            raise ValueError("Malformed coverage cells: " + coverage_path)
        for cell in cells:
            if not isinstance(cell, dict):
                raise ValueError("Malformed coverage cell: " + coverage_path)
            # A focused POI assessment carries each period and site within
            # its cell; a dated research-delta stores them on the parent
            # document. Respect both without inventing missing research tasks.
            period = cell.get("period") or coverage_doc.get("period")
            geography = cell.get("geography") or coverage_doc.get("geography")
            theme = cell.get("theme")
            rating = cell.get("rating") or cell.get("new_rating")
            explanation = cell.get("why") or cell.get("assessment")
            next_task = cell.get("next") or cell.get("remaining_gap")
            if not all(isinstance(value, str) and value
                       for value in (period, theme, geography, rating, explanation)):
                raise ValueError("Malformed private coverage gap: " + coverage_path)
            coverage_gaps.append({
                "coverage_path": coverage_path,
                "period": period,
                "theme": theme,
                "geography": geography,
                "readiness": rating,
                "explanation": explanation,
                "research_needed": next_task,
                "assigned_to_published_chapter": None,
                "review_state": "awaiting_human_evidence_and_editorial_review",
                "publication_authorization": False,
            })
    report = {
        "schema_version": 1,
        "status": "verified_handoff_not_approved",
        "research_commit_sha": sha,
        "handoff_manifest_commit_sha": handoff_commit,
        "handoff_schema_version": manifest["schema_version"],
        "immutable_handoff_path": immutable,
        "immutable_handoff_blob_sha": snapshot_blob_sha,
        "research_branch_at_build": git("rev-parse", RESEARCH_REF).decode().strip(),
        "handoff_manifest_blob_sha256": hashlib.sha256(
            git("show", f"{RESEARCH_REF}:{MANIFEST_PATH}")).hexdigest(),
        "canonical_version": manifest.get("canonical_version"),
        "canonical_promoted": False,
        "research_ready_for_editorial_review": manifest.get("ready_for_editorial_review") is True,
        "audit_ready_for_editorial_review": audit.get("ready_for_editorial_review") is True,
        "ready_for_publication": False,
        "app_reader_text_available_for_line_audit": manuscript_sha is not None,
        "app_reader_sha256": manuscript_sha,
        "reader_passages_pending_evidence_review": passage_inventory["passage_count"] if passage_inventory else 0,
        "audit_scope_limit": audit.get("scope_limit"),
        "coverage_status": coverage.get("status"),
        "coverage_counts": coverage["counts"],
        "chapter_audit_artifact_paths": manifest["chapter_audit_artifact_paths"],
        "coverage_artifact_paths": manifest["coverage_artifact_paths"],
        "staged_reconciliation": staged_reconciliation,
        "artifact_checks": inspected,
        "unresolved": manifest.get("blockers", []),
        "review_queue_count": len(queue),
        "coverage_gap_review_count": len(coverage_gaps),
        "audit_documents_reviewed": len(audits),
        "historical_discrepancies_pending_review": len(discrepancies),
        "publication_policy": "No candidate findings, sources or editorial prose imported or published",
    }
    return report, {
        "schema_version": 1, "research_commit_sha": sha,
        "status": "human_review_required_not_for_publication",
        "reader_sha256": manuscript_sha,
        "items": queue,
        "unresolved_historical_discrepancies": discrepancies,
        "coverage_gaps": coverage_gaps,
    }, passage_inventory


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        report, queue, passages = validate()
    except (subprocess.CalledProcessError, ValueError, KeyError,
            TypeError, json.JSONDecodeError) as exc:
        # No stale verified queue may survive a failed newer handoff.
        for stale in ("editorial-review-queue.json", "editorial-passage-inventory.json"):
            (OUT / stale).unlink(missing_ok=True)
        blocked = {"schema_version": 1, "status": "no_verified_handoff",
                   "reason": str(exc), "ready_for_publication": False}
        (OUT / "handoff-report.json").write_text(
            json.dumps(blocked, indent=2) + "\n", encoding="utf-8")
        print("::warning::Research handoff not verified:", exc, flush=True)
        raise SystemExit(1) from exc
    (OUT / "handoff-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "editorial-review-queue.json").write_text(
        json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if passages is not None:
        (OUT / "editorial-passage-inventory.json").write_text(
            json.dumps(passages, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert report["status"] == "verified_handoff_not_approved"
    assert not report["ready_for_publication"]
    assert all(item["editorial_passage_id"] is None for item in queue["items"])
    print("Verified pinned research handoff:", report["research_commit_sha"], flush=True)
    print("Provisional audit topics queued for HUMAN review:", len(queue["items"]), flush=True)
    print("Existing history passages inventoried for human line audit:",
          report["reader_passages_pending_evidence_review"], flush=True)
    print("No staged research merged or published.", flush=True)


if __name__ == "__main__":
    main()
