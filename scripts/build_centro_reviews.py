#!/usr/bin/env python3
"""Additive Discover / Explore / Plan phone readers for the three Centro POIs.

Every page is derived from its CURRENT built dossier, not a static preview or
the extracted ZIP. The original historical chapters, observations, source IDs,
and optional deep dives remain in the HTML. The canonical POI stays available.
Run after enable_reader_feedback.py, before test_centro_reviews.py.
"""
from pathlib import Path
import re

ROOT = Path("site/poi")
SLUGS = ("zocalo", "metropolitan-cathedral", "national-palace")
ORIGINAL_SCRIPT = '<script src="../../feedback/annotate.js" defer></script>'
REVIEW_SCRIPT = '<script src="../../../feedback/annotate.js" defer></script>'

STYLE = r"""
<style id="centro-review-styles">
.review-intro{border:1px solid var(--line);border-radius:15px;background:#fff;padding:18px;margin:24px 0}
.review-intro h2{margin:0 0 10px}.review-intro p{margin:0}
.review-switch{position:sticky;top:0;z-index:20;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;background:#f5f8f9;padding:10px 0}
.review-switch button{background:#fff;border:1px solid #b4cdd0;border-radius:11px;padding:12px 3px;color:#183d45;font:700 15px system-ui;cursor:pointer}
.review-switch button[aria-selected="true"]{background:#126c69;color:#fff}
.review-switch small{display:block;font:12px system-ui;font-weight:400;margin-top:3px}
.review-screen{display:none}.review-screen.active{display:block}
.review-card{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;margin:17px 0}
.review-card .chapter{padding:10px 0;border:0;scroll-margin-top:120px}
.review-card .narrative{font-size:18px}
.review-count{font:800 12px system-ui;letter-spacing:.06em;color:#126c69;text-transform:uppercase}
.review-pager{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0 25px}
.review-pager button{border:0;border-radius:9px;padding:12px 15px;background:#126c69;color:#fff;font:700 14px system-ui;cursor:pointer}
.review-pager button:disabled{opacity:.35;cursor:not-allowed}
.review-chapter-select{max-width:100%;width:100%;border:1px solid #9abdc0;background:white;padding:12px;border-radius:9px;font:15px system-ui;margin:7px 0}
.review-switch button:focus-visible,.review-pager button:focus-visible,.review-chapter-select:focus-visible{outline:3px solid #126c69;outline-offset:3px}
.review-screen .observations{margin:0;background:transparent;padding:0}
.review-screen .observations li{display:block;padding:0;border:0}
.review-screen .observations li span{display:none}
.review-screen .observations li p{font:18px/1.65 Georgia,serif}
.review-screen .next{border:0}
.review-nav-footer{font-size:14px;color:#536875;margin:18px 0}
@media(max-width:750px){.review-card{padding:16px}.review-switch button{font-size:14px}.review-switch small{font-size:11px}}
</style>
"""

