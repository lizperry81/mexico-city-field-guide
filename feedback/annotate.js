(()=>{'use strict';
const PAGE=(location.pathname.match(/\/poi\/([^/]+)\//)||location.pathname.match(/\/walks\/([^/]+)\//)||[])[1]||'guide';
const PREFIX='cdmx-reader-feedback-v2:';
const KEY=PREFIX+PAGE;
let notes=[];
try{
  let raw=localStorage.getItem(KEY);
  if(!raw && PAGE==='templo-mayor'){
    raw=localStorage.getItem('cdmx-templo-feedback-v1');
    if(raw) localStorage.setItem(KEY,raw);
  }
  notes=JSON.parse(raw||'[]');
  if(!Array.isArray(notes)) notes=[];
}catch(e){notes=[]}
function allNotes(){
  let result=[];
  try{
    for(let i=0;i<localStorage.length;i++){
      const key=localStorage.key(i);
      if(!key||!key.startsWith(PREFIX))continue;
      const rows=JSON.parse(localStorage.getItem(key)||'[]');
      if(Array.isArray(rows))result.push(...rows.map(n=>({...n,page:n.page||key.slice(PREFIX.length)})));
    }
  }catch(e){}
  if(!result.length)result=notes.map(n=>({...n,page:PAGE}));
  return result;
}
const css=document.createElement('style');css.textContent=`
#feedback-open{position:fixed;right:16px;bottom:22px;z-index:9999;border:0;border-radius:30px;background:#124f5c;color:#fff;padding:13px 19px;font:700 15px system-ui;box-shadow:0 4px 20px #0004}
.cdmx-comment-btn{margin:8px 0 14px;padding:6px 11px;background:#e4f1f0;color:#145c60;border:1px solid #99c8c3;border-radius:20px;font:600 12px system-ui;cursor:pointer}
#feedback-overlay{position:fixed;inset:0;background:#0008;z-index:10000;display:none;align-items:end;justify-content:center}
#feedback-overlay.open{display:flex}
#feedback-drawer{box-sizing:border-box;width:min(100%,680px);max-height:92dvh;overflow-y:auto;background:#fff;color:#172c35;border-radius:20px 20px 0 0;padding:22px;font:15px/1.5 system-ui;box-shadow:0 -6px 25px #0003}
#feedback-drawer h2{font:700 23px system-ui;margin:0 0 12px}#feedback-drawer label{display:block;font-weight:700;margin:12px 0 5px}
#feedback-drawer textarea{box-sizing:border-box;width:100%;min-height:120px;border:1px solid #91a6ac;border-radius:8px;padding:12px;font:16px system-ui}
#feedback-drawer button{padding:11px 13px;border-radius:8px;border:1px solid #9bb4b7;background:#f1f7f7;color:#124f5c;font:600 14px system-ui;margin:5px 5px 5px 0;cursor:pointer}
#feedback-drawer button.primary{background:#125e63;color:#fff;border-color:#125e63}
#feedback-context{background:#f2f5f5;padding:12px;border-radius:8px;max-height:115px;overflow:auto;font:14px Georgia,serif}
#feedback-saved{max-height:180px;overflow:auto}#feedback-saved article{border-top:1px solid #d4e0e2;padding:8px 0}#feedback-saved small{display:block;color:#53666d}
`;document.head.append(css);
const openBtn=document.createElement('button');openBtn.id='feedback-open';openBtn.textContent='Comments (0)';document.body.append(openBtn);
const overlay=document.createElement('div');overlay.id='feedback-overlay';overlay.innerHTML='<div id="feedback-drawer" role="dialog" aria-modal="true" aria-label="Comment on this guide"><div style="display:flex;justify-content:space-between;align-items:center"><h2>Comment on the guide</h2><button id="feedback-close" aria-label="Close comments">Close ×</button></div><p style="font-size:13px">Tap “Comment on this passage” to attach feedback to specific text. Your notes stay in this browser until shared; the report includes comments saved across the Historic Center guide pages.</p><label>Passage or section</label><div id="feedback-context">General feedback on the guide</div><label for="feedback-text">Your comment</label><textarea id="feedback-text" placeholder="What is missing, inaccurate, unclear, or worth expanding?"></textarea><div><button id="feedback-save" class="primary">Save comment</button><button id="feedback-share">Share all comments</button><button id="feedback-copy">Copy report</button></div><p id="feedback-message" role="status" style="font-size:13px"></p><h3 style="font:700 16px system-ui">Saved comments</h3><div id="feedback-saved"></div></div>';document.body.append(overlay);
const $=id=>document.getElementById(id);let context='General feedback on the Templo Mayor guide';
function report(){return 'Mexico City Field Guide — Reader feedback\nCreated: '+new Date().toISOString()+'\n\n'+allNotes().map((n,i)=>(i+1)+'. PAGE: '+n.page+'\nSECTION: '+n.section+'\nPASSAGE: '+n.context+'\nCOMMENT: '+n.comment+'\n').join('\n') }
function draw(){$('feedback-open').textContent='Comments ('+notes.length+')';$('feedback-saved').innerHTML='';notes.forEach((n,i)=>{const a=document.createElement('article');const strong=document.createElement('strong');strong.textContent=n.section;const small=document.createElement('small');small.textContent=n.context.slice(0,130);const p=document.createElement('p');p.textContent=n.comment;const del=document.createElement('button');del.textContent='Delete';del.onclick=()=>{if(confirm('Delete this comment?')){notes.splice(i,1);persist()}};a.append(strong,small,p,del);$('feedback-saved').append(a)})}
function persist(){try{localStorage.setItem(KEY,JSON.stringify(notes));$('feedback-message').textContent='Saved on this device.'}catch(e){$('feedback-message').textContent='Could not save locally; copy your report now.'}draw()}
function open(text,section){context=text||'General feedback on the Templo Mayor guide';$('feedback-context').textContent=context;$('feedback-text').value='';$('feedback-message').textContent='';overlay.classList.add('open');$('feedback-text').focus();overlay.dataset.section=section||'General';draw()}
openBtn.onclick=()=>open();$('feedback-close').onclick=()=>overlay.classList.remove('open');overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.classList.remove('open')});
$('feedback-save').onclick=()=>{const comment=$('feedback-text').value.trim();if(!comment){$('feedback-message').textContent='Please write a comment first.';return}notes.push({page:PAGE,section:overlay.dataset.section,context,comment,date:new Date().toISOString()});persist();$('feedback-text').value=''};
$('feedback-copy').onclick=async()=>{try{await navigator.clipboard.writeText(report());$('feedback-message').textContent='Report copied. Paste it into our ChatGPT conversation.'}catch(e){$('feedback-message').textContent='Copy unavailable; try Share all comments.'}};
$('feedback-share').onclick=async()=>{const text=report();if(!allNotes().length){$('feedback-message').textContent='Save at least one comment first.';return}if(navigator.share){try{await navigator.share({title:'Templo Mayor guide feedback',text});return}catch(e){if(e.name==='AbortError')return}}try{await navigator.clipboard.writeText(text);$('feedback-message').textContent='Report copied. Paste it into ChatGPT.'}catch(e){$('feedback-message').textContent='Select and copy the report using your browser.';const ta=$('feedback-text');ta.value=text;ta.select()}};
const root=document.querySelector('main')||document.body;
let section='Templo Mayor';
root.querySelectorAll('h1,h2,h3,h4,p').forEach((el,i)=>{if(el.closest('nav,header,footer,#feedback-overlay')||el.textContent.trim().length<55)return;if(el.matches('h1,h2,h3,h4'))section=el.textContent.trim();const btn=document.createElement('button');btn.type='button';btn.className='cdmx-comment-btn';btn.textContent='✎ Comment on this passage';const snippet=el.textContent.trim().slice(0,480);const heading=el.closest('section')?.querySelector('h2,h3')?.textContent?.trim()||section;btn.onclick=()=>open(snippet,heading);el.insertAdjacentElement('afterend',btn)});
draw();
})();