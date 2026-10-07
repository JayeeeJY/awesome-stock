<template>
  <div class="accounts-page">
    <div class="page-header">
      <div><h2 class="page-title">账户管理</h2><p class="page-subtitle">把不同币种和账户拆成独立账本，先看资金落点，再看单只股票。</p></div>
      <div class="page-actions"><PortfolioFx @saved="load" /><el-button type="primary" :icon="Plus" @click="openDialog()">新增账户</el-button></div>
    </div>
    <AppDataState v-if="loading && !loaded" tone="loading" title="正在读取账户账本" description="正在汇总账户、币种和持仓资产。" />
    <AppDataState v-else-if="error" :tone="accounts.length ? 'stale' : 'error'" title="账户信息暂未更新" :description="error" action-label="重新加载" @action="load" />
    <AppDataState v-else-if="loaded && !accounts.length" tone="empty" title="还没有投资账户" description="先建立一个资金账户和期初现金，再录入真实成交。" action-label="新增账户" @action="openDialog()" />
    <el-alert v-if="snapshot && !snapshotCurrent" title="估值日期已变化，正在重新核对；更新完成前不显示旧估值。" type="warning" :closable="false" />
    <section v-if="accounts.length" class="summary-grid">
      <article class="summary-card"><span class="summary-label">账户数量</span><b class="summary-value">{{ accounts.length }}</b><small>{{ positionCount }} 个持仓</small></article>
      <article v-for="currency in currencies" :key="currency" class="summary-card"><span class="summary-label">{{ currency }} 账本</span><b class="summary-value">{{ accounts.filter(a => a.currency === currency).length }}</b><small>{{ currencyValue(currency) }} USD · 持仓市值</small></article>
      <article class="summary-card"><span class="summary-label">主账本</span><b class="summary-value">{{ base?.accounts.find(a=>a.account_id===base?.lead_account_id)?.name || '—' }}</b><small v-if="leadAccount">{{ assetShare(leadAccount) }} · {{ formatMoney(usdValue(leadAccount)) }} USD</small><small v-else>{{ base?.holdings_complete ? '暂无持仓' : '缺少有效价格或汇率' }}</small></article>
    </section>
    <section v-if="accounts.length" class="book-grid">
      <article v-for="account in orderedAccounts" :key="account.id" class="book-card">
        <div class="book-head"><div><div class="book-name">{{ account.name }}</div><div class="book-meta">{{ account.broker || '手工事实账本' }} · {{ account.cost_method === 'fifo' ? 'FIFO' : '加权平均' }}成本</div></div><el-tag size="small" :type="account.currency === 'USD' ? 'success' : 'warning'" effect="plain">{{ account.currency }}</el-tag></div>
        <div class="book-main"><div class="book-value">{{ formatMoney(usdValue(account)) }} USD</div><div class="book-native">{{ formatMoney(holdingsValue(account)) }} {{ account.currency }} · {{ !snapshotCurrent ? '等待更新估值' : account.valuation_complete ? '按已记录价格' : '缺少有效价格' }}</div></div>
        <div class="book-bar" :aria-label="'美元持仓占比 '+assetShare(account)"><span :style="{width:assetShare(account)==='—'?'0%':assetShare(account)}"></span></div>
        <div class="book-foot"><span>美元持仓占比 {{ assetShare(account) }}</span><span>现金 {{ money(account.cash) }} {{ account.currency }}</span></div>
        <div class="book-foot"><span>{{ livePositions(account).length }} 个持仓</span><el-tooltip content="原币已实现与未实现收益按当前记录汇率折算；不包含历史汇兑损益。"><span class="mono converted-return">折算收益 {{ formatMoney(converted(account)?.total_return_at_current_fx_usd) }} USD</span></el-tooltip></div>
        <div class="book-signal"><span>第一大持仓 {{ leading(account)?.symbol || '—' }}</span><span>持仓占比 {{ leadingShare(account) }}</span></div>
        <p v-if="account.currency!=='USD'" class="form-help fx-status">{{ fxStatus(account) }}</p>
        <p v-if="!account.valuation_complete" class="form-help">{{ account.positions.filter(p=>p.quote_status==='missing').length }} 项缺价 · {{ account.positions.filter(p=>p.quote_status==='stale').length }} 项价格过期</p>
      </article>
    </section>
    <p v-if="accounts.length" class="form-help">折算收益为原币已实现与未实现收益按当前记录汇率换算，不包含历史汇兑损益；原币收益保留在下表供核对。</p>
    <el-table v-if="accounts.length" :data="orderedAccounts" v-loading="loading" stripe style="width:100%" aria-label="账户账本">
      <el-table-column prop="name" label="账户名称" min-width="180" /><el-table-column prop="broker" label="券商" min-width="140"><template #default="{row}">{{ row.broker||'—' }}</template></el-table-column>
      <el-table-column prop="currency" label="基础货币" width="110"><template #default="{row}"><el-tag size="small" effect="plain">{{ row.currency }}</el-tag></template></el-table-column>
      <el-table-column label="持仓数量" width="110" align="right"><template #default="{row}">{{ livePositions(row).length }}</template></el-table-column>
      <el-table-column label="美元持仓市值" min-width="170" align="right"><template #default="{row}">{{ formatMoney(base?.accounts.find(a=>a.account_id===row.id)?.holdings_value_usd ?? null) }} USD</template></el-table-column>
      <el-table-column label="原币持仓市值" min-width="170" align="right"><template #default="{row}"><span class="account-native-value">{{ formatMoney(holdingsValue(row)) }} {{ row.currency }}</span></template></el-table-column>
      <el-table-column label="折算收益（USD）" min-width="180" align="right"><template #default="{row}"><el-tooltip content="原币账本收益按当前记录汇率折算；不包含历史汇兑损益。"><span>{{ formatMoney(converted(row)?.total_return_at_current_fx_usd) }} USD</span></el-tooltip></template></el-table-column>
      <el-table-column label="总收益（原币）" min-width="170" align="right"><template #default="{row}"><span class="account-total-return">{{ formatMoney(totalReturn(row)) }} {{ row.currency }}</span></template></el-table-column>
      <el-table-column label="第一大持仓" min-width="140"><template #default="{row}"><span class="account-leading">{{ leading(row)?.symbol||'—' }}</span></template></el-table-column>
      <el-table-column label="期初现金" min-width="160" align="right"><template #default="{row}">{{ money(row.opening_cash) }}</template></el-table-column>
      <el-table-column label="账本现金" min-width="160" align="right"><template #default="{row}">{{ money(row.cash) }}</template></el-table-column>
      <el-table-column label="成本计算" width="140"><template #default="{row}">{{ row.cost_method === 'fifo' ? 'FIFO' : '加权平均' }}</template></el-table-column>
      <el-table-column label="操作" width="150" fixed="right"><template #default="{row}"><el-button link type="primary" @click="openDialog(row)">编辑</el-button><el-button link type="danger" :disabled="deleting" @click="deleteAccount(row)">删除</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="editing ? '编辑账户' : '新增账户'" width="480px" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="closeDialog">
      <el-alert v-if="saveError" :title="saveError" type="error" :closable="false" show-icon />
      <el-form label-width="100px" label-position="left" @submit.prevent="save">
        <el-form-item label="账户名称"><el-input v-model="form.name" placeholder="如：我的美股账户" maxlength="80" :disabled="saving" /></el-form-item>
        <el-form-item label="券商"><el-input v-model="form.broker" maxlength="80" placeholder="选填，仅用于识别账户" :disabled="saving" /></el-form-item>
        <el-form-item label="基础货币"><el-select v-model="form.currency" style="width:100%" :disabled="saving || !!editing"><el-option v-for="currency in ['USD','HKD','CNY','JPY','EUR','GBP']" :key="currency" :label="currency" :value="currency" /></el-select></el-form-item>
        <el-form-item label="期初现金"><el-input v-model="form.opening_cash" inputmode="decimal" placeholder="0" :disabled="saving || !!editing" /></el-form-item>
        <el-form-item label="成本计算"><el-radio-group v-model="form.cost_method" :disabled="saving || !!editing"><el-radio value="fifo">FIFO</el-radio><el-radio value="avg">加权平均</el-radio></el-radio-group></el-form-item>
        <p class="form-help">期初现金、币种和成本方式保存后不可直接改写；后续入金、出金单独记账。</p>
      </el-form>
      <template #footer><el-button :disabled="saving" @click="closeDialog">取消</el-button><el-button type="primary" :loading="saving" @click="save">{{ editing ? '保存修改' : '创建' }}</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {valuationIsCurrent} from '@/utils/valuationDate'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {registerPageMaterial} from '@/api/pageMaterial'
