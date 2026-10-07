<template>
 <div :class="allocation?'allocation-page':'what-if-page'">
  <div class="page-header"><div class="header-copy header-info"><div class="header-kicker">{{ allocation?'ASSET ALLOCATION':'PLAN SIMULATION' }}</div><h1 class="header-title title">{{ title }}</h1><p class="header-subtitle subtitle">{{ allocation?'分层管理持仓，跟踪目标 vs 实际配置':'按单一账户及其币种试算，保存快照不创建交易或订单。' }}</p></div><div class="header-actions"><template v-if="allocation"><el-button type="primary" :icon="Plus" :disabled="!workspace||!form.account_id||!layersReady||busy" @click="layersPanel?.openCreate()">新建配置层</el-button></template><template v-else><el-button :disabled="busy" @click="refresh">刷新账本</el-button><el-button type="primary" :loading="busy" @click="calculate">计算影响</el-button></template></div></div>
  <AppDataState v-if="error" tone="error" title="试算未完成" :description="error" />
  <section v-if="allocation" class="allocation-overview" aria-label="账户配置概览"><div class="overview-scope"><span>按账户原币展示，不跨币种合计</span><el-select v-if="workspace" v-model="form.account_id" :disabled="busy" aria-label="资金账户"><el-option v-for="item in workspace.accounts" :key="item.id" :value="item.id" :label="item.name+' · '+item.currency"/></el-select><span v-else class="scope-unavailable">{{ error?'账本读取失败，请刷新':'正在读取账本' }}</span></div><div class="allocation-overview-grid"><article v-for="metric in allocationOverview" :key="metric.label" class="summary-card"><span class="summary-label">{{ metric.label }}</span><strong class="summary-value" :class="metric.tone">{{ metric.value }}</strong><small>{{ metric.detail }}</small></article></div></section>
  <AllocationLayers v-if="allocation&&workspace" ref="layersPanel" @changed="refresh" @readiness="layersReady=$event" :account-id="form.account_id" :refresh-key="workspace.token" :show-create-button="false"/>
  <el-card class="input-card" shadow="never"><template #header><div class="card-header"><span>{{ allocation?'配置试算':'试算输入' }}</span><el-button v-if="allocation" :disabled="busy" @click="refresh">刷新账本</el-button><el-button v-if="allocation" type="primary" :loading="busy" :disabled="!workspace||!form.account_id" @click="calculate">计算影响</el-button><el-button @click="router.push('/plan/build-up')">已保存计划</el-button><el-button v-if="!allocation" :disabled="busy" @click="router.push(mode==='build_up'?'/plan/pre-trade':'/plan/budget')">{{ mode==='build_up'?'交易前检查':'分批预算' }}</el-button></div></template><el-form label-position="top" class="simulation-form"><el-form-item v-if="!allocation" label="资金账户"><el-select v-model="form.account_id" :disabled="busy" aria-label="资金账户"><el-option v-for="account in workspace?.accounts" :key="account.id" :value="account.id" :label="account.name+' · '+account.currency"/></el-select></el-form-item><template v-if="!allocation"><el-form-item label="标的代码"><el-input v-model="form.symbol" :disabled="busy" maxlength="24"/></el-form-item><el-form-item v-if="mode==='pre_trade'" label="买卖方向"><el-select v-model="form.side" :disabled="busy"><el-option label="买入" value="buy"/><el-option label="卖出" value="sell"/></el-select></el-form-item><el-form-item label="数量"><el-input v-model="form.quantity" :disabled="busy"/></el-form-item><el-form-item label="假设成交价格"><el-input v-model="form.price" :disabled="busy"/></el-form-item><el-form-item label="单笔 / 每批费用"><el-input v-model="form.fee" :disabled="busy"/></el-form-item><el-form-item label="用户仓位上限 %"><el-input v-model="form.max_percent" :disabled="busy"/></el-form-item><template v-if="mode==='build_up'"><el-form-item label="总预算"><el-input v-model="form.budget" :disabled="busy"/></el-form-item><el-form-item label="批次数（1–12）"><el-input v-model="form.stages" :disabled="busy"/></el-form-item></template></template><el-form-item v-else-if="form.allocation_source==='symbols'" label="目标比例（每行 CODE=百分比，现金用 @CASH）" class="target-input"><el-input v-model="form.targets" type="textarea" :rows="7" :disabled="busy"/><p>须包含账户所有持仓与现金，比例合计 100%。</p></el-form-item></el-form><p v-if="account">现金 {{ money(account.cash) }} {{ account.currency }} · {{ account.valuation_complete?'账户价格快照完整':'缺少有效价格，须补齐后试算' }}</p></el-card>
  <el-card v-if="mode==='pre_trade'" class="input-card" shadow="never"><template #header><div class="card-header"><span>交易序列 · {{ trades.length }} / 20</span><el-button :disabled="busy||trades.length>=20" @click="addTrade">加入当前交易</el-button><el-button :disabled="busy||!trades.length" @click="trades=[]">清空序列</el-button></div></template><p>未添加序列时试算上方单笔输入；添加后仅按下方顺序试算。卖出所得可用于后续买入，遇到阻断即停止。已有持仓按快照估值，新标的全程沿用首笔假设价格。</p><ol><li v-for="(trade,index) in trades" :key="index" class="sequence-row"><span>{{ index+1 }}. {{ trade.symbol }} · {{ trade.side==='buy'?'买入':'卖出' }} {{ trade.quantity }} @ {{ trade.price }} · 费用 {{ trade.fee }} · 上限 {{ trade.max_percent }}%</span><el-button :disabled="busy||index===0" @click="moveTrade(index)">上移</el-button><el-button :disabled="busy" @click="trades.splice(index,1)">移除</el-button></li></ol></el-card>
  <div v-if="allocation" class="input-card"><el-form label-position="top"><el-form-item label="配置试算依据"><el-radio-group v-model="form.allocation_source" :disabled="busy"><el-radio value="symbols">逐标的比例</el-radio><el-radio value="layers">已保存配置层</el-radio></el-radio-group></el-form-item><el-form-item v-if="form.allocation_source==='layers'" label="现金目标占比 %"><el-input v-model="form.cash_percent" :disabled="busy"/><p>配置层目标比例与现金合计须为100%。按比例计算目标金额；层中的选填目标金额仅供参考，不替代比例。偏离仅供核对，不生成交易。</p></el-form-item></el-form></div>
  <el-alert v-if="historicalMaterial" title="助手材料已选为历史快照；请在助手中主动载入并核对。" type="info" :closable="false"><el-button @click="historicalMaterial=null">改用当前页面材料</el-button></el-alert>
  <section v-if="preview" class="results-section"><h2 class="section-title">试算结果 · {{ preview.result.currency }}</h2><el-alert :title="preview.result.status==='blocked'?'存在阻断项，请调整假设':'已完成试算，请人工复核'" :type="preview.result.status==='blocked'?'warning':'info'" :closable="false"/><p v-if="preview.result.type==='pre_trade_batch'&&preview.result.status==='blocked'">汇总停留在阻断前最后一笔有效交易；下表包含失败假设，后续交易未计算。</p><ul v-if="preview.result.issues?.length"><li v-for="issue in preview.result.issues" :key="issue">{{ issue }}</li></ul><div class="summary-row"><article v-for="metric in summary(preview.result)" :key="metric.label" class="summary-card"><div class="summary-label">{{ metric.label }}</div><div class="summary-value">{{ metric.value }}</div></article></div><el-table v-if="preview.result.rows" :data="preview.result.rows"><el-table-column v-for="column in columns" :key="column.key" :label="column.label" min-width="150"><template #default="{row}">{{ ['symbol','stage','side','status'].includes(column.key)?cellLabel(row[column.key]):money(row[column.key],column.key.includes('percent')?4:2) }}</template></el-table-column></el-table><div class="snapshot-save"><el-input v-model="snapshotTitle" aria-label="快照名称" placeholder="试算快照名称" maxlength="120" :disabled="busy||saved"/><el-button type="primary" :disabled="!snapshotTitle.trim()||saved" :loading="busy" @click="save">{{ saved?'快照已保存':'保存固定试算快照' }}</el-button></div><p>输入变更会清除当前结果；保存时重新核对账本与价格版本。</p></section>
  <section class="scenario-list"><h2>已保存试算</h2><p v-if="!scenarios.length">尚无试算快照。</p><article v-for="record in scenarios" :key="record.id" class="chart-card"><h3>{{ record.title }}</h3><p>{{ record.updated_at }} · {{ record.ledger_fingerprint===workspace?.ledger_fingerprint&&record.price_fingerprint===workspace?.price_fingerprint?'账本及价格依据未改变':'账本或价格已变化，请重新计算' }}</p><el-button @click="history=record">查看固定快照</el-button><el-popconfirm title="归档快照并保留历史？" confirm-button-text="归档" cancel-button-text="取消" @confirm="archive(record)"><template #reference><el-button :disabled="busy">归档快照</el-button></template></el-popconfirm></article><el-button @click="archiveOpen=true">归档快照历史</el-button></section>
  <el-drawer v-model="archiveOpen" title="归档快照" size="min(680px,96vw)"><article v-for="record in workspace?.versions.filter(r=>r.kind==='scenario'&&r.archived)" :key="record.id"><h3>{{ record.title }}</h3><el-button @click="archiveOpen=false;history=record">查看快照</el-button></article></el-drawer>
  <el-drawer :model-value="!!history" title="固定试算依据" size="min(760px,96vw)" @close="history=null"><template v-if="history"><h2>{{ history.title }}</h2><el-button @click="selectHistoricalMaterial">在助手中核对这份历史快照</el-button><p>{{ history.updated_at }}</p><p>以下是当时保存的输入、结果和价格来源，不代表当前账本。</p><details open><summary>试算输入</summary><dl><template v-for="(value,key) in history.input as Record<string,unknown>" :key="key"><dt>{{ inputLabels[key]||key }}</dt><dd>{{ typeof value==='object'?JSON.stringify(value,null,2):value }}</dd></template></dl></details><h3>保存结果 · {{ (history.result as Result).currency }}</h3><dl><template v-for="metric in summary(history.result as Result)" :key="metric.label"><dt>{{ metric.label }}</dt><dd>{{ metric.value }}</dd></template></dl><p v-for="issue in (history.result as Result).issues" :key="issue">{{ issue }}</p><el-table v-if="(history.result as Result).rows" :data="(history.result as Result).rows"><el-table-column v-for="column in columnSet((history.result as Result).type)" :key="column.key" :label="column.label" min-width="140"><template #default="{row}">{{ ['symbol','stage','side','status'].includes(column.key)?cellLabel(row[column.key]):money(row[column.key],column.key.includes('percent')?4:2) }}</template></el-table-column></el-table><template v-if="(history.result as Result).layer_evidence"><h3>固定配置层依据</h3><p v-for="layer in (history.result as Result).layer_evidence as BusinessRecord[]" :key="layer.id">{{ layer.title }} · v{{ layer.revision }} · 目标 {{ layer.target_percent }}% · 归属 {{ (layer.symbols as string[]).join('、') }}</p></template><h3>固定价格来源</h3><article v-for="quote in history.price_evidence as BusinessRecord[]" :key="quote.id"><p>{{ quote.symbol }} · {{ quote.currency }} {{ quote.price }} · {{ quote.as_of }}</p><p>{{ quote.source }} · v{{ quote.revision }}</p></article></template></el-drawer>
 </div>
