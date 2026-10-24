// Explicit per-request retrieval: no persistent server corpus or generated answers.
let evidenceView={selected:new Set(),query:'',hits:[],snapshot:[],busy:false,error:'',searched:false,request:0};
function evidenceCurrent(){return evidenceView.snapshot.every(s=>state.entries.some(e=>e.id===s.id&&e.text===s.text));}
function evidencePage(){
 const v=evidenceView;
 if(!evidenceCurrent()){v.hits=[];v.searched=false;v.error='材料已修改或删除，请重新检索。';}
 const entries=state.entries.filter(e=>typeof e.text==='string'&&e.text.trim());
 return heading('RESEARCH EVIDENCE','历史证据检索','从已归档材料中找回相关原文，再判断它是否支持你的研究。')+
 `<div class="notice">试验版 · 词法检索，不是 AI 问答。点击检索会把勾选正文发送给当前连接的本机服务，在内存中按次建立索引，结束后释放；不调用外部模型、不保存服务端材料。</div>
 <section class="card"><h2>1. 选择本次材料范围</h2><p>每次最多 20 条、合计 10 万字。同一材料的不同归档观点可能重复，请按需勾选。</p>
 ${entries.length?entries.map(e=>`<label class="evidence-choice"><input type="checkbox" data-evidence-id="${esc(e.id)}" ${v.selected.has(e.id)?'checked':''}> <span>${esc(e.title||'未命名材料')} · ${esc(frame(e.node)?.name||'未归类')}</span></label>`).join(''):empty('还没有已归档材料','先到材料研读中导入正文、确认观点并归档。',action('去材料研读','goto','data-area="reader"'))}
 <h2>2. 输入你想找的证据</h2><label for="evidence-query">研究问题或关键词</label><input id="evidence-query" maxlength="500" value="${esc(v.query)}" placeholder="例如：白银需求增长有哪些反向条件？">
 <div class="actions"><button class="primary" id="evidence-search" ${!online||v.busy?'disabled':''}>${v.busy?'正在检索…':'发送所选材料并检索'}</button><button class="button" id="evidence-clear">清空本次范围与结果</button></div>
 ${!online?'<p class="notice warn">请启动本地服务后使用。独立 HTML 离线文件不提供检索。</p>':''}<p id="evidence-error" role="status">${esc(v.error)}</p></section>
 <section class="card" id="evidence-results"><h2>3. 核对候选原文</h2><p>返回最多 5 个相关片段。顺序只代表词汇匹配；可能遗漏反证，也可能完全不足以回答问题。</p>
 ${v.hits.map((hit,i)=>{const source=v.snapshot.find(s=>s.id===hit.source);return `<article class="entry"><h3>${esc(source?.title||'材料')} · 原文片段 ${i+1}</h3><blockquote>${esc(hit.text)}</blockquote><small>词法匹配 · 原文字符 ${hit.start+1}–${hit.end}</small><div class="actions"><button class="button" data-evidence-open="${i}">回到原文核对</button></div></article>`;}).join('')||empty(v.searched?'没有词汇匹配结果':'尚未检索',v.searched?'这不代表材料没有相关观点。可改用关键词或直接阅读原文。':'先选择材料并输入问题。')}</section>`;
}
function bindEvidencePage(){
 if(route!=='retrieval')return;
 $$('[data-evidence-id]').forEach(box=>box.onchange=()=>{box.checked?evidenceView.selected.add(box.dataset.evidenceId):evidenceView.selected.delete(box.dataset.evidenceId);evidenceView.request++;evidenceView.busy=false;evidenceView.hits=[];evidenceView.searched=false;evidenceView.snapshot=[];render();});
 $('#evidence-query').oninput=e=>{evidenceView.query=e.target.value;evidenceView.request++;evidenceView.busy=false;evidenceView.hits=[];evidenceView.searched=false;$('#evidence-results').innerHTML='<p>问题已变化，请重新检索。</p>';const button=$('#evidence-search');button.disabled=!online;button.textContent='发送所选材料并检索';};
 $('#evidence-search').onclick=searchEvidence;
 $('#evidence-clear').onclick=()=>{evidenceView={selected:new Set(),query:'',hits:[],snapshot:[],busy:false,error:'',searched:false,request:evidenceView.request+1};render();};
 $$('[data-evidence-open]').forEach(button=>button.onclick=()=>openEvidence(Number(button.dataset.evidenceOpen)));
}
async function searchEvidence(){
 const v=evidenceView;
 v.snapshot=state.entries.filter(e=>v.selected.has(e.id)).map(e=>({id:e.id,text:e.text,title:e.title}));
 v.hits=[];v.error='';v.searched=false;
 if(!v.query.trim()||!v.snapshot.length){v.error='请勾选至少一条材料，并输入检索问题。';return render();}
 if(v.snapshot.length>20||v.snapshot.reduce((n,s)=>n+Array.from(s.text).length,0)>100000){v.error='请选择最多 20 条、合计不超过 10 万字的材料。';return render();}
 const request=++v.request;
 v.busy=true;render();
 try{
  const result=await api('/api/retrieve',{query:v.query,materials:v.snapshot.map(({id,text})=>({id,text}))});
  if(evidenceView!==v||request!==v.request)return;
  if(!evidenceCurrent())throw Error('检索期间材料已变化，请重新检索。');
  v.hits=result.hits;v.searched=true;
 }catch(error){if(evidenceView===v&&request===v.request)v.error=error.message;}
 finally{if(evidenceView===v&&request===v.request){v.busy=false;if(route==='retrieval')render();}}
}
function openEvidence(i){
 const hit=evidenceView.hits[i],source=hit&&evidenceView.snapshot.find(s=>s.id===hit.source);
 const current=source&&state.entries.find(e=>e.id===source.id);
 if(!source||!current||current.text!==source.text){evidenceView.hits=[];evidenceView.error='原材料已变化，旧结果不能继续引用。';return render();}
 const chars=Array.from(current.text);
 if(chars.slice(hit.start,hit.end).join('')!==hit.text)return toast('引用位置校验失败，请重新检索');
 dialog(current.title,`<p>高亮为本次检索片段；请结合前后文核对，不能据此自动确认观点。</p><div class="evidence-source">${esc(chars.slice(0,hit.start).join(''))}<mark id="evidence-highlight">${esc(hit.text)}</mark>${esc(chars.slice(hit.end).join(''))}</div>`);
 $('#evidence-highlight').scrollIntoView({block:'center'});
}
