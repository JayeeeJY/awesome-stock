<template>
  <div class="trades-page">
    <div class="page-header"><div><h2 class="page-title">交易流水</h2><p class="page-subtitle">记录已经发生的成交，按账户、币种与时间核对投资事实。</p></div><div class="page-actions"><el-button @click="router.push('/review')">查看复盘</el-button><el-button type="primary" :icon="Plus" :disabled="!accounts.length" @click="open()">新增交易</el-button></div></div>
    <div class="filter-bar"><div class="filter-left">
      <el-select v-model="filters.account" clearable placeholder="全部账户" aria-label="筛选账户" style="width:160px"><el-option v-for="a in accounts" :key="a.id" :label="a.name" :value="a.id" /></el-select>
      <el-input v-model="filters.symbol" clearable placeholder="搜索标的" aria-label="搜索标的" style="width:130px" />
      <el-select v-model="filters.side" clearable placeholder="买入 / 卖出" aria-label="筛选方向" style="width:130px"><el-option label="买入" value="buy" /><el-option label="卖出" value="sell" /></el-select>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div><div class="filter-right"><el-button @click="router.push('/settings')">导入与导出</el-button></div></div>
    <AppDataState v-if="loading && !loaded" tone="loading" title="正在读取交易流水" />
    <AppDataState v-else-if="error" :tone="trades.length ? 'stale':'error'" title="交易信息暂未更新" :description="error" action-label="重新加载" @action="load" />
    <AppDataState v-else-if="!accounts.length && loaded" tone="empty" title="先建立资金账户" description="为不同币种建立独立账本，再录入成交。" action-label="账户管理" @action="router.push('/portfolio/accounts')" />
    <AppDataState v-else-if="!filtered.length && loaded" tone="empty" title="当前范围没有交易记录" description="调整筛选，或录入已发生的成交。普通成交不强制填写决策理由。" />
    <div v-if="trades.length" class="summary-bar"><span>当前范围 <b>{{ filtered.length }}</b> 笔成交</span><span>买入 <b class="pl-pos">{{ filtered.filter(t=>t.side==='buy').length }}</b></span><span>卖出 <b class="pl-neg">{{ filtered.filter(t=>t.side==='sell').length }}</b></span><span>金额按原币种记录，不跨币种相加</span></div>
    <el-table v-if="filtered.length" :data="paged" stripe v-loading="loading" aria-label="交易流水">
      <el-table-column label="成交时间" width="180"><template #default="{row}">{{ new Date(row.executed_at).toLocaleString('zh-CN') }}</template></el-table-column>
      <el-table-column prop="symbol" label="标的" width="100"><template #default="{row}"><span class="ticker-cell">{{ row.symbol }}</span></template></el-table-column>
      <el-table-column label="账户" min-width="160"><template #default="{row}"><el-tag size="small" type="info">{{ accountName(row.account_id) }}</el-tag></template></el-table-column>
      <el-table-column label="方向" width="80"><template #default="{row}"><el-tag size="small" :type="row.side==='buy'?'success':'danger'">{{ row.side==='buy'?'买入':'卖出' }}</el-tag></template></el-table-column>
      <el-table-column prop="quantity" label="数量" min-width="130" align="right" /><el-table-column prop="price" label="价格" min-width="130" align="right" /><el-table-column prop="fee" label="费用" min-width="100" align="right" />
      <el-table-column label="操作" width="180" fixed="right"><template #default="{row}"><el-button link type="primary" @click="open(row)">更正</el-button><el-button link :disabled="saving" @click="contextTrade=row.id">决策资格</el-button><el-popconfirm title="删除这笔成交？系统将重新核对全部后续记录，历史版本会保留。" confirm-button-text="删除" cancel-button-text="取消" @confirm="remove(row)"><template #reference><el-button link type="danger" :disabled="saving" >删除</el-button></template></el-popconfirm></template></el-table-column>
    </el-table>
    <el-pagination v-if="filtered.length>20" v-model:current-page="page" :page-size="20" :total="filtered.length" layout="total, prev, pager, next" />
    <TradeContext v-if="contextTrade" ref="contextPanel" :trade-id="contextTrade" @close="contextTrade=null"/>
    <el-dialog v-model="dialog" :title="editing?'更正交易':'新增交易'" width="min(760px, calc(100vw - 24px))" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="close">
      <el-alert v-if="saveError" :title="saveError" type="error" :closable="false" show-icon />
      <el-form class="trade-form" label-width="90px" label-position="left" @submit.prevent="save">
        <el-row :gutter="16"><el-col :xs="24" :sm="14"><el-form-item label="标的代码"><el-input v-model="form.symbol" placeholder="AAPL" maxlength="24" :disabled="saving" /></el-form-item></el-col><el-col :xs="24" :sm="10"><el-form-item label="方向"><el-radio-group v-model="form.side" :disabled="saving"><el-radio value="buy">买入</el-radio><el-radio value="sell">卖出</el-radio></el-radio-group></el-form-item></el-col></el-row>
        <el-form-item label="资金账户"><el-select v-model="form.account_id" style="width:100%" :disabled="saving||!!editing"><el-option v-for="a in accounts" :key="a.id" :label="a.name+' · '+a.currency" :value="a.id" /></el-select></el-form-item>
        <el-form-item label="成交时间"><el-input v-model="form.executed_at" type="datetime-local" step="1" :disabled="saving" /></el-form-item>
        <el-row :gutter="16"><el-col v-for="(label,key) in {quantity:'数量',price:'价格',fee:'费用'}" :key="key" :xs="24" :sm="8"><el-form-item :label="label"><el-input v-model="form[key]" inputmode="decimal" :disabled="saving" /></el-form-item></el-col></el-row>
        <p>保存时按实际成交时间校验全部后续现金和持仓。更正不会覆盖历史版本。</p>
      </el-form>
      <template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import TradeContext from './TradeContext.vue'
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {registerPageMaterial} from '@/api/pageMaterial'
import AppDataState from '@/components/Global/AppDataState.vue'
import { request, type Account, type Ledger, type Trade } from '@/api/owner'
const contextTrade=ref<string|null>(null),contextPanel=ref<InstanceType<typeof TradeContext>|null>(null)
const router=useRouter(), accounts=ref<Account[]>([]), loading=ref(false), loaded=ref(false), error=ref(''), saveError=ref(''), saving=ref(false), dialog=ref(false), editing=ref<Trade|null>(null), page=ref(1)
const filters=reactive({account:'',symbol:'',side:''}), form=reactive({account_id:'',symbol:'',side:'buy',quantity:'',price:'',fee:'0',executed_at:''})
let baseline='', pending: Record<string,unknown>|undefined, fingerprint=''
const deletionIds=new Map<string,string>()
const dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline)
const trades=computed(()=>accounts.value.flatMap(a=>a.trades).sort((a,b)=>b.executed_at.localeCompare(a.executed_at)||b.event_order-a.event_order))
const filtered=computed(()=>trades.value.filter(t=>(!filters.account||t.account_id===filters.account)&&(!filters.side||t.side===filters.side)&&t.symbol.includes(filters.symbol.trim().toUpperCase())))
const paged=computed(()=>filtered.value.slice((page.value-1)*20,page.value*20))
watch(filters,()=>page.value=1)
const accountName=(id:string)=>{const a=accounts.value.find(a=>a.id===id);return a?`${a.name} · ${a.currency}`:id}
const unregisterMaterial=registerPageMaterial('/portfolio/trades',()=>{
  if(loading.value||saving.value||error.value||!loaded.value||dialog.value||contextTrade.value)throw Error('请先完成交易页加载并关闭编辑或决策资格窗口，再载入材料。')
  const ids=new Set(paged.value.map(t=>t.account_id))
  return {scope:'filtered_trade_page',filters:{...filters,symbol:filters.symbol.trim().toUpperCase()},page:page.value,page_size:20,total_filtered:filtered.value.length,
    accounts:accounts.value.filter(a=>ids.has(a.id)).map(a=>({id:a.id,name:a.name,currency:a.currency,cost_method:a.cost_method})),
    records:paged.value,
    notice:'仅当前筛选结果的当前页已保存成交，不代表完整交易史；不含现金流水、持仓、研究笔记或未保存输入。不同币种不能直接合计。'}
})
onBeforeUnmount(unregisterMaterial)
function localTime(value?:string){const d=value?new Date(value):new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,19)}
async function load(){if(loading.value)return;loading.value=true;error.value='';try{accounts.value=(await request<Ledger>('/api/v1/owner/ledger')).accounts;loaded.value=true;page.value=Math.min(page.value,Math.max(1,Math.ceil(filtered.value.length/20)))}catch(e){error.value=e instanceof Error?e.message:'读取失败'}finally{loading.value=false}}
function open(t?:Trade){if(saving.value)return;editing.value=t||null;pending=undefined;fingerprint='';saveError.value='';Object.assign(form,t?{account_id:t.account_id,symbol:t.symbol,side:t.side,quantity:t.quantity,price:t.price,fee:t.fee,executed_at:localTime(t.executed_at)}:{account_id:accounts.value[0]?.id||'',symbol:'',side:'buy',quantity:'',price:'',fee:'0',executed_at:localTime()});baseline=JSON.stringify(form);dialog.value=true}
async function discard(){if(saving.value)return false;if(contextPanel.value&&!await contextPanel.value.close())return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('未保存的交易内容将丢失。是否放弃？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑',type:'warning'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){
 if(saving.value)return;saveError.value=''
 if(!form.account_id||!form.symbol.trim()||!['quantity','price','fee'].every(k=>/^\d{1,12}(?:\.\d{1,8})?$/.test(form[k as 'quantity']))||!form.executed_at||!Number.isFinite(new Date(form.executed_at).getTime())){saveError.value='请检查标的、账户、成交时间和数值格式。';return}
 const values={...form,symbol:form.symbol.trim().toUpperCase(),executed_at:editing.value&&form.executed_at===localTime(editing.value.executed_at)?editing.value.executed_at:new Date(form.executed_at).toISOString()}
 const next=JSON.stringify(values);if(!pending||fingerprint!==next){pending={...values,id:editing.value?.id||crypto.randomUUID(),revision:editing.value?.revision||0,operation_id:crypto.randomUUID()};fingerprint=next}
 saving.value=true;try{await request('/api/v1/owner/trades','POST',pending);dialog.value=false;pending=undefined;ElMessage.success('交易已保存');await load()}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}
}
async function remove(t:Trade){if(saving.value)return;saving.value=true;const key=t.id+':'+t.revision;const id=deletionIds.get(key)||crypto.randomUUID();deletionIds.set(key,id);try{await request('/api/v1/owner/trades','DELETE',{id:t.id,revision:t.revision,operation_id:id});deletionIds.delete(key);ElMessage.success('交易已删除，历史版本保留');await load()}catch(e){ElMessage.error(e instanceof Error?e.message:'删除失败')}finally{saving.value=false}}
const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}}
onBeforeRouteLeave(discard)
onMounted(()=>{load();window.addEventListener('beforeunload',beforeUnload)})
onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>

