<template>
  <div class="basic-layout">
    <!-- 侧边栏 -->
    <aside
      class="sidebar"
      :class="{ collapsed: sidebarCollapsed }"
      :style="{ width: sidebarWidth + 'px' }"
    >
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-mark">
            <img src="/logo.svg" alt="Awesome Stock" />
          </div>
          <div v-show="!sidebarCollapsed" class="logo-copy">
            <span class="logo-text">Awesome Stock</span>
            <span class="logo-subtitle">Personal AI Decision OS</span>
          </div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <SidebarMenu />
      </nav>

      <div class="sidebar-footer">
        <UserProfile />
      </div>
    </aside>

    <!-- 点击蒙层：移动端展开时，点击空白处收起侧边栏 -->
    <div
      v-if="isMobile && !sidebarCollapsed"
      class="sidebar-overlay"
      @click="appStore.setSidebarCollapsed(true)"
    ></div>

    <!-- 主内容区 -->
    <div
      class="main-container"
      :class="{ 'assistant-docked': assistantDocked }"
      :style="{
        marginLeft: sidebarMarginLeft + 'px',
        marginRight: assistantDocked ? assistantWidth + 'px' : '0px'
      }"
      @click="handleMainClick"
    >
      <!-- 顶部导航栏 -->
      <header class="header">
        <div class="header-left">
          <el-button
            v-if="isMobile"
            text
            @click.stop="appStore.toggleSidebar()"
            class="sidebar-toggle"
            aria-label="打开主导航"
          >
            <el-icon><Expand v-if="sidebarCollapsed" /><Fold v-else /></el-icon>
          </el-button>

          <Breadcrumb />
        </div>

        <div class="header-right">
          <HeaderActions />
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="main-content">
        <div class="content-wrapper">
          <section v-if="routeViewError" class="route-error-panel" role="alert">
            <div class="route-error-mark">AS</div>
            <p class="route-error-eyebrow">AWESOME STOCK RECOVERY</p>
            <h2>{{ routeErrorCopy.title }}</h2>
            <p>{{ routeErrorCopy.description }}</p>
            <div class="route-error-actions">
              <el-button type="primary" @click="retryCurrentView">
                {{ routeErrorCopy.retry }}
              </el-button>
              <el-button @click="returnToDashboard">
                {{ routeErrorCopy.dashboard }}
              </el-button>
            </div>
          </section>
          <router-view v-else v-slot="{ Component, route: activeRoute }">
            <transition :name="typeof activeRoute.meta.transition === 'string' ? activeRoute.meta.transition : 'fade'" appear>
              <keep-alive :include="keepAliveComponents">
                <component
                  :is="Component"
                  :key="`${resolveViewKey(activeRoute)}:${routeViewEpoch}`"
                />
              </keep-alive>
            </transition>
          </router-view>
        </div>
      </main>

      <!-- 页脚 -->
      <footer class="footer">
        <AppFooter />
      </footer>
    </div>

    <MobileTabBar v-if="isMobile" />
    <ActionInbox />
    <AssistantPanel :can-dock="assistantCanDock" :is-mobile="isMobile" />


    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { computed, onErrorCaptured, onMounted, onUnmounted, ref, watch } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useRoute, useRouter } from 'vue-router'
import AssistantPanel from '@/components/AskAwesome/AssistantPanel.vue'
import { useAskStore } from '@/stores/ask'
import ActionInbox from '@/components/Dashboard/ActionInbox.vue'
import SidebarMenu from '@/components/Layout/SidebarMenu.vue'
import UserProfile from '@/components/Layout/UserProfile.vue'
import Breadcrumb from '@/components/Layout/Breadcrumb.vue'
import HeaderActions from '@/components/Layout/HeaderActions.vue'
import AppFooter from '@/components/Layout/AppFooter.vue'
import MobileTabBar from '@/components/Layout/MobileTabBar.vue'

import { Expand, Fold } from '@element-plus/icons-vue'

const appStore = useAppStore()
const ask = useAskStore()

const route = useRoute()
const router = useRouter()
const routeViewError = ref<unknown>(null)
const routeViewEpoch = ref(0)
const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)

const routeErrorCopy = computed(() =>
  appStore.language === 'en-US'
    ? {
        title: 'This page stopped unexpectedly',
        description: 'Your data is safe. Retry this view or return to Cockpit.',
        retry: 'Retry page',
        dashboard: 'Return to Cockpit'
      }
    : {
        title: '页面运行出现异常',
        description: '数据没有丢失。你可以重新加载当前页面，或先返回 Cockpit。',
        retry: '重新加载',
        dashboard: '返回 Cockpit'
      }
)

