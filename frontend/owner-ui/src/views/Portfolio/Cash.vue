<template>
  <div class="accounts-page">
    <div class="page-header"><div><h2 class="page-title">资金流水</h2><p class="page-subtitle">分别记录入金、出金与交易现金变化，核对每个账户的现金余额。</p></div><div><el-button @click="historyOpen=true">修改历史</el-button><el-button type="primary" :disabled="!accounts.length" @click="open()">记录出入金</el-button></div></div>
    <AppDataState v-if="error" :tone="accounts.length?'stale':'error'" title="资金账本暂未更新" :description="error" action-label="重新加载" @action="load" />
    <AppDataState v-else-if="loading&&!loaded" tone="loading" title="正在读取资金账本" />
    <AppDataState v-else-if="loaded&&!accounts.length" tone="empty" title="先建立资金账户" action-label="账户管理" @action="router.push('/portfolio/accounts')" />
    <section class="book-grid"><article v-for="a in accounts" :key="a.id" class="book-card"><div class="book-head"><div><div class="book-name">{{ a.name }}</div><div class="book-meta">{{ a.currency }} · 账本现金</div></div><el-tag size="small" effect="plain">{{ a.currency }}</el-tag></div><div class="book-main"><div class="book-value" :title="a.cash">{{ money(a.cash) }}</div></div><div class="book-foot"><span>期初 {{ money(a.opening_cash) }}</span><span>交易现金变化 {{ money(a.trade_cash_change) }}</span></div><div class="book-signal"><span>入金 {{ money(a.deposits) }}</span><span>出金 {{ money(a.withdrawals) }}</span></div></article></section>
    <div class="cash-filter"><el-select v-model="accountId" aria-label="筛选资金账户" placeholder="全部账户" clearable style="width:220px"><el-option v-for="a in accounts" :key="a.id" :label="a.name+' · '+a.currency" :value="a.id" /></el-select><el-button :loading="loading" @click="load">刷新</el-button></div>
    <el-table class="desktop-cash-table" :data="rows" stripe v-loading="loading" aria-label="资金流水"><el-table-column label="发生时间" width="180"><template #default="{row}">{{ new Date(row.occurred_at).toLocaleString('zh-CN') }}</template></el-table-column><el-table-column label="账户" min-width="170"><template #default="{row}">{{ name(row.account_id) }}</template></el-table-column><el-table-column label="方向" width="90"><template #default="{row}"><el-tag :type="row.direction==='deposit'?'success':'warning'">{{ row.direction==='deposit'?'入金':'出金' }}</el-tag></template></el-table-column><el-table-column prop="amount" label="金额" min-width="130" align="right" /><el-table-column prop="note" label="备注" min-width="200" /><el-table-column label="操作" width="150" fixed="right"><template #default="{row}"><el-button link type="primary" :disabled="saving" @click="open(row)">更正</el-button><el-popconfirm title="删除这笔资金记录？系统将核对全部后续记录，历史版本会保留。" confirm-button-text="删除" cancel-button-text="取消" @confirm="remove(row)"><template #reference><el-button link type="danger" :disabled="saving">删除</el-button></template></el-popconfirm></template></el-table-column></el-table>
    <section class="mobile-cash-list" aria-label="资金流水记录"><article v-for="row in rows" :key="row.id" class="mobile-cash-card"><div class="mobile-cash-head"><strong>{{ name(row.account_id) }}</strong><el-tag size="small" :type="row.direction==='deposit'?'success':'warning'">{{ row.direction==='deposit'?'入金':'出金' }}</el-tag></div><div class="mobile-cash-main"><b>{{ money(row.amount) }} {{ accounts.find(a=>a.id===row.account_id)?.currency||'' }}</b><time :datetime="row.occurred_at">{{ new Date(row.occurred_at).toLocaleString('zh-CN') }}</time></div><p v-if="row.note">{{ row.note }}</p><div class="mobile-cash-actions"><el-button type="primary" text :disabled="saving" @click="open(row)">更正</el-button><el-popconfirm title="删除这笔资金记录？系统将核对全部后续记录，历史版本会保留。" confirm-button-text="删除" cancel-button-text="取消" @confirm="remove(row)"><template #reference><el-button type="danger" text :disabled="saving">删除</el-button></template></el-popconfirm></div></article></section>
    <el-dialog v-model="dialog" :title="editing?'更正资金流水':'记录出入金'" width="min(520px, calc(100vw - 24px))" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="close">
      <el-alert v-if="saveError" :title="saveError" type="error" :closable="false" />
      <el-form label-position="top"><el-form-item label="资金账户"><el-select v-model="form.account_id" :disabled="saving||!!editing" style="width:100%"><el-option v-for="a in accounts" :key="a.id" :label="a.name+' · '+a.currency" :value="a.id" /></el-select></el-form-item><el-form-item label="方向"><el-radio-group v-model="form.direction" :disabled="saving"><el-radio value="deposit">入金</el-radio><el-radio value="withdrawal">出金</el-radio></el-radio-group></el-form-item><el-form-item label="金额"><el-input v-model="form.amount" inputmode="decimal" :disabled="saving" /></el-form-item><el-form-item label="发生时间"><el-input v-model="form.occurred_at" type="datetime-local" step="1" :disabled="saving" /></el-form-item><el-form-item label="备注"><el-input v-model="form.note" type="textarea" maxlength="1000" :disabled="saving" /></el-form-item></el-form>
      <p class="form-help">仅记录已经发生的资金事实。若任何后续时点透支，保存会被拒绝。</p>
      <template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
    <el-drawer v-model="historyOpen" title="资金修改历史" size="min(740px, 95vw)"><el-table :data="versions" stripe><el-table-column label="账户" min-width="160"><template #default="{row}">{{ name(row.account_id) }}</template></el-table-column><el-table-column prop="revision" label="版本" width="70" /><el-table-column prop="amount" label="金额" width="140" /><el-table-column label="状态" width="100"><template #default="{row}">{{ row.deleted?'已删除':'已保存' }}</template></el-table-column><el-table-column prop="occurred_at" label="发生时间" width="220" /><el-table-column prop="note" label="备注" min-width="170" /></el-table><p class="form-help">删除会保留审计与历史版本，不等于隐私擦除。</p></el-drawer>
  </div>
