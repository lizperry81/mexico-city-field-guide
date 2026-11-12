#!/usr/bin/env python3
"""Test research preservation and functional code in the three Centro mobile readers."""
import json
import re
from html import escape
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

root=Path("site")
centro=json.loads((root/"data/centro.json").read_text(encoding="utf-8"))
pages={"zocalo":("zocalo",6,3),"metropolitan-cathedral":("catedral",7,3),"national-palace":("palacio",5,3)}
assert (root/"index.html").stat().st_size > 500_000, "Original rich homepage lost"
for slug,(key,min_chapters,min_observations) in pages.items():
    base=(root/"poi"/slug/"index.html").read_text(encoding="utf-8")
    page=(root/"poi"/slug/"review/index.html").read_text(encoding="utf-8")
    record=centro["stops"][key]
    history=[p["pt"] for p in record["read"] if "pt" in p]
    assert len(history)>=min_chapters and len(record["find"])>=min_observations
    assert len(page)>len(base)+4500 and len(page)>14000,(slug,len(page),len(base))
    assert 'id="centro-reader-link"' in base
    assert 'href="review/"' in base
    assert 'id="centro-review-script"' in page
    assert 'id="centro-review-styles"' in page
    assert 'name="viewport"' in page and 'width=device-width' in page
    assert 'src="../../../feedback/annotate.js"' in page
    assert 'href="../../../research-library/"' in page
    assert 'href="../../../"' in page, "Homepage link must be rebased for nested review"
    for x in ('review-switch','dataset.mode','review-chapter-select',
              'review-observation-','Choose guide mode','Discover','Explore','Plan',
              'Page-specific verification pending','What to look for on site'):
        assert x in page, (slug,x)
    assert escape(record["summary"],quote=True) in page
    for p in history:
        assert escape(p["h"],quote=True) in page,(slug,p["h"])
        for b in p.get("blocks",[]):
            if "p" in b:
                txt=b["p"][0] if isinstance(b["p"],list) else b["p"]
                assert escape(txt,quote=True) in page,(slug,txt[:80])
                if isinstance(b["p"],list) and len(b["p"])>1 and isinstance(b["p"][1],list):
                    for ref in b["p"][1]:
                        assert escape(ref,quote=True) in page,(slug,ref)
        for extra in p.get("more",[]):
            assert escape(extra.get("label","Historical context"),quote=True) in page,(slug,"deep dive")
    for obs in record["find"]:
        assert escape(obs,quote=True) in page,(slug,"on-site observation")
    js=re.search(r'<script id="centro-review-script">([\s\S]*?)</script>',page)
    assert js,slug
    with TemporaryDirectory() as temp:
        script=Path(temp)/"review.js"
        script.write_text(js.group(1),encoding="utf-8")
        checked=run(["node","--check",str(script)],capture_output=True,text=True)
        assert checked.returncode==0,(slug,checked.stderr)
    print("PASS",slug,len(history),"complete chapters",len(record["find"]),
          "on-site observations, original source IDs, dynamic reader JS, feedback and links")
print("PASS: 3 generated mobile review pages preserve the original POIs and rich homepage")
