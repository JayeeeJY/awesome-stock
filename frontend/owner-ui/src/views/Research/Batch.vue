<template>
 <section class="batch-page">
  <section class="batch-hero"><div><span>AWESOME RESEARCH / BATCH PROTOCOL</span><h1>批量研究</h1><p>逐标的核对发送材料，独立保留生成结果与失败状态。</p></div><div class="protocol-note"><strong>最多 10 个标的</strong><span>每个标的一次模型请求，费用由你配置的服务计收</span></div></section>
  <section class="batch-console"><div class="input-panel"><header><span>01 / 研究范围</span><strong>{{ symbols.length }}/10</strong></header><el-input v-model="input" aria-label="批量研究标的" type="textarea" :rows="5" placeholder="用空格或逗号分隔标的代码" :disabled="working"/><div class="symbol-list"><span v-for="symbol in symbols" :key="symbol">{{ symbol }}</span></div></div><div class="config-panel"><header><span>02 / 研究问题</span></header><el-input v-model="question" type="textarea" :rows="5" aria-label="批量研究问题" :disabled="working"/><el-button class="batch-run" type="primary" :loading="loading" :disabled="working" @click="load">准备逐标的材料</el-button></div></section>
  <el-alert v-if="error" :title="error" type="error" :closable="false"/>
  <el-alert v-if="items.length&&!batchCurrent" title="标的或研究问题已改变，请重新准备材料后再预览或发送。原批次草稿仍保留。" type="warning" :closable="false"/>
  <section v-if="items.length" class="batch-summary"><div><span>RESEARCH MATRIX</span><h2>当前批次 · {{ items.length }} 个标的</h2></div><div><strong>{{ completed }}</strong><span>已有草稿</span></div><div><strong>{{ failed }}</strong><span>需要处理</span></div></section>
  <section v-if="items.length" class="batch-controls"><el-button :disabled="working||!batchCurrent" @click="prepareAll">预览整批发送内容</el-button><el-button type="primary" :disabled="working||!batchCurrent||!previewCount" @click="generateAll">确认发送已预览项（{{ previewCount }} 次请求）</el-button><el-button v-if="working" :disabled="stopping" @click="stopping=true">{{ stopping?'将在当前步骤后暂停':'暂停后续请求' }}</el-button><p>可先逐项展开核对；改动某项会使该项预览失效。失败不自动重试，成功结果保留。</p></section>
  <section v-if="items.length" class="result-table"><article v-for="item in items" :key="item.symbol" class="result-row" :class="{failed:states[item.symbol]?.failed}"><div class="stock-cell"><strong>{{ item.symbol }}</strong><small>{{ item.count }} 条本地材料</small></div><span>{{ states[item.symbol]?.busy?'正在处理':states[item.symbol]?.failed?'需处理':states[item.symbol]?.result?'已有未核验草稿':states[item.symbol]?.preview?'待确认发送':'待预览' }}</span><el-button @click="active=item.symbol">{{ active===item.symbol?'正在查看':'查看材料与结果' }}</el-button></article></section>
  <section v-for="item in items" v-show="active===item.symbol" :key="batchVersion+item.symbol" class="batch-detail"><h2>{{ item.symbol }} · 独立研究</h2><Assistant :ref="el=>register(item.symbol,el)" :source-context="item.context" :symbol="item.symbol" :initial-question="item.question" managed-navigation :external-busy="running||!batchCurrent" @state="states[item.symbol]=$event" /></section>
  <section v-if="!items.length" class="batch-empty"><div class="matrix-mark"><span v-for="n in 9" :key="n"/></div><h2>先准备材料，再确认发送</h2><p>准备材料不会请求模型，也不会自动导入真实行情。</p></section>
 </section>
