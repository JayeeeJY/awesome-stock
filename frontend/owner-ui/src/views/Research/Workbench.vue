<template>
 <section class="research-page">
  <section class="research-hero" :class="{'is-compact':loaded&&!loading}"><div><div class="eyebrow"><span class="protocol-dot"/>AWESOME RESEARCH / V1</div><h1>个股研究</h1><p>从已保存的来源出发，区分事实、推断与证据缺口。</p></div><div class="framework-badge"><span>研究协议</span><strong>Evidence → Context → Conclusion</strong></div></section>
  <section class="research-console" :class="{'is-compact':loaded&&!loading}"><div class="console-input"><label for="research-symbols">标的代码</label><el-input id="research-symbols" v-model="input" type="text" size="large" @input="loadFeedback=''" /></div><el-button class="run-button" type="primary" :loading="loading" :disabled="assistantState.busy" @click="load">载入本地研究材料</el-button><el-button @click="router.push('/research/notes')">笔记与历史</el-button><div v-if="loaded&&!loading" class="console-lens-summary"><span>本次研究问题</span><strong>{{ lenses.filter(l=>selectedLenses.includes(l.id)).map(l=>l.title).join(' · ') }}</strong><el-button :aria-expanded="editingLenses" @click="editingLenses=!editingLenses">{{ editingLenses?'收起研究问题':'调整研究问题' }}</el-button></div></section>
  <p v-if="loadFeedback" class="load-feedback" role="status" aria-live="polite">{{ loadFeedback }}</p>
  <AppDataState v-if="error" tone="error" title="研究材料未更新" :description="error" action-label="重试" @action="load"/>
  <section v-if="!loaded||loading||editingLenses" class="lens-panel"><div class="section-heading"><div><span class="section-kicker">RESEARCH LENSES</span><h2>选择本次研究必须回答的问题</h2></div><span>{{ selectedLenses.length }}/{{ lenses.length }}</span></div><div class="lens-grid"><button v-for="lens in lenses" :key="lens.id" type="button" class="lens-card" :class="{active:selectedLenses.includes(lens.id)}" :aria-pressed="selectedLenses.includes(lens.id)" @click="toggle(lens.id)"><span class="lens-index">{{ lens.index }}</span><strong>{{ lens.title }}</strong><small>{{ lens.description }}</small><span class="lens-state">{{ selectedLenses.includes(lens.id)?'已纳入':'未纳入' }}</span></button></div></section>
  <section v-if="!loaded" class="research-empty"><div class="empty-orbit"><span/></div><div><h2>从论点与证据开始</h2><p>输入标的，主动载入本地笔记、候选与证据。载入不会调用模型或行情。</p></div></section>
  <template v-if="loaded">
   <ReportHistory :ai-receipt="adoptedSynthesis?.receipt_id" :symbol="selected[0]" :lenses="selectedLenses" :disabled="loading||assistantState.busy"/>
   <section class="report-command"><div class="report-identity"><span>本地材料快照</span><h2>{{ selected[0] }}</h2><strong>{{ records.length }} 条记录</strong></div><div class="command-conclusion"><div class="conclusion-kicker"><span>{{ reportSummary.label }}</span></div><h2>{{ reportSummary.headline }}</h2><template v-if="adoptedSynthesis"><el-tag type="warning">AI 综合 · 未核验 · {{ adoptedSynthesis.model }}</el-tag><p class="adopted-brief">{{ adoptedSynthesis.synthesis.decision_brief }}</p><small>{{ adoptedSynthesis.synthesis.why_now }}</small><p>不确定性：{{ adoptedSynthesis.synthesis.uncertainty }}</p><ul><li v-for="(condition,index) in adoptedSynthesis.synthesis.decision_conditions" :key="index">{{ condition }}</li></ul><details><summary>查看规则摘要与本次生成依据</summary><p>{{ reportSummary.detail }}</p><p>{{ adoptedSynthesis.provider }} / {{ adoptedSynthesis.model }} · {{ adoptedSynthesis.generated_at }}</p><pre>{{ adoptedSynthesis.context }}</pre></details><el-button @click="adoptedSynthesis=null">恢复规则摘要</el-button></template><template v-else><p>{{ reportLead }}</p><details class="report-basis"><summary>查看保存判断与研究范围</summary><p>{{ reportSummary.detail }}</p><p>当前研究范围：{{ selected.join('、') }}</p></details></template><small class="report-caveat">材料覆盖与有效性不等于投资结论；AI 草稿需单独生成和核对。</small></div><div class="command-scores"><div><span>有效证据</span><strong>{{ usableEvidence.length }}/{{ evidence.length }}</strong></div><div><span>最近观察</span><strong class="date-metric">{{ latestObservation||'—' }}</strong></div><div><span>结论置信度</span><strong>未评估</strong></div></div></section>
   <section class="terminal-card action-card report-actions"><header><span>02 / 下一步核对</span></header><ol><li v-for="action in nextActions" :key="action">{{ action }}</li></ol><div v-if="gaps.length" class="gap-box"><strong>证据缺口</strong><span v-for="gap in gaps" :key="gap">{{ gap }}</span></div><div class="report-links"><el-button @click="router.push({path:'/research/screening',query:{symbol:selected[0]}})">补充证据</el-button><el-button @click="router.push({path:'/decisions',query:{symbol:selected[0]}})">记录判断</el-button></div></section>
   <section class="terminal-card lens-results"><header><span>03 / 关键证据读数</span><small>只描述当前保存材料，不推断缺失指标</small></header><div class="readout-list"><article v-for="lens in lenses.filter(l=>selectedLenses.includes(l.id))" :key="lens.id"><span>{{ lens.index }}</span><div><h3>{{ lens.title }}</h3><p>{{ readout(lens.id) }}</p></div></article></div></section>
   <section class="report-grid"><article v-if="selectedLenses.includes('position')" class="terminal-card position-card"><header><span>04 / 持仓语境</span><el-tag>{{ positions.length?'账本中有持仓':'账本中无持仓' }}</el-tag></header><div v-for="position in positions" :key="position.account_id" class="position-metrics"><div><span>{{ position.account_name }} · 数量</span><strong>{{ position.quantity }}</strong></div><div><span>市值 · {{ position.currency }}</span><strong>{{ money(position.market_value) }}</strong></div><div><span>该账户内权重</span><strong>{{ position.weight }}</strong></div></div><p v-if="!positions.length">当前已记录账本中没有此标的持仓。</p><p class="muted">不同币种不合并；缺少有效价格时不生成估值或权重。</p></article>
   <article v-if="selectedLenses.includes('valuation')||selectedLenses.includes('momentum')" class="terminal-card snapshot-card"><header><span>市场与估值参照</span></header><div class="snapshot-grid"><div v-for="metric in ['pe','pb']" :key="metric"><span>{{ metric==='pe'?'P/E':'P/B' }}</span><strong>{{ fact(metric)?.value??'—' }}</strong><small>{{ fact(metric)?String(fact(metric)?.source)+' · '+fact(metric)?.as_of:'缺少有效核验材料' }}</small></div></div><div v-for="quote in quotes" :key="quote.id" class="quote-reference"><strong>{{ quote.currency }} {{ quote.price }}</strong><p>{{ quote.source }} · {{ quote.as_of }} · {{ currentQuote(quote.as_of,quote.symbol,quote.currency)?'三日内快照':String(quote.as_of)>today?'未来日期，待核对':'已过期，仅供历史参考' }}</p></div><p v-if="!quotes.length">独立价格快照缺失；日线指标另见下方，不用于自动改写持仓估值。</p></article></section>
   <NewsEvidence v-if="newsSource&&selectedLenses.some(l=>['business','catalysts','risk'].includes(l))" :source="newsSource"/><MemoryEvidence v-if="researchMemory" :memory="researchMemory"/><CompanyEvidence v-if="selectedLenses.some(l=>['business','valuation'].includes(l))&&companySource" :source="companySource"/><PositionEvidence v-if="selectedLenses.includes('position')&&positionIntelligence" :evidence="positionIntelligence"/><TechnicalEvidencePanel v-if="selectedLenses.includes('momentum')" :evidence="technicalEvidence"/><details class="terminal-card evidence-details"><summary><span>05 / 来源与版本账本</span><small>{{ records.length }} 条材料</small></summary><div class="evidence-list"><article v-for="item in records" :key="item.id" class="material-card"><h3>{{ item.symbol }} · {{ item.title }}</h3><p>{{ kindLabel(item.kind) }} · v{{ item.revision }} · {{ item.updated_at }}</p><p v-if="item.kind==='evidence'">人工方向：{{ item.direction==='weakens'?'削弱判断':item.direction==='strengthens'?'支持判断':'未标记 / 中性' }} · 来源：{{ item.source }} · {{ item.verification==='verified'?'人工已核验':'未核验' }} · 截止 {{ item.expires_on }}{{ String(item.expires_on)<today?' · 已过期':'' }}</p><p class="material-content">{{ item.content?readableHandoffNote(item.id,String(item.content)):item.thesis||item.value||'未填写数值' }}</p><p v-if="item.kind==='decision'">反方依据：{{ item.counter_case }}；失效条件：{{ item.invalidation }}</p></article><p v-if="!records.length">尚无保存的研究材料。</p></div></details>
  </template>
  <Assistant ref="assistant" :key="materialGeneration" :source-context="sourceContext" :symbol="selected[0]" :external-busy="loading" allow-report-synthesis @synthesis="adoptSynthesis" @state="assistantState=$event" />
 </section>
