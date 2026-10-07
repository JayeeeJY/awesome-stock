'use strict';
const $=id=>document.getElementById(id);
let viewData=null;
let committedPath=location.pathname,tradeDirty=false,accountDirty=false;
let currentView=['/cockpit','/portfolio','/research','/decisions','/evolve','/plans','/cash','/screening','/planning','/trends','/academy','/settings'].includes(location.pathname)?location.pathname.slice(1):'ledger';
let initialized=false,busy=false,editing=null,ledger=null,pending=new Map();
function message(text,isError=false){const node=$('message');node.classList.toggle('error',isError);node.setAttribute('role',isError?'alert':'status');node.setAttribute('aria-live',isError?'assertive':'polite');node.textContent=text;}
function csrf(){const c=document.cookie.split('; ').find(v=>v.startsWith('__Host-awesome_owner_csrf='));return c?decodeURIComponent(c.split('=').slice(1).join('=')):'';}
async function request(url,method='GET',body,retry=true){
 const response=await fetch(url,{method,credentials:'same-origin',headers:method==='GET'?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf(),'X-Requested-With':'awesome-owner'},body:body===undefined?undefined:JSON.stringify(body)});const data=await response.json();
 if(response.status===401&&data.error?.code!=='invalid_credentials'&&retry&&!url.includes('/auth/')&&!url.endsWith('/password')){try{await request('/api/v1/auth/refresh','POST',{},false);return request(url,method,body,false);}catch{authView();throw Error('会话已失效，请重新登录；输入仍保留。');}}
 if(!response.ok){if(response.status===401&&data.error?.code!=='invalid_credentials'&&!url.endsWith('/login')&&!url.endsWith('/password'))authView();throw Error(data.error?.message||'操作失败，请重试。');}return data;
}
function authView(){if($('workspace-navigation')?.open)$('workspace-navigation').close();if($('ai-dialog')?.open)$('ai-dialog').close();if($('plan-dialog')?.open)$('plan-dialog').close(); if($('review-dialog')?.open)$('review-dialog').close();if($('document-dialog')?.open)$('document-dialog').close();document.body.classList.remove('signed-in'); $('auth').hidden=false;$('workspace').hidden=true;$('auth-title').textContent=initialized?'登录本地账号':'创建本地账号';$('auth-help').textContent=initialized?'使用你创建的固定账号登录；没有默认口令。':'这是空账本。创建唯一的本地账号后，即可建立自己的资金账户。用户名用英文字母、数字及 . _ @ + -，口令12–128字符。';$('auth-submit').textContent=initialized?'登录':'创建账号';$('confirm-label').hidden=initialized;$('confirm-password').required=!initialized;$('password').autocomplete=initialized?'current-password':'new-password';}
async function run(fn){if(busy)return;busy=true;const focused=document.activeElement;document.querySelectorAll('button,input,select,textarea').forEach(x=>x.disabled=true);try{await fn();}catch(e){message(e.message,true);}finally{busy=false;document.querySelectorAll('button,input,select,textarea').forEach(x=>x.disabled=false);$('trade-account').disabled=!!editing;if(typeof lockReviewControls==='function')lockReviewControls();if(typeof lockPlanControls==='function')lockPlanControls();if(typeof lockTransferControls==='function')lockTransferControls();if(typeof lockCashControls==='function')lockCashControls();if(document.activeElement===document.body&&focused?.isConnected&&!focused.disabled&&focused.getClientRects().length)focused.focus({preventScroll:true});}}
function operation(key,values){const fingerprint=JSON.stringify(values),old=pending.get(key);if(old?.fingerprint===fingerprint)return old.body;const body={...values,operation_id:crypto.randomUUID()};pending.set(key,{fingerprint,body});return body;}
function element(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function localTime(value){const d=value?new Date(value):new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,19);}
function resetTrade(){tradeDirty=false;editing=null;pending.delete('trade');$('trade-form').reset();$('executed-at').value=localTime();$('trade-account').disabled=false;$('trade-heading').textContent='录入交易';$('edit-status').textContent='新记录按成交时间进入账本。同一时间按录入顺序处理。';}
function editTrade(t){if(busy)return;if(tradeDirty&&!confirm('放弃当前编辑内容并载入这笔交易？'))return;editing=t;pending.delete('trade');$('trade-account').value=t.account_id;$('trade-account').disabled=true;for(const [id,k] of [['symbol','symbol'],['side','side'],['quantity','quantity'],['price','price'],['fee','fee']])$(id).value=t[k];$('executed-at').value=localTime(t.executed_at);$('trade-heading').textContent='更正交易';$('edit-status').textContent=`当前版本 ${t.revision}；保存时校验全部后续交易。`;$('trade-form').scrollIntoView({behavior:'smooth',block:'center'});}
async function reload(){
 ledger=await request('/api/v1/owner/ledger');$('first-account').hidden=ledger.accounts.length>0;const selected=$('trade-account').value;$('trade-account').replaceChildren();$('accounts').replaceChildren();$('trades').replaceChildren();
 if(!ledger.accounts.length){$('accounts').append(element('p','还没有资金账户。先建立账户和期初现金，再录入交易。'));}
 for(const a of ledger.accounts){const option=element('option',`${a.name} · ${a.currency}`);option.value=a.id;$('trade-account').append(option);const card=element('div');card.className='account-card';card.append(element('h3',`${a.name} · ${a.currency}`));const metrics=element('div');metrics.className='metrics';for(const [label,value] of [['账本现金',a.cash],['期初现金',a.opening_cash],['市值','— / 缺少行情']]){const item=element('div',label);item.append(element('strong',value));metrics.append(item);}card.append(metrics);
 const wrap=element('div');wrap.className='table-wrap';const table=element('table'),head=element('tr');for(const h of ['标的','持有数量','剩余成本','已实现损益','未实现损益'])head.append(element('th',h));const th=element('thead');th.append(head);table.append(th);const tb=element('tbody');for(const h of a.holdings){const tr=element('tr');for(const v of [h.symbol,h.quantity,h.open_cost,h.realized_pnl,'— / 缺少行情'])tr.append(element('td',v));tb.append(tr);}table.append(tb);wrap.append(table);card.append(wrap);$('accounts').append(card);
 for(const t of a.trades){const tr=element('tr');tr.dataset.tradeId=t.id;for(const v of [`${a.name} / ${a.currency}`,new Date(t.executed_at).toLocaleString(),t.symbol,t.side==='buy'?'买入':'卖出',t.quantity,t.price,t.fee,String(t.revision)])tr.append(element('td',v));const actions=element('td');const edit=element('button','更正');edit.className='secondary';edit.onclick=()=>editTrade(t);const remove=element('button','删除');remove.className='danger';remove.onclick=()=>{if(busy||!confirm('删除该交易并重算后续账目？如产生超卖或透支，将拒绝删除。'))return;run(async()=>{await request('/api/v1/owner/trades','DELETE',operation(`delete-${t.id}`,{id:t.id,revision:t.revision}));pending.delete(`delete-${t.id}`);if(editing?.id===t.id)resetTrade();await reload();message('交易已删除，账本已重算。');});};actions.append(edit,remove);tr.append(actions);$('trades').append(tr);}}
 if([...$('trade-account').options].some(o=>o.value===selected))$('trade-account').value=selected;
 if(['cockpit','portfolio'].includes(currentView))await loadViews();
 if(currentView==='evolve')await loadEvolve();
 if(currentView==='plans')await loadPlans();
 if(currentView==='academy')await loadAcademy();
 if(currentView==='settings')await loadSettings();
 if(currentView==='cash')await loadCash();
 if(typeof syncTransferAccounts==='function')syncTransferAccounts();
 if(typeof loadBusiness==='function')await loadBusiness();
 // Commit a shared research form only after all preceding reads succeed.
 if(['research','decisions'].includes(currentView))await loadDocuments();
 showView();
}
$('auth-form').onsubmit=e=>{e.preventDefault();run(async()=>{const username=$('username').value,password=$('password').value;if(!initialized){if(password!==$('confirm-password').value)throw Error('两次口令不一致。');await request('/api/v1/owner/setup','POST',{username,password});initialized=true;authView();}await request('/api/v1/auth/login','POST',{username,password});$('password').value='';$('confirm-password').value='';$('auth').hidden=true;$('workspace').hidden=false;await reload();message('已登录本地账本。');});};
$('account-form').onsubmit=e=>{e.preventDefault();run(async()=>{const values={name:$('account-name').value,currency:$('currency').value,opening_cash:$('opening-cash').value};const key=JSON.stringify(values);let old=pending.get('account-id');if(!old||old.key!==key){old={key,id:crypto.randomUUID()};pending.set('account-id',old);}await request('/api/v1/owner/accounts','POST',operation('account',{...values,id:old.id}));pending.delete('account');pending.delete('account-id');$('account-form').reset();accountDirty=false;await reload();message('账户已建立。期初现金已保存。');});};
$('trade-form').onsubmit=e=>{e.preventDefault();run(async()=>{const fields={account_id:$('trade-account').value,symbol:$('symbol').value,side:$('side').value,quantity:$('quantity').value,price:$('price').value,fee:$('fee').value,executed_at:editing&&$('executed-at').value===localTime(editing.executed_at)?editing.executed_at:new Date($('executed-at').value).toISOString(),revision:editing?.revision||0};let identity=editing?.id||pending.get('trade-id');if(!identity){identity=crypto.randomUUID();pending.set('trade-id',identity);}await request('/api/v1/owner/trades','POST',operation('trade',{...fields,id:identity}));pending.delete('trade-id');resetTrade();await reload();message('交易已保存，现金与持仓已重算。');});};
$('new-trade').onclick=()=>{if(confirm('清空当前交易表单？尚未保存的内容将丢弃。')){resetTrade();pending.delete('trade-id');}};
$('refresh').onclick=()=>run(async()=>{await reload();message('账本已刷新。编辑区输入保留，更正前请载入最新版本。');});
function createBackup(){return run(async()=>{const b=await request('/api/v1/owner/backup','POST',{});$('backup-result').textContent=`已备份：${b.name}。包含口令哈希与账本，请妥善保管。`;$('settings-backup-result').textContent=`本次已创建备份：${b.name}。保存在上方备份目录。`;message('本地备份已完成。');});}
$('backup').onclick=createBackup;
$('logout').onclick=()=>run(async()=>{await request('/api/v1/auth/logout','POST',{});authView();$('accounts').replaceChildren();$('trades').replaceChildren();resetTrade();if(typeof clearResearch==='function')clearResearch();if(typeof clearEvolve==='function')clearEvolve();if(typeof clearPlans==='function')clearPlans();if(typeof clearInfo==='function')clearInfo();if(typeof clearTransfer==='function')clearTransfer();if(typeof clearCash==='function')clearCash();if(typeof clearBusiness==='function')clearBusiness();pending.clear();message('已退出，数据仍保存在本机。');});
$('password-form').onsubmit=e=>{e.preventDefault();run(async()=>{if($('new-password').value!==$('repeat-password').value)throw Error('两次新口令不一致。');await request('/api/v1/owner/password','POST',{current_password:$('old-password').value,new_password:$('new-password').value});$('password-form').reset();if(typeof clearBusiness==='function')clearBusiness();authView();message('口令已修改，请重新登录。');});};
window.addEventListener('DOMContentLoaded',()=>{resetTrade();run(async()=>{const s=await request('/api/v1/owner/status');initialized=s.initialized;if(s.authenticated){$('workspace').hidden=false;await reload();}else authView();});});

