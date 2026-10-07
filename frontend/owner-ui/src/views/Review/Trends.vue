<template><div class="diagnosis-page">
 <div class="page-header"><div class="header-info"><h2 class="title">规则与周期趋势</h2><span class="subtitle">保留规则修订，分别观察决策过程和结果。</span></div><div class="header-actions" role="group" aria-label="规则管理操作"><el-button class="refresh-rules" :loading="loading" @click="load">刷新规则</el-button><el-button class="archive-rules" text @click="archives=true">查看已归档规则</el-button><el-button class="new-rule" type="primary" @click="edit()">新增规则</el-button></div></div>
 <AppDataState v-if="error" tone="error" title="规则读取失败" :description="error" action-label="重试" @action="load"/>
 <div class="status-strip"><div class="status-pill"><span class="status-label">启用规则</span><strong>{{ rules.filter(r=>r.enabled).length }}</strong></div><div class="status-pill"><span class="status-label">停用规则</span><strong>{{ rules.filter(r=>!r.enabled).length }}</strong></div><div class="status-pill"><span class="status-label">处理方式</span><strong>人工复核</strong></div></div>
 <section v-if="rules.length" class="rule-grid"><article v-for="rule in rules" :key="rule.id" class="rule-card"><h3>{{ rule.title }}</h3><el-tag>{{ rule.enabled?'启用':'停用' }} · v{{ rule.revision }}</el-tag><p>适用范围：{{ rule.scope }}</p><h4>触发条件</h4><p>{{ rule.condition }}</p><h4>人工检查或处理方式</h4><p>{{ rule.action }}</p><div class="rule-actions"><el-button :disabled="saving" @click="toggle(rule)">{{ rule.enabled?'停用规则':'确认启用' }}</el-button><el-button :disabled="saving" @click="edit(rule)">更正规则</el-button><el-popconfirm title="归档规则并保留历史？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(rule)"><template #reference><el-button :disabled="saving">归档规则</el-button></template></el-popconfirm><el-button @click="history=rule">版本历史</el-button></div></article></section>
 <AppDataState v-if="!loading&&!error&&!rules.length" tone="empty" title="尚无有效规则" description="新增规则默认停用，核对后可主动启用。"/>
 <el-card shadow="never" class="trend-card"><template #header><div class="card-title">周期复盘统计</div></template><div class="range-fields"><label>开始日期<el-input v-model="from" type="date" aria-label="开始日期"/></label><label>结束日期<el-input v-model="to" type="date" aria-label="结束日期"/></label><el-button :loading="querying" @click="query">查询趋势</el-button></div><AppDataState v-if="trendError" tone="error" title="趋势查询失败" :description="trendError"/><template v-if="trend"><p>{{ trend.basis }}</p><p>当前区间共 {{ trend.total }} 条复盘；不是全部交易的质量或收益统计。</p><el-table :data="trend.months" style="width:100%"><el-table-column v-for="column in columns" :key="column.key" :prop="column.key" :label="column.label" min-width="115"/></el-table><p v-if="!trend.total">此区间没有有效复盘。</p><div class="rule-actions"><el-button v-for="record in trend.records" :key="record.id" @click="router.push({path:'/review',query:{id:record.id}})">{{ record.reviewed_on }} · {{ record.title }} · v{{ record.revision }}</el-button></div></template></el-card>
 <el-dialog v-model="dialog" :title="editing?'更正规则':'新增规则'" width="min(720px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!saving" :close-on-press-escape="!saving"><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item v-for="field in fields" :key="field.key" :label="field.label"><el-input v-model="form[field.key]" :type="field.key==='condition'||field.key==='action'?'textarea':'text'" :maxlength="field.key==='condition'||field.key==='action'?4000:120" :disabled="saving"/></el-form-item></el-form><p>{{ editing?.enabled?'此规则当前启用，更正时会先请你核对完整内容。':'保存后保持停用；启用需另行确认。' }}规则不执行交易。</p><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存规则</el-button></template></el-dialog>
 <el-drawer :model-value="!!history" title="规则版本历史" size="min(720px,96vw)" @close="history=null"><template v-if="history"><article v-for="version in versions.filter(r=>r.id===history?.id).slice().reverse()" :key="version.revision" class="rule-card"><h3>{{ version.title }} · v{{ version.revision }}</h3><p>{{ version.archived?'已归档':version.enabled?'启用':'停用' }} · {{ version.updated_at }}</p><p>范围：{{ version.scope }}</p><p>触发：{{ version.condition }}</p><p>处理：{{ version.action }}</p></article></template></el-drawer>
 <el-drawer v-model="archives" title="已归档规则" size="min(720px,96vw)"><p v-if="!archivedRules.length">没有已归档规则。</p><el-button v-for="rule in archivedRules" :key="rule.id" @click="archives=false;history=rule">{{ rule.title }} · v{{ rule.revision }}</el-button></el-drawer>
 </div></template>