</template>
<script setup lang="ts">
import { computed,onMounted,onBeforeUnmount,reactive,ref } from 'vue'
import { useRouter,onBeforeRouteLeave } from 'vue-router'
import { ElDrawer,ElMessage,ElMessageBox } from 'element-plus'
import {registerPageMaterial} from '@/api/pageMaterial'
import AppDataState from '@/components/Global/AppDataState.vue'
import { request,type Account } from '@/api/owner'
import { operationCache } from '@/api/business'
import { money } from '@/utils/decimal'
interface Cash {id:string;revision:number;account_id:string;direction:'deposit'|'withdrawal';amount:string;occurred_at:string;note:string;event_order:number;deleted:boolean;updated_at:string}
interface CashAccount extends Account {cash_flows:Cash[];deposits:string;withdrawals:string;trade_cash_change:string}
const router=useRouter(),accounts=ref<CashAccount[]>([]),versions=ref<Cash[]>([]),accountId=ref(''),loading=ref(false),loaded=ref(false),error=ref(''),saveError=ref(''),saving=ref(false),dialog=ref(false),historyOpen=ref(false),editing=ref<Cash|null>(null)
const form=reactive({account_id:'',direction:'deposit',amount:'',occurred_at:'',note:''}),operations=operationCache()
let id='',baseline=''
const dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline)
const rows=computed(()=>accounts.value.flatMap(a=>a.cash_flows).filter(r=>!accountId.value||r.account_id===accountId.value).sort((a,b)=>b.occurred_at.localeCompare(a.occurred_at)||b.event_order-a.event_order))
const name=(id:string)=>{const a=accounts.value.find(a=>a.id===id);return a?a.name+' · '+a.currency:id}
const unregisterMaterial=registerPageMaterial('/portfolio/cash',(selection)=>{
  if(selection!=='current'&&selection!=='history')throw Error('请先选择资金材料范围。')
  const historical=selection==='history'
  if(loading.value||saving.value||error.value||!loaded.value||dialog.value)throw Error('请先完成资金页加载并关闭编辑窗口，再载入材料。')
  const selected=historical?accounts.value:accounts.value.filter(a=>!accountId.value||a.id===accountId.value)
  return {scope:historical?'cash_revision_history':'filtered_cash_flows',account_filter:historical?null:accountId.value||null,
    accounts:selected.map(a=>({id:a.id,name:a.name,currency:a.currency,opening_cash:a.opening_cash,cash:a.cash,deposits:a.deposits,withdrawals:a.withdrawals,trade_cash_change:a.trade_cash_change})),
    records:historical?versions.value:rows.value,
    notice:historical?'资金修改历史，可能包含旧版本和已删除记录，不能重复计入当前余额。':'当前筛选的已保存资金流水；不含逐笔成交、历史版本或未保存输入。不同币种不能直接合计。'}
})
onBeforeUnmount(unregisterMaterial)
function localTime(value?:string){const d=value?new Date(value):new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,19)}
async function load(){if(loading.value)return;loading.value=true;error.value='';try{const [ledger,history]=await Promise.all([request<{accounts:CashAccount[]}>('/api/v1/owner/ledger'),request<{versions:Cash[]}>('/api/v1/owner/cash-flows')]);accounts.value=ledger.accounts;versions.value=history.versions;loaded.value=true}catch(e){error.value=e instanceof Error?e.message:'读取失败'}finally{loading.value=false}}
function open(row?:Cash){if(saving.value)return;editing.value=row||null;id=row?.id||crypto.randomUUID();operations.clear();saveError.value='';Object.assign(form,row?{account_id:row.account_id,direction:row.direction,amount:row.amount,occurred_at:localTime(row.occurred_at),note:row.note}:{account_id:accountId.value||accounts.value[0]?.id||'',direction:'deposit',amount:'',occurred_at:localTime(),note:''});baseline=JSON.stringify(form);dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的资金记录？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){if(saving.value)return;saveError.value='';if(!/^\d{1,12}(?:\.\d{1,8})?$/.test(form.amount)||!form.occurred_at||!Number.isFinite(new Date(form.occurred_at).getTime())){saveError.value='请核对金额与发生时间；金额最多12位整数、8位小数。';return}saving.value=true;try{await request('/api/v1/owner/cash-flows','POST',operations.body('save',{...form,id,revision:editing.value?.revision||0,occurred_at:editing.value&&form.occurred_at===localTime(editing.value.occurred_at)?editing.value.occurred_at:new Date(form.occurred_at).toISOString()}));dialog.value=false;ElMessage.success('资金记录已保存');await load()}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}}
async function remove(row:Cash){if(saving.value)return;saving.value=true;try{await request('/api/v1/owner/cash-flows','DELETE',operations.body('delete:'+row.id,{id:row.id,revision:row.revision}));ElMessage.success('记录已删除，历史版本保留');await load()}catch(e){ElMessage.error(e instanceof Error?e.message:'删除失败')}finally{saving.value=false}}
const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}}
onBeforeRouteLeave(discard);onMounted(()=>{load();window.addEventListener('beforeunload',beforeUnload)});onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>