</template>
<script setup lang="ts">
import {computed,ref,onBeforeUnmount,watch} from 'vue'
import {registerPageMaterial} from '@/api/pageMaterial'
import {useRoute,useRouter} from 'vue-router'
import Assistant from '@/components/Research/Assistant.vue'
import ReportHistory from '@/components/Research/ReportHistory.vue'
import AppDataState from '@/components/Global/AppDataState.vue'
import {getWorkspace,type BusinessRecord,type Workspace} from '@/api/business'
import MemoryEvidence from '@/components/Research/MemoryEvidence.vue'
import type {ResearchMemory} from '@/api/researchMemory'
import NewsEvidence from '@/components/Research/NewsEvidence.vue'
import type {NewsSource} from '@/api/news'
import CompanyEvidence from '@/components/Research/CompanyEvidence.vue'
import type {CompanySource} from '@/api/company'
import PositionEvidence from '@/components/Research/PositionEvidence.vue'
import type {PositionIntelligence} from '@/api/researchPosition'
import TechnicalEvidencePanel from '@/components/Research/TechnicalEvidence.vue'
import type {TechnicalEvidence} from '@/api/researchTechnical'
import {request} from '@/api/owner'
import {money,percent,sum,multiply} from '@/utils/decimal'
import {readableHandoffNote} from '@/utils/handoffNote'
const route=useRoute(),router=useRouter(),input=ref(typeof route.query.symbol==='string'?route.query.symbol:''),selected=ref<string[]>([]),records=ref<BusinessRecord[]>([]),loading=ref(false),loaded=ref(false),error=ref(''),loadFeedback=ref(''),loadCount=ref(0)
const memorySnapshot=ref<ResearchMemory|null>(null)
const researchMemory=computed(()=>memorySnapshot.value&&memorySnapshot.value.evaluated_on!==today.value?{...memorySnapshot.value,refresh_required:true,quality_score:null,freshness_score:null}:memorySnapshot.value)
const newsSource=ref<NewsSource|null>(null)
const companySource=ref<CompanySource|null>(null)
const positionSnapshot=ref<PositionIntelligence|null>(null)
const positionIntelligence=computed(()=>positionSnapshot.value&&positionSnapshot.value.evaluated_on!==today.value?{...positionSnapshot.value,status:'refresh_required',risk_level:'unknown',signals:[],context_signals:[],weight_percent:null,total_holdings_usd:null,symbol_holdings_usd:null}:positionSnapshot.value)
const technicalSnapshot=ref<TechnicalEvidence|null>(null)
const snapshot=ref<Workspace|null>(null),clock=ref(Date.now())
const technicalEvidence=computed(()=>technicalSnapshot.value?.source&&(technicalSnapshot.value.evaluated_on!==today.value||(technicalSnapshot.value.market_evaluated_on&&technicalSnapshot.value.market_evaluated_on!==marketToday(technicalSnapshot.value.source.symbol,technicalSnapshot.value.source.currency)))?{...technicalSnapshot.value,status:'refresh_required',technical:null,market_signals:[],assistant_context:undefined}:technicalSnapshot.value)
const today=computed(()=>new Date(clock.value).toISOString().slice(0,10)),freshAfter=computed(()=>new Date(clock.value-3*86400000).toISOString().slice(0,10))
function refreshClock(){clock.value=Date.now()}
const clockTimer=window.setInterval(refreshClock,30000)
window.addEventListener('focus',refreshClock);document.addEventListener('visibilitychange',refreshClock)
onBeforeUnmount(()=>{window.clearInterval(clockTimer);window.removeEventListener('focus',refreshClock);document.removeEventListener('visibilitychange',refreshClock)})
function marketToday(symbol:unknown,currency:unknown){return new Date(clock.value+(typeof symbol==='string'&&((currency==='CNY'&&/^(?:(?:60|68)\d{4}(?:\.SHH)?|(?:00|30)\d{4}(?:\.SHZ)?)$/.test(symbol))||(currency==='HKD'&&/^\d{4,5}$/.test(symbol)))?8*3600000:0)).toISOString().slice(0,10)}
function currentQuote(date:unknown,symbol?:unknown,currency?:unknown){const end=marketToday(symbol,currency),start=new Date(Date.parse(end+'T00:00:00Z')-3*86400000).toISOString().slice(0,10);return typeof date==='string'&&date>=start&&date<=end}

