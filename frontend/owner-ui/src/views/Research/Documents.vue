<template>
 <div class="journal-page">
  <div class="page-header"><div><h2 class="page-title">{{ kind==='note'?'研究笔记':'投资判断' }}</h2><p class="page-subtitle">保存论点与证据；修改产生新版本，已有引用保持原样。</p></div><div class="header-actions"><el-button @click="load" :loading="loading">刷新</el-button><el-button type="primary" @click="edit()">新建{{ kind==='note'?'笔记':'判断' }}</el-button></div></div>
  <AppDataState v-if="error" tone="error" title="读取记录失败" :description="error" action-label="重试" @action="load" />
  <div class="filter-bar"><el-button @click="router.push('/research/notes')">研究笔记</el-button><el-button @click="router.push('/decisions')">投资判断</el-button><el-input v-model="search" placeholder="搜索标题或标的" aria-label="搜索记录" clearable /><el-checkbox v-model="archived">包含已归档</el-checkbox></div>
  <div v-loading="loading" class="entry-list"><article v-for="doc in rows" :key="doc.id" class="entry-card"><div class="entry-header"><div class="entry-meta"><el-tag>{{ doc.symbol }}</el-tag><span class="entry-date">v{{ doc.revision }} · {{ new Date(doc.updated_at).toLocaleString('zh-CN') }}{{ doc.archived?' · 已归档':'' }}</span></div><div class="entry-actions"><el-button v-if="!doc.archived" link type="primary" @click="edit(doc)">编辑</el-button><el-popconfirm v-if="!doc.archived" title="归档后保留历史与现有引用，继续？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(doc)"><template #reference><el-button link type="danger" :disabled="saving">归档</el-button></template></el-popconfirm></div></div><h3>{{ doc.title }}</h3><p class="excerpt">{{ readableHandoffNote(doc.id, doc.content).slice(0,220) }}</p><div class="versions"><el-button v-for="v in data?.versions.filter(v=>v.id===doc.id).slice().reverse()" :key="v.revision" size="small" @click="selected=v">查看 v{{ v.revision }}</el-button></div></article></div>
  <AppDataState v-if="!loading&&!error&&!rows.length" tone="empty" title="没有符合条件的记录" description="可以新建笔记，或调整筛选条件。" />
  <section v-if="kind==='decision'" class="entry-card"><h3>成交与判断关联</h3><p>可选引用已保存的判断版本，不改变交易金额，也不会下单。</p><p v-if="!data?.trades.length">尚无成交。录入交易后可在这里关联。</p><article v-for="trade in data?.trades" :key="trade.id" class="trade-reference-row"><div><strong>{{ trade.symbol }}</strong> · {{ trade.side==='buy'?'买入':'卖出' }} {{ trade.quantity }} · {{ new Date(trade.executed_at).toLocaleString('zh-CN') }}<small>成交 {{ trade.id.slice(0,8) }}</small></div><div><el-button v-if="linked(trade.id)?.decision_id" link @click="showDecision(trade.id)">查看判断 v{{ linked(trade.id)?.decision_revision }}</el-button><el-button @click="editLink(trade)">管理关联</el-button></div></article></section>
  <el-dialog v-model="linkDialog" title="成交判断关联" width="min(560px, calc(100vw - 24px))" :close-on-click-modal="false" :show-close="!saving" :close-on-press-escape="!saving" :before-close="closeLink"><p>只显示同一标的的判断版本。留空并保存可解除关联。</p><el-alert v-if="linkError" :title="linkError" type="error" :closable="false"/><el-select v-model="linkReference" clearable :value-on-clear="''" aria-label="成交判断版本" style="width:100%" :disabled="saving"><el-option label="不关联 / 解除关联" value="" /><el-option v-for="doc in linkOptions" :key="doc.id+'@'+doc.revision" :value="doc.id+'@'+doc.revision" :label="doc.title+' · v'+doc.revision" /></el-select><template #footer><el-button :disabled="saving" @click="closeLink">取消</el-button><el-button :loading="saving" type="primary" @click="saveLink">保存关联</el-button></template></el-dialog>
  <el-dialog v-model="dialog" :title="editing?'编辑记录':'新建记录'" width="min(760px, calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!saving" :close-on-press-escape="!saving">
   <el-alert v-if="saveError" :title="saveError" type="error" :closable="false" /><el-form label-position="top"><el-form-item label="标题"><el-input v-model="form.title" maxlength="120" :disabled="saving" /></el-form-item><el-form-item label="标的代码"><el-input v-model="form.symbol" maxlength="24" :disabled="saving" /></el-form-item><el-form-item :label="kind==='note'?'研究内容':'现在为什么行动'"><el-input v-model="form.content" type="textarea" :rows="6" maxlength="20000" :disabled="saving" /></el-form-item>
   <template v-if="kind==='decision'"><el-form-item v-for="field in fields" :key="field.key" :label="field.label"><el-input v-model="form[field.key]" :type="field.key==='review_on'?'date':'textarea'" maxlength="4000" :disabled="saving" /></el-form-item><el-form-item label="引用研究版本"><el-select v-model="reference" clearable :value-on-clear="''" :disabled="saving" style="width:100%" aria-label="引用研究版本"><el-option v-for="note in references" :key="note.id+'@'+note.revision" :value="note.id+'@'+note.revision" :label="note.title+' · v'+note.revision" /></el-select></el-form-item></template></el-form><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存记录</el-button></template>
  </el-dialog>
  <el-drawer :model-value="!!selected" title="记录历史" size="min(680px,96vw)" @close="selected=null"><template v-if="selected"><h2>{{ selected.title }}</h2><p>{{ selected.symbol }} · v{{ selected.revision }} · {{ selected.updated_at }}</p><h3>{{ selected.kind==='note'?'研究内容':'现在为什么行动' }}</h3><p class="document-text">{{ readableHandoffNote(selected.id, selected.content) }}</p><template v-if="selected.kind==='decision'"><section v-for="field in fields" :key="field.key"><h3>{{ field.label }}</h3><p class="document-text">{{ selected[field.key] }}</p></section><el-button v-if="selected.research_ref" @click="openReference(selected.research_ref)">查看固定研究依据 v{{ selected.research_ref.revision }}</el-button></template></template></el-drawer>
 </div>
