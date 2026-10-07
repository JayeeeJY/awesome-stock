<template>
 <div class="journal-page">
  <JournalEntries ref="journalPanel"><DecisionCoach ref="coachPanel" @saved="load"/></JournalEntries>
  <CoachPeriod ref="periodPanel"/>
  <div class="page-header"><div><h2 class="page-title">决策复盘</h2><p class="page-subtitle">分别记录过程与结果，保留当时的判断、研究和成交依据。</p></div><div class="header-actions"><el-button :loading="loading" @click="load">刷新复盘</el-button><el-button type="primary" @click="edit()">新建复盘</el-button></div></div>
  <section class="summary-grid" aria-label="复盘概览"><article v-for="item in summary" :key="item.label" class="summary-card"><span class="summary-label">{{ item.label }}</span><b class="summary-value">{{ item.value }}</b><small>{{ item.detail }}</small></article></section>
  <AppDataState v-if="error" tone="error" title="读取复盘失败" :description="error" action-label="重试" @action="load"/>
  <div class="filter-bar"><el-input v-model="search" placeholder="搜索标题或标的" aria-label="搜索复盘" clearable/><el-checkbox v-model="archived">包含已归档</el-checkbox></div>
  <div v-loading="loading" class="entry-list"><article v-for="review in rows" :key="review.id" class="entry-card"><div class="entry-header"><div class="entry-meta"><el-tag>{{ review.symbol }}</el-tag><span class="entry-date">{{ review.reviewed_on }} · v{{ review.revision }}{{ review.archived?' · 已归档':'' }}</span></div><div class="entry-actions"><el-button v-if="!review.archived" link @click="edit(review)">编辑复盘</el-button><el-popconfirm v-if="!review.archived" title="归档复盘并保留历史依据？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(review)"><template #reference><el-button link :disabled="saving">归档复盘</el-button></template></el-popconfirm></div></div><h3>{{ review.title }}</h3><p>过程：{{ processes[review.process_status] }} · 结果：{{ outcomes[review.outcome_status] }}</p><p class="excerpt">{{ review.process_note.slice(0,220) }}</p><el-alert v-if="review.evidence_changed" title="当前成交或引用已有变化，此复盘保留原快照。" type="warning" :closable="false"/><div class="versions"><el-button v-for="version in data?.versions.filter(v=>v.id===review.id).slice().reverse()" :key="version.revision" size="small" @click="history=version">查看 v{{ version.revision }}</el-button></div></article></div>
  <AppDataState v-if="!loading&&!error&&!rows.length" tone="empty" title="没有符合条件的复盘" description="先保存投资判断，再选择一个判断版本开始复盘。"/>
  <section class="coach-journal"><h3>教练复核日记</h3><p v-if="!data?.coach_journal.length">尚无存入日记的教练复核。</p><article v-for="entry in data?.coach_journal" :key="entry.id" class="entry-card"><h4>{{ entry.title }}</h4><p>复核版本 {{ entry.annotation_revision }} · {{ new Date(entry.updated_at).toLocaleString('zh-CN') }}</p><p class="document-text">{{ entry.content }}</p><details><summary>查看教练日记固定依据</summary><ReviewEvidence :snapshot="entry.report.evidence.decision_evidence"/></details></article></section>
  <section class="daily-journal"><h3>日报日记归档</h3><p>按生成时间保留每份事实日报，可查看固定依据。它不会自动判定你的交易过程是否正确。</p><el-input v-model="journalSearch" aria-label="搜索日报日记" placeholder="搜索账户、日期或标的" clearable/><p v-if="!journalRows.length">没有符合条件的日报日记。</p><article v-for="entry in journalRows" :key="entry.id" class="entry-card"><div class="entry-header"><strong>{{ entry.journal?.account_name||'历史日报' }}</strong><span>{{ new Date(entry.captured_at).toLocaleString('zh-CN') }}</span></div><p>{{ entry.journal?.tickers.join(' · ')||'无标的摘要' }}</p><p>{{ entry.currency }} · {{ entry.facts.status==='complete'?'资料齐全':'资料不足' }}</p><details><summary>阅读固定日报</summary><p class="document-text">{{ entry.journal?.content||'旧版日报未保存日记文本，请打开原始依据查看。' }}</p></details><el-button @click="router.push({path:'/review/diagnosis',query:{id:entry.id}})">打开日报依据</el-button></article></section>
  <el-dialog v-model="dialog" :title="editing?'编辑复盘':'新建复盘'" width="min(800px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!saving" :close-on-press-escape="!saving"><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item label="固定判断版本"><el-select v-model="reference" aria-label="固定判断版本" :disabled="saving||!!editing" style="width:100%" @change="choose"><el-option v-for="candidate in data?.candidates" :key="refKey(candidate.ref)" :value="refKey(candidate.ref)" :label="candidate.snapshot.decision.title+' · '+candidate.snapshot.decision.symbol+' · v'+candidate.ref.revision+(candidate.decision_archived?'（已归档判断）':'')"/></el-select></el-form-item><template v-if="basis"><p>{{ editing?'修订文字保留原快照；新依据需要新建复盘。':'保存前核对成交引用，保存后固定依据。' }}</p><el-button v-if="!editing" :disabled="saving||loading" @click="refreshBasis">更新未保存依据</el-button><ReviewEvidence :snapshot="basis.snapshot"/></template><el-form-item label="复盘日期"><el-input v-model="form.reviewed_on" type="date" :disabled="saving"/></el-form-item><el-form-item label="过程判断（人工）"><el-select v-model="form.process_status" :disabled="saving"><el-option v-for="(label,value) in processes" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item label="过程复核"><el-input v-model="form.process_note" type="textarea" :rows="4" maxlength="20000" :disabled="saving"/></el-form-item><el-form-item label="结果状态"><el-select v-model="form.outcome_status" :disabled="saving"><el-option v-for="(label,value) in outcomes" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item :label="form.outcome_status==='observed'?'结果备注（必填）':'结果备注（可选）'"><el-input v-model="form.outcome_note" type="textarea" maxlength="20000" :disabled="saving"/></el-form-item><el-form-item label="下次改进"><el-input v-model="form.next_step" type="textarea" maxlength="10000" :disabled="saving"/></el-form-item></el-form><p>盈利或亏损不能代替过程判断；待观察不会被计为亏损或违规。</p><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存复盘</el-button></template></el-dialog>
  <el-drawer :model-value="!!history" title="复盘历史与固定依据" size="min(800px,96vw)" @close="history=null"><template v-if="history"><h2>{{ history.title }} · v{{ history.revision }}</h2><p>{{ history.reviewed_on }} · {{ history.symbol }}</p><h3>过程：{{ processes[history.process_status] }}</h3><p class="document-text">{{ history.process_note }}</p><h3>结果：{{ outcomes[history.outcome_status] }}</h3><p class="document-text">{{ history.outcome_note||'未填写' }}</p><h3>下次改进</h3><p class="document-text">{{ history.next_step }}</p><ReviewEvidence :snapshot="history.evidence"/></template></el-drawer>
 </div>
