<template>
 <el-card v-if="points.length" shadow="never" class="history-trend-card">
  <h3>诊断历史趋势</h3><p>最近 7 次已保存诊断。资料不足不画分数；政策或公式变化时断开连线。可选择节点查看固定报告。</p>
  <div class="history-chart-scroll" tabindex="0" aria-label="诊断趋势，可横向滚动">
   <svg viewBox="0 0 640 260" role="img" aria-label="最近七次诊断分数趋势">
    <g v-for="score in [0,25,50,75,100]" :key="score"><line x1="40" x2="620" :y1="y(score)" :y2="y(score)" class="grid-line"/><text x="34" :y="y(score)+4" text-anchor="end">{{ score }}</text></g>
    <g v-for="segment in segments" :key="segment.key"><path :d="segment.area" fill="rgba(64,158,255,0.14)"/><path :d="segment.line" fill="none" stroke="#409EFF" stroke-width="3" class="score-segment"/></g>
    <g v-for="(point,index) in points" :key="point.id"><circle v-if="complete(point)" :cx="x(index)" :cy="y(Number(point.report.score))" r="4" fill="#409EFF" class="score-point" :tabindex="disabled?-1:0" role="button" :aria-label="label(point)" @click="choose(point.id)" @keydown.enter.prevent="choose(point.id)" @keydown.space.prevent="choose(point.id)"><title>{{ label(point) }}</title></circle><text v-else :x="x(index)" y="213" text-anchor="middle">待补</text><text :x="x(index)" y="247" text-anchor="middle">{{ shortDate(point.report.generated_at) }}</text></g>
   </svg>
  </div>
  <details><summary>查看趋势数据与断点原因</summary><ol><li v-for="(point,index) in points" :key="point.id"><el-button link :disabled="disabled" @click="choose(point.id)">{{ label(point) }}</el-button><span v-if="!complete(point)">资料不足，未绘制分数</span><span v-else-if="index&&complete(points[index-1])&&!compatible(points[index-1],point)">政策或公式变化，未连接上一点</span></li></ol></details>
 </el-card>
</template>
<script setup lang="ts">
import {computed} from 'vue'
type Point={id:string;report:{status:string;score:string|null;formula:string;policy:unknown;generated_at:string;account_id:string;currency:string}}
const props=defineProps<{reports:Point[];disabled:boolean}>(),emit=defineEmits<{select:[string]}>()
const points=computed(()=>props.reports.slice(0,7).reverse())
const complete=(p:Point)=>p.report.status==='complete'&&p.report.score!==null
function stable(value:unknown):string{if(Array.isArray(value))return '['+value.map(stable).join(',')+']';if(value&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>JSON.stringify(k)+':'+stable(v)).join(',')+'}';return JSON.stringify(value)}
const compatible=(a:Point,b:Point)=>a.report.account_id===b.report.account_id&&a.report.currency===b.report.currency&&a.report.formula===b.report.formula&&stable(a.report.policy)===stable(b.report.policy)
const x=(index:number)=>points.value.length===1?330:50+index*560/(points.value.length-1),y=(score:number)=>220-score*1.9
const segments=computed(()=>points.value.slice(1).flatMap((p,i)=>{const previous=points.value[i];if(!complete(p)||!complete(previous)||!compatible(previous,p))return [];const a=x(i),b=x(i+1),c=(a+b)/2,ay=y(Number(previous.report.score)),by=y(Number(p.report.score));const curve=`C ${c} ${ay}, ${c} ${by}, ${b} ${by}`;return [{key:p.id,line:`M ${a} ${ay} ${curve}`,area:`M ${a} 220 L ${a} ${ay} ${curve} L ${b} 220 Z`}]}))
const label=(p:Point)=>`${new Date(p.report.generated_at).toLocaleString('zh-CN',{hour12:false})} · ${p.report.score??'资料不足'}`
const shortDate=(value:string)=>new Date(value).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})
function choose(id:string){if(!props.disabled)emit('select',id)}
</script>
<style scoped>
.history-trend-card{margin:20px 0}.history-chart-scroll{overflow-x:auto;max-width:100%}svg{width:100%;height:260px;min-width:380px;display:block}svg text{fill:var(--el-text-color-secondary);font-size:11px}.grid-line{stroke:var(--el-border-color)}.score-point{cursor:pointer}.score-point:focus{outline:2px solid var(--el-color-primary);outline-offset:4px}p,li{font-size:12px;overflow-wrap:anywhere}li{margin:8px 0}summary{cursor:pointer}.el-button{white-space:normal;height:auto}
</style>
