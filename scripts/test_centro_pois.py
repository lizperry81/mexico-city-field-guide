#!/usr/bin/env python3
"""Regression tests for three expanded Centro Histórico historical field dossiers."""
import json
from pathlib import Path
from html import escape

root=Path("site")
centro=json.loads((root/"data"/"centro.json").read_text(encoding="utf-8"))
expected={"zocalo":("zocalo",6,3),"metropolitan-cathedral":("catedral",7,3),"national-palace":("palacio",5,3)}
for slug,(key,min_topics,min_observations) in expected.items():
    page=(root/"poi"/slug/"index.html").read_text(encoding="utf-8")
    record=centro["stops"][key]
    pts=[x["pt"] for x in record["read"] if "pt" in x]
    assert len(pts)>=min_topics
    assert len(record["find"])>=min_observations
    assert len(page)>9000,(slug,len(page))
    assert escape(record["summary"],quote=True) in page
    for pt in pts:
        assert escape(pt["h"],quote=True) in page,(slug,pt["h"])
        for block in pt.get("blocks",[]):
            if "p" in block:
                para=block["p"];txt=para[0] if isinstance(para,list) else para
                assert escape(txt,quote=True) in page,(slug,txt[:60])
        for extra in pt.get("more",[]):
            assert escape(extra.get("label","Historical context"),quote=True) in page,(slug,"missing deep dive")
    for observation in record["find"]:
        assert escape(observation,quote=True) in page,(slug,"missing on-site observation")
    for href in ['href="../../"', 'href="../templo-mayor/"','href="../../research-library/"']:
        assert href in page,(slug,href)
    assert "Page-specific verification pending" in page
    assert "What to look for on site" in page
    print("PASS",slug,len(pts),"historical layers",len(record["find"]),"observations",len(page),"HTML chars")
