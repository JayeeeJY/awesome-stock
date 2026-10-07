<template><div class="settings-page"><section class="settings-hero"><div class="settings-hero-copy"><div class="settings-kicker">Awesome Stock Control Center</div><h1 class="settings-title">账户与数据管理</h1><p class="settings-subtitle">管理自己的登录口令、完整备份和数据副本。</p></div></section><div class="settings-layout"><aside class="settings-sidebar"><button class="settings-nav-item is-active">账户与数据</button><button class="settings-nav-item" @click="router.push('/settings/appearance')">外观</button><button class="settings-nav-item" @click="router.push('/settings/connections')">数据与 AI 连接</button><button class="settings-nav-item" @click="router.push('/settings/transfer')">导入与导出</button></aside><div class="settings-main"><AppDataState v-if="error" tone="error" title="操作未完成" :description="error"/><p v-if="notice" role="status" class="notice">{{ notice }}</p><section class="settings-panel"><div class="panel-title">本地账号与存储</div><p>当前账号：{{ settings?.username||'读取中' }}</p><dl><template v-for="field in locations" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ settings?.[field.key] }}</dd></template></dl><el-button :disabled="busy" @click="load">刷新信息</el-button></section>
<section class="settings-panel"><div class="panel-title">修改登录口令</div><p>修改成功后所有登录会话失效，模型与行情连接清除，需要重新登录。</p><el-form label-position="top"><el-form-item label="当前登录口令"><el-input v-model="password.current" type="password" autocomplete="current-password" :disabled="busy"/></el-form-item><el-form-item label="新口令（12–128字符）"><el-input v-model="password.next" type="password" autocomplete="new-password" :disabled="busy"/></el-form-item><el-form-item label="再次填写新口令"><el-input v-model="password.repeat" type="password" autocomplete="new-password" :disabled="busy"/></el-form-item></el-form><el-button :disabled="busy" @click="changePassword">修改口令并重新登录</el-button></section>
<section class="settings-panel"><div class="panel-title">完整备份</div><p>完整备份包含账本、历史和口令哈希，未加密，请妥善保管。模型及行情密钥不进入备份。</p><div class="panel-actions"><el-button :disabled="busy" @click="backup">创建完整备份</el-button><el-button :disabled="busy" @click="listBackups">查看本地备份</el-button></div><p v-if="backups!==null&&!backups.length">当前目录没有完整备份。</p><article v-for="item in backups" :key="item.name" class="surface-card"><strong>{{ item.name }}</strong><p>{{ item.bytes.toLocaleString() }} 字节</p><el-button :disabled="busy" @click="deleteTarget=item;deletePassword='';deleteError='' ">删除此备份</el-button></article><p>清单仅包括当前数据目录中的完整备份；外部复制、下载文件和系统快照需分别管理。</p><details><summary>如何恢复</summary><ol><li>妥善保存备份目录中的 manifest.json 与 owner.sqlite3，两者必须来自同一次备份。</li><li>停止使用待恢复的服务，保留原数据目录，不覆盖。</li><li>使用安装包的恢复启动参数，将备份恢复到一个尚不存在的新目录；完成校验后启动恢复实例。</li><li>用备份时的账号和口令登录，核对账户、交易和历史，再决定是否切换使用。</li></ol><p>当前网页提供备份创建与管理。恢复须通过本机启动工具完成，不能将业务 JSON 导出当作完整备份。</p></details></section>
<section class="settings-panel"><div class="panel-title">清空当前业务数据</div><p>清空账户、交易、资金流水、研究、计划、规则、所有版本历史及审计，保留登录账号。已有备份和下载副本保留，不保证磁盘物理擦除。</p><el-button :disabled="busy" @click="previewReset">预览清空范围</el-button><template v-if="privacy"><dl><template v-for="(count,key) in privacy.counts" :key="key"><dt>{{ tableNames[key]||key }}</dt><dd>{{ count }}</dd></template></dl><el-form label-position="top"><el-form-item label="清空时的当前口令"><el-input v-model="resetPassword" type="password" autocomplete="current-password" :disabled="busy"/></el-form-item><el-form-item label="输入：清空当前业务数据"><el-input v-model="resetConfirmation" :disabled="busy"/></el-form-item></el-form><el-button type="danger" :disabled="busy" @click="reset">确认清空当前业务数据</el-button></template></section></div></div>
<el-dialog :model-value="!!deleteTarget" title="确认删除备份" width="min(600px,calc(100vw - 24px))" :close-on-click-modal="false" :show-close="!busy" :close-on-press-escape="!busy" :before-close="closeDelete"><p>永久删除 {{ deleteTarget?.name }}。当前账本不受影响，外部副本不会被删除。</p><el-form label-position="top"><el-form-item label="删除备份时的当前口令"><el-input v-model="deletePassword" type="password" autocomplete="current-password" :disabled="busy"/></el-form-item></el-form><p v-if="deleteError" role="alert">{{ deleteError }}</p><template #footer><el-button :disabled="busy" @click="closeDelete">取消</el-button><el-button type="danger" :disabled="busy" @click="deleteBackup">永久删除选定备份</el-button></template></el-dialog>
</div></template>
<script setup lang="ts">
import {reactive,ref,computed,onBeforeUnmount} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import AppDataState from '@/components/Global/AppDataState.vue'
import {request} from '@/api/owner'
import {useAuthStore} from '@/stores/auth'
import {useBusinessStore} from '@/stores/business'
type Settings={username:string;data_directory:string;database_file:string;backup_directory:string;schema_version:number}
type Backup={name:string;bytes:number;token:string}
const router=useRouter(),auth=useAuthStore(),business=useBusinessStore(),settings=ref<Settings|null>(null),busy=ref(false),error=ref(''),notice=ref(''),backups=ref<Backup[]|null>(null),deleteTarget=ref<Backup|null>(null),deletePassword=ref(''),deleteError=ref(''),privacy=ref<{counts:Record<string,number>;token:string}|null>(null),resetPassword=ref(''),resetConfirmation=ref(''),password=reactive({current:'',next:'',repeat:''});let exiting=false
const locations=[{key:'data_directory',label:'数据目录'},{key:'database_file',label:'账本文件'},{key:'backup_directory',label:'备份目录'},{key:'schema_version',label:'数据版本'}] as const,tableNames:Record<string,string>={trade_links:'成交关联',cash_flows:'资金流水',cash_flow_versions:'资金历史',ledger_events:'账本事件',trades:'成交',accounts:'资金账户',documents:'业务记录',document_versions:'业务历史',operations:'操作回执',audit:'审计记录'}
const dirty=computed(()=>!!password.current||!!password.next||!!password.repeat||!!deletePassword.value||!!resetPassword.value||!!resetConfirmation.value)
async function run(fn:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';notice.value='';try{await fn()}catch(e){error.value=e instanceof Error?e.message:'操作失败'}finally{busy.value=false}}
async function load(){await run(async()=>{settings.value=await request('/api/v1/owner/settings')})}
async function listBackups(){await run(async()=>{backups.value=(await request<{backups:Backup[]}>('/api/v1/owner/backup-list')).backups})}
async function reauthenticate(){exiting=true;clearPasswords();auth.authenticated=false;auth.user=null;business.reset();await router.replace('/login')}
function clearPasswords(){Object.assign(password,{current:'',next:'',repeat:''});deletePassword.value='';resetPassword.value=''}
async function changePassword(){await run(async()=>{if(password.next!==password.repeat)throw Error('两次新口令不一致。');if(password.next.length<12||password.next.length>128)throw Error('新口令需12–128字符。');try{await request('/api/v1/owner/password','POST',{current_password:password.current,new_password:password.next},false);await reauthenticate()}finally{Object.assign(password,{current:'',next:'',repeat:''})}})}
async function backup(){await run(async()=>{const receipt=await request<{name:string}>('/api/v1/owner/backup','POST',{},false);notice.value='已创建完整备份：'+receipt.name;backups.value=(await request<{backups:Backup[]}>('/api/v1/owner/backup-list')).backups})}
function closeDelete(){if(!busy.value){deleteTarget.value=null;deletePassword.value='';deleteError.value=''}}
async function deleteBackup(){if(busy.value||!deleteTarget.value)return;busy.value=true;deleteError.value='';try{await request('/api/v1/owner/delete-backup','POST',{name:deleteTarget.value.name,token:deleteTarget.value.token,confirmation:'删除此备份',current_password:deletePassword.value},false);deleteTarget.value=null;backups.value=(await request<{backups:Backup[]}>('/api/v1/owner/backup-list')).backups;notice.value='选定备份已删除，当前账本与外部副本未改变。'}catch(e){deleteError.value=e instanceof Error?e.message:'删除失败'}finally{deletePassword.value='';busy.value=false}}
async function previewReset(){await run(async()=>{privacy.value=null;resetConfirmation.value='';privacy.value=await request('/api/v1/owner/privacy')})}
async function reset(){await run(async()=>{if(!privacy.value)throw Error('请先预览清空范围。');if(resetConfirmation.value!=='清空当前业务数据')throw Error('请准确填写确认文字。');try{await request('/api/v1/owner/reset','POST',{token:privacy.value.token,confirmation:resetConfirmation.value,current_password:resetPassword.value},false);privacy.value=null;resetConfirmation.value='';await reauthenticate()}finally{resetPassword.value=''}})}
onBeforeRouteLeave(async()=>{if(exiting)return true;if(busy.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('离开将清除尚未提交的口令和确认内容。','离开数据管理',{confirmButtonText:'离开',cancelButtonText:'继续编辑'});return true}catch{return false}})
const beforeUnload=(e:BeforeUnloadEvent)=>{if(!exiting&&(dirty.value||busy.value)){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>{clearPasswords();window.removeEventListener('beforeunload',beforeUnload)});load()
</script>
<style scoped>
.settings-page {
  padding: 28px 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.settings-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 16px;
  padding: 24px 26px;
  border-radius: 24px;
  border: 1px solid rgba(91, 153, 255, 0.14);
  background:
    radial-gradient(circle at top right, rgba(72, 196, 255, 0.16), transparent 32%),
    linear-gradient(135deg, rgba(10, 27, 54, 0.96), rgba(14, 44, 86, 0.92));
  box-shadow: 0 20px 54px rgba(5, 18, 43, 0.24);
}

.settings-kicker {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #8fd3ff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.settings-title {
  margin: 16px 0 10px;
  font-size: 34px;
  line-height: 1.08;
  color: #f3fbff;
}

.settings-subtitle {
  margin: 0;
  max-width: 720px;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(216, 232, 255, 0.84);
}

.settings-hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.hero-stat {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(7, 20, 42, 0.42);
  border: 1px solid rgba(109, 178, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-stat-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(151, 197, 240, 0.75);
}

.hero-stat b {
  font-size: 20px;
  color: #f5fbff;
}

.hero-stat small {
  color: rgba(185, 211, 242, 0.72);
  font-size: 12px;
}

.settings-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
}

.settings-sidebar,
.settings-panel {
  border-radius: 22px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color-overlay);
  box-shadow: 0 16px 44px rgba(17, 32, 62, 0.08);
}

.settings-sidebar {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-self: start;
  position: sticky;
  top: 28px;
}

.settings-nav-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 16px;
  background: rgba(14, 26, 46, 0.03);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-nav-item:hover {
  border-color: rgba(84, 167, 255, 0.16);
  background: rgba(84, 167, 255, 0.06);
}

.settings-nav-item.is-active {
  border-color: rgba(84, 167, 255, 0.22);
  background: linear-gradient(135deg, rgba(84, 167, 255, 0.12), rgba(33, 108, 231, 0.08));
  color: #0f56cf;
}

.settings-side-note {
  margin-top: 8px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(84, 167, 255, 0.05);
  color: var(--el-text-color-regular);
}

.settings-side-note-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.settings-side-note p {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
}

.settings-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-panel {
  padding: 22px 24px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.panel-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.beta-panel-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-grid {
  display: grid;
  gap: 16px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.surface-card,
.toggle-card,
.security-box,
.data-ownership-box {
  border-radius: 18px;
  border: 1px solid var(--el-border-color-lighter);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.04), rgba(84, 167, 255, 0.01));
}

.surface-card {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}

.surface-card-title,
.toggle-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.surface-card-copy,
.toggle-copy {
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.data-ownership-box {
  margin-top: 14px;
  padding: 18px;
}

.data-ownership-head,
.data-ownership-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.data-ownership-scope {
  flex: 0 0 auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.data-ownership-actions {
  justify-content: flex-end;
  margin-top: 16px;
}

.delete-confirmation {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.delete-confirmation label {
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.delete-confirmation code {
  display: block;
  overflow-wrap: anywhere;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
  color: var(--el-color-danger);
  font-variant-numeric: tabular-nums;
}

.radio-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.toggle-list {
  display: grid;
  gap: 14px;
}

.beta-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.beta-summary-card {
  position: relative;
  overflow: hidden;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(84, 167, 255, 0.14);
  background:
    radial-gradient(circle at top right, rgba(72, 196, 255, 0.14), transparent 36%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.08), rgba(84, 167, 255, 0.018));
}

.beta-summary-card span {
  display: block;
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
}

.beta-summary-card b {
  color: var(--el-text-color-primary);
  font-size: 28px;
  line-height: 1;
}

.beta-section-block {
  margin-top: 16px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid var(--el-border-color-lighter);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(248, 251, 255, 0.92)),
    radial-gradient(circle at top right, rgba(84, 167, 255, 0.08), transparent 42%);
}

.beta-section-title {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 800;
}

.beta-table {
  --el-table-header-bg-color: rgba(84, 167, 255, 0.055);
  --el-table-row-hover-bg-color: rgba(84, 167, 255, 0.055);
}

.beta-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.invite-code-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.toggle-card,
.security-box {
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.data-health {
  margin-bottom: 18px;
  padding: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, rgba(49, 207, 220, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.07), rgba(84, 167, 255, 0.012));
}

.data-health-head,
.data-source-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.data-health-title {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 800;
}

.data-health-copy {
  margin-top: 5px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.data-health-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.data-health-metric {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: var(--el-fill-color-blank);
}

.data-health-metric span,
.data-source-row span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.data-health-metric b {
  display: block;
  margin: 5px 0 8px;
  color: var(--el-text-color-primary);
  font-size: 22px;
}

.data-source-list,
.data-health-anomalies {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.data-source-row {
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.data-source-row strong {
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.data-source-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.data-health-anomaly {
  padding: 9px 12px;
  border-radius: 10px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  background: rgba(230, 162, 60, 0.09);
}

.data-health-anomaly.is-critical {
  color: var(--el-color-danger);
  background: rgba(245, 108, 108, 0.09);
}

.ai-settings {
  display: grid;
  gap: 18px;
}

.ai-fallback-alert {
  border-radius: 14px;
  border-color: rgba(84, 167, 255, 0.18);
  background:
    radial-gradient(circle at top left, rgba(80, 211, 255, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.075), rgba(84, 167, 255, 0.022));
}

.ai-fallback-alert :deep(.el-alert__title) {
  color: var(--el-text-color-primary);
}

.ai-fallback-alert :deep(.el-alert__description) {
  color: var(--el-text-color-secondary);
}

.ai-fallback-alert :deep(.el-alert__icon) {
  color: #61d7ff;
}

.ai-mode-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.ai-mode-grid :deep(.el-radio) {
  width: 100%;
  height: auto;
  min-height: 84px;
  margin: 0;
  padding: 15px 16px;
  align-items: flex-start;
  border-radius: 16px;
}

.ai-mode-grid :deep(.el-radio__input) {
  margin-top: 3px;
}

.ai-mode-grid :deep(.el-radio__label) {
  min-width: 0;
  padding-left: 10px;
  white-space: normal;
}

.ai-mode-copy {
  display: grid;
  gap: 5px;
}

.ai-mode-copy b {
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.ai-mode-copy small,
.ai-mode-panel small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.ai-mode-panel {
  padding: 16px 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 16px;
  background:
    radial-gradient(circle at top right, rgba(49, 207, 220, 0.1), transparent 36%),
    linear-gradient(135deg, rgba(84, 167, 255, 0.07), rgba(84, 167, 255, 0.015));
}

.ai-mode-panel > div {
  display: grid;
  gap: 5px;
}

.ai-mode-panel b {
  color: var(--el-text-color-primary);
  font-size: 17px;
}

.ai-optional-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 14px;
}

.ai-optional-grid.is-guardrail-only {
  grid-template-columns: 1fr;
}

.ai-local-card,
.ai-guardrail-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.055), rgba(84, 167, 255, 0.012));
}

.ai-local-card {
  display: grid;
  gap: 9px;
}

.ai-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ai-local-card b {
  color: var(--el-text-color-primary);
  font-size: 17px;
}

.ai-local-card small,
.ai-guardrail-card li {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.ai-local-meta {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px 10px;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  align-items: center;
}

.ai-local-meta span {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 700;
}

.ai-local-meta code {
  min-width: 0;
  overflow-wrap: anywhere;
  padding: 5px 8px;
  border-radius: 9px;
  color: var(--el-color-primary);
  background: rgba(84, 167, 255, 0.08);
  font-size: 12px;
}

.ai-guardrail-card ul {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
  padding-left: 18px;
}

.ai-detail-label {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ai-provider-form {
  padding: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at top right, rgba(80, 211, 255, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.055), rgba(84, 167, 255, 0.012));
}

.ai-credential-note,
.ai-saved-row,
.ai-last-test {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.ai-credential-note {
  margin-top: -2px;
  line-height: 1.6;
}

.ai-saved-row {
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.ai-last-test {
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(84, 167, 255, 0.05);
}

.ai-last-test b.is-success {
  color: var(--el-color-success);
}

.ai-last-test b.is-failed {
  color: var(--el-color-danger);
}

.ai-actions {
  gap: 10px;
}

.ops-card {
  text-align: left;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--el-border-color-lighter);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.045), rgba(84, 167, 255, 0.008));
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.ops-card:hover {
  transform: translateY(-2px);
  border-color: rgba(84, 167, 255, 0.2);
  box-shadow: 0 14px 34px rgba(31, 73, 151, 0.1);
}

.ops-card-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.ops-card-copy {
  margin-top: 8px;
  min-height: 42px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--el-text-color-secondary);
}

.ops-card-link {
  display: inline-block;
  margin-top: 12px;
  font-size: 13px;
  font-weight: 700;
  color: #2f7dff;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

@media (max-width: 1240px) {
	  .settings-hero,
	  .settings-layout,
	  .two-columns,
	  .ai-mode-grid,
	  .ai-optional-grid,
	  .ops-grid,
	  .data-health-metrics,
	  .beta-summary-grid {
    grid-template-columns: 1fr;
  }

  .settings-sidebar {
    position: static;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 18px 16px 28px;
  }

  .settings-title {
    font-size: 28px;
  }

  .settings-hero-stats {
    grid-template-columns: 1fr;
  }

  .toggle-card,
  .security-box,
  .data-ownership-head,
  .data-ownership-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .data-ownership-actions .el-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>

<style scoped>.settings-panel p,.settings-panel li{line-height:1.7;overflow-wrap:anywhere}dd{margin:6px 0 16px;overflow-wrap:anywhere}.surface-card{margin-top:16px}.surface-card strong{overflow-wrap:anywhere}.panel-actions{flex-wrap:wrap}.notice{padding:16px;border:1px solid #24405f;border-radius:12px;overflow-wrap:anywhere}.settings-nav-item{width:100%}</style>
