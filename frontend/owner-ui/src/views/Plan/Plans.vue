<template>
 <div class="buildup-page">
  <div class="page-header"><div class="header-copy"><div class="header-kicker">BUILD-UP PLAN</div><h1 class="header-title">投资计划</h1><div class="header-subtitle">以保存的判断为依据，明确触发条件、步骤与停止条件。</div></div><div class="header-actions"><el-button :loading="loading" @click="load">刷新计划</el-button><el-button type="primary" @click="edit()">新建计划</el-button></div></div>
  <AppDataState v-if="error" tone="error" title="计划未更新" :description="error" action-label="重试" @action="load"/>
  <el-alert v-if="historicalMaterial" title="助手材料已选为历史快照；请在助手中主动载入并核对。" type="info" :closable="false"><el-button @click="historicalMaterial=null">改用当前页面材料</el-button></el-alert>
  <div class="stats-row"><div class="stat-card"><div class="stat-label">待执行</div><div class="stat-value">{{ active.filter(p=>p.status==='ready').length }}</div></div><div class="stat-card"><div class="stat-label">暂停</div><div class="stat-value">{{ active.filter(p=>p.status==='paused').length }}</div></div><div class="stat-card"><div class="stat-label">手工标记完成</div><div class="stat-value">{{ active.filter(p=>p.status==='completed').length }}</div></div><div class="stat-card"><div class="stat-label">草稿</div><div class="stat-value">{{ active.filter(p=>p.status==='draft').length }}</div></div></div>
  <ExecutionTimeline :executions="data?.executions||[]"/>
  <div class="plan-toolbar"><el-input v-model="search" placeholder="搜索计划或标的" aria-label="搜索计划" clearable/><el-checkbox v-model="showArchived">包含已归档</el-checkbox><el-button @click="router.push('/plan/pre-trade')">交易前试算</el-button></div>
  <div v-loading="loading" class="plans-container"><article v-for="plan in rows" :key="plan.id" class="plan-card" :class="{'is-paused':plan.status==='paused','is-completed':plan.status==='completed'}"><div class="plan-header"><div class="plan-title-row"><h3 class="plan-ticker">{{ plan.symbol }}</h3><span class="plan-company">{{ plan.title }}</span><el-tag>{{ statuses[plan.status] }}{{ plan.archived?' · 已归档':'' }}</el-tag></div><div class="plan-actions"><el-button v-if="!plan.archived" link @click="edit(plan)">编辑计划</el-button><el-popconfirm v-if="!plan.archived" title="归档计划并保留历史？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(plan)"><template #reference><el-button link :disabled="saving">归档计划</el-button></template></el-popconfirm></div></div><el-alert v-if="plan.decision_changed||plan.decision_archived" title="判断已有新版本或已归档，此计划保留原依据。" type="warning" :closable="false"/><div class="plan-rules"><div class="rules-title">{{ types[plan.plan_type] }} · 复核 {{ plan.review_on }}</div><p>触发：{{ plan.trigger }}</p><ol><li v-for="(step,index) in plan.steps" :key="index">{{ step }}</li></ol><p>风险上限：{{ plan.risk_limit }}</p><p>停止条件：{{ plan.stop_condition }}</p></div><div v-if="plan.strategy" class="plan-rules"><div class="rules-title">回撤加仓条件 · 锚价 {{ plan.strategy.anchor_price }} {{ plan.target?.currency }}</div><p>底仓 {{ plan.strategy.base_percent }}% · {{ portion(plan.target?.quantity,plan.strategy.base_percent) }} 股</p><div v-for="(rule,i) in plan.strategy.rules" :key="i" class="rule-item"><span class="rule-trigger">回撤 {{ rule.pullback_percent }}%</span><span class="rule-action">加仓 {{ rule.add_percent }}% · {{ portion(plan.target?.quantity,rule.add_percent) }} 股</span><span class="rule-label">{{ rule.label }} · 条件价格 ≤ {{ triggerPrice(plan.strategy.anchor_price,rule.pullback_percent) }}</span></div><p>仅为已保存计划条件，不是当前行情或自动下单指令。</p></div><div class="plan-footer"><el-button @click="history=plan">查看固定依据</el-button><el-button v-for="version in data?.versions.filter(v=>v.id===plan.id).slice().reverse()" :key="version.revision" size="small" @click="history=version">查看 v{{ version.revision }}</el-button></div><div v-if="plan.target" class="plan-progress"><div class="progress-info"><span class="progress-label">建仓进度</span><span class="progress-value">{{ plan.progress?.quantity ?? '待核对' }} / {{ plan.target.quantity }} 股</span></div><el-progress v-if="plan.progress?.percent!=null" :percentage="Math.min(100,Number(plan.progress.percent))" :format="()=>plan.progress!.percent+'%'"/><p>累计买入成交进度，不代表当前净持仓。预算 {{ plan.target.budget ?? '未设置' }} {{ plan.target.currency }} · 已用（含费用）{{ plan.progress?.spent ?? '待核对' }}</p><el-alert v-if="plan.progress?.needs_review" title="关联成交有变更，核对并重新关联前暂停计算进度。" type="warning" :closable="false"/><el-alert v-if="plan.progress?.over_budget" title="实际投入已超过计划预算。" type="warning" :closable="false"/></div><PlanExecutions :plan="plan" @changed="load"/></article></div>
  <AppDataState v-if="!loading&&!error&&!rows.length" tone="empty" title="没有符合条件的计划" description="先保存投资判断，再制定有固定依据的计划。" />
  <el-dialog v-model="dialog" :title="editing?'编辑计划':'新建计划'" width="min(760px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!saving" :close-on-press-escape="!saving"><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item label="固定判断版本"><el-select v-model="reference" :disabled="saving||!!editing" aria-label="固定判断版本" style="width:100%"><el-option v-for="decision in decisions" :key="decision.id+'@'+decision.revision" :value="decision.id+'@'+decision.revision" :label="decision.title+' · '+decision.symbol+' · v'+decision.revision" /></el-select></el-form-item><p v-if="!decisions.length">请先到投资判断保存记录。</p><details v-if="basis"><summary>保存后固定的判断依据</summary><h3>{{ basis.title }} · v{{ basis.revision }}</h3><p>{{ basis.content }}</p><p>反方证据：{{ basis.counter_case }}</p><p>失效条件：{{ basis.invalidation }}</p></details><el-form-item label="计划名称"><el-input v-model="form.title" maxlength="120" :disabled="saving"/></el-form-item><el-form-item label="计划类型"><el-select v-model="form.plan_type" :disabled="saving"><el-option v-for="(label,value) in types" :key="value" :label="label" :value="value"/></el-select></el-form-item><template v-if="form.plan_type==='build_up'"><el-checkbox v-model="form.track" :disabled="saving">设置建仓目标</el-checkbox><template v-if="form.track"><el-form-item label="建仓账户"><el-select v-model="form.account_id" :disabled="saving"><el-option v-for="a in data?.accounts" :key="a.id" :value="a.id" :label="a.name+' · '+a.currency"/></el-select></el-form-item><el-form-item label="目标股数"><el-input v-model="form.quantity" inputmode="decimal" :disabled="saving"/></el-form-item><el-form-item label="目标预算（含成交费用，可留空）"><el-input v-model="form.budget" inputmode="decimal" :disabled="saving"/></el-form-item></template></template><PlanStrategy v-if="form.track&&form.plan_type==='build_up'" v-model="form.strategy" :disabled="saving"/><el-form-item label="人工状态"><el-select v-model="form.status" :disabled="saving"><el-option v-for="(label,value) in statuses" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item v-for="field in fields" :key="field.key" :label="field.label"><el-input v-model="form[field.key]" :type="field.key==='review_on'?'date':'textarea'" :maxlength="field.key==='steps'?24000:4000" :disabled="saving"/></el-form-item></el-form><p>保存或标记完成不会创建交易。更换判断依据需新建计划。</p><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存计划</el-button></template></el-dialog>
  <el-drawer :model-value="!!history" title="计划历史与固定依据" size="min(760px,96vw)" @close="history=null"><template v-if="history"><h2>{{ history.title }} · v{{ history.revision }}</h2><el-button @click="selectHistoricalMaterial">在助手中核对这份历史计划</el-button><p>{{ history.symbol }} · {{ statuses[history.status] }} · {{ history.updated_at }}</p><dl><template v-for="field in fields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ field.key==='steps'?history.steps.join('\n'):history[field.key] }}</dd></template></dl><p v-if="history.target">建仓目标：{{ history.target.quantity }} 股 · 预算 {{ history.target.budget ?? '未设置' }} {{ history.target.currency }}</p><div v-if="history.strategy"><h3>当时的回撤条件</h3><p>锚价 {{ history.strategy.anchor_price }} · 底仓 {{ history.strategy.base_percent }}%</p><p v-for="(rule,i) in history.strategy.rules" :key="i">回撤 {{ rule.pullback_percent }}% · 加仓 {{ rule.add_percent }}% · {{ rule.label }}</p></div><h3>原判断：{{ history.evidence.decision.title }} · v{{ history.decision_ref.revision }}</h3><p>{{ history.evidence.decision.content }}</p><p>支持：{{ history.evidence.decision.support }}</p><p>反方：{{ history.evidence.decision.counter_case }}</p><p>失效：{{ history.evidence.decision.invalidation }}</p><p>原风险上限：{{ history.evidence.decision.risk_limit }}</p><template v-if="history.evidence.research"><h3>原研究：{{ history.evidence.research.title }} · v{{ history.evidence.research.revision }}</h3><p>{{ history.evidence.research.content }}</p></template></template></el-drawer>
 </div>
