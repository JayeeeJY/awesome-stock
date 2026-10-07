<template>
  <div class="overview-page">
    <PortfolioOverviewHeader title="持仓总览" subtitle="在资本、风险与研究三种视角中查看同一份持仓事实。" />
    <section v-if="workspace" class="portfolio-summary-dashboard" aria-label="Portfolio Summary">
      <article v-for="item in summary" :key="item.label" class="portfolio-summary-metric" :class="`is-${item.tone || 'neutral'}`"><span class="portfolio-summary-label">{{ item.label }}</span><strong class="portfolio-summary-value mono-value">{{ item.value }}</strong><small class="portfolio-summary-meta">{{ item.meta }}</small></article>
    </section>
    <p v-if="workspace&&!baseCurrent" class="valuation-stale">评估日已变化，请刷新后查看当前估值。</p>
    <AppDataState v-if="error" :tone="workspace?'stale':'error'" title="持仓数据暂未更新" :description="error" action-label="重新加载" compact @action="load" />
    <AppDataState v-else-if="!workspace && loading" tone="loading" title="正在读取持仓" description="汇总账户、成交与价格快照。" compact />
    <section class="command-center">
      <div class="command-table-shell" v-loading="loading">
        <div class="command-table-topline"><div class="command-table-copy"><span class="command-kicker">PORTFOLIO LEDGER</span><strong>持仓明细</strong><small>{{ rows.length }} 个账户持仓 · 原币展示 · USD 排序</small></div>
          <div class="command-table-controls">
            <el-input v-model="search" class="command-control is-search" placeholder="搜索标的" aria-label="搜索标的" clearable />
            <el-select v-model="accountId" class="command-control" aria-label="账户范围" placeholder="全部账户" clearable><el-option v-for="account in workspace?.accounts || []" :key="account.id" :label="account.name+' · '+account.currency" :value="account.id" /></el-select>
            <el-select v-model="currency" class="command-control" aria-label="币种范围" placeholder="全部币种" clearable><el-option v-for="item in currencies" :key="item" :label="item" :value="item" /></el-select>
            <el-select v-model="sort" class="command-control is-sort" aria-label="持仓排序"><el-option label="按标的" value="symbol" /><el-option label="按市值" value="value" /><el-option label="按收益" value="return" /></el-select>
            <button class="command-tool-button is-icon" type="button" aria-label="刷新持仓" @click="load"><el-icon><Refresh /></el-icon></button>
            <el-dropdown trigger="click" @command="manage"><button class="command-tool-button is-icon" type="button" aria-label="管理持仓"><el-icon><MoreFilled /></el-icon></button><template #dropdown><el-dropdown-menu><el-dropdown-item command="accounts">账户管理</el-dropdown-item><el-dropdown-item command="trades">交易流水</el-dropdown-item><el-dropdown-item command="cash">资金流水</el-dropdown-item><el-dropdown-item command="quote">记录价格快照</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
          </div>
        </div>
        <div class="command-rows-scroll" tabindex="0" aria-label="横向滚动持仓表"><div class="command-grid command-table-header" role="row"><span v-for="(label,index) in ['标的','价格快照','持仓','平均成本','收益','今日估值变化','账户','操作']" :key="label" class="command-sort-head" :class="{'is-right':(index>=1&&index<=5)||index===7}">{{ label }}</span></div>
        <div v-for="row in rows" :key="row.key" class="command-grid command-row" role="button" tabindex="0" :aria-label="`查看 ${row.symbol} · ${row.account_name}`" @click="open(row)" @keydown.enter.prevent="open(row)" @keydown.space.prevent="open(row)">
          <div class="command-symbol-cell"><span class="command-avatar">{{ row.symbol.slice(0,2) }}</span><span class="command-symbol-copy"><strong>{{ row.symbol }}</strong><small v-if="companyLabel(row)" :title="`${companyLabel(row)?.name} · ${companyLabel(row)?.source} · ${companyLabel(row)?.retrieved_at} · 供应商资料未核验`">{{ companyLabel(row)?.name }} · 未核验</small><small v-else>{{ row.currency }} · 名称待补</small></span></div>
          <div class="command-number-cell is-right"><strong class="mono-value command-price-main">{{ money(row.quote?.price,4) }}</strong><small v-if="dayChangeRate(row)" :class="tone(row.day_price_effect)" title="所属市场当日报价与同源昨收比较">{{ dayChangeRate(row) }}</small><small v-else>{{ quoteStatus(row) }}{{ row.quote_status==='current_snapshot'?(row.quote?.previous_close?' · 非当日快照':' · 缺同源昨收'):'' }}</small></div>
          <div class="command-number-cell is-right"><strong class="mono-value">{{ row.quantity }} 股</strong><small class="mono-value">{{ money(row.market_value) }} {{ row.currency }}</small></div>
          <div class="command-number-cell is-right"><strong class="mono-value">{{ money(divide(row.open_cost,row.quantity),4) }}</strong><small class="mono-value is-muted">成本 {{ money(row.open_cost) }}</small></div>
          <div class="command-number-cell is-right command-return-cell"><div class="command-return-main"><strong class="mono-value" :class="tone(totalReturn(row))">{{ money(totalReturn(row)) }}</strong><span v-if="floatingReturnRate(row)" :class="tone(row.unrealized_pnl)">浮动 {{ floatingReturnRate(row) }}</span></div><em :title="`浮盈 ${money(row.unrealized_pnl)} · 已实现 ${money(row.realized_pnl)}`">浮盈 {{ money(row.unrealized_pnl) }} · 已实现 {{ money(row.realized_pnl) }}</em></div>
          <div class="command-number-cell is-right"><strong class="mono-value">{{ money(baseCurrent?row.day_price_effect:null) }}</strong><small title="当前数量 × 报价日价差">当前数量 × 报价日价差</small></div>
          <div class="command-account-cell"><span :title="row.account_name">{{ row.account_name }}</span><small>{{ row.currency }}</small></div>
          <div class="command-actions-cell"><button class="command-more-button" type="button" aria-label="持仓详情" @click.stop="open(row)"><el-icon><MoreFilled /></el-icon></button></div>
        </div>
        </div>
        <AppDataState v-if="workspace && !rows.length" class="command-empty-state" tone="empty" title="当前范围没有持仓" description="调整筛选，或先建立账户并录入实际成交。" action-label="录入交易" compact @action="router.push('/portfolio/trades')" />
      </div>
    </section>
    <section v-if="rows.length" class="distribution-section">
      <button type="button" class="distribution-toggle" :aria-expanded="distributionOpen" aria-controls="portfolio-distribution" @click="toggleDistribution">
        <span><small>DISTRIBUTION MAP</small><strong>结构分布</strong><em>从持仓集中度和账户分散度看组合结构，而不只看单行数据。</em></span>
        <b>{{ distributionOpen?'收起图表':'展开图表' }}</b>
      </button>
      <div v-if="distributionOpen" id="portfolio-distribution" class="distribution-grid">
        <article><small>POSITION MIX</small><strong>持仓占比</strong><p v-if="!structureComplete">价格或汇率资料不完整，暂不计算跨币种占比。</p><template v-else><div v-for="item in positionStructure" :key="item.key" class="distribution-item"><span>{{ item.label }}</span><b>{{ item.share }}</b><div class="distribution-track"><i :style="{width:item.share}" /></div></div></template></article>
        <article><small>ACCOUNT MIX</small><strong>账户分布</strong><p v-if="!structureComplete">价格或汇率资料不完整，暂不计算账户占比。</p><template v-else><div v-for="item in accountStructure" :key="item.key" class="distribution-item"><span>{{ item.label }}</span><b>{{ item.share }}</b><div class="distribution-track"><i :style="{width:item.share}" /></div></div></template></article>
        <div class="distribution-history"><AppDataState v-if="snapshotError" tone="error" title="固定快照暂未读取" :description="snapshotError" action-label="重试" compact @action="loadSnapshotHistory"/><AppDataState v-else-if="snapshotLoading" tone="loading" title="正在读取固定快照" description="只读取已保存的事实日报。" compact/><SnapshotHistory v-else :snapshots="dailySnapshots" :disabled="false" @select="openDailySnapshot"/><p class="distribution-history-note">全组合 USD 固定历史；持仓市值不含现金，也不是剔除出入金后的投资回报率。<router-link to="/review/diagnosis">查看事实日报</router-link></p></div>
      </div>
    </section>
    <p v-if="workspace" class="valuation-notice">今日估值变化不含日内成交、费用或分红；仅使用所属市场当日报价（美股按UTC保守校验）与同源昨收。行内涨跌幅也只由同源昨收计算；浮动收益率只按未平仓成本计算，不把已实现收益混入分母。已保存公司名来自供应商资料，仍未人工核验；没有来源时显示待补。汇总与排序使用已记录的美元汇率；收益为当前汇率折算，不含历史汇兑收益。缺少有效价格／汇率的数值不合计，排序置后。{{ baseCurrent ? '' : '评估日已变化，请刷新。' }} <router-link to="/portfolio/accounts">查看汇率依据</router-link></p>
    <el-drawer v-model="drawer" direction="rtl" size="min(540px, 94vw)" :with-header="false" class="position-detail-drawer" aria-label="持仓详情">
      <aside v-if="selected" class="position-drawer-panel">
        <header class="position-drawer-header"><div class="position-drawer-symbol"><span class="command-avatar">{{ selected.symbol.slice(0,2) }}</span><div><strong>{{ selected.symbol }}</strong><small v-if="companyLabel(selected)">{{ companyLabel(selected)?.name }} · 未核验</small><small>{{ selected.account_name }} · {{ selected.currency }}</small></div></div><button type="button" class="position-drawer-close" aria-label="关闭持仓详情" @click="drawer=false">×</button></header>
        <div class="position-drawer-price-line"><div><span>价格快照</span><strong class="mono-value">{{ money(selected.quote?.price,4) }}</strong></div><div class="is-right"><span>当日涨跌</span><strong class="mono-value" :class="tone(selected.day_price_effect)">{{ dayChangeRate(selected)||'—' }}</strong></div></div>
        <p v-if="!baseCurrent" class="position-drawer-note">评估日已变化；刷新前不显示旧估值和收益。</p>
        <div class="position-drawer-metrics"><article v-for="item in positionMetrics" :key="item.label"><span>{{ item.label }}</span><strong class="mono-value">{{ item.value }}</strong><small>{{ item.meta }}</small></article></div>
        <nav class="position-drawer-tabs" aria-label="持仓详情标签"><button v-for="item in [{id:'detail',label:'详情'},{id:'prices',label:'价格记录'},{id:'research',label:'研究依据'},{id:'plan',label:'操作计划'}]" :key="item.id" type="button" :class="{'is-active':tab===item.id}" @click="tab=item.id">{{ item.label }}</button></nav>
        <section v-if="tab==='detail'" class="position-drawer-section"><div class="position-drawer-facts"><div><span>持有数量</span><strong>{{ selected.quantity }}</strong></div><div><span>平均成本</span><strong>{{ money(divide(selected.open_cost,selected.quantity),4) }}</strong></div><div><span>成本余额</span><strong :title="selected.open_cost">{{ money(selected.open_cost) }}</strong></div><div><span>已实现损益</span><strong>{{ money(selected.realized_pnl) }}</strong></div><div><span>价格日期</span><strong>{{ selected.quote?.as_of || '未提供' }}</strong></div><div><span>价格状态</span><strong>{{ quoteStatus(selected) }}</strong></div></div><p class="position-drawer-note">同源昨收：{{ money(selected.quote?.previous_close,4) }}。价格来源：{{ selected.quote?.source || '未提供' }}。价格快照超过三日时，估值与未实现损益不再计算。</p><button class="position-drawer-primary" type="button" @click="editQuote(selected)">记录价格快照</button></section>
        <section v-else-if="tab==='prices'" class="position-drawer-section"><el-table :data="quoteHistory" size="small"><el-table-column prop="as_of" label="价格日期" width="115" /><el-table-column prop="price" label="价格" min-width="100" /><el-table-column prop="previous_close" label="同源昨收" min-width="100" /><el-table-column prop="source" label="来源" min-width="130" /></el-table><p class="position-drawer-note">只展示已保存的同币种价格版本；不将手工快照当作连续行情。</p></section>
        <section v-else-if="tab==='research'" class="position-drawer-section"><p class="position-drawer-note">查看该标的已保存的论点与反方证据。</p><button type="button" class="position-drawer-primary" @click="router.push({path:'/research',query:{symbol:selected.symbol}})">打开研究</button></section>
        <section v-else class="position-drawer-section"><p class="position-drawer-note">计划与成交分别记录，不会自动下单。</p><button type="button" class="position-drawer-primary" @click="router.push({path:'/plan/build-up',query:{symbol:selected.symbol}})">打开计划</button></section>
      </aside>
    </el-drawer>
    <el-dialog v-model="quoteDialog" title="记录价格快照" width="min(520px, calc(100vw - 24px))" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="closeQuote">
      <el-alert v-if="saveError" :title="saveError" type="error" :closable="false" />
      <el-form label-position="top"><el-form-item label="标的代码"><el-input v-model="quote.symbol" :disabled="saving" /></el-form-item><el-form-item label="币种"><el-select v-model="quote.currency" :disabled="saving"><el-option v-for="c in ['USD','HKD','CNY','EUR','GBP','JPY']" :key="c" :value="c" :label="c" /></el-select></el-form-item><el-form-item label="价格"><el-input v-model="quote.price" inputmode="decimal" :disabled="saving" /></el-form-item><el-form-item label="同源昨收（可选）"><el-input v-model="quote.previous_close" inputmode="decimal" :disabled="saving" placeholder="留空时不计算当日估值变化" /></el-form-item><el-form-item label="价格日期"><el-input v-model="quote.as_of" type="date" :disabled="saving" /></el-form-item><el-form-item label="价格来源"><el-input v-model="quote.source" maxlength="300" placeholder="填写可核对的数据来源" :disabled="saving" /></el-form-item></el-form>
      <template #footer><el-button :disabled="saving" @click="closeQuote">取消</el-button><el-button type="primary" :loading="saving" :disabled="loading" @click="saveQuote">保存价格</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {valuationIsCurrent} from '@/utils/valuationDate'
