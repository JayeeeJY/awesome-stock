<template>
  <nav class="mobile-tab-bar" aria-label="移动端主导航">
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="mobile-tab-bar__item"
      :class="{ 'is-active': isActive(item) }"
      :aria-current="isActive(item) ? 'page' : undefined"
    >
      <el-icon><component :is="item.icon" /></el-icon>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Aim, Notebook, Odometer, RefreshRight, TrendCharts, Wallet } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { routeMatchesPrefix } from '@/config/navigation'

type TabItem = {
  to: string
  label: string
  icon: typeof Odometer
  matches: string[]
}

const route = useRoute()
const appStore = useAppStore()

const items = computed<TabItem[]>(() => {
  const english = appStore.language === 'en-US'
  return [
    { to: '/cockpit', label: english ? 'Cockpit' : '驾驶舱', icon: Odometer, matches: ['/cockpit', '/today'] },
    { to: '/portfolio', label: english ? 'Portfolio' : '持仓', icon: Wallet, matches: ['/portfolio'] },
    { to: '/research', label: english ? 'Research' : '研究', icon: TrendCharts, matches: ['/research', '/stocks/'] },
    { to: '/plan', label: english ? 'Plan' : '计划', icon: Aim, matches: ['/plan'] },
    { to: '/review', label: english ? 'Evolve' : '进化', icon: RefreshRight, matches: ['/review', '/evolve'] },
    { to: '/academy', label: english ? 'Academy' : '学院', icon: Notebook, matches: ['/academy', '/learn', '/education'] },
  ]
})

const isActive = (item: TabItem) => item.matches.some(path => routeMatchesPrefix(route.path, path))
</script>

<style lang="scss" scoped>
.mobile-tab-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 940;
  display: none;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  min-height: calc(58px + env(safe-area-inset-bottom));
  padding: 5px 6px max(5px, env(safe-area-inset-bottom));
  background: rgba(7, 18, 36, 0.94);
  border-top: 1px solid rgba(112, 202, 255, 0.16);
  box-shadow: 0 -12px 32px rgba(2, 10, 24, 0.32);
  backdrop-filter: blur(22px) saturate(145%);
  -webkit-backdrop-filter: blur(22px) saturate(145%);
}

.mobile-tab-bar__item {
  min-width: 0;
  min-height: 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: 12px;
  color: #7f9dbb;
  text-decoration: none;
  font-size: 9px;
  font-weight: 600;
  line-height: 1;
  -webkit-tap-highlight-color: transparent;

  .el-icon {
    font-size: 18px;
    transition: transform 0.18s ease;
  }

  &.is-active {
    color: #72dcff;
    background: linear-gradient(180deg, rgba(85, 194, 255, 0.13), rgba(44, 143, 255, 0.05));
  }

  &.is-active .el-icon {
    transform: translateY(-1px);
    filter: drop-shadow(0 0 9px rgba(85, 194, 255, 0.32));
  }
}

@media (max-width: 1099px) {
  .mobile-tab-bar {
    display: grid;
  }
}

@media (prefers-reduced-motion: reduce) {
  .mobile-tab-bar__item .el-icon {
    transition: none;
  }
}
</style>
