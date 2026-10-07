<template>
  <el-menu
    :default-active="activeMenu"
    class="sidebar-menu"
    :aria-label="t.navigation"
    @select="handleSelect"
  >
    <div class="menu-workspace">
      <section class="menu-group" :aria-label="t.cockpit">
        <el-menu-item index="/cockpit" class="is-primary">
          <el-icon><Odometer /></el-icon>
          <template #title>
            <span class="primary-title"><b>{{ t.cockpit }}</b><small>{{ t.cockpitHint }}</small></span>
          </template>
        </el-menu-item>
      </section>

      <section
        v-for="group in workspaceGroups"
        :key="group.key"
        class="menu-group workspace-group"
        :class="{ 'is-current': isWorkspaceActive(group), 'is-open': isWorkspaceOpen(group) }"
        :aria-label="group.label"
      >
        <button
          type="button"
          class="workspace-toggle"
          :aria-expanded="isWorkspaceOpen(group)"
          :aria-controls="`${group.key}-workspace-links`"
          @click="toggleWorkspace(group)"
        >
          <span class="workspace-icon" aria-hidden="true">
            <el-icon><component :is="group.icon" /></el-icon>
          </span>
          <span class="primary-title">
            <b>{{ group.label }}</b>
            <small>{{ group.hint }}</small>
          </span>
          <el-icon class="workspace-chevron" aria-hidden="true"><ArrowDown /></el-icon>
        </button>

        <div
          v-show="isWorkspaceOpen(group)"
          :id="`${group.key}-workspace-links`"
          class="secondary-links"
          :aria-label="group.toolsLabel"
        >
          <router-link
            v-for="link in group.links"
            :key="link.to"
            :to="link.to"
            :class="{ 'is-active': isLinkActive(link) }"
            :aria-current="isLinkActive(link) ? 'page' : undefined"
          >
            {{ link.label }}
          </router-link>
        </div>
      </section>

      <section class="menu-group" :aria-label="t.academy">
        <el-menu-item index="/academy">
          <el-icon><Notebook /></el-icon>
          <template #title>
            <span class="primary-title"><b>{{ t.academy }}</b><small>{{ t.academyHint }}</small></span>
          </template>
        </el-menu-item>
      </section>
    </div>

    <section class="menu-group is-utility" :aria-label="t.system">
      <div class="menu-section-label">{{ t.system }}</div>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <template #title>{{ t.generalSettings }}</template>
      </el-menu-item>
    </section>
  </el-menu>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Aim, ArrowDown, Notebook, Odometer, RefreshRight, Setting, TrendCharts, Wallet } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { routeMatchesPrefix } from '@/config/navigation'

type WorkspaceKey = 'portfolio' | 'research' | 'plan' | 'evolve'

type WorkspaceLink = {
  to: string
  label: string
  matches: string[]
}

type WorkspaceGroup = {
  key: WorkspaceKey
  label: string
  hint: string
  toolsLabel: string
  icon: typeof Wallet
  matchPrefixes: string[]
  links: WorkspaceLink[]
}

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const manuallyOpenGroups = ref<WorkspaceKey[]>([])

const activeMenu = computed(() => {
  if (routeMatchesPrefix(route.path, '/cockpit') || routeMatchesPrefix(route.path, '/today')) return '/cockpit'
  if (routeMatchesPrefix(route.path, '/academy') || routeMatchesPrefix(route.path, '/learn') || routeMatchesPrefix(route.path, '/education')) return '/academy'
  if (routeMatchesPrefix(route.path, '/settings')) return '/settings'
  return ''
})

const t = computed(() => {
  if (appStore.language === 'en-US') {
    return {
      navigation: 'Primary navigation',
      system: 'System',
      cockpit: 'Cockpit',
      cockpitHint: 'Daily overview',
      portfolio: 'Portfolio',
      portfolioHint: 'Facts ledger',
      portfolioTools: 'Portfolio pages',
      holdings: 'Holdings',
      trades: 'Trades',
      accounts: 'Accounts',
      allocation: 'Allocation',
      research: 'Research',
      researchHint: 'Thesis & evidence',
      researchTools: 'Research pages',
      singleResearch: 'Stock Research',
      screening: 'Opportunity Screener',
      batchResearch: 'Batch Research',
      buildUp: 'Build-up',
      preTradeCheck: 'Pre-trade Check',
      plan: 'Plan',
      planHint: 'Strategy tools',
      planTools: 'Plan pages',
      evolve: 'Evolve',
      evolveHint: 'Rule memory',
      evolveTools: 'Evolve pages',
      evolutionLog: 'Evolution Log',
      diagnosis: 'Health Trend',
      academy: 'Academy',
      academyHint: 'Knowledge frameworks',
      generalSettings: 'Settings',
    }
  }
  return {
    navigation: '主导航',
    system: '系统',
    cockpit: '驾驶舱',
    cockpitHint: '今日总览',
    portfolio: '投资组合',
    portfolioHint: '资产事实',
    portfolioTools: '投资组合页面',
    holdings: '持仓',
    trades: '交易流水',
    accounts: '账户管理',
    allocation: '资产配置',
    research: '研究',
    researchHint: '论点与证据',
    researchTools: '研究页面',
    singleResearch: '个股研究',
    screening: '机会筛选',
    batchResearch: '批量研究',
    buildUp: '分批建仓',
    preTradeCheck: '交易前检查',
    plan: '计划',
    planHint: '策略工具',
    planTools: '计划页面',
    evolve: '进化',
    evolveHint: '规则沉淀',
    evolveTools: '进化页面',
    evolutionLog: '进化记录',
    diagnosis: '健康趋势',
    academy: '学院',
    academyHint: '投资知识框架',
    generalSettings: '系统设置',
  }
})

