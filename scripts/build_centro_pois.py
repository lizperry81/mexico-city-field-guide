#!/usr/bin/env python3
"""Publish substantial Centro Histórico POIs from the preserved Centro dossier.

This is an additive view of the original V81 historical guide content. It
does not alter the base app, records, claims, or bibliography.
"""
from __future__ import annotations
import json
from pathlib import Path
from html import escape

SITE = Path("site")
DATA = json.loads((SITE / "data" / "centro.json").read_text(encoding="utf-8"))
STOPS = DATA["stops"]
PAGES = {
    "zocalo": ("zocalo", "Zócalo", "A square of successive governments, markets, popular protest and archaeological discovery."),
    "metropolitan-cathedral": ("catedral", "Metropolitan Cathedral", "A colonial construction project, a sinking foundation and a history of the city under its stone."),
    "national-palace": ("palacio", "National Palace", "Government on the site of Mexica power, and the competing histories on Diego Rivera's walls."),
}
RELATED = [
    ("Templo Mayor", "../templo-mayor/"),
    ("Zócalo", "../zocalo/"),
    ("Metropolitan Cathedral", "../metropolitan-cathedral/"),
    ("National Palace", "../national-palace/"),
]
def h(value):
    return escape(str(value if value is not None else ""), quote=True)

def render_paragraph(par):
    if isinstance(par, list):
        body = par[0] if par else ""
        ids = par[1] if len(par)>1 and isinstance(par[1], list) else []
        status = par[2] if len(par)>2 else ""
    else:
        body, ids, status = par, [], ""
    refs = ", ".join(str(x) for x in ids)
    return (f'<p class="narrative">{h(body)}</p>'
            f'<p class="source">Archived source IDs: {h(refs or "not specified")}. '
            f'{h("Flag: " + str(status) + ". " if status else "")}'
            'Page-specific verification pending.</p>')

def render_blocks(blocks):
    output=[]
    for item in blocks:
        if "p" in item:
            output.append(render_paragraph(item["p"]))
        elif "h" in item:
            output.append(f'<h3>{h(item["h"])}</h3>')
        elif "where" in item:
            output.append(f'<p class="waypoint">{h(item["where"])}</p>')
        elif "take" in item:
            output.append(f'<div class="observation"><strong>Consider</strong><p>{h(item["take"])}</p></div>')
        elif "obj" in item:
            obj = item["obj"]
            output.append(f'<section class="object"><h3>{h(obj.get("name","Object"))}</h3>')
            if obj.get("p"):
                output.append(render_paragraph(obj["p"]))
            for look in obj.get("look", []):
                output.append('<div class="observation"><strong>Look closely</strong>'
                              +render_paragraph(look)+'</div>')
            output.append('</section>')
        elif "fork" in item:
            fork=item["fork"]
            output.append(f'<p class="source">{h(fork.get("q","Optional route"))}</p>')
    return "".join(output)

def build(slug, record_key, title, subtitle):
    record = STOPS[record_key]
    pts = [entry["pt"] for entry in record.get("read",[]) if "pt" in entry]
    observations = record.get("find",[])
    assert len(pts) >= 5, f"{title}: not enough preserved historical content"
    assert len(observations) >= 2, f"{title}: missing observation points"
    sections=[]
    for i, pt in enumerate(pts, 1):
        more=""
        for extra in pt.get("more", []):
            more += ('<details class="deeper"><summary>Explore further: '
                     +h(extra.get("label","Historical context"))+'</summary>'
                     +render_blocks(extra.get("blocks",[]))+'</details>')
        period = (f'<span class="date">{h(pt["when"])}</span>' if pt.get("when") else "")
        sections.append(
            f'<section class="chapter" id="chapter-{i}">'
            f'<p class="eyebrow">HISTORICAL LAYER {i} {period}</p>'
            f'<h2>{h(pt.get("h","Historical subject"))}</h2>'
            +render_blocks(pt.get("blocks",[]))
            +more+"</section>")
    order = "".join(f'<a href="#chapter-{i}">{i}. {h(p.get("h","Historical subject"))}</a>'
                    for i,p in enumerate(pts,1))
    on_site = "".join(f'<li><span>{i:02d}</span><p>{h(x)}</p></li>' for i,x in enumerate(observations,1))
    links = "".join(f'<a href="{h(href)}">{h(name)}</a>' for name,href in RELATED
                    if name.lower().replace(" ","-") != slug)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)} | Ciudad Viva Field Guide</title>