</template>
<script setup lang="ts">
import {ref,computed,reactive,onBeforeUnmount} from 'vue'
import {onBeforeRouteLeave} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import {registerPageMaterial} from '@/api/pageMaterial'
import Assistant from '@/components/Research/Assistant.vue'
import {request} from '@/api/owner'
import {getWorkspace,type BusinessRecord} from '@/api/business'
type Item={symbol:string;context:string;question:string;count:number}
type State={busy:boolean;preview:boolean;result:boolean;failed:boolean;dirty:boolean}
type Controller={prepare:()=>Promise<void>;generate:()=>Promise<void>}
const batchVersion=ref(0),input=ref(''),question=ref('请分别列出有来源的事实、推断、反方证据与缺口，不把缺失数据当作已知事实。'),loading=ref(false),running=ref(false),stopping=ref(false),error=ref(''),items=ref<Item[]>([]),active=ref(''),states=reactive<Record<string,State>>({}),controllers=new Map<string,Controller>()
const symbols=computed(()=>[...new Set(input.value.toUpperCase().split(/[\s,，]+/).filter(Boolean))]),working=computed(()=>loading.value||running.value||Object.values(states).some(s=>s.busy)),completed=computed(()=>Object.values(states).filter(s=>s.result).length),failed=computed(()=>Object.values(states).filter(s=>s.failed).length),previewCount=computed(()=>items.value.filter(i=>states[i.symbol]?.preview).length)
const batchCurrent=computed(()=>items.value.length>0&&JSON.stringify(symbols.value)===JSON.stringify(items.value.map(i=>i.symbol))&&items.value.every(i=>i.question===question.value))
function register(symbol:string,el:unknown){if(el)controllers.set(symbol,el as Controller);else controllers.delete(symbol)}
const unregisterMaterial=registerPageMaterial('/research/batch',()=>{
  if(working.value||error.value||!batchCurrent.value)throw Error('请先按当前标的和问题准备批次材料，并等待批次操作完成。')
  return {scope:'prepared_batch_sources',batch_version:batchVersion.value,active_symbol:active.value,
    items:items.value.map(i=>({symbol:i.symbol,question:i.question,source:JSON.parse(i.context),status:states[i.symbol]||null})),
    notice:'当前已准备批次的原始来源和处理状态；不包含逐项编辑后的待发送文本或AI生成草稿，不把已有草稿状态当成已核验证据。未准备的新输入不计入本材料。'}
})
onBeforeUnmount(unregisterMaterial)
async function discard(){if(working.value)return false;if(!items.value.length)return true;try{await ElMessageBox.confirm('当前批次的输入和未保存结果将被清除。','离开当前批次',{confirmButtonText:'继续',cancelButtonText:'保留批次'});return true}catch{return false}}
async function load(){if(working.value)return;if(symbols.value.length<1||symbols.value.length>10||symbols.value.some(s=>!/^([A-Z0-9][A-Z0-9.^_-]{0,23})$/.test(s))||!question.value.trim()||question.value.length>4000){error.value='请填写1–10个有效标的及不超过4000字的研究问题。';return}if(!(await discard()))return;loading.value=true;error.value='';try{const requestedSymbols=[...symbols.value],requestedQuestion=question.value;const [workspace,documents]=await Promise.all([getWorkspace(),request<{documents:BusinessRecord[]}>('/api/v1/owner/documents')]);const records=[...workspace.records.filter(r=>['candidate','evidence'].includes(r.kind)),...documents.documents.filter(d=>d.kind==='note'&&!d.archived)];batchVersion.value++;items.value=[];for(const key of Object.keys(states))delete states[key];controllers.clear();items.value=requestedSymbols.map(symbol=>{const own=records.filter(r=>r.symbol===symbol);return {symbol,count:own.length,question:requestedQuestion,context:JSON.stringify({symbol,records:own,notice:'本标的本地材料快照；证据缺口与未核验状态不能自动补全。'},null,2)}});active.value=items.value[0].symbol}catch(e){error.value=e instanceof Error?e.message:'准备失败'}finally{loading.value=false}}
async function prepareAll(){if(working.value||!batchCurrent.value)return;running.value=true;stopping.value=false;try{for(const item of items.value){if(stopping.value)break;await controllers.get(item.symbol)?.prepare()}}finally{running.value=false}}
async function generateAll(){if(working.value||!batchCurrent.value||!previewCount.value)return;running.value=true;stopping.value=false;try{for(const [index,item] of items.value.filter(i=>states[i.symbol]?.preview).entries()){if(stopping.value)break;if(index)await new Promise(resolve=>setTimeout(resolve,1100));if(stopping.value)break;await controllers.get(item.symbol)?.generate()}}finally{running.value=false}}
onBeforeRouteLeave(discard);const beforeUnload=(e:BeforeUnloadEvent)=>{if(working.value||items.value.length){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>

<style scoped lang="scss">
.batch-page {
  --panel: rgba(9, 26, 47, 0.84);
  --line: rgba(78, 204, 255, 0.17);
  --text: #e9f7ff;
  --muted: #7f9bb4;
  min-height: calc(100vh - 64px);
  padding: 30px;
  color: var(--text);
  background:
    radial-gradient(circle at 80% 0%, rgba(39, 197, 206, 0.13), transparent 28%),
    radial-gradient(circle at 8% 8%, rgba(49, 105, 205, 0.22), transparent 32%),
    #071321;
}
.batch-hero,
.batch-console,
.batch-empty,
.batch-loading,
.batch-summary,
.result-table,
.comparison-notes {
  max-width: 1500px;
  margin-left: auto;
  margin-right: auto;
}
.batch-hero {
  display: flex;
  padding: 4px 2px 24px;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  > div > span { color: #54d9ff; font: 700 11px "SFMono-Regular", Consolas, monospace; letter-spacing: 0.14em; }
  h1 { margin: 9px 0 7px; font-size: clamp(30px, 3vw, 46px); letter-spacing: -0.04em; }
  p { max-width: 780px; margin: 0; color: var(--muted); line-height: 1.7; }
}
.protocol-note {
  padding: 12px 15px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(5, 17, 31, 0.65);
  strong { display: block; margin-bottom: 5px; color: #90edff; font-size: 12px; }
  span { color: var(--muted); font-size: 11px; }
}
.batch-console {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.input-panel,
.config-panel {
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  > header { display: flex; margin: -18px -18px 15px; padding: 13px 18px; justify-content: space-between; border-bottom: 1px solid var(--line); color: #5cdfff; font: 700 10px "SFMono-Regular", Consolas, monospace; letter-spacing: 0.08em; }
  label { display: block; margin: 13px 0 7px; color: var(--muted); font-size: 11px; }
  :deep(.el-textarea__inner), :deep(.el-input__wrapper), :deep(.el-radio-group) {
    color: var(--text);
    border: 1px solid rgba(90, 183, 232, 0.13);
    background: rgba(4, 16, 29, 0.72);
    box-shadow: none;
  }
  :deep(.el-radio-button__inner) { color: #8da9bf; border: 0; background: transparent; box-shadow: none; }
  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) { color: #eaf8ff; background: rgba(52, 134, 207, 0.35); box-shadow: none; }
}
.symbol-list {
  display: flex;
  gap: 7px;
  margin-top: 10px;
  flex-wrap: wrap;
  button { padding: 6px 9px; color: #a9ddf3; border: 1px solid rgba(82, 205, 255, 0.22); border-radius: 6px; background: rgba(39, 122, 167, 0.12); cursor: pointer; }
}
.invalid { color: #ff8b83; font-size: 11px; }
.lens-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; :deep(.el-checkbox) { width: 100%; margin: 0; border-color: rgba(100, 175, 219, 0.17); background: rgba(8, 24, 42, 0.5); } }
.batch-run { width: 100%; height: 44px; margin-top: 18px; border: 0; background: linear-gradient(110deg, #3d72ff, #38cce8); font-weight: 700; }
.batch-empty,
.batch-loading {
  display: grid;
  min-height: 300px;
  margin-top: 14px;
  place-items: center;
  text-align: center;
  border: 1px dashed var(--line);
  border-radius: 16px;
  background: rgba(5, 17, 30, 0.42);
  h2 { margin: 8px 0; font-size: 20px; }
  p { max-width: 700px; color: var(--muted); }
}
.matrix-mark { display: grid; grid-template-columns: repeat(3, 11px); gap: 7px; span { width: 11px; height: 11px; border: 1px solid rgba(82, 213, 255, 0.38); &:nth-child(5) { background: #4cdcff; box-shadow: 0 0 17px #4cdcff; } } }
.progress-rail { width: min(420px, 80%); height: 2px; overflow: hidden; background: rgba(92, 175, 218, 0.16); span { display: block; width: 38%; height: 100%; background: #4ad9ff; box-shadow: 0 0 12px #4ad9ff; animation: move 1.4s ease-in-out infinite; } }
@keyframes move { from { transform: translateX(-100%); } to { transform: translateX(360%); } }
.batch-summary {
  display: grid;
  grid-template-columns: 1fr 150px 150px;
  gap: 10px;
  margin-top: 15px;
  > div { padding: 15px; border: 1px solid var(--line); border-radius: 13px; background: var(--panel); }
  span { display: block; color: var(--muted); font-size: 10px; }
  h2 { margin: 5px 0 0; font-size: 17px; }
  strong { display: block; margin-bottom: 3px; color: #82ecff; font: 800 24px "SFMono-Regular", Consolas, monospace; }
}
.result-table {
  margin-top: 10px;
  border: 1px solid var(--line);
  border-radius: 15px;
  background: var(--panel);
  overflow: hidden;
}
.result-row {
  display: grid;
  min-height: 64px;
  padding: 0 15px;
  grid-template-columns: 1.05fr 0.85fr 0.75fr 0.75fr 2fr 110px;
  gap: 14px;
  align-items: center;
  border-bottom: 1px solid var(--line);
  > span { color: #9db3c5; font-size: 12px; }
  > p { margin: 0; color: #b2c5d3; line-height: 1.45; }
  &.failed { opacity: 0.62; }
}
.result-table > header {
  min-height: 42px;
  color: #6c8ca4;
  font: 700 9px "SFMono-Regular", Consolas, monospace;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgba(23, 57, 87, 0.36);
}
.stock-cell { strong { display: block; color: #e9f7ff; font: 700 13px "SFMono-Regular", Consolas, monospace; } small { display: block; margin-top: 4px; color: #6f8ca3; } }
.posture { color: #ffc475 !important; }
.quality-meter { display: flex; align-items: center; gap: 8px; > span { width: 70px; height: 4px; overflow: hidden; border-radius: 3px; background: rgba(102, 159, 196, 0.13); i { display: block; height: 100%; background: linear-gradient(90deg, #4c7dff, #4bdddc); } } strong { color: #9bdff0; font: 700 11px "SFMono-Regular", Consolas, monospace; } }
.comparison-notes { display: flex; margin-top: 12px; padding: 18px; align-items: center; justify-content: space-between; gap: 20px; border: 1px solid var(--line); border-radius: 14px; background: rgba(7, 22, 39, 0.7); > div > span { color: #55dafe; font: 700 10px "SFMono-Regular", Consolas, monospace; } h3 { margin: 7px 0; font-size: 15px; } p { margin: 0; color: var(--muted); line-height: 1.6; } }
.comparison-tags { display: flex; gap: 7px; flex-wrap: wrap; span { padding: 7px 9px; border: 1px solid var(--line); border-radius: 999px; color: #87a6bc !important; white-space: nowrap; } }
@media (max-width: 1000px) {
  .batch-console { grid-template-columns: 1fr; }
  .result-row { grid-template-columns: 1fr 1fr 1fr; padding: 13px; > p { grid-column: 1 / 3; } }
  .result-table > header { display: none; }
}
@media (max-width: 720px) {
  .batch-page { padding: 16px; }
  .batch-hero, .comparison-notes { align-items: flex-start; flex-direction: column; }
  .protocol-note { width: 100%; box-sizing: border-box; }
  .lens-options { grid-template-columns: repeat(2, 1fr); }
  .batch-summary { grid-template-columns: 1fr 1fr; > div:first-child { grid-column: 1 / -1; } }
  .result-row { grid-template-columns: 1fr 1fr; > p { grid-column: 1 / -1; } }
}
</style>

<style scoped>
.batch-page{min-width:0}
.batch-controls,.batch-detail{margin-top:20px;padding:18px;border:1px solid rgba(112,202,255,.18);border-radius:16px}
.batch-controls{display:flex;gap:10px;flex-wrap:wrap}
.batch-controls p{width:100%;line-height:1.6;color:#a5bad3}
.result-row{grid-template-columns:minmax(0,1fr) minmax(140px,1fr) 220px}
.result-row > .el-button{width:220px;justify-self:end}
.symbol-list{gap:8px;flex-wrap:wrap}
.symbol-list span{padding:5px 10px;border:1px solid rgba(112,202,255,.2);border-radius:8px}
@media(max-width:720px){
  .result-row{grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;padding:14px}
  .result-row > span{grid-column:1;grid-row:2}
  .result-row > .el-button{grid-column:2;grid-row:1 / 3;width:130px;max-width:100%;margin:0}
}
@media(max-width:600px){.batch-page{padding:12px 0}.batch-detail{padding:12px}}
</style>