import PortfolioFx from '@/components/PortfolioFx.vue'
import AppDataState from '@/components/Global/AppDataState.vue'
import { request, accountOperation, type Account } from '@/api/owner'
import { operationCache, type ValuedAccount } from '@/api/business'
import { money as formatMoney, sum, percent, compare } from '@/utils/decimal'
interface BaseValuation {evaluated_on:string;evaluated_market_dates:Record<string,string>;native_accounts:ValuedAccount[];lead_account_id:string|null;holdings_complete:boolean;total_holdings_usd:string|null;accounts:{account_id:string;name:string;holdings_value_usd:string|null;total_return_at_current_fx_usd:string|null;fx_status:string;fx_evidence:{as_of:string;expires_on:string;source:string;revision:number}|null}[]}
const snapshot=ref<BaseValuation|null>(null),clockNow=ref(Date.now())
const snapshotCurrent=computed(()=>valuationIsCurrent(snapshot.value,clockNow.value))
const base=computed(()=>snapshotCurrent.value?snapshot.value:null)
let refreshTimer:ReturnType<typeof setInterval>|undefined
function refreshDate(){
  if(document.visibilityState==='hidden')return
  clockNow.value=Date.now()
  if(snapshot.value&&!snapshotCurrent.value)void load()
}
const accounts = ref<ValuedAccount[]>([]), loading = ref(false), loaded = ref(false), error = ref('')
const dialog = ref(false), saving = ref(false), saveError = ref('')
const deleting=ref(false), deleteOperations=operationCache()
const editing=ref<ValuedAccount|null>(null), editOperations=operationCache()
let baseline=''
const form = reactive({name:'',broker:'',currency:'USD',opening_cash:'0',cost_method:'fifo' as 'fifo' | 'avg'})
let pending: ReturnType<typeof accountOperation> | undefined
const dirty = computed(() => dialog.value && JSON.stringify(form)!==baseline)
const livePositions = (account: Account) => account.holdings.filter(p => !/^0(?:\.0+)?$/.test(p.quantity))
const currencies = computed(() => ['USD','HKD',...['CNY','JPY','EUR','GBP'].filter(c=>accounts.value.some(a=>a.currency===c))])
const leadAccount=computed(()=>accounts.value.find(a=>a.id===base.value?.lead_account_id))
function currencyValue(currency:string) {
  const group=accounts.value.filter(a=>a.currency===currency)
  return snapshotCurrent.value&&group.every(a=>usdValue(a)!==null)?formatMoney(sum(group.map(a=>usdValue(a)!))):'—（估值不完整）'
}
function converted(account:ValuedAccount){return base.value?.accounts.find(a=>a.account_id===account.id)}
function usdValue(account:ValuedAccount){return converted(account)?.holdings_value_usd??null}
const orderedAccounts=computed(()=>base.value?.holdings_complete?[...accounts.value].sort((a,b)=>compare(usdValue(b)!,usdValue(a)!)||a.id.localeCompare(b.id)):accounts.value)
function assetShare(account:ValuedAccount) {
  return base.value?.holdings_complete && base.value.total_holdings_usd!==null?percent(usdValue(account)!,base.value.total_holdings_usd):'—'
}
function fxStatus(account:ValuedAccount){
  if(!snapshotCurrent.value)return '等待更新汇率依据'
  const row=converted(account),e=row?.fx_evidence
  if(!e)return '缺少汇率依据'
  return `${row?.fx_status==='current'?'汇率有效':'汇率过期'} · ${e.as_of} 至 ${e.expires_on} · ${e.source} · v${e.revision}`
}
function holdingsValue(account:ValuedAccount) {
  return snapshotCurrent.value&&account.valuation_complete?sum(account.positions.map(p=>p.market_value!)):null
}
function totalReturn(account:ValuedAccount) {
  return snapshotCurrent.value&&account.valuation_complete?sum([...account.holdings.map(p=>p.realized_pnl),...account.positions.map(p=>p.unrealized_pnl!)]):null
}
function leading(account:ValuedAccount) {
  if(!snapshotCurrent.value||!account.valuation_complete)return null
  return [...account.positions].sort((a,b)=>compare(b.market_value!,a.market_value!)||a.symbol.localeCompare(b.symbol))[0]||null
}
function leadingShare(account:ValuedAccount) {
  const lead=leading(account)
  return lead?percent(lead.market_value!,sum(account.positions.map(p=>p.market_value!))):'—'
}
const unregisterMaterial=registerPageMaterial('/portfolio/accounts',()=>{
  clockNow.value=Date.now()
  if(loading.value||error.value||!loaded.value||!snapshotCurrent.value||!base.value)throw Error('账户估值尚未就绪，请先在账户页完成刷新。')
  return {
    scope:'account_valuation_snapshot',evaluated_on:base.value.evaluated_on,evaluated_market_dates:base.value.evaluated_market_dates,base_currency:'USD',
    holdings_complete:base.value.holdings_complete,total_holdings_usd:base.value.total_holdings_usd,
    lead_account_id:base.value.lead_account_id,
    accounts:orderedAccounts.value.map(a=>({
      id:a.id,name:a.name,broker:a.broker,currency:a.currency,cost_method:a.cost_method,
      cash:a.cash,holdings_value_native:holdingsValue(a),return_native:totalReturn(a),
      positions:a.positions,usd_valuation:converted(a),
    })),
    notice:'当前账户页估值快照；汇率为用户记录，缺失/过期不视为已核验。折算收益不包含历史汇兑损益。未包含逐笔成交、研究笔记、连接配置或密钥。',
  }
})
onBeforeUnmount(unregisterMaterial)
const positionCount = computed(() => accounts.value.reduce((n,a) => n + livePositions(a).length, 0))
// Formatting keeps all server decimal digits; no floating-point monetary arithmetic.
function money(value: string) { const [integer, decimal] = value.split('.'); return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (decimal ? '.' + decimal : '') }
async function load() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try { const valuation=await request<BaseValuation>('/api/v1/owner/base-valuation'); accounts.value=valuation.native_accounts; snapshot.value=valuation; loaded.value = true }
  catch (e) { error.value = e instanceof Error ? e.message : '获取账户失败' }
  finally { loading.value = false }
}
function openDialog(account?:ValuedAccount) {
  if (dialog.value) return
  editing.value=account||null
  Object.assign(form, account ? {name:account.name,broker:account.broker,currency:account.currency,opening_cash:account.opening_cash,cost_method:account.cost_method} : {name:'',broker:'',currency:'USD',opening_cash:'0',cost_method:'fifo'})
  baseline=JSON.stringify(form);pending=undefined;editOperations.clear();saveError.value='';dialog.value=true
}
async function deleteAccount(account:ValuedAccount) {
  if(deleting.value)return
  deleting.value=true
  try {
    try { await ElMessageBox.confirm(`删除账户“${account.name}”？仅允许删除没有资金及业务历史的空账户；删除后不会影响其他账户。`,'删除空账户',{confirmButtonText:'删除账户',cancelButtonText:'取消',type:'warning'}) } catch { return }
    await request('/api/v1/owner/accounts','DELETE',deleteOperations.body(account.id,{id:account.id,revision:account.revision}))
    ElMessage.success('空账户已删除');await load()
  } catch(e) { ElMessage.error(e instanceof Error?e.message:'删除失败，请重试') }
  finally {deleting.value=false}
}
async function canDiscard() {
  if (saving.value) return false
  if (!dirty.value) return true
  try { await ElMessageBox.confirm('未保存的账户信息将丢失。是否放弃？', '放弃编辑', {confirmButtonText:'放弃',cancelButtonText:'继续编辑',type:'warning'}); return true }
  catch { return false }
}
async function closeDialog() { if (await canDiscard()) dialog.value = false }
async function save() {
  if (saving.value) return
  saveError.value = ''
  if (!form.name.trim() || !/^\d{1,12}(?:\.\d{1,8})?$/.test(form.opening_cash)) { saveError.value = '请填写账户名称；期初现金最多 12 位整数、8 位小数，不能使用科学计数法。'; return }
  const values = {...form, name:form.name.trim()}
  if (!pending || ['name','broker','currency','opening_cash','cost_method'].some(key => pending![key as keyof typeof values] !== values[key as keyof typeof values])) pending = accountOperation(values)
  saving.value = true
  try { if(editing.value)await request('/api/v1/owner/account-edit','POST',editOperations.body('account',{id:editing.value.id,revision:editing.value.revision,name:form.name.trim(),broker:form.broker.trim()}));else await request('/api/v1/owner/accounts','POST',pending); dialog.value = false; pending = undefined; ElMessage.success(editing.value?'账户已更新':'账户已创建'); await load() }
  catch (e) { saveError.value = e instanceof Error ? e.message : '创建失败，输入已保留。' }
  finally { saving.value = false }
}
const preventClose = (event: BeforeUnloadEvent) => { if (dirty.value || saving.value) { event.preventDefault(); event.returnValue = '' } }
onBeforeRouteLeave(canDiscard)
onMounted(() => { load(); window.addEventListener('beforeunload',preventClose);window.addEventListener('focus',refreshDate);document.addEventListener('visibilitychange',refreshDate);refreshTimer=setInterval(refreshDate,30000) })
onBeforeUnmount(() => {window.removeEventListener('beforeunload',preventClose);window.removeEventListener('focus',refreshDate);document.removeEventListener('visibilitychange',refreshDate);if(refreshTimer)clearInterval(refreshTimer)})
</script>

