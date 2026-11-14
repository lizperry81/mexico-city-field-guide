"""Fail-closed tamper tests against the actual 87-batch immutable Git handoff.

The pinned manifest is an unapproved research snapshot, NEVER an instruction
to modify Discover, Explore, the homepage, or the canonical V97 database.
"""
import copy
import json
import subprocess
from handoff_87_history import validate_frozen, validate_ledger

PIN = "c12136fecf7dfaa4c9372a4fdc860856ee665908"
REPLAY = "8035cec9040a31b0d265e6924707ba86a7ca52a6"

def git(*args):
    return subprocess.check_output(["git", *args]).decode().strip()

def load(ref, path):
    return json.loads(git("show", f"{ref}:{path}"))

manifest = load(PIN, "research/handoff/manifest.json")
frozen = load(PIN, manifest["immutable_handoff_path"])
ledger = load(PIN, frozen["verification_ledger_path"])
paths = {"sqlite": manifest["versioned_research_sqlite_gz_path"],
         "report": manifest["replay_report_path"],
         "batch": frozen["source_batch_artifact_paths"][0],
         "coverage": frozen["coverage_artifact_paths"][0],
         "audit": frozen["chapter_audit_artifact_paths"][0]}
actual = {name: git("rev-parse", f"{REPLAY}:{path}")
          for name, path in paths.items()}

validate_frozen(manifest, frozen)
validate_ledger(manifest, frozen, ledger, actual)

def reject(fn, *args):
    try:
        fn(*args)
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError("Accepted tampered 87-batch research identity or editorial status")

for key, value in (
    ("research_commit_sha", "0" * 40),
    ("verified_replay_commit_sha", "0" * 40),
    ("ready_for_publication", True),
    ("ready_for_editorial_review", True),
    ("canonical_promoted", True),
    ("publication_approved", True),
    ("auto_merge_permitted", True),
    ("compressed_sha256", "0" * 64),
    ("evidence_status", "editorially_approved"),
):
    altered = copy.deepcopy(manifest)
    altered[key] = value
    reject(validate_frozen, altered, frozen)
altered = copy.deepcopy(manifest)
altered["canonical"]["claims"] += 1
reject(validate_frozen, altered, frozen)
altered = copy.deepcopy(manifest)
altered["staged_counts"]["github_distinct_substantive_finding_ids"] += 1
reject(validate_frozen, altered, frozen)

for key, value in (
    ("research_commit_sha", "0" * 40),
    ("verified_replay_commit_sha", "0" * 40),
    ("ready_for_publication", True),
    ("publication_approved", True),
    ("canonical_rows_unchanged", False),
    ("independent_compressed_sha256", "0" * 64),
):
    altered = copy.deepcopy(ledger)
    altered[key] = value
    reject(validate_ledger, manifest, frozen, altered, actual)
altered = copy.deepcopy(ledger)
altered["counts_after"]["staged_findings"] += 1
reject(validate_ledger, manifest, frozen, altered, actual)
altered = copy.deepcopy(ledger)
altered["github_blob_sha"]["audit"] = "0" * 40
reject(validate_ledger, manifest, frozen, altered, actual)
reject(validate_ledger, manifest, frozen, ledger,
       dict(actual, report="0" * 40))
print("PASS: 87-batch Git object, replay and editorial nonpublication guards.")
