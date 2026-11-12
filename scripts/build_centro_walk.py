#!/usr/bin/env python3
"""Build a source-preserving Historic Center learning walk from the archived guide.

Additive publisher: reads centro.json and existing generated POIs, never
rewrites the original research, and links all four field dossiers together.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

SITE=Path("site")
CENTRO=json.loads((SITE/"data"/"centro.json").read_text(encoding="utf-8"))["stops"]

STOPS=[
    dict(slug="templo-mayor",key="templo",name="Templo Mayor",
         exterior="From the public perimeter, locate the excavated remains beside the cathedral. The twin shrine foundations are best examined inside the zone.",
         inside="Look for the paired Huitzilopochtli and Tlaloc shrines, the roofed Stage II and the House of the Eagles. Do not assume any particular section is open.",
         heading="One temple inside another",
         status="Archaeological zone and museum: admission, displayed objects and accessibility require a current official check."),
    dict(slug="metropolitan-cathedral",key="catedral",name="Metropolitan Cathedral",
         exterior="From the square, compare the cathedral facade and twin bell towers with the excavated Mexica precinct nearby.",
         inside="If open, examine the uneven floor and the estípite columns of the gilded Altar de los Reyes, subject to current access.",
         heading="Built on the temple, by the conquered",
         status="Cathedral access and the availability of altars or chapels can change."),
    dict(slug="zocalo",key="zocalo",name="Zócalo",
         exterior="Stand toward the center of the square. Identify the cathedral to the north, National Palace to the east and the Templo Mayor ruins northeast.",
         inside="This is primarily an outdoor stop. The historical dossier examines the 1692 riot and the Sun Stone discovery in 1790.",
         heading="Church, state and the empire they replaced",
         status="The square can be affected by events, demonstrations and temporary closures."),
    dict(slug="national-palace",key="palacio",name="National Palace",
         exterior="From the Zócalo, observe the long eastern facade of the National Palace and compare it with the cathedral and former Mexica ceremonial precinct.",
         inside="If access is available, use the staircase murals to compare Rivera's portrayal of the pre-Hispanic city, conquest and twentieth-century politics.",
         heading="Five centuries of power on one spot",
         status="Palace interiors, murals and historical rooms may be closed or subject to security arrangements.")
]
THREADS=[
    dict(id="conquest",title="Conquest and reconstruction",question="What changed physically after 1521?",
         intro="Compare the damaged Mexica ceremonial center, early Spanish religious construction, and changing interpretations of the conquest.",
         entries=[("templo-mayor","The massacre at Toxcatl"),("metropolitan-cathedral","Built on the temple, by the conquered"),("national-palace","A conquest without heroes")]),
    dict(id="government",title="Who controlled the city?",question="How did political power occupy the same blocks?",
         intro="Follow temple tribute, viceregal government and the republican state without assuming that their institutions were identical.",
         entries=[("templo-mayor","Who paid for it"),("zocalo","Church, state and the empire they replaced"),("national-palace","Five centuries of power on one spot")]),
    dict(id="water",title="The buried lake",question="What is still visible of the island city?",
         intro="The lake shaped the old capital, the cathedral foundation and the square where archaeological objects were rediscovered.",
         entries=[("templo-mayor","An island capital, founded in 1325"),("metropolitan-cathedral","The floor isn't level"),("zocalo","The stone under the pavement (1790)")]),
    dict(id="public",title="Protest, independence and memory",question="Whose history is represented in the public center?",
         intro="Read the 1692 crowd protest, later state ceremonies, and Rivera's twentieth-century mural as different forms of public history.",
         entries=[("zocalo","The day the poor burned the palace (1692)"),("metropolitan-cathedral","An emperor crowned, rebels' heads buried"),("national-palace","Rivera's history of Mexico")])
]
def h(value):return html.escape(str(value),quote=True)
def chapters(slug):
    key=next(s["key"] for s in STOPS if s["slug"]==slug)
    return [item["pt"] for item in CENTRO[key]["read"] if "pt" in item]
def topic_link(slug,heading):
    matches=[(i,p) for i,p in enumerate(chapters(slug),1) if p["h"]==heading]
    assert len(matches)==1,(slug,heading,"missing or changed archived heading")
    i,p=matches[0]
    anchor="dossier" if slug=="templo-mayor" else "chapter-"+str(i)
    return "../../poi/"+slug+"/#"+anchor,p
def refs_from(p):
    refs=[]
    for b in p.get("blocks",[]):
        v=b.get("p")
        if isinstance(v,list) and len(v)>1 and isinstance(v[1],list):
            refs.extend(v[1])
    return list(dict.fromkeys(str(x) for x in refs))
def build():
    for stop in STOPS:
        assert len(chapters(stop["slug"]))>=5
        assert len(CENTRO[stop["key"]]["find"])>=3
        assert len(CENTRO[stop["key"]]["ll"])==2
        assert any(p["h"]==stop["heading"] for p in chapters(stop["slug"]))
    threads=[]
    for thread in THREADS:
        entries=[]
        for slug,heading in thread["entries"]:
            link,p=topic_link(slug,heading)
            refs=refs_from(p)
            assert refs,(slug,heading,"missing archived source IDs")
            entries.append(dict(slug=slug,title=heading,url=link,original_source_ids=refs))
        threads.append(dict(id=thread["id"],title=thread["title"],question=thread["question"],
                            intro=thread["intro"],entries=entries))
    manifest={
        "version":"historic-center-walk-1",
        "source":"data/centro.json (preserved application archive)",
        "research_state":"archived-source-ids-not-independently-reverified",
        "site_access_verified_live":False,
        "modes":[
            {"id":"outdoor","label":"Outdoor circuit","estimate":"45–60 min","scope":"Exteriors only, no admission assumed"},
            {"id":"focus","label":"Archaeology focus","estimate":"2–3 hours","scope":"Optional Templo Mayor archaeological visit if open; other exterior stops"},
            {"id":"deep","label":"Full historic center","estimate":"4–6+ hours","scope":"Optional interior visits at Templo Mayor, Cathedral and National Palace if open"}
        ],
        "stops":[dict(slug=s["slug"],name=s["name"],coordinates=CENTRO[s["key"]]["ll"],
                      archived_minutes_estimate=CENTRO[s["key"]].get("mins"),
                      chapter_count=len(chapters(s["slug"])),
                      observation_count=len(CENTRO[s["key"]]["find"]),
                      research_status="archived-research-review-pending") for s in STOPS],
        "threads":threads
    }
    out=SITE/"data"/"historic-center-walk.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

    stop_html=[]
    for n,s in enumerate(STOPS,1):
        link,p=topic_link(s["slug"],s["heading"])
        ids=", ".join(refs_from(p)) or "not recorded"
        stop_html.append('<article class="stop" id="stop-'+h(s["slug"])+'" data-stop="'+h(s["slug"])+'">'
          '<p class="eyebrow">STOP '+str(n)+' / 4</p><h2>'+h(s["name"])+'</h2>'
          '<p class="field"><strong>Look outside</strong>'+h(s["exterior"])+'</p>'
          '<p class="field inside"><strong>When accessible</strong>'+h(s["inside"])+'</p>'
          '<p class="access">'+h(s["status"])+'</p>'
          '<a class="read" href="'+h(link)+'">Read the original chapter: '+h(s["heading"])+'</a>'
          '<p class="trace">Archived evidence IDs: '+h(ids)+'. Page-specific review is pending.</p>'
          '<a href="../../poi/'+h(s["slug"])+'/">Open the complete '+h(s["name"])+' historical dossier</a></article>')
    thread_html=[]
    for t in threads:
        links=[]
        for item in t["entries"]:
            name=next(s["name"] for s in STOPS if s["slug"]==item["slug"])
            links.append('<li><a href="'+h(item["url"])+'"><span>'+h(name)+'</span><strong>'+h(item["title"])+'</strong></a>'
                         '<small>Archived sources: '+h(", ".join(item["original_source_ids"]))+' · original evidence review pending</small></li>')
        thread_html.append('<section class="thread" data-thread="'+h(t["id"])+'"><h3>'+h(t["title"])+'</h3>'
                           '<p class="thread-question">'+h(t["question"])+'</p><p>'+h(t["intro"])+'</p><ol>'+''.join(links)+'</ol></section>')
    button_html=''.join('<button type="button" data-choose-thread="'+h(t["id"])+'" aria-pressed="false">'+h(t["title"])+'</button>' for t in threads)

    page=r'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Historic Center walk — Mexico City Field Guide</title>
<meta name="description" content="Follow the physical layers of Tenochtitlan, conquest, colonial Mexico and modern public memory through four connected sites.">
<style>
:root{--ink:#172d3b;--jade:#11746d;--navy:#102e40;--line:#d9e3e7;--muted:#4c6270}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f7f8;color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}
a{color:#096c71}button{font:inherit;cursor:pointer}header{background:var(--navy);padding:16px max(18px,calc((100vw - 1040px)/2));display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}header a{color:#d9f0ec;text-decoration:none}
main{max-width:1040px;margin:auto;padding:28px 18px 95px}.eyebrow{color:var(--jade);font-size:12px;letter-spacing:.11em;font-weight:800;text-transform:uppercase}
h1{font:700 clamp(37px,6vw,69px)/1.07 Georgia,serif;margin:12px 0 17px;max-width:870px}h2{font:700 clamp(26px,3.5vw,34px)/1.19 Georgia,serif;margin:10px 0 20px}h3{font:700 23px/1.27 Georgia,serif;margin:5px 0 8px}.lede{font:20px/1.56 Georgia,serif;max-width:820px}.note{padding:15px 18px;margin:21px 0;background:#fff6e9;border-left:4px solid #b17b30}
.controls{background:white;border:1px solid var(--line);border-radius:16px;padding:20px;margin:26px 0}.controls h2{font-size:25px;margin-bottom:9px}.choice{display:flex;gap:8px;flex-wrap:wrap}.choice button{border:1px solid #c8d6da;border-radius:11px;background:#eef4f4;padding:12px 14px;text-align:left;color:var(--ink)}.choice button[aria-pressed="true"],.navrow button[aria-pressed="true"]{background:var(--navy);color:white;border-color:var(--navy)}.choice small{display:block;opacity:.85}.plan{padding:13px 0 0;color:var(--muted)}
.stop{background:white;margin:17px 0;border:1px solid var(--line);border-radius:15px;padding:22px;scroll-margin-top:18px}.stop h2{margin-top:4px}.field{border-left:3px solid var(--jade);background:#edf5f4;padding:14px 16px}.field strong{display:block;margin-bottom:6px;color:#095a57}.access,.trace{font-size:13px;color:var(--muted)}.read{display:block;font-weight:700;margin:18px 0 5px}.walk-flow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:4px 0 17px}.walk-flow a{padding:8px 10px;background:#e6f1f0;border-radius:9px;text-decoration:none;font-size:14px}
.thread{border-top:1px solid var(--line);padding:21px 0}.thread-question{font-weight:750}.thread ol{list-style:none;padding:0;margin:16px 0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.thread li{border:1px solid var(--line);border-radius:12px;background:white;padding:15px}.thread li a{text-decoration:none;display:block}.thread li span{display:block;color:var(--muted);font-size:12px}.thread li strong{display:block;margin:6px 0}.thread li small{font-size:12px;color:var(--muted)}.navrow{display:flex;gap:8px;flex-wrap:wrap}.navrow button{background:#e6f1f0;border:1px solid #c8d6da;border-radius:10px;padding:10px}
@media(max-width:690px){.thread ol{display:block}.thread li{margin:10px 0}.choice button{flex:1 1 145px}.stop{padding:17px}.lede{font-size:19px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style></head><body>
<header><a href="../../">← Main field guide</a><a href="../../research-library/">Research evidence library</a></header>
<main>
<p class="eyebrow">LEARNING WALK · CENTRO HISTÓRICO · FOUR CONNECTED SITES</p>
<h1>From Tenochtitlan to Mexico City, one block at a time</h1>
<p class="lede">The surviving temple remains, the colonial cathedral, the main square and the seat of government tell different parts of the same history. Follow their physical connections rather than treating them as unrelated monuments.</p>
<div class="note"><strong>Editorial and practical limits.</strong> This walk links original historical dossiers and preserved source IDs. Many passages still need page-specific scholarly review. Time ranges are planning estimates, not travel-time or opening-hour guarantees. Verify current entry rules before relying on interior stops.</div>
<section class="controls" aria-labelledby="plan-title"><h2 id="plan-title">Shape the visit</h2>
<p>Choose the depth of the visit. All four places stay in geographic order; the inside/outside observations change.</p>
<div class="choice" role="group" aria-label="Visit depth">
<button type="button" data-mode="outdoor" aria-pressed="true">Outdoor circuit <small>45–60 min · exteriors only</small></button>
<button type="button" data-mode="focus" aria-pressed="false">Archaeology focus <small>2–3 hours · optional excavation entry</small></button>
<button type="button" data-mode="deep" aria-pressed="false">Full historic center <small>4–6+ hours · interiors when available</small></button>
</div><p class="plan" id="plan-message" aria-live="polite">Outdoor circuit: a four-stop, exterior-only walk. No ticketed entry assumed.</p></section>
<div class="walk-flow" aria-label="Route sequence"><a href="#stop-templo-mayor">1 · Templo Mayor</a><span aria-hidden="true">→</span><a href="#stop-metropolitan-cathedral">2 · Cathedral</a><span aria-hidden="true">→</span><a href="#stop-zocalo">3 · Zócalo</a><span aria-hidden="true">→</span><a href="#stop-national-palace">4 · National Palace</a></div>
<section aria-label="Four historical stops">__STOPS__</section>
<section aria-labelledby="threads-title"><p class="eyebrow">CASCADING HISTORY · FOLLOW A QUESTION</p><h2 id="threads-title">Take the same question through different places</h2>
<p>Each pathway opens the original historical chapter at a particular site. Archived evidence identifiers accompany links, without implying full-text scholarly verification.</p>
<div class="navrow" role="group" aria-label="Historical threads">__THREAD_BUTTONS__</div>
<div id="thread-sections">__THREADS__</div></section>
<a href="../../">Return to the complete Mexico City Field Guide</a></main>
<script>
(function(){
 var modes={
   outdoor:'Outdoor circuit: a four-stop, exterior-only walk. No ticketed entry assumed.',
   focus:'Archaeology focus: use the Templo Mayor interior guidance only if the zone is open. The other three stops remain exterior views. Allow for admission and queues.',
   deep:'Full historic center: explore interior observations wherever access is permitted. Expect closures and adjust the sequence if necessary.'
 };
 var buttons=document.querySelectorAll('[data-mode]');
 function setMode(mode){
   buttons.forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-mode')===mode));});
   document.getElementById('plan-message').textContent=modes[mode];
   document.querySelectorAll('.inside').forEach(function(el){
     var templo=el.closest('[data-stop="templo-mayor"]');
     el.hidden=mode==='outdoor'||(mode==='focus'&&!templo);
   });
 }
 buttons.forEach(function(b){b.addEventListener('click',function(){setMode(b.getAttribute('data-mode'));});});
 setMode('outdoor');
 var tbuttons=document.querySelectorAll('[data-choose-thread]');
 function chooseThread(id){
   tbuttons.forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-choose-thread')===id));});
   document.querySelectorAll('[data-thread]').forEach(function(t){t.hidden=t.getAttribute('data-thread')!==id;});
 }
 tbuttons.forEach(function(b){b.addEventListener('click',function(){chooseThread(b.getAttribute('data-choose-thread'));});});
 chooseThread('conquest');
})();
</script></body></html>'''
    page=page.replace("__STOPS__","".join(stop_html)).replace("__THREADS__","".join(thread_html)).replace("__THREAD_BUTTONS__",button_html)
    assert len(page)>12000 and "__THREADS__" not in page
    dest=SITE/"walks"/"historic-center"/"index.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(page,encoding="utf-8")

    box='<section class="historic-walk-crosslink" style="margin:24px 0;padding:18px;border:1px solid #c2d6d7;border-radius:12px;background:#e8f3f2"><strong>Follow the story across four sites</strong><p>Explore Templo Mayor, the Cathedral, the Zócalo and National Palace in one linked historical walk.</p><a href="../../walks/historic-center/">Open the Historic Center learning walk</a></section>'
    for stop in STOPS:
        target=SITE/"poi"/stop["slug"]/"index.html"
        content=target.read_text(encoding="utf-8")
        if 'historic-walk-crosslink' not in content:
            assert content.count("</main>")==1,stop["slug"]
            content=content.replace("</main>",box+"</main>")
        if stop["slug"]=="templo-mayor" and 'hash-to-panel-walk' not in content:
            adapter='''<script id="hash-to-panel-walk">(function(){function select(){var id=location.hash.slice(1);if(!id)return;var p=document.getElementById(id);if(!p||!p.classList.contains('panel'))return;document.querySelectorAll('[data-panel]').forEach(function(b){b.classList.toggle('active',b.dataset.panel===id);});document.querySelectorAll('.panel').forEach(function(el){el.classList.toggle('active',el.id===id);});p.scrollIntoView({block:'start'});}window.addEventListener('hashchange',select);select();})();</script>'''
            content=content.replace("</body>",adapter+"</body>")
        target.write_text(content,encoding="utf-8")
    homepage=SITE/"index.html"
    if homepage.exists():
        content=homepage.read_text(encoding="utf-8")
        if 'href="walks/historic-center/"' not in content:
            assert "</body>" in content
            banner='<a href="walks/historic-center/" style="display:block;max-width:680px;margin:16px auto;padding:16px;background:#112e40;color:#fff;text-align:center;border-radius:12px;text-decoration:none;font-weight:750">Explore the four-stop Historic Center learning walk →</a>'
            homepage.write_text(content.replace("</body>",banner+"</body>"),encoding="utf-8")
    print("PASS: four-stop historic walk, four original dossier gateways and four evidence-linked historical threads")

if __name__=="__main__":build()