import {registerPageMaterial} from '@/api/pageMaterial'
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { Refresh, MoreFilled } from '@element-plus/icons-vue'
import { ElDrawer, ElMessage, ElMessageBox } from 'element-plus'
import PortfolioOverviewHeader from '@/components/Portfolio/PortfolioOverviewHeader.vue'
import AppDataState from '@/components/Global/AppDataState.vue'
import SnapshotHistory from '@/views/Review/SnapshotHistory.vue'
import { request } from '@/api/owner'
import { getWorkspace, operationCache, type Workspace, type ValuedPosition } from '@/api/business'
import { money, sum, compare, divide, percent, negate } from '@/utils/decimal'
type Row = ValuedPosition & {key:string;account_id:string;account_name:string;currency:string}
type DailyRow = {id:string;kind:string;snapshot_id?:string;[key:string]:unknown}
const loadedAt=ref(''),clockNow=ref(Date.now())
let dayTimer:ReturnType<typeof setInterval>|undefined
const refreshDay=()=>{clockNow.value=Date.now()}
const baseCurrent=computed(()=>valuationIsCurrent(workspace.value?.base_valuation,clockNow.value))
const baseAccounts=computed(()=>baseCurrent.value?workspace.value?.base_valuation.accounts.filter(a=>accounts.value.some(n=>n.id===a.account_id))||[]:[])
const basePosition=(row:Row)=>baseAccounts.value.find(a=>a.account_id===row.account_id)?.positions.find(p=>p.symbol===row.symbol)
const router=useRouter(), workspace=ref<Workspace|null>(null), error=ref(''), loading=ref(false), search=ref(''), accountId=ref(''), currency=ref(''), sort=ref('symbol'), distributionOpen=ref(false)
const drawer=ref(false), selectedKey=ref(''), tab=ref('detail'), quoteDialog=ref(false), saving=ref(false), saveError=ref('')
const dailySnapshots=ref<DailyRow[]>([]),dailyBriefs=ref<DailyRow[]>([]),snapshotLoading=ref(false),snapshotError=ref('')
const quote=reactive({symbol:'',currency:'USD',price:'',previous_close:'',as_of:new Date().toISOString().slice(0,10),source:''}), operations=operationCache()
let quoteId='', quoteBaseline=''
const currencies=computed(()=>[...new Set(workspace.value?.accounts.map(a=>a.currency)||[])])
const accounts=computed(()=>workspace.value?.accounts.filter(a=>(!accountId.value||a.id===accountId.value)&&(!currency.value||a.currency===currency.value))||[])
const scopeCurrency=computed(()=>new Set(accounts.value.map(a=>a.currency)).size===1?accounts.value[0].currency:'')
const allRows=computed<Row[]>(()=>workspace.value?.accounts.flatMap(a=>a.positions.map(p=>({...p,key:a.id+':'+p.symbol,account_id:a.id,account_name:a.name,currency:a.currency})))||[])
const companyLabel=(row:Row)=>workspace.value?.company_sources?.[row.symbol+'|'+row.currency]
const signedPercent=(part:string,whole:string)=>{const value=percent(part,whole);return compare(part,'0')>0?'+'+value:value}
const dayChangeRate=(row:Row)=>{const previous=row.quote?.previous_close;if(!baseCurrent.value||row.day_price_effect===null||row.quote_status!=='current_snapshot'||!row.quote||!previous||compare(previous,'0')<=0)return null;return signedPercent(sum([row.quote.price,negate(previous)]),previous)}
const floatingReturnRate=(row:Row)=>baseCurrent.value&&row.unrealized_pnl!==null&&compare(row.open_cost,'0')>0?signedPercent(row.unrealized_pnl,row.open_cost):null
const totalReturn=(p:ValuedPosition)=>p.unrealized_pnl===null?null:sum([p.realized_pnl,p.unrealized_pnl])
const tone=(value:string|null)=>value===null?'is-muted':compare(value,'0')>=0?'pl-pos':'pl-neg'
const quoteStatus=(p:ValuedPosition)=>({missing:'缺少价格',stale:'价格已过期',current_snapshot:'已记录快照'}[p.quote_status])
const rows=computed(()=>allRows.value.filter(p=>accounts.value.some(a=>a.id===p.account_id)&&(p.symbol.includes(search.value.trim().toUpperCase())||companyLabel(p)?.name.toUpperCase().includes(search.value.trim().toUpperCase()))).sort((a,b)=>{
 if(sort.value==='symbol')return a.symbol.localeCompare(b.symbol)||a.account_name.localeCompare(b.account_name)
 const x=(sort.value==='value'?basePosition(a)?.market_value_usd:basePosition(a)?.total_return_at_current_fx_usd)??null,y=(sort.value==='value'?basePosition(b)?.market_value_usd:basePosition(b)?.total_return_at_current_fx_usd)??null
 return x===null?(y===null?0:1):y===null?-1:compare(y,x)
}))
const structureRows=computed(()=>rows.value.map(row=>({key:row.key,label:row.symbol+' · '+row.account_name,accountId:row.account_id,accountName:row.account_name,value:basePosition(row)?.market_value_usd??null})))
const structureComplete=computed(()=>structureRows.value.length>0&&structureRows.value.every(row=>row.value!==null)&&compare(sum(structureRows.value.map(row=>row.value!)),'0')>0)
const structureTotal=computed(()=>structureComplete.value?sum(structureRows.value.map(row=>row.value!)):'0')
const positionStructure=computed(()=>structureComplete.value?structureRows.value.map(row=>({...row,share:percent(row.value!,structureTotal.value)})).sort((a,b)=>compare(b.value!,a.value!)):[])
const accountStructure=computed(()=>{
 if(!structureComplete.value)return []
 const values=new Map<string,{key:string;label:string;value:string}>()
 for(const row of structureRows.value){const old=values.get(row.accountId);values.set(row.accountId,{key:row.accountId,label:row.accountName,value:old?sum([old.value,row.value!]):row.value!})}
 return [...values.values()].map(item=>({...item,share:percent(item.value,structureTotal.value)})).sort((a,b)=>compare(b.value,a.value))
})
const selected=computed(()=>allRows.value.find(p=>p.key===selectedKey.value)||null)
const summary=computed(()=>{
 const converted=baseAccounts.value
 const direction=(v:string|null)=>v===null||compare(v,'0')===0?'neutral':compare(v,'0')>0?'positive':'negative'
 const total=(key:'day_price_effect_usd'|'assets_value_usd'|'cash_usd'|'realized_at_current_fx_usd'|'unrealized_at_current_fx_usd')=>baseCurrent.value&&converted.length===accounts.value.length&&converted.every(a=>a[key]!==null)?sum(converted.map(a=>a[key]!)):null
 const assets=total('assets_value_usd'),cash=total('cash_usd'),unrealized=total('unrealized_at_current_fx_usd'),realized=total('realized_at_current_fx_usd')
 return [{label:'总资产',value:money(assets),meta:'USD · 含现金'},{label:'今日估值变化',value:money(total('day_price_effect_usd')),meta:'USD · 当前持仓×当日价差',tone:direction(total('day_price_effect_usd'))},{label:'浮动收益',value:money(unrealized),meta:unrealized===null?'缺少有效价格或汇率':'USD · 按当前汇率折算',tone:direction(unrealized)},{label:'已实现收益',value:money(realized),meta:'USD · 不含历史汇兑收益',tone:direction(realized)},{label:'持仓数量',value:String(accounts.value.reduce((n,a)=>n+a.positions.length,0)),meta:'账户持仓'},{label:'现金比例',value:cash!==null&&assets!==null?percent(cash,assets):'—',meta:cash===null?'缺少有效汇率':money(cash)+' USD'}]
})
const portfolioPositionWeight=computed(()=>{
 const row=selected.value,positions=workspace.value?.base_valuation.accounts.flatMap(a=>a.positions.map(p=>({account_id:a.account_id,...p})))||[]
 if(!row||!baseCurrent.value||!positions.length||positions.some(p=>p.market_value_usd===null))return null
 const total=sum(positions.map(p=>p.market_value_usd!)),current=positions.find(p=>p.account_id===row.account_id&&p.symbol===row.symbol)?.market_value_usd
 return current!==null&&current!==undefined&&compare(total,'0')>0?percent(current,total):null
})
const positionMetrics=computed(()=>{
 const row=selected.value;if(!row)return []
 return [
  {label:'市值',value:money(baseCurrent.value?row.market_value:null),meta:portfolioPositionWeight.value?'全组合持仓市值 '+portfolioPositionWeight.value:row.currency+' · 占比待补'},
  {label:'浮动收益',value:money(baseCurrent.value?row.unrealized_pnl:null),meta:floatingReturnRate(row)||'收益率待补'},
  {label:'今日估值变化',value:money(baseCurrent.value?row.day_price_effect:null),meta:dayChangeRate(row)||'当日涨跌待补'},
  {label:'持仓数量',value:row.quantity+' 股',meta:'成本 '+money(row.open_cost)+' '+row.currency},
 ]
})
const quoteHistory=computed(()=>workspace.value?.versions.filter(q=>q.kind==='quote'&&q.symbol===selected.value?.symbol&&q.currency===selected.value?.currency).sort((a,b)=>b.updated_at.localeCompare(a.updated_at))||[])
const unregisterMaterial=registerPageMaterial('/portfolio',()=>{
  refreshDay()
  if(!baseCurrent.value||loading.value||saving.value||error.value||!workspace.value||quoteDialog.value||drawer.value||loadedAt.value.slice(0,10)!==new Date().toISOString().slice(0,10))throw Error('请先刷新持仓并关闭价格编辑或详情窗口，再载入材料。')
  return {scope:'filtered_portfolio_positions',loaded_at:loadedAt.value,
    filters:{account_id:accountId.value||null,currency:currency.value||null,symbol:search.value.trim().toUpperCase(),sort:sort.value},
    positions:rows.value,summary:summary.value,base_valuation:{evaluated_on:workspace.value.base_valuation.evaluated_on,evaluated_market_dates:workspace.value.base_valuation.evaluated_market_dates,base_currency:'USD',return_basis:workspace.value.base_valuation.return_basis,accounts:baseAccounts.value.map(a=>({...a,positions:a.positions.filter(p=>rows.value.some(row=>row.account_id===a.account_id&&row.symbol===p.symbol))}))},
    summary_scope:'账户与币种范围内的汇总；标的搜索仅过滤持仓表，不改变汇总卡。',
    notice:'当前已载入持仓快照，保留缺价/过期状态和价格来源；汇总按记录的有效汇率折算USD，原币行不直接合计，今日估值变化仅当前数量乘当日报价与昨收的差，不含日内成交/费用/分红。不含逐笔成交或其他研究材料。'}
})
onBeforeUnmount(unregisterMaterial)
async function loadSnapshotHistory(){if(snapshotLoading.value)return;snapshotLoading.value=true;snapshotError.value='';try{const data=await request<{records:DailyRow[]}>('/api/v1/owner/daily-history','POST',{account_id:'portfolio:all'});dailySnapshots.value=data.records.filter(r=>r.kind==='daily_snapshot');dailyBriefs.value=data.records.filter(r=>r.kind==='daily_brief')}catch(e){dailySnapshots.value=[];dailyBriefs.value=[];snapshotError.value=e instanceof Error?e.message:'读取失败'}finally{snapshotLoading.value=false}}
function toggleDistribution(){distributionOpen.value=!distributionOpen.value;if(distributionOpen.value)void loadSnapshotHistory()}
function openDailySnapshot(id:string){const brief=dailyBriefs.value.find(r=>r.snapshot_id===id);router.push({path:'/review/diagnosis',query:brief?{id:brief.id}:{}})}
async function load(){if(loading.value)return false;loading.value=true;error.value='';try{workspace.value=await getWorkspace();refreshDay();loadedAt.value=new Date().toISOString();if(distributionOpen.value)void loadSnapshotHistory();return true}catch(e){workspace.value=null;selectedKey.value='';drawer.value=false;dailySnapshots.value=[];dailyBriefs.value=[];loadedAt.value='';error.value=e instanceof Error?e.message:'读取失败';return false}finally{loading.value=false}}
function open(row:Row){selectedKey.value=row.key;tab.value='detail';drawer.value=true}
function manage(command:string){if(command==='quote')editQuote();else router.push('/portfolio/'+command)}
function editQuote(row?:Row){Object.assign(quote,{symbol:row?.symbol||'',currency:row?.currency||scopeCurrency.value||'USD',price:'',previous_close:'',as_of:new Date().toISOString().slice(0,10),source:''});quoteId=crypto.randomUUID();quoteBaseline=JSON.stringify(quote);operations.clear();saveError.value='';quoteDialog.value=true}
const dirty=computed(()=>quoteDialog.value&&JSON.stringify(quote)!==quoteBaseline)
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的价格快照？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function closeQuote(){if(await discard())quoteDialog.value=false}
async function saveQuote(){if(saving.value||loading.value)return;saving.value=true;saveError.value='';try{await request('/api/v1/owner/business','POST',operations.body('quote',{id:quoteId,revision:0,kind:'quote',data:{...quote,symbol:quote.symbol.trim().toUpperCase()}}));quoteDialog.value=false;operations.clear();if(await load())ElMessage.success('价格快照已保存');else{error.value='价格快照已保存，但持仓重新读取失败。请刷新持仓确认，避免重复保存。';ElMessage.warning(error.value)}}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}}
const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}}
onBeforeRouteLeave(discard);onMounted(()=>{load();dayTimer=setInterval(refreshDay,1000);window.addEventListener('beforeunload',beforeUnload)});onBeforeUnmount(()=>{if(dayTimer)clearInterval(dayTimer);window.removeEventListener('beforeunload',beforeUnload)})
</script>

