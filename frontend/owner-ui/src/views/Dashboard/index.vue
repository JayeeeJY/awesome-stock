<template>
  <div class="dashboard-page">
    <AppDataState v-if="store.error" :tone="store.workspace?'stale':'error'" title="驾驶舱暂未更新" :description="store.error" action-label="重新加载" @action="store.load" />
    <section class="dashboard-summary" v-loading="store.loading"><TodayStatusBar :state="state" :title="title" :detail="detail" :metrics="metrics" :loading="store.loading" :privacy="privacy" /><div class="summary-actions"><el-button type="primary" size="small" @click="router.push('/portfolio')">查看持仓</el-button><el-button size="small" text @click="app.togglePrivacyMode()">{{ privacy?'显示金额':'隐藏金额' }}</el-button><el-button size="small" :loading="store.loading" @click="store.load">刷新</el-button><details v-if="store.workspace" class="summary-more"><summary>基线与口径</summary><div class="summary-more-content"><el-button size="small" :loading="saving" :disabled="store.loading||!!store.error" @click="saveBaseline">保存检查基线</el-button><p class="valuation-note">汇总按记录汇率折算 USD，不含历史汇兑收益。今日估值变化为当前数量×所属市场当日报价（美股按UTC保守校验）与同源昨收之差，不含日内成交、费用和分红。<router-link to="/portfolio/accounts">查看汇率依据</router-link></p></div></details></div></section>
    <p v-if="store.workspace&&!baseCurrent" class="valuation-stale" role="status">评估日已变化，请刷新后核对价格与汇率。</p>
    <TodayChangesPanel :items="changes" :baseline="store.workspace?.baseline?.updated_at?new Date(store.workspace.baseline.updated_at).toLocaleString('zh-CN'):''" :loading="store.loading" :privacy="privacy" @open="router.push('/portfolio/cash')" />
    <TodayActionSummary :items="store.pendingActions" :loading="store.loading" @open="store.inboxOpen=true" />
    <el-card class="panel-card holdings-panel" shadow="never"><template #header><div class="card-head"><div><div class="card-title">核心持仓</div><div class="card-subtitle">{{ positionValueComplete?'只展示美元市值最大的四项，为今天的判断提供必要上下文。':'估值资料未齐，暂按代码显示持仓；补齐后按美元市值排序。' }}</div></div><el-button link type="primary" @click="router.push('/portfolio')">全部持仓</el-button></div></template>
      <div v-if="positions.length" class="position-list"><button v-for="p in corePositions" :key="p.key" type="button" class="position-row" @click="router.push('/portfolio')"><div class="position-main"><div class="position-ticker-row"><strong>{{ p.symbol }}</strong></div><small>{{ p.account_name }}</small></div><div class="position-side"><strong>{{ privacy?'••••':p.usdValue===null?'—':money(p.usdValue)+' USD' }}</strong><small v-if="privacy">已隐藏</small><small v-else>{{ p.usdValue!==null&&positionValueComplete?`仓位 ${percent(p.usdValue,positionValueTotal)}`:`${p.quantity} 股 · ${p.quote_status==='current_snapshot'?'估值待核':'缺少有效价格'}` }} · 累计 {{ p.returnPct }}</small></div></button></div>
      <div v-else class="portfolio-onboarding"><div class="onboarding-orb">AS</div><div class="onboarding-copy"><strong>建立你的投资事实底座</strong><p>先建立资金账户，再录入已经发生的成交。</p></div><div class="onboarding-steps"><button type="button" @click="router.push('/portfolio/accounts')"><span>01</span><b>资金账户</b><small>分开管理不同币种</small></button><button type="button" @click="router.push('/portfolio/trades')"><span>02</span><b>交易流水</b><small>记录实际成交</small></button><button type="button" @click="router.push('/research')"><span>03</span><b>研究依据</b><small>保存论点与证据</small></button></div></div>
    </el-card>
    <section class="context-section"><button class="context-toggle" type="button" :aria-expanded="contextExpanded" aria-controls="today-secondary-context" @click="contextExpanded=!contextExpanded"><span class="context-icon"><el-icon><TrendCharts/></el-icon></span><span class="context-copy"><b>趋势与账户上下文</b><small>账户原币事实与固定快照分开查看，需要时再展开。</small></span><span v-if="accounts.length" class="context-summary"><span class="context-pill"><b>账户</b><strong>{{ accounts.length }}</strong></span><span class="context-pill"><b>持仓</b><strong>{{ positions.length }}</strong></span></span><span class="context-state">{{ contextExpanded?'收起':'展开上下文' }}<el-icon :class="{'is-open':contextExpanded}"><ArrowRight/></el-icon></span></button><div v-if="contextExpanded" id="today-secondary-context" class="context-panel"><p>当前账户资产按各自原币展示；跨币种总额使用上方有来源的 USD 估值。</p><div v-if="accounts.length" class="context-accounts"><article v-for="account in accounts" :key="account.id"><strong>{{ account.name }} · {{ account.currency }}</strong><span>{{ privacy?'••••':money(baseCurrent&&account.valuation_complete?account.estimated_assets:null)+' '+account.currency }}</span><small>{{ account.positions.length }} 个持仓 · {{ !baseCurrent?'评估日已变化':account.valuation_complete?'估值完整':'价格资料待补' }}</small></article></div><p v-else>建立账户并保存事实快照后，这里会出现可核对的账户上下文。</p><router-link to="/review/diagnosis">查看固定快照趋势与诊断来源</router-link></div></section>
  </div>
