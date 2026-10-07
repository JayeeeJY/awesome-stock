'use strict';
// Static diagram literals retained from the reviewed Community frontend/app.js.
function academyDiagram(type) {
  const diagrams = {
    price_volume: `<svg viewBox="0 0 760 260" role="img" aria-label="K线与相对成交量示意图"><g class="diagram-grid"><path d="M40 42H730M40 92H730M40 142H730M40 192H730"/></g><g class="candles"><path d="M92 118V62M88 79h8v23h-8zM150 130V82M146 96h8v18h-8zM208 106V48M204 64h8v27h-8zM266 96V34M262 48h8v30h-8zM324 119V64M320 76h8v28h-8zM382 138V84M378 98h8v22h-8zM440 111V56M436 72h8v22h-8zM498 91V37M494 52h8v24h-8zM556 103V50M552 62h8v25h-8zM614 78V27M610 42h8v21h-8z"/></g><g class="volume-bars"><path d="M80 226v-22h24v22M138 226v-36h24v36M196 226v-54h24v54M254 226v-31h24v31M312 226v-19h24v19M370 226v-44h24v44M428 226v-28h24v28M486 226v-60h24v60M544 226v-38h24v38M602 226v-52h24v52"/></g><text x="42" y="25">价格结构</text><text x="42" y="248">相对成交量</text></svg>`,
    moving_average: `<svg viewBox="0 0 760 260" role="img" aria-label="价格与快慢移动平均线示意图"><g class="diagram-grid"><path d="M40 42H730M40 92H730M40 142H730M40 192H730"/></g><path class="price-line" d="M42 186L88 152 134 168 180 119 226 137 272 91 318 106 364 72 410 99 456 66 502 82 548 44 594 64 640 35 708 52"/><path class="line-fast" d="M42 176C130 161 160 138 226 130S335 90 410 87 520 63 708 48"/><path class="line-slow" d="M42 190C150 180 220 157 318 139S500 98 708 70"/><g class="diagram-legend"><text x="520" y="224">价格</text><text x="584" y="224">快线</text><text x="648" y="224">慢线</text></g></svg>`,
    rsi: `<svg viewBox="0 0 760 300" role="img" aria-label="价格与 RSI 70 50 30 区域示意图"><g class="diagram-grid"><path d="M40 35H710M40 85H710M40 135H710M40 205H710M40 250H710"/></g><path class="price-line" d="M42 118L80 105 118 112 156 83 194 91 232 64 270 72 308 43 346 69 384 57 422 91 460 78 498 110 536 97 574 126 612 101 650 70 706 83"/><path class="rsi-line" d="M42 250L80 226 118 238 156 203 194 211 232 178 270 190 308 167 346 201 384 188 422 229 460 214 498 244 536 221 574 256 612 230 650 198 706 209"/><path class="rsi-high" d="M40 180H710"/><path class="rsi-mid" d="M40 220H710"/><path class="rsi-low" d="M40 260H710"/><text x="716" y="184">70</text><text x="716" y="224">50</text><text x="716" y="264">30</text><text x="42" y="22">价格</text><text x="42" y="170">RSI (14)</text></svg>`,
    macd: `<svg viewBox="0 0 760 270" role="img" aria-label="MACD 零轴信号线与柱体示意图"><g class="diagram-grid"><path d="M40 48H720M40 118H720M40 188H720"/></g><path class="macd-zero" d="M40 150H720"/><g class="macd-bars"><path d="M70 150v34M96 150v27M122 150v17M148 150v8M174 150v-10M200 150v-22M226 150v-36M252 150v-45M278 150v-29M304 150v-14M330 150v8M356 150v22M382 150v30M408 150v19M434 150v4M460 150v-13M486 150v-25M512 150v-41M538 150v-33M564 150v-18M590 150v-4M616 150v11M642 150v23M668 150v14"/></g><path class="line-fast" d="M42 164C110 189 155 170 200 132S280 102 330 152 410 186 460 144 530 101 590 150 650 180 710 138"/><path class="line-slow" d="M42 154C110 169 170 159 220 139S300 125 350 151 430 166 480 145 550 123 610 150 670 163 710 148"/><text x="42" y="26">MACD 与 Signal</text><text x="724" y="154">0</text></svg>`,
    bollinger: `<svg viewBox="0 0 760 260" role="img" aria-label="布林带中轨与波动扩张收缩示意图"><g class="diagram-grid"><path d="M40 45H720M40 100H720M40 155H720M40 210H720"/></g><path class="band-area" d="M42 172C120 122 176 130 240 88S350 55 420 92 520 170 708 50L708 198C565 166 500 205 420 175S300 130 240 157 120 198 42 214Z"/><path class="band-line" d="M42 172C120 122 176 130 240 88S350 55 420 92 520 170 708 50M42 214C120 198 176 185 240 157S350 146 420 175 565 166 708 198"/><path class="line-slow" d="M42 193C120 163 180 158 240 123S350 100 420 133 530 168 708 124"/><path class="price-line" d="M42 201L94 170 146 181 198 135 250 118 302 88 354 105 406 128 458 151 510 184 562 149 614 112 666 75 708 91"/><text x="42" y="26">波动收缩</text><text x="605" y="26">波动扩张</text></svg>`,
    option_contract: `<div class="contract-diagram" role="img" aria-label="期权合约五个要素示意图"><div class="contract-core"><strong>期权合约</strong><span>一组明确条款</span></div><div><span>标的</span><strong>买卖什么</strong></div><div><span>类型</span><strong>看涨 / 看跌</strong></div><div><span>执行价</span><strong>约定价格</strong></div><div><span>到期日</span><strong>权利期限</strong></div><div><span>权利金</span><strong>买方成本</strong></div></div>`,
    option_payoff: `<svg viewBox="0 0 760 270" role="img" aria-label="买入看涨和买入看跌的到期盈亏示意图"><path class="payoff-axis" d="M55 28V230H720M55 135H720"/><path class="call-line" d="M70 180H360L680 45"/><path class="put-line" d="M70 45L350 180H690"/><path class="break-even" d="M448 28V230M272 28V230"/><text x="585" y="62">买入看涨</text><text x="82" y="62">买入看跌</text><text x="60" y="253">标的价格 →</text><text x="8" y="24">盈亏</text><text x="456" y="220">盈亏平衡</text><text x="280" y="220">盈亏平衡</text></svg>`,
    option_greeks: `<div class="greeks-diagram" role="img" aria-label="Delta Gamma Theta Vega 四类敏感度示意图"><div><strong>Δ Delta</strong><span>标的价格</span><i class="greek-line rising"></i></div><div><strong>Γ Gamma</strong><span>Delta 变化</span><i class="greek-line curve"></i></div><div><strong>Θ Theta</strong><span>时间流逝</span><i class="greek-line falling"></i></div><div><strong>V Vega</strong><span>隐含波动率</span><i class="greek-line rising-soft"></i></div></div>`,
  };
  return `<div class="academy-diagram">${Object.hasOwn(diagrams,type) ? diagrams[type] : ""}</div>`;
}