function showView(){
 document.body.classList.toggle('signed-in',!$('workspace').hidden);
 $('research-panel').hidden=!['research','decisions'].includes(currentView);
 for(const name of ['cockpit','portfolio','ledger','evolve','plans','cash','screening','planning','trends','academy','settings'])$(name+'-panel').hidden=name!==currentView;
 const title={screening:'Research · 候选与证据',planning:'Plan · 配置与交易试算',trends:'Evolve · 规则与周期趋势',cockpit:'Cockpit · 账本概览',portfolio:'Portfolio · 我的持仓',ledger:'本地账本',research:'Research · 研究笔记',decisions:'Plan · Decision投资判断',evolve:'Evolve · 决策复盘',plans:'Plan · 我的计划',academy:'Academy · 投资知识',settings:'Settings · 本地设置',cash:'Portfolio · 入金与出金'}[currentView];
 $('page-title').textContent=title;document.title=title+' · Awesome Stock';
 document.querySelectorAll('[data-view]').forEach(a=>{if(a.dataset.view===currentView){a.setAttribute('aria-current','page');const group=a.closest('details');if(group)group.open=true;if(innerWidth<1000){const nav=$('view-nav');nav.scrollLeft+=(group||a).getBoundingClientRect().left-nav.getBoundingClientRect().left-10;}}else a.removeAttribute('aria-current');});
 if(typeof updateOwnerShell==='function')updateOwnerShell();
}
function table(headers,rows){const t=element('table'),head=element('thead'),tr=element('tr');headers.forEach(h=>tr.append(element('th',h)));head.append(tr);t.append(head);const body=element('tbody');rows.forEach(row=>{const r=element('tr');row.forEach(value=>r.append(element('td',value)));body.append(r);});t.append(body);return t;}
function renderPositions(){
 $('positions').replaceChildren();const valued=typeof business!=='undefined'&&business?business.accounts.flatMap(a=>a.positions.map(p=>({...p,account_id:a.id,account_name:a.name,currency:a.currency}))):viewData.positions;const rows=valued.filter(p=>!$('portfolio-account').value||p.account_id===$('portfolio-account').value);
 if(!rows.length){$('positions').append(element('p','当前范围没有未平仓持仓。'));return;}
 $('positions').append(table(['账户','币种','标的','数量','剩余成本','已实现损益','市值 / 未实现损益'],rows.map(p=>[p.account_name,p.currency,p.symbol,p.quantity,p.open_cost,p.realized_pnl,p.market_value==null?'— / 缺少行情或价格陈旧':p.market_value+' / '+p.unrealized_pnl])));
}
async function loadViews(){
 viewData=await request('/api/v1/owner/views');$('overview').replaceChildren();
 for(const [label,value] of [['资金账户',viewData.account_count],['交易记录',viewData.trade_count],['账户持仓',viewData.open_position_count]]){const item=element('div',label);item.append(element('strong',String(value)));$('overview').append(item);}
 $('last-trade').textContent=viewData.last_executed_at?'最近成交时间：'+new Date(viewData.last_executed_at).toLocaleString():'尚无成交记录。';
 $('data-gaps').replaceChildren();for(const gap of viewData.data_gaps){const p=element('p',gap.text+' '),a=element('a','查看');a.href=gap.href;a.onclick=e=>{e.preventDefault();navigate(gap.href.slice(1));};p.append(a);$('data-gaps').append(p);}if(!viewData.data_gaps.length)$('data-gaps').append(element('p','当前规则未发现账本数据缺口；这不代表实时行情或投资风险检查已完成。'));
 $('recent-trades').replaceChildren();if(viewData.recent_trades.length)$('recent-trades').append(table(['成交时间','账户','币种','标的','方向','数量','价格'],viewData.recent_trades.map(t=>[new Date(t.executed_at).toLocaleString(),t.account_name,t.currency,t.symbol,t.side==='buy'?'买入':'卖出',t.quantity,t.price])));else $('recent-trades').append(element('p','还没有交易记录。'));
 $('currency-balances').replaceChildren();if(!viewData.currency_balances.length)$('currency-balances').append(element('p','尚无账户余额。请先建立资金账户。'));for(const b of viewData.currency_balances){const card=element('div');card.className='account-card';card.append(element('h3',b.currency));const m=element('div');m.className='metrics';for(const [label,value] of [['账本现金',b.cash],['剩余成本',b.open_cost],['已实现损益',b.realized_pnl]]){const i=element('div',label);i.append(element('strong',value));m.append(i);}card.append(m);$('currency-balances').append(card);}
 const selected=$('portfolio-account').value;$('portfolio-account').replaceChildren();const all=element('option','全部账户');all.value='';$('portfolio-account').append(all);for(const a of viewData.accounts){const o=element('option',a.name+' · '+a.currency);o.value=a.id;$('portfolio-account').append(o);}if([...$('portfolio-account').options].some(o=>o.value===selected))$('portfolio-account').value=selected;renderPositions();
}
function navigate(name,push=true){
 const restoreAddress=()=>{if(!push)history.replaceState({},'',committedPath);};
 if(busy){restoreAddress();return;}
 if(typeof documentNavigation==='function'&&!documentNavigation(name)){restoreAddress();return;}
 run(async()=>{const previous=currentView;currentView=name;try{await reload();}catch(e){currentView=previous;restoreAddress();showView();throw Error('切换失败，仍停留在原页面；未保存输入已保留。'+e.message);}if(push)history.pushState({},'', '/'+name);committedPath='/'+name;showView();$('page-title').focus();message('已读取本地账本。');});
}
document.querySelectorAll('[data-view]').forEach(a=>a.onclick=e=>{e.preventDefault();navigate(a.dataset.view);});
$('portfolio-account').onchange=()=>renderPositions();
window.addEventListener('popstate',()=>{const name=location.pathname.slice(1);if(name===currentView)return;navigate(['portfolio','cockpit','research','decisions','evolve','plans','cash','screening','planning','trends','academy','settings'].includes(name)?name:'ledger',false);});
// Initial view rendering waits until all deferred modules install their panels.
window.addEventListener('DOMContentLoaded',showView);

window.addEventListener('resize',showView);

$('start-account').onclick=()=>{$('account-name').focus();$('account-form').scrollIntoView({block:'center'});};
window.addEventListener('DOMContentLoaded',()=>{for(const dialog of document.querySelectorAll('dialog')){const heading=dialog.querySelector('h2');if(heading){heading.id=heading.id||dialog.id+'-title';dialog.setAttribute('aria-labelledby',heading.id);}}});

$('trade-form').addEventListener('input',()=>{tradeDirty=true;});$('account-form').addEventListener('input',()=>{accountDirty=true;});
window.addEventListener('beforeunload',e=>{if(tradeDirty||accountDirty){e.preventDefault();e.returnValue='';}});