BEHAVIOR = r"""
<script id="centro-review-script">
document.addEventListener('DOMContentLoaded',function(){
'use strict';
const main=document.querySelector('main');
const observations=main&&main.querySelector(':scope > .observations');
const layout=main&&main.querySelector(':scope > .layout');
const continuation=main&&main.querySelector(':scope > .next');
if(!main||!observations||!layout||!continuation)throw Error('Original Centro historical dossier missing');
const archive=layout.querySelector('article.chapters');
if(!archive)throw Error('Preserved historical chapters missing');
const chapters=Array.from(archive.querySelectorAll(':scope > section.chapter'));
const stops=Array.from(observations.querySelectorAll('ol > li'));
if(chapters.length<5||stops.length<2)throw Error('Historical material unexpectedly incomplete');
const intro=document.createElement('section');
intro.className='review-intro';
intro.innerHTML='<p class="eyebrow">RESEARCH-STAGE · HISTORICAL FIELD GUIDE</p><h2>Preserved historical dossier and field observations</h2><p><b>Discover</b> currently contains the archived research chapters, not a newly approved long-form narrative. <b>Explore</b> presents separate on-site observations. <b>Plan</b> covers visit planning and nearby places. Source identifiers and optional deep dives remain available for editorial review.</p>';
observations.before(intro);
const bar=document.createElement('nav');
bar.className='review-switch';bar.setAttribute('aria-label','Choose guide mode');
const modes=[['discover','Discover','Read the history'],['explore','Explore','Use on site'],['plan','Plan','Arrange a visit']];
const screens={};
for(const mode of modes){
  const b=document.createElement('button');b.type='button';b.dataset.mode=mode[0];
  b.setAttribute('aria-selected',String(mode[0]==='discover'));
  b.setAttribute('aria-controls','review-'+mode[0]);
  b.textContent=mode[1];
  const small=document.createElement('small');small.textContent=mode[2];b.append(small);bar.append(b);
}
intro.after(bar);
let previous=bar;
for(const mode of modes){
  const section=document.createElement('section');section.id='review-'+mode[0];
  section.className='review-screen'+(mode[0]==='discover'?' active':'');
  section.setAttribute('aria-label',mode[1]);previous.after(section);previous=section;screens[mode[0]]=section;
}
function box(){const node=document.createElement('div');node.className='review-card';return node}
function label(text){const p=document.createElement('p');p.className='review-count';p.textContent=text;return p}
function activate(mode,scroll){
  for(const key of Object.keys(screens))screens[key].classList.toggle('active',key===mode);
  bar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.mode===mode)));
  if(scroll)bar.scrollIntoView({block:'start',behavior:'auto'});
}
bar.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>activate(b.dataset.mode,true)));
function reader(host,items,kind){
  const cards=items.map((item,i)=>{
    const frame=box();frame.append(label(kind+' '+(i+1)+' of '+items.length),item);
    host.append(frame);return frame;
  });
  const nav=document.createElement('div');nav.className='review-pager';
  const prev=document.createElement('button');prev.type='button';prev.textContent='← Previous';
  const next=document.createElement('button');next.type='button';next.textContent='Next →';
  nav.append(prev,next);host.append(nav);
  let selectMenu=null;
  if(kind==='Chapter'){
    selectMenu=document.createElement('select');selectMenu.className='review-chapter-select';
    selectMenu.setAttribute('aria-label','Jump to a historical chapter');
    items.forEach((item,i)=>{
      const opt=document.createElement('option');opt.value=String(i);
      opt.textContent=(i+1)+'. '+(item.querySelector('h2')?.textContent||'Historical chapter');
      selectMenu.append(opt);
    });host.insertBefore(selectMenu,cards[0]);
  }
  let active=0;
  function select(i,scroll){
    active=Math.min(items.length-1,Math.max(0,i));
    cards.forEach((frame,j)=>frame.hidden=j!==active);
    prev.disabled=active===0;next.disabled=active===items.length-1;
    if(selectMenu)selectMenu.value=String(active);
    // Back from another connected POI returns to this exact chapter/observation.
    if(scroll && items[active].id)window.history.replaceState(null,'','#'+encodeURIComponent(items[active].id));
    if(scroll)bar.scrollIntoView({block:'start',behavior:'auto'});
  }
  prev.onclick=()=>select(active-1,true);next.onclick=()=>select(active+1,true);
  if(selectMenu)selectMenu.onchange=()=>select(Number(selectMenu.value),true);
  select(0,false);return select;
}
const discoverIntro=box();
discoverIntro.innerHTML='<h2>Read the historical chapters</h2><p>Follow the events and changes in sequence. Original source identifiers and research cautions remain next to their claims; optional explanations expand in place.</p>';
screens.discover.append(discoverIntro);
const historicalHost=document.createElement('div');screens.discover.append(historicalHost);
const chooseChapter=reader(historicalHost,chapters,'Chapter');
const exploreIntro=box();
exploreIntro.innerHTML='<h2>Look closely on site</h2><p>These observations are preserved from the original guide. Follow them at your own pace. They are not live walking directions; visibility and access must be checked at the site.</p>';
screens.explore.append(exploreIntro);
const obsHeading=observations.querySelector('h2');
const obsSpot=observations.querySelector('p');
if(obsSpot)exploreIntro.append(obsSpot);
if(obsHeading)exploreIntro.querySelector('h2').replaceWith(obsHeading);
const stopHost=document.createElement('div');screens.explore.append(stopHost);
const stopSections=stops.map((li,i)=>{
  const section=document.createElement('section');section.id='review-observation-'+(i+1);
  section.className='observations';
  const ol=document.createElement('ol');ol.append(li);section.append(ol);
  return section;
});
const chooseStop=reader(stopHost,stopSections,'Observation');
const plan=box();plan.innerHTML='<h2>Plan your visit</h2><p>Check official hours, admission, accessibility and access conditions before traveling. This research-stage page does not claim live availability or operating hours.</p>';
screens.plan.append(plan);
continuation.classList.remove('chapter');continuation.classList.add('next');
plan.append(continuation);
const walk=document.createElement('p');
const walkLink=document.createElement('a');walkLink.href='../../../walks/historic-center/';
walkLink.textContent='Follow the connected Historic Center learning walk';
walk.append(walkLink);plan.append(walk);
const library=document.createElement('p');
const libraryLink=document.createElement('a');libraryLink.href='../../../research-library/';
libraryLink.textContent='Review the scholarly evidence library';
library.append(libraryLink);plan.append(library);
layout.remove();observations.remove();
const closing=document.createElement('p');closing.className='review-nav-footer';
closing.textContent='This is an alternative reading layout. All historical text, source IDs and observations come from the preserved guide, which is still available separately.';
screens.plan.append(closing);
// The reader must also handle links opened after initial load (hashchange).
// Cross-site reading links resolve to exact historical chapters, not the top.
function navigateHash(){
  let hash;
  try{hash=decodeURIComponent(location.hash.slice(1))}
  catch{hash=location.hash.slice(1)}
  if(!hash)return;
  const historicalIndex=chapters.findIndex(c=>c.id===hash);
  if(historicalIndex>=0){activate('discover',false);chooseChapter(historicalIndex,false);return}
  const observationIndex=stopSections.findIndex(c=>c.id===hash);
  if(observationIndex>=0){activate('explore',false);chooseStop(observationIndex,false)}
}
navigateHash();
window.addEventListener('hashchange',navigateHash);
});
</script>
"""