<style scoped>
/* Fixed cells must mask the scrolling columns underneath in both themes. */
.accounts-page :deep(.el-table .el-table__cell.el-table-fixed-column--right) {
  background: #0c1b34 !important;
  background: rgb(from var(--el-bg-color-overlay) r g b / 1) !important;
}

.accounts-page {
  padding: 24px 28px 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.page-title {
  margin: 0;
  font-size: 30px;
  font-weight: 800;
}

.page-subtitle {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.summary-grid,
.book-grid {
  display: grid;
  gap: 14px;
}

.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-card,
.book-card {
  border-radius: 20px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color-overlay);
  box-shadow: 0 16px 44px rgba(17, 32, 62, 0.08);
}

.summary-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--el-text-color-secondary);
}

.summary-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.summary-card small {
  color: var(--el-text-color-secondary);
}

.book-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.book-card {
  overflow-wrap: anywhere;
  min-width: 0;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.book-head,
.book-foot,
.book-signal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.book-name {
  font-size: 16px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.book-meta,
.book-foot,
.book-signal {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.book-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.book-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.book-native {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.book-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(117, 147, 184, 0.12);
  overflow: hidden;
}

.book-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #48b8ff, #2d78ff);
}

.mono {
  font-variant-numeric: tabular-nums;
}

.is-profit {
  color: #0ca678;
}

.is-loss {
  color: #f03e3e;
}

@media (max-width: 1200px) {
  .summary-grid,
  .book-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .accounts-page {
    padding: 18px 16px 28px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid,
  .book-grid {
    grid-template-columns: 1fr;
  }

  .book-main,
  .book-foot,
  .book-signal {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

<style scoped>
/* Fixed cells must mask the scrolling columns underneath in both themes. */
.accounts-page :deep(.el-table .el-table__cell.el-table-fixed-column--right) {
  background: #0c1b34 !important;
  background: rgb(from var(--el-bg-color-overlay) r g b / 1) !important;
}

.book-main{flex-direction:column;align-items:flex-start;flex-wrap:nowrap}.book-value{max-width:100%}.book-name{overflow-wrap:anywhere}.book-value{font-size:clamp(20px,2vw,28px);overflow-wrap:anywhere}.form-help{color:var(--el-text-color-secondary);line-height:1.6}.accounts-page{min-width:0}
</style>
