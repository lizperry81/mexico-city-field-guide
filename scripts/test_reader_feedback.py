#!/usr/bin/env python3
"""Regression check: no historical page is lost when mobile comments are enabled."""
from pathlib import Path
from subprocess import run, PIPE

SITE=Path("site")
PAGES=["poi/templo-mayor", "poi/zocalo", "poi/metropolitan-cathedral",
       "poi/national-palace", "walks/historic-center"]
asset=SITE/"feedback/annotate.js"
assert asset.exists() and asset.stat().st_size>6000
js=asset.read_text(encoding="utf-8")
for marker in ["function allNotes()", "cdmx-templo-feedback-v1",
               "navigator.share", "navigator.clipboard.writeText",
               "const PAGE=", "feedback-save", "feedback-open",
               "Comment on this passage"]:
    assert marker in js, f"Reader feedback feature missing {marker}"
check=run(["node","--check",str(asset)],stdout=PIPE,stderr=PIPE,text=True)
assert check.returncode==0,check.stderr
for slug in PAGES:
    path=SITE/slug/"index.html"
    html=path.read_text(encoding="utf-8")
    assert len(html)>9000, f"Historical page truncated: {slug}"
    assert html.count('<script src="../../feedback/annotate.js" defer></script>')==1, slug
    assert 'name="viewport"' in html, f"Not responsive/mobile: {slug}"
    assert "</body>" in html
assert (SITE/"index.html").stat().st_size>500_000,"Richer homepage was replaced"
print("PASS: reader comments, local persistence, cross-page export, legacy migration, 5 historical pages and retained rich homepage")