const lenses=[{id:'position',index:'01',title:'持仓语境',description:'先回答我是否持有、持有多少、对组合影响多大'},{id:'business',index:'02',title:'业务质量',description:'识别行业、业务增长与资料缺口'},{id:'valuation',index:'03',title:'估值参照',description:'把 P/E、P/B 当成上下文，而不是答案'},{id:'momentum',index:'04',title:'价格行为',description:'读取本地快照和数据时间，不伪造趋势'},{id:'catalysts',index:'05',title:'事件催化',description:'跟踪财报、公司事件和下一验证窗口'},{id:'risk',index:'06',title:'反证风险',description:'优先保留削弱原判断的证据'}]
const assistant=ref<InstanceType<typeof Assistant>|null>(null),materialGeneration=ref(0),assistantState=ref({busy:false,preview:false,result:false,failed:false,dirty:false})
const editingLenses=ref(false)
const selectedLenses=ref(lenses.map(l=>l.id))
function toggle(id:string){if(selectedLenses.value.includes(id)){if(selectedLenses.value.length>1)selectedLenses.value=selectedLenses.value.filter(l=>l!==id)}else selectedLenses.value.push(id)}
const evidence=computed(()=>records.value.filter(r=>r.kind==='evidence')),usableEvidence=computed(()=>evidence.value.filter(r=>r.verification==='verified'&&String(r.expires_on)>=today.value)),latestObservation=computed(()=>evidence.value.map(r=>String(r.as_of)).sort().at(-1))
function fact(metric:string){const latest=evidence.value.filter(r=>r.metric===metric).sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of))||b.updated_at.localeCompare(a.updated_at))[0];return latest&&latest.verification==='verified'&&String(latest.expires_on)>=today.value&&latest.value!==null?latest:null}
const positions=computed(()=>snapshot.value?.accounts.flatMap(a=>a.positions.filter(p=>p.symbol===selected.value[0]).map(p=>({...p,quote_status:currentQuote(p.quote?.as_of,p.symbol,a.currency)?p.quote_status:p.quote?'stale':'missing',unrealized_pnl:currentQuote(p.quote?.as_of,p.symbol,a.currency)?p.unrealized_pnl:null,market_value:currentQuote(p.quote?.as_of,p.symbol,a.currency)?p.market_value:null,account_id:a.id,account_name:a.name,currency:a.currency,weight:a.positions.every(position=>currentQuote(position.quote?.as_of,position.symbol,a.currency))&&currentQuote(p.quote?.as_of,p.symbol,a.currency)&&p.market_value!==null&&a.estimated_assets!==null?percent(p.market_value,a.estimated_assets):'—'})))||[])
const quotes=computed(()=>snapshot.value?.records.filter(r=>r.kind==='quote'&&r.symbol===selected.value[0]).sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of))||b.updated_at.localeCompare(a.updated_at)||b.id.localeCompare(a.id)).filter((r,i,all)=>all.findIndex(x=>x.currency===r.currency)===i)||[])
const gaps=computed(()=>[...(!records.value.length?['尚无本地研究材料']:[]),...evidence.value.filter(r=>r.verification!=='verified'||String(r.expires_on)<today.value).map(r=>r.title+'：'+(r.verification!=='verified'?'尚未核验':'已过期')),...(selectedLenses.value.includes('valuation')?['pe','pb'].filter(m=>!fact(m)).map(m=>m.toUpperCase()+' 缺少有效来源'):[]),...(selectedLenses.value.includes('momentum')&&!quotes.value.some(q=>currentQuote(q.as_of,q.symbol,q.currency))?['缺少三日内价格快照']:[])])
const latestDecision=computed(()=>records.value.filter(r=>r.kind==='decision').sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||b.id.localeCompare(a.id))[0])
const concentrated=computed(()=>{const p=positionIntelligence.value;return selectedLenses.value.includes('position')&&p?.symbol_holdings_usd!=null&&p.total_holdings_usd!=null&&p.weight_percent!=null&&!sum([multiply(p.symbol_holdings_usd,'4'),multiply(p.total_holdings_usd,'-1')]).startsWith('-')})
const directionalEvidence=computed(()=>usableEvidence.value.filter(r=>['strengthens','weakens'].includes(String(r.direction))).sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of))||b.updated_at.localeCompare(a.updated_at)||b.id.localeCompare(a.id)))
const weakened=computed(()=>directionalEvidence.value[0]?.direction==='weakens'||directionalEvidence.value.filter(r=>r.direction==='weakens').length>directionalEvidence.value.filter(r=>r.direction==='strengthens').length)
const reportSummary=computed(()=>{
 const decision=latestDecision.value
 const detail=decision?'最新保存判断「'+decision.title+'」：'+String(decision.content||'尚未填写论点')+'；失效条件：'+String(decision.invalidation||'待补'):'尚未保存可追溯的投资判断；先核对持仓、证据缺口与下一步验证。'
 if(selectedLenses.value.includes('position')&&positionIntelligence.value?.risk_level==='critical'&&positionIntelligence.value.signals.length)return {posture:'risk_review',label:'仓位纪律复核',headline:positionIntelligence.value.signals[0].title,detail:positionIntelligence.value.signals[0].next_step+' '+detail}
 if(!positions.value.length)return {posture:'research_first',label:'先研究',headline:'先补齐关键证据，再决定是否进入观察清单',detail}
 if(concentrated.value)return {posture:'risk_review',label:'集中度复核',headline:'先复核仓位集中度，再判断个股逻辑',detail:'全组合持仓美元市值占比 '+money(positionIntelligence.value?.weight_percent??null)+'%（不含现金）'+'。25%为研究提示线，不是你的个人纪律阈值。'+detail}
 if(weakened.value)return {posture:'thesis_review',label:'复核持仓逻辑',headline:'最新证据正在削弱原判断，需要复核持仓逻辑',detail:'依据人工标注、已核验且未过期的证据方向；不代表系统已证实原判断失效。'+detail}
 if(decision)return {posture:'conditional_watch',label:'有待持续验证',headline:'已有保存判断，后续行动仍需绑定证据和条件',detail}
 return {posture:'needs_thesis',label:'补充持仓假设',headline:'有持仓但缺少保存判断，先补充可证伪的投资逻辑',detail}
})
const reportLead=computed(()=>{
 if(selectedLenses.value.includes('position')&&positionIntelligence.value?.risk_level==='critical'&&positionIntelligence.value.signals.length)return positionIntelligence.value.signals[0].next_step
 if(!positions.value.length)return '当前账本无此标的持仓；先核对来源和关键证据缺口。'
 if(concentrated.value)return '全组合持仓美元市值占比 '+money(positionIntelligence.value?.weight_percent??null)+'%（不含现金）；25%是研究提示线，不是你的个人纪律阈值。'
 if(weakened.value)return '已核验且未过期的人工方向证据提示复核；这不等于系统证实原判断失效。'
 if(latestDecision.value)return '最新保存判断「'+latestDecision.value.title+'」；继续核对支持依据、反方证据和失效条件。'
 return '已有持仓但尚无可追溯判断；先补充可证伪的投资逻辑。'
})
const nextActions=computed(()=>[...(selectedLenses.value.includes('position')&&positionIntelligence.value?.risk_level==='critical'?positionIntelligence.value.signals.map(s=>s.next_step):[]),...(weakened.value?['复核人工标记为削弱判断的有效证据；方向标记不等于系统已证实原判断失效。']:[]),...(concentrated.value?['核对全组合持仓集中度与自己的投资纪律；研究提示不代替组合约束。']:[]),...(latestDecision.value?['复核已保存判断的支持依据、反方证据和失效条件。']:['记录最关键的支持理由及一条可检验的失效条件。']),...(selectedLenses.value.includes('catalysts')?['核对下一项财报或公司事件；复核日期不等于已确认事件日期。']:[]),...(gaps.value.length?['补齐下方证据缺口，再评估材料是否足以支持判断。']:[]),'逐项核对来源，再决定是否需要AI辅助。'])
const kindLabel=(kind:string)=>({note:'研究笔记',decision:'投资判断',candidate:'候选逻辑',evidence:'证据'}[kind]||kind)
function readout(lens:string){if(lens==='position')return positions.value.length?positions.value.map(p=>p.account_name+' · '+p.quantity+' 股 · '+p.currency+' '+money(p.market_value)).join('；'):'已记录账本中无持仓';if(lens==='business')return ['revenue_growth','gross_margin'].map(m=>(m==='revenue_growth'?'营收增长':'毛利率')+'：'+(fact(m)?String(fact(m)?.value)+'%':'缺少有效证据')).join('；');if(lens==='valuation')return ['pe','pb'].map(m=>m.toUpperCase()+'：'+(fact(m)?.value??'缺少有效证据')).join('；');if(lens==='momentum'&&technicalEvidence.value?.technical)return '已保存日线 '+technicalEvidence.value.source?.candles.length+' 根，技术指标与来源见下方；不代表交易结论';if(lens==='momentum')return quotes.value.length?'已保存 '+quotes.value.length+' 个币种价格快照；单次快照不构成趋势判断':'没有价格快照，不推断趋势';if(lens==='risk')return records.value.filter(r=>r.kind==='decision').map(r=>r.title+'：'+r.counter_case+'；失效条件：'+r.invalidation).join('；')||'尚无保存的反方判断，请主动核查';return records.value.filter(r=>r.review_on).map(r=>r.title+' · 用户复核日期 '+r.review_on).join('；')||'尚无保存的事件或复核日期；不会自动生成事件'}
const sourceContext=computed(()=>loaded.value?JSON.stringify({evaluated_on:today.value,symbols:selected.value,records:records.value,rule_summary:reportSummary.value,next_actions:nextActions.value,evidence_gaps:gaps.value,research_questions:lenses.filter(l=>selectedLenses.value.includes(l.id)),position_context:selectedLenses.value.includes('position')?positions.value:[],price_snapshots:selectedLenses.value.includes('momentum')?quotes.value:[],research_memory:researchMemory.value,news_source:selectedLenses.value.some(l=>['business','catalysts','risk'].includes(l))?newsSource.value:null,company_source:selectedLenses.value.some(l=>['business','valuation'].includes(l))?companySource.value:null,position_intelligence:selectedLenses.value.includes('position')?positionIntelligence.value:null,market_technical:selectedLenses.value.includes('momentum')?(technicalEvidence.value?.assistant_context??technicalEvidence.value):null,notice:'仅已保存材料；缺失与过期状态不能自动视为已核验。'},null,2):'')
type AdoptedSynthesis={receipt_id?:string;provider:string;model:string;generated_at:string;context:string;symbol:string;synthesis:{status:'structured'|'unstructured';decision_brief?:string;why_now?:string;uncertainty?:string;decision_conditions?:string[];reason?:string}}
const adoptedSynthesis=ref<AdoptedSynthesis|null>(null)
function adoptSynthesis(value:AdoptedSynthesis){if(loading.value||value.symbol!==selected.value[0]||value.context!==sourceContext.value||value.synthesis.status!=='structured')return;adoptedSynthesis.value=JSON.parse(JSON.stringify(value))}
watch(sourceContext,()=>{adoptedSynthesis.value=null},{flush:'sync'})
const unregisterMaterial=registerPageMaterial('/research',()=>{if(loading.value||error.value||!loaded.value)throw Error('请先在研究页载入一个标的的材料');return {...JSON.parse(sourceContext.value),ai_synthesis:adoptedSynthesis.value}});onBeforeUnmount(unregisterMaterial);
async function load(){
 if(loading.value||assistantState.value.busy)return
 const symbols=[...new Set(input.value.toUpperCase().split(/[\s,，]+/).filter(Boolean))]
 loadFeedback.value=''
 if(!symbols.length||symbols.length>1||symbols.some(s=>!/^([A-Z0-9][A-Z0-9.^_-]{0,23})$/.test(s))){error.value='请填写一个有效标的代码';return}
 refreshClock();loading.value=true;error.value=''
 try{
  if(assistantState.value.dirty&&!(await assistant.value?.confirmMaterialChange()))return
  const [workspace,documents,technical,intelligence,company,memory,news]=await Promise.all([getWorkspace(),request<{documents:BusinessRecord[]}>('/api/v1/owner/documents'),request<TechnicalEvidence>('/api/v1/owner/research-technical','POST',{symbol:symbols[0]}),request<PositionIntelligence>('/api/v1/owner/research-position','POST',{symbol:symbols[0]}),request<{snapshot:CompanySource|null}>('/api/v1/owner/company-source','POST',{symbol:symbols[0]}),request<ResearchMemory>('/api/v1/owner/research-memory','POST',{symbol:symbols[0]}),request<{snapshot:NewsSource|null}>('/api/v1/owner/news-source','POST',{symbol:symbols[0]})])
  const sameSymbol=selected.value[0]===symbols[0]
  newsSource.value=news.snapshot;memorySnapshot.value=memory;companySource.value=company.snapshot;technicalSnapshot.value=technical;positionSnapshot.value=intelligence
  records.value=[...workspace.records.filter(r=>['candidate','evidence'].includes(r.kind)),...documents.documents.filter(d=>['note','decision'].includes(d.kind)&&!d.archived)].filter(r=>symbols.includes(String(r.symbol)))
  snapshot.value=workspace;selected.value=symbols;loaded.value=true;editingLenses.value=false;materialGeneration.value++
  loadCount.value=sameSymbol?loadCount.value+1:1
  loadFeedback.value=`${sameSymbol?'已重新读取':'已载入'} ${symbols[0]} 的本地材料（本页第 ${loadCount.value} 次）：${records.value.length} 条研究记录。下方显示持仓、价格与证据缺口；未调用模型或行情。`
 }catch(e){error.value=e instanceof Error?e.message:'载入失败'}finally{loading.value=false}
}
</script>