<style scoped>
.overview-page {
  padding: 10px 10px 22px;
}

:deep(.el-empty) {
  --el-empty-fill-color-0: rgba(126, 213, 255, 0.12);
  --el-empty-fill-color-1: rgba(126, 213, 255, 0.1);
  --el-empty-fill-color-2: rgba(126, 213, 255, 0.08);
  --el-empty-fill-color-3: rgba(126, 213, 255, 0.06);
  --el-empty-fill-color-4: rgba(126, 213, 255, 0.045);
  --el-empty-fill-color-5: rgba(126, 213, 255, 0.035);
  --el-empty-fill-color-6: rgba(126, 213, 255, 0.025);
  --el-empty-fill-color-7: rgba(126, 213, 255, 0.02);
  --el-empty-fill-color-8: rgba(126, 213, 255, 0.018);
  --el-empty-fill-color-9: rgba(126, 213, 255, 0.014);
}

:deep(.el-empty__description p) {
  color: #8ea6c4;
  font-size: 12px;
}

:deep(.el-dialog) {
  overflow: hidden;
  border: 1px solid rgba(126, 213, 255, 0.14);
  border-radius: 22px;
  background:
    radial-gradient(circle at 16% 0%, rgba(85, 194, 255, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.98), rgba(7, 17, 32, 0.98));
  box-shadow: 0 30px 70px rgba(1, 8, 21, 0.46);
}

