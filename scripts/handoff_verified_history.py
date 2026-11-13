"""Strict validation of the research team's versioned v4 history handoff.

This validates *metadata provenance only*. It cannot turn candidate historical
research into approved prose. The caller verifies each file's Git blob and
the compressed SQLite / replay checksums independently.
"""


def require(condition, reason):
    if not condition:
        raise ValueError("History v4 handoff: " + reason)


def validate_verified_history_v4(manifest, snapshot):
    require(snapshot.get("schema_version") == 4 and
            snapshot.get("kind") == "verified_research_to_app_handoff_history",
            "unsupported historical handoff")
    require(manifest.get("schema_version") == 4 and
            manifest.get("handoff_history_append_only") is True,
            "manifest must be versioned, append-only research")
    for key in ("research_commit_sha", "canonical_version", "canonical_hash"):
        require(snapshot.get(key) == manifest.get(key), "identity drift: " + key)
    require(snapshot.get("replay_persistence_commit_sha") ==
            manifest.get("verified_replay_commit_sha"),
            "verified replay commit does not match")
    require(snapshot.get("previous_manifest_sha") ==
            manifest.get("previous_manifest_blob_sha"),
            "previous-manifest history is not bound")

    require(snapshot.get("canonical_version") == "V97" and
            snapshot.get("canonical_status") == "unchanged_not_promoted" and
            manifest.get("canonical_status") ==
            "unchanged_provisional_V97_not_promoted", "canonical status")
    for obj, flag in ((manifest, "canonical_promoted"),
                      (manifest, "ready_for_publication"),
                      (manifest, "ready_for_editorial_review"),
                      (snapshot, "canonical_promoted"),
                      (snapshot, "publication_approved")):
        require(obj.get(flag) is False, "approval/promotion must be explicitly false: " + flag)
    require(snapshot.get("main_modified") is False,
            "research snapshot must not claim to modify main")
    evidence = snapshot.get("historical_evidence")
    current_evidence = manifest.get("evidence_status")
    require(isinstance(evidence, dict) and isinstance(current_evidence, dict),
            "evidence fields missing")
    for flag in ("ready_for_editorial_review", "ready_for_publication"):
        require(evidence.get(flag) is False, "snapshot evidence not reviewable/publishable")
    for flag in ("ready_for_editorial_review", "publication_approved"):
        require(current_evidence.get(flag) is False, "manifest evidence approval invalid")

    canonical_fields = {
        "sources": "sources", "claims": "claims",
        "claim_sources": "claim_source_links", "canonical_findings": "findings",
        "canonical_source_inspections": "source_inspections",
    }
    canonical = snapshot.get("canonical_counts")
    current_canonical = manifest.get("canonical")
    require(isinstance(canonical, dict) and isinstance(current_canonical, dict),
            "canonical counts absent")
    for history_key, manifest_key in canonical_fields.items():
        val = canonical.get(history_key)
        require(type(val) is int and val == current_canonical.get(manifest_key),
                "canonical counts differ: " + history_key)

    staged_fields = {
        "research_batches": "github_batches_replayed",
        "assertion_bearing_finding_ids": "github_distinct_substantive_finding_ids",
        "inspection_metadata_entries": "github_inspection_entries",
        "source_candidate_identities": "github_source_candidates",
        "unresolved_source_refs": "unknown_source_refs",
        "source_metadata_collisions": "source_metadata_collisions",
        "index_only_unresolved": "github_index_only_refs_unresolved",
    }
    staged = snapshot.get("staged_counts")
    current_staged = manifest.get("staged_counts")
    previous = snapshot.get("previous_counts")
    require(all(isinstance(x, dict) for x in (staged, current_staged, previous)),
            "staged/previous counts missing")
    for history_key, manifest_key in staged_fields.items():
        val = staged.get(history_key)
        require(type(val) is int and val >= 0 and
                val == current_staged.get(manifest_key),
                "staged counts differ: " + history_key)
    for key in ("research_batches", "assertion_bearing_finding_ids",
                "inspection_metadata_entries", "source_candidate_identities"):
        require(type(previous.get(key)) is int and
                0 <= previous[key] <= staged[key],
                "research before/after counters regressed: " + key)

    for history_key, manifest_key in (
        ("new_findings", "new_historical_finding_candidates_researched_this_run"),
        ("new_source_candidates", "new_source_candidate_records_this_run"),
        ("new_inspection_metadata", "new_source_inspection_metadata_this_run"),
    ):
        val = evidence.get(history_key)
        require(type(val) is int and val >= 0 and
                val == current_evidence.get(manifest_key),
                "candidate evidence count differs: " + history_key)
    require(staged["research_batches"] - previous["research_batches"] >= 1,
            "no versioned new batch")
    require(evidence["new_findings"] ==
            staged["assertion_bearing_finding_ids"] -
            previous["assertion_bearing_finding_ids"],
            "new findings do not reconcile")
    require(evidence["new_source_candidates"] ==
            staged["source_candidate_identities"] -
            previous["source_candidate_identities"],
            "new sources do not reconcile")
    require(evidence["new_inspection_metadata"] ==
            staged["inspection_metadata_entries"] -
            previous["inspection_metadata_entries"],
            "new source inspections do not reconcile")

    verification = snapshot.get("verification")
    require(isinstance(verification, dict) and
            verification.get("sqlite_integrity") == "ok" and
            verification.get("foreign_key_violations") == 0 and
            verification.get("canonical_rows_unchanged") is True and
            verification.get("canonical_tables_preserved") == 88,
            "SQLite integrity/canonical preservation not verified")
    readback = verification.get("github_readback")
    require(isinstance(readback, dict) and
            all(isinstance(readback.get(k), str) and
                len(readback[k]) == 40 and
                all(c in "0123456789abcdef" for c in readback[k])
                for k in ("replay_report_blob_sha", "compressed_sha_file_blob_sha")),
            "missing pinned GitHub readback blobs")
    require(isinstance(verification.get("github_actions_run"), str) and
            verification["github_actions_run"].startswith(
                "https://github.com/lizperry81/mexico-city-field-guide/actions/runs/") and
            verification.get("github_actions_conclusion") == "success",
            "research replay CI proof absent")

    require(snapshot.get("uncompressed_sqlite_sha256") ==
            manifest.get("versioned_research_sha256") and
            snapshot.get("compressed_sha256") ==
            manifest.get("compressed_sha256"),
            "SQLite checksums differ")
    artifacts = snapshot.get("artifact_paths")
    require(isinstance(artifacts, dict), "missing named artifact paths")
    for key, current_key in (("sqlite", "versioned_research_sqlite_gz_path"),
                             ("report", "replay_report_path")):
        require(artifacts.get(key) == manifest.get(current_key),
                "versioned file mismatch: " + key)
    for key, group in (("batch", "research_batch_artifact_paths"),
                       ("audit", "chapter_audit_artifact_paths"),
                       ("coverage", "coverage_artifact_paths"),
                       ("ledger", "reconciliation_artifact_paths"),
                       ("compressed_sha", "reconciliation_artifact_paths")):
        path = artifacts.get(key)
        require(isinstance(path, str) and path in manifest.get(group, []),
                "unbound research artifact: " + key)
    for key, group in (("chapter_audit_artifact_paths",
                        "chapter_audit_artifact_paths"),
                       ("coverage_artifact_paths",
                        "coverage_artifact_paths")):
        values = evidence.get(key)
        require(isinstance(values, list) and values and
                all(isinstance(path, str) and path in manifest.get(group, [])
                    for path in values),
                "unbound editorial evidence paths: " + key)
    require(artifacts["audit"] in evidence["chapter_audit_artifact_paths"] and
            artifacts["coverage"] in evidence["coverage_artifact_paths"],
            "latest audit/coverage not included in evidence")
    require(isinstance(evidence.get("editorial_conflict"), str) and
            bool(evidence["editorial_conflict"].strip()) and
            isinstance(evidence.get("source_access"), str) and
            bool(evidence["source_access"].strip()),
            "provisional historical conflict/source-access limitations lost")
    require(snapshot.get("blockers") == manifest.get("blockers") and
            isinstance(snapshot.get("blockers"), list) and snapshot["blockers"],
            "unresolved research blockers changed")
    return readback
