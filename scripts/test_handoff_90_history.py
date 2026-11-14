"""Fail-closed regression tests for the 90-batch private-only handoff."""
import copy
from check_research_handoff import RESEARCH_REF, git, git_json
from handoff_90_history import CONTRACT, validate_frozen, validate_ledger

m = git_json(RESEARCH_REF, "research/handoff/manifest.json")
if m.get("handoff_contract_status") == CONTRACT:
    f = git_json(RESEARCH_REF, m["immutable_handoff_path"])
    ledger = git_json(RESEARCH_REF, f["reconciliation_ledger_path"])
    actual = {
        name: git("rev-parse", f"{RESEARCH_REF}:{path}").decode().strip()
        for name, path in ledger["paths"].items()
    }
    validate_frozen(m, f)
    validate_ledger(m, f, ledger, actual)

    for mutation in (
        lambda a, b: a.update(publication_approved=True),
        lambda a, b: a.update(auto_merge_permitted=True),
        lambda a, b: a.update(ready_for_editorial_review=True),
        lambda a, b: a["staged_counts"].update(github_batches_replayed=91),
        lambda a, b: b.update(snapshot_commit_sha="0" * 40),
        lambda a, b: b["github_readback"].update(
            independent_external_binary_download_not_done=False),
        lambda a, b: a.update(evidence_status="approved"),
    ):
        ma, fa = copy.deepcopy(m), copy.deepcopy(f)
        mutation(ma, fa)
        try:
            validate_frozen(ma, fa)
        except ValueError:
            pass
        else:
            raise AssertionError("90-batch mutated frozen handoff accepted")
    for mutation in (
        lambda a: a.update(publication_approved=True),
        lambda a: a.update(canonical_promoted=True),
        lambda a: a["verified_hashes"].update(compressed_sqlite_sha256="0" * 64),
        lambda a: a["counts_after"].update(staged_findings=999),
        lambda a: a["paths"].update(report="research/reconciled/other/replay_report.json"),
        lambda a: a["source_identity_review"].update(unresolved_index_only_count=0),
        lambda a: a["validation"].update(gzip_test="failed"),
    ):
        bad = copy.deepcopy(ledger)
        mutation(bad)
        try:
            validate_ledger(m, f, bad, actual)
        except ValueError:
            pass
        else:
            raise AssertionError("90-batch mutated readback accepted")
    bad = dict(actual, compressed_db="0" * 40)
    try:
        validate_ledger(m, f, ledger, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Wrong committed compressed DB accepted")
    print("PASS: 90-batch replay, Git objects, conflicts and private-only status")
else:
    print("NOTICE: research handoff has advanced past batch 90; newest verification required")
