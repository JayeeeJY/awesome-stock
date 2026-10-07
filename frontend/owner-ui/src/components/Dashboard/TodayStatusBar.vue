<template><section class="today-status" :class="`is-${state}`" :aria-busy="loading"><div class="snapshot-head"><div class="snapshot-kicker"><span class="status-dot" aria-hidden="true"></span><span>PORTFOLIO SNAPSHOT / 组合概览</span></div><strong>{{ title }}</strong><small>{{ detail }}</small></div><div class="snapshot-metrics"><div v-for="(item,index) in metrics" :key="item.label" class="snapshot-metric" :class="{'is-assets':index===0}"><span>{{ item.label }}</span><strong :class="privacy?'':item.tone">{{ privacy?'••••':item.value }}</strong><small>{{ item.meta }}</small></div></div></section></template>
<script setup lang="ts">
defineProps<{state:string;title:string;detail:string;loading:boolean;privacy:boolean;metrics:Array<{label:string;value:string;meta:string;tone?:string}>}>()
</script>

<style scoped lang="scss">
.today-status {
  display: grid;
  min-height: 0;
  height: 90px;
  grid-template-columns: minmax(180px, 0.75fr) minmax(720px, 3.2fr);
  align-items: stretch;
  overflow: hidden;
  border: 1px solid rgba(112, 202, 255, 0.12);
  border-radius: 20px;
  background:
    radial-gradient(circle at 90% 0%, rgba(80, 126, 255, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(11, 27, 52, 0.94), rgba(7, 18, 36, 0.9));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.snapshot-head {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  padding: 10px 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.snapshot-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #7ccfff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.status-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: #f6bd4c;
  box-shadow: 0 0 0 4px rgba(246, 189, 76, 0.11);
}

.today-status.is-clear .status-dot {
  background: #53d6a0;
  box-shadow: 0 0 0 4px rgba(83, 214, 160, 0.11);
}

.today-status.is-attention .status-dot,
.today-status.is-data_issue .status-dot {
  background: #ff6978;
  box-shadow: 0 0 0 4px rgba(255, 105, 120, 0.11);
}

.snapshot-head strong {
  overflow: hidden;
  color: #f0f7ff;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snapshot-head small {
  overflow: hidden;
  color: #839bb9;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snapshot-metrics {
  display: grid;
  min-width: 0;
  grid-template-columns: 1.24fr repeat(5, minmax(0, 1fr));
}

.snapshot-metric {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  padding: 9px 14px;
  border-left: 1px solid rgba(255, 255, 255, 0.055);
}

.snapshot-metric:first-child {
  border-left: 0;
}

.snapshot-metric span,
.snapshot-metric small {
  display: block;
  overflow: hidden;
  color: #7d94b2;
  font-size: 10px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snapshot-metric span {
  font-weight: 700;
}

.snapshot-metric strong {
  display: block;
  overflow: visible;
  color: #eef7ff;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-size: clamp(14px, 1.1vw, 18px);
  font-variant-numeric: tabular-nums;
  font-weight: 780;
  letter-spacing: -0.035em;
  white-space: nowrap;
}

.snapshot-metric.is-assets strong {
  color: #eaf5ff;
}

.snapshot-metric.is-risk strong {
  color: #8fddff;
}

.is-positive {
  color: #ff7788 !important;
}

.is-negative {
  color: #4bd8a4 !important;
}

.is-neutral {
  color: #9bb0ca !important;
}

@media (max-width: 1180px) {
  .today-status {
    height: auto;
    grid-template-columns: 1fr;
  }

  .snapshot-head {
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .snapshot-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .snapshot-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
