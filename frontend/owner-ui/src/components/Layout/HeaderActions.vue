<template><div class="header-actions"><el-tooltip content="Ask AI · ⌘/Ctrl + J" placement="bottom"><span class="ask-trigger-shell"><button type="button" class="ask-awesome-trigger" :class="{active:ask.visible}" :aria-expanded="ask.visible" aria-label="打开 Ask Awesome 助手" @click="ask.open()"><span class="ask-trigger-mark"><img src="/logo.svg" alt=""/></span><span class="ask-trigger-copy"><b>Ask AI</b><small>证据助理</small></span><span class="ask-trigger-key">{{ shortcut }}</span></button></span></el-tooltip><el-popover v-model:visible="messagesOpen" placement="bottom-end" :width="420" trigger="click" popper-class="awesome-notification-popover" :show-arrow="false" @show="business.load()">
<template #reference><el-badge :value="business.pendingActions.length" :hidden="!business.pendingActions.length"><el-button text class="action-btn" aria-label="打开消息中心" :aria-expanded="messagesOpen"><el-icon><Bell /></el-icon></el-button></el-badge></template>
<section class="notif-panel" aria-label="消息中心" :aria-busy="business.loading||saving">
<div class="notif-panel-head"><div><div class="notif-panel-title">消息中心</div><div class="notif-panel-subtitle">{{ business.pendingActions.length ? `${business.pendingActions.length} 项待复核` : '查看已保存记录的复核提醒' }}</div></div><el-button size="small" type="primary" plain :disabled="saving" @click="openInbox">行动收件箱</el-button></div>
<div class="notif-toolbar"><el-segmented v-model="messageFilter" :options="[{label:'待处理',value:'pending'},{label:'稍后提醒',value:'snoozed'}]" :disabled="saving"/><span class="priority-counts">P0 {{ priorityCount('P0') }} · P1 {{ priorityCount('P1') }}</span></div>
<el-alert v-if="business.error||messageError" :title="messageError||business.error" type="error" :closable="false"/><el-button v-if="business.error" size="small" :loading="business.loading" @click="business.load()">重新加载</el-button>
<el-scrollbar max-height="300px"><el-empty v-if="!visibleMessages.length&&!business.loading&&!business.error" :description="messageFilter==='pending'?'当前没有待处理事项':'当前没有稍后提醒事项'"/><div v-else class="notif-list"><article v-for="item in visibleMessages" :key="item.id" class="notif-item" :class="`is-${item.priority.toLowerCase()}`" :data-action-item-id="item.id"><div class="row"><strong class="priority">{{ item.priority }}</strong><time>{{ item.due_on }}</time></div><button type="button" class="title" :disabled="saving" @click="openSource(item)">{{ item.title }}</button><p class="content">{{ item.reason }}</p><div class="source-line">{{ item.symbol }} · 来源版本 {{ item.source_revision }}</div><div v-if="messageFilter==='pending'" class="ops"><el-button size="small" text type="primary" :disabled="saving" @click="openSource(item)">复核</el-button><el-button size="small" text :disabled="saving||business.loading||!!business.error" @click="updateMessage(item,'resolved')">完成</el-button><el-button size="small" text :disabled="saving||business.loading||!!business.error" @click="updateMessage(item,'snoozed')">明天</el-button><el-button size="small" text :disabled="saving||business.loading||!!business.error" @click="ignoreMessage(item)">忽略</el-button></div><p v-else class="content">提醒日期：{{ item.feedback?.snooze_until }}</p></article></div></el-scrollbar></section></el-popover><el-button text class="action-btn" aria-label="切换明暗主题" @click="appStore.applyTheme(appStore.theme === 'dark' ? 'light' : 'dark')"><el-icon><Moon v-if="appStore.theme === 'light'" /><Sunny v-else /></el-icon></el-button><el-tooltip content="系统设置" placement="bottom"><el-button text class="action-btn" aria-label="系统设置" @click="router.push('/settings')"><el-icon><Setting /></el-icon></el-button></el-tooltip></div></template>
<script setup lang="ts">
import { useAskStore } from '@/stores/ask'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { ElBadge, ElMessageBox, ElPopover, ElSegmented, ElScrollbar, ElEmpty } from 'element-plus'
import { watch, ref, computed } from 'vue'
import { operationCache, type Action } from '@/api/business'
import { request } from '@/api/owner'
import { useRoute } from 'vue-router'
import { useBusinessStore } from '@/stores/business'
import { Setting, Moon, Sunny, Bell } from '@element-plus/icons-vue'
const ask=useAskStore(),shortcut=/Mac|iPhone|iPad/.test(navigator.platform)?'⌘J':'Ctrl J'
const router = useRouter(), appStore = useAppStore(), business = useBusinessStore(), route = useRoute()
const messagesOpen=ref(false),messageFilter=ref('pending'),messageError=ref(''),saving=ref(false),operations=operationCache(),feedbackIds=new Map<string,string>()
const visibleMessages=computed(()=>messageFilter.value==='pending'?business.pendingActions:business.workspace?.actions.filter(a=>a.status==='snoozed')||[])
const priorityCount=(priority:string)=>business.pendingActions.filter(a=>a.priority===priority).length
function openInbox(){messagesOpen.value=false;business.inboxOpen=true}
function openSource(item:Action){messagesOpen.value=false;const routes:Record<string,string>={'/plans':'/plan/build-up','/screening':'/research/screening'};router.push({path:routes[item.href]||item.href,query:{id:item.source_id}})}
async function updateMessage(item:Action,status:string,reason=''){
 if(saving.value||business.loading||business.error)return
 saving.value=true;messageError.value=''
 if(!feedbackIds.has(item.id))feedbackIds.set(item.id,crypto.randomUUID())
 const tomorrow=new Date();tomorrow.setUTCDate(tomorrow.getUTCDate()+1)
 try{
  await request('/api/v1/owner/business','POST',operations.body(`message:${item.id}:${status}`,{id:item.feedback?.id||feedbackIds.get(item.id),revision:item.feedback?.revision||0,kind:'action_state',data:{action_id:item.id,status,reason,snooze_until:status==='snoozed'?tomorrow.toISOString().slice(0,10):''}}))
  operations.clear();await business.load()
 }catch(e){messageError.value=e instanceof Error?e.message:'处理失败，请重新加载后核对'}finally{saving.value=false}
}
async function ignoreMessage(item:Action){
 if(saving.value)return
 try{const {value}=await ElMessageBox.prompt('填写忽略原因，便于之后复盘。','忽略提醒',{confirmButtonText:'忽略',cancelButtonText:'取消',inputValidator:value=>!value?.trim()?'请填写忽略原因':value.trim().length>2000?'原因最多2000字':true});await updateMessage(item,'ignored',value.trim())}catch(e){if(e!=='cancel'&&e!=='close')messageError.value='无法打开忽略操作，请重试'}
}
watch(()=>route.fullPath,()=>{messagesOpen.value=false;business.load()},{immediate:true})
</script>
<style lang="scss" scoped>
.ask-trigger-shell { display: inline-flex; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;

  .action-btn {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(112, 202, 255, 0.12);
    background: rgba(255, 255, 255, 0.03);
    color: #d7ebff;

    .el-icon { font-size: 18px; }
  }

  .action-btn:hover {
    border-color: rgba(112, 202, 255, 0.2);
    background: rgba(85, 194, 255, 0.08);
    color: #ffffff;
  }
}