let academyData=null,academySelected=null;
async function loadAcademy(){academyData=await request('/api/v1/owner/academy');renderAcademy();}
function renderAcademy(){
 const query=$('academy-search').value.trim().toLocaleLowerCase(),category=$('academy-category').value;
 const docs=(academyData?.documents||[]).filter(d=>(category==='all'||d.category===category)&&[d.title,d.lead,d.definition,...d.reading_points,...d.misreads,...d.checklist].join(' ').toLocaleLowerCase().includes(query));
 $('academy-list').replaceChildren();$('academy-reading').replaceChildren();$('academy-count').textContent=`${docs.length} 篇匹配文档`;
 if(!docs.length){$('academy-reading').append(element('p','没有匹配的文档。请调整关键词或分类。'));return;}
 if(!docs.some(d=>d.document_id===academySelected))academySelected=docs[0].document_id;
 for(const d of docs){const b=element('button',d.short_title);b.type='button';b.className='secondary';if(d.document_id===academySelected)b.setAttribute('aria-current','true');b.onclick=()=>{academySelected=d.document_id;renderAcademy();};$('academy-list').append(b);}
 const d=docs.find(d=>d.document_id===academySelected),body=$('academy-reading');
 body.append(element('small',d.category_label),element('h2',d.title),element('p',d.lead));
 if(d.formula)body.append(element('code',d.formula));
 // Only a fixed allowlist of local diagram literals is parsed as markup; API text uses textContent.
 const figure=element('div');figure.innerHTML=academyDiagram(d.diagram);body.append(figure,element('p','示意图仅解释概念；小屏可在图内横向查看。'));
 body.append(element('h3','它回答什么'),element('p',d.definition));
 for(const [heading,items,tag] of [['怎么读',d.reading_points,'ul'],['常见误读',d.misreads,'ul'],['使用检查清单',d.checklist,'ol']]){body.append(element('h3',heading));const list=element(tag);items.forEach(v=>list.append(element('li',v)));body.append(list);}
 body.append(element('p','静态教学内容，不构成投资建议；不保存学习进度。'));
 const actions=element('div');actions.className='row';for(const [name,label] of [['research','研究笔记'],['plans','我的计划'],['evolve','决策复盘']]){const a=element('a',label);a.href='/'+name;a.onclick=e=>{e.preventDefault();navigate(name);};actions.append(a);}body.append(actions);
}
async function loadSettings(){
 const s=await request('/api/v1/owner/settings');$('settings-account').textContent=`当前账号：${s.username}`;$('settings-storage').replaceChildren();
 for(const [label,value] of [['数据目录',s.data_directory],['账本文件',s.database_file],['备份目录',s.backup_directory],['数据版本',String(s.schema_version)]])$('settings-storage').append(element('dt',label),element('dd',value));
}
function clearInfo(){academyData=null;academySelected=null;$('academy-search').value='';$('academy-category').value='all';for(const id of ['academy-list','academy-reading','academy-count','settings-account','settings-storage','settings-backup-result','backup-result'])$(id).replaceChildren();$('password-form').reset();}
$('academy-search').oninput=renderAcademy;
$('academy-category').onchange=renderAcademy;
$('settings-backup').onclick=createBackup;
