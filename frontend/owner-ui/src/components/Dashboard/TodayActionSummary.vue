<template><section class="action-summary" :aria-busy="loading"><div class="summary-copy"><div class="summary-kicker"><span aria-hidden="true"></span>ACTION INBOX</div><h2>{{ loading?'正在读取复核队列':items.length?`${items.length} 项记录已到复核日期`:'当前没有到期复核项' }}</h2><p v-if="!items.length">仅依据已保存的复核日期提醒，不代表全部投资风险已检查。</p><div v-else class="action-feed"><button v-for="item in items.slice(0,2)" :key="item.id" type="button" class="action-feed-item" @click="$emit('open')"><b class="is-p1">{{ item.priority }}</b><span>{{ item.title }}</span><small>{{ item.reason }}</small></button></div></div><div class="summary-counts" aria-live="polite"><div class="count-chip is-p1"><b>{{ items.length }}</b><span>P1</span></div></div><el-button type="primary" class="open-button" @click="$emit('open')">打开行动收件箱<el-icon><ArrowRight /></el-icon></el-button></section></template>
<script setup lang="ts">
import {ArrowRight} from '@element-plus/icons-vue'
import type {Action} from '@/api/business'
defineProps<{items:Action[];loading:boolean}>()
defineEmits<{open:[]}>()
</script>

<style scoped lang="scss">
.action-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 16px;
  min-height: 86px;
  padding: 12px 14px;
  border: 1px solid rgba(112, 202, 255, 0.14);
  border-radius: 20px;
  background:
    radial-gradient(circle at 80% 0%, rgba(78, 126, 255, 0.13), transparent 32%),
    linear-gradient(135deg, rgba(12, 28, 54, 0.94), rgba(8, 20, 39, 0.88));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.045);
}

.summary-copy {
  min-width: 0;
}

.summary-kicker {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #7ccfff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.summary-kicker span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6dd5ff;
  box-shadow: 0 0 12px rgba(109, 213, 255, 0.72);
}

h2 {
  margin: 4px 0 3px;
  color: #edf7ff;
  font-size: 16px;
  letter-spacing: -0.02em;
}

p {
  margin: 0;
  color: #879fbd;
  font-size: 12px;
  line-height: 1.55;
}

.action-feed {
  display: grid;
  max-width: 820px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 6px;
}

.action-feed-item {
  display: grid;
  min-width: 0;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 8px;
  align-items: center;
  padding: 6px 8px;
  border: 1px solid rgba(112, 202, 255, 0.09);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.024);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.action-feed-item:hover,
.action-feed-item:focus-visible {
  background: rgba(112, 202, 255, 0.055);
  outline: none;
}

.action-feed-item b {
  color: #ffc26f;
  font: 800 11px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.action-feed-item b.is-p0 {
  color: #ff7f98;
}

.action-feed-item span,
.action-feed-item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-feed-item span {
  color: #e8f3ff;
  font-size: 12px;
  font-weight: 700;
}

.action-feed-item small {
  grid-column: 2;
  color: #7f96b3;
  font-size: 10px;
}

.summary-counts {
  display: flex;
  gap: 8px;
}

.count-chip {
  display: grid;
  min-width: 52px;
  min-height: 44px;
  place-items: center;
  align-content: center;
  border: 1px solid rgba(112, 202, 255, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.028);
}

.count-chip b {
  color: #e9f5ff;
  font: 800 16px/1 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
}

.count-chip span {
  margin-top: 5px;
  color: #7890ad;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.count-chip.is-p0 {
  border-color: rgba(255, 103, 139, 0.24);
  background: rgba(255, 103, 139, 0.065);
}

.count-chip.is-p0 span {
  color: #ff8aa5;
}

.count-chip.is-p1 {
  border-color: rgba(255, 189, 92, 0.22);
  background: rgba(255, 189, 92, 0.06);
}

.count-chip.is-p1 span {
  color: #ffc26f;
}

.count-chip.is-digest span {
  color: #74cfff;
}

.summary-counts.is-loading span {
  width: 52px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(90deg, rgba(255,255,255,.025), rgba(255,255,255,.07), rgba(255,255,255,.025));
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.open-button {
  min-width: 138px;
  height: 36px;
  border-radius: 11px;
}

@keyframes shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 860px) {
  .action-summary {
    grid-template-columns: 1fr auto;
  }

  .summary-counts {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .action-feed {
    grid-template-columns: 1fr;
  }

  .open-button {
    grid-column: 2;
    grid-row: 1;
  }
}

@media (max-width: 560px) {
  .action-summary {
    display: flex;
    min-height: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
    padding: 16px;
    border-radius: 16px;
  }

  .summary-counts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .count-chip,
  .summary-counts.is-loading span {
    min-width: 0;
    width: auto;
  }

  .open-button {
    width: 100%;
  }
}
</style>
