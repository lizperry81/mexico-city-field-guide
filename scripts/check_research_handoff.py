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
from handoff_verified_history import validate_verified_history_v4
from handoff_immutable_batch import validate_immutable_batch_v4
from handoff_new_audits import parse_new_audit
from handoff_82_history import validate_frozen as validate_82_frozen, validate_ledger as validate_82_ledger
from handoff_83_history import validate_frozen as validate_83_frozen, validate_ledger as validate_83_ledger
from handoff_84_history import validate_frozen as validate_84_frozen, validate_ledger as validate_84_ledger
from handoff_86_history import validate_frozen as validate_86_frozen, validate_ledger as validate_86_ledger
from handoff_87_history import validate_frozen as validate_87_frozen, validate_ledger as validate_87_ledger
from handoff_88_history import validate_frozen as validate_88_frozen, validate_ledger as validate_88_ledger
from handoff_89_history import validate_frozen as validate_89_frozen, validate_ledger as validate_89_ledger
from handoff_90_history import CONTRACT as CONTRACT_90, validate_frozen as validate_90_frozen, validate_ledger as validate_90_ledger
from handoff_91_history import (
    CONTRACT as CONTRACT_91, KIND as KIND_91,
    validate_frozen as validate_91_frozen,
    validate_ledger as validate_91_ledger,
)

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


def verified_index_only_total(declared, replay_total, te28_reclassified, snapshot_kind):
    """Require exact replay semantics plus the pinned historical TE28 repair.

    New frozen manifests and immutable batch records carry the full historical
    total directly in both their pointer and replay (23). Older v4 history
    records carried the post-reclassification count (18) in the replay and
    needed the TE28 delta (5). Never accept an arbitrary five-count drift.
    """
    if (type(declared) is not int or type(replay_total) is not int
            or type(te28_reclassified) is not int or te28_reclassified < 0):
        return False
    if snapshot_kind in ("research_to_app_handoff", "immutable_research_batch_handoff",
                         "research_to_app_handoff_immutable_snapshot",
                         "append_only_research_to_app_verified_handoff",
                         "append_only_research_handoff_history",
                         "append_only_research_to_app_handoff_history",
                         "verified_noncanonical_research_to_app_handoff_history",
                         "research_to_app_handoff_append_only_history",
                         "append_only_research_to_app_verified_history",
                         "immutable_research_handoff_history_entry",
                         "immutable_research_to_app_handoff_history"):
        return declared == replay_total
    return declared == replay_total + te28_reclassified