const workspaceGroups = computed<WorkspaceGroup[]>(() => [
  {
    key: 'portfolio',
    label: t.value.portfolio,
    hint: t.value.portfolioHint,
    toolsLabel: t.value.portfolioTools,
    icon: Wallet,
    matchPrefixes: ['/portfolio'],
    links: [
      { to: '/portfolio', label: t.value.holdings, matches: ['/portfolio'] },
      { to: '/portfolio/trades', label: t.value.trades, matches: ['/portfolio/trades', '/trades'] },
      { to: '/portfolio/accounts', label: t.value.accounts, matches: ['/portfolio/accounts', '/accounts'] },
      { to: '/portfolio/cash', label: appStore.language === 'en-US' ? 'Cash Flows' : '资金流水', matches: ['/portfolio/cash'] },
    ],
  },
  {
    key: 'research',
    label: t.value.research,
    hint: t.value.researchHint,
    toolsLabel: t.value.researchTools,
    icon: TrendCharts,
    matchPrefixes: ['/research', '/analysis', '/screening', '/stocks', '/decisions'],
    links: [
      { to: '/research', label: t.value.singleResearch, matches: ['/research', '/analysis', '/stocks'] },
      { to: '/research/screening', label: t.value.screening, matches: ['/research/screening', '/screening'] },
      { to: '/research/notes', label: '研究笔记', matches: ['/research/notes'] },
      { to: '/decisions', label: '投资判断', matches: ['/decisions'] },
      { to: '/research/batch', label: t.value.batchResearch, matches: ['/research/batch', '/analysis/batch'] },
    ],
  },
  {
    key: 'plan',
    label: t.value.plan,
    hint: t.value.planHint,
    toolsLabel: t.value.planTools,
    icon: Aim,
    matchPrefixes: ['/plan'],
    links: [
      { to: '/plan/allocation', label: t.value.allocation, matches: ['/plan/allocation', '/portfolio/allocation'] },
      { to: '/plan/build-up', label: t.value.buildUp, matches: ['/plan/build-up', '/plan/buildup', '/research/build-up', '/research/buildup', '/portfolio/buildup'] },
      { to: '/plan/budget', label: '分批预算', matches: ['/plan/budget'] },
      { to: '/plan/pre-trade', label: t.value.preTradeCheck, matches: ['/plan/pre-trade', '/research/what-if', '/whatif', '/portfolio/whatif'] },
    ],
  },
  {
    key: 'evolve',
    label: t.value.evolve,
    hint: t.value.evolveHint,
    toolsLabel: t.value.evolveTools,
    icon: RefreshRight,
    matchPrefixes: ['/review', '/evolve', '/diagnosis', '/journal'],
    links: [
      { to: '/review', label: t.value.evolutionLog, matches: ['/review', '/evolve', '/journal'] },
      { to: '/review/diagnosis', label: t.value.diagnosis, matches: ['/review/diagnosis', '/evolve/diagnosis', '/diagnosis'] },
    ],
  },
])

const activeWorkspace = computed<WorkspaceKey | null>(() => {
  const current = workspaceGroups.value.find(group =>
    group.matchPrefixes.some(prefix => routeMatchesPrefix(route.path, prefix))
  )
  return current?.key || null
})

const isWorkspaceActive = (group: WorkspaceGroup) => group.key === activeWorkspace.value

const isWorkspaceOpen = (group: WorkspaceGroup) =>
  isWorkspaceActive(group) || manuallyOpenGroups.value.includes(group.key)

const toggleWorkspace = (group: WorkspaceGroup) => {
  if (isWorkspaceActive(group)) return
  manuallyOpenGroups.value = manuallyOpenGroups.value.includes(group.key)
    ? manuallyOpenGroups.value.filter(key => key !== group.key)
    : [...manuallyOpenGroups.value, group.key]
}

const isOverviewLink = (link: WorkspaceLink) =>
  ['/portfolio', '/research', '/review'].includes(link.to)

const isLinkActive = (link: WorkspaceLink) => {
  if (isOverviewLink(link)) {
    if (link.to === '/portfolio') return route.path === '/portfolio' || route.path === '/portfolio/overview'
    if (link.to === '/research') return route.path === '/research' || route.path.startsWith('/stocks/')
    if (link.to === '/review') return route.path === '/review' || route.path === '/evolve' || route.path === '/journal'
  }
  return link.matches.some(prefix => routeMatchesPrefix(route.path, prefix))
}

