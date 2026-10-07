<template>
 <section class="report-entry" aria-labelledby="report-entry-title">
  <div class="report-entry-copy"><span class="report-entry-kicker">保存本次研究</span><h2 id="report-entry-title">把当前材料保存为可回看的研究报告</h2><p>先预览并核对来源、证据缺口与结论，再由你确认保存。报告会固定当时的材料和日期；仅查看或预览不会调用模型。</p><small>只是浏览研究材料？可以先跳过，不需要现在保存。</small></div>
  <el-button class="report-entry-button" type="primary" size="large" :disabled="!symbol||disabled" @click="open">预览报告 · 查看历史</el-button>
 </section>
 <el-dialog v-model="opened" title="固定研究报告" append-to-body width="min(960px,96vw)" :close-on-click-modal="false" :before-close="close">
  <p>第一步预览当前材料，第二步核对后确认保存。保存的报告按当时日期与材料固定，不随之后的价格变化；这里不会调用模型。</p>
  <el-alert v-if="error" :title="error" type="error" :closable="false"/>
  <div class="report-history-controls"><el-button type="primary" :disabled="busy" @click="prepare">第一步：预览当前报告</el-button><el-select v-model="selected" aria-label="已保存研究报告" :disabled="busy" :placeholder="matching.length?'查看已保存报告':'暂无已保存报告'" @change="showSaved"><el-option v-for="r in matching" :key="r.id" :value="r.id" :label="r.packet.symbol+' · '+r.updated_at"/></el-select></div>
  <section v-if="packet" class="fixed-research-report">
   <el-tag>{{ preview?'保存前预览':'已保存固定报告' }}</el-tag><h2>{{ packet.symbol }} · {{ packet.rule_report?.summary.headline||'历史材料包（未记录规则摘要）' }}</h2><p>评估日期 {{ packet.evaluated_on }}</p><template v-if="packet.rule_report"><p>{{ packet.rule_report.formula }}</p><p>{{ packet.rule_report.summary.detail }}</p><section v-if="packet.rule_report.ai_synthesis" class="fixed-ai-synthesis"><el-tag type="warning">AI 综合 · 未核验</el-tag><p>{{ packet.rule_report.ai_synthesis.provider }} / {{ packet.rule_report.ai_synthesis.model }} · {{ packet.rule_report.ai_synthesis.generated_at }}</p><p>{{ packet.rule_report.ai_synthesis.synthesis.decision_brief }}</p><p>{{ packet.rule_report.ai_synthesis.synthesis.why_now }}</p><p>不确定性：{{ packet.rule_report.ai_synthesis.synthesis.uncertainty }}</p><ul><li v-for="(condition,index) in packet.rule_report.ai_synthesis.synthesis.decision_conditions" :key="index">{{ condition }}</li></ul></section>
   <p v-if="packet.rule_report.concentration_accounts?.length">历史账户口径集中度提示：{{ packet.rule_report.concentration_accounts.join('、') }}；25%为研究提示线，不是个人纪律阈值。</p>
   <p v-if="packet.rule_report.concentration?.triggered">集中度提示：全组合持仓美元市值占比 {{ money(packet.rule_report.concentration.weight_percent) }}%（不含现金）；25%为研究提示线，不是个人纪律阈值。</p>
   <p v-else-if="packet.rule_report.concentration?.status==='not_evaluated'">全组合集中度未评估，请核对持仓问题选择、价格和汇率依据。</p>
   <h3>下一步核对</h3><ol><li v-for="action in packet.rule_report.next_actions" :key="action">{{ action }}</li></ol>
   <h3>证据缺口</h3><ul><li v-for="gap in packet.rule_report.evidence_gaps" :key="gap">{{ gap }}</li></ul><p v-if="!packet.rule_report.evidence_gaps.length">本规则未列出缺口，不等于研究资料完整。</p>
   <NewsEvidence v-if="packet.news_source" :source="packet.news_source"/><MemoryEvidence v-if="packet.research_memory" :memory="packet.research_memory"/><CompanyEvidence v-if="packet.company_source" :source="packet.company_source"/><PositionEvidence v-if="packet.position_intelligence" :evidence="packet.position_intelligence"/><TechnicalEvidencePanel v-if="packet.market_technical" :evidence="packet.market_technical"/><p>有效证据 {{ packet.rule_report.valid_evidence_count }}/{{ packet.rule_report.evidence_count }} · 结论置信度：未评估</p>
   <h3>固定估值参照</h3><p v-for="metric in ['pe','pb']" :key="metric">{{ metric.toUpperCase() }}：{{ packet.rule_report.metrics[metric]?.value??'缺少有效证据' }}</p>
   </template><h3>固定持仓与价格依据</h3><article v-for="a in packet.accounts" :key="a.id"><strong>{{ a.name }} · {{ a.currency }}</strong><p v-for="position in a.positions" :key="position.symbol">{{ position.symbol }} · {{ position.quantity }} 股 · 市值 {{ position.market_value??'缺少有效价格' }}</p></article><p v-if="!packet.accounts.length">未纳入持仓问题，或当时账本无此标的持仓。</p>
   <details><summary>完整固定材料与版本</summary><pre>{{ JSON.stringify(packet,null,2) }}</pre></details>
   <p v-if="!packet.rule_report?.ai_synthesis">本报告未包含 AI 综合；需要先在研究页采用与当前材料一致的综合结果。</p>
   <el-button v-if="preview" type="primary" size="large" :loading="busy" @click="save">第二步：确认保存这份报告</el-button>
  </section>
  <template #footer><el-button :disabled="busy" @click="close()">关闭固定报告</el-button></template>
 </el-dialog>