def validate_versioned_handoff(manifest, immutable_manifest, snapshot_sha):
    """Verify complete immutable handoffs without accepting snapshot drift.

    v2 requires identical files. v3 accepts two explicitly bound encodings.
    v4 accepts identical manifests, verified replay records, or a new
    append-only research snapshot with individually cross-checked identities,
    evidence counts, source manifests, and immutable artifacts.
    """
    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == KIND_91):
        validate_91_frozen(manifest, immutable_manifest)
        return

    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "immutable_research_handoff_history_entry"):
        if manifest.get("handoff_contract_status") == CONTRACT_90:
            validate_90_frozen(manifest, immutable_manifest)
        else:
            validate_89_frozen(manifest, immutable_manifest)
        return

    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "append_only_research_to_app_verified_history"):
        if manifest.get('handoff_contract_status') == '88_batch_sqlite_integrity_github_full_binary_sha256_verified_noncanonical_unapproved':
            validate_88_frozen(manifest, immutable_manifest)
        else:
            validate_87_frozen(manifest, immutable_manifest)
        return

    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "research_to_app_handoff_append_only_history"):
        current_reader = git("rev-parse", "HEAD:poi/templo-mayor/reader.html").decode().strip()
        validate_86_frozen(manifest, immutable_manifest, current_reader)
        return

    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "verified_noncanonical_research_to_app_handoff_history"):
        if "main_reader_blob_verified" in immutable_manifest.get("integrity", {}):
            main_reader = git("rev-parse", "HEAD:poi/templo-mayor/reader.html").decode().strip()
            validate_84_frozen(manifest, immutable_manifest, main_reader)
        else:
            validate_83_frozen(manifest, immutable_manifest)
        return

    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "append_only_research_to_app_handoff_history"):
        validate_82_frozen(manifest, immutable_manifest)
        return

    # Batch 81 uses a compact append-only history record. The producer did
    # not receive a replay commit SHA from its connector, so bind the exact
    # independently read-back Git blobs AND the committed integrity ledger.
    # This authorization is strictly for a private human review queue.
    if (manifest.get("schema_version") == 4 and
            immutable_manifest.get("kind") == "append_only_research_handoff_history"):
        frozen = immutable_manifest
        staged = manifest.get("staged_counts", {})
        evidence = manifest.get("evidence_status", {})
        readback = manifest.get("verified_binary_readback", {})
        replay = manifest.get("replay_evidence", {})
        if (frozen.get("schema_version") != 4
                or frozen.get("branch") != "research-persistence"
                or frozen.get("canonical_status") != "unchanged_provisional_V97_not_promoted"
                or manifest.get("canonical_status") != frozen["canonical_status"]
                or frozen.get("ready_for_editorial_review") is not False
                or frozen.get("ready_for_publication") is not False
                or frozen.get("canonical_promoted") is not False
                or frozen.get("automatically_merged") is not False
                or frozen.get("main_modified") is not False
                or manifest.get("ready_for_editorial_review") is not False
                or manifest.get("ready_for_publication") is not False
                or manifest.get("canonical_promoted") is not False
                or evidence.get("publication_approved") is not False
                or evidence.get("independently_corroborated_new_findings") != 0
                or manifest.get("verified_replay_commit_sha") is not None
                or readback.get("commit_sha") is not None):
            raise ValueError("Compact 81-batch history cannot authorize publication")
        for key in ("research_commit_sha", "canonical_version", "canonical_hash",
                    "versioned_research_sqlite_gz_path", "versioned_research_sha256",
                    "compressed_sha256"):
            if frozen.get(key) != manifest.get(key):
                raise ValueError("Compact immutable history changed: " + key)
        for key in ("github_batches_replayed",
                    "github_distinct_substantive_finding_ids",
                    "github_source_candidates", "github_inspection_entries",
                    "unknown_source_refs", "source_metadata_collisions",
                    "detached_source_identity_review_pending",
                    "new_source_candidates_all_types_this_run",
                    "new_source_inspection_metadata_this_run"):
            if frozen.get("staged_counts", {}).get(key) != staged.get(key):
                raise ValueError("Compact immutable staged count changed: " + key)
        if (frozen.get("staged_counts", {}).get("unresolved_index_only_ids") !=
                staged.get("github_index_only_refs_unresolved") or
                frozen.get("staged_counts", {}).get("new_historical_finding_candidates_this_run") !=
                evidence.get("new_historical_finding_candidates_researched_this_run")):
            raise ValueError("Compact immutable historical finding counts changed")
        for group in ("coverage_artifact_paths", "chapter_audit_artifact_paths",
                      "reconciliation_artifact_paths"):
            subset = frozen.get(group)
            if (not isinstance(subset, list) or not subset or
                    not set(subset).issubset(set(manifest.get(group, [])))):
                raise ValueError("Compact immutable research artifact paths changed: " + group)
        if (frozen.get("batch_path") not in manifest.get("research_batch_artifact_paths", [])
                or frozen.get("github_binary_blob_sha") != readback.get("git_blob_sha")
                or frozen.get("github_binary_blob_sha") != replay.get("readback_binary_git_blob_sha")
                or readback.get("report_blob_sha") != replay.get("readback_report_git_blob_sha")
                or readback.get("verified_report_path") != manifest.get("replay_report_path")
                or replay.get("verification_ledger") not in frozen["reconciliation_artifact_paths"]
                or readback.get("compressed_sha256") != manifest.get("compressed_sha256")
                or readback.get("uncompressed_sqlite_sha256") !=
                manifest.get("versioned_research_sha256")
                or readback.get("sqlite_integrity") != "ok"
                or readback.get("foreign_key_violations") != 0
                or readback.get("canonical_rows_unchanged") is not True
                or readback.get("compress_digest_recomputed_independently_from_github_fetched_base64") is not True):
            raise ValueError("Compact immutable history lacks independently pinned readback")
        proof = frozen.get("verification", {})
        if (proof.get("sqlite_integrity") != "ok"
                or proof.get("foreign_key_violations") != 0
                or proof.get("canonical_tables_preserved") != 88
                or proof.get("canonical_rows_unchanged") is not True
                or proof.get("github_readback_compressed_digest_match") is not True):
            raise ValueError("Compact immutable research replay verification changed")
        return

    version = manifest.get("schema_version")
    if version == 4 and immutable_manifest.get("kind") == "append_only_research_to_app_verified_handoff":
        # The producer separates the input research SHA from a later verified
        # replay commit. Both must match the immutable history and the pointer.
        field_pairs = (
            ("source_research_commit_sha", "research_commit_sha"),
            ("verified_replay_commit_sha", "verified_replay_commit_sha"),
            ("canonical_version", "canonical_version"),
            ("canonical_hash", "canonical_hash"),
            ("versioned_research_sqlite_gz_path", "versioned_research_sqlite_gz_path"),
            ("versioned_research_sha256", "versioned_research_sha256"),
            ("compressed_sha256", "compressed_sha256"),
            ("verified_replay_report_path", "replay_report_path"),
        )
        for old_key, new_key in field_pairs:
            if immutable_manifest.get(old_key) != manifest.get(new_key):
                raise ValueError("Immutable readback research identity changed: " + old_key)
        # The producer's 80-batch history records the evidence delta in a
        # shorter, independently versioned summary. Match EVERY quantitative
        # claim against the rolling manifest and retain publication safeguards.
        # Older full evidence-status snapshots still require exact equality.
        frozen_evidence = immutable_manifest.get("evidence_status")
        rolling_evidence = manifest.get("evidence_status")
        if frozen_evidence != rolling_evidence:
            if (not isinstance(frozen_evidence, dict)
                    or not isinstance(rolling_evidence, dict)
                    or set(frozen_evidence) != {
                        "new_findings", "new_sources", "new_inspections",
                        "independent_corroboration", "publication_approved",
                        "source_types"}
                    or any(type(frozen_evidence[k]) is not int or frozen_evidence[k] < 0
                           for k in ("new_findings", "new_sources", "new_inspections"))
                    or frozen_evidence["new_findings"] != rolling_evidence.get(
                        "new_historical_finding_candidates_researched_this_run")
                    or frozen_evidence["new_sources"] != manifest.get(
                        "staged_counts", {}).get("new_source_candidates_all_types_this_run")
                    or frozen_evidence["new_inspections"] != rolling_evidence.get(
                        "new_source_inspection_metadata_this_run")
                    or frozen_evidence["independent_corroboration"] is not False
                    or rolling_evidence.get("independently_corroborated_new_findings") != 0
                    or frozen_evidence["publication_approved"] is not False
                    or rolling_evidence.get("publication_approved") is not False
                    or rolling_evidence.get("ready_for_editorial_review") is not False
                    or not isinstance(frozen_evidence["source_types"], str)
                    or not frozen_evidence["source_types"].strip()):
                raise ValueError("Immutable readback evidence counts or approval changed")
        no_merge = immutable_manifest.get("no_automatic_merge") is True
        if immutable_manifest.get("no_automatic_merge") is None:
            # The new compact handoff encodes the same prohibition in an
            # immutable instruction; require BOTH producer and rolling
            # manifest to forbid automatic merge and publication explicitly.
            frozen_instruction = immutable_manifest.get("consumer_instruction")
            rolling_instruction = manifest.get("consumer_instruction")
            no_merge = (isinstance(frozen_instruction, str) and
                        "Never auto-merge" in frozen_instruction and
                        "publish" in frozen_instruction and
                        isinstance(rolling_instruction, str) and
                        "Do not publish, auto-merge" in rolling_instruction)
        if (immutable_manifest.get("schema_version") != 4
                or immutable_manifest.get("branch") != "research-persistence"
                or immutable_manifest.get("canonical_status") != "unchanged_provisional"
                or manifest.get("canonical_status") != "unchanged_provisional_V97_not_promoted"
                or immutable_manifest.get("ready_for_editorial_review") is not False
                or immutable_manifest.get("ready_for_publication") is not False
                or not no_merge
                or manifest.get("canonical_promoted") is not False
                or manifest.get("ready_for_editorial_review") is not False
                or manifest.get("ready_for_publication") is not False
                or manifest.get("evidence_status", {}).get("publication_approved") is not False
                or manifest.get("evidence_status", {}).get("independently_corroborated_new_findings") != 0):
            raise ValueError("Immutable readback handoff cannot approve publication")
        for old_key, new_key in (
                ("batches", "github_batches_replayed"),
                ("findings", "github_distinct_substantive_finding_ids"),
                ("source_candidates", "github_source_candidates"),
                ("source_inspections", "github_inspection_entries")):
            if (immutable_manifest.get("staged_counts", {}).get(old_key) !=
                    manifest.get("staged_counts", {}).get(new_key)):
                raise ValueError("Immutable readback staged count drift: " + old_key)
        for group in ("chapter_audit_artifact_paths", "coverage_artifact_paths",
                      "research_batch_artifact_paths"):
            # 80-batch shorthand uses 'batch_artifact_paths'. Every path
            # still needs to exist in the committed rolling manifest.
            frozen_group = ("batch_artifact_paths"
                            if group == "research_batch_artifact_paths" and
                            "batch_artifact_paths" in immutable_manifest
                            else group)
            subset = immutable_manifest.get(frozen_group)
            if (not isinstance(subset, list) or not subset or
                    not set(subset).issubset(set(manifest.get(group, [])))):
                raise ValueError("Immutable readback artifact path drift: " + group)
        ledger_paths = immutable_manifest.get("verification_ledger_artifact_paths")
        if ledger_paths is None:
            ledger_paths = [immutable_manifest.get("verification_ledger_path")]
        if (not isinstance(ledger_paths, list) or not ledger_paths or
                any(not isinstance(p, str) or
                    p not in manifest.get("reconciliation_artifact_paths", [])
                    for p in ledger_paths)
                or (manifest.get("replay_evidence", {}).get("verification_ledger") is not None and
                    manifest["replay_evidence"]["verification_ledger"] not in ledger_paths)):
            raise ValueError("Immutable readback ledger not pinned in the manifest")
        return
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
        # Some v4 producers commit a complete frozen copy of the manifest,
        # then append just two Git provenance fields to the moving pointer.
        # Bind the frozen object byte-for-byte by Git blob ID: never allow
        # different research counts, approval flags, or citation metadata.
        if immutable_manifest.get("kind") == "research_to_app_handoff":
            provenance_keys = {"immutable_handoff_blob_sha",
                               "handoff_history_commit_sha"}
            if (set(manifest) - set(immutable_manifest) != provenance_keys
                    or set(immutable_manifest) - set(manifest)
                    or any(manifest[k] != v for k, v in immutable_manifest.items())
                    or manifest.get("immutable_handoff_blob_sha") != snapshot_sha
                    or not isinstance(manifest.get("handoff_history_commit_sha"), str)
                    or not HEX40.fullmatch(manifest["handoff_history_commit_sha"])
                    or manifest.get("canonical_promoted") is not False
                    or manifest.get("ready_for_publication") is not False
                    or manifest.get("ready_for_editorial_review") is not False
                    or manifest.get("evidence_status", {}).get("publication_approved") is not False
                    or manifest.get("replay_evidence", {}).get("integrity") != "ok"
                    or manifest.get("replay_evidence", {}).get("foreign_key_violations") != 0
                    or manifest.get("replay_evidence", {}).get("canonical_rows_unchanged") is not True
                    or manifest.get("replay_evidence", {}).get("github_readback_verified") is not True):
                raise ValueError("Frozen v4 handoff disagrees with its Git-provenance-bound manifest")
            return
        # New v4 history records pin an independent replay, review audit and
        # coverage delta. Validate its complete metadata before accepting.
        if immutable_manifest.get("kind") == "verified_research_to_app_handoff_history":
            validate_verified_history_v4(manifest, immutable_manifest)
            return
        # Newer handoffs use an append-only, research-only snapshot containing
        # a before/after reconciliation record instead of a rolling-manifest
        # copy. Bind every key input/output to that immutable object. Only
        # separately reviewed evidence may ever be published.
        if immutable_manifest.get("kind") == "append_only_research_handoff_snapshot":
            if immutable_manifest.get("schema_version") != 4:
                raise ValueError("Append-only snapshot has wrong schema")
            # November 13 TE28/urban-breadth handoffs use an explicitly
            # versioned database object and more descriptive before/after
            # counters. Compare those fields exactly, not by positional guess.
            if isinstance(immutable_manifest.get("database"), dict):
                db = immutable_manifest["database"]
                if (immutable_manifest.get("research_branch") != "research-persistence"
                        or immutable_manifest.get("canonical_status") != "unchanged_not_promoted"
                        or immutable_manifest.get("canonical_promoted") is not False
                        or immutable_manifest.get("ready_for_editorial_review") is not False
                        or immutable_manifest.get("publication_approved") is not False
                        or manifest.get("canonical_promoted") is not False
                        or manifest.get("ready_for_publication") is not False
                        or manifest.get("ready_for_editorial_review") is not False):
                    raise ValueError("Nested v4 snapshot cannot approve publication")
                for key in ("research_commit_sha", "verified_replay_commit_sha",
                            "canonical_version", "canonical_hash"):
                    if immutable_manifest.get(key) != manifest.get(key):
                        raise ValueError("Nested v4 provenance drift: " + key)
                if (not isinstance(immutable_manifest.get("pipeline_fix_commit_sha"), str)
                        or not HEX40.fullmatch(immutable_manifest["pipeline_fix_commit_sha"])):
                    raise ValueError("Nested v4 missing pipeline provenance")
                for db_key, handoff_key in (
                    ("sqlite_gz", "versioned_research_sqlite_gz_path"),
                    ("replay_report", "replay_report_path"),
                    ("compressed_sha256", "compressed_sha256"),
                    ("sqlite_sha256", "versioned_research_sha256"),
                ):
                    if db.get(db_key) != manifest.get(handoff_key):
                        raise ValueError("Nested v4 database drift: " + db_key)
                if (db.get("integrity") != "ok"
                        or db.get("foreign_key_violations") != 0
                        or db.get("canonical_rows_unchanged") is not True
                        or db.get("original_V97_tables_preserved") != 88):
                    raise ValueError("Nested v4 replay integrity unverified")
                for key, value in manifest.get("canonical", {}).items():
                    if immutable_manifest.get("canonical_counts", {}).get(key) != value:
                        raise ValueError("Nested v4 canonical count drift: " + key)
                before = immutable_manifest.get("before")
                after = immutable_manifest.get("after")
                if not isinstance(before, dict) or not isinstance(after, dict):
                    raise ValueError("Nested v4 snapshot lacks before/after checks")
                metrics = {
                    "github_batches_replayed": "github_batch_files",
                    "github_distinct_substantive_finding_ids":
                        "assertion_bearing_staged_finding_ids",
                    "github_inspection_entries": "inspection_metadata",
                    "github_source_candidates": "source_candidate_ids",
                    "unknown_source_refs": "unresolved_source_ids",
                    "source_metadata_collisions": "source_metadata_collisions",
                    "github_index_only_refs_unresolved": "index_only_unresolved",
                }
                for current_key, snapshot_key in metrics.items():
                    if (not isinstance(after.get(snapshot_key), int)
                            or after[snapshot_key] !=
                            manifest.get("staged_counts", {}).get(current_key)):
                        raise ValueError("Nested v4 staged metrics drift: " + current_key)
                for key in ("github_batch_files", "assertion_bearing_staged_finding_ids",
                            "inspection_metadata", "source_candidate_ids"):
                    if (not isinstance(before.get(key), int)
                            or before[key] > after[key]):
                        raise ValueError("Nested v4 research history regressed: " + key)
                changes = immutable_manifest.get("changes", {})
                if (changes.get("legacy_TE28_findings_reclassified_from_index_only_to_substantive")
                        != before.get("index_only_unresolved") - after.get("index_only_unresolved")
                        or changes.get("new_historical_finding_candidates") !=
                        manifest.get("evidence_status", {}).get("new_historical_finding_candidates_researched_this_run")
                        or changes.get("new_source_candidates") !=
                        after["source_candidate_ids"] - before["source_candidate_ids"]
                        or changes.get("new_inspection_metadata_entries") !=
                        after["inspection_metadata"] - before["inspection_metadata"]):
                    raise ValueError("Nested v4 restoration/evidence metrics drift")
                evidence = immutable_manifest.get("evidence_status", {})
                current_evidence = manifest.get("evidence_status", {})
                if (evidence.get("publication_approved") is not False
                        or evidence.get("ready_for_editorial_review") is not False
                        or current_evidence.get("publication_approved") is not False
                        or current_evidence.get("ready_for_editorial_review") is not False):
                    raise ValueError("Nested v4 evidence cannot authorize publication")
                for snapshot_key, current_key in (
                    ("full_public_institutional_html_pages_examined_this_run",
                     "new_public_institutional_html_source_inspections_this_run"),
                    ("independently_corroborated_new_findings",
                     "independently_corroborated_new_findings"),
                ):
                    if evidence.get(snapshot_key) != current_evidence.get(current_key):
                        raise ValueError("Nested v4 source access/evidence drift: " + current_key)
                for group in ("chapter_audit_artifact_paths", "coverage_artifact_paths",
                              "research_batch_artifact_paths", "reconciliation_artifact_paths"):
                    paths = immutable_manifest.get(group)
                    if (not isinstance(paths, list) or not paths
                            or not set(paths).issubset(set(manifest.get(group, [])))):
                        raise ValueError("Nested v4 missing versioned artifacts: " + group)
                return
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

        # Versioned 69-batch source and historic-photo research uses a
        # distinct immutable metadata record. Verify evidence deltas, exact Git
        # identity, and explicit nonpublication flags before private review.
        if immutable_manifest.get("kind") == "immutable_research_batch_handoff":
            validate_immutable_batch_v4(manifest, immutable_manifest, snapshot_sha)
            return

        # New 1847/source-identity handoffs are immutable delta records, not
        # copies of the rolling manifest. Validate explicit provenance/counts
        # without granting staged research editorial publication authority.
        if immutable_manifest.get("kind") == "immutable_cross_automation_research_handoff":
            if (immutable_manifest.get("schema_version") != 4
                    or immutable_manifest.get("canonical_status") != "unchanged"
                    or immutable_manifest.get("ready_for_publication") is not False
                    or immutable_manifest.get("ready_for_editorial_review") is not False
                    or immutable_manifest.get("publication_approved") is True
                    or manifest.get("canonical_promoted") is not False
                    or manifest.get("ready_for_publication") is not False
                    or manifest.get("ready_for_editorial_review") is not False
                    or manifest.get("evidence_status", {}).get("publication_approved") is not False):
                raise ValueError("Cross-automation v4 snapshot cannot publish research")
            for field in ("research_commit_sha", "verified_replay_commit_sha",
                          "canonical_version", "canonical_hash",
                          "previous_manifest_blob_sha", "compressed_sha256"):
                if immutable_manifest.get(field) != manifest.get(field):
                    raise ValueError("Cross-automation v4 identity drift: " + field)
            for snapshot_field, manifest_field in (
                ("versioned_sqlite_gz_path", "versioned_research_sqlite_gz_path"),
                ("versioned_sqlite_sha256", "versioned_research_sha256"),
                ("verified_replay_report_path", "replay_report_path"),
                ("reconciliation_ledger_path", "source_identity_crosswalk_path"),
            ):
                if (not isinstance(immutable_manifest.get(snapshot_field), str)
                        or immutable_manifest[snapshot_field] != manifest.get(manifest_field)):
                    raise ValueError("Cross-automation v4 artifact drift: " + snapshot_field)
            original = immutable_manifest.get("original_research_batch_commit_sha")
            if not isinstance(original, str) or not HEX40.fullmatch(original):
                raise ValueError("Cross-automation v4 missing original batch provenance")
            before, after = immutable_manifest.get("before"), immutable_manifest.get("after")
            if not isinstance(before, dict) or not isinstance(after, dict):
                raise ValueError("Cross-automation v4 missing before/after counts")
            metric_pairs = {
                "batch_files": "github_batches_replayed",
                "staged_substantive_findings": "github_distinct_substantive_finding_ids",
                "inspection_metadata_rows": "github_inspection_entries",
                "source_candidates": "github_source_candidates",
                "missing_registered_sources": "unknown_source_refs",
            }
            for snapshot_key, handoff_key in metric_pairs.items():
                count = after.get(snapshot_key)
                if (type(count) is not int or count < 0
                        or count != manifest.get("staged_counts", {}).get(handoff_key)):
                    raise ValueError("Cross-automation v4 staged count drift: " + handoff_key)
            for key in ("batch_files", "staged_substantive_findings",
                        "inspection_metadata_rows", "source_candidates"):
                if (type(before.get(key)) is not int
                        or before[key] < 0 or before[key] > after[key]):
                    raise ValueError("Cross-automation v4 replay history regressed: " + key)
            evidence = manifest.get("evidence_status", {})
            changes = (
                ("staged_substantive_findings", "new_findings_staged",
                 "new_historical_finding_candidates_researched_this_run"),
                ("inspection_metadata_rows", "new_inspection_metadata",
                 "new_source_inspection_metadata_this_run"),
            )
            for count_key, snapshot_key, handoff_key in changes:
                if (after[count_key] - before[count_key] != immutable_manifest.get(snapshot_key)
                        or immutable_manifest.get(snapshot_key) != evidence.get(handoff_key)):
                    raise ValueError("Cross-automation v4 evidence delta drift: " + snapshot_key)
            if (after["source_candidates"] - before["source_candidates"] !=
                    evidence.get("new_source_candidate_records_this_run")):
                raise ValueError("Cross-automation v4 source-candidate delta drift")
            if (immutable_manifest.get("independent_corroborations") !=
                    evidence.get("independently_corroborated_new_findings")
                    or evidence.get("ready_for_editorial_review") is not False):
                raise ValueError("Cross-automation v4 cannot claim independent evidence approval")
            if (not isinstance(immutable_manifest.get("replay_workflow_url"), str)
                    or not immutable_manifest["replay_workflow_url"].startswith(
                        "https://github.com/lizperry81/mexico-city-field-guide/actions/runs/")):
                raise ValueError("Cross-automation v4 replay proof URL missing")
            for group in ("research_batch_artifact_paths",
                          "coverage_artifact_paths", "chapter_audit_artifact_paths"):
                snapshot_paths = immutable_manifest.get(group)
                if (not isinstance(snapshot_paths, list) or not snapshot_paths
                        or not set(snapshot_paths).issubset(set(manifest.get(group, [])))):
                    raise ValueError("Cross-automation v4 research artifacts drift: " + group)
            return

        # The current producer emits an immutable, research-only audit record
        # with its own source/coverage/batch path lists. Bind its entire staged
        # identity to the rolling manifest and the EXACT committed Git blob.
        # A missing or mismatched claimed blob is a hard failure, never a
        # reason to accept the most recent moving branch head instead.
        if immutable_manifest.get("kind") == "immutable_research_to_app_handoff":
            shared = (
                "schema_version", "research_commit_sha",
                "verified_replay_commit_sha", "previous_manifest_blob_sha",
                "previous_manifest_generated_at", "canonical_version",
                "canonical_hash", "canonical_status", "canonical",
                "staged_counts", "versioned_research_sqlite_gz_path",
                "versioned_research_sha256", "compressed_sha256",
                "replay_report_path", "evidence_status", "replay_evidence",
                "ready_for_editorial_review", "ready_for_publication",
                "blockers",
            )
            for field in shared:
                if immutable_manifest.get(field) != manifest.get(field):
                    raise ValueError("Immutable v4 research record drift: " + field)
            if manifest.get("immutable_handoff_blob_sha") != snapshot_sha:
                raise ValueError("Immutable v4 Git blob SHA does not match rolling manifest")
            if (manifest.get("canonical_promoted") is not False
                    or manifest.get("ready_for_publication") is not False
                    or manifest.get("ready_for_editorial_review") is not False
                    or manifest.get("canonical_status") !=
                    "unchanged_provisional_V97_not_promoted"
                    or manifest.get("evidence_status", {}).get("publication_approved") is not False
                    or manifest.get("evidence_status", {}).get("ready_for_editorial_review") is not False
                    or manifest.get("replay_evidence", {}).get("integrity") != "ok"
                    or manifest.get("replay_evidence", {}).get("foreign_key_violations") != 0
                    or manifest.get("replay_evidence", {}).get("canonical_rows_unchanged") is not True
                    or manifest.get("replay_evidence", {}).get("github_readback_verified") is not True):
                raise ValueError("Immutable v4 research evidence remains unverified")
            for record_key, manifest_key in (
                ("chapter_audit_artifact_paths", "chapter_audit_artifact_paths"),
                ("coverage_artifact_paths", "coverage_artifact_paths"),
                ("source_audit_paths", "chapter_audit_artifact_paths"),
                ("batch_artifact_paths", "research_batch_artifact_paths"),
            ):
                paths = immutable_manifest.get(record_key)
                if (not isinstance(paths, list) or not paths
                        or not set(paths).issubset(set(manifest.get(manifest_key, [])))):
                    raise ValueError("Immutable v4 audit artifact drift: " + record_key)
                for path in paths:
                    safe_path(path)
            source_inventory = immutable_manifest.get("inventory_path")
            if (not isinstance(source_inventory, str)
                    or source_inventory not in manifest.get("reconciliation_artifact_paths", [])):
                raise ValueError("Immutable v4 source inventory not bound to manifest")
            safe_path(source_inventory)
            return

        # The latest producer freezes the entire rolling manifest under a
        # different kind, then intends to pin its Git blob and history commit
        # from the moving pointer. Reject missing pins: existence of a file on
        # a mutable branch is insufficient provenance for editorial ingestion.
        if immutable_manifest.get("kind") == "research_to_app_handoff_immutable_snapshot":
            if immutable_manifest.get("schema_version") != 4:
                raise ValueError("Frozen v4 research snapshot schema changed")
            frozen = dict(immutable_manifest)
            pointer = dict(manifest)
            frozen.pop("kind", None)
            pointer.pop("kind", None)
            for provenance in ("immutable_handoff_blob_sha", "handoff_history_commit_sha"):
                if frozen.pop(provenance, None) is not None:
                    raise ValueError("Immutable v4 snapshot has a mutable self-reference")
                pointer.pop(provenance, None)
            if pointer != frozen:
                raise ValueError("Immutable v4 research snapshot differs from rolling manifest")
            if manifest.get("immutable_handoff_blob_sha") != snapshot_sha:
                raise ValueError("Immutable v4 research snapshot lacks an exact Git blob SHA pin")
            origin = manifest.get("handoff_history_commit_sha")
            if not isinstance(origin, str) or not HEX40.fullmatch(origin):
                raise ValueError("Immutable v4 research snapshot lacks a history commit SHA pin")
            if (manifest.get("canonical_promoted") is not False
                    or manifest.get("ready_for_publication") is not False
                    or manifest.get("ready_for_editorial_review") is not False
                    or manifest.get("evidence_status", {}).get("publication_approved") is not False
                    or manifest.get("evidence_status", {}).get("ready_for_editorial_review") is not False
                    or manifest.get("replay_evidence", {}).get("sqlite_integrity") != "ok"
                    or manifest.get("replay_evidence", {}).get("foreign_key_violations") != 0
                    or manifest.get("replay_evidence", {}).get("canonical_rows_unchanged") is not True
                    or manifest.get("replay_evidence", {}).get("github_snapshot_readback") is not True):
                raise ValueError("Immutable v4 research snapshot is not verified or unapproved")
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


