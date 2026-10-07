'use strict';
// Owner presentation layer. Existing forms and event handlers remain the data boundary.
const shellPages={
 cockpit:['投资驾驶舱','COCKPIT WORKSPACE','从账本事实出发，查看待处理事项与当前数据缺口。'],
 portfolio:['我的持仓','PORTFOLIO WORKBENCH','按账户与币种看清持仓、成本和现金。'],
 ledger:['账户与交易','PORTFOLIO WORKBENCH','建立资金账户，记录成交，让每一次变化有据可查。'],
 cash:['入金与出金','PORTFOLIO WORKBENCH','记录资金流动，核对现金余额。'],
 research:['研究笔记','RESEARCH WORKSPACE','保留证据、反方观点与当时的判断依据。'],
 screening:['候选与证据','RESEARCH WORKSPACE','整理候选标的，为研究补齐可追溯的事实。'],
 decisions:['投资判断','DECISION WORKSPACE','写清为什么行动，以及什么情况下需要重新判断。'],
 plans:['我的计划','PLAN WORKSPACE','把判断转为可复核的步骤，持续记录执行状态。'],
 planning:['配置与交易试算','PLAN WORKSPACE','在行动前核对约束与现金影响；试算不会生成订单。'],
 evolve:['决策复盘','EVOLVE WORKSPACE','对照当时的依据，复核过程、结果与下一次改进。'],
 trends:['规则与周期趋势','EVOLVE WORKSPACE','观察自己的决策过程，保留规则的每一次修订。'],
 academy:['投资学院','ACADEMY WORKSPACE','理解投资概念，为独立判断建立知识基础。'],
 settings:['系统设置','AWESOME STOCK CONTROL CENTER','管理本地账号、个人模型服务与数据备份。']
};
const shellHeader=document.querySelector('main>header');
shellHeader.classList.add('workspace-hero');
shellHeader.querySelector('small').id='shell-kicker';
shellHeader.querySelector('p').id='shell-description';
const shellBreadcrumb=element('span','个人投资工作台');shellBreadcrumb.id='shell-breadcrumb';
const shellToolbar=document.querySelector('.toolbar');shellToolbar.prepend(shellBreadcrumb);
shellToolbar.querySelector(':scope>span:not(#shell-breadcrumb)').classList.add('toolbar-account');
$('message').after($('backup-result'));