def generate(slug):
    source=ROOT/slug/"index.html"
    dest=ROOT/slug/"review/index.html"
    base=source.read_text(encoding="utf-8")
    assert len(base)>9000, f"Truncated source POI: {slug}"
    assert base.count(ORIGINAL_SCRIPT)==1, f"Missing annotation: {slug}"
    for marker in ('class="observations"', 'class="layout"', 'class="chapters"', 'class="chapter next"', 'research-library/'):
        assert marker in base, f"Missing original preserved material: {slug}: {marker}"
    review=re.sub(r'(?P<attr>(?:href|src))="(?P<parents>(?:\.\./)+)',
                  lambda m: m.group('attr')+'="../'+m.group('parents'),base)
    assert review.count(REVIEW_SCRIPT)==1, f"Feedback path lost: {slug}"
    review=review.replace("</head>",STYLE+"</head>",1)
    review=review.replace("</body>",BEHAVIOR+"</body>",1)
    review=review.replace(" | Ciudad Viva Field Guide</title>",
                          " | Discover, Explore, Plan — Ciudad Viva</title>",1)
    assert len(review)>len(base)+4500, f"Unexpected loss of reader content: {slug}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(review,encoding="utf-8")
    canonical_link=('<p id="centro-reader-link" class="status"><strong>Try the clearer phone layout:</strong> '
                    '<a href="review/">Discover / Explore / Plan, with passage-level comments</a>. '
                    'The full original guide stays available here.</p>')
    if 'id="centro-reader-link"' not in base:
        base=base.replace('<section class="observations"',canonical_link+'<section class="observations"',1)
        assert 'id="centro-reader-link"' in base, slug
        source.write_text(base,encoding="utf-8")
    print(f"Built {dest} ({len(review)} characters), retaining original {source}")

if __name__=="__main__":
    for slug in SLUGS:
        generate(slug)
