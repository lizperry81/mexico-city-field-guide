#!/usr/bin/env python3
"""Validate preserved historical coverage, cross-POI deep links and walk outputs."""
import json
import re
from html import escape
from pathlib import Path
from subprocess import run, PIPE
from tempfile import TemporaryDirectory

root=Path("site")
src=json.loads((root/"data"/"centro.json").read_text(encoding="utf-8"))
manifest=json.loads((root/"data"/"historic-center-walk.json").read_text(encoding="utf-8"))
walk=(root/"walks"/"historic-center"/"index.html").read_text(encoding="utf-8")
assert manifest["version"]=="historic-center-walk-1"
assert manifest["site_access_verified_live"] is False
assert manifest["research_state"]=="archived-source-ids-not-independently-reverified"
assert len(manifest["stops"])==4 and len(manifest["threads"])==4
assert [x["id"] for x in manifest["modes"]]==["outdoor","focus","deep"]
assert len(walk)>12000 and "__THREAD" not in walk
assert all(x in walk for x in ['data-mode="outdoor"','data-mode="focus"','data-mode="deep"',
                              'data-choose-thread="conquest"','data-choose-thread="government"',
                              'data-choose-thread="water"','data-choose-thread="public"',
                              'aria-live="polite"','id="stop-templo-mayor"'])
assert "page-specific scholarly review" in walk.lower()
expected={"templo-mayor":("templo",5),"zocalo":("zocalo",6),
          "metropolitan-cathedral":("catedral",7),"national-palace":("palacio",5)}
for slug,(key,n) in expected.items():
    poi=(root/"poi"/slug/"index.html").read_text(encoding="utf-8")
    parts=[item["pt"] for item in src["stops"][key]["read"] if "pt" in item]
    assert len(parts)>=n
    assert "historic-walk-crosslink" in poi and 'href="../../walks/historic-center/"' in poi
    assert len(poi)>9000
    assert slug in walk
    assert len(src["stops"][key]["find"])>=3
    for t in manifest["threads"]:
        for entry in t["entries"]:
            if entry["slug"]!=slug:continue
            assert entry["original_source_ids"],entry
            assert any(x["h"]==entry["title"] for x in parts),entry
            assert 'href="'+escape(entry["url"],quote=True)+'"' in walk,entry
if (root/"index.html").exists():
    home=(root/"index.html").read_text(encoding="utf-8")
    assert 'href="walks/historic-center/"' in home and len(home)>500000
templo=(root/"poi"/"templo-mayor"/"index.html").read_text(encoding="utf-8")
assert 'id="hash-to-panel-walk"' in templo
assert 'id="dossier"' in templo
assert 'data-panel="dossier"' in templo
assert all('id="dossier-topic-'+str(i)+'"' in templo for i in range(1,7))
assert '#dossier-topic-' in walk
assert "id.indexOf('dossier-topic-')" in templo
# Validate new standalone inline JavaScript syntax without requiring a browser.
scripts=re.findall(r"<script[^>]*>(.*?)</script>",walk,flags=re.S)
assert len(scripts)==1
with TemporaryDirectory() as d:
    path=Path(d)/"walk.js"
    path.write_text(scripts[0],encoding="utf-8")
    result=run(["node","--check",str(path)],stdout=PIPE,stderr=PIPE,text=True)
    assert result.returncode==0,result.stderr
print("PASS — 4 cross-linked preserved POIs; 4 historically sourced threads; 3 working-mode controls; mobile walk and JavaScript syntax")
