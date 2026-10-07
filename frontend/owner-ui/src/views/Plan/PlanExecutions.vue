<template>
 <section class="execution-section"><div class="execution-header"><h4>执行成交记录 · {{ active.length }} 笔</h4><PlanTrade :plan="plan" @changed="refresh"/><el-button v-if="!plan.archived" :disabled="busy" @click="open">关联已有成交</el-button><el-button :disabled="busy" @click="refresh">刷新执行记录</el-button></div>
 <p>关联已录入账本的实际成交，固定当时计划版本与步骤；不会再次写入成交，也不会自动把计划标记完成。</p><el-alert v-if="error" :title="error" type="error" :closable="false" />
 <ol class="plan-executions"><li v-for="(e,index) in active" :key="e.id"><div class="execution-item"><span class="exec-step">{{ index+1 }}</span><time class="exec-date" :datetime="e.trade.executed_at">{{ displayTime(e.trade.executed_at) }}</time><span class="exec-reason">{{ e.trade.side==='buy'?'买入':'卖出' }}</span><span class="exec-shares">{{ e.trade.quantity }} 股</span><span class="exec-price">@ {{ e.trade.price }} {{ e.trade.currency }}</span><span v-if="e.trade.side==='buy'" class="exec-amount">含费投入 {{ e.amount }} {{ e.trade.currency }}</span></div><p>{{ e.trade.account_name }} · 费用 {{ e.trade.fee }} · 计划 v{{ e.plan_revision }} 第 {{ e.step_index+1 }} 步：{{ e.step_text }}</p><p>{{ e.note }}</p><el-alert v-if="e.trade_changed" title="成交已修改或删除；此处保留关联时快照，请核对后撤销或重新关联。" type="warning" :closable="false"/><el-popconfirm title="撤销关联并保留历史？不会删除成交。" confirm-button-text="撤销关联" @confirm="archive(e)"><template #reference><el-button :disabled="busy">撤销关联</el-button></template></el-popconfirm></li></ol>
 <details><summary>已撤销关联（{{ archived.length }}）</summary><p v-for="e in archived" :key="e.id">{{ displayTime(e.trade.executed_at) }} · {{ e.trade.symbol }} {{ e.trade.quantity }} 股 · {{ e.step_text }} · {{ e.note }}</p></details>
 <el-dialog v-model="dialog" title="关联计划执行成交" width="min(600px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!busy" :close-on-press-escape="!busy"><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item label="执行步骤"><el-select v-model="step" :disabled="busy"><el-option v-for="(text,index) in plan.steps" :key="index" :value="index" :label="`${index+1}. ${text}`"/></el-select></el-form-item><el-form-item label="已录入成交"><el-select v-model="tradeId" :disabled="busy" style="width:100%"><el-option v-for="t in candidates" :key="t.id" :value="t.id" :label="`${t.account_name} · ${t.executed_at} · ${t.side==='buy'?'买入':'卖出'} ${t.quantity} @ ${t.price} ${t.currency}`"/></el-select></el-form-item><p v-if="!candidates.length">没有可关联的同标的成交，请先在交易流水录入实际成交。</p><el-form-item label="执行说明"><el-input v-model="note" type="textarea" maxlength="2000" :disabled="busy"/></el-form-item></el-form><template #footer><el-button :disabled="busy" @click="close">取消</el-button><el-button type="primary" :disabled="!tradeId||!note.trim()" :loading="busy" @click="save">确认关联</el-button></template></el-dialog>
 </section>
