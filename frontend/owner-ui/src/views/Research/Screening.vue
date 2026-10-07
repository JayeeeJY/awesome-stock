<template>
 <div class="stock-screening">
  <div class="page-header"><h1 class="page-title">机会筛选</h1><p class="page-description">筛选自己的候选与证据，再交接给研究。缺失、过期和未核验材料不会算作通过。</p></div>
  <AppDataState v-if="error" tone="error" title="筛选未更新" :description="error" action-label="重新加载" @action="load" />
  <el-card class="filter-panel" shadow="never"><template #header><div class="card-header"><span>筛选条件</span><el-tag>个人候选池</el-tag><el-button @click="edit('candidate')">新增候选</el-button><el-button @click="edit('evidence')">新增证据</el-button><el-button @click="archiveOpen=true">归档记录</el-button></div></template><el-form label-position="top" class="criteria"><el-form-item label="市场"><el-select v-model="filters.market" aria-label="筛选市场"><el-option v-for="m in ['ALL','US','HK','CN']" :key="m" :value="m" :label="m==='ALL'?'全部市场':m" /></el-select></el-form-item><el-form-item label="最低营收增长 %"><el-input v-model="filters.growth_min" /></el-form-item><el-form-item label="最低毛利率 %"><el-input v-model="filters.margin_min" /></el-form-item><el-form-item label="最高净债务 / EBITDA"><el-input v-model="filters.debt_max" /></el-form-item><el-button type="primary" :loading="loading" @click="load">按条件筛选</el-button></el-form></el-card>
  <el-alert v-if="workspace&&!filtersCurrent" title="筛选条件已修改，请重新筛选后再比较或交接结果。" type="warning" :closable="false"/><el-card class="results-panel" shadow="never"><template #header><div class="card-header"><span>候选结果 · {{ rows.length }}</span><el-button :disabled="!filtersCurrent||picked.length<2||picked.length>4" @click="compareOpen=true">比较选定候选</el-button><el-button :disabled="!filtersCurrent||!picked.length||picked.length>4||!!error" :loading="saving" @click="handoff">交接为研究笔记</el-button></div></template><p>满足输入阈值不等于投资建议；比较不生成排名。可选 1–4 个交接，2–4 个比较。</p><el-table :data="rows" row-key="id" @selection-change="selection"><el-table-column type="selection" width="45"/><el-table-column label="标的" min-width="170"><template #default="{row}"><strong>{{ row.candidate.symbol }}</strong><p>{{ row.candidate.title }}</p></template></el-table-column><el-table-column label="筛选结果" min-width="250"><template #default="{row}"><el-tag :type="row.status==='matched'?'success':'warning'">{{ status(row.status) }}</el-tag><p>证据缺口：{{ names(row.gaps) }}</p><p>不满足阈值：{{ names(row.outside_threshold) }}</p></template></el-table-column><el-table-column label="观察逻辑" min-width="220"><template #default="{row}">{{ row.candidate.thesis }}</template></el-table-column><el-table-column label="操作" width="160"><template #default="{row}"><el-button link @click="edit('candidate',row.candidate)">更正</el-button><el-button link @click="historyId=row.id">历史</el-button><el-popconfirm title="归档候选并保留历史？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(row.candidate)"><template #reference><el-button link :disabled="saving">归档</el-button></template></el-popconfirm></template></el-table-column></el-table></el-card>
  <el-card class="results-panel" shadow="never"><template #header>证据账本</template><el-input v-model="search" placeholder="搜索标的或证据" aria-label="搜索证据" clearable/><article v-for="e in evidence" :key="e.id" class="evidence-card"><h3>{{ e.symbol }} · {{ e.title }}</h3><p>{{ metrics[String(e.metric)] }}：{{ e.value??'缺失' }} · {{ e.verification==='verified'?'已人工核验':'尚未核验' }}</p><p>人工方向：{{ e.direction==='weakens'?'削弱判断':e.direction==='strengthens'?'支持判断':'未标记 / 中性' }}</p><p>来源：{{ e.source }}</p><p>观察 {{ e.as_of }} · 复核截止 {{ e.expires_on }}</p><el-button @click="edit('evidence',e)">更正证据</el-button><el-button @click="historyId=e.id">版本历史</el-button><el-popconfirm title="归档证据并保留历史？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(e)"><template #reference><el-button :disabled="saving">归档证据</el-button></template></el-popconfirm></article></el-card>
  <el-dialog v-model="dialog" :title="formKind==='candidate'?'候选记录':'证据记录'" width="min(680px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!saving" :close-on-press-escape="!saving"><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item v-for="field in fields" :key="field.key" :label="field.label"><el-select v-if="field.options" v-model="form[field.key]" :disabled="saving" style="width:100%"><el-option v-for="o in field.options" :key="o.value" :label="o.label" :value="o.value" /></el-select><el-input v-else v-model="form[field.key]" :disabled="saving" :type="field.type||'text'" :maxlength="field.max||1000" /></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存记录</el-button></template></el-dialog>
  <el-drawer v-model="compareOpen" title="候选证据比较" size="min(1000px,96vw)"><div class="comparison"><article v-for="row in rows.filter(r=>picked.includes(r.id))" :key="row.id"><h2>{{ row.candidate.symbol }}</h2><p>{{ status(row.status) }}</p><section v-for="metric in ['revenue_growth','gross_margin','net_debt_ebitda']" :key="metric"><h3>{{ metrics[metric] }}</h3><template v-if="row.facts[metric]"><p>{{ row.facts[metric]?.value??'缺失' }} · {{ row.facts[metric]?.verification==='verified'?'已人工核验':'尚未核验' }}</p><p>{{ row.facts[metric]?.source }}</p><p>{{ row.facts[metric]?.as_of }} / 截止 {{ row.facts[metric]?.expires_on }}</p></template><p v-else>尚无证据</p></section></article></div></el-drawer>
  <el-drawer v-model="archiveOpen" title="归档记录" size="min(680px,96vw)"><p>归档保留历史，不代表隐私删除。</p><article v-for="record in workspace?.versions.filter(r=>r.archived&&['candidate','evidence'].includes(r.kind))" :key="record.id" class="evidence-card"><h3>{{ record.symbol }} · {{ record.title }}</h3><el-button @click="archiveOpen=false;historyId=record.id">查看归档历史</el-button></article></el-drawer>
  <el-drawer :model-value="!!historyId" title="版本历史" size="min(680px,96vw)" @close="historyId='' "><article v-for="record in workspace?.versions.filter(r=>r.id===historyId).slice().reverse()" :key="record.revision" class="evidence-card"><h3>{{ record.title }} · v{{ record.revision }}{{ record.archived?' · 已归档':'' }}</h3><p>{{ record.updated_at }}</p><dl><template v-for="field in record.kind==='candidate'?candidateFields:evidenceFields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ record[field.key]??'缺失' }}</dd></template></dl></article></el-drawer>
 </div>