</template>
<script setup lang="ts">
import {registerPageMaterial} from '@/api/pageMaterial'
import type {CoachEvidence} from './types'
import {computed,ref,reactive,watch,onBeforeUnmount} from 'vue'
import {useRoute,useRouter,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElCheckbox,ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
import AppDataState from '@/components/Global/AppDataState.vue'
import CoachPeriod from './CoachPeriod.vue'
import DecisionCoach from './DecisionCoach.vue'
import JournalEntries from './JournalEntries.vue'
import ReviewEvidence from './ReviewEvidence.vue'
import type {Evidence,Reference} from './types'
type Review={id:string;revision:number;title:string;symbol:string;archived:boolean;decision_ref:Reference;evidence:Evidence;evidence_fingerprint:string;evidence_changed?:boolean;reviewed_on:string;process_status:string;process_note:string;outcome_status:string;outcome_note:string;next_step:string}
type Journal={id:string;captured_at:string;currency:string;facts:{status:string};journal?:{account_name:string;tickers:string[];content:string;entry_date:string}}
const periodPanel=ref<InstanceType<typeof CoachPeriod>|null>(null),coachPanel=ref<InstanceType<typeof DecisionCoach>|null>(null),journalPanel=ref<InstanceType<typeof JournalEntries>|null>(null)
const router=useRouter(),journalSearch=ref('')
type Candidate={ref:Reference;snapshot:Evidence;fingerprint:string;decision_archived?:boolean}
const processes:Record<string,string>={followed:'遵守原计划',deviated:'偏离原计划',unclear:'尚不能判断'},outcomes:Record<string,string>={pending:'待观察',observed:'已有观察'},refKey=(r:Reference)=>r.id+'@'+r.revision
const route=useRoute(),data=ref<{coach_journal:{id:string;title:string;content:string;annotation_revision:number;updated_at:string;report:{evidence:{decision_evidence:CoachEvidence}}}[];daily_journal:Journal[];candidates:Candidate[];reviews:Review[];versions:Review[]}|null>(null),loading=ref(false),saving=ref(false),error=ref(''),saveError=ref(''),search=ref(''),archived=ref(false),dialog=ref(false),editing=ref<Review|null>(null),history=ref<Review|null>(null),reference=ref(''),basis=ref<Candidate|null>(null),operations=operationCache();let id='',baseline=''
const summary=computed(()=>{const reviews=data.value?.reviews||[],current=reviews.filter(r=>!r.archived);return [
  {label:'已保存复盘',value:String(reviews.length),detail:'包括归档，历史依据保留'},
  {label:'待观察结果',value:String(current.filter(r=>r.outcome_status==='pending').length),detail:'不自动判作亏损或失败'},
  {label:'涉及标的',value:String(new Set(current.map(r=>r.symbol)).size),detail:'当前未归档复盘'},
  {label:'过程待核',value:String(current.filter(r=>r.process_status==='unclear').length),detail:'人工标记为尚不能判断'},
]})
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`},blank=()=>({reviewed_on:today(),process_status:'unclear',process_note:'',outcome_status:'pending',outcome_note:'',next_step:''}),form=reactive(blank()),state=()=>JSON.stringify([form,reference.value,basis.value?.fingerprint]),dirty=computed(()=>dialog.value&&state()!==baseline),rows=computed(()=>data.value?.reviews.filter(r=>(archived.value||!r.archived)&&(!search.value||(r.title+' '+r.symbol).toLowerCase().includes(search.value.toLowerCase())))||[])
const journalRows=computed(()=>data.value?.daily_journal.filter(r=>[r.journal?.account_name,r.captured_at,...(r.journal?.tickers||[])].join(' ').toLowerCase().includes(journalSearch.value.toLowerCase()))||[])
async function load(){if(loading.value)return false;loading.value=true;error.value='';try{data.value=await request('/api/v1/owner/evolve');const target=data.value?.reviews.find(r=>r.id===route.query.id);history.value=target||null;return true}catch(e){data.value=null;history.value=null;error.value=e instanceof Error?e.message:'读取失败';return false}finally{loading.value=false}}
function choose(){basis.value=data.value?.candidates.find(c=>refKey(c.ref)===reference.value)||null}
async function refreshBasis(){await load();if(!error.value){choose();operations.clear();ElMessage.success('依据已更新，请重新核对')}}
function edit(review?:Review){editing.value=review||null;id=review?.id||crypto.randomUUID();Object.assign(form,blank());if(review)for(const key of Object.keys(blank()) as Array<keyof ReturnType<typeof blank>>)form[key]=review[key];reference.value=review?refKey(review.decision_ref):'';basis.value=review?{ref:review.decision_ref,snapshot:review.evidence,fingerprint:review.evidence_fingerprint}:null;baseline=state();operations.clear();saveError.value='';dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的复盘内容？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){if(saving.value||loading.value)return;saveError.value='';if(!basis.value||!form.reviewed_on||!form.process_note.trim()||!form.next_step.trim()||(form.outcome_status==='observed'&&!form.outcome_note.trim())){saveError.value='请选择判断版本并填写日期、过程复核和下次改进；已有观察时须填写结果备注。';return}saving.value=true;try{await request('/api/v1/owner/evolve','POST',operations.body('save',{id,revision:editing.value?.revision||0,...form,decision_ref:basis.value.ref,expected_evidence:basis.value.fingerprint}));dialog.value=false;operations.clear();if(await load())ElMessage.success('复盘已保存，过程与结果分别记录');else ElMessage.warning('复盘已保存，但重新读取失败。请刷新确认，避免重复保存。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}}
async function archive(review:Review){if(saving.value||loading.value)return;saving.value=true;try{await request('/api/v1/owner/evolve','DELETE',operations.body('archive:'+review.id,{id:review.id,revision:review.revision}));operations.clear();if(!await load())ElMessage.warning('复盘已归档，但重新读取失败。请刷新确认。')}catch(e){ElMessage.error(e instanceof Error?e.message:'归档失败')}finally{saving.value=false}}
async function leave(){const ok=await discard();if(ok)dialog.value=false;return ok}onBeforeRouteLeave(leave);onBeforeRouteUpdate(leave);watch(()=>route.fullPath,()=>{history.value=null;load()},{immediate:true});const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
const unregisterMaterial=registerPageMaterial('/review',(scope)=>{if(loading.value||error.value||!data.value)throw Error('复盘材料尚未载入');let content:unknown;if(scope==='manual')content={search:search.value,include_archived:archived.value,records:rows.value};else if(scope==='daily')content={search:journalSearch.value,records:journalRows.value};else if(scope==='journal')content={records:data.value.coach_journal};else if(scope==='investment_journal'){if(!journalPanel.value)throw Error('投资日记尚未就绪');content=journalPanel.value.getMaterial()}else if(scope==='coach'){if(!coachPanel.value)throw Error('教练尚未就绪');content=coachPanel.value.getMaterial()}else if(scope==='period'){if(!periodPanel.value)throw Error('周期报告尚未就绪');content=periodPanel.value.getMaterial()}else throw Error('请选择复盘材料范围');return {scope,content}});onBeforeUnmount(unregisterMaterial);
</script>
<style scoped>
.journal-page {
  padding: 24px 28px 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header,
.header-actions,
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-header {
  align-items: flex-end;
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

.summary-grid,
.template-grid {
  display: grid;
  gap: 14px;
}

.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-card,
.template-card,
.entry-card {
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

.summary-label,
.template-kicker {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--el-text-color-secondary);
}

.summary-value {
  font-size: 28px;
  font-weight: 800;
}

.summary-card small {
  color: var(--el-text-color-secondary);
}

.template-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.template-card {
  padding: 18px 20px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.template-card:hover {
  transform: translateY(-2px);
  border-color: rgba(84, 167, 255, 0.18);
  box-shadow: 0 18px 40px rgba(35, 87, 163, 0.12);
}

.template-card b {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  color: var(--el-text-color-primary);
}

.template-card p {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.empty-state {
  padding: 40px 0;
}

.entry-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.entry-card {
  padding: 18px 20px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.entry-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 44px rgba(20, 43, 82, 0.12);
}

.entry-header,
.entry-meta,
.entry-footer,
.entry-actions,
.entry-tickers,
.entry-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.entry-header,
.entry-footer {
  justify-content: space-between;
}

.entry-date {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.entry-title {
  margin: 14px 0 10px;
  font-size: 20px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
}

.entry-preview {
  margin: 0;
  min-height: 72px;
  font-size: 14px;
  line-height: 1.75;
  color: var(--el-text-color-secondary);
}

.view-meta,
.view-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.view-content {
  margin: 18px 0;
  font-size: 14px;
  line-height: 1.85;
  white-space: pre-wrap;
  color: var(--el-text-color-primary);
}

@media (max-width: 1200px) {
  .summary-grid,
  .template-grid,
  .entry-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .journal-page {
    padding: 18px 16px 28px;
  }

  .page-header,
  .header-actions,
  .filter-bar,
  .entry-header,
  .entry-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid,
  .template-grid,
  .entry-list {
    grid-template-columns: 1fr;
  }
}
</style>

<style scoped>.filter-bar{flex-wrap:wrap}.filter-bar .el-input{max-width:300px}.versions{display:flex;gap:8px;flex-wrap:wrap}.document-text,.excerpt{white-space:pre-wrap;overflow-wrap:anywhere}.entry-card{cursor:default}.entry-card h3{overflow-wrap:anywhere}.entry-header{flex-wrap:wrap}.entry-meta{min-width:0;flex-wrap:wrap}.page-header{gap:12px;flex-wrap:wrap}</style>

<style scoped>.trade-reference-row{display:flex;justify-content:space-between;gap:12px;padding:14px 0;border-bottom:1px solid var(--el-border-color);flex-wrap:wrap}.trade-reference-row small{display:block;color:var(--el-text-color-secondary);margin-top:6px}</style>
<style scoped>.entry-card :deep(.el-alert--warning){background:rgba(242,169,59,.12);color:#ffd18b;border:1px solid rgba(242,169,59,.25);margin:12px 0}.versions{margin-top:12px}</style>