.ask-awesome-trigger {
  height: 38px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 9px 0 7px;
  border: 1px solid rgba(87, 202, 255, 0.18);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(49, 125, 230, 0.11), rgba(46, 206, 220, 0.045));
  color: #dcefff;
  cursor: pointer;
  transition: 0.2s ease;

  &:hover,
  &.active {
    border-color: rgba(83, 217, 255, 0.42);
    background: linear-gradient(135deg, rgba(49, 125, 230, 0.2), rgba(46, 206, 220, 0.08));
    box-shadow: 0 0 24px rgba(48, 171, 255, 0.1);
  }
}

.ask-trigger-mark {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(52, 137, 232, 0.12);

  img { width: 20px; height: 20px; }
}

.ask-trigger-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.05;

  b { font-size: 10px; font-weight: 700; }
  small { margin-top: 3px; color: #718da8; font-size: 7px; }
}

.ask-trigger-key {
  padding: 3px 5px;
  border: 1px solid rgba(109, 192, 239, 0.12);
  border-radius: 5px;
  color: #567791;
  font: 600 7px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
}

@media (max-width: 1280px) {
  .ask-trigger-copy,
  .ask-trigger-key { display: none; }
  .ask-awesome-trigger { width: 38px; justify-content: center; padding: 0; }
}

:global(.awesome-notification-popover) {
  width: min(420px, calc(100vw - 24px)) !important;
  max-width: calc(100vw - 24px);
  padding: 0 !important;
  overflow: hidden;
  border: 1px solid rgba(112, 202, 255, 0.18) !important;
  border-radius: 18px !important;
  background:
    linear-gradient(180deg, rgba(17, 34, 58, 0.98), rgba(9, 21, 40, 0.98)) !important;
  background-color: #091528 !important;
  box-shadow: 0 24px 54px rgba(0, 0, 0, 0.34), inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

.notif-panel {
  padding: 14px;
  color: #dcefff;
}

.notif-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(112, 202, 255, 0.12);
}

.notif-panel-title {
  font-size: 15px;
  font-weight: 800;
  color: #f3f9ff;
}

.notif-panel-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #7f95b0;
}

.notif-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.priority-counts,
.source-line {
  color: #66819c;
  font-size: 10px;
}

.notif-list { display: flex; flex-direction: column; gap: 8px; }
.notif-item { padding: 10px; border-radius: 10px; border: 1px solid rgba(112, 202, 255, 0.1); background: rgba(255,255,255,0.018); }
.notif-item.is-p0 { border-left: 2px solid rgba(255, 104, 122, 0.7); }
.notif-item.is-p1 { border-left: 2px solid rgba(242, 188, 105, 0.6); }
.notif-item .row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 4px; }
.notif-item .priority { color: #f2bc69; font-size: 10px; letter-spacing: 0.04em; }
.notif-item.is-p0 .priority { color: #ff7889; }
.notif-item .title {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: #edf8ff;
  font: inherit;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  margin-bottom: 4px;
}
.notif-item .title:hover { text-decoration: underline; }
.notif-item .content { margin: 0 0 5px; font-size: 11px; line-height: 1.5; color: var(--el-text-color-regular); }
.notif-item .ops { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
.notif-item .title,.notif-item .content,.source-line { overflow-wrap: anywhere; }

@media (max-width: 560px) {
  .header-actions :deep(.el-badge__content.is-fixed) {
    transform: translateY(-50%) translateX(65%);
  }

  .notif-toolbar,
  .notif-panel-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