</template>
<script setup lang="ts">
import {money} from '@/utils/decimal'
import NewsEvidence from './NewsEvidence.vue'
import type {NewsSource} from '@/api/news'
import MemoryEvidence from './MemoryEvidence.vue'
import type {ResearchMemory} from '@/api/researchMemory'
import CompanyEvidence from './CompanyEvidence.vue'
import type {CompanySource} from '@/api/company'
import PositionEvidence from './PositionEvidence.vue'
import type {PositionIntelligence} from '@/api/researchPosition'
import TechnicalEvidencePanel from './TechnicalEvidence.vue'
import type {TechnicalEvidence} from '@/api/researchTechnical'
import {computed,ref} from 'vue'
import {request} from '@/api/owner'
type Packet={news_source?:NewsSource|null;research_memory?:ResearchMemory|null;company_source?:CompanySource|null;position_intelligence?:PositionIntelligence|null;market_technical?:TechnicalEvidence|null;symbol:string;evaluated_on:string;rule_report?:{ai_synthesis?:{provider:string;model:string;generated_at:string;synthesis:{decision_brief:string;why_now:string;uncertainty:string;decision_conditions:string[]}};formula:string;summary:{headline:string;detail:string};concentration_accounts?:string[];concentration?:{triggered:boolean;weight_percent:string|null;status:string};next_actions:string[];evidence_gaps:string[];valid_evidence_count:number;evidence_count:number;metrics:Record<string,{value:string}|null>};accounts:{id:string;name:string;currency:string;positions:{symbol:string;quantity:string;market_value:string|null}[]}[]}
type Saved={id:string;updated_at:string;packet:Packet}
const props=defineProps<{symbol?:string;lenses:string[];disabled?:boolean;aiReceipt?:string}>(),opened=ref(false),busy=ref(false),error=ref(''),reports=ref<Saved[]>([]),selected=ref(''),preview=ref<{packet:Packet;token:string}|null>(null)
let pending:Record<string,unknown>|null=null
const matching=computed(()=>reports.value.filter(r=>r.packet.symbol===props.symbol)),packet=computed(()=>preview.value?.packet||reports.value.find(r=>r.id===selected.value)?.packet)
async function open(){opened.value=true;preview.value=null;pending=null;error.value='';busy.value=true;try{reports.value=(await request<{reports:Saved[]}>('/api/v1/owner/research-reports')).reports;if(!matching.value.some(r=>r.id===selected.value))selected.value=matching.value[0]?.id||''}catch(e){reports.value=[];selected.value='';error.value=e instanceof Error?e.message:'读取失败'}finally{busy.value=false}}
function showSaved(){preview.value=null;pending=null}
async function prepare(){if(busy.value||!props.symbol)return;busy.value=true;error.value='';preview.value=null;pending=null;try{const input={symbol:props.symbol,lenses:[...props.lenses],...(props.aiReceipt?{ai_receipt:props.aiReceipt}:{})};const value=await request<{packet:Packet;token:string}>('/api/v1/owner/research-report-preview','POST',input);preview.value=value;pending={id:crypto.randomUUID(),operation_id:crypto.randomUUID(),input,expected_token:value.token}}catch(e){error.value=e instanceof Error?e.message:'预览失败'}finally{busy.value=false}}
async function save(){if(busy.value||!preview.value||!pending)return;busy.value=true;error.value='';try{const saved=await request<Saved>('/api/v1/owner/research-reports','POST',pending);reports.value=[saved,...reports.value.filter(r=>r.id!==saved.id)];selected.value=saved.id;preview.value=null;pending=null}catch(e){error.value=e instanceof Error?e.message:'保存失败'}finally{busy.value=false}}
function close(done?:()=>void){if(busy.value)return;opened.value=false;done?.()}
</script>
<style scoped>
.report-entry{display:flex;max-width:1540px;margin:12px auto 0;padding:20px 22px;align-items:center;justify-content:space-between;gap:24px;border:1px solid rgba(77,217,255,.36);border-radius:16px;background:linear-gradient(115deg,rgba(18,67,109,.86),rgba(8,35,58,.94));box-shadow:0 12px 32px rgba(0,0,0,.14)}
.report-entry-copy{min-width:0;max-width:820px}.report-entry-kicker{color:#62dfff;font:700 11px "SFMono-Regular",Consolas,monospace;letter-spacing:.12em}.report-entry h2{margin:6px 0 7px;color:#eaf6ff;font-size:20px;line-height:1.35}.report-entry p{margin:0;color:#bbd2e5;font-size:14px;line-height:1.6}.report-entry small{display:block;margin-top:8px;color:#8ba9bf;font-size:12px}.report-entry-button{min-width:220px;min-height:48px;flex:none;border:0;background:linear-gradient(120deg,#386dff,#39c9f1);font-weight:700;white-space:normal}
@media(max-width:760px){.report-entry{padding:18px;align-items:stretch;flex-direction:column;gap:16px}.report-entry h2{font-size:18px}.report-entry-button{order:-1;width:100%;min-width:0}}
.report-history-controls{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.report-history-controls .el-select{min-width:0;flex:1 1 240px}.fixed-research-report{border:1px solid var(--el-border-color);border-radius:12px;padding:18px;overflow-wrap:anywhere}.fixed-research-report pre{max-height:min(60vh,640px);overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}.fixed-research-report h2{font-size:22px}.fixed-research-report p,.fixed-research-report li{line-height:1.7}
</style>
