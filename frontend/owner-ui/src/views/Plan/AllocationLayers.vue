<template>
 <section class="layers-container">
  <h2 v-if="layers.length" class="sr-only">分层资产配置</h2>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <div v-if="!error&&!layers.length" class="empty-state"><el-icon :size="64" color="#c0c4cc"><PieChart/></el-icon><h3>暂无配置层</h3><p>创建配置层来管理你的资产配置结构</p><el-button type="primary" :disabled="!account||busy" @click="edit()">创建第一个配置层</el-button><small v-if="unassigned.length">当前未分配持仓：{{ unassigned.join('、') }}</small></div>
  <div v-if="layers.length" class="chart-row"><div class="chart-card allocation-stack-card"><div class="chart-heading"><div><h3 class="chart-title">配置结构</h3><p class="chart-subtitle">用目标、实际和偏离看每一层，而不是看装饰图形。</p></div><div class="stack-total"><span>目标合计</span><strong>{{ sum(layers.map(l=>l.target_percent)) }}%</strong></div></div>
   <div class="allocation-stack"><div v-for="(layer,index) in layers" :key="layer.id" class="stack-layer" :style="stackStyle(layer,index)"><div class="stack-layer-main"><div class="stack-layer-identity"><span class="stack-tier">Tier {{ layer.tier }}</span><div><div class="stack-name">{{ layer.title }}</div><div class="stack-meta">{{ layer.sector||'未分类' }} · {{ account?.positions.filter(p=>layer.symbols.includes(p.symbol)).length||0 }} 个持仓</div></div></div><div class="stack-numbers"><div><span>目标</span><strong>{{ layer.target_percent }}%</strong></div><div><span>实际</span><strong>{{ actual(layer) }}</strong></div><div class="stack-delta" :class="deviationTone(layer)">{{ deviationLabel(layer) }}</div></div></div><div class="stack-track" aria-hidden="true"><div class="stack-target"></div><div v-if="value(layer)!==null" class="stack-actual"></div></div></div></div>
  </div><div class="chart-card allocation-comparison-card"><div class="chart-heading"><div><h3 class="chart-title">目标 vs 实际</h3><p class="chart-subtitle">按所选账户含现金资产计算；价格缺失时实际值留空。</p></div></div><div class="comparison-legend"><span><i class="target-key"/>目标</span><span><i class="actual-key"/>实际</span></div><div class="comparison-scroll"><div class="comparison-plot" :style="{minWidth:Math.max(320,layers.length*72+40)+'px'}" role="img" :aria-label="'各层目标与实际占比：'+layers.map(l=>l.title+'目标'+l.target_percent+'%，实际'+actual(l)).join('；')"><div class="plot-grid" aria-hidden="true"><div v-for="tick in [100,80,60,40,20,0]" :key="tick" class="plot-line" :style="{bottom:tick+'%'}"><span>{{ tick }}%</span></div></div><div class="plot-groups" aria-hidden="true"><div v-for="layer in layers" :key="layer.id" class="plot-group"><div class="plot-pair"><i class="target-bar" :style="{height:barHeight(layer.target_percent)+'%'}"/><i v-if="actualBarHeight(layer)!==null" class="actual-bar" :style="{height:actualBarHeight(layer)+'%'}"/></div><span class="plot-name">{{ layer.title }}</span></div></div></div></div></div></div>
  <p v-if="layers.length&&!targetComplete" class="allocation-warning" role="status">目标合计 {{ sum(layers.map(l=>l.target_percent)) }}%，尚未达到100%，不视为完整配置。</p>
  <article v-for="layer in layers" :key="layer.id" class="layer-card">
   <div class="layer-header"><div class="layer-title-row"><span class="layer-tier">Tier {{ layer.tier }}</span><h3 class="layer-name">{{ layer.title }}</h3><el-tag>{{ layer.sector||'未分类' }}</el-tag></div><div><el-button link @click="edit(layer)">编辑层</el-button><el-button link @click="history=layer">版本历史</el-button><el-popconfirm title="归档配置层并保留历史？" confirm-button-text="归档" @confirm="archive(layer)"><template #reference><el-button link :disabled="busy">归档层</el-button></template></el-popconfirm></div></div>
   <div class="layer-metrics"><div>目标 {{ layer.target_percent }}%</div><div>实际 {{ actual(layer) }}</div><div>偏离 {{ deviation(layer) }}</div><div>当前市值 {{ money(value(layer)) }} {{ account?.currency }}</div></div>
   <p>归属标的：{{ layer.symbols.join('、')||'尚未分配' }} · 单股上限 {{ layer.max_single_percent }}%（占账户资产）</p>
   <p v-if="breaches(layer).length">超过用户单股上限：{{ breaches(layer).join('、') }}</p>
   <p>目标金额 {{ money(layer.target_amount) }} · 股票池 {{ layer.stock_pool.join('、')||'未填写' }}</p><p class="layer-note">{{ layer.strategy_note||'未填写策略说明' }}</p>
  </article>
  <div v-if="layers.length" class="allocation-management"><div class="allocation-management-actions"><el-button :disabled="!account?.positions.length||busy" @click="openAssignment">调整持仓归属</el-button><el-button v-if="showCreateButton" type="primary" :disabled="!account||busy" @click="edit()">新建配置层</el-button></div><details><summary>账户口径与未分层持仓</summary><p>各层按当前账户原币资产计算占比；股票池仅作备选，归属标的才计入本层。修改配置不会创建成交。</p><p>未分层持仓 {{ unassigned.join('、')||'无' }} · 现金单列 {{ money(account?.cash) }} {{ account?.currency }}</p></details></div>
  <div v-if="contributions.length" class="contribution-section"><h3 class="section-title">层级贡献度 · {{ account?.currency }}</h3><p>仅当前持仓未实现盈亏，收益率以未平仓成本为基数；实际占比以含现金的账户资产为基数。已实现盈亏、现金和未分层持仓不归入层级盈亏。</p><div class="contribution-grid"><div v-for="c in contributions" :key="c.layer.id" class="contribution-card" :class="{'is-positive':c.pnl!==null&&compare(c.pnl,'0')>0,'is-negative':c.pnl!==null&&compare(c.pnl,'0')<0}"><div class="contrib-header"><span class="contrib-name">{{ c.layer.title }}</span><span class="contrib-tier">Tier {{ c.layer.tier }}</span></div><div class="contrib-metrics"><div class="contrib-metric"><span class="contrib-label">市值</span><span class="contrib-value">{{ money(c.marketValue) }}</span></div><div class="contrib-metric"><span class="contrib-label">未实现收益率</span><span class="contrib-value" :class="{'positive':c.pnl!==null&&compare(c.pnl,'0')>0,'negative':c.pnl!==null&&compare(c.pnl,'0')<0}">{{ c.pnl===null?'—':percent(c.pnl,c.cost) }}</span></div><div class="contrib-metric"><span class="contrib-label">持仓</span><span class="contrib-value">{{ c.count }}</span></div></div><p>未平仓成本 {{ money(c.cost) }} · 未实现盈亏 {{ money(c.pnl) }}</p><p v-if="!valuationCurrent">评估日已变化，请刷新后查看市值和盈亏。</p><p v-else-if="c.missing">{{ c.missing }} 项缺少有效价格，市值和盈亏待补。</p><div class="contrib-bar"><div class="bar-label">目标 {{ c.layer.target_percent }}%</div><div class="bar-track"><div v-if="value(c.layer)!==null&&account?.estimated_assets&&compare(account.estimated_assets,'0')>0" class="bar-fill" :style="{width:actual(c.layer)}"></div></div><div class="bar-label">实际 {{ actual(c.layer) }}</div></div></div></div></div>
  <el-button v-if="layers.length||archived.length" @click="historyOpen=true">查看归档配置层</el-button>
  <el-dialog v-model="assignDialog" title="调整持仓归属" width="min(560px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="closeAssignment" :show-close="!busy" :close-on-press-escape="!busy"><p>保存到账户：{{ assignAccountName }}</p><p>只改变配置层归属，不创建成交或改变持仓数量。</p><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top"><el-form-item label="持仓标的"><el-select v-model="assignSymbol" :disabled="busy" @change="selectAssignment"><el-option v-for="p in assignPositions" :key="p.symbol" :value="p.symbol" :label="p.symbol"/></el-select></el-form-item><el-form-item label="归属配置层"><el-select v-model="assignLayer" :disabled="busy"><el-option value="" label="未分配"/><el-option v-for="layer in assignLayers" :key="layer.id" :value="layer.id" :label="layer.title"/></el-select></el-form-item></el-form><template #footer><el-button :disabled="busy" @click="closeAssignment">取消</el-button><el-button :disabled="!assignSymbol" :loading="busy" type="primary" @click="saveAssignment">保存持仓归属</el-button></template></el-dialog>
  <el-dialog v-model="dialog" :title="editing?'编辑配置层':'新建配置层'" width="min(560px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!busy" :close-on-press-escape="!busy">
   <p>保存到账户：{{ workspace?.accounts.find(a=>a.id===editAccount)?.name }}</p><el-alert v-if="saveError" :title="saveError" type="error" :closable="false"/><el-form label-position="top">
    <el-form-item v-for="field in fields" :key="field.key" :label="field.label"><el-input v-model="form[field.key]" :disabled="busy" :type="field.key==='strategy_note'?'textarea':'text'"/></el-form-item>
   </el-form><template #footer><el-button :disabled="busy" @click="close">取消</el-button><el-button type="primary" :loading="busy" @click="save">保存配置层</el-button></template>
  </el-dialog>
  <el-dialog v-model="historyOpen" title="归档配置层" width="min(560px,calc(100vw - 24px))"><article v-for="layer in archived" :key="layer.id"><span>{{ layer.title }}</span><el-button @click="historyOpen=false;history=layer">查看版本</el-button></article></el-dialog>
  <el-dialog :model-value="!!history" title="配置层版本历史" width="min(680px,calc(100vw - 24px))" @close="history=null"><article v-for="version in versions" :key="version.revision"><h3>{{ version.title }} · v{{ version.revision }} {{ version.archived?'已归档':'' }}</h3><p>{{ version.updated_at }} · Tier {{ version.tier }} · {{ version.sector }}</p><p>目标 {{ version.target_percent }}% · 目标金额 {{ money(version.target_amount) }} · 单股上限 {{ version.max_single_percent }}%</p><p>归属：{{ version.symbols.join('、') }} · 股票池：{{ version.stock_pool.join('、') }}</p><p class="layer-note">{{ version.strategy_note }}</p></article></el-dialog>
 </section>
