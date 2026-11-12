#!/usr/bin/env python3
"""Generate a real POI experience from the recovered app's research archives."""
import json,html,pathlib,re
root=pathlib.Path("site")
data=root/"data"
def read(name):
    return json.loads((data/name).read_text(encoding="utf-8"))
walk=read("research/templo_walk_v63.json")
pilot=read("research/templo_mayor_pilot.json")
discovery=read("research/templo_verified_discoveries_v68.json")
centro=read("centro.json")
def e(x):return html.escape(str(x or ""),quote=True)
chapters=walk.get("chapters",[])
assert len(chapters)>=3, "Missing historic walk chapters"
assert len(pilot.get("claims",[]))>=15, "Missing claims"
def chapter(c,i):
    title=e(c.get("title",f"Section {i}"))
    body=e(c.get("core_text","")).replace("\n","<br>")
    extras=[]
    for k in ("what_to_look_for","look_for","field_prompt","evidence","uncertainty","historical_context","deep_dive","source_note"):
        v=c.get(k)
        if v:extras.append(f'<div class="aside"><b>{e(k.replace("_"," ").title())}</b><p>{e("; ".join(map(str,v)) if isinstance(v,list) else v)}</p></div>')
    return f'<section id="walk-{i}" class="section"><p class="eyebrow">FIELD STOP {i}</p><h2>{title}</h2><p class="prose">{body}</p>{"".join(extras)}</section>'
def claim(c):
    ids=", ".join(map(str,c.get("source_ids",[])))
    return f'<details><summary>{e(c.get("statement","Historical claim"))}</summary><p><b>Evidence IDs:</b> {e(ids or "Not linked")}</p><p><b>Review status:</b> {e(c.get("status","Unreviewed"))}</p><p><b>Locator:</b> {e(c.get("source_locator") or "No page locator recorded")}</p></details>'
def source(d):
    url=d.get("url","")
    link=f'<a href="{e(url)}" target="_blank" rel="noopener">Open institutional or publisher record ↗</a>' if url.startswith("https://") else ""
    return f'<details><summary>{e(d.get("title","Research source"))} <span class="muted">({e(d.get("year",""))})</span></summary><p>{e(d.get("citation",d.get("annotation","")))}</p><p>{e(d.get("annotation",""))}</p><p><b>Review:</b> {e(d.get("verification","not recorded"))}; full text read: {e(d.get("full_text_read",False))}</p>{link}</details>'
