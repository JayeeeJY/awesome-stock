<template>
 <el-card shadow="never" class="snapshot-history history-card">
  <template #header><div class="history-header"><div><div class="history-title">持仓市值快照趋势</div><div class="history-subtitle">最近 60 次固定快照；仅持仓市值，不是剔除出入金后的投资回报率。</div></div><el-tag v-if="points.length" type="info" size="small">{{ points.length }} 次快照</el-tag></div></template>
  <p v-if="points.length<2">至少保存 2 次事实日报后显示趋势。缺少有效价格或汇率不补零，币种或账户变化时不连线。</p>
  <div v-else ref="chartHost" class="snapshot-chart-scroll" tabindex="0" aria-label="持仓市值快照趋势，可横向滚动">
   <svg :viewBox="`0 0 ${plotWidth} 260`" role="img" aria-label="固定快照持仓市值趋势">
    <g v-for="tick in ticks" :key="tick"><line :x1="left" :x2="plotWidth-20" :y1="y(tick)" :y2="y(tick)" class="grid-line"/><text :x="left-6" :y="y(tick)+4" text-anchor="end">{{ axis(tick) }}</text></g>
    <g v-for="segment in segments" :key="segment.id"><path :d="segment.area" fill="rgba(24,177,123,.12)"/><path :d="segment.line" fill="none" stroke="#18b17b" stroke-width="3" class="snapshot-segment"/></g>
    <g v-for="(point,index) in points" :key="point.id"><circle v-if="point.value!==null" :cx="x(index)" :cy="y(Number(point.value))" r="4" fill="#18b17b" class="snapshot-point" role="button" :tabindex="disabled?-1:0" :aria-label="label(point)" @click="choose(point.id)" @keydown.enter.prevent="choose(point.id)" @keydown.space.prevent="choose(point.id)"><title>{{ label(point) }}</title></circle><text v-else :x="x(index)" y="217" text-anchor="middle">待补</text><text v-if="showLabel(index)" :x="x(index)" y="247" text-anchor="middle">{{ date(point.at) }}</text></g>
   </svg>
  </div>
  <details v-if="points.length"><summary>查看固定金额与来源</summary><ol><li v-for="point in points" :key="point.id"><el-button link :disabled="disabled" @click="choose(point.id)">{{ label(point) }}</el-button><small>快照 {{ point.id }} · 只读取当次保存价格与汇率依据</small></li></ol></details>
 </el-card>
</template>
<script setup lang="ts">
import {computed,ref,watch,onBeforeUnmount} from 'vue'
import {sum,money} from '@/utils/decimal'
type Snapshot={id:string;kind:string;[key:string]:unknown}
type Point={id:string;at:string;account:string;currency:string;value:string|null}
const props=defineProps<{snapshots:Snapshot[];disabled:boolean}>(),emit=defineEmits<{select:[string]}>()
const chartHost=ref<HTMLElement|null>(null),plotWidth=ref(640),left=computed(()=>plotWidth.value<400?42:74)
let observer:ResizeObserver|undefined
watch(chartHost,host=>{observer?.disconnect();if(host){const resize=()=>{plotWidth.value=Math.max(240,Math.min(640,host.clientWidth))};observer=new ResizeObserver(resize);observer.observe(host);resize()}},{flush:'post'})
onBeforeUnmount(()=>observer?.disconnect())
const points=computed<Point[]>(()=>[...props.snapshots].sort((a,b)=>String(a.captured_at).localeCompare(String(b.captured_at))||a.id.localeCompare(b.id)).slice(-60).map(s=>{
 const v=s.valuation as {currency:string;valuation_complete:boolean;positions:{market_value:string|null}[]}|undefined
 return {id:s.id,at:String(s.captured_at||''),account:String(s.account_id||''),currency:v?.currency||'',value:v?.valuation_complete&&v.positions.every(p=>p.market_value!==null)?sum(v.positions.map(p=>p.market_value!)):null}
}))
const maximum=computed(()=>Math.max(1,...points.value.filter(p=>p.value!==null).map(p=>Number(p.value)))),ticks=computed(()=>[0,.25,.5,.75,1].map(n=>n*maximum.value))
const x=(i:number)=>points.value.length<2?plotWidth.value/2:left.value+10+i*(plotWidth.value-left.value-30)/(points.value.length-1),y=(n:number)=>220-n/maximum.value*190
const segments=computed(()=>points.value.slice(1).flatMap((p,i)=>{const prev=points.value[i];if(p.value===null||prev.value===null||p.currency!==prev.currency||p.account!==prev.account)return [];const a=x(i),b=x(i+1),c=(a+b)/2,ay=y(Number(prev.value)),by=y(Number(p.value)),curve=`C ${c} ${ay}, ${c} ${by}, ${b} ${by}`;return [{id:p.id,line:`M ${a} ${ay} ${curve}`,area:`M ${a} 220 L ${a} ${ay} ${curve} L ${b} 220 Z`}]}))
const axis=(n:number)=>new Intl.NumberFormat('zh-CN',{notation:'compact',maximumFractionDigits:1}).format(n)
const date=(v:string)=>new Date(v).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})
const label=(p:Point)=>`${new Date(p.at).toLocaleString('zh-CN',{hour12:false})} · ${money(p.value)} ${p.currency}${p.value===null?' · 估值资料不足':''}`
const showLabel=(i:number)=>i===0||i===points.value.length-1||i%Math.ceil(points.value.length/Math.max(2,Math.floor(plotWidth.value/85)))===0
function choose(id:string){if(!props.disabled)emit('select',id)}
</script>
<style scoped>
.history-card{border-radius:20px}.history-header{display:flex;align-items:center;justify-content:space-between;gap:12px}.history-title{font-weight:700}.history-subtitle,p,li{font-size:12px;line-height:1.6;overflow-wrap:anywhere}.history-subtitle{color:#8ea6c4;margin-top:5px}.snapshot-chart-scroll{overflow-x:auto}svg{display:block;width:100%;min-width:240px;height:260px}text{fill:#8ea6c4;font-size:11px}.grid-line{stroke:rgba(142,166,196,.16)}.snapshot-point{cursor:pointer}.snapshot-point:focus{outline:2px solid #18b17b;outline-offset:3px}li{margin:8px 0}li small{display:block}.el-button{white-space:normal;height:auto}summary{cursor:pointer}
</style>
