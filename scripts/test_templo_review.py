#!/usr/bin/env python3
"""Guard the phone review against stale research, missing pages, and broken UX scripts."""
import json
import re
from html import escape
from pathlib import Path
from subprocess import run, PIPE
from tempfile import TemporaryDirectory

ROOT=Path("site")
main=(ROOT/"poi/templo-mayor/index.html").read_text(encoding="utf-8")
review=(ROOT/"poi/templo-mayor/review/index.html").read_text(encoding="utf-8")
feedback=(ROOT/"feedback/annotate.js").read_text(encoding="utf-8")
assert len(main)>35000, "Canonical rich POI was truncated"
assert len(review)>len(main), "Review appears to be a shortened stale copy"
assert 'id="review-reader-link"' in main, "Missing link to commentable layout"
assert 'href="review/"' in main
assert 'name="viewport"' in review
assert 'id="review-layout-script"' in review
assert 'id="review-layout-styles"' in review
assert 'src="../../../feedback/annotate.js"' in review, "Broken nested comment script"
assert 'href="../../../walks/historic-center/"' in review, "Broken nested walk link"
assert 'href="../../../research-library/"' in review, "Broken research-library link"
for id in ("story","site","dossier","museum","evidence","sources","visit","claimlist","walk-1","walk-8"):
    assert f'id="{id}"' in review, ("Lost historical section",id)
for token in ('History behind the excavated site','What to look for during the visit',
              'Tlaltecuhtli','Coyolxauhqui','review-deep-button','review-switch',
              'Research-stage guide','data-open-research'):
    assert token in review, ("Missing reader content or feature",token)
assert 'MutationObserver' in feedback, "Comments won't attach to dynamically moved chapters"
assert 'dataset.cdmxCommentBound' in feedback, "Comment buttons may be duplicated"
data=ROOT/"data/research"
walk=json.loads((data/"templo_walk_v63.json").read_text(encoding="utf-8"))
pilot=json.loads((data/"templo_mayor_pilot.json").read_text(encoding="utf-8"))
sources=json.loads((data/"templo_verified_discoveries_v68.json").read_text(encoding="utf-8"))
assert len(walk["chapters"])==8 and len(pilot["claims"])==21 and len(sources)==12
for record in walk["chapters"]:
    assert escape(record["core_text"],quote=True) in review, ("Lost field text",record["title"])
for claim in pilot["claims"]:
    assert escape(claim["statement"],quote=True) in review, ("Lost claim",claim["id"])
for source in sources:
    assert escape(source["title"],quote=True) in review, ("Lost research source",source["id"])
js=re.search(r'<script id="review-layout-script">(.*?)</script>',review,re.S)
assert js, "Review behavior not embedded"
assert "storyChapters.length!==8" in js.group(1)
assert "hist.length<7" in js.group(1)
assert "location.hash" in js.group(1), "Source-linked chapters must stay deep-linkable"
with TemporaryDirectory() as temp:
    f=Path(temp)/"review.js"
    f.write_text(js.group(1),encoding="utf-8")
    check=run(["node","--check",str(f)],capture_output=True,text=True)
    assert check.returncode==0,check.stderr
    check=run(["node","--check",str(ROOT/"feedback/annotate.js")],capture_output=True,text=True)
    assert check.returncode==0,check.stderr
print("PASS: current complete Templo Mayor data (8 chapters, 21 claims, 12 sources), nested mobile navigation, source-preserving review UI and live comment binding")