</template>
<script setup lang="ts">
import {computed,reactive,ref,watch,onMounted,onBeforeUnmount} from 'vue'
import {onBeforeRouteLeave} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {PieChart} from '@element-plus/icons-vue'
import {getWorkspace,operationCache,type Workspace,type BusinessRecord} from '@/api/business'
import {request} from '@/api/owner'
import {money,sum,percent,divide,negate,compare} from '@/utils/decimal'
import {valuationIsCurrent} from '@/utils/valuationDate'
type Layer=BusinessRecord & {account_id:string;tier:number;sector:string;target_percent:string;target_amount:string|null;max_single_percent:string;strategy_note:string;symbols:string[];stock_pool:string[]}
const props=withDefaults(defineProps<{accountId:string;refreshKey:string;showCreateButton?:boolean}>(),{showCreateButton:true}),workspace=ref<Workspace|null>(null),busy=ref(false),error=ref(''),saveError=ref(''),dialog=ref(false),editing=ref<Layer|null>(null),history=ref<Layer|null>(null),historyOpen=ref(false),ops=operationCache()
const clockNow=ref(Date.now())
let dateTimer:ReturnType<typeof setInterval>|undefined
function updateClock(){clockNow.value=Date.now()}
onMounted(()=>{dateTimer=setInterval(updateClock,60000);window.addEventListener('focus',updateClock);document.addEventListener('visibilitychange',updateClock)})
const assignAccountName=ref(''),assignDialog=ref(false),assignSymbol=ref(''),assignLayer=ref(''),assignPositions=ref<{symbol:string}[]>([]),assignLayers=ref<Layer[]>([])
const emit=defineEmits<{changed:[];readiness:[ready:boolean]}>()
let assignAccount='',assignToken='',assignBaseline=''
let id='',baseline='',loadVersion=0,editAccount=''
const blank=()=>({title:'',tier:'1',sector:'',target_percent:'0',target_amount:'',max_single_percent:'25',strategy_note:'',symbols:'',stock_pool:''}),form=reactive(blank())
type Key=keyof typeof form
const fields:Array<{key:Key;label:string}>=[{key:'title',label:'配置层名称'},{key:'tier',label:'层级（1–10）'},{key:'sector',label:'板块分类'},{key:'target_percent',label:'目标占比 %'},{key:'target_amount',label:'目标金额（选填）'},{key:'max_single_percent',label:'单股上限 %'},{key:'strategy_note',label:'策略说明'},{key:'symbols',label:'归属标的（逗号分隔）'},{key:'stock_pool',label:'备选股票池（逗号分隔）'}]
const account=computed(()=>workspace.value?.accounts.find(a=>a.id===props.accountId)),all=computed(()=>workspace.value?.records.filter(r=>r.kind==='allocation_layer'&&r.account_id===props.accountId) as Layer[]||[]),layers=computed(()=>all.value.filter(l=>!l.archived).sort((a,b)=>a.tier-b.tier||a.title.localeCompare(b.title))),archived=computed(()=>workspace.value?.versions.filter(r=>r.kind==='allocation_layer'&&r.account_id===props.accountId&&r.archived) as Layer[]||[]),versions=computed(()=>workspace.value?.versions.filter(r=>r.id===history.value?.id).slice().reverse() as Layer[]||[])
const unassigned=computed(()=>account.value?.positions.filter(p=>!layers.value.some(l=>l.symbols.includes(p.symbol))).map(p=>p.symbol)||[]),targetComplete=computed(()=>compare(sum(layers.value.map(l=>l.target_percent)),'100')===0),dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline||assignDialog.value&&JSON.stringify([assignSymbol.value,assignLayer.value])!==assignBaseline)
const valuationCurrent=computed(()=>valuationIsCurrent(workspace.value?.base_valuation,clockNow.value))
const contributions=computed(()=>layers.value.map(layer=>{const positions=account.value?.positions.filter(p=>layer.symbols.includes(p.symbol))||[];const missing=valuationCurrent.value?positions.filter(p=>p.market_value===null||p.unrealized_pnl===null).length:positions.length;return {layer,count:positions.length,missing,cost:sum(positions.map(p=>p.open_cost)),marketValue:!valuationCurrent.value||missing?null:sum(positions.map(p=>p.market_value!)),pnl:!valuationCurrent.value||missing?null:sum(positions.map(p=>p.unrealized_pnl!))}}))
function value(layer:Layer){return valuationCurrent.value&&account.value?.valuation_complete?sum(account.value.positions.filter(p=>layer.symbols.includes(p.symbol)).map(p=>p.market_value!)):null}
function stackStyle(layer:Layer,index:number){const colors=['#66e3ff','#8d9eff','#6de2b1','#e6c47a'];const v=value(layer);return {'--layer-color':colors[index%colors.length],'--target-width':layer.target_percent+'%','--actual-width':v===null||!account.value?.estimated_assets||compare(account.value.estimated_assets,'0')===0?'0%':percent(v,account.value.estimated_assets)}}
function barHeight(percentValue:string){return Math.max(0,Math.min(100,Number(percentValue)||0))}
function actualBarHeight(layer:Layer){const v=value(layer),assets=account.value?.estimated_assets;if(v===null||!assets||compare(assets,'0')<=0)return null;return Math.max(0,Math.min(100,Number(divide(v,assets)!)*100))}
function actual(layer:Layer){const v=value(layer);return v===null?(valuationCurrent.value?'—（缺少有效价格）':'—（评估日已变化）'):percent(v,account.value!.estimated_assets!)}
function deviationRatio(layer:Layer){const v=value(layer),assets=account.value?.estimated_assets;if(v===null||!assets||compare(assets,'0')<=0)return null;return sum([divide(v,assets)!,negate(divide(layer.target_percent,'100')!)])}
function deviation(layer:Layer){const ratio=deviationRatio(layer);return ratio===null?'—':percent(ratio,'1')}
function deviationTone(layer:Layer){const ratio=deviationRatio(layer);return ratio===null?'is-unknown':compare(ratio,'0')>0?'is-over':compare(ratio,'0')<0?'is-under':'is-balanced'}
function deviationLabel(layer:Layer){const ratio=deviationRatio(layer);if(ratio===null)return '待补';const direction=compare(ratio,'0');return direction>0?'超配 '+percent(ratio,'1'):direction<0?'低配 '+percent(negate(ratio),'1'):'达标'}
function breaches(layer:Layer){if(!valuationCurrent.value||!account.value?.valuation_complete||compare(account.value.estimated_assets!,'0')===0)return [];return account.value.positions.filter(p=>layer.symbols.includes(p.symbol)&&compare(divide(p.market_value!,account.value!.estimated_assets!)!,divide(layer.max_single_percent,'100')!)>0).map(p=>p.symbol)}
function openAssignment(){assignAccountName.value=account.value!.name;assignAccount=props.accountId;assignToken=workspace.value!.token;assignPositions.value=account.value!.positions;assignLayers.value=layers.value;assignSymbol.value=assignPositions.value[0]?.symbol||'';selectAssignment();saveError.value='';ops.clear();assignDialog.value=true}
function selectAssignment(){assignLayer.value=assignLayers.value.find(l=>l.symbols.includes(assignSymbol.value))?.id||'';assignBaseline=JSON.stringify([assignSymbol.value,assignLayer.value])}
async function closeAssignment(){if(await canLeave())assignDialog.value=false}
async function saveAssignment(){if(busy.value)return;busy.value=true;try{await request('/api/v1/owner/allocation-assignment','POST',ops.body('assign',{account_id:assignAccount,symbol:assignSymbol.value,layer_id:assignLayer.value||null,expected_token:assignToken}));assignDialog.value=false;ops.clear();if(await load())emit('changed');else ElMessage.warning('持仓归属已保存，但重新读取失败。请刷新确认。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败，请刷新后重试'}finally{busy.value=false}}
async function load(){const version=++loadVersion;emit('readiness',false);try{const data=await getWorkspace();if(version!==loadVersion)return false;workspace.value=data;error.value='';emit('readiness',!!data.accounts.find(a=>a.id===props.accountId));return true}catch(e){if(version===loadVersion){workspace.value=null;history.value=null;error.value=e instanceof Error?e.message:'读取失败';emit('readiness',false)}return false}}
function edit(layer?:Layer){if(busy.value||error.value||!account.value)return;editing.value=layer||null;editAccount=props.accountId;id=layer?.id||crypto.randomUUID();Object.assign(form,blank(),layer?{title:layer.title,tier:String(layer.tier),sector:layer.sector,target_percent:layer.target_percent,target_amount:layer.target_amount??'',max_single_percent:layer.max_single_percent,strategy_note:layer.strategy_note,symbols:layer.symbols.join(','),stock_pool:layer.stock_pool.join(',')}:{});baseline=JSON.stringify(form);saveError.value='';ops.clear();dialog.value=true}
defineExpose({openCreate:()=>edit()})
async function canLeave(){if(busy.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的配置层修改？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await canLeave())dialog.value=false}
async function save(){if(busy.value)return;saveError.value='';if(!/^(?:[1-9]|10)$/.test(form.tier)){saveError.value='层级必须为1–10整数';return}busy.value=true;try{const symbols=(s:string)=>s.split(/[,，\n]/).map(v=>v.trim().toUpperCase()).filter(Boolean);await request('/api/v1/owner/business','POST',ops.body('save',{id,revision:editing.value?.revision||0,kind:'allocation_layer',data:{...form,account_id:editAccount,tier:Number(form.tier),target_amount:form.target_amount||null,symbols:symbols(form.symbols),stock_pool:symbols(form.stock_pool)}}));dialog.value=false;ops.clear();if(await load())emit('changed');else ElMessage.warning('配置层已保存，但重新读取失败。请刷新确认，避免重复保存。')}catch(e){saveError.value=e instanceof Error?e.message:'保存失败'}finally{busy.value=false}}
async function archive(layer:Layer){if(busy.value)return;busy.value=true;try{await request('/api/v1/owner/business','DELETE',ops.body('archive:'+layer.id,{id:layer.id,revision:layer.revision}));ops.clear();if(await load())emit('changed');else ElMessage.warning('配置层已归档，但重新读取失败。请刷新确认。')}catch(e){error.value=e instanceof Error?e.message:'归档失败'}finally{busy.value=false}}
onBeforeRouteLeave(canLeave);watch(()=>[props.accountId,props.refreshKey],load,{immediate:true});const unload=(e:BeforeUnloadEvent)=>{if(dirty.value||busy.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>{loadVersion++;if(dateTimer)clearInterval(dateTimer);window.removeEventListener('focus',updateClock);document.removeEventListener('visibilitychange',updateClock);window.removeEventListener('beforeunload',unload)})
</script>
<style scoped lang="scss">
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.allocation-warning{margin:0;color:var(--el-color-warning);font-size:12px;line-height:1.6}.allocation-management{display:grid;gap:10px}.allocation-management-actions{display:flex;gap:8px;flex-wrap:wrap}.allocation-management p{margin:0;color:var(--el-text-color-secondary);font-size:12px;line-height:1.6}.allocation-management details{font-size:12px;color:var(--el-text-color-secondary)}.allocation-management summary{cursor:pointer;color:#91ccef}.allocation-management details p{margin:8px 0 0}

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

  &.is-unknown {
    color: rgba(196, 212, 235, 0.8);
    background: rgba(196, 212, 235, 0.08);
    border-color: rgba(196, 212, 235, 0.18);
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

.empty-state small { margin-top: 20px; font-size: 12px; }

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


.layers-container{display:flex;flex-direction:column;gap:16px;margin-bottom:24px}.layer-header,.layer-title-row,.layer-metrics{display:flex;gap:14px;justify-content:space-between;align-items:center;flex-wrap:wrap}.layer-card{padding:22px;border-radius:16px;background:var(--el-bg-color);border:1px solid var(--el-border-color)}.layer-tier{color:var(--el-color-primary);font-weight:700}.layer-name{margin:0}.layer-note{white-space:pre-wrap;overflow-wrap:anywhere}.layer-metrics{margin:16px 0}.layers-container p{overflow-wrap:anywhere}

.contribution-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}.contribution-card{min-width:0}.contrib-header{gap:8px}.contrib-name,.contrib-value,.contribution-card p,.bar-label{overflow-wrap:anywhere}.contrib-metric{min-width:0}.contrib-bar{flex-wrap:wrap}
.allocation-comparison-card{min-height:365px}.comparison-legend{display:flex;justify-content:center;gap:18px;color:var(--el-text-color-secondary);font-size:12px}.comparison-legend span{display:flex;align-items:center;gap:5px}.comparison-legend i{width:22px;height:10px;border-radius:2px}.target-key,.target-bar{background:#2f7dff}.actual-key,.actual-bar{background:#1f9d68}.comparison-scroll{overflow-x:auto;max-width:100%;padding-top:20px}.comparison-plot{position:relative;height:270px;padding:0 12px 0 34px}.plot-grid{position:absolute;inset:0 12px 26px 34px}.plot-line{position:absolute;left:0;right:0;border-top:1px dashed rgba(175,204,232,.45)}.plot-line span{position:absolute;left:-32px;top:-7px;color:var(--el-text-color-secondary);font-size:10px}.plot-groups{position:absolute;inset:0 12px 0 34px;display:flex;align-items:flex-end;gap:10px}.plot-group{height:100%;flex:1;min-width:48px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}.plot-pair{height:calc(100% - 26px);width:100%;display:flex;align-items:flex-end;justify-content:center;gap:4px}.plot-pair i{display:block;width:min(18px,35%);border-radius:3px 3px 0 0}.plot-name{height:26px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--el-text-color-secondary);font-size:11px;padding-top:5px}
</style>
