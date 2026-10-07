<template>
  <section
    class="app-data-state"
    :class="[`is-${tone}`, { 'is-compact': compact }]"
    :role="tone === 'error' ? 'alert' : 'status'"
    :aria-live="tone === 'error' ? 'assertive' : 'polite'"
  >
    <span class="state-indicator" aria-hidden="true">
      <span v-if="tone === 'loading'" class="state-spinner"></span>
      <el-icon v-else-if="tone === 'error'"><WarningFilled /></el-icon>
      <el-icon v-else-if="tone === 'stale'"><Clock /></el-icon>
      <el-icon v-else><DataLine /></el-icon>
    </span>
    <div class="state-copy">
      <strong>{{ title }}</strong>
      <span v-if="description">{{ description }}</span>
    </div>
    <el-button
      v-if="actionLabel && tone !== 'loading'"
      class="state-action"
      size="small"
      plain
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </el-button>
  </section>
</template>

<script setup lang="ts">
import { Clock, DataLine, WarningFilled } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    tone?: 'loading' | 'error' | 'stale' | 'empty'
    title: string
    description?: string
    actionLabel?: string
    compact?: boolean
  }>(),
  {
    tone: 'empty',
    description: '',
    actionLabel: '',
    compact: false
  }
)

defineEmits<{
  action: []
}>()
</script>

<style scoped lang="scss">
.app-data-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  min-height: 82px;
  padding: 15px 16px;
  border: 1px solid rgba(112, 202, 255, 0.17);
  border-radius: 14px;
  background:
    linear-gradient(100deg, rgba(85, 194, 255, 0.08), rgba(255, 255, 255, 0.025)),
    rgba(8, 19, 38, 0.78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
}

.app-data-state.is-compact {
  min-height: 0;
  padding: 9px 12px;
}

.state-indicator {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(112, 202, 255, 0.18);
  border-radius: 10px;
  color: #65d7ff;
  background: rgba(85, 194, 255, 0.08);
}

.state-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.state-copy strong {
  color: #edf7ff;
  font-size: 12px;
  line-height: 1.45;
}

.state-copy span {
  overflow: hidden;
  color: #8ea6c4;
  font-size: 11px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.is-error {
  border-color: rgba(255, 98, 117, 0.28);
  background:
    linear-gradient(100deg, rgba(255, 98, 117, 0.11), rgba(255, 255, 255, 0.02)),
    rgba(8, 19, 38, 0.8);
}

.is-error .state-indicator {
  border-color: rgba(255, 98, 117, 0.25);
  color: #ff7585;
  background: rgba(255, 98, 117, 0.1);
}

.is-stale {
  border-color: rgba(255, 181, 77, 0.25);
  background:
    linear-gradient(100deg, rgba(255, 181, 77, 0.1), rgba(85, 194, 255, 0.025)),
    rgba(8, 19, 38, 0.8);
}

.is-stale .state-indicator {
  border-color: rgba(255, 181, 77, 0.24);
  color: #ffc466;
  background: rgba(255, 181, 77, 0.1);
}

.state-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(101, 215, 255, 0.2);
  border-top-color: #65d7ff;
  border-radius: 50%;
  animation: state-spin 0.8s linear infinite;
}

@keyframes state-spin {
  to {
    transform: rotate(360deg);
  }
}

:global(html:not(.dark)) .app-data-state {
  border-color: rgba(43, 125, 210, 0.16);
  background: linear-gradient(100deg, rgba(77, 157, 235, 0.08), rgba(255, 255, 255, 0.88));
}

:global(html:not(.dark)) .state-copy strong {
  color: #173153;
}

:global(html:not(.dark)) .state-copy span {
  color: #607693;
}

@media (max-width: 720px) {
  .app-data-state {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .state-action {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