:deep(.el-dialog__header) {
  margin: 0;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(126, 213, 255, 0.09);
}

:deep(.el-dialog__title) {
  color: #edf7ff;
  font-size: 17px;
  font-weight: 760;
  letter-spacing: 0.01em;
}

:deep(.el-dialog__body) {
  padding: 18px 20px;
  color: #c9dcf2;
}

:deep(.el-dialog__footer) {
  padding: 14px 20px 18px;
  border-top: 1px solid rgba(126, 213, 255, 0.08);
}

:deep(.el-dialog .el-alert) {
  border-color: rgba(126, 213, 255, 0.12);
  background: rgba(126, 213, 255, 0.065);
}

:deep(.el-dialog .el-alert__title) {
  color: #e7f6ff;
  font-weight: 700;
}

:deep(.el-dialog .el-alert__description) {
  color: #8ea6c4;
}

:deep(.el-dialog .el-input__wrapper),
:deep(.el-dialog .el-input-number__decrease),
:deep(.el-dialog .el-input-number__increase),
:deep(.el-dialog .el-date-editor.el-input__wrapper) {
  border-color: rgba(126, 213, 255, 0.12);
  background: rgba(255, 255, 255, 0.035);
  box-shadow: inset 0 0 0 1px rgba(126, 213, 255, 0.1);
}

:deep(.el-dialog .el-input__inner),
:deep(.el-dialog .el-checkbox__label) {
  color: #dff0ff;
}

:deep(.el-dialog .el-upload-dragger) {
  border-color: rgba(126, 213, 255, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 0%, rgba(126, 213, 255, 0.08), transparent 36%),
    rgba(4, 14, 29, 0.4);
}

:deep(.el-dialog .el-upload-dragger:hover) {
  border-color: rgba(126, 213, 255, 0.28);
}

:deep(.el-dialog .el-upload__text),
:deep(.el-dialog .el-upload__tip) {
  color: #8ea6c4;
}

:deep(.el-dialog .el-table) {
  overflow: hidden;
  border-color: rgba(126, 213, 255, 0.1);
  border-radius: 14px;
  background: rgba(7, 17, 32, 0.76);
}

:deep(.el-dialog .el-table th.el-table__cell) {
  background: rgba(12, 27, 52, 0.96) !important;
  color: #8ea6c4;
}

:deep(.el-dialog .el-table tr),
:deep(.el-dialog .el-table td.el-table__cell) {
  background: rgba(7, 17, 32, 0.78) !important;
  color: #d7eaff;
}

.overview-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

:deep(.control-bar .el-input__wrapper),
:deep(.control-bar .el-select__wrapper) {
  background: rgba(255, 255, 255, 0.04);
  box-shadow: inset 0 0 0 1px rgba(112, 202, 255, 0.12);
}

:deep(.control-bar .el-input__wrapper.is-focus),
:deep(.control-bar .el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 0 0 1px rgba(112, 202, 255, 0.26),
    0 0 0 3px rgba(85, 194, 255, 0.08);
}

:deep(.control-bar .el-input__inner),
:deep(.control-bar .el-select__placeholder),
:deep(.control-bar .el-select__selected-item) {
  color: #dff0ff;
}

:deep(.control-bar .el-button) {
  min-height: 34px;
  border-radius: 12px;
  border-color: rgba(112, 202, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: #cfe5ff;
}

:deep(.control-bar .el-button:hover) {
  border-color: rgba(112, 202, 255, 0.24);
  background: rgba(85, 194, 255, 0.09);
  color: #f4fbff;
}

:deep(.control-bar .el-tag),
:deep(.account-breakdown-card .el-tag) {
  border-color: rgba(112, 202, 255, 0.14);
  background: rgba(85, 194, 255, 0.08);
  color: #dff0ff;
}

.control-bar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(112, 202, 255, 0.12);
  background: linear-gradient(180deg, rgba(12, 27, 52, 0.88), rgba(9, 20, 39, 0.82));
  box-shadow: 0 18px 34px rgba(1, 8, 21, 0.16);
}

.control-view-switcher {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px;
  border: 1px solid rgba(112, 202, 255, 0.1);
  border-radius: 12px;
  background: rgba(4, 14, 29, 0.46);
}

.control-view-button {
  min-height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #8ea6c4;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.control-view-button:hover,
.control-view-button:focus-visible {
  color: #dff2ff;
  background: rgba(85, 194, 255, 0.07);
}

.control-view-button:focus-visible,
.stock-ticker:focus-visible,
:deep(.control-bar .el-button:focus-visible),
:deep(.action-cell .action-link:focus-visible) {
  outline: 2px solid rgba(126, 213, 255, 0.72);
  outline-offset: 3px;
}

.control-view-button.is-active {
  color: #f4fbff;
  background: linear-gradient(135deg, rgba(44, 143, 255, 0.48), rgba(85, 194, 255, 0.24));
  box-shadow: 0 6px 14px rgba(32, 124, 228, 0.14);
}

.filter-active-count {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  margin-left: 6px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(85, 194, 255, 0.16);
  color: #e8f8ff;
  font: 700 10px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

:deep(.control-bar .el-button.has-active-filter) {
  border-color: rgba(112, 202, 255, 0.26);
  background: rgba(85, 194, 255, 0.1);
}

:global(.portfolio-filter-menu) {
  min-width: 260px;
}

:global(.portfolio-filter-menu .el-dropdown-menu__item) {
  padding: 8px 12px;
}

:global(.portfolio-filter-menu .el-dropdown-menu__item.is-selected) {
  background: rgba(64, 158, 255, 0.1);
  color: var(--el-color-primary);
}

.portfolio-filter-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  width: 100%;
}

.portfolio-filter-option > span {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.portfolio-filter-option b {
  font-size: 12px;
  line-height: 1.35;
}

.portfolio-filter-option small {
  max-width: 184px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 10px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.portfolio-filter-option strong {
  color: var(--el-color-primary);
  font: 700 12px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.portfolio-load-state {
  margin-bottom: 10px;
}

.governance-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.governance-grid,
.impact-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.governance-card,
.impact-item {
  border: 1px solid rgba(126, 213, 255, 0.12);
  border-radius: 14px;
  padding: 14px 16px;
  background:
    radial-gradient(circle at 16% 0%, rgba(126, 213, 255, 0.075), transparent 38%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.72), rgba(7, 17, 32, 0.62));
}

.governance-label,
.impact-label {
  margin-bottom: 6px;
  color: #8ea6c4;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.governance-value,
.impact-item b {
  font-size: 24px;
  font-weight: 700;
  color: #eef7ff;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.governance-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #7086a1;
}

.governance-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #8ea6c4;
}

.governance-warning {
  margin: 0;
}

.governance-rebuild {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0 4px;
  flex-wrap: wrap;
}

.governance-rebuild-title {
  margin-bottom: 4px;
  color: #eef7ff;
  font-size: 15px;
  font-weight: 600;
}

.governance-rebuild-desc {
  color: #8ea6c4;
  font-size: 13px;
}

.rebuild-impact-card {
  border: 1px solid rgba(126, 213, 255, 0.12);
  border-radius: 16px;
  background: rgba(7, 17, 32, 0.42);
}

.impact-warnings {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.impact-warning {
  font-size: 13px;
  color: #ffdd9a;
}

.impact-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.control-left,
.control-right {
  display: contents;
}

.top-notes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.inline-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 14px;
  border: 1px solid rgba(112, 202, 255, 0.1);
  background: rgba(12, 27, 52, 0.76);
}

.inline-note.is-warning {
  border-color: rgba(255, 181, 77, 0.2);
  background: linear-gradient(180deg, rgba(255, 181, 77, 0.08), rgba(12, 27, 52, 0.84));
}

.inline-note.is-info {
  border-color: rgba(85, 194, 255, 0.16);
  background: linear-gradient(180deg, rgba(85, 194, 255, 0.08), rgba(12, 27, 52, 0.84));
}

.inline-note-icon {
  margin-top: 1px;
  font-size: 16px;
  color: #e6a23c;
}

.inline-note.is-info .inline-note-icon {
  color: #409eff;
}

.inline-note-copy {
  min-width: 0;
  flex: 1 1 auto;
}

.inline-note-title {
  font-size: 11px;
  font-weight: 600;
  color: #edf6ff;
}

.inline-note-text {
  margin-top: 1px;
  font-size: 10px;
  line-height: 1.4;
  color: #95aac6;
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.inline-note-close {
  margin: -2px -2px 0 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--el-text-color-placeholder);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.inline-note-close:hover {
  color: var(--el-text-color-secondary);
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin: 6px 0 10px;
  padding: 14px 16px;
  border: 1px solid rgba(126, 213, 255, 0.1);
  border-radius: 18px;
  background:
    radial-gradient(circle at 94% 0%, rgba(126, 213, 255, 0.07), transparent 30%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.74), rgba(8, 18, 35, 0.68));
  box-shadow: 0 14px 30px rgba(1, 8, 21, 0.12);
}

.section-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.section-kicker {
  font-size: 10px;
  font-weight: 700;
  color: #8ea6c4;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #eef7ff;
}

.section-subtitle {
  font-size: 11px;
  line-height: 1.4;
  color: #7086a1;
}

.account-breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin: 0 0 18px;
}

.account-breakdown-card {
  position: relative;
  overflow: hidden;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(112, 202, 255, 0.11);
  background:
    radial-gradient(circle at 12% 0%, rgba(85, 194, 255, 0.08), transparent 36%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.88), rgba(9, 20, 39, 0.84));
  box-shadow: 0 16px 30px rgba(1, 8, 21, 0.14);
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.account-breakdown-card::before {
  position: absolute;
  inset: 0 0 auto;
  height: 2px;
  background: linear-gradient(90deg, rgba(91, 214, 255, 0.72), rgba(51, 214, 159, 0.32), transparent);
  content: '';
}

.account-breakdown-card:hover {
  border-color: rgba(126, 213, 255, 0.2);
  box-shadow: 0 18px 36px rgba(1, 8, 21, 0.2);
  transform: translateY(-1px);
}

.account-breakdown-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.account-breakdown-tags {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.account-breakdown-count {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: #8ea6c4;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.account-breakdown-name {
  font-size: 13px;
  font-weight: 720;
  color: #dcefff;
}

.account-breakdown-main {
  font-size: 20px;
  font-weight: 700;
  color: #eef7ff;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.account-breakdown-body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.account-breakdown-pl {
  font-size: 13px;
  font-weight: 650;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.account-breakdown-bar {
  margin-top: 10px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.account-breakdown-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(44, 143, 255, 0.88), rgba(61, 218, 255, 0.92));
  box-shadow: 0 0 18px rgba(61, 218, 255, 0.18);
}

.account-breakdown-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #8ea6c4;
}

.account-breakdown-signal {
  margin-top: 6px;
  padding-top: 7px;
  border-top: 1px solid rgba(126, 213, 255, 0.065);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 11px;
  color: #7086a1;
}

.ledger-section {
  margin-bottom: 18px;
  width: 100%;
}

.ledger-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  padding: 15px 18px 14px;
  border-radius: 20px 20px 14px 14px;
  border: 1px solid rgba(126, 213, 255, 0.1);
  background:
    radial-gradient(circle at 92% 0%, rgba(126, 213, 255, 0.09), transparent 30%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.78), rgba(8, 18, 35, 0.72));
  box-shadow: 0 18px 34px rgba(1, 8, 21, 0.12);
}

