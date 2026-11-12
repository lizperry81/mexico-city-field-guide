#!/usr/bin/env python3
"""Fail Pages build if the historical POI is empty, truncated, or unlinked."""
import json
from pathlib import Path
from html import escape
root = Path("site")
original_home = Path("recovered/mexico-city-field-guide.html").read_bytes()
built_home = (root / "index.html").read_bytes()
assert len(original_home) > 500_000, "The recovered rich homepage is unexpectedly short"
assert built_home == original_home, "Base homepage differs from richer preserved original; potential regression"
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
for marker in ('id="story"', 'id="site"', 'id="dossier"', 'id="museum"', 'id="evidence"', 'id="sources"', 'id="visit"', 'id="claimsearch"'):
    assert marker in page, f"Missing functioning interface element: {marker}"
centro = json.loads((root / "data" / "centro.json").read_text(encoding="utf-8"))
historic = [b["pt"] for b in centro["stops"]["templo"]["read"] if "pt" in b]
assert len(historic) >= 6, "Older substantive historical dossier unexpectedly missing"
for pt in historic:
    assert escape(pt["h"], quote=True) in page
    for block in pt.get("blocks",[]):
        if "p" in block: assert escape(block["p"][0],quote=True) in page
museum = next(t for t in centro["tours"] if t["id"] == "templomuseo")
assert "Tlaltecuhtli" in page and "Coyolxauhqui" in page
assert escape(museum["summary"],quote=True) in page
planning=json.loads((root / "poi" / "templo-mayor" / "poi.json").read_text(encoding="utf-8"))
assert planning["id"]=="templo" and planning["duration_minutes_estimate"]>=90
assert planning["opening_hours_status"]=="not_live_verified"
print(f"PASS — {len(walk['chapters'])} detailed field stops, {len(pilot['claims'])} claims, {len(sources)} research records, {len(page)} HTML characters")
