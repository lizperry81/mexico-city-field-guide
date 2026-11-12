#!/usr/bin/env python3
"""Build the commentable Discover/Explore/Plan preview from the *current built POI*.

The canonical original POI and its research are never replaced with a snapshot.
This creates an alternate presentation of the actual current full historical page.
Run after the historical POI, cross-links, and feedback script have been built.
"""
from pathlib import Path
import re

ROOT = Path("site")
SOURCE = ROOT / "poi/templo-mayor/index.html"
DEST = ROOT / "poi/templo-mayor/review/index.html"
SCRIPT = '<script src="../../feedback/annotate.js" defer></script>'
STYLE = r"""
<style id="review-layout-styles">
.review-intro{margin:18px 0;background:white;border:1px solid var(--line);border-radius:15px;padding:18px}
.review-intro p{margin-bottom:0}
.review-switch{position:sticky;top:0;z-index:20;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;background:#f4f7f8;padding:10px 0}
.review-switch button{background:white;border:1px solid #bed4d6;border-radius:11px;padding:12px 4px;color:#173d46;font:700 15px system-ui;cursor:pointer}
.review-switch button[aria-selected="true"]{background:#0d746e;color:white}
.review-switch small{display:block;font:12px system-ui;font-weight:400;margin-top:3px}
.review-screen{display:none}.review-screen.active{display:block}
.review-card{padding:20px;background:white;border:1px solid var(--line);border-radius:14px;margin:14px 0 22px}
.review-card .section{padding:16px 0}
.review-card h2{margin-top:8px}
.review-pager{display:flex;justify-content:space-between;gap:10px;margin:18px 0 0}
.review-pager button,.review-deep-button{border:0;border-radius:10px;padding:12px 15px;background:#0d746e;color:white;font:700 14px system-ui;cursor:pointer}
.review-pager button:disabled{opacity:.35;cursor:not-allowed}
.review-deep-button{display:inline-block;margin:7px 8px 7px 0;background:#dcefeb;color:#195b60;border:1px solid #97c5c2}
.review-count{font:700 12px system-ui;letter-spacing:.07em;color:#0d746e;text-transform:uppercase}
.review-collapsible{border:1px solid var(--line);background:white;border-radius:12px;padding:15px 18px;margin:18px 0}
.review-collapsible>summary{font:700 16px system-ui;cursor:pointer}
#review-overlay{position:fixed;inset:0;z-index:9500;background:#132a36b5;display:none;align-items:flex-end;justify-content:center}
#review-overlay.open{display:flex}
#review-dialog{box-sizing:border-box;background:#fff;color:#152e3b;padding:22px;border-radius:18px 18px 0 0;width:min(100%,750px);max-height:90dvh;overflow-y:auto;overscroll-behavior:contain}
#review-dialog .panel{display:block}
#review-dialog button{font:700 14px system-ui;border:1px solid #8db7b8;border-radius:9px;padding:10px 12px;margin:5px 5px 5px 0;background:#e5f1ef;color:#195a5e}
#review-dialog button[aria-pressed="true"]{background:#0d746e;color:#fff}
#review-dialog .research-pane{display:none}
#review-dialog .research-pane.active{display:block}
#review-dialog h2{margin:15px 0}
@media(max-width:750px){.review-card{padding:16px}.review-switch button{font-size:14px}.review-switch small{font-size:11px}}
</style>
"""
JS = r"""
<script id="review-layout-script">
document.addEventListener('DOMContentLoaded',()=>{
'use strict';
const main=document.querySelector('main.shell');
const tabBar=main?.querySelector('.tabs');
if(!main||!tabBar){throw Error('Preserved Templo Mayor panels unavailable');}
const originals={};
for(const key of ['story','site','dossier','museum','evidence','sources','visit']){
  const node=document.getElementById(key);
  if(!node)throw Error('Missing preserved panel: '+key);
  originals[key]=node;
  node.classList.remove('panel','active');
}
const intro=document.createElement('section');
intro.className='review-intro';
intro.innerHTML='<div class="eyebrow">READER REVIEW · HISTORICAL FIELD GUIDE</div><h2>One place. Three ways to experience it.</h2><p><b>Discover</b> tells the history; <b>Explore</b> guides your attention on site; <b>Plan</b> helps arrange the visit. Open claims and sources as optional evidence panels without losing your place.</p>';
tabBar.replaceWith(intro);
const bar=document.createElement('nav');
bar.className='review-switch';
bar.setAttribute('aria-label','Reading mode');
const tabs=[['discover','Discover','Historical chapters'],['explore','Explore','On-site field stops'],['plan','Plan','Visit essentials']];
tabs.forEach(([id,label,description])=>{
  const button=document.createElement('button');
  button.type='button';button.dataset.reviewMode=id;button.setAttribute('aria-controls','review-'+id);
  button.setAttribute('aria-selected',id==='discover'?'true':'false');
  button.innerHTML=label+'<small>'+description+'</small>';
  bar.appendChild(button);
});
intro.after(bar);
const screens={};
for(const [id] of tabs){
  const section=document.createElement('section');
  section.id='review-'+id;section.className='review-screen';
  section.setAttribute('aria-label',id+' reading mode');
  if(id==='discover')section.classList.add('active');
  bar.after(section);screens[id]=section;
}
function caption(text){
  const el=document.createElement('p');el.className='review-count';el.textContent=text;return el;
}
function card(){
  const article=document.createElement('article');article.className='review-card';return article;
}
function pager(host,items,label){
  let active=0;
  const cards=items.map((node,i)=>{
    const wrap=card();
    wrap.append(caption(label+' '+(i+1)+' / '+items.length),node);
    host.append(wrap);
    return wrap;
  });
  const nav=document.createElement('div');nav.className='review-pager';
  const prev=document.createElement('button');prev.textContent='← Previous';
  const next=document.createElement('button');next.textContent='Next →';
  nav.append(prev,next);host.append(nav);
  function select(i,scroll=false){
    active=Math.max(0,Math.min(i,cards.length-1));
    cards.forEach((c,j)=>c.hidden=j!==active);
    prev.disabled=active===0;next.disabled=active===cards.length-1;
    if(scroll)bar.scrollIntoView({block:'start',behavior:'auto'});
  }
  prev.onclick=()=>select(active-1,true);next.onclick=()=>select(active+1,true);
  select(0);return select;
}
function activate(id,scroll=true){
  Object.entries(screens).forEach(([key,el])=>el.classList.toggle('active',key===id));
  bar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.reviewMode===id)));
  if(scroll)bar.scrollIntoView({block:'start',behavior:'auto'});
}
bar.querySelectorAll('button').forEach(b=>b.onclick=()=>activate(b.dataset.reviewMode));
const hist=Array.from(originals.dossier.querySelectorAll(':scope > .section'));
if(hist.length<7)throw Error('Recovered historical dossier unexpectedly incomplete');
const historicalIntro=hist.shift();
const discoveryIntro=card();discoveryIntro.append(historicalIntro);
screens.discover.append(discoveryIntro);
const historyHolder=document.createElement('div');screens.discover.append(historyHolder);
const chooseHistory=pager(historyHolder,hist,'Historical chapter');
const storyChapters=Array.from(originals.story.querySelectorAll('section[id^="walk-"]'));
if(storyChapters.length!==8)throw Error('Expected all eight original field stops');
const fieldIntro=card();fieldIntro.innerHTML='<h2>Follow the excavations</h2><p>Use the field stops in order when the archaeological zone is accessible. Each stop provides a real observation, its historical interpretation and its evidence reference. Current access has not been verified.</p>';
screens.explore.append(fieldIntro);
const fieldHolder=document.createElement('div');screens.explore.append(fieldHolder);
const chooseField=pager(fieldHolder,storyChapters,'Field stop');
const onSite=document.createElement('details');onSite.className='review-collapsible';
onSite.innerHTML='<summary>What to look for and optional route directions</summary>';
onSite.append(originals.site);screens.explore.append(onSite);
const museum=document.createElement('details');museum.className='review-collapsible';
museum.innerHTML='<summary>Templo Mayor Museum — objects and archaeological contexts</summary>';
museum.append(originals.museum);screens.explore.append(museum);
const planning=card();planning.append(originals.visit);screens.plan.append(planning);
screens.plan.insertAdjacentHTML('beforeend','<p><a href="../../../walks/historic-center/">Continue to the connected Historic Center learning walk</a></p>');
// Keep evidence and sources complete and accessible without leaving the reading position.
const overlay=document.createElement('div');
overlay.id='review-overlay';
overlay.innerHTML='<div id="review-dialog" role="dialog" aria-modal="true" aria-label="Historical evidence and scholarly sources"><button type="button" id="review-close">← Return to reading</button><div><button type="button" data-research="evidence" aria-pressed="true">Claims & evidence</button><button type="button" data-research="sources" aria-pressed="false">Scholarly sources</button></div><div id="review-research-panels"></div></div>';
document.body.append(overlay);
const panelHost=document.getElementById('review-research-panels');
for(const name of ['evidence','sources']){
  originals[name].classList.add('research-pane');
  panelHost.append(originals[name]);
}
function showResearch(name){
  for(const type of ['evidence','sources'])originals[type].classList.toggle('active',type===name);
  overlay.querySelectorAll('[data-research]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.research===name)));
}
function openResearch(name){
  showResearch(name);overlay.classList.add('open');document.getElementById('review-close').focus();
}
const close=()=>{overlay.classList.remove('open');};
document.getElementById('review-close').onclick=close;
overlay.querySelectorAll('[data-research]').forEach(b=>b.onclick=()=>showResearch(b.dataset.research));
overlay.addEventListener('click',e=>{if(e.target===overlay)close()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&overlay.classList.contains('open'))close()});
for(const name of ['discover','explore']){
  const actions=document.createElement('div');actions.className='review-card';
  actions.innerHTML='<strong>Investigate the evidence</strong><p>Original research claims and source records are available as optional panels. Their editorial review statuses remain intact.</p><button type="button" class="review-deep-button" data-open-research="evidence">Claims & evidence</button><button type="button" class="review-deep-button" data-open-research="sources">Scholarly sources</button>';
  screens[name].append(actions);
}
main.querySelectorAll('[data-open-research]').forEach(b=>b.onclick=()=>openResearch(b.dataset.openResearch));
showResearch('evidence');
// Original walk deep-links still refer to dossier-topic-N and field-stop anchors.
const hash=decodeURIComponent(location.hash.slice(1));
let found=hist.findIndex(node=>node.id===hash||!!node.querySelector('#'+CSS.escape(hash||'__none__')));
if(found>=0){activate('discover',false);chooseHistory(found);}
else {
  found=storyChapters.findIndex(node=>node.id===hash);
  if(found>=0){activate('explore',false);chooseField(found);}
}
});
</script>
"""