</template>
<script setup lang="ts">
import {registerPageMaterial} from '@/api/pageMaterial'
import {computed,ref,reactive,watch,onBeforeUnmount} from 'vue'
import {useRoute,useRouter,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElDrawer,ElCheckbox,ElMessage,ElMessageBox} from 'element-plus'
import AppDataState from '@/components/Global/AppDataState.vue'
import {request,type Trade} from '@/api/owner'
import {operationCache} from '@/api/business'
import {readableHandoffNote} from '@/utils/handoffNote'
type Ref={id:string;revision:number}
type Link={trade_id:string;decision_id:string|null;decision_revision:number|null;revision:number}
type Field='support'|'counter_case'|'invalidation'|'risk_limit'|'review_on'
type Doc={id:string;revision:number;kind:'note'|'decision';title:string;symbol:string;content:string;support:string;counter_case:string;invalidation:string;risk_limit:string;review_on:string;research_ref:Ref|null;updated_at:string;archived:boolean}
const fields:Array<{key:Field;label:string}>=[{key:'support',label:'支持证据'},{key:'counter_case',label:'反方证据'},{key:'invalidation',label:'失效条件'},{key:'risk_limit',label:'风险上限'},{key:'review_on',label:'复核日期'}]
const route=useRoute(),router=useRouter(),kind=computed(()=>route.path==='/decisions'?'decision':'note'),data=ref<{documents:Doc[];versions:Doc[];trades:Trade[];links:Link[]}|null>(null),loading=ref(false),saving=ref(false),error=ref(''),saveError=ref(''),search=ref(''),archived=ref(false),dialog=ref(false),editing=ref<Doc|null>(null),selected=ref<Doc|null>(null),reference=ref(''),operations=operationCache()
const blank=()=>({title:'',symbol:'',content:'',support:'',counter_case:'',invalidation:'',risk_limit:'',review_on:''}),form=reactive(blank());let id='',baseline=''
const linkDialog=ref(false),linkTarget=ref<Trade|null>(null),linkReference=ref(''),linkError=ref('');let linkBaseline=''
const state=()=>JSON.stringify([form,reference.value]),dirty=computed(()=>(dialog.value&&state()!==baseline)||(linkDialog.value&&linkReference.value!==linkBaseline))
const rows=computed(()=>data.value?.documents.filter(d=>d.kind===kind.value&&(archived.value||!d.archived)&&(!search.value||(d.title+' '+d.symbol).toLowerCase().includes(search.value.toLowerCase())))||[])
const unregisterMaterials=['/research/notes','/decisions'].map(path=>registerPageMaterial(path,()=>{
  if(route.path!==path||loading.value||saving.value||error.value||!data.value||dialog.value||linkDialog.value||selected.value)throw Error('请先完成记录加载并关闭编辑、关联或历史窗口，再载入材料。')
  const refs=rows.value.flatMap(d=>d.research_ref?[d.research_ref]:[])
  const unique=refs.filter((r,i)=>refs.findIndex(x=>x.id===r.id&&x.revision===r.revision)===i)
  return {scope:'filtered_research_documents',kind:kind.value,filters:{search:search.value,include_archived:archived.value},records:rows.value,
    referenced_research:unique.map(r=>({reference:r,record:data.value!.versions.find(v=>v.id===r.id&&v.revision===r.revision)??null})),
    notice:'当前筛选的已保存笔记或判断；引用研究保留指定版本，缺失引用为null，不替换为最新版本。不包含筛选外文档、逐笔成交、关联编辑或未保存输入。归档状态不是当前有效依据。'}
}))
onBeforeUnmount(()=>unregisterMaterials.forEach(remove=>remove()))
const references=computed(()=>data.value?.versions.filter(d=>d.kind==='note'&&!d.archived&&d.symbol===form.symbol.trim().toUpperCase()&&(!data.value?.documents.find(c=>c.id===d.id)?.archived||(editing.value?.research_ref?.id===d.id&&editing.value?.research_ref?.revision===d.revision)))||[])
async function load(){if(loading.value)return false;loading.value=true;error.value='';try{data.value=await request('/api/v1/owner/documents');const target=data.value?.documents.find(d=>d.id===route.query.id);selected.value=target||null;return true}catch(e){data.value=null;selected.value=null;error.value=e instanceof Error?e.message:'读取失败';return false}finally{loading.value=false}}
function edit(doc?:Doc){editing.value=doc||null;id=doc?.id||crypto.randomUUID();Object.assign(form,blank());if(doc)for(const key of Object.keys(blank()) as Array<keyof ReturnType<typeof blank>>)form[key]=key==='content'?readableHandoffNote(doc.id,doc.content):doc[key];else if(typeof route.query.symbol==='string')form.symbol=route.query.symbol;reference.value=doc?.research_ref?doc.research_ref.id+'@'+doc.research_ref.revision:'';operations.clear();saveError.value='';baseline=state();dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的研究记录？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){if(saving.value||loading.value)return;saveError.value='';if(!form.title.trim()||!form.symbol.trim()||!form.content.trim()||(kind.value==='decision'&&fields.some(f=>!form[f.key].trim()))){saveError.value='请填写标题、标的和内容；投资判断的五项复核字段也必须完整。';return}const [rid,revision]=(reference.value||'').split('@');saving.value=true;try{await request('/api/v1/owner/documents','POST',operations.body('save',{id,revision:editing.value?.revision||0,kind:kind.value,...form,research_ref:kind.value==='decision'&&rid?{id:rid,revision:Number(revision)}:null}));dialog.value=false;operations.clear();if(await load())ElMessage.success('记录已保存，历史依据保留');else ElMessage.warning('记录已保存，但重新读取失败。请刷新确认，避免重复保存。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}}
async function archive(doc:Doc){if(saving.value||loading.value)return;saving.value=true;try{await request('/api/v1/owner/documents','DELETE',operations.body('archive:'+doc.id,{id:doc.id,revision:doc.revision}));operations.clear();if(!await load())ElMessage.warning('记录已归档，但重新读取失败。请刷新确认。')}catch(e){ElMessage.error(e instanceof Error?e.message:'归档失败')}finally{saving.value=false}}
function openReference(ref:Ref){const note=data.value?.versions.find(d=>d.id===ref.id&&d.revision===ref.revision);if(note)selected.value=note;else ElMessage.error('找不到引用版本，请重新加载记录')}
const linked=(tradeId:string)=>data.value?.links.find(l=>l.trade_id===tradeId)
const linkOptions=computed(()=>data.value?.versions.filter(d=>d.kind==='decision'&&!d.archived&&d.symbol===linkTarget.value?.symbol&&(!data.value?.documents.find(c=>c.id===d.id)?.archived||(linked(linkTarget.value!.id)?.decision_id===d.id&&linked(linkTarget.value!.id)?.decision_revision===d.revision)))||[])
function editLink(trade:Trade){linkTarget.value=trade;const link=linked(trade.id);linkReference.value=link?.decision_id?link.decision_id+'@'+link.decision_revision:'';linkBaseline=linkReference.value;linkError.value='';operations.clear();linkDialog.value=true}
function showDecision(tradeId:string){const link=linked(tradeId);const doc=data.value?.versions.find(d=>d.id===link?.decision_id&&d.revision===link?.decision_revision);if(doc)selected.value=doc}
async function closeLink(){if(await discard())linkDialog.value=false}
async function saveLink(){if(saving.value||loading.value||!linkTarget.value)return;if(linkReference.value===linkBaseline){linkDialog.value=false;return}const link=linked(linkTarget.value.id),[decision_id,rev]=(linkReference.value||'').split('@');saving.value=true;linkError.value='';try{await request('/api/v1/owner/trade-reference','POST',operations.body('link:'+linkTarget.value.id,{trade_id:linkTarget.value.id,trade_revision:linkTarget.value.revision,revision:link?.revision||0,decision_id:decision_id||null,decision_revision:decision_id?Number(rev):null}));linkDialog.value=false;operations.clear();if(await load())ElMessage.success('关联已保存，交易金额未改变');else ElMessage.warning('关联已保存，但重新读取失败。请刷新确认。')}catch(e){linkError.value=e instanceof Error?e.message:'保存失败'}finally{saving.value=false}}
async function leave(){const ok=await discard();if(ok){dialog.value=false;linkDialog.value=false;}return ok}
onBeforeRouteLeave(leave);onBeforeRouteUpdate(leave);watch(()=>route.fullPath,()=>{selected.value=null;load()},{immediate:true});const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
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
