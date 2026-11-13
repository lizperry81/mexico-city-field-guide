#!/usr/bin/env python3
"""Regression tests: drafted Discover prose must never be published by the builder."""
import copy
import json
from pathlib import Path

from build_discover_editorial import EDITORIAL, SITE, render, validate

draft_file = EDITORIAL / "templo-mayor.json"
draft = json.loads(draft_file.read_text(encoding="utf-8"))
assert validate(draft, "templo-mayor") is False
assert not (SITE / "poi/templo-mayor/discover/index.html").exists(), (
    "Unapproved Templo Mayor narrative was published")
status = json.loads((SITE / "data/discover-editorial-status.json").read_text(encoding="utf-8"))
row = next(x for x in status["manuscripts"] if x["poi_slug"] == "templo-mayor")
assert row["status"] == "draft" and row["published"] is False
assert row["chapter_count_published"] == 0
example = copy.deepcopy(draft)
example["status"] = "approved"
example["approval"] = {
    "editor": "TEST EDITOR", "evidence_auditor": "TEST AUDITOR",
    "approved_on": "2026-11-12", "editorial_review_complete": True,
    "page_specific_evidence_checked": True
}
example["chapters"] = [{
    "id": "example-test-only",
    "title": "Escape <script> from editorial HTML",
    "paragraphs": [{
        "text": "This is nonhistorical sample prose for testing the publication gate, and it must never be published.",
        "evidence": [{"source_id": "TEST", "page_or_section": "page 1",
                      "audit_status": "page_checked"}]
    }],
    "deep_dives": [{"title": "Example sidebar", "text": "Example only"}]
}]
assert validate(example, "templo-mayor")
page = render(example)
assert "&lt;script&gt;" in page and "<script> from editorial HTML" not in page
assert 'href="#example-test-only"' in page and "Verified source locators" in page
bad = copy.deepcopy(example)
bad["approval"]["page_specific_evidence_checked"] = False
try:
    validate(bad, "templo-mayor")
except ValueError:
    pass
else:
    raise AssertionError("Unverified manuscript allowed to publish")
bad = copy.deepcopy(example)
bad["chapters"][0]["paragraphs"][0]["evidence"][0]["page_or_section"] = ""
try:
    validate(bad, "templo-mayor")
except ValueError:
    pass
else:
    raise AssertionError("Missing page locator allowed to publish")
print("PASS: draft Discover stays unpublished; reviewed/cited future prose has a safe, navigable publishing route")
