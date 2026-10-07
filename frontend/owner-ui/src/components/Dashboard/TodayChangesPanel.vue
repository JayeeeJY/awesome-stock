<template><section class="changes-panel" :aria-busy="loading"><header class="changes-head"><div><div class="changes-kicker"><span class="kicker-mark" aria-hidden="true"></span>WHAT CHANGED</div><h2>自上次检查后的变化</h2><p>对照你保存的账本基线，核对资金、成本和持仓数量。</p></div><div class="changes-actions"><div v-if="baseline" class="baseline-chip">{{ baseline }}</div><button type="button" class="view-all" @click="expanded=!expanded">{{ expanded?'收起':'查看全部变化' }}</button></div></header><div v-if="items.length" class="changes-grid"><button v-for="(item,index) in (expanded?items:items.slice(0,3))" :key="item.id" class="change-item is-info" type="button" @click="$emit('open')"><div class="change-topline"><span class="change-index">{{ String(index+1).padStart(2,'0') }}</span><span class="change-basis">账本快照对比</span><span class="change-arrow" aria-hidden="true">↗</span></div><strong>{{ item.title }}</strong><p>{{ privacy?'金额与数量已隐藏':item.detail }}</p></button></div><div v-else class="changes-empty"><div class="empty-symbol" aria-hidden="true">◇</div><div><strong>{{ baseline?'与上次基线相比没有账本变化':'还没有检查基线' }}</strong><p>{{ baseline?'仅比较已记录的现金、成本与持仓数量。':'保存当前账本作为基线，后续检查可查看变化。' }}</p></div></div></section></template>
<script setup lang="ts">
import {ref} from 'vue'
defineProps<{items:Array<{id:string;title:string;detail:string}>;baseline:string;loading:boolean;privacy:boolean}>()
defineEmits<{open:[]}>()
const expanded=ref(false)
</script>

<style scoped lang="scss">
.changes-panel {
  padding: 12px 14px;
  border: 1px solid rgba(112, 202, 255, 0.12);
  border-radius: 20px;
  background:
    radial-gradient(circle at 88% 0%, rgba(85, 194, 255, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(12, 27, 52, 0.88), rgba(9, 20, 39, 0.84));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.changes-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
}

.changes-head > div:first-child {
  display: grid;
  min-width: 0;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.changes-kicker {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7ccfff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.kicker-mark {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6dd5ff;
  box-shadow: 0 0 12px rgba(109, 213, 255, 0.72);
}

.changes-head h2 {
  margin: 0;
  color: #ecf6ff;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.changes-head p,
.change-item p,
.changes-empty p {
  margin: 0;
  color: #8299b8;
  font-size: 12px;
  line-height: 1.55;
}

.changes-head p,
.change-item p {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.changes-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
}

.baseline-chip {
  flex: none;
  min-height: 24px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(112, 202, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.035);
  color: #8ea9c8;
  font-size: 11px;
}

.view-all {
  min-height: 24px;
  padding: 0 9px;
  border: 1px solid rgba(112, 202, 255, 0.13);
  border-radius: 999px;
  background: rgba(112, 202, 255, 0.055);
  color: #78cef8;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.view-all:hover,
.view-all:focus-visible {
  background: rgba(112, 202, 255, 0.09);
  outline: none;
}

.changes-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.change-item {
  min-width: 0;
  min-height: 62px;
  padding: 8px 10px;
  border: 1px solid rgba(112, 202, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.025);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: 160ms ease;
}

.change-item:hover,
.change-item:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(109, 213, 255, 0.28);
  background: rgba(85, 194, 255, 0.06);
  outline: none;
}

.change-item.is-high {
  border-top-color: rgba(255, 103, 139, 0.58);
}

.change-item.is-watch {
  border-top-color: rgba(255, 189, 92, 0.5);
}

.change-item.is-info {
  border-top-color: rgba(95, 222, 180, 0.44);
}

.change-topline {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 5px;
}

.change-index {
  color: #6683a7;
  font-family: 'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace;
  font-size: 10px;
}

.change-basis {
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(112, 202, 255, 0.07);
  color: #91b5d8;
  font-size: 10px;
}

.change-arrow {
  margin-left: auto;
  color: #5a7799;
}

.change-item strong,
.changes-empty strong {
  display: block;
  margin-bottom: 2px;
  color: #e6f2ff;
  font-size: 13px;
  line-height: 1.25;
}

.changes-empty {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 14px 16px;
  border: 1px dashed rgba(112, 202, 255, 0.14);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
}

.empty-symbol {
  width: 34px;
  height: 34px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: rgba(95, 222, 180, 0.09);
  color: #71dfb9;
  font-weight: 800;
}

.changes-empty.is-baseline_missing .empty-symbol {
  background: rgba(112, 202, 255, 0.08);
  color: #72cfff;
}

.changes-empty.is-unavailable .empty-symbol {
  background: rgba(255, 189, 92, 0.1);
  color: #ffc06a;
}

.change-skeleton {
  height: 62px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.025));
  background-size: 200% 100%;
  animation: changes-shimmer 1.4s infinite linear;
}

@keyframes changes-shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 900px) {
  .changes-grid {
    grid-template-columns: 1fr;
  }

  .change-item {
    min-height: 0;
  }
}

@media (max-width: 560px) {
  .changes-panel {
    padding: 15px;
    border-radius: 16px;
  }

  .changes-head {
    display: block;
  }

  .baseline-chip {
    margin-top: 10px;
  }
}
@media (max-width: 350px) {
  .changes-head > div:first-child { grid-template-columns: auto minmax(0, 1fr); }
  .changes-head p { display: none; }
}
</style>
