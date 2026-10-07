<template>
  <el-drawer v-model="store.inboxOpen" title="行动收件箱" size="min(760px, 96vw)" :before-close="closeInbox">
    <div class="reminders-page">
      <AppDataState v-if="store.error" :tone="store.workspace?'stale':'error'" title="复核队列暂未更新" :description="store.error" action-label="重新加载" @action="store.load" />
      <div class="filter-bar"><div class="filter-tabs"><el-button :type="filter==='pending'?'primary':'default'" @click="filter='pending'">待处理 {{ store.pendingActions.length }}</el-button><el-button :type="filter==='all'?'primary':'default'" @click="filter='all'">全部记录</el-button></div><el-button :loading="store.loading" @click="store.load">刷新</el-button></div>
      <div v-if="rows.length" class="reminder-list"><article v-for="item in rows" :key="item.id" class="reminder-row is-watch"><div class="reminder-top"><div class="reminder-left"><span class="reminder-badge">{{ item.priority }}</span><span class="reminder-ticker">{{ item.symbol }}</span></div><el-tag size="small">{{ statusLabel(item.status) }}</el-tag></div><div class="reminder-title">{{ item.title }}</div><div class="reminder-detail">{{ item.reason }} · {{ item.href==='/review/diagnosis'?'生成':'截止' }} {{ item.due_on }}</div><p class="reminder-detail">{{ item.next_step }}</p><p class="reminder-detail">来源版本 {{ item.source_revision }} · {{ new Date(item.updated_at).toLocaleString('zh-CN') }}</p><p v-if="item.feedback?.reason" class="reminder-detail">反馈：{{ item.feedback.reason }}</p><p v-if="item.status==='snoozed'" class="reminder-detail">提醒日期：{{ item.feedback?.snooze_until }}</p><div class="reminder-footer"><el-button link type="primary" @click="openSource(item)">打开来源记录</el-button><el-button link type="primary" @click="edit(item)">更新处理状态</el-button></div></article></div>
      <AppDataState v-else-if="!store.loading" tone="empty" title="当前范围没有待处理事项" description="普通成交不会被自动变成决策或复盘任务。" />
    </div>
  </el-drawer>
  <el-dialog v-model="dialog" title="更新处理状态" width="min(480px, calc(100vw - 24px))" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="close">
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-form label-position="top"><el-form-item label="处理状态"><el-select v-model="form.status" :disabled="saving" style="width:100%"><el-option v-for="status in ['pending','confirmed','snoozed','resolved','ignored']" :key="status" :value="status" :label="statusLabel(status)" /></el-select></el-form-item><el-form-item label="原因 / 误报反馈"><el-input v-model="form.reason" type="textarea" :disabled="saving" maxlength="2000" :placeholder="form.status==='ignored'?'忽略时请填写原因':'可补充处理说明'" /></el-form-item><el-form-item v-if="form.status==='snoozed'" label="稍后提醒日期"><el-input v-model="form.snooze_until" type="date" :disabled="saving" /></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存反馈</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import {computed,ref,reactive,onBeforeUnmount,watch} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import AppDataState from '@/components/Global/AppDataState.vue'
import {useBusinessStore} from '@/stores/business'
import {operationCache,type Action} from '@/api/business'
import {request} from '@/api/owner'
const store=useBusinessStore(),router=useRouter(),filter=ref('pending'),dialog=ref(false),saving=ref(false),error=ref(''),target=ref<Action|null>(null),form=reactive({status:'pending',reason:'',snooze_until:''}),operations=operationCache()
let id='',baseline=''
const rows=computed(()=>filter.value==='pending'?store.pendingActions:store.workspace?.actions||[])
const statusLabel=(status:string)=>({pending:'待处理',confirmed:'已确认',snoozed:'稍后提醒',resolved:'已解决',ignored:'已忽略'}[status]||status)
const dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline)
function edit(item:Action){target.value=item;id=item.feedback?.id||crypto.randomUUID();Object.assign(form,{status:item.status,reason:String(item.feedback?.reason||''),snooze_until:String(item.feedback?.snooze_until||'')});baseline=JSON.stringify(form);operations.clear();error.value='';dialog.value=true}
async function discard(){if(saving.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的处理反馈？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await discard())dialog.value=false}
async function closeInbox(){if(await discard()){dialog.value=false;store.inboxOpen=false}}
async function openSource(item:Action){if(!(await discard()))return;dialog.value=false;store.inboxOpen=false;const routes:Record<string,string>={'/decisions':'/decisions','/plans':'/plan/build-up','/screening':'/research/screening'};router.push({path:routes[item.href]||item.href,query:{id:item.source_id}})}
async function save(){if(saving.value||!target.value)return;error.value='';if(form.status==='ignored'&&!form.reason.trim()){error.value='请填写忽略原因，便于之后复盘。';return}saving.value=true;try{await request('/api/v1/owner/business','POST',operations.body('feedback',{id,revision:target.value.feedback?.revision||0,kind:'action_state',data:{action_id:target.value.id,...form,snooze_until:form.status==='snoozed'?form.snooze_until:''}}));dialog.value=false;ElMessage.success('处理状态已保存');await store.load()}catch(e){error.value=e instanceof Error?e.message:'保存失败'}finally{saving.value=false}}
const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||saving.value){e.preventDefault();e.returnValue=''}}
window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload));onBeforeRouteLeave(discard)
watch(()=>store.inboxOpen,open=>{if(open)store.load()})
</script>

