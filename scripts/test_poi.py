#!/usr/bin/env python3
"""Fail Pages build if the historical POI is empty, truncated, or unlinked."""
import json
from pathlib import Path
from html import escape
root = Path("site")
research = root / "data" / "research"
walk = json.loads((research / "templo_walk_v63.json").read_text(encoding="utf-8"))
pilot = json.loads((research / "templo_mayor_pilot.json").read_text(encoding="utf-8"))
sources = json.loads((research / "templo_verified_discoveries_v68.json").read_text(encoding="utf-8"))
page = (root / "poi" / "templo-mayor" / "index.html").read_text(encoding="utf-8")
assert len(walk["chapters"]) == 8
assert len(pilot["claims"]) == 21
assert len(sources) == 12
assert len(page) > 17000, f"Unexpectedly short POI page ({len(page)} chars)"
for c in walk["chapters"]:
    for k in ("title", "core_text", "field_instruction", "deep_dive_question"):
        assert escape(c[k], quote=True) in page, f"Lost historical field content: {c['id']} {k}"
for c in pilot["claims"]:
    assert escape(c["statement"], quote=True) in page, f"Missing claim {c['id']}"
for c in sources:
    assert escape(c["title"], quote=True) in page, f"Missing scholarly record {c['id']}"
assert 'href="../../"' in page, "Broken home navigation in deep POI path"
assert 'href="../../research-library/"' in page, "Broken library navigation"
for marker in ('id="story"', 'id="evidence"', 'id="sources"', 'id="visit"', 'id="claimsearch"'):
    assert marker in page, f"Missing functioning interface element: {marker}"
print(f"PASS — {len(walk['chapters'])} detailed field stops, {len(pilot['claims'])} claims, {len(sources)} research records, {len(page)} HTML characters")
