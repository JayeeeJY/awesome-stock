'use strict';
let researchData=null,documentEdit=null,documentDirty=false,documentKind='note';
const decisionKeys=['support','counter_case','invalidation','risk_limit','review_on'];
function referenceValue(ref){return ref?`${ref.id}@${ref.revision}`:'';}
function parseReference(value){if(!value)return null;const [id,revision]=value.split('@');return {id,revision:Number(revision)};}
function documentNavigation(name){
 const kind=name==='decisions'?'decision':'note';
 if(['research','decisions'].includes(name)&&kind!==documentKind){if(documentDirty&&!confirm('切换记录类型会清空尚未保存的内容，继续？'))return false;}
 return true;
}
function resetDocument(kind=documentKind){documentKind=kind;documentEdit=null;documentDirty=false;pending.delete('document');pending.delete('document-id');$('document-form').reset();$('document-heading').textContent=kind==='note'?'新建研究笔记':'新建Decision';$('document-version').textContent='尚未保存';}
function versionById(id,revision){return researchData.versions.find(d=>d.id===id&&d.revision===revision);}
function showHistory(record){
 $('document-history').replaceChildren();const title=element('h3',`${record.title} · ${record.symbol} · 版本 ${record.revision}`);$('document-history').append(title,element('p','保存时间：'+new Date(record.updated_at).toLocaleString()));
 for(const [key,label] of [['content',record.kind==='note'?'研究内容':'行动原因'],['support','支持证据'],['counter_case','反方证据'],['invalidation','失效条件'],['risk_limit','风险上限'],['review_on','复核日期']])if(record[key]){const box=element('div');box.append(element('h4',label),element('p',record[key]));$('document-history').append(box);}
 if(record.research_ref){const ref=versionById(record.research_ref.id,record.research_ref.revision);if(ref){const button=element('button',`查看研究依据：${ref.title} · 版本 ${ref.revision}`);button.className='secondary';button.onclick=()=>showHistory(ref);$('document-history').append(button);}}
 if(!$('document-dialog').open)$('document-dialog').showModal();
}
function fillResearchOptions(){
 const previous=$('document-research_ref').value;$('document-research_ref').replaceChildren();const none=element('option','不引用研究笔记');none.value='';$('document-research_ref').append(none);
 for(const d of researchData.versions){const latest=researchData.documents.find(x=>x.id===d.id),pinned=documentEdit?.research_ref;if(d.kind!=='note'||d.archived||(latest.archived&&!(pinned?.id===d.id&&pinned?.revision===d.revision)))continue;const o=element('option',`${d.symbol} · ${d.title} · v${d.revision}${latest.archived?'（已归档原引用）':''}`);o.value=referenceValue(d);$('document-research_ref').append(o);}
 if([...$('document-research_ref').options].some(o=>o.value===previous))$('document-research_ref').value=previous;
}
function editDocument(d){if(busy)return;if(documentDirty&&!confirm('放弃尚未保存内容并载入该记录？'))return;resetDocument(d.kind);documentEdit=d;$('document-title').value=d.title;$('document-symbol').value=d.symbol;$('document-content').value=d.content;for(const key of decisionKeys)$('document-'+key).value=d[key];fillResearchOptions();$('document-research_ref').value=referenceValue(d.research_ref);$('document-heading').textContent='编辑：'+d.title;$('document-version').textContent=`当前版本 ${d.revision}；保存会产生新版本，原引用保持不变。`;$('document-title').focus();}
async function loadDocuments(){
 researchData=await request('/api/v1/owner/documents');const kind=currentView==='decisions'?'decision':'note';if(kind!==documentKind)resetDocument(kind);
 $('research-heading').textContent=kind==='note'?'研究笔记':'Decision 投资判断';$('research-help').textContent=kind==='note'?'保存研究与证据；历史版本可以被Decision引用。':'记录你的判断依据与复核条件；成交可选引用，不产生交易指令。';
 $('decision-fields').hidden=kind==='note';$('references-section').hidden=kind==='note';for(const key of decisionKeys)$('document-'+key).required=kind==='decision';$('content-label').firstChild.textContent=kind==='note'?'研究内容':'现在为什么行动';
 renderDocuments();fillResearchOptions();renderReferences();
}
function renderDocuments(){
 $('document-list').replaceChildren();const docs=researchData.documents.filter(d=>d.kind===documentKind&&($('document-filter').value==='all'||!d.archived));if(!docs.length)$('document-list').append(element('p','暂无记录。从右侧创建第一条内容。'));
 for(const d of docs){const card=element('article');card.className='document-card';card.append(element('h3',d.title),element('p',`${d.symbol} · v${d.revision}${d.archived?' · 已归档':''}`));const actions=element('div');actions.className='row';if(!d.archived){const edit=element('button','编辑');edit.type='button';edit.className='secondary';edit.onclick=()=>editDocument(d);actions.append(edit);const archive=element('button','归档');archive.type='button';archive.className='secondary';archive.onclick=()=>{if(busy||!confirm('归档后不再新增引用，已有历史依据会保留。继续？'))return;run(async()=>{await request('/api/v1/owner/documents','DELETE',operation('archive-'+d.id,{id:d.id,revision:d.revision}));if(documentEdit?.id===d.id)resetDocument();await loadDocuments();message('已归档，历史版本和原有引用保留。');});};actions.append(archive);}card.append(actions);const history=element('details');history.append(element('summary','历史版本'));for(const v of researchData.versions.filter(x=>x.id===d.id).reverse()){const b=element('button',`查看 v${v.revision}${v.archived?' · 归档':''}`);b.type='button';b.className='secondary history-button';b.onclick=()=>showHistory(v);history.append(b);}card.append(history);$('document-list').append(card);}
}
function fillDecisionOptions(){
 const trade=researchData.trades.find(t=>t.id===$('reference-trade').value);const link=researchData.links.find(l=>l.trade_id===trade?.id);$('reference-decision').replaceChildren();const none=element('option','不关联 / 解除关联');none.value='';$('reference-decision').append(none);
 for(const d of researchData.versions){const current=researchData.documents.find(x=>x.id===d.id),pinned=link?.decision_id===d.id&&link?.decision_revision===d.revision;if(d.kind!=='decision'||d.archived||d.symbol!==trade?.symbol||(current.archived&&!pinned))continue;const o=element('option',`${d.title} · ${d.symbol} · v${d.revision}${current.archived?'（原有引用）':''}`);o.value=referenceValue(d);$('reference-decision').append(o);}
 if(link?.decision_id)$('reference-decision').value=`${link.decision_id}@${link.decision_revision}`;
}
function renderReferences(){
 const selected=$('reference-trade').value;$('reference-trade').replaceChildren();for(const t of researchData.trades){const option=element('option',`${t.symbol} · ${t.side==='buy'?'买入':'卖出'} ${t.quantity} · ${new Date(t.executed_at).toLocaleString()} · ${t.id.slice(0,8)}`);option.value=t.id;$('reference-trade').append(option);}if(researchData.trades.some(t=>t.id===selected))$('reference-trade').value=selected;fillDecisionOptions();
 $('reference-list').replaceChildren();if(!researchData.trades.length)$('reference-list').append(element('p','尚无成交。先在Portfolio / 账户与交易录入，再按需关联。'));
 for(const link of researchData.links.filter(l=>l.decision_id)){const d=versionById(link.decision_id,link.decision_revision),t=researchData.trades.find(t=>t.id===link.trade_id);if(!d||!t)continue;const p=element('p',`${t.symbol} · ${t.quantity} · ${t.id.slice(0,8)} → `),b=element('button',`${d.title} · v${d.revision}`);b.type='button';b.className='secondary';b.onclick=()=>showHistory(d);p.append(b);$('reference-list').append(p);}
}
$('document-form').oninput=()=>{documentDirty=true;};
$('document-form').onchange=()=>{documentDirty=true;};
$('document-filter').onchange=renderDocuments;
$('new-document').onclick=()=>{if(!documentDirty||confirm('清空未保存内容并新建？'))resetDocument();};
$('close-document').onclick=()=>$('document-dialog').close();
$('reference-trade').onchange=fillDecisionOptions;
$('document-form').onsubmit=e=>{e.preventDefault();run(async()=>{let id=documentEdit?.id||pending.get('document-id');if(!id){id=crypto.randomUUID();pending.set('document-id',id);}const values={id,revision:documentEdit?.revision||0,kind:documentKind,title:$('document-title').value,symbol:$('document-symbol').value,content:$('document-content').value,research_ref:documentKind==='decision'?parseReference($('document-research_ref').value):null};for(const key of decisionKeys)values[key]=documentKind==='decision'?$('document-'+key).value:'';const saved=await request('/api/v1/owner/documents','POST',operation('document',values));pending.delete('document-id');pending.delete('document');documentEdit=saved;documentDirty=false;$('document-heading').textContent='编辑：'+saved.title;$('document-version').textContent=`已保存版本 ${saved.revision}；历史引用保持不变。`;await loadDocuments();message('记录已保存；历史依据保留。');});};
$('reference-form').onsubmit=e=>{e.preventDefault();run(async()=>{const t=researchData.trades.find(t=>t.id===$('reference-trade').value);if(!t)throw Error('请先录入成交。');const link=researchData.links.find(l=>l.trade_id===t.id),ref=parseReference($('reference-decision').value);if(link&&link.decision_id===(ref?.id||null)&&link.decision_revision===(ref?.revision||null)){message('当前引用未改变。');return;}await request('/api/v1/owner/trade-reference','POST',operation('reference-'+t.id,{trade_id:t.id,trade_revision:t.revision,revision:link?.revision||0,decision_id:ref?.id||null,decision_revision:ref?.revision||null}));pending.delete('reference-'+t.id);await loadDocuments();message('成交引用已保存，交易金额没有改变。');});};
window.addEventListener('beforeunload',e=>{if(documentDirty){e.preventDefault();e.returnValue='';}});

function clearResearch(){resetDocument();researchData=null;$('document-list').replaceChildren();$('reference-list').replaceChildren();$('document-history').replaceChildren();}
