<template>
 <div class="diagnosis-page">
  <div class="page-header"><div class="header-info"><h2 class="title">组合诊断</h2><span class="subtitle">按全部账户或单账户持仓、已记录价格和你的纪律阈值复核，保留每次诊断依据。</span></div><div class="header-actions"><el-button :disabled="busy" @click="refresh">刷新账本与历史</el-button><el-button @click="router.push('/review/rules')">规则与周期趋势</el-button></div></div>
  <Constitution ref="constitutionPanel" :policy="policy" :disabled="busy" @use="useConstitution"/><p v-if="constitutionRevision">本次选用纪律 v{{ constitutionRevision }}；修改阈值后转为自定义政策。</p>
  <AppDataState v-if="error" tone="error" title="诊断未完成" :description="error"/>
  <AppDataState v-if="!busy&&!account&&!error" tone="empty" title="尚无诊断账户" description="先在账户管理建立账户并录入实际持仓，再进行组合诊断。"/>
  <el-form label-position="top"><el-form-item label="诊断账户"><el-select :model-value="accountId" :disabled="busy" @update:model-value="switchAccount"><el-option v-if="workspace?.accounts.length" value="portfolio:all" label="全部账户组合 · USD"/><el-option v-for="a in workspace?.accounts" :key="a.id" :value="a.id" :label="a.name+' · '+a.currency"/></el-select></el-form-item></el-form>
  <el-card v-if="account&&account.positions.every(p=>contexts[p.symbol])" class="policy-card" shadow="never"><template #header><strong>诊断依据与纪律阈值</strong></template>
   <p v-if="accountId==='portfolio:all'">全部账户统一按已保存汇率折算为 USD；同币种、同代码持仓合并，不同币种代码分开。成本与浮盈使用当次汇率，不包含历史汇兑收益。各账户单股上限仍按该账户资产检查。</p>
   <p>以持仓市值（不含现金）计算权重；新闻为你录入的观察，不会自动联网核实。缺失资料会保留为未知，不补成满分。</p>
   <el-form label-position="top"><div class="policy-grid"><el-form-item v-for="f in policyFields" :key="f.key" :label="f.label"><el-input v-model="policy[f.key]" :disabled="busy" inputmode="decimal"/></el-form-item></div>
    <fieldset v-for="(rule,index) in policy.custom_rules" :key="index"><legend>自定义纪律 {{ index+1 }}</legend><el-form-item :label="`规则名称 ${index+1}`"><el-input v-model="rule.name" :disabled="busy"/></el-form-item><el-form-item label="指标"><el-select v-model="rule.metric" :disabled="busy"><el-option value="position_percent" label="持仓占比 %"/><el-option value="unrealized_pnl_percent" label="未实现盈亏率 %"/></el-select></el-form-item><el-form-item label="比较"><el-select v-model="rule.operator" :disabled="busy"><el-option v-for="(label,key) in operators" :key="key" :value="key" :label="label"/></el-select></el-form-item><el-form-item label="阈值"><el-input v-model="rule.threshold" :disabled="busy"/></el-form-item><el-form-item label="程度"><el-select v-model="rule.severity" :disabled="busy"><el-option value="watch" label="观察"/><el-option value="critical" label="严重"/></el-select></el-form-item><el-button :disabled="busy" @click="policy.custom_rules.splice(index,1)">删除规则 {{ index+1 }}</el-button></fieldset>
    <el-button :disabled="busy||policy.custom_rules.length>=20" @click="addRule">添加自定义纪律</el-button>
    <fieldset v-for="p in account.positions" :key="p.symbol"><legend>{{ p.symbol }} · 持仓资料</legend><p>价格状态：{{ priceNames[p.quote_status] }}</p><el-button :disabled="busy" @click="loadSources(p.symbol)">核对 {{ p.symbol }} 已保存来源</el-button><el-button v-if="contexts[p.symbol].source_evidence" :disabled="busy" @click="manualContext(p.symbol)">改为手工观察</el-button><div v-if="sourceProposal?.symbol===p.symbol" class="saved-source-proposal"><p>{{ sourceProposal.notice }}</p><template v-if="sourceProposal.context"><p>公司：{{ sourceProposal.context.company }} · 新闻：{{ newsNames[sourceProposal.context.news as keyof typeof newsNames] }}</p><p>观察依据日期：{{ sourceProposal.context.as_of }}</p><details><summary>查看来源版本与原文</summary><pre>{{ JSON.stringify(sourceProposal.context.source_evidence,null,2) }}</pre></details><el-button :disabled="busy" @click="adoptSources(p.symbol)">核对后采用 {{ p.symbol }} 来源</el-button></template><p v-else>没有可采用的公司来源；可在个人连接中主动查询并保存，或继续手工录入。</p></div><p v-if="contexts[p.symbol].source_evidence">已绑定供应商来源版本，未人工核验。改动需重新核对；切换手工观察会清除来源绑定。</p><el-form-item :label="`${p.symbol} 公司归属`"><el-input v-model="contexts[p.symbol].company" :disabled="busy||!!contexts[p.symbol].source_evidence"/></el-form-item><el-form-item :label="`${p.symbol} 新闻观察`"><el-select v-model="contexts[p.symbol].news" :disabled="busy||!!contexts[p.symbol].source_evidence"><el-option v-for="(label,key) in newsNames" :key="key" :value="key" :label="label"/></el-select></el-form-item><el-form-item :label="`${p.symbol} 资料来源`"><el-input v-model="contexts[p.symbol].source" :disabled="busy||!!contexts[p.symbol].source_evidence"/></el-form-item><el-form-item :label="`${p.symbol} 观察日期`"><el-input v-model="contexts[p.symbol].as_of" type="date" :disabled="busy||!!contexts[p.symbol].source_evidence"/></el-form-item></fieldset>
   </el-form><el-button type="primary" :disabled="busy" @click="run">运行诊断预览</el-button><el-button v-if="preview" :disabled="busy" @click="save">保存本次诊断</el-button><el-button v-if="preview" :disabled="busy" @click="captureDaily">生成并保存事实日报</el-button>
  </el-card>
  <template v-if="report">
   <DiagnosisIntelligence :brain="report.intelligence" :maximum="report.policy.max_percent" :currency="report.currency"/>
   <div class="status-strip"><div class="status-pill"><span class="status-label">报告状态</span><strong class="status-value">{{ statusNames[report.status] }}</strong></div><div class="status-pill"><span class="status-label">依据时间</span><span class="status-value">{{ time(report.generated_at) }}</span></div><div class="status-pill"><span class="status-label">显示内容</span><span class="status-value">{{ preview?'未保存预览':'固定历史报告' }}</span></div></div>
   <el-alert v-for="missing in report.missing" :key="missing" :title="missing" type="warning" :closable="false"/>
   <section class="summary-grid"><el-card class="score-card" shadow="never"><div class="score-container"><div class="gauge-chart"><svg viewBox="0 0 200 200" role="img" :aria-label="report.score===null?'总分资料不足':`规则总分 ${report.score}`"><circle cx="100" cy="100" r="72" fill="none" stroke="var(--el-border-color)" stroke-width="16"/><circle v-if="report.score!==null" cx="100" cy="100" r="72" fill="none" stroke="#2f7dff" stroke-width="16" :stroke-dasharray="`${Number(report.score)*4.5239} 452.39`" transform="rotate(-90 100 100)"/><text x="100" y="105" text-anchor="middle" fill="currentColor" font-size="30">{{ report.score??'—' }}</text></svg></div><div class="score-details"><div class="grade-badge">{{ report.grade??'资料不足' }}</div><p>当前持仓 {{ report.position_count }} 项</p><p>持仓市值 {{ money(report.total_value) }} {{ report.currency }}</p><p>产品规则评分，不是收益预测。</p></div></div></el-card><el-card shadow="never"><h3>最近两次固定诊断比较</h3><template v-if="comparison"><p v-if="!comparison.policy_comparable">政策或公式不同，不比较评分。</p><p>评分变化 {{ comparison.score_delta??'不可比较' }}</p><p>持仓市值变化 {{ money(comparison.total_value_delta) }} {{ report.currency }}（不等于投资收益）</p><p v-for="(delta,key) in comparison.dimension_deltas" :key="key">{{ dimensionNames[key] }}：{{ delta??'不可比较' }}</p></template><p v-else>保存两次相同诊断范围的报告后显示比较。</p></el-card></section>
   <el-row :gutter="20" class="dimension-grid"><el-col v-for="(dim,key) in report.dimensions" :key="key" :xs="24" :sm="12" :lg="6"><el-card class="dimension-card" shadow="hover"><template #header><div class="card-header"><span>{{ dim.name }}</span><span class="dim-score">{{ dim.score??'—' }}</span></div></template><el-progress v-if="dim.score!==null" :percentage="Number(dim.score)" :show-text="false" :stroke-width="12"/><p v-else>依据不足，不计算此维度。</p></el-card></el-col></el-row>
   <el-card shadow="never"><h3>持仓情景冲击与纪律信号</h3><p>分别假设单个持仓变化，不代表同时发生或实际成交。</p><el-table :data="report.impacts"><el-table-column prop="symbol" label="标的" min-width="100"/><el-table-column label="持仓占比 %" min-width="130"><template #default="{row}">{{ money(row.position_percent) }}</template></el-table-column><el-table-column prop="scenario_move_percent" label="假设变化 %" min-width="130"/><el-table-column label="情景损益" min-width="140"><template #default="{row}">{{ money(row.scenario_pnl) }} {{ report.currency }}</template></el-table-column><el-table-column label="变化后占比 %" min-width="140"><template #default="{row}">{{ money(row.projected_position_percent) }}</template></el-table-column></el-table><article v-for="impact in report.impacts" :key="impact.symbol"><p v-for="(breach,i) in impact.breaches" :key="i">{{ impact.symbol }} · {{ breach.severity==='critical'?'严重':'观察' }} · {{ breach.name||breachNames[breach.code] }} {{ breach.current??'' }} {{ breach.limit?' / 阈值 '+breach.limit:'' }}</p></article><p v-for="alert in report.position_size_alerts" :key="alert">{{ alert }}</p></el-card>
  </template>
  <el-card v-if="account" class="schedule-panel" shadow="never"><h3>定时事实日报</h3><p>按指定时区和星期保存当时资料。服务须保持运行；节假日不会自动排除，不联网获取收盘价或调用模型。</p><p>当前状态：{{ schedule?.config.enabled?'已启用':'未启用' }}</p><p>下次执行：{{ schedule?.next_due?time(schedule.next_due):'—' }}（按浏览器本地时间显示）</p><p v-if="schedule?.retry_at">下次重试：{{ time(schedule.retry_at) }}</p><el-form label-position="top"><el-form-item label="定时时区"><el-input v-model="scheduleForm.timezone" :disabled="busy" placeholder="例如 Asia/Shanghai"/></el-form-item><el-form-item label="当地执行时间"><el-input v-model="scheduleForm.time" type="time" :disabled="busy"/></el-form-item><el-form-item label="执行星期"><el-checkbox-group v-model="scheduleForm.weekdays" :disabled="busy"><el-checkbox v-for="(day,index) in weekdays" :key="index" :value="index">{{ day }}</el-checkbox></el-checkbox-group></el-form-item></el-form><p>启用或更新时使用本次诊断预览的政策及持仓资料；以后资料过期会如实显示缺失，不自动补成完整评分。</p><el-button :disabled="busy||!preview" @click="saveSchedule(true)">按本次预览启用定时</el-button><el-button :disabled="busy||!schedule?.config.enabled" @click="saveSchedule(false)">停用定时</el-button><p v-if="!preview">先运行上方诊断预览，再启用或更新定时设置。</p><h4>最近运行记录</h4><p v-if="!scheduleRuns.length">尚无定时运行记录。</p><article v-for="r in scheduleRuns.slice(0,10)" :key="r.id"><p>{{ time(r.observed_at) }} · {{ runNames[r.status]||r.status }} · 第 {{ r.attempt }} 次尝试</p><p v-if="r.data_status">资料：{{ statusNames[r.data_status] }}</p><p v-if="r.status==='failed'">本次未生成日报。最多自动尝试三次；也可重新预览后主动生成当次日报。</p><p v-if="r.status==='missed'">超过六小时，已跳过，不补造历史快照。</p></article></el-card>
  <el-card class="daily-panel" shadow="never"><h3>组合事实日报</h3><p>先运行诊断预览，再主动生成日报。固定生成当时的账本与价格依据，不是交易所收盘价；不会调用模型或产生交易。</p><p v-if="!dailyBriefs.length">尚无日报。</p><article v-for="brief in dailyBriefs" :key="brief.id" :id="'daily-'+brief.id" class="daily-entry" :class="{'linked-daily':route.query.id===brief.id}"><h4>{{ time(brief.captured_at) }} · {{ statusNames[brief.facts.status] }}</h4><p>持仓 {{ brief.facts.position_count }} 项 · 持仓市值 {{ money(brief.facts.position_value) }} {{ brief.currency }}</p><p>规则评分 {{ brief.facts.score??'资料不足' }} · {{ brief.facts.grade??'未评级' }}</p><p v-for="reason in brief.facts.missing" :key="reason">{{ reason }}</p><details><summary>查看固定账本与价格快照</summary><pre>{{ JSON.stringify(dailySnapshots.find(s=>s.id===brief.snapshot_id),null,2) }}</pre></details><el-button :disabled="busy||!!preview" @click="selected=reports.find(r=>r.id===brief.diagnosis_id)||null">查看关联诊断</el-button><el-button :disabled="busy" @click="aiBrief=brief">可选 AI 日报汇总</el-button><el-button :disabled="busy" @click="feedbackTarget={id:brief.id,symbol:'',label:'固定日报'}">评价此日报</el-button></article></el-card>
  <InsightFeedback v-if="feedbackTarget" ref="feedbackPanel" :target-id="feedbackTarget.id" :target-symbol="feedbackTarget.symbol" :label="feedbackTarget.label" @close="feedbackTarget=null"/>
  <DailyAssistant v-if="aiBrief" ref="aiAssistant" :brief="aiBrief" :account-id="accountId" @close="aiBrief=null"/>
  <section v-if="!preview&&(selected||reports[0])"><el-button :disabled="busy" @click="feedbackTarget={id:(selected||reports[0]).id,symbol:'',label:'固定诊断'}">评价此诊断</el-button><el-button v-for="impact in report?.intelligence?.top_impacts" :key="impact.symbol" :disabled="busy" @click="feedbackTarget={id:(selected||reports[0]).id,symbol:impact.symbol,label:impact.symbol+' 固定持仓影响'}">评价 {{ impact.symbol }} 持仓影响</el-button></section>
  <SnapshotHistory :snapshots="dailySnapshots" :disabled="busy||!!preview" @select="openSnapshot"/>
  <DiagnosisHistory :reports="reports" :disabled="busy||!!preview" @select="id=>selected=reports.find(r=>r.id===id)||null"/>
  <el-card class="history-panel" shadow="never"><h3>固定诊断历史</h3><p v-if="!reports.length">尚无已保存报告。</p><el-button v-for="r in reports" :key="r.id" :disabled="busy||!!preview" @click="selected=r">{{ time(r.report.generated_at) }} · {{ r.report.score??'资料不足' }}</el-button><details v-if="report"><summary>查看当时政策与资料来源</summary><pre>{{ JSON.stringify({constitution:report.constitution_evidence,policy:report.policy,holding_context:report.holding_context},null,2) }}</pre><h4>当时的价格依据（不是当前行情）</h4><article v-for="p in report.account_evidence.positions" :key="p.symbol" class="price-evidence"><strong>{{ p.symbol }}</strong><template v-if="p.quote"><p>{{ p.quote.price }} {{ p.quote.currency }} · {{ p.quote.as_of }} · v{{ p.quote.revision }}</p><p>{{ p.quote.source }}</p><p>当时状态：{{ priceNames[p.quote_status] }}</p></template><details v-if="p.components"><summary>查看各账户原币价格、成本和汇率版本</summary><pre>{{ JSON.stringify(p.components,null,2) }}</pre></details><p v-else-if="!p.quote">当时缺少价格快照</p></article></details></el-card>
 </div>