<style scoped lang="scss">
.research-page {
  --research-bg: #081426;
  --research-panel: rgba(10, 28, 51, 0.82);
  --research-line: rgba(93, 190, 255, 0.18);
  --research-text: #eaf6ff;
  --research-muted: #82a0bb;
  --research-cyan: #4dd9ff;
  --research-blue: #3f7cff;
  min-height: calc(100vh - 64px);
  padding: 22px 28px 28px;
  color: var(--research-text);
  background:
    radial-gradient(circle at 12% 0%, rgba(23, 111, 175, 0.24), transparent 34%),
    radial-gradient(circle at 90% 14%, rgba(33, 211, 200, 0.12), transparent 30%),
    linear-gradient(180deg, #0a1729, #07111f);
}

.research-hero,
.research-console,
.lens-panel,
.research-empty,
.research-loading,
.report-command,
.report-actions,
.terminal-card {
  max-width: 1540px;
  margin-left: auto;
  margin-right: auto;
}

.research-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 2px 18px;
  h1 { margin: 7px 0 6px; font-size: clamp(26px, 2.35vw, 38px); letter-spacing: -0.04em; }
  p { max-width: 760px; margin: 0; color: var(--research-muted); font-size: 15.5px; line-height: 1.62; }
}

.research-hero.is-compact {
  align-items: center;
  padding-bottom: 12px;

  h1 {
    font-size: clamp(24px, 1.85vw, 32px);
  }

  p {
    max-width: 680px;
    font-size: 14px;
    line-height: 1.45;
  }
}