</template>
<script setup lang="ts">
import PlanExecutions from './PlanExecutions.vue'
import PlanStrategy from './PlanStrategy.vue'
import type {Strategy} from './strategyTypes'
import {multiply,divide,sum,negate} from '@/utils/decimal'
import ExecutionTimeline from './ExecutionTimeline.vue'
import {useAskStore} from '@/stores/ask'
import {registerPageMaterial} from '@/api/pageMaterial'
import {computed,ref,reactive,watch,onBeforeUnmount} from 'vue'
import {useRoute,useRouter,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElProgress,ElCheckbox,ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
import AppDataState from '@/components/Global/AppDataState.vue'
type Decision={id:string;revision:number;symbol:string;title:string;content:string;support:string;counter_case:string;invalidation:string;risk_limit:string}
type Plan={strategy?:Strategy|null;target?:{account_id:string;quantity:string;budget:string|null;currency:string}|null;progress?:{quantity:string|null;spent:string|null;percent:string|null;needs_review:boolean;over_budget:boolean};id:string;revision:number;title:string;symbol:string;plan_type:string;status:string;trigger:string;steps:string[];risk_limit:string;stop_condition:string;review_on:string;decision_ref:{id:string;revision:number};evidence:{decision:Decision;research:Decision|null};archived:boolean;updated_at:string;decision_changed?:boolean;decision_archived?:boolean}
type Field='trigger'|'steps'|'risk_limit'|'stop_condition'|'review_on'
const types:Record<string,string>={build_up:'分批建仓',rebalance:'调整仓位',reduce:'减仓退出'},statuses:Record<string,string>={draft:'草稿',ready:'待执行',paused:'暂停',completed:'手工标记完成'},fields:Array<{key:Field;label:string}>=[{key:'trigger',label:'触发条件'},{key:'steps',label:'执行步骤（每行一步，最多12步）'},{key:'risk_limit',label:'风险上限'},{key:'stop_condition',label:'停止条件'},{key:'review_on',label:'复核日期'}]
const route=useRoute(),router=useRouter(),data=ref<{plans:Plan[];versions:Plan[];decisions:Decision[];executions:import('./executionTypes').Execution[];accounts:{id:string;name:string;currency:string}[]}|null>(null),loading=ref(false),saving=ref(false),error=ref(''),saveError=ref(''),search=ref(''),showArchived=ref(false),dialog=ref(false),editing=ref<Plan|null>(null),history=ref<Plan|null>(null),reference=ref(''),operations=operationCache();let id='',baseline=''
const blank=()=>({title:'',plan_type:'build_up',status:'draft',trigger:'',steps:'',risk_limit:'',stop_condition:'',review_on:'',track:false,account_id:'',quantity:'',budget:'',strategy:null as Strategy|null}),form=reactive(blank()),fingerprint=()=>JSON.stringify([form,reference.value]),dirty=computed(()=>dialog.value&&fingerprint()!==baseline),active=computed(()=>data.value?.plans.filter(p=>!p.archived)||[]),rows=computed(()=>data.value?.plans.filter(p=>(showArchived.value||!p.archived)&&(!search.value||(p.title+' '+p.symbol).toLowerCase().includes(search.value.toLowerCase())))||[])
const decisions=computed(()=>{const options=[...(data.value?.decisions||[])];if(editing.value&&!options.some(d=>d.id===editing.value!.decision_ref.id&&d.revision===editing.value!.decision_ref.revision))options.push(editing.value.evidence.decision);return options}),basis=computed(()=>decisions.value.find(d=>d.id+'@'+d.revision===reference.value))
const unregisterMaterial=registerPageMaterial('/plan/build-up',()=>{
  if(!loading.value&&!saving.value&&historicalMaterial.value)return {scope:'fixed_plan_evidence',snapshot:historicalMaterial.value,notice:'明确选中的历史计划及当时固定判断依据；不包含当前进度，不表示实际执行或当前判断。'}
  if(loading.value||saving.value||error.value||!data.value||dialog.value||history.value)throw Error('请先完成计划加载并关闭编辑或历史窗口，再载入材料。')
  const ids=new Set(rows.value.map(p=>p.id))
  return {scope:'filtered_plans_and_execution_evidence',filters:{search:search.value,include_archived:showArchived.value},plans:rows.value,
    executions:data.value.executions.filter(e=>ids.has(e.plan_id)),
    notice:'当前筛选的已保存计划及其执行证据。手工完成状态不是成交证明；执行记录保留绑定的成交版本，trade_changed表示原成交已变化，archived表示执行关联已归档。不得把旧版本或归档关联重复计入当前进度。未包含筛选外计划、其他成交或未保存输入。'}
})
onBeforeUnmount(unregisterMaterial)
const historicalMaterial=ref<Record<string,unknown>|null>(null)
function selectHistoricalMaterial(){if(!history.value)return;historicalMaterial.value=JSON.parse(JSON.stringify(Object.fromEntries(['id','revision','title','symbol','plan_type','status','trigger','steps','risk_limit','stop_condition','review_on','decision_ref','evidence','target','strategy','archived','updated_at'].map(key=>[key,(history.value as unknown as Record<string,unknown>)[key]]))));history.value=null;useAskStore().open()}
const portion=(quantity:string|undefined,percent:string)=>quantity?divide(multiply(quantity,percent),'100',18):'—'
const triggerPrice=(anchor:string,percent:string)=>divide(multiply(anchor,sum(['100',negate(percent)])),'100',18)
async function load(){if(loading.value)return false;loading.value=true;error.value='';try{data.value=await request('/api/v1/owner/plans');const target=data.value?.plans.find(p=>p.id===route.query.id);history.value=target||null;return true}catch(e){data.value=null;history.value=null;historicalMaterial.value=null;error.value=e instanceof Error?e.message:'读取失败';return false}finally{loading.value=false}}
function edit(plan?:Plan){editing.value=plan||null;id=plan?.id||crypto.randomUUID();Object.assign(form,blank());if(plan)Object.assign(form,{title:plan.title,plan_type:plan.plan_type,status:plan.status,trigger:plan.trigger,steps:plan.steps.join('\n'),risk_limit:plan.risk_limit,stop_condition:plan.stop_condition,review_on:plan.review_on});if(plan?.strategy)form.strategy=JSON.parse(JSON.stringify(plan.strategy));if(plan?.target)Object.assign(form,{track:true,account_id:plan.target.account_id,quantity:plan.target.quantity,budget:plan.target.budget||''});reference.value=plan?plan.decision_ref.id+'@'+plan.decision_ref.revision:'';baseline=fingerprint();operations.clear();saveError.value='';dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的计划内容？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){if(saving.value||loading.value)return;const steps=form.steps.split('\n').map(s=>s.trim()).filter(Boolean);saveError.value='';if(!reference.value||!form.title.trim()||fields.some(f=>!form[f.key].trim())||steps.length>12||steps.some(s=>s.length>2000)){saveError.value='请填写全部字段；步骤最多12行，每行不超过2000字。';return}if(form.track&&form.plan_type==='build_up'&&(!form.account_id||!form.quantity.trim())){saveError.value='请选择账户并填写目标股数';return}saving.value=true;try{const [decisionId,revision]=reference.value.split('@');await request('/api/v1/owner/plans','POST',operations.body('save',{id,revision:editing.value?.revision||0,...Object.fromEntries(Object.entries(form).filter(([key])=>!['track','account_id','quantity','budget'].includes(key))),strategy:form.track&&form.plan_type==='build_up'?form.strategy:null,target:form.track&&form.plan_type==='build_up'?{account_id:form.account_id,quantity:form.quantity.trim(),budget:form.budget.trim()||null}:null,steps,decision_ref:{id:decisionId,revision:Number(revision)}}));dialog.value=false;operations.clear();if(await load())ElMessage.success('计划已保存，未创建交易');else ElMessage.warning('计划已保存，但重新读取失败。请刷新确认，避免重复保存。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}}
async function archive(plan:Plan){if(saving.value||loading.value)return;saving.value=true;try{await request('/api/v1/owner/plans','DELETE',operations.body('archive:'+plan.id,{id:plan.id,revision:plan.revision}));operations.clear();if(!await load())ElMessage.warning('计划已归档，但重新读取失败。请刷新确认。')}catch(e){ElMessage.error(e instanceof Error?e.message:'归档失败')}finally{saving.value=false}}
async function leave(){const ok=await discard();if(ok)dialog.value=false;return ok}
onBeforeRouteLeave(leave);onBeforeRouteUpdate(leave);watch(()=>route.fullPath,()=>{history.value=null;historicalMaterial.value=null;load()},{immediate:true});const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>

<style lang="scss" scoped>
.buildup-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.timeline-section {
  margin-bottom: 24px;
}

.chart-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 12px;
}

.chart-container {
  width: 100%;
  height: 260px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #2f7dff;
  margin-bottom: 4px;
}

.header-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.header-subtitle {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.stat-sub {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.discipline-card {
  border-color: var(--el-border-color);
}

.grade-A { color: #1f9d68; }
.grade-B { color: #2f7dff; }
.grade-C { color: #e6a23c; }
.grade-D { color: #f56c6c; }

.grade-badge {
  font-size: 14px;
  font-weight: 700;
  margin-left: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--el-fill-color);
}

.plans-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px;

  &.is-completed { opacity: 0.7; }
  &.is-paused { border-left: 4px solid #e6a23c; }
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.plan-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plan-ticker {
  font-size: 20px;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin: 0;
}

.plan-company {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.plan-actions {
  display: flex;
  gap: 4px;
}

.plan-progress {
  margin-bottom: 16px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.progress-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.progress-sub {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

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

.plan-rules {
  background: rgba(47, 125, 255, 0.04);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.rules-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
  font-size: 13px;
}

.rule-trigger {
  font-weight: 700;
  color: #f56c6c;
  min-width: 80px;
}

.rule-action {
  font-weight: 700;
  color: #1f9d68;
  min-width: 80px;
}

.rule-label {
  color: var(--el-text-color-secondary);
}

.plan-footer {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.rules-editor {
  width: 100%;
}

.rule-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.rule-sep {
  color: var(--el-text-color-secondary);
}

.execute-info {
  p {
    margin: 4px 0;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }
  b {
    color: var(--el-text-color-primary);
  }
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: var(--el-text-color-secondary);

  h3 {
    margin: 16px 0 8px;
    font-size: 18px;
    color: var(--el-text-color-primary);
  }

  p {
    margin-bottom: 20px;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>

<style scoped>.header-title{margin:0}.plan-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:20px}.plan-toolbar .el-input{max-width:300px}.plan-header,.plan-title-row,.plan-footer{flex-wrap:wrap}.plan-company,.plan-rules,dd{overflow-wrap:anywhere;white-space:pre-wrap}.plan-footer{gap:8px}dd{margin:6px 0 18px}.stats-row{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:600px){.stats-row{grid-template-columns:repeat(2,minmax(0,1fr))}.page-header{flex-wrap:wrap;gap:12px}.plan-card{padding:16px}}</style>

<style scoped>.plan-card.is-completed{opacity:1}.plan-card :deep(.el-alert--warning){background:rgba(242,169,59,.12);color:#ffd18b;border:1px solid rgba(242,169,59,.25)}</style>