</template>
<script setup lang="ts">
import {registerPageMaterial} from '@/api/pageMaterial'
import Constitution from './Constitution.vue'
import SnapshotHistory from './SnapshotHistory.vue'
import DiagnosisIntelligence from './DiagnosisIntelligence.vue'
import InsightFeedback from './InsightFeedback.vue'
import DailyAssistant from './DailyAssistant.vue'
import DiagnosisHistory from './DiagnosisHistory.vue'
import {ref,reactive,computed,watch,onBeforeUnmount,nextTick} from 'vue'
import {useRouter,useRoute,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElProgress,ElMessageBox,ElCheckbox,ElCheckboxGroup} from 'element-plus'
import AppDataState from '@/components/Global/AppDataState.vue'
import {getWorkspace,operationCache,type Workspace} from '@/api/business'
import {useBusinessStore} from '@/stores/business'
import {request} from '@/api/owner'
import {money} from '@/utils/decimal'
type Policy={warning_percent:string;max_percent:string;shock_percent:string;custom_rules:{name:string;metric:string;operator:string;threshold:string;severity:string}[]}
type Context={company:string;news:string;source:string;as_of:string;source_evidence?:unknown}
type Input={constitution_revision?:number;account_id:string;policy:Policy;holding_context:Record<string,Context>}
type DiagnosticAccount=Omit<Workspace['accounts'][number],'positions'> & {positions:(Workspace['accounts'][number]['positions'][number] & {components?:unknown[]})[]}
type Report={constitution_evidence?:unknown;intelligence?:InstanceType<typeof DiagnosisIntelligence>['$props']['brain'];account_id:string;formula:string;account_evidence:DiagnosticAccount;status:string;generated_at:string;score:string|null;grade:string|null;position_count:number;total_value:string|null;currency:string;missing:string[];dimensions:Record<string,{name:string;score:string|null}>;impacts:{symbol:string;position_percent:string;scenario_move_percent:string;scenario_pnl:string;projected_position_percent:string|null;breaches:{severity:string;code:string;name?:string;current?:string;limit?:string}[]}[];position_size_alerts?:string[];policy:Policy;holding_context:Record<string,Context>}
type Saved={id:string;input:Input;report:Report}
type Schedule={revision:number;config:{enabled:boolean;timezone:string;time:string;weekdays:number[];input:Input};next_due:string|null;retry_at:string|null}
const schedule=ref<Schedule|null>(null),scheduleRuns=ref<{id:string;observed_at:string;attempt:number;status:string;data_status:string|null}[]>([]),scheduleForm=reactive({timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC',time:'16:30',weekdays:[0,1,2,3,4]})
const weekdays=['周一','周二','周三','周四','周五','周六','周日'],runNames:Record<string,string>={completed:'已完成',failed:'失败',missed:'错过执行时间'}
const feedbackTarget=ref<{id:string;symbol:string;label:string}|null>(null),feedbackPanel=ref<InstanceType<typeof InsightFeedback>|null>(null)
const aiBrief=ref<DailyBrief|null>(null),aiAssistant=ref<InstanceType<typeof DailyAssistant>|null>(null)
type DailyBrief={id:string;kind:'daily_brief';captured_at:string;snapshot_id:string;diagnosis_id:string;currency:string;facts:{position_count:number;position_value:string|null;score:string|null;grade:string|null;status:string;missing:string[]}}
const sourceProposal=ref<{symbol:string;context:Context|null;notice:string}|null>(null)
const dailyBriefs=ref<DailyBrief[]>([]),dailySnapshots=ref<{id:string;kind:string;[key:string]:unknown}[]>([])
type Comparison={policy_comparable:boolean;score_delta:string|null;total_value_delta:string|null;dimension_deltas:Record<string,string|null>}
const route=useRoute(),businessStore=useBusinessStore()
const router=useRouter(),workspace=ref<Workspace|null>(null),accountId=ref(''),busy=ref(false),error=ref(''),reports=ref<Saved[]>([]),selected=ref<Saved|null>(null),comparison=ref<Comparison|null>(null),preview=ref<{report:Report;token:string}|null>(null),policy=reactive<Policy>({warning_percent:'20',max_percent:'30',shock_percent:'10',custom_rules:[]}),contexts=reactive<Record<string,Context>>({}),ops=operationCache()
const policyFields=[{key:'warning_percent',label:'观察持仓占比 %'},{key:'max_percent',label:'最大持仓占比 %'},{key:'shock_percent',label:'假设单股下跌幅度 %'}] as const
const operators={gt:'大于',gte:'大于或等于',lt:'小于',lte:'小于或等于'},newsNames={unavailable:'未核对',neutral:'中性观察',positive:'正面观察',negative:'负面观察'},priceNames={missing:'缺失',stale:'过期',current_snapshot:'有效快照'},statusNames:Record<string,string>={complete:'资料齐全',partial:'资料不完整',unavailable:'不可用'},dimensionNames:Record<string,string>={concentration:'集中度',profitability:'浮盈持仓比例',diversification:'分散度',position_size:'仓位大小',discipline:'纪律信号'},breachNames:Record<string,string>={position_weight:'持仓超过阈值',negative_news_on_large_position:'较大持仓有负面观察',custom_rule:'自定义纪律'}
const portfolioScope=ref<DiagnosticAccount|null>(null)
const account=computed(()=>accountId.value==='portfolio:all'?portfolioScope.value:workspace.value?.accounts.find(a=>a.id===accountId.value)),report=computed(()=>preview.value?.report||selected.value?.report||reports.value[0]?.report||null)
let baseline='',input:Input|null=null,saveId='',alive=true
const constitutionPanel=ref<InstanceType<typeof Constitution>|null>(null),constitutionRevision=ref<number|null>(null)
function useConstitution(v:{revision:number;config:{policy:Policy}}){Object.assign(policy,JSON.parse(JSON.stringify(v.config.policy)));constitutionRevision.value=v.revision;preview.value=null;input=null}
watch(policy,()=>{constitutionRevision.value=null},{deep:true,flush:'sync'})
const fingerprint=()=>JSON.stringify([policy,contexts,scheduleForm,constitutionRevision.value]),dirty=computed(()=>fingerprint()!==baseline||!!preview.value)
const time=(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})
watch([policy,contexts],()=>{preview.value=null;input=null;ops.clear();saveId=''},{deep:true,flush:'sync'})
async function loadSources(symbol:string){if(busy.value)return;busy.value=true;error.value='';sourceProposal.value=null;try{sourceProposal.value=await request('/api/v1/owner/diagnosis-sources','POST',{account_id:accountId.value,symbol})}catch(e){error.value=e instanceof Error?e.message:'来源读取失败'}finally{busy.value=false}}
function adoptSources(symbol:string){if(sourceProposal.value?.symbol===symbol&&sourceProposal.value.context){contexts[symbol]=JSON.parse(JSON.stringify(sourceProposal.value.context));sourceProposal.value=null}}
function manualContext(symbol:string){const old=contexts[symbol];contexts[symbol]={company:old.company,news:'unavailable',source:'',as_of:new Date().toISOString().slice(0,10)};sourceProposal.value=null}
function addRule(){policy.custom_rules.push({name:'',metric:'position_percent',operator:'gt',threshold:'30',severity:'watch'})}
async function discard(){if(busy.value)return false;if(constitutionPanel.value&&!await constitutionPanel.value.leave())return false;if(feedbackPanel.value&&!await feedbackPanel.value.close())return false;if(aiAssistant.value&&!await aiAssistant.value.close())return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的诊断依据和预览？','离开编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function load(){sourceProposal.value=null;portfolioScope.value=null;busy.value=true;error.value='';try{const w=await getWorkspace();if(!alive)return false;workspace.value=w;const linked=w.daily_index.find(r=>r.id===route.query.id);if(linked&&!accountId.value&&typeof linked.account_id==='string')accountId.value=linked.account_id;if(!accountId.value)accountId.value=w.accounts[0]?.id||'';if(accountId.value==='portfolio:all')portfolioScope.value=await request<DiagnosticAccount>('/api/v1/owner/diagnosis-scope','POST',{account_id:accountId.value});if(!alive)return false;const h=accountId.value?await request<{reports:Saved[];comparison:Comparison|null}>('/api/v1/owner/diagnosis-history','POST',{account_id:accountId.value}):{reports:[],comparison:null};if(!alive)return false;const daily=accountId.value?await request<{records:({id:string;kind:string;[key:string]:unknown})[]}>('/api/v1/owner/daily-history','POST',{account_id:accountId.value}):{records:[]};if(!alive)return false;const scheduled=accountId.value?await request<{schedule:Schedule|null;runs:typeof scheduleRuns.value}>('/api/v1/owner/daily-schedule-status','POST',{account_id:accountId.value}):{schedule:null,runs:[]};if(!alive)return false;schedule.value=scheduled.schedule;scheduleRuns.value=scheduled.runs;Object.assign(scheduleForm,scheduled.schedule?{timezone:scheduled.schedule.config.timezone,time:scheduled.schedule.config.time,weekdays:[...scheduled.schedule.config.weekdays]}:{timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC',time:'16:30',weekdays:[0,1,2,3,4]});dailyBriefs.value=daily.records.filter(r=>r.kind==='daily_brief') as unknown as DailyBrief[];dailySnapshots.value=daily.records.filter(r=>r.kind==='daily_snapshot');reports.value=h.reports;comparison.value=h.comparison;selected.value=null;preview.value=null;Object.assign(policy,h.reports[0]?.input.policy||{warning_percent:'20',max_percent:'30',shock_percent:'10',custom_rules:[]});policy.custom_rules=JSON.parse(JSON.stringify(policy.custom_rules));constitutionRevision.value=h.reports[0]?.input.constitution_revision??null;for(const key of Object.keys(contexts))delete contexts[key];for(const p of account.value?.positions||[])contexts[p.symbol]={...(h.reports[0]?.input.holding_context[p.symbol]||{company:'',news:'unavailable',source:'',as_of:new Date().toISOString().slice(0,10)})};baseline=fingerprint();await nextTick();if(linked)document.getElementById('daily-'+linked.id)?.scrollIntoView({block:'center'});await businessStore.load();return true}catch(e){workspace.value=null;portfolioScope.value=null;reports.value=[];comparison.value=null;dailyBriefs.value=[];dailySnapshots.value=[];schedule.value=null;scheduleRuns.value=[];selected.value=null;preview.value=null;input=null;error.value=e instanceof Error?e.message:'读取失败';return false}finally{busy.value=false}}
function openSnapshot(id:string){const brief=dailyBriefs.value.find(b=>b.snapshot_id===id);if(brief)router.push({path:'/review/diagnosis',query:{id:brief.id}})}
async function refresh(){if(await discard())await load()}
async function switchAccount(value:string){if(value!==accountId.value&&await discard()){accountId.value=value;preview.value=null;selected.value=null;reports.value=[];comparison.value=null;await load()}}
async function run(){if(busy.value)return;busy.value=true;error.value='';preview.value=null;saveId='';ops.clear();try{const completeContexts:Record<string,Context>={};for(const [sy,c] of Object.entries(contexts)){if(c.company.trim()&&c.source.trim()&&c.as_of)completeContexts[sy]={...c,company:c.company.trim(),source:c.source.trim()};else if(c.company.trim()||c.source.trim()||c.news!=='unavailable')throw Error(`${sy} 请补齐公司归属、资料来源和日期，或清空公司与来源以保留未知。`)}const candidate:Input={...(constitutionRevision.value?{constitution_revision:constitutionRevision.value}:{}),account_id:accountId.value,policy:JSON.parse(JSON.stringify(policy)),holding_context:completeContexts};const result=await request<{report:Report;token:string}>('/api/v1/owner/diagnosis-preview','POST',candidate);if(alive){input=candidate;preview.value=result}}catch(e){error.value=e instanceof Error?e.message:'诊断失败'}finally{busy.value=false}}
async function save(){if(busy.value||!preview.value||!input)return;busy.value=true;error.value='';saveId ||= crypto.randomUUID();try{await request('/api/v1/owner/diagnosis','POST',ops.body('save',{id:saveId,input,expected_token:preview.value.token}));ops.clear();saveId='';preview.value=null;input=null;if(!await load())error.value='诊断已保存，但重新读取失败。请刷新确认，避免重复保存。'}catch(e){error.value=e instanceof Error?e.message:'保存失败，预览已保留'}finally{busy.value=false}}
async function captureDaily(){if(busy.value||!preview.value||!input)return;busy.value=true;error.value='';try{await request('/api/v1/owner/daily-capture','POST',ops.body('daily',{input,expected_token:preview.value.token}));ops.clear();preview.value=null;input=null;if(!await load())error.value='日报已保存，但重新读取失败。请刷新确认，避免重复保存。'}catch(e){error.value=e instanceof Error?e.message:'日报保存失败，预览已保留，可重试'}finally{busy.value=false}}
async function saveSchedule(enabled:boolean){if(busy.value||enabled&&(!preview.value||!input)||!enabled&&!schedule.value)return;if(!enabled&&!await discard())return;busy.value=true;error.value='';try{const config=enabled?{enabled,...scheduleForm,weekdays:[...scheduleForm.weekdays],input}: {...schedule.value!.config,enabled:false};await request('/api/v1/owner/daily-schedule','POST',ops.body('schedule',{revision:schedule.value?.revision||0,config}));ops.clear();preview.value=null;input=null;schedule.value=null;if(!await load())error.value='定时配置已保存，但重新读取失败。请刷新确认，避免重复保存。'}catch(e){error.value=e instanceof Error?e.message:'定时配置保存失败，编辑已保留'}finally{busy.value=false}}
onBeforeRouteUpdate(discard);watch(()=>route.query.id,()=>{if(alive){accountId.value='';load()}});
const unregisterMaterial=registerPageMaterial('/review/diagnosis',()=>{if(busy.value||!report.value)throw Error('请先完成诊断预览或选择一份历史诊断');return {account_id:report.value.account_id,report_kind:preview.value?'unsaved_preview':'fixed_report',report_id:preview.value?null:(selected.value||reports.value[0])?.id,report:report.value}});onBeforeUnmount(unregisterMaterial);
onBeforeRouteLeave(discard);const unload=(e:BeforeUnloadEvent)=>{if(busy.value||dirty.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>{alive=false;window.removeEventListener('beforeunload',unload)});baseline=fingerprint();load()
</script>

<style scoped>
.schedule-panel{margin:20px 0}.schedule-panel .el-checkbox-group{display:flex;flex-wrap:wrap}.schedule-panel .el-button{margin:4px 4px 4px 0}
.linked-daily{outline:2px solid var(--el-color-primary);outline-offset:4px}
.daily-panel{margin:20px 0}.daily-entry{padding:16px 0;border-top:1px solid var(--el-border-color)}.daily-entry pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:340px;overflow:auto}

.diagnosis-page {
  padding: 24px;
}

.diagnosis-brain {
  margin: 16px 0 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-info .title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-info .subtitle {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  display: block;
}

.truth-note {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.status-pill {
  min-width: 180px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 16px;
  background: var(--el-bg-color-overlay);
}

.status-label {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status-value {
  display: block;
  margin-top: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.summary-grid,
.chart-grid,
.content-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 24px;
}

.summary-grid,
.content-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.score-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
}

.gauge-chart {
  width: 240px;
  height: 160px;
}

.score-details {
  margin-left: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.grade-badge {
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 4px;
}

.interpretation {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
}

.summary-info {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.card-head,
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-title,
.history-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.card-subtitle,
.history-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.automation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.automation-item {
  padding: 14px;
  border-radius: 16px;
  background: var(--el-fill-color-light);
}

.automation-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.automation-value {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.comparison-summary {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid var(--el-border-color);
}

.comparison-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.comparison-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.comparison-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--el-fill-color-light);
  font-size: 12px;
  font-weight: 600;
}

.comparison-list {
  margin-top: 14px;
}

.comparison-list-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
}

.comparison-list-item {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 6px;
}

.comparison-list-item.is-added {
  color: #f56c6c;
}

.comparison-list-item.is-removed {
  color: #67c23a;
}

.history-chart {
  width: 100%;
  height: 280px;
}

.grade-a,
.delta-positive {
  color: #67c23a;
}

.grade-b {
  color: #409eff;
}

.grade-c {
  color: #e6a23c;
}

.grade-df,
.delta-negative {
  color: #f56c6c;
}

.delta-neutral {
  color: var(--el-text-color-secondary);
}

.dimension-grid {
  margin-bottom: 24px;
}

.dimension-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}

.dim-score {
  color: #409eff;
}

.dim-detail {
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.dim-alerts {
  margin-top: 12px;
  border-top: 1px solid #f5f7fa;
  padding-top: 12px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  font-size: 12px;
  color: #e6a23c;
  margin-bottom: 6px;
  line-height: 1.4;
}

.warning-icon {
  margin-right: 4px;
  margin-top: 2px;
  font-size: 14px;
}

.brief-card,
.score-card,
.automation-card,
.history-card {
  border-radius: 20px;
}

.daily-report-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.36fr);
  gap: 16px;
  align-items: stretch;
}

.daily-brief-main {
  min-width: 0;
}

.daily-brief-basis-warning {
  margin-bottom: 12px;
}

.daily-brief-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 9px;
  color: #7b8da4;
  font-size: 11px;
}

.daily-brief {
  margin: 0;
  min-height: 260px;
  padding: 16px;
  border: 1px solid rgba(226, 233, 243, 0.92);
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.7;
  color: var(--el-text-color-primary);
}

.brief-feedback {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  color: var(--el-text-color-regular);
  font-size: 12px;
}

.brief-feedback small {
  margin-left: auto;
  color: var(--el-text-color-secondary);
}

.daily-report-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.daily-report-history-title {
  font-size: 12px;
  font-weight: 700;
  color: #6f8299;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.daily-report-item {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(226, 233, 243, 0.96);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.daily-report-item:hover,
.daily-report-item.active {
  border-color: rgba(64, 158, 255, 0.36);
  background: rgba(239, 247, 255, 0.96);
  transform: translateY(-1px);
}

.daily-report-item.historical {
  opacity: 0.72;
}

.daily-report-item span,
.daily-report-item b,
.daily-report-item em,
.daily-report-item small {
  display: block;
}

.daily-report-item span {
  color: #7a8aa0;
  font-size: 12px;
}

.daily-report-item b {
  margin-top: 4px;
  color: #102344;
  font-size: 14px;
}

.daily-report-item em {
  width: fit-content;
  margin-top: 5px;
  padding: 1px 5px;
  border-radius: 4px;
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  font-size: 10px;
  font-style: normal;
}

.daily-report-item small {
  margin-top: 6px;
  color: #6b7d94;
  font-size: 12px;
  line-height: 1.45;
}

.alerts-panel {
  background: #fff;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #ebeef5;
}

.panel-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.top-alert-item {
  margin-bottom: 12px;
}

.top-alert-item:last-child {
  margin-bottom: 0;
}

@media (max-width: 1200px) {
  .summary-grid,
  .chart-grid,
  .content-grid,
  .daily-report-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions :deep(.el-button) {
    flex: 1;
  }

  .score-container {
    flex-direction: column;
    align-items: flex-start;
    min-height: auto;
  }

  .score-details {
    margin-left: 0;
    margin-top: 12px;
  }

  .automation-grid {
    grid-template-columns: 1fr;
  }
}

.policy-card,.history-panel{margin:20px 0}.policy-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));gap:16px}fieldset{min-width:0;border:1px solid var(--el-border-color);border-radius:8px;padding:16px;margin:16px 0}legend{color:var(--el-text-color-secondary)}.gauge-chart svg{width:100%;height:100%;color:var(--el-text-color-primary)}pre{white-space:pre-wrap;overflow-wrap:anywhere}.history-panel .el-button{max-width:100%;white-space:normal;margin:6px 0;height:auto;padding:10px}.status-strip{flex-wrap:wrap}
</style>

<style scoped>.saved-source-proposal{margin:12px 0;padding:12px;border:1px solid #29415e;border-radius:12px}.saved-source-proposal pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}</style>