.eyebrow,
.section-kicker {
  color: var(--research-cyan);
  font: 700 11px/1.2 "SFMono-Regular", Consolas, monospace;
  letter-spacing: 0.16em;
}

.protocol-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 8px;
  border-radius: 50%;
  background: #43f0c5;
  box-shadow: 0 0 14px #43f0c5;
}

.framework-badge {
  min-width: 270px;
  padding: 12px 16px;
  border: 1px solid var(--research-line);
  border-radius: 12px;
  background: rgba(9, 25, 44, 0.7);
  span { display: block; margin-bottom: 5px; color: var(--research-muted); font-size: 11px; }
  strong { font: 600 12px "SFMono-Regular", Consolas, monospace; color: #bcecff; }
}

.research-console {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(250px, 0.7fr) auto;
  gap: 16px;
  align-items: end;
  padding: 18px;
  border: 1px solid var(--research-line);
  border-radius: 16px;
  background: var(--research-panel);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.18);
  label { display: block; margin-bottom: 8px; color: var(--research-muted); font-size: 12px; }
  :deep(.el-input__wrapper),
  :deep(.el-radio-group) {
    min-height: 44px;
    border: 1px solid rgba(107, 188, 255, 0.14);
    background: rgba(5, 17, 32, 0.8);
    box-shadow: none;
  }
  :deep(.el-radio-button__inner) {
    min-height: 42px;
    padding-top: 13px;
    color: #8da9bf;
    border: 0;
    background: transparent;
    box-shadow: none;
  }
  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    color: #e9f8ff;
    background: rgba(57, 139, 213, 0.34);
    box-shadow: none;
  }
  :deep(.el-input__inner) { color: var(--research-text); }
}