<meta name="description" content="{h(subtitle)}">
<style>
:root {{--ink:#142531;--jade:#126c69;--muted:#536875;--line:#dce5e8;--paper:#fff}}
* {{box-sizing:border-box}}
html {{scroll-behavior:smooth}}
body {{margin:0;background:#f5f8f9;color:var(--ink);font:16px/1.7 system-ui,-apple-system,sans-serif}}
a {{color:#08686d}}
.top {{background:#112b3c;color:white;padding:18px max(20px,calc((100vw - 1050px)/2));display:flex;gap:20px;justify-content:space-between;flex-wrap:wrap}}
.top a {{color:#c4e7e3;text-decoration:none}}
main {{max-width:1050px;margin:auto;padding:34px 20px 100px}}
h1 {{font:700 clamp(40px,6vw,70px)/1.1 Georgia,serif;margin:12px 0}}
h2 {{font:700 clamp(25px,3vw,34px)/1.25 Georgia,serif}}
h3 {{font:700 20px/1.3 Georgia,serif}}
.lead {{font:21px/1.5 Georgia,serif;max-width:760px}}
.eyebrow {{font:800 12px/1.4 system-ui,sans-serif;letter-spacing:.12em;color:#126c69}}
.status {{border-left:4px solid #b77d2d;background:#fcf3e4;padding:15px;margin:24px 0;max-width:820px}}
.layout {{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:40px}}
.chapters {{min-width:0}}
.chapter {{padding:32px 0;border-bottom:1px solid var(--line);scroll-margin-top:26px}}
.narrative {{font:19px/1.8 Georgia,serif;margin:18px 0 8px}}
.source {{font-size:13px;color:var(--muted);margin:0 0 18px}}
.date {{background:#e1eff0;border-radius:6px;padding:3px 7px;letter-spacing:0;font-size:12px}}
aside {{align-self:start;position:sticky;top:20px;border:1px solid var(--line);background:white;padding:18px;border-radius:12px}}
aside a {{display:block;text-decoration:none;font-size:14px;margin:12px 0}}
details {{padding:15px 18px;margin:20px 0;background:white;border:1px solid var(--line);border-radius:12px}}
summary {{cursor:pointer;font-weight:700;color:#08686d}}
.waypoint {{color:#126c69;font-weight:700}}
.observations {{padding:22px 24px;background:#e8f2f1;border-radius:14px}}
.observations ol {{padding:0;margin:0;list-style:none}}
.observations li {{display:flex;align-items:start;gap:16px;border-bottom:1px solid #c8dedc;padding:12px 0}}
.observations li:last-child {{border:0}}
.observations li span {{color:#126c69;font-weight:800}}
.observations li p {{margin:0}}
.observation,.object {{margin:18px 0;padding:14px 18px;background:#edf4f3;border-left:3px solid var(--jade)}}
.next a {{display:inline-block;margin:7px 14px 7px 0}}
@media(max-width:760px) {{.layout {{display:block}}aside {{position:static;margin-top:20px}}.narrative {{font-size:18px}}}}
</style></head>
<body>
<header class="top"><a href="../../">← Main Field Guide</a><a href="../templo-mayor/">Templo Mayor historical guide</a></header>
<main>
<p class="eyebrow">HISTORIC CENTER · PLACE-BASED HISTORY</p>
<h1>{h(title)}</h1><p class="lead">{h(subtitle)}</p>
<p>{h(record.get("summary",""))}</p>
<div class="status"><strong>Research-stage material.</strong> These are substantive historical
interpretations preserved from the existing city guide, with original source IDs.
They have not all received independent page-level verification. Museum access,
tours, opening hours and displays can change; consult current official information.</div>
<section class="observations" aria-labelledby="look-title">
<h2 id="look-title">What to look for on site</h2><p>{h(record.get("spot",""))}</p>
<ol>{on_site}</ol></section>
<div class="layout"><article class="chapters" aria-label="Historical chapters">
{''.join(sections)}
</article><aside aria-label="Chapter navigation"><strong>Explore the historical layers</strong>
{order}</aside></div>
<section class="chapter next"><h2>Continue exploring the Historic Center</h2>
<p>These places are historically connected, not separate sightseeing entries.
Follow the political and physical transformation of Tenochtitlan and Mexico City.</p>
{links}
<p class="source">The original historical dossier and source IDs remain in the
existing application. Check the evidence library for the editorial status of each claim.</p>
<a href="../../research-library/">Research evidence library</a></section>
</main></body></html>
"""
    path = SITE / "poi" / slug / "index.html"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(page,encoding="utf-8")
    assert len(page)>9000, f"Unexpectedly thin {slug} page: {len(page)} chars"
    print(f"Built {path}: {len(pts)} historic layers, {len(observations)} on-site observations, "
          f"{sum(len(p.get('more',[])) for p in pts)} optional deep dives, {len(page)} chars")

if __name__ == "__main__":
    for slug, (key,title,subtitle) in PAGES.items():
        build(slug,key,title,subtitle)
