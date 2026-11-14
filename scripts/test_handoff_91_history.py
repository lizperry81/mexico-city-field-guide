"""Fail-closed 91-batch private-research handoff regressions.

This test reads the checked-out research branch; no GitHub staging content is
copied into the public app.
"""
import copy
from check_research_handoff import RESEARCH_REF, git, git_json
from handoff_91_history import CONTRACT, validate_frozen, validate_ledger

m = git_json(RESEARCH_REF, "research/handoff/manifest.json")
if m.get("handoff_contract_status") == CONTRACT:
    f = git_json(RESEARCH_REF, m["immutable_handoff_path"])
    ledger = git_json(RESEARCH_REF, f["latest_reconciliation_ledger_path"])
    actual = {
        key: git("rev-parse", f"{RESEARCH_REF}:{path}").decode().strip()
        for key, path in ledger["paths"].items()
    }
    validate_frozen(m, f)
    validate_ledger(m, f, ledger, actual)

    def must_reject(action, where):
        mm, ff, ll, aa = (copy.deepcopy(m), copy.deepcopy(f),
                           copy.deepcopy(ledger), dict(actual))
        action(mm, ff, ll, aa)
        try:
            validate_frozen(mm, ff)
            validate_ledger(mm, ff, ll, aa)
        except ValueError:
            return
        raise AssertionError("91-batch unsafe mutation passed: " + where)

    mutations = (
        ("publish", lambda a, b, c, d: a.update(publication_approved=True)),
        ("editorial approval", lambda a, b, c, d:
            b.update(ready_for_editorial_review=True)),
        ("automatic merge", lambda a, b, c, d:
            a.update(auto_merge_permitted=True)),
        ("inflated findings", lambda a, b, c, d:
            a["staged_counts"].update(github_distinct_substantive_finding_ids=608)),
        ("hidden conflict", lambda a, b, c, d:
            a["staged_counts"].update(source_metadata_collisions=0)),
        ("new source SHA", lambda a, b, c, d:
            b.update(research_commit_sha="0" * 40)),
        ("wrong replay commit", lambda a, b, c, d:
            a.update(verified_replay_commit_sha="0" * 40)),
        ("fake independent binary", lambda a, b, c, d:
            a["replay_evidence"].update(independent_binary_download_blocked=False)),
        ("wrong ledger snapshot", lambda a, b, c, d:
            c.update(verified_snapshot_commit_sha="0" * 40)),
        ("tampered ledger count", lambda a, b, c, d:
            c["after"].update(github_distinct_substantive_finding_ids=999)),
        ("tampered blob", lambda a, b, c, d:
            d.update(sql="0" * 40)),
        ("tampered report identity", lambda a, b, c, d:
            c["checks"].update(readback_report_blob_sha="0" * 40)),
        ("changed audit path", lambda a, b, c, d:
            c["paths"].update(audit="research/audits/other.json")),
        ("canon promotion", lambda a, b, c, d:
            c.update(canonical_promoted=True)),
        ("false workflow claim", lambda a, b, c, d:
            c["checks"].update(external_binary_download_or_hash_performed=True)),
    )
    for label, mutate in mutations:
        must_reject(mutate, label)
    print("PASS: 91-batch immutable Git identities, conflict counts and no-publication guards")
else:
    print("NOTICE: 91-batch fixture superseded; newest handoff must be reviewed")
