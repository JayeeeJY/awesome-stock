<template>
 <section v-if="groups.length||pending" class="timeline-section" aria-label="建仓时间线">
  <el-alert v-if="pending" :title="`${pending} 笔关联成交待核对，未计入图表。`" type="warning" :closable="false"/>
  <div v-for="group in groups" :key="group.currency" class="chart-card">
   <h3 class="chart-title">建仓时间线 · {{ group.currency }}</h3>
   <p class="chart-caption">按实际成交时间排列，每柱为一笔已关联买入的含费用投入。</p>
   <div class="chart-scroll" tabindex="0" :aria-label="`${group.currency} 成交金额图，可横向滚动`">
    <svg :viewBox="`0 0 ${width(group.rows.length)} 260`" :style="{minWidth:width(group.rows.length)+'px'}" role="img" :aria-label="`${group.currency} ${group.rows.length} 笔买入，详细数据见下方表格`">
     <g v-for="tick in [0,1,2,3,4]" :key="tick"><line x1="85" :x2="width(group.rows.length)-20" :y1="220-tick*45" :y2="220-tick*45" class="grid-line"/><text x="78" :y="224-tick*45" text-anchor="end">{{ axis(group.max,tick) }}</text></g>
     <g v-for="(e,index) in group.rows" :key="e.id"><rect :x="105+index*64" :y="220-height(e.amount,group.max)" width="24" :height="height(e.amount,group.max)" rx="4" :fill="color(e.trade.symbol)"><title>{{ e.trade.symbol }} · {{ time(e.trade.executed_at) }} · {{ e.trade.quantity }} 股 @ {{ e.trade.price }} · 含费 {{ e.amount }} {{ group.currency }} · {{ e.note }}</title></rect><text :x="117+index*64" y="241" text-anchor="middle">{{ shortDate(e.trade.executed_at) }}</text></g>
    </svg>
   </div>
   <details><summary>查看时间线数据（{{ group.rows.length }} 笔）</summary><div class="table-scroll"><table><thead><tr><th>成交时间</th><th>标的 / 账户</th><th>股数</th><th>含费投入（{{ group.currency }}）</th></tr></thead><tbody><tr v-for="e in group.rows" :key="e.id"><td>{{ time(e.trade.executed_at) }}</td><td>{{ e.trade.symbol }} / {{ e.trade.account_name }}</td><td>{{ e.trade.quantity }}</td><td>{{ e.amount }}</td></tr></tbody></table></div></details>
  </div>
 </section>
</template>
<script setup lang="ts">
import {computed} from 'vue'
import type {Execution} from './executionTypes'
import {compare,divide,money,multiply} from '@/utils/decimal'
const props=defineProps<{executions:Execution[]}>()
const pending=computed(()=>props.executions.filter(e=>!e.archived&&e.trade_changed&&e.trade.side==='buy').length)
const groups=computed(()=>{
 const map=new Map<string,Execution[]>()
 for(const e of props.executions){if(e.archived||e.trade_changed||e.trade.side!=='buy')continue;const rows=map.get(e.trade.currency)||[];rows.push(e);map.set(e.trade.currency,rows)}
 return [...map].sort(([a],[b])=>a.localeCompare(b)).map(([currency,rows])=>({currency,rows:rows.sort((a,b)=>Date.parse(a.trade.executed_at)-Date.parse(b.trade.executed_at)||a.id.localeCompare(b.id)),max:rows.reduce((m,e)=>compare(e.amount,m)>0?e.amount:m,'0')}))
})
const symbols=computed(()=>[...new Set(props.executions.map(e=>e.trade.symbol))].sort())
const colors=['#2f7dff','#1f9d68','#e6a23c','#f56c6c','#9b59b6']
const color=(symbol:string)=>colors[symbols.value.indexOf(symbol)%colors.length]
const width=(count:number)=>Math.max(420,120+count*64)
// Number conversion is only for chart coordinates; labels retain decimal strings.
const height=(value:string,max:string)=>Number(divide(value,max,8)||'0')*180
const axis=(max:string,tick:number)=>tick===0?'0':money(divide(multiply(max,String(tick)),'4',8))
const time=(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})
const shortDate=(value:string)=>new Date(value).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})
</script>
<style scoped>
.timeline-section{margin-bottom:24px}.chart-card{background:var(--el-bg-color);border:1px solid var(--el-border-color-lighter);border-radius:12px;padding:16px;margin-bottom:16px}.chart-title{font-size:14px;font-weight:600;color:var(--el-text-color-primary);margin:0 0 12px}.chart-caption{font-size:12px;color:var(--el-text-color-secondary)}.chart-scroll,.table-scroll{overflow-x:auto;max-width:100%}svg{width:100%;height:260px;display:block}svg text{fill:var(--el-text-color-secondary);font-size:10px}.grid-line{stroke:var(--el-border-color);stroke-dasharray:4 4}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--el-border-color);white-space:nowrap}summary{cursor:pointer;font-size:12px;color:var(--el-text-color-secondary)}
</style>