onErrorCaptured((error, _instance, info) => {
  console.error('Route view crashed:', error, info)
  routeViewError.value = error
  return false
})

const retryCurrentView = () => {
  routeViewEpoch.value += 1
  routeViewError.value = null
}

const returnToDashboard = async () => {
  routeViewEpoch.value += 1
  routeViewError.value = null
  if (route.path === '/cockpit') return
  await router.replace('/cockpit')
}

// 需要缓存的高频页面
const keepAliveComponents = computed(() => [
  'DashboardHome',
  'CockpitHome',
  'PortfolioOverview',
  'Diagnosis',
  'PortfolioReminders',
  'CockpitActionInbox',
  'Trades',
  'Accounts',
  'SingleAnalysis',
  'AnalysisHistory',
  'StockScreeningHome',
  'AcademyHome'
])

const resolveViewKey = (route: RouteLocationNormalizedLoaded) => {
  const name = typeof route.name === 'string' ? route.name : ''
  return keepAliveComponents.value.includes(name) ? name : route.fullPath
}

// 移动端判断
// iPad 竖屏也使用紧凑导航，避免侧栏挤压数据密集页面。
const isMobile = computed(() => viewportWidth.value < 1100)
const sidebarCollapsed = computed(() => (isMobile.value ? appStore.sidebarCollapsed : false))
const sidebarWidth = computed(() =>
  isMobile.value
    ? sidebarCollapsed.value
      ? 0
      : appStore.actualSidebarWidth
    : appStore.sidebarWidth
)
const sidebarMarginLeft = computed(() => (isMobile.value ? 0 : sidebarWidth.value))
const assistantWidth = 470
const assistantCanDock = computed(() => viewportWidth.value >= 1560)
const assistantDocked = computed(() => ask.visible && ask.pinned && assistantCanDock.value)
const handleAskShortcut = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {event.preventDefault();ask.open()}
  if (event.key === 'Escape' && isMobile.value) appStore.setSidebarCollapsed(true)
}

const updateViewportWidth = () => {
  viewportWidth.value = window.innerWidth
}

onMounted(() => {
  updateViewportWidth()
  if (isMobile.value) {
    appStore.setSidebarCollapsed(true)
  }
  window.addEventListener('resize', updateViewportWidth)
  window.addEventListener('keydown', handleAskShortcut)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateViewportWidth)
  window.removeEventListener('keydown', handleAskShortcut)
})

// 点击主内容时，若移动端且侧边栏已展开，则收起
const handleMainClick = () => {
  if (isMobile.value && !sidebarCollapsed.value) {
    appStore.setSidebarCollapsed(true)
  }
}

// 监听窗口大小变化：在小屏幕上自动折叠侧边栏
watch(isMobile, mobile => {
  if (mobile && !appStore.sidebarCollapsed) {
    appStore.setSidebarCollapsed(true)
  }
  if (!mobile && appStore.sidebarCollapsed) {
    appStore.setSidebarCollapsed(false)
  }
})

// 路由变化时，移动端收起侧边栏
watch(
  () => route.fullPath,
  () => {
    routeViewError.value = null
    if (isMobile.value) {
      appStore.setSidebarCollapsed(true)
    }
  }
)
</script>

<style lang="scss" scoped>
.basic-layout {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(85, 194, 255, 0.06), transparent 24%),
    radial-gradient(circle at 70% 0%, rgba(99, 102, 241, 0.06), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.018), rgba(255, 255, 255, 0)), transparent;
}

.route-error-panel {
  width: min(680px, calc(100% - 32px));
  margin: clamp(56px, 10vh, 120px) auto;
  padding: 42px;
  border: 1px solid rgba(95, 205, 255, 0.18);
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(79, 167, 255, 0.14), transparent 38%),
    linear-gradient(145deg, rgba(17, 37, 68, 0.94), rgba(8, 21, 40, 0.96));
  box-shadow: 0 30px 80px rgba(1, 8, 22, 0.32);
  color: #dcecff;
}

.route-error-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  margin-bottom: 22px;
  border-radius: 13px;
  background: linear-gradient(135deg, #2d79ff, #50d7ff);
  color: #fff;
  font-weight: 800;
  letter-spacing: -0.04em;
  box-shadow: 0 14px 34px rgba(54, 165, 255, 0.28);
}