<script setup lang="ts">
import {computed,ref,reactive,watch,onBeforeUnmount} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import {registerPageMaterial} from '@/api/pageMaterial'
import AppDataState from '@/components/Global/AppDataState.vue'
import {request} from '@/api/owner'
import {getWorkspace,operationCache,type Workspace,type BusinessRecord} from '@/api/business'
type Rule=BusinessRecord&{condition:string;action:string;scope:string;enabled:boolean}
type Trend={from:string;to:string;total:number;basis:string;months:Array<Record<string,unknown>>;records:Array<{id:string;title:string;revision:number;reviewed_on:string}>}
const router=useRouter(),data=ref<Workspace|null>(null),loading=ref(false),saving=ref(false),querying=ref(false),error=ref(''),trendError=ref(''),saveError=ref(''),dialog=ref(false),editing=ref<Rule|null>(null),history=ref<Rule|null>(null),archives=ref(false),operations=operationCache(),trend=ref<Trend|null>(null)
const date=new Date(),today=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`,from=ref(today.slice(0,4)+'-01-01'),to=ref(today)
const fields=[{key:'title',label:'规则名称'},{key:'condition',label:'触发条件'},{key:'action',label:'人工检查或处理方式'},{key:'scope',label:'适用范围'}] as const,columns=[{key:'month',label:'月份'},{key:'total',label:'复盘数'},{key:'followed',label:'遵守计划'},{key:'deviated',label:'偏离计划'},{key:'unclear',label:'尚不能判断'},{key:'observed',label:'已有观察'},{key:'pending',label:'待观察'}]
const rules=computed(()=>(data.value?.records.filter(r=>r.kind==='rule')||[]) as Rule[]),versions=computed(()=>(data.value?.versions.filter(r=>r.kind==='rule')||[]) as Rule[]),archivedRules=computed(()=>versions.value.filter(r=>r.archived&&!versions.value.some(v=>v.id===r.id&&v.revision>r.revision)))
const unregisterMaterial=registerPageMaterial('/review/rules',()=>{
  if(loading.value||saving.value||querying.value||error.value||!data.value||dialog.value||history.value||archives.value)throw Error('请先完成规则加载或趋势查询，并关闭编辑与历史窗口，再载入材料。')
  const current=trend.value&&trend.value.from===from.value&&trend.value.to===to.value?trend.value:null
  return {scope:'rules_and_review_trend',rules:rules.value,range:{from:from.value,to:to.value},
    trend:current,trend_status:current?'queried':trendError.value?'query_failed':'needs_query',
    notice:'规则保留启用/停用状态，仅用于人工复核，不执行交易。趋势仅统计所选区间内的复盘，不代表所有交易的收益或质量；未查询或失败时趋势为null，不沿用旧结果。未包含历史规则版本、账户或逐笔成交。'}
})
onBeforeUnmount(unregisterMaterial)
const blank=()=>({title:'',condition:'',action:'',scope:''}),form=reactive(blank());let id='',baseline='',queryGeneration=0
const dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline)
async function load(){if(loading.value)return;loading.value=true;error.value='';try{data.value=await getWorkspace()}catch(e){error.value=e instanceof Error?e.message:'读取失败'}finally{loading.value=false}}
watch([from,to],()=>{trend.value=null;trendError.value='';queryGeneration++})
async function query(){if(querying.value)return;trend.value=null;trendError.value='';if(!from.value||!to.value||from.value>to.value){trendError.value='请填写有效区间，开始日期不能晚于结束日期。';return}const generation=++queryGeneration;querying.value=true;try{const result=await request<Trend>('/api/v1/owner/trends','POST',{from:from.value,to:to.value});if(generation===queryGeneration)trend.value=result}catch(e){if(generation===queryGeneration)trendError.value=e instanceof Error?e.message:'查询失败'}finally{querying.value=false}}
function edit(rule?:Rule){editing.value=rule||null;id=rule?.id||crypto.randomUUID();Object.assign(form,blank());if(rule)for(const field of fields)form[field.key]=rule[field.key];baseline=JSON.stringify(form);operations.clear();saveError.value='';dialog.value=true}
async function confirmRule(title:string,r:typeof form){try{await ElMessageBox.confirm(`名称：${r.title}\n范围：${r.scope}\n触发：${r.condition}\n人工处理：${r.action}\n\n此操作不执行交易。`,title,{confirmButtonText:'确认',cancelButtonText:'取消'});return true}catch{return false}}
async function save(){if(saving.value)return;saveError.value='';if(fields.some(f=>!form[f.key].trim())){saveError.value='请填写规则名称、条件、处理方式和适用范围。';return}saving.value=true;try{if(editing.value?.enabled&&!await confirmRule('确认更正已启用规则',form))return;await request('/api/v1/owner/business','POST',operations.body('save',{id,revision:editing.value?.revision||0,kind:'rule',data:{...form,enabled:editing.value?.enabled||false}}));dialog.value=false;await load();ElMessage.success('规则已保存')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败'}finally{saving.value=false}}
async function toggle(rule:Rule){if(saving.value)return;saving.value=true;try{if(!await confirmRule(rule.enabled?'确认停用规则':'确认启用规则',rule))return;await request('/api/v1/owner/business','POST',operations.body('toggle:'+rule.id,{id:rule.id,revision:rule.revision,kind:'rule',data:{title:rule.title,condition:rule.condition,action:rule.action,scope:rule.scope,enabled:!rule.enabled}}));await load()}catch(e){ElMessage.error(e instanceof Error?e.message:'更新失败')}finally{saving.value=false}}
async function archive(rule:Rule){if(saving.value)return;saving.value=true;try{await request('/api/v1/owner/business','DELETE',operations.body('archive:'+rule.id,{id:rule.id,revision:rule.revision}));await load()}catch(e){ElMessage.error(e instanceof Error?e.message:'归档失败')}finally{saving.value=false}}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的规则内容？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}async function close(){if(await discard())dialog.value=false}onBeforeRouteLeave(discard);const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>{queryGeneration++;window.removeEventListener('beforeunload',beforeUnload)});load();query()
</script>
<style scoped>
.diagnosis-page {
  padding: 24px;
}

.diagnosis-brain {
  margin: 16px 0 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.header-actions :deep(.el-button) {
  margin-left: 0;
}

.archive-rules {
  color: var(--el-text-color-secondary);
}

.header-info .title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-info .subtitle {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
  display: block;
}

.truth-note {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.status-pill {
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid #e9eef5;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
}

.status-label {
  display: block;
  font-size: 12px;
  color: #909399;
}

.status-value {
  display: block;
  margin-top: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.summary-grid,
.chart-grid,
.content-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 24px;
}

.summary-grid,
.content-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.score-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
}

.gauge-chart {
  width: 240px;
  height: 160px;
}

.score-details {
  margin-left: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.grade-badge {
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 4px;
}

.interpretation {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
}

.summary-info {
  font-size: 14px;
  color: #606266;
}

.card-head,
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-title,
.history-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.card-subtitle,
.history-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.automation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.automation-item {
  padding: 14px;
  border-radius: 16px;
  background: #f7f9fc;
}

.automation-label {
  font-size: 12px;
  color: #909399;
}

.automation-value {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.comparison-summary {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #edf1f7;
}

.comparison-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.comparison-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.comparison-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: #f4f6fb;
  font-size: 12px;
  font-weight: 600;
}

.comparison-list {
  margin-top: 14px;
}

.comparison-list-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.comparison-list-item {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 6px;
}

.comparison-list-item.is-added {
  color: #f56c6c;
}

.comparison-list-item.is-removed {
  color: #67c23a;
}

.history-chart {
  width: 100%;
  height: 280px;
}

.grade-a,
.delta-positive {
  color: #67c23a;
}

.grade-b {
  color: #409eff;
}

.grade-c {
  color: #e6a23c;
}

.grade-df,
.delta-negative {
  color: #f56c6c;
}

.delta-neutral {
  color: #909399;
}

.dimension-grid {
  margin-bottom: 24px;
}

.dimension-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}

.dim-score {
  color: #409eff;
}

.dim-detail {
  margin-top: 12px;
  font-size: 13px;
  color: #909399;
}

.dim-alerts {
  margin-top: 12px;
  border-top: 1px solid #f5f7fa;
  padding-top: 12px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  font-size: 12px;
  color: #e6a23c;
  margin-bottom: 6px;
  line-height: 1.4;
}

.warning-icon {
  margin-right: 4px;
  margin-top: 2px;
  font-size: 14px;
}

.brief-card,
.score-card,
.automation-card,
.history-card {
  border-radius: 20px;
}

.daily-report-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.36fr);
  gap: 16px;
  align-items: stretch;
}

.daily-brief-main {
  min-width: 0;
}

.daily-brief-basis-warning {
  margin-bottom: 12px;
}

.daily-brief-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 9px;
  color: #7b8da4;
  font-size: 11px;
}

.daily-brief {
  margin: 0;
  min-height: 260px;
  padding: 16px;
  border: 1px solid rgba(226, 233, 243, 0.92);
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.7;
  color: #303133;
}

.brief-feedback {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  color: var(--el-text-color-regular);
  font-size: 12px;
}

.brief-feedback small {
  margin-left: auto;
  color: var(--el-text-color-secondary);
}

.daily-report-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.daily-report-history-title {
  font-size: 12px;
  font-weight: 700;
  color: #6f8299;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.daily-report-item {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(226, 233, 243, 0.96);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.daily-report-item:hover,
.daily-report-item.active {
  border-color: rgba(64, 158, 255, 0.36);
  background: rgba(239, 247, 255, 0.96);
  transform: translateY(-1px);
}

.daily-report-item.historical {
  opacity: 0.72;
}

.daily-report-item span,
.daily-report-item b,
.daily-report-item em,
.daily-report-item small {
  display: block;
}

.daily-report-item span {
  color: #7a8aa0;
  font-size: 12px;
}

.daily-report-item b {
  margin-top: 4px;
  color: #102344;
  font-size: 14px;
}

.daily-report-item em {
  width: fit-content;
  margin-top: 5px;
  padding: 1px 5px;
  border-radius: 4px;
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  font-size: 10px;
  font-style: normal;
}

.daily-report-item small {
  margin-top: 6px;
  color: #6b7d94;
  font-size: 12px;
  line-height: 1.45;
}

.alerts-panel {
  background: #fff;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #ebeef5;
}

.panel-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.top-alert-item {
  margin-bottom: 12px;
}

.top-alert-item:last-child {
  margin-bottom: 0;
}

@media (max-width: 1200px) {
  .summary-grid,
  .chart-grid,
  .content-grid,
  .daily-report-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .refresh-rules { order: 1; }
  .new-rule { order: 2; }
  .archive-rules {
    order: 3;
    grid-column: 1 / -1;
    justify-self: end;
  }

  .score-container {
    flex-direction: column;
    align-items: flex-start;
    min-height: auto;
  }

  .score-details {
    margin-left: 0;
    margin-top: 12px;
  }

  .automation-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<style scoped>.rule-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:20px 0}.rule-card{padding:20px;border:1px solid var(--el-border-color);border-radius:18px;background:var(--el-bg-color-overlay);min-width:0;margin-bottom:12px}.rule-card p,.rule-card h3{white-space:pre-wrap;overflow-wrap:anywhere}.rule-actions,.range-fields{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.rule-actions .el-button{margin-left:0;max-width:100%;height:auto;min-height:32px;white-space:normal}.trend-card{margin-top:24px}.range-fields label{max-width:100%}.title{color:#edf5ff}.subtitle{color:#a5bad3}.status-pill strong{color:#dcecff}@media(max-width:760px){.rule-grid{grid-template-columns:1fr}.page-header{flex-wrap:wrap;gap:12px}.status-strip{flex-wrap:wrap}}</style>
<style scoped>.diagnosis-page .title{color:#edf5ff}.diagnosis-page .status-pill{background:#101e32;border:1px solid #24405f}.diagnosis-page .status-label{color:#a5bad3}.diagnosis-page .status-pill strong{color:#edf5ff}.diagnosis-page .status-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}@media(max-width:760px){.diagnosis-page .status-strip{grid-template-columns:1fr}}</style>