.ledger-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.ledger-kicker {
  font-size: 10px;
  font-weight: 700;
  color: #7f9ab8;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.ledger-title {
  font-size: 17px;
  font-weight: 760;
  color: #eef7ff;
}

.ledger-subtitle {
  max-width: 860px;
  font-size: 11px;
  color: #7086a1;
  line-height: 1.55;
}

.ledger-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.ledger-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(126, 213, 255, 0.13);
  background: rgba(255, 255, 255, 0.025);
  color: #d5eaff;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.stock-cell {
  display: flex;
  align-items: center;
  gap: 11px;
}

.stock-avatar {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 11px;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.14),
    0 6px 14px rgba(1, 8, 21, 0.28);
  filter: saturate(0.82) brightness(0.94);
}

.stock-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stock-ticker {
  display: inline-flex;
  width: fit-content;
  padding: 0;
  border: 0;
  background: transparent;
  font-weight: 760;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-size: 13.5px;
  color: #eef7ff;
  cursor: pointer;
  transition: color 0.15s ease;
  line-height: 1.1;
}

.stock-ticker:hover,
.stock-ticker:focus-visible {
  color: #5bc0ff;
}

.stock-name {
  font-size: 11px;
  color: #8098b5;
  line-height: 1.3;
  max-width: 168px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sector-tag {
  font-size: 11px;
  color: #dcefff;
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(112, 202, 255, 0.08);
  border: 1px solid rgba(112, 202, 255, 0.15);
}

.company-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.company-main {
  color: #eef7ff;
  font-weight: 600;
  font-size: 13px;
  line-height: 1.34;
}

.company-sub {
  font-size: 10px;
  color: #7086a1;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mono-value {
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.numeric-main {
  font-weight: 690;
  letter-spacing: -0.015em;
  font-size: 12.8px;
}

.metric-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.numeric-meta {
  font-size: 10px;
  color: #7086a1;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.action-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
}

.action-links {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
  white-space: nowrap;
  width: 100%;
}

.action-brief {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  width: 100%;
}

.action-brief-label {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: #cde6ff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.action-brief-label.is-neutral {
  border-color: rgba(112, 202, 255, 0.14);
  color: #cde6ff;
}

.action-brief-label.is-positive {
  border-color: rgba(51, 214, 159, 0.22);
  background: rgba(51, 214, 159, 0.12);
  color: #b9ffe2;
}

.action-brief-label.is-watch {
  border-color: rgba(255, 181, 77, 0.22);
  background: rgba(255, 181, 77, 0.1);
  color: #ffe1a6;
}

.action-brief-label.is-risk {
  border-color: rgba(255, 107, 123, 0.22);
  background: rgba(255, 107, 123, 0.12);
  color: #ffd3db;
}

.action-brief-meta {
  max-width: 100%;
  font-size: 10px;
  line-height: 1.35;
  text-align: right;
  color: #7086a1;
  letter-spacing: 0.04em;
}

:deep(.action-cell .el-button.is-circle) {
  width: 28px;
  height: 28px;
}

:deep(.portfolio-table .el-table__body-wrapper .el-table__row) {
  height: 54px;
}

:deep(.portfolio-table .el-table__body-wrapper .el-table__row td .cell) {
  padding: 6px 0;
}

:deep(.portfolio-table .el-table__footer-wrapper td) {
  background: rgba(17, 37, 89, 0.03);
  font-weight: 600;
}

:deep(.portfolio-table .el-table__footer-wrapper .cell) {
  white-space: nowrap;
}

.small-pct {
  font-size: 11px;
  opacity: 0.85;
}

.price-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  width: 100%;
}

.change-inline {
  font-size: 11px;
  font-weight: 600;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.price-main-row {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
  width: 100%;
}

.price-source-tags {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.price-meta {
  margin-top: 2px;
  font-size: 10px;
  color: #7086a1;
}

.weight-chip {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
}

.weight-chip.is-warning {
  border-color: rgba(255, 181, 77, 0.22);
  background: rgba(255, 181, 77, 0.08);
}

.pnl-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.pnl-pct {
  font-size: 11px;
  font-weight: 600;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.account-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  background: rgba(85, 194, 255, 0.08);
  color: #dff0ff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

:deep(.action-cell .action-link) {
  min-height: 27px;
  min-width: 45px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.16);
  background: rgba(255, 255, 255, 0.04);
  color: #cde6ff;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  text-decoration: none;
  letter-spacing: 0.03em;
  text-transform: none;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

:deep(.action-cell .action-link:hover) {
  border-color: rgba(112, 202, 255, 0.32);
  background: rgba(85, 194, 255, 0.12);
  color: #f4fbff;
  transform: translateY(-1px);
}

:deep(.action-cell .action-link.is-primary) {
  background: linear-gradient(135deg, rgba(44, 143, 255, 0.22), rgba(85, 194, 255, 0.14));
  border-color: rgba(112, 202, 255, 0.28);
  color: #edf8ff;
}

:deep(.portfolio-table) {
  border-radius: 22px;
  overflow: hidden;
  border: 1px solid rgba(126, 213, 255, 0.11);
  background:
    linear-gradient(180deg, rgba(11, 24, 45, 0.86), rgba(7, 17, 32, 0.84));
  box-shadow: 0 22px 42px rgba(1, 8, 21, 0.18);
}

:deep(.portfolio-table .el-table__header-wrapper th) {
  height: 42px;
  background: linear-gradient(180deg, rgba(15, 32, 58, 0.96), rgba(10, 23, 43, 0.94)) !important;
  border-bottom-color: rgba(126, 213, 255, 0.1) !important;
}

:deep(.portfolio-table .el-table__header-wrapper th .cell) {
  font-size: 11px;
  font-weight: 600;
  color: #7f95b0;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable .cell) {
  display: inline-grid;
  grid-template-columns: minmax(0, max-content) 16px;
  align-items: center;
  justify-content: start;
  column-gap: 6px;
  min-height: 28px;
  width: 100%;
  white-space: nowrap;
  overflow: visible;
  line-height: 1.15;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable.is-right .cell) {
  justify-content: end;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable .caret-wrapper) {
  position: static;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 18px;
  margin-left: 1px;
  border: 1px solid rgba(126, 213, 255, 0.16);
  border-radius: 999px;
  background: rgba(10, 29, 53, 0.48);
  color: rgba(127, 149, 176, 0.72);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.015);
  opacity: 0.72;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease, opacity 0.16s ease,
    box-shadow 0.16s ease;
  vertical-align: middle;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable .caret-wrapper::before) {
  content: '↕';
  display: block;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0;
  transform: translateY(-0.5px);
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable .sort-caret) {
  display: none !important;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable:hover .caret-wrapper) {
  border-color: rgba(126, 213, 255, 0.34);
  background: rgba(22, 64, 104, 0.72);
  color: rgba(185, 223, 255, 0.92);
  opacity: 1;
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable.ascending .caret-wrapper),
:deep(.portfolio-table .el-table__header-wrapper th.is-sortable.descending .caret-wrapper) {
  border-color: rgba(91, 214, 255, 0.46);
  background: rgba(36, 118, 186, 0.34);
  color: #72e4ff;
  opacity: 1;
  box-shadow: 0 0 14px rgba(91, 214, 255, 0.1), inset 0 0 0 1px rgba(255, 255, 255, 0.025);
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable.ascending .caret-wrapper::before) {
  content: '↑';
}

:deep(.portfolio-table .el-table__header-wrapper th.is-sortable.descending .caret-wrapper::before) {
  content: '↓';
}

:deep(.portfolio-table .el-table__body tr > td.el-table__cell) {
  border-bottom-color: rgba(126, 213, 255, 0.055) !important;
  padding-top: 10px;
  padding-bottom: 10px;
  transition: background 0.18s ease, box-shadow 0.18s ease;
}

:deep(.portfolio-table .el-table__body tr:hover > td.el-table__cell) {
  background: rgba(126, 213, 255, 0.065) !important;
}

:deep(.portfolio-table .el-table__body tr:hover > td.el-table__cell:first-child) {
  box-shadow: inset 3px 0 0 0 #5bd6ff;
}

:deep(.portfolio-table .cell) {
  font-size: 12px;
  line-height: 1.3;
}

:deep(.portfolio-table .el-table__body-wrapper .el-table__row) {
  height: 66px;
}

:deep(.portfolio-table .el-table-fixed-column--left),
:deep(.portfolio-table .el-table-fixed-column--right) {
  background: rgba(9, 20, 39, 0.96) !important;
}

:deep(.portfolio-table .el-table__fixed-right-patch) {
  background: rgba(10, 23, 43, 0.96) !important;
}

:deep(.portfolio-table .el-table__footer-wrapper td) {
  border-top: 1px solid rgba(126, 213, 255, 0.1);
  background: rgba(12, 27, 52, 0.96) !important;
  color: #dbefff;
}

.earnings-cell,
.signal-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.earnings-meta,
.signal-meta {
  font-size: 11px;
  color: #7086a1;
}

.tag-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.charts-row.is-single {
  grid-template-columns: 1fr;
}

.chart-card {
  position: relative;
  overflow: hidden;
  min-height: 318px;
  padding: 15px;
  border: 1px solid rgba(112, 202, 255, 0.11);
  border-radius: 18px;
  background:
    radial-gradient(circle at 86% 0%, rgba(126, 213, 255, 0.09), transparent 34%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.9), rgba(9, 20, 39, 0.84));
  box-shadow: 0 18px 34px rgba(1, 8, 21, 0.16);
}

.chart-card::after {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.035), transparent 34%);
  content: '';
}