const handleSelect = (index: string) => {
  if (index !== route.path) {
    router.push(index)
  }
}
</script>

<style lang="scss" scoped>
.sidebar-menu {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100%;
  padding: 18px 12px 14px;
  border: none;
  background: transparent;

  :deep(.el-menu-item) {
    height: 50px;
    margin: 0;
    padding-left: 12px !important;
    border: 1px solid transparent;
    border-radius: 16px;
    color: #b8cbe3;
    font-size: 15px;
    font-weight: 600;
    line-height: 50px;
  }

  :deep(.el-menu-item),
  :deep(.el-menu-item .el-icon) {
    transition: all 0.2s ease;
  }

  :deep(.el-menu-item:hover) {
    border-color: rgba(126, 213, 255, 0.14);
    background: rgba(126, 213, 255, 0.07);
    color: #f3fbff;
  }

  :deep(.el-menu-item.is-active) {
    border-color: rgba(126, 213, 255, 0.24);
    background:
      radial-gradient(circle at 12% 8%, rgba(126, 213, 255, 0.18), transparent 34%),
      linear-gradient(135deg, rgba(30, 88, 166, 0.42) 0%, rgba(18, 42, 78, 0.72) 100%);
    box-shadow:
      inset 3px 0 0 #5bd6ff,
      0 14px 28px rgba(3, 13, 28, 0.22);
    color: #ffffff;
  }

  :deep(.el-menu-item .el-icon) {
    display: inline-grid;
    width: 28px;
    height: 28px;
    place-items: center;
    margin-right: 11px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.035);
    color: #7f9dbb;
    font-size: 15px;
  }

  :deep(.el-menu-item.is-active .el-icon) {
    background: rgba(126, 213, 255, 0.12);
    color: #7fe1ff;
  }
}

.menu-workspace {
  display: grid;
  gap: 10px;
}

.menu-group {
  min-width: 0;
}

.menu-group.is-utility {
  margin-top: auto;
  padding-top: 11px;
  border-top: 1px solid rgba(112, 202, 255, 0.09);
}

.workspace-toggle {
  display: grid;
  width: 100%;
  min-height: 50px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  padding: 0 11px 0 12px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  color: #b8cbe3;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    border-color: rgba(126, 213, 255, 0.14);
    background: rgba(126, 213, 255, 0.055);
    color: #f3fbff;
  }

  &:focus-visible {
    outline: 2px solid rgba(126, 213, 255, 0.72);
    outline-offset: 2px;
  }
}

.workspace-icon {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.035);
  color: #7f9dbb;
  font-size: 15px;
  transition: color 0.2s ease, background 0.2s ease;
}

.workspace-chevron {
  color: #66809f;
  font-size: 13px;
  transition: transform 0.18s ease, color 0.18s ease;
}

.workspace-group.is-current .workspace-toggle {
  border-color: rgba(126, 213, 255, 0.18);
  background: rgba(25, 73, 130, 0.18);
  box-shadow: inset 2px 0 0 rgba(91, 214, 255, 0.72);
  color: #eef8ff;
}

.workspace-group.is-current .workspace-icon {
  background: rgba(126, 213, 255, 0.12);
  color: #7fe1ff;
}

.workspace-group.is-open .workspace-chevron {
  color: #86dfff;
  transform: rotate(180deg);
}

.primary-title {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
  line-height: 1.1;

  b {
    color: inherit;
    font-size: 15px;
    letter-spacing: 0.01em;
  }

  small {
    max-width: 150px;
    overflow: hidden;
    color: #748ca9;
    font-size: 12px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.secondary-links {
  display: grid;
  gap: 4px;
  padding: 6px 4px 0 52px;

  a {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 10px;
    border: 1px solid transparent;
    border-radius: 9px;
    color: #7f97b4;
    font-size: 13px;
    font-weight: 600;
    line-height: 1;
    text-decoration: none;
    white-space: nowrap;
    transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease;
  }

  a + a::before {
    content: none;
  }

  a:hover,
  a:focus-visible,
  a.is-active {
    border-color: rgba(126, 213, 255, 0.13);
    background: rgba(126, 213, 255, 0.06);
    color: #aeeeff;
  }

  a:focus-visible {
    outline: 2px solid rgba(126, 213, 255, 0.72);
    outline-offset: 2px;
  }

  a.is-active {
    box-shadow: inset 2px 0 0 rgba(91, 214, 255, 0.78);
  }
}

.menu-section-label {
  padding: 0 8px 7px;
  color: #6f89a5;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.is-primary :deep(.el-icon) {
  color: #7fe1ff;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-menu :deep(.el-menu-item),
  .sidebar-menu :deep(.el-menu-item .el-icon),
  .workspace-toggle,
  .workspace-icon,
  .workspace-chevron,
  .secondary-links a {
    transition: none;
  }

  .workspace-group.is-open .workspace-chevron {
    transform: none;
  }
}
</style>