<style scoped lang="scss">
.reminders-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero-bar,
.summary-card,
.panel-card {
  border: 1px solid rgba(226, 233, 243, 0.9);
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
}

.hero-bar {
  padding: 16px 18px;
  border-radius: 18px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.hero-title {
  font-size: 22px;
  font-weight: 800;
  color: #102344;
}

.hero-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #6e8098;
  line-height: 1.55;
}

.hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  border-radius: 16px;
  padding: 14px 16px;
}

.summary-card.is-critical {
  background: linear-gradient(180deg, rgba(234, 91, 99, 0.08), rgba(255, 255, 255, 0.94));
}

.summary-card.is-watch {
  background: linear-gradient(180deg, rgba(242, 169, 59, 0.08), rgba(255, 255, 255, 0.94));
}

.summary-label {
  font-size: 12px;
  color: #6f8299;
}

.summary-value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 800;
  color: #102344;
}

.summary-detail {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #657a95;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.filter-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(300px, 0.72fr);
  gap: 10px;
}

.panel-card {
  border-radius: 18px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #102344;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #73839a;
}

.reminder-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reminder-row {
  width: 100%;
  text-align: left;
  padding: 11px 12px 10px;
  border-radius: 14px;
  border: 1px solid rgba(226, 233, 243, 0.96);
  background: rgba(255, 255, 255, 0.82);
  cursor: pointer;
  transition: all 0.18s ease;
}

.reminder-row:hover {
  border-color: rgba(112, 160, 215, 0.28);
  background: rgba(255, 255, 255, 0.96);
  transform: translateY(-1px);
}

.reminder-row.is-critical {
  border-color: rgba(234, 91, 99, 0.22);
  background: linear-gradient(180deg, rgba(234, 91, 99, 0.06), rgba(255, 255, 255, 0.95));
}

.reminder-row.is-watch {
  border-color: rgba(242, 169, 59, 0.22);
  background: linear-gradient(180deg, rgba(242, 169, 59, 0.06), rgba(255, 255, 255, 0.95));
}

.reminder-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.reminder-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reminder-badge,
.reminder-ticker,
.reminder-action {
  font-size: 11px;
  font-weight: 700;
}

.reminder-badge {
  color: #7e8fa6;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.reminder-ticker,
.reminder-action {
  color: #2855ff;
}

.reminder-title {
  margin-top: 5px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  color: #102344;
}

.reminder-detail {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #657a95;
}

.reminder-footer {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(151, 166, 186, 0.28);
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(226, 233, 243, 0.96);
  font-size: 13px;
  color: #4b607a;
}

.category-item:last-child {
  border-bottom: none;
}

.category-item b {
  font-size: 16px;
  color: #102344;
}

.side-notes {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(226, 233, 243, 0.96);
}

.ticker-clusters {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(226, 233, 243, 0.96);
}

.ticker-cluster-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.ticker-cluster {
  display: grid;
  grid-template-columns: 1fr auto;
  min-width: 118px;
  gap: 2px 8px;
  padding: 8px 10px;
  border: 1px solid rgba(207, 219, 235, 0.9);
  border-radius: 12px;
  background: rgba(248, 251, 255, 0.92);
  color: #405772;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.ticker-cluster:hover,
.ticker-cluster.is-active {
  border-color: rgba(55, 126, 255, 0.45);
  background: linear-gradient(180deg, rgba(236, 244, 255, 0.98), rgba(255, 255, 255, 0.95));
  box-shadow: 0 8px 18px rgba(38, 85, 160, 0.08);
}

.ticker-cluster span {
  font-size: 12px;
  font-weight: 800;
  color: #102344;
}

.ticker-cluster small {
  grid-column: 1 / -1;
  min-height: 16px;
  color: #7b8ca2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ticker-cluster b {
  color: #2c73ff;
}

.note-title {
  font-size: 13px;
  font-weight: 700;
  color: #102344;
}

.note-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #657a95;
  font-size: 12px;
  line-height: 1.7;
}

.closed-loop {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(226, 233, 243, 0.96);
}

.closed-loop-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(240, 246, 255, 0.8);
  color: #425874;
  font-size: 12px;
}

.closed-loop-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.closed-loop-item small {
  flex: none;
  color: #8a98aa;
}

@media (max-width: 1100px) {
  .summary-grid,
  .panel-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-bar,
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-meta {
    justify-content: flex-start;
  }
}
</style>

<style scoped>.reminders-page{padding:0;min-width:0}.reminder-title,.reminder-detail{overflow-wrap:anywhere}.reminder-footer{flex-wrap:wrap}</style>

<style scoped>
/* The global drawer uses the original dashboard's dark surface in both themes. */
.reminders-page .reminder-row.is-watch{background:linear-gradient(180deg,rgba(12,27,52,.98),rgba(9,20,39,.98));border-color:rgba(112,202,255,.22);cursor:default}
.reminders-page .reminder-row:hover{transform:none;border-color:rgba(112,202,255,.4)}
.reminders-page .reminder-title{color:#eaf5ff}
.reminders-page .reminder-detail,.reminders-page .reminder-badge{color:#a5bad3}
.reminders-page .reminder-ticker{color:#75d5ff}
</style>