</template>
<script setup lang="ts">
import {valuationIsCurrent} from '@/utils/valuationDate'
import {registerPageMaterial} from '@/api/pageMaterial'
import {computed,onMounted,onBeforeUnmount,ref} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage} from 'element-plus'
import {ArrowRight,TrendCharts} from '@element-plus/icons-vue'
import AppDataState from '@/components/Global/AppDataState.vue'
import TodayStatusBar from '@/components/Dashboard/TodayStatusBar.vue'
import TodayChangesPanel from '@/components/Dashboard/TodayChangesPanel.vue'
import TodayActionSummary from '@/components/Dashboard/TodayActionSummary.vue'
import {useBusinessStore} from '@/stores/business'
import {useAppStore} from '@/stores/app'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
import {money,sum,compare,percent,negate} from '@/utils/decimal'
const store=useBusinessStore(),app=useAppStore(),router=useRouter(),privacy=computed(()=>app.privacyMode),saving=ref(false),contextExpanded=ref(false),operations=operationCache()
let baselineId='',dayTimer:ReturnType<typeof setInterval>|undefined
const clockNow=ref(Date.now()),refreshDay=()=>{clockNow.value=Date.now()}
const baseCurrent=computed(()=>valuationIsCurrent(store.workspace?.base_valuation,clockNow.value))
const converted=computed(()=>baseCurrent.value?store.workspace?.base_valuation.accounts||[]:[])
const valuationComplete=computed(()=>baseCurrent.value&&converted.value.length===accounts.value.length&&converted.value.every(a=>a.assets_value_usd!==null))
const accounts=computed(()=>store.workspace?.accounts||[])
const positions=computed(()=>accounts.value.flatMap(a=>a.positions.map(p=>({...p,key:a.id+':'+p.symbol,account_name:a.name,currency:a.currency}))).sort((a,b)=>a.symbol.localeCompare(b.symbol)))
const valuedPositions=computed(()=>positions.value.map(p=>({...p,usdValue:baseCurrent.value?converted.value.find(a=>a.account_id===p.key.split(':')[0])?.positions.find(v=>v.symbol===p.symbol)?.market_value_usd??null:null,
  returnPct:!baseCurrent.value||p.quote_status!=='current_snapshot'||p.unrealized_pnl===null||compare(p.open_cost,'0')<=0?'—':`${compare(sum([p.realized_pnl,p.unrealized_pnl]),'0')>0?'+':''}${percent(sum([p.realized_pnl,p.unrealized_pnl]),p.open_cost)}`})))