</template>
<script setup lang="ts">
import {computed,ref,reactive,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElDrawer,ElMessage,ElMessageBox} from 'element-plus'
import {Plus} from '@element-plus/icons-vue'
import {request} from '@/api/owner'
import {getWorkspace,operationCache,type Workspace,type BusinessRecord} from '@/api/business'
import {money,sum,compare,percent} from '@/utils/decimal'
import {valuationIsCurrent} from '@/utils/valuationDate'
import AllocationLayers from './AllocationLayers.vue'
import {useAskStore} from '@/stores/ask'
import {registerPageMaterial} from '@/api/pageMaterial'
import AppDataState from '@/components/Global/AppDataState.vue'
type Result={type:string;currency:string;status:string;issues?:string[];rows?:Record<string,string|number>[];[key:string]:unknown}
type Preview={result:Result;token:string}
const calculatedAt=ref('')
const clockNow=ref(Date.now())
let dateTimer:ReturnType<typeof setInterval>|undefined
function updateClock(){clockNow.value=Date.now()}
onMounted(()=>{dateTimer=setInterval(updateClock,60000);window.addEventListener('focus',updateClock);document.addEventListener('visibilitychange',updateClock)})
onBeforeUnmount(()=>{if(dateTimer)clearInterval(dateTimer);window.removeEventListener('focus',updateClock);document.removeEventListener('visibilitychange',updateClock)})
const route=useRoute(),router=useRouter(),mode=computed(()=>route.path==='/plan/allocation'?'allocation':route.path==='/plan/budget'?'build_up':'pre_trade'),allocation=computed(()=>mode.value==='allocation'),title=computed(()=>allocation.value?'资产配置':mode.value==='build_up'?'分批预算':'交易前试算'),workspace=ref<Workspace|null>(null),busy=ref(false),error=ref(''),preview=ref<Preview|null>(null),snapshotTitle=ref(''),saved=ref(false),history=ref<BusinessRecord|null>(null),archiveOpen=ref(false),operations=operationCache()
const layersPanel=ref<InstanceType<typeof AllocationLayers>|null>(null),layersReady=ref(false)
const form=reactive({account_id:'',symbol:'',side:'buy',quantity:'1',price:'',fee:'0',max_percent:'25',budget:'100',stages:'2',targets:'@CASH=100',allocation_source:'symbols',cash_percent:'0'});let scenarioId='',lastInput:Record<string,unknown>|null=null,baseline=JSON.stringify(form)
type TradeInput={symbol:string;side:string;quantity:string;price:string;fee:string;max_percent:string}
const trades=ref<TradeInput[]>([])
function addTrade(){
 if(trades.value.length>=20)return
 if(!form.symbol.trim()||![form.quantity,form.price,form.fee,form.max_percent].every(v=>/^\d{1,12}(?:\.\d{1,8})?$/.test(v))){error.value='请先填写标的及有效数量、价格、费用和仓位上限';return}
 trades.value.push({symbol:form.symbol.trim().toUpperCase(),side:form.side,quantity:form.quantity,price:form.price,fee:form.fee,max_percent:form.max_percent});error.value=''
}
function moveTrade(index:number){const previous=trades.value[index-1];trades.value[index-1]=trades.value[index];trades.value[index]=previous}
watch(trades,invalidate,{deep:true,flush:'sync'})
watch(()=>form.account_id,()=>{trades.value=[]})
const account=computed(()=>workspace.value?.accounts.find(a=>a.id===form.account_id)),scenarios=computed(()=>workspace.value?.records.filter(r=>r.kind==='scenario')||[])
const allocationOverview=computed(()=>{
 const selected=account.value,positions=selected?.positions||[]
 const current=valuationIsCurrent(workspace.value?.base_valuation,clockNow.value)
 const valued=!!selected&&current&&selected.valuation_complete&&positions.every(p=>p.market_value!==null&&p.unrealized_pnl!==null)
 const market=valued?sum(positions.map(p=>p.market_value!)):null
 const cost=selected?sum(positions.map(p=>p.open_cost)):null
 const pnl=valued?sum(positions.map(p=>p.unrealized_pnl!)):null
 const returnRate=pnl!==null&&cost!==null&&compare(cost,'0')>0?percent(pnl,cost):'—'
 const layers=workspace.value?.records.filter(r=>r.kind==='allocation_layer'&&!r.archived&&r.account_id===selected?.id)||[]
 const assigned=new Set(layers.flatMap(r=>Array.isArray(r.symbols)?r.symbols.filter((s):s is string=>typeof s==='string'):[]))
 const assets=selected?.estimated_assets
 const share=(assignedState:boolean)=>market!==null&&assets&&compare(assets,'0')>0?percent(sum(positions.filter(p=>assigned.has(p.symbol)===assignedState).map(p=>p.market_value!)),assets):'—'
 const emptyNote=error.value?'账本读取失败，请刷新':'先选择账户'
 const quoteNote=!selected?emptyNote:!current?'评估日已变化，请刷新':!valued?'价格资料不足':'账户原币 · 不含现金'
 return [
  {label:'持仓市值',value:money(market),detail:quoteNote,tone:''},
  {label:'持仓成本',value:money(cost),detail:selected?`${selected.currency} · 未平仓成本`:emptyNote,tone:''},
  {label:'未实现收益率',value:returnRate,detail:quoteNote,tone:pnl!==null&&compare(pnl,'0')!==0?(compare(pnl,'0')>0?'positive':'negative'):''},
  {label:'已配置',value:share(true),detail:'已归属持仓市值 / 含现金资产',tone:''},
  {label:'未分配',value:share(false),detail:'未归属持仓市值 / 含现金资产',tone:''},
 ]
})
const unregisterMaterials=['/plan/allocation','/plan/budget','/plan/pre-trade'].map(path=>registerPageMaterial(path,()=>{
  if(route.path===path&&!busy.value&&historicalMaterial.value)return {scope:'fixed_simulation_snapshot',snapshot:historicalMaterial.value,notice:'明确选中的固定历史试算；保留当时输入、结果和价格依据，不代表当前账本或可执行交易。'}
  if(route.path!==path||busy.value||error.value||!preview.value||!lastInput||history.value||archiveOpen.value)throw Error('请先完成当前试算并关闭历史窗口，再载入材料；输入变化后需要重新计算。')
  return {scope:'current_planning_preview',page:path,calculated_at:calculatedAt.value,
    input:lastInput,result:preview.value.result,
    account:account.value?{id:account.value.id,name:account.value.name,currency:account.value.currency}:null,
    saved_snapshot_id:saved.value?scenarioId:null,
    notice:'当前试算输入与结果，不是已执行交易。仅包含此次试算，不含其他方案。账本或价格可能在计算后变化，采取行动前须重新计算并人工确认。'}
}))
onBeforeUnmount(()=>unregisterMaterials.forEach(remove=>remove()))
const historicalMaterial=ref<BusinessRecord|null>(null)
function selectHistoricalMaterial(){if(!history.value)return;historicalMaterial.value=JSON.parse(JSON.stringify(history.value));history.value=null;useAskStore().open()}
const inputLabels:Record<string,string>={type:'试算类型',account_id:'账户标识',symbol:'标的',side:'方向',quantity:'数量',price:'假设价格',fee:'费用',max_percent:'仓位上限 %',budget:'预算',stages:'批次',targets:'目标比例',cash_percent:'现金目标比例'}
function columnSet(type:string){if(type==='pre_trade_batch')return [{key:'stage',label:'顺序'},{key:'symbol',label:'标的'},{key:'side',label:'方向'},{key:'cash_after',label:'该笔后现金'},{key:'weight_after',label:'该笔后仓位 %'},{key:'status',label:'检查结果'}];return ['allocation','layer_allocation'].includes(type)?[{key:'symbol',label:'标的'},{key:'current_value',label:'当前市值'},{key:'current_percent',label:'当前比例 %'},{key:'target_percent',label:'目标比例 %'},{key:'adjustment_value',label:'调整金额'}]:[{key:'stage',label:'批次'},{key:'quantity',label:'数量'},{key:'price',label:'假设价格'},{key:'fee',label:'费用'},{key:'required_cash',label:'所需现金'}]}
const columns=computed(()=>columnSet(preview.value?.result.type||mode.value))
function cellLabel(value:string|number){return ({buy:'买入',sell:'卖出',passed:'通过',blocked:'阻断'} as Record<string,string>)[String(value)]||value}
function summary(result:Result){return [['assets_before','试算前净资产'],['cash_before','试算前现金'],['cash_after','试算后现金'],['quantity_after','试算后数量'],['position_value_after','试算后标的市值'],['estimated_assets_after','试算后净资产'],['weight_after','试算后仓位 %'],['planned_cash','计划支出'],['unallocated_budget','剩余预算']].filter(([key])=>key in result).map(([key,label])=>({label,value:result[key]===null?'—':key==='quantity_after'?String(result[key]):money(String(result[key]),key==='weight_after'?4:2)}))}
function invalidate(){historicalMaterial.value=null;preview.value=null;lastInput=null;saved.value=false;scenarioId='';operations.clear()}
watch(form,invalidate,{deep:true,flush:'sync'})
async function refresh(){if(busy.value)return;busy.value=true;error.value='';invalidate();try{workspace.value=await getWorkspace();if(!workspace.value.accounts.some(item=>item.id===form.account_id))form.account_id=workspace.value.accounts[0]?.id||'';baseline=JSON.stringify(form)}catch(e){workspace.value=null;error.value=e instanceof Error?e.message:'读取失败'}finally{busy.value=false}}
function body(){if(mode.value==='pre_trade'&&trades.value.length)return {type:'pre_trade_batch',account_id:form.account_id,trades:trades.value.map(t=>({...t}))};const base={type:mode.value,account_id:form.account_id};if(allocation.value&&form.allocation_source==='layers')return {type:'layer_allocation',account_id:form.account_id,cash_percent:form.cash_percent};if(allocation.value){const targets:Record<string,string>=Object.create(null);for(const line of form.targets.split('\n').map(s=>s.trim()).filter(Boolean)){const pair=line.split('=');if(pair.length!==2||!pair[0].trim()||!pair[1].trim())throw Error('目标比例应为每行 CODE=百分比');const key=pair[0].trim().toUpperCase();if(key in targets)throw Error('目标标的不能重复');const value=pair[1].trim();if(!/^\d{1,12}(?:\.\d{1,8})?$/.test(value))throw Error('目标比例须为非负普通小数，最多8位小数');targets[key]=value}if(compare(sum(Object.values(targets)),'100')!==0)throw Error('目标比例合计必须为 100%。');return {...base,targets}}const common={...base,symbol:form.symbol,price:form.price,fee:form.fee,max_percent:form.max_percent};if(mode.value==='build_up'){if(!/^([1-9]|1[0-2])$/.test(form.stages))throw Error('批次数必须为1–12整数');return {...common,budget:form.budget,stages:Number(form.stages)}}return {...common,side:form.side,quantity:form.quantity}}
async function calculate(){if(busy.value)return;error.value='';invalidate();busy.value=true;try{const input=body();const result=await request<Preview>('/api/v1/owner/planning','POST',input);lastInput=input;preview.value=result;calculatedAt.value=new Date().toISOString();snapshotTitle.value=title.value+' · '+new Date().toLocaleDateString('zh-CN')}catch(e){error.value=e instanceof Error?e.message:'试算失败'}finally{busy.value=false}}
async function save(){if(busy.value||!preview.value||!lastInput||saved.value)return;busy.value=true;error.value='';scenarioId ||= crypto.randomUUID();try{await request('/api/v1/owner/business','POST',operations.body('save',{id:scenarioId,revision:0,kind:'scenario',data:{title:snapshotTitle.value,input:lastInput,expected_token:preview.value.token}}));saved.value=true;operations.clear();try{workspace.value=await getWorkspace();ElMessage.success('固定试算已保存，账本没有改变')}catch{workspace.value=null;error.value='固定试算已保存，但账本重新读取失败。请刷新确认，避免重复保存。'}}catch(e){error.value=e instanceof Error?e.message:'保存失败'}finally{busy.value=false}}
async function archive(record:BusinessRecord){if(busy.value)return;busy.value=true;try{await request('/api/v1/owner/business','DELETE',operations.body('archive:'+record.id,{id:record.id,revision:record.revision}));workspace.value=await getWorkspace()}catch(e){error.value=e instanceof Error?e.message:'归档失败'}finally{busy.value=false}}
async function leave(){if(busy.value)return false;if(JSON.stringify(form)===baseline&&!preview.value&&!trades.value.length)return true;try{await ElMessageBox.confirm('离开会清除当前输入和未保存试算，已保存快照保留。','离开试算',{confirmButtonText:'离开',cancelButtonText:'继续试算'});return true}catch{return false}}
onBeforeRouteLeave(leave);onBeforeRouteUpdate(leave);watch(()=>route.path,()=>{trades.value=[];form.symbol=typeof route.query.symbol==='string'?route.query.symbol:'';refresh()},{immediate:true});const beforeUnload=(e:BeforeUnloadEvent)=>{if(busy.value||JSON.stringify(form)!==baseline||preview.value||trades.value.length){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>

<style scoped>
.sequence-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0;overflow-wrap:anywhere}.sequence-row>span{flex:1;min-width:150px}
.what-if-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-info .title { margin: 0; font-size: 24px; font-weight: 600; color: #303133; }
.header-info .subtitle { font-size: 14px; color: #909399; margin-top: 4px; display: block; }

.input-card {
  margin-bottom: 24px;
}

.cash-inputs {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) repeat(auto-fit, minmax(190px, 240px));
  gap: 12px;
  align-items: end;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.cash-copy,
.cash-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cash-copy span,
.cash-field span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notices-panel {
  margin-bottom: 24px;
}

.notice-item {
  margin-bottom: 8px;
}

.results-section {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #303133;
}

.summary-cards {
  margin-bottom: 24px;
}

.summary-card {
  text-align: center;
}

.summary-card .label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.summary-card .value { font-size: 20px; font-weight: bold; color: #303133; margin-bottom: 4px; }
.summary-card .diff { font-size: 12px; color: #909399; }

.text-up { color: #67C23A !important; }
.text-down { color: #F56C6C !important; }
.text-warning { color: #E6A23C !important; }

.details-row {
  margin-bottom: 24px;
}

.table-card, .chart-card {
  height: 100%;
}

.concentration-chart {
  height: 350px;
  width: 100%;
}

:deep(.row-new) { background-color: #f0f9eb !important; }
:deep(.row-modified) { background-color: #fdf6ec !important; }
:deep(.row-closed) { background-color: #fef0f0 !important; }
</style>

<style lang="scss" scoped>
.allocation-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.pyramid-section {
  margin-bottom: 24px;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
  gap: 16px;
  align-items: stretch;
}

.chart-card {
  min-width: 0;
  background:
    linear-gradient(145deg, rgba(24, 45, 77, 0.92), rgba(11, 24, 45, 0.94)),
    var(--el-bg-color);
  border: 1px solid rgba(97, 178, 255, 0.14);
  border-radius: 14px;
  padding: 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.chart-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.chart-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin: 0;
}

.chart-subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.chart-container {
  width: 100%;
  height: 270px;
}

.allocation-stack-card {
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(circle at 18% 8%, rgba(102, 227, 255, 0.14), transparent 30%),
      radial-gradient(circle at 85% 90%, rgba(124, 109, 255, 0.12), transparent 34%);
  }

  > * {
    position: relative;
  }
}

.stack-total {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid rgba(102, 227, 255, 0.16);
  border-radius: 10px;
  background: rgba(102, 227, 255, 0.06);

  span {
    font-size: 10px;
    color: var(--el-text-color-secondary);
  }

  strong {
    font-size: 16px;
    line-height: 1;
    color: #dceaff;
  }
}

.allocation-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stack-layer {
  --layer-color: #66e3ff;
  --target-width: 0%;
  --actual-width: 0%;

  padding: 12px;
  border: 1px solid rgba(132, 175, 224, 0.13);
  border-radius: 12px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--layer-color) 18%, transparent), transparent 58%),
    rgba(10, 24, 45, 0.62);
  transition: border-color 0.2s ease, transform 0.2s ease;

  &:hover {
    border-color: color-mix(in srgb, var(--layer-color) 45%, rgba(132, 175, 224, 0.13));
    transform: translateY(-1px);
  }
}

.stack-layer-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.stack-layer-identity {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.stack-tier {
  flex-shrink: 0;
  min-width: 48px;
  text-align: center;
  font-size: 10px;
  font-weight: 800;
  color: #061426;
  background: var(--layer-color);
  border-radius: 999px;
  padding: 4px 8px;
  box-shadow: 0 0 18px color-mix(in srgb, var(--layer-color) 32%, transparent);
}

.stack-name {
  max-width: 230px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 800;
  color: #e8f1ff;
}

.stack-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  font-size: 11px;
  color: rgba(196, 212, 235, 0.64);
}

.stack-numbers {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: repeat(3, auto);
  align-items: center;
  gap: 12px;

  > div:not(.stack-delta) {
    display: flex;
    flex-direction: column;
    gap: 2px;
    text-align: right;
  }

  span {
    font-size: 10px;
    color: rgba(196, 212, 235, 0.6);
  }

  strong {
    font-size: 13px;
    color: #f2f7ff;
  }
}

.stack-delta {
  min-width: 76px;
  text-align: center;
  font-size: 11px;
  font-weight: 800;
  border-radius: 999px;
  padding: 5px 8px;
  border: 1px solid transparent;

  &.is-over {
    color: #ffd48a;
    background: rgba(255, 202, 97, 0.11);
    border-color: rgba(255, 202, 97, 0.22);
  }

  &.is-under {
    color: #ff9dab;
    background: rgba(255, 123, 156, 0.11);
    border-color: rgba(255, 123, 156, 0.24);
  }

  &.is-balanced {
    color: #7ef0bd;
    background: rgba(53, 212, 154, 0.1);
    border-color: rgba(53, 212, 154, 0.22);
  }
}

.stack-track {
  position: relative;
  height: 8px;
  margin-top: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(116, 146, 188, 0.16);
}

.stack-target,
.stack-actual {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--target-width);
  border-radius: inherit;
}

.stack-target {
  background: color-mix(in srgb, var(--layer-color) 30%, rgba(255, 255, 255, 0.08));
}

.stack-actual {
  width: var(--actual-width);
  background: linear-gradient(90deg, var(--layer-color), color-mix(in srgb, var(--layer-color) 65%, #ffffff));
  box-shadow: 0 0 18px color-mix(in srgb, var(--layer-color) 28%, transparent);

  &.is-empty {
    width: 8px;
    opacity: 0.7;
  }
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

.summary-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.summary-value {
  font-size: 20px;
  font-weight: 800;
  color: var(--el-text-color-primary);

  &.positive { color: #1f9d68; }
  &.negative { color: #f56c6c; }
}

.layers-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.layer-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid var(--el-border-color);

  &.is-overweight { border-left-color: #e6a23c; }
  &.is-underweight { border-left-color: #f56c6c; }
}

.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.layer-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.layer-tier {
  font-size: 11px;
  font-weight: 700;
  color: #2f7dff;
  background: rgba(47, 125, 255, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

.layer-name {
  font-size: 18px;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin: 0;
}

.sector-tag {
  margin-left: 4px;
  font-weight: 500;
  color: #2f7dff;
  border-color: #2f7dff40;
  background: #2f7dff10;
}

.layer-actions {
  display: flex;
  gap: 4px;
}

.layer-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 16px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.metric-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.layer-strategy {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(47, 125, 255, 0.04);
  border-radius: 6px;
}

.layer-stock-pool {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.pool-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.pool-tag {
  font-weight: 600;
}

.layer-positions {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}

.positions-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.position-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
}

.pos-ticker {
  font-weight: 800;
  color: var(--el-text-color-primary);
  min-width: 60px;
}

.pos-name {
  flex: 1;
  color: var(--el-text-color-secondary);
}

.pos-weight {
  font-weight: 700;
  color: var(--el-text-color-primary);
  min-width: 50px;
  text-align: right;
}

.pos-value {
  color: var(--el-text-color-secondary);
  min-width: 80px;
  text-align: right;
}

.rebalance-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px;
  margin-top: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin: 0 0 16px 0;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(47, 125, 255, 0.04);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 14px;

  b { color: #2f7dff; }
}

.suggestion-reason {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.contribution-section {
  margin-top: 32px;
}

.contribution-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.contribution-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-border-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  &.is-positive {
    border-left: 3px solid #1f9d68;
  }

  &.is-negative {
    border-left: 3px solid #f56c6c;
  }
}

.contrib-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.contrib-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.contrib-tier {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color);
  padding: 2px 6px;
  border-radius: 4px;
}

.contrib-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.contrib-metric {
  text-align: center;
}

.contrib-label {
  display: block;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.contrib-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);

  &.positive { color: #1f9d68; }
  &.negative { color: #f56c6c; }
}

.contrib-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.bar-track {
  flex: 1;
  height: 6px;
  background: var(--el-fill-color);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #2f7dff, #1f9d68);
  border-radius: 3px;
  transition: width 0.3s;
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
  .summary-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .chart-row {
    grid-template-columns: 1fr;
  }

  .chart-heading,
  .stack-layer-main {
    flex-direction: column;
    align-items: stretch;
  }

  .stack-total {
    align-items: flex-start;
  }

  .stack-numbers {
    width: 100%;
    grid-template-columns: repeat(3, 1fr);

    > div:not(.stack-delta) {
      text-align: left;
    }
  }

  .layer-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

<style scoped>
.sequence-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0;overflow-wrap:anywhere}.sequence-row>span{flex:1;min-width:150px}.simulation-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.target-input{grid-column:1/-1}.summary-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:20px 0}.summary-value{overflow-wrap:anywhere}.card-header,.header-actions,.snapshot-save{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.snapshot-save{margin-top:18px}.snapshot-save .el-input{max-width:360px}.chart-card{margin-bottom:14px}.scenario-list{margin-top:24px}.header-title{margin:0}.page-header{flex-wrap:wrap;gap:12px}pre,dd{white-space:pre-wrap;overflow-wrap:anywhere}dd{margin:6px 0 14px}.summary-card{min-width:0}@media(max-width:480px){.simulation-form{grid-template-columns:1fr}.what-if-page,.allocation-page{padding:12px 0}.summary-row{grid-template-columns:1fr 1fr}.summary-value{font-size:18px}}</style>

<style scoped>
.sequence-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0;overflow-wrap:anywhere}.sequence-row>span{flex:1;min-width:150px}.what-if-page .title,.allocation-page .header-title{color:#edf5ff}.header-subtitle,.subtitle{color:#a5bad3}</style>

<style scoped>
.allocation-overview{margin-bottom:24px}
.overview-scope{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--el-text-color-secondary);margin-bottom:12px}
.overview-scope .el-select{width:min(260px,100%)}
.allocation-overview-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}
.allocation-overview-grid .summary-card{min-width:0;display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:8px;border-radius:14px;background:var(--el-bg-color);border:1px solid var(--el-border-color-lighter)}
.allocation-overview-grid .summary-label{margin:0}
.allocation-overview-grid .summary-value{font-size:24px;overflow-wrap:anywhere}
.allocation-overview-grid small{font-size:11px;line-height:1.5;color:var(--el-text-color-secondary)}
.allocation-page :deep(.layers-container){margin-bottom:24px}
@media(max-width:1000px){.allocation-overview-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:620px){.allocation-overview-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){
  .allocation-page{padding:24px}
  .allocation-page .page-header{flex-wrap:nowrap;align-items:flex-start;gap:12px}
  .allocation-page .header-copy{flex:1;min-width:0}
  .allocation-page .header-actions{flex:0 0 auto}
  .allocation-page .header-actions .el-button{margin:0;padding:8px 12px;min-height:34px}
  .allocation-page .header-info .title{font-weight:800}
  .allocation-page .header-subtitle{font-size:12px;line-height:1.5}
  .overview-scope{flex-wrap:nowrap;gap:8px;font-size:10px}
  .overview-scope>span:first-child{min-width:0}
  .overview-scope .el-select{width:165px;flex:0 0 165px}
  .allocation-overview-grid{gap:16px}
  .allocation-overview-grid .summary-card{padding:12px 14px;gap:4px;border-radius:12px}
  .allocation-overview-grid .summary-value{font-size:21px}
  .allocation-overview-grid small{font-size:9px;line-height:1.25}
}
@media(max-width:350px){.allocation-page{padding:20px 14px}.overview-scope .el-select{width:140px;flex-basis:140px}.allocation-overview-grid{gap:10px}.allocation-overview-grid .summary-card{padding:10px}.allocation-overview-grid small{display:none}.allocation-page .header-actions .el-button{padding:7px 9px;font-size:11px}}
</style>