<style scoped>
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

<style scoped>.accounts-page{min-width:0}.book-name,.book-value{overflow-wrap:anywhere}.book-value{font-size:24px}.cash-filter{display:flex;gap:12px;flex-wrap:wrap}.form-help{color:var(--el-text-color-secondary);line-height:1.6}input[type="datetime-local"]{min-width:0}</style>
<style scoped>
.mobile-cash-list{display:none}
@media(max-width:768px){
  .desktop-cash-table{display:none}
  .mobile-cash-list{display:grid;gap:12px}
  .mobile-cash-card{min-width:0;padding:15px;border:1px solid var(--el-border-color-lighter);border-radius:16px;background:var(--el-bg-color-overlay)}
  .mobile-cash-head,.mobile-cash-main,.mobile-cash-actions{display:flex;align-items:center;justify-content:space-between;gap:10px}
  .mobile-cash-head strong{min-width:0;color:var(--el-text-color-primary);font-size:14px;overflow-wrap:anywhere}
  .mobile-cash-main{align-items:flex-start;flex-direction:column;margin-top:13px}
  .mobile-cash-main b{color:var(--el-text-color-primary);font-size:20px;font-variant-numeric:tabular-nums}
  .mobile-cash-main time,.mobile-cash-card p{color:var(--el-text-color-secondary);font-size:12px;line-height:1.5}
  .mobile-cash-card p{margin:10px 0 0;overflow-wrap:anywhere}
  .mobile-cash-actions{justify-content:flex-end;margin-top:12px;padding-top:10px;border-top:1px solid var(--el-border-color-lighter)}
}
</style>
