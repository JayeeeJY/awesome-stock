<template>
<section class="portfolio-brain" aria-label="组合大脑"><header class="brain-header"><div><div class="brain-kicker"><span class="brain-pulse"></span>PORTFOLIO BRAIN</div><h3>组合大脑</h3><p>依据当前显示的诊断报告，按仓位与纪律命中排序；历史报告保持当时证据。</p></div></header>
<p v-if="!brain">这份历史报告没有组合影响摘要，重新预览可计算；原记录不会改写。</p>
<template v-else><p v-if="brain.status!=='complete'">资料未齐全，已知信号不代表全部风险。</p><div class="brain-metrics"><article><span>持仓数量</span><b>{{ brain.position_count }}</b><small>已计算 {{ brain.coverage_count }} 项</small></article><article><span>高影响持仓</span><b class="is-danger">{{ brain.high_impact_count??'—' }}</b><small>规则风险分级</small></article><article><span>仓位上限</span><b>{{ maximum }}%</b><small>持仓市值占比</small></article><article><span>纪律命中</span><b>{{ brain.rule_breach_count??'—' }}</b><small>缺失不补为零</small></article></div>
<div class="brain-body single-column"><div class="brain-block"><div class="block-head"><div><b>优先组合影响</b><span>最多显示前10项</span></div></div><p v-if="!brain.top_impacts.length">缺少可用影响计算，请先补齐价格与依据。</p><details v-for="impact in brain.top_impacts" :key="impact.symbol" class="impact-detail"><summary class="impact-row"><span class="risk-rail" :class="`is-${impact.risk_level}`"></span><span class="impact-main"><span class="impact-title-row"><b>{{ impact.symbol }}</b><em :class="`is-${impact.risk_level}`">{{ levels[impact.risk_level] }}</em></span><span class="impact-headline">占比 {{ money(impact.position_percent) }}% · 风险分 {{ impact.risk_score }}</span><span class="impact-action">展开复核依据 →</span></span><span class="impact-scenario"><small>压力损益</small><b>{{ money(impact.scenario_pnl) }}</b><em>{{ currency }}</em></span></summary><div class="impact-evidence"><p v-for="action in impact.review_actions" :key="action">{{ actions[action] }}</p><p>纪律命中 {{ impact.breaches.length }} 条；情景损益不是已发生收益。</p><p>事实指纹：{{ impact.fact_hash }}</p></div></details></div></div></template>
</section>
</template>
<script setup lang="ts">
import {money} from '@/utils/decimal'
defineProps<{brain?:{status:string;position_count:number;coverage_count:number;high_impact_count:number|null;rule_breach_count:number|null;top_impacts:{symbol:string;risk_level:string;risk_score:number;position_percent:string;scenario_pnl:string;review_actions:string[];breaches:unknown[];fact_hash:string}[]};maximum:string;currency:string}>()
const levels:Record<string,string>={low:'低',watch:'观察',high:'高',critical:'严重'},actions:Record<string,string>={review_position_size:'复核持仓规模与既定纪律',maintain_and_monitor:'持续核对资料与持仓变化',complete_evidence:'先补齐缺失证据再评估完整风险'}
</script>
<style scoped>