.route-error-eyebrow {
  margin: 0 0 8px;
  color: #62d8ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.route-error-panel h2 {
  margin: 0 0 12px;
  color: #f5f9ff;
  font-size: clamp(24px, 3vw, 34px);
}

.route-error-panel > p:not(.route-error-eyebrow) {
  margin: 0;
  color: #9db1cc;
  line-height: 1.7;
}

.route-error-actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 950; // 低于侧边栏(1000)，高于内容区
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  background:
    radial-gradient(circle at 26% 0%, rgba(85, 194, 255, 0.1), transparent 24%),
    linear-gradient(180deg, rgba(12, 24, 45, 0.96) 0%, rgba(6, 16, 31, 0.98) 100%);
  border-right: 1px solid rgba(126, 213, 255, 0.1);
  box-shadow: 18px 0 44px rgba(2, 10, 24, 0.22);
  backdrop-filter: blur(24px);
  transition: width 0.3s ease;
  z-index: 1000;
  display: flex;
  flex-direction: column;

  &.collapsed {
    width: 64px !important;
  }

  .sidebar-header {
    height: 78px;
    display: flex;
    align-items: center;
    padding: 0 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;

      .logo-mark {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        isolation: isolate;
      }

      .logo-mark::before {
        content: '';
        position: absolute;
        inset: -4px;
        border-radius: 14px;
        background: radial-gradient(circle, rgba(86, 214, 255, 0.18) 0%, rgba(86, 214, 255, 0) 72%);
        filter: blur(8px);
        pointer-events: none;
      }

      img {
        width: 38px;
        height: 38px;
        position: relative;
        z-index: 1;
        filter: drop-shadow(0 0 14px rgba(86, 214, 255, 0.2))
          drop-shadow(0 10px 18px rgba(9, 42, 96, 0.32));
      }

      .logo-copy {
        display: flex;
        flex-direction: column;
      }

      .logo-text {
        font-size: 16px;
        font-weight: 750;
        color: #edf6ff;
        white-space: nowrap;
        line-height: 1.1;
        letter-spacing: 0.015em;
      }

      .logo-subtitle {
        margin-top: 3px;
        font-size: 11px;
        color: #7893b1;
        white-space: nowrap;
      }
    }
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
    padding: 6px 0 10px;
  }

  .sidebar-footer {
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding: 10px 12px 14px;
    background: rgba(255, 255, 255, 0.015);
  }
}

.main-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease, margin-right 0.28s cubic-bezier(0.22, 0.78, 0.22, 1);

  &.assistant-docked .main-content {
    padding-left: 18px;
    padding-right: 18px;
  }
}

.header {
  height: 60px;
  background: linear-gradient(180deg, rgba(11, 25, 47, 0.82) 0%, rgba(9, 20, 39, 0.72) 100%);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(112, 202, 255, 0.1);
  box-shadow: 0 10px 24px rgba(2, 10, 24, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 999;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .sidebar-toggle {
      padding: 8px;

      .el-icon {
        font-size: 18px;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
}

.main-content {
  flex: 1;
  padding: 24px;
  min-height: calc(100vh - 60px - 60px); // 减去header和footer高度

  .content-wrapper {
    max-width: 1540px;
    margin: 0 auto;
  }
}

.footer {
  min-height: 60px;
  background: rgba(7, 17, 31, 0.32);
  border-top: 1px solid rgba(112, 202, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

// 响应式设计
@media (max-width: 1099px) {
  .sidebar {
    transform: translateX(-100%);

    &:not(.collapsed) {
      transform: translateX(0);
    }
  }

  .main-container {
    margin-left: 0 !important;
  }

  .main-content {
    padding: 12px 12px calc(78px + env(safe-area-inset-bottom));
    min-height: calc(100dvh - 56px);
  }

  .header {
    height: 56px;
    padding: env(safe-area-inset-top) 12px 0;

    .header-left {
      min-width: 0;
      gap: 8px;
    }

    .header-right {
      gap: 6px;
    }
  }

  .footer {
    display: none;
  }

  :deep(.el-backtop) {
    right: 16px !important;
    bottom: calc(76px + env(safe-area-inset-bottom)) !important;
  }
}

// 路由过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.18s ease;
}

.slide-left-enter-from {
  transform: translateX(18px);
  opacity: 0;
}

.slide-left-leave-to {
  transform: translateX(-18px);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .main-container,
  .fade-enter-active,
  .fade-leave-active,
  .slide-left-enter-active,
  .slide-left-leave-active {
    transition: none;
  }

  .slide-left-enter-from,
  .slide-left-leave-to {
    transform: none;
  }
}
</style>