</template>
<script setup lang="ts">
import {ref,reactive,computed,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {getWorkspace,operationCache,type Workspace,type BusinessRecord} from '@/api/business'
import {registerPageMaterial} from '@/api/pageMaterial'
import AppDataState from '@/components/Global/AppDataState.vue'
type Field={key:string;label:string;type?:'text'|'textarea'|'date';max?:number;options?:Array<{value:string;label:string}>}
const metrics:Record<string,string>={revenue_growth:'营收增长 %',gross_margin:'毛利率 %',net_debt_ebitda:'净债务 / EBITDA',pe:'市盈率 P/E',pb:'市净率 P/B',other:'其他证据'}
const candidateFields:Field[]=[{key:'symbol',label:'标的代码',max:24},{key:'title',label:'候选名称',max:120},{key:'market',label:'市场',options:['US','HK','CN'].map(value=>({value,label:value}))},{key:'thesis',label:'观察逻辑',type:'textarea',max:4000},{key:'review_on',label:'复核日期',type:'date'}]
const evidenceFields:Field[]=[{key:'symbol',label:'标的代码',max:24},{key:'title',label:'证据说明',type:'textarea'},{key:'metric',label:'指标',options:Object.entries(metrics).map(([value,label])=>({value,label}))},{key:'direction',label:'对当前判断的影响（人工标记）',options:[{value:'neutral',label:'未标记 / 中性'},{value:'strengthens',label:'支持判断'},{value:'weakens',label:'削弱判断'}]},{key:'value',label:'指标值（可留空）'},{key:'source',label:'来源链接或文件说明'},{key:'as_of',label:'观察日期',type:'date'},{key:'expires_on',label:'复核截止日期',type:'date'},{key:'verification',label:'人工核验状态',options:[{value:'unverified',label:'尚未核验'},{value:'verified',label:'已人工核验'}]}]
type Row={id:string;candidate:BusinessRecord;status:string;gaps:string[];outside_threshold:string[];facts:Record<string,BusinessRecord|null>}
const router=useRouter(),workspace=ref<Workspace|null>(null),rows=ref<Row[]>([]),picked=ref<string[]>([]),filters=reactive({market:'ALL',growth_min:'12',margin_min:'35',debt_max:'2'}),loading=ref(false),saving=ref(false),error=ref(''),search=ref(''),dialog=ref(false),saveError=ref(''),formKind=ref<'candidate'|'evidence'>('candidate'),form=reactive<Record<string,string>>({}),editing=ref<BusinessRecord|null>(null),historyId=ref(''),compareOpen=ref(false),archiveOpen=ref(false),operations=operationCache();let id='',baseline='',handoffId=''
const fields=computed(()=>formKind.value==='candidate'?candidateFields:evidenceFields),dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline),evidence=computed(()=>workspace.value?.records.filter(r=>r.kind==='evidence'&&(!search.value||(r.title+' '+r.symbol).toLowerCase().includes(search.value.toLowerCase())))||[])
const appliedFilters=ref(''),screenedAt=ref('')
const filtersCurrent=computed(()=>appliedFilters.value===JSON.stringify(filters))
const unregisterMaterial=registerPageMaterial('/research/screening',()=>{
  if(loading.value||saving.value||error.value||!workspace.value||!filtersCurrent.value||dialog.value||historyId.value||archiveOpen.value)throw Error('请先按当前条件重新筛选，并关闭编辑或历史窗口，再载入材料。')
  return {scope:picked.value.length?'selected_screening_results':'current_screening_results',filters:JSON.parse(appliedFilters.value),screened_at:screenedAt.value,
    rows:picked.value.length?rows.value.filter(r=>picked.value.includes(r.id)):rows.value,
    notice:'当前条件计算的候选及固定指标依据；保留缺口、未核验与不满足阈值状态。选择候选时仅包含选择项；不包含独立证据账本搜索结果、其他候选或AI草稿。不代表排名或投资建议。'}
})
onBeforeUnmount(unregisterMaterial)
const status=(value:string)=>({matched:'满足输入阈值',excluded:'不满足阈值',needs_evidence:'需要补充或核验材料'}[value]||value),names=(values:string[])=>values.map(v=>metrics[v]||v).join('、')||'无'
function selection(values:Row[]){picked.value=values.map(r=>r.id)}
async function load(){if(loading.value)return false;loading.value=true;error.value='';try{const criteria={...filters};const state=await getWorkspace();const result=await request<{rows:Omit<Row,'id'>[]}>('/api/v1/owner/screen','POST',criteria);workspace.value=state;appliedFilters.value=JSON.stringify(criteria);screenedAt.value=new Date().toISOString();rows.value=result.rows.map(r=>({...r,id:r.candidate.id}));picked.value=[];compareOpen.value=false;return true}catch(e){workspace.value=null;rows.value=[];picked.value=[];appliedFilters.value='';screenedAt.value='';compareOpen.value=false;historyId.value='';archiveOpen.value=false;error.value=e instanceof Error?e.message:'读取失败';return false}finally{loading.value=false}}
function edit(kind:'candidate'|'evidence',record?:BusinessRecord){formKind.value=kind;editing.value=record||null;id=record?.id||crypto.randomUUID();for(const key of Object.keys(form))delete form[key];for(const field of fields.value)form[field.key]=record?String(record[field.key]??(field.key==='direction'?'neutral':'')):(field.options?.[0]?.value||'');baseline=JSON.stringify(form);saveError.value='';operations.clear();dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的候选或证据？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function save(){if(saving.value||loading.value)return;saveError.value='';if(fields.value.some(f=>f.key!=='value'&&!form[f.key]?.trim())){saveError.value='请填写必填字段；指标值允许留空。';return}saving.value=true;try{await request('/api/v1/owner/business','POST',operations.body('save',{id,revision:editing.value?.revision||0,kind:formKind.value,data:{...form}}));dialog.value=false;operations.clear();if(await load())ElMessage.success('记录已保存');else ElMessage.warning('记录已保存，但重新读取失败。请刷新确认，避免重复保存。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败'}finally{saving.value=false}}
async function archive(record:BusinessRecord){if(saving.value||loading.value)return;saving.value=true;try{await request('/api/v1/owner/business','DELETE',operations.body('archive:'+record.id,{id:record.id,revision:record.revision}));operations.clear();if(!await load())ElMessage.warning('记录已归档，但重新读取失败。请刷新确认。')}catch(e){ElMessage.error(e instanceof Error?e.message:'归档失败')}finally{saving.value=false}}
async function handoff(){if(saving.value||!filtersCurrent.value||!workspace.value||!picked.value.length||picked.value.length>4)return;saving.value=true;handoffId ||= crypto.randomUUID();try{await request('/api/v1/owner/handoff','POST',operations.body('handoff',{id:handoffId,candidate_ids:[...picked.value].sort(),expected_token:workspace.value.token}));handoffId='';operations.clear();ElMessage.success('固定证据快照已保存为研究笔记');saving.value=false;await router.push('/research/notes')}catch(e){ElMessage.error(e instanceof Error?e.message:'交接失败，请刷新核对证据')}finally{saving.value=false}}
onBeforeRouteLeave(async()=>{const ok=await discard();if(ok)dialog.value=false;return ok});const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload));onMounted(load)
</script>

<style lang="scss" scoped>
.stock-screening {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .filter-panel {
    margin-bottom: 24px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-actions {
        display: flex;
        gap: 8px;
      }
    }

    .filter-form {
      .filter-actions {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-top: 24px;
      }
    }
  }

  .results-panel {
    .pagination-wrapper {
      display: flex;
      justify-content: center;
      margin-top: 24px;
    }
  }

  .text-red {
    color: #f56c6c;
  }

  .text-green {
    color: #67c23a;
  }
}
</style>

<style scoped>.criteria{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;align-items:end}.card-header{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.evidence-card{padding:18px 0;border-bottom:1px solid var(--el-border-color);overflow-wrap:anywhere}.comparison{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px}.comparison article,.comparison p,dd{overflow-wrap:anywhere}.results-panel{margin-top:20px}dd{margin:8px 0 16px}.filter-panel,.results-panel{min-width:0}@media(max-width:480px){.criteria{grid-template-columns:1fr}.page-title{font-size:24px}}</style>
