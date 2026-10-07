import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark' | 'auto'
const widthKey = 'awesome-owner-ui-sidebar-width'
const themeKey = 'awesome-owner-ui-theme-mode'
const privacyKey = 'awesome-owner-ui-privacy-mode'

export const useAppStore = defineStore('app', {
  state: () => ({
    language: 'zh-CN' as 'zh-CN' | 'en-US',
    sidebarCollapsed: false,
    sidebarWidth: 224,
    themeMode: 'light' as ThemeMode,
    theme: 'light' as 'light' | 'dark',
    privacyMode: false,
  }),
  getters: { actualSidebarWidth: state => state.sidebarCollapsed ? 64 : state.sidebarWidth },
  actions: {
    syncSystemTheme() {
      if (this.themeMode !== 'auto') return
      this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      document.documentElement.classList.toggle('dark', this.theme === 'dark')
    },
    setThemeMode(mode: ThemeMode) {
      this.themeMode = mode
      this.theme = mode === 'auto' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : mode
      document.documentElement.classList.toggle('dark', this.theme === 'dark')
      try { localStorage.setItem(themeKey, mode) } catch { /* private storage disabled */ }
    },
    applyTheme(theme: 'light' | 'dark') { this.setThemeMode(theme) },
    setSidebarWidth(width: number) {
      if (!Number.isInteger(width) || width < 216 || width > 280 || width % 4 !== 0) return
      this.sidebarWidth = width
      try { localStorage.setItem(widthKey, String(width)) } catch { /* private storage disabled */ }
    },
    setPrivacyMode(enabled: boolean) {
      this.privacyMode = enabled
      try { localStorage.setItem(privacyKey, String(enabled)) } catch { /* private storage disabled */ }
    },
    togglePrivacyMode() { this.setPrivacyMode(!this.privacyMode) },
    initAppearance() {
      try {
        const stored = localStorage.getItem(themeKey) || localStorage.getItem('awesome-owner-ui-theme')
        this.setThemeMode(stored === 'dark' || stored === 'auto' ? stored : 'light')
        const width = Number(localStorage.getItem(widthKey))
        if (width) this.setSidebarWidth(width)
        this.setPrivacyMode(localStorage.getItem(privacyKey) === 'true')
      } catch { this.setThemeMode('light') }
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => this.syncSystemTheme())
    },
    setSidebarCollapsed(value: boolean) { this.sidebarCollapsed = value },
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed },
  },
})