.portfolio-brain { border: 1px solid rgba(67, 179, 255, .2); border-radius: 18px; padding: 18px; background: linear-gradient(135deg, rgba(11, 35, 65, .86), rgba(8, 25, 47, .94)); box-shadow: 0 18px 50px rgba(3, 15, 31, .22); color: #dcecff; }
.brain-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.brain-kicker { display: flex; align-items: center; gap: 8px; color: #67d4ff; font: 700 11px/1.2 "JetBrains Mono", monospace; letter-spacing: .15em; }
.brain-pulse { width: 7px; height: 7px; border-radius: 50%; background: #31e7c1; box-shadow: 0 0 14px #31e7c1; }
.brain-header h3 { margin: 7px 0 3px; font-size: 21px; color: #f4f9ff; }
.brain-header p, .block-head span { margin: 0; color: #8199b7; font-size: 12px; }
.brain-actions { display: flex; gap: 8px; }
.brain-data-state { margin-bottom: 12px; }
.brain-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
.brain-metrics article { display: grid; gap: 3px; padding: 11px 12px; border: 1px solid rgba(105, 178, 236, .14); border-radius: 11px; background: rgba(126, 178, 230, .055); }
.brain-metrics span, .brain-metrics small { color: #7e96b3; font-size: 11px; }
.brain-metrics b { color: #edf7ff; font: 700 22px/1.1 "JetBrains Mono", monospace; }
.brain-metrics b.is-warning { color: #ffbd5b; } .brain-metrics b.is-danger { color: #ff6e7f; }
.brain-body { display: grid; grid-template-columns: 1.15fr .85fr; gap: 10px; }
.brain-body.single-column { grid-template-columns: 1fr; }
.brain-block { min-width: 0; overflow: hidden; border: 1px solid rgba(96, 163, 218, .14); border-radius: 12px; background: rgba(3, 19, 37, .42); }
.block-head { padding: 11px 12px; border-bottom: 1px solid rgba(96, 163, 218, .12); }
.block-head > div { display: flex; align-items: baseline; gap: 9px; } .block-head b { font-size: 13px; color: #eaf5ff; }
.impact-row, .coverage-row { width: 100%; border: 0; border-bottom: 1px solid rgba(92, 152, 203, .11); color: inherit; background: transparent; cursor: pointer; text-align: left; }
.impact-row:last-child, .coverage-row:last-child { border-bottom: 0; }
.impact-row { display: grid; grid-template-columns: 3px 1fr auto; gap: 11px; padding: 10px 12px 10px 0; }
.impact-row:hover, .coverage-row:hover { background: rgba(62, 155, 227, .08); }
.risk-rail { border-radius: 0 4px 4px 0; background: #42d7b0; }.risk-rail.is-watch { background: #ffbd5b; }.risk-rail.is-high,.risk-rail.is-critical { background: #ff6076; }
.impact-main { display: grid; gap: 4px; min-width: 0; }.impact-title-row { display: flex; align-items: center; gap: 7px; }.impact-title-row b { color: #f1f7ff; font-family: "JetBrains Mono", monospace; }.impact-title-row em { padding: 1px 5px; border-radius: 4px; color: #41d9b2; background: rgba(65, 217, 178, .11); font-size: 10px; font-style: normal; }.impact-title-row em.is-watch { color: #ffbd5b; }.impact-title-row em.is-high,.impact-title-row em.is-critical { color: #ff7587; }.impact-title-row small { color: #8ea6c2; }
.impact-headline { overflow: hidden; color: #9cafc7; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.impact-action { color: #53c8ff; font-size: 11px; }.impact-scenario { display: grid; align-content: center; justify-items: end; gap: 2px; min-width: 92px; }.impact-scenario small,.impact-scenario em { color: #728ba9; font-size: 10px; font-style: normal; }.impact-scenario b { color: #ff7183; font: 700 13px "JetBrains Mono", monospace; }
.coverage-row { display: grid; grid-template-columns: 60px 1fr auto auto; align-items: center; gap: 8px; padding: 10px 12px; }.coverage-symbol { color: #63cfff; font: 700 12px "JetBrains Mono", monospace; }.coverage-copy { display: grid; gap: 2px; min-width: 0; }.coverage-copy b { color: #eaf4ff; font-size: 12px; }.coverage-copy small { overflow: hidden; color: #7189a6; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }.coverage-weight { color: #8fa7c2; font: 11px "JetBrains Mono", monospace; }.coverage-state { min-width: 44px; padding: 2px 5px; border-radius: 5px; color: #41d7af; background: rgba(65, 215, 175, .1); font-size: 10px; text-align: center; }.coverage-state.needs-review { color: #ffb757; background: rgba(255, 183, 87, .1); }
.constitution-intro { margin-bottom: 16px; color: var(--el-text-color-secondary); line-height: 1.7; }.constitution-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }.constitution-switches { display: grid; gap: 9px; margin-bottom: 18px; }
.is-compact { padding: 14px; }.is-compact .brain-header { margin-bottom: 10px; }.is-compact .brain-header h3 { font-size: 18px; }.is-compact .brain-metrics article { padding: 9px 10px; }.is-compact .brain-metrics b { font-size: 18px; }
@media (max-width: 900px) { .brain-metrics { grid-template-columns: repeat(2, 1fr); }.brain-body { grid-template-columns: 1fr; }.brain-header { flex-direction: column; }.brain-actions { width: 100%; }.constitution-grid { grid-template-columns: 1fr; } }

.portfolio-brain{margin:20px 0}.impact-evidence{padding:0 12px 12px;overflow-wrap:anywhere}.impact-title-row{flex-wrap:wrap}.impact-scenario{min-width:0}.impact-detail{min-width:0}@media(max-width:480px){.impact-row{grid-template-columns:3px minmax(0,1fr)}.impact-scenario{grid-column:2}.brain-metrics b{font-size:18px}}
</style>