const shellMenu=element('button','☰');shellMenu.id='workspace-menu';shellMenu.type='button';shellMenu.className='secondary';shellMenu.setAttribute('aria-label','打开工作区菜单');shellMenu.setAttribute('aria-controls','workspace-navigation');shellMenu.setAttribute('aria-expanded','false');shellToolbar.prepend(shellMenu);
const shellDrawer=element('dialog');shellDrawer.id='workspace-navigation';shellDrawer.setAttribute('aria-label','工作区导航');
const shellClose=element('button','关闭菜单');shellClose.type='button';shellClose.className='secondary drawer-close';shellDrawer.append(shellClose);$('workspace').append(shellDrawer);
const shellNav=$('view-nav'),shellNavAnchor=document.createComment('desktop navigation');shellNav.before(shellNavAnchor);
shellMenu.onclick=()=>{shellDrawer.showModal();shellMenu.setAttribute('aria-expanded','true');};shellClose.onclick=()=>shellDrawer.close();
shellDrawer.addEventListener('close',()=>shellMenu.setAttribute('aria-expanded','false'));
shellNav.addEventListener('click',e=>{if(e.target.closest('[data-view]')&&shellDrawer.open)shellDrawer.close();});
const shellSymbols={cockpit:'◈',portfolio:'▥',ledger:'≡',cash:'↔',research:'⌕',screening:'◇',decisions:'◎',plans:'☷',planning:'▦',evolve:'↗',trends:'⌁',academy:'▤',settings:'⚙'};
for(const a of shellNav.querySelectorAll('[data-view]')){const name=a.dataset.view;const label=element('span',shellPages[name][0]);const symbol=element('span',shellSymbols[name]);symbol.className='nav-symbol';symbol.setAttribute('aria-hidden','true');a.replaceChildren(symbol,label);}
for(const [index,group] of [...shellNav.querySelectorAll('details')].entries()){const labels=[['资产','Portfolio'],['研究','Research'],['计划','Plan'],['进化','Evolve']][index];const summary=group.querySelector('summary');summary.replaceChildren(element('strong',labels[0]),element('small',labels[1]));}
const shellBottom=element('nav');shellBottom.id='mobile-workspaces';shellBottom.setAttribute('aria-label','常用工作区');
for(const name of ['cockpit','portfolio','research','plans','evolve','settings']){const a=element('a');a.href='/'+name;a.dataset.mobileView=name;const icon=element('span',shellSymbols[name]);icon.setAttribute('aria-hidden','true');a.append(icon,element('small',{cockpit:'驾驶舱',portfolio:'资产',research:'研究',plans:'计划',evolve:'进化',settings:'设置'}[name]));a.onclick=e=>{e.preventDefault();navigate(name);};shellBottom.append(a);}$('workspace').append(shellBottom);
// Settings sections stay mounted: changing a tab never clears an unfinished form.
const settingsPanel=$('settings-panel');const settingsSections=[...settingsPanel.children];
const settingsLayout=element('div');settingsLayout.className='settings-layout';const settingsTabs=element('div');settingsTabs.className='settings-tabs';settingsTabs.setAttribute('role','tablist');settingsTabs.setAttribute('aria-label','设置分类');settingsTabs.setAttribute('aria-orientation','vertical');const settingsBody=element('div');settingsBody.className='settings-body';settingsLayout.append(settingsTabs,settingsBody);settingsPanel.append(settingsLayout);
const settingsGroups=[['account','本地账号',[0]],['appearance','外观',[]],['connections','AI 与行情',[4]],['data','数据与备份',[1,2]],['privacy','隐私与安全',[5]],['about','关于与能力',[3]]];
let selectedSettings='account';
function selectSettings(name,focus=false){selectedSettings=name;for(const tab of settingsTabs.children){const active=tab.dataset.settingsTab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}for(const panel of settingsBody.children)panel.hidden=panel.id!=='settings-group-'+name;if(focus)$('settings-tab-'+name).focus();}
for(const [name,title,indices] of settingsGroups){const tab=element('button',title);tab.id='settings-tab-'+name;tab.type='button';tab.dataset.settingsTab=name;tab.setAttribute('role','tab');tab.setAttribute('aria-controls','settings-group-'+name);tab.onclick=()=>selectSettings(name);settingsTabs.append(tab);const panel=element('div');panel.id='settings-group-'+name;panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',tab.id);for(const index of indices)if(settingsSections[index])panel.append(settingsSections[index]);settingsBody.append(panel);}
settingsTabs.addEventListener('keydown',e=>{const tabs=[...settingsTabs.children];let index=tabs.indexOf(document.activeElement);if(index<0)return;if(['ArrowDown','ArrowRight'].includes(e.key))index=(index+1)%tabs.length;else if(['ArrowUp','ArrowLeft'].includes(e.key))index=(index+tabs.length-1)%tabs.length;else if(e.key==='Home')index=0;else if(e.key==='End')index=tabs.length-1;else return;e.preventDefault();selectSettings(tabs[index].dataset.settingsTab,true);});
const appearance=element('section');appearance.append(element('h2','工作台外观'),element('p','选择适合你的阅读环境。偏好仅保存在当前浏览器，不会改变账本数据。'));const themeLabel=element('label','界面主题');const themeSelect=element('select');themeSelect.id='owner-theme';for(const [value,title] of [['midnight','深蓝科技'],['calm','沉静深色']]){const option=element('option',title);option.value=value;themeSelect.append(option);}themeLabel.append(themeSelect);appearance.append(themeLabel);$('settings-group-appearance').append(appearance);
let savedTheme='midnight';try{savedTheme=localStorage.getItem('awesome-owner-theme')||savedTheme;}catch{}if(!['midnight','calm'].includes(savedTheme))savedTheme='midnight';themeSelect.value=savedTheme;document.documentElement.dataset.ownerTheme=savedTheme;themeSelect.onchange=()=>{document.documentElement.dataset.ownerTheme=themeSelect.value;try{localStorage.setItem('awesome-owner-theme',themeSelect.value);}catch{}updateOwnerShell();};
const shellFacts=element('div');shellFacts.id='shell-facts';shellHeader.append(shellFacts);
for(const [label,value] of [['使用方式','个人 · 本地'],['数据更新','主动读取'],['模型与行情','按需自行配置'],['界面主题','深蓝科技']]){const card=element('div');card.append(element('small',label),element('strong',value));shellFacts.append(card);}
selectSettings('account');
function updateOwnerShell(){const signed=!$('workspace').hidden;const page=shellPages[currentView];if(signed){$('page-title').textContent=page[0];$('shell-kicker').textContent=page[1];$('shell-description').textContent=page[2];shellBreadcrumb.textContent='个人工作台 / '+page[0];}shellHeader.classList.toggle('settings-hero',signed&&currentView==='settings');shellFacts.hidden=!signed||currentView!=='settings';shellHeader.querySelector('.badge').hidden=signed;shellFacts.lastElementChild.querySelector('strong').textContent=themeSelect.value==='calm'?'沉静深色':'深蓝科技';
 const mobile=innerWidth<1000;shellMenu.hidden=!mobile;if(mobile&&shellNav.parentElement!==shellDrawer)shellDrawer.append(shellNav);else if(!mobile&&shellNav.parentElement===shellDrawer){shellDrawer.close();shellNavAnchor.after(shellNav);}for(const a of shellBottom.children){if(a.dataset.mobileView===currentView)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}if(!signed&&shellDrawer.open)shellDrawer.close();}
window.addEventListener('DOMContentLoaded',updateOwnerShell);
