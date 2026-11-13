#!/usr/bin/env python3
"""Guard research handoff against accidental editorial publication or unsafe paths."""
import json
from pathlib import Path

from check_research_handoff import OUT, safe_path
from editorial_passage_inventory import HistoryPassages

for unsafe in ("../site/index.html", "research/../../site/index.html",
               "/research/handoff/manifest.json", r"research\..\site"):
    try:
        safe_path(unsafe)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe handoff path accepted: " + unsafe)
assert safe_path("research/audits/valid.json") == "research/audits/valid.json"

report = json.loads((OUT / "handoff-report.json").read_text(encoding="utf-8"))
assert report["ready_for_publication"] is False
if report["status"] == "no_verified_handoff":
    assert not (OUT / "editorial-review-queue.json").exists()
    assert not (OUT / "editorial-passage-inventory.json").exists()
    print("PASS: unverified handoff is blocked and has no editorial queue")
else:
    assert report["status"] == "verified_handoff_not_approved"
    assert len(report["research_commit_sha"]) == 40
    assert not report["canonical_promoted"]
    assert report["artifact_checks"]
    queue = json.loads((OUT / "editorial-review-queue.json").read_text(encoding="utf-8"))
    assert queue["research_commit_sha"] == report["research_commit_sha"]
    assert queue["status"] == "human_review_required_not_for_publication"
    assert len(queue["items"]) == report["review_queue_count"]
    for item in queue["items"]:
        assert item["editorial_passage_id"] is None
        assert item["source_id_confirmed"] is None
        assert item["page_or_section_checked"] is None
        assert item["review_state"].startswith("awaiting_human")
    passages = json.loads((OUT / "editorial-passage-inventory.json").read_text(encoding="utf-8"))
    assert passages["status"] == "private_passage_inventory_human_evidence_review_required"
    assert passages["source_sha256"] == report["app_reader_sha256"]
    assert passages["passage_count"] == report["reader_passages_pending_evidence_review"]
    assert passages["passage_count"] >= 10
    assert all(f"dossier-topic-{n}" in passages["section_ids"] for n in range(1, 7))
    assert len(set(p["passage_id"] for p in passages["passages"])) == passages["passage_count"]
    for passage in passages["passages"]:
        assert passage["human_review_status"] == "not_reviewed"
        assert passage["source_id_confirmed"] is None
        assert passage["page_or_section_checked"] is None
        assert passage["audit_claim_ids_assigned"] == []
        assert passage["publication_authorization"] is False
    print("PASS: version-pinned handoff and private paragraph evidence slots remain unpublished")

assert not Path("site/data/editorial-review-queue.json").exists()
assert not Path("site/data/handoff-report.json").exists()
assert not Path("site/data/editorial-passage-inventory.json").exists()

# Nested archaeological explanations may be useful, but they are not automatically
# equivalent to independently verified main-narrative paragraphs.
parser = HistoryPassages()
parser.feed('<article id="history"><p>Existing <em>narrative</em> passage</p>'
            '<details><p>Optional deep dive</p></details></article>'
            '<section id="explore"><p>Physical field instructions</p></section>')
assert len(parser.passages) == 1
assert parser.passages[0]["section_id"] == "history-introduction"
assert parser.passages[0]["publication_authorization"] is False