.research-console.is-compact {
  grid-template-columns: minmax(240px, 0.72fr) minmax(190px, 0.45fr) auto minmax(260px, 1fr);
  gap: 10px;
  align-items: center;
  padding: 11px 12px;
  border-color: rgba(93, 190, 255, 0.12);
  border-radius: 14px;
  box-shadow: none;

  label {
    margin-bottom: 5px;
    font-size: 12px;
  }

  :deep(.el-input__wrapper),
  :deep(.el-radio-group) {
    min-height: 36px;
  }

  :deep(.el-input__inner) {
    font-size: 14px;
  }

  :deep(.el-radio-button__inner) {
    min-height: 34px;
    padding: 9px 12px 0;
    font-size: 12px;
  }

  .run-button {
    min-width: 142px;
    height: 36px;
    box-shadow: none;
  }
}

.console-lens-summary {
  min-width: 0;
  padding: 0 4px;

  span,
  strong {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    margin-bottom: 4px;
    color: var(--research-muted);
    font-size: 12px;
  }

  strong {
    color: #bfe7ff;
    font-size: 13px;
    font-weight: 700;
  }
}

.run-button {
  min-width: 210px;
  height: 46px;
  border: 0;
  background: linear-gradient(120deg, #386dff, #39c9f1);
  font-weight: 700;
  box-shadow: 0 12px 28px rgba(49, 136, 255, 0.28);
}

.lens-panel { margin-top: 18px; }
.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 10px;
  h2 { margin: 5px 0 0; font-size: 18px; }
  > span { color: var(--research-muted); font: 600 12px "SFMono-Regular", Consolas, monospace; }
}

