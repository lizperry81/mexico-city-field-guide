#!/usr/bin/env python3
"""Read-only, provenance-checked research handoff for editorial review.

Run from a full-history main checkout after fetching research-persistence.
Writes private CI artifacts only; NEVER writes to site/, edits research, or
authorizes publication. A failed validation exits nonzero.
"""
from __future__ import annotations

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
          "new_research_artifact_paths")


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
    if p.is_absolute() or ".." in p.parts or not path.startswith("research/"):
        raise ValueError(f"Out-of-scope research artifact path: {path}")
    return path


def validate():
    manifest = git_json(RESEARCH_REF, MANIFEST_PATH)
    if manifest.get("schema_version") != 2 or manifest.get("kind") != "research_to_app_handoff":
        raise ValueError("Unrecognized research handoff schema")
    sha = manifest.get("research_commit_sha", "")
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        raise ValueError("Missing or invalid pinned research commit SHA")
    resolved = git("rev-parse", f"{sha}^{{commit}}").decode().strip()
    if resolved != sha:
        raise ValueError("Pinned research SHA could not be resolved")
    subprocess.run(["git", "merge-base", "--is-ancestor", sha, RESEARCH_REF],
                   check=True, capture_output=True)

    inspected = []
    for group in GROUPS:
        paths = manifest.get(group, [])
        if not isinstance(paths, list):
            raise ValueError(f"Invalid handoff path group: {group}")
        for path in paths:
            safe_path(path)
            blob = git("show", f"{sha}:{path}")
            if not blob:
                raise ValueError(f"Empty referenced research artifact: {path}")
            inspected.append({"group": group, "path": path,
                              "bytes": len(blob),
                              "sha256": hashlib.sha256(blob).hexdigest()})
    if not inspected or not manifest.get("chapter_audit_artifact_paths") or not manifest.get("coverage_artifact_paths"):
        raise ValueError("Research handoff lacks audit or coverage artifacts")

    immutable = safe_path(manifest.get("immutable_handoff_path"))
    immutable_manifest = git_json(RESEARCH_REF, immutable)
    if immutable_manifest.get("research_commit_sha") != sha:
        raise ValueError("Versioned handoff snapshot points to a different research commit")
    if immutable_manifest != manifest:
        raise ValueError("Versioned handoff differs from the current manifest")
    audit = git_json(sha, manifest["chapter_audit_artifact_paths"][0])
    coverage = git_json(sha, manifest["coverage_artifact_paths"][0])
    if not isinstance(audit.get("claims"), list) or not isinstance(coverage.get("counts"), dict):
        raise ValueError("Handoff audit or coverage artifact has invalid structure")
    if manifest.get("ready_for_publication") is not False or manifest.get("canonical_promoted") is not False:
        raise ValueError("Cannot safely classify research handoff as unapproved")
    manuscript = Path("poi/templo-mayor/reader.html")
    passage_inventory = inventory(manuscript) if manuscript.is_file() else None
    manuscript_sha = passage_inventory["source_sha256"] if passage_inventory else None

    # This is a queue of REVIEW QUESTIONS. Sources and topics are not copied
    # into public content or attached to a passage without a human line audit.
    queue = [{
        "audit_claim_id": c.get("claim_id"),
        "topic_for_review": c.get("topic"),
        "candidate_evidence_status": c.get("status"),
        "editorial_passage_id": None,
        "source_id_confirmed": None,
        "page_or_section_checked": None,
        "review_state": "awaiting_human_source_and_passage_check"
    } for c in audit["claims"]]
    if any(not row["audit_claim_id"] or not row["topic_for_review"] for row in queue):
        raise ValueError("Research audit contains unidentified claim topics")

    report = {
        "schema_version": 1,
        "status": "verified_handoff_not_approved",
        "research_commit_sha": sha,
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
        "artifact_checks": inspected,
        "unresolved": manifest.get("blockers", []),
        "review_queue_count": len(queue),
        "publication_policy": "No candidate findings, sources or editorial prose imported or published",
    }
    return report, {
        "schema_version": 1, "research_commit_sha": sha,
        "status": "human_review_required_not_for_publication",
        "reader_sha256": manuscript_sha,
        "items": queue,
    }, passage_inventory


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        report, queue, passages = validate()
    except (subprocess.CalledProcessError, ValueError, KeyError,
            TypeError, json.JSONDecodeError) as exc:
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
