#!/usr/bin/env python3
"""Regression tests: drafted Discover prose must never be published by the builder."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from build_discover_editorial import (EDITORIAL, SITE, render, validate,
                                      verify_verbatim_archives, verify_visual_assets)

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
    "deep_dives": [{"title": "Example sidebar", "text": "Example only",
                    "evidence": [{"source_id": "TEST-DIVE",
                                  "page_or_section": "page 2",
                                  "audit_status": "page_checked"}]}]
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
# Optional deep dives are independently evidence-gated; unlike display
# toggles they may contain substantive archaeological claims.
for alter in (
    lambda d: d["chapters"][0]["deep_dives"][0].pop("evidence"),
    lambda d: d["chapters"][0]["deep_dives"][0]["evidence"][0].update(
        audit_status="candidate"),
    lambda d: d["chapters"][0]["deep_dives"][0]["evidence"][0].update(
        page_or_section=""),
):
    invalid = copy.deepcopy(example)
    alter(invalid)
    try:
        validate(invalid, "templo-mayor")
    except ValueError:
        pass
    else:
        raise AssertionError("Unverified optional history deep dive allowed to publish")
# A manuscript with self-asserted approval still cannot be published without
# the exact independently archived prose and a matching adjacent checksum.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    try:
        verify_verbatim_archives(example, root)
    except ValueError as exc:
        assert "Missing exact approved chapter archive" in str(exc)
    else:
        raise AssertionError("Unarchived approved prose passed publication gate")
    archive = root / "editorial/approved/templo-mayor--example-test-only.md"
    archive.parent.mkdir(parents=True)
    original = ("# Test-only chapter\\n\\n" + example["chapters"][0]["paragraphs"][0]["text"] +
                "\\n\\n" + example["chapters"][0]["deep_dives"][0]["text"] + "\\n")
    archive.write_text(original, encoding="utf-8")
    checksum = archive.with_suffix(".md.sha256")
    checksum.write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\\n",
                        encoding="utf-8")
    verify_verbatim_archives(example, root)
    altered_dive = copy.deepcopy(example)
    altered_dive["chapters"][0]["deep_dives"][0]["text"] += " Unapproved edit."
    try:
        verify_verbatim_archives(altered_dive, root)
    except ValueError as exc:
        assert "not verbatim" in str(exc)
    else:
        raise AssertionError("Unapproved deep-dive prose passed verbatim archive check")
    modified = copy.deepcopy(example)
    modified["chapters"][0]["paragraphs"][0]["text"] += " An unauthorized alteration."
    try:
        verify_verbatim_archives(modified, root)
    except ValueError as exc:
        assert "not verbatim" in str(exc)
    else:
        raise AssertionError("Rewritten approved prose passed archival comparison")
    archive.write_text(original + "Tampered\\n", encoding="utf-8")
    try:
        verify_verbatim_archives(example, root)
    except ValueError as exc:
        assert "checksum mismatch" in str(exc)
    else:
        raise AssertionError("Altered approved archive passed checksum gate")
# Optional historical photos, maps, artifacts and timelines remain unpublished
# until both source-page and reproduction-rights checks are complete.
visual_example = copy.deepcopy(example)
visual_example["chapters"][0]["visuals"] = [{
    "kind": "historical_photo",
    "after_paragraph": 1,
    "asset_path": "assets/discover/test-image.webp",
    "alt": "Verified visual description",
    "caption": "Test-only caption & <unsafe>",
    "credit": "Test archive",
    "rights_status": "cleared",
    "rights_basis": "Test permission record, not a real license",
    "evidence": [{"source_id": "TEST-IMAGE", "page_or_section": "catalog record 2",
                  "audit_status": "page_checked"}]
}]
assert validate(visual_example, "templo-mayor")
visual_page = render(visual_example)
assert 'src="../assets/discover/test-image.webp"' in visual_page
assert 'alt="Verified visual description"' in visual_page
assert "Test-only caption &amp; &lt;unsafe&gt;" in visual_page
assert "Credit: Test archive" in visual_page and "Evidence: TEST-IMAGE" in visual_page
for change, value in [
    ("rights_status", "unknown"), ("asset_path", "../secret.jpg"),
    ("after_paragraph", 2), ("alt", ""),
]:
    bad = copy.deepcopy(visual_example)
    bad["chapters"][0]["visuals"][0][change] = value
    try:
        validate(bad, "templo-mayor")
    except ValueError:
        pass
    else:
        raise AssertionError("Unauthorized image field passed: " + change)
bad = copy.deepcopy(visual_example)
bad["chapters"][0]["visuals"][0]["evidence"][0]["audit_status"] = "candidate"
try:
    validate(bad, "templo-mayor")
except ValueError:
    pass
else:
    raise AssertionError("Unverified illustration provenance passed")
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    try:
        verify_visual_assets(visual_example, root)
    except ValueError as exc:
        assert "asset missing" in str(exc)
    else:
        raise AssertionError("Uncommitted image file passed publication gate")
    asset = root / "poi/templo-mayor/assets/discover/test-image.webp"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"test fixture, never published")
    verify_visual_assets(visual_example, root)
# Adjacent chapter links are navigational only; Explore stops are never
# imported as chapters. Test escaping and first/last boundary behavior.
chapter_two = copy.deepcopy(example["chapters"][0])
chapter_two["id"] = "second-test-chapter"
chapter_two["title"] = "Second & <chapter>"
chapter_two["paragraphs"][0]["text"] = (
    "This second nonhistorical test paragraph verifies chapter navigation "
    "without creating any real historical manuscript."
)
two_chapters = copy.deepcopy(example)
two_chapters["chapters"].append(chapter_two)
page = render(two_chapters)
assert 'class="skip-link" href="#chapter-navigation"' in page
assert 'id="chapter-navigation" aria-label="Chapters"' in page
assert 'rel="next" href="#second-test-chapter"' in page
assert 'Next chapter: Second &amp; &lt;chapter&gt;' in page
assert 'rel="prev" href="#example-test-only"' in page
assert page.count('rel="next"') == 1
assert page.count('rel="prev"') == 1
assert 'href="#explore"' not in page
print("PASS: draft Discover unpublished; archive and checksum required for future approved prose")