.chart-card.is-wide {
  min-height: 344px;
}

.chart-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.chart-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.chart-kicker {
  font-size: 10px;
  font-weight: 700;
  color: #8ea6c4;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.chart-title {
  font-size: 14px;
  font-weight: 720;
  color: #eef7ff;
}

.chart-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: #cde6ff;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chart-container {
  position: relative;
  z-index: 1;
  height: 224px;
}

.chart-insight {
  position: relative;
  z-index: 1;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid rgba(126, 213, 255, 0.07);
  font-size: 11px;
  line-height: 1.6;
  color: #8ea6c4;
}

.warn-weight {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: #e6a23c;
}

.bootstrap-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bootstrap-status {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.status-card {
  border: 1px solid rgba(126, 213, 255, 0.12);
  border-radius: 14px;
  padding: 14px 16px;
  background:
    radial-gradient(circle at 16% 0%, rgba(126, 213, 255, 0.075), transparent 38%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.72), rgba(7, 17, 32, 0.62));
}

.status-label {
  margin-bottom: 6px;
  color: #8ea6c4;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-value {
  font-size: 24px;
  font-weight: 700;
  color: #eef7ff;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.bootstrap-fields {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.bootstrap-upload {
  width: 100%;
}

.bootstrap-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.bootstrap-file-name {
  font-size: 13px;
  color: #8ea6c4;
}

.bootstrap-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bootstrap-preview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.bootstrap-preview-warning {
  margin: 0;
}

.column-picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.column-picker-title {
  font-size: 13px;
  font-weight: 600;
  color: #eef7ff;
}

.column-picker-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

:global(.warn-row td) {
  background-color: rgba(230, 162, 60, 0.06) !important;
}

:global(.risk-row td) {
  background-color: rgba(245, 108, 108, 0.06) !important;
}

:global(.focus-row td) {
  background-color: rgba(64, 158, 255, 0.08) !important;
}

.pl-pos {
  color: #ee6e7c;
}
.pl-neg {
  color: #43c986;
}
.pl-zero {
  color: #6d8097;
}

.desk-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.desk-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 18px 16px;
  border-radius: 20px;
  border: 1px solid rgba(126, 213, 255, 0.11);
  background:
    radial-gradient(circle at 14% 0%, rgba(85, 194, 255, 0.08), transparent 36%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.84), rgba(9, 20, 39, 0.8));
  box-shadow: 0 16px 34px rgba(1, 8, 21, 0.16);
}

.desk-head,
.desk-action-row,
.queue-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.desk-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #8ea6c4;
  text-transform: uppercase;
}

.desk-title {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 800;
  color: #eef7ff;
}

.desk-action-list,
.queue-list,
.preset-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.desk-action-row,
.queue-row,
.preset-button {
  width: 100%;
  border-radius: 16px;
  border: 1px solid rgba(126, 213, 255, 0.1);
  background: rgba(4, 14, 29, 0.36);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.desk-action-row,
.queue-row {
  padding: 14px 14px 13px;
}

.desk-action-row:hover,
.queue-row:hover,
.preset-button:hover {
  transform: translateY(-1px);
  border-color: rgba(126, 213, 255, 0.2);
  box-shadow: 0 12px 28px rgba(1, 8, 21, 0.18);
}

.desk-action-row.is-risk {
  border-color: rgba(245, 108, 108, 0.18);
  background: rgba(245, 108, 108, 0.045);
}

.desk-action-row.is-watch {
  border-color: rgba(230, 162, 60, 0.18);
  background: rgba(230, 162, 60, 0.04);
}

.desk-action-row.is-positive {
  border-color: rgba(103, 194, 58, 0.16);
  background: rgba(103, 194, 58, 0.04);
}

.desk-action-main,
.queue-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.desk-action-topline,
.queue-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.desk-action-badge,
.queue-pulse {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(84, 167, 255, 0.1);
  font-size: 11px;
  font-weight: 700;
  color: #8fdfff;
}

.queue-pulse.is-risk {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.08);
}

.queue-pulse.is-watch {
  color: #d48806;
  background: rgba(230, 162, 60, 0.08);
}

.queue-pulse.is-positive {
  color: #1f9d68;
  background: rgba(103, 194, 58, 0.08);
}

.desk-action-ticker,
.queue-ticker {
  font-size: 16px;
  font-weight: 800;
  color: #eef7ff;
}

.desk-action-title {
  font-size: 15px;
  line-height: 1.45;
  color: #eef7ff;
  font-weight: 700;
}

.desk-action-detail,
.queue-company,
.queue-side small,
.preset-copy,
.desk-footnote {
  font-size: 12px;
  line-height: 1.7;
  color: #8ea6c4;
}

.desk-action-cta {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: #8fdfff;
}

.queue-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  text-align: right;
}

.queue-side b {
  font-size: 15px;
  color: #eef7ff;
}

.preset-button {
  padding: 14px 15px;
  text-align: left;
}

.preset-label {
  display: block;
  font-size: 14px;
  font-weight: 800;
  color: #eef7ff;
}

.preset-copy {
  display: block;
  margin-top: 4px;
}

.desk-footnote {
  padding-top: 4px;
}

@media (min-width: 961px) and (max-width: 1320px) {
  .control-bar {
    gap: 8px;
  }

  .control-view-button {
    padding: 0 8px;
  }

  .control-left :deep(.el-select) {
    width: 140px !important;
  }

  .control-left :deep(.el-input) {
    width: 165px !important;
  }

  :deep(.control-icon-button) {
    width: 36px;
    padding: 0;
  }

  :deep(.control-icon-button .control-button-label) {
    display: none;
  }
}

.portfolio-summary-dashboard {
  display: grid;
  grid-template-columns: repeat(6, minmax(150px, 1fr));
  align-items: stretch;
  gap: 0;
  min-height: 112px;
  margin-bottom: 14px;
  padding: 14px 18px;
  border: 1px solid rgba(86, 151, 216, 0.11);
  border-radius: 22px;
  background:
    radial-gradient(circle at 10% 0%, rgba(59, 172, 255, 0.12), transparent 42%),
    linear-gradient(135deg, rgba(9, 24, 43, 0.82), rgba(9, 15, 31, 0.76)),
    rgba(7, 15, 29, 0.82);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 22px 70px rgba(0, 0, 0, 0.14);
}

.portfolio-summary-metric {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 4px 16px;
  border-left: 1px solid rgba(115, 168, 218, 0.1);
}

