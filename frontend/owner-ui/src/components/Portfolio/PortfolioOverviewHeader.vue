<template>
  <div class="overview-header">
    <div class="overview-copy">
      <div class="overview-brand-line">
        <img class="overview-mark" src="/logo.svg" alt="Awesome Stock mark" />
        <div class="overview-eyebrow">Portfolio Workbench</div>
      </div>
      <div class="overview-title">{{ title }}</div>
      <div v-if="subtitle" class="overview-subtitle">{{ subtitle }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped lang="scss">
.overview-header {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}

.overview-brand-line {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 7px;
}

.overview-mark {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  box-shadow: 0 10px 22px rgba(10, 24, 48, 0.22);
}

.overview-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border: 1px solid rgba(126, 213, 255, 0.13);
  border-radius: 999px;
  background: rgba(126, 213, 255, 0.06);
  color: #9fc8de;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.overview-title {
  color: #edf6ff;
  font-size: 25px;
  font-weight: 760;
  letter-spacing: -0.01em;
}

.overview-subtitle {
  color: #95aac6;
  font-size: 12px;
}

@media (max-width: 780px) {
  .overview-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