sections="".join(chapter(c,i) for i,c in enumerate(chapters,1))
claims="".join(claim(c) for c in pilot["claims"])
sources="".join(source(d) for d in discovery)
toc="".join(f'<a href="#walk-{i}">{i}. {e(c.get("title","Field stop"))}</a>' for i,c in enumerate(chapters,1))
page="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Templo Mayor | Ciudad Viva Field Guide</title>
<style>
:root{--ink:#142531;--muted:#526774;--jade:#0d746e;--paper:#fff;--line:#dce5e8}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f7f8;color:var(--ink);font:16px/1.65 system-ui,-apple-system,sans-serif}header{background:#112b3c;color:#fff;padding:17px max(18px,calc((100vw - 1050px)/2));display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}header a{color:#bce5dc;text-decoration:none}.shell{max-width:1050px;margin:auto;padding:24px 18px 110px}.eyebrow{font-size:12px;letter-spacing:.11em;color:var(--jade);font-weight:800;text-transform:uppercase}h1{font:700 clamp(40px,6vw,72px)/1.07 Georgia,serif;margin:12px 0 18px}h2{font:700 clamp(26px,3.2vw,37px)/1.18 Georgia,serif;margin:0 0 18px}h3{margin:0 0 10px}.lead{font:21px/1.55 Georgia,serif;max-width:760px}.tabs{position:sticky;top:0;z-index:5;background:#fff;border-block:1px solid var(--line);display:flex;gap:6px;overflow-x:auto;padding:10px 0}.tabs button{border:0;border-radius:22px;padding:10px 15px;background:#e9f0f1;white-space:nowrap;font:600 14px system-ui;cursor:pointer}.tabs button.active{background:var(--jade);color:#fff}.panel{display:none}.panel.active{display:block}.layout{display:grid;grid-template-columns:minmax(0,1fr) 255px;gap:30px}.section{padding:32px 0;border-bottom:1px solid var(--line);scroll-margin-top:85px}.prose{font:19px/1.75 Georgia,serif;white-space:normal}.aside{padding:15px 18px;border-left:3px solid var(--jade);background:#e8f1f1;margin:18px 0}.aside p{margin:5px 0}.side{position:sticky;top:78px;align-self:start;background:#fff;padding:20px;border:1px solid var(--line);border-radius:12px}.side a{display:block;color:#155e62;text-decoration:none;margin:11px 0;font-size:14px}.card{background:#fff;padding:22px;border:1px solid var(--line);border-radius:14px;margin:18px 0}details{border-top:1px solid var(--line);padding:15px 0}summary{cursor:pointer;font-weight:650}details p{font-size:14px;color:#3b515d}.muted{color:var(--muted)}input{padding:13px 15px;border:1px solid #9db5bd;border-radius:8px;font:inherit;width:100%}a{color:#116b71}.meta{display:flex;gap:10px;flex-wrap:wrap}.meta span{background:#e3eff0;border-radius:15px;padding:5px 11px;font-size:13px}.notice{border-left:4px solid #bd823b;background:#f9f0df;padding:15px;margin:22px 0}.hidden{display:none!important}@media(max-width:760px){.layout{display:block}.side{position:static;margin:18px 0}.prose{font-size:18px}}
</style></head><body>
<header><a href="../">← Ciudad Viva · Main guide</a><a href="../research-library/">Research evidence library</a></header>
<main class="shell"><div class="eyebrow">POINT OF INTEREST · HISTORIC CENTER</div><h1>Templo Mayor</h1><p class="lead">Explore the excavated ceremonial center of Tenochtitlan through historical interpretation, archaeological evidence, and a field sequence built from the project's earlier research—not a new short-form summary.</p>
<div class="meta"><span>Mexica</span><span>Archaeology</span><span>Construction phases</span><span>Conquest</span><span>Centro Histórico</span></div>
<div class="notice"><b>Editorial status:</b> Research-stage guide. Claims with incomplete page verification are labeled. Check official sources for current opening hours and accessibility; no live availability is claimed.</div>
<div class="tabs" role="tablist" aria-label="Point of interest sections"><button class="active" data-panel="story">Field experience</button><button data-panel="evidence">Claims & evidence</button><button data-panel="sources">Sources</button><button data-panel="visit">Visit & connections</button></div>
<div id="story" class="panel active"><div class="layout"><article>""" + sections + """</article><aside class="side"><b>Explore the field sequence</b>""" + toc + """</aside></div></div>
<div id="evidence" class="panel"><section class="section"><h2>Historical claims and review status</h2><p>These """ + str(len(pilot["claims"])) + """ research claims are recovered from the Templo Mayor pilot, with their original status and source identifiers. They are not automatically treated as verified conclusions.</p><input id="claimsearch" placeholder="Filter claims by topic or wording" aria-label="Search historical claims"><div id="claimlist">""" + claims + """</div></section></div>
<div id="sources" class="panel"><section class="section"><h2>Excavation and scholarly source records</h2><p>Research archive records include original citations, links, and verification notes. A publisher page being checked does not mean a full publication was read.</p>""" + sources + """</section></div>
<div id="visit" class="panel"><section class="section"><h2>Use this guide on site</h2><p>Begin with the excavation's surviving structures, follow the field stops in order where accessible, then use the museum to connect objects to excavation contexts. Exact route and object visibility depend on current site access.</p><div class="card"><h3>Official access and visitor information</h3><p><a href="https://www.inah.gob.mx/zonas/zona-arqueologica-templo-mayor" target="_blank" rel="noopener">INAH Templo Mayor archaeological zone ↗</a></p><p>Hours, admission, and accessibility require a current official check.</p></div><h3>Related historical places</h3><p>Historic Center · Zócalo · Metropolitan Cathedral · National Palace · Tlatelolco. These relationships will support the future walk planner.</p><p><a href="../">Return to the full Field Guide</a></p></section></div>
</main><script>document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-panel]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===b.dataset.panel))});document.querySelector('#claimsearch').oninput=e=>{let q=e.target.value.toLowerCase();document.querySelectorAll('#claimlist details').forEach(x=>x.classList.toggle('hidden',!x.textContent.toLowerCase().includes(q)))};</script></body></html>"""
out=root/"poi"/"templo-mayor"/"index.html"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(page,encoding="utf-8")
assert len(page)>10000
print(f"Built {out}: {len(chapters)} field chapters, {len(pilot['claims'])} research claims, {len(discovery)} scholarly records")
