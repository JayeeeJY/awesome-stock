<template><div class="settings-page"><section class="settings-hero"><div class="settings-hero-copy"><div class="settings-kicker">Awesome Stock Control Center</div><h1 class="settings-title">导入与导出</h1><p class="settings-subtitle">预览成交与账目影响，确认后整批写入。</p></div></section><div class="settings-layout"><aside class="settings-sidebar"><button class="settings-nav-item" @click="router.push('/settings/account')">账户与数据</button><button class="settings-nav-item" @click="router.push('/settings/appearance')">外观</button><button class="settings-nav-item" @click="router.push('/settings/connections')">数据与 AI 连接</button><button class="settings-nav-item is-active">导入与导出</button></aside><div class="settings-main"><AppDataState v-if="error" tone="error" title="传输未完成" :description="error"/><p v-if="notice" role="status" class="notice">{{ notice }}</p><section class="settings-panel"><div class="panel-title">CSV 成交导入</div><p>选择不超过32KiB、最多200条成交的UTF-8文件。数量、价格和费用使用普通小数；成交时间须包含时区。先下载固定七列表头模板。</p><el-button :disabled="busy" @click="templateDownload">下载 CSV 模板</el-button><el-form label-position="top"><el-form-item label="导入账户"><el-select v-model="accountId" :disabled="busy" aria-label="导入账户"><el-option v-for="account in accounts" :key="account.id" :label="account.name+' · '+account.currency" :value="account.id"/></el-select></el-form-item><el-form-item label="CSV 文件"><input ref="fileInput" aria-label="CSV 文件" type="file" accept=".csv,text/csv" :disabled="busy" @change="chooseFile"/></el-form-item></el-form><p v-if="!accounts.length">请先创建资金账户。</p><el-button type="primary" :disabled="busy||!accountId||!file" @click="previewImport">预览导入</el-button>
<div v-if="preview" class="import-preview"><h3>新增 {{ preview.new_count }} 笔 · 重复跳过 {{ preview.duplicate_count }} 笔 · {{ preview.currency }}</h3><p v-if="preview.rows.some(r=>r.possible_duplicate)" role="alert">存在编号不同但成交事实相同的记录，请核对是否重复。</p><p v-for="message in preview.errors" :key="message" role="alert">{{ message }}</p><el-table :data="preview.rows" style="width:100%"><el-table-column prop="row" label="数据行" width="80"/><el-table-column prop="record_id" label="成交编号" min-width="150"/><el-table-column label="结果" width="90"><template #default="{row}">{{ statuses[row.status] }}</template></el-table-column><el-table-column label="标的 / 方向" min-width="130"><template #default="{row}">{{ row.trade?row.trade.symbol+' / '+(row.trade.side==='buy'?'买入':'卖出'):'—' }}</template></el-table-column><el-table-column label="数量 / 价格 / 费用" min-width="180"><template #default="{row}">{{ row.trade?row.trade.quantity+' / '+row.trade.price+' / '+row.trade.fee:'—' }}</template></el-table-column><el-table-column label="成交时间 UTC" min-width="210"><template #default="{row}">{{ row.trade?.executed_at||'—' }}</template></el-table-column><el-table-column prop="message" label="说明" min-width="240"/></el-table><template v-if="preview.after"><p>{{ preview.before.name }} · {{ preview.currency }}；现金 {{ preview.before.cash }} → {{ preview.after.cash }}</p><el-table :data="comparisons" style="width:100%"><el-table-column prop="symbol" label="标的" min-width="100"/><el-table-column prop="quantity" label="数量：前 → 后" min-width="170"/><el-table-column prop="cost" label="剩余成本：前 → 后" min-width="190"/><el-table-column prop="pnl" label="已实现损益：前 → 后" min-width="210"/></el-table></template><p>{{ preview.can_import?(preview.new_count?'请核对明细、币种及前后账目，再确认导入。':'没有新增成交，无需导入。'):'存在错误或冲突，整批不会写入。' }}</p><el-button v-if="preview.can_import&&preview.new_count" type="primary" :disabled="busy" @click="confirmImport">确认导入成交</el-button></div></section>
<section class="settings-panel"><div class="panel-title">业务 JSON 导出</div><p>导出业务数据供查阅和迁移，不包含登录凭据或连接密钥。文件仍含个人业务信息，请妥善保管。</p><p>业务导出不是完整备份，不能用它代替完整恢复文件。完整备份在账户与数据页管理。</p><el-button :disabled="busy" @click="exportBusiness">下载业务 JSON</el-button></section></div></div></div></template>
<script setup lang="ts">
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import {request,type Account,type Trade,type Ledger} from '@/api/owner'
import {useBusinessStore} from '@/stores/business'
import AppDataState from '@/components/Global/AppDataState.vue'
type Preview={rows:Array<{row:number;record_id?:string;status:string;message:string;possible_duplicate?:boolean;trade?:Trade}>;errors:string[];before:Account;after:Account|null;can_import:boolean;new_count:number;duplicate_count:number;currency:string;preview_token:string}
const router=useRouter(),business=useBusinessStore(),accounts=ref<Account[]>([]),accountId=ref(''),file=ref<File|null>(null),fileInput=ref<HTMLInputElement|null>(null),busy=ref(false),error=ref(''),notice=ref(''),preview=ref<Preview|null>(null),statuses:Record<string,string>={new:'新增',duplicate:'跳过',conflict:'冲突',invalid:'无效'};let input:{account_id:string;csv:string}|null=null,operation='',generation=0
const comparisons=computed(()=>{const p=preview.value;if(!p?.after)return [];return [...new Set([...p.before.holdings,...p.after.holdings].map(h=>h.symbol))].map(symbol=>{const a=p.before.holdings.find(h=>h.symbol===symbol),b=p.after!.holdings.find(h=>h.symbol===symbol);return {symbol,quantity:`${a?.quantity||'0'} → ${b?.quantity||'0'}`,cost:`${a?.open_cost||'0'} → ${b?.open_cost||'0'}`,pnl:`${a?.realized_pnl||'0'} → ${b?.realized_pnl||'0'}`}})})
function invalidate(){generation++;preview.value=null;input=null;operation='';error.value='';notice.value=''}watch(accountId,invalidate)
function chooseFile(event:Event){invalidate();file.value=(event.target as HTMLInputElement).files?.[0]||null}
async function load(){try{accounts.value=(await request<Ledger>('/api/v1/owner/ledger')).accounts;if(!accounts.value.some(a=>a.id===accountId.value))accountId.value=accounts.value[0]?.id||''}catch(e){error.value=e instanceof Error?e.message:'读取账户失败'}}
async function previewImport(){if(busy.value)return;invalidate();busy.value=true;const epoch=generation;try{if(!file.value||file.value.size>32768)throw Error('请选择不超过32KiB的UTF-8 CSV文件。');let csv:string;try{csv=new TextDecoder('utf-8',{fatal:true}).decode(await file.value.arrayBuffer())}catch{throw Error('文件不是有效UTF-8，请转换编码后重试。')}const payload={account_id:accountId.value,csv};const result=await request<Preview>('/api/v1/owner/import-preview','POST',payload);if(epoch!==generation)return;input=payload;preview.value=result;operation=crypto.randomUUID();notice.value='预览完成，尚未写入成交。'}catch(e){error.value=e instanceof Error?e.message:'预览失败'}finally{busy.value=false}}
async function confirmImport(){if(busy.value||!input||!preview.value?.can_import||!preview.value.new_count)return;busy.value=true;error.value='';try{const receipt=await request<{imported:number;skipped:number}>('/api/v1/owner/import-confirm','POST',{...input,preview_token:preview.value.preview_token,operation_id:operation});invalidate();file.value=null;if(fileInput.value)fileInput.value.value='';await load();business.reset();await business.load();notice.value=`已导入 ${receipt.imported} 笔，跳过 ${receipt.skipped} 笔重复记录。`}catch(e){error.value=e instanceof Error?e.message:'导入失败，请核对后重新预览'}finally{busy.value=false}}
function download(name:string,content:string,type:string){const url=URL.createObjectURL(new Blob([content],{type}));const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),10000)}
function templateDownload(){download('awesome-stock-trades-template.csv','record_id,symbol,side,quantity,price,fee,executed_at\n','text/csv;charset=utf-8')}
async function exportBusiness(){if(busy.value)return;busy.value=true;error.value='';try{const data=await request<{exported_at:string}>('/api/v1/owner/export');download('awesome-stock-business-'+data.exported_at.slice(0,10)+'.json',JSON.stringify(data,null,2)+'\n','application/json');notice.value='业务 JSON 已生成并发起下载，请在浏览器下载列表确认文件。'}catch(e){error.value=e instanceof Error?e.message:'导出失败'}finally{busy.value=false}}
onBeforeRouteLeave(async()=>{if(busy.value)return false;if(!file.value&&!preview.value)return true;try{await ElMessageBox.confirm('离开会丢弃当前文件选择与导入预览，尚未导入的成交不会写入。','离开导入导出',{confirmButtonText:'离开',cancelButtonText:'继续核对'});return true}catch{return false}});const beforeUnload=(e:BeforeUnloadEvent)=>{if(busy.value||file.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>{generation++;input=null;file.value=null;window.removeEventListener('beforeunload',beforeUnload)});load()
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

<style scoped>.settings-panel p{line-height:1.7;overflow-wrap:anywhere}.settings-panel .el-select{width:100%}.settings-nav-item{width:100%}.notice{padding:16px;border:1px solid #24405f;border-radius:12px;overflow-wrap:anywhere}.import-preview{margin-top:20px;min-width:0}input[type=file]{max-width:100%;color:#c6dcf5}.settings-form,.el-form{margin-top:18px}</style>
<style scoped>.settings-layout,.settings-main,.settings-sidebar,.settings-panel{min-width:0}.settings-panel input[type=file]{width:100%;min-width:0}.settings-panel :deep(.el-form-item__content){min-width:0}.settings-panel .el-button{max-width:100%;white-space:normal;height:auto;min-height:32px}</style>