def audit_matrix_explicitly_unapproved(doc):
    """Recognize the two evidence-only locator matrix formats, fail closed."""
    if doc.get("proposed_text_is_not_approved") is True:
        return True
    return (
        doc.get("kind") ==
        "templo_mayor_discover_exact_prose_claim_to_source_locator_addendum"
        and doc.get("publication_approved") is False
        and doc.get("ready_for_editorial_review") is False
        and doc.get("main_modified") is False
        and isinstance(doc.get("proposed_unpublished_historical_addition"), str)
        and bool(doc["proposed_unpublished_historical_addition"].strip())
        and isinstance(doc.get("claim_to_source_locator_matrix"), list)
        and bool(doc["claim_to_source_locator_matrix"])
    )


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
    source_sha = (immutable_manifest.get("source_research_commit_sha")
                  if immutable_manifest.get("kind") == "append_only_research_to_app_verified_handoff"
                  else immutable_manifest.get("research_commit_sha"))
    if source_sha != sha:
        raise ValueError("Versioned handoff snapshot points to a different research commit")
    validate_versioned_handoff(manifest, immutable_manifest, snapshot_blob_sha)
    if immutable_manifest.get("kind") == KIND_91:
        # Bind six artifacts to the verified replay commit and the immutable
        # handoff manifest. The ledger alone cannot authorize consumption.
        ledger_path = safe_path(immutable_manifest["latest_reconciliation_ledger_path"])
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        snapshot = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", snapshot, handoff_commit],
                       check=True, capture_output=True)
        actual91 = {}
        for name, path in ledger["paths"].items():
            safe_path(path)
            pinned = git("rev-parse", f"{snapshot}:{path}").decode().strip()
            current = git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
            if pinned != current:
                raise ValueError("91-batch research Git artifact changed: " + path)
            actual91[name] = current
        validate_91_ledger(manifest, immutable_manifest, ledger, actual91)
        canonical91 = manifest["canonical"]
        manifest["canonical"] = {
            "sources": canonical91["sources"], "claims": canonical91["claims"],
            "claim_source_links": canonical91["claim_sources"],
            "findings": canonical91["canonical_findings"],
            "source_inspections": canonical91["canonical_source_inspections"],
        }
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False, "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                manifest["staged_counts"]["new_historical_finding_candidates_this_run"],
        }

    if immutable_manifest.get("kind") == "immutable_research_handoff_history_entry":
        # Producer workflow readback is corroborated against immutable Git
        # objects, then against raw gzip/SHA-256 bytes later in this function.
        ledger_path = safe_path(immutable_manifest["reconciliation_ledger_path"])
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        paths89 = {
            "sqlite": manifest["versioned_research_sqlite_gz_path"],
            "report": manifest["replay_report_path"],
            "checksum": manifest["replay_evidence"]["compressed_checksum_path"],
            "batch": immutable_manifest["source_batch_path"],
            "coverage": immutable_manifest["coverage_artifact_paths"][0],
            "audit": immutable_manifest["chapter_audit_artifact_paths"][0],
        }
        snapshot = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", snapshot, handoff_commit],
                       check=True, capture_output=True)
        actual89 = {}
        for name, path in paths89.items():
            safe_path(path)
            pinned = git("rev-parse", f"{snapshot}:{path}").decode().strip()
            current = git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
            if pinned != current:
                raise ValueError("Research replay Git object changed: " + path)
            actual89[name] = current
        if manifest.get("handoff_contract_status") == CONTRACT_90:
            validate_90_ledger(manifest, immutable_manifest, ledger, {
                "compressed_db": actual89["sqlite"],
                "report": actual89["report"],
                "checksum": actual89["checksum"],
                "batch": actual89["batch"],
                "coverage": actual89["coverage"],
                "audit": actual89["audit"],
            })
        else:
            validate_89_ledger(manifest, immutable_manifest, ledger, actual89)
        canonical89 = manifest["canonical"]
        manifest["canonical"] = {
            "sources": canonical89["sources"], "claims": canonical89["claims"],
            "claim_source_links": canonical89["claim_sources"],
            "findings": canonical89["canonical_findings"],
            "source_inspections": canonical89["canonical_source_inspections"],
        }
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False, "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                manifest["staged_counts"]["new_historical_finding_candidates_this_run"],
        }

    if immutable_manifest.get("kind") == "append_only_research_to_app_verified_history":
        # Independently authenticate the immutable snapshot's Git objects.
        ledger_path = safe_path(immutable_manifest["verification_ledger_path"])
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        source_paths = {
            "sqlite": manifest["versioned_research_sqlite_gz_path"],
            "report": manifest["replay_report_path"],
            "batch": immutable_manifest["source_batch_artifact_paths"][0],
            "coverage": immutable_manifest["coverage_artifact_paths"][0],
            "audit": immutable_manifest["chapter_audit_artifact_paths"][0],
        }
        replay_commit = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", replay_commit,
                        handoff_commit], capture_output=True, check=True)
        actual = {
            label: git("rev-parse", f"{handoff_commit}:{safe_path(path)}").decode().strip()
            for label, path in source_paths.items()
        }
        if ledger.get('kind') == 'github_research_reconciliation_full_binary_readback':
            source_paths.update({'input': immutable_manifest['source_batch_artifact_paths'][0],
                                 'chapter': immutable_manifest['chapter_audit_artifact_paths'][0],
                                 'compressed': manifest['replay_evidence']['compressed_checksum_path']})
            actual.update({name: git('rev-parse', f'{handoff_commit}:{safe_path(path)}').decode().strip()
                           for name, path in source_paths.items()})
        for label, path in source_paths.items():
            if git("rev-parse", f"{replay_commit}:{path}").decode().strip() != actual[label]:
                raise ValueError("Verified Git object changed after replay: " + path)
        if ledger.get('kind') == 'github_research_reconciliation_full_binary_readback':
            validate_88_ledger(manifest, immutable_manifest, ledger, actual)
        else:
            validate_87_ledger(manifest, immutable_manifest, ledger, actual)
        # Adapt the authenticated producer schema only in memory, preserving
        # the earlier v4 nonpublication and canonical-integrity checks.
        original = manifest["canonical"]
        manifest["canonical"] = {
            "sources": original["sources"], "claims": original["claims"],
            "claim_source_links": original["claim_sources"],
            "findings": original["canonical_findings"],
            "source_inspections": original["canonical_source_inspections"],
        }
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False, "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                manifest["staged_counts"]["new_historical_finding_candidates_this_run"],
        }

    if immutable_manifest.get("kind") == "research_to_app_handoff_append_only_history":
        # Authenticate actual repository blobs at the replay and handoff
        # commits. Adapt producer aliases only AFTER strict verification.
        ledger_path = safe_path(manifest["replay_evidence"]["verification_ledger"])
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        paths = {"sqlite": manifest["versioned_research_sqlite_gz_path"],
                 "report": manifest["replay_report_path"]}
        actual = {key: git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
                  for key, path in paths.items()}
        snapshot = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", snapshot, handoff_commit],
                       check=True, capture_output=True)
        for key, path in paths.items():
            if git("rev-parse", f"{snapshot}:{path}").decode().strip() != actual[key]:
                raise ValueError("86-batch Git artifact changed after pinned replay: " + path)
        validate_86_ledger(manifest, immutable_manifest, ledger, actual)
        source_canonical = manifest["canonical"]
        manifest["canonical"] = {
            "sources": source_canonical["sources"],
            "claims": source_canonical["claims"],
            "claim_source_links": source_canonical["claim_sources"],
            "findings": source_canonical["canonical_findings"],
            "source_inspections": source_canonical["canonical_source_inspections"],
        }
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False,
            "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                manifest["staged_counts"]["new_historical_finding_candidates_this_run"],
        }

    if immutable_manifest.get("kind") == "verified_noncanonical_research_to_app_handoff_history":
        # Verify the new 83-batch producer format against committed Git object
        # identities and an independent readback ledger before a PRIVATE queue.
        ledger_path = safe_path(manifest["replay_evidence"]["verification_ledger"])
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        artifact_paths = {
            "sqlite": manifest["versioned_research_sqlite_gz_path"],
            "report": manifest["replay_report_path"],
            "checksum": manifest["replay_evidence"]["compressed_checksum_path"],
        }
        actual = {
            name: git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
            for name, path in artifact_paths.items()
        }
        snapshot_commit = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", snapshot_commit, handoff_commit],
                       capture_output=True, check=True)
        for name, path in artifact_paths.items():
            at_snapshot = git("rev-parse", f"{snapshot_commit}:{path}").decode().strip()
            if at_snapshot != actual[name]:
                raise ValueError("83-batch verified snapshot artifact changed: " + path)
        if ledger.get("kind") == "verified_full_reconciliation_github_binary_readback":
            main_reader = git("rev-parse", "HEAD:poi/templo-mayor/reader.html").decode().strip()
            validate_84_ledger(manifest, ledger, actual, main_reader)
        else:
            validate_83_ledger(manifest, ledger, actual)
        # Translate the producer's unapproved status string ONLY after validation.
        # This is an ephemeral in-memory adapter, never a content publication.
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False,
            "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                manifest["staged_counts"]["new_historical_finding_candidates_this_run"],
        }

    if immutable_manifest.get("kind") == "append_only_research_handoff_history":
        # Cross-check each compact immutable identity with the actual Git
        # object on the manifest-publishing commit. A string that resembles a
        # SHA or a ledger claim alone is never enough to ingest research.
        readback = manifest["verified_binary_readback"]
        ledger_path = manifest["replay_evidence"]["verification_ledger"]
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        actual = {
            "sqlite": git("rev-parse", f"{handoff_commit}:{manifest['versioned_research_sqlite_gz_path']}").decode().strip(),
            "report": git("rev-parse", f"{handoff_commit}:{manifest['replay_report_path']}").decode().strip(),
        }
        checks = ledger.get("verification", {})
        before, after = ledger.get("before"), ledger.get("after")
        staged, canonical = manifest["staged_counts"], manifest["canonical"]
        expected_after = {
            "github_batches": staged["github_batches_replayed"],
            "substantive_finding_ids": staged["github_distinct_substantive_finding_ids"],
            "provisional_source_identities": staged["github_source_candidates"],
            "source_inspection_metadata_rows": staged["github_inspection_entries"],
            "canonical_sources": canonical["sources"],
            "canonical_claims": canonical["claims"],
            "canonical_claim_source_links": canonical["claim_source_links"],
            "canonical_findings": canonical["findings"],
        }
        if (ledger.get("kind") != "reconciliation_integrity_and_persisted_github_readback"
                or ledger.get("schema_version") != 2
                or ledger.get("branch") != "research-persistence"
                or ledger.get("batch_research_commit_sha") != sha
                or ledger.get("canonical_sha256") != manifest["canonical_hash"]
                or ledger.get("snapshot_path") != manifest["versioned_research_sqlite_gz_path"]
                or ledger.get("replay_report_path") != manifest["replay_report_path"]
                or ledger.get("status") != "VERIFIED_VERSIONED_NONCANONICAL_RESEARCH_STAGING"
                or ledger.get("ready_for_editorial_review") is not False
                or ledger.get("ready_for_publication") is not False
                or ledger.get("main_modified") is not False
                or ledger.get("automated_merge") is not False
                or after != expected_after
                or not isinstance(before, dict)
                or any(type(before.get(k)) is not int or before[k] > after[k]
                       for k in ("github_batches", "substantive_finding_ids",
                                 "provisional_source_identities",
                                 "source_inspection_metadata_rows"))
                or after["substantive_finding_ids"] - before["substantive_finding_ids"] !=
                manifest["evidence_status"]["new_historical_finding_candidates_researched_this_run"]
                or after["provisional_source_identities"] - before["provisional_source_identities"] !=
                staged["new_source_candidates_all_types_this_run"]
                or after["source_inspection_metadata_rows"] - before["source_inspection_metadata_rows"] !=
                staged["new_source_inspection_metadata_this_run"]
                or checks.get("gzip_git_blob_sha") != actual["sqlite"]
                or checks.get("replay_report_git_blob_sha") != actual["report"]
                or actual["sqlite"] != readback["git_blob_sha"]
                or actual["report"] != readback["report_blob_sha"]
                or checks.get("compressed_digest_match") is not True
                or checks.get("compressed_sha256_expected") != manifest["compressed_sha256"]
                or checks.get("compressed_sha256_computed_from_github_fetched_bytes") !=
                manifest["compressed_sha256"]
                or checks.get("uncompressed_sqlite_sha256_from_replay_report") !=
                manifest["versioned_research_sha256"]
                or checks.get("integrity_check") != "ok"
                or checks.get("foreign_key_violations") != 0
                or checks.get("canonical_tables_preserved") != 88
                or checks.get("canonical_rows_unchanged") is not True
                or checks.get("branch_readback") is not True
                or checks.get("source_identity_auto_merge") is not False):
            raise ValueError("81-batch independent Git readback ledger failed closed")
    if immutable_manifest.get("kind") == "append_only_research_to_app_handoff_history":
        # Authenticate actual Git blobs at BOTH the pinned replay commit
        # and the manifest-publishing commit. New staged records remain
        # privately reviewable, never public or canonical.
        proof_path = safe_path(manifest["replay_evidence"]["verification_ledger"])
        ledger = json.loads(bound_blob(proof_path).decode("utf-8"))
        actual = {
            "sqlite": git("rev-parse", f"{handoff_commit}:{manifest['versioned_research_sqlite_gz_path']}").decode().strip(),
            "report": git("rev-parse", f"{handoff_commit}:{manifest['replay_report_path']}").decode().strip(),
            "checksum": git("rev-parse", f"{handoff_commit}:{manifest['replay_evidence']['compressed_checksum_path']}").decode().strip(),
        }
        pinned_commit = manifest["verified_replay_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", pinned_commit, handoff_commit],
                       check=True, capture_output=True)
        for artifact, key in (
            (manifest["versioned_research_sqlite_gz_path"], "sqlite"),
            (manifest["replay_report_path"], "report"),
        ):
            if git("rev-parse", f"{pinned_commit}:{artifact}").decode().strip() != actual[key]:
                raise ValueError("82-style Git artifact not pinned to verified replay commit: " + artifact)
        validate_82_ledger(manifest, ledger, actual)
        # Only after provenance, artifact identities and explicit nonapproval
        # have passed, adapt the new producer's status string for the legacy
        # staging and private-queue checks below. Never mutate repository data.
        staged_82 = manifest["staged_counts"]
        manifest["evidence_status"] = {
            "ready_for_editorial_review": False,
            "publication_approved": False,
            "independently_corroborated_new_findings": 0,
            "new_historical_finding_candidates_researched_this_run":
                staged_82["new_historical_finding_candidates_this_run"],
        }

    if (manifest["schema_version"] == 4
            and immutable_manifest.get("kind") in ("research_to_app_handoff",
                                                   "immutable_research_batch_handoff",
                                                   "research_to_app_handoff_immutable_snapshot")
            and immutable_manifest != manifest):
        # Verify the claimed history commit actually contains this immutable
        # Git blob, and is an ancestor of the manifest-publishing commit.
        origin = manifest["handoff_history_commit_sha"]
        subprocess.run(["git", "merge-base", "--is-ancestor", origin, handoff_commit],
                       check=True, capture_output=True)
        if git("rev-parse", f"{origin}:{immutable}").decode().strip() != snapshot_blob_sha:
            raise ValueError("Frozen v4 snapshot not present at pinned history commit")
    if immutable_manifest.get("kind") == "append_only_research_to_app_verified_handoff":
        # Bind readback claims to immutable Git objects at the handoff commit.
        ledger_path = immutable_manifest.get("verification_ledger_path")
        if ledger_path is None:
            ledger_path = manifest["replay_evidence"]["verification_ledger"]
            if ledger_path not in immutable_manifest.get("verification_ledger_artifact_paths", []):
                raise ValueError("Immutable readback ledger is not in history")
        ledger = json.loads(bound_blob(ledger_path).decode("utf-8"))
        if ledger.get("kind") == "independent_full_replay_persistence_readback_verification":
            # Batch 80 records verified Git readback as a flat independent
            # ledger. Check its original branch, replay outputs, unchanged
            # canonical tables and counts against the exact committed files.
            canonical = manifest["canonical"]
            actual_canonical = {
                "sources": canonical["sources"],
                "claims": canonical["claims"],
                "claim_sources": canonical["claim_source_links"],
                "canonical_findings": canonical["findings"],
                "canonical_source_inspections": canonical["source_inspections"],
            }
            staged = manifest["staged_counts"]
            expected_after = {
                "batches": staged["github_batches_replayed"],
                "findings": staged["github_distinct_substantive_finding_ids"],
                "source_candidates": staged["github_source_candidates"],
                "source_inspections": staged["github_inspection_entries"],
                "canonical_sources": canonical["sources"],
                "canonical_claims": canonical["claims"],
                "canonical_links": canonical["claim_source_links"],
                "canonical_findings": canonical["findings"],
            }
            before = ledger.get("before_verified_staged_counts")
            after = ledger.get("after_verified_staged_counts")
            if (ledger.get("schema_version") != 3
                    or ledger.get("branch") != "research-persistence"
                    or ledger.get("source_research_commit_sha") != sha
                    or ledger.get("verified_replay_commit_sha") != manifest["verified_replay_commit_sha"]
                    or ledger.get("canonical_version") != manifest["canonical_version"]
                    or ledger.get("canonical_hash") != manifest["canonical_hash"]
                    or ledger.get("canonical_rows_unchanged") is not True
                    or ledger.get("canonical_tables_preserved") != 88
                    or ledger.get("canonical_counts") != actual_canonical
                    or ledger.get("report_path") != manifest["replay_report_path"]
                    or ledger.get("versioned_research_sqlite_gz_path") != manifest["versioned_research_sqlite_gz_path"]
                    or ledger.get("versioned_research_sha256") != manifest["versioned_research_sha256"]
                    or ledger.get("compressed_sha256") != manifest["compressed_sha256"]
                    or ledger.get("sqlite_integrity") != "ok"
                    or ledger.get("foreign_key_violations") != 0
                    or ledger.get("batch_inventory_matches_new_batch") is not True
                    or ledger.get("canonical_promoted") is not False
                    or ledger.get("ready_for_editorial_review") is not False
                    or ledger.get("ready_for_publication") is not False
                    or after != expected_after
                    or not isinstance(before, dict)
                    or any(type(before.get(k)) is not int or before[k] > after[k]
                           for k in ("batches", "findings", "source_candidates",
                                     "source_inspections"))
                    or after["findings"] - before["findings"] != manifest["evidence_status"]["new_historical_finding_candidates_researched_this_run"]
                    or after["source_candidates"] - before["source_candidates"] != staged["new_source_candidates_all_types_this_run"]
                    or after["source_inspections"] - before["source_inspections"] != staged["new_source_inspection_metadata_this_run"]
                    or ledger.get("source_identity_merge_performed") is not False
                    or len(ledger.get("unknown_source_ids", [])) != staged["unknown_source_refs"]
                    or len(ledger.get("source_metadata_collisions", [])) != staged["source_metadata_collisions"]
                    or ledger.get("detached_inspections") != staged["detached_original_inspection_rows_replayed"]):
                raise ValueError("Compact Git readback ledger does not match verified research")
            for key, path in (
                ("versioned_research_sqlite_gz_git_blob_sha", manifest["versioned_research_sqlite_gz_path"]),
                ("report_git_blob_sha", manifest["replay_report_path"]),
            ):
                if ledger.get(key) != git("rev-parse", f"{handoff_commit}:{path}").decode().strip():
                    raise ValueError("Compact Git readback object identity mismatch: " + key)
        else:
            # Previous independently pinned replay format remains supported.
            checks = ledger.get("checks", {})
            if (not re.fullmatch(r"reconciled_[0-9]+_batch_github_readback_verification",
                                 str(ledger.get("kind", "")))
                    or ledger.get("research_commit_sha") != sha
                    or ledger.get("verified_replay_commit_sha") != manifest["verified_replay_commit_sha"]
                    or ledger.get("replay_report_path") != manifest["replay_report_path"]
                    or ledger.get("verified_snapshot_path") != manifest["versioned_research_sqlite_gz_path"]
                    or ledger.get("verified_handoff_history_path") != immutable
                    or ledger.get("readback_status") != "verified_success_noncanonical"
                    or ledger.get("publication_approved") is not False
                    or checks.get("sqlite_integrity") != "ok"
                    or checks.get("foreign_key_violations") != 0
                    or checks.get("canonical_rows_unchanged") is not True
                    or checks.get("output_uncompressed_sha256") != manifest["versioned_research_sha256"]
                    or checks.get("compressed_sha256") != manifest["compressed_sha256"]
                    or checks.get("github_distinct_findings") != manifest["staged_counts"]["github_distinct_substantive_finding_ids"]
                    or checks.get("raw_git_batch_documents") != manifest["staged_counts"]["github_batches_replayed"]):
                raise ValueError("Immutable readback ledger failed independent checks")
            for key, path in (
                ("compressed_git_blob_sha", manifest["versioned_research_sqlite_gz_path"]),
                ("source_report_git_blob_sha", manifest["replay_report_path"]),
            ):
                if checks.get(key) != git("rev-parse", f"{handoff_commit}:{path}").decode().strip():
                    raise ValueError("Immutable readback Git blob identity mismatch: " + key)
    if immutable_manifest.get("kind") == "immutable_research_batch_handoff":
        for key, expected, path in (
            ("replay_report", immutable_manifest["replay_report_git_blob_sha"],
             manifest["replay_report_path"]),
            ("replay_binary", immutable_manifest["replay_binary_git_blob_sha"],
             manifest["versioned_research_sqlite_gz_path"]),
        ):
            actual = git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
            if actual != expected:
                raise ValueError("Immutable batch Git readback mismatch: " + key)
    if immutable_manifest.get("kind") == "verified_research_to_app_handoff_history":
        # The producer pins the Git blob identities after a successful readback.
        # Compare to the committed artifact, not merely a self-asserted hash.
        readback = immutable_manifest["verification"]["github_readback"]
        for key, path in (
            ("replay_report_blob_sha", manifest["replay_report_path"]),
            ("compressed_sha_file_blob_sha",
             immutable_manifest["artifact_paths"]["compressed_sha"]),
        ):
            actual = git("rev-parse", f"{handoff_commit}:{path}").decode().strip()
            if actual != readback[key]:
                raise ValueError("Research handoff Git readback mismatch: " + key)
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
            actual = replay.get(replay_key)
            declared = staged.get(handoff_key)
            if handoff_key == "github_index_only_refs_total":
                # The TE28 repair reclassified five previously index-only
                # identifiers as assertion-bearing records. The handoff keeps
                # the historical total; the latest replay counts the remaining
                # index-only references. Require the exact documented delta.
                changes = immutable_manifest.get("changes", {})
                restored = changes.get(
                    "legacy_TE28_findings_reclassified_from_index_only_to_substantive")
                if immutable_manifest.get("kind") in ("verified_research_to_app_handoff_history",
                                                      "immutable_cross_automation_research_handoff",
                                                      "immutable_research_batch_handoff",
                                                      "research_to_app_handoff",
                                                      "append_only_research_to_app_verified_handoff",
                                                      "append_only_research_handoff_history",
                                                      "append_only_research_to_app_handoff_history",
                                                      "verified_noncanonical_research_to_app_handoff_history",
                                                      "research_to_app_handoff_append_only_history",
                                                      "append_only_research_to_app_verified_history",
                                                      "immutable_research_handoff_history_entry",
                                                       "immutable_research_to_app_handoff_history"):
                    # The compact later handoff has no 'changes' section.
                    # Recover the earlier TE28 reclassification ONLY from its
                    # pinned, append-only historical record, not a guessed delta.
                    te28_path = ("research/handoff/history/"
                        "20261113T1004Z-te28-schema-repair-and-reform-urban-breadth.json")
                    if te28_path not in manifest.get("handoff_history_paths", []):
                        raise ValueError("v4 missing historical TE28 index-only repair")
                    te28 = json.loads(bound_blob(te28_path).decode("utf-8"))
                    if (te28.get("kind") != "append_only_research_handoff_snapshot"
                            or te28.get("canonical_hash") != manifest.get("canonical_hash")
                            or te28.get("publication_approved") is not False
                            or te28.get("canonical_promoted") is not False):
                        raise ValueError("v4 TE28 recovery history is not validated")
                    restored = te28.get("changes", {}).get(
                        "legacy_TE28_findings_reclassified_from_index_only_to_substantive")
                # In the 69-batch replay the producer now reports the full
                # historical index-only total (23), including the five TE28
                # identifiers already reclassified. Earlier replay formats
                # reported the post-reclassification remainder instead.
                # Require the pinned TE28 evidence either way.
                if not verified_index_only_total(
                        declared, actual, restored, immutable_manifest.get("kind")):
                    raise ValueError("v4 index-only recovery totals unverified")
                continue
            if not isinstance(declared, int) or declared != actual:
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
                        for key in ("claims", "evidence_entries", "claim_to_source",
                                    "claim_to_source_locator_matrix", "claim_source_locator_matrix", "clauses",
                                     "claim_to_reading_gate", "passages",
                                    "gates", "reader_anchors"))):
            raise ValueError("Invalid chapter audit format: " + path)
        if (audit_doc.get("ready_for_publication") is True or
                audit_doc.get("editorial_approved") is True or
                audit_doc.get("publication_approved") is True or
                (audit_doc.get("claim_to_source_locator_matrix") is not None
                 and not audit_matrix_explicitly_unapproved(audit_doc))):
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
    source_locator_slots = []
    exact_reader_audits = []
    for audit_path, audit_doc in audits:
        # Strict typed audits remain private and cannot authorize manuscript
        # publication. The current-reader audit is bound to its Git blob ID.
        current_reader_blob = git(
            "rev-parse", "HEAD:poi/templo-mayor/reader.html").decode().strip()
        typed_items = parse_new_audit(audit_path, audit_doc, current_reader_blob)
        if typed_items is not None:
            queue.extend(typed_items)
            if (audit_doc.get("kind") ==
                    "templo_mayor_discover_actual_reader_claim_to_source_locator_audit"):
                exact_reader_audits.append({
                    "audit_path": audit_path,
                    "reader_blob_sha_in_research": audit_doc["target_main_blob_sha"],
                    "matches_current_main_reader":
                        audit_doc["target_main_blob_sha"] == current_reader_blob,
                    "publication_authorization": False,
                })
            continue
        is_exact_reader_audit = (
            audit_doc.get("kind") == "exact_main_branch_reader_prose_audit")
        is_gate_audit = (
            audit_doc.get("kind") ==
            "Templo_Mayor_Discover_editorial_evidence_gate_addendum")
        matches_reader = None
        if is_gate_audit:
            source_blob = audit_doc.get("main_reader_blob_sha_rechecked")
            if (audit_doc.get("target_main_file") != "poi/templo-mayor/reader.html"
                    or not isinstance(source_blob, str)
                    or not HEX40.fullmatch(source_blob)):
                raise ValueError("Evidence-gate audit lacks an exact reader Git blob")
            matches_reader = (git("rev-parse", "HEAD:poi/templo-mayor/reader.html")
                              .decode().strip() == source_blob)
        if is_exact_reader_audit:
            inspected_reader = audit_doc.get("inspected_repository_file") or {}
            if (inspected_reader.get("path") != "poi/templo-mayor/reader.html"
                    or not isinstance(inspected_reader.get("blob_sha"), str)
                    or not HEX40.fullmatch(inspected_reader["blob_sha"])):
                raise ValueError("Exact-prose audit has no pinned reader Git blob")
            matches_reader = (
                git("rev-parse", "HEAD:poi/templo-mayor/reader.html")
                .decode().strip() == inspected_reader["blob_sha"])
            exact_reader_audits.append({
                "audit_path": audit_path,
                "reader_blob_sha_in_research": inspected_reader["blob_sha"],
                "matches_current_main_reader": matches_reader,
                "publication_authorization": False,
            })
            for source in audit_doc.get("source_locators", []):
                if (not isinstance(source, dict) or
                        not all(isinstance(source.get(k), str) and source[k]
                                for k in ("id", "url", "locator", "access"))):
                    raise ValueError("Malformed exact-prose source locator")
                source_locator_slots.append({
                    "audit_path": audit_path,
                    "source_id_proposed": source["id"],
                    "source_url_proposed": source["url"],
                    "source_locator_proposed": source["locator"],
                    "source_access_claimed": source["access"],
                    "source_locator_confirmed": False,
                    "publication_authorization": False,
                })
        candidates = (audit_doc.get("claims", []) +
                      audit_doc.get("evidence_entries", []) +
                      audit_doc.get("claim_to_source", []) +
                      audit_doc.get("claim_to_source_locator_matrix", []))
        for candidate_index, candidate in enumerate(candidates, 1):
            if not isinstance(candidate, dict):
                raise ValueError("Malformed audit candidate in " + audit_path)
            is_gate = is_gate_audit and "reader_paragraph" in candidate
            if is_gate and (not isinstance(candidate.get("locators"), list)
                            or not candidate["locators"]
                            or not all(isinstance(x, str) and x for x in candidate["locators"])):
                raise ValueError("Evidence-gate audit has missing source locators")
            is_evidence = ("claim_key" in candidate or "source_url" in candidate
                           or is_gate)
            is_reader_prose = is_exact_reader_audit and "reader_paragraph" in candidate
            claim_id = (candidate.get("claim_id") or candidate.get("claim_key") or
                        (f"reader-prose-review-{candidate_index:02d}"
                         if is_reader_prose else
                         f"evidence-gate-review-{candidate_index:02d}" if is_gate else None))
            topic = (candidate.get("topic") or candidate.get("risk") or
                     candidate.get("event"))
            if not claim_id or not topic:
                raise ValueError("Research audit contains unidentified review topics")
            if ((is_reader_prose and candidate.get("status") == "historical_date_conflict")
                    or (is_gate and candidate.get("status") ==
                        "historical_chronology_conflict_blocker")):
                discrepancies.append({
                    "audit_path": audit_path,
                    "issue": candidate.get("finding") or candidate.get("claim"),
                    "current_status": candidate.get("status"),
                    "reader_paragraph_index_proposed": candidate.get("reader_paragraph"),
                    "source_comparison_completed": False,
                    "publication_authorization": False,
                    "review_state": "awaiting_human_original_source_comparison",
                })
            queue.append({
                "audit_path": audit_path,
                "audit_claim_id": claim_id,
                "topic_for_review": topic,
                "reader_paragraph_index_proposed":
                    candidate.get("reader_paragraph") if (is_reader_prose or is_gate) else None,
                "reader_anchor_proposed":
                    (candidate.get("reader_anchor") if is_gate else
                     candidate.get("anchor") if is_reader_prose else None),
                "reader_audit_matches_main_blob":
                    matches_reader if (is_reader_prose or is_gate) else None,
                "candidate_evidence_summary_unverified":
                    (candidate.get("claim") if is_gate else
                     candidate.get("finding") if is_reader_prose else None),
                "source_locator_candidates_unverified":
                    candidate.get("locators", []) if is_gate else [],
                "proposed_editorial_addition_unapproved":
                    candidate.get("draft_addition") if is_gate else None,
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
                     or candidate.get("editorial_action") or candidate.get("action")
                     or candidate.get("gap"))
                    if (is_evidence or is_reader_prose) else None,
                "read_before_context_proposed":
                    candidate.get("read_before") if is_evidence else None,
                "on_site_context_proposed":
                    candidate.get("on_site") if is_evidence else None,
                "editorial_passage_id": None,
                "source_id_confirmed": None,
                "page_or_section_checked": None,
                "publication_authorization": False,
                "review_state": (
                    "awaiting_human_stale_reader_blob_reaudit"
                    if (is_reader_prose or is_gate) and not matches_reader
                    else "awaiting_human_source_and_passage_check"),
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
        cells = coverage_doc.get("cells")
        if cells is None:
            # New research deltas use a 'readiness' array instead of 'cells'.
            # Preserve those gaps privately rather than silently dropping them.
            cells = coverage_doc.get("readiness", [])
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
            explanation = (cell.get("why") or cell.get("assessment")
                           or cell.get("explanatory_readiness") or cell.get("reason")
                           or cell.get("readiness") or cell.get("evidence_gap")
                           or (coverage_doc.get("rating_method")
                               if coverage_doc.get("kind") ==
                               "historically_grounded_explanatory_readiness_delta"
                               else None))
            next_task = (cell.get("next") or cell.get("remaining_gap")
                         or cell.get("gap") or cell.get("missing")
                          or cell.get("next_evidence_needed") or cell.get("evidence_gap"))
            # Focused 2026-11-13 coverage deltas record evidence limitations
            # as explicit blocker lists, not a single "next" string. Preserve
            # the actual research gaps rather than rejecting a valid handoff.
            if next_task is None and isinstance(cell.get("blockers"), list):
                blockers = cell["blockers"]
                if blockers and all(isinstance(item, str) and item for item in blockers):
                    next_task = "; ".join(blockers)
            next_task = next_task or coverage_doc.get("next_coverage_action")
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
                "candidate_finding_ids_unverified":
                    (cell.get("evidence_findings") if isinstance(
                        cell.get("evidence_findings"), list) else
                     cell.get("finding_ids") if isinstance(
                        cell.get("finding_ids"), list) else
                      cell.get("linked_assertion_ids") if isinstance(
                          cell.get("linked_assertion_ids"), list) else []),
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
        "source_locator_review_count": len(source_locator_slots),
        "exact_reader_audit_status": exact_reader_audits,
        "publication_policy": "No candidate findings, sources or editorial prose imported or published",
    }
    return report, {
        "schema_version": 1, "research_commit_sha": sha,
        "status": "human_review_required_not_for_publication",
        "reader_sha256": manuscript_sha,
        "items": queue,
        "unresolved_historical_discrepancies": discrepancies,
        "source_locator_slots": source_locator_slots,
        "exact_reader_audit_status": exact_reader_audits,
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
