"""Fail-closed validation for the research team's 69-batch immutable v4 handoff.

Only validates metadata and evidence provenance. No content from this handoff
is approved for publication or allowed to overwrite the public guide.
"""
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def require(condition, reason):
    if not condition:
        raise ValueError("Immutable batch v4 handoff: " + reason)


def validate_immutable_batch_v4(manifest, snapshot, blob_sha):
    require(snapshot.get("schema_version") == 4 and
            snapshot.get("kind") == "immutable_research_batch_handoff",
            "unknown immutable batch format")
    require(manifest.get("schema_version") == 4 and
            manifest.get("handoff_history_append_only") is True,
            "rolling handoff must be versioned and append-only")
    require(HEX40.fullmatch(blob_sha or "") is not None and
            manifest.get("immutable_handoff_blob_sha") == blob_sha,
            "immutable Git blob identity mismatch")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                "previous_manifest_blob_sha", "compressed_sha256",
                "versioned_research_sha256", "replay_report_path",
                "versioned_research_sqlite_gz_path"):
        require(snapshot.get(key) == manifest.get(key),
                "research identity drift: " + key)
    require(snapshot.get("branch") == "research-persistence" and
            HEX40.fullmatch(snapshot.get("research_commit_sha", "")) is not None and
            snapshot.get("canonical_version") == "V97" and
            HEX64.fullmatch(snapshot.get("canonical_hash", "")) is not None,
            "research branch or canonical identity unverified")
    require(snapshot.get("canonical_status") ==
            "unchanged_provisional_V97_not_promoted" ==
            manifest.get("canonical_status"), "canonical status drift")
    for obj in (snapshot, manifest):
        for flag in ("canonical_promoted", "ready_for_editorial_review"):
            require(obj.get(flag) is False, "research approval forbidden: " + flag)
    require(snapshot.get("ready_for_publication") is False and
            manifest.get("ready_for_publication") is False and
            snapshot.get("main_modified") is False,
            "publication or main-branch mutation claimed")
    require(snapshot.get("ready_for_editorial_review") is False and
            snapshot.get("ready_for_publication") is False,
            "provisional work falsely approved")

    expected_canonical = snapshot.get("canonical_counts")
    current_canonical = manifest.get("canonical")
    require(isinstance(expected_canonical, dict) and
            expected_canonical == current_canonical and
            all(type(v) is int and v >= 0 for v in expected_canonical.values()),
            "canonical records/counts differ")

    baseline, staged = snapshot.get("baseline_counts"), snapshot.get("staged_counts")
    current = manifest.get("staged_counts")
    require(all(isinstance(x, dict) for x in (baseline, staged, current)),
            "missing baseline or staged counters")
    mapping = {
        "batches": "github_batches_replayed",
        "assertion_bearing_findings": "github_distinct_substantive_finding_ids",
        "source_candidates": "github_source_candidates",
        "source_inspection_metadata": "github_inspection_entries",
        "unregistered_source_ids": "unknown_source_refs",
        "metadata_collisions": "source_metadata_collisions",
    }
    for key, manifest_key in mapping.items():
        require(type(staged.get(key)) is int and staged[key] >= 0 and
                staged[key] == current.get(manifest_key),
                "new staged count differs: " + key)
        require(type(baseline.get(key)) is int and baseline[key] >= 0,
                "baseline count missing: " + key)
    for key in ("batches", "assertion_bearing_findings",
                "source_candidates", "source_inspection_metadata"):
        require(baseline[key] <= staged[key],
                "staged counter regressed: " + key)
    require(staged["unregistered_source_ids"] <= baseline["unregistered_source_ids"],
            "unregistered reference count regressed")
    require(staged["metadata_collisions"] == baseline["metadata_collisions"],
            "bibliographic conflict records changed without review")

    changes = {
        "new_candidate_findings": ("assertion_bearing_findings",
                                   "new_historical_finding_candidates_this_run"),
        "new_inspection_metadata": ("source_inspection_metadata",
                                    "new_source_inspection_metadata_this_run"),
    }
    for key, (counter, manifest_key) in changes.items():
        val = snapshot.get(key)
        require(type(val) is int and val >= 0 and
                val == staged[counter] - baseline[counter] and
                val == current.get(manifest_key),
                "research evidence delta differs: " + key)
    resolved = snapshot.get("new_provisional_source_id_resolutions")
    new_sources = snapshot.get("new_source_candidate_records")
    require(type(resolved) is int and resolved >= 0 and
            type(new_sources) is int and new_sources >= 0 and
            baseline["unregistered_source_ids"] - staged["unregistered_source_ids"] == resolved and
            staged["source_candidates"] - baseline["source_candidates"] ==
            resolved + new_sources and
            resolved == current.get("source_id_provisional_recoveries_this_run") and
            new_sources == current.get("new_scholarly_source_candidate_records_this_run"),
            "recovered source identities are not reconciled")

    replay = manifest.get("replay_evidence")
    verified = snapshot.get("verification")
    require(isinstance(replay, dict) and isinstance(verified, dict) and
            verified.get("sqlite_integrity") == "ok" and
            verified.get("foreign_key_violations") == 0 and
            verified.get("all_88_original_tables_preserved") is True and
            verified.get("canonical_rows_unchanged") is True and
            verified.get("versioned_db_git_readback") is True and
            verified.get("report_git_readback") is True and
            verified.get("github_replay_workflow_internal_persisted_sha256_check") is True and
            replay.get("integrity") == "ok" and
            replay.get("foreign_key_violations") == 0 and
            replay.get("original_tables_preserved") == 88 and
            replay.get("canonical_rows_unchanged") is True and
            replay.get("github_readback_verified") is True,
            "verified database replay or Git readback missing")
    for key, evidence_key in (("replay_report_git_blob_sha",
                               "github_replay_report_blob_sha"),
                              ("replay_binary_git_blob_sha",
                               "github_replay_binary_blob_sha")):
        value = snapshot.get(key)
        require(isinstance(value, str) and HEX40.fullmatch(value) is not None and
                value == replay.get(evidence_key),
                "Git readback differs: " + key)
    evidence = snapshot.get("evidence_status")
    current_evidence = manifest.get("evidence_status")
    require(isinstance(evidence, dict) and isinstance(current_evidence, dict),
            "missing explicit evidence restrictions")
    for obj in (evidence, current_evidence):
        require(obj.get("ready_for_editorial_review") is False and
                obj.get("publication_approved") is False,
                "historical candidates must remain unapproved")
    require(evidence.get("new_findings_are") ==
            "source_linked_provisional_uncorroborated" and
            evidence.get("original_historical_photographs_examined") is False and
            evidence.get("source_photo_rights_cleared") is False and
            current_evidence.get("independently_corroborated_new_findings") == 0,
            "photo/source limitations lost")
    require(snapshot.get("blockers") == manifest.get("blockers") and
            isinstance(snapshot.get("blockers"), list) and snapshot["blockers"],
            "outstanding evidence blockers changed")

    for group in ("reconciliation_artifact_paths", "research_batch_artifact_paths",
                  "chapter_audit_artifact_paths", "coverage_artifact_paths"):
        snapshot_paths = snapshot.get(group)
        manifest_paths = manifest.get(group)
        require(isinstance(snapshot_paths, list) and snapshot_paths and
                isinstance(manifest_paths, list) and
                all(isinstance(path, str) and path in manifest_paths
                    for path in snapshot_paths),
                "missing bound research path in " + group)
    require(snapshot.get("chapter_audit_artifact_paths", [])[-1] ==
            manifest.get("chapter_audit_artifact_paths", [])[-1] and
            snapshot.get("coverage_artifact_paths", [])[-1] ==
            manifest.get("coverage_artifact_paths", [])[-1],
            "latest audit or coverage omitted")
    return True