def build():
    assert SOURCE.is_file(), f"Missing complete source POI: {SOURCE}"
    base = SOURCE.read_text(encoding="utf-8")
    for marker in ('id="story"', 'id="site"', 'id="dossier"', 'id="museum"',
                   'id="evidence"', 'id="sources"', 'id="visit"', 'id="claimlist"',
                   "History behind the excavated site", "Coyolxauhqui", "Tlaltecuhtli", SCRIPT):
        assert marker in base, f"Cannot publish review that has lost {marker}"
    assert base.count(SCRIPT) == 1
    assert len(base) > 35000, "Unexpected loss of preserved original POI content"
    page = base.replace("<title>Templo Mayor | Ciudad Viva Field Guide</title>",
                        "<title>Templo Mayor | Discover, Explore, Plan</title>", 1)
    assert page != base
    # This preview lives one directory deeper than the canonical POI.
    # Preserve the meaning of all original relative navigation and feedback links.
    page = re.sub(r'(?P<attr>(?:href|src))="(?P<parents>(?:\.\./)+)',
                  lambda m: m.group('attr') + '=\"../' + m.group('parents'), page)
    page = page.replace("</head>", STYLE + "</head>", 1)
    page = page.replace("</body>", JS + "</body>", 1)
    assert page.count('<script src="../../../feedback/annotate.js" defer></script>') == 1
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(page, encoding="utf-8")
    # Link to the review while leaving every original tab and historical paragraph intact.
    link='<p id="review-reader-link" class="notice"><b>Review the new reading layout:</b> <a href="review/">Open Discover / Explore / Plan, with passage-by-passage comments.</a> The complete original guide remains on this page.</p>'
    if 'id="review-reader-link"' not in base:
        base=base.replace('<div class="tabs"',link+'<div class="tabs"',1)
        SOURCE.write_text(base,encoding="utf-8")
    print(f"Built {DEST} from complete current POI ({len(page)} characters); preserved original {SOURCE}.")

if __name__ == "__main__":
    build()