</template>
<script setup lang="ts">
import PlanTrade from './PlanTrade.vue'
import {computed,ref,watch,onBeforeUnmount} from 'vue'
import {onBeforeRouteLeave} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {request,type Trade} from '@/api/owner'
import {operationCache} from '@/api/business'
type T=Trade&{account_name:string;currency:string}
type E=import('./executionTypes').Execution
const props=defineProps<{plan:{id:string;revision:number;steps:string[];symbol:string;plan_type:string;archived:boolean;target?:{account_id:string}|null}}>(),data=ref<{executions:E[];trades:T[]}|null>(null),busy=ref(false),error=ref(''),saveError=ref(''),dialog=ref(false),step=ref(0),tradeId=ref(''),note=ref(''),ops=operationCache()
const emit=defineEmits<{changed:[]}>()
let id='',version=0,planRevision=0
const active=computed(()=>data.value?.executions.filter(e=>e.plan_id===props.plan.id&&!e.archived)||[]),archived=computed(()=>data.value?.executions.filter(e=>e.plan_id===props.plan.id&&e.archived)||[]),candidates=computed(()=>data.value?.trades.filter(t=>t.symbol===props.plan.symbol&&(!props.plan.target||t.account_id===props.plan.target.account_id)&&!data.value?.executions.some(e=>!e.archived&&e.trade.id===t.id)&&(props.plan.plan_type==='rebalance'||t.side===(props.plan.plan_type==='reduce'?'sell':'buy')))||[]),dirty=computed(()=>dialog.value&&(tradeId.value!==''||note.value!==''||step.value!==0))
function displayTime(value:string){return new Date(value).toLocaleString('zh-CN',{hour12:false})}
async function load(){const v=++version;try{const result=await request<{executions:E[];trades:T[]}>('/api/v1/owner/plans');if(v!==version)return false;data.value=result;error.value='';return true}catch(e){if(v===version){data.value=null;error.value=e instanceof Error?e.message:'读取失败'}return false}}
async function refresh(){if(await load())emit('changed')}
async function open(){if(!await load())return;step.value=0;tradeId.value='';note.value='';id=crypto.randomUUID();planRevision=props.plan.revision;ops.clear();saveError.value='';dialog.value=true}
async function canLeave(){if(busy.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的执行关联？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await canLeave())dialog.value=false}
async function save(){if(busy.value)return;const t=candidates.value.find(t=>t.id===tradeId.value);if(!t)return;busy.value=true;try{await request('/api/v1/owner/plan-executions','POST',ops.body('save',{id,revision:0,plan_id:props.plan.id,plan_revision:planRevision,step_index:step.value,trade_id:t.id,trade_revision:t.revision,note:note.value.trim()}));dialog.value=false;ops.clear();if(await load())emit('changed');else ElMessage.warning('执行关联已保存，但重新读取失败。请刷新确认，避免重复关联。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败'}finally{busy.value=false}}
async function archive(e:E){if(busy.value)return;busy.value=true;try{await request('/api/v1/owner/plan-executions','DELETE',ops.body('archive:'+e.id,{id:e.id,revision:e.revision}));ops.clear();if(await load())emit('changed');else ElMessage.warning('执行关联已撤销，但重新读取失败。请刷新确认。')}catch(e){error.value=e instanceof Error?e.message:'撤销失败'}finally{busy.value=false}}
watch(()=>[props.plan.id,props.plan.revision],load,{immediate:true});onBeforeRouteLeave(canLeave);const unload=(e:BeforeUnloadEvent)=>{if(dirty.value||busy.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>{version++;window.removeEventListener('beforeunload',unload)})
</script>
<style scoped>
.execution-section{margin-top:18px;border-top:1px solid var(--el-border-color);padding-top:16px}.execution-header{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.execution-section p{white-space:pre-wrap;overflow-wrap:anywhere}.execution-section li{padding:12px 0}.execution-section strong{overflow-wrap:anywhere}
.plan-executions {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
  margin-bottom: 12px;
}

.executions-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.execution-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
}

.exec-step {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2f7dff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.exec-date {
  color: var(--el-text-color-secondary);
  min-width: 80px;
}

.exec-reason {
  flex: 1;
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.exec-shares {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.exec-price {
  color: var(--el-text-color-secondary);
}

.exec-amount {
  font-weight: 700;
  color: var(--el-text-color-primary);
  min-width: 80px;
  text-align: right;
}


.plan-executions{list-style:none;padding-left:0}.execution-item{flex-wrap:wrap}.exec-step{flex-shrink:0}.exec-date,.exec-price,.exec-amount{overflow-wrap:anywhere}.exec-amount{max-width:100%}
</style>