.portfolio-summary-metric:first-child {
  border-left: 0;
}

.portfolio-summary-label,
.portfolio-summary-meta {
  display: block;
  color: #71849c;
  font-size: 10px;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.portfolio-summary-value {
  display: block;
  margin-top: 8px;
  color: #e8f1ff;
  font-size: clamp(20px, 1.42vw, 28px);
  line-height: 1;
  white-space: nowrap;
}

.portfolio-summary-meta {
  margin-top: 8px;
  color: #52677f;
  font-size: 10px;
  letter-spacing: 0.03em;
  text-transform: none;
}

.portfolio-summary-metric.is-positive .portfolio-summary-value {
  color: #28d7aa;
}

.portfolio-summary-metric.is-negative .portfolio-summary-value {
  color: #ff657b;
}

.command-control {
  width: 142px;
}

.command-search {
  width: 176px;
}

.command-control.is-narrow {
  width: 116px;
}

.command-control.is-sort {
  width: 128px;
}

.command-control :deep(.el-input__wrapper),
.command-control :deep(.el-select__wrapper) {
  min-height: 34px;
  border-radius: 12px;
  background: rgba(7, 17, 32, 0.62);
  box-shadow: inset 0 0 0 1px rgba(96, 151, 206, 0.13);
}

.command-tool-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 11px;
  border: 1px solid rgba(103, 168, 228, 0.15);
  border-radius: 12px;
  background: rgba(7, 17, 32, 0.58);
  color: #a9bed6;
  font-size: 11px;
  font-weight: 720;
  cursor: pointer;
}

.command-tool-button:hover,
.command-tool-button.has-active-filter {
  background: rgba(41, 121, 201, 0.18);
  color: #eaf5ff;
}

.command-tool-button.is-icon {
  width: 34px;
  padding: 0;
}

.command-tool-button b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  border-radius: 999px;
  background: rgba(68, 178, 255, 0.22);
  color: #80d6ff;
  font-size: 10px;
}