const positionValueComplete=computed(()=>valuedPositions.value.length>0&&valuedPositions.value.every(p=>p.usdValue!==null))
const positionValueTotal=computed(()=>positionValueComplete.value?sum(valuedPositions.value.map(p=>p.usdValue!)):'0')
const corePositions=computed(()=>[...valuedPositions.value].sort((a,b)=>positionValueComplete.value?compare(b.usdValue!,a.usdValue!)||a.symbol.localeCompare(b.symbol):a.symbol.localeCompare(b.symbol)).slice(0,4))
const state=computed(()=>store.error?'data_issue':!accounts.value.length?'setup':store.pendingActions.length?'review':!valuationComplete.value?'data_issue':'clear')
const title=computed(()=>store.loading&&!store.workspace?'正在读取组合状态':store.error?'驾驶舱暂时无法更新':!accounts.value.length?'先建立你的投资账本':store.pendingActions.length?'有到期记录需要复核':!valuationComplete.value?'先补齐价格、汇率或刷新数据':'账本已更新，继续按计划检查')
const detail=computed(()=>store.error?store.error:!store.workspace?'尚未取得账本':`${accounts.value.length} 个资金账户 · ${positions.value.length} 个持仓 · ${positions.value.filter(p=>p.quote_status==='current_snapshot').length} 个有效价格快照`)
const metrics=computed(()=>{
 const total=(key:'day_price_effect_usd'|'assets_value_usd'|'cash_usd'|'realized_at_current_fx_usd'|'unrealized_at_current_fx_usd')=>baseCurrent.value&&converted.value.length===accounts.value.length&&converted.value.every(a=>a[key]!==null)?sum(converted.value.map(a=>a[key]!)):null
 const tone=(value:string|null)=>value===null||compare(value,'0')===0?'is-neutral':compare(value,'0')>0?'is-positive':'is-negative'
 const assets=total('assets_value_usd'),cash=total('cash_usd'),realized=total('realized_at_current_fx_usd'),unrealized=total('unrealized_at_current_fx_usd'),pnl=realized!==null&&unrealized!==null?sum([realized,unrealized]):null
 return [{label:'总资产',value:money(assets),meta:assets===null?'缺少有效价格或汇率':'USD · 含现金'},{label:'今日估值变化',value:money(total('day_price_effect_usd')),meta:'USD · 当前持仓×当日价差',tone:tone(total('day_price_effect_usd'))},{label:'累计盈亏',value:money(pnl),meta:'USD · 当前汇率折算',tone:tone(pnl)},{label:'当前仓位',value:assets!==null&&cash!==null?percent(sum([assets,negate(cash)]),assets):'—',meta:'当前持仓市值占比'},{label:'现金比例',value:assets!==null&&cash!==null?percent(cash,assets):'—',meta:'来自已记录现金'},{label:'待复核',value:String(store.pendingActions.length),meta:'已到用户设置日期'}]
})
const changes=computed(()=>store.workspace?.changes.filter(c=>c.status!=='compared'||compare(c.cash_change||'0','0')!==0||compare(c.cost_change||'0','0')!==0||c.quantities.some(q=>compare(q.change,'0')!==0)).map(c=>({id:c.account_id,title:c.account_name+' · '+c.currency,detail:c.status!=='compared'?'账户新增或移除':`现金变化 ${money(c.cash_change)}；成本变化 ${money(c.cost_change)}；${c.quantities.filter(q=>compare(q.change,'0')!==0).map(q=>q.symbol+' '+q.change+' 股').join('、')||'持仓数量未变化'}`}))||[])
const unregisterMaterial=registerPageMaterial('/cockpit',()=>{
  refreshDay()
  if(privacy.value)throw Error('金额处于隐藏状态；如需载入驾驶舱材料，请先主动显示金额。')
  if(!baseCurrent.value||store.loading||saving.value||store.error||!store.workspace||store.loadedAt.slice(0,10)!==new Date().toISOString().slice(0,10))throw Error('请先刷新驾驶舱，再载入材料。')
  return {scope:'cockpit_display_snapshot',loaded_at:store.loadedAt,state:state.value,title:title.value,detail:detail.value,
    metrics:metrics.value,base_valuation:{evaluated_on:store.workspace.base_valuation.evaluated_on,evaluated_market_dates:store.workspace.base_valuation.evaluated_market_dates,base_currency:'USD',return_basis:store.workspace.base_valuation.return_basis,accounts:converted.value.map(({positions:_,...a})=>a)},changes:changes.value,baseline_at:store.workspace.baseline?.updated_at??null,
    pending_actions:store.pendingActions,positions_preview:positions.value.slice(0,4),
    notice:'当前驾驶舱摘要，持仓速览仅前四项，不是完整持仓清单。指标缺失保留为缺失；汇总按已记录的有效汇率折算USD，不含历史汇兑收益；原币持仓行不直接合计，估值变化不含日内成交/费用/分红。不含全账户逐笔成交或研究文档。'}
})
onBeforeUnmount(unregisterMaterial)
async function saveBaseline(){if(saving.value||store.loading||store.error||!store.workspace)return;saving.value=true;baselineId ||= crypto.randomUUID();try{await request('/api/v1/owner/business','POST',operations.body('baseline',{id:baselineId,revision:0,kind:'baseline',data:{title:'手动检查基线'}}));baselineId='';operations.clear();await store.load();if(store.error)ElMessage.warning('检查基线已保存，但驾驶舱重新读取失败。请刷新确认，避免重复保存。');else ElMessage.success('检查基线已保存')}catch(e){ElMessage.error(e instanceof Error?e.message:'保存失败')}finally{saving.value=false}}
onMounted(()=>{store.load();dayTimer=setInterval(refreshDay,1000);window.addEventListener('focus',refreshDay);document.addEventListener('visibilitychange',refreshDay)})
onBeforeUnmount(()=>{if(dayTimer)clearInterval(dayTimer);window.removeEventListener('focus',refreshDay);document.removeEventListener('visibilitychange',refreshDay)})
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dashboard-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  padding: 0 2px;
}
.summary-more{position:relative;color:#90c9e9;font-size:12px}.summary-more summary{display:flex;align-items:center;min-height:24px;padding:0 7px;border:1px solid rgba(112,202,255,.18);border-radius:999px;background:rgba(112,202,255,.055);cursor:pointer;list-style:none}.summary-more summary::-webkit-details-marker{display:none}.summary-more summary:focus-visible{outline:2px solid #6cdfff;outline-offset:2px}.summary-more-content{position:absolute;z-index:20;right:0;top:calc(100% + 7px);width:min(420px,calc(100vw - 28px));display:grid;justify-items:start;gap:10px;padding:14px;border:1px solid #3b5a78;border-radius:12px;background:#0d213a;box-shadow:0 12px 30px rgba(0,6,18,.4)}

.panel-card {
  border: 1px solid rgba(112, 202, 255, 0.12);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(12, 27, 52, 0.88), rgba(9, 20, 39, 0.84));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.panel-card :deep(.el-card__header) {
  padding: 13px 16px 10px;
  border-bottom-color: rgba(255, 255, 255, 0.06);
}

.panel-card :deep(.el-card__body) {
  padding: 10px 16px 14px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.card-title {
  color: #eaf5ff;
  font-size: 15px;
  font-weight: 800;
}

.card-subtitle {
  margin-top: 4px;
  color: #879fbd;
  font-size: 12px;
  line-height: 1.45;
}

.position-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.position-row {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 12px;
  border: 1px solid rgba(112, 202, 255, 0.09);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.025);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: 160ms ease;
}

.position-row:hover,
.position-row:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(112, 202, 255, 0.26);
  background: rgba(85, 194, 255, 0.06);
  outline: none;
}

