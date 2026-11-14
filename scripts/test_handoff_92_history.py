"""Regression test for immutable 92-batch research handoff (private only).

Run with: python scripts/test_handoff_92_history.py
Requires a local research-persistence remote-tracking ref, as in pages.yml.
"""
import copy
from check_research_handoff import RESEARCH_REF, git, git_json
from handoff_92_history import CONTRACT, KIND, paths, validate_frozen, validate_ledger

m = git_json(RESEARCH_REF, "research/handoff/manifest.json")
if m.get("handoff_contract_status") == CONTRACT:
    f = git_json(RESEARCH_REF, m["immutable_handoff_path"])
    ledger = git_json(RESEARCH_REF, f["verification_ledger_path"])
    snapshot = m["verified_replay_commit_sha"]
    actual = {name: git("rev-parse", f"{snapshot}:{path}").decode().strip()
              for name, path in paths(m, f).items()}

    validate_frozen(m, f)
    validate_ledger(m, f, ledger, actual)
    assert f["kind"] == KIND
    assert not m["publication_approved"] and not f["publication_approved"]

    def must_reject(label, action):
        mm, ff, ll, aa = (copy.deepcopy(m), copy.deepcopy(f),
                          copy.deepcopy(ledger), dict(actual))
        action(mm, ff, ll, aa)
        try:
            validate_frozen(mm, ff)
            validate_ledger(mm, ff, ll, aa)
        except (ValueError, KeyError):
            return
        raise AssertionError("Unsafe 92-batch mutation accepted: " + label)

    edits = [
        ("false editorial approval", lambda a,b,c,d: a.update(publication_approved=True)),
        ("false automatic merge", lambda a,b,c,d: b.update(auto_merge_permitted=True)),
        ("false full primary research", lambda a,b,c,d:
            a["staged_counts"].update(original_1807_gazeta_de_mexico_read_this_run=1)),
        ("fewer unresolved conflicts", lambda a,b,c,d:
            a["staged_counts"].update(source_metadata_collisions=0)),
        ("inflated findings", lambda a,b,c,d:
            a["staged_counts"].update(github_distinct_substantive_finding_ids=619)),
        ("wrong source commit", lambda a,b,c,d: b.update(research_commit_sha="0"*40)),
        ("wrong replay commit", lambda a,b,c,d: a.update(verified_replay_commit_sha="0"*40)),
        ("misidentified source batch", lambda a,b,c,d:
            b.update(source_batch_artifact_paths=["research/batches/not-the-batch.json"])),
        ("changed Git blob", lambda a,b,c,d: d.update(batch="0"*40)),
        ("changed binary", lambda a,b,c,d: d.update(binary="0"*40)),
        ("faked independent binary check", lambda a,b,c,d:
            c["github_readback"].update(independent_external_binary_digest_recomputed=True)),
        ("ledger publication approval", lambda a,b,c,d: c.update(publication_approved=True)),
        ("ledger count drift", lambda a,b,c,d:
            c["replay_counts"].update(staged_finding_ids=777)),
        ("ledger canonical changed", lambda a,b,c,d: c.update(canonical_rows_unchanged=False)),
        ("source review shortcut", lambda a,b,c,d: b.update(ready_for_editorial_review=True)),
    ]
    for label, edit in edits:
        must_reject(label, edit)

    print("PASS: 92-batch immutable handoff, all seven staged Git identities, "
          "conflict counts and nonpublication guards")
else:
    print("NOTICE: 92-batch verification superseded by newer research; "
          "private handoff validator remains fail-closed")
