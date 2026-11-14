"""Tamper regressions for the 89-batch private-only research handoff.

Runs after Actions fetches research-persistence. The 89 producer record is
never treated as human-reviewed or authorized Discover/Explore publication.
"""
import copy

from handoff_89_history import validate_frozen, validate_ledger
from check_research_handoff import RESEARCH_REF, git, git_json

m = git_json(RESEARCH_REF, "research/handoff/manifest.json")
if m.get("handoff_contract_status") == (
        "89_batch_sqlite_integrity_and_workflow_git_readback_verified_noncanonical_unapproved"):
    f = git_json(RESEARCH_REF, m["immutable_handoff_path"])
    l = git_json(RESEARCH_REF, f["reconciliation_ledger_path"])
    paths = {
        "sqlite": m["versioned_research_sqlite_gz_path"],
        "report": m["replay_report_path"],
        "checksum": m["replay_evidence"]["compressed_checksum_path"],
        "batch": f["source_batch_path"],
        "coverage": f["coverage_artifact_paths"][0],
        "audit": f["chapter_audit_artifact_paths"][0],
    }
    actual = {name: git("rev-parse", f"{RESEARCH_REF}:{path}").decode().strip()
              for name, path in paths.items()}
    validate_frozen(m, f)
    validate_ledger(m, f, l, actual)

    for mutate in (
        lambda a, b: a.update(publication_approved=True),
        lambda a, b: a.update(auto_merge_permitted=True),
        lambda a, b: a.update(ready_for_publication=True),
        lambda a, b: a["staged_counts"].update(github_batches_replayed=90),
        lambda a, b: b.update(snapshot_commit_sha="a"*40),
        lambda a, b: b["github_readback"].update(
            independent_binary_sha256_recalculation_not_claimed=False),
    ):
        ma, fa = copy.deepcopy(m), copy.deepcopy(f)
        mutate(ma, fa)
        try:
            validate_frozen(ma, fa)
        except ValueError:
            pass
        else:
            raise AssertionError("89-batch frozen provenance tamper accepted")
    for mutate in (
        lambda a, b: a.update(publication_approved=True),
        lambda a, b: a.update(original_canonical_rows_unchanged=False),
        lambda a, b: a["replay_after"].update(findings=999),
        lambda a, b: a["sha256"].update(compressed_git_workflow_verified="0"*64),
        lambda a, b: a["github_blob_sha"].update(report="0"*40),
        lambda a, b: a["github_verification"].update(
            independent_binary_sha256_recalculation_not_claimed=False),
    ):
        la, aa = copy.deepcopy(l), dict(actual)
        mutate(la, aa)
        try:
            validate_ledger(m, f, la, aa)
        except ValueError:
            pass
        else:
            raise AssertionError("89-batch ledger tamper accepted")
    aa = dict(actual, sqlite="0"*40)
    try:
        validate_ledger(m, f, l, aa)
    except ValueError:
        pass
    else:
        raise AssertionError("89-batch altered committed Git object accepted")
    print("PASS: 89-batch immutable handoff, Git blobs and unapproved-only tamper tests")
else:
    print("NOTICE: research producer has moved beyond 89; consumer handoff will validate latest")