<style scoped>
.trades-page {
  padding: 20px 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 18px;
}

.page-title {
  margin: 0;
  font-size: 30px;
  font-weight: 800;
}

.page-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-left,
.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-bar {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--el-bg-color-overlay);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.review-card {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  background: linear-gradient(180deg, rgba(17, 37, 89, 0.025), rgba(17, 37, 89, 0.01));
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.review-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.review-card b {
  font-size: 20px;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.review-card small {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.review-notes {
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  background: #fff;
}

.review-notes-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.review-notes-list {
  margin: 10px 0 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--el-text-color-secondary);
}

.ticker-cell {
  font-weight: 600;
  font-family: monospace;
}

.note-cell {
  display: block;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
}

.reason-cell {
  display: block;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  color: var(--el-text-color-primary);
}

.reason-missing {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.decision-requirement-panel {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(64, 158, 255, 0.06), rgba(64, 158, 255, 0.02));
}

.decision-requirement-panel--required {
  border-color: rgba(245, 108, 108, 0.36);
  background: linear-gradient(180deg, rgba(245, 108, 108, 0.08), rgba(245, 108, 108, 0.02));
}

.decision-requirement-panel--suggest {
  border-color: rgba(230, 162, 60, 0.34);
  background: linear-gradient(180deg, rgba(230, 162, 60, 0.08), rgba(230, 162, 60, 0.02));
}

.decision-requirement-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.decision-requirement-eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.decision-requirement-head h3 {
  margin: 0;
  font-size: 16px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
}

.decision-requirement-head p:last-child,
.decision-requirement-footnote,
.decision-requirement-empty {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.decision-requirement-body {
  margin-top: 12px;
}

.decision-requirement-facts {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.decision-trigger-list {
  margin: 12px 0 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.decision-trigger-list li + li {
  margin-top: 6px;
}

.decision-trigger-list b {
  display: block;
  color: var(--el-text-color-primary);
}

.decision-mode-group {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.subtotal {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.pl-pos { color: #67C23A; }
.pl-neg { color: #F56C6C; }

@media (max-width: 1100px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .review-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .review-grid {
    grid-template-columns: 1fr;
  }

  .decision-requirement-head {
    flex-direction: column;
  }

  .decision-mode-group {
    align-items: flex-start;
  }
}
</style>

<style scoped>
@media (max-width:480px) {
  .trade-form :deep(.el-form-item){display:block;margin-bottom:12px}
  .trade-form :deep(.el-form-item__label){display:block;width:auto!important;height:auto;line-height:24px;text-align:left}
  .trade-form :deep(.el-form-item__content){margin-left:0!important;min-width:0}
  .trade-form :deep(input[type="datetime-local"]){min-width:0;font-size:12px}
}
</style>