.lens-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(130px, 1fr));
  gap: 10px;
}
.lens-card {
  position: relative;
  display: flex;
  min-height: 122px;
  padding: 15px;
  flex-direction: column;
  align-items: flex-start;
  color: var(--research-muted);
  text-align: left;
  border: 1px solid rgba(112, 168, 209, 0.14);
  border-radius: 14px;
  background: rgba(8, 22, 39, 0.62);
  cursor: pointer;
  transition: 180ms ease;
  &:hover { transform: translateY(-2px); border-color: rgba(77, 217, 255, 0.35); }
  &.active {
    color: var(--research-text);
    border-color: rgba(77, 217, 255, 0.42);
    background: linear-gradient(145deg, rgba(28, 83, 130, 0.48), rgba(8, 27, 48, 0.82));
    box-shadow: inset 0 0 28px rgba(63, 124, 255, 0.08);
  }
  strong { margin: 13px 0 6px; font-size: 14px; }
  small { font-size: 12px; line-height: 1.55; }
}
.lens-index { color: var(--research-cyan); font: 700 11px "SFMono-Regular", Consolas, monospace; }
.lens-state {
  margin-top: auto;
  padding-top: 12px;
  color: #6c879f;
  font: 600 10px "SFMono-Regular", Consolas, monospace;
  letter-spacing: 0.08em;
}
.active .lens-state { color: #59e1d0; }

.research-empty,
.research-loading {
  display: grid;
  min-height: 280px;
  margin-top: 18px;
  place-items: center;
  text-align: center;
  border: 1px dashed rgba(99, 177, 229, 0.19);
  border-radius: 18px;
  background: rgba(5, 17, 31, 0.36);
  h2 { margin: 8px 0; font-size: 20px; }
  p { max-width: 680px; color: var(--research-muted); }
}
.empty-orbit {
  position: relative;
  width: 62px;
  height: 62px;
  border: 1px solid rgba(77, 217, 255, 0.35);
  border-radius: 50%;
  &::after { content: ""; position: absolute; inset: 13px; border: 1px solid rgba(63, 124, 255, 0.5); transform: rotate(35deg); }
  span { position: absolute; top: 5px; right: 8px; width: 7px; height: 7px; border-radius: 50%; background: #4dd9ff; box-shadow: 0 0 12px #4dd9ff; }
}
.empty-principles {
  display: flex;
  gap: 8px;
  span { padding: 7px 10px; border: 1px solid var(--research-line); border-radius: 999px; color: #86a8c3; font-size: 11px; }
}
.research-loading { position: relative; overflow: hidden; }
.scan-line { position: absolute; inset: 0; background: linear-gradient(180deg, transparent, rgba(77, 217, 255, 0.08), transparent); animation: scan 1.8s linear infinite; }
.loading-mark { color: var(--research-cyan); font: 800 30px "SFMono-Regular", Consolas, monospace; text-shadow: 0 0 24px rgba(77, 217, 255, 0.6); }
@keyframes scan { from { transform: translateY(-100%); } to { transform: translateY(100%); } }

.report-command {
  display: grid;
  grid-template-columns: minmax(190px, 0.45fr) minmax(0, 1.65fr) minmax(260px, 0.55fr);
  gap: 14px;
  margin-top: 14px;
  padding: 16px;
  border: 1px solid rgba(77, 217, 255, 0.25);
  border-radius: 18px;
  background: linear-gradient(120deg, rgba(20, 61, 101, 0.72), rgba(8, 31, 53, 0.9));
}
.report-identity {
  span { color: var(--research-cyan); font: 700 11px "SFMono-Regular", Consolas, monospace; }
  h2 { margin: 9px 0 4px; font-size: 17px; }
  strong { color: #8fadd0; font: 700 12px "SFMono-Regular", Consolas, monospace; }
}
.command-conclusion {
  span { color: #ffc76a; font: 700 11px "SFMono-Regular", Consolas, monospace; text-transform: uppercase; }
  h2 { margin: 7px 0; max-width: 920px; font-size: 20px; line-height: 1.32; }
  p { max-width: 920px; margin: 0; color: #a7bfd3; font-size: 15.5px; line-height: 1.65; }
}
.report-basis { margin-top: 6px; color: #91b5d0; font-size: 12px; }
.report-basis summary { width: fit-content; cursor: pointer; color: #75cfff; }
.report-basis p { margin-top: 8px; }
.report-caveat { display: block; margin-top: 7px; color: #82a0bb; font-size: 11px; line-height: 1.45; }
.conclusion-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-why-now {
  display: block;
  margin-top: 8px;
  max-width: 920px;
  color: #75abc6;
  font-size: 13px;
  line-height: 1.55;
}
.command-scores {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  align-items: stretch;
  > div { display: grid; padding: 8px; place-content: center; text-align: center; border-left: 1px solid rgba(93, 190, 255, 0.12); }
  span { color: var(--research-muted); font-size: 11px; }
  strong { margin-top: 4px; color: #dff8ff; font: 800 20px "SFMono-Regular", Consolas, monospace; }
}

.report-grid,
.evidence-grid {
  display: grid;
  max-width: 1540px;
  margin: 12px auto 0;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.report-actions {
  margin-top: 12px;
}

.terminal-card {
  border: 1px solid rgba(93, 190, 255, 0.13);
  border-radius: 16px;
  background: var(--research-panel);
  overflow: hidden;
  > header { display: flex; min-height: 38px; padding: 0 14px; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(93, 190, 255, 0.12); color: #69dffc; font: 700 10px "SFMono-Regular", Consolas, monospace; letter-spacing: 0.09em; }
  > footer { padding: 9px 14px; border-top: 1px solid rgba(93, 190, 255, 0.12); color: #6e8aa2; font-size: 11px; }
}
.position-metrics,
.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 15px;
  > div { padding: 3px 13px; border-left: 1px solid rgba(93, 190, 255, 0.12); &:first-child { border-left: 0; } }
  span { display: block; margin-bottom: 7px; color: var(--research-muted); font-size: 12px; }
  strong { font: 700 18px "SFMono-Regular", Consolas, monospace; }
}
.snapshot-grid { grid-template-columns: repeat(4, 1fr); }
.account-strip { display: flex; gap: 8px; padding: 0 16px 14px; flex-wrap: wrap; span { padding: 6px 8px; border-radius: 6px; background: rgba(80, 151, 210, 0.1); color: #91b2cb; font-size: 12px; } }
.positive { color: #ff6873 !important; }
.negative { color: #43ce83 !important; }
.neutral { color: #a8bdcf !important; }

.lens-results { margin-top: 12px; }
.readout-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  article { display: grid; min-height: 92px; padding: 15px 16px; grid-template-columns: 34px 1fr; gap: 10px; border-bottom: 1px solid rgba(93, 190, 255, 0.11); &:nth-child(odd) { border-right: 1px solid rgba(93, 190, 255, 0.11); } }
  > article > span { color: #4dd9ff; font: 700 10px "SFMono-Regular", Consolas, monospace; }
  h3 { margin: 0 0 6px; font-size: 15px; }
  p { max-width: 680px; margin: 0; color: #94aec4; font-size: 15px; line-height: 1.62; }
}

.evidence-details {
  margin-top: 12px;
}

.evidence-details summary {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 14px;
  border-bottom: 1px solid transparent;
  color: #69dffc;
  font: 700 10px "SFMono-Regular", Consolas, monospace;
  letter-spacing: 0.09em;
  cursor: pointer;
  list-style: none;
}

.evidence-details summary::-webkit-details-marker {
  display: none;
}

.evidence-details summary::after {
  content: attr(data-collapsed-label);
  color: #8aa8c2;
  font-size: 11px;
  letter-spacing: 0;
}

.evidence-details[open] summary {
  border-bottom-color: rgba(93, 190, 255, 0.12);
}

.evidence-details[open] summary::after {
  content: attr(data-expanded-label);
}

.evidence-details summary small {
  margin-left: auto;
  color: #7894ae;
  font-size: 11px;
  letter-spacing: 0;
}

.evidence-list {
  max-height: 560px;
  overflow: auto;
  > div { display: grid; padding: 12px 14px; grid-template-columns: 52px 1fr; gap: 12px; border-bottom: 1px solid rgba(93, 190, 255, 0.1); }
  strong { font-size: 14px; }
  p { max-width: 940px; margin: 5px 0; color: #91aabf; font-size: 14px; line-height: 1.55; }
  small { color: #59758d; font: 11px "SFMono-Regular", Consolas, monospace; }
}
.quality { height: fit-content; padding: 4px 5px; border-radius: 4px; color: #9eb5c6; text-align: center; font: 700 9px "SFMono-Regular", Consolas, monospace; background: rgba(130, 157, 179, 0.12); &.high { color: #4ce4bd; background: rgba(46, 207, 163, 0.12); } &.low { color: #ff9a88; background: rgba(255, 113, 103, 0.12); } }
.action-card ol { margin: 0; padding: 14px 18px 6px 38px; li { padding: 0 0 10px 4px; color: #b3c7d9; font-size: 15px; line-height: 1.55; } }
.gap-box { display: grid; gap: 7px; margin: 8px 16px 16px; padding: 13px; border: 1px solid rgba(255, 178, 93, 0.19); border-radius: 9px; background: rgba(255, 157, 70, 0.05); strong { color: #ffc17a; font-size: 11px; } span { color: #9fb2c1; font-size: 11px; } }
.muted { padding: 18px; color: var(--research-muted); }
.report-disclaimer { max-width: 920px; margin: 14px auto 0; color: #607b92; font-size: 12px; line-height: 1.55; text-align: center; }

@media (max-width: 1100px) {
  .lens-grid { grid-template-columns: repeat(3, 1fr); }
  .research-console.is-compact {
    grid-template-columns: minmax(240px, 1fr) minmax(190px, 0.7fr) auto;
  }
  .console-lens-summary {
    grid-column: 1 / -1;
  }
  .report-command { grid-template-columns: 1fr; }
  .command-scores > div:first-child { border-left: 0; }
}
@media (max-width: 760px) {
  .research-page { padding: 16px; }
  .research-hero { align-items: flex-start; flex-direction: column; }
  .framework-badge { width: 100%; box-sizing: border-box; }
  .research-console,
  .research-console.is-compact { grid-template-columns: 1fr; }
  .console-lens-summary { grid-column: auto; }
  .run-button { width: 100%; }
  .lens-grid { grid-template-columns: repeat(2, 1fr); }
  .report-grid, .evidence-grid { grid-template-columns: 1fr; }
  .readout-list { grid-template-columns: 1fr; article:nth-child(odd) { border-right: 0; } }
  .position-metrics, .snapshot-grid { grid-template-columns: repeat(2, 1fr); > div:nth-child(odd) { border-left: 0; } }
  .empty-principles { flex-direction: column; }
}
</style>

<style scoped>.research-page{min-width:0}.material-card{padding:16px 0;border-bottom:1px solid rgba(112,202,255,.15);overflow-wrap:anywhere}.material-card p{color:#a5bad3;line-height:1.7}.material-content{white-space:pre-wrap}.research-console{grid-template-columns:minmax(0,1fr) auto auto}.section-heading h2{overflow-wrap:anywhere}@media(max-width:700px){.research-page{padding:16px}.research-console{grid-template-columns:1fr}.section-heading{flex-wrap:wrap}}</style>

<style scoped>.report-links{display:flex;gap:12px;flex-wrap:wrap}.quote-reference{padding-top:12px}.snapshot-grid small{display:block;overflow-wrap:anywhere;color:#a5bad3}.command-scores strong{font-size:18px}.position-metrics{margin-bottom:16px}.command-conclusion p{overflow-wrap:anywhere}</style>

<style scoped>.command-scores .date-metric{font-size:12px;white-space:nowrap;letter-spacing:0}</style>

<style scoped>.command-conclusion{overflow-wrap:anywhere;min-width:0}.command-conclusion pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>

<style scoped>.load-feedback{margin:10px 0 0;padding:10px 14px;border:1px solid rgba(77,217,255,.3);border-radius:10px;background:rgba(20,67,93,.55);color:#c5f1ff;line-height:1.55;overflow-wrap:anywhere}</style>