.position-main,
.position-side {
  min-width: 0;
}

.position-ticker-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.position-ticker-row strong,
.position-side strong {
  color: #edf7ff;
  font: 750 13px/1.2 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.position-ticker-row span {
  color: #78d3ff;
  font: 700 10px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.position-main small,
.position-side small {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: #849cb9;
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.position-side {
  flex: 0 0 260px;
  text-align: right;
}

.is-positive { color: #ff7886 !important; }
.is-negative { color: #48d8a1 !important; }
.is-neutral { color: #7e94ae !important; }

.portfolio-onboarding {
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) minmax(420px, 1.8fr);
  align-items: center;
  gap: 16px;
}

.onboarding-orb {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid rgba(112, 202, 255, 0.24);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(75, 109, 255, 0.34), rgba(91, 212, 255, 0.2));
  color: #dff7ff;
  font: 800 15px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.onboarding-copy strong {
  color: #edf7ff;
  font-size: 14px;
}

.onboarding-copy p {
  margin: 5px 0 0;
  color: #849cb9;
  font-size: 11px;
  line-height: 1.5;
}

.onboarding-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

.onboarding-steps button {
  min-height: 76px;
  padding: 10px;
  border: 1px solid rgba(112, 202, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.025);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.onboarding-steps span,
.onboarding-steps b,
.onboarding-steps small {
  display: block;
}

.onboarding-steps span { color: #72d1ff; font-size: 9px; font-weight: 800; }
.onboarding-steps b { margin-top: 7px; color: #e7f3ff; font-size: 11px; }
.onboarding-steps small { margin-top: 4px; color: #7890ac; font-size: 9px; line-height: 1.35; }

.context-section {
  overflow: hidden;
  border: 1px solid rgba(112, 202, 255, 0.1);
  border-radius: 18px;
  background: rgba(8, 20, 39, 0.56);
}

.context-toggle {
  display: grid;
  width: 100%;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 13px;
  padding: 10px 14px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.context-toggle:hover,
.context-toggle:focus-visible {
  background: rgba(85, 194, 255, 0.045);
  outline: none;
}

.context-icon {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgba(112, 202, 255, 0.16);
  border-radius: 11px;
  background: rgba(85, 194, 255, 0.07);
  color: #75d2ff;
}

.context-copy b,
.context-copy small {
  display: block;
}

.context-copy b { color: #dcecff; font-size: 13px; }
.context-copy small { margin-top: 3px; color: #7f97b4; font-size: 11px; line-height: 1.4; }

.context-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}

.context-pill {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  gap: 7px;
  padding: 0 9px;
  border: 1px solid rgba(112, 202, 255, 0.1);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.024);
}

.context-pill b {
  color: #7087a3;
  font-size: 10px;
  font-weight: 700;
}

.context-pill strong {
  color: #dcecff;
  font: 760 11px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.context-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #91b9d8;
  font-size: 11px;
  font-weight: 700;
}

.context-state .el-icon { transition: transform 160ms ease; }
.context-state .el-icon.is-open { transform: rotate(90deg); }

.context-panel {
  padding: 0 12px 12px;
}

.context-panel p { color: #8ea6c4; font-size: 12px; line-height: 1.6; }
.context-panel a { color: #75d5ff; font-size: 12px; }
.context-accounts { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin: 10px 0 16px; }
.context-accounts article { display: flex; flex-direction: column; gap: 6px; padding: 12px; border: 1px solid rgba(112, 202, 255, 0.1); border-radius: 12px; background: rgba(255, 255, 255, 0.025); }
.context-accounts strong { color: #dcecff; font-size: 12px; }
.context-accounts span { color: #eaf5ff; font-size: 16px; font-weight: 750; }
.context-accounts small { color: #7f97b4; font-size: 11px; }

@media (max-width: 900px) {
  .position-list { grid-template-columns: 1fr; }
  .portfolio-onboarding { grid-template-columns: auto 1fr; }
  .onboarding-steps { grid-column: 1 / -1; }
}

@media (max-width: 560px) {
  .dashboard-page { gap: 14px; }
  .summary-actions { justify-content: flex-start; }
  .summary-actions :deep(.el-button) { margin-left: 0; }
  .panel-card { border-radius: 16px; }
  .panel-card :deep(.el-card__header) { padding: 14px 15px 11px; }
  .panel-card :deep(.el-card__body) { padding: 11px 15px 15px; }
  .card-head { align-items: flex-start; }
  .position-row { padding: 11px; }
  .portfolio-onboarding { display: flex; flex-direction: column; align-items: stretch; }
  .onboarding-orb { margin: 0 auto; }
  .onboarding-copy { text-align: center; }
  .onboarding-steps { grid-template-columns: 1fr; }
  .onboarding-steps button { min-height: 68px; }
  .context-toggle { grid-template-columns: auto minmax(0, 1fr); }
  .context-summary { grid-column: 1 / -1; justify-content: flex-start; }
  .context-state { grid-column: 1 / -1; justify-content: flex-end; }
}
</style>

<style scoped>.valuation-note{margin:0;color:#a5bad3;font-size:12px;line-height:1.6}.valuation-note a{color:#75d5ff}.valuation-stale{margin:0;color:var(--el-color-warning);font-size:12px;line-height:1.6}</style>