.command-center {
  overflow: visible;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.command-table-shell {
  overflow: hidden;
  border: 1px solid rgba(102, 164, 225, 0.12);
  border-radius: 20px;
  background:
    linear-gradient(140deg, rgba(8, 23, 42, 0.68), rgba(8, 15, 30, 0.78)),
    rgba(5, 13, 24, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 20px 60px rgba(0, 0, 0, 0.16);
}

.command-table-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 72px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(91, 151, 214, 0.1);
}

.command-table-copy {
  display: flex;
  flex: 1 1 260px;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  min-width: 0;
}

.command-kicker {
  color: #56d6ff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.command-table-topline strong {
  color: #eaf3ff;
  font-size: 18px;
  font-weight: 760;
}

.command-table-copy small {
  overflow: hidden;
  color: #667a92;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-table-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 1 1 720px;
  gap: 8px;
  min-width: 0;
}

.command-grid {
  display: grid;
  grid-template-columns:
    minmax(180px, 22fr)
    minmax(100px, 10fr)
    minmax(115px, 15fr)
    minmax(106px, 12fr)
    minmax(190px, 18fr)
    minmax(105px, 10fr)
    minmax(96px, 10fr)
    minmax(36px, 3fr);
  column-gap: 8px;
  align-items: center;
}

.command-table-header {
  height: 38px;
  padding: 0 14px;
  border-bottom: 1px solid rgba(91, 151, 214, 0.08);
  background: rgba(6, 14, 28, 0.42);
}

.command-sort-head {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #77879c;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
  text-align: left;
  text-transform: none;
}

button.command-sort-head {
  cursor: pointer;
}

.command-sort-head.is-right {
  justify-content: flex-end;
  text-align: right;
}

.command-sort-head span {
  display: none;
}

.command-sort-head span.is-active {
  display: none;
}

.command-row {
  height: 58px;
  min-height: 58px;
  padding: 0 14px;
  border-bottom: 1px solid rgba(91, 151, 214, 0.058);
  color: #d5e5f7;
  outline: none;
  cursor: pointer;
  transition:
    background-color 120ms ease;
}

.command-row::before,
.command-row::after {
  display: none;
  content: none;
}

.command-row:last-child {
  border-bottom: 0;
}

.command-row:hover,
.command-row:focus-visible {
  background: rgba(52, 131, 206, 0.052);
}

.command-row.focus-row {
  background: rgba(64, 205, 255, 0.075);
}

.command-symbol-cell {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.command-avatar {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  color: #fff;
  font-family: 'Geist Mono', 'SF Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-size: 10px;
  font-weight: 800;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.16),
    0 6px 18px rgba(0, 0, 0, 0.2);
}

.command-symbol-copy,
.command-number-cell,
.command-account-cell {
  display: grid;
  grid-template-rows: 20px 16px;
  row-gap: 2px;
  align-items: center;
  min-width: 0;
}

.command-symbol-copy strong {
  overflow: hidden;
  color: #f3f7ff;
  font-size: 13px;
  font-weight: 660;
  line-height: 20px;
  letter-spacing: 0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-symbol-copy small,
.command-number-cell small,
.command-number-cell em,
.command-account-cell small {
  overflow: hidden;
  color: #687c93;
  font-size: 11px;
  font-style: normal;
  line-height: 16px;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-number-cell {
  justify-items: end;
  width: 100%;
  text-align: right;
}

.command-number-cell.is-right {
  justify-items: end;
  text-align: right;
}

.command-number-cell strong {
  color: #dce8f8;
  font-size: 13px;
  font-weight: 660;
  line-height: 20px;
  white-space: nowrap;
}

.command-price-main {
  color: #e5edf8 !important;
}

.command-number-cell .is-muted {
  color: #596e86;
}

.command-return-main {
  display: inline-flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 6px;
  max-width: 100%;
  min-width: 0;
}

.command-return-main strong {
  font-size: 13px;
  font-weight: 660;
  letter-spacing: normal;
  line-height: 20px;
}

.command-return-main span {
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
}

.command-return-cell em {
  max-width: 100%;
  margin: 0;
  color: #687b91;
  font-size: 11px;
  line-height: 16px;
}

.command-account-cell span {
  overflow: hidden;
  color: #c2d1e4;
  font-size: 13px;
  font-weight: 660;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-actions-cell {
  display: flex;
  justify-content: flex-end;
  opacity: 0.42;
  transition: opacity 120ms ease;
}

.command-row:hover .command-actions-cell,
.command-row:focus-visible .command-actions-cell {
  opacity: 1;
}

.command-more-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #7d90a7;
  cursor: pointer;
}

.command-more-button:hover {
  border-color: rgba(104, 177, 242, 0.2);
  background: rgba(69, 144, 222, 0.16);
  color: #e9f6ff;
}

.command-signal {
  display: inline-flex;
  align-self: flex-end;
  max-width: 100%;
  margin-top: 0;
  padding: 0;
  border-radius: 0;
  background: transparent !important;
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1.16;
  white-space: nowrap;
}

.command-signal.is-warn {
  color: #d6ad62;
}

.command-signal.is-risk {
  color: #de6f80;
}

.command-signal.is-info {
  color: #78a9cf;
}

.command-empty-state {
  margin: 24px 16px;
}

:global(.position-detail-drawer) {
  overflow: hidden;
  border-left: 1px solid rgba(97, 170, 232, 0.16);
  background:
    radial-gradient(circle at 18% 0%, rgba(61, 194, 255, 0.11), transparent 34%),
    linear-gradient(180deg, #071225 0%, #08182c 48%, #06101f 100%) !important;
  box-shadow: -22px 0 70px rgba(0, 0, 0, 0.42);
}

:global(.position-detail-drawer .el-drawer__body) {
  padding: 0;
  color: #dce9f8;
}

.position-drawer-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
  padding: 18px;
}

.position-drawer-header,
.position-drawer-price-line,
.position-drawer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.position-drawer-symbol {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.position-drawer-symbol strong {
  display: block;
  color: #f5f9ff;
  font-size: 18px;
  font-weight: 820;
  letter-spacing: 0.02em;
}

.position-drawer-symbol small {
  display: block;
  overflow: hidden;
  max-width: 360px;
  color: #7f96b0;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.position-drawer-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(122, 185, 242, 0.14);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.035);
  color: #9db2ca;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.position-drawer-close:hover {
  border-color: rgba(95, 205, 255, 0.32);
  color: #f2f8ff;
}

.position-drawer-price-line {
  padding: 13px 14px;
  border: 1px solid rgba(91, 151, 214, 0.13);
  border-radius: 16px;
  background: rgba(6, 18, 35, 0.62);
}

.position-drawer-price-line > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.position-drawer-price-line .is-right {
  align-items: flex-end;
}

.position-drawer-price-line span,
.position-drawer-metrics span,
.position-drawer-facts span,
.position-drawer-list span,
.position-drawer-thesis span,
.position-drawer-plan span {
  color: #7088a3;
  font-size: 10px;
  font-weight: 780;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.position-drawer-price-line strong {
  color: #f1f7ff;
  font-size: 22px;
  font-weight: 780;
  letter-spacing: -0.02em;
}

.position-drawer-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.position-drawer-metrics article {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(91, 151, 214, 0.1);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.03);
}

.position-drawer-metrics strong {
  display: block;
  overflow: hidden;
  margin: 5px 0 3px;
  color: #f1f7ff;
  font-size: 18px;
  font-weight: 780;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.position-drawer-metrics small {
  display: block;
  color: #7288a2;
  font-size: 11px;
}

.position-drawer-metrics article.is-positive strong,
.position-drawer-price-line strong.pl-pos {
  color: #36d5a4;
}

.position-drawer-metrics article.is-negative strong,
.position-drawer-price-line strong.pl-neg {
  color: #ff6c82;
}

.position-drawer-metrics article.is-warning {
  border-color: rgba(236, 174, 79, 0.22);
}

.position-drawer-pulse {
  padding: 12px 13px;
  border: 1px solid rgba(91, 151, 214, 0.11);
  border-radius: 15px;
  background: linear-gradient(135deg, rgba(66, 166, 255, 0.08), rgba(255, 255, 255, 0.025));
}

.position-drawer-pulse span,
.position-drawer-pulse strong {
  display: block;
}

.position-drawer-pulse span {
  color: #76d7ff;
  font-size: 10px;
  font-weight: 820;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.position-drawer-pulse strong {
  margin-top: 5px;
  color: #d8e8fa;
  font-size: 13px;
  line-height: 1.45;
}

.position-drawer-pulse.is-risk {
  border-color: rgba(255, 100, 124, 0.24);
}

.position-drawer-pulse.is-watch {
  border-color: rgba(236, 174, 79, 0.24);
}

.position-drawer-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.position-drawer-signals .command-signal {
  align-self: auto;
  margin: 0;
}

.position-drawer-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  padding: 4px;
  border: 1px solid rgba(91, 151, 214, 0.12);
  border-radius: 14px;
  background: rgba(3, 11, 23, 0.5);
}

.position-drawer-tabs button {
  min-width: 0;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #8096af;
  font-size: 11px;
  font-weight: 760;
  cursor: pointer;
}

.position-drawer-tabs button.is-active {
  background: rgba(71, 164, 245, 0.16);
  color: #eaf6ff;
  box-shadow: inset 0 0 0 1px rgba(88, 202, 255, 0.18);
}

.position-drawer-section {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  padding: 2px 0 12px;
}

.position-drawer-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.position-drawer-facts > div,
.position-drawer-list > div,
.position-drawer-thesis,
.position-drawer-plan {
  min-width: 0;
  padding: 13px;
  border: 1px solid rgba(91, 151, 214, 0.1);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.026);
}

.position-drawer-facts strong,
.position-drawer-list strong,
.position-drawer-plan strong {
  display: block;
  overflow: hidden;
  margin-top: 5px;
  color: #eaf3ff;
  font-size: 13px;
  font-weight: 760;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.position-drawer-facts small,
.position-drawer-list small,
.position-drawer-note,
.position-drawer-thesis p,
.position-drawer-plan p {
  margin: 6px 0 0;
  color: #7189a4;
  font-size: 12px;
  line-height: 1.6;
}

.position-drawer-chart {
  overflow: hidden;
  border: 1px solid rgba(91, 151, 214, 0.1);
  border-radius: 16px;
  background:
    linear-gradient(rgba(111, 176, 232, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(111, 176, 232, 0.05) 1px, transparent 1px),
    rgba(3, 11, 23, 0.34);
  background-size: 36px 36px;
}

.position-drawer-chart svg {
  display: block;
  width: 100%;
  height: 180px;
  padding: 18px;
}

.position-drawer-chart polyline {
  fill: none;
  stroke: #47d7b6;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 3;
  filter: drop-shadow(0 0 10px rgba(71, 215, 182, 0.28));
}

.position-drawer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.position-drawer-primary,
.position-drawer-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 820;
  cursor: pointer;
}

.position-drawer-primary {
  border: 1px solid rgba(89, 204, 255, 0.38);
  background: linear-gradient(135deg, rgba(38, 132, 255, 0.34), rgba(48, 202, 235, 0.2));
  color: #eaf8ff;
}

.position-drawer-secondary {
  border: 1px solid rgba(111, 170, 226, 0.18);
  background: rgba(255, 255, 255, 0.035);
  color: #a9bdd3;
}

.position-drawer-primary:hover,
.position-drawer-secondary:hover {
  transform: translateY(-1px);
}

@media (max-width: 1500px) {
  .portfolio-summary-dashboard {
    grid-template-columns: repeat(3, minmax(180px, 1fr));
  }

  .command-table-topline,
  .command-table-controls {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .command-table-topline {
    align-items: flex-start;
  }
}

@media (max-width: 1180px) {
  .command-table-shell { overflow: hidden; }
  .command-rows-scroll { overflow-x: auto; }

  .command-grid {
    min-width: 1080px;
  }

  .portfolio-summary-dashboard {
    grid-template-columns: repeat(3, minmax(110px, 1fr));
  }
}

@media (max-width: 960px) {
  .overview-header,
  .section-head,
  .ledger-head,
  .control-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .desk-grid,
  .charts-row,
  .bootstrap-status,
  .bootstrap-preview-grid,
  .governance-grid,
  .impact-grid {
    grid-template-columns: 1fr;
  }

  .scope-note {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .control-left,
  .control-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    width: 100%;
  }

  .control-right {
    justify-content: flex-start;
  }

}

@media (max-width: 640px) {
  .overview-page {
    padding: 8px 2px 18px;
  }

  .control-view-switcher {
    width: 100%;
  }

  .control-view-button {
    flex: 1;
  }

  .control-left :deep(.el-select),
  .control-left :deep(.el-input) {
    width: 100% !important;
  }

  :deep(.control-icon-button) {
    width: 36px;
    padding: 0;
  }

  :deep(.control-icon-button .control-button-label) {
    display: none;
  }

  .ledger-head {
    padding: 12px;
  }

  .ledger-meta {
    display: none;
  }

}

@media (prefers-reduced-motion: reduce) {
  .control-view-button,
  .stock-ticker,
  .account-breakdown-card,
  .queue-row,
  .preset-button,
  :deep(.portfolio-table .el-table__body tr > td.el-table__cell),
  :deep(.action-cell .action-link) {
    transition: none;
  }
}
</style>

<style scoped>.command-avatar{background:linear-gradient(135deg,#2865a1,#144c6b)}.command-control{width:150px}.overview-page{min-width:0}.portfolio-summary-value{overflow-wrap:anywhere}.position-drawer-note{overflow-wrap:anywhere}@media(max-width:480px){.portfolio-summary-dashboard{grid-template-columns:repeat(3,minmax(0,1fr));padding:14px 10px}.portfolio-summary-metric{padding:6px 7px}.portfolio-summary-value{font-size:clamp(16px,4.5vw,20px);white-space:normal;overflow-wrap:anywhere}.portfolio-summary-meta{white-space:normal;overflow-wrap:anywhere}.command-table-controls{min-width:0}.command-control{width:140px}}</style>

<style scoped>.valuation-notice{font-size:12px;line-height:1.6;color:#a5bad3}.valuation-notice a{color:#75d5ff}.valuation-stale{margin:0 0 12px;color:#e7bd79;font-size:12px;line-height:1.5}.command-rows-scroll{min-width:0;overflow-x:auto}</style>
<style scoped>
.distribution-section{margin:16px 0 12px;border:1px solid rgba(112,202,255,.14);border-radius:20px;background:linear-gradient(135deg,rgba(12,27,52,.92),rgba(8,19,38,.92));overflow:hidden}
.distribution-toggle{display:flex;width:100%;align-items:end;justify-content:space-between;gap:16px;padding:15px 16px;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer}
.distribution-toggle span{display:grid;min-width:0;gap:4px}.distribution-toggle small,.distribution-grid article>small{color:#7ccfff;font-size:10px;font-style:normal;font-weight:800;letter-spacing:.13em}.distribution-toggle strong{color:#edf7ff;font-size:16px}.distribution-toggle em{color:#829ab8;font-size:11px;font-style:normal;line-height:1.45}.distribution-toggle b{flex:none;color:#75d5ff;font-size:12px}.distribution-toggle:focus-visible{outline:2px solid #75d5ff;outline-offset:-3px}
.distribution-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:0 16px 16px}.distribution-grid article{min-width:0;padding:14px;border:1px solid rgba(112,202,255,.11);border-radius:14px;background:rgba(255,255,255,.025)}.distribution-grid article>strong{display:block;margin:5px 0 13px;color:#e9f5ff;font-size:14px}.distribution-grid p{color:#91a7c1;font-size:12px;line-height:1.5}.distribution-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;margin-top:10px;color:#b7cde5;font-size:12px}.distribution-item span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.distribution-item b{color:#e8f4ff;font-variant-numeric:tabular-nums}.distribution-track{grid-column:1/-1;height:6px;overflow:hidden;border-radius:999px;background:rgba(112,202,255,.11)}.distribution-track i{display:block;height:100%;max-width:100%;border-radius:999px;background:linear-gradient(90deg,#3288d8,#66ceff)}
.distribution-history{grid-column:1/-1;min-width:0;border:1px solid rgba(112,202,255,.11);border-radius:14px;background:rgba(255,255,255,.025);overflow:hidden}.distribution-history :deep(.snapshot-history){border:0;background:transparent;box-shadow:none}.distribution-history-note{margin:0;padding:0 16px 14px}.distribution-history-note a{color:#75d5ff}
@media(max-width:640px){.distribution-grid{grid-template-columns:1fr}.distribution-toggle{display:grid;grid-template-columns:1fr;align-items:start}.distribution-toggle em{max-width:none}.distribution-toggle b{display:block;width:100%;margin-top:6px;padding:9px 12px;border-radius:11px;background:linear-gradient(90deg,#4376f5,#40bdf1);color:#fff;text-align:center}}
</style>
