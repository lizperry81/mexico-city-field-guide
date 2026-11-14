"""Tamper regressions using the real pinned 86-batch Git history."""
import copy
import json
import subprocess
from handoff_86_history import validate_frozen, validate_ledger

PIN = "0ac5bd9c2acf57707927225ddfb83be39f81f241"
REPLAY = "f0e59fdd671a572e332eafdd05622a384a30aebd"

def git(*args):
    return subprocess.check_output(["git", *args]).decode().strip()

def load(ref, path):
    return json.loads(git("show", f"{ref}:{path}"))

m = load(PIN, "research/handoff/manifest.json")
f = load(PIN, m["immutable_handoff_path"])
ledger = load(PIN, m["latest_reconciliation_ledger_path"])
reader = m["latest_research_integrity"]["main_reader_blob_verified"]
actual = {
    "sqlite": git("rev-parse", f"{REPLAY}:{m['versioned_research_sqlite_gz_path']}"),
    "report": git("rev-parse", f"{REPLAY}:{m['replay_report_path']}"),
}
validate_frozen(m, f, reader)
validate_ledger(m, f, ledger, actual)

def reject(fn, *args):
    try:
        fn(*args)
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError("Accepted altered 86-batch research or publication authorization")

for field, value in (
    ("ready_for_editorial_review", True), ("ready_for_publication", True),
    ("auto_merge_permitted", True), ("canonical_promoted", True),
    ("research_commit_sha", "0"*40), ("verified_replay_commit_sha", "0"*40),
    ("evidence_status", "publication_approved")):
    altered = copy.deepcopy(m)
    altered[field] = value
    reject(validate_frozen, altered, f, reader)
altered = copy.deepcopy(m)
altered["canonical"]["claims"] += 1
reject(validate_frozen, altered, f, reader)
altered = copy.deepcopy(m)
altered["staged_counts"]["github_distinct_substantive_finding_ids"] += 1
reject(validate_frozen, altered, f, reader)
reject(validate_frozen, m, f, "f"*40)

for field, value in (
    ("ready_for_editorial_review", True), ("publication_approved", True),
    ("canonical_rows_unchanged", False), ("research_commit_sha", "0"*40),
    ("sqlite_gzip_github_blob_sha", "0"*40),
    ("replay_report_blob_sha", "0"*40)):
    altered = copy.deepcopy(ledger)
    altered[field] = value
    reject(validate_ledger, m, f, altered, actual)
altered = copy.deepcopy(ledger)
altered["staged_counts"]["findings"] -= 1
reject(validate_ledger, m, f, altered, actual)
altered = copy.deepcopy(ledger)
altered["github_binary_readback"]["compressed_sha256_recalculated_matches_repo_checksum"] = False
reject(validate_ledger, m, f, altered, actual)
reject(validate_ledger, m, f, ledger, dict(actual, report="0"*40))
print("PASS: 86-batch Git identities and editorial nonpublication regressions.")
